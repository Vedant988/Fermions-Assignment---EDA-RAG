"""
systems_engineer.py — Stage 2: Pure Python MicroarchBuilder
============================================================
Takes:
  - isa_facts.json   (behavioral facts from Stage 1 Researcher Agent)
  - isa_definitions/riscv32.json  (offline physical constants — zero LLM tokens)

Produces:
  - microarch.yaml   (golden Interface Control Document)

NO LLM calls. NO hardcoded binary strings. ALL math is deterministic Python.
"""

from __future__ import annotations
import json
import yaml
from math import ceil, log2
from pathlib import Path
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _min_bits(n: int) -> int:
    """Minimum bits to represent n distinct values (minimum 1)."""
    return max(1, ceil(log2(max(n, 2))))


def _seq_encoding(items: list[str]) -> dict[str, int]:
    """Assign sequential non-overlapping integers to a list of unique items."""
    seen = {}
    result = {}
    for item in items:
        if item in seen:
            continue
        seen[item] = True
        result[item] = len(result)
    return result


def _binary_str(value: int, width: int) -> str:
    """Format integer as binary string with leading zeros."""
    return format(value, f'0{width}b')


# ── Offline ISA Loader ────────────────────────────────────────────────────────

def load_offline_isa(isa_name: str, definitions_dir: str = "isa_definitions") -> dict:
    """
    Load physical ISA constants from a local JSON file.
    These are immutable architectural facts that NEVER get sent to an LLM.
    """
    path = Path(definitions_dir) / f"{isa_name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No offline ISA definition for '{isa_name}'. "
            f"Expected: {path}\n"
            f"Add a '{isa_name}.json' to '{definitions_dir}/' to support this architecture."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── MicroarchBuilder ──────────────────────────────────────────────────────────

class MicroarchBuilder:
    """
    Converts behavioral ISA facts + offline physical constants into a
    deterministic, mathematically-sound microarch.yaml (Interface Control Document).

    This is the core of the Hybrid Thinking Pipeline:
      - LLM extracts WHAT operations exist (Stage 1)
      - Python decides HOW WIDE the wires are and WHICH BINARY CODE each operation gets
    """

    def __init__(self, isa_facts: dict, offline_isa: dict):
        self.facts = isa_facts
        self.offline = offline_isa

    # ── Public API ────────────────────────────────────────────────────────────

    def build(self) -> dict:
        """Build and return the complete microarch dict."""
        alu_ops   = self.facts.get("alu_operations", [])
        mem_sizes = self.facts.get("memory_sizes", [])
        imm_fmts  = self.facts.get("immediate_formats", [])
        wb_srcs   = self.facts.get("writeback_sources", [])
        br_conds  = self.facts.get("branch_conditions", [])
        
        # Throw errors if Stage 1 failed to list them
        if not alu_ops: raise ValueError("Missing 'alu_operations'. The Stage 1 LLM may have rate-limited or hallucinated invalid JSON.")
        if not mem_sizes: raise ValueError("Missing 'memory_sizes' from Stage 1 facts. Ensure Stage 1 succeeded.")
        if not imm_fmts: raise ValueError("Missing 'immediate_formats' from Stage 1 facts. Ensure Stage 1 succeeded.")
        if not wb_srcs: raise ValueError("Missing 'writeback_sources' from Stage 1 facts. Ensure Stage 1 succeeded.")
        if not br_conds: raise ValueError("Missing 'branch_conditions' from Stage 1 facts. Ensure Stage 1 succeeded.")

        # Step 1: Compute bus widths from counts
        alu_width = _min_bits(len(alu_ops))
        mem_width = _min_bits(len(mem_sizes))
        imm_width = _min_bits(len(imm_fmts) + 1)   # +1 for "N/A" slot
        wb_width  = _min_bits(len(wb_srcs))

        # Step 2: Assign non-overlapping binary encodings
        alu_enc = _seq_encoding(alu_ops)
        mem_enc = _seq_encoding(mem_sizes)
        imm_enc = _seq_encoding(imm_fmts)   # I=0, S=1, B=2, U=3, J=4
        wb_enc  = _seq_encoding(wb_srcs)

        # Step 3: Branch encoding — use funct3 from offline ISA spec (these ARE the wire values)
        br_enc = self._build_branch_encoding(br_conds)

        # Step 4: Merge offline opcodes + behavioral facts into per-instruction ICD
        icd = self._build_instruction_icd(alu_enc, imm_enc, wb_enc, mem_enc, br_enc)

        # Step 5: Validate — catch collisions before they reach RTL
        self._validate_icd(icd)

        microarch = {
            "architecture": self.offline.get("name", "unknown"),
            "xlen": self.offline.get("xlen", 32),
            "num_registers": self.offline.get("num_registers", 32),
            "special_rules": self.facts.get("special_rules", {}),
            "alu": {
                "width": alu_width,
                "encoding": {k: v for k, v in alu_enc.items()},
                "binary": {k: _binary_str(v, alu_width) for k, v in alu_enc.items()},
            },
            "mem_size": {
                "width": mem_width,
                "encoding": {k: v for k, v in mem_enc.items()},
                "binary": {k: _binary_str(v, mem_width) for k, v in mem_enc.items()},
            },
            "imm_type": {
                "width": imm_width,
                "encoding": {k: v for k, v in imm_enc.items()},
                "binary": {k: _binary_str(v, imm_width) for k, v in imm_enc.items()},
            },
            "writeback": {
                "width": wb_width,
                "encoding": {k: v for k, v in wb_enc.items()},
                "binary": {k: _binary_str(v, wb_width) for k, v in wb_enc.items()},
            },
            "branch": {
                "encoding": br_enc,
                "binary": {k: _binary_str(v, 3) for k, v in br_enc.items()},
            },
            "instruction_icd": icd,
        }

        return microarch

    def save(self, microarch: dict, output_path: str = "microarch.yaml"):
        """Write the microarch dict to a YAML file."""
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(microarch, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"[OK] microarch.yaml written -> {output_path}")

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _build_branch_encoding(self, br_conds: list[str]) -> dict[str, int]:
        """
        Map branch condition names to their binary values.
        For RISC-V, branch funct3 IS the wire value (not sequential).
        For unknown architectures, assign sequentially as fallback.
        """
        # Use offline ISA funct3 values for branch instructions (the RISC-V way)
        rv_branch_funct3 = {}
        for instr in self.offline.get("instructions", []):
            if instr.get("format") == "B" and instr.get("funct3"):
                # Map mnemonic → integer value of funct3
                rv_branch_funct3[instr["mnemonic"]] = int(instr["funct3"], 2)

        # Map requested condition names to funct3 values
        COND_TO_MNEMONIC = {
            "EQ": "BEQ", "NE": "BNE", "LT": "BLT",
            "GE": "BGE", "LTU": "BLTU", "GEU": "BGEU",
        }
        result = {}
        for cond in br_conds:
            mnemonic = COND_TO_MNEMONIC.get(cond.upper())
            if mnemonic and mnemonic in rv_branch_funct3:
                result[cond] = rv_branch_funct3[mnemonic]
            else:
                # Fallback: assign sequentially (for non-RISC-V ISAs)
                result[cond] = len(result)
        return result

    def _build_instruction_icd(
        self,
        alu_enc: dict,
        imm_enc: dict,
        wb_enc: dict,
        mem_enc: dict,
        br_enc: dict,
    ) -> list[dict]:
        """
        Build the per-instruction Interface Control Document.
        Opcodes/funct3 come from offline JSON.
        ALU/IMM/WB codes come from Python-computed encodings.
        """
        # 1. Build a fast lookup: Mnemonic -> Behavioral Record (From Stage 1 LLM)
        behav_lookup = {
            rec["mnemonic"].upper(): rec 
            for rec in self.facts.get("instruction_records", [])
        }

        icd = []
        # 2. Loop through the Physical Constants (From Stage 0 Offline JSON)
        for instr in self.offline.get("instructions", []):
            mnemonic = instr["mnemonic"].upper()
            
            # If the LLM didn't figure out what this instruction does, fail loudly!
            if mnemonic not in behav_lookup:
                raise ValueError(f"Missing behavioral facts for instruction: {mnemonic}")
            
            behav = behav_lookup[mnemonic]
            fmt = instr.get("format", "")

            # 3. DYNAMIC MAPPING (Zero Hardcoding)
            # Match the format from Stage 0 to the Immediate Encodings we calculated
            imm_code = imm_enc.get(fmt) 

            # Map the LLM's behavioral strings to the Python-calculated binary integers
            alu_code = alu_enc.get(behav.get("alu_op", "ADD"), 0)
            wb_code = wb_enc.get(behav.get("writeback", "ALU"), 0)
            mem_sz_code = mem_enc.get(behav.get("mem_size")) if behav.get("mem_size") else None

            # 4. Merge Physical + Behavioral + Binary
            record = {
                "mnemonic": mnemonic,
                "format": fmt,
                "opcode": instr["opcode"],
                "funct3": instr.get("funct3"),
                "funct7b5": instr.get("funct7b5"),
                
                # Binary Encodings (For Jinja2 Truth Tables)
                "alu_op": alu_code,
                "imm_type": imm_code,
                "writeback": wb_code,
                "mem_size": mem_sz_code,
                
                # Behavioral Flags (For the LLM Cheatsheet)
                "alu_src_a": behav.get("alu_src_a", "rs1"),
                "alu_src_b": behav.get("alu_src_b", "rs2"),
                "reg_write": int(bool(behav.get("reg_write", False))),
                "mem_read": int(bool(behav.get("mem_read", False))),
                "mem_write": int(bool(behav.get("mem_write", False))),
                "branch": int(bool(behav.get("branch", False))),
                "jump": int(bool(behav.get("jump", False))),
                
                # Pass-through rules
                "mem_extend": behav.get("mem_extend"),
                "jump_type": behav.get("jump_type"),
                "special": behav.get("special_rules", {})
            }
            icd.append(record)
            
        return icd

    def _validate_icd(self, icd: list[dict]):
        """
        Sanity checks — catch design errors before Verilog is generated.
        Raises ValueError with a clear message if any check fails.
        """
        # Check 1: No two entries have the same (opcode, funct3, funct7b5) — would cause overlapping decoder
        seen_keys: dict[tuple, str] = {}
        for rec in icd:
            key = (rec["opcode"], rec.get("funct3"), rec.get("funct7b5"))
            if key in seen_keys:
                raise ValueError(
                    f"[COLLISION] {rec['mnemonic']} and {seen_keys[key]} share the same "
                    f"opcode={rec['opcode']}, funct3={rec.get('funct3')}, funct7b5={rec.get('funct7b5')}. "
                    f"This would create unreachable Verilog case arms."
                )
            seen_keys[key] = rec["mnemonic"]

        print(f"[OK] ICD validation passed: {len(icd)} instructions, 0 collisions.")


# ── CLI entry point ───────────────────────────────────────────────────────────

def build_from_files(
    isa_name: str = "riscv32",
    facts_path: str | None = None,
    output_path: str = "microarch.yaml",
    definitions_dir: str = "isa_definitions",
) -> dict:
    """
    Build microarch.yaml from an offline ISA definition + optional isa_facts.json.
    """
    offline_isa = load_offline_isa(isa_name, definitions_dir)

    if not facts_path:
        raise ValueError("A path to a valid Stage 1 isa_facts.json must be provided!")

    with open(facts_path, encoding="utf-8") as f:
        isa_facts = json.load(f)

    builder = MicroarchBuilder(isa_facts, offline_isa)
    microarch = builder.build()
    builder.save(microarch, output_path)
    return microarch


def microarch_to_cheatsheet(microarch: dict) -> str:
    """
    Generate the dynamic ISA cheatsheet from microarch.yaml.
    This replaces build_isa_cheatsheet() in app.py — now fully generic.
    """
    alu_w  = microarch["alu"]["width"]
    imm_w  = microarch["imm_type"]["width"]
    mem_w  = microarch["mem_size"]["width"]
    wb_w   = microarch["writeback"]["width"]

    header = (
        "=== MICROARCH WIRING CHEATSHEET (use ONLY these values) ===\n"
        f"{'INSTR':<8}| {'opcode':<7} | {'f3':<3} | {'f7b5':<4} "
        f"| {'alu_op':>{alu_w+5}}| {'imm':>{imm_w+3}}| {'wb':>{wb_w+3}}"
        f"| rw | mr | mw | br | jmp | alu_a  | alu_b | mem_sz"
    )
    sep = "-" * 110
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

    return "\n".join(rows)


if __name__ == "__main__":
    import sys
    isa_name = sys.argv[1] if len(sys.argv) > 1 else "riscv32"
    facts_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_path = sys.argv[3] if len(sys.argv) > 3 else "microarch.yaml"
    microarch = build_from_files(isa_name, facts_path, output_path)

    print("\n=== Generated Cheatsheet ===")
    print(microarch_to_cheatsheet(microarch))
