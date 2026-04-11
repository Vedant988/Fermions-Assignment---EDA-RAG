# Pipeline Debug Report
**Saved:** 2026-04-11 12:21:54  |  **Label:** `isa`

---

## Phase 1 — Planner Agent

**Architecture:** `single-cycle`
**Reason:** Initial RTL generation locked to single-cycle: a golden reference model isolates ISA correctness from pipeline hazard complexity. Pipelining is a later iteration.

### Assumptions Made
- Strictly single-cycle architecture. NO pipeline registers. NO IF/ID, ID/EX, EX/MEM stage latches.
- No hazard detection unit, no forwarding multiplexers — not needed in single-cycle.
- Simple synchronous memory interface with byte-enable for loads/stores.
- x0 hardwired to zero. No compressed instructions, no FP, no privileged mode.

### Instruction Groups
| Priority | Group | Instructions |
|---|---|---|
| P1 | R-Type ALU | ADD, SUB, AND, OR, XOR, SLT, SLTU, SLL, SRL, SRA |
| P2 | I-Type ALU | ADDI, ANDI, ORI, XORI, SLTI, SLTIU, SLLI, SRLI, SRAI |
| P3 | U-Type | LUI, AUIPC |
| P4 | Branches | BEQ, BNE, BLT, BGE, BLTU, BGEU |
| P5 | Loads | LB, LH, LW, LBU, LHU |
| P6 | Stores | SB, SH, SW |
| P7 | Jumps | JAL, JALR |

### Module Build Order (DAG)
1. **regfile** (leaf)
2. **imm_gen** (leaf)
3. **alu** (leaf)
4. **branch_unit** ← alu
5. **load_store** (leaf)
6. **control** (leaf)
7. **pc_next** ← branch_unit
8. **top** ← regfile, imm_gen, alu, branch_unit, load_store, control, pc_next

### Milestones
| Phase | Goal | Modules |
|---|---|---|
| 1 | regfile + ALU + R-type only: passes rv32ui-p-add | regfile, alu, control, top |
| 2 | I-type + U-type + Shifts: passes rv32ui-p-addi, lui, auipc | imm_gen |
| 3 | Branches + Jumps: passes rv32ui-p-beq, jal, jalr | branch_unit, pc_next |
| 4 | Loads + Stores: passes rv32ui-p-lb through sw | load_store |

**tohost address:** `0x80001000`  |  **Reset PC:** `0x00000000`

---

## Phase 2 — ISA Expert Agent

**Total decoded instructions:** 23

### Control Signal Truth Table
| instruction | format | opcode | funct3 | funct7 | ALU_op | reg_write | mem_read | mem_write | branch | jump | wb_src |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADD | R | 0110011 | 000 | 0000000 | ADD | 1 | 0 | 0 | 0 | 0 | alu |
| SUB | R | 0110011 | 000 | 0100000 | SUB | 1 | 0 | 0 | 0 | 0 | alu |
| AND | R | 0110011 | 111 | 0000000 | AND | 1 | 0 | 0 | 0 | 0 | alu |
| OR | R | 0110011 | 110 | 0000000 | OR | 1 | 0 | 0 | 0 | 0 | alu |
| XOR | R | 0110011 | 100 | 0000000 | XOR | 1 | 0 | 0 | 0 | 0 | alu |
| SLT | R | 0110011 | 010 | 0000000 | SLT | 1 | 0 | 0 | 0 | 0 | alu |
| SLTU | R | 0110011 | 011 | 0000000 | SLTU | 1 | 0 | 0 | 0 | 0 | alu |
| SLL | R | 0110011 | 001 | 0000000 | SLL | 1 | 0 | 0 | 0 | 0 | alu |
| SRL | R | 0110011 | 101 | 0000000 | SRL | 1 | 0 | 0 | 0 | 0 | alu |
| SRA | R | 0110011 | 101 | 0100000 | SRA | 1 | 0 | 0 | 0 | 0 | alu |
| LUI | U | 0110111 | N/A | N/A | PASS_B | 1 | 0 | 0 | 0 | 0 | alu |
| AUIPC | U | 0010111 | N/A | N/A | ADD | 1 | 0 | 0 | 0 | 0 | alu |
| BEQ | B | 1100011 | 000 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| BNE | B | 1100011 | 001 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| BLT | B | 1100011 | 100 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| BGE | B | 1100011 | 101 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| BLTU | B | 1100011 | 110 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| BGEU | B | 1100011 | 111 | N/A | SUB | 0 | 0 | 0 | 1 | 0 | N/A |
| SB | S | 0100011 | 000 | N/A | ADD | 0 | 0 | 1 | 0 | 0 | N/A |
| SH | S | 0100011 | 001 | N/A | ADD | 0 | 0 | 1 | 0 | 0 | N/A |
| SW | S | 0100011 | 010 | N/A | ADD | 0 | 0 | 1 | 0 | 0 | N/A |
| JAL | J | 1101111 | N/A | N/A | ADD | 1 | 0 | 0 | 0 | 1 | pc+4 |
| JALR | I | 1100111 | 000 | N/A | ADD | 1 | 0 | 0 | 0 | 1 | pc+4 |

### RAG Contexts Used Per Group

#### Context for group containing `ADD`
```
[2.1.4.2. Integer Register-Register Instructions]
> **Section Context:** 2.1.4. Integer Computational Instructions

# 2.1.4.2. Integer Register-Register Instructions

RV32I defines several arithmetic R-type operations. All operations read the rs1 and rs2 registers as source operands and write the result into register rd . The funct7 and funct3 fields select the type of operation.


`[FIGURE: Instruction encoding diagram]`

ADD performs the addition of rs1 and rs2 . SUB performs the subtraction of rs2 from rs1 . Overflows are ignored and the low XLEN bits of results are written to the destination rd . SLT and SLTU perform signed and unsigned compares respectively, writing 1 to rd if rs1 < rs2 , 0 otherwise. Note, SLTU rd , x0 , rs2 sets rd to 1 if rs2 is not equal to zero, otherwise sets rd to zero (assembler pseudoinstruction SNEZ rd, rs ). AND, OR, and XOR perform bitwise logical operations.

SLL, SRL, and SRA perform logical left, logical right, and arithmetic right shifts on the value in register rs1 by the shift amount held in the lower 5 bits of register rs2 .

---

[Assembly Test: PICORV32_FIRMWARE_START]
# Assembly Test: `PICORV32_FIRMWARE_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/firmware/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
// This is free and unencumbered software released into the public domain.
//
// Anyone is free to copy, modify, publish, use, compile, sell, or
// distribute this software, either in source code form or as a compiled
// binary, for any purpose, commercial or non-commercial, and by any
// means.

#define ENABLE_QREGS
#define ENABLE_HELLO
#define ENABLE_RVTST
#define ENABLE_SIEVE
#define ENABLE_MULTST
#define ENABLE_STATS

#ifndef ENABLE_QREGS
#  undef ENABLE_RVTST
#endif

// Only save registers in IRQ wrapper that are to be saved by the caller in
// the RISC-V ABI, with the excpetion of the stack pointer. The IRQ handler
// will save the rest if ne
```

#### Context for group containing `LUI`
```
[2.1.4.1. Integer Register-Immediate Instructions]
> **Section Context:** 2.1.4. Integer Computational Instructions

# 2.1.4.1. Integer Register-Immediate Instructions


`[FIGURE: Instruction encoding diagram]`

ADDI adds the sign-extended 12-bit immediate to register rs1 . Arithmetic overflow is ignored and the result is simply the low XLEN bits of the result. ADDI rd, rs1, 0 is used to implement the MV rd, rs1 assembler pseudoinstruction.

SLTI (set less than immediate) places the value 1 in register rd if register rs1 is less than the sign-extended immediate when both are treated as signed numbers, else 0 is written to rd . SLTIU is similar but compares the values as unsigned numbers (i.e., the immediate is first sign-extended to XLEN bits then treated as an unsigned number). Note, SLTIU rd, rs1, 1 sets rd to 1 if rs1 equals zero, otherwise sets rd to 0 (assembler pseudoinstruction SEQZ rd, rs ).

ANDI, ORI, XORI are logical operations that perform bitwise AND, OR, and XOR on register rs1 and the sign-extended 12-bit immediate and place the result in rd . Note, XORI rd, rs1, -1 performs a bitwise logical inversion of register rs1 (assembler pseudoinstruction NOT rd, rs ).


`[FIGURE: Instruction encoding diagram]`

Shifts by a c

---

[Assembly Test: PICORV32_DHRYSTONE_START]
# Assembly Test: `PICORV32_DHRYSTONE_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text
	.global start
	.global main

start:
	/* print "START\n" */
	lui a0,0x10000000>>12
	addi a1,zero,'S'
	addi a2,zero,'T'
	addi a3,zero,'A'
	addi a4,zero,'R'
	addi a5,zero,'\n'
	sw a1,0(a0)
	sw a2,0(a0)
	sw a3,0(a0)
	sw a4,0(a0)
	sw a2,0(a0)
	sw a5,0(a0)

	/* execute some insns for "make timing" */
	lui a0,0
	auipc a0,0
	slli a0,a0,0
	slli a0,a0,31
	addi a1,zero,0
	sll a0,a0,a1
	addi a1,zero,31
	sll a0,a0,a1

	/* set stack pointer */
	lui sp,(64*1024)>>12

	/* jump t
```

#### Context for group containing `BEQ`
```
[Assembly Test: PICORV32_TESTS_BEQ]
# Assembly Test: `PICORV32_TESTS_BEQ`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/beq.S`

## Parsed Test Vectors (20 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "-1"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0",
      "1"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "0"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-1",
      "1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 11,
    "macro": "T

---

[2.1.5.2. Conditional Branches]
> **Section Context:** 2.1.5. Control Transfer Instructions

# 2.1.5.2. Conditional Branches

All branch instructions use the B-type instruction format. The 12-bit B-immediate encodes signed offsets in multiples of 2 bytes. The offset is sign-extended and added to the address of the branch instruction to give the target address. The conditional branch range is ±4 KiB.


`[FIGURE: Instruction encoding diagram]`

Branch instructions compare two registers. BEQ and BNE take the branch if registers rs1 and rs2 are equal or unequal respectively. BLT and BLTU take the branch if rs1 is less than rs2 , using signed and unsigned comparison respectively. BGE and BGEU take the branch if rs1 is greater than or equal to rs2 , usi
```

#### Context for group containing `SB`
```
[Assembly Test: PICORV32_SCRIPTS_CSMITH_START]
# Assembly Test: `PICORV32_SCRIPTS_CSMITH_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text.start
.global application_entry_point

/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */
lui sp, %hi(4*1024*1024)
addi sp, sp, %lo(4*1024*1024)

/* push zeros on the stack for argc and argv */
/* (stack is aligned to 16 bytes in riscv calling convention) */
addi sp,sp,-16
sw zero,0(sp)
sw zero,4(sp)
sw zero,8(sp)
sw zero,12(sp)

/* jump to libc init */
j application_entry_point
```

---

[2.1.6. Load and Store Instructions]
# 2.1.6. Load and Store Instructions

RV32I is a load-store architecture, where only load and store instructions access memory and arithmetic instructions only operate on CPU registers. RV32I provides a 32-bit address space that is byte-addressed. The EEI will define what portions of the address space are legal to access with which instructions (e.g., some addresses might be read only, or support word access only). Loads with a destination of x0 must still raise any exceptions and cause any other side effects even though the load value is discarded.

The EEI will define whether the memory system is little-endian or big-endian. In RISC-V, endianness is byte-address invariant.

In a system for which endianness is by
```

#### Context for group containing `JAL`
```
[2.1.5.1. Unconditional Jumps]
> **Section Context:** 2.1.5. Control Transfer Instructions

# 2.1.5.1. Unconditional Jumps

The jump and link (JAL) instruction uses the J-type format, where the J-immediate encodes a signed offset in multiples of 2 bytes. The offset is sign-extended and added to the address of the jump instruction to form the jump target address. Jumps can therefore target a ±1 MiB range. JAL stores the address of the instruction following the jump ('pc'+4) into register rd . The standard software calling convention uses 'x1' as the return address register and 'x5' as an alternate link register.

The alternate link register supports calling millicode routines (e.g., those to save and restore registers in compressed code) while preserving the regular return address register. The register x5 was chosen as the alternate link register as it maps to a temporary in the standard calling convention, and has an encoding that is only one bit different than the regular link register.

Plain unconditional jumps (assembler pseudoinstruction J) are encoded as a JAL with rd = x0 .


`[FIGURE: Instruction encoding diagram]`

The indirect jump instruction JALR (jump and link register) uses the I-type encoding. Th

---

[2.1.4.1. Integer Register-Immediate Instructions]
> **Section Context:** 2.1.4. Integer Computational Instructions

# 2.1.4.1. Integer Register-Immediate Instructions


`[FIGURE: Instruction encoding diagram]`

ADDI adds the sign-extended 12-bit immediate to register rs1 . Arithmetic overflow is ignored and the result is simply the low XLEN bits of the result. ADDI rd, rs1, 0 is used to implement the MV rd, rs1 assembler pseudoinstruction.

SLTI (set less than immediate) places the value 1 in register rd if register rs1 is less than the sign-extended immediate when both are treated as signed numbers, else 0 is written to rd . SLTIU is similar but compares the values as unsigned numbers (i.e., the immediate is first sign-extended to XLEN bits then trea
```

### ⚠️ Raw LLM Fallbacks (JSON parse failed)

#### Group: I-Type ALU
```
[
  {
    "instruction": "ADDI",
    "format": "I",
    "opcode": "0010011",
    "funct3": "000",
    "funct7": "N/A",
    "ALU_op": "ADD",
    "alu_src_a": "rs1",
    "alu_src_b": "imm",
    "reg_write": 1,
    "mem_read": 0,
    "mem_write": 0,
    "mem_size": "N/A",
    "mem_extend": "N/A",
    "branch": 0,
    "jump": 0,
    "wb_src": "alu",
    "imm_type": "I",
    "notes": "rd = rs1 + sign_ext(imm)"
  },
  {
    "instruction": "ANDI",
    "format": "I",
    "opcode": "0010011",
    "funct3": "111",
    "funct7": "N/A",
    "ALU_op": "AND",
    "alu_src_a": "rs1",
    "alu_src_b": "imm",
    "reg_write": 1,
    "mem_read": 0,
    "mem_write": 0,
    "mem_size": "N/A",
    "mem_extend": "N/A",
    "branch": 0,
    "jump": 0,
    "wb_src": "alu",
    "imm_type": "I",
    "notes": "rd = rs1 & sign_ext(imm)"
  },
  {
    "instruction": "ORI",
    "format": "I",
    "opcode": "0010011",
    "funct3": "110",
    "funct7": "N/A",
    "ALU_op": "OR",
    "alu_src_a": "rs1",
    "alu_src_b
```

#### Group: Loads
```

```

---

## Phase 3 — RTL Generator Agent

_Not run yet._

---

_Full JSONs in same folder: `planner_state.json`, `isa_expert_table.json`, `rtl/*.v`_