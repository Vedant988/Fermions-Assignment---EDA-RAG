# Pipeline Debug Report
**Saved:** 2026-04-13 15:02:48  |  **Label:** `planner`

---

## Phase 1 — Planner Agent

**Architecture:** `single-cycle`
**Reason:** Initial RTL generation locked to single-cycle: a golden reference model isolates ISA correctness from pipeline hazard complexity. Pipelining is a later iteration.

### Assumptions Made
- Strictly single-cycle architecture. NO pipeline registers. NO IF/ID, ID/EX, EX/MEM stage latches.
- No hazard detection unit, no forwarding multiplexers — not needed in single-cycle.
- Simple synchronous memory interface with byte-enable for loads/stores.
- The load_store module is a purely combinational masking unit that acts as an interface to external memory. It MUST NOT have a clock (clk) input.
- x0 hardwired to zero. No compressed instructions, no FP, no privileged mode.
- Naming Rule: A module name MUST NEVER exactly match any of its port names (e.g. pc_next output port is next_pc, not pc_next). LLMs hallucinate badly on port name collisions.

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

_Not run yet._

---

## Phase 3 — RTL Generator Agent

_Not run yet._

---

_Full JSONs in same folder: `planner_state.json`, `isa_expert_table.json`, `rtl/*.v`_