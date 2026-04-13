module branch_unit(
  input  logic [2:0] branch_type,
  input  logic [31:0] rs1,
  input  logic [31:0] rs2,
  input  logic branch,
  output logic taken
);

  always_comb begin
    case (branch_type)
      3'b000: taken = (branch) && (rs1 == rs2);
      3'b001: taken = (branch) && (rs1 != rs2);
      3'b100: taken = (branch) && ($signed(rs1) < $signed(rs2));
      3'b101: taken = (branch) && ($signed(rs1) >= $signed(rs2));
      3'b110: taken = (branch) && (rs1 < rs2);
      3'b111: taken = (branch) && (rs1 >= rs2);
      default: begin end
    endcase
  end

endmodule