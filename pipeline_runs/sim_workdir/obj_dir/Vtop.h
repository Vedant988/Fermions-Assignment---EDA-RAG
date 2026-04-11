// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Primary design header
//
// This header should be included by all source files instantiating the design.
// The class here is then constructed to instantiate the design.
// See the Verilator manual for examples.

#ifndef _VTOP_H_
#define _VTOP_H_  // guard

#include "verilated.h"

//==========

class Vtop__Syms;

//----------

VL_MODULE(Vtop) {
  public:
    
    // PORTS
    // The application code writes and reads these signals to
    // propagate new values into/out from the Verilated model.
    VL_IN8(clk,0,0);
    VL_IN8(resetn,0,0);
    VL_OUT8(dmem_wstrb,3,0);
    VL_OUT8(dmem_read,0,0);
    VL_OUT8(dmem_write,0,0);
    VL_OUT(imem_addr,31,0);
    VL_IN(imem_rdata,31,0);
    VL_OUT(dmem_addr,31,0);
    VL_OUT(dmem_wdata,31,0);
    VL_IN(dmem_rdata,31,0);
    
    // LOCAL SIGNALS
    // Internals; generally not touched by application code
    CData/*1:0*/ top__DOT__ctrl_alu_src_a;
    CData/*0:0*/ top__DOT__ctrl_alu_src_b;
    CData/*1:0*/ top__DOT__ctrl_result_src;
    CData/*0:0*/ top__DOT__ctrl_reg_write;
    CData/*0:0*/ top__DOT__ctrl_mem_read;
    CData/*0:0*/ top__DOT__ctrl_mem_write;
    CData/*1:0*/ top__DOT__ctrl_mem_size;
    CData/*0:0*/ top__DOT__ctrl_mem_extend;
    CData/*0:0*/ top__DOT__ctrl_branch;
    CData/*2:0*/ top__DOT__ctrl_branch_type;
    CData/*0:0*/ top__DOT__ctrl_jump;
    CData/*0:0*/ top__DOT__ctrl_jump_type;
    CData/*3:0*/ top__DOT__ctrl_alu_op;
    CData/*2:0*/ top__DOT__ctrl_imm_type;
    IData/*31:0*/ top__DOT__pc_reg;
    IData/*31:0*/ top__DOT__next_pc;
    IData/*31:0*/ top__DOT__imm_val;
    IData/*31:0*/ top__DOT__rs1_data;
    IData/*31:0*/ top__DOT__rs2_data;
    IData/*31:0*/ top__DOT__alu_a;
    IData/*31:0*/ top__DOT__alu_b;
    IData/*31:0*/ top__DOT__alu_result;
    IData/*31:0*/ top__DOT__ls_rdata;
    IData/*31:0*/ top__DOT__u_load_store__DOT__unnamedblk1__DOT__wdata_masked;
    IData/*31:0*/ top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted;
    IData/*31:0*/ top__DOT__u_load_store__DOT__unnamedblk2__DOT__extended;
    IData/*31:0*/ top__DOT__u_regfile__DOT__rf[32];
    
    // LOCAL VARIABLES
    // Internals; generally not touched by application code
    CData/*0:0*/ __Vclklast__TOP__clk;
    CData/*0:0*/ __Vclklast__TOP__resetn;
    
    // INTERNAL VARIABLES
    // Internals; generally not touched by application code
    Vtop__Syms* __VlSymsp;  // Symbol table
    
    // CONSTRUCTORS
  private:
    VL_UNCOPYABLE(Vtop);  ///< Copying not allowed
  public:
    /// Construct the model; called by application code
    /// The special name  may be used to make a wrapper with a
    /// single model invisible with respect to DPI scope names.
    Vtop(const char* name = "TOP");
    /// Destroy the model; called (often implicitly) by application code
    ~Vtop();
    
    // API METHODS
    /// Evaluate the model.  Application must call when inputs change.
    void eval() { eval_step(); }
    /// Evaluate when calling multiple units/models per time step.
    void eval_step();
    /// Evaluate at end of a timestep for tracing, when using eval_step().
    /// Application must call after all eval() and before time changes.
    void eval_end_step() {}
    /// Simulation complete, run final blocks.  Application must call on completion.
    void final();
    
    // INTERNAL METHODS
  private:
    static void _eval_initial_loop(Vtop__Syms* __restrict vlSymsp);
  public:
    void __Vconfigure(Vtop__Syms* symsp, bool first);
  private:
    static QData _change_request(Vtop__Syms* __restrict vlSymsp);
    static QData _change_request_1(Vtop__Syms* __restrict vlSymsp);
  public:
    static void _combo__TOP__1(Vtop__Syms* __restrict vlSymsp);
    static void _combo__TOP__5(Vtop__Syms* __restrict vlSymsp);
    static void _combo__TOP__7(Vtop__Syms* __restrict vlSymsp);
  private:
    void _ctor_var_reset() VL_ATTR_COLD;
  public:
    static void _eval(Vtop__Syms* __restrict vlSymsp);
  private:
#ifdef VL_DEBUG
    void _eval_debug_assertions();
#endif  // VL_DEBUG
  public:
    static void _eval_initial(Vtop__Syms* __restrict vlSymsp) VL_ATTR_COLD;
    static void _eval_settle(Vtop__Syms* __restrict vlSymsp) VL_ATTR_COLD;
    static void _sequent__TOP__4(Vtop__Syms* __restrict vlSymsp);
    static void _sequent__TOP__6(Vtop__Syms* __restrict vlSymsp);
    static void _settle__TOP__2(Vtop__Syms* __restrict vlSymsp) VL_ATTR_COLD;
} VL_ATTR_ALIGNED(VL_CACHE_LINE_BYTES);

//----------


#endif  // guard
