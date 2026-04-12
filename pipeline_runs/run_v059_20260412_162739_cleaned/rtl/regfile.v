module regfile (
    input  logic        clk,      // Clock input
    input  logic        we,       // Write enable
    input  logic [4:0]  rs1,      // Source register 1
    input  logic [4:0]  rs2,      // Source register 2
    input  logic [4:0]  rd,       // Destination register
    input  logic [31:0] rd_data,  // Data to write
    output logic [31:0] rd1,      // Read data from rs1
    output logic [31:0] rd2       // Read data from rs2
);

    // 32 general‑purpose registers (x0–x31)
    logic [31:0] rf [31:0];

    // Sequential write: on rising edge of clk
    always_ff @(posedge clk) begin
        // Guard against writing to x0 (hardwired to zero)
        if (we && rd != 5'd0) begin
            rf[rd] <= rd_data;
        end
    end

    // Combinational read: outputs are always the current register values
    always_comb begin
        rd1 = rf[rs1];
        rd2 = rf[rs2];
    end

endmodule