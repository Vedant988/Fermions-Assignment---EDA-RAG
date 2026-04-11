```verilog
module regfile(
    input  logic        clk,        // Clock input
    input  logic        we,         // Write enable
    input  logic [4:0]  rs1,        // Source register 1 address
    input  logic [4:0]  rs2,        // Source register 2 address
    input  logic [4:0]  rd,         // Destination register address
    input  logic [31:0] rd_data,    // Data to write to destination register
    output logic [31:0] rd1,        // Data read from rs1
    output logic [31:0] rd2         // Data read from rs2
);

    // 32 general‑purpose 32‑bit registers
    logic [31:0] rf [31:0];

    // Sequential write logic
    always_ff @(posedge clk) begin
        // Guard against writing to x0 (register 0)
        if (we && rd != 5'd0) begin
            rf[rd] <= rd_data;          // Write data to selected register
        end
    end

    // Combinational read logic
    always_comb begin
        // Read from rs1
        case (rs1)
            5'd0:  rd1 = 32'b0;          // x0 is hardwired to zero
            default: rd1 = rf[rs1];      // Normal register read
        endcase

        // Read from rs2
        case (rs2)
            5'd0:  rd2 = 32'b0;          // x0 is hardwired to zero
            default: rd2 = rf[rs2];      // Normal register read
        endcase
    end

endmodule
```