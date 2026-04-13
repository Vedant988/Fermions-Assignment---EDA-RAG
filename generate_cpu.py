"""
generate_cpu.py — Full RV32I CPU Generation Pipeline
=====================================================
Runs the complete three-tier RTL generation flow from a single command:

  python generate_cpu.py [microarch.yaml] [output_dir] [--behavioral-only] [--lint-only]

Tier 1  TRUTH_TABLE       control.v, imm_gen.v         0 LLM tokens  (Jinja2)
Tier 2  BEHAVIORAL_LOGIC  regfile, alu, branch_unit,   LLM + cheatsheet
                          load_store, pc_next, cpu
Tier 3  TESTBENCH_ONLY    tb_cpu.v                      0 LLM tokens  (Jinja2)

Then runs Verilator lint on all generated files and prints a pass/fail summary.
"""

from __future__ import annotations
import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Build order: regfile and pc_next are explicitly included.
# ORDER MATTERS — cpu must come last (depends on all others).
# ─────────────────────────────────────────────────────────────────────────────

BEHAVIORAL_BUILD_ORDER: list[str] = [
    "regfile",      # sequential: 32×32 RF, x0 hardwired — needs always_ff + reset logic
    "alu",          # combinational: ADD/SUB/AND/OR/XOR/SLL/SRL/SRA/SLT/SLTU + SRA signed-intermediate
    "branch_unit",  # combinational: BEQ/BNE/BLT/BGE/BLTU/BGEU — MUST use raw funct3 values
    "load_store",   # combinational: byte-lane masking, word-aligned addr, signed/unsigned extend
    "pc_next",      # combinational: PC+4 | PC+imm | rs1+imm&~1 — sequential PC reg lives in cpu
    "cpu",          # structural: instantiates ALL above + control + imm_gen — last always
]


def _groq_client():
    """Create and return a Groq client from GROQ_API_KEY env var."""
    try:
        from groq import Groq
    except ImportError:
        print("[ERROR] groq package not found. Run: pip install groq")
        sys.exit(1)

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] GROQ_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)
    return Groq(api_key=api_key)


def run_verilator_lint(rtl_files: list[Path]) -> tuple[bool, str]:
    """
    Run Verilator lint-only on the given list of .v files.
    Returns (passed: bool, output: str).
    """
    try:
        result = subprocess.run(
            ["verilator", "--lint-only", "--Wall", "-sv", "-Wno-TIMESCALEMOD", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-PINMISSING", "-Wno-STMTDLY"] + [str(f) for f in rtl_files],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return passed, output
    except FileNotFoundError:
        return False, "[Verilator not found — install with: sudo apt install verilator]"
    except subprocess.TimeoutExpired:
        return False, "[Verilator timed out after 60s]"


def print_summary(results: dict[str, str], lint_passed: bool | None, lint_output: str, elapsed: float):
    """Print a clean terminal summary."""
    print("\n" + "═" * 65)
    print("  RV32I CPU Generation Summary")
    print("═" * 65)
    print(f"  {'Module':<14}  {'File':<24}  Lines")
    print(f"  {'-'*14}  {'-'*24}  -----")
    for name, verilog in results.items():
        lines = verilog.count("\n")
        tier_tag = (
            "[Jinja2]" if name in ("control", "imm_gen", "tb_cpu")
            else "[LLM]   "
        )
        print(f"  {name:<14}  {name+'.v':<24}  {lines}  {tier_tag}")
    print(f"\n  Total modules : {len(results)}")
    print(f"  Elapsed       : {elapsed:.1f}s")
    print(f"  LLM tokens    : (see output above)")

    if lint_passed is None:
        print(f"\n  Verilator     : [skipped]")
    elif lint_passed:
        print(f"\n  ✅  Verilator  : PASS — 0 errors")
    else:
        print(f"\n  ❌  Verilator  : FAIL")
        for line in lint_output.splitlines():
            print(f"    {line}")
    print("═" * 65 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete RV32I single-cycle CPU from microarch.yaml"
    )
    parser.add_argument("microarch",    nargs="?", default="microarch.yaml",
                        help="Path to microarch.yaml (default: microarch.yaml)")
    parser.add_argument("output_dir",   nargs="?", default="rtl_generated",
                        help="Output directory for .v files (default: rtl_generated)")
    parser.add_argument("--behavioral-only", action="store_true",
                        help="Skip TRUTH_TABLE and testbench; only run LLM modules")
    parser.add_argument("--lint-only",  action="store_true",
                        help="Skip generation; only lint existing rtl_generated/ files")
    parser.add_argument("--module",     type=str, default=None,
                        help="Generate a single specific module (e.g. --module alu)")
    parser.add_argument("--no-lint",    action="store_true",
                        help="Skip Verilator lint step")
    parser.add_argument("--model",      type=str, default="openai/gpt-oss-20b",
                        help="Groq model to use for BEHAVIORAL_LOGIC modules")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load microarch.yaml ───────────────────────────────────────────────────
    print(f"[Pipeline] Loading {args.microarch}...")
    with open(args.microarch, encoding="utf-8") as f:
        microarch = yaml.safe_load(f)
    arch = microarch.get("architecture", "unknown")
    print(f"[Pipeline] Architecture: {arch}")

    # ── Load offline ISA (for imm_gen context) ───────────────────────────────
    offline_isa = None
    isa_name = arch.lower().replace(" ", "").replace("-", "")
    if "rv32i" in isa_name or "riscv32" in isa_name:
        isa_path = Path("isa_definitions") / "riscv32.json"
        if isa_path.exists():
            with open(isa_path, encoding="utf-8") as f:
                offline_isa = json.load(f)
            print(f"[Pipeline] Loaded offline ISA: {isa_path}")

    # ── Import renderer ───────────────────────────────────────────────────────
    from rtl_renderer import RTLRenderer, BEHAVIORAL_LOGIC_MODULES_SET

    renderer  = RTLRenderer(templates_dir="rtl_templates")
    t_start   = time.time()
    results   = {}

    # ── Lint-only shortcut ────────────────────────────────────────────────────
    if args.lint_only:
        print("[Pipeline] --lint-only: scanning existing files...")
        rtl_files = sorted(output_dir.glob("*.v"))
        if not rtl_files:
            print(f"[Pipeline] No .v files found in {output_dir}/")
            sys.exit(1)
        print(f"[Pipeline] Linting {len(rtl_files)} files...")
        passed, lint_out = run_verilator_lint(rtl_files)
        print_summary({f.stem: open(f).read() for f in rtl_files},
                      passed, lint_out, time.time() - t_start)
        sys.exit(0 if passed else 1)

    # ── Single-module shortcut ────────────────────────────────────────────────
    if args.module:
        from rtl_renderer import route_module, TIER_TRUTH_TABLE, TIER_BEHAVIORAL_LOGIC
        mod = args.module
        tier = route_module(mod)
        print(f"[Pipeline] Single-module mode: {mod} (tier={tier})")

        if tier == TIER_TRUTH_TABLE:
            verilog = renderer.render(mod, microarch, offline_isa,
                                     str(output_dir / f"{mod}.v"))
            results[mod] = verilog
        elif tier == TIER_BEHAVIORAL_LOGIC:
            client = _groq_client()
            verilog = renderer.render_behavioral(mod, microarch, client,
                                                 str(output_dir / f"{mod}.v"),
                                                 model=args.model)
            results[mod] = verilog
        else:
            print(f"[Pipeline] '{mod}' is TESTBENCH_ONLY — use --no-lint with full run.")
            sys.exit(0)

        elapsed = time.time() - t_start
        print_summary(results, None, "", elapsed)
        sys.exit(0)

    # ── Full pipeline ─────────────────────────────────────────────────────────

    # Step 1 — TRUTH_TABLE (Jinja2, 0 tokens)
    if not args.behavioral_only:
        print("\n[Step 1] ── TRUTH_TABLE modules (Jinja2, 0 tokens) ──")
        tt = renderer.render_all_truth_tables(microarch, offline_isa, str(output_dir))
        results.update(tt)
    else:
        print("[Step 1] Skipped (--behavioral-only)")

    # Step 2 — BEHAVIORAL_LOGIC (LLM + cheatsheet)
    print("\n[Step 2] ── BEHAVIORAL_LOGIC modules (LLM + cheatsheet) ──")
    client = _groq_client()

    build_order = BEHAVIORAL_BUILD_ORDER
    for mod_name in build_order:
        out_path = str(output_dir / f"{mod_name}.v")
        verilog = renderer.render_behavioral(
            mod_name, microarch, client, out_path, model=args.model
        )
        results[mod_name] = verilog
        # Small pause to respect rate limits between modules
        time.sleep(1.0)

    # Step 3 — TESTBENCH (Jinja2, memory arrays here only)
    if not args.behavioral_only:
        print("\n[Step 3] ── TESTBENCH (Jinja2) ──")
        tb_path = str(output_dir / "tb_cpu.v")
        tb_template = Path("rtl_templates") / "tb_cpu.v.j2"
        if tb_template.exists():
            verilog = renderer.render_testbench(microarch, tb_path)
            results["tb_cpu"] = verilog
        else:
            print(f"[Step 3] tb_cpu.v.j2 not found — skipping testbench.")

    # Step 4 — Verilator lint
    lint_passed, lint_out = None, ""
    if not args.no_lint:
        print("\n[Step 4] ── Verilator lint ──")
        # Lint core modules only (exclude tb_cpu which needs a top-level wrapper)
        core_files = [
            output_dir / f"{m}.v"
            for m in ["control", "imm_gen", "regfile", "alu",
                      "branch_unit", "load_store", "pc_next", "cpu"]
            if (output_dir / f"{m}.v").exists()
        ]
        if core_files:
            lint_passed, lint_out = run_verilator_lint(core_files)
            if lint_passed:
                print("[Verilator] PASS — 0 errors")
            else:
                print("[Verilator] FAIL:")
                print(lint_out)
        else:
            print("[Verilator] No core files found to lint.")
    else:
        print("\n[Step 4] Skipped (--no-lint)")

    elapsed = time.time() - t_start
    print_summary(results, lint_passed, lint_out, elapsed)
    sys.exit(0 if (lint_passed is None or lint_passed) else 1)


if __name__ == "__main__":
    main()
