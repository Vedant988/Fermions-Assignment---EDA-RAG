```verilog
// Branch unit: parallel comparator for branch decisions
module branch_unit (
    input  logic [2:0] branch_type, // 0=eq,1=ne,2=lt,3=ge,4=ltu,5=geu
    input  logic [31:0] rs1, rs2,
    output logic taken
);
    // Combinational logic for branch decision
    always_comb begin
        case (branch_type)
            3'd0: taken = (rs1 == rs2);                     // BEQ
            3'd1: taken = (rs1 != rs2);                     // BNE
            3'd2: taken = ($signed(rs1) < $signed(rs2));    // BLT
            3'd3: taken = ($signed(rs1) >= $signed(rs2));   // BGE
            3'd4: taken = (rs1 < rs2);                      // BLTU
            3'd5: taken = (rs1 >= rs2);                     // BGEU
            default: taken = 1'b0;                          // safety default
        endcase
    end
endmodule
```