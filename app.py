"""
RISC-V RAG Assistant — Streamlit App
=====================================
Calls the pipeline functions from rag_test.py directly (no code duplication).
Uses chunk.py via subprocess for live URL ingestion.

Run:
    streamlit run app.py
"""

import os
import sys
import json
import time
import glob
import subprocess
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RISC-V RAG Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark glassmorphism background */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1528 50%, #0a1020 100%);
    min-height: 100vh;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(13, 21, 40, 0.95);
    border-right: 1px solid rgba(99, 179, 237, 0.15);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #94a3b8;
    font-weight: 500;
    padding: 8px 20px;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important;
}

/* Cards */
.rag-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 14px;
    transition: border-color 0.2s;
}
.rag-card:hover {
    border-color: rgba(99,179,237,0.35);
}
.rag-card-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: #63b3ed;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.rag-card-body {
    font-size: 0.88rem;
    color: #cbd5e1;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.5;
}
.score-badge {
    display: inline-block;
    background: rgba(99,179,237,0.18);
    color: #90cdf4;
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}
.tok-badge {
    display: inline-block;
    background: rgba(139,92,246,0.18);
    color: #c4b5fd;
    border-radius: 6px;
    padding: 2px 9px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
}
.answer-box {
    background: rgba(16,24,40,0.85);
    border: 1px solid rgba(99,179,237,0.2);
    border-left: 4px solid #3b82f6;
    border-radius: 10px;
    padding: 20px 24px;
    color: #e2e8f0;
    font-size: 0.9rem;
    line-height: 1.7;
    white-space: pre-wrap;
}
.budget-bar-wrap {
    background: rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 12px 16px;
    margin: 10px 0 16px 0;
    border: 1px solid rgba(255,255,255,0.08);
}
.stat-pill {
    display: inline-block;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #93c5fd;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 3px;
}
</style>
""", unsafe_allow_html=True)

# ── Lazy-import pipeline from rag_test.py ─────────────────────────────────────
@st.cache_resource(show_spinner="⚙️ Initialising RAG pipeline...")
def load_pipeline():
    """
    Import and initialise the full RAG pipeline once.
    Returns everything needed for retrieval.
    """
    # Ensure project root is on path
    project_root = str(Path(__file__).parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Import shared constants and functions from rag_test
    import rag_test as rt

    parent_store, children, new_children = rt.build_hierarchy()

    bm25, tokenize_fn = rt.build_bm25_children(children)

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(rt.EMBED_MODEL)

    collection = rt.build_chroma_children(new_children, embedder)

    return {
        "rt":           rt,
        "parent_store": parent_store,
        "children":     children,
        "bm25":         bm25,
        "tokenize_fn":  tokenize_fn,
        "embedder":     embedder,
        "collection":   collection,
    }


def run_retrieval(pipe, question: str, use_hyde: bool, groq_client, top_k_parents: int, top_k_children: int):
    """Run the full retrieval chain and return parents + token info."""
    rt = pipe["rt"]

    # HyDE expansion
    if use_hyde:
        embed_q = rt.expand_query_hyde(groq_client, question)
    else:
        embed_q = question

    dense_hits  = rt.dense_retrieve_children(pipe["collection"], pipe["embedder"], embed_q, top_k_children)
    sparse_hits = rt.sparse_retrieve_children(pipe["bm25"], pipe["tokenize_fn"], pipe["children"], question, rt.BM25_FETCH)
    fused       = rt.rrf_fuse_children(dense_hits, sparse_hits, k=rt.RRF_K, top_n=top_k_children)
    parents     = rt.expand_to_parents(fused, pipe["parent_store"], top_n=top_k_parents)
    return parents


# ── Corpus stats helper ────────────────────────────────────────────────────────
def corpus_stats():
    data_dir = Path("scraped data")
    rows = []
    for jp in sorted(data_dir.glob("*_chunks.json")):
        slug = jp.name.replace("_chunks.json", "")
        with open(jp, encoding="utf-8") as f:
            chunks = json.load(f)
        total_words = sum(len(c.get("document_text","").split()) for c in chunks)
        doc_types   = {}
        for c in chunks:
            dt = c.get("document_type", "unknown")
            doc_types[dt] = doc_types.get(dt, 0) + 1
        rows.append({
            "Slug": slug,
            "Chunks": len(chunks),
            "Est. Tokens": int(total_words * 1.3),
            "Doc Types": ", ".join(f"{k}:{v}" for k,v in sorted(doc_types.items())),
        })
    return rows


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ RISC-V RAG")
    st.markdown("*Knowledge-grounded RTL Assistant*")
    st.divider()

    api_key = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Overrides GROQ_API_KEY from .env",
    )

    st.divider()
    st.markdown("### Retrieval Settings")
    top_k_parents  = st.slider("Top-K Parents sent to LLM", 1, 5, 3)
    top_k_children = st.slider("Top-K Children fetched", 6, 20, 12)
    use_hyde        = st.toggle("Enable HyDE (experimental — OFF recommended for this corpus)", value=False)

    st.divider()
    st.markdown("### Model")
    st.code("openai/gpt-oss-20b", language=None)
    st.caption("8K TPM · 30 RPM · Groq hosted")

    st.divider()
    if st.button("🔄 Reload Pipeline", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()


# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 28px 0 16px 0;">
    <h1 style="font-size:2.2rem; font-weight:700; color:#e2e8f0; margin:0; letter-spacing:-0.03em;">
        ⚡ RISC-V RAG Assistant
    </h1>
    <p style="color:#64748b; margin:6px 0 0 0; font-size:0.95rem;">
        Hierarchical Parent-Child Retrieval · BM25 + Dense + RRF · HyDE augmentation
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_qa, tab_ingest, tab_corpus = st.tabs(["🔍 RAG Q&A", "📥 Ingest URL", "📚 Corpus"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RAG Q&A
# ═══════════════════════════════════════════════════════════════════════════════
with tab_qa:
    st.markdown("### Ask a RISC-V Architecture Question")
    st.caption("The pipeline retrieves from your ingested corpus, then grounds the LLM answer in those sources.")

    question = st.text_area(
        "Question",
        placeholder="e.g. How do you implement the 4-bit byte-mask for SB, SH and SW instructions?",
        height=90,
        label_visibility="collapsed",
    )

    col_run, col_clear = st.columns([5, 1])
    with col_run:
        run_btn = st.button("⚡ Retrieve & Answer", type="primary", use_container_width=True,
                            disabled=not question.strip())
    with col_clear:
        if st.button("✕ Clear", use_container_width=True):
            st.rerun()

    if run_btn and question.strip():
        if not api_key:
            st.error("❌ Please enter your Groq API Key in the sidebar.")
            st.stop()

        from groq import Groq
        groq_client = Groq(api_key=api_key)

        # Load pipeline (cached)
        with st.spinner("Loading pipeline..."):
            pipe = load_pipeline()

        rt = pipe["rt"]

        # ── Retrieval ─────────────────────────────────────────────────────────
        with st.spinner("🔍 Retrieving relevant chunks..."):
            if use_hyde:
                st.info("💭 HyDE enabled — generating hypothetical passage first...")
            parents = run_retrieval(pipe, question, use_hyde, groq_client, top_k_parents, top_k_children)

        # ── Source cards ──────────────────────────────────────────────────────
        st.markdown(f"#### 📎 Top {len(parents)} Parent Sources")
        for p in parents:
            ptok = rt.count_tokens(p["full_text"])
            st.markdown(f"""
<div class="rag-card">
    <div class="rag-card-title">
        {p['section_title']}
        &nbsp;&nbsp;<span class="score-badge">RRF {p['rrf_score']:.4f}</span>
        &nbsp;<span class="tok-badge">{ptok} tok</span>
    </div>
    <div class="rag-card-body">
        <b>Matched child:</b> {p['child_matched'][:200]}
    </div>
</div>""", unsafe_allow_html=True)

        # ── Token budget bar ──────────────────────────────────────────────────
        messages, prompt_tokens = rt.build_prompt(question, parents)
        total_req = prompt_tokens + rt.MAX_OUTPUT_TOKENS
        pct = min(prompt_tokens / rt.MAX_INPUT_TOKENS, 1.0)
        bar_filled = int(pct * 36)
        bar = "█" * bar_filled + "░" * (36 - bar_filled)
        over = "⚠️ OVER BUDGET" if prompt_tokens > rt.MAX_INPUT_TOKENS else ""

        st.markdown(f"""
<div class="budget-bar-wrap">
    <span class="stat-pill">📥 Prompt: {prompt_tokens} tok</span>
    <span class="stat-pill">📤 Max output: {rt.MAX_OUTPUT_TOKENS} tok</span>
    <span class="stat-pill">🔒 Cap: {rt.MAX_INPUT_TOKENS} tok</span>
    {"<span class='stat-pill' style='background:rgba(239,68,68,0.2);color:#fca5a5;border-color:#ef4444;'>⚠️ OVER BUDGET</span>" if over else ""}
    <br><br>
    <code style="color:#94a3b8;">[{bar}] {pct*100:.1f}%</code>
</div>""", unsafe_allow_html=True)

        # ── LLM Answer ────────────────────────────────────────────────────────
        st.markdown("#### 💡 Answer")
        answer_placeholder = st.empty()
        answer_placeholder.markdown('<div class="answer-box">⏳ Generating answer...</div>', unsafe_allow_html=True)

        try:
            limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)
            answer, used_tokens = rt.ask_llm(groq_client, question, parents, rate_limiter=limiter)
            answer_placeholder.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
        except Exception as e:
            answer_placeholder.error(f"❌ LLM Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ingest URL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ingest:
    st.markdown("### 📥 Ingest a New Knowledge Source")
    st.caption("Calls `chunk.py` to scrape, chunk, and save the new source. The pipeline auto-picks it up on next reload.")

    col_url, col_slug = st.columns([3, 1])
    with col_url:
        ingest_url = st.text_input(
            "URL",
            placeholder="https://github.com/lowRISC/ibex or https://example.com/spec.pdf",
            label_visibility="visible",
        )
    with col_slug:
        ingest_slug = st.text_input("Slug (output filename prefix)", placeholder="ibex")

    ingest_btn = st.button(
        "🚀 Run Ingest",
        type="primary",
        use_container_width=True,
        disabled=not (ingest_url.strip() and ingest_slug.strip()),
    )

    if ingest_btn:
        slug = ingest_slug.strip().lower().replace(" ", "_")
        url  = ingest_url.strip()

        st.info(f"▶️ Running: `python3 chunk.py {url} --slug {slug}`")
        log_area = st.empty()
        full_log = ""

        cmd = [sys.executable, "chunk.py", url, "--slug", slug]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(Path(__file__).parent),
        )

        for line in proc.stdout:
            full_log += line
            log_area.code(full_log, language="bash")

        proc.wait()
        if proc.returncode == 0:
            st.success(f"✅ Ingestion complete! `scraped data/{slug}_chunks.json` is ready.")
            st.info("💡 Click **Reload Pipeline** in the sidebar to embed the new data into ChromaDB.")
        else:
            st.error(f"❌ chunk.py exited with code {proc.returncode}. Check the log above.")

        # Show output files
        chunks_file = Path(f"scraped data/{slug}_chunks.json")
        if chunks_file.exists():
            with open(chunks_file, encoding="utf-8") as f:
                chunks = json.load(f)
            st.markdown(f"**Output:** `{chunks_file}` — **{len(chunks)} chunks**")
            with st.expander("Preview first 3 chunks"):
                for c in chunks[:3]:
                    st.json({k: str(v)[:300] for k, v in c.items()})


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Corpus
# ═══════════════════════════════════════════════════════════════════════════════
with tab_corpus:
    st.markdown("### 📚 Knowledge Base Corpus")
    st.caption("All `*_chunks.json` files currently in `scraped data/`. Drop new ones in and reload the pipeline.")

    data_dir = Path("scraped data")
    if not data_dir.exists():
        st.warning("⚠️ `scraped data/` directory not found.")
    else:
        rows = corpus_stats()
        if not rows:
            st.info("No chunks found yet. Use the **Ingest URL** tab to add sources.")
        else:
            # Summary metrics
            total_chunks = sum(r["Chunks"] for r in rows)
            total_tokens = sum(r["Est. Tokens"] for r in rows)

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("📦 Total Sources", len(rows))
            mc2.metric("🧩 Total Chunks", f"{total_chunks:,}")
            mc3.metric("🔢 Est. Total Tokens", f"{total_tokens:,}")

            st.divider()

            # Per-slug cards
            for r in rows:
                slug_path = data_dir / f"{r['Slug']}_chunks.json"
                md_path   = data_dir / f"{r['Slug']}_full_doc.md"
                has_md    = md_path.exists()

                st.markdown(f"""
<div class="rag-card">
    <div class="rag-card-title">
        {r['Slug']}
        &nbsp;<span class="score-badge">{r['Chunks']} chunks</span>
        &nbsp;<span class="tok-badge">{r['Est. Tokens']:,} tok</span>
        {'&nbsp;<span class="score-badge" style="background:rgba(34,197,94,0.15);color:#86efac;">✓ full_doc.md</span>' if has_md else ''}
    </div>
    <div class="rag-card-body">{r['Doc Types']}</div>
</div>""", unsafe_allow_html=True)

            # Manifest status
            manifest_path = Path("chroma_store/manifest.json")
            if manifest_path.exists():
                st.divider()
                st.markdown("#### 🗺️ ChromaDB Manifest (ingestion cache)")
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                for slug, file_hash in manifest.items():
                    cached = "✅ cached" if slug in [r["Slug"] for r in rows] else "⚠️ orphan"
                    st.markdown(f"- `{slug}` — `{file_hash[:12]}...` — {cached}")
            else:
                st.caption("No manifest found — pipeline hasn't run yet.")
