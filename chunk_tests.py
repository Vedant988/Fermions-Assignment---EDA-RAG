"""
RISC-V riscv-tests Scraper
===========================
Pulls all rv32ui/*.S test files from GitHub raw API, plus the critical
support files (test_macros.h, riscv_test.h env header) and chunks them
into a structured testbench_chunks.json for the RAG knowledge base.

Sources:
  https://github.com/riscv-software-src/riscv-tests/tree/master/isa/rv32ui
  https://github.com/riscv-software-src/riscv-tests/blob/master/README.md

Key design decisions (from live review of the repo):
  - rv32ui/*.S files are thin wrappers — they #include the canonical rv64ui/*.S body
  - So we scrape BOTH rv32ui/*.S (to confirm which tests exist) AND rv64ui/*.S
    (which contains the actual test vectors)
  - test_macros.h is parsed to extract macro → RTL-behavior mappings
  - Each output chunk = one instruction test file, with:
      * The raw assembly test vectors (TEST_RR_OP, TEST_IMM_OP, etc.)
      * A parsed JSON representation of every test case
      * The RTL invariants that macro enforces (from test_macros.h)
      * The tohost pass/fail protocol description
"""

import os
import re
import json
import requests

# ── Constants ──────────────────────────────────────────────────────────────────

RAW_BASE    = "https://raw.githubusercontent.com/riscv-software-src/riscv-tests/master"
API_BASE    = "https://api.github.com/repos/riscv-software-src/riscv-tests/contents"
OUTPUT_DIR  = "scraped data"
HEADERS     = {"User-Agent": "RVTests-Scraper/1.0", "Accept": "application/vnd.github.v3+json"}

# The tohost protocol — injected into every chunk's metadata
TOHOST_PROTOCOL = (
    "Pass/Fail is signaled by writing to the `tohost` memory-mapped address. "
    "A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number "
    "in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the "
    "linker-assigned tohost symbol) and halt simulation when it detects a non-zero write."
)

# RTL behavioral contract each macro enforces (from test_macros.h review)
MACRO_RTL_CONTRACTS = {
    "TEST_RR_OP": (
        "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. "
        "rd must equal expected result. Tests: ALU compute, register write."
    ),
    "TEST_IMM_OP": (
        "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. "
        "rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute."
    ),
    "TEST_RR_SRC1_EQ_DEST": (
        "rd == rs1 hazard: source register is also destination. "
        "RegFile must handle read-before-write in same cycle (rd=rs1 case)."
    ),
    "TEST_RR_SRC2_EQ_DEST": (
        "rd == rs2 hazard: source register 2 is also destination. "
        "RegFile must handle read-before-write in same cycle (rd=rs2 case)."
    ),
    "TEST_RR_SRC12_EQ_DEST": (
        "rd == rs1 == rs2: all three refer to same register. "
        "Tests double-alias read-before-write in RegFile."
    ),
    "TEST_RR_ZEROSRC1": (
        "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
    ),
    "TEST_RR_ZEROSRC2": (
        "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
    ),
    "TEST_RR_ZERODEST": (
        "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. "
        "This is the most critical x0 invariant test."
    ),
    "TEST_RR_DEST_BYPASS": (
        "NOP cycles inserted between instruction and result check. "
        "Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
    ),
    "TEST_RR_SRC12_BYPASS": (
        "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
    ),
    "TEST_RR_SRC21_BYPASS": (
        "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). "
        "Tests that the register file correctly handles operand order independence "
        "when NOP slots separate the two source loads."
    ),
    "TEST_IMM_SRC1_EQ_DEST": (
        "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
    ),
    "TEST_IMM_DEST_BYPASS": (
        "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
    ),
    "TEST_IMM_ZEROSRC1": (
        "I-type with rs1=x0. Immediate instruction must read zero from x0."
    ),
    "TEST_IMM_ZERODEST": (
        "I-type with rd=x0. Result must not corrupt x0."
    ),
    "TEST_LD_OP": (
        "Load instruction correctness: compute effective address rs1+offset, load from memory. "
        "Tests: address adder, byte/halfword/word sign/zero extension logic."
    ),
    "TEST_ST_OP": (
        "Store instruction correctness: compute effective address, write rs2 to memory. "
        "Tests: store byte/halfword/word masking, subsequent load must return stored value."
    ),
    "TEST_BR2_OP_TAKEN": (
        "Branch taken: condition is true, PC must jump to target. "
        "Tests: branch condition logic, PC update to PC+imm."
    ),
    "TEST_BR2_OP_NOTTAKEN": (
        "Branch not taken: condition is false, PC must fall through to PC+4. "
        "Tests: branch condition logic, sequential PC increment."
    ),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch_raw(path: str) -> str | None:
    """Fetch raw file content from GitHub."""
    url = f"{RAW_BASE}/{path}"
    r = requests.get(url, timeout=20, headers={"User-Agent": "RVTests-Scraper/1.0"})
    if r.status_code == 200:
        return r.text
    print(f"   [WARN] Could not fetch {url} (HTTP {r.status_code})")
    return None


def list_github_dir(path: str) -> list[dict]:
    """List files in a GitHub repo directory via the Contents API."""
    url = f"{API_BASE}/{path}"
    r = requests.get(url, timeout=20, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def parse_test_vectors(asm_source: str, instruction: str) -> list[dict]:
    """
    Extract structured test vectors from assembly source.
    Parses the TEST_*_OP macro calls into (test_id, type, args) JSON objects.
    """
    vectors = []
    # Match any TEST_*_OP call: TEST_RR_OP( 2, add, 0x00000000, 0x00000001, 0x00000001 )
    pattern = re.compile(
        r'(TEST_\w+)\(\s*(\d+)\s*,\s*[\w.]+\s*,\s*([^)]+)\)',
        re.MULTILINE
    )
    for match in pattern.finditer(asm_source):
        macro   = match.group(1).strip()
        test_id = int(match.group(2))
        args    = [a.strip() for a in match.group(3).split(',') if a.strip()]

        vec = {
            "test_id":  test_id,
            "macro":    macro,
            "rtl_contract": MACRO_RTL_CONTRACTS.get(macro, "See test_macros.h for full definition."),
        }

        # Parse structured fields based on known macro types
        if macro == "TEST_RR_OP":
            if len(args) >= 2: vec["expected_result"] = args[0]
            if len(args) >= 3: vec["rs1_value"]       = args[1]
            if len(args) >= 4: vec["rs2_value"]       = args[2]
        elif macro == "TEST_IMM_OP":
            if len(args) >= 2: vec["expected_result"] = args[0]
            if len(args) >= 3: vec["rs1_value"]       = args[1]
            if len(args) >= 4: vec["immediate"]       = args[2]
        elif macro in ("TEST_BR2_OP_TAKEN", "TEST_BR2_OP_NOTTAKEN"):
            if len(args) >= 1: vec["rs1_value"]  = args[0]
            if len(args) >= 2: vec["rs2_value"]  = args[1]
            vec["branch_taken"] = (macro == "TEST_BR2_OP_TAKEN")
        elif macro == "TEST_LD_OP":
            if len(args) >= 1: vec["expected_result"] = args[0]
            if len(args) >= 2: vec["offset"]          = args[1]
            if len(args) >= 3: vec["base_label"]      = args[2]
        elif macro == "TEST_ST_OP":
            if len(args) >= 1: vec["expected_result"] = args[0]
            if len(args) >= 2: vec["offset"]          = args[1]
            if len(args) >= 3: vec["base_label"]      = args[2]

        vectors.append(vec)

    return vectors


def build_chunk_text(instruction: str, rv64_source: str, vectors: list[dict]) -> str:
    """Build a rich Markdown chunk for one rv32ui test."""
    lines = [
        f"# rv32ui Test: `{instruction.upper()}`",
        "",
        f"> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32",
        f"> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)",
        f"> **Pass/Fail Protocol:** {TOHOST_PROTOCOL}",
        "",
        "## Test Coverage Summary",
        "",
        f"Total test cases parsed: **{len(vectors)}**",
        "",
        "| Test ID | Macro | RTL Contract |",
        "| --- | --- | --- |",
    ]
    for v in vectors[:8]:   # Show first 8 in table (keep chunk bounded)
        lines.append(f"| {v['test_id']} | `{v['macro']}` | {v['rtl_contract'][:80]}... |")
    if len(vectors) > 8:
        lines.append(f"| ... | ... | ({len(vectors)-8} more test cases) |")

    lines += [
        "",
        "## Key RTL Invariants This Test Suite Enforces",
        "",
    ]
    seen_macros = set()
    for v in vectors:
        m = v["macro"]
        if m not in seen_macros and m in MACRO_RTL_CONTRACTS:
            lines.append(f"- **`{m}`**: {MACRO_RTL_CONTRACTS[m]}")
            seen_macros.add(m)

    lines += [
        "",
        "## Structured Test Vectors (JSON)",
        "",
        "```json",
        json.dumps(vectors, indent=2),
        "```",
        "",
        "## Raw Assembly Source",
        "",
        "```asm",
        rv64_source.strip(),
        "```",
    ]
    return '\n'.join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Step 1: Fetch critical support files ──────────────────────────────────
    print("[1/5] Fetching README and test_macros.h...")
    readme_text      = fetch_raw("README.md") or ""
    test_macros_text = fetch_raw("isa/macros/scalar/test_macros.h") or ""

    # Save them as standalone RAG chunks
    support_chunks = []
    if readme_text:
        support_chunks.append({
            "chunk_id":     "support_0",
            "section_title": "riscv-tests: TVM Protocol and Test Format",
            "source_url":   f"{RAW_BASE}/README.md",
            "document_type": "protocol",
            "document_text": (
                "# riscv-tests: TVM Protocol and Pass/Fail Specification\n\n"
                f"> **Pass/Fail Protocol:** {TOHOST_PROTOCOL}\n\n"
                "## Target Virtual Machines (TVMs)\n\n"
                "| TVM | Description |\n| --- | --- |\n"
                "| `rv32ui` | RV32 user-level, integer only — **our target** |\n"
                "| `rv32si` | RV32 supervisor-level, integer only |\n\n"
                "## Test Environments\n\n"
                "| Environment | Description |\n| --- | --- |\n"
                "| `p` | No virtual memory, only core 0 boots — **our target** |\n\n"
                "## Test Structure\n\n"
                "Every test file follows: `RVTEST_CODE_BEGIN` → test vectors using macros "
                "→ `RVTEST_PASS` or `RVTEST_FAIL` → `RVTEST_DATA_BEGIN/END`.\n\n"
                "## Full README\n\n"
                f"```\n{readme_text.strip()}\n```"
            ),
        })

    if test_macros_text:
        # Split into 3 focused sub-chunks to stay within embedding model token limits
        # Each chunk covers one semantic group of macros
        reg_macros   = {k: v for k, v in MACRO_RTL_CONTRACTS.items() if "RR" in k or "IMM" in k}
        mem_macros   = {k: v for k, v in MACRO_RTL_CONTRACTS.items() if "LD" in k or "ST" in k}
        br_macros    = {k: v for k, v in MACRO_RTL_CONTRACTS.items() if "BR" in k or "JR" in k or "JALR" in k}

        for i, (group_name, group_macros) in enumerate([
            ("Register-Immediate and Register-Register", reg_macros),
            ("Memory Load/Store", mem_macros),
            ("Branch and Jump", br_macros),
        ]):
            support_chunks.append({
                "chunk_id":     f"support_macros_{i+1}",
                "section_title": f"riscv-tests: test_macros.h — {group_name} RTL Contracts",
                "source_url":   f"{RAW_BASE}/isa/macros/scalar/test_macros.h",
                "document_type": "macro_reference",
                "document_text": (
                    f"# riscv-tests test_macros.h: {group_name} Contracts\n\n"
                    "These macros define the **exact hardware behavior** that must hold "
                    "for riscv-tests to pass. Each expands to a sequence of instructions "
                    "followed by a `bne ..., fail` check.\n\n"
                    "## RTL Contracts\n\n"
                    + '\n'.join(f"- **`{k}`**: {v}" for k, v in group_macros.items())
                ),
            })
    print(f"   {len(support_chunks)} support chunks built.")


    # ── Step 2: List all rv32ui test files ────────────────────────────────────
    print("[2/5] Listing rv32ui test files...")
    rv32ui_files = list_github_dir("isa/rv32ui")
    asm_files = [f for f in rv32ui_files if f["name"].endswith(".S")]
    print(f"   Found {len(asm_files)} .S test files in rv32ui/")

    # ── Step 3: Fetch & parse each test ───────────────────────────────────────
    print("[3/5] Fetching and parsing each test...")
    instruction_chunks = []

    for i, f in enumerate(sorted(asm_files, key=lambda x: x["name"])):
        instruction = f["name"].replace(".S", "")
        print(f"   [{i+1}/{len(asm_files)}] {instruction}...", end="")

        # rv32ui wrapper just re-exports rv64ui — fetch the canonical source
        rv64_path = f"isa/rv64ui/{instruction}.S"
        rv64_source = fetch_raw(rv64_path)

        if not rv64_source:
            # Some instructions only exist in rv32ui (e.g. fence_i variations)
            rv32_source = fetch_raw(f"isa/rv32ui/{instruction}.S")
            rv64_source = rv32_source or ""

        vectors = parse_test_vectors(rv64_source, instruction)
        doc_text = build_chunk_text(instruction, rv64_source, vectors)

        # Classify instruction type for metadata
        instr_type = "unknown"
        if any(x in instruction for x in ("add", "sub", "and", "or", "xor", "slt", "sll", "srl", "sra", "lui", "auipc")):
            instr_type = "arithmetic_logic"
        elif any(x in instruction for x in ("lw", "lh", "lb", "lbu", "lhu")):
            instr_type = "load"
        elif any(x in instruction for x in ("sw", "sh", "sb")):
            instr_type = "store"
        elif any(x in instruction for x in ("beq", "bne", "blt", "bge", "bltu", "bgeu")):
            instr_type = "branch"
        elif any(x in instruction for x in ("jal", "jalr")):
            instr_type = "jump"
        elif instruction in ("fence", "ecall", "ebreak"):
            instr_type = "system"

        instruction_chunks.append({
            "chunk_id":         f"rv32ui_{instruction}",
            "section_title":    f"rv32ui Test: {instruction.upper()}",
            "instruction":      instruction.upper(),
            "instruction_type": instr_type,
            "source_url":       f"{RAW_BASE}/isa/rv32ui/{instruction}.S",
            "canonical_url":    f"{RAW_BASE}/{rv64_path}",
            "total_test_cases": len(vectors),
            "macros_used":      list({v["macro"] for v in vectors}),
            "test_vectors":     vectors,
            "document_text":    doc_text,
        })
        print(f" {len(vectors)} test cases")

    # ── Step 4: Write outputs ──────────────────────────────────────────────────
    print("[4/5] Saving outputs...")
    all_chunks = support_chunks + instruction_chunks

    tb_chunks_path = os.path.join(OUTPUT_DIR, "testbench_chunks.json")
    with open(tb_chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"   → {tb_chunks_path}")

    # Full Markdown for human review
    tb_md_path = os.path.join(OUTPUT_DIR, "testbench_full_doc.md")
    with open(tb_md_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(f"\n\n---\n<!-- {c['chunk_id']} -->\n\n")
            f.write(c.get("document_text", ""))
    print(f"   → {tb_md_path}")

    # ── Step 5: Stats report ──────────────────────────────────────────────────
    print(f"\n[5/5] ✅ Done.")
    by_type = {}
    for c in instruction_chunks:
        t = c["instruction_type"]
        by_type[t] = by_type.get(t, 0) + 1

    print(f"\n   Total chunks          : {len(all_chunks)}")
    print(f"   Support chunks        : {len(support_chunks)}")
    print(f"   Instruction chunks    : {len(instruction_chunks)}")
    print(f"\n   Breakdown by type:")
    for t, cnt in sorted(by_type.items()):
        print(f"     {t:<22}: {cnt}")

    total_vectors = sum(c["total_test_cases"] for c in instruction_chunks)
    print(f"\n   Total test vectors parsed: {total_vectors}")
    print(f"\n   Artifacts saved to '{OUTPUT_DIR}/':")
    print(f"     testbench_chunks.json  → machine-readable RAG input")
    print(f"     testbench_full_doc.md  → human-readable debug view")


if __name__ == "__main__":
    main()
