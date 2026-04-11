// Branch unit: parallel comparator for branch decisions
module branch_unit (
    input  logic [2:0] branch_type, // RISC-V funct3: 000=BEQ,001=BNE,100=BLT,101=BGE,110=BLTU,111=BGEU
    input  logic [31:0] rs1, rs2,
    output logic taken
);
    // Combinational logic for branch decision
    always_comb begin
        case (branch_type)
            3'b000: taken = (rs1 == rs2);                     // BEQ  (funct3=0)
            3'b001: taken = (rs1 != rs2);                     // BNE  (funct3=1)
            3'b100: taken = ($signed(rs1) < $signed(rs2));    // BLT  (funct3=4)
            3'b101: taken = ($signed(rs1) >= $signed(rs2));   // BGE  (funct3=5)
            3'b110: taken = (rs1 < rs2);                      // BLTU (funct3=6)
            3'b111: taken = (rs1 >= rs2);                     // BGEU (funct3=7)
            default: taken = 1'b0;                            // safety default
        endcase
    end
endmodule