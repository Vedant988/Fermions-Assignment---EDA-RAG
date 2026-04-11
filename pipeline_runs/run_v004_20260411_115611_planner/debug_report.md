# Pipeline Debug Report
**Saved:** 2026-04-11 11:56:11  |  **Label:** `planner`

---

## Phase 1 — Planner Agent

**Architecture:** `pipelined`
**Reason:** The design includes a 5‑stage pipeline (Fetch → Decode → Execute → Memory → Writeback) as specified.

### Assumptions Made
- Single‑issue, in‑order pipeline with no branch prediction or out‑of‑order execution.
- No compressed instructions, no privileged mode, no floating point.
- Simple memory interface (single bus) with byte‑enable support for loads/stores.
- Hardwired x0 to zero.
- tohost address is 0x80001000 and reset PC is 0x00000000.

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
| 1 | Register file + ALU + R-type only passes rv32ui-p-add | regfile, alu, control, top |
| 2 | I-type + U-type + Shifts pass all rv32ui-p-addi, lui, auipc | imm_gen |
| 3 | Branches + Jumps pass rv32ui-p-beq..bne..jal..jalr | branch_unit, pc_next |
| 4 | Loads + Stores pass all rv32ui-p-lb..sw | load_store |

**tohost address:** `0x80001000`  |  **Reset PC:** `0x00000000`

---

## Phase 2 — ISA Expert Agent

_Not run yet._

---

## Phase 3 — RTL Generator Agent

_Not run yet._

---

_Full JSONs in same folder: `planner_state.json`, `isa_expert_table.json`, `rtl/*.v`_