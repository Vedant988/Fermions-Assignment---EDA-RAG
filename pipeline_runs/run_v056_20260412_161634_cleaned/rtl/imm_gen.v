// imm_gen.v
// Immediate generator for a single-cycle RISC‑V core
// Generates the 32‑bit immediate value based on the instruction format
// and the imm_type control signal.
//
// imm_type encoding (3 bits):
//   3'b000 = I‑type   (ADDI, etc.)
//   3'b001 = S‑type   (SW, SH, SB)
//   3'b010 = B‑type   (BEQ, BNE, etc.)
//   3'b011 = U‑type   (LUI, AUIPC)
//   3'b100 = J‑type   (JAL)
//   (other values default to zero)
//
// The module is purely combinational and does not use a clock.

module imm_gen
(
    /* verilator lint_off UNUSED */
    input  logic [31:0] instr,          // 32‑bit instruction word
    /* verilator lint_on UNUSED */
    input  logic [2:0]  imm_type,       // immediate type selector
    output logic [31:0] imm              // 32‑bit immediate output
);

    // Intermediate wires for sign‑extended immediates
    logic [31:0] imm_i, imm_s, imm_b, imm_u, imm_j;

    // I‑type: 12‑bit sign‑extended immediate
    assign imm_i = {{20{instr[31]}}, instr[31:20]};

    // S‑type: 12‑bit sign‑extended immediate (bits 31:25 and 11:7)
    assign imm_s = {{20{instr[31]}}, instr[31:25], instr[11:7]};

    // B‑type: 13‑bit sign‑extended immediate (bit 12 is instr[31])
    assign imm_b = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};

    // U‑type: 20‑bit upper immediate (no sign extension)
    assign imm_u = {instr[31:12], 12'b0};

    // J‑type: 21‑bit sign‑extended immediate (bit 20 is instr[31])
    assign imm_j = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};

    // Select the appropriate immediate based on imm_type
    always_comb begin
        case (imm_type)
            3'b000: imm = imm_i;   // I‑type
            3'b001: imm = imm_s;   // S‑type
            3'b010: imm = imm_b;   // B‑type
            3'b011: imm = imm_u;   // U‑type
            3'b100: imm = imm_j;   // J‑type
            default: imm = 32'b0;  // safety default
        endcase
    end

endmodule