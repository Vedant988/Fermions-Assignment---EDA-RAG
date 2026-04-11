// load_store.v
// Memory is EXTERNAL. We output mem_addr, mem_wdata, mem_wstrb and read mem_rdata.

module load_store (
    input  wire [31:0] addr,
    input  wire [31:0] wdata,
    input  wire        mem_read,
    input  wire        mem_write,
    input  wire [1:0]  mem_size,   // 00=byte, 01=half, 10=word
    input  wire        mem_extend, // 0=sign-extend, 1=zero-extend
    
    output reg  [31:0] rdata,      // Sent to register file (already extended)
    
    // Flat memory interface to testbench/D-Cache
    output wire [31:0] mem_addr,
    output reg  [31:0] mem_wdata,
    output reg  [3:0]  mem_wstrb,  // Byte enable mask
    input  wire [31:0] mem_rdata
);

    // 1. Memory Address is directly passed to the bus
    // Mask lower 2 bits out since memory is word-aligned outside the CPU usually, 
    // but standard RV32 testbenches expect the raw byte address.
    assign mem_addr = addr;

    // 2. Decode Write Strobe (mem_wstrb) and Shift Write Data (mem_wdata)
    always_comb begin
        mem_wstrb = 4'b0000;
        mem_wdata = wdata; // default pass-through for Word
        
        if (mem_write) begin
            case (mem_size)
                2'b00: begin // SB (Store Byte)
                    mem_wdata = {4{wdata[7:0]}}; // Replicate byte across all lanes
                    mem_wstrb = 4'b0001 << addr[1:0];
                end
                2'b01: begin // SH (Store Half)
                    mem_wdata = {2{wdata[15:0]}}; // Replicate halfword
                    mem_wstrb = addr[1] ? 4'b1100 : 4'b0011;
                end
                2'b10: begin // SW (Store Word)
                    mem_wdata = wdata;
                    mem_wstrb = 4'b1111;
                end
                default: mem_wstrb = 4'b0000;
            endcase
        end
    end

    // 3. Shift Read Data and Sign/Zero Extend (rdata)
    reg [31:0] shifted_rdata;
    always_comb begin
        // Shift data down based on address alignment
        case (addr[1:0])
            2'b00: shifted_rdata = mem_rdata;
            2'b01: shifted_rdata = {8'b0,  mem_rdata[31:8]};
            2'b10: shifted_rdata = {16'b0, mem_rdata[31:16]};
            2'b11: shifted_rdata = {24'b0, mem_rdata[31:24]};
        endcase

        rdata = 32'b0;
        if (mem_read) begin
            case (mem_size)
                2'b00: begin // LB / LBU
                    if (mem_extend == 1'b0) // sign-extend
                        rdata = {{24{shifted_rdata[7]}}, shifted_rdata[7:0]};
                    else                    // zero-extend
                        rdata = {24'b0, shifted_rdata[7:0]};
                end
                2'b01: begin // LH / LHU
                    if (mem_extend == 1'b0) // sign-extend
                        rdata = {{16{shifted_rdata[15]}}, shifted_rdata[15:0]};
                    else                    // zero-extend
                        rdata = {16'b0, shifted_rdata[15:0]};
                end
                2'b10: begin // LW
                    rdata = shifted_rdata;
                end
                default: rdata = 32'b0;
            endcase
        end
    end

endmodule
