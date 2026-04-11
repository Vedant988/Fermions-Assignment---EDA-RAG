module load_store(
    input  logic        clk,          // Clock (unused, kept for interface consistency)
    input  logic        mem_read,     // Read enable
    input  logic        mem_write,    // Write enable
    input  logic [1:0]  mem_size,     // 00=byte, 01=halfword, 10=word
    input  logic        mem_extend,   // 0=zero-extend, 1=sign-extend
    input  logic [31:0] addr,         // Byte address of the memory operation
    input  logic [31:0] wdata,        // Data to write (only lower bits used)
    output logic [31:0] rdata,        // Data read from memory (after extension)
    output logic [31:0] mem_addr,     // External memory address bus
    output logic [31:0] mem_wdata,    // External memory write data bus
    output logic [3:0]  mem_wstrb,    // External memory write strobe (byte lanes)
    input  logic [31:0] mem_rdata     // External memory read data bus
);

    // Byte offset within the word (bits [1:0] of the address)
    logic [1:0] byte_offset;
    assign byte_offset = addr[1:0];

    // Pass through the address to the external memory
    assign mem_addr = addr;

    // Generate write strobe based on size and byte offset
    always_comb begin
        case (mem_size)
            2'b00: mem_wstrb = 4'b0001 << byte_offset; // Byte
            2'b01: mem_wstrb = 4'b0011 << byte_offset; // Halfword
            2'b10: mem_wstrb = 4'b1111;                // Word
            default: mem_wstrb = 4'b0000;              // Undefined size
        endcase
        // Disable write strobe when not writing
        if (!mem_write) mem_wstrb = 4'b0000;
    end

    // Prepare write data aligned to the byte offset
    always_comb begin
        logic [31:0] wdata_masked;
        case (mem_size)
            2'b00: wdata_masked = {24'b0, wdata[7:0]};   // Byte
            2'b01: wdata_masked = {16'b0, wdata[15:0]};  // Halfword
            2'b10: wdata_masked = wdata;                // Word
            default: wdata_masked = 32'b0;              // Undefined size
        endcase
        mem_wdata = wdata_masked << (byte_offset * 8);
        // Zero write data when not writing
        if (!mem_write) mem_wdata = 32'b0;
    end

    // Read data extraction and extension
    always_comb begin
        logic [31:0] extracted;
        logic [31:0] extended;
        if (mem_read) begin
            // Shift to the requested byte offset
            extracted = mem_rdata >> (byte_offset * 8);
            // Mask to the requested size
            case (mem_size)
                2'b00: extracted = extracted[7:0];
                2'b01: extracted = extracted[15:0];
                2'b10: extracted = extracted;
                default: extracted = 32'b0;
            endcase
            // Sign or zero extend based on mem_extend
            if (mem_extend) begin
                case (mem_size)
                    2'b00: extended = {{24{extracted[7]}}, extracted[7:0]};
                    2'b01: extended = {{16{extracted[15]}}, extracted[15:0]};
                    2'b10: extended = extracted;
                    default: extended = 32'b0;
                endcase
            end else begin
                case (mem_size)
                    2'b00: extended = {24'b0, extracted[7:0]};
                    2'b01: extended = {16'b0, extracted[15:0]};
                    2'b10: extended = extracted;
                    default: extended = 32'b0;
                endcase
            end
            rdata = extended;
        end else begin
            rdata = 32'b0; // No read, output zero
        end
    end

endmodule