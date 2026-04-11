"""
RISC-V RAG Assistant — Streamlit App
=====================================
3-Agent Pipeline:
  1. Planner Agent    → architecture decision + module list + milestones
  2. ISA Expert Agent → RAG-grounded instruction encoding + control signals
  3. RTL Generator    → Verilog module code per spec

Plus:
  - RAG Q&A tab (ad-hoc retrieval)
  - Ingest URL tab   (calls chunk.py)
  - Corpus tab       (manifests + stats)

Run:
    streamlit run app.py
"""

import os
import sys
import re
import json
import time
import subprocess
import textwrap
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RISC-V RTL Forge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #060b18 0%, #0b1225 55%, #07101e 100%);
    min-height: 100vh;
}

[data-testid="stSidebar"] {
    background: rgba(10, 18, 38, 0.97);
    border-right: 1px solid rgba(99,179,237,0.12);
}

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
    padding: 8px 18px;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important;
}

.rag-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(99,179,237,0.14);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.rag-card:hover { border-color: rgba(99,179,237,0.32); }
.rag-card-title {
    font-size: 0.76rem;
    font-weight: 600;
    color: #63b3ed;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 5px;
}
.rag-card-body {
    font-size: 0.86rem;
    color: #cbd5e1;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.5;
}

/* Agent phase cards */
.agent-card {
    background: rgba(255,255,255,0.04);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.agent-card-planner  { border-left: 4px solid #f59e0b; border: 1px solid rgba(245,158,11,0.25); border-left: 4px solid #f59e0b; }
.agent-card-isa      { border-left: 4px solid #22d3ee; border: 1px solid rgba(34,211,238,0.25); border-left: 4px solid #22d3ee; }
.agent-card-rtl      { border-left: 4px solid #a78bfa; border: 1px solid rgba(167,139,250,0.25); border-left: 4px solid #a78bfa; }
.agent-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.agent-header-planner { color: #fbbf24; }
.agent-header-isa     { color: #67e8f9; }
.agent-header-rtl     { color: #c4b5fd; }
.phase-step {
    display: inline-block;
    width: 28px; height: 28px;
    border-radius: 50%;
    text-align: center;
    line-height: 28px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-right: 10px;
}
.step-done   { background: #22c55e; color: #052e16; }
.step-active { background: #3b82f6; color: white; }
.step-idle   { background: rgba(255,255,255,0.08); color: #64748b; }

.score-badge {
    display: inline-block;
    background: rgba(99,179,237,0.16);
    color: #90cdf4;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.73rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
}
.tok-badge {
    display: inline-block;
    background: rgba(139,92,246,0.16);
    color: #c4b5fd;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.73rem;
    font-family: 'JetBrains Mono', monospace;
}
.answer-box {
    background: rgba(12,20,38,0.9);
    border: 1px solid rgba(99,179,237,0.18);
    border-left: 4px solid #3b82f6;
    border-radius: 10px;
    padding: 18px 22px;
    color: #e2e8f0;
    font-size: 0.88rem;
    line-height: 1.7;
    white-space: pre-wrap;
}
.verilog-box {
    background: #0d1117;
    border: 1px solid rgba(167,139,250,0.25);
    border-left: 4px solid #a78bfa;
    border-radius: 10px;
    padding: 18px 22px;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.83rem;
    line-height: 1.6;
    white-space: pre;
    overflow-x: auto;
}
.budget-bar {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 8px 0 14px 0;
    border: 1px solid rgba(255,255,255,0.07);
}
.stat-pill {
    display: inline-block;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.22);
    color: #93c5fd;
    border-radius: 20px;
    padding: 3px 11px;
    font-size: 0.76rem;
    font-weight: 500;
    margin: 2px;
}
.milestone-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.milestone-num {
    background: rgba(59,130,246,0.18);
    color: #93c5fd;
    border-radius: 50%;
    width: 26px; height: 26px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.78rem; font-weight: 700;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)

# ── Pipeline loader (cached) ───────────────────────────────────────────────────
@st.cache_resource(show_spinner="⚙️ Starting RAG pipeline...")
def load_pipeline():
    project_root = str(Path(__file__).parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import rag_test as rt
    parent_store, children, new_children = rt.build_hierarchy()
    bm25, tokenize_fn = rt.build_bm25_children(children)
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(rt.EMBED_MODEL)
    collection = rt.build_chroma_children(new_children, embedder)
    return {"rt": rt, "parent_store": parent_store, "children": children,
            "bm25": bm25, "tokenize_fn": tokenize_fn,
            "embedder": embedder, "collection": collection}


PROJECT_ROOT = Path(__file__).parent


def save_pipeline_snapshot(label: str = "") -> Path:
    """Save current agent session state to a timestamped, incremental folder
    with full human-readable debug_report.md for every phase."""
    run_dir = PROJECT_ROOT / "pipeline_runs"
    run_dir.mkdir(exist_ok=True)
    max_id = 0
    for p in run_dir.glob("run_v*"):
        m = re.search(r'run_v(\d+)_', p.name)
        if m:
            max_id = max(max_id, int(m.group(1)))
    next_id = max_id + 1
    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    save_dir = run_dir / f"run_v{next_id:03d}_{ts}{suffix}"
    save_dir.mkdir()

    plan = st.session_state.get("agent_plan")
    isa  = st.session_state.get("agent_isa")
    rtl  = st.session_state.get("agent_rtl")

    # ── Raw JSONs ──────────────────────────────────────────────────────────────
    if plan:
        with open(save_dir / "planner_state.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
    if isa:
        with open(save_dir / "isa_expert_table.json", "w", encoding="utf-8") as f:
            json.dump(isa, f, indent=2)
    if rtl:
        rtl_dir = save_dir / "rtl"
        rtl_dir.mkdir()
        for mod_name, code in rtl.items():
            with open(rtl_dir / f"{mod_name}.v", "w", encoding="utf-8") as f:
                f.write(code)

    # ── Human-readable debug report ───────────────────────────────────────────
    lines = []
    lines.append(f"# Pipeline Debug Report")
    lines.append(f"**Saved:** {time.strftime('%Y-%m-%d %H:%M:%S')}  |  **Label:** `{label or 'snapshot'}`\n")
    lines.append("---\n")

    # PHASE 1 — PLANNER
    lines.append("## Phase 1 — Planner Agent\n")
    if plan:
        lines.append(f"**Architecture:** `{plan.get('architecture','—')}`")
        lines.append(f"**Reason:** {plan.get('reason','—')}\n")

        assumptions = plan.get("assumptions", [])
        if assumptions:
            lines.append("### Assumptions Made")
            for a in assumptions:
                lines.append(f"- {a}")
            lines.append("")

        missing = plan.get("missing_spec", [])
        if missing:
            lines.append("### ❓ Spec Gaps (clarify before RTL)")
            for m in missing:
                lines.append(f"- {m}")
            lines.append("")

        groups = plan.get("instruction_groups", [])
        if groups:
            lines.append("### Instruction Groups")
            lines.append("| Priority | Group | Instructions |")
            lines.append("|---|---|---|")
            for g in groups:
                lines.append(f"| P{g['priority']} | {g['group']} | {', '.join(g['instructions'])} |")
            lines.append("")

        modules = plan.get("modules", [])
        if modules:
            lines.append("### Module Build Order (DAG)")
            for i, mod in enumerate(modules):
                deps = mod.get("depends_on", [])
                dep_str = " ← " + ", ".join(deps) if deps else " (leaf)"
                lines.append(f"{i+1}. **{mod['name']}**{dep_str}")
            lines.append("")

        milestones = plan.get("milestones", [])
        if milestones:
            lines.append("### Milestones")
            lines.append("| Phase | Goal | Modules |")
            lines.append("|---|---|---|")
            for ms in milestones:
                lines.append(f"| {ms['phase']} | {ms['goal']} | {', '.join(ms.get('modules',[]))} |")
            lines.append("")

        lines.append(f"**tohost address:** `{plan.get('tohost_address','—')}`  |  "
                     f"**Reset PC:** `{plan.get('reset_pc','—')}`\n")
    else:
        lines.append("_Not run yet._\n")

    lines.append("---\n")

    # PHASE 2 — ISA EXPERT
    lines.append("## Phase 2 — ISA Expert Agent\n")
    if isa:
        typed = [r for r in isa if "instruction" in r]
        raw_fallbacks = [r for r in isa if "instruction" not in r]

        if typed:
            lines.append(f"**Total decoded instructions:** {len(typed)}\n")
            lines.append("### Control Signal Truth Table")
            hdr_cols = ["instruction","format","opcode","funct3","funct7",
                        "ALU_op","reg_write","mem_read","mem_write","branch","jump","alu_src","wb_src"]
            present = [c for c in hdr_cols if any(c in r for r in typed)]
            lines.append("| " + " | ".join(present) + " |")
            lines.append("| " + " | ".join(["---"]*len(present)) + " |")
            for r in typed:
                lines.append("| " + " | ".join(str(r.get(c,"—")) for c in present) + " |")
            lines.append("")

            # RAG contexts
            contexts = [(r.get("instruction",""), r["_context_used"])
                        for r in typed if "_context_used" in r]
            if contexts:
                lines.append("### RAG Contexts Used Per Group")
                for instr, ctx in contexts:
                    lines.append(f"\n#### Context for group containing `{instr}`")
                    lines.append("```")
                    lines.append(ctx[:2000])   # cap to keep file sane
                    lines.append("```")
                lines.append("")

        if raw_fallbacks:
            lines.append("### ⚠️ Raw LLM Fallbacks (JSON parse failed)")
            for fb in raw_fallbacks:
                lines.append(f"\n#### Group: {fb.get('group','?')}")
                lines.append("```")
                lines.append(fb.get("raw","")[:1000])
                lines.append("```")
            lines.append("")
    else:
        lines.append("_Not run yet._\n")

    lines.append("---\n")

    # PHASE 3 — RTL GENERATOR
    lines.append("## Phase 3 — RTL Generator Agent\n")
    if rtl:
        lines.append(f"**Generated modules:** {len(rtl)}\n")
        lines.append("| Module | File | Lines |")
        lines.append("|---|---|---|")
        for mod_name, code in rtl.items():
            lines.append(f"| {mod_name} | rtl/{mod_name}.v | {len(code.splitlines())} |")
        lines.append("")
    else:
        lines.append("_Not run yet._\n")

    lines.append("---\n")
    lines.append(f"_Full JSONs in same folder: `planner_state.json`, `isa_expert_table.json`, `rtl/*.v`_")

    with open(save_dir / "debug_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return save_dir



def run_retrieval(pipe, question, use_hyde, groq_client, top_k_parents=3, top_k_children=12):
    rt = pipe["rt"]
    embed_q = rt.expand_query_hyde(groq_client, question) if use_hyde else question
    dense  = rt.dense_retrieve_children(pipe["collection"], pipe["embedder"], embed_q, top_k_children)
    sparse = rt.sparse_retrieve_children(pipe["bm25"], pipe["tokenize_fn"], pipe["children"], question, rt.BM25_FETCH)
    fused  = rt.rrf_fuse_children(dense, sparse, k=rt.RRF_K, top_n=top_k_children)
    return rt.expand_to_parents(fused, pipe["parent_store"], top_n=top_k_parents)


def corpus_stats():
    data_dir = PROJECT_ROOT / "scraped data"
    rows = []
    for jp in sorted(data_dir.glob("*_chunks.json")):
        slug = jp.name.replace("_chunks.json", "")
        with open(jp, encoding="utf-8") as f:
            chunks = json.load(f)
        total_words = sum(len(c.get("document_text", "").split()) for c in chunks)
        doc_types = {}
        for c in chunks:
            dt = c.get("document_type", "unknown")
            doc_types[dt] = doc_types.get(dt, 0) + 1
        rows.append({"Slug": slug, "Chunks": len(chunks),
                     "Est. Tokens": int(total_words * 1.3),
                     "Doc Types": ", ".join(f"{k}:{v}" for k, v in sorted(doc_types.items()))})
    return rows


# ── Session state init ─────────────────────────────────────────────────────────
for _k, _v in [("agent_plan", None), ("agent_isa", None), ("agent_rtl", {})]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ═════════════════════════════════════════════════════════════════════════════
# AGENT PROMPTS
# ═════════════════════════════════════════════════════════════════════════════

PLANNER_SYSTEM = """You are the Planner Agent for an automated RISC-V RTL design flow.

PHASE CONSTRAINT — READ THIS FIRST:
This is the INITIAL golden reference generation pass. The architecture MUST be single-cycle.
Reason: A pipelined architecture requires Hazard Units and Forwarding Muxes that are NOT in the module
list. Generating a pipelined design without those will pass synthesis but fail every Read-After-Write
data hazard test in riscv-tests. Lock to single-cycle now; pipeline it in a later iteration.

IMPORTANT: Even if the user says "pipeline" or "5-stage", set architecture="single-cycle" and
explain this decision in the reason field.

MANDATORY OUTPUT — valid JSON only, no prose:
{
  "architecture": "single-cycle",
  "reason": "Initial RTL generation locked to single-cycle: a golden reference model isolates ISA correctness from pipeline hazard complexity. Pipelining is a later iteration.",
  "assumptions": [
    "Strictly single-cycle architecture. NO pipeline registers. NO IF/ID, ID/EX, EX/MEM stage latches.",
    "No hazard detection unit, no forwarding multiplexers — not needed in single-cycle.",
    "Simple synchronous memory interface with byte-enable for loads/stores.",
    "The load_store module is a purely combinational masking unit that acts as an interface to external memory. It MUST NOT have a clock (clk) input.",
    "x0 hardwired to zero. No compressed instructions, no FP, no privileged mode."
  ],
  "missing_spec": ["list of things the user should clarify, empty if none"],
  "instruction_groups": [
    {"group": "R-Type ALU",       "instructions": ["ADD","SUB","AND","OR","XOR","SLT","SLTU","SLL","SRL","SRA"], "priority": 1},
    {"group": "I-Type ALU",       "instructions": ["ADDI","ANDI","ORI","XORI","SLTI","SLTIU","SLLI","SRLI","SRAI"], "priority": 2},
    {"group": "U-Type",           "instructions": ["LUI","AUIPC"], "priority": 3},
    {"group": "Branches",         "instructions": ["BEQ","BNE","BLT","BGE","BLTU","BGEU"], "priority": 4},
    {"group": "Loads",            "instructions": ["LB","LH","LW","LBU","LHU"], "priority": 5},
    {"group": "Stores",           "instructions": ["SB","SH","SW"], "priority": 6},
    {"group": "Jumps",            "instructions": ["JAL","JALR"], "priority": 7}
  ],
  "modules": [
    {"name": "regfile",       "depends_on": []},
    {"name": "imm_gen",       "depends_on": []},
    {"name": "alu",           "depends_on": []},
    {"name": "branch_unit",   "depends_on": ["alu"]},
    {"name": "load_store",    "depends_on": []},
    {"name": "control",       "depends_on": []},
    {"name": "pc_next",       "depends_on": ["branch_unit"]},
    {"name": "top",           "depends_on": ["regfile","imm_gen","alu","branch_unit","load_store","control","pc_next"]}
  ],
  "milestones": [
    {"phase": 1, "goal": "regfile + ALU + R-type only: passes rv32ui-p-add",          "modules": ["regfile","alu","control","top"]},
    {"phase": 2, "goal": "I-type + U-type + Shifts: passes rv32ui-p-addi, lui, auipc", "modules": ["imm_gen"]},
    {"phase": 3, "goal": "Branches + Jumps: passes rv32ui-p-beq, jal, jalr",          "modules": ["branch_unit","pc_next"]},
    {"phase": 4, "goal": "Loads + Stores: passes rv32ui-p-lb through sw",             "modules": ["load_store"]}
  ],
  "tohost_address": "0x80001000",  // TESTBENCH USE ONLY — do not instantiate in top.v
  "reset_pc": "0x00000000"
}
"""

ISA_EXPERT_SYSTEM = """You are the ISA Expert Agent for a RISC-V RTL pipeline.

You will receive a list of instructions and relevant specification context from a RISC-V knowledge base.
Use the RAG context to validate encoding details; fill missing bit fields from your intrinsic RV32I knowledge.

For EACH instruction output one JSON record. Output a JSON array ONLY, no prose.

SCHEMA (every field is MANDATORY):
{
  "instruction": "ADD",        // mnemonic
  "format":      "R",          // R / I / S / B / U / J
  "opcode":      "0110011",    // 7-bit binary string
  "funct3":      "000",        // 3-bit binary string, "N/A" for U/J
  "funct7":      "0000000",    // 7-bit binary string, "N/A" for non R-type
  "ALU_op":      "ADD",        // ALU primitive: ADD SUB AND OR XOR SLT SLTU SLL SRL SRA
                               //   NEVER PASS_B — use result_src="imm" to bypass ALU instead
  "alu_src_a":   "rs1",        // First ALU operand mux: "rs1" | "pc" | "zero"
  "alu_src_b":   "rs2",        // Second ALU operand mux: "rs2" | "imm"
  "result_src":  "alu",        // Writeback DATA source mux: "alu" | "mem" | "pc+4" | "imm"
                               //   LUI → "imm" (bypasses ALU), AUIPC → "alu", Loads → "mem"
  "reg_write":   1,            // 1 = writes to rd, 0 = does not
  "mem_read":    0,            // 1 = load instruction
  "mem_write":   0,            // 1 = store instruction
  "mem_size":    "N/A",        // data width: "8" | "16" | "32" | "N/A"
  "mem_extend":  "N/A",        // "signed" | "unsigned" | "N/A"
  "branch":      0,            // 1 = conditional branch
  "branch_type": "N/A",        // "eq"|"ne"|"lt"|"ge"|"ltu"|"geu"|"N/A"  — used by branch_unit comparator directly
  "jump":        0,            // 1 = unconditional jump (JAL/JALR)
  "jump_type":   "N/A",        // "jal" | "jalr" | "N/A"  — JALR requires pc_next to clear LSB: target &= ~1
  "imm_type":    "N/A",        // "I" | "S" | "B" | "U" | "J" | "N/A"
  "notes":       ""
}

FIVE CANONICAL EXAMPLES (study before generating):

Example 1 — ADD (R-type, both regs into ALU):
{
  "instruction": "ADD", "format": "R", "opcode": "0110011", "funct3": "000", "funct7": "0000000",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "rs2", "result_src": "alu",
  "reg_write": 1, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 0, "branch_type": "N/A", "jump": 0, "jump_type": "N/A", "imm_type": "N/A", "notes": ""
}

Example 2 — LUI (U-type — imm bypasses ALU entirely via result_src, ALU is IDLE):
{
  "instruction": "LUI", "format": "U", "opcode": "0110111", "funct3": "N/A", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "zero", "alu_src_b": "imm", "result_src": "imm",
  "reg_write": 1, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 0, "branch_type": "N/A", "jump": 0, "jump_type": "N/A", "imm_type": "U",
  "notes": "rd = imm<<12; result_src=imm bypasses ALU — the mux routes imm directly to regfile"
}

Example 3 — BEQ (B-type — branch_type drives dedicated comparator, NOT ALU subtraction):
{
  "instruction": "BEQ", "format": "B", "opcode": "1100011", "funct3": "000", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "rs2", "result_src": "N/A",
  "reg_write": 0, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 1, "branch_type": "eq", "jump": 0, "jump_type": "N/A", "imm_type": "B",
  "notes": "branch_unit receives branch_type=eq and compares rs1==rs2 directly"
}

Example 4 — JALR (I-type — jump_type=jalr triggers LSB clear on target address):
{
  "instruction": "JALR", "format": "I", "opcode": "1100111", "funct3": "000", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "imm", "result_src": "pc+4",
  "reg_write": 1, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 0, "branch_type": "N/A", "jump": 1, "jump_type": "jalr", "imm_type": "I",
  "notes": "pc_next MUST clear bit[0]: target = (rs1+imm) & ~32'h1. rd = pc+4"
}

Example 5 — LB (I-type load — result_src=mem, mem_size and mem_extend critical):
{
  "instruction": "LB", "format": "I", "opcode": "0000011", "funct3": "000", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "imm", "result_src": "mem",
  "reg_write": 1, "mem_read": 1, "mem_write": 0, "mem_size": "8", "mem_extend": "signed",
  "branch": 0, "branch_type": "N/A", "jump": 0, "jump_type": "N/A", "imm_type": "I",
  "notes": "rd = sign_ext(mem[rs1+imm][7:0])"
}

ADDITIONAL RULES:
1. LUI: result_src="imm" — the final mux routes the shifted immediate DIRECTLY to regfile, bypassing ALU.
2. AUIPC: ALU_op=ADD, alu_src_a=pc, result_src="alu" (ALU genuinely computes PC+imm).
3. Branches: ALU_op=ADD (unused), branch_type="eq"|"ne"|"lt"|"ge"|"ltu"|"geu". branch_unit uses branch_type directly.
4. JALR: jump_type="jalr" — pc_next module MUST apply & ~1 to the computed target.
5. JAL: jump_type="jal" — no LSB clear needed.
6. mem_size: LB/SB=2'b00, LH/SH=2'b01, LW/SW=2'b10 (matches funct3[1:0]).
   mem_extend comes from funct3[2]: 0=signed (LB/LH), 1=unsigned (LBU/LHU). Stores do not use mem_extend.
   CRITICAL: mem_extend=0 → sign-extend; mem_extend=1 → zero-extend. This matches the RISC-V funct3 encoding.
7. All R-type instructions share opcode 0110011 — correct; funct3/funct7 differentiate them.
"""



RTL_GENERATOR_SYSTEM = """You are the RTL Generator Agent for a RISC-V single-cycle processor.

ARCHITECTURE MANDATE — SINGLE-CYCLE ONLY:
Every instruction completes in exactly one clock cycle. DO NOT generate:
  ✗ Pipeline stage registers (IF_ID, ID_EX, EX_MEM, MEM_WB)
  ✗ Hazard detection units, forwarding muxes, stall logic, flush signals
  ✗ Internal memory arrays (SRAM/BRAM). The CPU interfaces with external memory.
Violating this will fail rv32ui-p-add on the very first RAW hazard.

You receive:
- Module name + its DAG dependencies.
- The full ISA control signal truth table from ISA Expert — ground truth for all encodings.
- Architecture-level constants (reset_pc only — tohost belongs in the testbench, NOT in top.v).

PER-MODULE PORT CONTRACTS (use EXACTLY these port names for interconnect):
  regfile    : clk, we, rs1[4:0], rs2[4:0], rd[4:0], rd_data[31:0] 
               → rd1[31:0], rd2[31:0]   (x0 hardwired: write guarded by `if (rd != 0)`)
  imm_gen    : instr[31:0], imm_type[2:0] → imm[31:0]
  alu        : a[31:0], b[31:0], alu_op[3:0] → result[31:0], zero
  branch_unit: branch_type[2:0], rs1[31:0], rs2[31:0] → taken
               CRITICAL: branch_type IS the raw RISC-V funct3 field. Use the EXACT binary codes:
                 3'b000=BEQ, 3'b001=BNE, 3'b100=BLT, 3'b101=BGE, 3'b110=BLTU, 3'b111=BGEU
               DO NOT use sequential integers (0,1,2,3,4,5) — that is an ISA violation.
               (DO NOT use ALU output — this is a dedicated parallel comparator)
  load_store : mem_read, mem_write, mem_size[1:0], mem_extend, addr[31:0], wdata[31:0], mem_rdata[31:0] 
               → rdata[31:0], mem_addr[31:0], mem_wdata[31:0], mem_wstrb[3:0]
               CRITICAL mem_extend polarity: mem_extend comes from funct3[2].
                 funct3[2]=0 (LB/LH) → mem_extend=0 → SIGN extend.
                 funct3[2]=1 (LBU/LHU) → mem_extend=1 → ZERO extend.
               So: `if (!mem_extend)` triggers sign-extension; `else` triggers zero-extension.
               CRITICAL mem_addr: The external memory bus is WORD-addressed with byte strobes.
                 Always output word-aligned address: `mem_addr = {addr[31:2], 2'b00}`
                 The byte_offset (addr[1:0]) is encoded in mem_wstrb lane selection only.
               CRITICAL: This module is purely combinational mask generation. DO NOT declare or instantiate with a clk port.
  control    : opcode[6:0], funct3[2:0], funct7b5 → 
               alu_src_a[1:0], alu_src_b, result_src[1:0], 
               reg_write, mem_read, mem_write, mem_size[1:0], mem_extend, 
               branch, branch_type[2:0], jump, jump_type, alu_op[3:0], imm_type[2:0]
  pc_next    : pc[31:0], imm[31:0], rs1[31:0], taken, jump, jump_type → pc_next[31:0]
               CRITICAL: if jump_type=1 (JALR), apply `pc_next = (rs1+imm) & ~32'h1` (clear LSB)
  top        : clk, resetn, imem_rdata[31:0], dmem_rdata[31:0] 
               → imem_addr[31:0], dmem_addr[31:0], dmem_wdata[31:0], dmem_wstrb[3:0], dmem_read, dmem_write
               (instantiates all sub-modules; pure CPU core, NO tohost logic)

MULTIPLEXER CONTRACTS (Enforce these mappings in top.v and control.v):
  alu_src_a  = 2'b00: rs1  |  2'b01: pc  |  2'b10: zero
  alu_src_b  = 1'b0: rs2   |  1'b1: imm
  result_src = 2'b00: alu  |  2'b01: mem |  2'b10: pc+4 | 2'b11: imm (LUI bypass)

RULES:
- STRICT LINTER RULE: All assignments MUST have explicitly matching bit widths. Do NOT rely on implicit zero-extension or truncation. If assigning a 1-bit or 8-bit value to a 32-bit net, you must explicitly pad it (e.g., use `32'b1` instead of `1'b1`, or `{24'b0, val[7:0]}`).
- Use `always_comb` for combinational logic. Every `case` MUST have a `default` clause.
- Use `always_ff @(posedge clk or negedge resetn)` for sequential elements (regfile write, PC).
- x0 write guard: `if (we && rd != 5'd0)` in regfile.
- control.v: derive all outputs from the ISA truth table using opcode/funct3/funct7b5.
- Add a one-line comment on every non-obvious assignment.
- Do NOT generate a testbench or any tohost/HTIF logic. Module definition only.
Output ONLY the Verilog code inside a ```verilog block, no prose before or after.
"""


def llm_call(groq_client, system: str, user: str, limiter, max_tokens: int = 4096, stream=False) -> str:
    """Single LLM call with rate limiting. Returns full string."""
    total_est = len(system) // 4 + len(user) // 4 + max_tokens
    limiter.wait(total_est)
    if stream:
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            temperature=0.1,
            max_tokens=max_tokens,
            stream=True,
        )
        result = ""
        for chunk in completion:
            result += chunk.choices[0].delta.content or ""
        limiter.record(total_est)
        return result
    else:
        try:
            resp = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": user}],
                temperature=0.1,
                max_tokens=max_tokens,
                stream=False,
            )
            limiter.record(total_est)
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"// API ERROR: {str(e)}"


# ── RTL-specific helpers ───────────────────────────────────────────────────────

def _is_complete_verilog(code: str) -> bool:
    """Return True if the Verilog output ends with an endmodule (not truncated)."""
    # Strip markdown fences and whitespace
    clean = re.sub(r'```[\w]*', '', code).strip()
    return 'endmodule' in clean


# Forbidden RTL patterns — each entry is (regex_pattern, human_description)
# These are ARCHITECTURE violations, not syntax bugs.
_RTL_FORBIDDEN = [
    (
        r'\blogic\s+\[\d+:\d+\]\s+\w+\s*\[\s*\d+\s*:\s*\d+\s*\]',
        "Internal memory array declared inside the module (e.g. `logic [31:0] mem [0:1023]`). "
        "Memory is EXTERNAL to the CPU. The load_store module must expose a flat memory interface: "
        "output mem_addr[31:0], output mem_wdata[31:0], output mem_wstrb[3:0], input mem_rdata[31:0]. "
        "Delete the internal array and rewire to these ports."
    ),
    (
        r'\breg\s+\[\d+:\d+\]\s+\w+\s*\[',
        "Internal memory array using `reg` type found. Memory must be external. "
        "Expose flat memory bus ports instead."
    ),
    (
        r'\b(IF_ID|ID_EX|EX_MEM|MEM_WB)\b',
        "Pipeline stage register found. This is a SINGLE-CYCLE architecture. "
        "Pipeline registers are forbidden. Remove all stage latches."
    ),
    (
        r'\bhazard\b|\bforward\b|\bstall\b|\bflush\b',
        "Hazard/forward/stall/flush logic found. This is a SINGLE-CYCLE architecture. "
        "These constructs are forbidden."
    ),
]


def generate_verilog_with_continuation(
    groq_client, system: str, user_msg: str, limiter,
    max_tokens: int = 4096, max_rounds: int = 3
) -> tuple[str, list[str]]:
    """
    Generate a Verilog module with automatic truncation recovery.

    Returns:
        (final_code, log_messages)  — log_messages is a list of human-readable
        status strings suitable for display in the Streamlit UI.
    """
    logs = []
    code = llm_call(groq_client, system, user_msg, limiter, max_tokens=max_tokens)
    logs.append(f"Round 1: generated {len(code)} chars.")

    for rnd in range(2, max_rounds + 2):
        if _is_complete_verilog(code):
            logs.append("✅ Module complete (endmodule found).")
            break
        logs.append(f"⚠️ Truncation detected (no endmodule). Firing continuation round {rnd}...")
        continuation_user = (
            f"The previous generation was cut off. Here is what was generated so far:\n\n"
            f"```verilog\n{code[-1500:]}\n```\n\n"
            f"Continue EXACTLY from where it was cut off. "
            f"Do NOT restart the module from the beginning. "
            f"Output only the missing Verilog lines up to and including `endmodule`."
        )
        extra = llm_call(groq_client, system, continuation_user, limiter, max_tokens=max_tokens)
        code = code + "\n" + extra
        logs.append(f"Round {rnd}: appended {len(extra)} more chars.")
        if rnd == max_rounds + 1:
            logs.append("🔴 Max continuation rounds reached. Module may still be incomplete.")

    return code, logs


def validate_and_repair_verilog(
    groq_client, system: str, original_user_msg: str,
    code: str, limiter, max_tokens: int = 4096
) -> tuple[str, list[str]]:
    """
    Scan generated Verilog for forbidden architectural patterns.
    If any are found, fire an automatic LLM repair call describing the exact violation.

    Returns:
        (final_code, log_messages)
    """
    logs = []
    violations = []
    for pattern, description in _RTL_FORBIDDEN:
        if re.search(pattern, code, re.IGNORECASE):
            violations.append(description)

    if not violations:
        logs.append("✅ No architectural violations detected.")
        return code, logs

    violation_text = "\n".join(f"- {v}" for v in violations)
    logs.append(f"🔴 {len(violations)} violation(s) found. Firing auto-repair call...")
    logs.append(violation_text)

    repair_user = (
        f"{original_user_msg}\n\n"
        f"CRITICAL: Your previous output contained architectural violations that must be fixed:\n"
        f"{violation_text}\n\n"
        f"Here is the violating code:\n```verilog\n{code}\n```\n\n"
        f"Rewrite the COMPLETE module fixing EVERY violation listed above. "
        f"Output ONLY the corrected Verilog module, no prose."
    )
    repaired = llm_call(groq_client, system, repair_user, limiter, max_tokens=max_tokens)
    if not repaired.strip() or repaired.startswith("// API ERROR"):
        logs.append(f"🔴 Repair call failed or returned empty string. Keeping original violating code.")
        return code, logs

    logs.append(f"✅ Repair call returned {len(repaired)} chars.")
    return repaired, logs



def strip_unused_signals(code: str) -> tuple[str, list[str]]:
    """Remove unused logic/wire/reg declarations from generated Verilog.

    Strategy: a declared net is 'unused' if the only line containing its
    identifier is the declaration itself.  We check whole-word occurrences
    on every non-comment line, so false-positives (sub-strings) are avoided.
    Returns (cleaned_code, list_of_removed_names).
    """
    lines = code.split('\n')
    # Match:  logic [w] name;  /  logic name;  /  wire [...] name;  /  reg [...] name;
    DECL_RE = re.compile(
        r'^\s*(?:logic|wire|reg)(?:\s+(?:signed|unsigned))?'
        r'(?:\s*\[[^\]]*\])?\s+(\w+)\s*;'
    )

    # Strip // comments for occurrence counting
    def no_comment(line: str) -> str:
        return re.sub(r'//.*', '', line)

    declared: dict[str, int] = {}   # signal_name -> line index
    for i, line in enumerate(lines):
        m = DECL_RE.match(line)
        if m:
            declared[m.group(1)] = i

    removed: list[str] = []
    unused_line_idxs: set[int] = set()

    for sig, decl_idx in declared.items():
        pattern = re.compile(r'\b' + re.escape(sig) + r'\b')
        refs = [
            i for i, line in enumerate(lines)
            if pattern.search(no_comment(line))
        ]
        if refs == [decl_idx]:       # only appears on its own declaration line
            unused_line_idxs.add(decl_idx)
            removed.append(sig)

    cleaned = '\n'.join(line for i, line in enumerate(lines)
                        if i not in unused_line_idxs)
    return cleaned, removed


def parse_json_safe(text: str):
    """Extract and parse the first JSON object or array from text."""
    text = text.strip()
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # find first { or [
    for start_ch, end_ch in [('{', '}'), ('[', ']')]:
        si = text.find(start_ch)
        ei = text.rfind(end_ch)
        if si != -1 and ei != -1 and ei > si:
            try:
                return json.loads(text[si:ei+1])
            except Exception:
                pass
    return None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ RISC-V RTL Forge")
    st.markdown("*RAG-Grounded 3-Agent Pipeline*")
    st.divider()

    api_key = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Overrides GROQ_API_KEY from .env",
    )

    st.divider()
    st.markdown("### RAG Settings")
    top_k_parents  = st.slider("Top-K Parents (context chunks)", 1, 5, 3)
    top_k_children = st.slider("Top-K Children (retrieval)", 6, 20, 12)
    use_hyde        = st.toggle("Enable HyDE (experimental — OFF recommended)", value=False)

    st.divider()
    st.markdown("### Model")
    st.code("openai/gpt-oss-20b", language=None)
    st.caption("8K TPM · 30 RPM · Groq hosted")

    st.divider()
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 Pipeline", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()
    with col_r2:
        if st.button("🗑️ Agents", use_container_width=True):
            st.session_state.agent_plan = None
            st.session_state.agent_isa  = None
            st.session_state.agent_rtl  = {}
            st.rerun()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:24px 0 14px 0;">
  <h1 style="font-size:2.1rem;font-weight:700;color:#e2e8f0;margin:0;letter-spacing:-0.03em;">
    ⚡ RISC-V RTL Forge
  </h1>
  <p style="color:#475569;margin:5px 0 0 0;font-size:0.92rem;">
    RAG Knowledge Base · 3-Agent Design Pipeline · Corpus Management
  </p>
</div>
""", unsafe_allow_html=True)

tab_agent, tab_qa, tab_ingest, tab_corpus = st.tabs([
    "🤖 Agent Pipeline", "🔍 RAG Q&A", "📥 Ingest URL", "📚 Corpus"
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0 — AGENT PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_agent:
    # ── Phase status bar ──────────────────────────────────────────────────────
    plan_done = st.session_state.agent_plan is not None
    isa_done  = st.session_state.agent_isa  is not None
    rtl_done  = bool(st.session_state.agent_rtl)

    def step_cls(done, active):
        if done:   return "step-done"
        if active: return "step-active"
        return "step-idle"

    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:14px 0 22px 0;">
  <span class="phase-step {step_cls(plan_done, True)}">1</span>
  <span style="color:{'#fbbf24' if not plan_done else '#22c55e'};font-weight:600;">Planner</span>
  <span style="color:#334155;padding:0 6px;">──────</span>
  <span class="phase-step {step_cls(isa_done, plan_done)}">2</span>
  <span style="color:{'#67e8f9' if plan_done and not isa_done else ('#22c55e' if isa_done else '#475569')};font-weight:600;">ISA Expert</span>
  <span style="color:#334155;padding:0 6px;">──────</span>
  <span class="phase-step {step_cls(rtl_done, isa_done)}">3</span>
  <span style="color:{'#c4b5fd' if isa_done and not rtl_done else ('#22c55e' if rtl_done else '#475569')};font-weight:600;">RTL Generator</span>
</div>
""", unsafe_allow_html=True)

    # ── Restore from Disk (shown when session state is empty after a reload) ───
    session_empty = (st.session_state.agent_plan is None and
                     st.session_state.agent_isa  is None and
                     not st.session_state.agent_rtl)

    _run_dirs = sorted([d for d in (PROJECT_ROOT / "pipeline_runs").glob("run_v*")
                        if (d / "rtl").exists() or (d / "plan.json").exists()])
    if _run_dirs:
        _last_run = _run_dirs[-1]
        if session_empty:
            st.info(f"💾 **Session cleared.** Last saved pipeline: `{_last_run.name}` — restore it without hitting the API:")
        with st.expander("🔄 Restore Last Pipeline from Disk", expanded=session_empty):
            st.caption(f"Source: `{_last_run}`")
            _cr1, _cr2, _cr3 = st.columns(3)
            with _cr1:
                if st.button("📋 Restore Plan", use_container_width=True, key="restore_plan"):
                    import json as _j
                    _f = _last_run / "plan.json"
                    if _f.exists():
                        st.session_state.agent_plan = _j.loads(_f.read_text()); st.rerun()
                    else: st.error("No plan.json found.")
            with _cr2:
                if st.button("📊 Restore ISA", use_container_width=True, key="restore_isa"):
                    import json as _j
                    _f = _last_run / "isa.json"
                    if _f.exists():
                        st.session_state.agent_isa = _j.loads(_f.read_text()); st.rerun()
                    else: st.error("No isa.json found.")
            with _cr3:
                if st.button("⚙️ Restore RTL", use_container_width=True, key="restore_rtl"):
                    _d = _last_run / "rtl"
                    if _d.exists():
                        st.session_state.agent_rtl = {v.stem: v.read_text(encoding="utf-8") for v in _d.glob("*.v")}
                        st.success(f"Restored {len(st.session_state.agent_rtl)} modules!"); st.rerun()
                    else: st.error("No rtl/ folder found.")
            st.markdown("---")
            if st.button("⚡ Restore ALL (Plan + ISA + RTL) — Zero tokens!", use_container_width=True, type="primary", key="restore_all"):
                import json as _j
                if (_last_run / "plan.json").exists():
                    st.session_state.agent_plan = _j.loads((_last_run / "plan.json").read_text())
                if (_last_run / "isa.json").exists():
                    st.session_state.agent_isa  = _j.loads((_last_run / "isa.json").read_text())
                _rtl_d = _last_run / "rtl"
                if _rtl_d.exists():
                    st.session_state.agent_rtl = {v.stem: v.read_text(encoding="utf-8") for v in _rtl_d.glob("*.v")}
                st.success(f"✅ Full pipeline restored from `{_last_run.name}`. Zero API tokens used!"); st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1 — PLANNER
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="agent-card agent-card-planner">', unsafe_allow_html=True)
    st.markdown('<div class="agent-header agent-header-planner">⬡ Phase 1 — Planner Agent</div>', unsafe_allow_html=True)
    st.markdown("**Input:** Natural language design request. **Output:** Architecture plan, module list, instruction coverage, milestones.", unsafe_allow_html=False)

    user_request = st.text_area(
        "Design Request",
        value="Build a single-cycle RV32I processor core that passes the riscv-tests suite.",
        height=80,
        key="planner_input",
        label_visibility="collapsed",
    )

    if st.button("▶ Run Planner", type="primary", key="run_planner"):
        if not api_key:
            st.error("❌ Add Groq API Key in sidebar.")
        else:
            from groq import Groq
            groq_client = Groq(api_key=api_key)
            import rag_test as rt
            limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)

            with st.spinner("🧠 Planner thinking..."):
                raw = llm_call(groq_client, PLANNER_SYSTEM, user_request, limiter, max_tokens=2048)

            plan = parse_json_safe(raw)
            if plan:
                st.session_state.agent_plan = plan
                st.session_state.agent_isa  = None   # reset downstream
                st.session_state.agent_rtl  = {}
                saved = save_pipeline_snapshot("planner")
                st.success(f"✅ Plan generated — auto-saved to `{saved.name}`")
            else:
                st.error("❌ Could not parse JSON plan. Raw output:")
                st.code(raw)

    if st.session_state.agent_plan:
        plan = st.session_state.agent_plan
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Architecture", plan.get("architecture", "—").title())
        pc2.metric("Modules", len(plan.get("modules", [])))
        pc3.metric("Milestones", len(plan.get("milestones", [])))

        col_l, col_r = st.columns(2)
        with col_l:
            with st.expander("📦 Module Build Order", expanded=True):
                mods = plan.get("modules", [])
                for i, m in enumerate(mods):
                    deps = m.get("depends_on", [])
                    dep_str = f" ← {', '.join(deps)}" if deps else " (leaf)"
                    st.markdown(f"`{i+1}.` **{m['name']}**{dep_str}")

            with st.expander("📋 Instruction Groups"):
                for grp in plan.get("instruction_groups", []):
                    st.markdown(f"**P{grp['priority']} · {grp['group']}:** {', '.join(grp['instructions'])}")

        with col_r:
            with st.expander("🚩 Milestones", expanded=True):
                for ms in plan.get("milestones", []):
                    st.markdown(f"""
<div class="milestone-row">
  <div class="milestone-num">{ms['phase']}</div>
  <div><b>{ms['goal']}</b><br>
  <span style="font-size:0.78rem;color:#64748b;">{', '.join(ms.get('modules',[]))}</span></div>
</div>""", unsafe_allow_html=True)

            if plan.get("assumptions"):
                with st.expander("⚠️ Assumptions made"):
                    for a in plan["assumptions"]:
                        st.markdown(f"- {a}")
            if plan.get("missing_spec"):
                with st.expander("❓ Spec gaps — clarify before RTL"):
                    for m in plan["missing_spec"]:
                        st.markdown(f"- {m}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2 — ISA EXPERT
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="agent-card agent-card-isa">', unsafe_allow_html=True)
    st.markdown('<div class="agent-header agent-header-isa">⬡ Phase 2 — ISA Expert Agent (RAG-Grounded)</div>', unsafe_allow_html=True)
    st.markdown("Retrieves precise encoding + control signal data from the RISC-V corpus for every instruction in the plan.", unsafe_allow_html=False)

    plan_done = st.session_state.agent_plan is not None  # Re-evaluate to catch Phase 1 completion mid-run

    if not plan_done:
        st.info("▲ Run the Planner first to unlock this phase.")
    else:
        # Pre-load the RAG pipeline as soon as Phase 1 is done so Phase 2 button is instant
        with st.spinner("⚙️ Warming up RAG pipeline..."):
            pipe = load_pipeline()
        st.caption("✅ RAG pipeline ready. Click Run ISA Expert to decode all instruction groups.")

        if st.button("▶ Run ISA Expert", type="primary", key="run_isa"):
            if not api_key:
                st.error("❌ Add Groq API Key in sidebar.")
            else:
                from groq import Groq
                groq_client = Groq(api_key=api_key)
                import rag_test as rt
                limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)

                plan = st.session_state.agent_plan
                all_records = []
                isa_progress = st.progress(0, text="Retrieving from corpus...")
                per_group = plan.get("instruction_groups", [])

                for gi, grp in enumerate(per_group):
                    query = (f"Instruction encoding, opcode, funct3, funct7, and control signals "
                             f"for {grp['group']}: {', '.join(grp['instructions'])}")

                    isa_progress.progress((gi) / len(per_group),
                                         text=f"RAG → {grp['group']} ({gi+1}/{len(per_group)})")

                    parents = run_retrieval(pipe, query, use_hyde, groq_client,
                                            top_k_parents=top_k_parents,
                                            top_k_children=top_k_children)

                    context = "\n\n---\n\n".join(
                        f"[{p['section_title']}]\n{p['full_text'][:1200]}" for p in parents
                    )
                    user_msg = (f"Instructions to decode: {', '.join(grp['instructions'])}\n\n"
                                f"Context from RISC-V corpus:\n{context}")

                    raw = llm_call(groq_client, ISA_EXPERT_SYSTEM, user_msg, limiter, max_tokens=2000)
                    records = parse_json_safe(raw)
                    if isinstance(records, list):
                        if len(records) > 0:
                            records[0]["_context_used"] = context
                        all_records.extend(records)
                    else:
                        all_records.append({"group": grp["group"], "raw": raw, "_context_used": context})

                isa_progress.progress(1.0, text="✅ ISA analysis complete.")
                st.session_state.agent_isa = all_records
                st.session_state.agent_rtl = {}
                saved = save_pipeline_snapshot("isa")
                st.success(f"✅ Decoded {len(all_records)} instruction records — auto-saved to `{saved.name}`")

        if st.session_state.agent_isa:
            records = st.session_state.agent_isa
            typed = [r for r in records if "instruction" in r]
            raw_fallbacks = [r for r in records if "instruction" not in r]

            if typed:
                st.markdown(f"#### 📊 Control Signal Truth Table ({len(typed)} instructions)")
                # Build display table and exclude the internal _context_used key
                import pandas as pd
                cols_show = ["instruction", "format", "opcode", "funct3", "funct7",
                             "ALU_op", "alu_src_a", "alu_src_b",
                             "reg_write", "mem_read", "mem_write", "mem_size", "mem_extend",
                             "branch", "jump", "wb_src", "imm_type"]
                safe_cols = [c for c in cols_show if any(c in r for r in typed)]
                df = pd.DataFrame([{c: r.get(c, "—") for c in safe_cols} for r in typed])
                st.dataframe(df, use_container_width=True, height=350)
                
                with st.expander("🔍 View RAG Contexts fed to ISA Expert"):
                    st.markdown("For each instruction group, the RAG pipeline retrieved the following specific chunks from your corpus:")
                    for r in records:
                        if "_context_used" in r:
                            st.markdown(f"**Group containing `{r.get('instruction', r.get('group', ''))}`**")
                            st.code(r["_context_used"], language="markdown")

            for fb in raw_fallbacks:
                with st.expander(f"⚠️ Raw output for {fb.get('group', 'unknown')}"):
                    st.code(fb.get("raw", ""))

    st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3 — RTL GENERATOR
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="agent-card agent-card-rtl">', unsafe_allow_html=True)
    st.markdown('<div class="agent-header agent-header-rtl">⬡ Phase 3 — RTL Generator Agent</div>', unsafe_allow_html=True)
    st.markdown("Generates synthesizable Verilog for each module in the build order, grounded by the ISA truth table.", unsafe_allow_html=False)

    isa_done = st.session_state.agent_isa is not None  # Re-evaluate to catch Phase 2 completion mid-run

    if not isa_done:
        st.info("▲ Run the ISA Expert first to unlock this phase.")
    else:
        plan    = st.session_state.agent_plan
        modules = plan.get("modules", [])
        mod_names = [m["name"] for m in modules]

        selected_mods = st.multiselect(
            "Select modules to generate (tip: start with leaf nodes first)",
            options=mod_names,
            default=mod_names[:3],
            key="rtl_mod_select",
        )

        if st.button("▶ Generate RTL", type="primary", key="run_rtl", disabled=not selected_mods):
            if not api_key:
                st.error("❌ Add Groq API Key in sidebar.")
            else:
                from groq import Groq
                groq_client = Groq(api_key=api_key)
                import rag_test as rt
                limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)

                isa_table_str = json.dumps(
                    [r for r in st.session_state.agent_isa if "instruction" in r],
                    indent=2
                )[:4000]   # cap so we don't blow the context

                arch = plan.get("architecture", "single-cycle")
                all_rtl = dict(st.session_state.agent_rtl)   # preserve any already generated

                rtl_progress = st.progress(0, text="Generating RTL...")

                for mi, mod_name in enumerate(selected_mods):
                    rtl_progress.progress(mi / len(selected_mods),
                                          text=f"Generating {mod_name}.v ({mi+1}/{len(selected_mods)})...")

                    mod_spec = next((m for m in modules if m["name"] == mod_name), {})
                    user_msg = textwrap.dedent(f"""
                    Architecture: {arch}
                    Reset PC: {plan.get('reset_pc', '0x00000000')}

                    Module to generate: {mod_name}
                    Depends on: {', '.join(mod_spec.get('depends_on', [])) or 'None (leaf)'}

                    ISA Control Signal Truth Table (use ONLY this for encoding):
                    {isa_table_str}

                    Generate the complete synthesizable Verilog module for `{mod_name}`.
                    """).strip()

                    # Step 1: Generate with automatic truncation continuation
                    verilog, cont_logs = generate_verilog_with_continuation(
                        groq_client, RTL_GENERATOR_SYSTEM, user_msg, limiter, max_tokens=4096
                    )
                    # Step 2: Validate and auto-repair architectural violations
                    verilog, val_logs = validate_and_repair_verilog(
                        groq_client, RTL_GENERATOR_SYSTEM, user_msg, verilog, limiter, max_tokens=4096
                    )
                    all_rtl[mod_name] = verilog
                    # Surface the engine logs so the user can see what happened
                    for msg in cont_logs + val_logs:
                        if msg.startswith("✅"):
                            st.caption(f"`{mod_name}` · {msg}")
                        elif msg.startswith(("⚠️", "🔴")):
                            st.warning(f"`{mod_name}` · {msg}")
                        else:
                            st.caption(f"`{mod_name}` · {msg}")

                rtl_progress.progress(1.0, text="✅ RTL generation complete.")
                st.session_state.agent_rtl = all_rtl
                saved = save_pipeline_snapshot("rtl")
                st.success(f"✅ Generated {len(selected_mods)} module(s). Auto-saved to `{saved.name}`")

        if st.session_state.agent_rtl:
            rtl = st.session_state.agent_rtl
            st.markdown(f"#### 📁 Generated Verilog ({len(rtl)} modules)")

            # Download all as a zip
            import io, zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zobj:
                for fname, code in rtl.items():
                    zobj.writestr(f"{fname}.v", code)
            zip_buf.seek(0)
            col_dl, col_sync, col_clean = st.columns([1, 1, 1])
            with col_dl:
                st.download_button(
                    "💾 Download All (.zip)",
                    data=zip_buf,
                    file_name="riscv_rtl.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            with col_sync:
                if st.button("🔄 Sync UI with Disk", use_container_width=True):
                    # Find latest run with an rtl folder
                    run_dirs = sorted([d for d in (PROJECT_ROOT / "pipeline_runs").glob("run_v*") if (d / "rtl").exists()])
                    if run_dirs:
                        latest_rtl = run_dirs[-1] / "rtl"
                        for v_file in latest_rtl.glob("*.v"):
                            with open(v_file, "r", encoding="utf-8") as f:
                                st.session_state.agent_rtl[v_file.stem] = f.read()
                        st.success(f"UI synced with `{latest_rtl.parent.name}`!")
                        st.rerun()
                    else:
                        st.error("No valid rtl folders found on disk.")
            
            with col_clean:
                if st.button("🧹 Clean Verilog (Lint Ready)", use_container_width=True):
                    cleaned_params = {}
                    for mod_name, code in st.session_state.agent_rtl.items():
                        clean_code = re.sub(r'^```[a-zA-Z]*\n', '', code, flags=re.MULTILINE)
                        clean_code = re.sub(r'\n```$', '', clean_code)
                        clean_code = clean_code.strip()
                        # Remove unused signal declarations before linting
                        clean_code, removed = strip_unused_signals(clean_code)
                        if removed:
                            clean_code = f"// [Auto-cleaned] Removed unused: {', '.join(removed)}\n" + clean_code
                        cleaned_params[mod_name] = clean_code
                    st.session_state.agent_rtl = cleaned_params
                    saved_clean = save_pipeline_snapshot("cleaned")
                    st.success(f"Fixed formatting! Saved to `{saved_clean.name}`")
                    st.rerun()

            if st.button("🔍 Run Verilator Lint Check", use_container_width=True, type="secondary"):
                import tempfile
                with st.spinner("Running Verilator..."):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        v_files = []
                        for mod_name, code in st.session_state.agent_rtl.items():
                            fpath = os.path.join(tmpdir, f"{mod_name}.v")
                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(code)
                            v_files.append(f"{mod_name}.v")
                        
                        # -Wall catches real errors; --Wno-UNUSED silences stylistic 'not used' warnings
                        # (dead declarations are already stripped by strip_unused_signals();
                        #  partial-port-bit usage like instr[6:0] can't be removed without altering the port)
                        cmd = ["verilator", "--lint-only", "-Wall", "--Wno-UNUSED"] + v_files
                        try:
                            res = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True)
                        except FileNotFoundError:
                            # Fallback if python is on Windows but Verilator is in WSL
                            cmd = ["wsl", "verilator", "--lint-only", "-Wall", "--Wno-UNUSED"] + v_files
                            try:
                                res = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True)
                            except Exception as e:
                                res = subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr=str(e))
                        
                        output = (res.stdout + "\n" + res.stderr).strip()
                        if res.returncode == 0 and not output:
                            st.success("✅ Verilator Strict Lint Passed! Zero warnings, zero errors.")
                        elif res.returncode == 0:
                            st.warning("⚠️ Passed with warnings:")
                            st.code(output, language="bash")
                        else:
                            st.error("❌ Verilator Lint Failed:")
                            st.code(output, language="bash")

            for mod_name, code in rtl.items():
                with st.expander(f"📄 {mod_name}.v", expanded=(len(rtl) == 1)):
                    # individual download
                    st.download_button(
                        f"⬇ {mod_name}.v",
                        data=code,
                        file_name=f"{mod_name}.v",
                        mime="text/plain",
                        key=f"dl_{mod_name}",
                    )
                    st.code(code, language="verilog")

    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="phase-card">', unsafe_allow_html=True)
    st.markdown('<div class="phase-header"><h2>Phase 4: Bring Silicon to Life (C++ Testbench)</h2></div>', unsafe_allow_html=True)
    st.markdown("Your Verilog is isolated. Let's supply the heartbeat (clock) and external motherboard RAM (1MB) using a C++ Verilator Testbench.")
    
    vtop_exists = __import__('pathlib').Path("/tmp/riscv_sim/obj_dir/Vtop").exists()
    if vtop_exists:
        st.success("✅ Cached CPU binary found at `/tmp/riscv_sim/obj_dir/Vtop`. You can run the simulation directly.")

    col_build, col_run = st.columns([1, 1])
    with col_build:
        force_rebuild = st.checkbox("🔨 Force Full Rebuild (slow, ~60s)", value=not vtop_exists)
        do_build = st.button("🚀 Build & Simulate CPU", use_container_width=True, type="primary")
    with col_run:
        st.caption("Skip rebuild, run cached binary instantly:")
        run_only = st.button("▶️ Run Simulation Only", use_container_width=True,
                             disabled=not vtop_exists)

    if do_build or run_only:
        tb_code = """#include <iostream>
#include <fstream>
#include <iomanip>
#include "Vtop.h"         
#include "verilated.h"

// 1MB Flat Memory Array
#define MEM_SIZE 1024 * 1024 
uint8_t main_memory[MEM_SIZE] = {0};

uint32_t read_word(uint32_t addr) {
    if (addr >= MEM_SIZE - 3) return 0;
    return main_memory[addr] | (main_memory[addr+1] << 8) | 
           (main_memory[addr+2] << 16) | (main_memory[addr+3] << 24);
}

void write_memory(uint32_t addr, uint32_t data, uint8_t wstrb) {
    if (addr >= MEM_SIZE - 3) return;
    if (wstrb & 0x1) main_memory[addr]   = data & 0xFF;
    if (wstrb & 0x2) main_memory[addr+1] = (data >> 8) & 0xFF;
    if (wstrb & 0x4) main_memory[addr+2] = (data >> 16) & 0xFF;
    if (wstrb & 0x8) main_memory[addr+3] = (data >> 24) & 0xFF;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtop* top = new Vtop;

    // --- LOAD FIRMWARE ---
    // If a binary file is passed as argv[1], load it. Otherwise fall back to hardcoded boot program.
    if (argc >= 2) {
        std::ifstream file(argv[1], std::ios::binary);
        if (!file) { std::cerr << "Error: Could not open " << argv[1] << std::endl; return 1; }
        uint32_t addr = 0;
        while (addr < MEM_SIZE && file.read(reinterpret_cast<char*>(&main_memory[addr]), 1)) addr++;
        std::cout << "Loaded " << addr << " bytes from " << argv[1] << std::endl;
    } else {
        // Fallback: ADDI x1,x0,5 -> JAL x0,0 (infinite loop)
        main_memory[0]=0x93; main_memory[1]=0x00; main_memory[2]=0x50; main_memory[3]=0x00;
        main_memory[4]=0x6f; main_memory[5]=0x00; main_memory[6]=0x00; main_memory[7]=0x00;
        std::cout << "Running built-in boot program." << std::endl;
    }

    top->clk = 0;
    top->resetn = 0;
    uint64_t ticks = 0;
    const uint64_t MAX_TICKS = 200000; // 100k cycles max
    int exit_code = 0;

    std::cout << "Starting RISC-V Simulation..." << std::endl;

    while (!Verilated::gotFinish() && ticks < MAX_TICKS) {
        top->clk = !top->clk;
        if (ticks > 4) top->resetn = 1;

        top->eval();

        top->imem_rdata = read_word(top->imem_addr);
        if (top->dmem_read) top->dmem_rdata = read_word(top->dmem_addr);
        else top->dmem_rdata = 0;

        if (top->clk == 1 && top->dmem_write) {
            write_memory(top->dmem_addr, top->dmem_wdata, top->dmem_wstrb);
        }

        top->eval();

        // tohost trap: our custom linker script places tohost at 0x00001000
        // riscv-tests write 1 on PASS, (test_id<<1)|1 on FAIL
        if (top->clk == 1 && top->dmem_write && top->dmem_addr == 0x00001000) {
            uint32_t val = top->dmem_wdata;
            if (val == 1) { std::cout << "TOHOST:PASS" << std::endl; exit_code = 0; }
            else { std::cout << "TOHOST:FAIL:" << (val >> 1) << std::endl; exit_code = 1; }
            break;
        }

            // Only print first 15 cycles to avoid flooding stdout with infinite loop output
            static int print_limit = 0;
            if (top->clk == 0 && top->resetn == 1 && argc < 2 && print_limit < 15) {
                std::cout << "Cycle: " << std::dec << (ticks/2)
                          << " | PC: 0x" << std::setfill('0') << std::setw(8) << std::hex << top->imem_addr
                          << " | Instr: 0x" << std::setw(8) << top->imem_rdata << std::endl;
                print_limit++;
                if (print_limit == 15) {
                    std::cout << std::dec << "... (trace limit reached, CPU is running. Will stop at cycle 1000)" << std::endl;
                }
            }
            // For boot program (no file), cap at 1000 cycles — enough to see behaviour
            if (argc < 2 && ticks > 2000) break;

        ticks++; // IMPORTANT: advance clock!
    }

    if (ticks >= MAX_TICKS) std::cout << "TIMEOUT after " << (ticks/2) << " cycles." << std::endl;
    std::cout << "Simulation Ended." << std::endl;
    top->final();
    delete top;
    return exit_code;
}
"""
        import subprocess
        from pathlib import Path as _Path

        # GNU Make cannot build in paths with spaces — use /tmp as a safe, space-free sandbox
        sim_dir = _Path("/tmp/riscv_sim")
        sim_dir.mkdir(parents=True, exist_ok=True)
        sim_dir_str = str(sim_dir)  # "/tmp/riscv_sim" — guaranteed no spaces

        with st.spinner("Writing files, compiling and simulating..."):
            # Write all .v files
            v_files = []
            for mod_name, code in st.session_state.agent_rtl.items():
                fpath = sim_dir / f"{mod_name}.v"
                fpath.write_text(code, encoding="utf-8")
                v_files.append(f"{mod_name}.v")

            # Write testbench.cpp
            (sim_dir / "testbench.cpp").write_text(tb_code, encoding="utf-8")

            st.caption(f"📁 Working directory: `{sim_dir_str}`")

            skip_compile = run_only or (not force_rebuild and vtop_exists)

            if skip_compile:
                st.info("⚡ Skipping Verilator + g++ (using cached binary). Check 'Force Full Rebuild' to recompile.")
            v_files_str = " ".join(v_files)
            log_lines = []

            def run_step(label, cmd):
                r = subprocess.run(["bash", "-c", f"cd '{sim_dir_str}' && {cmd}"],
                                   capture_output=True, text=True)
                out = (r.stdout + r.stderr).strip()
                log_lines.append(f"--- {label} ---\n{out}" if out else f"--- {label} --- (no output)")
                return r.returncode, out

            sim_ready = False  # Will be set to True once we know the binary exists

            if not skip_compile:
                # Step 1: Verilate
                code1, out1 = run_step(
                    "Step 1: Verilator → C++",
                    f"rm -rf obj_dir && verilator --Wno-fatal --top-module top --cc {v_files_str} --exe testbench.cpp"
                )
                if code1 != 0:
                    st.error("❌ Verilator Failed:")
                    st.code(out1, language="bash")
                else:
                    # Auto-detect Makefile
                    find_res = subprocess.run(
                        ["bash", "-c", f"find '{sim_dir_str}/obj_dir' -maxdepth 1 -name 'V*.mk'"],
                        capture_output=True, text=True
                    )
                    mk_candidates = find_res.stdout.strip().splitlines()
                    if mk_candidates:
                        mk_name = mk_candidates[0].split("/")[-1]
                        target  = mk_name.replace(".mk", "")
                        mk_flag = f"-f {mk_name} {target}"
                    else:
                        mk_flag = ""

                    # Step 2: Compile
                    code2, out2 = run_step("Step 2: g++ Compile", f"make -j -C obj_dir {mk_flag}")
                    if code2 != 0:
                        st.error("❌ g++ Compilation Failed:")
                        st.code(out2, language="bash")
                    else:
                        st.success("✅ Compiled successfully!")
                        sim_ready = True
            else:
                sim_ready = True  # Binary already exists, skip build entirely

            if sim_ready:
                st.markdown("### 🖥️ RISC-V Terminal Output")
                out_placeholder = st.empty()
                out_lines = []
                # Use Popen so readline() yields control between lines (no full blocking)
                sim_proc = subprocess.Popen(
                    ["bash", "-c", f"cd '{sim_dir_str}' && ./obj_dir/Vtop"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in iter(sim_proc.stdout.readline, ""):
                    out_lines.append(line.rstrip())
                    out_placeholder.code("\n".join(out_lines[-30:]), language="bash")
                sim_proc.wait()
                if sim_proc.returncode == 0:
                    st.success("✅ Simulation Complete!")
                else:
                    st.error("❌ Runtime crash!")

            with st.expander("📋 Full Build Log"):
                st.code("\n\n".join(log_lines), language="bash")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5 — THE RISC-V GAUNTLET
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="phase-card">', unsafe_allow_html=True)
    st.markdown('<div class="phase-header"><h2>🏆 Phase 5: The RISC-V Gauntlet (riscv-tests)</h2></div>', unsafe_allow_html=True)
    st.markdown("Run the **official RISC-V Foundation test suite** against your CPU. Each test targets one instruction class (ADD, BEQ, LW, etc.).")

    import subprocess as _sp
    from pathlib import Path as _P5

    tests_bin_dir = _P5("/tmp/riscv-tests-bin")
    vtop_bin     = _P5("/tmp/riscv_sim/obj_dir/Vtop")

    col_setup, col_status = st.columns([1, 2])
    with col_setup:
        if st.button("📥 Setup riscv-tests", use_container_width=True):
            with st.spinner("Installing toolchain and compiling tests (~3 min first time)..."):
                setup_script = r"""
#!/bin/bash
set -e

# 1. Install toolchain
if ! command -v riscv64-unknown-elf-gcc &>/dev/null; then
    sudo apt-get install -y -q gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf
fi

# 2. Clone repo + pull env/ submodule (env/ contains riscv_test.h)
if [ ! -f /tmp/riscv-tests/env/p/riscv_test.h ]; then
    # Clone main repo if not present
    if [ ! -d /tmp/riscv-tests/.git ]; then
        rm -rf /tmp/riscv-tests
        git clone --depth=1 https://github.com/riscv-software-src/riscv-tests /tmp/riscv-tests
    fi
    # Pull the env/ submodule (contains riscv_test.h and link.ld)
    cd /tmp/riscv-tests && git submodule update --init --depth=1
fi

ENV_DIR=/tmp/riscv-tests/env/p
ISA_DIR=/tmp/riscv-tests/isa/rv32ui
MACRO_DIR=/tmp/riscv-tests/isa/macros/scalar
OUT_DIR=/tmp/riscv-tests-bin
mkdir -p $OUT_DIR

# 3. Write a CUSTOM linker script placing code at 0x00000000 and tohost at 0x00001000
# This matches our testbench CPU which resets to PC=0x0 and has 1MB RAM
cat > /tmp/riscv-link.ld << 'LDEOF'
OUTPUT_ARCH( "riscv" )
ENTRY( _start )
SECTIONS {
  . = 0x00000000;
  .text.init : { *(.text.init) }
  . = ALIGN(0x100);
  .text : { *(.text) }
  . = 0x00001000;
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .data : { *(.data) }
  .bss : { *(.bss) }
  _end = .;
}
LDEOF

# 3.5. CRITICAL PATCH: riscv_test.h uses 'ecall' for RVTEST_PASS which requires
#      machine-mode exception support. Our bare-metal CPU has no CSR/trap support.
#      Patch RVTEST_PASS to jump directly to write_tohost instead.
echo "Patching riscv_test.h to bypass ecall (bare-metal CPU has no exception support)..."
# Replace ecall inside RVTEST_PASS definition with j write_tohost
sed -i '/^#define RVTEST_PASS/,/ecall/{s/ecall/j write_tohost/}' ${ENV_DIR}/riscv_test.h
# Replace j fail_tohost with j write_tohost (write_tohost uses TESTNUM/gp value)
sed -i 's/j fail_tohost/j write_tohost/' ${ENV_DIR}/riscv_test.h
echo "Patch applied."

# 4. Compile each rv32ui test directly (bypass broken autoconf/configure)
PASS=0; FAIL=0
for src in $ISA_DIR/*.S; do
    base=$(basename "$src" .S)
    test_name="rv32ui-p-${base}"
    elf="/tmp/riscv-tests/${test_name}"
    bin="${OUT_DIR}/${test_name}.bin"
    
    riscv64-unknown-elf-gcc \
        -march=rv32im -mabi=ilp32 \
        -static -nostdlib -nostartfiles \
        -T/tmp/riscv-link.ld \
        -I${ENV_DIR} -I${MACRO_DIR} \
        "$src" -o "$elf" 2>/dev/null && \
    riscv64-unknown-elf-objcopy -O binary "$elf" "$bin" && \
    echo "✓ ${test_name}" && PASS=$((PASS+1)) || \
    (echo "✗ ${test_name} SKIPPED" && FAIL=$((FAIL+1)))
done

echo ""
echo "DONE: ${PASS} compiled, ${FAIL} skipped -> $(ls ${OUT_DIR}/*.bin 2>/dev/null | wc -l) binaries in ${OUT_DIR}"
"""
                res = _sp.run(["bash", "-c", setup_script], capture_output=True, text=True)
                out = (res.stdout + res.stderr).strip()
                if res.returncode == 0:
                    st.success("✅ riscv-tests ready!")
                else:
                    st.error("❌ Setup failed:")
                st.code(out[-3000:], language="bash")  # last 3000 chars

    with col_status:
        bins = sorted(tests_bin_dir.glob("*.bin")) if tests_bin_dir.exists() else []
        if bins:
            st.success(f"✅ {len(bins)} test binaries found in `/tmp/riscv-tests-bin/`")
        else:
            st.info("ℹ️ Click **Setup riscv-tests** first to download and compile the test suite.")

    st.divider()

    if not vtop_bin.exists():
        st.warning("⚠️ CPU binary not found at `/tmp/riscv_sim/obj_dir/Vtop`. Run Phase 4 Build first!")
    elif bins:
        if st.button("⚔️ Run Full Gauntlet", use_container_width=True, type="primary"):
            results = []
            progress   = st.progress(0, text="Starting gauntlet...")
            live_table = st.empty()

            # Build a single bash script that runs every test and emits one result
            # line per test → Popen + readline() streams results live, no blocking
            bin_paths_str = " ".join(f'"{str(b)}"' for b in bins)
            gauntlet_sh = f"""
#!/bin/bash
VTOP="{str(vtop_bin)}"
for bin in {bin_paths_str}; do
    name=$(basename "$bin" .bin)
    out=$("$VTOP" "$bin" 2>&1)
    if echo "$out" | grep -q "TOHOST:PASS"; then
        echo "PASS:$name"
    elif echo "$out" | grep -q "TOHOST:FAIL:"; then
        code=$(echo "$out" | grep -o "TOHOST:FAIL:[0-9]*" | cut -d: -f3)
        echo "FAIL:$name:$code"
    elif echo "$out" | grep -q "TIMEOUT"; then
        echo "TIMEOUT:$name"
    else
        echo "UNKNOWN:$name"
    fi
done
echo "DONE"
"""
            proc = _sp.Popen(["bash", "-c", gauntlet_sh],
                             stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True)

            import pandas as pd
            for line in iter(proc.stdout.readline, ""):
                line = line.strip()
                if not line or line == "DONE":
                    break
                parts = line.split(":", 2)
                verdict, name = parts[0], parts[1] if len(parts) > 1 else "?"
                fail_num = parts[2] if len(parts) > 2 else ""
                if verdict == "PASS":    status = "✅ PASS"
                elif verdict == "FAIL":  status = f"❌ FAIL (test #{fail_num})"
                elif verdict == "TIMEOUT": status = "⏱️ TIMEOUT"
                else:                    status = "❓ UNKNOWN"
                results.append({"Test": name, "Result": status})
                pct = len(results) / len(bins)
                progress.progress(pct, text=f"[{len(results)}/{len(bins)}] {name}: {status}")
                live_table.dataframe(pd.DataFrame(results), use_container_width=True)

            proc.wait()
            progress.progress(1.0, text="Gauntlet complete!")
            df = pd.DataFrame(results) if results else pd.DataFrame(columns=["Test","Result"])
            passed = (df["Result"].str.startswith("✅")).sum()
            failed = len(df) - passed
            st.markdown(f"### Score: **{passed}/{len(df)}** tests passed")
            if failed == 0:
                st.success("🏆 PERFECT SCORE! Your core is RV32I compliant!")
            else:
                st.warning(f"⚠️ {failed} test(s) failed — review the table below.")
            st.dataframe(df, use_container_width=True, height=600)

    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    # ── Master Save Button ───────────────────────────────────────────────────
    plan_done = st.session_state.agent_plan is not None
    isa_done  = st.session_state.agent_isa is not None
    rtl_done  = bool(st.session_state.agent_rtl)
    
    if plan_done or isa_done or rtl_done:
        if st.button("💾 Save Snapshot to Disk (Manual)", use_container_width=True):
            saved = save_pipeline_snapshot("manual")
            st.success(f"✅ Pipeline snapshot saved to `{saved}`")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RAG Q&A
# ═══════════════════════════════════════════════════════════════════════════════
with tab_qa:
    st.markdown("### 🔍 Ask a RISC-V Architecture Question")
    st.caption("Retrieves from your ingested corpus and grounds the LLM answer in exact source passages.")

    question = st.text_area(
        "Question",
        placeholder="e.g. How do you implement the 4-bit byte-mask for SB, SH and SW?",
        height=90,
        label_visibility="collapsed",
        key="qa_question",
    )

    col_run, col_clr = st.columns([5, 1])
    with col_run:
        run_btn = st.button("⚡ Retrieve & Answer", type="primary",
                            use_container_width=True, disabled=not question.strip())
    with col_clr:
        if st.button("✕", use_container_width=True):
            st.rerun()

    if run_btn and question.strip():
        if not api_key:
            st.error("❌ Add Groq API Key in sidebar.")
            st.stop()

        from groq import Groq
        groq_client = Groq(api_key=api_key)
        with st.spinner("Loading pipeline..."):
            pipe = load_pipeline()
        rt = pipe["rt"]

        with st.spinner("🔍 Retrieving..."):
            parents = run_retrieval(pipe, question, use_hyde, groq_client,
                                    top_k_parents, top_k_children)

        st.markdown(f"#### 📎 Top {len(parents)} Source Chunks")
        for p in parents:
            ptok = rt.count_tokens(p["full_text"])
            st.markdown(f"""
<div class="rag-card">
  <div class="rag-card-title">
    {p['section_title']}
    &nbsp;<span class="score-badge">RRF {p['rrf_score']:.4f}</span>
    &nbsp;<span class="tok-badge">{ptok} tok</span>
  </div>
  <div class="rag-card-body">{p['child_matched'][:240]}</div>
</div>""", unsafe_allow_html=True)

        # Token budget
        _, prompt_tokens = rt.build_prompt(question, parents)
        pct = min(prompt_tokens / rt.MAX_INPUT_TOKENS, 1.0)
        bar = "█" * int(pct * 36) + "░" * (36 - int(pct * 36))
        over_html = ("<span class='stat-pill' style='background:rgba(239,68,68,0.18);"
                     "color:#fca5a5;border-color:#ef4444;'>⚠️ OVER BUDGET</span>"
                     if prompt_tokens > rt.MAX_INPUT_TOKENS else "")
        st.markdown(f"""
<div class="budget-bar">
  <span class="stat-pill">📥 {prompt_tokens} tok</span>
  <span class="stat-pill">📤 max {rt.MAX_OUTPUT_TOKENS} tok</span>
  <span class="stat-pill">🔒 cap {rt.MAX_INPUT_TOKENS}</span>
  {over_html}
  <br><br><code style="color:#64748b;">[{bar}] {pct*100:.1f}%</code>
</div>""", unsafe_allow_html=True)

        st.markdown("#### 💡 Answer")
        placeholder = st.empty()
        placeholder.markdown('<div class="answer-box">⏳ Generating...</div>', unsafe_allow_html=True)
        try:
            limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)
            answer, _ = rt.ask_llm(groq_client, question, parents, rate_limiter=limiter)
            placeholder.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
        except Exception as e:
            placeholder.error(f"❌ {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ingest URL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ingest:
    st.markdown("### 📥 Ingest a New Knowledge Source")
    st.caption("Runs `chunk.py` to scrape → chunk → save. The pipeline auto-picks it up on next reload.")

    c1, c2 = st.columns([3, 1])
    with c1:
        ingest_url = st.text_input("URL", placeholder="https://github.com/riscv/riscv-isa-manual")
    with c2:
        ingest_slug = st.text_input("Slug", placeholder="isa_manual")

    if st.button("🚀 Run Ingest", type="primary", use_container_width=True,
                 disabled=not (ingest_url.strip() and ingest_slug.strip())):
        slug = ingest_slug.strip().lower().replace(" ", "_")
        url  = ingest_url.strip()
        st.info(f"▶️ `python3 chunk.py {url} --slug {slug}`")
        log_area = st.empty()
        full_log = ""
        cmd  = [sys.executable, "chunk.py", url, "--slug", slug]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, cwd=str(Path(__file__).parent))
        for line in proc.stdout:
            full_log += line
            log_area.code(full_log, language="bash")
        proc.wait()
        if proc.returncode == 0:
            st.success(f"✅ Done! Reload the pipeline to embed `{slug}`.")
        else:
            st.error(f"❌ chunk.py exited {proc.returncode}")

        cf = Path(f"scraped data/{slug}_chunks.json")
        if cf.exists():
            with open(cf, encoding="utf-8") as f:
                chunks = json.load(f)
            st.markdown(f"**{len(chunks)} chunks** written to `{cf}`")
            with st.expander("Preview first 3"):
                for c in chunks[:3]:
                    st.json({k: str(v)[:300] for k, v in c.items()})


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Corpus
# ═══════════════════════════════════════════════════════════════════════════════
with tab_corpus:
    st.markdown("### 📚 Knowledge Base Corpus")
    st.caption("All `*_chunks.json` files in `scraped data/`.")

    data_dir = Path("scraped data")
    if not data_dir.exists():
        st.warning("⚠️ `scraped data/` not found.")
    else:
        rows = corpus_stats()
        if not rows:
            st.info("No data yet — use Ingest URL tab.")
        else:
            total_chunks = sum(r["Chunks"] for r in rows)
            total_tokens = sum(r["Est. Tokens"] for r in rows)
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("📦 Sources", len(rows))
            mc2.metric("🧩 Chunks", f"{total_chunks:,}")
            mc3.metric("🔢 Est. Tokens", f"{total_tokens:,}")
            st.divider()

            for r in rows:
                has_md = (data_dir / f"{r['Slug']}_full_doc.md").exists()
                st.markdown(f"""
<div class="rag-card">
  <div class="rag-card-title">
    {r['Slug']}
    &nbsp;<span class="score-badge">{r['Chunks']} chunks</span>
    &nbsp;<span class="tok-badge">{r['Est. Tokens']:,} tok</span>
    {'&nbsp;<span class="score-badge" style="background:rgba(34,197,94,0.14);color:#86efac;">✓ md</span>' if has_md else ''}
  </div>
  <div class="rag-card-body">{r['Doc Types']}</div>
</div>""", unsafe_allow_html=True)

            mf = Path("chroma_store/manifest.json")
            if mf.exists():
                st.divider()
                st.markdown("#### 🗺️ ChromaDB Manifest")
                with open(mf, encoding="utf-8") as f:
                    manifest = json.load(f)
                slug_set = {r["Slug"] for r in rows}
                for slug, fhash in manifest.items():
                    icon = "✅" if slug in slug_set else "⚠️ orphan"
                    st.markdown(f"- `{slug}` — `{fhash[:14]}...` — {icon}")
            else:
                st.caption("No manifest — pipeline hasn't run yet.")
