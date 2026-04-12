module branch_unit(
  input  logic       branch,
  input  logic [2:0] branch_type, // funct3 field
  input  logic [31:0] rs1,
  input  logic [31:0] rs2,
  output logic taken
);
  // Combinational branch decision logic
  always_comb begin
    logic condition;
    case (branch_type)
      3'b000: condition = (rs1 == rs2);                     // BEQ
      3'b001: condition = (rs1 != rs2);                     // BNE
      3'b100: condition = ($signed(rs1) < $signed(rs2));    // BLT
      3'b101: condition = ($signed(rs1) >= $signed(rs2));   // BGE
      3'b110: condition = (rs1 < rs2);                      // BLTU
      3'b111: condition = (rs1 >= rs2);                     // BGEU
      default: condition = 1'b0;                            // safety default
    endcase
    taken = branch & condition;
  end
endmodule