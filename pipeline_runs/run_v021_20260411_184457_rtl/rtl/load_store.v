```verilog
module load_store (
    input  logic        mem_read,      // Load request
    input  logic        mem_write,     // Store request
    input  logic [1:0]  mem_size,      // 00=byte, 01=halfword, 10=word
    input  logic        mem_extend,    // 0=sign extend, 1=zero extend
    input  logic [31:0] addr,          // Memory address
    input  logic [31:0] wdata,         // Data to write
    input  logic [31:0] mem_rdata,     // Data read from external memory
    output logic [31:0] rdata,         // Data output to CPU
    output logic [31:0] mem_addr,      // Word‑aligned address for external bus
    output logic [31:0] mem_wdata,     // Data to write on external bus
    output logic [3:0]  mem_wstrb       // Byte‑enable strobes for external bus
);

    // Word‑aligned address: clear the two least‑significant bits
    assign mem_addr = {addr[31:2], 2'b00}; // Align address to 4‑byte boundary

    // Pass through write data unchanged
    assign mem_wdata = wdata;

    // Generate byte‑enable strobes based on store size and address offset
    logic [3:0] wstrb;
    always_comb begin
        if (mem_write) begin
            case (mem_size)
                2'b00: begin // Byte store
                    case (addr[1:0])
                        2'b00: wstrb = 4'b0001;
                        2'b01: wstrb = 4'b0010;
                        2'b10: wstrb = 4'b0100;
                        2'b11: wstrb = 4'b1000;
                        default: wstrb = 4'b0000; // Should never occur
                    endcase
                end
                2'b01: begin // Halfword store
                    case (addr[1:0])
                        2'b00: wstrb = 4'b0011;
                        2'b01: wstrb = 4'b0110;
                        2'b10: wstrb = 4'b1100;
                        2'b11: wstrb = 4'b1001;
                        default: wstrb = 4'b0000; // Should never occur
                    endcase
                end
                2'b10: begin // Word store
                    wstrb = 4'b1111;
                end
                default: wstrb = 4'b0000; // Reserved size
            endcase
        end else begin
            wstrb = 4'b0000; // No write, no strobes
        end
    end
    assign mem_wstrb = wstrb;

    // Sign or zero extend loaded data based on mem_extend and mem_size
    logic [31:0] extended_data;
    always_comb begin
        case (mem_size)
            2'b00: begin // Byte
                if (!mem_extend) // Sign extend
                    extended_data = {{24{mem_rdata[7]}}, mem_rdata[7:0]};
                else // Zero extend
                    extended_data = {24'b0, mem_rdata[7:0]};
            end
            2'b01: begin // Halfword
                if (!mem_extend) // Sign extend
                    extended_data = {{16{mem_rdata[15]}}, mem_rdata[15:0]};
                else // Zero extend
                    extended_data = {16'b0, mem_rdata[15:0]};
            end
            2'b10: begin // Word
                extended_data = mem_rdata;
            end
            default: extended_data = 32'b0; // Reserved size
        endcase
    end

    // Output data only when a load is requested
    assign rdata = mem_read ? extended_data : 32'b0;

endmodule
```