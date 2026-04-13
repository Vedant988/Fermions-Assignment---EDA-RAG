module load_store(
  input   logic         mem_read,
  input   logic         mem_write,
  input   logic [1:0]   mem_size,
  input   logic         mem_extend,
  input   logic [31:0]  addr,
  input   logic [31:0]  wdata,
  input   logic [31:0]  mem_rdata,
  output  logic [31:0]  rdata,
  output  logic [31:0]  mem_addr,
  output  logic [31:0]  mem_wdata,
  output  logic [3:0]   mem_wstrb
);

  always_comb begin
    mem_addr = {addr[31:2], 2'b00};
    case (mem_size)
      2'b00: begin
        rdata = mem_rdata;
        mem_wdata = wdata;
        mem_wstrb = 4'b0001;
      end
      2'b01: begin
        case (mem_extend)
          1'b0: rdata = {16'b0, mem_rdata[15:0]};
          1'b1: rdata = {mem_rdata[15:0], 16'b0};
        endcase
        mem_wdata = {16'b0, wdata[15:0]};
        mem_wstrb = 4'b0011;
      end
      2'b10: begin
        case (mem_extend)
          1'b0: rdata = {24'b0, mem_rdata[7:0]};
          1'b1: rdata = {mem_rdata[7:0], 24'b0};
        endcase
        mem_wdata = {24'b0, wdata[7:0]};
        mem_wstrb = 4'b1111;
      end
      default: begin
        rdata = 32'b0;
        mem_wdata = 32'b0;
        mem_wstrb = 4'b0000;
      end
    endcase
  end

endmodule