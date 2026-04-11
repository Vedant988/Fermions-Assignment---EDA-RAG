module top (
    input  logic        clk,
    input  logic        resetn,
    
    // Instruction Memory Interface (Fetch)
    output logic [31:0] imem_addr,
    input  logic [31:0] imem_rdata,
    
    // Data Memory Interface (Load/Store)
    output logic [31:0] dmem_addr,
    output logic [31:0] dmem_wdata,
    output logic [3:0]  dmem_wstrb,
    input  logic [31:0] dmem_rdata,
    output logic        dmem_read,  // Exported for testbench state
    output logic        dmem_write  // Exported for testbench state
);

    // ========================================================================
    // 1. PROGRAM COUNTER & INSTRUCTION FETCH
    // ========================================================================
    logic [31:0] pc_reg;
    logic [31:0] next_pc;

    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            pc_reg <= 32'h00000000;
        end else begin
            pc_reg <= next_pc;
        end
    end

    // Route PC to Instruction Memory
    assign imem_addr = pc_reg;
    logic [31:0] instr;
    assign instr = imem_rdata;

    // Instruction Bit-Slicing
    logic [6:0] opcode   = instr[6:0];
    logic [4:0] rd       = instr[11:7];
    logic [2:0] funct3   = instr[14:12];
    logic [4:0] rs1      = instr[19:15];
    logic [4:0] rs2      = instr[24:20];
    logic       funct7b5 = instr[30];

    // ========================================================================
    // 2. CONTROL UNIT
    // ========================================================================
    logic [1:0] ctrl_alu_src_a;
    logic       ctrl_alu_src_b;
    logic [1:0] ctrl_result_src;
    logic       ctrl_reg_write;
    logic       ctrl_mem_read;
    logic       ctrl_mem_write;
    logic [1:0] ctrl_mem_size;
    logic       ctrl_mem_extend;
    logic       ctrl_branch;
    logic [2:0] ctrl_branch_type;
    logic       ctrl_jump;
    logic       ctrl_jump_type;
    logic [3:0] ctrl_alu_op;
    logic [2:0] ctrl_imm_type;

    control u_control (
        .opcode     (opcode),
        .funct3     (funct3),
        .funct7b5   (funct7b5),
        .alu_src_a  (ctrl_alu_src_a),
        .alu_src_b  (ctrl_alu_src_b),
        .result_src (ctrl_result_src),
        .reg_write  (ctrl_reg_write),
        .mem_read   (ctrl_mem_read),
        .mem_write  (ctrl_mem_write),
        .mem_size   (ctrl_mem_size),
        .mem_extend (ctrl_mem_extend),
        .branch     (ctrl_branch),
        .branch_type(ctrl_branch_type),
        .jump       (ctrl_jump),
        .jump_type  (ctrl_jump_type),
        .alu_op     (ctrl_alu_op),
        .imm_type   (ctrl_imm_type)
    );

    // ========================================================================
    // 3. IMMEDIATE GENERATOR
    // ========================================================================
    logic [31:0] imm_val;

    imm_gen u_imm_gen (
        .instr    (instr),
        .imm_type (ctrl_imm_type),
        .imm      (imm_val)
    );

    // ========================================================================
    // 4. REGISTER FILE
    // ========================================================================
    logic [31:0] rs1_data;
    logic [31:0] rs2_data;
    logic [31:0] wb_data;

    regfile u_regfile (
        .clk     (clk),
        .we      (ctrl_reg_write),
        .rs1     (rs1),
        .rs2     (rs2),
        .rd      (rd),
        .rd_data (wb_data),
        .rd1     (rs1_data),
        .rd2     (rs2_data)
    );

    // ========================================================================
    // 5. ALU & MULTIPLEXERS
    // ========================================================================
    logic [31:0] alu_a;
    logic [31:0] alu_b;
    logic [31:0] alu_result;
    logic        alu_zero; // Unused, we use the dedicated branch_unit

    // ALU Source A Mux
    always_comb begin
        case (ctrl_alu_src_a)
            2'b00: alu_a = rs1_data;
            2'b01: alu_a = pc_reg;
            2'b10: alu_a = 32'b0;
            default: alu_a = rs1_data;
        endcase
    end

    // ALU Source B Mux
    assign alu_b = ctrl_alu_src_b ? imm_val : rs2_data;

    alu u_alu (
        .a      (alu_a),
        .b      (alu_b),
        .alu_op (ctrl_alu_op),
        .result (alu_result),
        .zero   (alu_zero)
    );

    // ========================================================================
    // 6. BRANCH UNIT & NEXT PC
    // ========================================================================
    logic branch_cmp_taken;
    logic actual_branch_taken;

    branch_unit u_branch_unit (
        .branch_type (ctrl_branch_type),
        .rs1         (rs1_data),
        .rs2         (rs2_data),
        .taken       (branch_cmp_taken)
    );

    // Branch is only taken if the control unit says it's a branch instruction AND the comparison is true
    assign actual_branch_taken = ctrl_branch & branch_cmp_taken;

    pc_next u_pc_next (
        .pc        (pc_reg),
        .imm       (imm_val),
        .rs1       (rs1_data),
        .taken     (actual_branch_taken),
        .jump      (ctrl_jump),
        .jump_type ({2'b00, ctrl_jump_type}), // Zero padded to match the 3-bit input from earlier module definition
        .pc_next   (next_pc)
    );

    // ========================================================================
    // 7. DATA MEMORY (LOAD / STORE UNIT)
    // ========================================================================
    logic [31:0] ls_rdata;

    // Export control signals for the testbench to handle transactions
    assign dmem_read  = ctrl_mem_read;
    assign dmem_write = ctrl_mem_write;

    load_store u_load_store (
        .clk        (clk),
        .mem_read   (ctrl_mem_read),
        .mem_write  (ctrl_mem_write),
        .mem_size   (ctrl_mem_size),
        .mem_extend (ctrl_mem_extend),
        .addr       (alu_result),
        .wdata      (rs2_data),
        .rdata      (ls_rdata),
        .mem_addr   (dmem_addr),
        .mem_wdata  (dmem_wdata),
        .mem_wstrb  (dmem_wstrb),
        .mem_rdata  (dmem_rdata)
    );

    // ========================================================================
    // 8. WRITEBACK MULTIPLEXER
    // ========================================================================
    always_comb begin
        case (ctrl_result_src)
            2'b00: wb_data = alu_result;         // R-Type, I-Type ALU
            2'b01: wb_data = ls_rdata;           // Loads
            2'b10: wb_data = pc_reg + 32'd4;     // JAL, JALR
            2'b11: wb_data = imm_val;            // LUI
            default: wb_data = alu_result;
        endcase
    end

endmodule