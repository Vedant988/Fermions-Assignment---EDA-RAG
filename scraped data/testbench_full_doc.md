

---
<!-- support_0 -->

# riscv-tests: TVM Protocol and Pass/Fail Specification

> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Target Virtual Machines (TVMs)

| TVM | Description |
| --- | --- |
| `rv32ui` | RV32 user-level, integer only — **our target** |
| `rv32si` | RV32 supervisor-level, integer only |

## Test Environments

| Environment | Description |
| --- | --- |
| `p` | No virtual memory, only core 0 boots — **our target** |

## Test Structure

Every test file follows: `RVTEST_CODE_BEGIN` → test vectors using macros → `RVTEST_PASS` or `RVTEST_FAIL` → `RVTEST_DATA_BEGIN/END`.

## Full README

```
riscv-tests
================

About
-----------

This repository hosts unit tests for RISC-V processors.

Building from repository
-----------------------------

We assume that the RISCV environment variable is set to the RISC-V tools
install path, and that the [riscv-gnu-toolchain](
https://github.com/riscv-collab/riscv-gnu-toolchain) package is installed.

    $ git clone https://github.com/riscv/riscv-tests
    $ cd riscv-tests
    $ git submodule update --init --recursive
    $ autoconf
    $ ./configure --prefix=$RISCV/target
    $ make
    $ make install

The rest of this document describes the format of test programs for the RISC-V
architecture.

Test Virtual Machines
-------------------------

To allow maximum reuse of a given test, each test program is constrained to
only use features of a given *test virtual machine* or TVM. A TVM hides
differences between alternative implementations by defining:

* The set of registers and instructions that can be used. 
* Which portions of memory can be accessed.
* The way the test program starts and ends execution. 
* The way that test data is input.
* The way that test results are output.

The following table shows the TVMs currently defined for RISC-V. All of these
TVMs only support a single hardware thread.

TVM Name | Description
--- | ---
`rv32ui` | RV32 user-level, integer only
`rv32si` | RV32 supervisor-level, integer only
`rv64ui` | RV64 user-level, integer only
`rv64uf` | RV64 user-level, integer and floating-point
`rv64uv` | RV64 user-level, integer, floating-point, and vector
`rv64si` | RV64 supervisor-level, integer only
`rv64sv` | RV64 supervisor-level, integer and vector

A test program for RISC-V is written within a single assembly language file,
which is passed through the C preprocessor, and all regular assembly
directives can be used. An example test program is shown below. Each test
program should first include the `riscv_test.h` header file, which defines the
macros used by the TVM. The header file will have different contents depending
on the target environment for which the test will be built.  One of the goals
of the various TVMs is to allow the same test program to be compiled and run
on very different target environments yet still produce the same results. The
following table shows the target environment currently defined.

Target Environment Name | Description
--- | ---
`p` | virtual memory is disabled, only core 0 boots up
`pm` | virtual memory is disabled, all cores boot up
`pt` | virtual memory is disabled, timer interrupt fires every 100 cycles
`v` | virtual memory is enabled

Each test program must next specify for which TVM it is designed by including
the appropriate TVM macro, `RVTEST_RV64U` in this example. This specification
can change the way in which subsequent macros are interpreted, and supports
a static check of the TVM functionality used by the program.

The test program will begin execution at the first instruction after
`RVTEST_CODE_BEGIN`, and continue until execution reaches an `RVTEST_PASS`
macro or the `RVTEST_CODE_END` macro, which is implicitly a success. A test
can explicitly fail by invoking the `RVTEST_FAIL` macro.

The example program contains self-checking code to test the result of the add.
However, self-checks rely on correct functioning of the processor instructions
used to implement the self check (e.g., the branch) and so cannot be the only
testing strategy.

All tests should also contain a test data section, delimited by
`RVTEST_DATA_BEGIN` and `RVTEST_DATA_END`. There is no alignment guarantee for
the start of the test data section, so regular assembler alignment
instructions should be used to ensure desired alignment of data values. This
region of memory will be captured at the end of the test to act as a signature
from the test. The signature can be compared with that from a run on the
golden model.

Any given test environment for running tests should also include a timeout
facility, which will class a test as failing if it does not successfully
complete a test within a reasonable time bound.

    #include "riscv_test.h"

    RVTEST_RV64U        # Define TVM used by program.

    # Test code region.
    RVTEST_CODE_BEGIN   # Start of test code.
            lw      x2, testdata
            addi    x2, 1         # Should be 42 into $2.
            sw      x2, result    # Store result into memory overwriting 1s.
            li      x3, 42        # Desired result.
            bne     x2, x3, fail  # Fail out if doesn't match.
            RVTEST_PASS           # Signal success.
    fail:
            RVTEST_FAIL
    RVTEST_CODE_END     # End of test code.

    # Input data section.
    # This section is optional, and this data is NOT saved in the output.
    .data
            .align 3
    testdata:
            .dword 41

    # Output data section.
    RVTEST_DATA_BEGIN   # Start of test output data region.
            .align 3
    result:
            .dword -1
    RVTEST_DATA_END     # End of test output data region.

User-Level TVMs
--------------------

Test programs for the `rv32u*` and `rv64u*` TVMs can contain all instructions
from the respective base user-level ISA (RV32 or RV64), except for those with
the SYSTEM major opcode (syscall, break, rdcycle, rdtime, rdinstret). All user
registers (pc, x0-x31, f0-f31, fsr) can be accessed.

The `rv32ui` and `rv64ui` TVMs are integer-only subsets of `rv32u` and `rv64u`
respectively. These subsets can not use any floating-point instructions (major
opcodes: LOAD-FP, STORE-FP, MADD, MSUB, NMSUB, NMADD, OP-FP), and hence cannot
access the floating-point register state (f0-f31 and fsr). The integer-only
TVMs are useful for initial processor bringup and to test simpler
implementations that lack a hardware FPU.

Note that any `rv32ui` test program is also valid for the `rv32u` TVM, and
similarly `rv64ui` is a strict subset of `rv64u`. To allow a given test to run
on the widest possible set of implementations, it is desirable to write any
given test to run on the smallest or least capable TVM possible. For example,
any simple tests of integer functionality should be written for the `rv64ui`
TVM, as the same test can then be run on RV64 implementations with or without a
hardware FPU. As another example, all tests for these base user-level TVMs will
also be valid for more advanced processors with instruction-set extensions.

At the start of execution, the values of all registers are undefined. All
branch and jump destinations must be to labels within the test code region of
the assembler source file. The code and data sections will be relocated
differently for the various implementations of the test environment, and so
test program results shall not depend on absolute addresses of instructions or
data memory. The test build environment should support randomization of the
section relocation to provide better coverage and to ensure test signatures do
not contain absolute addresses.

Supervisor-Level TVMs
--------------------------

The supervisor-level TVMs allow testing of supervisor-level state and
instructions.  As with the user-level TVMs, we provide integer-only
supervisor-level TVMs indicated with a trailing `i`.

History and Acknowledgements
---------------------------------

This style of test virtual machine originated with the T0 (Torrent-0) vector
microprocessor project at UC Berkeley and ICSI, begun in 1992. The main
developers of this test strategy were Krste Asanovic and David Johnson. A
precursor to `torture` was `rantor` developed by Phil Kohn at ICSI.

A variant of this testing approach was also used for the Scale vector-thread
processor at MIT, begun in 2000. Ronny Krashinsky and Christopher Batten were
the principal architects of the Scale chip. Jeffrey Cohen and Mark Hampton
developed a version of torture capable of generating vector-thread code.
```

---
<!-- support_macros_1 -->

# riscv-tests test_macros.h: Register-Immediate and Register-Register Contracts

These macros define the **exact hardware behavior** that must hold for riscv-tests to pass. Each expands to a sequence of instructions followed by a `bne ..., fail` check.

## RTL Contracts

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

---
<!-- support_macros_2 -->

# riscv-tests test_macros.h: Memory Load/Store Contracts

These macros define the **exact hardware behavior** that must hold for riscv-tests to pass. Each expands to a sequence of instructions followed by a `bne ..., fail` check.

## RTL Contracts

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.
- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.
- **`TEST_ST_OP`**: Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.
- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

---
<!-- support_macros_3 -->

# riscv-tests test_macros.h: Branch and Jump Contracts

These macros define the **exact hardware behavior** that must hold for riscv-tests to pass. Each expands to a sequence of instructions followed by a `bne ..., fail` check.

## RTL Contracts

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

---
<!-- rv32ui_add -->

# rv32ui Test: `ADD`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **37**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (29 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x00000000",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x00000002",
    "rs1_value": "0x00000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000a",
    "rs1_value": "0x00000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffff8000",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff7fff8000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000007fff",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000007fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000080007ffe",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80007fff",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000007fff7fff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffffffe",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000080000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# add.S
#-----------------------------------------------------------------------------
#
# Test add instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  add, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  add, 0x00000002, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  add, 0x0000000a, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  add, 0xffffffffffff8000, 0x0000000000000000, 0xffffffffffff8000 );
  TEST_RR_OP( 6,  add, 0xffffffff80000000, 0xffffffff80000000, 0x00000000 );
  TEST_RR_OP( 7,  add, 0xffffffff7fff8000, 0xffffffff80000000, 0xffffffffffff8000 );

  TEST_RR_OP( 8,  add, 0x0000000000007fff, 0x0000000000000000, 0x0000000000007fff );
  TEST_RR_OP( 9,  add, 0x000000007fffffff, 0x000000007fffffff, 0x0000000000000000 );
  TEST_RR_OP( 10, add, 0x0000000080007ffe, 0x000000007fffffff, 0x0000000000007fff );

  TEST_RR_OP( 11, add, 0xffffffff80007fff, 0xffffffff80000000, 0x0000000000007fff );
  TEST_RR_OP( 12, add, 0x000000007fff7fff, 0x000000007fffffff, 0xffffffffffff8000 );

  TEST_RR_OP( 13, add, 0xffffffffffffffff, 0x0000000000000000, 0xffffffffffffffff );
  TEST_RR_OP( 14, add, 0x0000000000000000, 0xffffffffffffffff, 0x0000000000000001 );
  TEST_RR_OP( 15, add, 0xfffffffffffffffe, 0xffffffffffffffff, 0xffffffffffffffff );

  TEST_RR_OP( 16, add, 0x0000000080000000, 0x0000000000000001, 0x000000007fffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 17, add, 24, 13, 11 );
  TEST_RR_SRC2_EQ_DEST( 18, add, 25, 14, 11 );
  TEST_RR_SRC12_EQ_DEST( 19, add, 26, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 20, 0, add, 24, 13, 11 );
  TEST_RR_DEST_BYPASS( 21, 1, add, 25, 14, 11 );
  TEST_RR_DEST_BYPASS( 22, 2, add, 26, 15, 11 );

  TEST_RR_SRC12_BYPASS( 23, 0, 0, add, 24, 13, 11 );
  TEST_RR_SRC12_BYPASS( 24, 0, 1, add, 25, 14, 11 );
  TEST_RR_SRC12_BYPASS( 25, 0, 2, add, 26, 15, 11 );
  TEST_RR_SRC12_BYPASS( 26, 1, 0, add, 24, 13, 11 );
  TEST_RR_SRC12_BYPASS( 27, 1, 1, add, 25, 14, 11 );
  TEST_RR_SRC12_BYPASS( 28, 2, 0, add, 26, 15, 11 );

  TEST_RR_SRC21_BYPASS( 29, 0, 0, add, 24, 13, 11 );
  TEST_RR_SRC21_BYPASS( 30, 0, 1, add, 25, 14, 11 );
  TEST_RR_SRC21_BYPASS( 31, 0, 2, add, 26, 15, 11 );
  TEST_RR_SRC21_BYPASS( 32, 1, 0, add, 24, 13, 11 );
  TEST_RR_SRC21_BYPASS( 33, 1, 1, add, 25, 14, 11 );
  TEST_RR_SRC21_BYPASS( 34, 2, 0, add, 26, 15, 11 );

  TEST_RR_ZEROSRC1( 35, add, 15, 15 );
  TEST_RR_ZEROSRC2( 36, add, 32, 32 );
  TEST_RR_ZEROSRC12( 37, add, 0 );
  TEST_RR_ZERODEST( 38, add, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_addi -->

# rv32ui Test: `ADDI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **24**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 7 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 8 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 9 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| ... | ... | (16 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x00000000",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x00000002",
    "rs1_value": "0x00000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000a",
    "rs1_value": "0x00000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffffffff800",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffff7ffff800",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x00000000000007ff",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000007fffffff",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x00000000800007fe",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffff800007ff",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000007ffff7ff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffffffffffe",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000080000000",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# addi.S
#-----------------------------------------------------------------------------
#
# Test addi instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  addi, 0x00000000, 0x00000000, 0x000 );
  TEST_IMM_OP( 3,  addi, 0x00000002, 0x00000001, 0x001 );
  TEST_IMM_OP( 4,  addi, 0x0000000a, 0x00000003, 0x007 );

  TEST_IMM_OP( 5,  addi, 0xfffffffffffff800, 0x0000000000000000, 0x800 );
  TEST_IMM_OP( 6,  addi, 0xffffffff80000000, 0xffffffff80000000, 0x000 );
  TEST_IMM_OP( 7,  addi, 0xffffffff7ffff800, 0xffffffff80000000, 0x800 );

  TEST_IMM_OP( 8,  addi, 0x00000000000007ff, 0x00000000, 0x7ff );
  TEST_IMM_OP( 9,  addi, 0x000000007fffffff, 0x7fffffff, 0x000 );
  TEST_IMM_OP( 10, addi, 0x00000000800007fe, 0x7fffffff, 0x7ff );

  TEST_IMM_OP( 11, addi, 0xffffffff800007ff, 0xffffffff80000000, 0x7ff );
  TEST_IMM_OP( 12, addi, 0x000000007ffff7ff, 0x000000007fffffff, 0x800 );

  TEST_IMM_OP( 13, addi, 0xffffffffffffffff, 0x0000000000000000, 0xfff );
  TEST_IMM_OP( 14, addi, 0x0000000000000000, 0xffffffffffffffff, 0x001 );
  TEST_IMM_OP( 15, addi, 0xfffffffffffffffe, 0xffffffffffffffff, 0xfff );

  TEST_IMM_OP( 16, addi, 0x0000000080000000, 0x7fffffff, 0x001 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, addi, 24, 13, 11 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, addi, 24, 13, 11 );
  TEST_IMM_DEST_BYPASS( 19, 1, addi, 23, 13, 10 );
  TEST_IMM_DEST_BYPASS( 20, 2, addi, 22, 13,  9 );

  TEST_IMM_SRC1_BYPASS( 21, 0, addi, 24, 13, 11 );
  TEST_IMM_SRC1_BYPASS( 22, 1, addi, 23, 13, 10 );
  TEST_IMM_SRC1_BYPASS( 23, 2, addi, 22, 13,  9 );

  TEST_IMM_ZEROSRC1( 24, addi, 32, 32 );
  TEST_IMM_ZERODEST( 25, addi, 33, 50 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_and -->

# rv32ui Test: `AND`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **26**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_SRC1_EQ_DEST` | rd == rs1 hazard: source register is also destination. RegFile must handle read-... |
| 7 | `TEST_RR_SRC2_EQ_DEST` | rd == rs2 hazard: source register 2 is also destination. RegFile must handle rea... |
| 8 | `TEST_RR_SRC12_EQ_DEST` | rd == rs1 == rs2: all three refer to same register. Tests double-alias read-befo... |
| 9 | `TEST_RR_DEST_BYPASS` | NOP cycles inserted between instruction and result check. Tests that pipeline (e... |
| ... | ... | (18 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0f000f00",
    "rs1_value": "0xff00ff00"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x00f000f0",
    "rs1_value": "0x0ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000f000f",
    "rs1_value": "0x00ff00ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xf000f000",
    "rs1_value": "0xf00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# and.S
#-----------------------------------------------------------------------------
#
# Test and instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, and, 0xf000f000, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_EQ_DEST( 8, and, 0xff00ff00, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, and, 0, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, and, 0, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, and, 0 );
  TEST_RR_ZERODEST( 27, and, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_andi -->

# rv32ui Test: `ANDI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **13**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_SRC1_EQ_DEST` | I-type with rd == rs1. RegFile must handle read-before-write for immediate instr... |
| 7 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 8 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 9 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| ... | ... | (5 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xff00ff00",
    "rs1_value": "0xff00ff00"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000f0",
    "rs1_value": "0x0ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000f",
    "rs1_value": "0x00ff00ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x00000000",
    "rs1_value": "0xf00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# andi.S
#-----------------------------------------------------------------------------
#
# Test andi instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, andi, 0xff00ff00, 0xff00ff00, 0xf0f );
  TEST_IMM_OP( 3, andi, 0x000000f0, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, andi, 0x0000000f, 0x00ff00ff, 0x70f );
  TEST_IMM_OP( 5, andi, 0x00000000, 0xf00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, andi, 0x00000000, 0xff00ff00, 0x0f0 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, andi, 0x00000700, 0x0ff00ff0, 0x70f );
  TEST_IMM_DEST_BYPASS( 8,  1, andi, 0x000000f0, 0x00ff00ff, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 9,  2, andi, 0xf00ff00f, 0xf00ff00f, 0xf0f );

  TEST_IMM_SRC1_BYPASS( 10, 0, andi, 0x00000700, 0x0ff00ff0, 0x70f );
  TEST_IMM_SRC1_BYPASS( 11, 1, andi, 0x000000f0, 0x00ff00ff, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 12, 2, andi, 0x0000000f, 0xf00ff00f, 0x70f );

  TEST_IMM_ZEROSRC1( 13, andi, 0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, andi, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_auipc -->

# rv32ui Test: `AUIPC`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **2**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_CASE` | See test_macros.h for full definition.... |
| 3 | `TEST_CASE` | See test_macros.h for full definition.... |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# auipc.S
#-----------------------------------------------------------------------------
#
# Test auipc instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  TEST_CASE(2, a0, 10000, \
    .align 3; \
    lla a0, 1f + 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

  TEST_CASE(3, a0, -10000, \
    .align 3; \
    lla a0, 1f - 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_beq -->

# rv32ui Test: `BEQ`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **20**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 6 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 7 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_SRC12_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (12 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0",
    "rs2_value": "0",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-1",
    "rs2_value": "-1",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "0",
    "branch_taken": false
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-1",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "-1",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# beq.S
#-----------------------------------------------------------------------------
#
# Test beq instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, beq,  0,  0 );
  TEST_BR2_OP_TAKEN( 3, beq,  1,  1 );
  TEST_BR2_OP_TAKEN( 4, beq, -1, -1 );

  TEST_BR2_OP_NOTTAKEN( 5, beq,  0,  1 );
  TEST_BR2_OP_NOTTAKEN( 6, beq,  1,  0 );
  TEST_BR2_OP_NOTTAKEN( 7, beq, -1,  1 );
  TEST_BR2_OP_NOTTAKEN( 8, beq,  1, -1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, beq, 0, -1 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, beq, 0, -1 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    beq x0, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_bge -->

# rv32ui Test: `BGE`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **23**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 6 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 7 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| ... | ... | (15 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0",
    "rs2_value": "0",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-1",
    "rs2_value": "-1",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "0",
    "branch_taken": true
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "-1",
    "branch_taken": true
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-1",
    "rs2_value": "-2",
    "branch_taken": true
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-1",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-2",
    "rs2_value": "-1",
    "branch_taken": false
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-2",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bge.S
#-----------------------------------------------------------------------------
#
# Test bge instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bge,  0,  0 );
  TEST_BR2_OP_TAKEN( 3, bge,  1,  1 );
  TEST_BR2_OP_TAKEN( 4, bge, -1, -1 );
  TEST_BR2_OP_TAKEN( 5, bge,  1,  0 );
  TEST_BR2_OP_TAKEN( 6, bge,  1, -1 );
  TEST_BR2_OP_TAKEN( 7, bge, -1, -2 );

  TEST_BR2_OP_NOTTAKEN(  8, bge,  0,  1 );
  TEST_BR2_OP_NOTTAKEN(  9, bge, -1,  1 );
  TEST_BR2_OP_NOTTAKEN( 10, bge, -2, -1 );
  TEST_BR2_OP_NOTTAKEN( 11, bge, -2,  1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 12, 0, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 13, 0, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 14, 0, 2, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 15, 1, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 16, 1, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 17, 2, 0, bge, -1, 0 );

  TEST_BR2_SRC12_BYPASS( 18, 0, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 19, 0, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 20, 0, 2, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 21, 1, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 22, 1, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 23, 2, 0, bge, -1, 0 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 24, x1, 3, \
    li  x1, 1; \
    bge x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_bgeu -->

# rv32ui Test: `BGEU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **23**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 6 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 7 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| ... | ... | (15 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0x00000000",
    "rs2_value": "0x00000000",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0x00000001",
    "rs2_value": "0x00000001",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0xffffffff",
    "rs2_value": "0xffffffff",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0x00000001",
    "rs2_value": "0x00000000",
    "branch_taken": true
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0xffffffff",
    "rs2_value": "0xfffffffe",
    "branch_taken": true
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0xffffffff",
    "rs2_value": "0x00000000",
    "branch_taken": true
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0x00000000",
    "rs2_value": "0x00000001",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0xfffffffe",
    "rs2_value": "0xffffffff",
    "branch_taken": false
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0x00000000",
    "rs2_value": "0xffffffff",
    "branch_taken": false
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0x7fffffff",
    "rs2_value": "0x80000000",
    "branch_taken": false
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bgeu.S
#-----------------------------------------------------------------------------
#
# Test bgeu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bgeu, 0x00000000, 0x00000000 );
  TEST_BR2_OP_TAKEN( 3, bgeu, 0x00000001, 0x00000001 );
  TEST_BR2_OP_TAKEN( 4, bgeu, 0xffffffff, 0xffffffff );
  TEST_BR2_OP_TAKEN( 5, bgeu, 0x00000001, 0x00000000 );
  TEST_BR2_OP_TAKEN( 6, bgeu, 0xffffffff, 0xfffffffe );
  TEST_BR2_OP_TAKEN( 7, bgeu, 0xffffffff, 0x00000000 );

  TEST_BR2_OP_NOTTAKEN(  8, bgeu, 0x00000000, 0x00000001 );
  TEST_BR2_OP_NOTTAKEN(  9, bgeu, 0xfffffffe, 0xffffffff );
  TEST_BR2_OP_NOTTAKEN( 10, bgeu, 0x00000000, 0xffffffff );
  TEST_BR2_OP_NOTTAKEN( 11, bgeu, 0x7fffffff, 0x80000000 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 12, 0, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 13, 0, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 14, 0, 2, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 15, 1, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 16, 1, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 17, 2, 0, bgeu, 0xefffffff, 0xf0000000 );

  TEST_BR2_SRC12_BYPASS( 18, 0, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 19, 0, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 20, 0, 2, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 21, 1, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 22, 1, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 23, 2, 0, bgeu, 0xefffffff, 0xf0000000 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 24, x1, 3, \
    li  x1, 1; \
    bgeu x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_blt -->

# rv32ui Test: `BLT`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **20**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 6 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 7 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_SRC12_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (12 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-1",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-2",
    "rs2_value": "-1",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "0",
    "branch_taken": false
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "-1",
    "branch_taken": false
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-1",
    "rs2_value": "-2",
    "branch_taken": false
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "-2",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# blt.S
#-----------------------------------------------------------------------------
#
# Test blt instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, blt,  0,  1 );
  TEST_BR2_OP_TAKEN( 3, blt, -1,  1 );
  TEST_BR2_OP_TAKEN( 4, blt, -2, -1 );

  TEST_BR2_OP_NOTTAKEN( 5, blt,  1,  0 );
  TEST_BR2_OP_NOTTAKEN( 6, blt,  1, -1 );
  TEST_BR2_OP_NOTTAKEN( 7, blt, -1, -2 );
  TEST_BR2_OP_NOTTAKEN( 8, blt,  1, -2 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, blt, 0, -1 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, blt, 0, -1 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    blt x0, x1, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_bltu -->

# rv32ui Test: `BLTU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **20**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 6 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 7 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_SRC12_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (12 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0x00000000",
    "rs2_value": "0x00000001",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0xfffffffe",
    "rs2_value": "0xffffffff",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0x00000000",
    "rs2_value": "0xffffffff",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0x00000001",
    "rs2_value": "0x00000000",
    "branch_taken": false
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0xffffffff",
    "rs2_value": "0xfffffffe",
    "branch_taken": false
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0xffffffff",
    "rs2_value": "0x00000000",
    "branch_taken": false
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0x80000000",
    "rs2_value": "0x7fffffff",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bltu.S
#-----------------------------------------------------------------------------
#
# Test bltu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bltu, 0x00000000, 0x00000001 );
  TEST_BR2_OP_TAKEN( 3, bltu, 0xfffffffe, 0xffffffff );
  TEST_BR2_OP_TAKEN( 4, bltu, 0x00000000, 0xffffffff );

  TEST_BR2_OP_NOTTAKEN( 5, bltu, 0x00000001, 0x00000000 );
  TEST_BR2_OP_NOTTAKEN( 6, bltu, 0xffffffff, 0xfffffffe );
  TEST_BR2_OP_NOTTAKEN( 7, bltu, 0xffffffff, 0x00000000 );
  TEST_BR2_OP_NOTTAKEN( 8, bltu, 0x80000000, 0x7fffffff );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, bltu, 0xf0000000, 0xefffffff );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, bltu, 0xf0000000, 0xefffffff );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    bltu x0, x1, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_bne -->

# rv32ui Test: `BNE`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **20**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 3 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 4 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 5 | `TEST_BR2_OP_TAKEN` | Branch taken: condition is true, PC must jump to target. Tests: branch condition... |
| 6 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 7 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 8 | `TEST_BR2_OP_NOTTAKEN` | Branch not taken: condition is false, PC must fall through to PC+4. Tests: branc... |
| 9 | `TEST_BR2_SRC12_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (12 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_BR2_OP_TAKEN`**: Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.
- **`TEST_BR2_OP_NOTTAKEN`**: Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "0",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "0",
    "branch_taken": true
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "-1",
    "rs2_value": "1",
    "branch_taken": true
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "rtl_contract": "Branch taken: condition is true, PC must jump to target. Tests: branch condition logic, PC update to PC+imm.",
    "rs1_value": "1",
    "rs2_value": "-1",
    "branch_taken": true
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "0",
    "rs2_value": "0",
    "branch_taken": false
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "1",
    "rs2_value": "1",
    "branch_taken": false
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "rtl_contract": "Branch not taken: condition is false, PC must fall through to PC+4. Tests: branch condition logic, sequential PC increment.",
    "rs1_value": "-1",
    "rs2_value": "-1",
    "branch_taken": false
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bne.S
#-----------------------------------------------------------------------------
#
# Test bne instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bne,  0,  1 );
  TEST_BR2_OP_TAKEN( 3, bne,  1,  0 );
  TEST_BR2_OP_TAKEN( 4, bne, -1,  1 );
  TEST_BR2_OP_TAKEN( 5, bne,  1, -1 );

  TEST_BR2_OP_NOTTAKEN( 6, bne,  0,  0 );
  TEST_BR2_OP_NOTTAKEN( 7, bne,  1,  1 );
  TEST_BR2_OP_NOTTAKEN( 8, bne, -1, -1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, bne, 0, 0 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, bne, 0, 0 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    bne x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_fence_i -->

# rv32ui Test: `FENCE_I`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **2**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_CASE` | See test_macros.h for full definition.... |
| 3 | `TEST_CASE` | See test_macros.h for full definition.... |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# fence_i.S
#-----------------------------------------------------------------------------
#
# Test self-modifying code and the fence.i instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

li a3, 111
lh a0, insn
lh a1, insn+2

# test I$ hit
.align 6
sh a0, 2f, t0
sh a1, 2f+2, t0
fence.i

la a5, 2f
jalr t1, a5, 0
TEST_CASE( 2, a3, 444, nop )

# test prefetcher hit
li a4, 100
1: addi a4, a4, -1
bnez a4, 1b

sh a0, 3f, t0
sh a1, 3f+2, t0
fence.i

.align 6
la a5, 3f
jalr t1, a5, 0
TEST_CASE( 3, a3, 777, nop )

TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

insn:
  addi a3, a3, 333

2: addi a3, a3, 222
jalr a5, t1, 0

3: addi a3, a3, 555
jalr a5, t1, 0

RVTEST_DATA_END
```

---
<!-- rv32ui_jal -->

# rv32ui Test: `JAL`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **1**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 3 | `TEST_CASE` | See test_macros.h for full definition.... |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# jal.S
#-----------------------------------------------------------------------------
#
# Test jal instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Test 2: Basic test
  #-------------------------------------------------------------

test_2:
  li  TESTNUM, 2
  li  ra, 0

  jal x4, target_2
linkaddr_2:
  nop
  nop

  j fail

target_2:
  la  x2, linkaddr_2
  bne x2, x4, fail

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 3, ra, 3, \
    li  ra, 1; \
    jal x0, 1f; \
    addi ra, ra, 1; \
    addi ra, ra, 1; \
    addi ra, ra, 1; \
    addi ra, ra, 1; \
1:  addi ra, ra, 1; \
    addi ra, ra, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_jalr -->

# rv32ui Test: `JALR`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **4**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 4 | `TEST_JALR_SRC1_BYPASS` | See test_macros.h for full definition.... |
| 5 | `TEST_JALR_SRC1_BYPASS` | See test_macros.h for full definition.... |
| 6 | `TEST_JALR_SRC1_BYPASS` | See test_macros.h for full definition.... |
| 7 | `TEST_CASE` | See test_macros.h for full definition.... |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 4,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 7,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# jalr.S
#-----------------------------------------------------------------------------
#
# Test jalr instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Test 2: Basic test
  #-------------------------------------------------------------

test_2:
  li  TESTNUM, 2
  li  t0, 0
  la  t1, target_2

  jalr t0, t1, 0
linkaddr_2:
  j fail

target_2:
  la  t1, linkaddr_2
  bne t0, t1, fail

  #-------------------------------------------------------------
  # Test 3: Basic test2, rs = rd
  #-------------------------------------------------------------

test_3:
  li  TESTNUM, 3
  la  t0, target_3

  jalr t0, t0, 0
linkaddr_3:
  j fail

target_3:
  la  t1, linkaddr_3
  bne t0, t1, fail

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_JALR_SRC1_BYPASS( 4, 0, jalr );
  TEST_JALR_SRC1_BYPASS( 5, 1, jalr );
  TEST_JALR_SRC1_BYPASS( 6, 2, jalr );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  .option push
  .align 2
  .option norvc
  TEST_CASE( 7, t0, 4, \
    li  t0, 1; \
    la  t1, 1f; \
    jr  t1, -4; \
    addi t0, t0, 1; \
    addi t0, t0, 1; \
    addi t0, t0, 1; \
    addi t0, t0, 1; \
1:  addi t0, t0, 1; \
    addi t0, t0, 1; \
  )
  .option pop

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_lb -->

# rv32ui Test: `LB`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **18**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 3 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 4 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 5 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 6 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 7 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 8 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 9 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| ... | ... | (10 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffffffffff",
    "offset": "0",
    "base_label": "tdat"
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000000",
    "offset": "1",
    "base_label": "tdat"
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffffffffff0",
    "offset": "2",
    "base_label": "tdat"
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000000f",
    "offset": "3",
    "base_label": "tdat"
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffffffffff",
    "offset": "-3",
    "base_label": "tdat4"
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000000",
    "offset": "-2",
    "base_label": "tdat4"
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffffffffff0",
    "offset": "-1",
    "base_label": "tdat4"
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000000f",
    "offset": "0",
    "base_label": "tdat4"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lb.S
#-----------------------------------------------------------------------------
#
# Test lb instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lb, 0xffffffffffffffff, 0,  tdat );
  TEST_LD_OP( 3, lb, 0x0000000000000000, 1,  tdat );
  TEST_LD_OP( 4, lb, 0xfffffffffffffff0, 2,  tdat );
  TEST_LD_OP( 5, lb, 0x000000000000000f, 3, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lb, 0xffffffffffffffff, -3, tdat4 );
  TEST_LD_OP( 7, lb, 0x0000000000000000, -2,  tdat4 );
  TEST_LD_OP( 8, lb, 0xfffffffffffffff0, -1,  tdat4 );
  TEST_LD_OP( 9, lb, 0x000000000000000f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0xffffffffffffffff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lb x5, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0x0000000000000000, \
    la  x1, tdat; \
    addi x1, x1, -6; \
    lb x5, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lb, 0xfffffffffffffff0, 1, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lb, 0x000000000000000f, 1, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lb, 0x0000000000000000, 1, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lb, 0xfffffffffffffff0, 1, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lb, 0x000000000000000f, 1, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lb, 0x0000000000000000, 1, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x5, tdat; \
    lb  x2, 0(x5); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x5, tdat; \
    lb  x2, 0(x5); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xff
tdat2:  .byte 0x00
tdat3:  .byte 0xf0
tdat4:  .byte 0x0f

RVTEST_DATA_END
```

---
<!-- rv32ui_lbu -->

# rv32ui Test: `LBU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **18**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 3 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 4 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 5 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 6 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 7 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 8 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 9 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| ... | ... | (10 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "0",
    "base_label": "tdat"
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000000",
    "offset": "1",
    "base_label": "tdat"
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000f0",
    "offset": "2",
    "base_label": "tdat"
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000000f",
    "offset": "3",
    "base_label": "tdat"
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "-3",
    "base_label": "tdat4"
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000000",
    "offset": "-2",
    "base_label": "tdat4"
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000f0",
    "offset": "-1",
    "base_label": "tdat4"
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000000f",
    "offset": "0",
    "base_label": "tdat4"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lbu.S
#-----------------------------------------------------------------------------
#
# Test lbu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lbu, 0x00000000000000ff, 0,  tdat );
  TEST_LD_OP( 3, lbu, 0x0000000000000000, 1,  tdat );
  TEST_LD_OP( 4, lbu, 0x00000000000000f0, 2,  tdat );
  TEST_LD_OP( 5, lbu, 0x000000000000000f, 3, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lbu, 0x00000000000000ff, -3, tdat4 );
  TEST_LD_OP( 7, lbu, 0x0000000000000000, -2,  tdat4 );
  TEST_LD_OP( 8, lbu, 0x00000000000000f0, -1,  tdat4 );
  TEST_LD_OP( 9, lbu, 0x000000000000000f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x00000000000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lbu x5, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0x0000000000000000, \
    la  x1, tdat; \
    addi x1, x1, -6; \
    lbu x5, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lbu, 0x00000000000000f0, 1, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lbu, 0x000000000000000f, 1, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lbu, 0x0000000000000000, 1, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lbu, 0x00000000000000f0, 1, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lbu, 0x000000000000000f, 1, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lbu, 0x0000000000000000, 1, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x5, tdat; \
    lbu  x2, 0(x5); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x5, tdat; \
    lbu  x2, 0(x5); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xff
tdat2:  .byte 0x00
tdat3:  .byte 0xf0
tdat4:  .byte 0x0f

RVTEST_DATA_END
```

---
<!-- rv32ui_ld_st -->

# rv32ui Test: `LD_ST`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **69**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 3 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 4 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 5 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 6 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 7 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 8 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| 9 | `TEST_LD_ST_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (61 more test cases) |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 25,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 26,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 27,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 28,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 29,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 30,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 31,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 32,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 33,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 34,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 35,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 36,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 37,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 38,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 39,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 40,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 41,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 42,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 43,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 44,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 45,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 46,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 47,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 48,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 49,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 50,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 51,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 52,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 53,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 54,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 55,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 56,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 57,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 58,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 59,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 60,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 61,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 62,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 63,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 64,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 65,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 66,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 67,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 68,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 69,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 70,
    "macro": "TEST_LD_ST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# ld_st.S
#-----------------------------------------------------------------------------
#
# Test load and store instructions
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Bypassing Tests
  #-------------------------------------------------------------

  # Test sb and lb (signed byte)
  TEST_LD_ST_BYPASS(2,  lb,  sb, 0xffffffffffffffdd, 0, tdat );
  TEST_LD_ST_BYPASS(3,  lb,  sb, 0xffffffffffffffcd, 1, tdat );
  TEST_LD_ST_BYPASS(4,  lb,  sb, 0xffffffffffffffcc, 2, tdat );
  TEST_LD_ST_BYPASS(5,  lb,  sb, 0xffffffffffffffbc, 3, tdat );
  TEST_LD_ST_BYPASS(6,  lb,  sb, 0xffffffffffffffbb, 4, tdat );
  TEST_LD_ST_BYPASS(7,  lb,  sb, 0xffffffffffffffab, 5, tdat );

  TEST_LD_ST_BYPASS(8,  lb, sb, 0x33, 0, tdat );
  TEST_LD_ST_BYPASS(9,  lb, sb, 0x23, 1, tdat );
  TEST_LD_ST_BYPASS(10, lb, sb, 0x22, 2, tdat );
  TEST_LD_ST_BYPASS(11, lb, sb, 0x12, 3, tdat );
  TEST_LD_ST_BYPASS(12, lb, sb, 0x11, 4, tdat );
  TEST_LD_ST_BYPASS(13, lb, sb, 0x01, 5, tdat );

  # Test sb and lbu (unsigned byte)
  TEST_LD_ST_BYPASS(14, lbu, sb, 0x33, 0, tdat );
  TEST_LD_ST_BYPASS(15, lbu, sb, 0x23, 1, tdat );
  TEST_LD_ST_BYPASS(16, lbu, sb, 0x22, 2, tdat );
  TEST_LD_ST_BYPASS(17, lbu, sb, 0x12, 3, tdat );
  TEST_LD_ST_BYPASS(18, lbu, sb, 0x11, 4, tdat );
  TEST_LD_ST_BYPASS(19, lbu, sb, 0x01, 5, tdat );

  # Test sw and lw (signed word)
  TEST_LD_ST_BYPASS(20, lw, sw, 0xffffffffaabbccdd, 0,  tdat );
  TEST_LD_ST_BYPASS(21, lw, sw, 0xffffffffdaabbccd, 4,  tdat );
  TEST_LD_ST_BYPASS(22, lw, sw, 0xffffffffddaabbcc, 8,  tdat );
  TEST_LD_ST_BYPASS(23, lw, sw, 0xffffffffcddaabbc, 12, tdat );
  TEST_LD_ST_BYPASS(24, lw, sw, 0xffffffffccddaabb, 16, tdat );
  TEST_LD_ST_BYPASS(25, lw, sw, 0xffffffffbccddaab, 20, tdat );

  TEST_LD_ST_BYPASS(26, lw, sw, 0x00112233, 0,  tdat );
  TEST_LD_ST_BYPASS(27, lw, sw, 0x30011223, 4,  tdat );
  TEST_LD_ST_BYPASS(28, lw, sw, 0x33001122, 8,  tdat );
  TEST_LD_ST_BYPASS(29, lw, sw, 0x23300112, 12, tdat );
  TEST_LD_ST_BYPASS(30, lw, sw, 0x22330011, 16, tdat );
  TEST_LD_ST_BYPASS(31, lw, sw, 0x12233001, 20, tdat );

  # Test sh and lh (signed halfword)
  TEST_LD_ST_BYPASS(32, lh, sh, 0xffffffffffffccdd, 0, tdat );
  TEST_LD_ST_BYPASS(33, lh, sh, 0xffffffffffffbccd, 2, tdat );
  TEST_LD_ST_BYPASS(34, lh, sh, 0xffffffffffffbbcc, 4, tdat );
  TEST_LD_ST_BYPASS(35, lh, sh, 0xffffffffffffabbc, 6, tdat );
  TEST_LD_ST_BYPASS(36, lh, sh, 0xffffffffffffaabb, 8, tdat );
  TEST_LD_ST_BYPASS(37, lh, sh, 0xffffffffffffdaab, 10, tdat );

  TEST_LD_ST_BYPASS(38, lh, sh, 0x2233, 0, tdat );
  TEST_LD_ST_BYPASS(39, lh, sh, 0x1223, 2, tdat );
  TEST_LD_ST_BYPASS(40, lh, sh, 0x1122, 4, tdat );
  TEST_LD_ST_BYPASS(41, lh, sh, 0x0112, 6, tdat );
  TEST_LD_ST_BYPASS(42, lh, sh, 0x0011, 8, tdat );
  TEST_LD_ST_BYPASS(43, lh, sh, 0x3001, 10, tdat );

  # Test sh and lhu (unsigned halfword)
  TEST_LD_ST_BYPASS(44, lhu, sh, 0x2233, 0, tdat );
  TEST_LD_ST_BYPASS(45, lhu, sh, 0x1223, 2, tdat );
  TEST_LD_ST_BYPASS(46, lhu, sh, 0x1122, 4, tdat );
  TEST_LD_ST_BYPASS(47, lhu, sh, 0x0112, 6, tdat );
  TEST_LD_ST_BYPASS(48, lhu, sh, 0x0011, 8, tdat );
  TEST_LD_ST_BYPASS(49, lhu, sh, 0x3001, 10, tdat );

  # RV64-specific tests for ld, sd, and lwu
#if __riscv_xlen == 64
  # Test sd and ld (doubleword)
  TEST_LD_ST_BYPASS(50, ld, sd, 0x0011223344556677, 0,  tdat );
  TEST_LD_ST_BYPASS(51, ld, sd, 0x1122334455667788, 8,  tdat );
  TEST_LD_ST_BYPASS(52, ld, sd, 0x2233445566778899, 16, tdat );
  TEST_LD_ST_BYPASS(53, ld, sd, 0xabbccdd, 0,  tdat );
  TEST_LD_ST_BYPASS(54, ld, sd, 0xaabbccd, 8,  tdat );
  TEST_LD_ST_BYPASS(55, ld, sd, 0xdaabbcc, 16, tdat );
  TEST_LD_ST_BYPASS(56, ld, sd, 0xddaabbc, 24, tdat );
  TEST_LD_ST_BYPASS(57, ld, sd, 0xcddaabb, 32, tdat );
  TEST_LD_ST_BYPASS(58, ld, sd, 0xccddaab, 40, tdat );

  TEST_LD_ST_BYPASS(59, ld, sd, 0x00112233, 0,  tdat );
  TEST_LD_ST_BYPASS(60, ld, sd, 0x30011223, 8,  tdat );
  TEST_LD_ST_BYPASS(61, ld, sd, 0x33001122, 16, tdat );
  TEST_LD_ST_BYPASS(62, ld, sd, 0x23300112, 24, tdat );
  TEST_LD_ST_BYPASS(63, ld, sd, 0x22330011, 32, tdat );
  TEST_LD_ST_BYPASS(64, ld, sd, 0x12233001, 40, tdat );

  # Test sw and lwu (unsigned word)
  TEST_LD_ST_BYPASS(65, lwu, sw, 0x00112233, 0,  tdat );
  TEST_LD_ST_BYPASS(66, lwu, sw, 0x33001122, 8,  tdat );
  TEST_LD_ST_BYPASS(67, lwu, sw, 0x30011223, 4,  tdat );
  TEST_LD_ST_BYPASS(68, lwu, sw, 0x23300112, 12, tdat );
  TEST_LD_ST_BYPASS(69, lwu, sw, 0x22330011, 16, tdat );
  TEST_LD_ST_BYPASS(70, lwu, sw, 0x12233001, 20, tdat );
#endif

  li a0, 0xef         # Immediate load for manual store test
  la a1, tdat         # Load address of tdat
  sb a0, 3(a1)        # Store byte at offset 3 of tdat
  lb a2, 3(a1)        # Load byte back for verification

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
    .rept 20
    .word 0xdeadbeef
    .endr


RVTEST_DATA_END
```

---
<!-- rv32ui_lh -->

# rv32ui Test: `LH`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **18**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 3 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 4 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 5 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 6 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 7 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 8 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 9 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| ... | ... | (10 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "0",
    "base_label": "tdat"
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffffffff00",
    "offset": "2",
    "base_label": "tdat"
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000ff0",
    "offset": "4",
    "base_label": "tdat"
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffffffff00f",
    "offset": "6",
    "base_label": "tdat"
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "-6",
    "base_label": "tdat4"
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffffffff00",
    "offset": "-4",
    "base_label": "tdat4"
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000ff0",
    "offset": "-2",
    "base_label": "tdat4"
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffffffff00f",
    "offset": "0",
    "base_label": "tdat4"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lh.S
#-----------------------------------------------------------------------------
#
# Test lh instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lh, 0x00000000000000ff, 0,  tdat );
  TEST_LD_OP( 3, lh, 0xffffffffffffff00, 2,  tdat );
  TEST_LD_OP( 4, lh, 0x0000000000000ff0, 4,  tdat );
  TEST_LD_OP( 5, lh, 0xfffffffffffff00f, 6, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lh, 0x00000000000000ff, -6,  tdat4 );
  TEST_LD_OP( 7, lh, 0xffffffffffffff00, -4,  tdat4 );
  TEST_LD_OP( 8, lh, 0x0000000000000ff0, -2,  tdat4 );
  TEST_LD_OP( 9, lh, 0xfffffffffffff00f,  0, tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x00000000000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lh x5, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0xffffffffffffff00, \
    la  x1, tdat; \
    addi x1, x1, -5; \
    lh x5, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lh, 0x0000000000000ff0, 2, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lh, 0xfffffffffffff00f, 2, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lh, 0xffffffffffffff00, 2, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lh, 0x0000000000000ff0, 2, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lh, 0xfffffffffffff00f, 2, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lh, 0xffffffffffffff00, 2, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x5, tdat; \
    lh  x2, 0(x5); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x5, tdat; \
    lh  x2, 0(x5); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0x00ff
tdat2:  .half 0xff00
tdat3:  .half 0x0ff0
tdat4:  .half 0xf00f

RVTEST_DATA_END
```

---
<!-- rv32ui_lhu -->

# rv32ui Test: `LHU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **18**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 3 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 4 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 5 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 6 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 7 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 8 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 9 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| ... | ... | (10 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "0",
    "base_label": "tdat"
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000ff00",
    "offset": "2",
    "base_label": "tdat"
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000ff0",
    "offset": "4",
    "base_label": "tdat"
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000f00f",
    "offset": "6",
    "base_label": "tdat"
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x00000000000000ff",
    "offset": "-6",
    "base_label": "tdat4"
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000ff00",
    "offset": "-4",
    "base_label": "tdat4"
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000000ff0",
    "offset": "-2",
    "base_label": "tdat4"
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000000f00f",
    "offset": "0",
    "base_label": "tdat4"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lhu.S
#-----------------------------------------------------------------------------
#
# Test lhu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lhu, 0x00000000000000ff, 0,  tdat );
  TEST_LD_OP( 3, lhu, 0x000000000000ff00, 2,  tdat );
  TEST_LD_OP( 4, lhu, 0x0000000000000ff0, 4,  tdat );
  TEST_LD_OP( 5, lhu, 0x000000000000f00f, 6, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lhu, 0x00000000000000ff, -6,  tdat4 );
  TEST_LD_OP( 7, lhu, 0x000000000000ff00, -4,  tdat4 );
  TEST_LD_OP( 8, lhu, 0x0000000000000ff0, -2,  tdat4 );
  TEST_LD_OP( 9, lhu, 0x000000000000f00f,  0, tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x00000000000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lhu x5, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0x000000000000ff00, \
    la  x1, tdat; \
    addi x1, x1, -5; \
    lhu x5, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lhu, 0x0000000000000ff0, 2, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lhu, 0x000000000000f00f, 2, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lhu, 0x000000000000ff00, 2, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lhu, 0x0000000000000ff0, 2, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lhu, 0x000000000000f00f, 2, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lhu, 0x000000000000ff00, 2, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x5, tdat; \
    lhu  x2, 0(x5); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x5, tdat; \
    lhu  x2, 0(x5); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0x00ff
tdat2:  .half 0xff00
tdat3:  .half 0x0ff0
tdat4:  .half 0xf00f

RVTEST_DATA_END
```

---
<!-- rv32ui_lui -->

# rv32ui Test: `LUI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **5**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_CASE` | See test_macros.h for full definition.... |
| 3 | `TEST_CASE` | See test_macros.h for full definition.... |
| 4 | `TEST_CASE` | See test_macros.h for full definition.... |
| 5 | `TEST_CASE` | See test_macros.h for full definition.... |
| 6 | `TEST_CASE` | See test_macros.h for full definition.... |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 4,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lui.S
#-----------------------------------------------------------------------------
#
# Test lui instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_CASE( 2, x1, 0x0000000000000000, lui x1, 0x00000 );
  TEST_CASE( 3, x1, 0xfffffffffffff800, lui x1, 0xfffff;sra x1,x1,1);
  TEST_CASE( 4, x1, 0x00000000000007ff, lui x1, 0x7ffff;sra x1,x1,20);
  TEST_CASE( 5, x1, 0xfffffffffffff800, lui x1, 0x80000;sra x1,x1,20);

  TEST_CASE( 6, x0, 0, lui x0, 0x80000 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_lw -->

# rv32ui Test: `LW`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **18**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 3 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 4 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 5 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 6 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 7 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 8 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| 9 | `TEST_LD_OP` | Load instruction correctness: compute effective address rs1+offset, load from me... |
| ... | ... | (10 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_LD_OP`**: Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000ff00ff",
    "offset": "0",
    "base_label": "tdat"
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffff00ff00",
    "offset": "4",
    "base_label": "tdat"
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000ff00ff0",
    "offset": "8",
    "base_label": "tdat"
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffff00ff00f",
    "offset": "12",
    "base_label": "tdat"
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x0000000000ff00ff",
    "offset": "-12",
    "base_label": "tdat4"
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xffffffffff00ff00",
    "offset": "-8",
    "base_label": "tdat4"
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0x000000000ff00ff0",
    "offset": "-4",
    "base_label": "tdat4"
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "rtl_contract": "Load instruction correctness: compute effective address rs1+offset, load from memory. Tests: address adder, byte/halfword/word sign/zero extension logic.",
    "expected_result": "0xfffffffff00ff00f",
    "offset": "0",
    "base_label": "tdat4"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lw.S
#-----------------------------------------------------------------------------
#
# Test lw instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lw, 0x0000000000ff00ff, 0,  tdat );
  TEST_LD_OP( 3, lw, 0xffffffffff00ff00, 4,  tdat );
  TEST_LD_OP( 4, lw, 0x000000000ff00ff0, 8,  tdat );
  TEST_LD_OP( 5, lw, 0xfffffffff00ff00f, 12, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lw, 0x0000000000ff00ff, -12, tdat4 );
  TEST_LD_OP( 7, lw, 0xffffffffff00ff00, -8,  tdat4 );
  TEST_LD_OP( 8, lw, 0x000000000ff00ff0, -4,  tdat4 );
  TEST_LD_OP( 9, lw, 0xfffffffff00ff00f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x0000000000ff00ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lw x5, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0xffffffffff00ff00, \
    la  x1, tdat; \
    addi x1, x1, -3; \
    lw x5, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lw, 0x000000000ff00ff0, 4, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lw, 0xfffffffff00ff00f, 4, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lw, 0xffffffffff00ff00, 4, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lw, 0x000000000ff00ff0, 4, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lw, 0xfffffffff00ff00f, 4, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lw, 0xffffffffff00ff00, 4, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x5, tdat; \
    lw  x2, 0(x5); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x5, tdat; \
    lw  x2, 0(x5); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .word 0x00ff00ff
tdat2:  .word 0xff00ff00
tdat3:  .word 0x0ff00ff0
tdat4:  .word 0xf00ff00f

RVTEST_DATA_END
```

---
<!-- rv32ui_ma_data -->

# rv32ui Test: `MA_DATA`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **0**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# ma_data.S
#-----------------------------------------------------------------------------
#
# Test misaligned ld/st data.
# Based on rv64mi-ma_addr.S
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  la s0, data

#define SEXT(x, n) ((-((x) >> ((n)-1)) << (n)) | ((x) & ((1 << (n))-1)))

/* Check that a misaligned load reads the correct value. */
#define MISALIGNED_LOAD_TEST(testnum, insn, base, offset, res) \
  li TESTNUM, testnum; \
  li t1, res; \
  insn t2, offset(base); \
  bne t1, t2, fail; \
1:

# within quadword
  MISALIGNED_LOAD_TEST(1,  lh,  s0, 1, SEXT(0x0201, 16))
  MISALIGNED_LOAD_TEST(2,  lhu, s0, 1, 0x0201)
  MISALIGNED_LOAD_TEST(3,  lw,  s0, 1, SEXT(0x04030201, 32))
  MISALIGNED_LOAD_TEST(4,  lw,  s0, 2, SEXT(0x05040302, 32))
  MISALIGNED_LOAD_TEST(5,  lw,  s0, 3, SEXT(0x06050403, 32))

#if __riscv_xlen == 64
  MISALIGNED_LOAD_TEST(6,  lwu, s0, 1, 0x04030201)
  MISALIGNED_LOAD_TEST(7,  lwu, s0, 2, 0x05040302)
  MISALIGNED_LOAD_TEST(8,  lwu, s0, 3, 0x06050403)

  MISALIGNED_LOAD_TEST(9,  ld, s0, 1, 0x0807060504030201)
  MISALIGNED_LOAD_TEST(10, ld, s0, 2, 0x0908070605040302)
  MISALIGNED_LOAD_TEST(11, ld, s0, 3, 0x0a09080706050403)
  MISALIGNED_LOAD_TEST(12, ld, s0, 4, 0x0b0a090807060504)
  MISALIGNED_LOAD_TEST(13, ld, s0, 5, 0x0c0b0a0908070605)
  MISALIGNED_LOAD_TEST(14, ld, s0, 6, 0x0d0c0b0a09080706)
  MISALIGNED_LOAD_TEST(15, ld, s0, 7, 0x0e0d0c0b0a090807)
#endif

# octword crossing
  MISALIGNED_LOAD_TEST(16, lh,  s0, 31, SEXT(0x201f, 16))
  MISALIGNED_LOAD_TEST(17, lhu, s0, 31, 0x201f)
  MISALIGNED_LOAD_TEST(18, lw,  s0, 29, SEXT(0x201f1e1d, 32))
  MISALIGNED_LOAD_TEST(19, lw,  s0, 30, SEXT(0x21201f1e, 32))
  MISALIGNED_LOAD_TEST(20, lw,  s0, 31, SEXT(0x2221201f, 32))

#if __riscv_xlen == 64
  MISALIGNED_LOAD_TEST(21, lwu, s0, 29, 0x201f1e1d)
  MISALIGNED_LOAD_TEST(22, lwu, s0, 30, 0x21201f1e)
  MISALIGNED_LOAD_TEST(23, lwu, s0, 31, 0x2221201f)

  MISALIGNED_LOAD_TEST(24, ld, s0, 25, 0x201f1e1d1c1b1a19)
  MISALIGNED_LOAD_TEST(25, ld, s0, 26, 0x21201f1e1d1c1b1a)
  MISALIGNED_LOAD_TEST(26, ld, s0, 27, 0x2221201f1e1d1c1b)
  MISALIGNED_LOAD_TEST(27, ld, s0, 28, 0x232221201f1e1d1c)
  MISALIGNED_LOAD_TEST(28, ld, s0, 29, 0x24232221201f1e1d)
  MISALIGNED_LOAD_TEST(29, ld, s0, 30, 0x2524232221201f1e)
  MISALIGNED_LOAD_TEST(30, ld, s0, 31, 0x262524232221201f)
#endif

# cacheline crossing
  MISALIGNED_LOAD_TEST(31, lh,  s0, 63, SEXT(0x403f, 16))
  MISALIGNED_LOAD_TEST(32, lhu, s0, 63, 0x403f)
  MISALIGNED_LOAD_TEST(33, lw,  s0, 61, SEXT(0x403f3e3d, 32))
  MISALIGNED_LOAD_TEST(34, lw,  s0, 62, SEXT(0x41403f3e, 32))
  MISALIGNED_LOAD_TEST(35, lw,  s0, 63, SEXT(0x4241403f, 32))

#if __riscv_xlen == 64
  MISALIGNED_LOAD_TEST(36, lwu, s0, 61, 0x403f3e3d)
  MISALIGNED_LOAD_TEST(37, lwu, s0, 62, 0x41403f3e)
  MISALIGNED_LOAD_TEST(38, lwu, s0, 63, 0x4241403f)

  MISALIGNED_LOAD_TEST(39, ld, s0, 57, 0x403f3e3d3c3b3a39)
  MISALIGNED_LOAD_TEST(40, ld, s0, 58, 0x41403f3e3d3c3b3a)
  MISALIGNED_LOAD_TEST(41, ld, s0, 59, 0x4241403f3e3d3c3b)
  MISALIGNED_LOAD_TEST(42, ld, s0, 60, 0x434241403f3e3d3c)
  MISALIGNED_LOAD_TEST(43, ld, s0, 61, 0x44434241403f3e3d)
  MISALIGNED_LOAD_TEST(44, ld, s0, 62, 0x4544434241403f3e)
  MISALIGNED_LOAD_TEST(45, ld, s0, 63, 0x464544434241403f)
#endif


/* Check that a misaligned store writes the correct value. */
#define MISALIGNED_STORE_TEST(testnum, st_insn, ld_insn, base, offset, st_data) \
  li TESTNUM, testnum; \
  li t1, st_data; \
  st_insn t1, offset(base); \
  ld_insn t2, offset(base); \
  bne t1, t2, fail; \
1:

# within quadword
  MISALIGNED_STORE_TEST(46, sh, lh,  s0, 1, SEXT(0x8180, 16))
  MISALIGNED_STORE_TEST(47, sh, lhu, s0, 1, 0x8382)
  MISALIGNED_STORE_TEST(48, sw, lw,  s0, 1, SEXT(0x87868584, 32))
  MISALIGNED_STORE_TEST(49, sw, lw,  s0, 2, SEXT(0x8b8a8988, 32))
  MISALIGNED_STORE_TEST(50, sw, lw,  s0, 3, SEXT(0x8f8e8d8c, 32))

#if __riscv_xlen == 64
  MISALIGNED_STORE_TEST(51, sw, lwu, s0, 1, 0x93929190)
  MISALIGNED_STORE_TEST(52, sw, lwu, s0, 2, 0x97969594)
  MISALIGNED_STORE_TEST(53, sw, lwu, s0, 3, 0x9b9a9998)

  MISALIGNED_STORE_TEST(54, sd, ld, s0, 1, 0xa3a2a1a09f9e9d9c)
  MISALIGNED_STORE_TEST(55, sd, ld, s0, 2, 0xabaaa9a8a7a6a5a4)
  MISALIGNED_STORE_TEST(56, sd, ld, s0, 3, 0xb3b2b1b0afaeadac)
  MISALIGNED_STORE_TEST(57, sd, ld, s0, 4, 0xbbbab9b8b7b6b5b4)
  MISALIGNED_STORE_TEST(58, sd, ld, s0, 5, 0xc3c2c1c0bfbebdbc)
  MISALIGNED_STORE_TEST(59, sd, ld, s0, 6, 0xcbcac9c8c7c6c5c4)
  MISALIGNED_STORE_TEST(60, sd, ld, s0, 7, 0xd3d2d1d0cfcecdcc)
#endif

# octword crossing
  MISALIGNED_STORE_TEST(61, sh, lh,  s0, 31, SEXT(0xd5d4, 16))
  MISALIGNED_STORE_TEST(62, sh, lhu, s0, 31, 0xd7d6)
  MISALIGNED_STORE_TEST(63, sw, lw,  s0, 29, SEXT(0xdbdad9d8, 32))
  MISALIGNED_STORE_TEST(64, sw, lw,  s0, 30, SEXT(0xdfdedddc, 32))
  MISALIGNED_STORE_TEST(65, sw, lw,  s0, 31, SEXT(0xe3e2e1e0, 32))

#if __riscv_xlen == 64
  MISALIGNED_STORE_TEST(66, sw, lwu, s0, 29, 0xe7e6e5e4)
  MISALIGNED_STORE_TEST(67, sw, lwu, s0, 30, 0xebeae9e8)
  MISALIGNED_STORE_TEST(68, sw, lwu, s0, 31, 0xefeeedec)

  MISALIGNED_STORE_TEST(69, sd, ld, s0, 25, 0xf7f6f5f4f3f2f1f0)
  MISALIGNED_STORE_TEST(70, sd, ld, s0, 26, 0xfffefdfcfbfaf9f8)
  MISALIGNED_STORE_TEST(71, sd, ld, s0, 27, 0x0706050403020100)
  MISALIGNED_STORE_TEST(72, sd, ld, s0, 28, 0x0f0e0d0c0b0a0908)
  MISALIGNED_STORE_TEST(73, sd, ld, s0, 29, 0x1716151413121110)
  MISALIGNED_STORE_TEST(74, sd, ld, s0, 30, 0x1f1e1d1c1b1a1918)
  MISALIGNED_STORE_TEST(75, sd, ld, s0, 31, 0x2726252423222120)
#endif

# cacheline crossing
  MISALIGNED_STORE_TEST(76, sh, lh,  s0, 63, SEXT(0x3534, 16))
  MISALIGNED_STORE_TEST(77, sh, lhu, s0, 63, 0x3736)
  MISALIGNED_STORE_TEST(78, sw, lw,  s0, 61, SEXT(0x3b3a3938, 32))
  MISALIGNED_STORE_TEST(79, sw, lw,  s0, 62, SEXT(0x3f3e3d3c, 32))
  MISALIGNED_STORE_TEST(80, sw, lw,  s0, 63, SEXT(0x43424140, 32))

#if __riscv_xlen == 64
  MISALIGNED_STORE_TEST(81, sw, lwu, s0, 61, 0x47464544)
  MISALIGNED_STORE_TEST(82, sw, lwu, s0, 62, 0x4b4a4948)
  MISALIGNED_STORE_TEST(83, sw, lwu, s0, 63, 0x4f4e4d4c)

  MISALIGNED_STORE_TEST(84, sd, ld, s0, 57, 0x5756555453525150)
  MISALIGNED_STORE_TEST(85, sd, ld, s0, 58, 0x5f5e5d5c5b5a5958)
  MISALIGNED_STORE_TEST(86, sd, ld, s0, 59, 0x6766656463626160)
  MISALIGNED_STORE_TEST(87, sd, ld, s0, 60, 0x6f6e6d6c6b6a6968)
  MISALIGNED_STORE_TEST(88, sd, ld, s0, 61, 0x7776757473727170)
  MISALIGNED_STORE_TEST(89, sd, ld, s0, 62, 0x7f7e7d7c7b7a7978)
  MISALIGNED_STORE_TEST(90, sd, ld, s0, 63, 0x8786858483828180)
#endif


/* Check that a misaligned store writes the correct value, checked by a narrower load. */
#define MISMATCHED_STORE_TEST(testnum, st_insn, ld_insn, base, st_offset, ld_offset, st_data, ld_data) \
  li TESTNUM, testnum; \
  li t1, st_data; \
  li t2, ld_data; \
  st_insn t1, st_offset(base); \
  ld_insn t3, ld_offset(base); \
  bne t2, t3, fail; \
1:

# within quadword
  MISMATCHED_STORE_TEST(91,  sh, lb,  s0, 1, 1, 0x9998, SEXT(0x98, 8))
  MISMATCHED_STORE_TEST(92,  sh, lb,  s0, 1, 2, 0x9b9a, SEXT(0x9b, 8))
  MISMATCHED_STORE_TEST(93,  sh, lbu, s0, 1, 1, 0x9d9c, 0x9c)
  MISMATCHED_STORE_TEST(94,  sh, lbu, s0, 1, 2, 0x9f9e, 0x9f)
  MISMATCHED_STORE_TEST(95,  sw, lb,  s0, 1, 1, 0xa3a2a1a0, SEXT(0xa0, 8))
  MISMATCHED_STORE_TEST(96,  sw, lbu, s0, 2, 3, 0xa7a6a5a4, 0xa5)
  MISMATCHED_STORE_TEST(97,  sw, lh,  s0, 3, 4, 0xabaaa9a8, SEXT(0xaaa9, 16))
  MISMATCHED_STORE_TEST(98,  sw, lhu, s0, 3, 5, 0xafaeadac, 0xafae)

#if __riscv_xlen == 64
  MISMATCHED_STORE_TEST(99,  sd, lb,  s0, 1, 7, 0xb7b6b5b4b3b2b1b0, SEXT(0xb6, 8))
  MISMATCHED_STORE_TEST(100, sd, lbu, s0, 2, 3, 0xbfbebdbcbbbab9b8, 0xb9)
  MISMATCHED_STORE_TEST(101, sd, lh,  s0, 3, 9, 0xc7c6c5c4c3c2c1c0, SEXT(0xc7c6, 16))
  MISMATCHED_STORE_TEST(102, sd, lhu, s0, 4, 5, 0xcfcecdcccbcac9c8, 0xcac9)
  MISMATCHED_STORE_TEST(103, sd, lw,  s0, 5, 9, 0xd7d6d5d4d3d2d1d0, SEXT(0xd7d6d5d4, 32))
  MISMATCHED_STORE_TEST(104, sd, lw,  s0, 6, 8, 0xdfdedddcdbdad9d8, SEXT(0xdddcdbda, 32))
  MISMATCHED_STORE_TEST(105, sd, lwu, s0, 7, 8, 0xe7e6e5e4e3e2e1e0, 0xe4e3e2e1)
#endif

# octword crossing
  MISMATCHED_STORE_TEST(106, sh, lb,  s0, 31, 31, 0xe9e8, SEXT(0xe8, 8))
  MISMATCHED_STORE_TEST(107, sh, lb,  s0, 31, 32, 0xebea, SEXT(0xeb, 8))
  MISMATCHED_STORE_TEST(108, sh, lbu, s0, 31, 31, 0xedec, 0xec)
  MISMATCHED_STORE_TEST(109, sh, lbu, s0, 31, 32, 0xefee, 0xef)
  MISMATCHED_STORE_TEST(110, sw, lb,  s0, 29, 29, 0xf3f2f1f0, SEXT(0xf0, 8))
  MISMATCHED_STORE_TEST(111, sw, lbu, s0, 30, 32, 0xf7f6f5f4, 0xf6)
  MISMATCHED_STORE_TEST(112, sw, lh,  s0, 29, 31, 0xfbfaf9f8, SEXT(0xfbfa, 16))
  MISMATCHED_STORE_TEST(113, sw, lhu, s0, 31, 31, 0xfffefdfc, 0xfdfc)

#if __riscv_xlen == 64
  MISMATCHED_STORE_TEST(114, sd, lb,  s0, 25, 32, 0x0706050403020100, SEXT(0x07, 8))
  MISMATCHED_STORE_TEST(115, sd, lbu, s0, 26, 33, 0x0f0e0d0c0b0a0908, 0x0f)
  MISMATCHED_STORE_TEST(116, sd, lh,  s0, 27, 31, 0x1716151413121110, SEXT(0x1514, 16))
  MISMATCHED_STORE_TEST(117, sd, lhu, s0, 28, 31, 0x1f1e1d1c1b1a1918, 0x1c1b)
  MISMATCHED_STORE_TEST(118, sd, lw,  s0, 29, 29, 0x2726252423222120, SEXT(0x23222120, 32))
  MISMATCHED_STORE_TEST(119, sd, lw,  s0, 30, 30, 0x2f2e2d2c2b2a2928, SEXT(0x2b2a2928, 32))
  MISMATCHED_STORE_TEST(120, sd, lwu, s0, 31, 31, 0x3736353433323130, 0x33323130)
#endif

# cacheline crossing
  MISMATCHED_STORE_TEST(121, sh, lb,  s0, 63, 63, 0x4948, SEXT(0x48, 8))
  MISMATCHED_STORE_TEST(122, sh, lb,  s0, 63, 64, 0x4b4a, SEXT(0x4b, 8))
  MISMATCHED_STORE_TEST(123, sh, lbu, s0, 63, 63, 0x4d4c, 0x4c)
  MISMATCHED_STORE_TEST(124, sh, lbu, s0, 63, 64, 0x4f4e, 0x4f)
  MISMATCHED_STORE_TEST(125, sw, lb,  s0, 61, 61, 0x53525150, SEXT(0x50, 8))
  MISMATCHED_STORE_TEST(126, sw, lbu, s0, 62, 64, 0x57565554, 0x56)
  MISMATCHED_STORE_TEST(127, sw, lh,  s0, 61, 63, 0x5b5a5958, SEXT(0x5b5a, 16))
  MISMATCHED_STORE_TEST(128, sw, lhu, s0, 63, 63, 0x5f5e5d5c, 0x5d5c)

#if __riscv_xlen == 64
  MISMATCHED_STORE_TEST(129, sd, lb,  s0, 57, 64, 0x6766656463626160, SEXT(0x67, 8))
  MISMATCHED_STORE_TEST(130, sd, lbu, s0, 58, 65, 0x6f6e6d6c6b6a6968, 0x6f)
  MISMATCHED_STORE_TEST(131, sd, lh,  s0, 59, 63, 0x7776757473727170, SEXT(0x7574, 16))
  MISMATCHED_STORE_TEST(132, sd, lhu, s0, 60, 63, 0x7f7e7d7c7b7a7978, 0x7c7b)
  MISMATCHED_STORE_TEST(133, sd, lw,  s0, 61, 61, 0x8786858483828180, SEXT(0x83828180, 32))
  MISMATCHED_STORE_TEST(134, sd, lw,  s0, 62, 62, 0x8f8e8d8c8b8a8988, SEXT(0x8b8a8988, 32))
  MISMATCHED_STORE_TEST(135, sd, lwu, s0, 63, 63, 0x9796959493929190, 0x93929190)
#endif

/* Memory contents at this point should be:
.word 0x10080000
.word 0x30282018
.word 0x34333231
.word 0x0f373635
.word 0x13121110
.word 0x17161514
.word 0x10080018
.word 0x30282018

.word 0x34333231
.word 0x27373635
.word 0x2b2a2928
.word 0x2f2e2d2c
.word 0x33323130
.word 0x37363534
.word 0x70686038
.word 0x90888078

.word 0x94939291
.word 0x47979695
.word 0x4b4a4948
.word 0x4f4e4d4c
.word 0x53525150
.word 0x57565554
.word 0x5b5a5958
.word 0x5f5e5d5c
.word 0x63626160
.word 0x67666564
.word 0x6b6a6968
.word 0x6f6e6d6c
.word 0x73727170
.word 0x77767574
.word 0x7b7a7978
.word 0x7f7e7d7c
*/

/* Check that a misaligned store writes the correct value, checked by a wider load. */

#if __riscv_xlen == 64
# within quadword
  MISMATCHED_STORE_TEST(136, sb, lh,  s0, 1, 1, 0x98, SEXT(0xb898, 16))
  MISMATCHED_STORE_TEST(137, sb, lhu, s0, 2, 1, 0x99, 0x9998)
  MISMATCHED_STORE_TEST(138, sh, lw,  s0, 1, 1, 0x9b9a, SEXT(0xc8c09b9a, 32))
  MISMATCHED_STORE_TEST(139, sh, lw,  s0, 3, 2, 0x9d9c, SEXT(0xd09d9c9b, 32))
  MISMATCHED_STORE_TEST(140, sh, lw,  s0, 5, 3, 0x9f9e, SEXT(0x9f9e9d9c, 32))

  MISMATCHED_STORE_TEST(141, sb, lwu, s0, 2, 1, 0xa0, 0x9d9ca09a)
  MISMATCHED_STORE_TEST(142, sh, lwu, s0, 3, 2, 0xa2a1, 0x9ea2a1a0)
  MISMATCHED_STORE_TEST(143, sh, lwu, s0, 5, 3, 0xa4a3, 0xa4a3a2a1)

  MISMATCHED_STORE_TEST(144, sb, ld, s0, 2,  1, 0xa5, 0xe1e0a4a3a2a1a59a)
  MISMATCHED_STORE_TEST(145, sh, ld, s0, 7,  2, 0xa7a6, 0xe2a7a6a4a3a2a1a5)
  MISMATCHED_STORE_TEST(146, sh, ld, s0, 9,  3, 0xa9a8, 0xa9a8a7a6a4a3a2a1)
  MISMATCHED_STORE_TEST(147, sw, ld, s0, 5,  4, 0xadacabaa, 0xe4a9a8adacabaaa2)
  MISMATCHED_STORE_TEST(148, sw, ld, s0, 7,  5, 0xb1b0afae, 0xe5e4b1b0afaeabaa)
  MISMATCHED_STORE_TEST(149, sw, ld, s0, 9,  6, 0xb5b4b3b2, 0xe6b5b4b3b2afaeab)
  MISMATCHED_STORE_TEST(150, sw, ld, s0, 11, 7, 0xb9b8b7b6, 0xb9b8b7b6b3b2afae)

# octword crossing
  MISMATCHED_STORE_TEST(151, sb, lh,  s0, 31, 31, 0xba, SEXT(0x31ba, 16))
  MISMATCHED_STORE_TEST(152, sb, lhu, s0, 32, 31, 0xbb, 0xbbba)
  MISMATCHED_STORE_TEST(153, sh, lw,  s0, 30, 30, 0xbdbc, SEXT(0x32bbbdbc, 32))
  MISMATCHED_STORE_TEST(154, sh, lw,  s0, 31, 30, 0xbfbe, SEXT(0x32bfbebc, 32))
  MISMATCHED_STORE_TEST(155, sh, lw,  s0, 32, 30, 0xc1c0, SEXT(0xc1c0bebc, 32))

  MISMATCHED_STORE_TEST(156, sb, lwu, s0, 32, 31, 0xc2, 0x33c1c2be)
  MISMATCHED_STORE_TEST(157, sh, lwu, s0, 31, 29, 0xc4c3, 0xc4c3bc20)
  MISMATCHED_STORE_TEST(158, sh, lwu, s0, 32, 30, 0xc6c5, 0xc6c5c3bc)

  MISMATCHED_STORE_TEST(159, sb, ld, s0, 32, 25, 0xc7, 0xc7c3bc2018100800)
  MISMATCHED_STORE_TEST(160, sh, ld, s0, 31, 26, 0xc9c8, 0xc6c9c8bc20181008)
  MISMATCHED_STORE_TEST(161, sh, ld, s0, 31, 27, 0xcbca, 0x33c6cbcabc201810)
  MISMATCHED_STORE_TEST(162, sw, ld, s0, 32, 28, 0xcfcecdcc, 0xcfcecdcccabc2018)
  MISMATCHED_STORE_TEST(163, sw, ld, s0, 31, 29, 0xd3d2d1d0, 0x35cfd3d2d1d0bc20)
  MISMATCHED_STORE_TEST(164, sw, ld, s0, 30, 30, 0xd7d6d5d4, 0x3635cfd3d7d6d5d4)
  MISMATCHED_STORE_TEST(165, sw, ld, s0, 29, 31, 0xdbdad9d8, 0x373635cfd3d7dbda)

# cacheline crossing
  MISMATCHED_STORE_TEST(166, sb, lh,  s0, 63, 63, 0xdc, SEXT(0x91dc, 16))
  MISMATCHED_STORE_TEST(167, sb, lhu, s0, 64, 63, 0xdd, 0xdddc)
  MISMATCHED_STORE_TEST(168, sh, lw,  s0, 62, 62, 0xdfde, SEXT(0x92dddfde, 32))
  MISMATCHED_STORE_TEST(169, sh, lw,  s0, 63, 62, 0xe1e0, SEXT(0x92e1e0de, 32))
  MISMATCHED_STORE_TEST(170, sh, lw,  s0, 64, 62, 0xe3e2, SEXT(0xe3e2e0de, 32))

  MISMATCHED_STORE_TEST(171, sb, lwu, s0, 64, 63, 0xe4, 0x93e3e4e0)
  MISMATCHED_STORE_TEST(172, sh, lwu, s0, 63, 61, 0xe6e5, 0xe6e5de80)
  MISMATCHED_STORE_TEST(173, sh, lwu, s0, 64, 62, 0xe8e7, 0xe8e7e5de)

  MISMATCHED_STORE_TEST(174, sb, ld, s0, 64, 57, 0xe9, 0xe9e5de8078706860)
  MISMATCHED_STORE_TEST(175, sh, ld, s0, 63, 58, 0xebea, 0xe8ebeade80787068)
  MISMATCHED_STORE_TEST(176, sh, ld, s0, 63, 59, 0xedec, 0x93e8edecde807870)
  MISMATCHED_STORE_TEST(177, sw, ld, s0, 64, 60, 0xf1f0efee, 0xf1f0efeeecde8078)
  MISMATCHED_STORE_TEST(178, sw, ld, s0, 63, 61, 0xf5f4f3f2, 0x95f1f5f4f3f2de80)
  MISMATCHED_STORE_TEST(179, sw, ld, s0, 62, 62, 0xf9f8f7f6, 0x9695f1f5f9f8f7f6)
  MISMATCHED_STORE_TEST(180, sw, ld, s0, 61, 63, 0xfdfcfbfa, 0x979695f1f5f9fdfc)
#endif

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

data:
  .align 3

.word 0x03020100
.word 0x07060504
.word 0x0b0a0908
.word 0x0f0e0d0c
.word 0x13121110
.word 0x17161514
.word 0x1b1a1918
.word 0x1f1e1d1c
.word 0x23222120
.word 0x27262524
.word 0x2b2a2928
.word 0x2f2e2d2c
.word 0x33323130
.word 0x37363534
.word 0x3b3a3938
.word 0x3f3e3d3c

.word 0x43424140
.word 0x47464544
.word 0x4b4a4948
.word 0x4f4e4d4c
.word 0x53525150
.word 0x57565554
.word 0x5b5a5958
.word 0x5f5e5d5c
.word 0x63626160
.word 0x67666564
.word 0x6b6a6968
.word 0x6f6e6d6c
.word 0x73727170
.word 0x77767574
.word 0x7b7a7978
.word 0x7f7e7d7c

.fill 0xff, 1, 80


  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_or -->

# rv32ui Test: `OR`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **26**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_SRC1_EQ_DEST` | rd == rs1 hazard: source register is also destination. RegFile must handle read-... |
| 7 | `TEST_RR_SRC2_EQ_DEST` | rd == rs2 hazard: source register 2 is also destination. RegFile must handle rea... |
| 8 | `TEST_RR_SRC12_EQ_DEST` | rd == rs1 == rs2: all three refer to same register. Tests double-alias read-befo... |
| 9 | `TEST_RR_DEST_BYPASS` | NOP cycles inserted between instruction and result check. Tests that pipeline (e... |
| ... | ... | (18 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xff0fff0f",
    "rs1_value": "0xff00ff00"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfff0fff0",
    "rs1_value": "0x0ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0fff0fff",
    "rs1_value": "0x00ff00ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xf0fff0ff",
    "rs1_value": "0xf00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# or.S
#-----------------------------------------------------------------------------
#
# Test or instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, or, 0xf0fff0ff, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_EQ_DEST( 8, or, 0xff00ff00, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, or, 0xff00ff00, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, or, 0x00ff00ff, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, or, 0 );
  TEST_RR_ZERODEST( 27, or, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_ori -->

# rv32ui Test: `ORI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **13**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_SRC1_EQ_DEST` | I-type with rd == rs1. RegFile must handle read-before-write for immediate instr... |
| 7 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 8 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 9 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| ... | ... | (5 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffff0f",
    "rs1_value": "0xffffffffff00ff00"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000000ff00ff0",
    "rs1_value": "0x000000000ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000ff07ff",
    "rs1_value": "0x0000000000ff00ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffff00ff0ff",
    "rs1_value": "0xfffffffff00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# ori.S
#-----------------------------------------------------------------------------
#
# Test ori instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, ori, 0xffffffffffffff0f, 0xffffffffff00ff00, 0xf0f );
  TEST_IMM_OP( 3, ori, 0x000000000ff00ff0, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, ori, 0x0000000000ff07ff, 0x0000000000ff00ff, 0x70f );
  TEST_IMM_OP( 5, ori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, ori, 0xff00fff0, 0xff00ff00, 0x0f0 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, ori, 0x000000000ff00ff0, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 8,  1, ori, 0x0000000000ff07ff, 0x0000000000ff00ff, 0x70f );
  TEST_IMM_DEST_BYPASS( 9,  2, ori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  TEST_IMM_SRC1_BYPASS( 10, 0, ori, 0x000000000ff00ff0, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 11, 1, ori, 0xffffffffffffffff, 0x0000000000ff00ff, 0xf0f );
  TEST_IMM_SRC1_BYPASS( 12, 2, ori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  TEST_IMM_ZEROSRC1( 13, ori, 0x0f0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, ori, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sb -->

# rv32ui Test: `SB`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **22**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 3 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 4 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 5 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 6 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 7 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 8 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 9 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| ... | ... | (14 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_ST_OP`**: Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0xffffffffffffffaa",
    "base_label": "0"
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0x0000000000000000",
    "base_label": "1"
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0xffffffffffffefa0",
    "base_label": "2"
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0x000000000000000a",
    "base_label": "3"
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0xffffffffffffffaa",
    "base_label": "-3"
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0x0000000000000000",
    "base_label": "-2"
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0xffffffffffffffa0",
    "base_label": "-1"
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sb",
    "offset": "0x000000000000000a",
    "base_label": "0"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sb.S
#-----------------------------------------------------------------------------
#
# Test sb instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lb, sb, 0xffffffffffffffaa, 0, tdat );
  TEST_ST_OP( 3, lb, sb, 0x0000000000000000, 1, tdat );
  TEST_ST_OP( 4, lh, sb, 0xffffffffffffefa0, 2, tdat );
  TEST_ST_OP( 5, lb, sb, 0x000000000000000a, 3, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lb, sb, 0xffffffffffffffaa, -3, tdat8 );
  TEST_ST_OP( 7, lb, sb, 0x0000000000000000, -2, tdat8 );
  TEST_ST_OP( 8, lb, sb, 0xffffffffffffffa0, -1, tdat8 );
  TEST_ST_OP( 9, lb, sb, 0x000000000000000a, 0,  tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x78, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sb x2, 32(x4); \
    lb x5, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0xffffffffffffff98, \
    la  x1, tdat9; \
    li  x2, 0x00003098; \
    addi x1, x1, -6; \
    sb x2, 7(x1); \
    la  x4, tdat10; \
    lb x5, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lb, sb, 0xffffffffffffffdd, 0, tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lb, sb, 0xffffffffffffffcd, 1, tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lb, sb, 0xffffffffffffffcc, 2, tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lb, sb, 0xffffffffffffffbc, 3, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lb, sb, 0xffffffffffffffbb, 4, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lb, sb, 0xffffffffffffffab, 5, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lb, sb, 0x33, 0, tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lb, sb, 0x23, 1, tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lb, sb, 0x22, 2, tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lb, sb, 0x12, 3, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lb, sb, 0x11, 4, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lb, sb, 0x01, 5, tdat );

  li a0, 0xef
  la a1, tdat
  sb a0, 3(a1)

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xef
tdat2:  .byte 0xef
tdat3:  .byte 0xef
tdat4:  .byte 0xef
tdat5:  .byte 0xef
tdat6:  .byte 0xef
tdat7:  .byte 0xef
tdat8:  .byte 0xef
tdat9:  .byte 0xef
tdat10: .byte 0xef

RVTEST_DATA_END
```

---
<!-- rv32ui_sh -->

# rv32ui Test: `SH`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **22**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 3 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 4 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 5 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 6 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 7 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 8 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 9 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| ... | ... | (14 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_ST_OP`**: Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0x00000000000000aa",
    "base_label": "0"
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0xffffffffffffaa00",
    "base_label": "2"
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0xffffffffbeef0aa0",
    "base_label": "4"
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0xffffffffffffa00a",
    "base_label": "6"
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0x00000000000000aa",
    "base_label": "-6"
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0xffffffffffffaa00",
    "base_label": "-4"
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0x0000000000000aa0",
    "base_label": "-2"
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sh",
    "offset": "0xffffffffffffa00a",
    "base_label": "0"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sh.S
#-----------------------------------------------------------------------------
#
# Test sh instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lh, sh, 0x00000000000000aa, 0, tdat );
  TEST_ST_OP( 3, lh, sh, 0xffffffffffffaa00, 2, tdat );
  TEST_ST_OP( 4, lw, sh, 0xffffffffbeef0aa0, 4, tdat );
  TEST_ST_OP( 5, lh, sh, 0xffffffffffffa00a, 6, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lh, sh, 0x00000000000000aa, -6, tdat8 );
  TEST_ST_OP( 7, lh, sh, 0xffffffffffffaa00, -4, tdat8 );
  TEST_ST_OP( 8, lh, sh, 0x0000000000000aa0, -2, tdat8 );
  TEST_ST_OP( 9, lh, sh, 0xffffffffffffa00a, 0,  tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x5678, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sh x2, 32(x4); \
    lh x5, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0x3098, \
    la  x1, tdat9; \
    li  x2, 0x00003098; \
    addi x1, x1, -5; \
    sh x2, 7(x1); \
    la  x4, tdat10; \
    lh x5, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lh, sh, 0xffffffffffffccdd, 0,  tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lh, sh, 0xffffffffffffbccd, 2,  tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lh, sh, 0xffffffffffffbbcc, 4,  tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lh, sh, 0xffffffffffffabbc, 6, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lh, sh, 0xffffffffffffaabb, 8, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lh, sh, 0xffffffffffffdaab, 10, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lh, sh, 0x2233, 0,  tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lh, sh, 0x1223, 2,  tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lh, sh, 0x1122, 4,  tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lh, sh, 0x0112, 6, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lh, sh, 0x0011, 8, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lh, sh, 0x3001, 10, tdat );

  li a0, 0xbeef
  la a1, tdat
  sh a0, 6(a1)

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0xbeef
tdat2:  .half 0xbeef
tdat3:  .half 0xbeef
tdat4:  .half 0xbeef
tdat5:  .half 0xbeef
tdat6:  .half 0xbeef
tdat7:  .half 0xbeef
tdat8:  .half 0xbeef
tdat9:  .half 0xbeef
tdat10: .half 0xbeef

RVTEST_DATA_END
```

---
<!-- rv32ui_simple -->

# rv32ui Test: `SIMPLE`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **0**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# simple.S
#-----------------------------------------------------------------------------
#
# This is the most basic self checking test. If your simulator does not
# pass thiss then there is little chance that it will pass any of the
# more complicated self checking tests.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

RVTEST_PASS

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sll -->

# rv32ui Test: `SLL`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **45**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (37 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000001",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000002",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000080",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000004000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000080000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffffffe",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffff80",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffc000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000021212121",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000042424242",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000001090909080",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000084848484000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x1090909080000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000021212121",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000042424242",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000001090909080",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000084848484000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x8000000000000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 50,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x8000000000000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 51,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffff8000000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 52,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0909080000000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sll.S
#-----------------------------------------------------------------------------
#
# Test sll instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sll, 0x0000000000000001, 0x0000000000000001, 0  );
  TEST_RR_OP( 3,  sll, 0x0000000000000002, 0x0000000000000001, 1  );
  TEST_RR_OP( 4,  sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_OP( 5,  sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_OP( 6,  sll, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_RR_OP( 7,  sll, 0xffffffffffffffff, 0xffffffffffffffff, 0  );
  TEST_RR_OP( 8,  sll, 0xfffffffffffffffe, 0xffffffffffffffff, 1  );
  TEST_RR_OP( 9,  sll, 0xffffffffffffff80, 0xffffffffffffffff, 7  );
  TEST_RR_OP( 10, sll, 0xffffffffffffc000, 0xffffffffffffffff, 14 );
  TEST_RR_OP( 11, sll, 0xffffffff80000000, 0xffffffffffffffff, 31 );

  TEST_RR_OP( 12, sll, 0x0000000021212121, 0x0000000021212121, 0  );
  TEST_RR_OP( 13, sll, 0x0000000042424242, 0x0000000021212121, 1  );
  TEST_RR_OP( 14, sll, 0x0000001090909080, 0x0000000021212121, 7  );
  TEST_RR_OP( 15, sll, 0x0000084848484000, 0x0000000021212121, 14 );
  TEST_RR_OP( 16, sll, 0x1090909080000000, 0x0000000021212121, 31 );

  # Verify that shifts only use bottom six(rv64) or five(rv32) bits

  TEST_RR_OP( 17, sll, 0x0000000021212121, 0x0000000021212121, 0xffffffffffffffc0 );
  TEST_RR_OP( 18, sll, 0x0000000042424242, 0x0000000021212121, 0xffffffffffffffc1 );
  TEST_RR_OP( 19, sll, 0x0000001090909080, 0x0000000021212121, 0xffffffffffffffc7 );
  TEST_RR_OP( 20, sll, 0x0000084848484000, 0x0000000021212121, 0xffffffffffffffce );

#if __riscv_xlen == 64
  TEST_RR_OP( 21, sll, 0x8000000000000000, 0x0000000021212121, 0xffffffffffffffff );
  TEST_RR_OP( 50, sll, 0x8000000000000000, 0x0000000000000001, 63 );
  TEST_RR_OP( 51, sll, 0xffffff8000000000, 0xffffffffffffffff, 39 );
  TEST_RR_OP( 52, sll, 0x0909080000000000, 0x0000000021212121, 43 );
#endif

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC2_EQ_DEST( 23, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, sll, 24, 3 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_DEST_BYPASS( 26, 1, sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, sll, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, sll, 0x0000000080000000, 0x0000000000000001, 31 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, sll, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, sll, 0x0000000080000000, 0x0000000000000001, 31 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, sll, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, sll, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, sll, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_RR_ZEROSRC1( 40, sll, 0, 15 );
  TEST_RR_ZEROSRC2( 41, sll, 32, 32 );
  TEST_RR_ZEROSRC12( 42, sll, 0 );
  TEST_RR_ZERODEST( 43, sll, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_slli -->

# rv32ui Test: `SLLI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **27**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 7 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 8 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 9 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| ... | ... | (19 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000000001",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000000002",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000000080",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000004000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000080000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffffffffffe",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffff80",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffc000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000021212121",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000042424242",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000001090909080",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000084848484000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x1090909080000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 50,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x8000000000000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 51,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffff8000000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 52,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0909080000000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slli.S
#-----------------------------------------------------------------------------
#
# Test slli instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  slli, 0x0000000000000001, 0x0000000000000001, 0  );
  TEST_IMM_OP( 3,  slli, 0x0000000000000002, 0x0000000000000001, 1  );
  TEST_IMM_OP( 4,  slli, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_IMM_OP( 5,  slli, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_IMM_OP( 6,  slli, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_IMM_OP( 7,  slli, 0xffffffffffffffff, 0xffffffffffffffff, 0  );
  TEST_IMM_OP( 8,  slli, 0xfffffffffffffffe, 0xffffffffffffffff, 1  );
  TEST_IMM_OP( 9,  slli, 0xffffffffffffff80, 0xffffffffffffffff, 7  );
  TEST_IMM_OP( 10, slli, 0xffffffffffffc000, 0xffffffffffffffff, 14 );
  TEST_IMM_OP( 11, slli, 0xffffffff80000000, 0xffffffffffffffff, 31 );

  TEST_IMM_OP( 12, slli, 0x0000000021212121, 0x0000000021212121, 0  );
  TEST_IMM_OP( 13, slli, 0x0000000042424242, 0x0000000021212121, 1  );
  TEST_IMM_OP( 14, slli, 0x0000001090909080, 0x0000000021212121, 7  );
  TEST_IMM_OP( 15, slli, 0x0000084848484000, 0x0000000021212121, 14 );
  TEST_IMM_OP( 16, slli, 0x1090909080000000, 0x0000000021212121, 31 );

#if __riscv_xlen == 64
  TEST_IMM_OP( 50, slli, 0x8000000000000000, 0x0000000000000001, 63 );
  TEST_IMM_OP( 51, slli, 0xffffff8000000000, 0xffffffffffffffff, 39 );
  TEST_IMM_OP( 52, slli, 0x0909080000000000, 0x0000000021212121, 43 );
#endif

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, slli, 0x00000080, 0x00000001, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, slli, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_IMM_DEST_BYPASS( 19, 1, slli, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_IMM_DEST_BYPASS( 20, 2, slli, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_IMM_SRC1_BYPASS( 21, 0, slli, 0x0000000000000080, 0x0000000000000001, 7  );
  TEST_IMM_SRC1_BYPASS( 22, 1, slli, 0x0000000000004000, 0x0000000000000001, 14 );
  TEST_IMM_SRC1_BYPASS( 23, 2, slli, 0x0000000080000000, 0x0000000000000001, 31 );

  TEST_IMM_ZEROSRC1( 24, slli, 0, 31 );
  TEST_IMM_ZERODEST( 25, slli, 33, 20 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_slt -->

# rv32ui Test: `SLT`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **37**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (29 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000007"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slt.S
#-----------------------------------------------------------------------------
#
# Test slt instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  slt, 0, 0x0000000000000000, 0x0000000000000000 );
  TEST_RR_OP( 3,  slt, 0, 0x0000000000000001, 0x0000000000000001 );
  TEST_RR_OP( 4,  slt, 1, 0x0000000000000003, 0x0000000000000007 );
  TEST_RR_OP( 5,  slt, 0, 0x0000000000000007, 0x0000000000000003 );

  TEST_RR_OP( 6,  slt, 0, 0x0000000000000000, 0xffffffffffff8000 );
  TEST_RR_OP( 7,  slt, 1, 0xffffffff80000000, 0x0000000000000000 );
  TEST_RR_OP( 8,  slt, 1, 0xffffffff80000000, 0xffffffffffff8000 );

  TEST_RR_OP( 9,  slt, 1, 0x0000000000000000, 0x0000000000007fff );
  TEST_RR_OP( 10, slt, 0, 0x000000007fffffff, 0x0000000000000000 );
  TEST_RR_OP( 11, slt, 0, 0x000000007fffffff, 0x0000000000007fff );

  TEST_RR_OP( 12, slt, 1, 0xffffffff80000000, 0x0000000000007fff );
  TEST_RR_OP( 13, slt, 0, 0x000000007fffffff, 0xffffffffffff8000 );

  TEST_RR_OP( 14, slt, 0, 0x0000000000000000, 0xffffffffffffffff );
  TEST_RR_OP( 15, slt, 1, 0xffffffffffffffff, 0x0000000000000001 );
  TEST_RR_OP( 16, slt, 0, 0xffffffffffffffff, 0xffffffffffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 17, slt, 0, 14, 13 );
  TEST_RR_SRC2_EQ_DEST( 18, slt, 1, 11, 13 );
  TEST_RR_SRC12_EQ_DEST( 19, slt, 0, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 20, 0, slt, 1, 11, 13 );
  TEST_RR_DEST_BYPASS( 21, 1, slt, 0, 14, 13 );
  TEST_RR_DEST_BYPASS( 22, 2, slt, 1, 12, 13 );

  TEST_RR_SRC12_BYPASS( 23, 0, 0, slt, 0, 14, 13 );
  TEST_RR_SRC12_BYPASS( 24, 0, 1, slt, 1, 11, 13 );
  TEST_RR_SRC12_BYPASS( 25, 0, 2, slt, 0, 15, 13 );
  TEST_RR_SRC12_BYPASS( 26, 1, 0, slt, 1, 10, 13 );
  TEST_RR_SRC12_BYPASS( 27, 1, 1, slt, 0, 16, 13 );
  TEST_RR_SRC12_BYPASS( 28, 2, 0, slt, 1,  9, 13 );

  TEST_RR_SRC21_BYPASS( 29, 0, 0, slt, 0, 17, 13 );
  TEST_RR_SRC21_BYPASS( 30, 0, 1, slt, 1,  8, 13 );
  TEST_RR_SRC21_BYPASS( 31, 0, 2, slt, 0, 18, 13 );
  TEST_RR_SRC21_BYPASS( 32, 1, 0, slt, 1,  7, 13 );
  TEST_RR_SRC21_BYPASS( 33, 1, 1, slt, 0, 19, 13 );
  TEST_RR_SRC21_BYPASS( 34, 2, 0, slt, 1,  6, 13 );

  TEST_RR_ZEROSRC1( 35, slt, 0, -1 );
  TEST_RR_ZEROSRC2( 36, slt, 1, -1 );
  TEST_RR_ZEROSRC12( 37, slt, 0 );
  TEST_RR_ZERODEST( 38, slt, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_slti -->

# rv32ui Test: `SLTI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **24**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 7 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 8 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 9 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| ... | ... | (16 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000007"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slti.S
#-----------------------------------------------------------------------------
#
# Test slti instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  slti, 0, 0x0000000000000000, 0x000 );
  TEST_IMM_OP( 3,  slti, 0, 0x0000000000000001, 0x001 );
  TEST_IMM_OP( 4,  slti, 1, 0x0000000000000003, 0x007 );
  TEST_IMM_OP( 5,  slti, 0, 0x0000000000000007, 0x003 );

  TEST_IMM_OP( 6,  slti, 0, 0x0000000000000000, 0x800 );
  TEST_IMM_OP( 7,  slti, 1, 0xffffffff80000000, 0x000 );
  TEST_IMM_OP( 8,  slti, 1, 0xffffffff80000000, 0x800 );

  TEST_IMM_OP( 9,  slti, 1, 0x0000000000000000, 0x7ff );
  TEST_IMM_OP( 10, slti, 0, 0x000000007fffffff, 0x000 );
  TEST_IMM_OP( 11, slti, 0, 0x000000007fffffff, 0x7ff );

  TEST_IMM_OP( 12, slti, 1, 0xffffffff80000000, 0x7ff );
  TEST_IMM_OP( 13, slti, 0, 0x000000007fffffff, 0x800 );

  TEST_IMM_OP( 14, slti, 0, 0x0000000000000000, 0xfff );
  TEST_IMM_OP( 15, slti, 1, 0xffffffffffffffff, 0x001 );
  TEST_IMM_OP( 16, slti, 0, 0xffffffffffffffff, 0xfff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, slti, 1, 11, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, slti, 0, 15, 10 );
  TEST_IMM_DEST_BYPASS( 19, 1, slti, 1, 10, 16 );
  TEST_IMM_DEST_BYPASS( 20, 2, slti, 0, 16,  9 );

  TEST_IMM_SRC1_BYPASS( 21, 0, slti, 1, 11, 15 );
  TEST_IMM_SRC1_BYPASS( 22, 1, slti, 0, 17,  8 );
  TEST_IMM_SRC1_BYPASS( 23, 2, slti, 1, 12, 14 );

  TEST_IMM_ZEROSRC1( 24, slti, 0, 0xfff );
  TEST_IMM_ZERODEST( 25, slti, 0x00ff00ff, 0xfff );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sltiu -->

# rv32ui Test: `SLTIU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **24**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 7 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 8 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 9 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| ... | ... | (16 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x0000000000000007"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "1",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sltiu.S
#-----------------------------------------------------------------------------
#
# Test sltiu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  sltiu, 0, 0x0000000000000000, 0x000 );
  TEST_IMM_OP( 3,  sltiu, 0, 0x0000000000000001, 0x001 );
  TEST_IMM_OP( 4,  sltiu, 1, 0x0000000000000003, 0x007 );
  TEST_IMM_OP( 5,  sltiu, 0, 0x0000000000000007, 0x003 );

  TEST_IMM_OP( 6,  sltiu, 1, 0x0000000000000000, 0x800 );
  TEST_IMM_OP( 7,  sltiu, 0, 0xffffffff80000000, 0x000 );
  TEST_IMM_OP( 8,  sltiu, 1, 0xffffffff80000000, 0x800 );

  TEST_IMM_OP( 9,  sltiu, 1, 0x0000000000000000, 0x7ff );
  TEST_IMM_OP( 10, sltiu, 0, 0x000000007fffffff, 0x000 );
  TEST_IMM_OP( 11, sltiu, 0, 0x000000007fffffff, 0x7ff );

  TEST_IMM_OP( 12, sltiu, 0, 0xffffffff80000000, 0x7ff );
  TEST_IMM_OP( 13, sltiu, 1, 0x000000007fffffff, 0x800 );

  TEST_IMM_OP( 14, sltiu, 1, 0x0000000000000000, 0xfff );
  TEST_IMM_OP( 15, sltiu, 0, 0xffffffffffffffff, 0x001 );
  TEST_IMM_OP( 16, sltiu, 0, 0xffffffffffffffff, 0xfff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, sltiu, 1, 11, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, sltiu, 0, 15, 10 );
  TEST_IMM_DEST_BYPASS( 19, 1, sltiu, 1, 10, 16 );
  TEST_IMM_DEST_BYPASS( 20, 2, sltiu, 0, 16,  9 );

  TEST_IMM_SRC1_BYPASS( 21, 0, sltiu, 1, 11, 15 );
  TEST_IMM_SRC1_BYPASS( 22, 1, sltiu, 0, 17,  8 );
  TEST_IMM_SRC1_BYPASS( 23, 2, sltiu, 1, 12, 14 );

  TEST_IMM_ZEROSRC1( 24, sltiu, 1, 0xfff );
  TEST_IMM_ZERODEST( 25, sltiu, 0x00ff00ff, 0xfff );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sltu -->

# rv32ui Test: `SLTU`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **37**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (29 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x00000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x00000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x00000007"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x80000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0x80000000"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x7fffffff"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "1",
    "rs1_value": "0x00000000"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0xffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0",
    "rs1_value": "0xffffffff"
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sltu.S
#-----------------------------------------------------------------------------
#
# Test sltu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sltu, 0, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  sltu, 0, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  sltu, 1, 0x00000003, 0x00000007 );
  TEST_RR_OP( 5,  sltu, 0, 0x00000007, 0x00000003 );

  TEST_RR_OP( 6,  sltu, 1, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 7,  sltu, 0, 0x80000000, 0x00000000 );
  TEST_RR_OP( 8,  sltu, 1, 0x80000000, 0xffff8000 );

  TEST_RR_OP( 9,  sltu, 1, 0x00000000, 0x00007fff );
  TEST_RR_OP( 10, sltu, 0, 0x7fffffff, 0x00000000 );
  TEST_RR_OP( 11, sltu, 0, 0x7fffffff, 0x00007fff );

  TEST_RR_OP( 12, sltu, 0, 0x80000000, 0x00007fff );
  TEST_RR_OP( 13, sltu, 1, 0x7fffffff, 0xffff8000 );

  TEST_RR_OP( 14, sltu, 1, 0x00000000, 0xffffffff );
  TEST_RR_OP( 15, sltu, 0, 0xffffffff, 0x00000001 );
  TEST_RR_OP( 16, sltu, 0, 0xffffffff, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 17, sltu, 0, 14, 13 );
  TEST_RR_SRC2_EQ_DEST( 18, sltu, 1, 11, 13 );
  TEST_RR_SRC12_EQ_DEST( 19, sltu, 0, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 20, 0, sltu, 1, 11, 13 );
  TEST_RR_DEST_BYPASS( 21, 1, sltu, 0, 14, 13 );
  TEST_RR_DEST_BYPASS( 22, 2, sltu, 1, 12, 13 );

  TEST_RR_SRC12_BYPASS( 23, 0, 0, sltu, 0, 14, 13 );
  TEST_RR_SRC12_BYPASS( 24, 0, 1, sltu, 1, 11, 13 );
  TEST_RR_SRC12_BYPASS( 25, 0, 2, sltu, 0, 15, 13 );
  TEST_RR_SRC12_BYPASS( 26, 1, 0, sltu, 1, 10, 13 );
  TEST_RR_SRC12_BYPASS( 27, 1, 1, sltu, 0, 16, 13 );
  TEST_RR_SRC12_BYPASS( 28, 2, 0, sltu, 1,  9, 13 );

  TEST_RR_SRC21_BYPASS( 29, 0, 0, sltu, 0, 17, 13 );
  TEST_RR_SRC21_BYPASS( 30, 0, 1, sltu, 1,  8, 13 );
  TEST_RR_SRC21_BYPASS( 31, 0, 2, sltu, 0, 18, 13 );
  TEST_RR_SRC21_BYPASS( 32, 1, 0, sltu, 1,  7, 13 );
  TEST_RR_SRC21_BYPASS( 33, 1, 1, sltu, 0, 19, 13 );
  TEST_RR_SRC21_BYPASS( 34, 2, 0, sltu, 1,  6, 13 );

  TEST_RR_ZEROSRC1( 35, sltu, 1, -1 );
  TEST_RR_ZEROSRC2( 36, sltu, 0, -1 );
  TEST_RR_ZEROSRC12( 37, sltu, 0 );
  TEST_RR_ZERODEST( 38, sltu, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sra -->

# rv32ui Test: `SRA`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **42**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (34 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffc0000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffff000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffe0000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffff80000001"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000007fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000003fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000ffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000000001ffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff81818181",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffc0c0c0c0",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffff030303",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffe0606",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff81818181",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffc0c0c0c0",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffff030303",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffe0606",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sra.S
#-----------------------------------------------------------------------------
#
# Test sra instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sra, 0xffffffff80000000, 0xffffffff80000000, 0  );
  TEST_RR_OP( 3,  sra, 0xffffffffc0000000, 0xffffffff80000000, 1  );
  TEST_RR_OP( 4,  sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_OP( 5,  sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_OP( 6,  sra, 0xffffffffffffffff, 0xffffffff80000001, 31 );

  TEST_RR_OP( 7,  sra, 0x000000007fffffff, 0x000000007fffffff, 0  );
  TEST_RR_OP( 8,  sra, 0x000000003fffffff, 0x000000007fffffff, 1  );
  TEST_RR_OP( 9,  sra, 0x0000000000ffffff, 0x000000007fffffff, 7  );
  TEST_RR_OP( 10, sra, 0x000000000001ffff, 0x000000007fffffff, 14 );
  TEST_RR_OP( 11, sra, 0x0000000000000000, 0x000000007fffffff, 31 );

  TEST_RR_OP( 12, sra, 0xffffffff81818181, 0xffffffff81818181, 0  );
  TEST_RR_OP( 13, sra, 0xffffffffc0c0c0c0, 0xffffffff81818181, 1  );
  TEST_RR_OP( 14, sra, 0xffffffffff030303, 0xffffffff81818181, 7  );
  TEST_RR_OP( 15, sra, 0xfffffffffffe0606, 0xffffffff81818181, 14 );
  TEST_RR_OP( 16, sra, 0xffffffffffffffff, 0xffffffff81818181, 31 );

  # Verify that shifts only use bottom six(rv64) or five(rv32) bits

  TEST_RR_OP( 17, sra, 0xffffffff81818181, 0xffffffff81818181, 0xffffffffffffffc0 );
  TEST_RR_OP( 18, sra, 0xffffffffc0c0c0c0, 0xffffffff81818181, 0xffffffffffffffc1 );
  TEST_RR_OP( 19, sra, 0xffffffffff030303, 0xffffffff81818181, 0xffffffffffffffc7 );
  TEST_RR_OP( 20, sra, 0xfffffffffffe0606, 0xffffffff81818181, 0xffffffffffffffce );
  TEST_RR_OP( 21, sra, 0xffffffffffffffff, 0xffffffff81818181, 0xffffffffffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_SRC2_EQ_DEST( 23, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, sra, 0, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_DEST_BYPASS( 26, 1, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, sra, 0xffffffffffffffff, 0xffffffff80000000, 31 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, sra, 0xffffffffffffffff, 0xffffffff80000000, 31 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, sra, 0xffffffffffffffff, 0xffffffff80000000, 31 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, sra, 0xffffffffffffffff, 0xffffffff80000000, 31 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, sra, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, sra, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, sra, 0xffffffffffffffff, 0xffffffff80000000, 31 );

  TEST_RR_ZEROSRC1( 40, sra, 0, 15 );
  TEST_RR_ZEROSRC2( 41, sra, 32, 32 );
  TEST_RR_ZEROSRC12( 42, sra, 0 );
  TEST_RR_ZERODEST( 43, sra, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_srai -->

# rv32ui Test: `SRAI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **24**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 7 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 8 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 9 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| ... | ... | (16 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffff8000000000",
    "rs1_value": "0xffffff8000000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffc0000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffff000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffffffe0000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffff80000001"
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000007fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000003fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000ffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000000001ffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffff81818181",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffc0c0c0c0",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffff030303",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffffffe0606",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffffffffff",
    "rs1_value": "0xffffffff81818181"
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srai.S
#-----------------------------------------------------------------------------
#
# Test srai instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  srai, 0xffffff8000000000, 0xffffff8000000000, 0  );
  TEST_IMM_OP( 3,  srai, 0xffffffffc0000000, 0xffffffff80000000, 1  );
  TEST_IMM_OP( 4,  srai, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_IMM_OP( 5,  srai, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_IMM_OP( 6,  srai, 0xffffffffffffffff, 0xffffffff80000001, 31 );

  TEST_IMM_OP( 7,  srai, 0x000000007fffffff, 0x000000007fffffff, 0  );
  TEST_IMM_OP( 8,  srai, 0x000000003fffffff, 0x000000007fffffff, 1  );
  TEST_IMM_OP( 9,  srai, 0x0000000000ffffff, 0x000000007fffffff, 7  );
  TEST_IMM_OP( 10, srai, 0x000000000001ffff, 0x000000007fffffff, 14 );
  TEST_IMM_OP( 11, srai, 0x0000000000000000, 0x000000007fffffff, 31 );

  TEST_IMM_OP( 12, srai, 0xffffffff81818181, 0xffffffff81818181, 0  );
  TEST_IMM_OP( 13, srai, 0xffffffffc0c0c0c0, 0xffffffff81818181, 1  );
  TEST_IMM_OP( 14, srai, 0xffffffffff030303, 0xffffffff81818181, 7  );
  TEST_IMM_OP( 15, srai, 0xfffffffffffe0606, 0xffffffff81818181, 14 );
  TEST_IMM_OP( 16, srai, 0xffffffffffffffff, 0xffffffff81818181, 31 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, srai, 0xffffffffff000000, 0xffffffff80000000, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, srai, 0xffffffffff000000, 0xffffffff80000000, 7  );
  TEST_IMM_DEST_BYPASS( 19, 1, srai, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_IMM_DEST_BYPASS( 20, 2, srai, 0xffffffffffffffff, 0xffffffff80000001, 31 );

  TEST_IMM_SRC1_BYPASS( 21, 0, srai, 0xffffffffff000000, 0xffffffff80000000, 7 );
  TEST_IMM_SRC1_BYPASS( 22, 1, srai, 0xfffffffffffe0000, 0xffffffff80000000, 14 );
  TEST_IMM_SRC1_BYPASS( 23, 2, srai, 0xffffffffffffffff, 0xffffffff80000001, 31 );

  TEST_IMM_ZEROSRC1( 24, srai, 0, 4 );
  TEST_IMM_ZERODEST( 25, srai, 33, 10 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_srl -->

# rv32ui Test: `SRL`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **42**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_SRL` | See test_macros.h for full definition.... |
| 3 | `TEST_SRL` | See test_macros.h for full definition.... |
| 4 | `TEST_SRL` | See test_macros.h for full definition.... |
| 5 | `TEST_SRL` | See test_macros.h for full definition.... |
| 6 | `TEST_SRL` | See test_macros.h for full definition.... |
| 7 | `TEST_SRL` | See test_macros.h for full definition.... |
| 8 | `TEST_SRL` | See test_macros.h for full definition.... |
| 9 | `TEST_SRL` | See test_macros.h for full definition.... |
| ... | ... | (34 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 4,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 7,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 8,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 9,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_SRL",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000021212121",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000010909090",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000424242",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000008484",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0x0000000021212121"
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srl.S
#-----------------------------------------------------------------------------
#
# Test srl instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

#define TEST_SRL(n, v, a) \
  TEST_RR_OP(n, srl, ((v) & ((1 << (__riscv_xlen-1) << 1) - 1)) >> (a), v, a)

  TEST_SRL( 2,  0xffffffff80000000, 0  );
  TEST_SRL( 3,  0xffffffff80000000, 1  );
  TEST_SRL( 4,  0xffffffff80000000, 7  );
  TEST_SRL( 5,  0xffffffff80000000, 14 );
  TEST_SRL( 6,  0xffffffff80000001, 31 );

  TEST_SRL( 7,  0xffffffffffffffff, 0  );
  TEST_SRL( 8,  0xffffffffffffffff, 1  );
  TEST_SRL( 9,  0xffffffffffffffff, 7  );
  TEST_SRL( 10, 0xffffffffffffffff, 14 );
  TEST_SRL( 11, 0xffffffffffffffff, 31 );

  TEST_SRL( 12, 0x0000000021212121, 0  );
  TEST_SRL( 13, 0x0000000021212121, 1  );
  TEST_SRL( 14, 0x0000000021212121, 7  );
  TEST_SRL( 15, 0x0000000021212121, 14 );
  TEST_SRL( 16, 0x0000000021212121, 31 );

  # Verify that shifts only use bottom six(rv64) or five(rv32) bits

  TEST_RR_OP( 17, srl, 0x0000000021212121, 0x0000000021212121, 0xffffffffffffffc0 );
  TEST_RR_OP( 18, srl, 0x0000000010909090, 0x0000000021212121, 0xffffffffffffffc1 );
  TEST_RR_OP( 19, srl, 0x0000000000424242, 0x0000000021212121, 0xffffffffffffffc7 );
  TEST_RR_OP( 20, srl, 0x0000000000008484, 0x0000000021212121, 0xffffffffffffffce );
  TEST_RR_OP( 21, srl, 0x0000000000000000, 0x0000000021212121, 0xffffffffffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_SRC2_EQ_DEST( 23, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, srl, 0, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_DEST_BYPASS( 26, 1, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, srl, 0x00000001, 0x80000000, 31 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, srl, 0x00000001, 0x80000000, 31 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, srl, 0x00000001, 0x80000000, 31 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, srl, 0x00000001, 0x80000000, 31 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, srl, 0x01000000, 0x80000000, 7  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, srl, 0x00020000, 0x80000000, 14 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, srl, 0x00000001, 0x80000000, 31 );

  TEST_RR_ZEROSRC1( 40, srl, 0, 15 );
  TEST_RR_ZEROSRC2( 41, srl, 32, 32 );
  TEST_RR_ZEROSRC12( 42, srl, 0 );
  TEST_RR_ZERODEST( 43, srl, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_srli -->

# rv32ui Test: `SRLI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **24**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 3 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 4 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 5 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 6 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 7 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 8 | `TEST_SRLI` | See test_macros.h for full definition.... |
| 9 | `TEST_SRLI` | See test_macros.h for full definition.... |
| ... | ... | (16 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 4,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 7,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 8,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 9,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_SRLI",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srli.S
#-----------------------------------------------------------------------------
#
# Test srli instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

#define TEST_SRLI(n, v, a) \
  TEST_IMM_OP(n, srli, ((v) & ((1 << (__riscv_xlen-1) << 1) - 1)) >> (a), v, a)

  TEST_SRLI( 2,  0xffffffff80000000, 0  );
  TEST_SRLI( 3,  0xffffffff80000000, 1  );
  TEST_SRLI( 4,  0xffffffff80000000, 7  );
  TEST_SRLI( 5,  0xffffffff80000000, 14 );
  TEST_SRLI( 6,  0xffffffff80000001, 31 );

  TEST_SRLI( 7,  0xffffffffffffffff, 0  );
  TEST_SRLI( 8,  0xffffffffffffffff, 1  );
  TEST_SRLI( 9,  0xffffffffffffffff, 7  );
  TEST_SRLI( 10, 0xffffffffffffffff, 14 );
  TEST_SRLI( 11, 0xffffffffffffffff, 31 );

  TEST_SRLI( 12, 0x0000000021212121, 0  );
  TEST_SRLI( 13, 0x0000000021212121, 1  );
  TEST_SRLI( 14, 0x0000000021212121, 7  );
  TEST_SRLI( 15, 0x0000000021212121, 14 );
  TEST_SRLI( 16, 0x0000000021212121, 31 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, srli, 0x01000000, 0x80000000, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, srli, 0x01000000, 0x80000000, 7  );
  TEST_IMM_DEST_BYPASS( 19, 1, srli, 0x00020000, 0x80000000, 14 );
  TEST_IMM_DEST_BYPASS( 20, 2, srli, 0x00000001, 0x80000001, 31 );

  TEST_IMM_SRC1_BYPASS( 21, 0, srli, 0x01000000, 0x80000000, 7  );
  TEST_IMM_SRC1_BYPASS( 22, 1, srli, 0x00020000, 0x80000000, 14 );
  TEST_IMM_SRC1_BYPASS( 23, 2, srli, 0x00000001, 0x80000001, 31 );

  TEST_IMM_ZEROSRC1( 24, srli, 0, 4 );
  TEST_IMM_ZERODEST( 25, srli, 33, 10 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_st_ld -->

# rv32ui Test: `ST_LD`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **69**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 3 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 4 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 5 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 6 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 7 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 8 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| 9 | `TEST_ST_LD_BYPASS` | See test_macros.h for full definition.... |
| ... | ... | (61 more test cases) |

## Key RTL Invariants This Test Suite Enforces


## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 10,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 24,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 25,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 26,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 27,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 28,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 29,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 30,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 31,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 32,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 33,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 34,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 35,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 36,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 37,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 38,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 39,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 40,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 41,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 42,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 43,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 44,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 45,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 46,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 47,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 48,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 49,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 50,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 51,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 52,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 53,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 54,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 55,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 56,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 57,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 58,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 59,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 60,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 61,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 62,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 63,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 64,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 65,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 66,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 67,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 68,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 69,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 70,
    "macro": "TEST_ST_LD_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# st_ld.S
#-----------------------------------------------------------------------------
#
# Test store and load instructions
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Bypassing Tests
  #-------------------------------------------------------------

  # Test sb and lb (signed byte)
  TEST_ST_LD_BYPASS(2,  lb,  sb, 0xffffffffffffffdd, 0, tdat );
  TEST_ST_LD_BYPASS(3,  lb,  sb, 0xffffffffffffffcd, 1, tdat );
  TEST_ST_LD_BYPASS(4,  lb,  sb, 0xffffffffffffffcc, 2, tdat );
  TEST_ST_LD_BYPASS(5,  lb,  sb, 0xffffffffffffffbc, 3, tdat );
  TEST_ST_LD_BYPASS(6,  lb,  sb, 0xffffffffffffffbb, 4, tdat );
  TEST_ST_LD_BYPASS(7,  lb,  sb, 0xffffffffffffffab, 5, tdat );

  TEST_ST_LD_BYPASS(8,  lb, sb, 0x33, 0, tdat );
  TEST_ST_LD_BYPASS(9,  lb, sb, 0x23, 1, tdat );
  TEST_ST_LD_BYPASS(10, lb, sb, 0x22, 2, tdat );
  TEST_ST_LD_BYPASS(11, lb, sb, 0x12, 3, tdat );
  TEST_ST_LD_BYPASS(12, lb, sb, 0x11, 4, tdat );
  TEST_ST_LD_BYPASS(13, lb, sb, 0x01, 5, tdat );

  # Test sb and lbu (unsigned byte)
  TEST_ST_LD_BYPASS(14, lbu, sb, 0x33, 0, tdat );
  TEST_ST_LD_BYPASS(15, lbu, sb, 0x23, 1, tdat );
  TEST_ST_LD_BYPASS(16, lbu, sb, 0x22, 2, tdat );
  TEST_ST_LD_BYPASS(17, lbu, sb, 0x12, 3, tdat );
  TEST_ST_LD_BYPASS(18, lbu, sb, 0x11, 4, tdat );
  TEST_ST_LD_BYPASS(19, lbu, sb, 0x01, 5, tdat );

  # Test sw and lw (signed word)
  TEST_ST_LD_BYPASS(20, lw, sw, 0xffffffffaabbccdd, 0,  tdat );
  TEST_ST_LD_BYPASS(21, lw, sw, 0xffffffffdaabbccd, 4,  tdat );
  TEST_ST_LD_BYPASS(22, lw, sw, 0xffffffffddaabbcc, 8,  tdat );
  TEST_ST_LD_BYPASS(23, lw, sw, 0xffffffffcddaabbc, 12, tdat );
  TEST_ST_LD_BYPASS(24, lw, sw, 0xffffffffccddaabb, 16, tdat );
  TEST_ST_LD_BYPASS(25, lw, sw, 0xffffffffbccddaab, 20, tdat );

  TEST_ST_LD_BYPASS(26, lw, sw, 0x00112233, 0,  tdat );
  TEST_ST_LD_BYPASS(27, lw, sw, 0x30011223, 4,  tdat );
  TEST_ST_LD_BYPASS(28, lw, sw, 0x33001122, 8,  tdat );
  TEST_ST_LD_BYPASS(29, lw, sw, 0x23300112, 12, tdat );
  TEST_ST_LD_BYPASS(30, lw, sw, 0x22330011, 16, tdat );
  TEST_ST_LD_BYPASS(31, lw, sw, 0x12233001, 20, tdat );

  # Test sh and lh (signed halfword)
  TEST_ST_LD_BYPASS(32, lh, sh, 0xffffffffffffccdd, 0, tdat );
  TEST_ST_LD_BYPASS(33, lh, sh, 0xffffffffffffbccd, 2, tdat );
  TEST_ST_LD_BYPASS(34, lh, sh, 0xffffffffffffbbcc, 4, tdat );
  TEST_ST_LD_BYPASS(35, lh, sh, 0xffffffffffffabbc, 6, tdat );
  TEST_ST_LD_BYPASS(36, lh, sh, 0xffffffffffffaabb, 8, tdat );
  TEST_ST_LD_BYPASS(37, lh, sh, 0xffffffffffffdaab, 10, tdat );

  TEST_ST_LD_BYPASS(38, lh, sh, 0x2233, 0, tdat );
  TEST_ST_LD_BYPASS(39, lh, sh, 0x1223, 2, tdat );
  TEST_ST_LD_BYPASS(40, lh, sh, 0x1122, 4, tdat );
  TEST_ST_LD_BYPASS(41, lh, sh, 0x0112, 6, tdat );
  TEST_ST_LD_BYPASS(42, lh, sh, 0x0011, 8, tdat );
  TEST_ST_LD_BYPASS(43, lh, sh, 0x3001, 10, tdat );

  # Test sh and lhu (unsigned halfword)
  TEST_ST_LD_BYPASS(44, lhu, sh, 0x2233, 0, tdat );
  TEST_ST_LD_BYPASS(45, lhu, sh, 0x1223, 2, tdat );
  TEST_ST_LD_BYPASS(46, lhu, sh, 0x1122, 4, tdat );
  TEST_ST_LD_BYPASS(47, lhu, sh, 0x0112, 6, tdat );
  TEST_ST_LD_BYPASS(48, lhu, sh, 0x0011, 8, tdat );
  TEST_ST_LD_BYPASS(49, lhu, sh, 0x3001, 10, tdat );

  # RV64-specific tests for ld, sd, and lwu
#if __riscv_xlen == 64
  # Test sd and ld (doubleword)
  TEST_ST_LD_BYPASS(50, ld, sd, 0x0011223344556677, 0,  tdat );
  TEST_ST_LD_BYPASS(51, ld, sd, 0x1122334455667788, 8,  tdat );
  TEST_ST_LD_BYPASS(52, ld, sd, 0x2233445566778899, 16, tdat );
  TEST_ST_LD_BYPASS(53, ld, sd, 0xabbccdd, 0,  tdat );
  TEST_ST_LD_BYPASS(54, ld, sd, 0xaabbccd, 8,  tdat );
  TEST_ST_LD_BYPASS(55, ld, sd, 0xdaabbcc, 16, tdat );
  TEST_ST_LD_BYPASS(56, ld, sd, 0xddaabbc, 24, tdat );
  TEST_ST_LD_BYPASS(57, ld, sd, 0xcddaabb, 32, tdat );
  TEST_ST_LD_BYPASS(58, ld, sd, 0xccddaab, 40, tdat );

  TEST_ST_LD_BYPASS(59, ld, sd, 0x00112233, 0,  tdat );
  TEST_ST_LD_BYPASS(60, ld, sd, 0x30011223, 8,  tdat );
  TEST_ST_LD_BYPASS(61, ld, sd, 0x33001122, 16, tdat );
  TEST_ST_LD_BYPASS(62, ld, sd, 0x23300112, 24, tdat );
  TEST_ST_LD_BYPASS(63, ld, sd, 0x22330011, 32, tdat );
  TEST_ST_LD_BYPASS(64, ld, sd, 0x12233001, 40, tdat );

  # Test sw and lwu (unsigned word)
  TEST_ST_LD_BYPASS(65, lwu, sw, 0x00112233, 0,  tdat );
  TEST_ST_LD_BYPASS(66, lwu, sw, 0x33001122, 8,  tdat );
  TEST_ST_LD_BYPASS(67, lwu, sw, 0x30011223, 4,  tdat );
  TEST_ST_LD_BYPASS(68, lwu, sw, 0x23300112, 12, tdat );
  TEST_ST_LD_BYPASS(69, lwu, sw, 0x22330011, 16, tdat );
  TEST_ST_LD_BYPASS(70, lwu, sw, 0x12233001, 20, tdat );
#endif

  li a0, 0xef         # Immediate load for manual store test
  la a1, tdat         # Load address of tdat
  sb a0, 3(a1)        # Store byte at offset 3 of tdat
  lb a2, 3(a1)        # Load byte back for verification

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
    .rept 20
    .word 0xdeadbeef
    .endr


RVTEST_DATA_END
```

---
<!-- rv32ui_sub -->

# rv32ui Test: `SUB`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **36**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 7 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 8 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 9 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| ... | ... | (28 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0x0000000000000001"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffffffc",
    "rs1_value": "0x0000000000000003"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000008000",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80000000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff80008000",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffffffff8001",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000007fffffff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x000000007fff8000",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xffffffff7fff8001",
    "rs1_value": "0xffffffff80000000"
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000080007fff",
    "rs1_value": "0x000000007fffffff"
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000001",
    "rs1_value": "0x0000000000000000"
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xfffffffffffffffe",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0000000000000000",
    "rs1_value": "0xffffffffffffffff"
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sub.S
#-----------------------------------------------------------------------------
#
# Test sub instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sub, 0x0000000000000000, 0x0000000000000000, 0x0000000000000000 );
  TEST_RR_OP( 3,  sub, 0x0000000000000000, 0x0000000000000001, 0x0000000000000001 );
  TEST_RR_OP( 4,  sub, 0xfffffffffffffffc, 0x0000000000000003, 0x0000000000000007 );

  TEST_RR_OP( 5,  sub, 0x0000000000008000, 0x0000000000000000, 0xffffffffffff8000 );
  TEST_RR_OP( 6,  sub, 0xffffffff80000000, 0xffffffff80000000, 0x0000000000000000 );
  TEST_RR_OP( 7,  sub, 0xffffffff80008000, 0xffffffff80000000, 0xffffffffffff8000 );

  TEST_RR_OP( 8,  sub, 0xffffffffffff8001, 0x0000000000000000, 0x0000000000007fff );
  TEST_RR_OP( 9,  sub, 0x000000007fffffff, 0x000000007fffffff, 0x0000000000000000 );
  TEST_RR_OP( 10, sub, 0x000000007fff8000, 0x000000007fffffff, 0x0000000000007fff );

  TEST_RR_OP( 11, sub, 0xffffffff7fff8001, 0xffffffff80000000, 0x0000000000007fff );
  TEST_RR_OP( 12, sub, 0x0000000080007fff, 0x000000007fffffff, 0xffffffffffff8000 );

  TEST_RR_OP( 13, sub, 0x0000000000000001, 0x0000000000000000, 0xffffffffffffffff );
  TEST_RR_OP( 14, sub, 0xfffffffffffffffe, 0xffffffffffffffff, 0x0000000000000001 );
  TEST_RR_OP( 15, sub, 0x0000000000000000, 0xffffffffffffffff, 0xffffffffffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 16, sub, 2, 13, 11 );
  TEST_RR_SRC2_EQ_DEST( 17, sub, 3, 14, 11 );
  TEST_RR_SRC12_EQ_DEST( 18, sub, 0, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 19, 0, sub, 2, 13, 11 );
  TEST_RR_DEST_BYPASS( 20, 1, sub, 3, 14, 11 );
  TEST_RR_DEST_BYPASS( 21, 2, sub, 4, 15, 11 );

  TEST_RR_SRC12_BYPASS( 22, 0, 0, sub, 2, 13, 11 );
  TEST_RR_SRC12_BYPASS( 23, 0, 1, sub, 3, 14, 11 );
  TEST_RR_SRC12_BYPASS( 24, 0, 2, sub, 4, 15, 11 );
  TEST_RR_SRC12_BYPASS( 25, 1, 0, sub, 2, 13, 11 );
  TEST_RR_SRC12_BYPASS( 26, 1, 1, sub, 3, 14, 11 );
  TEST_RR_SRC12_BYPASS( 27, 2, 0, sub, 4, 15, 11 );

  TEST_RR_SRC21_BYPASS( 28, 0, 0, sub, 2, 13, 11 );
  TEST_RR_SRC21_BYPASS( 29, 0, 1, sub, 3, 14, 11 );
  TEST_RR_SRC21_BYPASS( 30, 0, 2, sub, 4, 15, 11 );
  TEST_RR_SRC21_BYPASS( 31, 1, 0, sub, 2, 13, 11 );
  TEST_RR_SRC21_BYPASS( 32, 1, 1, sub, 3, 14, 11 );
  TEST_RR_SRC21_BYPASS( 33, 2, 0, sub, 4, 15, 11 );

  TEST_RR_ZEROSRC1( 34, sub, 15, -15 );
  TEST_RR_ZEROSRC2( 35, sub, 32, 32 );
  TEST_RR_ZEROSRC12( 36, sub, 0 );
  TEST_RR_ZERODEST( 37, sub, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_sw -->

# rv32ui Test: `SW`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **22**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 3 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 4 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 5 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 6 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 7 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 8 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| 9 | `TEST_ST_OP` | Store instruction correctness: compute effective address, write rs2 to memory. T... |
| ... | ... | (14 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_ST_OP`**: Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0x0000000000aa00aa",
    "base_label": "0"
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0xffffffffaa00aa00",
    "base_label": "4"
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0x000000000aa00aa0",
    "base_label": "8"
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0xffffffffa00aa00a",
    "base_label": "12"
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0x0000000000aa00aa",
    "base_label": "-12"
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0xffffffffaa00aa00",
    "base_label": "-8"
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0x000000000aa00aa0",
    "base_label": "-4"
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "rtl_contract": "Store instruction correctness: compute effective address, write rs2 to memory. Tests: store byte/halfword/word masking, subsequent load must return stored value.",
    "expected_result": "sw",
    "offset": "0xffffffffa00aa00a",
    "base_label": "0"
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sw.S
#-----------------------------------------------------------------------------
#
# Test sw instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lw, sw, 0x0000000000aa00aa, 0,  tdat );
  TEST_ST_OP( 3, lw, sw, 0xffffffffaa00aa00, 4,  tdat );
  TEST_ST_OP( 4, lw, sw, 0x000000000aa00aa0, 8,  tdat );
  TEST_ST_OP( 5, lw, sw, 0xffffffffa00aa00a, 12, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lw, sw, 0x0000000000aa00aa, -12, tdat8 );
  TEST_ST_OP( 7, lw, sw, 0xffffffffaa00aa00, -8,  tdat8 );
  TEST_ST_OP( 8, lw, sw, 0x000000000aa00aa0, -4,  tdat8 );
  TEST_ST_OP( 9, lw, sw, 0xffffffffa00aa00a, 0,   tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x5, 0x12345678, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sw x2, 32(x4); \
    lw x5, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x5, 0x58213098, \
    la  x1, tdat9; \
    li  x2, 0x58213098; \
    addi x1, x1, -3; \
    sw x2, 7(x1); \
    la  x4, tdat10; \
    lw x5, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lw, sw, 0xffffffffaabbccdd, 0,  tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lw, sw, 0xffffffffdaabbccd, 4,  tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lw, sw, 0xffffffffddaabbcc, 8,  tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lw, sw, 0xffffffffcddaabbc, 12, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lw, sw, 0xffffffffccddaabb, 16, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lw, sw, 0xffffffffbccddaab, 20, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lw, sw, 0x00112233, 0,  tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lw, sw, 0x30011223, 4,  tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lw, sw, 0x33001122, 8,  tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lw, sw, 0x23300112, 12, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lw, sw, 0x22330011, 16, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lw, sw, 0x12233001, 20, tdat );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .word 0xdeadbeef
tdat2:  .word 0xdeadbeef
tdat3:  .word 0xdeadbeef
tdat4:  .word 0xdeadbeef
tdat5:  .word 0xdeadbeef
tdat6:  .word 0xdeadbeef
tdat7:  .word 0xdeadbeef
tdat8:  .word 0xdeadbeef
tdat9:  .word 0xdeadbeef
tdat10: .word 0xdeadbeef

RVTEST_DATA_END
```

---
<!-- rv32ui_xor -->

# rv32ui Test: `XOR`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **26**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 3 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 4 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 5 | `TEST_RR_OP` | R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs... |
| 6 | `TEST_RR_SRC1_EQ_DEST` | rd == rs1 hazard: source register is also destination. RegFile must handle read-... |
| 7 | `TEST_RR_SRC2_EQ_DEST` | rd == rs2 hazard: source register 2 is also destination. RegFile must handle rea... |
| 8 | `TEST_RR_SRC12_EQ_DEST` | rd == rs1 == rs2: all three refer to same register. Tests double-alias read-befo... |
| 9 | `TEST_RR_DEST_BYPASS` | NOP cycles inserted between instruction and result check. Tests that pipeline (e... |
| ... | ... | (18 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_RR_OP`**: R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.
- **`TEST_RR_SRC1_EQ_DEST`**: rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case).
- **`TEST_RR_SRC2_EQ_DEST`**: rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case).
- **`TEST_RR_SRC12_EQ_DEST`**: rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile.
- **`TEST_RR_DEST_BYPASS`**: NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values.
- **`TEST_RR_SRC12_BYPASS`**: NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling.
- **`TEST_RR_SRC21_BYPASS`**: NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads.
- **`TEST_RR_ZEROSRC1`**: rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZEROSRC2`**: rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value.
- **`TEST_RR_ZERODEST`**: rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xf00ff00f",
    "rs1_value": "0xff00ff00"
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0xff00ff00",
    "rs1_value": "0x0ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x0ff00ff0",
    "rs1_value": "0x00ff00ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "rtl_contract": "R-type instruction correctness: li rs1=val1, li rs2=val2, execute inst rd,rs1,rs2. rd must equal expected result. Tests: ALU compute, register write.",
    "expected_result": "0x00ff00ff",
    "rs1_value": "0xf00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "rtl_contract": "rd == rs1 hazard: source register is also destination. RegFile must handle read-before-write in same cycle (rd=rs1 case)."
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "rtl_contract": "rd == rs2 hazard: source register 2 is also destination. RegFile must handle read-before-write in same cycle (rd=rs2 case)."
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "rtl_contract": "rd == rs1 == rs2: all three refer to same register. Tests double-alias read-before-write in RegFile."
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "rtl_contract": "NOP cycles inserted between instruction and result check. Tests that pipeline (even single-cycle) correctly forwards or discards stale values."
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "rtl_contract": "NOP cycles between loading rs1 and rs2. Tests read-after-write hazard handling."
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "rtl_contract": "NOP cycles, but rs2 is loaded BEFORE rs1 (reversed operand order). Tests that the register file correctly handles operand order independence when NOP slots separate the two source loads."
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "rtl_contract": "rs1 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "rtl_contract": "rs2 = x0 (always zero). Instruction must read 0 from x0, not a stale value."
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "rtl_contract": "rd = x0: write result to x0. x0 MUST remain hardwired zero after write. This is the most critical x0 invariant test."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# xor.S
#-----------------------------------------------------------------------------
#
# Test xor instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, xor, 0x00ff00ff, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_EQ_DEST( 8, xor, 0x00000000, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, xor, 0xff00ff00, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, xor, 0x00ff00ff, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, xor, 0 );
  TEST_RR_ZERODEST( 27, xor, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- rv32ui_xori -->

# rv32ui Test: `XORI`

> **Section Context:** rv32ui ISA test suite — integer-only user-level RV32
> **TVM:** `rv32ui` | **Target Env:** `p` (no VM, single core)
> **Pass/Fail Protocol:** Pass/Fail is signaled by writing to the `tohost` memory-mapped address. A write of 1 means PASS; any non-zero value != 1 encodes FAIL with test number in bits [31:1]. The Verilog testbench must poll address 0x80001000 (or the linker-assigned tohost symbol) and halt simulation when it detects a non-zero write.

## Test Coverage Summary

Total test cases parsed: **13**

| Test ID | Macro | RTL Contract |
| --- | --- | --- |
| 2 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 3 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 4 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 5 | `TEST_IMM_OP` | I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. ... |
| 6 | `TEST_IMM_SRC1_EQ_DEST` | I-type with rd == rs1. RegFile must handle read-before-write for immediate instr... |
| 7 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 8 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| 9 | `TEST_IMM_DEST_BYPASS` | I-type with NOP cycles after result. Tests forwarding path for immediate instruc... |
| ... | ... | (5 more test cases) |

## Key RTL Invariants This Test Suite Enforces

- **`TEST_IMM_OP`**: I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.
- **`TEST_IMM_SRC1_EQ_DEST`**: I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions.
- **`TEST_IMM_DEST_BYPASS`**: I-type with NOP cycles after result. Tests forwarding path for immediate instructions.
- **`TEST_IMM_ZEROSRC1`**: I-type with rs1=x0. Immediate instruction must read zero from x0.
- **`TEST_IMM_ZERODEST`**: I-type with rd=x0. Result must not corrupt x0.

## Structured Test Vectors (JSON)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xffffffffff00f00f",
    "rs1_value": "0x0000000000ff0f00"
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x000000000ff00f00",
    "rs1_value": "0x000000000ff00ff0"
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0x0000000000ff0ff0",
    "rs1_value": "0x0000000000ff08ff"
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "rtl_contract": "I-type immediate instruction correctness: li rs1=val1, execute inst rd,rs1,imm. rd must equal expected result. Tests: sign-extension of 12-bit immediate, ALU compute.",
    "expected_result": "0xfffffffff00ff0ff",
    "rs1_value": "0xfffffffff00ff00f"
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "rtl_contract": "I-type with rd == rs1. RegFile must handle read-before-write for immediate instructions."
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "rtl_contract": "I-type with NOP cycles after result. Tests forwarding path for immediate instructions."
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "rtl_contract": "See test_macros.h for full definition."
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "rtl_contract": "I-type with rs1=x0. Immediate instruction must read zero from x0."
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "rtl_contract": "I-type with rd=x0. Result must not corrupt x0."
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# xori.S
#-----------------------------------------------------------------------------
#
# Test xori instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, xori, 0xffffffffff00f00f, 0x0000000000ff0f00, 0xf0f );
  TEST_IMM_OP( 3, xori, 0x000000000ff00f00, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, xori, 0x0000000000ff0ff0, 0x0000000000ff08ff, 0x70f );
  TEST_IMM_OP( 5, xori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, xori, 0xffffffffff00f00f, 0xffffffffff00f700, 0x70f );

   #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, xori, 0x000000000ff00f00, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 8,  1, xori, 0x0000000000ff0ff0, 0x0000000000ff08ff, 0x70f );
  TEST_IMM_DEST_BYPASS( 9,  2, xori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  TEST_IMM_SRC1_BYPASS( 10, 0, xori, 0x000000000ff00f00, 0x000000000ff00ff0, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 11, 1, xori, 0x0000000000ff0ff0, 0x0000000000ff0fff, 0x00f );
  TEST_IMM_SRC1_BYPASS( 12, 2, xori, 0xfffffffff00ff0ff, 0xfffffffff00ff00f, 0x0f0 );

  TEST_IMM_ZEROSRC1( 13, xori, 0x0f0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, xori, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```