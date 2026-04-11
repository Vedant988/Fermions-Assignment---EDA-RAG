```verilog
module branch_unit (
    input  logic [2:0] branch_type, // funct3 field: 000=BEQ, 001=BNE, 100=BLT, 101=BGE, 110=BLTU, 111=BGEU
    input  logic [31:0] rs1, rs2,   // source register values
    output logic taken              // branch taken flag
);
    // Branch comparison logic
    always_comb begin
        case (branch_type)
            3'b000: taken = (rs1 == rs2);                     // BEQ
            3'b001: taken = (rs1 != rs2);                     // BNE
            3'b100: taken = ($signed(rs1) < $signed(rs2));    // BLT
            3'b101: taken = ($signed(rs1) >= $signed(rs2));   // BGE
            3'b110: taken = (rs1 < rs2);                      // BLTU
            3'b111: taken = (rs1 >= rs2);                     // BGEU
            default: taken = 1'b0;                            // safety default
        endcase
    end
endmodule
```