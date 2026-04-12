module top(
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
    // Instruction fields
    wire [31:0] instr = imem_rdata;
    wire [6:0]  opcode   = instr[6:0];
    wire [2:0]  funct3   = instr[14:12];
    wire        funct7b5 = instr[30];
    wire [4:0]  rs1      = instr[19:15];
    wire [4:0]  rs2      = instr[24:20];
    wire [4:0]  rd       = instr[11:7];

    // Control signals
    wire [3:0]  alu_op;
    wire [1:0]  alu_src_a;
    wire        alu_src_b;
    wire [1:0]  result_src;
    wire        reg_write;
    wire        mem_read;
    wire        mem_write;
    wire [1:0]  mem_size;
    wire        mem_extend;
    wire        branch;
    wire [2:0]  branch_type;
    wire        jump;
    wire        jump_type;
    wire [2:0]  imm_type;

    // Immediate
    wire [31:0] imm;

    // Core state
    reg  [31:0] pc;
    wire [31:0] next_pc;
    wire [31:0] result;

    // Register file
    wire [31:0] rs1_data;
    wire [31:0] rs2_data;
    regfile u_regfile (
        .clk      (clk),
        .we       (reg_write),
        .rs1      (rs1),
        .rs2      (rs2),
        .rd       (rd),
        .rd_data  (result),
        .rd1      (rs1_data),
        .rd2      (rs2_data)
    );

    // Immediate generator
    imm_gen u_imm_gen (
        .instr    (instr),
        .imm_type (imm_type),
        .imm      (imm)
    );

    // Control unit
    control u_control (
        .opcode      (opcode),
        .funct3      (funct3),
        .funct7b5    (funct7b5),
        .alu_src_a   (alu_src_a),
        .alu_src_b   (alu_src_b),
        .result_src  (result_src),
        .reg_write   (reg_write),
        .mem_read    (mem_read),
        .mem_write   (mem_write),
        .mem_size    (mem_size),
        .mem_extend  (mem_extend),
        .branch      (branch),
        .branch_type (branch_type),
        .jump        (jump),
        .jump_type   (jump_type),
        .alu_op      (alu_op),
        .imm_type    (imm_type)
    );

    // ALU operands
    wire [31:0] zero = 32'b0;
    wire [31:0] alu_a = (alu_src_a == 2'b00) ? rs1_data :
                        (alu_src_a == 2'b01) ? pc :
                        zero; // alu_src_a == 2'b10
    wire [31:0] alu_b = (alu_src_b == 1'b0) ? rs2_data : imm;

    // ALU
    wire [31:0] alu_result;
    wire        alu_zero; // not used
    alu u_alu (
        .a        (alu_a),
        .b        (alu_b),
        .alu_op   (alu_op),
        .result   (alu_result),
        .zero     (alu_zero)
    );

    // Branch unit
    wire taken;
    branch_unit u_branch_unit (
        .branch_type (branch_type),
        .rs1         (rs1_data),
        .rs2         (rs2_data),
        .taken       (taken)
    );

    // Load/Store
    wire [31:0] mem_rdata;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0]  mem_wstrb;
    load_store u_load_store (
        .mem_read   (mem_read),
        .mem_write  (mem_write),
        .mem_size   (mem_size),
        .mem_extend (mem_extend),
        .addr       (alu_result), // ALU result is the address
        .wdata      (rs2_data),   // Store data comes from rs2
        .mem_rdata  (dmem_rdata),
        .rdata      (mem_rdata),
        .mem_addr   (mem_addr),
        .mem_wdata  (mem_wdata),
        .mem_wstrb  (mem_wstrb)
    );

    // Result mux
    wire [31:0] pc_plus4 = pc + 32'd4;
    assign result = (result_src == 2'b00) ? alu_result :
                    (result_src == 2'b01) ? mem_rdata :
                    (result_src == 2'b10) ? pc_plus4 :
                    imm; // result_src == 2'b11

    // Next PC logic
    pc_next u_pc_next (
        .pc        (pc),
        .imm       (imm),
        .rs1       (rs1_data),
        .taken     (taken),
        .jump      (jump),
        .jump_type (jump_type),
        .next_pc   (next_pc)
    );

    // PC update
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            pc <= 32'h00000000;
        end else begin
            pc <= next_pc;
        end
    end

    // Memory interface assignments
    assign imem_addr  = pc;
    assign dmem_addr  = mem_addr;
    assign dmem_wdata = mem_wdata;
    assign dmem_wstrb = mem_wstrb;
    assign dmem_read  = mem_read;
    assign dmem_write = mem_write;

endmodule