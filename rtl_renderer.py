"""
rtl_renderer.py — Stage 4: Universal RTL Router
================================================
Routes each module to the correct generation tier:

  TIER 1 — TRUTH_TABLE   : Jinja2 + Python   (zero LLM tokens)
    control.v, imm_gen.v
    These are pure opcode→binary routing tables. Python does this perfectly.

  TIER 2 — BEHAVIORAL_LOGIC : LLM + dynamic cheatsheet
    alu.v, branch_unit.v, cpu.v (top-level)
    Require actual Verilog behavioral math and structural DAG wiring.
    The LLM is given the exact binary cheatsheet from microarch.yaml so it
    NEVER hallucinates encodings.

  TIER 3 — TESTBENCH_ONLY : Jinja2 (tb_cpu.v.j2)
    data_mem and instr_mem arrays live ONLY in the testbench.
    They MUST NOT appear in the CPU core.

Usage (CLI):
  python rtl_renderer.py microarch.yaml rtl_generated/          # all modules
  python rtl_renderer.py microarch.yaml rtl_generated/ control  # single module
"""

from __future__ import annotations
import os
import re
import json
import yaml
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


# ─────────────────────────────────────────────────────────────────────────────
# Tier classification — the Router table
# ─────────────────────────────────────────────────────────────────────────────

TIER_TRUTH_TABLE       = "truth_table"       # Jinja2 + Python, 0 LLM tokens
TIER_BEHAVIORAL_LOGIC  = "behavioral_logic"  # LLM + dynamic cheatsheet
TIER_TESTBENCH_ONLY    = "testbench_only"    # Jinja2, memory arrays, TB only

MODULE_TIERS: dict[str, str] = {
    # ── TRUTH_TABLE (pure combinational routing, no reasoning needed) ──────
    "control":     TIER_TRUTH_TABLE,
    "imm_gen":     TIER_TRUTH_TABLE,

    # ── BEHAVIORAL_LOGIC (LLM writes actual Verilog math + DAG wiring) ────
    "regfile":     TIER_BEHAVIORAL_LOGIC,
    "alu":         TIER_BEHAVIORAL_LOGIC,
    "branch_unit": TIER_BEHAVIORAL_LOGIC,
    "load_store":  TIER_BEHAVIORAL_LOGIC,
    "pc_next":     TIER_BEHAVIORAL_LOGIC,
    "cpu":         TIER_BEHAVIORAL_LOGIC,   # top-level structural wrapper

    # ── TESTBENCH_ONLY (memory arrays — never in the CPU core) ────────────
    "instr_mem":   TIER_TESTBENCH_ONLY,
    "data_mem":    TIER_TESTBENCH_ONLY,
    "tb_cpu":      TIER_TESTBENCH_ONLY,
}

# Convenience sets derived from the single source of truth above
BEHAVIORAL_LOGIC_MODULES_SET: set[str] = {
    name for name, tier in MODULE_TIERS.items() if tier == TIER_BEHAVIORAL_LOGIC
}
TRUTH_TABLE_MODULES_SET: set[str] = {
    name for name, tier in MODULE_TIERS.items() if tier == TIER_TRUTH_TABLE
}
TESTBENCH_ONLY_MODULES_SET: set[str] = {
    name for name, tier in MODULE_TIERS.items() if tier == TIER_TESTBENCH_ONLY
}

# Jinja2 template files for TRUTH_TABLE modules
TRUTH_TABLE_TEMPLATES: dict[str, str] = {
    "control": "control.v.j2",
    "imm_gen": "imm_gen.v.j2",
}

# Jinja2 template for the testbench (memory arrays live here)
TESTBENCH_TEMPLATE = "tb_cpu.v.j2"


def route_module(module_name: str) -> str:
    """Return the tier classification for a module name."""
    tier = MODULE_TIERS.get(module_name)
    if tier is None:
        raise ValueError(
            f"Unknown module '{module_name}'. "
            f"Register it in MODULE_TIERS before generating RTL."
        )
    return tier


# ─────────────────────────────────────────────────────────────────────────────
# Context builders — TRUTH_TABLE (pure Python, all binary formatting here)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_bin(value: int | None, width: int) -> str | None:
    """Format an integer as a fixed-width binary string, or return None."""
    if value is None:
        return None
    return format(value, f'0{width}b')


def _alu_src_a_bits(src: str) -> str:
    """Map alu_src_a semantic name → 2-bit binary."""
    return {"rs1": "00", "pc": "01", "zero": "10"}.get(src, "00")


def _enrich_rec(rec: dict, alu_w: int, imm_w: int, wb_w: int, mem_w: int) -> dict:
    """
    Add pre-computed bin_* fields to an ICD record.
    The Jinja2 template only reads these — zero math inside the template.
    """
    r = dict(rec)
    r["bin_alu_op"]    = _fmt_bin(rec.get("alu_op"),    alu_w)
    r["bin_imm_type"]  = _fmt_bin(rec.get("imm_type"),  imm_w)
    r["bin_writeback"] = _fmt_bin(rec.get("writeback"),  wb_w)
    r["bin_mem_size"]  = _fmt_bin(rec.get("mem_size"),   mem_w)
    r["bin_alu_src_a"] = _alu_src_a_bits(rec.get("alu_src_a", "rs1"))
    return r


def build_control_context(microarch: dict) -> dict:
    """
    Build the full Jinja2 context for control.v.j2.

    Groups ICD records by opcode, then by funct3, then by funct7b5 —
    exactly matching the case/if nesting the template needs.
    """
    alu_w = microarch["alu"]["width"]
    imm_w = microarch["imm_type"]["width"]
    wb_w  = microarch["writeback"]["width"]
    mem_w = microarch["mem_size"]["width"]
    icd   = microarch["instruction_icd"]

    # Enrich all records with pre-computed binary strings
    enriched = [_enrich_rec(r, alu_w, imm_w, wb_w, mem_w) for r in icd]

    # Group by opcode (preserve insertion order = instruction order)
    opcode_map: dict[str, list] = {}
    for r in enriched:
        opcode_map.setdefault(r["opcode"], []).append(r)

    opcode_groups = []
    for opcode_val, recs in opcode_map.items():
        mnemonics = [r["mnemonic"] for r in recs]

        if len(recs) == 1:
            opcode_groups.append({
                "opcode":    opcode_val,
                "mnemonics": mnemonics,
                "single":    True,
                "rec":       recs[0],
            })
        else:
            # Multiple instructions share this opcode → need funct3 sub-case
            funct3_map: dict[str, list] = {}
            for r in recs:
                f3 = r.get("funct3") or "000"
                funct3_map.setdefault(f3, []).append(r)

            funct3_groups = []
            for f3, f3_recs in funct3_map.items():
                f3_mnemonics = [r["mnemonic"] for r in f3_recs]
                if len(f3_recs) == 1:
                    funct3_groups.append({
                        "f3":        f3,
                        "mnemonics": f3_mnemonics,
                        "single":    True,
                        "rec":       f3_recs[0],
                    })
                else:
                    # Multiple with same opcode+funct3 → split by funct7b5
                    funct3_groups.append({
                        "f3":        f3,
                        "mnemonics": f3_mnemonics,
                        "single":    False,
                        "recs":      f3_recs,
                    })

            opcode_groups.append({
                "opcode":        opcode_val,
                "mnemonics":     mnemonics,
                "single":        False,
                "funct3_groups": funct3_groups,
            })

    return {
        "mod_name":         "control",
        "arch_name":        microarch.get("architecture", "unknown"),
        "xlen":             microarch.get("xlen", 32),
        "alu_w":            alu_w,
        "imm_w":            imm_w,
        "wb_w":             wb_w,
        "mem_w":            mem_w,
        "num_instructions": len(icd),
        "num_alu_ops":      len(microarch["alu"]["encoding"]),
        "opcode_groups":    opcode_groups,
    }


def build_imm_gen_context(microarch: dict, offline_isa: dict | None = None) -> dict:
    """
    Build the Jinja2 context for imm_gen.v.j2.
    Pre-computes sign-extension repetition widths so the template does zero math.
    """
    imm_w   = microarch["imm_type"]["width"]
    imm_enc = microarch["imm_type"].get("binary", {})
    xlen    = microarch.get("xlen", 32)

    imm_formats = {}
    if offline_isa:
        imm_formats = offline_isa.get("format_immediates", {})

    sign_ext = {
        "I": xlen - 12,
        "S": xlen - 12,
        "B": xlen - 13,
        "U": 0,
        "J": xlen - 21,
    }

    return {
        "mod_name":    "imm_gen",
        "arch_name":   microarch.get("architecture", "unknown"),
        "xlen":        xlen,
        "imm_w":       imm_w,
        "imm_enc":     imm_enc,
        "imm_formats": imm_formats,
        "sign_ext":    sign_ext,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic cheatsheet — fed to the LLM for BEHAVIORAL_LOGIC modules
# ─────────────────────────────────────────────────────────────────────────────

def build_microarch_cheatsheet(microarch: dict) -> str:
    """
    Generate the dense tabular cheatsheet from microarch.yaml.
    This is the ONLY ISA context the LLM sees — all binary values are
    pre-computed by Python so the LLM cannot hallucinate them.

    ~500 tokens vs the raw JSON (~7,000 tokens).
    """
    alu_w = microarch["alu"]["width"]
    imm_w = microarch["imm_type"]["width"]
    mem_w = microarch["mem_size"]["width"]
    wb_w  = microarch["writeback"]["width"]

    header = (
        "=== MICROARCH WIRING CHEATSHEET (use ONLY these values) ===\n"
        f"{'INSTR':<8}| {'opcode':<7} | {'f3':<3} | {'f7b5':<4} "
        f"| {'alu_op':>{alu_w+5}}| {'imm':>{imm_w+3}}| {'wb':>{wb_w+3}}"
        f"| rw | mr | mw | br | jmp | alu_a  | alu_b | mem_sz"
    )
    sep = "-" * 112
    rows = [header, sep]

    for rec in microarch.get("instruction_icd", []):
        alu_bin = format(rec["alu_op"], f"0{alu_w}b") if rec["alu_op"] is not None else "N/A"
        imm_bin = format(rec["imm_type"], f"0{imm_w}b") if rec["imm_type"] is not None else "N/A"
        wb_bin  = format(rec["writeback"], f"0{wb_w}b") if rec["writeback"] is not None else "N/A"
        m_sz    = format(rec["mem_size"], f"0{mem_w}b") if rec["mem_size"] is not None else "N/A"
        f3      = rec.get("funct3") or "---"
        f7b5    = str(rec.get("funct7b5")) if rec.get("funct7b5") is not None else "-"

        rows.append(
            f"{rec['mnemonic']:<8}| {rec['opcode']:<7} | {f3:<3} | {f7b5:<4} "
            f"| {alu_w}'b{alu_bin}| {imm_w}'b{imm_bin}| {wb_w}'b{wb_bin}"
            f"| {rec['reg_write']}  | {rec['mem_read']}  | {rec['mem_write']}  "
            f"| {rec['branch']}  | {rec['jump']}   "
            f"| {str(rec.get('alu_src_a','?')):<6} | {str(rec.get('alu_src_b','?')):<5} | {wb_w}'b{m_sz}"
        )

    # Append encoding legend
    rows.append("")
    rows.append("=== ALU_OP ENCODING (canonical — alu.v and control.v MUST match) ===")
    for name, code in microarch["alu"]["encoding"].items():
        rows.append(f"  {alu_w}'b{format(code, f'0{alu_w}b')} = {name}")

    rows.append("")
    rows.append("=== IMM_TYPE ENCODING (canonical — imm_gen.v and control.v MUST match) ===")
    for name, code in microarch["imm_type"]["encoding"].items():
        rows.append(f"  {imm_w}'b{format(code, f'0{imm_w}b')} = {name}-type")

    rows.append("")
    rows.append("=== BRANCH funct3 ENCODING (canonical — branch_unit.v MUST use these) ===")
    for name, code in microarch["branch"]["encoding"].items():
        rows.append(f"  3'b{format(code, '03b')} = {name}")

    return "\n".join(rows)


# ─────────────────────────────────────────────────────────────────────────────
# RTL Generator system prompt (mirrors app.py RTL_GENERATOR_SYSTEM)
# ─────────────────────────────────────────────────────────────────────────────

RTL_GENERATOR_SYSTEM = """You are the RTL Generator Agent for a RISC-V single-cycle processor.

ARCHITECTURE MANDATE — SINGLE-CYCLE ONLY:
Every instruction completes in exactly one clock cycle. DO NOT generate:
  ✗ Pipeline stage registers (IF_ID, ID_EX, EX_MEM, MEM_WB)
  ✗ Hazard detection units, forwarding muxes, stall logic, flush signals
  ✗ Internal memory arrays (SRAM/BRAM). The CPU interfaces with external memory.

PER-MODULE PORT CONTRACTS (use EXACTLY these port names for interconnect):
  regfile    : clk, we, rs1[4:0], rs2[4:0], rd[4:0], rd_data[31:0]
               → rd1[31:0], rd2[31:0]   (x0 hardwired: write guarded by `if (rd != 0)`)
  alu        : a[31:0], b[31:0], alu_op[3:0] → result[31:0], zero
  branch_unit: branch_type[2:0], rs1[31:0], rs2[31:0], branch → taken
               CRITICAL: branch_type IS the raw RISC-V funct3 field.
               MUST guard output: taken = branch & condition_met;
  load_store : mem_read, mem_write, mem_size[1:0], mem_extend, addr[31:0], wdata[31:0], mem_rdata[31:0]
               → rdata[31:0], mem_addr[31:0], mem_wdata[31:0], mem_wstrb[3:0]
               CRITICAL: purely combinational — DO NOT add a clk port.
               mem_addr MUST be word-aligned: `mem_addr = {addr[31:2], 2'b00}`
  pc_next    : pc[31:0], imm[31:0], rs1[31:0], taken, jump, jump_type → next_pc[31:0]
               CRITICAL: if jump=1 OR taken=1, the branch is executed. Otherwise next_pc = pc + 4.
               CRITICAL: if jump=1 or taken=1, the target relies on jump_type:
                         jump_type=0 (JAL/Branch) → next_pc = pc + imm
                         jump_type=1 (JALR)       → next_pc = (rs1 + imm) & ~32'h1
               CRITICAL: jump is an essential 1-bit input! MUST use it!
  cpu        : clk, resetn, imem_rdata[31:0], dmem_rdata[31:0]
               → imem_addr[31:0], dmem_addr[31:0], dmem_wdata[31:0], dmem_wstrb[3:0], dmem_read, dmem_write
               (instantiates ALL sub-modules; NO tohost logic; NO memory arrays)

MULTIPLEXER CONTRACTS:
  alu_src_a  = 2'b00: rs1  |  2'b01: pc  |  2'b10: zero
  alu_src_b  = 1'b0: rs2   |  1'b1: imm
  result_src = 2'b00: alu  |  2'b01: mem |  2'b10: pc+4 | 2'b11: imm (LUI bypass)

STRICT LINTER RULES (Verilator --Wall):
- Use `always_comb` for combinational logic. `always_ff @(posedge clk or negedge resetn)` for sequential.
- Every `case` MUST have a `default: begin end` clause.
- Unused input bits: wrap port in `/* verilator lint_off UNUSED */` … `/* verilator lint_on UNUSED */`
- Unconnected outputs in instantiation: use `.zero()` and wrap in PINCONNECTEMPTY pragmas.
- Width mismatches on shifts: wrap in `/* verilator lint_off WIDTH */` pragmas.

SRA SYNTHESIS RULE:
  logic signed [31:0] signed_a; assign signed_a = $signed(a);
  result = signed_a >>> shamt;

Output ONLY the raw Verilog code. The very first line MUST be the `module` declaration.
NO markdown fences, NO prose, NO leading comments.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Port Contract Dictionary — exact pin names for every sub-module.
# Injected into the cpu prompt so the LLM cannot hallucinate wire names.
# ─────────────────────────────────────────────────────────────────────────────

PORT_CONTRACTS: dict[str, str] = {
    "regfile": (
        "  module regfile (\n"
        "    input  logic        clk,\n"
        "    input  logic        we,\n"
        "    input  logic [4:0]  rs1, rs2, rd,\n"
        "    input  logic [31:0] rd_data,\n"
        "    output logic [31:0] rd1, rd2\n"
        "  );"
    ),
    "imm_gen": (
        "  module imm_gen (\n"
        "    input  logic [31:0] instr,\n"
        "    input  logic [2:0]  imm_type,\n"
        "    output logic [31:0] imm\n"
        "  );"
    ),
    "alu": (
        "  module alu (\n"
        "    input  logic [31:0] a, b,\n"
        "    input  logic [3:0]  alu_op,\n"
        "    output logic [31:0] result,\n"
        "    output logic        zero\n"
        "  );"
    ),
    "branch_unit": (
        "  module branch_unit (\n"
        "    input  logic [2:0]  branch_type,\n"
        "    input  logic [31:0] rs1, rs2,\n"
        "    input  logic        branch,\n"
        "    output logic        taken\n"
        "  );"
    ),
    "load_store": (
        "  module load_store (\n"
        "    input  logic        mem_read, mem_write,\n"
        "    input  logic [1:0]  mem_size,\n"
        "    input  logic        mem_extend,\n"
        "    input  logic [31:0] addr, wdata, mem_rdata,\n"
        "    output logic [31:0] rdata, mem_addr, mem_wdata,\n"
        "    output logic [3:0]  mem_wstrb\n"
        "  );"
    ),
    "control": (
        "  module control (\n"
        "    input  logic [6:0]  opcode,\n"
        "    input  logic [2:0]  funct3,\n"
        "    input  logic        funct7b5,\n"
        "    output logic [3:0]  alu_op,\n"
        "    output logic        alu_src_b,\n"
        "    output logic [1:0]  alu_src_a,\n"
        "    output logic [1:0]  result_src,\n"
        "    output logic        reg_write,\n"
        "    output logic        mem_read, mem_write,\n"
        "    output logic [1:0]  mem_size,\n"
        "    output logic        mem_extend,\n"
        "    output logic        branch,\n"
        "    output logic [2:0]  branch_type,\n"
        "    output logic        jump, jump_type,\n"
        "    output logic [2:0]  imm_type\n"
        "  );"
    ),
    "pc_next": (
        "  module pc_next (\n"
        "    input  logic [31:0] pc, imm, rs1,\n"
        "    input  logic        taken, jump, jump_type,\n"
        "    output logic [31:0] next_pc\n"
        "  );"
    ),
}


def build_llm_prompt(module_name: str, microarch: dict) -> tuple[str, str]:
    """
    Build the (system_prompt, user_message) pair for a BEHAVIORAL_LOGIC module.

    For `cpu` (top-level), injects the full PORT_CONTRACTS dictionary so the
    LLM knows exact pin names for every sub-module — prevents hallucinated
    wire names that cause Verilator PINMISMATCH errors.

    Returns (system_prompt, user_message).
    """
    cheatsheet = build_microarch_cheatsheet(microarch)
    arch = microarch.get("architecture", "RV32I")
    xlen = microarch.get("xlen", 32)
    reset_pc = "0x00000000"

    # Base prompt — all modules get the cheatsheet
    user_msg = (
        f"Generate the Verilog module for: `{module_name}`\n"
        f"Architecture : {arch}  (XLEN={xlen}, single-cycle, no pipeline registers)\n"
        f"Reset PC     : {reset_pc}\n"
        f"Special rules: x0 hardwired to zero, jalr_lsb_clear=true\n"
        f"\n"
        f"The following cheatsheet contains ALL binary encodings derived from microarch.yaml.\n"
        f"Use these EXACT values — do NOT invent your own encodings.\n"
        f"\n"
        f"{cheatsheet}\n"
    )

    # cpu (top-level) additionally gets the exact port contracts for every
    # sub-module it must instantiate — this is the only way to guarantee
    # correct pin names in the structural DAG.
    if module_name == "cpu":
        port_section = (
            "\n"
            "=== PORT CONTRACTS — use EXACTLY these module signatures when instantiating ===\n"
            "Wire every port by name (.port_name(wire_name)). Do NOT use positional connections.\n"
            "\n"
        )
        for mod, contract in PORT_CONTRACTS.items():
            port_section += f"--- {mod} ---\n{contract}\n\n"

        port_section += (
            "=== INSTANTIATION ORDER (DAG, leaf-first) ===\n"
            "  1. regfile    (leaf — no sub-module deps)\n"
            "  2. imm_gen    (leaf)\n"
            "  3. control    (leaf — generated by Python/Jinja2)\n"
            "  4. alu        (leaf)\n"
            "  5. branch_unit (depends on control.branch output)\n"
            "  6. load_store  (leaf — combinational only)\n"
            "  7. pc_next    (depends on branch_unit.taken)\n"
            "  Wire all together in a single `cpu` module.\n"
        )
        user_msg += port_section

    user_msg += f"\nGenerate ONLY the `{module_name}` module. No testbench. No tohost logic.\n"
    return RTL_GENERATOR_SYSTEM, user_msg


# ─────────────────────────────────────────────────────────────────────────────
# Renderer engine
# ─────────────────────────────────────────────────────────────────────────────

class RTLRenderer:
    """
    Universal RTL Router.

    For each module it inspects MODULE_TIERS and dispatches to:
      - render()            → TRUTH_TABLE   (Jinja2, 0 tokens)
      - render_behavioral() → BEHAVIORAL_LOGIC (LLM + cheatsheet)
      - render_testbench()  → TESTBENCH_ONLY  (Jinja2, memory arrays)
    """

    def __init__(self, templates_dir: str = "rtl_templates"):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    # ── Tier 1: TRUTH_TABLE ──────────────────────────────────────────────────

    def is_truth_table(self, module_name: str) -> bool:
        return MODULE_TIERS.get(module_name) == TIER_TRUTH_TABLE

    def render(
        self,
        module_name: str,
        microarch: dict,
        offline_isa: dict | None = None,
        output_path: str | None = None,
    ) -> str:
        """Render a TRUTH_TABLE module via Jinja2. Zero LLM tokens."""
        if not self.is_truth_table(module_name):
            raise ValueError(
                f"Module '{module_name}' is tier={MODULE_TIERS.get(module_name)}, "
                f"not TRUTH_TABLE. Use render_behavioral() instead."
            )

        template_file = TRUTH_TABLE_TEMPLATES[module_name]

        if module_name == "control":
            context = build_control_context(microarch)
        elif module_name == "imm_gen":
            context = build_imm_gen_context(microarch, offline_isa)
        else:
            raise ValueError(f"No context builder registered for '{module_name}'")

        template = self.env.get_template(template_file)
        verilog  = template.render(**context)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(verilog)
            lines = verilog.count("\n")
            print(f"[TRUTH_TABLE] {module_name}.v → {output_path}  ({lines} lines, 0 LLM tokens)")

        return verilog

    def render_all_truth_tables(
        self,
        microarch: dict,
        offline_isa: dict | None = None,
        output_dir: str = "rtl_generated",
    ) -> dict[str, str]:
        """Render every TRUTH_TABLE module. Returns {module_name: verilog_string}."""
        results = {}
        for mod_name in TRUTH_TABLE_TEMPLATES:
            out_path = str(Path(output_dir) / f"{mod_name}.v")
            results[mod_name] = self.render(mod_name, microarch, offline_isa, out_path)
        return results

    # ── Tier 2: BEHAVIORAL_LOGIC (LLM) ──────────────────────────────────────

    def render_behavioral(
        self,
        module_name: str,
        microarch: dict,
        groq_client,
        output_path: str | None = None,
        model: str = "openai/gpt-oss-20b",
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a BEHAVIORAL_LOGIC module via the Groq LLM.

        The LLM is given ONLY the dynamic cheatsheet (not the raw JSON).
        All binary constants are pre-computed by Python.
        """
        tier = MODULE_TIERS.get(module_name)
        if tier != TIER_BEHAVIORAL_LOGIC:
            raise ValueError(
                f"Module '{module_name}' is tier={tier}, not BEHAVIORAL_LOGIC."
            )

        system_prompt, user_msg = build_llm_prompt(module_name, microarch)

        print(f"[BEHAVIORAL] {module_name}.v → calling LLM ({model})...")
        t0 = time.time()

        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_msg},
            ],
            max_tokens=max_tokens,
            temperature=0.05,   # nearly deterministic — we want exact Verilog
        )

        elapsed = time.time() - t0
        verilog_raw = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0

        # Strip markdown fences if the LLM added them despite instructions
        verilog = _strip_fences(verilog_raw)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(verilog)
            lines = verilog.count("\n")
            print(
                f"[BEHAVIORAL] {module_name}.v → {output_path}  "
                f"({lines} lines, {tokens_used} tokens, {elapsed:.1f}s)"
            )

        return verilog

    # ── Tier 3: TESTBENCH_ONLY ───────────────────────────────────────────────

    def render_testbench(
        self,
        microarch: dict,
        output_path: str | None = None,
        hex_file: str = "program.hex",
        mem_depth: int = 1024,
        tohost_addr: str = "0x80001000",
    ) -> str:
        """
        Render tb_cpu.v from tb_cpu.v.j2.
        This is the ONLY place instruction and data memory arrays exist.
        """
        template_file = TESTBENCH_TEMPLATE
        if not (self.templates_dir / template_file).exists():
            raise FileNotFoundError(
                f"Testbench template not found: {self.templates_dir / template_file}\n"
                f"Create rtl_templates/tb_cpu.v.j2 to enable testbench generation."
            )

        context = {
            "arch_name":   microarch.get("architecture", "unknown"),
            "xlen":        microarch.get("xlen", 32),
            "mem_depth":   mem_depth,
            "hex_file":    hex_file,
            "tohost_addr": tohost_addr,
            "reset_pc":    "32'h00000000",
        }

        template = self.env.get_template(template_file)
        verilog  = template.render(**context)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(verilog)
            lines = verilog.count("\n")
            print(f"[TESTBENCH]  tb_cpu.v → {output_path}  ({lines} lines, 0 LLM tokens)")

        return verilog

    # ── Top-level dispatcher ─────────────────────────────────────────────────

    def render_all(
        self,
        microarch: dict,
        groq_client=None,
        offline_isa: dict | None = None,
        output_dir: str = "rtl_generated",
        behavioral_modules: list[str] | None = None,
        skip_testbench: bool = False,
    ) -> dict[str, str]:
        """
        Run the full pipeline:
          1. All TRUTH_TABLE modules (Jinja2, 0 tokens)
          2. All requested BEHAVIORAL_LOGIC modules (LLM)
          3. Testbench (Jinja2, unless skip_testbench=True)

        Returns {module_name: verilog_string} for all generated modules.
        """
        results: dict[str, str] = {}

        # ── Tier 1: TRUTH_TABLE ───────────────────────────────────────────
        print("\n[Router] ═══ TIER 1: TRUTH_TABLE (Jinja2, 0 tokens) ═══")
        tt = self.render_all_truth_tables(microarch, offline_isa, output_dir)
        results.update(tt)

        # ── Tier 2: BEHAVIORAL_LOGIC ──────────────────────────────────────
        if behavioral_modules:
            if groq_client is None:
                raise ValueError(
                    "groq_client is required to render BEHAVIORAL_LOGIC modules. "
                    "Pass a groq.Groq() instance."
                )
            print("\n[Router] ═══ TIER 2: BEHAVIORAL_LOGIC (LLM + cheatsheet) ═══")
            for mod_name in behavioral_modules:
                tier = MODULE_TIERS.get(mod_name)
                if tier != TIER_BEHAVIORAL_LOGIC:
                    print(f"[Router] WARNING: '{mod_name}' is tier={tier}, skipping.")
                    continue
                out_path = str(Path(output_dir) / f"{mod_name}.v")
                verilog = self.render_behavioral(mod_name, microarch, groq_client, out_path)
                results[mod_name] = verilog

        # ── Tier 3: TESTBENCH ─────────────────────────────────────────────
        if not skip_testbench:
            tb_path = str(Path(output_dir) / "tb_cpu.v")
            template_path = self.templates_dir / TESTBENCH_TEMPLATE
            if template_path.exists():
                print("\n[Router] ═══ TIER 3: TESTBENCH_ONLY (Jinja2) ═══")
                verilog = self.render_testbench(microarch, tb_path)
                results["tb_cpu"] = verilog
            else:
                print(f"\n[Router] Skipping testbench — {TESTBENCH_TEMPLATE} not found yet.")

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove ```verilog ... ``` fences that the LLM adds despite instructions."""
    text = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    microarch_path = sys.argv[1] if len(sys.argv) > 1 else "microarch.yaml"
    output_dir     = sys.argv[2] if len(sys.argv) > 2 else "rtl_generated"
    module_filter  = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"[RTL Router] Loading {microarch_path}...")
    with open(microarch_path, encoding="utf-8") as f:
        microarch = yaml.safe_load(f)

    offline_isa = None
    isa_name = microarch.get("architecture", "").lower().replace(" ", "").replace("-", "")
    if "rv32i" in isa_name or "riscv32" in isa_name:
        isa_path = Path("isa_definitions") / "riscv32.json"
        if isa_path.exists():
            with open(isa_path, encoding="utf-8") as f:
                offline_isa = json.load(f)
            print(f"[RTL Router] Loaded offline ISA: {isa_path}")

    renderer = RTLRenderer(templates_dir="rtl_templates")

    if module_filter:
        tier = route_module(module_filter)
        print(f"[RTL Router] Module '{module_filter}' → tier={tier}")
        if tier == TIER_TRUTH_TABLE:
            verilog = renderer.render(module_filter, microarch, offline_isa,
                                      str(Path(output_dir) / f"{module_filter}.v"))
            print(f"\n{'='*60}")
            print(verilog)
        elif tier == TIER_BEHAVIORAL_LOGIC:
            print(f"[RTL Router] '{module_filter}' is BEHAVIORAL_LOGIC.")
            print(f"  → Use generate_cpu.py to render it via the Groq LLM.")
            print(f"\n--- Cheatsheet that will be sent to the LLM ---")
            print(build_microarch_cheatsheet(microarch))
        elif tier == TIER_TESTBENCH_ONLY:
            print(f"[RTL Router] '{module_filter}' is TESTBENCH_ONLY.")
            print(f"  → Use generate_cpu.py to render tb_cpu.v.")
    else:
        print(f"\n[RTL Router] Module tier manifest:")
        for name, tier in MODULE_TIERS.items():
            print(f"  {name:<14} → {tier}")

        print(f"\n[RTL Router] Rendering TRUTH_TABLE modules → {output_dir}/")
        results = renderer.render_all_truth_tables(microarch, offline_isa, output_dir)
        print(f"\n[RTL Router] Done. Generated {len(results)} TRUTH_TABLE modules:")
        for name, code in results.items():
            lines = code.count("\n")
            print(f"  {name}.v : {lines} lines")
        print(f"\n[Token cost: 0. TRUTH_TABLE rendered from microarch.yaml.]")
        print(f"\n[RTL Router] To generate BEHAVIORAL_LOGIC modules (alu, branch_unit, cpu),")
        print(f"  run:  python generate_cpu.py")
