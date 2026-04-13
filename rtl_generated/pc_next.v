module pc_next(
    input  logic [31:0] pc,
    input  logic [31:0] imm,
    input  logic [31:0] rs1,
    input  logic taken,
    input  logic jump,
    input  logic [1:0] jump_type,
    output logic [31:0] next_pc
);

always_comb begin
    if (jump || taken) begin
        if (jump_type == 2'b0) begin // JAL or Branch
            next_pc = pc + imm;
        end else if (jump_type == 2'b1) begin // JALR
            next_pc = (rs1 + imm) & ~32'h1;
        end else begin
            next_pc = pc + 4;
        end
    end else begin
        next_pc = pc + 4;
    end
end

endmodule