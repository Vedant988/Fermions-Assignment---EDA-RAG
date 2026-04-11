#include <iostream>
#include <fstream>
#include <iomanip>
#include "Vtop.h"         
#include "verilated.h"

// 1MB Flat Memory Array
#define MEM_SIZE 1024 * 1024 
uint8_t main_memory[MEM_SIZE] = {0};

uint32_t read_word(uint32_t addr) {
    if (addr >= MEM_SIZE - 3) return 0;
    return main_memory[addr] | (main_memory[addr+1] << 8) | 
           (main_memory[addr+2] << 16) | (main_memory[addr+3] << 24);
}

void write_memory(uint32_t addr, uint32_t data, uint8_t wstrb) {
    if (addr >= MEM_SIZE - 3) return;
    if (wstrb & 0x1) main_memory[addr]   = data & 0xFF;
    if (wstrb & 0x2) main_memory[addr+1] = (data >> 8) & 0xFF;
    if (wstrb & 0x4) main_memory[addr+2] = (data >> 16) & 0xFF;
    if (wstrb & 0x8) main_memory[addr+3] = (data >> 24) & 0xFF;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtop* top = new Vtop;

    // Hardcoded program: ADDI x1, x0, 5 followed by JAL x0, 0 (loop)
    main_memory[0] = 0x93; main_memory[1] = 0x00; main_memory[2] = 0x50; main_memory[3] = 0x00;
    main_memory[4] = 0x6f; main_memory[5] = 0x00; main_memory[6] = 0x00; main_memory[7] = 0x00;

    top->clk = 0;
    top->resetn = 0; 
    uint64_t ticks = 0;

    std::cout << "Starting RISC-V Simulation..." << std::endl;

    while (!Verilated::gotFinish() && ticks < 20) {
        top->clk = !top->clk;
        if (ticks > 4) top->resetn = 1; 

        top->eval(); 

        top->imem_rdata = read_word(top->imem_addr);
        if (top->dmem_read) top->dmem_rdata = read_word(top->dmem_addr);
        else top->dmem_rdata = 0;

        if (top->clk == 1 && top->dmem_write) {
            write_memory(top->dmem_addr, top->dmem_wdata, top->dmem_wstrb);
        }

        top->eval(); 

        if (top->clk == 1 && top->dmem_write && top->dmem_addr == 0x80001000) {
            uint32_t tohost_val = top->dmem_wdata;
            if (tohost_val == 1) std::cout << "✅ TEST PASSED!" << std::endl;
            else std::cout << "❌ TEST FAILED code: " << (tohost_val >> 1) << std::endl;
            break; 
        }

        if (top->clk == 0 && top->resetn == 1) {
            std::cout << "Cycle: " << (ticks / 2) 
                      << " | PC: 0x" << std::setfill('0') << std::setw(8) << std::hex << top->imem_addr 
                      << " | Instr: 0x" << std::setw(8) << top->imem_rdata 
                      << std::endl;
        }
        ticks++;
    }

    std::cout << "Simulation Ended." << std::endl;
    top->final();
    delete top;
    return 0;
}
