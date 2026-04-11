// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop.h"
#include "Vtop__Syms.h"

//==========

VL_CTOR_IMP(Vtop) {
    Vtop__Syms* __restrict vlSymsp = __VlSymsp = new Vtop__Syms(this, name());
    Vtop* const __restrict vlTOPp VL_ATTR_UNUSED = vlSymsp->TOPp;
    // Reset internal values
    
    // Reset structure values
    _ctor_var_reset();
}

void Vtop::__Vconfigure(Vtop__Syms* vlSymsp, bool first) {
    if (false && first) {}  // Prevent unused
    this->__VlSymsp = vlSymsp;
    if (false && this->__VlSymsp) {}  // Prevent unused
    Verilated::timeunit(-12);
    Verilated::timeprecision(-12);
}

Vtop::~Vtop() {
    VL_DO_CLEAR(delete __VlSymsp, __VlSymsp = NULL);
}

void Vtop::_settle__TOP__2(Vtop__Syms* __restrict vlSymsp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop::_settle__TOP__2\n"); );
    Vtop* const __restrict vlTOPp VL_ATTR_UNUSED = vlSymsp->TOPp;
    // Body
    vlTOPp->top__DOT__ctrl_branch = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_branch = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_branch_type = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_branch_type 
                                    = (7U & (vlTOPp->imem_rdata 
                                             >> 0xcU));
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_jump = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((8U & vlTOPp->imem_rdata)) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_jump = 1U;
                            }
                        }
                    }
                } else {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_jump = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_jump_type = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((8U & vlTOPp->imem_rdata)) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_jump_type = 0U;
                            }
                        }
                    }
                } else {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_jump_type = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_mem_extend = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((1U & (~ (vlTOPp->imem_rdata >> 5U)))) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_mem_extend 
                                    = (1U & (vlTOPp->imem_rdata 
                                             >> 0xeU));
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_mem_read = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((1U & (~ (vlTOPp->imem_rdata >> 5U)))) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_mem_read = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_mem_write = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_mem_write = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_mem_size = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_mem_size 
                                    = (3U & (vlTOPp->imem_rdata 
                                             >> 0xcU));
                            }
                        }
                    }
                }
            }
        } else {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_mem_size 
                                    = (3U & (vlTOPp->imem_rdata 
                                             >> 0xcU));
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_alu_op = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_op 
                                    = ((0x4000U & vlTOPp->imem_rdata)
                                        ? ((0x2000U 
                                            & vlTOPp->imem_rdata)
                                            ? ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 9U
                                                : 8U)
                                            : ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? (
                                                   (0x40000000U 
                                                    & vlTOPp->imem_rdata)
                                                    ? 7U
                                                    : 6U)
                                                : 5U))
                                        : ((0x2000U 
                                            & vlTOPp->imem_rdata)
                                            ? ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 4U
                                                : 3U)
                                            : ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 2U
                                                : (
                                                   (0x40000000U 
                                                    & vlTOPp->imem_rdata)
                                                    ? 1U
                                                    : 0U))));
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_op = 0U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_op = 0U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_op 
                                    = ((0x4000U & vlTOPp->imem_rdata)
                                        ? ((0x2000U 
                                            & vlTOPp->imem_rdata)
                                            ? ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 9U
                                                : 8U)
                                            : ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? (
                                                   (0x40000000U 
                                                    & vlTOPp->imem_rdata)
                                                    ? 7U
                                                    : 6U)
                                                : 5U))
                                        : ((0x2000U 
                                            & vlTOPp->imem_rdata)
                                            ? ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 4U
                                                : 3U)
                                            : ((0x1000U 
                                                & vlTOPp->imem_rdata)
                                                ? 2U
                                                : 0U)));
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_op = 0U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_alu_src_a = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 2U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 0U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 0U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 1U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 0U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_a = 0U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_alu_src_b = 0U;
    if ((1U & (~ (vlTOPp->imem_rdata >> 6U)))) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 1U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 0U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 1U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 1U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 1U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_alu_src_b = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_imm_type = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((8U & vlTOPp->imem_rdata)) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 4U;
                            }
                        }
                    }
                } else {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 0U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 2U;
                            }
                        }
                    }
                }
            }
        }
    } else {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 3U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 1U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 3U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 0U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_imm_type = 0U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_result_src = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((8U & vlTOPp->imem_rdata)) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 2U;
                            }
                        }
                    }
                } else {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 2U;
                            }
                        }
                    }
                }
            }
        }
    } else {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 3U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 0U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 0U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 0U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_result_src = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__ctrl_reg_write = 0U;
    if ((0x40U & vlTOPp->imem_rdata)) {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((1U & (~ (vlTOPp->imem_rdata >> 4U)))) {
                if ((8U & vlTOPp->imem_rdata)) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    }
                } else {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    }
                }
            }
        }
    } else {
        if ((0x20U & vlTOPp->imem_rdata)) {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    }
                }
            }
        } else {
            if ((0x10U & vlTOPp->imem_rdata)) {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((4U & vlTOPp->imem_rdata)) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    } else {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    }
                }
            } else {
                if ((1U & (~ (vlTOPp->imem_rdata >> 3U)))) {
                    if ((1U & (~ (vlTOPp->imem_rdata 
                                  >> 2U)))) {
                        if ((2U & vlTOPp->imem_rdata)) {
                            if ((1U & vlTOPp->imem_rdata)) {
                                vlTOPp->top__DOT__ctrl_reg_write = 1U;
                            }
                        }
                    }
                }
            }
        }
    }
    vlTOPp->top__DOT__rs1_data = 0U;
    if ((0U != (0x1fU & (vlTOPp->imem_rdata >> 0xfU)))) {
        vlTOPp->top__DOT__rs1_data = vlTOPp->top__DOT__u_regfile__DOT__rf
            [(0x1fU & (vlTOPp->imem_rdata >> 0xfU))];
    }
    vlTOPp->top__DOT__rs2_data = 0U;
    if ((0U != (0x1fU & (vlTOPp->imem_rdata >> 0x14U)))) {
        vlTOPp->top__DOT__rs2_data = vlTOPp->top__DOT__u_regfile__DOT__rf
            [(0x1fU & (vlTOPp->imem_rdata >> 0x14U))];
    }
    vlTOPp->imem_addr = vlTOPp->top__DOT__pc_reg;
    vlTOPp->dmem_read = vlTOPp->top__DOT__ctrl_mem_read;
    vlTOPp->dmem_write = vlTOPp->top__DOT__ctrl_mem_write;
    vlTOPp->top__DOT__imm_val = ((4U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                  ? ((2U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                      ? 0U : ((1U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                               ? 0U
                                               : ((0xffe00000U 
                                                   & ((- (IData)(
                                                                 (1U 
                                                                  & (vlTOPp->imem_rdata 
                                                                     >> 0x1fU)))) 
                                                      << 0x15U)) 
                                                  | ((0x100000U 
                                                      & (vlTOPp->imem_rdata 
                                                         >> 0xbU)) 
                                                     | ((0xff000U 
                                                         & vlTOPp->imem_rdata) 
                                                        | ((0x800U 
                                                            & (vlTOPp->imem_rdata 
                                                               >> 9U)) 
                                                           | (0x7feU 
                                                              & (vlTOPp->imem_rdata 
                                                                 >> 0x14U))))))))
                                  : ((2U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                      ? ((1U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                          ? (0xfffff000U 
                                             & vlTOPp->imem_rdata)
                                          : ((0xffffe000U 
                                              & ((- (IData)(
                                                            (1U 
                                                             & (vlTOPp->imem_rdata 
                                                                >> 0x1fU)))) 
                                                 << 0xdU)) 
                                             | ((0x1000U 
                                                 & (vlTOPp->imem_rdata 
                                                    >> 0x13U)) 
                                                | ((0x800U 
                                                    & (vlTOPp->imem_rdata 
                                                       << 4U)) 
                                                   | ((0x7e0U 
                                                       & (vlTOPp->imem_rdata 
                                                          >> 0x14U)) 
                                                      | (0x1eU 
                                                         & (vlTOPp->imem_rdata 
                                                            >> 7U)))))))
                                      : ((1U & (IData)(vlTOPp->top__DOT__ctrl_imm_type))
                                          ? ((0xfffff000U 
                                              & ((- (IData)(
                                                            (1U 
                                                             & (vlTOPp->imem_rdata 
                                                                >> 0x1fU)))) 
                                                 << 0xcU)) 
                                             | ((0xfe0U 
                                                 & (vlTOPp->imem_rdata 
                                                    >> 0x14U)) 
                                                | (0x1fU 
                                                   & (vlTOPp->imem_rdata 
                                                      >> 7U))))
                                          : ((0xfffff000U 
                                              & ((- (IData)(
                                                            (1U 
                                                             & (vlTOPp->imem_rdata 
                                                                >> 0x1fU)))) 
                                                 << 0xcU)) 
                                             | (0xfffU 
                                                & (vlTOPp->imem_rdata 
                                                   >> 0x14U))))));
    vlTOPp->top__DOT__alu_a = ((0U == (IData)(vlTOPp->top__DOT__ctrl_alu_src_a))
                                ? vlTOPp->top__DOT__rs1_data
                                : ((1U == (IData)(vlTOPp->top__DOT__ctrl_alu_src_a))
                                    ? vlTOPp->top__DOT__pc_reg
                                    : ((2U == (IData)(vlTOPp->top__DOT__ctrl_alu_src_a))
                                        ? 0U : vlTOPp->top__DOT__rs1_data)));
    vlTOPp->top__DOT__alu_b = ((IData)(vlTOPp->top__DOT__ctrl_alu_src_b)
                                ? vlTOPp->top__DOT__imm_val
                                : vlTOPp->top__DOT__rs2_data);
    vlTOPp->top__DOT__next_pc = ((IData)(4U) + vlTOPp->top__DOT__pc_reg);
    if (vlTOPp->top__DOT__ctrl_jump) {
        vlTOPp->top__DOT__next_pc = ((IData)(vlTOPp->top__DOT__ctrl_jump_type)
                                      ? ((IData)(vlTOPp->top__DOT__ctrl_jump_type)
                                          ? (0xfffffffeU 
                                             & (vlTOPp->top__DOT__rs1_data 
                                                + vlTOPp->top__DOT__imm_val))
                                          : ((IData)(4U) 
                                             + vlTOPp->top__DOT__pc_reg))
                                      : (vlTOPp->top__DOT__pc_reg 
                                         + vlTOPp->top__DOT__imm_val));
    } else {
        if (((IData)(vlTOPp->top__DOT__ctrl_branch) 
             & ((4U & (IData)(vlTOPp->top__DOT__ctrl_branch_type))
                 ? ((~ ((IData)(vlTOPp->top__DOT__ctrl_branch_type) 
                        >> 1U)) & ((1U & (IData)(vlTOPp->top__DOT__ctrl_branch_type))
                                    ? (vlTOPp->top__DOT__rs1_data 
                                       >= vlTOPp->top__DOT__rs2_data)
                                    : (vlTOPp->top__DOT__rs1_data 
                                       < vlTOPp->top__DOT__rs2_data)))
                 : ((2U & (IData)(vlTOPp->top__DOT__ctrl_branch_type))
                     ? ((1U & (IData)(vlTOPp->top__DOT__ctrl_branch_type))
                         ? VL_GTES_III(1,32,32, vlTOPp->top__DOT__rs1_data, vlTOPp->top__DOT__rs2_data)
                         : VL_LTS_III(1,32,32, vlTOPp->top__DOT__rs1_data, vlTOPp->top__DOT__rs2_data))
                     : ((1U & (IData)(vlTOPp->top__DOT__ctrl_branch_type))
                         ? (vlTOPp->top__DOT__rs1_data 
                            != vlTOPp->top__DOT__rs2_data)
                         : (vlTOPp->top__DOT__rs1_data 
                            == vlTOPp->top__DOT__rs2_data)))))) {
            vlTOPp->top__DOT__next_pc = (vlTOPp->top__DOT__pc_reg 
                                         + vlTOPp->top__DOT__imm_val);
        }
    }
    vlTOPp->top__DOT__alu_result = ((8U & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                     ? ((4U & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                         ? 0U : ((2U 
                                                  & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                  ? 0U
                                                  : 
                                                 ((1U 
                                                   & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                   ? 
                                                  (vlTOPp->top__DOT__alu_a 
                                                   & vlTOPp->top__DOT__alu_b)
                                                   : 
                                                  (vlTOPp->top__DOT__alu_a 
                                                   | vlTOPp->top__DOT__alu_b))))
                                     : ((4U & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                         ? ((2U & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                             ? ((1U 
                                                 & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                 ? 
                                                VL_SHIFTRS_III(32,32,5, vlTOPp->top__DOT__alu_a, 
                                                               (0x1fU 
                                                                & vlTOPp->top__DOT__alu_b))
                                                 : 
                                                (vlTOPp->top__DOT__alu_a 
                                                 >> 
                                                 (0x1fU 
                                                  & vlTOPp->top__DOT__alu_b)))
                                             : ((1U 
                                                 & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                 ? 
                                                (vlTOPp->top__DOT__alu_a 
                                                 ^ vlTOPp->top__DOT__alu_b)
                                                 : 
                                                ((vlTOPp->top__DOT__alu_a 
                                                  < vlTOPp->top__DOT__alu_b)
                                                  ? 1U
                                                  : 0U)))
                                         : ((2U & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                             ? ((1U 
                                                 & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                 ? 
                                                (VL_LTS_III(1,32,32, vlTOPp->top__DOT__alu_a, vlTOPp->top__DOT__alu_b)
                                                  ? 1U
                                                  : 0U)
                                                 : 
                                                (vlTOPp->top__DOT__alu_a 
                                                 << 
                                                 (0x1fU 
                                                  & vlTOPp->top__DOT__alu_b)))
                                             : ((1U 
                                                 & (IData)(vlTOPp->top__DOT__ctrl_alu_op))
                                                 ? 
                                                (vlTOPp->top__DOT__alu_a 
                                                 - vlTOPp->top__DOT__alu_b)
                                                 : 
                                                (vlTOPp->top__DOT__alu_a 
                                                 + vlTOPp->top__DOT__alu_b)))));
    vlTOPp->dmem_addr = vlTOPp->top__DOT__alu_result;
    vlTOPp->dmem_wstrb = (0xfU & ((0U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                   ? ((IData)(1U) << 
                                      (3U & vlTOPp->top__DOT__alu_result))
                                   : ((1U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                       ? ((IData)(3U) 
                                          << (3U & vlTOPp->top__DOT__alu_result))
                                       : ((2U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                           ? 0xfU : 0U))));
    if ((1U & (~ (IData)(vlTOPp->top__DOT__ctrl_mem_write)))) {
        vlTOPp->dmem_wstrb = 0U;
    }
    vlTOPp->top__DOT__u_load_store__DOT__unnamedblk1__DOT__wdata_masked 
        = ((0U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
            ? (0xffU & vlTOPp->top__DOT__rs2_data) : 
           ((1U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
             ? (0xffffU & vlTOPp->top__DOT__rs2_data)
             : ((2U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                 ? vlTOPp->top__DOT__rs2_data : 0U)));
    vlTOPp->dmem_wdata = ((0x1fU >= (0x18U & (vlTOPp->top__DOT__alu_result 
                                              << 3U)))
                           ? (vlTOPp->top__DOT__u_load_store__DOT__unnamedblk1__DOT__wdata_masked 
                              << (0x18U & (vlTOPp->top__DOT__alu_result 
                                           << 3U)))
                           : 0U);
    if ((1U & (~ (IData)(vlTOPp->top__DOT__ctrl_mem_write)))) {
        vlTOPp->dmem_wdata = 0U;
    }
    if (vlTOPp->top__DOT__ctrl_mem_read) {
        vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted 
            = ((0x1fU >= (0x18U & (vlTOPp->top__DOT__alu_result 
                                   << 3U))) ? (vlTOPp->dmem_rdata 
                                               >> (0x18U 
                                                   & (vlTOPp->top__DOT__alu_result 
                                                      << 3U)))
                : 0U);
        if ((0U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))) {
            vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted 
                = (0xffU & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted);
        } else {
            if ((1U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))) {
                vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted 
                    = (0xffffU & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted);
            } else {
                if ((2U != (IData)(vlTOPp->top__DOT__ctrl_mem_size))) {
                    vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted = 0U;
                }
            }
        }
        vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extended 
            = ((IData)(vlTOPp->top__DOT__ctrl_mem_extend)
                ? ((0U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                    ? ((0xffffff00U & ((- (IData)((1U 
                                                   & (vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted 
                                                      >> 7U)))) 
                                       << 8U)) | (0xffU 
                                                  & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted))
                    : ((1U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                        ? ((0xffff0000U & ((- (IData)(
                                                      (1U 
                                                       & (vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted 
                                                          >> 0xfU)))) 
                                           << 0x10U)) 
                           | (0xffffU & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted))
                        : ((2U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                            ? vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted
                            : 0U))) : ((0U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                        ? (0xffU & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted)
                                        : ((1U == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                            ? (0xffffU 
                                               & vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted)
                                            : ((2U 
                                                == (IData)(vlTOPp->top__DOT__ctrl_mem_size))
                                                ? vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted
                                                : 0U))));
        vlTOPp->top__DOT__ls_rdata = vlTOPp->top__DOT__u_load_store__DOT__unnamedblk2__DOT__extended;
    } else {
        vlTOPp->top__DOT__ls_rdata = 0U;
    }
}

void Vtop::_eval_initial(Vtop__Syms* __restrict vlSymsp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop::_eval_initial\n"); );
    Vtop* const __restrict vlTOPp VL_ATTR_UNUSED = vlSymsp->TOPp;
    // Body
    vlTOPp->__Vclklast__TOP__clk = vlTOPp->clk;
    vlTOPp->__Vclklast__TOP__resetn = vlTOPp->resetn;
}

void Vtop::final() {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop::final\n"); );
    // Variables
    Vtop__Syms* __restrict vlSymsp = this->__VlSymsp;
    Vtop* const __restrict vlTOPp VL_ATTR_UNUSED = vlSymsp->TOPp;
}

void Vtop::_eval_settle(Vtop__Syms* __restrict vlSymsp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop::_eval_settle\n"); );
    Vtop* const __restrict vlTOPp VL_ATTR_UNUSED = vlSymsp->TOPp;
    // Body
    vlTOPp->_settle__TOP__2(vlSymsp);
}

void Vtop::_ctor_var_reset() {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop::_ctor_var_reset\n"); );
    // Body
    clk = VL_RAND_RESET_I(1);
    resetn = VL_RAND_RESET_I(1);
    imem_addr = VL_RAND_RESET_I(32);
    imem_rdata = VL_RAND_RESET_I(32);
    dmem_addr = VL_RAND_RESET_I(32);
    dmem_wdata = VL_RAND_RESET_I(32);
    dmem_wstrb = VL_RAND_RESET_I(4);
    dmem_rdata = VL_RAND_RESET_I(32);
    dmem_read = VL_RAND_RESET_I(1);
    dmem_write = VL_RAND_RESET_I(1);
    top__DOT__pc_reg = VL_RAND_RESET_I(32);
    top__DOT__next_pc = VL_RAND_RESET_I(32);
    top__DOT__ctrl_alu_src_a = VL_RAND_RESET_I(2);
    top__DOT__ctrl_alu_src_b = VL_RAND_RESET_I(1);
    top__DOT__ctrl_result_src = VL_RAND_RESET_I(2);
    top__DOT__ctrl_reg_write = VL_RAND_RESET_I(1);
    top__DOT__ctrl_mem_read = VL_RAND_RESET_I(1);
    top__DOT__ctrl_mem_write = VL_RAND_RESET_I(1);
    top__DOT__ctrl_mem_size = VL_RAND_RESET_I(2);
    top__DOT__ctrl_mem_extend = VL_RAND_RESET_I(1);
    top__DOT__ctrl_branch = VL_RAND_RESET_I(1);
    top__DOT__ctrl_branch_type = VL_RAND_RESET_I(3);
    top__DOT__ctrl_jump = VL_RAND_RESET_I(1);
    top__DOT__ctrl_jump_type = VL_RAND_RESET_I(1);
    top__DOT__ctrl_alu_op = VL_RAND_RESET_I(4);
    top__DOT__ctrl_imm_type = VL_RAND_RESET_I(3);
    top__DOT__imm_val = VL_RAND_RESET_I(32);
    top__DOT__rs1_data = VL_RAND_RESET_I(32);
    top__DOT__rs2_data = VL_RAND_RESET_I(32);
    top__DOT__alu_a = VL_RAND_RESET_I(32);
    top__DOT__alu_b = VL_RAND_RESET_I(32);
    top__DOT__alu_result = VL_RAND_RESET_I(32);
    top__DOT__ls_rdata = VL_RAND_RESET_I(32);
    { int __Vi0=0; for (; __Vi0<32; ++__Vi0) {
            top__DOT__u_regfile__DOT__rf[__Vi0] = VL_RAND_RESET_I(32);
    }}
    top__DOT__u_load_store__DOT__unnamedblk1__DOT__wdata_masked = VL_RAND_RESET_I(32);
    top__DOT__u_load_store__DOT__unnamedblk2__DOT__extracted = VL_RAND_RESET_I(32);
    top__DOT__u_load_store__DOT__unnamedblk2__DOT__extended = VL_RAND_RESET_I(32);
}
