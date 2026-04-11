```verilog
module regfile(
    input  logic        clk,      // clock
    input  logic        we,       // write enable
    input  logic [4:0]  rs1,      // source register 1
    input  logic [4:0]  rs2,      // source register 2
    input  logic [4:0]  rd,       // destination register
    input  logic [31:0] rd_data,  // data to write
    output logic [31:0] rd1,      // read data from rs1
    output logic [31:0] rd2       // read data from rs2
);

    // 32 general‑purpose registers, 32 bits each
    logic [31:0] rf [0:31];

    // Write port: register file write
    always_ff @(posedge clk) begin
        // Guard against writing to x0 (register 0)
        if (we && rd != 5'd0) begin
            rf[rd] <= rd_data; // non‑obvious: write only when enabled and rd ≠ 0
        end
    end

    // Read ports: combinational logic
    always_comb begin
        // Default values to avoid latches
        rd1 = 32'd0;
        rd2 = 32'd0;
        // Read rs1 if not x0
        if (rs1 != 5'd0) begin
            rd1 = rf[rs1];
        end
        // Read rs2 if not x0
        if (rs2 != 5'd0) begin
            rd2 = rf[rs2];
        end
    end

endmodule
```