module regfile(
  input  logic        clk,
  input  logic        we,
  input  logic [4:0]  rs1,
  input  logic [4:0]  rs2,
  input  logic [4:0]  rd,
  input  logic [31:0] rd_data,
  output logic [31:0] rd1,
  output logic [31:0] rd2
);

  logic [31:0] registers [31:0];

  always_ff @(posedge clk or negedge we) begin
    if (~we) begin
      registers <= '{default: 32'b0};
    end else if (we && rd != 0) begin
      registers[rd] <= rd_data;
    end
  end

  always_comb begin
    case (rs1)
      5'b00000: rd1 = 32'b0;
      default:  rd1 = registers[rs1];
    endcase

    case (rs2)
      5'b00000: rd2 = 32'b0;
      default:  rd2 = registers[rs2];
    endcase
  end

endmodule