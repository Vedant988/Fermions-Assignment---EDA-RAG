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
  "tohost_address": "0x80001000",
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
  "ALU_op":      "ADD",        // True ALU primitive: ADD SUB AND OR XOR SLT SLTU SLL SRL SRA PASS_B
                               //   NEVER use an instruction name here (AUIPC, LUI, JAL are NOT ALU ops)
  "alu_src_a":   "rs1",        // First ALU operand mux: "rs1" | "pc" | "zero"
  "alu_src_b":   "rs2",        // Second ALU operand mux: "rs2" | "imm"
  "reg_write":   1,            // 1 = writes to rd, 0 = does not
  "mem_read":    0,            // 1 = load instruction
  "mem_write":   0,            // 1 = store instruction
  "mem_size":    "N/A",        // data width: "8" | "16" | "32" | "N/A"
  "mem_extend":  "N/A",        // "signed" | "unsigned" | "N/A"
  "branch":      0,            // 1 = conditional branch
  "jump":        0,            // 1 = unconditional jump (JAL/JALR)
  "wb_src":      "alu",        // writeback mux: "alu" | "mem" | "pc+4"
  "imm_type":    "N/A",        // "I" | "S" | "B" | "U" | "J" | "N/A"
  "notes":       ""
}

FOUR CANONICAL EXAMPLES (study these carefully before generating):

Example 1 — ADD (R-type, register ALU):
{
  "instruction": "ADD", "format": "R", "opcode": "0110011", "funct3": "000", "funct7": "0000000",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "rs2",
  "reg_write": 1, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 0, "jump": 0, "wb_src": "alu", "imm_type": "N/A", "notes": ""
}

Example 2 — SB (S-type store byte — alu_src_b MUST be imm for address calc):
{
  "instruction": "SB", "format": "S", "opcode": "0100011", "funct3": "000", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "imm",
  "reg_write": 0, "mem_read": 0, "mem_write": 1, "mem_size": "8", "mem_extend": "N/A",
  "branch": 0, "jump": 0, "wb_src": "N/A", "imm_type": "S", "notes": "addr = rs1 + imm; data = rs2[7:0]"
}

Example 3 — LB (I-type load byte signed — mem_size and mem_extend are critical):
{
  "instruction": "LB", "format": "I", "opcode": "0000011", "funct3": "000", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "rs1", "alu_src_b": "imm",
  "reg_write": 1, "mem_read": 1, "mem_write": 0, "mem_size": "8", "mem_extend": "signed",
  "branch": 0, "jump": 0, "wb_src": "mem", "imm_type": "I", "notes": "rd = sign_ext(mem[rs1+imm][7:0])"
}

Example 4 — AUIPC (U-type — ALU_op is ADD, alu_src_a is PC, NOT 'AUIPC'):
{
  "instruction": "AUIPC", "format": "U", "opcode": "0010111", "funct3": "N/A", "funct7": "N/A",
  "ALU_op": "ADD", "alu_src_a": "pc", "alu_src_b": "imm",
  "reg_write": 1, "mem_read": 0, "mem_write": 0, "mem_size": "N/A", "mem_extend": "N/A",
  "branch": 0, "jump": 0, "wb_src": "alu", "imm_type": "U", "notes": "rd = PC + (imm << 12)"
}

ADDITIONAL RULES:
1. ALU_op MUST be a primitive: ADD SUB AND OR XOR SLT SLTU SLL SRL SRA PASS_B — NEVER an instruction name.
2. LUI: ALU_op=PASS_B, alu_src_a=zero, alu_src_b=imm (ALU just passes the shifted immediate through).
3. All R-type instructions share opcode 0110011 — this is correct, funct3/funct7 differentiate them.
4. mem_size: LB/SB=8, LH/SH=16, LW/SW=32. mem_extend: LB/LH=signed, LBU/LHU=unsigned, stores=N/A.
5. Branches: alu_src_a=rs1, alu_src_b=rs2 (ALU compares operands), wb_src=N/A, reg_write=0.
6. JAL: alu_src_a=pc, alu_src_b=imm, ALU_op=ADD (computes target), wb_src=pc+4.
7. JALR: alu_src_a=rs1, alu_src_b=imm, ALU_op=ADD, wb_src=pc+4.
"""



RTL_GENERATOR_SYSTEM = """You are the RTL Generator Agent for a RISC-V single-cycle processor.

ARCHITECTURE MANDATE — SINGLE-CYCLE ONLY:
This is a single-cycle implementation. Every instruction completes in exactly one clock cycle.
DO NOT generate any of the following — they belong to a pipelined architecture:
  ✗ Pipeline stage registers (IF_ID, ID_EX, EX_MEM, MEM_WB)
  ✗ Hazard detection units
  ✗ Forwarding multiplexers
  ✗ Stall logic
  ✗ Flush signals
Violating these constraints will produce code that passes synthesis but fails rv32ui-p-add immediately.

You receive:
- Module name + its dependencies (from the Planner DAG).
- The full ISA control signal truth table (from ISA Expert) — this is ground truth for all encodings.
- Architecture-level constants (reset_pc, tohost_address).

PER-MODULE PORT CONTRACTS (use EXACTLY these port names for correct interconnect in top.v):
  regfile    : clk, we, rs1, rs2, rd, rd_data → rd1[31:0], rd2[31:0]
  imm_gen    : instr[31:0] → imm[31:0]
  alu        : a[31:0], b[31:0], alu_op[3:0] → result[31:0], zero
  branch_unit: funct3[2:0], rs1[31:0], rs2[31:0] → taken
  load_store : clk, mem_read, mem_write, mem_size[1:0], mem_extend, addr[31:0], wdata[31:0] → rdata[31:0]
  control    : opcode[6:0], funct3[2:0], funct7[6:0] → all control signals (alu_src_a, alu_src_b, reg_write, mem_read, mem_write, mem_size, mem_extend, branch, jump, wb_src, alu_op, imm_type)
  pc_next    : pc[31:0], imm[31:0], rs1[31:0], taken, jump, branch, jump_type → pc_next[31:0]
  top        : clk, rst → (instantiates all sub-modules; writes tohost on test end)

RULES:
- Use `always_comb` for combinational logic. Every `case` MUST have a `default` clause (no latches).
- Use `always_ff @(posedge clk)` for sequential elements (regfile, PC register).
- Register x0 in regfile: gate write-enable as `if (rd != 5'd0)`.
- For control.v: drive all control signals from opcode/funct3/funct7 using the ISA truth table.
- Add a one-line comment on every non-obvious signal assignment.
- Do NOT generate a testbench. Module definition only.
Output ONLY the Verilog code, no prose before or after.
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
                    tohost address: {plan.get('tohost_address', '0x80001000')}
                    Reset PC: {plan.get('reset_pc', '0x00000000')}

                    Module to generate: {mod_name}
                    Depends on: {', '.join(mod_spec.get('depends_on', [])) or 'None (leaf)'}

                    ISA Control Signal Truth Table (use ONLY this for encoding):
                    {isa_table_str}

                    Generate the complete synthesizable Verilog module for `{mod_name}`.
                    """).strip()

                    verilog = llm_call(groq_client, RTL_GENERATOR_SYSTEM, user_msg,
                                       limiter, max_tokens=4096)
                    all_rtl[mod_name] = verilog

                rtl_progress.progress(1.0, text="✅ RTL generation complete.")
                st.session_state.agent_rtl = all_rtl
                st.success(f"✅ Generated {len(selected_mods)} module(s).")

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
            st.download_button(
                "💾 Download All (.zip)",
                data=zip_buf,
                file_name="riscv_rtl.zip",
                mime="application/zip",
                use_container_width=False,
            )

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
