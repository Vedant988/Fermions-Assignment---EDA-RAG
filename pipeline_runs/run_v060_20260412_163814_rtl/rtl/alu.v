module alu (
    input  logic [31:0] a,
    input  logic [31:0] b,
    input  logic [3:0]  alu_op,
    output logic [31:0] result,
    output logic        zero
);
    // Shift amount is the lower 5 bits of operand b
    logic [4:0] shamt = b[4:0];

    // Signed intermediate for arithmetic right shift
    logic signed [31:0] signed_a;
    assign signed_a = $signed(a);

    always_comb begin
        case (alu_op)
            4'b0000: result = a + b;                                 // ADD
            4'b0001: result = a - b;                                 // SUB
            4'b0010: result = a << shamt;                            // SLL
            4'b0011: result = ($signed(a) < $signed(b)) ? 32'b1 : 32'b0; // SLT
            4'b0100: result = (a < b) ? 32'b1 : 32'b0;                // SLTU
            4'b0101: result = a ^ b;                                 // XOR
            4'b0110: result = a >> shamt;                            // SRL
            4'b0111: result = signed_a >>> shamt;                    // SRA
            4'b1000: result = a | b;                                 // OR
            4'b1001: result = a & b;                                 // AND
            default: result = 32'b0;                                 // Undefined op
        endcase
    end

    // Zero flag: true when result is zero
    assign zero = (result == 32'b0);
endmodule