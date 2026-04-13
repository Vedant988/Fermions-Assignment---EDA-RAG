"""
researcher_agent.py — Stage 1: The Architect Agent (Universal Hardware Extractor)
=================================================================================
Runs focused, multi-phase RAG+LLM micro-queries to extract structural and behavioral facts
for ANY user-defined hardware accelerator, CPU, or subsystem.

Phases:
1.1 Classification Node: Understands domain constraints
1.2 Question Generator: Base queries + Dynamic domain queries
1.3 Context Router: BM25 specific finding
1.4 Extraction Engine: Async token paced API calls
1.5 Contract Compiler: Validates and dumps to system_facts.json
"""

from __future__ import annotations
import asyncio
import json
import time
import re
from pathlib import Path
from typing import Any

from groq import Groq
from rank_bm25 import BM25Okapi


# ── Async Token Bucket ────────────────────────────────────────────────────────

class AsyncTokenBucket:
    """
    Async rate limiter that reads actual x-ratelimit headers from Groq API
    to dynamically set wait times — never oversleeping, never under-sleeping.

    Tracks both TPM (tokens per minute) and RPM (requests per minute).
    """

    def __init__(self, max_tpm: int = 8000, max_rpm: int = 30):
        self.max_tpm = max_tpm
        self.max_rpm = max_rpm
        self._log: list[tuple[float, int]] = []   # (timestamp, tokens)
        self._remaining_tpm: int | None = None     # from last API header
        self._reset_tpm_in: float = 0.0            # seconds until TPM window resets
        self._lock = asyncio.Lock()

    def update_from_headers(self, headers: dict):
        try:
            rem = headers.get("x-ratelimit-remaining-tokens")
            if rem is not None:
                self._remaining_tpm = int(rem)

            reset_str = headers.get("x-ratelimit-reset-tokens", "0s")
            m = re.match(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s", reset_str)
            if m:
                mins = int(m.group(1) or 0)
                secs = float(m.group(2))
                self._reset_tpm_in = mins * 60 + secs
        except Exception:
            pass

    async def acquire(self, tokens_needed: int) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._log = [(t, tok) for t, tok in self._log if now - t < 60.0]

                used_tokens = sum(tok for _, tok in self._log)
                used_req    = len(self._log)

                if self._remaining_tpm is not None:
                    tpm_ok = self._remaining_tpm >= tokens_needed
                else:
                    tpm_ok = (used_tokens + tokens_needed) <= self.max_tpm

                rpm_ok = used_req < self.max_rpm

                if tpm_ok and rpm_ok:
                    break

                if self._remaining_tpm is not None and self._reset_tpm_in > 0:
                    sleep_for = self._reset_tpm_in + 0.5
                elif self._log:
                    oldest_ts = self._log[0][0]
                    sleep_for = max(0.5, (oldest_ts + 61.0) - now)
                else:
                    sleep_for = 5.0

                rem_display = self._remaining_tpm if self._remaining_tpm is not None else self.max_tpm - used_tokens
                print(f"  ⏳ Token bucket: {rem_display} TPM remaining, need {tokens_needed}. "
                      f"Sleeping {sleep_for:.1f}s...", flush=True)
                await asyncio.sleep(sleep_for)
                self._remaining_tpm = None

    def record(self, tokens_used: int):
        self._log.append((time.monotonic(), tokens_used))


# ── Local BM25 Pre-Filter (Phase 1.3 helper) ──────────────────────────────────

def _bm25_prefilter(question: str, children: list[dict], top_k: int = 2) -> list[str]:
    """
    Zero-cost local BM25 filter to find the most relevant paragraphs.
    """
    def tokenize(t):
        return re.findall(r"[a-zA-Z0-9_\-\.]+", t.lower())

    corpus = [tokenize(c["text"]) for c in children]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(question))
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [children[i]["text"] for i in top_idx]


# ── Hardcoded Base Questions (Phase 1.2 base) ─────────────────────────────────

BASE_QUESTIONS = [
    {
        "key": "ports_and_widths",
        "question": "What are the primary input and output ports, and their bit-widths?",
        "output_schema": "{\"ports\": [{\"name\": \"...\", \"direction\": \"in/out\", \"width\": 32}]}",
        "max_tokens": 200,
    },
    {
        "key": "clock_and_reset",
        "question": "Is the system clock synchronous or asynchronous, and what is the reset behavior (active high/low)?",
        "output_schema": "{\"clock\": \"synchronous/asynchronous\", \"reset\": \"active_high/active_low\"}",
        "max_tokens": 100,
    },
    {
        "key": "memory_interfaces",
        "question": "What are the memory read/write interfaces?",
        "output_schema": "{\"interfaces\": [{\"name\": \"...\", \"type\": \"read/write/rw\"}]}",
        "max_tokens": 150,
    }
]


# ── ArchitectAgent ──────────────────────────────────────────────────────────

# ── ArchitectAgent ──────────────────────────────────────────────────────────

class ArchitectAgent:
    """
    Phase 1.1: Classification Node
    Phase 1.2: Hybrid Question Generator
    Phase 1.3: RAG Filter
    Phase 1.4: Async Fact Engine
    Phase 1.5: Contract Compiler
    """

    def __init__(
        self,
        groq_client: Groq,
        rag_pipe: dict,
        user_prompt: str,
        model: str = "openai/gpt-oss-20b",
        max_tpm: int = 8000,
        max_rpm: int = 30,
    ):
        self.client       = groq_client
        self.pipe         = rag_pipe
        self.user_prompt  = user_prompt
        self.model        = model
        self.bucket       = AsyncTokenBucket(max_tpm=max_tpm, max_rpm=max_rpm)
        
        # New: Global Token Counters for the session
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def _log_usage(self, phase_name: str, usage_obj: Any) -> None:
        """Helper to extract and print token usage from Groq's API response."""
        if usage_obj:
            p_tok = getattr(usage_obj, "prompt_tokens", 0)
            c_tok = getattr(usage_obj, "completion_tokens", 0)
            tot = getattr(usage_obj, "total_tokens", 0)
            
            self.total_prompt_tokens += p_tok
            self.total_completion_tokens += c_tok
            
            print(f"   📊 [{phase_name}] Tokens: {p_tok} IN + {c_tok} OUT = {tot} TOTAL")

    async def run(self) -> dict:
        children = self.pipe["children"]
        print(f"\n🔬 ArchitectAgent processing prompt: '{self.user_prompt}'")
        
        # ── Phase 1.1: Classification ──
        print("   [Phase 1.1] Classifying target hardware...")
        classification = self._phase_1_1_classify()
        print(f"      Domain: {classification.get('hardware_domain')}")
        print(f"      Data Width: {classification.get('data_width')}")
        
        # ── Phase 1.2: Question Generation ──
        print("   [Phase 1.2] Generating dynamic architecture micro-queries...")
        dynamic_questions = self._phase_1_2_generate_questions(classification)
        
        master_query_list = list(BASE_QUESTIONS)
        for i, q_text in enumerate(dynamic_questions):
            master_query_list.append({
                "key": f"dynamic_query_{i+1}",
                "question": q_text,
                "output_schema": "{\"answer\": \"detailed logic constraints\"}",
                "max_tokens": 500, # Increased to prevent cutoff
            })
            
        print(f"      Total questions to execute: {len(master_query_list)}")
        
        # ── Phase 1.3 & 1.4: Vector Filter & Async Fact Extraction ──
        print("   [Phase 1.3 & 1.4] Executing RAG micro-queries...")
        
        # Run sequentially to safely respect rate limits predictability
        results = {}
        for mq in master_query_list:
            key, value = await self._run_micro_query(mq, children)
            results[key] = value
            # Print a snippet of the result to terminal
            print(f"   ✅ {key}: {str(value)[:60]}...")
            
        # ── Phase 1.5: Compiler ──
        print("   [Phase 1.5] Validating and Compiling Contract...")
        
        # Basic validation / fallback
        if "clock_and_reset" not in results or not results["clock_and_reset"] or "error" in results["clock_and_reset"]:
            print("   ⚠️  Clocking missing, applying easy-to-implement default: synchronous, active_low")
            results["clock_and_reset"] = {"clock": "synchronous", "reset": "active_low"}
            
        final_facts = {
            "user_prompt": self.user_prompt,
            "classification": classification,
            "extracted_facts": results
        }
        
        # ── Global Summary ──
        grand_total = self.total_prompt_tokens + self.total_completion_tokens
        print("\n" + "="*50)
        print(" 🏁 SESSION TOKEN SUMMARY")
        print(f"    Input (Prompt) Tokens:     {self.total_prompt_tokens}")
        print(f"    Output (Completion) Tokens:{self.total_completion_tokens}")
        print(f"    Grand Total for Pipeline:  {grand_total}")
        print("="*50 + "\n")
            
        return final_facts

    def _phase_1_1_classify(self) -> dict:
        system  = "You are a Principal Hardware Architect. Classify this request into a strict JSON schema. Output ONLY valid JSON, no markdown fences."
        user = (
            f"Prompt: '{self.user_prompt}'\n\n"
            "Output VALID JSON ONLY, matching exactly this schema:\n"
            "{\n"
            "  \"hardware_domain\": \"accelerator\" (e.g. CPU, accelerator, DSP, crypto),\n"
            "  \"data_width\": 16,\n"
            "  \"core_focus\": [\"MAC units\", \"INT8 math\"],\n"
            "  \"custom_user_quirks\": []\n"
            "}"
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0
        )
        
        # Log the tokens used for Phase 1.1
        self._log_usage("Phase 1.1 Classification", resp.usage)
        
        content = self._extract_json_string(resp.choices[0].message.content)
        try:
            return json.loads(content)
        except Exception as e:
            print(f"   ⚠️ Could not parse 1.1 classification, falling back: {e}")
            return {"hardware_domain": "unknown", "data_width": 32, "core_focus": [], "custom_user_quirks": []}
        
    def _phase_1_2_generate_questions(self, classification: dict) -> list[str]:
        system = "You are a Principal Hardware Architect. Output VALID JSON ONLY as an array of 5 strings. No markdown fences."
        user = (
            f"We are building a {classification.get('hardware_domain')} with a focus on: "
            f"{', '.join(classification.get('core_focus', []))}. "
            f"Data width is {classification.get('data_width', 'unknown')}.\n"
            "Generate the 5 most critical architectural questions we must extract from the manual to write the Verilog logic.\n"
            "Output VALID JSON ONLY as an array of 5 exactly formulated questions."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2
        )
        
        # Log the tokens used for Phase 1.2
        self._log_usage("Phase 1.2 Question Gen", resp.usage)
        
        content = self._extract_json_string(resp.choices[0].message.content)
        try:
            qs = json.loads(content)
            if isinstance(qs, list) and len(qs) > 0:
                return qs[:5]
            return ["What are the critical architectural states?"]
        except Exception as e:
            print(f"   ⚠️ Could not parse 1.2 dynamic questions, falling back: {e}")
            return ["What are the critical functional operations?"]

    async def _run_micro_query(self, mq: dict, children: list[dict]) -> tuple[str, Any]:
        key = mq["key"]
        question = mq["question"]
        
        # 1.3 Context Router logic inside the caller
        top_paragraphs = _bm25_prefilter(question, children, top_k=2)
        context = "\n\n---\n\n".join(top_paragraphs)
        
        # We keep the safe fallback instructions
        system = (
            "You are an expert hardware extraction AI. Extract the exact behavioral logic. "
            "Do not invent signals. Output ONLY valid JSON matching the schema, no markdown fences. "
            "CRITICAL: If the context lacks the answer, DO NOT return empty. Return the requested JSON schema with 'unknown' or null values."
        )
        
        # THE FIX: Inject the user prompt as an absolute OVERRIDE layer
        user = (
            f"USER ARCHITECTURAL CONSTRAINTS (ABSOLUTE OVERRIDE):\n{self.user_prompt}\n\n"
            f"REFERENCE CONTEXT:\n{context}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"SCHEMA:\n{mq['output_schema']}\n"
            "INSTRUCTIONS:\n"
            "1. Extract facts from the REFERENCE CONTEXT to answer the QUESTION.\n"
            "2. CRITICAL VETO: You MUST obey the USER ARCHITECTURAL CONSTRAINTS. If the REFERENCE CONTEXT describes features explicitly excluded by the user (e.g., privilege modes, floating point, caches), IGNORE THEM completely and do not include them in your output.\n"
            "Output ONLY valid JSON."
            "3. ANTI-EXHAUSTION RULE: DO NOT generate exhaustive tables, complete instruction lists, or massive arrays. If the context contains a giant table, extract the underlying RULE or PATTERN and provide only 1 or 2 brief examples. Keep your output concise.\n"
            "Output ONLY valid JSON."
        )
        
        safe_max_tokens = max(mq.get("max_tokens", 300), 3024)
        
        system_tokens = len(system) // 4
        user_tokens = len(user) // 4
        total_tokens = system_tokens + user_tokens + safe_max_tokens
        
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                await self.bucket.acquire(total_tokens)
                raw_resp = self.client.chat.completions.with_raw_response.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.0,
                    max_tokens=safe_max_tokens,
                    
                    # 1. COMMENT OUT THIS LINE to disable the API strict JSON bouncer
                    # response_format={"type": "json_object"} 
                )
                headers = dict(raw_resp.headers)
                self.bucket.update_from_headers(headers)
                self.bucket.record(total_tokens)
                
                parsed_resp = raw_resp.parse()
                self._log_usage(f"Micro-Query: {key}", parsed_resp.usage)
                
                content = parsed_resp.choices[0].message.content
                if not content:
                    raise ValueError("Empty LLM response.")
                
                # 2. ADD THIS PRINT STATEMENT to see exactly what the LLM generated
                print(f"\n\n🚨 --- RAW LLM OUTPUT FOR {key} --- 🚨\n{content}\n---------------------------------------\n")
                    
                content = self._extract_json_string(content)
                parsed = json.loads(content)
                return key, parsed
            except Exception as e:
                last_error = e
                await asyncio.sleep(2)
        
        print(f"   ⚠️ Fallback for {key} due to error: {last_error}")
        return key, {"error": "Extraction failed", "question": question}

    def _extract_json_string(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```\s*$", "", text, flags=re.IGNORECASE).strip()
        
        start = text.find("{")
        start_arr = text.find("[")
        if start == -1 and start_arr == -1: return text
        
        if start != -1 and start_arr != -1:
            idx = min(start, start_arr)
        else:
            idx = max(start, start_arr)
            
        if idx > 0: text = text[idx:]
        
        end = text.rfind("}")
        end_arr = text.rfind("]")
        if end != -1 and end_arr != -1:
            e_idx = max(end, end_arr)
        else:
            e_idx = max(end, end_arr)
            
        if e_idx != -1 and e_idx < len(text) - 1:
            text = text[:e_idx+1]
        return text

# ── Sync wrapper for use inside Streamlit (non-async) ─────────────────────────

def run_architect_sync(
    groq_client: Groq,
    rag_pipe: dict,
    user_prompt: str,
    model: str = "openai/gpt-oss-20b",
) -> dict:
    """
    Synchronous wrapper around the async ArchitectAgent.
    Safe to call from Streamlit or any sync context.
    """
    agent = ArchitectAgent(groq_client, rag_pipe, user_prompt, model)
    return asyncio.run(agent.run())


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    import rag_test as rt

    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY not found in .env")
        exit(1)
        
    client = Groq(api_key=api_key)

    print("Building RAG pipeline...")
    parent_store, children, new_children = rt.build_hierarchy()
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(rt.EMBED_MODEL)
    collection = rt.build_chroma_children(new_children, embedder)
    bm25, tokenize_fn = rt.build_bm25_children(children)

    pipe = {
        "rt": rt,
        "parent_store": parent_store,
        "children": children,
        "bm25": bm25,
        "tokenize_fn": tokenize_fn,
        "embedder": embedder,
        "collection": collection,
    }

    # Simulate user prompt (Phase 1 Intake)
    test_prompt = """You are generating RTL for a **simple in-order RV32I processor** — a 32-bit RISC-V core implementing the base integer instruction set. This is the smallest complete RISC-V ISA: 47 instructions covering arithmetic, loads/stores, branches, and jumps. No floating point, no compressed instructions, no privileged mode required.

A minimal in-order implementation has the following canonical stages:

```
Fetch → Decode → Execute → Memory → Writeback
```

Key components to generate:

| Component | Description |
|---|---|
| **Program Counter (PC)** | Holds current instruction address, updates on branch/jump or sequential increment |
| **Instruction Fetch** | Reads instruction from memory at PC |
| **Decoder** | Decodes opcode, funct3, rs1, rs2, rd, and immediate fields |
| **Register File** | 32 × 32-bit general-purpose registers (x0 hardwired to 0) |
| **ALU** | Performs ADD, SUB, AND, OR, XOR, SLT, shifts |
| **Branch Unit** | Evaluates BEQ, BNE, BLT, BGE, BLTU, BGEU conditions |
| **Load/Store Unit** | Handles LW, LH, LB, SW, SH, SB with byte-enable logic |
| **Control Hazard Handling** | Pipeline flush or stall on taken branches |

> You are **not** expected to implement caches, out-of-order execution, branch prediction, or privilege modes. Focus on a correct, functional RV32I core."""
    
    facts = run_architect_sync(client, pipe, test_prompt)
    
    out_path = Path("system_facts.json")
    with open(out_path, "w") as f:
        json.dump(facts, f, indent=2)
        
    print(f"\\n✅ Phase 1.5 Contract Compiler logic complete!")
    print(f"✅ system_facts.json written → {out_path}")
    print("\\n--- JSON OUTPUT ---")
    print(json.dumps(facts, indent=2))
