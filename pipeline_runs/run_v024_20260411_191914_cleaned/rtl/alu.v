module alu (
    input  logic [31:0] a,          // operand A
    input  logic [31:0] b,          // operand B
    input  logic [3:0]  alu_op,     // operation code
    output logic [31:0] result,     // ALU result
    output logic        zero        // zero flag
);
    // Internal wires for shift amount and signed comparison
    logic [4:0] shamt;             // shift amount (b[4:0])
    logic [31:0] signed_a;         // signed version of a
    logic [31:0] signed_b;         // signed version of b

    // Assign shift amount explicitly to avoid implicit truncation
    assign shamt = b[4:0];

    // Convert operands to signed for signed operations
    assign signed_a = a;
    assign signed_b = b;

    // Combinational ALU logic
    always_comb begin
        // Default assignments
        result = 32'b0;            // default result
        zero   = 1'b0;             // default zero flag

        case (alu_op)
            // 4'b0000: ADD
            4'b0000: begin
                result = a + b;     // addition
            end
            // 4'b0001: SUB
            4'b0001: begin
                result = a - b;     // subtraction
            end
            // 4'b0010: AND
            4'b0010: begin
                result = a & b;     // bitwise AND
            end
            // 4'b0011: OR
            4'b0011: begin
                result = a | b;     // bitwise OR
            end
            // 4'b0100: XOR
            4'b0100: begin
                result = a ^ b;     // bitwise XOR
            end
            // 4'b0101: SLL (logical left shift)
            4'b0101: begin
                result = a << shamt; // shift left
            end
            // 4'b0110: SRL (logical right shift)
            4'b0110: begin
                result = a >> shamt; // shift right logical
            end
            // 4'b0111: SRA (arithmetic right shift)
            4'b0111: begin
                result = a >>> shamt; // shift right arithmetic
            end
            // 4'b1000: SLT (signed less than)
            4'b1000: begin
                result = ($signed(a) < $signed(b)) ? 32'b1 : 32'b0;
            end
            // 4'b1001: SLTU (unsigned less than)
            4'b1001: begin
                result = (a < b) ? 32'b1 : 32'b0;
            end
            // Default: result remains zero
            default: begin
                result = 32'b0;
            end
        endcase

        // Zero flag: true if result is all zeros
        zero = (result == 32'b0);
    end
endmodule