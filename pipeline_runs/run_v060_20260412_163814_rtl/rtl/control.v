module control(
  input logic [6:0] opcode,
  input logic [2:0] funct3,
  input logic funct7b5,
  output logic [1:0] alu_src_a,
  output logic alu_src_b,
  output logic [1:0] result_src,
  output logic reg_write,
  output logic mem_read,
  output logic mem_write,
  output logic [1:0] mem_size,
  output logic mem_extend,
  output logic branch,
  output logic [2:0] branch_type,
  output logic jump,
  output logic jump_type,
  output logic [3:0] alu_op,
  output logic [2:0] imm_type
);
  // Default assignments to avoid linter warnings
  assign alu_src_a   = 2'b00; // default rs1
  assign alu_src_b   = 1'b0;  // default rs2
  assign result_src  = 2'b00; // default ALU result
  assign reg_write   = 1'b0;
  assign mem_read    = 1'b0;
  assign mem_write   = 1'b0;
  assign mem_size    = 2'b00; // byte
  assign mem_extend  = 1'b0;  // sign extend
  assign branch      = 1'b0;
  assign branch_type = 3'b000;
  assign jump        = 1'b0;
  assign jump_type   = 1'b0;
  assign alu_op      = 4'b0000; // ADD
  assign imm_type    = 3'b000;  // I-type

  always_comb begin
    // Decode based on opcode
    case (opcode)
      7'b0110111: begin // LUI
        alu_src_a   = 2'b10; // zero
        alu_src_b   = 1'b1;  // imm
        result_src  = 2'b11; // imm bypass
        reg_write   = 1'b1;
        imm_type    = 3'b011; // U-type
        // other signals remain default
      end
      7'b0010111: begin // AUIPC
        alu_src_a   = 2'b01; // pc
        alu_src_b   = 1'b1;  // imm
        result_src  = 2'b00; // ALU result
        reg_write   = 1'b1;
        imm_type    = 3'b011; // U-type
      end
      7'b1101111: begin // JAL
        alu_src_a   = 2'b01; // pc
        alu_src_b   = 1'b1;  // imm
        result_src  = 2'b10; // pc+4
        reg_write   = 1'b1;
        jump        = 1'b1;
        jump_type   = 1'b0; // JAL
        imm_type    = 3'b100; // J-type
      end
      7'b1100111: begin // JALR
        alu_src_a   = 2'b00; // rs1
        alu_src_b   = 1'b1;  // imm
        result_src  = 2'b10; // pc+4
        reg_write   = 1'b1;
        jump        = 1'b1;
        jump_type   = 1'b1; // JALR
        imm_type    = 3'b000; // I-type
      end
      7'b1100011: begin // BRANCH
        alu_src_a