"""
RAG Quality Test Harness — v3 (Hierarchical Parent-Child Retrieval)
====================================================================
Standalone script — does NOT touch app.py.

Child Chunk Sources (Why we split by source type):
---------------------------------------------------
  ISA (rv32_full_doc.md):
    Already contains '<!-- chunk_id=N | Section Title -->' dividers produced by
    chunk_isa.py. Within each section the blank lines create natural paragraph
    boundaries — these paragraphs become children. This preserves the doc's own
    visual/semantic spacing as child boundaries (the user's key insight).

  Testbench (testbench_chunks.json):
    No equivalent markdown source. Children are produced by the greedy
    sentence-packer fallback (~120 token budget per child).

Retrieval pipeline:
  Query → HyDE → Dense(children) ┐
  Query →        BM25(children)  ┘ → RRF → top-K children
                                           → expand parent_id → full parent text
                                           → deduplicate → LLM

Usage:
  pip install rank-bm25
  python rag_test.py             # HyDE ON  (best quality)
  python rag_test.py --no-hyde  # HyDE OFF (faster, saves tokens)
"""

import os
import re
import sys
import json
import time
import argparse
import uuid
from typing import List, Dict
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from groq import Groq

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

CHROMA_DIR      = "chroma_store"
COLLECTION_NAME = "rag_children"
EMBED_MODEL     = "all-MiniLM-L6-v2"
LLM_MODEL       = "openai/gpt-oss-20b"
DATA_DIR        = "scraped data"   # ← drop a new *_chunks.json here and it auto-ingests

CHILD_MAX_TOKENS  = 120
TOP_K_CHILDREN    = 12
TOP_K_PARENTS     = 3
RRF_K             = 60
BM25_FETCH        = 15
USE_HYDE = ("--no-hyde" not in sys.argv) if __name__ == "__main__" else False
RESULTS_DIR       = "results"
MANIFEST_FILE     = f"{CHROMA_DIR}/manifest.json"  # tracks ingested slug hashes

# ── Test Questions ─────────────────────────────────────────────────────────────

EVAL_QUESTIONS = [
    # 1. Decode & Immediate Generation
    "How do you structure the Verilog case statements in the Instruction Decoder to safely extract opcodes and route the correct sign-extended immediate logic for R, I, S, B, U, and J formats without inferring latches?",
    
    # 2. Top-Level & Verilator Integration
    "In a SystemVerilog top-level module for a single-cycle RV32I core, how should the clock, synchronous reset, and flat memory interface ports be defined to ensure clean compilation and compatibility with a Verilator C++ testbench?",
    
    # 3. Testbench / tohost interface
    "Write the Verilog monitor logic required in the data memory interface to detect a store operation to the `tohost` address (0x80001000) and extract the pass/fail code for the simulation environment.",
    
    # 4. Byte-masking (Crucial for SB/SH/SW)
    "How do you implement the combinational Verilog logic to generate the 4-bit `dmem_wmask` and align the `rs2` write data for SB, SH, and SW instructions based on the lower 2 bits of the ALU calculated address?",
    
    # 5. Register File x0 Invariant
    "Describe the Verilog implementation of a dual-read, single-write RV32I Register File that natively enforces the x0 hardwired-to-zero invariant, specifically addressing the write-enable gating required to pass TEST_RR_ZERODEST.",
    
    # 6. Branch Logic & Next-PC
    "How do you design the Verilog Next-PC (NPC) multiplexer and branch condition evaluation logic to correctly route either `PC+4` or `PC+imm` synchronously, ensuring no timing loops?",
    
    # 7. Datapath Routing
    "Provide the Verilog structural mapping and control signal assignments needed to multiplex data from the Register File, through the ALU, and back to the Register File write-port during the execution of a standard R-type instruction.",
    
    # 8. Load Alignment & Extension
    "Describe the Verilog multiplexing and bit-slicing logic required in the memory writeback stage to properly shift, sign-extend (LB, LH), or zero-extend (LBU, LHU) the 32-bit raw read data from the data memory.",
    
    # 9. JALR & Alignment Exceptions
    "How do you implement the Verilog logic to clear the LSB for JALR target addresses (`& ~1`), and simultaneously assert an `instruction_misaligned` exception signal if the resulting branch or jump target is not 32-bit aligned?",
    
    # 10. ALU Shifter Logic
    "Explain the SystemVerilog implementation of the ALU's right-shift unit, specifically how to distinguish between SRL (logical) and SRA (arithmetic) utilizing the `$signed()` system task or manual sign-bit replication to avoid synthesis mismatches."
]


# ── Child Splitters ───────────────────────────────────────────────────────────

def rough_token_count(text: str) -> int:
    return int(len(text.split()) * 1.3)


def clean_paragraph(text: str) -> str:
    """Strip markdown noise that makes poor child embeddings."""
    text = re.sub(r'`\[FIGURE:[^\]`]*\]`', '', text)   # `[FIGURE: ...]`
    text = re.sub(r'```[\s\S]*?```', '', text)           # fenced code blocks
    text = re.sub(r'^\|.+\|$', '', text, flags=re.MULTILINE)  # table rows
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)     # blockquote sidebar
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)         # image tags
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)          # links
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text) # bold/italic
    text = re.sub(r'#{1,6}\s+', '', text)               # header markers
    return re.sub(r'[ \t]+', ' ', text).strip()


def paragraphs_from_markdown_section(section_text: str) -> list[str]:
    """
    Split a markdown section into children using BLANK LINES as boundaries.
    This respects the document author's own visual topic spacing — the user's
    key insight: rv32_full_doc.md already uses blank lines to separate distinct
    ideas (endianness, instruction definitions, alignment policy, etc.)
    """
    raw_paras = re.split(r'\n{2,}', section_text)
    children = []
    for para in raw_paras:
        cleaned = clean_paragraph(para)
        if len(cleaned) > 40:        # discard trivial one-liners
            children.append(cleaned)
    return children


def sentence_pack_children(parent_text: str, max_tokens: int = CHILD_MAX_TOKENS) -> list[str]:
    """
    Fallback sentence packer for chunks without a structured markdown source
    (testbench chunks). Greedy accumulate sentences up to token budget.
    """
    # Light clean
    text = re.sub(r'`\[FIGURE:[^\]`]*\]`', '', parent_text)
    text = re.sub(r'\|[^\n]+\|', '', text)
    text = re.sub(r'[ \t]+', ' ', text).strip()

    raw = re.split(r'(?<=[.!?])\s+(?=[A-Z\-`\*])', text)
    sentences = [s.strip() for s in raw if len(s.strip()) > 25]

    children, current, tokens = [], [], 0
    for sent in sentences:
        t = rough_token_count(sent)
        if current and tokens + t > max_tokens:
            children.append(' '.join(current))
            current, tokens = [sent], t
        else:
            current.append(sent)
            tokens += t
    if current:
        children.append(' '.join(current))
    return [c for c in children if len(c) > 30]


# ── Build Parent Store + Child Index ─────────────────────────────────────────

def load_children_from_full_doc(full_doc_path: str, parent_store: dict) -> list[dict]:
    """
    Parse a {slug}_full_doc.md using the <!-- chunk_id=N | Title --> dividers.
    Splits each section's text by blank lines to produce paragraph-level children.
    This respects the document author's own visual spacing for child boundaries.
    """
    p = Path(full_doc_path)
    if not p.exists():
        return []

    raw = p.read_text(encoding="utf-8")
    
    # Matches "<!-- chunk_id=12 | Title -->", "<!-- rv32ui_add -->", etc.
    parts = re.split(r'<!--\s*(.*?)\s*-->', raw)
    children: list[dict] = []

    i = 1
    while i + 1 < len(parts):
        tag = parts[i].strip()
        section_text = parts[i + 1]

        # Parse tag
        if tag.startswith("chunk_id="):
            tag = tag.replace("chunk_id=", "")
        tag_parts = tag.split("|", 1)
        pid = tag_parts[0].strip()
        section_title = tag_parts[1].strip() if len(tag_parts) > 1 else str(parent_store.get(pid, {}).get("section_title", ""))

        parent = parent_store.get(pid, {})

        paras = paragraphs_from_markdown_section(section_text)
        for j, para in enumerate(paras):
            unique_hex = uuid.uuid4().hex[:6]
            children.append({
                "child_id":      f"{pid}__p{j}_{unique_hex}",
                "parent_id":     pid,
                "text":          para,
                "section_title": section_title,
                "document_type": str(parent.get("document_type", "unknown")),
                "source_url":    str(parent.get("source_url", "")),
            })
        i += 2

    return children


def _file_hash(path: Path) -> str:
    """MD5 hash of a file's content — used to detect if a chunk file changed."""
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_manifest() -> dict:
    """Load the ingestion manifest (slug → file_hash) from disk."""
    p = Path(MANIFEST_FILE)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    """Persist the manifest back to disk."""
    Path(CHROMA_DIR).mkdir(exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def build_hierarchy() -> tuple[dict, list[dict], list[dict]]:
    """
    Dynamically scan the DATA_DIR for all *_chunks.json files.
    Returns:
      parent_store   : dict[str → chunk_dict]  (ALL parents, for retrieval)
      all_children   : list[child_dict]         (ALL children, for BM25)
      new_children   : list[child_dict]         (only CHANGED/NEW ones, for ChromaDB)
    """
    parent_store: dict[str, dict] = {}
    all_children: list[dict] = []
    new_children: list[dict] = []

    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        print(f"  [ERROR] {DATA_DIR} not found.")
        return parent_store, all_children, new_children

    json_files = list(data_dir.glob("*_chunks.json"))
    if not json_files:
        print(f"  [WARN] No *_chunks.json files found in {DATA_DIR}.")

    manifest = load_manifest()

    for json_path in json_files:
        slug = json_path.name.replace("_chunks.json", "")
        md_path = data_dir / f"{slug}_full_doc.md"
        current_hash = _file_hash(json_path)
        is_new = manifest.get(slug) != current_hash

        # Load Parents (always — needed for retrieval)
        with open(json_path, encoding="utf-8") as f:
            chunks = json.load(f)

        for c in chunks:
            pid = str(c.get("chunk_id", ""))
            if pid:
                parent_store[pid] = c

        # Build children for this slug
        children: list[dict] = []
        if md_path.exists():
            children = load_children_from_full_doc(str(md_path), parent_store)

        if not children:
            for c in chunks:
                pid = str(c.get("chunk_id", ""))
                if not pid: continue
                text = c.get("document_text", "")[:8000]
                for j, ctext in enumerate(sentence_pack_children(text)):
                    unique_hex = uuid.uuid4().hex[:6]
                    children.append({
                        "child_id":      f"{pid}__c{j}_{unique_hex}",
                        "parent_id":     pid,
                        "text":          ctext,
                        "section_title": str(c.get("section_title", "")),
                        "document_type": str(c.get("document_type", "unknown")),
                        "source_url":    str(c.get("source_url", "")),
                    })

        all_children.extend(children)

        tag = "[NEW]" if is_new else "[cached]"
        src = "Markdown Split" if md_path.exists() else "Sentence Pack"
        print(f"  {tag} {slug}: {len(chunks)} parents → {len(children)} children ({src})")

        if is_new:
            new_children.extend(children)
            manifest[slug] = current_hash  # update after processing

    save_manifest(manifest)
    print(f"\n  Total : {len(parent_store)} parents | {len(all_children)} children | {len(new_children)} NEW to embed.")
    return parent_store, all_children, new_children


def build_chroma_children(new_children: list[dict], embedder: SentenceTransformer):
    """
    Incrementally upsert only NEW children into the persistent ChromaDB.
    The collection is NEVER wiped — existing embeddings from previous runs are kept.
    If new_children is empty, just opens the existing collection.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    # Get-or-create (never delete)
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        existing_count = collection.count()
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        existing_count = 0

    if not new_children:
        print(f"  ChromaDB up-to-date. {existing_count} children already indexed.")
        return collection

    BATCH = 100
    total = len(new_children)
    for i in range(0, total, BATCH):
        batch = new_children[i: i + BATCH]
        ids        = [c["child_id"] for c in batch]
        documents  = [c["text"] for c in batch]
        metas      = [{
            "parent_id":     c.get("parent_id", ""),
            "section_title": c.get("section_title", "Untitled"),
            "instruction":   c.get("instruction", ""),
            "document_type": c.get("document_type", "unknown"),
            "source_url":    c.get("source_url", ""),
        } for c in batch]
        embeddings = embedder.encode(documents, show_progress_bar=False).tolist()
        collection.upsert(ids=ids, documents=documents,
                          embeddings=embeddings, metadatas=metas)
        print(f"  Embedded {min(i+BATCH, total)}/{total} new children...", end="\r")
    print(f"\n  ChromaDB updated: +{total} new children (total: {collection.count()}).")
    return collection


def build_bm25_children(children: list[dict]):
    """BM25 index over child texts."""
    def tokenize(t):
        return re.findall(r"[a-zA-Z0-9_\-\.]+", t.lower())
    corpus = [tokenize(c["text"]) for c in children]
    return BM25Okapi(corpus), tokenize


# ── HyDE ──────────────────────────────────────────────────────────────────────

HYDE_SYSTEM = """You are a technical document writer for RISC-V ISA specifications and RTL verification.
Given a question, write a SHORT hypothetical passage (3-5 sentences) that would appear in a
RISC-V specification document or testbench reference manual that directly answers the question.
Write in spec style — use field names, hex values, signal names, register notation.
Output ONLY the passage text, no preamble."""

def expand_query_hyde(groq_client: Groq, question: str) -> str:
    try:
        resp = groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": HYDE_SYSTEM},
                {"role": "user",   "content": question},
            ],
            temperature=0.2,
            max_tokens=180,
            stream=False,
        )
        return f"{question}\n\n{resp.choices[0].message.content.strip()}"
    except Exception as e:
        print(f"    [HYDE WARN] {e}")
        return question


# ── Dense + Sparse + RRF ──────────────────────────────────────────────────────

def dense_retrieve_children(collection, embedder, query_text: str, n: int) -> list[dict]:
    q_emb = embedder.encode([query_text]).tolist()
    res   = collection.query(query_embeddings=q_emb, n_results=n)
    hits  = []
    for rank, (doc, meta, dist) in enumerate(zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    )):
        hits.append({
            "child_text":    doc,
            "parent_id":     meta["parent_id"],
            "section_title": meta["section_title"],
            "dense_score":   round(1 - dist, 4),
            "dense_rank":    rank,
        })
    return hits


def sparse_retrieve_children(bm25, tokenize_fn, children: list[dict],
                              question: str, n: int) -> list[dict]:
    scores  = bm25.get_scores(tokenize_fn(question))
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
    hits    = []
    for rank, idx in enumerate(top_idx):
        c = children[idx]
        hits.append({
            "child_text":    c["text"],
            "parent_id":     c["parent_id"],
            "section_title": c["section_title"],
            "bm25_score":    round(float(scores[idx]), 4),
            "bm25_rank":     rank,
        })
    return hits


def rrf_fuse_children(dense: list[dict], sparse: list[dict],
                      k: int = RRF_K, top_n: int = TOP_K_CHILDREN) -> list[dict]:
    """
    RRF on child hits. Key = child_text (unique per child).
    Returns children sorted by fused RRF score.
    """
    scores:   dict[str, float] = defaultdict(float)
    payloads: dict[str, dict]  = {}

    for rank, h in enumerate(dense):
        key = h["child_text"][:120]
        scores[key]   += 1.0 / (k + rank + 1)
        payloads[key]  = h

    for rank, h in enumerate(sparse):
        key = h["child_text"][:120]
        scores[key]   += 1.0 / (k + rank + 1)
        if key not in payloads:
            payloads[key] = h

    ranked = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    result = []
    for key in ranked:
        entry = payloads[key].copy()
        entry["rrf_score"] = round(scores[key], 6)
        result.append(entry)
    return result


def expand_to_parents(fused_children: list[dict], parent_store: dict,
                      top_n: int = TOP_K_PARENTS) -> list[dict]:
    """
    THE KEY STEP: map each child → its full parent chunk.
    Deduplicate parents (multiple high-scoring children may share one parent).
    Return the union of top-N unique parent full texts for LLM context.
    """
    seen_parents: set[str] = set()
    parents_for_llm = []

    for child in fused_children:
        pid = child["parent_id"]
        if pid in seen_parents:
            continue   # already have this parent
        seen_parents.add(pid)

        parent = parent_store.get(pid, {})
        parents_for_llm.append({
            "parent_id":     pid,
            "section_title": parent.get("section_title", pid),
            "full_text":     parent.get("document_text", child["child_text"])[:6000],
            "child_matched": child["child_text"],
            "rrf_score":     child["rrf_score"],
        })

        if len(parents_for_llm) >= top_n:
            break

    return parents_for_llm


# Token budget constants
MAX_INPUT_TOKENS  = 5500   # hard cap — stay well under Groq 8000 TPM limit
MAX_OUTPUT_TOKENS = 4500

def count_tokens(text: str) -> int:
    """Fast heuristic: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def build_prompt(question: str, parents: list[dict]) -> tuple[list[dict], int]:
    """
    Build the messages list, hard-truncating each parent's full_text so the
    total estimated input token count stays under MAX_INPUT_TOKENS.
    Returns (messages, estimated_prompt_token_count).
    """
    SYSTEM = (
        "You are an expert RISC-V RTL design assistant. "
        "Answer using ONLY the provided context. Be precise and technical. "
        "Cite register names, field positions, and hex values when present. "
        "If the context lacks sufficient information, state what is missing."
    )
    # Fixed overhead: system + question + formatting separators
    fixed_tokens = count_tokens(SYSTEM) + count_tokens(question) + 60
    budget = MAX_INPUT_TOKENS - fixed_tokens

    # Distribute budget equally across parents (chars = tokens * 4)
    per_parent_chars = max(200, (budget // max(len(parents), 1)) * 4)

    context_parts = []
    for p in parents:
        header = f"[Source: {p['section_title']} | child_match: \"{p['child_matched'][:80]}...\"]"
        text   = p["full_text"][:per_parent_chars]
        context_parts.append(f"{header}\n\n{text}")

    context_block = "\n\n---\n\n".join(context_parts)
    user_content  = f"CONTEXT:\n{context_block}\n\nQUESTION: {question}"

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": user_content},
    ]
    total_tokens = count_tokens(SYSTEM) + count_tokens(user_content)
    return messages, total_tokens


def ask_llm(groq_client: Groq, question: str, parents: list[dict],
            rate_limiter=None) -> tuple[str, int]:
    messages, prompt_tokens = build_prompt(question, parents)
    total_request_tokens = prompt_tokens + MAX_OUTPUT_TOKENS

    # Wait for rate-limit headroom before calling
    if rate_limiter is not None:
        rate_limiter.wait(total_request_tokens)

    resp = groq_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=MAX_OUTPUT_TOKENS,
        stream=False,
    )

    if rate_limiter is not None:
        rate_limiter.record(total_request_tokens)

    content = resp.choices[0].message.content
    if not content:
        return "[LLM ERROR] API returned empty content — input may have been filtered or exceeded limit silently.", prompt_tokens
    return content, prompt_tokens


# ── Rate Limiter ───────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Sliding-window rate limiter that enforces:
      - max_tpm  : max tokens per 60-second window
      - max_rpm  : max requests per 60-second window
    Automatically sleeps until there is enough headroom before each request.
    """
    def __init__(self, max_tpm: int = 8000, max_rpm: int = 30):
        self.max_tpm = max_tpm
        self.max_rpm = max_rpm
        self._log: list[tuple[float, int]] = []  # (timestamp, tokens_used)

    def _purge(self):
        """Remove entries older than 60 seconds."""
        cutoff = time.time() - 60.0
        self._log = [(t, tok) for t, tok in self._log if t > cutoff]

    def _used_tokens(self) -> int:
        self._purge()
        return sum(tok for _, tok in self._log)

    def _used_requests(self) -> int:
        self._purge()
        return len(self._log)

    def wait(self, tokens_needed: int):
        """Block until this request can safely be made within rate limits."""
        while True:
            self._purge()
            tpm_ok = (self._used_tokens() + tokens_needed) <= self.max_tpm
            rpm_ok = self._used_requests() < self.max_rpm

            if tpm_ok and rpm_ok:
                break

            # Calculate how long until the oldest entry expires
            if self._log:
                oldest_ts = self._log[0][0]
                sleep_for = max(0.5, (oldest_ts + 61.0) - time.time())
            else:
                sleep_for = 5.0

            used_tok = self._used_tokens()
            used_req = self._used_requests()
            print(f"\n  ⏳ Rate limit: {used_tok}/{self.max_tpm} tok used, "
                  f"{used_req}/{self.max_rpm} req — sleeping {sleep_for:.1f}s...")
            time.sleep(sleep_for)

    def record(self, tokens_used: int):
        """Record a completed API call."""
        self._log.append((time.time(), tokens_used))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found in .env")
    groq_client = Groq(api_key=api_key)

    print("=" * 68)
    print(f"  RAG v3 — Parent-Child Hierarchical Retrieval"
          + (" + HyDE" if USE_HYDE else ""))
    print("=" * 68)

    # ── 1. Build hierarchy ──────────────────────────────────────────────────────
    print("\n[1/5] Building parent store + child chunks...")
    parent_store, children, new_children = build_hierarchy()

    # Rate limiter (8K TPM, 30 RPM  — from Groq docs for openai/gpt-oss-20b)
    limiter = RateLimiter(max_tpm=8000, max_rpm=30)
    print(f"  Rate limiter: {limiter.max_tpm} TPM / {limiter.max_rpm} RPM")

    # ── 2. BM25 on children ───────────────────────────────────────────────────
    print("\n[2/5] Building BM25 index over children...")
    bm25, tokenize_fn = build_bm25_children(children)
    print(f"  BM25 ready over {len(children)} children.")

    # ── 3. Dense index on children ────────────────────────────────────────────
    print(f"\n[3/5] Loading embedding model '{EMBED_MODEL}'...")
    embedder = SentenceTransformer(EMBED_MODEL)
    print(f"  Dim: {embedder.get_sentence_embedding_dimension()}")

    print(f"\n[4/5] Incrementally embedding into ChromaDB...")
    collection = build_chroma_children(new_children, embedder)

    # ── 4. Evaluate ─────────────────────────────────────────────────────────────
    print(f"\n[5/5] Running {len(EVAL_QUESTIONS)} questions...")
    print(f"  Config: child_max_tokens={CHILD_MAX_TOKENS}, "
          f"top_k_children={TOP_K_CHILDREN}, top_k_parents={TOP_K_PARENTS}, "
          f"hyde={'ON' if USE_HYDE else 'OFF'}\n")

    # 60-second warm-up: ensures the TPM window is fully clear before Q1
    print("  ⏳ 60s safety warm-up (clearing TPM window before Q1)...", flush=True)
    time.sleep(60)
    print("  ✓ Ready.\n")
    results = []

    for i, question in enumerate(EVAL_QUESTIONS):
        print(f"Q{i+1:02d}. {question}")
        print("-" * 62)

        # HyDE (also counts toward rate limit)
        if USE_HYDE:
            print("  → HyDE...", end="", flush=True)
            embed_q = expand_query_hyde(groq_client, question)
            print(" ✓")
        else:
            embed_q = question

        # Dense child retrieval
        dense_hits  = dense_retrieve_children(collection, embedder, embed_q, TOP_K_CHILDREN)

        # Sparse child retrieval (always on raw question)
        sparse_hits = sparse_retrieve_children(bm25, tokenize_fn, children, question, BM25_FETCH)

        # RRF fuse children
        fused_children = rrf_fuse_children(dense_hits, sparse_hits,
                                           k=RRF_K, top_n=TOP_K_CHILDREN)

        # ← THE KEY STEP: expand child → full parent
        parents = expand_to_parents(fused_children, parent_store, top_n=TOP_K_PARENTS)

        # Print telemetry
        print(f"  Parents fetched ({len(parents)}) via child expansion:")
        for p in parents:
            ptok = count_tokens(p['full_text'])
            print(f"    [rrf={p['rrf_score']:.5f}] ({ptok} tok) {p['section_title'][:50]}")
            print(f"           child: \"{p['child_matched'][:70]}\"")

        # LLM answer
        try:
            answer, prompt_tokens = ask_llm(groq_client, question, parents,
                                            rate_limiter=limiter)
        except Exception as e:
            answer = f"[LLM ERROR] {e}"
            prompt_tokens = -1

        print(f"\n  ┌─ Token Budget ──────────────────────────────────────────")
        print(f"  │  Input (prompt): {prompt_tokens:>5} tok   Max output: {MAX_OUTPUT_TOKENS} tok   Hard cap: {MAX_INPUT_TOKENS} tok")
        bar_pct = min(prompt_tokens / MAX_INPUT_TOKENS, 1.0)
        bar_len = int(bar_pct * 40)
        bar = '█' * bar_len + '░' * (40 - bar_len)
        flag = " ⚠️  OVER BUDGET" if prompt_tokens > MAX_INPUT_TOKENS else ""
        print(f"  └  [{bar}] {bar_pct*100:.1f}%{flag}")
        print(f"\n  Answer:\n  {answer[:350].replace(chr(10), chr(10)+'  ')}...")
        print()

        results.append({
            "question_id":      i + 1,
            "question":         question,
            "hyde_used":        USE_HYDE,
            "child_max_tokens": CHILD_MAX_TOKENS,
            "prompt_tokens":    prompt_tokens,
            "parents_retrieved": [
                {
                    "parent_id":     p["parent_id"],
                    "section_title": p["section_title"],
                    "rrf_score":     p["rrf_score"],
                    "child_matched": p["child_matched"],
                }
                for p in parents
            ],
            "answer": answer,
        })

    # ── 5. Save ───────────────────────────────────────────────────────────────
    out_dir = Path(RESULTS_DIR)
    out_dir.mkdir(exist_ok=True)

    # Find the next incremental version number across ALL result files
    existing = list(out_dir.glob("rag_test_results_v*.json"))
    max_id = 0
    for f_path in existing:
        m = re.search(r'_v(\d+)\.json$', f_path.name)
        if m:
            max_id = max(max_id, int(m.group(1)))
    next_id = max_id + 1
    output_file = out_dir / f"rag_test_results_v{next_id}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version":           f"v{next_id}-parent-child",
            "run_timestamp":     time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model":             LLM_MODEL,
            "embed_model":       EMBED_MODEL,
            "child_max_tokens":  CHILD_MAX_TOKENS,
            "top_k_children":    TOP_K_CHILDREN,
            "top_k_parents":     TOP_K_PARENTS,
            "hyde":              USE_HYDE,
            "rrf_k":             RRF_K,
            "max_input_tokens":  MAX_INPUT_TOKENS,
            "num_questions":     len(EVAL_QUESTIONS),
            "total_parents":     len(parent_store),
            "total_children":    len(children),
            "results":           results,
        }, f, indent=2, ensure_ascii=False)

    print("=" * 68)
    print(f"  Results → {output_file}")
    print(f"  Corpus: {len(parent_store)} parents expanded to {len(children)} children")
    print("=" * 68)


if __name__ == "__main__":
    main()
