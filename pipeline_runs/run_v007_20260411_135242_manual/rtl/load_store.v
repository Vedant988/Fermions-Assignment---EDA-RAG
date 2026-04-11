```verilog
module load_store (
    input  logic        clk,
    input  logic        mem_read,
    input  logic        mem_write,
    input  logic [1:0]  mem_size,   // 00=byte, 01=halfword, 10=word
    input  logic        mem_extend, // 1=sign‑extend, 0=zero‑extend
    input  logic [31:0] addr,
    input  logic [31:0] wdata,
    output logic [31:0] rdata
);
    // 4‑KB memory (1024 words)
    logic [31:0] mem [0:1023];

    // Write logic (sequential)
    always_ff @(posedge clk) begin
        if (mem_write) begin
            case (mem_size)
                2'b00: begin // byte write
                    // write 8 bits to the selected byte
                    mem[addr[11:2]][addr[1:0]*8 +:8] <= wdata[7:0];
                end
                2'b01: begin // halfword write
                    // write 16 bits to the selected halfword
                    mem[addr[11:2]][addr[1:0]*8 +:16] <= wdata[15:0];
                end
                2'b10: begin // word write
                    mem[addr[11:2]] <= wdata;
                end
                default: ; // no operation for undefined size
            endcase
        end
    end

    // Read logic (combinational)
    always_comb begin
        if (mem_read) begin
            case (mem_size)
                2'b00: begin // byte read
                    // sign‑extend or zero‑extend the selected byte
                    if (mem_extend)
                        rdata = {{24{mem[addr[11:2]][addr[1:0]*8 +:8][7]}},
                                 mem[addr[11:2]][addr[1:0]*8 +:8]};
                    else
                        rdata = {{24{1'b0}},
                                 mem[addr[11:2]][addr[1:0]*8 +:8]};
                end
                2'b01: begin // halfword read
                    // sign‑extend or zero‑extend the selected halfword
                    if (mem_extend)
                        rdata = {{16{mem[addr[11:2]][addr[1:0]*8 +:16][15]}},
                                 mem[addr[11:2]][addr[1:0]*8 +:16]};
                    else
                        rdata = {{16{1'b0}},
                                 mem[addr[11:2]][addr[1:0]*8 +:16]};
                end
                2'b10: begin // word read
                    rdata = mem[addr[11:2]];
                end
                default: rdata = 32'b0; // undefined size
            endcase
        end else begin
            rdata = 32'b0; // no read
        end
    end
endmodule
```