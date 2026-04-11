```verilog
module pc_next (
    input  logic [31:0] pc,      // current PC
    input  logic [31:0] imm,     // sign‑extended immediate
    input  logic [31:0] rs1,     // rs1 value (used for JALR)
    input  logic        taken,   // branch taken flag
    input  logic        jump,    // jump flag
    input  logic [2:0]  jump_type, // 0=JAL, 1=JALR, others unused
    output logic [31:0] pc_next  // next PC value
);

    always_comb begin
        // Default PC+4 (normal sequential execution)
        pc_next = pc + 32'd4;

        if (jump) begin
            // Jump instruction: JAL or JALR
            case (jump_type)
                3'd0: pc_next = pc + imm;                     // JAL
                3'd1: pc_next = (rs1 + imm) & ~32'h1;         // JALR clears LSB
                default: pc_next = pc + 32'd4;                // safety fallback
            endcase
        end
        else if (taken) begin
            // Branch taken: PC + immediate offset
            pc_next = pc + imm;
        end
    end

endmodule
```