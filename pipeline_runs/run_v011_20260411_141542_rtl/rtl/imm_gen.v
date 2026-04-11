```verilog
module imm_gen (
    input  logic [31:0] instr,      // 32‑bit instruction word
    input  logic [2:0]  imm_type,   // immediate type selector
    output logic [31:0] imm         // sign/zero extended immediate
);

    // Immediate generation combinational logic
    always_comb begin
        case (imm_type)
            3'b000: // I‑type: sign‑extend 12‑bit immediate
                imm = {{20{instr[31]}}, instr[31:20]};
            3'b001: // S‑type: sign‑extend 12‑bit immediate from bits [31:25] and [11:7]
                imm = {{20{instr[31]}}, instr[31:25], instr[11:7]};
            3'b010: // B‑type: sign‑extend 13‑bit immediate (shifted left 1)
                imm = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
            3'b011: // U‑type: upper immediate shifted left 12 (no sign extension)
                imm = {instr[31:12], 12'b0};
            3'b100: // J‑type: sign‑extend 21‑bit immediate (shifted left 1)
                imm = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};
            default: // N/A or undefined type
                imm = 32'b0;
        endcase
    end

endmodule
```