module cpu (
  input  logic        clk,
  input  logic        resetn,
  input  logic [31:0] imem_rdata,
  input  logic [31:0] dmem_rdata,
  output logic [31:0] imem_addr,
  output logic [31:0] dmem_addr,
  output logic [31:0] dmem_wdata,
  output logic [3:0]  dmem_wstrb,
  output logic        dmem_read,
  output logic        dmem_write
);

  logic [31:0] pc;
  logic [31:0] next_pc;
  logic [31:0] rs1;
  logic [31:0] rs2;
  logic [31:0] rd1;
  logic [31:0] rd2;
  logic [31:0] rd_data;
  logic [31:0] imm;
  logic [31:0] alu_a;
  logic [31:0] alu_b;
  logic [31:0] alu_result;
  logic [31:0] mem_rdata;
  logic [31:0] mem_addr;
  logic [31:0] mem_wdata;
  logic [3:0]  mem_wstrb;
  logic        mem_read;
  logic        mem_write;
  logic        mem_extend;
  logic [1:0]  mem_size;
  logic [3:0]  alu_op;
  logic        alu_src_b;
  logic [1:0]  alu_src_a;
  logic [1:0]  result_src;
  logic        reg_write;
  logic        branch;
  logic [2:0]  branch_type;
  logic        jump;
  logic        jump_type;
  logic [2:0]  imm_type;
  logic        taken;
  logic        zero;

  regfile regfile_inst (
    .clk(clk),
    .we(reg_write & (imem_rdata[11:7] != 0)),
    .rs1(imem_rdata[19:15]),
    .rs2(imem_rdata[24:20]),
    .rd(imem_rdata[11:7]),
    .rd_data(rd_data),
    .rd1(rd1),
    .rd2(rd2)
  );

  imm_gen imm_gen_inst (
    .instr(imem_rdata),
    .imm_type(imm_type),
    .imm(imm)
  );

  control control_inst (
    .opcode(imem_rdata[6:0]),
    .funct3(imem_rdata[14:12]),
    .funct7b5(imem_rdata[30]),
    .alu_op(alu_op),
    .alu_src_b(alu_src_b),
    .alu_src_a(alu_src_a),
    .result_src(result_src),
    .reg_write(reg_write),
    .mem_read(mem_read),
    .mem_write(mem_write),
    .mem_size(mem_size),
    .mem_extend(mem_extend),
    .branch(branch),
    .branch_type(branch_type),
    .jump(jump),
    .jump_type(jump_type),
    .imm_type(imm_type)
  );

  alu alu_inst (
    .a(alu_a),
    .b(alu_b),
    .alu_op(alu_op),
    .result(alu_result),
    .zero(zero)
  );

  branch_unit branch_unit_inst (
    .branch_type(branch_type),
    .rs1(rd1),
    .rs2(rd2),
    .branch(branch),
    .taken(taken)
  );

  load_store load_store_inst (
    .mem_read(mem_read),
    .mem_write(mem_write),
    .mem_size(mem_size),
    .mem_extend(mem_extend),
    .addr(alu_result),
    .wdata(rd2),
    .mem_rdata(dmem_rdata),
    .rdata(mem_rdata),
    .mem_addr(mem_addr),
    .mem_wdata(mem_wdata),
    .mem_wstrb(mem_wstrb)
  );

  pc_next pc_next_inst (
    .pc(pc),
    .imm(imm),
    .rs1(rd1),
    .taken(taken),
    .jump(jump),
    .jump_type(jump_type),
    .next_pc(next_pc)
  );

  always_comb begin
    case (alu_src_a)
      2'b00: alu_a = rd1;
      2'b01: alu_a = pc;
      2'b10: alu_a = 32'b0;
      default: alu_a = 32'b0;
    endcase

    case (alu_src_b)
      1'b0: alu_b = rd2;
      1'b1: alu_b = imm;
      default: alu_b = 32'b0;
    endcase

    case (result_src)
      2'b00: rd_data = alu_result;
      2'b01: rd_data = mem_rdata;
      2'b10: rd_data = pc + 4;
      2'b11: rd_data = imm;
      default: rd_data = 32'b0;
    endcase
  end

  always_ff @(posedge clk or negedge resetn) begin
    if (!resetn) begin
      pc <= 32'b0;
    end else begin
      pc <= next_pc;
    end
  end

  assign imem_addr = pc;
  assign dmem_addr = mem_addr;
  assign dmem_wdata = mem_wdata;
  assign dmem_wstrb = mem_wstrb;
  assign dmem_read = mem_read;
  assign dmem_write = mem_write;

endmodule