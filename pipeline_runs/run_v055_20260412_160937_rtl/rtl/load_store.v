module load_store (
    input  logic        mem_read,          // Read enable
    input  logic        mem_write,         // Write enable
    input  logic [1:0]  mem_size,          // 00=byte, 01=halfword, 10=word
    input  logic        mem_extend,        // 0=sign‑extend, 1=zero‑extend
    input  logic [31:0] addr,              // Memory address
    input  logic [31:0] wdata,             // Data to write
    input  logic [31:0] mem_rdata,         // Data read from external memory
    output logic [31:0] rdata,             // Data to register file
    output logic [31:0] mem_addr,          // Word‑aligned address for external bus
    output logic [31:0] mem_wdata,         // Data to write on external bus
    output logic [3:0]  mem_wstrb          // Byte‑enable strobes
);

    // Byte offset within the word (bits [1:0] of the address)
    logic [1:0] byte_offset;
    assign byte_offset = addr[1:0];

    // Word‑aligned address for the external memory bus
    assign mem_addr = {addr[31:2], 2'b00};

    // Shift amount for aligning data and strobes (byte_offset * 8)
    logic [4:0] shift_amt;
    assign shift_amt = byte_offset << 3;   // 8 * byte_offset

    // Generate byte‑enable strobes based on mem_size and byte_offset
    always_comb begin
        case (mem_size)
            2'b00: begin // Byte store
                case (byte_offset)
                    2'b00: mem_wstrb = 4'b0001;
                    2'b01: mem_wstrb = 4'b0010;
                    2'b10: mem_wstrb = 4'b0100;
                    2'b11: mem_wstrb = 4'b1000;
                endcase
            end
            2'b01: begin // Halfword store
                case (byte_offset)
                    2'b00: mem_wstrb = 4'b0011;
                    2'b10: mem_wstrb = 4'b1100;
                    default: mem_wstrb = 4'b0000; // misaligned
                endcase
            end
            2'b10: begin // Word store
                mem_wstrb = 4'b1111;
            end
            default: mem_wstrb = 4'b0000; // undefined size
        endcase
    end

    // Mask for the selected bytes (used for both write data and load extraction)
    logic [31:0] byte_mask;
    always_comb begin
        case (mem_size)
            2'b00: byte_mask = 32'h000000ff << (byte_offset * 8);
            2'b01: byte_mask = 32'h0000ffff << (byte_offset * 8);
            2'b10: byte_mask = 32'hffffffff; // whole word
            default: byte_mask = 32'b0;
        endcase
    end

    // Write data aligned to the target byte lane and masked by strobes
    logic [31:0] wdata_shifted;
    assign wdata_shifted = wdata << shift_amt;
    assign mem_wdata = (wdata_shifted & byte_mask) & (mem_wstrb << shift_amt);

    // Load data extraction and extension
    logic [31:0] extracted;
    assign extracted = mem_rdata >> shift_amt;

    logic [31:0] extracted_masked;
    assign extracted_masked = extracted & byte_mask;

    logic signed [31:0] signed_extracted;
    assign signed_extracted = $signed(extracted_masked);

    // Sign or zero extend based on mem_extend
    assign rdata = mem_extend ? extracted_masked : signed_extracted;

endmodule