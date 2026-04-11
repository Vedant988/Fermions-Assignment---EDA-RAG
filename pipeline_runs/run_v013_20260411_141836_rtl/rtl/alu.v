```verilog
module alu (
    input  logic [31:0] a,          // operand A
    input  logic [31:0] b,          // operand B
    input  logic [3:0]  alu_op,     // operation selector
    output logic [31:0] result,     // ALU result
    output logic        zero        // zero flag
);

    // Combinational ALU logic
    always_comb begin
        case (alu_op)
            4'b0000: result = a + b;                     // ADD
            4'b0001: result = a - b;                     // SUB
            4'b0010: result = a << b[4:0];               // SLL (shift amount = b[4:0])
            4'b0011: result = ($signed(a) < $signed(b)) ? 1'b1 : 1'b0; // SLT
            4'b0100: result = (a < b) ? 1'b1 : 1'b0;      // SLTU
            4'b0101: result = a ^ b;                     // XOR
            4'b0110: result = a >> b[4:0];               // SRL
            4'b0111: result = $signed(a) >>> b[4:0];     // SRA
            4'b1000: result = a | b;                     // OR
            4'b1001: result = a & b;                     // AND
            default: result = 32'b0;                     // Default to zero
        endcase
        zero = (result == 32'b0);                         // Zero flag
    end

endmodule
```