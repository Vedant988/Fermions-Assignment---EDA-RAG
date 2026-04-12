module control(
  input  logic [6:0] opcode,
  input  logic [2:0] funct3,
  input  logic       funct7b5,
  output logic [1:0] alu_src_a,
  output logic       alu_src_b,
  output logic [1:0] result_src,
  output logic       reg_write,
  output logic       mem_read,
  output logic       mem_write,
  output logic [1:0] mem_size,
  output logic       mem_extend,
  output logic       branch,
  output logic [2:0] branch_type,
  output logic       jump,
  output logic       jump_type,
  output logic [3:0] alu_op,
  output logic [2:0] imm_type
);

  // Default assignments
  always_comb begin
    alu_src_a   = 2'b00;          // rs1
    alu_src_b   = 1'b0;           // rs2
    result_src  = 2'b00;          // ALU result
    reg_write   = 1'b0;
    mem_read    = 1'b0;
    mem_write   = 1'b0;
    mem_size    = 2'b00;
    mem_extend  = 1'b0;
    branch      = 1'b0;
    branch_type = 3'b000;
    jump        = 1'b0;
    jump_type   = 1'b0;
    alu_op      = 4'b0000;        // ADD
    imm_type    = 3'b000;

    case (opcode)
      // U-type: LUI
      7'b0110111: begin
        alu_src_a  = 2'b10;        // zero
        alu_src_b  = 1'b1;         // imm
        result_src = 2'b11;        // imm bypass
        reg_write  = 1'b1;
        imm_type   = 3'b011;       // U-type
        alu_op     = 4'b0000;      // ADD (unused)
      end

      // U-type: AUIPC
      7'b0010111: begin
        alu_src_a  = 2'b01;        // pc
        alu_src_b  = 1'b1;         // imm
        result_src = 2'b00;        // ALU result
        reg_write  = 1'b1;
        imm_type   = 3'b011;       // U-type
        alu_op     = 4'b0000;      // ADD
      end

      // J-type: JAL
      7'b1101111: begin
        result_src = 2'b10;        // pc+4
        reg_write  = 1'b1;
        imm_type   = 3'b010;       // J-type
        jump       = 1'b1;
        jump_type  = 1'b0;         // JAL
      end
      
      default: begin
        // Everything is defaulted above
      end
    endcase
  end
endmodule