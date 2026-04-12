// pc_next.v
// Computes the next program counter value for a single-cycle RISC‑V CPU.
// Depends on the branch_unit for the branch taken signal.
// Implements JAL, JALR, branch, and sequential PC update logic.

module pc_next (
    input  logic [31:0] pc,      // current PC
    input  logic [31:0] imm,     // sign‑extended immediate
    input  logic [31:0] rs1,     // source register 1 (used for JALR)
    input  logic        taken,   // branch taken flag from branch_unit
    input  logic        jump,    // jump flag from control
    input  logic        jump_type, // 1 for JALR, 0 for JAL
    output logic [31:0] next_pc  // computed next PC
);

    // Sequential PC update logic
    always_comb begin
        // Default: sequential execution (pc + 4)
        next_pc = pc + 32'd4;

        // Handle jumps first (JAL/JALR)
        if (jump) begin
            if (jump_type) begin
                // JALR: (rs1 + imm) & ~1
                next_pc = (rs1 + imm) & ~32'h1;
            end else begin
                // JAL: pc + imm
                next_pc = pc + imm;
            end
        end
        // Handle taken branches
        else if (taken) begin
            next_pc = pc + imm;
        end
    end

endmodule