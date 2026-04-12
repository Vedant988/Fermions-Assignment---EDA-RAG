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
    // Default assignments to avoid linter warnings
    always_comb begin
        // Default values
        alu_src_a   = 2'b00;   // rs1
        alu_src_b   = 1'b0;    // rs2
        result_src  = 2'b00;   // ALU result
        reg_write   = 1'b0;
        mem_read    = 1'b0;
        mem_write   = 1'b0;
        mem_size    = 2'b00;   // byte
        mem_extend  = 1'b0;    // sign extend
        branch      = 1'b0;
        branch_type = 3'b000;
        jump        = 1'b0;
        jump_type   = 1'b0;
        alu_op      = 4'b0000; // ADD
        imm_type    = 3'b000;  // R-type

        case (opcode)
            7'b0110111: begin // LUI
                alu_src_a  = 2'b10; // zero
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b11; // imm bypass
                reg_write  = 1'b1;
                imm_type   = 3'b011; // U-type
            end
            7'b0010111: begin // AUIPC
                alu_src_a  = 2'b01; // pc
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                imm_type   = 3'b011; // U-type
            end
            7'b1101111: begin // JAL
                alu_src_a  = 2'b01; // pc
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b10; // pc+4
                reg_write  = 1'b1;
                jump       = 1'b1;
                jump_type  = 1'b0;  // JAL
                imm_type   = 3'b010; // J-type
            end
            7'b1100111: begin // JALR
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b10; // pc+4
                reg_write  = 1'b1;
                jump       = 1'b1;
                jump_type  = 1'b1;  // JALR
                imm_type   = 3'b001; // I-type
            end
            7'b1100011: begin // BRANCH
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b0;  // rs2
                branch     = 1'b1;
                branch_type= funct3;
                imm_type   = 3'b001; // B-type
            end
            7'b0000011: begin // LOAD
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b01; // mem
                reg_write  = 1'b1;
                mem_read   = 1'b1;
                imm_type   = 3'b001; // I-type
                // mem_size and mem_extend based on funct3
                case (funct3)
                    3'b000: begin // LB
                        mem_size   = 2'b00; // byte
                        mem_extend = 1'b0; // sign
                    end
                    3'b001: begin // LH
                        mem_size   = 2'b01; // half
                        mem_extend = 1'b0; // sign
                    end
                    3'b010: begin // LW
                        mem_size   = 2'b10; // word
                        mem_extend = 1'b0; // sign (ignored)
                    end
                    3'b100: begin // LBU
                        mem_size   = 2'b00; // byte
                        mem_extend = 1'b1; // zero
                    end
                    3'b101: begin // LHU
                        mem_size   = 2'b01; // half
                        mem_extend = 1'b1; // zero
                    end
                    default: begin
                        mem_size   = 2'b00;
                        mem_extend = 1'b0;
                    end
                endcase
            end
            7'b0100011: begin // STORE
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                mem_write  = 1'b1;
                imm_type   = 3'b001; // S-type
                // mem_size based on funct3
                case (funct3)
                    3'b000: mem_size = 2'b00; // byte
                    3'b001: mem_size = 2'b01; // half
                    3'b010: mem_size = 2'b10; // word
                    default: mem_size = 2'b00;
                endcase
            end
            7'b0010011: begin // OP-IMM
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b1;  // imm
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                imm_type   = 3'b001; // I-type
                // alu_op based on funct3. Only shifts care about funct7b5.
                case (funct3)
                    3'b000: alu_op = 4'b0000; // ADDI -> ADD
                    3'b010: alu_op = 4'b0011; // SLTI -> SLT
                    3'b011: alu_op = 4'b0100; // SLTIU -> SLTU
                    3'b100: alu_op = 4'b0101; // XORI -> XOR
                    3'b110: alu_op = 4'b1000; // ORI -> OR
                    3'b111: alu_op = 4'b1001; // ANDI -> AND
                    3'b001: alu_op = 4'b0010; // SLLI -> SLL
                    3'b101: alu_op = funct7b5 ? 4'b0111 : 4'b0110; // SRAI / SRLI
                    default: alu_op = 4'b0000;
                endcase
            end
            7'b0110011: begin // OP
                alu_src_a  = 2'b00; // rs1
                alu_src_b  = 1'b0;  // rs2
                result_src = 2'b00; // ALU
                reg_write  = 1'b1;
                imm_type   = 3'b000; // R-type
                // alu_op based on funct3 and funct7b5
                case ({funct3, funct7b5})
                    4'b0000: alu_op = 4'b0000; // ADD
                    4'b0001: alu_op = 4'b0001; // SUB
                    4'b0010: alu_op = 4'b0010; // SLL
                    4'b0100: alu_op = 4'b0011; // SLT
                    4'b0110: alu_op = 4'b0100; // SLTU
                    4'b1000: alu_op = 4'b0101; // XOR
                    4'b1010: alu_op = 4'b0110; // SRL
                    4'b1011: alu_op = 4'b0111; // SRA
                    4'b1100: alu_op = 4'b1000; // OR
                    4'b1110: alu_op = 4'b1001; // AND
                    default: alu_op = 4'b0000; 
                endcase
            end
            default: begin
                // Fully handled by defaults at top of always_comb
            end
        endcase
    end
endmodule