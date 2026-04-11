```verilog
// Control unit for a single‑cycle RV32I core
module control (
    input  wire [6:0] opcode,
    input  wire [2:0] funct3,
    input  wire       funct7b5,          // bit 5 of funct7

    output reg  [1:0] alu_src_a,        // 00=rs1, 01=pc, 10=zero
    output reg        alu_src_b,        // 0=rs2, 1=imm
    output reg  [1:0] result_src,       // 00=ALU, 01=mem, 10=pc+4, 11=imm
    output reg        reg_write,
    output reg        mem_read,
    output reg        mem_write,
    output reg  [1:0] mem_size,         // 00=byte, 01=half, 10=word
    output reg        mem_extend,       // 0=sign, 1=zero
    output reg        branch,
    output reg  [2:0] branch_type,      // 0=eq,1=ne,2=lt,3=ge,4=ltu,5=geu
    output reg        jump,
    output reg        jump_type,        // 0=JAL, 1=JALR
    output reg  [3:0] alu_op,           // ALU operation code
    output reg  [2:0] imm_type          // 000=I,001=S,010=B,011=U,100=J
);

    // Default assignments
    always_comb begin
        // Default values for all outputs
        alu_src_a   = 2'b00;   // rs1
        alu_src_b   = 1'b0;    // rs2
        result_src  = 2'b00;   // ALU result
        reg_write   = 1'b0;
        mem_read    = 1'b0;
        mem_write   = 1'b0;
        mem_size    = 2'b00;   // byte
        mem_extend  = 1'b0;    // sign‑extend
        branch      = 1'b0;
        branch_type = 3'b000;
        jump        = 1'b0;
        jump_type   = 1'b0;
        alu_op      = 4'b0000; // ADD
        imm_type    = 3'b000;  // I‑type

        case (opcode)
            // LUI
            7'b0110111: begin
                alu_src_a   = 2'b10;   // zero
                alu_src_b   = 1'b1;    // imm
                result_src  = 2'b11;   // imm bypass
                reg_write   = 1'b1;
                imm_type    = 3'b011;  // U‑type
                // ALU not used, but set to ADD for consistency
                alu_op      = 4'b0000;
            end

            // AUIPC
            7'b0010111: begin
                alu_src_a   = 2'b01;   // pc
                alu_src_b   = 1'b1;    // imm
                result_src  = 2'b11;   // imm bypass
                reg_write   = 1'b1;
                imm_type    = 3'b011;  // U‑type
                alu_op      = 4'b0000; // ADD
            end

            // JAL
            7'b1101111: begin
                alu_src_a   = 2'b01;   // pc
                alu_src_b   = 1'b1;    // imm
                result_src  = 2'b10;   // pc+4
                reg_write   = 1'b1;
                jump        = 1'b1;
                jump_type   = 1'b0;    // JAL
                imm_type    = 3'b100;  // J‑type
                alu_op      = 4'b0000; // ADD
            end

            // JALR
            7'b1100111: begin
                alu_src_a   = 2'b01;   // pc
                alu_src_b   = 1'b1;    // imm
                result_src  = 2'b10;   // pc+4
                reg_write   = 1'b1;
                jump        = 1'b1;
                jump_type   = 1'b1;    // JALR
                imm_type    = 3'b000;  // I‑type
                alu_op      = 4'b0000; // ADD
            end

            // Branches
            7'b1100011: begin
                alu_src_a   = 2'b00;   // rs1
                alu_src_b   = 1'b0;    // rs2
                branch      = 1'b1;
                imm_type    = 3'b010;  // B‑type
                // Branch type derived from funct3
                case (funct3)
                    3'b000: branch_type = 3'b000; // BEQ
                    3'b001: branch_type = 3'b001; // BNE
                    3'b100: branch_type = 3'b010; // BLT
                    3'b101: branch_type = 3'b011; // BGE
                    3'b110: branch_type = 3'b100; // BLTU
                    3'b111: branch_type = 3'b101; // BGEU
                    default: branch_type = 3'b000;
                endcase
                // ALU used for address calculation
                alu_op = 4'b0000; // ADD
            end

            // Loads
            7'b0000011: begin
                alu_src_a   = 2'b00;   // rs1
                alu_src_b   = 1'b1;    // imm
                result_src  = 2'b01;   // mem data
                reg_write   = 1'b1;
                mem_read    = 1'b1;
                imm_type    = 3'b000;  // I‑type
                // Determine size and extend from funct3
                case (funct3)
                    3'b000: begin // LB
                        mem_size   = 2'b00; // byte
                        mem_extend = 1'b0;  // sign‑extend
                        alu_op     = 4'b0000; // ADD
                    end
                    3'b001: begin // LH
                        mem_size   = 2'b01; // half
                        mem_extend = 1'b0;  // sign‑extend
                        alu_op     = 4'b0000;
                    end
                    3'b010: begin // LW
                        mem_size   = 2'b10; // word
                        mem_extend = 1'b0;  // sign‑extend
                        alu_op     = 4'b0000;
                    end
                    3'b100: begin // LBU
                        mem_size   = 2'b00; // byte
                        mem_extend = 1'b1;  // zero‑extend
                        alu_op     = 4'b0000;
                    end
                    3'b101: begin // LHU
                        mem_size   = 2'b01; // half
                        mem_extend = 1'b1;  // zero‑extend
                        alu_op     = 4'b0000;
                    end
                    default: begin
                        mem_size   = 2'b00;
                        mem_extend = 1'b0;
                        alu_op     = 4'b0000;
                    end
                endcase
            end

            // Stores
            7'b0100011: begin
                alu_src_a   = 2'b00;   // rs1
                alu_src_b   =