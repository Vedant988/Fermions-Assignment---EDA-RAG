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
import sys
import re
import json
import time
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from groq import Groq

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

CHUNK_FILES     = [
    "scraped data/rv32_chunks.json",
    "scraped data/testbench_chunks.json",
]
CHROMA_DIR      = "chroma_store_v3"       # fresh store, separate from v1/v2
COLLECTION_NAME = "rv32i_children"
EMBED_MODEL     = "all-MiniLM-L6-v2"
LLM_MODEL       = "openai/gpt-oss-20b"

CHILD_MAX_TOKENS  = 120       # soft cap for sentence-packer (testbench chunks)
TOP_K_CHILDREN    = 12        # children retrieved before parent dedup
TOP_K_PARENTS     = 4         # unique full parents sent to LLM
RRF_K             = 60
BM25_FETCH        = 15
USE_HYDE          = "--no-hyde" not in sys.argv
OUTPUT_FILE       = "rag_test_results_v3.json"
DATA_DIR          = "scraped data"

# ── Test Questions ─────────────────────────────────────────────────────────────

EVAL_QUESTIONS = [
    "What is the exact bit encoding of the BEQ instruction in RV32I?",
    "How does the JALR instruction compute its target address?",
    "What is the difference between SRL and SRA in RV32I?",
    "How does AUIPC use the program counter?",
    "What happens when you write to register x0 in RV32I?",
    "What sign extension does LH perform on a 16-bit value?",       # was failing
    "What is the byte mask for an SB instruction?",                  # was failing
    "How does the riscv-tests suite signal PASS or FAIL to the testbench?",
    "What RTL invariant does TEST_RR_ZERODEST enforce?",
    "What does TEST_BR2_OP_NOTTAKEN verify about branch logic?",
    "What is the tohost memory address the Verilog testbench must poll?",
    "What modules are needed to implement a single-cycle RV32I processor?",
    "What are the corner cases for the ALU in an RV32I implementation?",
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
            children.append({
                "child_id":      f"{pid}__p{j}",
                "parent_id":     pid,
                "text":          para,
                "section_title": section_title,
                "document_type": str(parent.get("document_type", "unknown")),
                "source_url":    str(parent.get("source_url", "")),
            })
        i += 2

    return children


def build_hierarchy() -> tuple[dict, list[dict]]:
    """
    Dynamically scan the DATA_DIR for all *_chunks.json files.
    Returns:
      parent_store : dict[str → chunk_dict]   (full parent text, NOT embedded)
      all_children : list[child_dict]          (atomic units, embedded into VDB)
    """
    parent_store: dict[str, dict] = {}
    all_children: list[dict] = []
    
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        print(f"  [ERROR] {DATA_DIR} not found.")
        return parent_store, all_children

    json_files = list(data_dir.glob("*_chunks.json"))
    if not json_files:
        print(f"  [WARN] No *_chunks.json files found in {DATA_DIR}.")

    for json_path in json_files:
        slug = json_path.name.replace("_chunks.json", "")
        md_path = data_dir / f"{slug}_full_doc.md"
        
        # Load Parents
        with open(json_path, encoding="utf-8") as f:
            chunks = json.load(f)
            
        for c in chunks:
            pid = str(c.get("chunk_id", ""))
            if pid:
                parent_store[pid] = c
                
        # Try markdown paragraph splitting first
        children = []
        if md_path.exists():
            children = load_children_from_full_doc(str(md_path), parent_store)
            
        if children:
            print(f"  ✓ {slug}: {len(chunks)} parents → {len(children)} children (Markdown Split)")
        else:
            # Fallback to Sentence Packer
            for c in chunks:
                pid = str(c.get("chunk_id", ""))
                if not pid: continue
                text = c.get("document_text", "")[:8000]
                for j, ctext in enumerate(sentence_pack_children(text)):
                    children.append({
                        "child_id":      f"{pid}__c{j}",
                        "parent_id":     pid,
                        "text":          ctext,
                        "section_title": str(c.get("section_title", "")),
                        "document_type": str(c.get("document_type", "unknown")),
                        "source_url":    str(c.get("source_url", "")),
                    })
            print(f"  ✓ {slug}: {len(chunks)} parents → {len(children)} children (Sentence Pack Fallback)")
            
        all_children.extend(children)

    print(f"\n  Total Hierarchy: {len(parent_store)} unique parents, {len(all_children)} atomic children.")
    return parent_store, all_children


def build_chroma_children(children: list[dict], embedder: SentenceTransformer):
    """Embed all children and upsert into ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    BATCH = 100
    total = len(children)
    for i in range(0, total, BATCH):
        batch = children[i: i + BATCH]
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
        print(f"  Embedded {min(i+BATCH, total)}/{total} children...", end="\r")
    print(f"\n  ChromaDB child collection built: {total} children.")
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


# ── LLM Answer ────────────────────────────────────────────────────────────────

def ask_llm(groq_client: Groq, question: str, parents: list[dict]) -> str:
    context_block = "\n\n---\n\n".join(
        f"[Source: {p['section_title']} | child_match: \"{p['child_matched'][:80]}...\"]\n\n{p['full_text']}"
        for p in parents
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert RISC-V RTL design assistant. "
                "Answer using ONLY the provided context. Be precise and technical. "
                "Cite register names, field positions, and hex values when present. "
                "If the context lacks sufficient information, state what is missing."
            )
        },
        {
            "role": "user",
            "content": f"CONTEXT:\n{context_block}\n\nQUESTION: {question}"
        }
    ]
    resp = groq_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
        stream=False,
    )
    return resp.choices[0].message.content


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

    # ── 1. Build hierarchy ────────────────────────────────────────────────────
    print("\n[1/5] Building parent store + child chunks...")
    parent_store, children = build_hierarchy()

    # ── 2. BM25 on children ───────────────────────────────────────────────────
    print("\n[2/5] Building BM25 index over children...")
    bm25, tokenize_fn = build_bm25_children(children)
    print(f"  BM25 ready over {len(children)} children.")

    # ── 3. Dense index on children ────────────────────────────────────────────
    print(f"\n[3/5] Loading embedding model '{EMBED_MODEL}'...")
    embedder = SentenceTransformer(EMBED_MODEL)
    print(f"  Dim: {embedder.get_sentence_embedding_dimension()}")

    print(f"\n[4/5] Embedding {len(children)} children into ChromaDB...")
    collection = build_chroma_children(children, embedder)

    # ── 4. Evaluate ───────────────────────────────────────────────────────────
    print(f"\n[5/5] Running {len(EVAL_QUESTIONS)} questions...")
    print(f"  Config: child_max_tokens={CHILD_MAX_TOKENS}, "
          f"top_k_children={TOP_K_CHILDREN}, top_k_parents={TOP_K_PARENTS}, "
          f"hyde={'ON' if USE_HYDE else 'OFF'}\n")
    results = []

    for i, question in enumerate(EVAL_QUESTIONS):
        print(f"Q{i+1:02d}. {question}")
        print("-" * 62)

        # HyDE
        if USE_HYDE:
            print("  → HyDE...", end="", flush=True)
            embed_q = expand_query_hyde(groq_client, question)
            print(" ✓")
            time.sleep(0.4)
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
            print(f"    [rrf={p['rrf_score']:.5f}] {p['section_title'][:55]}")
            print(f"           child: \"{p['child_matched'][:70]}\"")

        # LLM answer
        try:
            answer = ask_llm(groq_client, question, parents)
        except Exception as e:
            answer = f"[LLM ERROR] {e}"

        print(f"\n  Answer:\n  {answer[:350].replace(chr(10), chr(10)+'  ')}...")
        print()

        results.append({
            "question_id": i + 1,
            "question":    question,
            "hyde_used":   USE_HYDE,
            "child_max_tokens": CHILD_MAX_TOKENS,
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

        time.sleep(1.5)

    # ── 5. Save ───────────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "version":           "v3-parent-child",
            "model":             LLM_MODEL,
            "embed_model":       EMBED_MODEL,
            "child_max_tokens":  CHILD_MAX_TOKENS,
            "top_k_children":    TOP_K_CHILDREN,
            "top_k_parents":     TOP_K_PARENTS,
            "hyde":              USE_HYDE,
            "rrf_k":             RRF_K,
            "total_parents":     len(parent_store),
            "total_children":    len(children),
            "results":           results,
        }, f, indent=2, ensure_ascii=False)

    print("=" * 68)
    print(f"  Results → {OUTPUT_FILE}")
    print(f"  Corpus: {len(parent_store)} parents expanded to {len(children)} children")
    print("=" * 68)


if __name__ == "__main__":
    main()
