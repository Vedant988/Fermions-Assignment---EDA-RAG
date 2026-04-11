#include <iostream>
#include <fstream>
#include <iomanip>
#include "Vtop.h"
#include "verilated.h"

#define MEM_SIZE (1024 * 1024)
uint8_t main_memory[MEM_SIZE] = {0};

uint32_t read_word(uint32_t addr) {
    if (addr >= MEM_SIZE - 3) return 0;
    return main_memory[addr] | (main_memory[addr+1]<<8) |
           (main_memory[addr+2]<<16) | (main_memory[addr+3]<<24);
}

void write_memory(uint32_t addr, uint32_t data, uint8_t wstrb) {
    if (addr >= MEM_SIZE - 3) return;
    if (wstrb & 0x1) main_memory[addr]   = data & 0xFF;
    if (wstrb & 0x2) main_memory[addr+1] = (data>>8) & 0xFF;
    if (wstrb & 0x4) main_memory[addr+2] = (data>>16) & 0xFF;
    if (wstrb & 0x8) main_memory[addr+3] = (data>>24) & 0xFF;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtop* top = new Vtop;

    if (argc >= 2) {
        std::ifstream file(argv[1], std::ios::binary);
        uint32_t addr = 0;
        while (addr < MEM_SIZE && file.read(reinterpret_cast<char*>(&main_memory[addr]),1)) addr++;
        std::cerr << "Loaded " << std::dec << addr << " bytes\n";
    }

    top->clk = 0; top->resetn = 0;
    uint64_t ticks = 0;
    uint32_t prev_pc = 0xFFFFFFFF;
    int repeat_count = 0;

    while (ticks < 2000) {  // Only 1000 cycles
        top->clk = !top->clk;
        if (ticks > 4) top->resetn = 1;

        top->eval();

        top->imem_rdata = read_word(top->imem_addr);
        top->dmem_rdata = top->dmem_read ? read_word(top->dmem_addr) : 0;

        if (top->clk == 1 && top->dmem_write)
            write_memory(top->dmem_addr, top->dmem_wdata, top->dmem_wstrb);

        top->eval();

        // Detect tohost write
        if (top->clk == 1 && top->dmem_write) {
            std::cout << "MEM WRITE: addr=0x" << std::hex << top->dmem_addr
                      << " data=0x" << top->dmem_wdata << "\n";
            if (top->dmem_addr == 0x00001000) {
                uint32_t v = top->dmem_wdata;
                if (v == 1) std::cout << "TOHOST:PASS\n";
                else std::cout << "TOHOST:FAIL:" << std::dec << (v>>1) << "\n";
                break;
            }
        }

        // Print PC trace on falling edge
        if (top->clk == 0 && top->resetn == 1) {
            uint32_t pc = top->imem_addr;
            if (pc != prev_pc) {
                if (repeat_count > 0)
                    std::cout << "  ^ repeated " << std::dec << repeat_count << "x\n";
                std::cout << "Cycle " << std::dec << (ticks/2)
                          << ": PC=0x" << std::hex << std::setw(8) << std::setfill('0') << pc
                          << " Instr=0x" << std::setw(8) << top->imem_rdata << "\n";
                prev_pc = pc;
                repeat_count = 0;
            } else {
                repeat_count++;
            }
        }
        ticks++;
    }
    if (repeat_count > 0)
        std::cout << "  ^ repeated " << std::dec << repeat_count << "x, STUCK HERE\n";

    top->final(); delete top;
    return 0;
}
