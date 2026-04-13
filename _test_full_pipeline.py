"""
Full pipeline terminal test — all 3 phases with the RV32I description.
Stages:
  Phase 1 — Planner  (LLM)
  Phase 2 — Researcher + Systems Engineer  (LLM micro-queries + deterministic)
  Phase 4a— RTL Renderer (Jinja2, 0 LLM tokens for control + imm_gen)
"""
import os, sys, json, time, re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

import httpx
from groq import Groq
client = Groq(api_key=api_key, http_client=httpx.Client())

MODEL = "llama-3.3-70b-versatile"
OUT_DIR = Path("terminal_run_output")
OUT_DIR.mkdir(exist_ok=True)

CPU_DESCRIPTION = """\
You are generating RTL for a **simple in-order RV32I processor** — a 32-bit RISC-V core implementing the base integer instruction set. This is the smallest complete RISC-V ISA: 47 instructions covering arithmetic, loads/stores, branches, and jumps. No floating point, no compressed instructions, no privileged mode required.

A minimal in-order implementation has the following canonical stages:
  Fetch → Decode → Execute → Memory → Writeback

Key components to generate:
  - Program Counter (PC): Holds current instruction address, updates on branch/jump or sequential increment
  - Instruction Fetch: Reads instruction from memory at PC
  - Decoder: Decodes opcode, funct3, rs1, rs2, rd, and immediate fields
  - Register File: 32 × 32-bit general-purpose registers (x0 hardwired to 0)
  - ALU: Performs ADD, SUB, AND, OR, XOR, SLT, shifts
  - Branch Unit: Evaluates BEQ, BNE, BLT, BGE, BLTU, BGEU conditions
  - Load/Store Unit: Handles LW, LH, LB, SW, SH, SB with byte-enable logic
  - Control Hazard Handling: Pipeline flush or stall on taken branches

NOT required: caches, out-of-order execution, branch prediction, privilege modes.
Focus on a correct, functional RV32I core.
"""

PLANNER_SYSTEM = """You are the Planner Agent for an automated RISC-V RTL design flow.

PHASE CONSTRAINT: This is the INITIAL golden reference generation pass. The architecture MUST be single-cycle.
IMPORTANT: Even if the user says \"pipeline\" or \"5-stage\", set architecture=\"single-cycle\".

MANDATORY OUTPUT — valid JSON only, no prose:
{
  "architecture": "single-cycle",
  "reason": "<your reason>",
  "assumptions": ["..."],
  "missing_spec": [],
  "instruction_groups": [
    {"group": "R-Type ALU",  "instructions": ["ADD","SUB","AND","OR","XOR","SLT","SLTU","SLL","SRL","SRA"], "priority": 1},
    {"group": "I-Type ALU",  "instructions": ["ADDI","ANDI","ORI","XORI","SLTI","SLTIU","SLLI","SRLI","SRAI"], "priority": 2},
    {"group": "U-Type",      "instructions": ["LUI","AUIPC"], "priority": 3},
    {"group": "Branches",    "instructions": ["BEQ","BNE","BLT","BGE","BLTU","BGEU"], "priority": 4},
    {"group": "Loads",       "instructions": ["LB","LH","LW","LBU","LHU"], "priority": 5},
    {"group": "Stores",      "instructions": ["SB","SH","SW"], "priority": 6},
    {"group": "Jumps",       "instructions": ["JAL","JALR"], "priority": 7}
  ],
  "modules": [
    {"name": "regfile",    "depends_on": []},
    {"name": "imm_gen",    "depends_on": []},
    {"name": "alu",        "depends_on": []},
    {"name": "branch_unit","depends_on": ["alu"]},
    {"name": "load_store", "depends_on": []},
    {"name": "control",    "depends_on": []},
    {"name": "pc_next",    "depends_on": ["branch_unit"]},
    {"name": "top",        "depends_on": ["regfile","imm_gen","alu","branch_unit","load_store","control","pc_next"]}
  ],
  "milestones": [
    {"phase": 1, "goal": "regfile + ALU + R-type only", "modules": ["regfile","alu","control","top"]},
    {"phase": 2, "goal": "I-type + U-type + Shifts",     "modules": ["imm_gen"]},
    {"phase": 3, "goal": "Branches + Jumps",             "modules": ["branch_unit","pc_next"]},
    {"phase": 4, "goal": "Loads + Stores",               "modules": ["load_store"]}
  ],
  "tohost_address": "0x80001000",
  "reset_pc": "0x00000000"
}
"""

def strip_fences(s):
    s = re.sub(r"^```[a-z]*\n?", "", s.strip())
    s = re.sub(r"```\s*$", "", s).strip()
    # strip JS-style comments before parsing
    s = re.sub(r"//[^\n]*", "", s)
    return s

# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PHASE 1 — PLANNER AGENT")
print("="*60)
t0 = time.time()

resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user",   "content": CPU_DESCRIPTION},
    ],
    temperature=0.0,
    max_tokens=1200,
)
raw_plan = resp.choices[0].message.content
plan = json.loads(strip_fences(raw_plan))
with open(OUT_DIR / "planner_state.json", "w") as f:
    json.dump(plan, f, indent=2)

print(f"Architecture : {plan['architecture']}")
print(f"Modules      : {[m['name'] for m in plan['modules']]}")
print(f"Groups       : {[g['group'] for g in plan['instruction_groups']]}")
print(f"Done in {time.time()-t0:.1f}s\n")

# ─────────────────────────────────────────────────────────────
print("="*60)
print("PHASE 2a — RESEARCHER AGENT (7 micro-queries)")
print("="*60)
t0 = time.time()

import rag_test as rt
from researcher_agent import run_researcher_sync

parent_store, children, new_children = rt.build_hierarchy()
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer(rt.EMBED_MODEL)
collection = rt.build_chroma_children(new_children, embedder)
bm25, tokenize_fn = rt.build_bm25_children(children)
pipe = {
    "rt": rt, "parent_store": parent_store, "children": children,
    "bm25": bm25, "tokenize_fn": tokenize_fn,
    "embedder": embedder, "collection": collection,
}
arch = plan.get("architecture", "RISC-V RV32I")
isa_facts = run_researcher_sync(client, pipe, "RISC-V RV32I")

with open(OUT_DIR / "isa_facts.json", "w") as f:
    json.dump(isa_facts, f, indent=2)
print(f"\nResearcher done in {time.time()-t0:.1f}s.")

# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PHASE 2b — SYSTEMS ENGINEER (deterministic microarch.yaml)")
print("="*60)
t0 = time.time()

from systems_engineer import MicroarchBuilder, load_offline_isa
offline_isa = load_offline_isa("riscv32")
builder = MicroarchBuilder(isa_facts, offline_isa)
microarch = builder.build()
builder.save(microarch, str(OUT_DIR / "microarch.yaml"))
print(f"microarch.yaml written -> {OUT_DIR}/microarch.yaml")
print(f"Done in {time.time()-t0:.2f}s  (0 LLM tokens)")

# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PHASE 4a — JINJA2 RTL RENDERER (control.v + imm_gen.v)")
print("="*60)
t0 = time.time()

from rtl_renderer import RTLRenderer
rtl_out_dir = str(OUT_DIR / "rtl")
renderer = RTLRenderer()
results = renderer.render_all_truth_tables(microarch, offline_isa, rtl_out_dir)

for mod, path in results.items():
    lines = open(path).read().count("\n")
    print(f"  [{mod}] -> {path}  ({lines} lines,  0 LLM tokens)")
print(f"Done in {time.time()-t0:.2f}s")

# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("VERILATOR LINT CHECK")
print("="*60)
rtl_path = OUT_DIR / "rtl"
passed = True
for v_file in rtl_path.glob("*.v"):
    ret = os.system(f"verilator --lint-only --Wall {v_file}")
    if ret != 0:
        passed = False
        print(f"  FAIL: {v_file.name}")
    else:
        print(f"  PASS: {v_file.name}")

print()
if passed:
    print("✅  ALL PHASES COMPLETE — Output written to:", OUT_DIR)
else:
    print("❌  LINT FAILED — check output above")
