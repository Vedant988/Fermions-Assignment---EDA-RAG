module control (
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
    always_comb begin
        // 1. DEFAULT ASSIGNMENTS (Prevents Latches)
        alu_src_a   = 2'b00; // rs1
        alu_src_b   = 1'b0;  // rs2
        result_src  = 2'b00; // ALU
        reg_write   = 1'b0;
        mem_read    = 1'b0;
        mem_write   = 1'b0;
        mem_size    = 2'b00; // byte
        mem_extend  = 1'b0;  // sign-extend
        branch      = 1'b0;
        branch_type = 3'b000;
        jump        = 1'b0;
        jump_type   = 1'b0;
        alu_op      = 4'b0000; // ADD
        imm_type    = 3'b000; // I-type

        // 2. OPCODE DECODING
        case (opcode)
            7'b0110111: begin // LUI
                alu_src_a  = 2'b10; // zero
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b11; // bypass ALU -> imm
                reg_write  = 1'b1;
                imm_type   = 3'b011; // U-type
            end
            
            7'b0010111: begin // AUIPC
                alu_src_a  = 2'b01; // pc
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                imm_type   = 3'b011; // U-type
                alu_op     = 4'b0000; // ADD
            end
            
            7'b1101111: begin // JAL
                result_src = 2'b10; // pc+4
                reg_write  = 1'b1;
                jump       = 1'b1;
                jump_type  = 1'b0; // JAL
                imm_type   = 3'b100; // J-type
            end
            
            7'b1100111: begin // JALR
                result_src = 2'b10; // pc+4
                reg_write  = 1'b1;
                jump       = 1'b1;
                jump_type  = 1'b1; // JALR
                imm_type   = 3'b000; // I-type
            end
            
            7'b1100011: begin // BRANCH
                branch      = 1'b1;
                imm_type    = 3'b010; // B-type
                branch_type = funct3; // Map directly to comparator
            end
            
            7'b0000011: begin // LOAD (LB, LH, LW, LBU, LHU)
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b01; // MEM
                reg_write  = 1'b1;
                mem_read   = 1'b1;
                imm_type   = 3'b000; // I-type
                alu_op     = 4'b0000; // ADD (rs1 + imm)
                mem_size   = funct3[1:0]; // 00=B, 01=H, 10=W
                mem_extend = funct3[2];   // 0=signed, 1=unsigned
            end
            
            7'b0100011: begin // STORE (SB, SH, SW)
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                mem_write  = 1'b1;
                imm_type   = 3'b001; // S-type
                alu_op     = 4'b0000; // ADD (rs1 + imm)
                mem_size   = funct3[1:0]; // 00=B, 01=H, 10=W
            end
            
            7'b0010011: begin // OP-IMM (ADDI, SLLI, etc.)
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                imm_type   = 3'b000; // I-type
                case (funct3)
                    3'b000: alu_op = 4'b0000; // ADDI
                    3'b010: alu_op = 4'b0011; // SLTI
                    3'b011: alu_op = 4'b0100; // SLTIU
                    3'b100: alu_op = 4'b0101; // XORI
                    3'b110: alu_op = 4'b1000; // ORI
                    3'b111: alu_op = 4'b1001; // ANDI
                    3'b001: alu_op = 4'b0010; // SLLI
                    3'b101: alu_op = funct7b5 ? 4'b0111 : 4'b0110; // SRAI / SRLI
                endcase
            end
            
            7'b0110011: begin // OP (ADD, SUB, AND, etc.)
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b0;  // rs2
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                case (funct3)
                    3'b000: alu_op = funct7b5 ? 4'b0001 : 4'b0000; // SUB / ADD
                    3'b001: alu_op = 4'b0010; // SLL
                    3'b010: alu_op = 4'b0011; // SLT
                    3'b011: alu_op = 4'b0100; // SLTU
                    3'b100: alu_op = 4'b0101; // XOR
                    3'b101: alu_op = funct7b5 ? 4'b0111 : 4'b0110; // SRA / SRL
                    3'b110: alu_op = 4'b1000; // OR
                    3'b111: alu_op = 4'b1001; // AND
                endcase
            end
            
            default: ; // Handled by default assignments at the top
        endcase
    end
endmodule