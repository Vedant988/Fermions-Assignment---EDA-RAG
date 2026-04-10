

---
<!-- chunk_id=picorv32_COPYING_0 | picorv32_COPYING -->

ISC License

Copyright (C) 2015 - 2021  Claire Xenia Wolf <claire@yosyshq.com>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

---
<!-- chunk_id=picorv32_Makefile_0 | Give the user some easy overrides for local configuration quirks. -->

# Give the user some easy overrides for local configuration quirks.

---
<!-- chunk_id=picorv32_Makefile_1 | If you change one of these and it breaks, then you get to keep both pieces. -->

# If you change one of these and it breaks, then you get to keep both pieces.
SHELL = bash
PYTHON = python3
VERILATOR = verilator
ICARUS_SUFFIX =
IVERILOG = iverilog$(ICARUS_SUFFIX)
VVP = vvp$(ICARUS_SUFFIX)

TEST_OBJS = $(addsuffix .o,$(basename $(wildcard tests/*.S)))
FIRMWARE_OBJS = firmware/start.o firmware/irq.o firmware/print.o firmware/hello.o firmware/sieve.o firmware/multest.o firmware/stats.o
GCC_WARNS  = -Werror -Wall -Wextra -Wshadow -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wwrite-strings
GCC_WARNS += -Wredundant-decls -Wstrict-prototypes -Wmissing-prototypes -pedantic # -Wconversion
TOOLCHAIN_PREFIX = $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)i/bin/riscv32-unknown-elf-
COMPRESSED_ISA = C

---
<!-- chunk_id=picorv32_Makefile_2 | Add things like "export http_proxy=... https_proxy=..." here -->

# Add things like "export http_proxy=... https_proxy=..." here
GIT_ENV = true

test: testbench.vvp firmware/firmware.hex
	$(VVP) -N $<

test_vcd: testbench.vvp firmware/firmware.hex
	$(VVP) -N $< +vcd +trace +noerror

test_rvf: testbench_rvf.vvp firmware/firmware.hex
	$(VVP) -N $< +vcd +trace +noerror

test_wb: testbench_wb.vvp firmware/firmware.hex
	$(VVP) -N $<

test_wb_vcd: testbench_wb.vvp firmware/firmware.hex
	$(VVP) -N $< +vcd +trace +noerror

test_ez: testbench_ez.vvp
	$(VVP) -N $<

test_ez_vcd: testbench_ez.vvp
	$(VVP) -N $< +vcd

test_sp: testbench_sp.vvp firmware/firmware.hex
	$(VVP) -N $<

test_axi: testbench.vvp firmware/firmware.hex
	$(VVP) -N $< +axi_test

test_synth: testbench_synth.vvp firmware/firmware.hex
	$(VVP) -N $<

test_verilator: testbench_verilator firmware/firmware.hex
	./testbench_verilator

testbench.vvp: testbench.v picorv32.v
	$(IVERILOG) -o $@ $(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) $^
	chmod -x $@

testbench_rvf.vvp: testbench.v picorv32.v rvfimon.v
	$(IVERILOG) -o $@ -D RISCV_FORMAL $(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) $^
	chmod -x $@

testbench_wb.vvp: testbench_wb.v picorv32.v
	$(IVERILOG) -o $@ $(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) $^
	chmod -x $@

testbench_ez.vvp: testbench_ez.v picorv32.v
	$(IVERILOG) -o $@ $(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) $^
	chmod -x $@

testbench_sp.vvp: testbench.v picorv32.v
	$(IVERILOG) -o $@ $(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) -DSP_TEST $^
	chmod -x $@

testbench_synth.vvp: testbench.v synth.v
	$(IVERILOG) -o $@ -DSYNTH_TEST $^
	chmod -x $@

testbench_verilator: testbench.v picorv32.v testbench.cc
	$(VERILATOR) --cc --exe -Wno-lint -trace --top-module picorv32_wrapper testbench.v picorv32.v testbench.cc \
			$(subst C,-DCOMPRESSED_ISA,$(COMPRESSED_ISA)) --Mdir testbench_verilator_dir
	$(MAKE) -C testbench_verilator_dir -f Vpicorv32_wrapper.mk
	cp testbench_verilator_dir/Vpicorv32_wrapper testbench_verilator

check: check-yices

check-%: check.smt2
	yosys-smtbmc -s $(subst check-,,$@) -t 30 --dump-vcd check.vcd check.smt2
	yosys-smtbmc -s $(subst check-,,$@) -t 25 --dump-vcd check.vcd -i check.smt2

check.smt2: picorv32.v
	yosys -v2 -p 'read_verilog -formal picorv32.v' \
	          -p 'prep -top picorv32 -nordff' \
		  -p 'assertpmux -noinit; opt -fast; dffunmap' \
		  -p 'write_smt2 -wires check.smt2'

synth.v: picorv32.v scripts/yosys/synth_sim.ys
	yosys -qv3 -l synth.log scripts/yosys/synth_sim.ys

firmware/firmware.hex: firmware/firmware.bin firmware/makehex.py
	$(PYTHON) firmware/makehex.py $< 32768 > $@

firmware/firmware.bin: firmware/firmware.elf
	$(TOOLCHAIN_PREFIX)objcopy -O binary $< $@
	chmod -x $@

firmware/firmware.elf: $(FIRMWARE_OBJS) $(TEST_OBJS) firmware/sections.lds
	$(TOOLCHAIN_PREFIX)gcc -Os -mabi=ilp32 -march=rv32im$(subst C,c,$(COMPRESSED_ISA)) -ffreestanding -nostdlib -o $@ \
		-Wl,--build-id=none,-Bstatic,-T,firmware/sections.lds,-Map,firmware/firmware.map,--strip-debug \
		$(FIRMWARE_OBJS) $(TEST_OBJS) -lgcc
	chmod -x $@

firmware/start.o: firmware/start.S
	$(TOOLCHAIN_PREFIX)gcc -c -mabi=ilp32 -march=rv32im$(subst C,c,$(COMPRESSED_ISA)) -o $@ $<

firmware/%.o: firmware/%.c
	$(TOOLCHAIN_PREFIX)gcc -c -mabi=ilp32 -march=rv32i$(subst C,c,$(COMPRESSED_ISA)) -Os --std=c99 $(GCC_WARNS) -ffreestanding -nostdlib -o $@ $<

tests/%.o: tests/%.S tests/riscv_test.h tests/test_macros.h
	$(TOOLCHAIN_PREFIX)gcc -c -mabi=ilp32 -march=rv32im -o $@ -DTEST_FUNC_NAME=$(notdir $(basename $<)) \
		-DTEST_FUNC_TXT='"$(notdir $(basename $<))"' -DTEST_FUNC_RET=$(notdir $(basename $<))_ret $<

download-tools:
	sudo bash -c 'set -ex; mkdir -p /var/cache/distfiles; $(GIT_ENV); \
	$(foreach REPO,riscv-gnu-toolchain riscv-binutils-gdb riscv-gcc riscv-glibc riscv-newlib, \
		if ! test -d /var/cache/distfiles/$(REPO).git; then rm -rf /var/cache/distfiles/$(REPO).git.part; \
			git clone --bare https://github.com/riscv/$(REPO) /var/cache/distfiles/$(REPO).git.part; \
			mv /var/cache/distfiles/$(REPO).git.part /var/cache/distfiles/$(REPO).git; else \
			(cd /var/cache/distfiles/$(REPO).git; git fetch https://github.com/riscv/$(REPO)); fi;)'

define build_tools_template
build-$(1)-tools:
	@read -p "This will remove all existing data from $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)$(subst riscv32,,$(1)). Type YES to continue: " reply && [[ "$$$$reply" == [Yy][Ee][Ss] || "$$$$reply" == [Yy] ]]
	sudo bash -c "set -ex; rm -rf $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)$(subst riscv32,,$(1)); mkdir -p $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)$(subst riscv32,,$(1)); chown $$$${USER}: $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)$(subst riscv32,,$(1))"
	+$(MAKE) build-$(1)-tools-bh

build-$(1)-tools-bh:
	+set -ex; $(GIT_ENV); \
	if [ -d /var/cache/distfiles/riscv-gnu-toolchain.git ]; then reference_riscv_gnu_toolchain="--reference /var/cache/distfiles/riscv-gnu-toolchain.git"; else reference_riscv_gnu_toolchain=""; fi; \
	if [ -d /var/cache/distfiles/riscv-binutils-gdb.git ]; then reference_riscv_binutils_gdb="--reference /var/cache/distfiles/riscv-binutils-gdb.git"; else reference_riscv_binutils_gdb=""; fi; \
	if [ -d /var/cache/distfiles/riscv-gcc.git ]; then reference_riscv_gcc="--reference /var/cache/distfiles/riscv-gcc.git"; else reference_riscv_gcc=""; fi; \
	if [ -d /var/cache/distfiles/riscv-glibc.git ]; then reference_riscv_glibc="--reference /var/cache/distfiles/riscv-glibc.git"; else reference_riscv_glibc=""; fi; \
	if [ -d /var/cache/distfiles/riscv-newlib.git ]; then reference_riscv_newlib="--reference /var/cache/distfiles/riscv-newlib.git"; else reference_riscv_newlib=""; fi; \
	rm -rf riscv-gnu-toolchain-$(1); git clone $$$$reference_riscv_gnu_toolchain https://github.com/riscv/riscv-gnu-toolchain riscv-gnu-toolchain-$(1); \
	cd riscv-gnu-toolchain-$(1); git checkout $(RISCV_GNU_TOOLCHAIN_GIT_REVISION); \
	git submodule update --init $$$$reference_riscv_binutils_gdb riscv-binutils; \
	git submodule update --init $$$$reference_riscv_binutils_gdb riscv-gdb; \
	git submodule update --init $$$$reference_riscv_gcc riscv-gcc; \
	git submodule update --init $$$$reference_riscv_glibc riscv-glibc; \
	git submodule update --init $$$$reference_riscv_newlib riscv-newlib; \
	mkdir build; cd build; ../configure --with-arch=$(2) --prefix=$(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)$(subst riscv32,,$(1)); make

.PHONY: build-$(1)-tools
endef

$(eval $(call build_tools_template,riscv32i,rv32i))
$(eval $(call build_tools_template,riscv32ic,rv32ic))
$(eval $(call build_tools_template,riscv32im,rv32im))
$(eval $(call build_tools_template,riscv32imc,rv32imc))

build-tools:
	@echo "This will remove all existing data from $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)i, $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)ic, $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)im, and $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX)imc."
	@read -p "Type YES to continue: " reply && [[ "$$reply" == [Yy][Ee][Ss] || "$$reply" == [Yy] ]]
	sudo bash -c "set -ex; rm -rf $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX){i,ic,im,imc}; mkdir -p $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX){i,ic,im,imc}; chown $${USER}: $(RISCV_GNU_TOOLCHAIN_INSTALL_PREFIX){i,ic,im,imc}"
	+$(MAKE) build-riscv32i-tools-bh
	+$(MAKE) build-riscv32ic-tools-bh
	+$(MAKE) build-riscv32im-tools-bh
	+$(MAKE) build-riscv32imc-tools-bh

toc:
	gawk '/^-+$$/ { y=tolower(x); gsub("[^a-z0-9]+", "-", y); gsub("-$$", "", y); printf("- [%s](#%s)\n", x, y); } { x=$$0; }' README.md

clean:
	rm -rf riscv-gnu-toolchain-riscv32i riscv-gnu-toolchain-riscv32ic \
		riscv-gnu-toolchain-riscv32im riscv-gnu-toolchain-riscv32imc
	rm -vrf $(FIRMWARE_OBJS) $(TEST_OBJS) check.smt2 check.vcd synth.v synth.log \
		firmware/firmware.elf firmware/firmware.bin firmware/firmware.hex firmware/firmware.map \
		testbench.vvp testbench_sp.vvp testbench_synth.vvp testbench_ez.vvp \
		testbench_rvf.vvp testbench_wb.vvp testbench.vcd testbench.trace \
		testbench_verilator testbench_verilator_dir

.PHONY: test test_vcd test_sp test_axi test_wb test_wb_vcd test_ez test_ez_vcd test_synth download-tools build-tools toc clean

---
<!-- chunk_id=picorv32_README_0 | Table of Contents -->

#### Table of Contents

- [Features and Typical Applications](#features-and-typical-applications)
- [Files in this Repository](#files-in-this-repository)
- [Verilog Module Parameters](#verilog-module-parameters)
- [Cycles per Instruction Performance](#cycles-per-instruction-performance)
- [PicoRV32 Native Memory Interface](#picorv32-native-memory-interface)
- [Pico Co-Processor Interface (PCPI)](#pico-co-processor-interface-pcpi)
- [Custom Instructions for IRQ Handling](#custom-instructions-for-irq-handling)
- [Building a pure RV32I Toolchain](#building-a-pure-rv32i-toolchain)
- [Linking binaries with newlib for PicoRV32](#linking-binaries-with-newlib-for-picorv32)
- [Evaluation: Timing and Utilization on Xilinx 7-Series FPGAs](#evaluation-timing-and-utilization-on-xilinx-7-series-fpgas)


Features and Typical Applications
---------------------------------

- Small (750-2000 LUTs in 7-Series Xilinx Architecture)
- High f<sub>max</sub> (250-450 MHz on 7-Series Xilinx FPGAs)
- Selectable native memory interface or AXI4-Lite master
- Optional IRQ support (using a simple custom ISA)
- Optional Co-Processor Interface

This CPU is meant to be used as auxiliary processor in FPGA designs and ASICs. Due
to its high f<sub>max</sub> it can be integrated in most existing designs without crossing
clock domains. When operated on a lower frequency, it will have a lot of timing
slack and thus can be added to a design without compromising timing closure.

For even smaller size it is possible disable support for registers `x16`..`x31` as
well as `RDCYCLE[H]`, `RDTIME[H]`, and `RDINSTRET[H]` instructions, turning the
processor into an RV32E core.

Furthermore it is possible to choose between a dual-port and a single-port
register file implementation. The former provides better performance while
the latter results in a smaller core.

*Note: In architectures that implement the register file in dedicated memory
resources, such as many FPGAs, disabling the 16 upper registers and/or
disabling the dual-port register file may not further reduce the core size.*

The core exists in three variations: `picorv32`, `picorv32_axi` and `picorv32_wb`.
The first provides a simple native memory interface, that is easy to use in simple
environments. `picorv32_axi` provides an AXI-4 Lite Master interface that can
easily be integrated with existing systems that are already using the AXI
standard. `picorv32_wb` provides a Wishbone master interface.

A separate core `picorv32_axi_adapter` is provided to bridge between the native
memory interface and AXI4. This core can be used to create custom cores that
include one or more PicoRV32 cores together with local RAM, ROM, and
memory-mapped peripherals, communicating with each other using the native
interface, and communicating with the outside world via AXI4.

The optional IRQ feature can be used to react to events from the outside, implement
fault handlers, or catch instructions from a larger ISA and emulate them in
software.

The optional Pico Co-Processor Interface (PCPI) can be used to implement
non-branching instructions in an external coprocessor. Implementations
of PCPI cores that implement the M Standard Extension instructions
`MUL[H[SU|U]]` and `DIV[U]/REM[U]` are included in this package.


Files in this Repository
------------------------

---
<!-- chunk_id=picorv32_README_1 | README.md -->

#### README.md

You are reading it right now.

---
<!-- chunk_id=picorv32_README_2 | picorv32.v -->

#### picorv32.v

This Verilog file contains the following Verilog modules:

| Module                   | Description                                                           |
| ------------------------ | --------------------------------------------------------------------- |
| `picorv32`               | The PicoRV32 CPU                                                      |
| `picorv32_axi`           | The version of the CPU with AXI4-Lite interface                       |
| `picorv32_axi_adapter`   | Adapter from PicoRV32 Memory Interface to AXI4-Lite                   |
| `picorv32_wb`            | The version of the CPU with Wishbone Master interface                 |
| `picorv32_pcpi_mul`      | A PCPI core that implements the `MUL[H[SU\|U]]` instructions          |
| `picorv32_pcpi_fast_mul` | A version of `picorv32_pcpi_fast_mul` using a single cycle multiplier |
| `picorv32_pcpi_div`      | A PCPI core that implements the `DIV[U]/REM[U]` instructions          |

Simply copy this file into your project.

---
<!-- chunk_id=picorv32_README_3 | Makefile and testbenches -->

#### Makefile and testbenches

A basic test environment. Run `make test` to run the standard test bench (`testbench.v`)
in the standard configurations. There are other test benches and configurations. See
the `test_*` make target in the Makefile for details.

Run `make test_ez` to run `testbench_ez.v`, a very simple test bench that does
not require an external firmware .hex file. This can be useful in environments
where the RISC-V compiler toolchain is not available.

*Note: The test bench is using Icarus Verilog. However, Icarus Verilog 0.9.7
(the latest release at the time of writing) has a few bugs that prevent the
test bench from running. Upgrade to the latest github master of Icarus Verilog
to run the test bench.*

---
<!-- chunk_id=picorv32_README_4 | firmware/ -->

#### firmware/

A simple test firmware. This runs the basic tests from `tests/`, some C code, tests IRQ
handling and the multiply PCPI core.

All the code in `firmware/` is in the public domain. Simply copy whatever you can use.

---
<!-- chunk_id=picorv32_README_5 | tests/ -->

#### tests/

Simple instruction-level tests from [riscv-tests](https://github.com/riscv/riscv-tests).

---
<!-- chunk_id=picorv32_README_6 | dhrystone/ -->

#### dhrystone/

Another simple test firmware that runs the Dhrystone benchmark.

---
<!-- chunk_id=picorv32_README_7 | picosoc/ -->

#### picosoc/

A simple example SoC using PicoRV32 that can execute code directly from a
memory mapped SPI flash.

---
<!-- chunk_id=picorv32_README_8 | scripts/ -->

#### scripts/

Various scripts and examples for different (synthesis) tools and hardware architectures.


Verilog Module Parameters
-------------------------

The following Verilog module parameters can be used to configure the PicoRV32
core.

---
<!-- chunk_id=picorv32_README_9 | ENABLE_COUNTERS (default = 1) -->

#### ENABLE_COUNTERS (default = 1)

This parameter enables support for the `RDCYCLE[H]`, `RDTIME[H]`, and
`RDINSTRET[H]` instructions. This instructions will cause a hardware
trap (like any other unsupported instruction) if `ENABLE_COUNTERS` is set to zero.

*Note: Strictly speaking the `RDCYCLE[H]`, `RDTIME[H]`, and `RDINSTRET[H]`
instructions are not optional for an RV32I core. But chances are they are not
going to be missed after the application code has been debugged and profiled.
This instructions are optional for an RV32E core.*

---
<!-- chunk_id=picorv32_README_10 | ENABLE_COUNTERS64 (default = 1) -->

#### ENABLE_COUNTERS64 (default = 1)

This parameter enables support for the `RDCYCLEH`, `RDTIMEH`, and `RDINSTRETH`
instructions. If this parameter is set to 0, and `ENABLE_COUNTERS` is set to 1,
then only the `RDCYCLE`, `RDTIME`, and `RDINSTRET` instructions are available.

---
<!-- chunk_id=picorv32_README_11 | ENABLE_REGS_16_31 (default = 1) -->

#### ENABLE_REGS_16_31 (default = 1)

This parameter enables support for registers the `x16`..`x31`. The RV32E ISA
excludes this registers. However, the RV32E ISA spec requires a hardware trap
for when code tries to access this registers. This is not implemented in PicoRV32.

---
<!-- chunk_id=picorv32_README_12 | ENABLE_REGS_DUALPORT (default = 1) -->

#### ENABLE_REGS_DUALPORT (default = 1)

The register file can be implemented with two or one read ports. A dual ported
register file improves performance a bit, but can also increase the size of
the core.

---
<!-- chunk_id=picorv32_README_13 | LATCHED_MEM_RDATA (default = 0) -->

#### LATCHED_MEM_RDATA (default = 0)

Set this to 1 if the `mem_rdata` is kept stable by the external circuit after a
transaction. In the default configuration the PicoRV32 core only expects the
`mem_rdata` input to be valid in the cycle with `mem_valid && mem_ready` and
latches the value internally.

This parameter is only available for the `picorv32` core. In the
`picorv32_axi` and `picorv32_wb` core this is implicitly set to 0.

---
<!-- chunk_id=picorv32_README_14 | TWO_STAGE_SHIFT (default = 1) -->

#### TWO_STAGE_SHIFT (default = 1)

By default shift operations are performed in two stages: first shifts in units
of 4 bits and then shifts in units of 1 bit. This speeds up shift operations,
but adds additional hardware. Set this parameter to 0 to disable the two-stage
shift to further reduce the size of the core.

---
<!-- chunk_id=picorv32_README_15 | BARREL_SHIFTER (default = 0) -->

#### BARREL_SHIFTER (default = 0)

By default shift operations are performed by successively shifting by a
small amount (see `TWO_STAGE_SHIFT` above). With this option set, a barrel
shifter is used instead.

---
<!-- chunk_id=picorv32_README_16 | TWO_CYCLE_COMPARE (default = 0) -->

#### TWO_CYCLE_COMPARE (default = 0)

This relaxes the longest data path a bit by adding an additional FF stage
at the cost of adding an additional clock cycle delay to the conditional
branch instructions.

*Note: Enabling this parameter will be most effective when retiming (aka
"register balancing") is enabled in the synthesis flow.*

---
<!-- chunk_id=picorv32_README_17 | TWO_CYCLE_ALU (default = 0) -->

#### TWO_CYCLE_ALU (default = 0)

This adds an additional FF stage in the ALU data path, improving timing
at the cost of an additional clock cycle for all instructions that use
the ALU.

*Note: Enabling this parameter will be most effective when retiming (aka
"register balancing") is enabled in the synthesis flow.*

---
<!-- chunk_id=picorv32_README_18 | COMPRESSED_ISA (default = 0) -->

#### COMPRESSED_ISA (default = 0)

This enables support for the RISC-V Compressed Instruction Set.

---
<!-- chunk_id=picorv32_README_19 | CATCH_MISALIGN (default = 1) -->

#### CATCH_MISALIGN (default = 1)

Set this to 0 to disable the circuitry for catching misaligned memory
accesses.

---
<!-- chunk_id=picorv32_README_20 | CATCH_ILLINSN (default = 1) -->

#### CATCH_ILLINSN (default = 1)

Set this to 0 to disable the circuitry for catching illegal instructions.

The core will still trap on `EBREAK` instructions with this option
set to 0. With IRQs enabled, an `EBREAK` normally triggers an IRQ 1. With
this option set to 0, an `EBREAK` will trap the processor without
triggering an interrupt.

---
<!-- chunk_id=picorv32_README_21 | ENABLE_PCPI (default = 0) -->

#### ENABLE_PCPI (default = 0)

Set this to 1 to enable the _external_ Pico Co-Processor Interface (PCPI).
The external interface is not required for the internal PCPI cores, such as
`picorv32_pcpi_mul`.

---
<!-- chunk_id=picorv32_README_22 | ENABLE_MUL (default = 0) -->

#### ENABLE_MUL (default = 0)

This parameter internally enables PCPI and instantiates the `picorv32_pcpi_mul`
core that implements the `MUL[H[SU|U]]` instructions. The external PCPI
interface only becomes functional when ENABLE_PCPI is set as well.

---
<!-- chunk_id=picorv32_README_23 | ENABLE_FAST_MUL (default = 0) -->

#### ENABLE_FAST_MUL (default = 0)

This parameter internally enables PCPI and instantiates the `picorv32_pcpi_fast_mul`
core that implements the `MUL[H[SU|U]]` instructions. The external PCPI
interface only becomes functional when ENABLE_PCPI is set as well.

If both ENABLE_MUL and ENABLE_FAST_MUL are set then the ENABLE_MUL setting
will be ignored and the fast multiplier core will be instantiated.

---
<!-- chunk_id=picorv32_README_24 | ENABLE_DIV (default = 0) -->

#### ENABLE_DIV (default = 0)

This parameter internally enables PCPI and instantiates the `picorv32_pcpi_div`
core that implements the `DIV[U]/REM[U]` instructions. The external PCPI
interface only becomes functional when ENABLE_PCPI is set as well.

---
<!-- chunk_id=picorv32_README_25 | ENABLE_IRQ (default = 0) -->

#### ENABLE_IRQ (default = 0)

Set this to 1 to enable IRQs. (see "Custom Instructions for IRQ Handling" below
for a discussion of IRQs)

---
<!-- chunk_id=picorv32_README_26 | ENABLE_IRQ_QREGS (default = 1) -->

#### ENABLE_IRQ_QREGS (default = 1)

Set this to 0 to disable support for the `getq` and `setq` instructions. Without
the q-registers, the irq return address will be stored in x3 (gp) and the IRQ
bitmask in x4 (tp), the global pointer and thread pointer registers according
to the RISC-V ABI.  Code generated from ordinary C code will not interact with
those registers.

Support for q-registers is always disabled when ENABLE_IRQ is set to 0.

---
<!-- chunk_id=picorv32_README_27 | ENABLE_IRQ_TIMER (default = 1) -->

#### ENABLE_IRQ_TIMER (default = 1)

Set this to 0 to disable support for the `timer` instruction.

Support for the timer is always disabled when ENABLE_IRQ is set to 0.

---
<!-- chunk_id=picorv32_README_28 | ENABLE_TRACE (default = 0) -->

#### ENABLE_TRACE (default = 0)

Produce an execution trace using the `trace_valid` and `trace_data` output ports.
For a demonstration of this feature run `make test_vcd` to create a trace file
and then run `python3 showtrace.py testbench.trace firmware/firmware.elf` to decode
it.

---
<!-- chunk_id=picorv32_README_29 | REGS_INIT_ZERO (default = 0) -->

#### REGS_INIT_ZERO (default = 0)

Set this to 1 to initialize all registers to zero (using a Verilog `initial` block).
This can be useful for simulation or formal verification.

---
<!-- chunk_id=picorv32_README_30 | MASKED_IRQ (default = 32'h 0000_0000) -->

#### MASKED_IRQ (default = 32'h 0000_0000)

A 1 bit in this bitmask corresponds to a permanently disabled IRQ.

---
<!-- chunk_id=picorv32_README_31 | LATCHED_IRQ (default = 32'h ffff_ffff) -->

#### LATCHED_IRQ (default = 32'h ffff_ffff)

A 1 bit in this bitmask indicates that the corresponding IRQ is "latched", i.e.
when the IRQ line is high for only one cycle, the interrupt will be marked as
pending and stay pending until the interrupt handler is called (aka "pulse
interrupts" or "edge-triggered interrupts").

Set a bit in this bitmask to 0 to convert an interrupt line to operate
as "level sensitive" interrupt.

---
<!-- chunk_id=picorv32_README_32 | PROGADDR_RESET (default = 32'h 0000_0000) -->

#### PROGADDR_RESET (default = 32'h 0000_0000)

The start address of the program.

---
<!-- chunk_id=picorv32_README_33 | PROGADDR_IRQ (default = 32'h 0000_0010) -->

#### PROGADDR_IRQ (default = 32'h 0000_0010)

The start address of the interrupt handler.

---
<!-- chunk_id=picorv32_README_34 | STACKADDR (default = 32'h ffff_ffff) -->

#### STACKADDR (default = 32'h ffff_ffff)

When this parameter has a value different from 0xffffffff, then register `x2` (the
stack pointer) is initialized to this value on reset. (All other registers remain
uninitialized.) Note that the RISC-V calling convention requires the stack pointer
to be aligned on 16 bytes boundaries (4 bytes for the RV32I soft float calling
convention).


Cycles per Instruction Performance
----------------------------------

*A short reminder: This core is optimized for size and f<sub>max</sub>, not performance.*

Unless stated otherwise, the following numbers apply to a PicoRV32 with
ENABLE_REGS_DUALPORT active and connected to a memory that can accommodate
requests within one clock cycle.

The average Cycles per Instruction (CPI) is approximately 4, depending on the mix of
instructions in the code. The CPI numbers for the individual instructions can
be found in the table below. The column "CPI (SP)" contains the CPI numbers for
a core built without ENABLE_REGS_DUALPORT.

| Instruction          |  CPI | CPI (SP) |
| ---------------------| ----:| --------:|
| direct jump (jal)    |    3 |        3 |
| ALU reg + immediate  |    3 |        3 |
| ALU reg + reg        |    3 |        4 |
| branch (not taken)   |    3 |        4 |
| memory load          |    5 |        5 |
| memory store         |    5 |        6 |
| branch (taken)       |    5 |        6 |
| indirect jump (jalr) |    6 |        6 |
| shift operations     | 4-14 |     4-15 |

When `ENABLE_MUL` is activated, then a `MUL` instruction will execute
in 40 cycles and a `MULH[SU|U]` instruction will execute in 72 cycles.

When `ENABLE_DIV` is activated, then a `DIV[U]/REM[U]` instruction will
execute in 40 cycles.

When `BARREL_SHIFTER` is activated, a shift operation takes as long as
any other ALU operation.

The following dhrystone benchmark results are for a core with enabled
`ENABLE_FAST_MUL`, `ENABLE_DIV`, and `BARREL_SHIFTER` options.

Dhrystone benchmark results: 0.516 DMIPS/MHz (908 Dhrystones/Second/MHz)

For the Dhrystone benchmark the average CPI is 4.100.

Without using the look-ahead memory interface (usually required for max
clock speed), this results drop to 0.305 DMIPS/MHz and 5.232 CPI.


PicoRV32 Native Memory Interface
--------------------------------

The native memory interface of PicoRV32 is a simple valid-ready interface
that can run one memory transfer at a time:

    output        mem_valid
    output        mem_instr
    input         mem_ready

    output [31:0] mem_addr
    output [31:0] mem_wdata
    output [ 3:0] mem_wstrb
    input  [31:0] mem_rdata

The core initiates a memory transfer by asserting `mem_valid`. The valid
signal stays high until the peer asserts `mem_ready`. All core outputs
are stable over the `mem_valid` period. If the memory transfer is an
instruction fetch, the core asserts `mem_instr`.

---
<!-- chunk_id=picorv32_README_35 | Read Transfer -->

#### Read Transfer

In a read transfer `mem_wstrb` has the value 0 and `mem_wdata` is unused.

The memory reads the address `mem_addr` and makes the read value available on
`mem_rdata` in the cycle `mem_ready` is high.

There is no need for an external wait cycle. The memory read can be implemented
asynchronously with `mem_ready` going high in the same cycle as `mem_valid`, or
`mem_ready` being tied to constant 1.

---
<!-- chunk_id=picorv32_README_36 | Write Transfer -->

#### Write Transfer

In a write transfer `mem_wstrb` is not 0 and `mem_rdata` is unused. The memory
write the data at `mem_wdata` to the address `mem_addr` and acknowledges the
transfer by asserting `mem_ready`.

The 4 bits of `mem_wstrb` are write enables for the four bytes in the addressed
word. Only the 8 values `0000`, `1111`, `1100`, `0011`, `1000`, `0100`, `0010`,
and `0001` are possible, i.e. no write, write 32 bits, write upper 16 bits,
write lower 16, or write a single byte respectively.

There is no need for an external wait cycle. The memory can acknowledge the
write immediately  with `mem_ready` going high in the same cycle as
`mem_valid`, or `mem_ready` being tied to constant 1.

---
<!-- chunk_id=picorv32_README_37 | Look-Ahead Interface -->

#### Look-Ahead Interface

The PicoRV32 core also provides a "Look-Ahead Memory Interface" that provides
all information about the next memory transfer one clock cycle earlier than the
normal interface.

    output        mem_la_read
    output        mem_la_write
    output [31:0] mem_la_addr
    output [31:0] mem_la_wdata
    output [ 3:0] mem_la_wstrb

In the clock cycle before `mem_valid` goes high, this interface will output a
pulse on `mem_la_read` or `mem_la_write` to indicate the start of a read or
write transaction in the next clock cycle.

*Note: The signals `mem_la_read`, `mem_la_write`, and `mem_la_addr` are driven
by combinatorial circuits within the PicoRV32 core. It might be harder to
achieve timing closure with the look-ahead interface than with the normal
memory interface described above.*


Pico Co-Processor Interface (PCPI)
----------------------------------

The Pico Co-Processor Interface (PCPI) can be used to implement non-branching
instructions in external cores:

    output        pcpi_valid
    output [31:0] pcpi_insn
    output [31:0] pcpi_rs1
    output [31:0] pcpi_rs2
    input         pcpi_wr
    input  [31:0] pcpi_rd
    input         pcpi_wait
    input         pcpi_ready

When an unsupported instruction is encountered and the PCPI feature is
activated (see ENABLE_PCPI above), then `pcpi_valid` is asserted, the
instruction word itself is output on `pcpi_insn`, the `rs1` and `rs2`
fields are decoded and the values in those registers are output
on `pcpi_rs1` and `pcpi_rs2`.

An external PCPI core can then decode the instruction, execute it, and assert
`pcpi_ready` when execution of the instruction is finished. Optionally a
result value can be written to `pcpi_rd` and `pcpi_wr` asserted. The
PicoRV32 core will then decode the `rd` field of the instruction and
write the value from `pcpi_rd` to the respective register.

When no external PCPI core acknowledges the instruction within 16 clock
cycles, then an illegal instruction exception is raised and the respective
interrupt handler is called. A PCPI core that needs more than a couple of
cycles to execute an instruction, should assert `pcpi_wait` as soon as
the instruction has been decoded successfully and keep it asserted until
it asserts `pcpi_ready`. This will prevent the PicoRV32 core from raising
an illegal instruction exception.


Custom Instructions for IRQ Handling
------------------------------------

*Note: The IRQ handling features in PicoRV32 do not follow the RISC-V
Privileged ISA specification. Instead a small set of very simple custom
instructions is used to implement IRQ handling with minimal hardware
overhead.*

The following custom instructions are only supported when IRQs are enabled
via the `ENABLE_IRQ` parameter (see above).

The PicoRV32 core has a built-in interrupt controller with 32 interrupt inputs. An
interrupt can be triggered by asserting the corresponding bit in the `irq`
input of the core.

When the interrupt handler is started, the `eoi` End Of Interrupt (EOI) signals
for the handled interrupts go high. The `eoi` signals go low again when the
interrupt handler returns.

The IRQs 0-2 can be triggered internally by the following built-in interrupt sources:

| IRQ | Interrupt Source                    |
| ---:| ------------------------------------|
|   0 | Timer Interrupt                     |
|   1 | EBREAK/ECALL or Illegal Instruction |
|   2 | BUS Error (Unalign Memory Access)   |

This interrupts can also be triggered by external sources, such as co-processors
connected via PCPI.

The core has 4 additional 32-bit registers `q0 .. q3` that are used for IRQ
handling. When the IRQ handler is called, the register `q0` contains the return
address and `q1` contains a bitmask of all IRQs to be handled. This means one
call to the interrupt handler needs to service more than one IRQ when more than
one bit is set in `q1`.

When support for compressed instructions is enabled, then the LSB of q0 is set
when the interrupted instruction is a compressed instruction. This can be used if
the IRQ handler wants to decode the interrupted instruction.

Registers `q2` and `q3` are uninitialized and can be used as temporary storage
when saving/restoring register values in the IRQ handler.

All of the following instructions are encoded under the `custom0` opcode. The f3
and rs2 fields are ignored in all this instructions.

See [firmware/custom_ops.S](firmware/custom_ops.S) for GNU assembler macros that
implement mnemonics for this instructions.

See [firmware/start.S](firmware/start.S) for an example implementation of an
interrupt handler assembler wrapper, and [firmware/irq.c](firmware/irq.c) for
the actual interrupt handler.

---
<!-- chunk_id=picorv32_README_38 | getq rd, qs -->

#### getq rd, qs

This instruction copies the value from a q-register to a general-purpose
register.

    0000000 ----- 000XX --- XXXXX 0001011
    f7      rs2   qs    f3  rd    opcode

Example:

    getq x5, q2

---
<!-- chunk_id=picorv32_README_39 | setq qd, rs -->

#### setq qd, rs

This instruction copies the value from a general-purpose register to a
q-register.

    0000001 ----- XXXXX --- 000XX 0001011
    f7      rs2   rs    f3  qd    opcode

Example:

    setq q2, x5

---
<!-- chunk_id=picorv32_README_40 | retirq -->

#### retirq

Return from interrupt. This instruction copies the value from `q0`
to the program counter and re-enables interrupts.

    0000010 ----- 00000 --- 00000 0001011
    f7      rs2   rs    f3  rd    opcode

Example:

    retirq

---
<!-- chunk_id=picorv32_README_41 | maskirq -->

#### maskirq

The "IRQ Mask" register contains a bitmask of masked (disabled) interrupts.
This instruction writes a new value to the irq mask register and reads the old
value.

    0000011 ----- XXXXX --- XXXXX 0001011
    f7      rs2   rs    f3  rd    opcode

Example:

    maskirq x1, x2

The processor starts with all interrupts disabled.

An illegal instruction or bus error while the illegal instruction or bus error
interrupt is disabled will cause the processor to halt.

---
<!-- chunk_id=picorv32_README_42 | waitirq -->

#### waitirq

Pause execution until an interrupt becomes pending. The bitmask of pending IRQs
is written to `rd`.

    0000100 ----- 00000 --- XXXXX 0001011
    f7      rs2   rs    f3  rd    opcode

Example:

    waitirq x1

---
<!-- chunk_id=picorv32_README_43 | timer -->

#### timer

Reset the timer counter to a new value. The counter counts down clock cycles and
triggers the timer interrupt when transitioning from 1 to 0. Setting the
counter to zero disables the timer. The old value of the counter is written to
`rd`.

    0000101 ----- XXXXX --- XXXXX 0001011
    f7      rs2   rs    f3  rd    opcode

Example:

    timer x1, x2


Building a pure RV32I Toolchain
-------------------------------

TL;DR: Run the following commands to build the complete toolchain:

    make download-tools
    make -j$(nproc) build-tools

The default settings in the [riscv-tools](https://github.com/riscv/riscv-tools) build
scripts will build a compiler, assembler and linker that can target any RISC-V ISA,
but the libraries are built for RV32G and RV64G targets. Follow the instructions
below to build a complete toolchain (including libraries) that target a pure RV32I
CPU.

The following commands will build the RISC-V GNU toolchain and libraries for a
pure RV32I target, and install it in `/opt/riscv32i`:

    # Ubuntu packages needed:
    sudo apt-get install autoconf automake autotools-dev curl libmpc-dev \
            libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo \
	    gperf libtool patchutils bc zlib1g-dev git libexpat1-dev

    sudo mkdir /opt/riscv32i
    sudo chown $USER /opt/riscv32i

    git clone https://github.com/riscv/riscv-gnu-toolchain riscv-gnu-toolchain-rv32i
    cd riscv-gnu-toolchain-rv32i
    git checkout 411d134
    git submodule update --init --recursive

    mkdir build; cd build
    ../configure --with-arch=rv32i --prefix=/opt/riscv32i
    make -j$(nproc)

The commands will all be named using the prefix `riscv32-unknown-elf-`, which
makes it easy to install them side-by-side with the regular riscv-tools (those
are using the name prefix `riscv64-unknown-elf-` by default).

Alternatively you can simply use one of the following make targets from PicoRV32's
Makefile to build a `RV32I[M][C]` toolchain. You still need to install all
prerequisites, as described above. Then run any of the following commands in the
PicoRV32 source directory:

| Command                                  | Install Directory  | ISA       |
|:---------------------------------------- |:------------------ |:--------  |
| `make -j$(nproc) build-riscv32i-tools`   | `/opt/riscv32i/`   | `RV32I`   |
| `make -j$(nproc) build-riscv32ic-tools`  | `/opt/riscv32ic/`  | `RV32IC`  |
| `make -j$(nproc) build-riscv32im-tools`  | `/opt/riscv32im/`  | `RV32IM`  |
| `make -j$(nproc) build-riscv32imc-tools` | `/opt/riscv32imc/` | `RV32IMC` |

Or simply run `make -j$(nproc) build-tools` to build and install all four tool chains.

By default calling any of those make targets will (re-)download the toolchain
sources. Run `make download-tools` to download the sources to `/var/cache/distfiles/`
once in advance.

*Note: These instructions are for git rev 411d134 (2018-02-14) of riscv-gnu-toolchain.*


Linking binaries with newlib for PicoRV32
-----------------------------------------

The tool chains (see last section for install instructions) come with a version of
the newlib C standard library.

Use the linker script [firmware/riscv.ld](firmware/riscv.ld) for linking binaries
against the newlib library. Using this linker script will create a binary that
has its entry point at 0x10000. (The default linker script does not have a static
entry point, thus a proper ELF loader would be needed that can determine the
entry point at runtime while loading the program.)

Newlib comes with a few syscall stubs. You need to provide your own implementation
of those syscalls and link your program with this implementation, overwriting the
default stubs from newlib. See `syscalls.c` in [scripts/cxxdemo/](scripts/cxxdemo/)
for an example of how to do that.


Evaluation: Timing and Utilization on Xilinx 7-Series FPGAs
-----------------------------------------------------------

The following evaluations have been performed with Vivado 2017.3.

---
<!-- chunk_id=picorv32_README_44 | Timing on Xilinx 7-Series FPGAs -->

#### Timing on Xilinx 7-Series FPGAs

The `picorv32_axi` module with enabled `TWO_CYCLE_ALU` has been placed and
routed for Xilinx Artix-7T, Kintex-7T, Virtex-7T, Kintex UltraScale, and Virtex
UltraScale devices in all speed grades. A binary search is used to find the
shortest clock period for which the design meets timing.

See `make table.txt` in [scripts/vivado/](scripts/vivado/).

| Device                    | Device               | Speedgrade | Clock Period (Freq.) |
|:------------------------- |:---------------------|:----------:| --------------------:|
| Xilinx Kintex-7T          | xc7k70t-fbg676-2     | -2         |     2.4 ns (416 MHz) |
| Xilinx Kintex-7T          | xc7k70t-fbg676-3     | -3         |     2.2 ns (454 MHz) |
| Xilinx Virtex-7T          | xc7v585t-ffg1761-2   | -2         |     2.3 ns (434 MHz) |
| Xilinx Virtex-7T          | xc7v585t-ffg1761-3   | -3         |     2.2 ns (454 MHz) |
| Xilinx Kintex UltraScale  | xcku035-fbva676-2-e  | -2         |     2.0 ns (500 MHz) |
| Xilinx Kintex UltraScale  | xcku035-fbva676-3-e  | -3         |     1.8 ns (555 MHz) |
| Xilinx Virtex UltraScale  | xcvu065-ffvc1517-2-e | -2         |     2.1 ns (476 MHz) |
| Xilinx Virtex UltraScale  | xcvu065-ffvc1517-3-e | -3         |     2.0 ns (500 MHz) |
| Xilinx Kintex UltraScale+ | xcku3p-ffva676-2-e   | -2         |     1.4 ns (714 MHz) |
| Xilinx Kintex UltraScale+ | xcku3p-ffva676-3-e   | -3         |     1.3 ns (769 MHz) |
| Xilinx Virtex UltraScale+ | xcvu3p-ffvc1517-2-e  | -2         |     1.5 ns (666 MHz) |
| Xilinx Virtex UltraScale+ | xcvu3p-ffvc1517-3-e  | -3         |     1.4 ns (714 MHz) |

---
<!-- chunk_id=picorv32_README_45 | Utilization on Xilinx 7-Series FPGAs -->

#### Utilization on Xilinx 7-Series FPGAs

The following table lists the resource utilization in area-optimized synthesis
for the following three cores:

- **PicoRV32 (small):** The `picorv32` module without counter instructions,
  without two-stage shifts, with externally latched `mem_rdata`, and without
  catching of misaligned memory accesses and illegal instructions.

- **PicoRV32 (regular):** The `picorv32` module in its default configuration.

- **PicoRV32 (large):** The `picorv32` module with enabled PCPI, IRQ, MUL,
  DIV, BARREL_SHIFTER, and COMPRESSED_ISA features.

See `make area` in [scripts/vivado/](scripts/vivado/).

| Core Variant       | Slice LUTs | LUTs as Memory | Slice Registers |
|:------------------ | ----------:| --------------:| ---------------:|
| PicoRV32 (small)   |        761 |             48 |             442 |
| PicoRV32 (regular) |        917 |             48 |             583 |
| PicoRV32 (large)   |       2019 |             88 |            1085 |

---
<!-- chunk_id=picorv32_dhrystone_Makefile_0 | picorv32_dhrystone_Makefile -->

USE_MYSTDLIB = 0
OBJS = dhry_1.o dhry_2.o stdlib.o
CFLAGS = -MD -O3 -mabi=ilp32 -march=rv32im -DTIME -DRISCV
TOOLCHAIN_PREFIX = /opt/riscv32im/bin/riscv32-unknown-elf-

ifeq ($(USE_MYSTDLIB),1)
CFLAGS += -DUSE_MYSTDLIB -ffreestanding -nostdlib
OBJS += start.o
else
OBJS += syscalls.o
endif

test: testbench.vvp dhry.hex
	vvp -N testbench.vvp

test_trace: testbench.vvp dhry.hex
	vvp -N $< +trace
	python3 ../showtrace.py testbench.trace dhry.elf > testbench.ins

test_nola: testbench_nola.vvp dhry.hex
	vvp -N testbench_nola.vvp

timing: timing.txt
	grep '^##' timing.txt | gawk 'x != "" {print x,$$3-y;} {x=$$2;y=$$3;}' | sort | uniq -c | \
		gawk '{printf("%03d-%-7s %2d %-8s (%d)\n",$$3,$$2,$$3,$$2,$$1);}' | sort | cut -c13-

timing.txt: timing.vvp dhry.hex
	vvp -N timing.vvp > timing.txt

testbench.vvp: testbench.v ../picorv32.v
	iverilog -o testbench.vvp testbench.v ../picorv32.v
	chmod -x testbench.vvp

testbench_nola.vvp: testbench_nola.v ../picorv32.v
	iverilog -o testbench_nola.vvp testbench_nola.v ../picorv32.v
	chmod -x testbench_nola.vvp

timing.vvp: testbench.v ../picorv32.v
	iverilog -o timing.vvp -DTIMING testbench.v ../picorv32.v
	chmod -x timing.vvp

dhry.hex: dhry.elf
	$(TOOLCHAIN_PREFIX)objcopy -O verilog $< $@

ifeq ($(USE_MYSTDLIB),1)
dhry.elf: $(OBJS) sections.lds
	$(TOOLCHAIN_PREFIX)gcc $(CFLAGS) -Wl,-Bstatic,-T,sections.lds,-Map,dhry.map,--strip-debug -o $@ $(OBJS) -lgcc
	chmod -x $@
else
dhry.elf: $(OBJS)
	$(TOOLCHAIN_PREFIX)gcc $(CFLAGS) -Wl,-Bstatic,-T,../firmware/riscv.ld,-Map,dhry.map,--strip-debug -o $@ $(OBJS) -lgcc -lc
	chmod -x $@
endif

%.o: %.c
	$(TOOLCHAIN_PREFIX)gcc -c $(CFLAGS) $<

%.o: %.S
	$(TOOLCHAIN_PREFIX)gcc -c $(CFLAGS) $<

dhry_1.o dhry_2.o: CFLAGS += -Wno-implicit-int -Wno-implicit-function-declaration

clean:
	rm -rf *.o *.d dhry.elf dhry.map dhry.bin dhry.hex testbench.vvp testbench.vcd timing.vvp timing.txt testbench_nola.vvp

.PHONY: test clean

-include *.d

---
<!-- chunk_id=picorv32_dhrystone_README_0 | picorv32_dhrystone_README -->

The Dhrystone benchmark and a verilog testbench to run it.

---
<!-- chunk_id=picorv32_dhrystone_start_asm | Assembly Test: PICORV32_DHRYSTONE_START -->

# Assembly Test: `PICORV32_DHRYSTONE_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text
	.global start
	.global main

start:
	/* print "START\n" */
	lui a0,0x10000000>>12
	addi a1,zero,'S'
	addi a2,zero,'T'
	addi a3,zero,'A'
	addi a4,zero,'R'
	addi a5,zero,'\n'
	sw a1,0(a0)
	sw a2,0(a0)
	sw a3,0(a0)
	sw a4,0(a0)
	sw a2,0(a0)
	sw a5,0(a0)

	/* execute some insns for "make timing" */
	lui a0,0
	auipc a0,0
	slli a0,a0,0
	slli a0,a0,31
	addi a1,zero,0
	sll a0,a0,a1
	addi a1,zero,31
	sll a0,a0,a1

	/* set stack pointer */
	lui sp,(64*1024)>>12

	/* jump to main C code */
	jal ra,main

	/* print "DONE\n" */
	lui a0,0x10000000>>12
	addi a1,zero,'D'
	addi a2,zero,'O'
	addi a3,zero,'N'
	addi a4,zero,'E'
	addi a5,zero,'\n'
	sw a1,0(a0)
	sw a2,0(a0)
	sw a3,0(a0)
	sw a4,0(a0)
	sw a5,0(a0)

	/* trap */
	ebreak
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 3–9

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 10–59

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	wire mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg  [31:0] mem_rdata;

	wire mem_la_read;
	wire mem_la_write;
	wire [31:0] mem_la_addr;
	wire [31:0] mem_la_wdata;
	wire [3:0] mem_la_wstrb;

	wire trace_valid;
	wire [35:0] trace_data;

	picorv32 #(
		.BARREL_SHIFTER(1),
		.ENABLE_FAST_MUL(1),
		.ENABLE_DIV(1),
		.PROGADDR_RESET('h10000),
		.STACKADDR('h10000),
		.ENABLE_TRACE(1)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  ),
		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb),
		.trace_valid (trace_valid),
		.trace_data  (trace_data )
	);

	reg [7:0] memory [0:256*1024-1];
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_3 | initial $readmemh("dhry.hex", memory); -->

# Verilog Block: `initial $readmemh("dhry.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 60–63

```verilog
initial $readmemh("dhry.hex", memory);

	assign mem_ready = 1;
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 64–86

```verilog
always @(posedge clk) begin
		mem_rdata[ 7: 0] <= mem_la_read ? memory[mem_la_addr + 0] : 'bx;
		mem_rdata[15: 8] <= mem_la_read ? memory[mem_la_addr + 1] : 'bx;
		mem_rdata[23:16] <= mem_la_read ? memory[mem_la_addr + 2] : 'bx;
		mem_rdata[31:24] <= mem_la_read ? memory[mem_la_addr + 3] : 'bx;
		if (mem_la_write) begin
			case (mem_la_addr)
				32'h1000_0000: begin
`ifndef TIMING
					$write("%c", mem_la_wdata);
					$fflush();
`endif
				end
				default: begin
					if (mem_la_wstrb[0]) memory[mem_la_addr + 0] <= mem_la_wdata[ 7: 0];
					if (mem_la_wstrb[1]) memory[mem_la_addr + 1] <= mem_la_wdata[15: 8];
					if (mem_la_wstrb[2]) memory[mem_la_addr + 2] <= mem_la_wdata[23:16];
					if (mem_la_wstrb[3]) memory[mem_la_addr + 3] <= mem_la_wdata[31:24];
				end
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_5 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 87–93

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);
	end

	integer trace_file;
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_6 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 94–107

```verilog
initial begin
		if ($test$plusargs("trace")) begin
			trace_file = $fopen("testbench.trace", "w");
			repeat (10) @(posedge clk);
			while (!trap) begin
				@(posedge clk);
				if (trace_valid)
					$fwrite(trace_file, "%x\n", trace_data);
			end
			$fclose(trace_file);
			$display("Finished writing testbench.trace.");
		end
	end
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_7 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 108–116

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			repeat (10) @(posedge clk);
			$display("TRAP");
			$finish;
		end
	end

`ifdef TIMING
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_8 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 117–120

```verilog
initial begin
		repeat (100000) @(posedge clk);
		$finish;
	end
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_9 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench.v` | Lines 121–125

```verilog
always @(posedge clk) begin
		if (uut.dbg_next)
			$display("## %-s %d", uut.dbg_ascii_instr ? uut.dbg_ascii_instr : "pcpi", uut.count_cycle);
	end
`endif
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 1–4

```verilog
// A version of the dhrystone test bench that isn't using the look-ahead interface

`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 5–11

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 12–44

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	reg  mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0]  mem_wstrb;
	reg  [31:0] mem_rdata;

	picorv32 #(
		.BARREL_SHIFTER(1),
		.ENABLE_FAST_MUL(1),
		.ENABLE_DIV(1),
		.PROGADDR_RESET('h10000),
		.STACKADDR('h10000)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	reg [7:0] memory [0:256*1024-1];
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_3 | initial $readmemh("dhry.hex", memory); -->

# Verilog Block: `initial $readmemh("dhry.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 45–46

```verilog
initial $readmemh("dhry.hex", memory);
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 47–82

```verilog
always @(posedge clk) begin
		mem_ready <= 1'b0;

		mem_rdata[ 7: 0] <= 'bx;
		mem_rdata[15: 8] <= 'bx;
		mem_rdata[23:16] <= 'bx;
		mem_rdata[31:24] <= 'bx;

		if (mem_valid & !mem_ready) begin
			if (|mem_wstrb) begin
				mem_ready <= 1'b1;

				case (mem_addr)
					32'h1000_0000: begin
						$write("%c", mem_wdata);
						$fflush();
					end
					default: begin
						if (mem_wstrb[0]) memory[mem_addr + 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr + 1] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr + 2] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr + 3] <= mem_wdata[31:24];
					end
				endcase
			end
			else begin
				mem_ready <= 1'b1;

				mem_rdata[ 7: 0] <= memory[mem_addr + 0];
				mem_rdata[15: 8] <= memory[mem_addr + 1];
				mem_rdata[23:16] <= memory[mem_addr + 2];
				mem_rdata[31:24] <= memory[mem_addr + 3];
			end
		end
	end
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_5 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 83–87

```verilog
initial begin
		$dumpfile("testbench_nola.vcd");
		$dumpvars(0, testbench);
	end
```

---
<!-- chunk_id=picorv32_dhrystone_testbench_nola_6 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/dhrystone/testbench_nola.v` | Lines 88–94

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			repeat (10) @(posedge clk);
			$display("TRAP");
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_firmware_README_0 | picorv32_firmware_README -->

A simple test firmware. This code is in the public domain. Simply copy whatever
you can use.

---
<!-- chunk_id=picorv32_firmware_custom_ops_asm | Assembly Test: PICORV32_FIRMWARE_CUSTOM_OPS -->

# Assembly Test: `PICORV32_FIRMWARE_CUSTOM_OPS`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/firmware/custom_ops.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
// This is free and unencumbered software released into the public domain.
//
// Anyone is free to copy, modify, publish, use, compile, sell, or
// distribute this software, either in source code form or as a compiled
// binary, for any purpose, commercial or non-commercial, and by any
// means.

#define regnum_q0   0
#define regnum_q1   1
#define regnum_q2   2
#define regnum_q3   3

#define regnum_x0   0
#define regnum_x1   1
#define regnum_x2   2
#define regnum_x3   3
#define regnum_x4   4
#define regnum_x5   5
#define regnum_x6   6
#define regnum_x7   7
#define regnum_x8   8
#define regnum_x9   9
#define regnum_x10 10
#define regnum_x11 11
#define regnum_x12 12
#define regnum_x13 13
#define regnum_x14 14
#define regnum_x15 15
#define regnum_x16 16
#define regnum_x17 17
#define regnum_x18 18
#define regnum_x19 19
#define regnum_x20 20
#define regnum_x21 21
#define regnum_x22 22
#define regnum_x23 23
#define regnum_x24 24
#define regnum_x25 25
#define regnum_x26 26
#define regnum_x27 27
#define regnum_x28 28
#define regnum_x29 29
#define regnum_x30 30
#define regnum_x31 31

#define regnum_zero 0
#define regnum_ra   1
#define regnum_sp   2
#define regnum_gp   3
#define regnum_tp   4
#define regnum_t0   5
#define regnum_t1   6
#define regnum_t2   7
#define regnum_s0   8
#define regnum_s1   9
#define regnum_a0  10
#define regnum_a1  11
#define regnum_a2  12
#define regnum_a3  13
#define regnum_a4  14
#define regnum_a5  15
#define regnum_a6  16
#define regnum_a7  17
#define regnum_s2  18
#define regnum_s3  19
#define regnum_s4  20
#define regnum_s5  21
#define regnum_s6  22
#define regnum_s7  23
#define regnum_s8  24
#define regnum_s9  25
#define regnum_s10 26
#define regnum_s11 27
#define regnum_t3  28
#define regnum_t4  29
#define regnum_t5  30
#define regnum_t6  31

// x8 is s0 and also fp
#define regnum_fp   8

#define r_type_insn(_f7, _rs2, _rs1, _f3, _rd, _opc) \
.word (((_f7) << 25) | ((_rs2) << 20) | ((_rs1) << 15) | ((_f3) << 12) | ((_rd) << 7) | ((_opc) << 0))

#define picorv32_getq_insn(_rd, _qs) \
r_type_insn(0b0000000, 0, regnum_ ## _qs, 0b100, regnum_ ## _rd, 0b0001011)

#define picorv32_setq_insn(_qd, _rs) \
r_type_insn(0b0000001, 0, regnum_ ## _rs, 0b010, regnum_ ## _qd, 0b0001011)

#define picorv32_retirq_insn() \
r_type_insn(0b0000010, 0, 0, 0b000, 0, 0b0001011)

#define picorv32_maskirq_insn(_rd, _rs) \
r_type_insn(0b0000011, 0, regnum_ ## _rs, 0b110, regnum_ ## _rd, 0b0001011)

#define picorv32_waitirq_insn(_rd) \
r_type_insn(0b0000100, 0, 0, 0b100, regnum_ ## _rd, 0b0001011)

#define picorv32_timer_insn(_rd, _rs) \
r_type_insn(0b0000101, 0, regnum_ ## _rs, 0b110, regnum_ ## _rd, 0b0001011)
```

---
<!-- chunk_id=picorv32_firmware_riscv_ld_0 | picorv32_firmware_riscv_ld -->

/* ---- Original Script: /opt/riscv32i/riscv32-unknown-elf/lib/ldscripts/elf32lriscv.x ---- */
/* Default linker script, for normal executables */
/* Copyright (C) 2014-2017 Free Software Foundation, Inc.
   Copying and distribution of this script, with or without modification,
   are permitted in any medium without royalty provided the copyright
   notice and this notice are preserved.  */
OUTPUT_FORMAT("elf32-littleriscv", "elf32-littleriscv",
	      "elf32-littleriscv")
OUTPUT_ARCH(riscv)
ENTRY(_start)
SEARCH_DIR("/opt/riscv32i/riscv32-unknown-elf/lib");
SECTIONS
{
  /* Read-only sections, merged into text segment: */
  PROVIDE (__executable_start = SEGMENT_START("text-segment", 0x10000)); . = SEGMENT_START("text-segment", 0x10000) + SIZEOF_HEADERS;
  .interp         : { *(.interp) }
  .note.gnu.build-id : { *(.note.gnu.build-id) }
  .hash           : { *(.hash) }
  .gnu.hash       : { *(.gnu.hash) }
  .dynsym         : { *(.dynsym) }
  .dynstr         : { *(.dynstr) }
  .gnu.version    : { *(.gnu.version) }
  .gnu.version_d  : { *(.gnu.version_d) }
  .gnu.version_r  : { *(.gnu.version_r) }
  .rela.init      : { *(.rela.init) }
  .rela.text      : { *(.rela.text .rela.text.* .rela.gnu.linkonce.t.*) }
  .rela.fini      : { *(.rela.fini) }
  .rela.rodata    : { *(.rela.rodata .rela.rodata.* .rela.gnu.linkonce.r.*) }
  .rela.data.rel.ro   : { *(.rela.data.rel.ro .rela.data.rel.ro.* .rela.gnu.linkonce.d.rel.ro.*) }
  .rela.data      : { *(.rela.data .rela.data.* .rela.gnu.linkonce.d.*) }
  .rela.tdata	  : { *(.rela.tdata .rela.tdata.* .rela.gnu.linkonce.td.*) }
  .rela.tbss	  : { *(.rela.tbss .rela.tbss.* .rela.gnu.linkonce.tb.*) }
  .rela.ctors     : { *(.rela.ctors) }
  .rela.dtors     : { *(.rela.dtors) }
  .rela.got       : { *(.rela.got) }
  .rela.sdata     : { *(.rela.sdata .rela.sdata.* .rela.gnu.linkonce.s.*) }
  .rela.sbss      : { *(.rela.sbss .rela.sbss.* .rela.gnu.linkonce.sb.*) }
  .rela.sdata2    : { *(.rela.sdata2 .rela.sdata2.* .rela.gnu.linkonce.s2.*) }
  .rela.sbss2     : { *(.rela.sbss2 .rela.sbss2.* .rela.gnu.linkonce.sb2.*) }
  .rela.bss       : { *(.rela.bss .rela.bss.* .rela.gnu.linkonce.b.*) }
  .rela.iplt      :
    {
      PROVIDE_HIDDEN (__rela_iplt_start = .);
      *(.rela.iplt)
      PROVIDE_HIDDEN (__rela_iplt_end = .);
    }
  .rela.plt       :
    {
      *(.rela.plt)
    }
  .init           :
  {
    KEEP (*(SORT_NONE(.init)))
  }
  .plt            : { *(.plt) }
  .iplt           : { *(.iplt) }
  .text           :
  {
    *(.text.unlikely .text.*_unlikely .text.unlikely.*)
    *(.text.exit .text.exit.*)
    *(.text.startup .text.startup.*)
    *(.text.hot .text.hot.*)
    *(.text .stub .text.* .gnu.linkonce.t.*)
    /* .gnu.warning sections are handled specially by elf32.em.  */
    *(.gnu.warning)
  }
  .fini           :
  {
    KEEP (*(SORT_NONE(.fini)))
  }
  PROVIDE (__etext = .);
  PROVIDE (_etext = .);
  PROVIDE (etext = .);
  .rodata         : { *(.rodata .rodata.* .gnu.linkonce.r.*) }
  .rodata1        : { *(.rodata1) }
  .sdata2         :
  {
    *(.sdata2 .sdata2.* .gnu.linkonce.s2.*)
  }
  .sbss2          : { *(.sbss2 .sbss2.* .gnu.linkonce.sb2.*) }
  .eh_frame_hdr : { *(.eh_frame_hdr) *(.eh_frame_entry .eh_frame_entry.*) }
  .eh_frame       : ONLY_IF_RO { KEEP (*(.eh_frame)) *(.eh_frame.*) }
  .gcc_except_table   : ONLY_IF_RO { *(.gcc_except_table
  .gcc_except_table.*) }
  .gnu_extab   : ONLY_IF_RO { *(.gnu_extab*) }
  /* These sections are generated by the Sun/Oracle C++ compiler.  */
  .exception_ranges   : ONLY_IF_RO { *(.exception_ranges
  .exception_ranges*) }
  /* Adjust the address for the data segment.  We want to adjust up to
     the same address within the page on the next page up.  */
  . = DATA_SEGMENT_ALIGN (CONSTANT (MAXPAGESIZE), CONSTANT (COMMONPAGESIZE));
  /* Exception handling  */
  .eh_frame       : ONLY_IF_RW { KEEP (*(.eh_frame)) *(.eh_frame.*) }
  .gnu_extab      : ONLY_IF_RW { *(.gnu_extab) }
  .gcc_except_table   : ONLY_IF_RW { *(.gcc_except_table .gcc_except_table.*) }
  .exception_ranges   : ONLY_IF_RW { *(.exception_ranges .exception_ranges*) }
  /* Thread Local Storage sections  */
  .tdata	  : { *(.tdata .tdata.* .gnu.linkonce.td.*) }
  .tbss		  : { *(.tbss .tbss.* .gnu.linkonce.tb.*) *(.tcommon) }
  .preinit_array     :
  {
    PROVIDE_HIDDEN (__preinit_array_start = .);
    KEEP (*(.preinit_array))
    PROVIDE_HIDDEN (__preinit_array_end = .);
  }
  .init_array     :
  {
    PROVIDE_HIDDEN (__init_array_start = .);
    KEEP (*(SORT_BY_INIT_PRIORITY(.init_array.*) SORT_BY_INIT_PRIORITY(.ctors.*)))
    KEEP (*(.init_array EXCLUDE_FILE (*crtbegin.o *crtbegin?.o *crtend.o *crtend?.o ) .ctors))
    PROVIDE_HIDDEN (__init_array_end = .);
  }
  .fini_array     :
  {
    PROVIDE_HIDDEN (__fini_array_start = .);
    KEEP (*(SORT_BY_INIT_PRIORITY(.fini_array.*) SORT_BY_INIT_PRIORITY(.dtors.*)))
    KEEP (*(.fini_array EXCLUDE_FILE (*crtbegin.o *crtbegin?.o *crtend.o *crtend?.o ) .dtors))
    PROVIDE_HIDDEN (__fini_array_end = .);
  }
  .ctors          :
  {
    /* gcc uses crtbegin.o to find the start of
       the constructors, so we make sure it is
       first.  Because this is a wildcard, it
       doesn't matter if the user does not
       actually link against crtbegin.o; the
       linker won't look for a file to match a
       wildcard.  The wildcard also means that it
       doesn't matter which directory crtbegin.o
       is in.  */
    KEEP (*crtbegin.o(.ctors))
    KEEP (*crtbegin?.o(.ctors))
    /* We don't want to include the .ctor section from
       the crtend.o file until after the sorted ctors.
       The .ctor section from the crtend file contains the
       end of ctors marker and it must be last */
    KEEP (*(EXCLUDE_FILE (*crtend.o *crtend?.o ) .ctors))
    KEEP (*(SORT(.ctors.*)))
    KEEP (*(.ctors))
  }
  .dtors          :
  {
    KEEP (*crtbegin.o(.dtors))
    KEEP (*crtbegin?.o(.dtors))
    KEEP (*(EXCLUDE_FILE (*crtend.o *crtend?.o ) .dtors))
    KEEP (*(SORT(.dtors.*)))
    KEEP (*(.dtors))
  }
  .jcr            : { KEEP (*(.jcr)) }
  .data.rel.ro : { *(.data.rel.ro.local* .gnu.linkonce.d.rel.ro.local.*) *(.data.rel.ro .data.rel.ro.* .gnu.linkonce.d.rel.ro.*) }
  .dynamic        : { *(.dynamic) }
  . = DATA_SEGMENT_RELRO_END (0, .);
  .data           :
  {
    *(.data .data.* .gnu.linkonce.d.*)
    SORT(CONSTRUCTORS)
  }
  .data1          : { *(.data1) }
  .got            : { *(.got.plt) *(.igot.plt) *(.got) *(.igot) }
  /* We want the small data sections together, so single-instruction offsets
     can access them all, and initialized data all before uninitialized, so
     we can shorten the on-disk segment size.  */
  .sdata          :
  {
    __global_pointer$ = . + 0x800;
    *(.srodata.cst16) *(.srodata.cst8) *(.srodata.cst4) *(.srodata.cst2) *(.srodata .srodata.*)
    *(.sdata .sdata.* .gnu.linkonce.s.*)
  }
  _edata = .; PROVIDE (edata = .);
  . = .;
  __bss_start = .;
  .sbss           :
  {
    *(.dynsbss)
    *(.sbss .sbss.* .gnu.linkonce.sb.*)
    *(.scommon)
  }
  .bss            :
  {
   *(.dynbss)
   *(.bss .bss.* .gnu.linkonce.b.*)
   *(COMMON)
   /* Align here to ensure that the .bss section occupies space up to
      _end.  Align after .bss to ensure correct alignment even if the
      .bss section disappears because there are no input sections.
      FIXME: Why do we need it? When there is no .bss section, we don't
      pad the .data section.  */
   . = ALIGN(. != 0 ? 32 / 8 : 1);
  }
  . = ALIGN(32 / 8);
  . = SEGMENT_START("ldata-segment", .);
  . = ALIGN(32 / 8);
  _end = .; PROVIDE (end = .);
  . = DATA_SEGMENT_END (.);
  /* Stabs debugging sections.  */
  .stab          0 : { *(.stab) }
  .stabstr       0 : { *(.stabstr) }
  .stab.excl     0 : { *(.stab.excl) }
  .stab.exclstr  0 : { *(.stab.exclstr) }
  .stab.index    0 : { *(.stab.index) }
  .stab.indexstr 0 : { *(.stab.indexstr) }
  .comment       0 : { *(.comment) }
  /* DWARF debug sections.
     Symbols in the DWARF debugging sections are relative to the beginning
     of the section so we begin them at 0.  */
  /* DWARF 1 */
  .debug          0 : { *(.debug) }
  .line           0 : { *(.line) }
  /* GNU DWARF 1 extensions */
  .debug_srcinfo  0 : { *(.debug_srcinfo) }
  .debug_sfnames  0 : { *(.debug_sfnames) }
  /* DWARF 1.1 and DWARF 2 */
  .debug_aranges  0 : { *(.debug_aranges) }
  .debug_pubnames 0 : { *(.debug_pubnames) }
  /* DWARF 2 */
  .debug_info     0 : { *(.debug_info .gnu.linkonce.wi.*) }
  .debug_abbrev   0 : { *(.debug_abbrev) }
  .debug_line     0 : { *(.debug_line .debug_line.* .debug_line_end ) }
  .debug_frame    0 : { *(.debug_frame) }
  .debug_str      0 : { *(.debug_str) }
  .debug_loc      0 : { *(.debug_loc) }
  .debug_macinfo  0 : { *(.debug_macinfo) }
  /* SGI/MIPS DWARF 2 extensions */
  .debug_weaknames 0 : { *(.debug_weaknames) }
  .debug_funcnames 0 : { *(.debug_funcnames) }
  .debug_typenames 0 : { *(.debug_typenames) }
  .debug_varnames  0 : { *(.debug_varnames) }
  /* DWARF 3 */
  .debug_pubtypes 0 : { *(.debug_pubtypes) }
  .debug_ranges   0 : { *(.debug_ranges) }
  /* DWARF Extension.  */
  .debug_macro    0 : { *(.debug_macro) }
  .debug_addr     0 : { *(.debug_addr) }
  .gnu.attributes 0 : { KEEP (*(.gnu.attributes)) }
  /DISCARD/ : { *(.note.GNU-stack) *(.gnu_debuglink) *(.gnu.lto_*) }
}

---
<!-- chunk_id=picorv32_firmware_start_asm | Assembly Test: PICORV32_FIRMWARE_START -->

# Assembly Test: `PICORV32_FIRMWARE_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/firmware/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
// This is free and unencumbered software released into the public domain.
//
// Anyone is free to copy, modify, publish, use, compile, sell, or
// distribute this software, either in source code form or as a compiled
// binary, for any purpose, commercial or non-commercial, and by any
// means.

#define ENABLE_QREGS
#define ENABLE_HELLO
#define ENABLE_RVTST
#define ENABLE_SIEVE
#define ENABLE_MULTST
#define ENABLE_STATS

#ifndef ENABLE_QREGS
#  undef ENABLE_RVTST
#endif

// Only save registers in IRQ wrapper that are to be saved by the caller in
// the RISC-V ABI, with the excpetion of the stack pointer. The IRQ handler
// will save the rest if necessary. I.e. skip x3, x4, x8, x9, and x18-x27.
#undef ENABLE_FASTIRQ

#include "custom_ops.S"

	.section .text
	.global irq
	.global hello
	.global sieve
	.global multest
	.global hard_mul
	.global hard_mulh
	.global hard_mulhsu
	.global hard_mulhu
	.global hard_div
	.global hard_divu
	.global hard_rem
	.global hard_remu
	.global stats

reset_vec:
	// no more than 16 bytes here !
	picorv32_waitirq_insn(zero)
	picorv32_maskirq_insn(zero, zero)
	j start


/* Interrupt handler
 **********************************/

.balign 16
irq_vec:
	/* save registers */

#ifdef ENABLE_QREGS

	picorv32_setq_insn(q2, x1)
	picorv32_setq_insn(q3, x2)

	lui x1, %hi(irq_regs)
	addi x1, x1, %lo(irq_regs)

	picorv32_getq_insn(x2, q0)
	sw x2,   0*4(x1)

	picorv32_getq_insn(x2, q2)
	sw x2,   1*4(x1)

	picorv32_getq_insn(x2, q3)
	sw x2,   2*4(x1)

#ifdef ENABLE_FASTIRQ
	sw x5,   5*4(x1)
	sw x6,   6*4(x1)
	sw x7,   7*4(x1)
	sw x10, 10*4(x1)
	sw x11, 11*4(x1)
	sw x12, 12*4(x1)
	sw x13, 13*4(x1)
	sw x14, 14*4(x1)
	sw x15, 15*4(x1)
	sw x16, 16*4(x1)
	sw x17, 17*4(x1)
	sw x28, 28*4(x1)
	sw x29, 29*4(x1)
	sw x30, 30*4(x1)
	sw x31, 31*4(x1)
#else
	sw x3,   3*4(x1)
	sw x4,   4*4(x1)
	sw x5,   5*4(x1)
	sw x6,   6*4(x1)
	sw x7,   7*4(x1)
	sw x8,   8*4(x1)
	sw x9,   9*4(x1)
	sw x10, 10*4(x1)
	sw x11, 11*4(x1)
	sw x12, 12*4(x1)
	sw x13, 13*4(x1)
	sw x14, 14*4(x1)
	sw x15, 15*4(x1)
	sw x16, 16*4(x1)
	sw x17, 17*4(x1)
	sw x18, 18*4(x1)
	sw x19, 19*4(x1)
	sw x20, 20*4(x1)
	sw x21, 21*4(x1)
	sw x22, 22*4(x1)
	sw x23, 23*4(x1)
	sw x24, 24*4(x1)
	sw x25, 25*4(x1)
	sw x26, 26*4(x1)
	sw x27, 27*4(x1)
	sw x28, 28*4(x1)
	sw x29, 29*4(x1)
	sw x30, 30*4(x1)
	sw x31, 31*4(x1)
#endif

#else // ENABLE_QREGS

#ifdef ENABLE_FASTIRQ
	sw gp,   0*4+0x200(zero)
	sw x1,   1*4+0x200(zero)
	sw x2,   2*4+0x200(zero)
	sw x5,   5*4+0x200(zero)
	sw x6,   6*4+0x200(zero)
	sw x7,   7*4+0x200(zero)
	sw x10, 10*4+0x200(zero)
	sw x11, 11*4+0x200(zero)
	sw x12, 12*4+0x200(zero)
	sw x13, 13*4+0x200(zero)
	sw x14, 14*4+0x200(zero)
	sw x15, 15*4+0x200(zero)
	sw x16, 16*4+0x200(zero)
	sw x17, 17*4+0x200(zero)
	sw x28, 28*4+0x200(zero)
	sw x29, 29*4+0x200(zero)
	sw x30, 30*4+0x200(zero)
	sw x31, 31*4+0x200(zero)
#else
	sw gp,   0*4+0x200(zero)
	sw x1,   1*4+0x200(zero)
	sw x2,   2*4+0x200(zero)
	sw x3,   3*4+0x200(zero)
	sw x4,   4*4+0x200(zero)
	sw x5,   5*4+0x200(zero)
	sw x6,   6*4+0x200(zero)
	sw x7,   7*4+0x200(zero)
	sw x8,   8*4+0x200(zero)
	sw x9,   9*4+0x200(zero)
	sw x10, 10*4+0x200(zero)
	sw x11, 11*4+0x200(zero)
	sw x12, 12*4+0x200(zero)
	sw x13, 13*4+0x200(zero)
	sw x14, 14*4+0x200(zero)
	sw x15, 15*4+0x200(zero)
	sw x16, 16*4+0x200(zero)
	sw x17, 17*4+0x200(zero)
	sw x18, 18*4+0x200(zero)
	sw x19, 19*4+0x200(zero)
	sw x20, 20*4+0x200(zero)
	sw x21, 21*4+0x200(zero)
	sw x22, 22*4+0x200(zero)
	sw x23, 23*4+0x200(zero)
	sw x24, 24*4+0x200(zero)
	sw x25, 25*4+0x200(zero)
	sw x26, 26*4+0x200(zero)
	sw x27, 27*4+0x200(zero)
	sw x28, 28*4+0x200(zero)
	sw x29, 29*4+0x200(zero)
	sw x30, 30*4+0x200(zero)
	sw x31, 31*4+0x200(zero)
#endif

#endif // ENABLE_QREGS

	/* call interrupt handler C function */

	lui sp, %hi(irq_stack)
	addi sp, sp, %lo(irq_stack)

	// arg0 = address of regs
	lui a0, %hi(irq_regs)
	addi a0, a0, %lo(irq_regs)

	// arg1 = interrupt type
#ifdef ENABLE_QREGS
	picorv32_getq_insn(a1, q1)
#else
	addi a1, tp, 0
#endif

	// call to C function
	jal ra, irq

	/* restore registers */

#ifdef ENABLE_QREGS

	// new irq_regs address returned from C code in a0
	addi x1, a0, 0

	lw x2,   0*4(x1)
	picorv32_setq_insn(q0, x2)

	lw x2,   1*4(x1)
	picorv32_setq_insn(q1, x2)

	lw x2,   2*4(x1)
	picorv32_setq_insn(q2, x2)

#ifdef ENABLE_FASTIRQ
	lw x5,   5*4(x1)
	lw x6,   6*4(x1)
	lw x7,   7*4(x1)
	lw x10, 10*4(x1)
	lw x11, 11*4(x1)
	lw x12, 12*4(x1)
	lw x13, 13*4(x1)
	lw x14, 14*4(x1)
	lw x15, 15*4(x1)
	lw x16, 16*4(x1)
	lw x17, 17*4(x1)
	lw x28, 28*4(x1)
	lw x29, 29*4(x1)
	lw x30, 30*4(x1)
	lw x31, 31*4(x1)
#else
	lw x3,   3*4(x1)
	lw x4,   4*4(x1)
	lw x5,   5*4(x1)
	lw x6,   6*4(x1)
	lw x7,   7*4(x1)
	lw x8,   8*4(x1)
	lw x9,   9*4(x1)
	lw x10, 10*4(x1)
	lw x11, 11*4(x1)
	lw x12, 12*4(x1)
	lw x13, 13*4(x1)
	lw x14, 14*4(x1)
	lw x15, 15*4(x1)
	lw x16, 16*4(x1)
	lw x17, 17*4(x1)
	lw x18, 18*4(x1)
	lw x19, 19*4(x1)
	lw x20, 20*4(x1)
	lw x21, 21*4(x1)
	lw x22, 22*4(x1)
	lw x23, 23*4(x1)
	lw x24, 24*4(x1)
	lw x25, 25*4(x1)
	lw x26, 26*4(x1)
	lw x27, 27*4(x1)
	lw x28, 28*4(x1)
	lw x29, 29*4(x1)
	lw x30, 30*4(x1)
	lw x31, 31*4(x1)
#endif

	picorv32_getq_insn(x1, q1)
	picorv32_getq_insn(x2, q2)

#else // ENABLE_QREGS

	// new irq_regs address returned from C code in a0
	addi a1, zero, 0x200
	beq a0, a1, 1f
	ebreak
1:

#ifdef ENABLE_FASTIRQ
	lw gp,   0*4+0x200(zero)
	lw x1,   1*4+0x200(zero)
	lw x2,   2*4+0x200(zero)
	lw x5,   5*4+0x200(zero)
	lw x6,   6*4+0x200(zero)
	lw x7,   7*4+0x200(zero)
	lw x10, 10*4+0x200(zero)
	lw x11, 11*4+0x200(zero)
	lw x12, 12*4+0x200(zero)
	lw x13, 13*4+0x200(zero)
	lw x14, 14*4+0x200(zero)
	lw x15, 15*4+0x200(zero)
	lw x16, 16*4+0x200(zero)
	lw x17, 17*4+0x200(zero)
	lw x28, 28*4+0x200(zero)
	lw x29, 29*4+0x200(zero)
	lw x30, 30*4+0x200(zero)
	lw x31, 31*4+0x200(zero)
#else
	lw gp,   0*4+0x200(zero)
	lw x1,   1*4+0x200(zero)
	lw x2,   2*4+0x200(zero)
	// do not restore x3 (gp)
	lw x4,   4*4+0x200(zero)
	lw x5,   5*4+0x200(zero)
	lw x6,   6*4+0x200(zero)
	lw x7,   7*4+0x200(zero)
	lw x8,   8*4+0x200(zero)
	lw x9,   9*4+0x200(zero)
	lw x10, 10*4+0x200(zero)
	lw x11, 11*4+0x200(zero)
	lw x12, 12*4+0x200(zero)
	lw x13, 13*4+0x200(zero)
	lw x14, 14*4+0x200(zero)
	lw x15, 15*4+0x200(zero)
	lw x16, 16*4+0x200(zero)
	lw x17, 17*4+0x200(zero)
	lw x18, 18*4+0x200(zero)
	lw x19, 19*4+0x200(zero)
	lw x20, 20*4+0x200(zero)
	lw x21, 21*4+0x200(zero)
	lw x22, 22*4+0x200(zero)
	lw x23, 23*4+0x200(zero)
	lw x24, 24*4+0x200(zero)
	lw x25, 25*4+0x200(zero)
	lw x26, 26*4+0x200(zero)
	lw x27, 27*4+0x200(zero)
	lw x28, 28*4+0x200(zero)
	lw x29, 29*4+0x200(zero)
	lw x30, 30*4+0x200(zero)
	lw x31, 31*4+0x200(zero)
#endif

#endif // ENABLE_QREGS

	picorv32_retirq_insn()

.balign 0x200
irq_regs:
	// registers are saved to this memory region during interrupt handling
	// the program counter is saved as register 0
	.fill 32,4

	// stack for the interrupt handler
	.fill 128,4
irq_stack:


/* Main program
 **********************************/

start:
	/* zero-initialize all registers */

	addi x1, zero, 0
	addi x2, zero, 0
	addi x3, zero, 0
	addi x4, zero, 0
	addi x5, zero, 0
	addi x6, zero, 0
	addi x7, zero, 0
	addi x8, zero, 0
	addi x9, zero, 0
	addi x10, zero, 0
	addi x11, zero, 0
	addi x12, zero, 0
	addi x13, zero, 0
	addi x14, zero, 0
	addi x15, zero, 0
	addi x16, zero, 0
	addi x17, zero, 0
	addi x18, zero, 0
	addi x19, zero, 0
	addi x20, zero, 0
	addi x21, zero, 0
	addi x22, zero, 0
	addi x23, zero, 0
	addi x24, zero, 0
	addi x25, zero, 0
	addi x26, zero, 0
	addi x27, zero, 0
	addi x28, zero, 0
	addi x29, zero, 0
	addi x30, zero, 0
	addi x31, zero, 0

#ifdef ENABLE_HELLO
	/* set stack pointer */
	lui sp,(128*1024)>>12

	/* call hello C code */
	jal ra,hello
#endif

	/* running tests from riscv-tests */

#ifdef ENABLE_RVTST
#  define TEST(n) \
	.global n; \
	addi x1, zero, 1000; \
	picorv32_timer_insn(zero, x1); \
	jal zero,n; \
	.global n ## _ret; \
	n ## _ret:
#else
#  define TEST(n) \
	.global n ## _ret; \
	n ## _ret:
#endif

	TEST(lui)
	TEST(auipc)
	TEST(j)
	TEST(jal)
	TEST(jalr)

	TEST(beq)
	TEST(bne)
	TEST(blt)
	TEST(bge)
	TEST(bltu)
	TEST(bgeu)

	TEST(lb)
	TEST(lh)
	TEST(lw)
	TEST(lbu)
	TEST(lhu)

	TEST(sb)
	TEST(sh)
	TEST(sw)

	TEST(addi)
	TEST(slti) // also tests sltiu
	TEST(xori)
	TEST(ori)
	TEST(andi)
	TEST(slli)
	TEST(srli)
	TEST(srai)

	TEST(add)
	TEST(sub)
	TEST(sll)
	TEST(slt) // what is with sltu ?
	TEST(xor)
	TEST(srl)
	TEST(sra)
	TEST(or)
	TEST(and)

	TEST(mulh)
	TEST(mulhsu)
	TEST(mulhu)
	TEST(mul)

	TEST(div)
	TEST(divu)
	TEST(rem)
	TEST(remu)

	TEST(simple)

	/* set stack pointer */
	lui sp,(128*1024)>>12

	/* set gp and tp */
	lui gp, %hi(0xdeadbeef)
	addi gp, gp, %lo(0xdeadbeef)
	addi tp, gp, 0

#ifdef ENABLE_SIEVE
	/* call sieve C code */
	jal ra,sieve
#endif

#ifdef ENABLE_MULTST
	/* call multest C code */
	jal ra,multest
#endif

#ifdef ENABLE_STATS
	/* call stats C code */
	jal ra,stats
#endif

	/* print "DONE\n" */
	lui a0,0x10000000>>12
	addi a1,zero,'D'
	addi a2,zero,'O'
	addi a3,zero,'N'
	addi a4,zero,'E'
	addi a5,zero,'\n'
	sw a1,0(a0)
	sw a2,0(a0)
	sw a3,0(a0)
	sw a4,0(a0)
	sw a5,0(a0)

	li a0, 0x20000000
	li a1, 123456789
	sw a1,0(a0)

	/* trap */
	ebreak


/* Hard mul functions for multest.c
 **********************************/

hard_mul:
	mul a0, a0, a1
	ret

hard_mulh:
	mulh a0, a0, a1
	ret

hard_mulhsu:
	mulhsu a0, a0, a1
	ret

hard_mulhu:
	mulhu a0, a0, a1
	ret

hard_div:
	div a0, a0, a1
	ret

hard_divu:
	divu a0, a0, a1
	ret

hard_rem:
	rem a0, a0, a1
	ret

hard_remu:
	remu a0, a0, a1
	ret
```

---
<!-- chunk_id=picorv32_picorv32_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1–32

```verilog
/*
 *  PicoRV32 -- A Small RISC-V (RV32I) Processor Core
 *
 *  Copyright (C) 2015  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

/* verilator lint_off WIDTH */
/* verilator lint_off PINMISSING */
/* verilator lint_off CASEOVERLAP */
/* verilator lint_off CASEINCOMPLETE */

`timescale 1 ns / 1 ps
// `default_nettype none
// `define DEBUGNETS
// `define DEBUGREGS
// `define DEBUGASM
// `define DEBUG

`ifdef DEBUG
```

---
<!-- chunk_id=picorv32_picorv32_1 | `define debug(debug_command) debug_command -->

# Verilog Block: ``define debug(debug_command) debug_command`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 33–34

```verilog
`define debug(debug_command) debug_command
`else
```

---
<!-- chunk_id=picorv32_picorv32_2 | `define debug(debug_command) -->

# Verilog Block: ``define debug(debug_command)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 35–38

```verilog
`define debug(debug_command)
`endif

`ifdef FORMAL
```

---
<!-- chunk_id=picorv32_picorv32_3 | `define FORMAL_KEEP (* keep *) -->

# Verilog Block: ``define FORMAL_KEEP (* keep *)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 39–39

```verilog
`define FORMAL_KEEP (* keep *)
```

---
<!-- chunk_id=picorv32_picorv32_4 | `define assert(assert_expr) assert(assert_expr) -->

# Verilog Block: ``define assert(assert_expr) assert(assert_expr)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 40–42

```verilog
`define assert(assert_expr) assert(assert_expr)
`else
  `ifdef DEBUGNETS
```

---
<!-- chunk_id=picorv32_picorv32_5 | `define FORMAL_KEEP (* keep *) -->

# Verilog Block: ``define FORMAL_KEEP (* keep *)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 43–44

```verilog
`define FORMAL_KEEP (* keep *)
  `else
```

---
<!-- chunk_id=picorv32_picorv32_6 | `define FORMAL_KEEP -->

# Verilog Block: ``define FORMAL_KEEP`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 45–46

```verilog
`define FORMAL_KEEP
  `endif
```

---
<!-- chunk_id=picorv32_picorv32_7 | `define assert(assert_expr) empty_statement -->

# Verilog Block: ``define assert(assert_expr) empty_statement`

> **Block Comment:** uncomment this for register file in extra module `define PICORV32_REGS picorv32_regs

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 47–54

```verilog
`define assert(assert_expr) empty_statement
`endif

// uncomment this for register file in extra module
// `define PICORV32_REGS picorv32_regs

// this macro can be used to check if the verilog files in your
// design are read in the correct order.
```

---
<!-- chunk_id=picorv32_picorv32_8 | `define PICORV32_V -->

# Verilog Block: ``define PICORV32_V`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 55–61

```verilog
`define PICORV32_V


/***************************************************************
 * picorv32
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_9 | module picorv32 #( -->

# Verilog Block: `module picorv32 #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 62–205

```verilog
module picorv32 #(
	parameter [ 0:0] ENABLE_COUNTERS = 1,
	parameter [ 0:0] ENABLE_COUNTERS64 = 1,
	parameter [ 0:0] ENABLE_REGS_16_31 = 1,
	parameter [ 0:0] ENABLE_REGS_DUALPORT = 1,
	parameter [ 0:0] LATCHED_MEM_RDATA = 0,
	parameter [ 0:0] TWO_STAGE_SHIFT = 1,
	parameter [ 0:0] BARREL_SHIFTER = 0,
	parameter [ 0:0] TWO_CYCLE_COMPARE = 0,
	parameter [ 0:0] TWO_CYCLE_ALU = 0,
	parameter [ 0:0] COMPRESSED_ISA = 0,
	parameter [ 0:0] CATCH_MISALIGN = 1,
	parameter [ 0:0] CATCH_ILLINSN = 1,
	parameter [ 0:0] ENABLE_PCPI = 0,
	parameter [ 0:0] ENABLE_MUL = 0,
	parameter [ 0:0] ENABLE_FAST_MUL = 0,
	parameter [ 0:0] ENABLE_DIV = 0,
	parameter [ 0:0] ENABLE_IRQ = 0,
	parameter [ 0:0] ENABLE_IRQ_QREGS = 1,
	parameter [ 0:0] ENABLE_IRQ_TIMER = 1,
	parameter [ 0:0] ENABLE_TRACE = 0,
	parameter [ 0:0] REGS_INIT_ZERO = 0,
	parameter [31:0] MASKED_IRQ = 32'h 0000_0000,
	parameter [31:0] LATCHED_IRQ = 32'h ffff_ffff,
	parameter [31:0] PROGADDR_RESET = 32'h 0000_0000,
	parameter [31:0] PROGADDR_IRQ = 32'h 0000_0010,
	parameter [31:0] STACKADDR = 32'h ffff_ffff
) (
	input clk, resetn,
	output reg trap,

	output reg        mem_valid,
	output reg        mem_instr,
	input             mem_ready,

	output reg [31:0] mem_addr,
	output reg [31:0] mem_wdata,
	output reg [ 3:0] mem_wstrb,
	input      [31:0] mem_rdata,

	// Look-Ahead Interface
	output            mem_la_read,
	output            mem_la_write,
	output     [31:0] mem_la_addr,
	output reg [31:0] mem_la_wdata,
	output reg [ 3:0] mem_la_wstrb,

	// Pico Co-Processor Interface (PCPI)
	output reg        pcpi_valid,
	output reg [31:0] pcpi_insn,
	output     [31:0] pcpi_rs1,
	output     [31:0] pcpi_rs2,
	input             pcpi_wr,
	input      [31:0] pcpi_rd,
	input             pcpi_wait,
	input             pcpi_ready,

	// IRQ Interface
	input      [31:0] irq,
	output reg [31:0] eoi,

`ifdef RISCV_FORMAL
	output reg        rvfi_valid,
	output reg [63:0] rvfi_order,
	output reg [31:0] rvfi_insn,
	output reg        rvfi_trap,
	output reg        rvfi_halt,
	output reg        rvfi_intr,
	output reg [ 1:0] rvfi_mode,
	output reg [ 1:0] rvfi_ixl,
	output reg [ 4:0] rvfi_rs1_addr,
	output reg [ 4:0] rvfi_rs2_addr,
	output reg [31:0] rvfi_rs1_rdata,
	output reg [31:0] rvfi_rs2_rdata,
	output reg [ 4:0] rvfi_rd_addr,
	output reg [31:0] rvfi_rd_wdata,
	output reg [31:0] rvfi_pc_rdata,
	output reg [31:0] rvfi_pc_wdata,
	output reg [31:0] rvfi_mem_addr,
	output reg [ 3:0] rvfi_mem_rmask,
	output reg [ 3:0] rvfi_mem_wmask,
	output reg [31:0] rvfi_mem_rdata,
	output reg [31:0] rvfi_mem_wdata,

	output reg [63:0] rvfi_csr_mcycle_rmask,
	output reg [63:0] rvfi_csr_mcycle_wmask,
	output reg [63:0] rvfi_csr_mcycle_rdata,
	output reg [63:0] rvfi_csr_mcycle_wdata,

	output reg [63:0] rvfi_csr_minstret_rmask,
	output reg [63:0] rvfi_csr_minstret_wmask,
	output reg [63:0] rvfi_csr_minstret_rdata,
	output reg [63:0] rvfi_csr_minstret_wdata,
`endif

	// Trace Interface
	output reg        trace_valid,
	output reg [35:0] trace_data
);
	localparam integer irq_timer = 0;
	localparam integer irq_ebreak = 1;
	localparam integer irq_buserror = 2;

	localparam integer irqregs_offset = ENABLE_REGS_16_31 ? 32 : 16;
	localparam integer regfile_size = (ENABLE_REGS_16_31 ? 32 : 16) + 4*ENABLE_IRQ*ENABLE_IRQ_QREGS;
	localparam integer regindex_bits = (ENABLE_REGS_16_31 ? 5 : 4) + ENABLE_IRQ*ENABLE_IRQ_QREGS;

	localparam WITH_PCPI = ENABLE_PCPI || ENABLE_MUL || ENABLE_FAST_MUL || ENABLE_DIV;

	localparam [35:0] TRACE_BRANCH = {4'b 0001, 32'b 0};
	localparam [35:0] TRACE_ADDR   = {4'b 0010, 32'b 0};
	localparam [35:0] TRACE_IRQ    = {4'b 1000, 32'b 0};

	reg [63:0] count_cycle, count_instr;
	reg [31:0] reg_pc, reg_next_pc, reg_op1, reg_op2, reg_out;
	reg [4:0] reg_sh;

	reg [31:0] next_insn_opcode;
	reg [31:0] dbg_insn_opcode;
	reg [31:0] dbg_insn_addr;

	wire dbg_mem_valid = mem_valid;
	wire dbg_mem_instr = mem_instr;
	wire dbg_mem_ready = mem_ready;
	wire [31:0] dbg_mem_addr  = mem_addr;
	wire [31:0] dbg_mem_wdata = mem_wdata;
	wire [ 3:0] dbg_mem_wstrb = mem_wstrb;
	wire [31:0] dbg_mem_rdata = mem_rdata;

	assign pcpi_rs1 = reg_op1;
	assign pcpi_rs2 = reg_op2;

	wire [31:0] next_pc;

	reg irq_delay;
	reg irq_active;
	reg [31:0] irq_mask;
	reg [31:0] irq_pending;
	reg [31:0] timer;

`ifndef PICORV32_REGS
	reg [31:0] cpuregs [0:regfile_size-1];

	integer i;
```

---
<!-- chunk_id=picorv32_picorv32_10 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 206–213

```verilog
initial begin
		if (REGS_INIT_ZERO) begin
			for (i = 0; i < regfile_size; i = i+1)
				cpuregs[i] = 0;
		end
	end
`endif
```

---
<!-- chunk_id=picorv32_picorv32_11 | task empty_statement; -->

# Verilog Block: `task empty_statement;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 214–271

```verilog
task empty_statement;
		// This task is used by the `assert directive in non-formal mode to
		// avoid empty statement (which are unsupported by plain Verilog syntax).
		begin end
	endtask

`ifdef DEBUGREGS
	wire [31:0] dbg_reg_x0  = 0;
	wire [31:0] dbg_reg_x1  = cpuregs[1];
	wire [31:0] dbg_reg_x2  = cpuregs[2];
	wire [31:0] dbg_reg_x3  = cpuregs[3];
	wire [31:0] dbg_reg_x4  = cpuregs[4];
	wire [31:0] dbg_reg_x5  = cpuregs[5];
	wire [31:0] dbg_reg_x6  = cpuregs[6];
	wire [31:0] dbg_reg_x7  = cpuregs[7];
	wire [31:0] dbg_reg_x8  = cpuregs[8];
	wire [31:0] dbg_reg_x9  = cpuregs[9];
	wire [31:0] dbg_reg_x10 = cpuregs[10];
	wire [31:0] dbg_reg_x11 = cpuregs[11];
	wire [31:0] dbg_reg_x12 = cpuregs[12];
	wire [31:0] dbg_reg_x13 = cpuregs[13];
	wire [31:0] dbg_reg_x14 = cpuregs[14];
	wire [31:0] dbg_reg_x15 = cpuregs[15];
	wire [31:0] dbg_reg_x16 = cpuregs[16];
	wire [31:0] dbg_reg_x17 = cpuregs[17];
	wire [31:0] dbg_reg_x18 = cpuregs[18];
	wire [31:0] dbg_reg_x19 = cpuregs[19];
	wire [31:0] dbg_reg_x20 = cpuregs[20];
	wire [31:0] dbg_reg_x21 = cpuregs[21];
	wire [31:0] dbg_reg_x22 = cpuregs[22];
	wire [31:0] dbg_reg_x23 = cpuregs[23];
	wire [31:0] dbg_reg_x24 = cpuregs[24];
	wire [31:0] dbg_reg_x25 = cpuregs[25];
	wire [31:0] dbg_reg_x26 = cpuregs[26];
	wire [31:0] dbg_reg_x27 = cpuregs[27];
	wire [31:0] dbg_reg_x28 = cpuregs[28];
	wire [31:0] dbg_reg_x29 = cpuregs[29];
	wire [31:0] dbg_reg_x30 = cpuregs[30];
	wire [31:0] dbg_reg_x31 = cpuregs[31];
`endif

	// Internal PCPI Cores

	wire        pcpi_mul_wr;
	wire [31:0] pcpi_mul_rd;
	wire        pcpi_mul_wait;
	wire        pcpi_mul_ready;

	wire        pcpi_div_wr;
	wire [31:0] pcpi_div_rd;
	wire        pcpi_div_wait;
	wire        pcpi_div_ready;

	reg        pcpi_int_wr;
	reg [31:0] pcpi_int_rd;
	reg        pcpi_int_wait;
	reg        pcpi_int_ready;
```

---
<!-- chunk_id=picorv32_picorv32_12 | generate if (ENABLE_FAST_MUL) begin -->

# Verilog Block: `generate if (ENABLE_FAST_MUL) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 272–304

```verilog
generate if (ENABLE_FAST_MUL) begin
		picorv32_pcpi_fast_mul pcpi_mul (
			.clk       (clk            ),
			.resetn    (resetn         ),
			.pcpi_valid(pcpi_valid     ),
			.pcpi_insn (pcpi_insn      ),
			.pcpi_rs1  (pcpi_rs1       ),
			.pcpi_rs2  (pcpi_rs2       ),
			.pcpi_wr   (pcpi_mul_wr    ),
			.pcpi_rd   (pcpi_mul_rd    ),
			.pcpi_wait (pcpi_mul_wait  ),
			.pcpi_ready(pcpi_mul_ready )
		);
	end else if (ENABLE_MUL) begin
		picorv32_pcpi_mul pcpi_mul (
			.clk       (clk            ),
			.resetn    (resetn         ),
			.pcpi_valid(pcpi_valid     ),
			.pcpi_insn (pcpi_insn      ),
			.pcpi_rs1  (pcpi_rs1       ),
			.pcpi_rs2  (pcpi_rs2       ),
			.pcpi_wr   (pcpi_mul_wr    ),
			.pcpi_rd   (pcpi_mul_rd    ),
			.pcpi_wait (pcpi_mul_wait  ),
			.pcpi_ready(pcpi_mul_ready )
		);
	end else begin
		assign pcpi_mul_wr = 0;
		assign pcpi_mul_rd = 32'bx;
		assign pcpi_mul_wait = 0;
		assign pcpi_mul_ready = 0;
	end endgenerate
```

---
<!-- chunk_id=picorv32_picorv32_13 | generate if (ENABLE_DIV) begin -->

# Verilog Block: `generate if (ENABLE_DIV) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 305–324

```verilog
generate if (ENABLE_DIV) begin
		picorv32_pcpi_div pcpi_div (
			.clk       (clk            ),
			.resetn    (resetn         ),
			.pcpi_valid(pcpi_valid     ),
			.pcpi_insn (pcpi_insn      ),
			.pcpi_rs1  (pcpi_rs1       ),
			.pcpi_rs2  (pcpi_rs2       ),
			.pcpi_wr   (pcpi_div_wr    ),
			.pcpi_rd   (pcpi_div_rd    ),
			.pcpi_wait (pcpi_div_wait  ),
			.pcpi_ready(pcpi_div_ready )
		);
	end else begin
		assign pcpi_div_wr = 0;
		assign pcpi_div_rd = 32'bx;
		assign pcpi_div_wait = 0;
		assign pcpi_div_ready = 0;
	end endgenerate
```

---
<!-- chunk_id=picorv32_picorv32_14 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 325–389

```verilog
always @* begin
		pcpi_int_wr = 0;
		pcpi_int_rd = 32'bx;
		pcpi_int_wait  = |{ENABLE_PCPI && pcpi_wait,  (ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_wait,  ENABLE_DIV && pcpi_div_wait};
		pcpi_int_ready = |{ENABLE_PCPI && pcpi_ready, (ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_ready, ENABLE_DIV && pcpi_div_ready};

		(* parallel_case *)
		case (1'b1)
			ENABLE_PCPI && pcpi_ready: begin
				pcpi_int_wr = ENABLE_PCPI ? pcpi_wr : 0;
				pcpi_int_rd = ENABLE_PCPI ? pcpi_rd : 0;
			end
			(ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_ready: begin
				pcpi_int_wr = pcpi_mul_wr;
				pcpi_int_rd = pcpi_mul_rd;
			end
			ENABLE_DIV && pcpi_div_ready: begin
				pcpi_int_wr = pcpi_div_wr;
				pcpi_int_rd = pcpi_div_rd;
			end
		endcase
	end


	// Memory Interface

	reg [1:0] mem_state;
	reg [1:0] mem_wordsize;
	reg [31:0] mem_rdata_word;
	reg [31:0] mem_rdata_q;
	reg mem_do_prefetch;
	reg mem_do_rinst;
	reg mem_do_rdata;
	reg mem_do_wdata;

	wire mem_xfer;
	reg mem_la_secondword, mem_la_firstword_reg, last_mem_valid;
	wire mem_la_firstword = COMPRESSED_ISA && (mem_do_prefetch || mem_do_rinst) && next_pc[1] && !mem_la_secondword;
	wire mem_la_firstword_xfer = COMPRESSED_ISA && mem_xfer && (!last_mem_valid ? mem_la_firstword : mem_la_firstword_reg);

	reg prefetched_high_word;
	reg clear_prefetched_high_word;
	reg [15:0] mem_16bit_buffer;

	wire [31:0] mem_rdata_latched_noshuffle;
	wire [31:0] mem_rdata_latched;

	wire mem_la_use_prefetched_high_word = COMPRESSED_ISA && mem_la_firstword && prefetched_high_word && !clear_prefetched_high_word;
	assign mem_xfer = (mem_valid && mem_ready) || (mem_la_use_prefetched_high_word && mem_do_rinst);

	wire mem_busy = |{mem_do_prefetch, mem_do_rinst, mem_do_rdata, mem_do_wdata};
	wire mem_done = resetn && ((mem_xfer && |mem_state && (mem_do_rinst || mem_do_rdata || mem_do_wdata)) || (&mem_state && mem_do_rinst)) &&
			(!mem_la_firstword || (~&mem_rdata_latched[1:0] && mem_xfer));

	assign mem_la_write = resetn && !mem_state && mem_do_wdata;
	assign mem_la_read = resetn && ((!mem_la_use_prefetched_high_word && !mem_state && (mem_do_rinst || mem_do_prefetch || mem_do_rdata)) ||
			(COMPRESSED_ISA && mem_xfer && (!last_mem_valid ? mem_la_firstword : mem_la_firstword_reg) && !mem_la_secondword && &mem_rdata_latched[1:0]));
	assign mem_la_addr = (mem_do_prefetch || mem_do_rinst) ? {next_pc[31:2] + mem_la_firstword_xfer, 2'b00} : {reg_op1[31:2], 2'b00};

	assign mem_rdata_latched_noshuffle = (mem_xfer || LATCHED_MEM_RDATA) ? mem_rdata : mem_rdata_q;

	assign mem_rdata_latched = COMPRESSED_ISA && mem_la_use_prefetched_high_word ? {16'bx, mem_16bit_buffer} :
			COMPRESSED_ISA && mem_la_secondword ? {mem_rdata_latched_noshuffle[15:0], mem_16bit_buffer} :
			COMPRESSED_ISA && mem_la_firstword ? {16'bx, mem_rdata_latched_noshuffle[31:16]} : mem_rdata_latched_noshuffle;
```

---
<!-- chunk_id=picorv32_picorv32_15 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 390–400

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			mem_la_firstword_reg <= 0;
			last_mem_valid <= 0;
		end else begin
			if (!last_mem_valid)
				mem_la_firstword_reg <= mem_la_firstword;
			last_mem_valid <= mem_valid && !mem_ready;
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_16 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 401–429

```verilog
always @* begin
		(* full_case *)
		case (mem_wordsize)
			0: begin
				mem_la_wdata = reg_op2;
				mem_la_wstrb = 4'b1111;
				mem_rdata_word = mem_rdata;
			end
			1: begin
				mem_la_wdata = {2{reg_op2[15:0]}};
				mem_la_wstrb = reg_op1[1] ? 4'b1100 : 4'b0011;
				case (reg_op1[1])
					1'b0: mem_rdata_word = {16'b0, mem_rdata[15: 0]};
					1'b1: mem_rdata_word = {16'b0, mem_rdata[31:16]};
				endcase
			end
			2: begin
				mem_la_wdata = {4{reg_op2[7:0]}};
				mem_la_wstrb = 4'b0001 << reg_op1[1:0];
				case (reg_op1[1:0])
					2'b00: mem_rdata_word = {24'b0, mem_rdata[ 7: 0]};
					2'b01: mem_rdata_word = {24'b0, mem_rdata[15: 8]};
					2'b10: mem_rdata_word = {24'b0, mem_rdata[23:16]};
					2'b11: mem_rdata_word = {24'b0, mem_rdata[31:24]};
				endcase
			end
		endcase
	end
```

---
<!-- chunk_id=picorv32_picorv32_17 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 430–545

```verilog
always @(posedge clk) begin
		if (mem_xfer) begin
			mem_rdata_q <= COMPRESSED_ISA ? mem_rdata_latched : mem_rdata;
			next_insn_opcode <= COMPRESSED_ISA ? mem_rdata_latched : mem_rdata;
		end

		if (COMPRESSED_ISA && mem_done && (mem_do_prefetch || mem_do_rinst)) begin
			case (mem_rdata_latched[1:0])
				2'b00: begin // Quadrant 0
					case (mem_rdata_latched[15:13])
						3'b000: begin // C.ADDI4SPN
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= {2'b0, mem_rdata_latched[10:7], mem_rdata_latched[12:11], mem_rdata_latched[5], mem_rdata_latched[6], 2'b00};
						end
						3'b010: begin // C.LW
							mem_rdata_q[31:20] <= {5'b0, mem_rdata_latched[5], mem_rdata_latched[12:10], mem_rdata_latched[6], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
						3'b 110: begin // C.SW
							{mem_rdata_q[31:25], mem_rdata_q[11:7]} <= {5'b0, mem_rdata_latched[5], mem_rdata_latched[12:10], mem_rdata_latched[6], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
					endcase
				end
				2'b01: begin // Quadrant 1
					case (mem_rdata_latched[15:13])
						3'b 000: begin // C.ADDI
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
						end
						3'b 010: begin // C.LI
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
						end
						3'b 011: begin
							if (mem_rdata_latched[11:7] == 2) begin // C.ADDI16SP
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[4:3],
										mem_rdata_latched[5], mem_rdata_latched[2], mem_rdata_latched[6], 4'b 0000});
							end else begin // C.LUI
								mem_rdata_q[31:12] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
							end
						end
						3'b100: begin
							if (mem_rdata_latched[11:10] == 2'b00) begin // C.SRLI
								mem_rdata_q[31:25] <= 7'b0000000;
								mem_rdata_q[14:12] <= 3'b 101;
							end
							if (mem_rdata_latched[11:10] == 2'b01) begin // C.SRAI
								mem_rdata_q[31:25] <= 7'b0100000;
								mem_rdata_q[14:12] <= 3'b 101;
							end
							if (mem_rdata_latched[11:10] == 2'b10) begin // C.ANDI
								mem_rdata_q[14:12] <= 3'b111;
								mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
							end
							if (mem_rdata_latched[12:10] == 3'b011) begin // C.SUB, C.XOR, C.OR, C.AND
								if (mem_rdata_latched[6:5] == 2'b00) mem_rdata_q[14:12] <= 3'b000;
								if (mem_rdata_latched[6:5] == 2'b01) mem_rdata_q[14:12] <= 3'b100;
								if (mem_rdata_latched[6:5] == 2'b10) mem_rdata_q[14:12] <= 3'b110;
								if (mem_rdata_latched[6:5] == 2'b11) mem_rdata_q[14:12] <= 3'b111;
								mem_rdata_q[31:25] <= mem_rdata_latched[6:5] == 2'b00 ? 7'b0100000 : 7'b0000000;
							end
						end
						3'b 110: begin // C.BEQZ
							mem_rdata_q[14:12] <= 3'b000;
							{ mem_rdata_q[31], mem_rdata_q[7], mem_rdata_q[30:25], mem_rdata_q[11:8] } <=
									$signed({mem_rdata_latched[12], mem_rdata_latched[6:5], mem_rdata_latched[2],
											mem_rdata_latched[11:10], mem_rdata_latched[4:3]});
						end
						3'b 111: begin // C.BNEZ
							mem_rdata_q[14:12] <= 3'b001;
							{ mem_rdata_q[31], mem_rdata_q[7], mem_rdata_q[30:25], mem_rdata_q[11:8] } <=
									$signed({mem_rdata_latched[12], mem_rdata_latched[6:5], mem_rdata_latched[2],
											mem_rdata_latched[11:10], mem_rdata_latched[4:3]});
						end
					endcase
				end
				2'b10: begin // Quadrant 2
					case (mem_rdata_latched[15:13])
						3'b000: begin // C.SLLI
							mem_rdata_q[31:25] <= 7'b0000000;
							mem_rdata_q[14:12] <= 3'b 001;
						end
						3'b010: begin // C.LWSP
							mem_rdata_q[31:20] <= {4'b0, mem_rdata_latched[3:2], mem_rdata_latched[12], mem_rdata_latched[6:4], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
						3'b100: begin
							if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] == 0) begin // C.JR
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= 12'b0;
							end
							if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] != 0) begin // C.MV
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:25] <= 7'b0000000;
							end
							if (mem_rdata_latched[12] != 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JALR
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= 12'b0;
							end
							if (mem_rdata_latched[12] != 0 && mem_rdata_latched[6:2] != 0) begin // C.ADD
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:25] <= 7'b0000000;
							end
						end
						3'b110: begin // C.SWSP
							{mem_rdata_q[31:25], mem_rdata_q[11:7]} <= {4'b0, mem_rdata_latched[8:7], mem_rdata_latched[12:9], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
					endcase
				end
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_18 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 546–564

```verilog
always @(posedge clk) begin
		if (resetn && !trap) begin
			if (mem_do_prefetch || mem_do_rinst || mem_do_rdata)
				`assert(!mem_do_wdata);

			if (mem_do_prefetch || mem_do_rinst)
				`assert(!mem_do_rdata);

			if (mem_do_rdata)
				`assert(!mem_do_prefetch && !mem_do_rinst);

			if (mem_do_wdata)
				`assert(!(mem_do_prefetch || mem_do_rinst || mem_do_rdata));

			if (mem_state == 2 || mem_state == 3)
				`assert(mem_valid || mem_do_prefetch);
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_19 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 565–700

```verilog
always @(posedge clk) begin
		if (!resetn || trap) begin
			if (!resetn)
				mem_state <= 0;
			if (!resetn || mem_ready)
				mem_valid <= 0;
			mem_la_secondword <= 0;
			prefetched_high_word <= 0;
		end else begin
			if (mem_la_read || mem_la_write) begin
				mem_addr <= mem_la_addr;
				mem_wstrb <= mem_la_wstrb & {4{mem_la_write}};
			end
			if (mem_la_write) begin
				mem_wdata <= mem_la_wdata;
			end
			case (mem_state)
				0: begin
					if (mem_do_prefetch || mem_do_rinst || mem_do_rdata) begin
						mem_valid <= !mem_la_use_prefetched_high_word;
						mem_instr <= mem_do_prefetch || mem_do_rinst;
						mem_wstrb <= 0;
						mem_state <= 1;
					end
					if (mem_do_wdata) begin
						mem_valid <= 1;
						mem_instr <= 0;
						mem_state <= 2;
					end
				end
				1: begin
					`assert(mem_wstrb == 0);
					`assert(mem_do_prefetch || mem_do_rinst || mem_do_rdata);
					`assert(mem_valid == !mem_la_use_prefetched_high_word);
					`assert(mem_instr == (mem_do_prefetch || mem_do_rinst));
					if (mem_xfer) begin
						if (COMPRESSED_ISA && mem_la_read) begin
							mem_valid <= 1;
							mem_la_secondword <= 1;
							if (!mem_la_use_prefetched_high_word)
								mem_16bit_buffer <= mem_rdata[31:16];
						end else begin
							mem_valid <= 0;
							mem_la_secondword <= 0;
							if (COMPRESSED_ISA && !mem_do_rdata) begin
								if (~&mem_rdata[1:0] || mem_la_secondword) begin
									mem_16bit_buffer <= mem_rdata[31:16];
									prefetched_high_word <= 1;
								end else begin
									prefetched_high_word <= 0;
								end
							end
							mem_state <= mem_do_rinst || mem_do_rdata ? 0 : 3;
						end
					end
				end
				2: begin
					`assert(mem_wstrb != 0);
					`assert(mem_do_wdata);
					if (mem_xfer) begin
						mem_valid <= 0;
						mem_state <= 0;
					end
				end
				3: begin
					`assert(mem_wstrb == 0);
					`assert(mem_do_prefetch);
					if (mem_do_rinst) begin
						mem_state <= 0;
					end
				end
			endcase
		end

		if (clear_prefetched_high_word)
			prefetched_high_word <= 0;
	end


	// Instruction Decoder

	reg instr_lui, instr_auipc, instr_jal, instr_jalr;
	reg instr_beq, instr_bne, instr_blt, instr_bge, instr_bltu, instr_bgeu;
	reg instr_lb, instr_lh, instr_lw, instr_lbu, instr_lhu, instr_sb, instr_sh, instr_sw;
	reg instr_addi, instr_slti, instr_sltiu, instr_xori, instr_ori, instr_andi, instr_slli, instr_srli, instr_srai;
	reg instr_add, instr_sub, instr_sll, instr_slt, instr_sltu, instr_xor, instr_srl, instr_sra, instr_or, instr_and;
	reg instr_rdcycle, instr_rdcycleh, instr_rdinstr, instr_rdinstrh, instr_ecall_ebreak, instr_fence;
	reg instr_getq, instr_setq, instr_retirq, instr_maskirq, instr_waitirq, instr_timer;
	wire instr_trap;

	reg [regindex_bits-1:0] decoded_rd, decoded_rs1;
	reg [4:0] decoded_rs2;
	reg [31:0] decoded_imm, decoded_imm_j;
	reg decoder_trigger;
	reg decoder_trigger_q;
	reg decoder_pseudo_trigger;
	reg decoder_pseudo_trigger_q;
	reg compressed_instr;

	reg is_lui_auipc_jal;
	reg is_lb_lh_lw_lbu_lhu;
	reg is_slli_srli_srai;
	reg is_jalr_addi_slti_sltiu_xori_ori_andi;
	reg is_sb_sh_sw;
	reg is_sll_srl_sra;
	reg is_lui_auipc_jal_jalr_addi_add_sub;
	reg is_slti_blt_slt;
	reg is_sltiu_bltu_sltu;
	reg is_beq_bne_blt_bge_bltu_bgeu;
	reg is_lbu_lhu_lw;
	reg is_alu_reg_imm;
	reg is_alu_reg_reg;
	reg is_compare;

	assign instr_trap = (CATCH_ILLINSN || WITH_PCPI) && !{instr_lui, instr_auipc, instr_jal, instr_jalr,
			instr_beq, instr_bne, instr_blt, instr_bge, instr_bltu, instr_bgeu,
			instr_lb, instr_lh, instr_lw, instr_lbu, instr_lhu, instr_sb, instr_sh, instr_sw,
			instr_addi, instr_slti, instr_sltiu, instr_xori, instr_ori, instr_andi, instr_slli, instr_srli, instr_srai,
			instr_add, instr_sub, instr_sll, instr_slt, instr_sltu, instr_xor, instr_srl, instr_sra, instr_or, instr_and,
			instr_rdcycle, instr_rdcycleh, instr_rdinstr, instr_rdinstrh, instr_fence,
			instr_getq, instr_setq, instr_retirq, instr_maskirq, instr_waitirq, instr_timer};

	wire is_rdcycle_rdcycleh_rdinstr_rdinstrh;
	assign is_rdcycle_rdcycleh_rdinstr_rdinstrh = |{instr_rdcycle, instr_rdcycleh, instr_rdinstr, instr_rdinstrh};

	reg [63:0] new_ascii_instr;
	`FORMAL_KEEP reg [63:0] dbg_ascii_instr;
	`FORMAL_KEEP reg [31:0] dbg_insn_imm;
	`FORMAL_KEEP reg [4:0] dbg_insn_rs1;
	`FORMAL_KEEP reg [4:0] dbg_insn_rs2;
	`FORMAL_KEEP reg [4:0] dbg_insn_rd;
	`FORMAL_KEEP reg [31:0] dbg_rs1val;
	`FORMAL_KEEP reg [31:0] dbg_rs2val;
	`FORMAL_KEEP reg dbg_rs1val_valid;
	`FORMAL_KEEP reg dbg_rs2val_valid;
```

---
<!-- chunk_id=picorv32_picorv32_20 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 701–777

```verilog
always @* begin
		new_ascii_instr = "";

		if (instr_lui)      new_ascii_instr = "lui";
		if (instr_auipc)    new_ascii_instr = "auipc";
		if (instr_jal)      new_ascii_instr = "jal";
		if (instr_jalr)     new_ascii_instr = "jalr";

		if (instr_beq)      new_ascii_instr = "beq";
		if (instr_bne)      new_ascii_instr = "bne";
		if (instr_blt)      new_ascii_instr = "blt";
		if (instr_bge)      new_ascii_instr = "bge";
		if (instr_bltu)     new_ascii_instr = "bltu";
		if (instr_bgeu)     new_ascii_instr = "bgeu";

		if (instr_lb)       new_ascii_instr = "lb";
		if (instr_lh)       new_ascii_instr = "lh";
		if (instr_lw)       new_ascii_instr = "lw";
		if (instr_lbu)      new_ascii_instr = "lbu";
		if (instr_lhu)      new_ascii_instr = "lhu";
		if (instr_sb)       new_ascii_instr = "sb";
		if (instr_sh)       new_ascii_instr = "sh";
		if (instr_sw)       new_ascii_instr = "sw";

		if (instr_addi)     new_ascii_instr = "addi";
		if (instr_slti)     new_ascii_instr = "slti";
		if (instr_sltiu)    new_ascii_instr = "sltiu";
		if (instr_xori)     new_ascii_instr = "xori";
		if (instr_ori)      new_ascii_instr = "ori";
		if (instr_andi)     new_ascii_instr = "andi";
		if (instr_slli)     new_ascii_instr = "slli";
		if (instr_srli)     new_ascii_instr = "srli";
		if (instr_srai)     new_ascii_instr = "srai";

		if (instr_add)      new_ascii_instr = "add";
		if (instr_sub)      new_ascii_instr = "sub";
		if (instr_sll)      new_ascii_instr = "sll";
		if (instr_slt)      new_ascii_instr = "slt";
		if (instr_sltu)     new_ascii_instr = "sltu";
		if (instr_xor)      new_ascii_instr = "xor";
		if (instr_srl)      new_ascii_instr = "srl";
		if (instr_sra)      new_ascii_instr = "sra";
		if (instr_or)       new_ascii_instr = "or";
		if (instr_and)      new_ascii_instr = "and";

		if (instr_rdcycle)  new_ascii_instr = "rdcycle";
		if (instr_rdcycleh) new_ascii_instr = "rdcycleh";
		if (instr_rdinstr)  new_ascii_instr = "rdinstr";
		if (instr_rdinstrh) new_ascii_instr = "rdinstrh";
		if (instr_fence)    new_ascii_instr = "fence";

		if (instr_getq)     new_ascii_instr = "getq";
		if (instr_setq)     new_ascii_instr = "setq";
		if (instr_retirq)   new_ascii_instr = "retirq";
		if (instr_maskirq)  new_ascii_instr = "maskirq";
		if (instr_waitirq)  new_ascii_instr = "waitirq";
		if (instr_timer)    new_ascii_instr = "timer";
	end

	reg [63:0] q_ascii_instr;
	reg [31:0] q_insn_imm;
	reg [31:0] q_insn_opcode;
	reg [4:0] q_insn_rs1;
	reg [4:0] q_insn_rs2;
	reg [4:0] q_insn_rd;
	reg dbg_next;

	wire launch_next_insn;
	reg dbg_valid_insn;

	reg [63:0] cached_ascii_instr;
	reg [31:0] cached_insn_imm;
	reg [31:0] cached_insn_opcode;
	reg [4:0] cached_insn_rs1;
	reg [4:0] cached_insn_rs2;
	reg [4:0] cached_insn_rd;
```

---
<!-- chunk_id=picorv32_picorv32_21 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 778–808

```verilog
always @(posedge clk) begin
		q_ascii_instr <= dbg_ascii_instr;
		q_insn_imm <= dbg_insn_imm;
		q_insn_opcode <= dbg_insn_opcode;
		q_insn_rs1 <= dbg_insn_rs1;
		q_insn_rs2 <= dbg_insn_rs2;
		q_insn_rd <= dbg_insn_rd;
		dbg_next <= launch_next_insn;

		if (!resetn || trap)
			dbg_valid_insn <= 0;
		else if (launch_next_insn)
			dbg_valid_insn <= 1;

		if (decoder_trigger_q) begin
			cached_ascii_instr <= new_ascii_instr;
			cached_insn_imm <= decoded_imm;
			if (&next_insn_opcode[1:0])
				cached_insn_opcode <= next_insn_opcode;
			else
				cached_insn_opcode <= {16'b0, next_insn_opcode[15:0]};
			cached_insn_rs1 <= decoded_rs1;
			cached_insn_rs2 <= decoded_rs2;
			cached_insn_rd <= decoded_rd;
		end

		if (launch_next_insn) begin
			dbg_insn_addr <= next_pc;
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_22 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 809–839

```verilog
always @* begin
		dbg_ascii_instr = q_ascii_instr;
		dbg_insn_imm = q_insn_imm;
		dbg_insn_opcode = q_insn_opcode;
		dbg_insn_rs1 = q_insn_rs1;
		dbg_insn_rs2 = q_insn_rs2;
		dbg_insn_rd = q_insn_rd;

		if (dbg_next) begin
			if (decoder_pseudo_trigger_q) begin
				dbg_ascii_instr = cached_ascii_instr;
				dbg_insn_imm = cached_insn_imm;
				dbg_insn_opcode = cached_insn_opcode;
				dbg_insn_rs1 = cached_insn_rs1;
				dbg_insn_rs2 = cached_insn_rs2;
				dbg_insn_rd = cached_insn_rd;
			end else begin
				dbg_ascii_instr = new_ascii_instr;
				if (&next_insn_opcode[1:0])
					dbg_insn_opcode = next_insn_opcode;
				else
					dbg_insn_opcode = {16'b0, next_insn_opcode[15:0]};
				dbg_insn_imm = decoded_imm;
				dbg_insn_rs1 = decoded_rs1;
				dbg_insn_rs2 = decoded_rs2;
				dbg_insn_rd = decoded_rd;
			end
		end
	end

`ifdef DEBUGASM
```

---
<!-- chunk_id=picorv32_picorv32_23 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 840–847

```verilog
always @(posedge clk) begin
		if (dbg_next) begin
			$display("debugasm %x %x %s", dbg_insn_addr, dbg_insn_opcode, dbg_ascii_instr ? dbg_ascii_instr : "*");
		end
	end
`endif

`ifdef DEBUG
```

---
<!-- chunk_id=picorv32_picorv32_24 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 848–857

```verilog
always @(posedge clk) begin
		if (dbg_next) begin
			if (&dbg_insn_opcode[1:0])
				$display("DECODE: 0x%08x 0x%08x %-0s", dbg_insn_addr, dbg_insn_opcode, dbg_ascii_instr ? dbg_ascii_instr : "UNKNOWN");
			else
				$display("DECODE: 0x%08x     0x%04x %-0s", dbg_insn_addr, dbg_insn_opcode[15:0], dbg_ascii_instr ? dbg_ascii_instr : "UNKNOWN");
		end
	end
`endif
```

---
<!-- chunk_id=picorv32_picorv32_25 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 858–1185

```verilog
always @(posedge clk) begin
		is_lui_auipc_jal <= |{instr_lui, instr_auipc, instr_jal};
		is_lui_auipc_jal_jalr_addi_add_sub <= |{instr_lui, instr_auipc, instr_jal, instr_jalr, instr_addi, instr_add, instr_sub};
		is_slti_blt_slt <= |{instr_slti, instr_blt, instr_slt};
		is_sltiu_bltu_sltu <= |{instr_sltiu, instr_bltu, instr_sltu};
		is_lbu_lhu_lw <= |{instr_lbu, instr_lhu, instr_lw};
		is_compare <= |{is_beq_bne_blt_bge_bltu_bgeu, instr_slti, instr_slt, instr_sltiu, instr_sltu};

		if (mem_do_rinst && mem_done) begin
			instr_lui     <= mem_rdata_latched[6:0] == 7'b0110111;
			instr_auipc   <= mem_rdata_latched[6:0] == 7'b0010111;
			instr_jal     <= mem_rdata_latched[6:0] == 7'b1101111;
			instr_jalr    <= mem_rdata_latched[6:0] == 7'b1100111 && mem_rdata_latched[14:12] == 3'b000;
			instr_retirq  <= mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000010 && ENABLE_IRQ;
			instr_waitirq <= mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000100 && ENABLE_IRQ;

			is_beq_bne_blt_bge_bltu_bgeu <= mem_rdata_latched[6:0] == 7'b1100011;
			is_lb_lh_lw_lbu_lhu          <= mem_rdata_latched[6:0] == 7'b0000011;
			is_sb_sh_sw                  <= mem_rdata_latched[6:0] == 7'b0100011;
			is_alu_reg_imm               <= mem_rdata_latched[6:0] == 7'b0010011;
			is_alu_reg_reg               <= mem_rdata_latched[6:0] == 7'b0110011;

			{ decoded_imm_j[31:20], decoded_imm_j[10:1], decoded_imm_j[11], decoded_imm_j[19:12], decoded_imm_j[0] } <= $signed({mem_rdata_latched[31:12], 1'b0});

			decoded_rd <= mem_rdata_latched[11:7];
			decoded_rs1 <= mem_rdata_latched[19:15];
			decoded_rs2 <= mem_rdata_latched[24:20];

			if (mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000000 && ENABLE_IRQ && ENABLE_IRQ_QREGS)
				decoded_rs1[regindex_bits-1] <= 1; // instr_getq

			if (mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000010 && ENABLE_IRQ)
				decoded_rs1 <= ENABLE_IRQ_QREGS ? irqregs_offset : 3; // instr_retirq

			compressed_instr <= 0;
			if (COMPRESSED_ISA && mem_rdata_latched[1:0] != 2'b11) begin
				compressed_instr <= 1;
				decoded_rd <= 0;
				decoded_rs1 <= 0;
				decoded_rs2 <= 0;

				{ decoded_imm_j[31:11], decoded_imm_j[4], decoded_imm_j[9:8], decoded_imm_j[10], decoded_imm_j[6],
				  decoded_imm_j[7], decoded_imm_j[3:1], decoded_imm_j[5], decoded_imm_j[0] } <= $signed({mem_rdata_latched[12:2], 1'b0});

				case (mem_rdata_latched[1:0])
					2'b00: begin // Quadrant 0
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.ADDI4SPN
								is_alu_reg_imm <= |mem_rdata_latched[12:5];
								decoded_rs1 <= 2;
								decoded_rd <= 8 + mem_rdata_latched[4:2];
							end
							3'b010: begin // C.LW
								is_lb_lh_lw_lbu_lhu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rd <= 8 + mem_rdata_latched[4:2];
							end
							3'b110: begin // C.SW
								is_sb_sh_sw <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 8 + mem_rdata_latched[4:2];
							end
						endcase
					end
					2'b01: begin // Quadrant 1
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.NOP / C.ADDI
								is_alu_reg_imm <= 1;
								decoded_rd <= mem_rdata_latched[11:7];
								decoded_rs1 <= mem_rdata_latched[11:7];
							end
							3'b001: begin // C.JAL
								instr_jal <= 1;
								decoded_rd <= 1;
							end
							3'b 010: begin // C.LI
								is_alu_reg_imm <= 1;
								decoded_rd <= mem_rdata_latched[11:7];
								decoded_rs1 <= 0;
							end
							3'b 011: begin
								if (mem_rdata_latched[12] || mem_rdata_latched[6:2]) begin
									if (mem_rdata_latched[11:7] == 2) begin // C.ADDI16SP
										is_alu_reg_imm <= 1;
										decoded_rd <= mem_rdata_latched[11:7];
										decoded_rs1 <= mem_rdata_latched[11:7];
									end else begin // C.LUI
										instr_lui <= 1;
										decoded_rd <= mem_rdata_latched[11:7];
										decoded_rs1 <= 0;
									end
								end
							end
							3'b100: begin
								if (!mem_rdata_latched[11] && !mem_rdata_latched[12]) begin // C.SRLI, C.SRAI
									is_alu_reg_imm <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
									decoded_rs2 <= {mem_rdata_latched[12], mem_rdata_latched[6:2]};
								end
								if (mem_rdata_latched[11:10] == 2'b10) begin // C.ANDI
									is_alu_reg_imm <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								end
								if (mem_rdata_latched[12:10] == 3'b011) begin // C.SUB, C.XOR, C.OR, C.AND
									is_alu_reg_reg <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
									decoded_rs2 <= 8 + mem_rdata_latched[4:2];
								end
							end
							3'b101: begin // C.J
								instr_jal <= 1;
							end
							3'b110: begin // C.BEQZ
								is_beq_bne_blt_bge_bltu_bgeu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 0;
							end
							3'b111: begin // C.BNEZ
								is_beq_bne_blt_bge_bltu_bgeu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 0;
							end
						endcase
					end
					2'b10: begin // Quadrant 2
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.SLLI
								if (!mem_rdata_latched[12]) begin
									is_alu_reg_imm <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= mem_rdata_latched[11:7];
									decoded_rs2 <= {mem_rdata_latched[12], mem_rdata_latched[6:2]};
								end
							end
							3'b010: begin // C.LWSP
								if (mem_rdata_latched[11:7]) begin
									is_lb_lh_lw_lbu_lhu <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= 2;
								end
							end
							3'b100: begin
								if (mem_rdata_latched[12] == 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JR
									instr_jalr <= 1;
									decoded_rd <= 0;
									decoded_rs1 <= mem_rdata_latched[11:7];
								end
								if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] != 0) begin // C.MV
									is_alu_reg_reg <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= 0;
									decoded_rs2 <= mem_rdata_latched[6:2];
								end
								if (mem_rdata_latched[12] != 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JALR
									instr_jalr <= 1;
									decoded_rd <= 1;
									decoded_rs1 <= mem_rdata_latched[11:7];
								end
								if (mem_rdata_latched[12] != 0 && mem_rdata_latched[6:2] != 0) begin // C.ADD
									is_alu_reg_reg <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= mem_rdata_latched[11:7];
									decoded_rs2 <= mem_rdata_latched[6:2];
								end
							end
							3'b110: begin // C.SWSP
								is_sb_sh_sw <= 1;
								decoded_rs1 <= 2;
								decoded_rs2 <= mem_rdata_latched[6:2];
							end
						endcase
					end
				endcase
			end
		end

		if (decoder_trigger && !decoder_pseudo_trigger) begin
			pcpi_insn <= WITH_PCPI ? mem_rdata_q : 'bx;

			instr_beq   <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b000;
			instr_bne   <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b001;
			instr_blt   <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b100;
			instr_bge   <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b101;
			instr_bltu  <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b110;
			instr_bgeu  <= is_beq_bne_blt_bge_bltu_bgeu && mem_rdata_q[14:12] == 3'b111;

			instr_lb    <= is_lb_lh_lw_lbu_lhu && mem_rdata_q[14:12] == 3'b000;
			instr_lh    <= is_lb_lh_lw_lbu_lhu && mem_rdata_q[14:12] == 3'b001;
			instr_lw    <= is_lb_lh_lw_lbu_lhu && mem_rdata_q[14:12] == 3'b010;
			instr_lbu   <= is_lb_lh_lw_lbu_lhu && mem_rdata_q[14:12] == 3'b100;
			instr_lhu   <= is_lb_lh_lw_lbu_lhu && mem_rdata_q[14:12] == 3'b101;

			instr_sb    <= is_sb_sh_sw && mem_rdata_q[14:12] == 3'b000;
			instr_sh    <= is_sb_sh_sw && mem_rdata_q[14:12] == 3'b001;
			instr_sw    <= is_sb_sh_sw && mem_rdata_q[14:12] == 3'b010;

			instr_addi  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b000;
			instr_slti  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b010;
			instr_sltiu <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b011;
			instr_xori  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b100;
			instr_ori   <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b110;
			instr_andi  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b111;

			instr_slli  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b001 && mem_rdata_q[31:25] == 7'b0000000;
			instr_srli  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0000000;
			instr_srai  <= is_alu_reg_imm && mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0100000;

			instr_add   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b000 && mem_rdata_q[31:25] == 7'b0000000;
			instr_sub   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b000 && mem_rdata_q[31:25] == 7'b0100000;
			instr_sll   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b001 && mem_rdata_q[31:25] == 7'b0000000;
			instr_slt   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b010 && mem_rdata_q[31:25] == 7'b0000000;
			instr_sltu  <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b011 && mem_rdata_q[31:25] == 7'b0000000;
			instr_xor   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b100 && mem_rdata_q[31:25] == 7'b0000000;
			instr_srl   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0000000;
			instr_sra   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0100000;
			instr_or    <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b110 && mem_rdata_q[31:25] == 7'b0000000;
			instr_and   <= is_alu_reg_reg && mem_rdata_q[14:12] == 3'b111 && mem_rdata_q[31:25] == 7'b0000000;

			instr_rdcycle  <= ((mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11000000000000000010) ||
			                   (mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11000000000100000010)) && ENABLE_COUNTERS;
			instr_rdcycleh <= ((mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11001000000000000010) ||
			                   (mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11001000000100000010)) && ENABLE_COUNTERS && ENABLE_COUNTERS64;
			instr_rdinstr  <=  (mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11000000001000000010) && ENABLE_COUNTERS;
			instr_rdinstrh <=  (mem_rdata_q[6:0] == 7'b1110011 && mem_rdata_q[31:12] == 'b11001000001000000010) && ENABLE_COUNTERS && ENABLE_COUNTERS64;

			instr_ecall_ebreak <= ((mem_rdata_q[6:0] == 7'b1110011 && !mem_rdata_q[31:21] && !mem_rdata_q[19:7]) ||
					(COMPRESSED_ISA && mem_rdata_q[15:0] == 16'h9002));
			instr_fence <= (mem_rdata_q[6:0] == 7'b0001111 && !mem_rdata_q[14:12]);

			instr_getq    <= mem_rdata_q[6:0] == 7'b0001011 && mem_rdata_q[31:25] == 7'b0000000 && ENABLE_IRQ && ENABLE_IRQ_QREGS;
			instr_setq    <= mem_rdata_q[6:0] == 7'b0001011 && mem_rdata_q[31:25] == 7'b0000001 && ENABLE_IRQ && ENABLE_IRQ_QREGS;
			instr_maskirq <= mem_rdata_q[6:0] == 7'b0001011 && mem_rdata_q[31:25] == 7'b0000011 && ENABLE_IRQ;
			instr_timer   <= mem_rdata_q[6:0] == 7'b0001011 && mem_rdata_q[31:25] == 7'b0000101 && ENABLE_IRQ && ENABLE_IRQ_TIMER;

			is_slli_srli_srai <= is_alu_reg_imm && |{
				mem_rdata_q[14:12] == 3'b001 && mem_rdata_q[31:25] == 7'b0000000,
				mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0000000,
				mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0100000
			};

			is_jalr_addi_slti_sltiu_xori_ori_andi <= instr_jalr || is_alu_reg_imm && |{
				mem_rdata_q[14:12] == 3'b000,
				mem_rdata_q[14:12] == 3'b010,
				mem_rdata_q[14:12] == 3'b011,
				mem_rdata_q[14:12] == 3'b100,
				mem_rdata_q[14:12] == 3'b110,
				mem_rdata_q[14:12] == 3'b111
			};

			is_sll_srl_sra <= is_alu_reg_reg && |{
				mem_rdata_q[14:12] == 3'b001 && mem_rdata_q[31:25] == 7'b0000000,
				mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0000000,
				mem_rdata_q[14:12] == 3'b101 && mem_rdata_q[31:25] == 7'b0100000
			};

			is_lui_auipc_jal_jalr_addi_add_sub <= 0;
			is_compare <= 0;

			(* parallel_case *)
			case (1'b1)
				instr_jal:
					decoded_imm <= decoded_imm_j;
				|{instr_lui, instr_auipc}:
					decoded_imm <= mem_rdata_q[31:12] << 12;
				|{instr_jalr, is_lb_lh_lw_lbu_lhu, is_alu_reg_imm}:
					decoded_imm <= $signed(mem_rdata_q[31:20]);
				is_beq_bne_blt_bge_bltu_bgeu:
					decoded_imm <= $signed({mem_rdata_q[31], mem_rdata_q[7], mem_rdata_q[30:25], mem_rdata_q[11:8], 1'b0});
				is_sb_sh_sw:
					decoded_imm <= $signed({mem_rdata_q[31:25], mem_rdata_q[11:7]});
				default:
					decoded_imm <= 1'bx;
			endcase
		end

		if (!resetn) begin
			is_beq_bne_blt_bge_bltu_bgeu <= 0;
			is_compare <= 0;

			instr_beq   <= 0;
			instr_bne   <= 0;
			instr_blt   <= 0;
			instr_bge   <= 0;
			instr_bltu  <= 0;
			instr_bgeu  <= 0;

			instr_addi  <= 0;
			instr_slti  <= 0;
			instr_sltiu <= 0;
			instr_xori  <= 0;
			instr_ori   <= 0;
			instr_andi  <= 0;

			instr_add   <= 0;
			instr_sub   <= 0;
			instr_sll   <= 0;
			instr_slt   <= 0;
			instr_sltu  <= 0;
			instr_xor   <= 0;
			instr_srl   <= 0;
			instr_sra   <= 0;
			instr_or    <= 0;
			instr_and   <= 0;

			instr_fence <= 0;
		end
	end


	// Main State Machine

	localparam cpu_state_trap   = 8'b10000000;
	localparam cpu_state_fetch  = 8'b01000000;
	localparam cpu_state_ld_rs1 = 8'b00100000;
	localparam cpu_state_ld_rs2 = 8'b00010000;
	localparam cpu_state_exec   = 8'b00001000;
	localparam cpu_state_shift  = 8'b00000100;
	localparam cpu_state_stmem  = 8'b00000010;
	localparam cpu_state_ldmem  = 8'b00000001;

	reg [7:0] cpu_state;
	reg [1:0] irq_state;

	`FORMAL_KEEP reg [127:0] dbg_ascii_state;
```

---
<!-- chunk_id=picorv32_picorv32_26 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1186–1228

```verilog
always @* begin
		dbg_ascii_state = "";
		if (cpu_state == cpu_state_trap)   dbg_ascii_state = "trap";
		if (cpu_state == cpu_state_fetch)  dbg_ascii_state = "fetch";
		if (cpu_state == cpu_state_ld_rs1) dbg_ascii_state = "ld_rs1";
		if (cpu_state == cpu_state_ld_rs2) dbg_ascii_state = "ld_rs2";
		if (cpu_state == cpu_state_exec)   dbg_ascii_state = "exec";
		if (cpu_state == cpu_state_shift)  dbg_ascii_state = "shift";
		if (cpu_state == cpu_state_stmem)  dbg_ascii_state = "stmem";
		if (cpu_state == cpu_state_ldmem)  dbg_ascii_state = "ldmem";
	end

	reg set_mem_do_rinst;
	reg set_mem_do_rdata;
	reg set_mem_do_wdata;

	reg latched_store;
	reg latched_stalu;
	reg latched_branch;
	reg latched_compr;
	reg latched_trace;
	reg latched_is_lu;
	reg latched_is_lh;
	reg latched_is_lb;
	reg [regindex_bits-1:0] latched_rd;

	reg [31:0] current_pc;
	assign next_pc = latched_store && latched_branch ? reg_out & ~1 : reg_next_pc;

	reg [3:0] pcpi_timeout_counter;
	reg pcpi_timeout;

	reg [31:0] next_irq_pending;
	reg do_waitirq;

	reg [31:0] alu_out, alu_out_q;
	reg alu_out_0, alu_out_0_q;
	reg alu_wait, alu_wait_2;

	reg [31:0] alu_add_sub;
	reg [31:0] alu_shl, alu_shr;
	reg alu_eq, alu_ltu, alu_lts;
```

---
<!-- chunk_id=picorv32_picorv32_27 | generate if (TWO_CYCLE_ALU) begin -->

# Verilog Block: `generate if (TWO_CYCLE_ALU) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1229–1229

```verilog
generate if (TWO_CYCLE_ALU) begin
```

---
<!-- chunk_id=picorv32_picorv32_28 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1230–1238

```verilog
always @(posedge clk) begin
			alu_add_sub <= instr_sub ? reg_op1 - reg_op2 : reg_op1 + reg_op2;
			alu_eq <= reg_op1 == reg_op2;
			alu_lts <= $signed(reg_op1) < $signed(reg_op2);
			alu_ltu <= reg_op1 < reg_op2;
			alu_shl <= reg_op1 << reg_op2[4:0];
			alu_shr <= $signed({instr_sra || instr_srai ? reg_op1[31] : 1'b0, reg_op1}) >>> reg_op2[4:0];
		end
	end else begin
```

---
<!-- chunk_id=picorv32_picorv32_29 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1239–1248

```verilog
always @* begin
			alu_add_sub = instr_sub ? reg_op1 - reg_op2 : reg_op1 + reg_op2;
			alu_eq = reg_op1 == reg_op2;
			alu_lts = $signed(reg_op1) < $signed(reg_op2);
			alu_ltu = reg_op1 < reg_op2;
			alu_shl = reg_op1 << reg_op2[4:0];
			alu_shr = $signed({instr_sra || instr_srai ? reg_op1[31] : 1'b0, reg_op1}) >>> reg_op2[4:0];
		end
	end endgenerate
```

---
<!-- chunk_id=picorv32_picorv32_30 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1249–1292

```verilog
always @* begin
		alu_out_0 = 'bx;
		(* parallel_case, full_case *)
		case (1'b1)
			instr_beq:
				alu_out_0 = alu_eq;
			instr_bne:
				alu_out_0 = !alu_eq;
			instr_bge:
				alu_out_0 = !alu_lts;
			instr_bgeu:
				alu_out_0 = !alu_ltu;
			is_slti_blt_slt && (!TWO_CYCLE_COMPARE || !{instr_beq,instr_bne,instr_bge,instr_bgeu}):
				alu_out_0 = alu_lts;
			is_sltiu_bltu_sltu && (!TWO_CYCLE_COMPARE || !{instr_beq,instr_bne,instr_bge,instr_bgeu}):
				alu_out_0 = alu_ltu;
		endcase

		alu_out = 'bx;
		(* parallel_case, full_case *)
		case (1'b1)
			is_lui_auipc_jal_jalr_addi_add_sub:
				alu_out = alu_add_sub;
			is_compare:
				alu_out = alu_out_0;
			instr_xori || instr_xor:
				alu_out = reg_op1 ^ reg_op2;
			instr_ori || instr_or:
				alu_out = reg_op1 | reg_op2;
			instr_andi || instr_and:
				alu_out = reg_op1 & reg_op2;
			BARREL_SHIFTER && (instr_sll || instr_slli):
				alu_out = alu_shl;
			BARREL_SHIFTER && (instr_srl || instr_srli || instr_sra || instr_srai):
				alu_out = alu_shr;
		endcase

`ifdef RISCV_FORMAL_BLACKBOX_ALU
		alu_out_0 = $anyseq;
		alu_out = $anyseq;
`endif
	end

	reg clear_prefetched_high_word_q;
```

---
<!-- chunk_id=picorv32_picorv32_31 | always @(posedge clk) clear_prefetched_high_word_q <= clear_prefetched_high_word -->

# Verilog Block: `always @(posedge clk) clear_prefetched_high_word_q <= clear_prefetched_high_word`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1293–1294

```verilog
always @(posedge clk) clear_prefetched_high_word_q <= clear_prefetched_high_word;
```

---
<!-- chunk_id=picorv32_picorv32_32 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1295–1308

```verilog
always @* begin
		clear_prefetched_high_word = clear_prefetched_high_word_q;
		if (!prefetched_high_word)
			clear_prefetched_high_word = 0;
		if (latched_branch || irq_state || !resetn)
			clear_prefetched_high_word = COMPRESSED_ISA;
	end

	reg cpuregs_write;
	reg [31:0] cpuregs_wrdata;
	reg [31:0] cpuregs_rs1;
	reg [31:0] cpuregs_rs2;
	reg [regindex_bits-1:0] decoded_rs;
```

---
<!-- chunk_id=picorv32_picorv32_33 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1309–1336

```verilog
always @* begin
		cpuregs_write = 0;
		cpuregs_wrdata = 'bx;

		if (cpu_state == cpu_state_fetch) begin
			(* parallel_case *)
			case (1'b1)
				latched_branch: begin
					cpuregs_wrdata = reg_pc + (latched_compr ? 2 : 4);
					cpuregs_write = 1;
				end
				latched_store && !latched_branch: begin
					cpuregs_wrdata = latched_stalu ? alu_out_q : reg_out;
					cpuregs_write = 1;
				end
				ENABLE_IRQ && irq_state[0]: begin
					cpuregs_wrdata = reg_next_pc | latched_compr;
					cpuregs_write = 1;
				end
				ENABLE_IRQ && irq_state[1]: begin
					cpuregs_wrdata = irq_pending & ~irq_mask;
					cpuregs_write = 1;
				end
			endcase
		end
	end

`ifndef PICORV32_REGS
```

---
<!-- chunk_id=picorv32_picorv32_34 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1337–1347

```verilog
always @(posedge clk) begin
		if (resetn && cpuregs_write && latched_rd)
`ifdef PICORV32_TESTBUG_001
			cpuregs[latched_rd ^ 1] <= cpuregs_wrdata;
`elsif PICORV32_TESTBUG_002
			cpuregs[latched_rd] <= cpuregs_wrdata ^ 1;
`else
			cpuregs[latched_rd] <= cpuregs_wrdata;
`endif
	end
```

---
<!-- chunk_id=picorv32_picorv32_35 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1348–1386

```verilog
always @* begin
		decoded_rs = 'bx;
		if (ENABLE_REGS_DUALPORT) begin
`ifndef RISCV_FORMAL_BLACKBOX_REGS
			cpuregs_rs1 = decoded_rs1 ? cpuregs[decoded_rs1] : 0;
			cpuregs_rs2 = decoded_rs2 ? cpuregs[decoded_rs2] : 0;
`else
			cpuregs_rs1 = decoded_rs1 ? $anyseq : 0;
			cpuregs_rs2 = decoded_rs2 ? $anyseq : 0;
`endif
		end else begin
			decoded_rs = (cpu_state == cpu_state_ld_rs2) ? decoded_rs2 : decoded_rs1;
`ifndef RISCV_FORMAL_BLACKBOX_REGS
			cpuregs_rs1 = decoded_rs ? cpuregs[decoded_rs] : 0;
`else
			cpuregs_rs1 = decoded_rs ? $anyseq : 0;
`endif
			cpuregs_rs2 = cpuregs_rs1;
		end
	end
`else
	wire[31:0] cpuregs_rdata1;
	wire[31:0] cpuregs_rdata2;

	wire [5:0] cpuregs_waddr = latched_rd;
	wire [5:0] cpuregs_raddr1 = ENABLE_REGS_DUALPORT ? decoded_rs1 : decoded_rs;
	wire [5:0] cpuregs_raddr2 = ENABLE_REGS_DUALPORT ? decoded_rs2 : 0;

	`PICORV32_REGS cpuregs (
		.clk(clk),
		.wen(resetn && cpuregs_write && latched_rd),
		.waddr(cpuregs_waddr),
		.raddr1(cpuregs_raddr1),
		.raddr2(cpuregs_raddr2),
		.wdata(cpuregs_wrdata),
		.rdata1(cpuregs_rdata1),
		.rdata2(cpuregs_rdata2)
	);
```

---
<!-- chunk_id=picorv32_picorv32_36 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1387–1401

```verilog
always @* begin
		decoded_rs = 'bx;
		if (ENABLE_REGS_DUALPORT) begin
			cpuregs_rs1 = decoded_rs1 ? cpuregs_rdata1 : 0;
			cpuregs_rs2 = decoded_rs2 ? cpuregs_rdata2 : 0;
		end else begin
			decoded_rs = (cpu_state == cpu_state_ld_rs2) ? decoded_rs2 : decoded_rs1;
			cpuregs_rs1 = decoded_rs ? cpuregs_rdata1 : 0;
			cpuregs_rs2 = cpuregs_rs1;
		end
	end
`endif

	assign launch_next_insn = cpu_state == cpu_state_fetch && decoder_trigger && (!ENABLE_IRQ || irq_delay || irq_active || !(irq_pending & ~irq_mask));
```

---
<!-- chunk_id=picorv32_picorv32_37 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1402–1980

```verilog
always @(posedge clk) begin
		trap <= 0;
		reg_sh <= 'bx;
		reg_out <= 'bx;
		set_mem_do_rinst = 0;
		set_mem_do_rdata = 0;
		set_mem_do_wdata = 0;

		alu_out_0_q <= alu_out_0;
		alu_out_q <= alu_out;

		alu_wait <= 0;
		alu_wait_2 <= 0;

		if (launch_next_insn) begin
			dbg_rs1val <= 'bx;
			dbg_rs2val <= 'bx;
			dbg_rs1val_valid <= 0;
			dbg_rs2val_valid <= 0;
		end

		if (WITH_PCPI && CATCH_ILLINSN) begin
			if (resetn && pcpi_valid && !pcpi_int_wait) begin
				if (pcpi_timeout_counter)
					pcpi_timeout_counter <= pcpi_timeout_counter - 1;
			end else
				pcpi_timeout_counter <= ~0;
			pcpi_timeout <= !pcpi_timeout_counter;
		end

		if (ENABLE_COUNTERS) begin
			count_cycle <= resetn ? count_cycle + 1 : 0;
			if (!ENABLE_COUNTERS64) count_cycle[63:32] <= 0;
		end else begin
			count_cycle <= 'bx;
			count_instr <= 'bx;
		end

		next_irq_pending = ENABLE_IRQ ? irq_pending & LATCHED_IRQ : 'bx;

		if (ENABLE_IRQ && ENABLE_IRQ_TIMER && timer) begin
			timer <= timer - 1;
		end

		decoder_trigger <= mem_do_rinst && mem_done;
		decoder_trigger_q <= decoder_trigger;
		decoder_pseudo_trigger <= 0;
		decoder_pseudo_trigger_q <= decoder_pseudo_trigger;
		do_waitirq <= 0;

		trace_valid <= 0;

		if (!ENABLE_TRACE)
			trace_data <= 'bx;

		if (!resetn) begin
			reg_pc <= PROGADDR_RESET;
			reg_next_pc <= PROGADDR_RESET;
			if (ENABLE_COUNTERS)
				count_instr <= 0;
			latched_store <= 0;
			latched_stalu <= 0;
			latched_branch <= 0;
			latched_trace <= 0;
			latched_is_lu <= 0;
			latched_is_lh <= 0;
			latched_is_lb <= 0;
			pcpi_valid <= 0;
			pcpi_timeout <= 0;
			irq_active <= 0;
			irq_delay <= 0;
			irq_mask <= ~0;
			next_irq_pending = 0;
			irq_state <= 0;
			eoi <= 0;
			timer <= 0;
			if (~STACKADDR) begin
				latched_store <= 1;
				latched_rd <= 2;
				reg_out <= STACKADDR;
			end
			cpu_state <= cpu_state_fetch;
		end else
		(* parallel_case, full_case *)
		case (cpu_state)
			cpu_state_trap: begin
				trap <= 1;
			end

			cpu_state_fetch: begin
				mem_do_rinst <= !decoder_trigger && !do_waitirq;
				mem_wordsize <= 0;

				current_pc = reg_next_pc;

				(* parallel_case *)
				case (1'b1)
					latched_branch: begin
						current_pc = latched_store ? (latched_stalu ? alu_out_q : reg_out) & ~1 : reg_next_pc;
						`debug($display("ST_RD:  %2d 0x%08x, BRANCH 0x%08x", latched_rd, reg_pc + (latched_compr ? 2 : 4), current_pc);)
					end
					latched_store && !latched_branch: begin
						`debug($display("ST_RD:  %2d 0x%08x", latched_rd, latched_stalu ? alu_out_q : reg_out);)
					end
					ENABLE_IRQ && irq_state[0]: begin
						current_pc = PROGADDR_IRQ;
						irq_active <= 1;
						mem_do_rinst <= 1;
					end
					ENABLE_IRQ && irq_state[1]: begin
						eoi <= irq_pending & ~irq_mask;
						next_irq_pending = next_irq_pending & irq_mask;
					end
				endcase

				if (ENABLE_TRACE && latched_trace) begin
					latched_trace <= 0;
					trace_valid <= 1;
					if (latched_branch)
						trace_data <= (irq_active ? TRACE_IRQ : 0) | TRACE_BRANCH | (current_pc & 32'hfffffffe);
					else
						trace_data <= (irq_active ? TRACE_IRQ : 0) | (latched_stalu ? alu_out_q : reg_out);
				end

				reg_pc <= current_pc;
				reg_next_pc <= current_pc;

				latched_store <= 0;
				latched_stalu <= 0;
				latched_branch <= 0;
				latched_is_lu <= 0;
				latched_is_lh <= 0;
				latched_is_lb <= 0;
				latched_rd <= decoded_rd;
				latched_compr <= compressed_instr;

				if (ENABLE_IRQ && ((decoder_trigger && !irq_active && !irq_delay && |(irq_pending & ~irq_mask)) || irq_state)) begin
					irq_state <=
						irq_state == 2'b00 ? 2'b01 :
						irq_state == 2'b01 ? 2'b10 : 2'b00;
					latched_compr <= latched_compr;
					if (ENABLE_IRQ_QREGS)
						latched_rd <= irqregs_offset | irq_state[0];
					else
						latched_rd <= irq_state[0] ? 4 : 3;
				end else
				if (ENABLE_IRQ && (decoder_trigger || do_waitirq) && instr_waitirq) begin
					if (irq_pending) begin
						latched_store <= 1;
						reg_out <= irq_pending;
						reg_next_pc <= current_pc + (compressed_instr ? 2 : 4);
						mem_do_rinst <= 1;
					end else
						do_waitirq <= 1;
				end else
				if (decoder_trigger) begin
					`debug($display("-- %-0t", $time);)
					irq_delay <= irq_active;
					reg_next_pc <= current_pc + (compressed_instr ? 2 : 4);
					if (ENABLE_TRACE)
						latched_trace <= 1;
					if (ENABLE_COUNTERS) begin
						count_instr <= count_instr + 1;
						if (!ENABLE_COUNTERS64) count_instr[63:32] <= 0;
					end
					if (instr_jal) begin
						mem_do_rinst <= 1;
						reg_next_pc <= current_pc + decoded_imm_j;
						latched_branch <= 1;
					end else begin
						mem_do_rinst <= 0;
						mem_do_prefetch <= !instr_jalr && !instr_retirq;
						cpu_state <= cpu_state_ld_rs1;
					end
				end
			end

			cpu_state_ld_rs1: begin
				reg_op1 <= 'bx;
				reg_op2 <= 'bx;

				(* parallel_case *)
				case (1'b1)
					(CATCH_ILLINSN || WITH_PCPI) && instr_trap: begin
						if (WITH_PCPI) begin
							`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_op1 <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							if (ENABLE_REGS_DUALPORT) begin
								pcpi_valid <= 1;
								`debug($display("LD_RS2: %2d 0x%08x", decoded_rs2, cpuregs_rs2);)
								reg_sh <= cpuregs_rs2;
								reg_op2 <= cpuregs_rs2;
								dbg_rs2val <= cpuregs_rs2;
								dbg_rs2val_valid <= 1;
								if (pcpi_int_ready) begin
									mem_do_rinst <= 1;
									pcpi_valid <= 0;
									reg_out <= pcpi_int_rd;
									latched_store <= pcpi_int_wr;
									cpu_state <= cpu_state_fetch;
								end else
								if (CATCH_ILLINSN && (pcpi_timeout || instr_ecall_ebreak)) begin
									pcpi_valid <= 0;
									`debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pc);)
									if (ENABLE_IRQ && !irq_mask[irq_ebreak] && !irq_active) begin
										next_irq_pending[irq_ebreak] = 1;
										cpu_state <= cpu_state_fetch;
									end else
										cpu_state <= cpu_state_trap;
								end
							end else begin
								cpu_state <= cpu_state_ld_rs2;
							end
						end else begin
							`debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pc);)
							if (ENABLE_IRQ && !irq_mask[irq_ebreak] && !irq_active) begin
								next_irq_pending[irq_ebreak] = 1;
								cpu_state <= cpu_state_fetch;
							end else
								cpu_state <= cpu_state_trap;
						end
					end
					ENABLE_COUNTERS && is_rdcycle_rdcycleh_rdinstr_rdinstrh: begin
						(* parallel_case, full_case *)
						case (1'b1)
							instr_rdcycle:
								reg_out <= count_cycle[31:0];
							instr_rdcycleh && ENABLE_COUNTERS64:
								reg_out <= count_cycle[63:32];
							instr_rdinstr:
								reg_out <= count_instr[31:0];
							instr_rdinstrh && ENABLE_COUNTERS64:
								reg_out <= count_instr[63:32];
						endcase
						latched_store <= 1;
						cpu_state <= cpu_state_fetch;
					end
					is_lui_auipc_jal: begin
						reg_op1 <= instr_lui ? 0 : reg_pc;
						reg_op2 <= decoded_imm;
						if (TWO_CYCLE_ALU)
							alu_wait <= 1;
						else
							mem_do_rinst <= mem_do_prefetch;
						cpu_state <= cpu_state_exec;
					end
					ENABLE_IRQ && ENABLE_IRQ_QREGS && instr_getq: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_out <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						latched_store <= 1;
						cpu_state <= cpu_state_fetch;
					end
					ENABLE_IRQ && ENABLE_IRQ_QREGS && instr_setq: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_out <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						latched_rd <= latched_rd | irqregs_offset;
						latched_store <= 1;
						cpu_state <= cpu_state_fetch;
					end
					ENABLE_IRQ && instr_retirq: begin
						eoi <= 0;
						irq_active <= 0;
						latched_branch <= 1;
						latched_store <= 1;
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_out <= CATCH_MISALIGN ? (cpuregs_rs1 & 32'h fffffffe) : cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						cpu_state <= cpu_state_fetch;
					end
					ENABLE_IRQ && instr_maskirq: begin
						latched_store <= 1;
						reg_out <= irq_mask;
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						irq_mask <= cpuregs_rs1 | MASKED_IRQ;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						cpu_state <= cpu_state_fetch;
					end
					ENABLE_IRQ && ENABLE_IRQ_TIMER && instr_timer: begin
						latched_store <= 1;
						reg_out <= timer;
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						timer <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						cpu_state <= cpu_state_fetch;
					end
					is_lb_lh_lw_lbu_lhu && !instr_trap: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_op1 <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						cpu_state <= cpu_state_ldmem;
						mem_do_rinst <= 1;
					end
					is_slli_srli_srai && !BARREL_SHIFTER: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_op1 <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						reg_sh <= decoded_rs2;
						cpu_state <= cpu_state_shift;
					end
					is_jalr_addi_slti_sltiu_xori_ori_andi, is_slli_srli_srai && BARREL_SHIFTER: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_op1 <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						reg_op2 <= is_slli_srli_srai && BARREL_SHIFTER ? decoded_rs2 : decoded_imm;
						if (TWO_CYCLE_ALU)
							alu_wait <= 1;
						else
							mem_do_rinst <= mem_do_prefetch;
						cpu_state <= cpu_state_exec;
					end
					default: begin
						`debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
						reg_op1 <= cpuregs_rs1;
						dbg_rs1val <= cpuregs_rs1;
						dbg_rs1val_valid <= 1;
						if (ENABLE_REGS_DUALPORT) begin
							`debug($display("LD_RS2: %2d 0x%08x", decoded_rs2, cpuregs_rs2);)
							reg_sh <= cpuregs_rs2;
							reg_op2 <= cpuregs_rs2;
							dbg_rs2val <= cpuregs_rs2;
							dbg_rs2val_valid <= 1;
							(* parallel_case *)
							case (1'b1)
								is_sb_sh_sw: begin
									cpu_state <= cpu_state_stmem;
									mem_do_rinst <= 1;
								end
								is_sll_srl_sra && !BARREL_SHIFTER: begin
									cpu_state <= cpu_state_shift;
								end
								default: begin
									if (TWO_CYCLE_ALU || (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeu)) begin
										alu_wait_2 <= TWO_CYCLE_ALU && (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeu);
										alu_wait <= 1;
									end else
										mem_do_rinst <= mem_do_prefetch;
									cpu_state <= cpu_state_exec;
								end
							endcase
						end else
							cpu_state <= cpu_state_ld_rs2;
					end
				endcase
			end

			cpu_state_ld_rs2: begin
				`debug($display("LD_RS2: %2d 0x%08x", decoded_rs2, cpuregs_rs2);)
				reg_sh <= cpuregs_rs2;
				reg_op2 <= cpuregs_rs2;
				dbg_rs2val <= cpuregs_rs2;
				dbg_rs2val_valid <= 1;

				(* parallel_case *)
				case (1'b1)
					WITH_PCPI && instr_trap: begin
						pcpi_valid <= 1;
						if (pcpi_int_ready) begin
							mem_do_rinst <= 1;
							pcpi_valid <= 0;
							reg_out <= pcpi_int_rd;
							latched_store <= pcpi_int_wr;
							cpu_state <= cpu_state_fetch;
						end else
						if (CATCH_ILLINSN && (pcpi_timeout || instr_ecall_ebreak)) begin
							pcpi_valid <= 0;
							`debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pc);)
							if (ENABLE_IRQ && !irq_mask[irq_ebreak] && !irq_active) begin
								next_irq_pending[irq_ebreak] = 1;
								cpu_state <= cpu_state_fetch;
							end else
								cpu_state <= cpu_state_trap;
						end
					end
					is_sb_sh_sw: begin
						cpu_state <= cpu_state_stmem;
						mem_do_rinst <= 1;
					end
					is_sll_srl_sra && !BARREL_SHIFTER: begin
						cpu_state <= cpu_state_shift;
					end
					default: begin
						if (TWO_CYCLE_ALU || (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeu)) begin
							alu_wait_2 <= TWO_CYCLE_ALU && (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeu);
							alu_wait <= 1;
						end else
							mem_do_rinst <= mem_do_prefetch;
						cpu_state <= cpu_state_exec;
					end
				endcase
			end

			cpu_state_exec: begin
				reg_out <= reg_pc + decoded_imm;
				if ((TWO_CYCLE_ALU || TWO_CYCLE_COMPARE) && (alu_wait || alu_wait_2)) begin
					mem_do_rinst <= mem_do_prefetch && !alu_wait_2;
					alu_wait <= alu_wait_2;
				end else
				if (is_beq_bne_blt_bge_bltu_bgeu) begin
					latched_rd <= 0;
					latched_store <= TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0;
					latched_branch <= TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0;
					if (mem_done)
						cpu_state <= cpu_state_fetch;
					if (TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0) begin
						decoder_trigger <= 0;
						set_mem_do_rinst = 1;
					end
				end else begin
					latched_branch <= instr_jalr;
					latched_store <= 1;
					latched_stalu <= 1;
					cpu_state <= cpu_state_fetch;
				end
			end

			cpu_state_shift: begin
				latched_store <= 1;
				if (reg_sh == 0) begin
					reg_out <= reg_op1;
					mem_do_rinst <= mem_do_prefetch;
					cpu_state <= cpu_state_fetch;
				end else if (TWO_STAGE_SHIFT && reg_sh >= 4) begin
					(* parallel_case, full_case *)
					case (1'b1)
						instr_slli || instr_sll: reg_op1 <= reg_op1 << 4;
						instr_srli || instr_srl: reg_op1 <= reg_op1 >> 4;
						instr_srai || instr_sra: reg_op1 <= $signed(reg_op1) >>> 4;
					endcase
					reg_sh <= reg_sh - 4;
				end else begin
					(* parallel_case, full_case *)
					case (1'b1)
						instr_slli || instr_sll: reg_op1 <= reg_op1 << 1;
						instr_srli || instr_srl: reg_op1 <= reg_op1 >> 1;
						instr_srai || instr_sra: reg_op1 <= $signed(reg_op1) >>> 1;
					endcase
					reg_sh <= reg_sh - 1;
				end
			end

			cpu_state_stmem: begin
				if (ENABLE_TRACE)
					reg_out <= reg_op2;
				if (!mem_do_prefetch || mem_done) begin
					if (!mem_do_wdata) begin
						(* parallel_case, full_case *)
						case (1'b1)
							instr_sb: mem_wordsize <= 2;
							instr_sh: mem_wordsize <= 1;
							instr_sw: mem_wordsize <= 0;
						endcase
						if (ENABLE_TRACE) begin
							trace_valid <= 1;
							trace_data <= (irq_active ? TRACE_IRQ : 0) | TRACE_ADDR | ((reg_op1 + decoded_imm) & 32'hffffffff);
						end
						reg_op1 <= reg_op1 + decoded_imm;
						set_mem_do_wdata = 1;
					end
					if (!mem_do_prefetch && mem_done) begin
						cpu_state <= cpu_state_fetch;
						decoder_trigger <= 1;
						decoder_pseudo_trigger <= 1;
					end
				end
			end

			cpu_state_ldmem: begin
				latched_store <= 1;
				if (!mem_do_prefetch || mem_done) begin
					if (!mem_do_rdata) begin
						(* parallel_case, full_case *)
						case (1'b1)
							instr_lb || instr_lbu: mem_wordsize <= 2;
							instr_lh || instr_lhu: mem_wordsize <= 1;
							instr_lw: mem_wordsize <= 0;
						endcase
						latched_is_lu <= is_lbu_lhu_lw;
						latched_is_lh <= instr_lh;
						latched_is_lb <= instr_lb;
						if (ENABLE_TRACE) begin
							trace_valid <= 1;
							trace_data <= (irq_active ? TRACE_IRQ : 0) | TRACE_ADDR | ((reg_op1 + decoded_imm) & 32'hffffffff);
						end
						reg_op1 <= reg_op1 + decoded_imm;
						set_mem_do_rdata = 1;
					end
					if (!mem_do_prefetch && mem_done) begin
						(* parallel_case, full_case *)
						case (1'b1)
							latched_is_lu: reg_out <= mem_rdata_word;
							latched_is_lh: reg_out <= $signed(mem_rdata_word[15:0]);
							latched_is_lb: reg_out <= $signed(mem_rdata_word[7:0]);
						endcase
						decoder_trigger <= 1;
						decoder_pseudo_trigger <= 1;
						cpu_state <= cpu_state_fetch;
					end
				end
			end
		endcase

		if (ENABLE_IRQ) begin
			next_irq_pending = next_irq_pending | irq;
			if(ENABLE_IRQ_TIMER && timer)
				if (timer - 1 == 0)
					next_irq_pending[irq_timer] = 1;
		end

		if (CATCH_MISALIGN && resetn && (mem_do_rdata || mem_do_wdata)) begin
			if (mem_wordsize == 0 && reg_op1[1:0] != 0) begin
				`debug($display("MISALIGNED WORD: 0x%08x", reg_op1);)
				if (ENABLE_IRQ && !irq_mask[irq_buserror] && !irq_active) begin
					next_irq_pending[irq_buserror] = 1;
				end else
					cpu_state <= cpu_state_trap;
			end
			if (mem_wordsize == 1 && reg_op1[0] != 0) begin
				`debug($display("MISALIGNED HALFWORD: 0x%08x", reg_op1);)
				if (ENABLE_IRQ && !irq_mask[irq_buserror] && !irq_active) begin
					next_irq_pending[irq_buserror] = 1;
				end else
					cpu_state <= cpu_state_trap;
			end
		end
		if (CATCH_MISALIGN && resetn && mem_do_rinst && (COMPRESSED_ISA ? reg_pc[0] : |reg_pc[1:0])) begin
			`debug($display("MISALIGNED INSTRUCTION: 0x%08x", reg_pc);)
			if (ENABLE_IRQ && !irq_mask[irq_buserror] && !irq_active) begin
				next_irq_pending[irq_buserror] = 1;
			end else
				cpu_state <= cpu_state_trap;
		end
		if (!CATCH_ILLINSN && decoder_trigger_q && !decoder_pseudo_trigger_q && instr_ecall_ebreak) begin
			cpu_state <= cpu_state_trap;
		end

		if (!resetn || mem_done) begin
			mem_do_prefetch <= 0;
			mem_do_rinst <= 0;
			mem_do_rdata <= 0;
			mem_do_wdata <= 0;
		end

		if (set_mem_do_rinst)
			mem_do_rinst <= 1;
		if (set_mem_do_rdata)
			mem_do_rdata <= 1;
		if (set_mem_do_wdata)
			mem_do_wdata <= 1;

		irq_pending <= next_irq_pending & ~MASKED_IRQ;

		if (!CATCH_MISALIGN) begin
			if (COMPRESSED_ISA) begin
				reg_pc[0] <= 0;
				reg_next_pc[0] <= 0;
			end else begin
				reg_pc[1:0] <= 0;
				reg_next_pc[1:0] <= 0;
			end
		end
		current_pc = 'bx;
	end

`ifdef RISCV_FORMAL
	reg dbg_irq_call;
	reg dbg_irq_enter;
	reg [31:0] dbg_irq_ret;
```

---
<!-- chunk_id=picorv32_picorv32_38 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 1981–2063

```verilog
always @(posedge clk) begin
		rvfi_valid <= resetn && (launch_next_insn || trap) && dbg_valid_insn;
		rvfi_order <= resetn ? rvfi_order + rvfi_valid : 0;

		rvfi_insn <= dbg_insn_opcode;
		rvfi_rs1_addr <= dbg_rs1val_valid ? dbg_insn_rs1 : 0;
		rvfi_rs2_addr <= dbg_rs2val_valid ? dbg_insn_rs2 : 0;
		rvfi_pc_rdata <= dbg_insn_addr;
		rvfi_rs1_rdata <= dbg_rs1val_valid ? dbg_rs1val : 0;
		rvfi_rs2_rdata <= dbg_rs2val_valid ? dbg_rs2val : 0;
		rvfi_trap <= trap;
		rvfi_halt <= trap;
		rvfi_intr <= dbg_irq_enter;
		rvfi_mode <= 3;
		rvfi_ixl <= 1;

		if (!resetn) begin
			dbg_irq_call <= 0;
			dbg_irq_enter <= 0;
		end else
		if (rvfi_valid) begin
			dbg_irq_call <= 0;
			dbg_irq_enter <= dbg_irq_call;
		end else
		if (irq_state == 1) begin
			dbg_irq_call <= 1;
			dbg_irq_ret <= next_pc;
		end

		if (!resetn) begin
			rvfi_rd_addr <= 0;
			rvfi_rd_wdata <= 0;
		end else
		if (cpuregs_write && !irq_state) begin
`ifdef PICORV32_TESTBUG_003
			rvfi_rd_addr <= latched_rd ^ 1;
`else
			rvfi_rd_addr <= latched_rd;
`endif
`ifdef PICORV32_TESTBUG_004
			rvfi_rd_wdata <= latched_rd ? cpuregs_wrdata ^ 1 : 0;
`else
			rvfi_rd_wdata <= latched_rd ? cpuregs_wrdata : 0;
`endif
		end else
		if (rvfi_valid) begin
			rvfi_rd_addr <= 0;
			rvfi_rd_wdata <= 0;
		end

		casez (dbg_insn_opcode)
			32'b 0000000_?????_000??_???_?????_0001011: begin // getq
				rvfi_rs1_addr <= 0;
				rvfi_rs1_rdata <= 0;
			end
			32'b 0000001_?????_?????_???_000??_0001011: begin // setq
				rvfi_rd_addr <= 0;
				rvfi_rd_wdata <= 0;
			end
			32'b 0000010_?????_00000_???_00000_0001011: begin // retirq
				rvfi_rs1_addr <= 0;
				rvfi_rs1_rdata <= 0;
			end
		endcase

		if (!dbg_irq_call) begin
			if (dbg_mem_instr) begin
				rvfi_mem_addr <= 0;
				rvfi_mem_rmask <= 0;
				rvfi_mem_wmask <= 0;
				rvfi_mem_rdata <= 0;
				rvfi_mem_wdata <= 0;
			end else
			if (dbg_mem_valid && dbg_mem_ready) begin
				rvfi_mem_addr <= dbg_mem_addr;
				rvfi_mem_rmask <= dbg_mem_wstrb ? 0 : ~0;
				rvfi_mem_wmask <= dbg_mem_wstrb;
				rvfi_mem_rdata <= dbg_mem_rdata;
				rvfi_mem_wdata <= dbg_mem_wdata;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_39 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2064–2104

```verilog
always @* begin
`ifdef PICORV32_TESTBUG_005
		rvfi_pc_wdata = (dbg_irq_call ? dbg_irq_ret : dbg_insn_addr) ^ 4;
`else
		rvfi_pc_wdata = dbg_irq_call ? dbg_irq_ret : dbg_insn_addr;
`endif

		rvfi_csr_mcycle_rmask = 0;
		rvfi_csr_mcycle_wmask = 0;
		rvfi_csr_mcycle_rdata = 0;
		rvfi_csr_mcycle_wdata = 0;

		rvfi_csr_minstret_rmask = 0;
		rvfi_csr_minstret_wmask = 0;
		rvfi_csr_minstret_rdata = 0;
		rvfi_csr_minstret_wdata = 0;

		if (rvfi_valid && rvfi_insn[6:0] == 7'b 1110011 && rvfi_insn[13:12] == 3'b010) begin
			if (rvfi_insn[31:20] == 12'h C00) begin
				rvfi_csr_mcycle_rmask = 64'h 0000_0000_FFFF_FFFF;
				rvfi_csr_mcycle_rdata = {32'h 0000_0000, rvfi_rd_wdata};
			end
			if (rvfi_insn[31:20] == 12'h C80) begin
				rvfi_csr_mcycle_rmask = 64'h FFFF_FFFF_0000_0000;
				rvfi_csr_mcycle_rdata = {rvfi_rd_wdata, 32'h 0000_0000};
			end
			if (rvfi_insn[31:20] == 12'h C02) begin
				rvfi_csr_minstret_rmask = 64'h 0000_0000_FFFF_FFFF;
				rvfi_csr_minstret_rdata = {32'h 0000_0000, rvfi_rd_wdata};
			end
			if (rvfi_insn[31:20] == 12'h C82) begin
				rvfi_csr_minstret_rmask = 64'h FFFF_FFFF_0000_0000;
				rvfi_csr_minstret_rdata = {rvfi_rd_wdata, 32'h 0000_0000};
			end
		end
	end
`endif

	// Formal Verification
`ifdef FORMAL
	reg [3:0] last_mem_nowait;
```

---
<!-- chunk_id=picorv32_picorv32_40 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2105–2117

```verilog
always @(posedge clk)
		last_mem_nowait <= {last_mem_nowait, mem_ready || !mem_valid};

	// stall the memory interface for max 4 cycles
	restrict property (|last_mem_nowait || mem_ready || !mem_valid);

	// resetn low in first cycle, after that resetn high
	restrict property (resetn != $initstate);

	// this just makes it much easier to read traces. uncomment as needed.
	// assume property (mem_valid || !mem_ready);

	reg ok;
```

---
<!-- chunk_id=picorv32_picorv32_41 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2118–2143

```verilog
always @* begin
		if (resetn) begin
			// instruction fetches are read-only
			if (mem_valid && mem_instr)
				assert (mem_wstrb == 0);

			// cpu_state must be valid
			ok = 0;
			if (cpu_state == cpu_state_trap)   ok = 1;
			if (cpu_state == cpu_state_fetch)  ok = 1;
			if (cpu_state == cpu_state_ld_rs1) ok = 1;
			if (cpu_state == cpu_state_ld_rs2) ok = !ENABLE_REGS_DUALPORT;
			if (cpu_state == cpu_state_exec)   ok = 1;
			if (cpu_state == cpu_state_shift)  ok = 1;
			if (cpu_state == cpu_state_stmem)  ok = 1;
			if (cpu_state == cpu_state_ldmem)  ok = 1;
			assert (ok);
		end
	end

	reg last_mem_la_read = 0;
	reg last_mem_la_write = 0;
	reg [31:0] last_mem_la_addr;
	reg [31:0] last_mem_la_wdata;
	reg [3:0] last_mem_la_wstrb = 0;
```

---
<!-- chunk_id=picorv32_picorv32_42 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2144–2166

```verilog
always @(posedge clk) begin
		last_mem_la_read <= mem_la_read;
		last_mem_la_write <= mem_la_write;
		last_mem_la_addr <= mem_la_addr;
		last_mem_la_wdata <= mem_la_wdata;
		last_mem_la_wstrb <= mem_la_wstrb;

		if (last_mem_la_read) begin
			assert(mem_valid);
			assert(mem_addr == last_mem_la_addr);
			assert(mem_wstrb == 0);
		end
		if (last_mem_la_write) begin
			assert(mem_valid);
			assert(mem_addr == last_mem_la_addr);
			assert(mem_wdata == last_mem_la_wdata);
			assert(mem_wstrb == last_mem_la_wstrb);
		end
		if (mem_la_read || mem_la_write) begin
			assert(!mem_valid || mem_ready);
		end
	end
`endif
```

---
<!-- chunk_id=picorv32_picorv32_43 | endmodule -->

# Verilog Block: `endmodule`

> **Block Comment:** This is a simple example implementation of PICORV32_REGS. Use the PICORV32_REGS mechanism if you want to use custom memory resources to implement the processor register file.

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2167–2173

```verilog
endmodule

// This is a simple example implementation of PICORV32_REGS.
// Use the PICORV32_REGS mechanism if you want to use custom
// memory resources to implement the processor register file.
// Note that your implementation must match the requirements of
// the PicoRV32 configuration. (e.g. QREGS, etc)
```

---
<!-- chunk_id=picorv32_picorv32_44 | module picorv32_regs ( -->

# Verilog Block: `module picorv32_regs (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2174–2184

```verilog
module picorv32_regs (
	input clk, wen,
	input [5:0] waddr,
	input [5:0] raddr1,
	input [5:0] raddr2,
	input [31:0] wdata,
	output [31:0] rdata1,
	output [31:0] rdata2
);
	reg [31:0] regs [0:30];
```

---
<!-- chunk_id=picorv32_picorv32_45 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2185–2189

```verilog
always @(posedge clk)
		if (wen) regs[~waddr[4:0]] <= wdata;

	assign rdata1 = regs[~raddr1[4:0]];
	assign rdata2 = regs[~raddr2[4:0]];
```

---
<!-- chunk_id=picorv32_picorv32_46 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2190–2196

```verilog
endmodule


/***************************************************************
 * picorv32_pcpi_mul
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_47 | module picorv32_pcpi_mul #( -->

# Verilog Block: `module picorv32_pcpi_mul #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2197–2220

```verilog
module picorv32_pcpi_mul #(
	parameter STEPS_AT_ONCE = 1,
	parameter CARRY_CHAIN = 4
) (
	input clk, resetn,

	input             pcpi_valid,
	input      [31:0] pcpi_insn,
	input      [31:0] pcpi_rs1,
	input      [31:0] pcpi_rs2,
	output reg        pcpi_wr,
	output reg [31:0] pcpi_rd,
	output reg        pcpi_wait,
	output reg        pcpi_ready
);
	reg instr_mul, instr_mulh, instr_mulhsu, instr_mulhu;
	wire instr_any_mul = |{instr_mul, instr_mulh, instr_mulhsu, instr_mulhu};
	wire instr_any_mulh = |{instr_mulh, instr_mulhsu, instr_mulhu};
	wire instr_rs1_signed = |{instr_mulh, instr_mulhsu};
	wire instr_rs2_signed = |{instr_mulh};

	reg pcpi_wait_q;
	wire mul_start = pcpi_wait && !pcpi_wait_q;
```

---
<!-- chunk_id=picorv32_picorv32_48 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2221–2248

```verilog
always @(posedge clk) begin
		instr_mul <= 0;
		instr_mulh <= 0;
		instr_mulhsu <= 0;
		instr_mulhu <= 0;

		if (resetn && pcpi_valid && pcpi_insn[6:0] == 7'b0110011 && pcpi_insn[31:25] == 7'b0000001) begin
			case (pcpi_insn[14:12])
				3'b000: instr_mul <= 1;
				3'b001: instr_mulh <= 1;
				3'b010: instr_mulhsu <= 1;
				3'b011: instr_mulhu <= 1;
			endcase
		end

		pcpi_wait <= instr_any_mul;
		pcpi_wait_q <= pcpi_wait;
	end

	reg [63:0] rs1, rs2, rd, rdx;
	reg [63:0] next_rs1, next_rs2, this_rs2;
	reg [63:0] next_rd, next_rdx, next_rdt;
	reg [6:0] mul_counter;
	reg mul_waiting;
	reg mul_finish;
	integer i, j;

	// carry save accumulator
```

---
<!-- chunk_id=picorv32_picorv32_49 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2249–2272

```verilog
always @* begin
		next_rd = rd;
		next_rdx = rdx;
		next_rs1 = rs1;
		next_rs2 = rs2;

		for (i = 0; i < STEPS_AT_ONCE; i=i+1) begin
			this_rs2 = next_rs1[0] ? next_rs2 : 0;
			if (CARRY_CHAIN == 0) begin
				next_rdt = next_rd ^ next_rdx ^ this_rs2;
				next_rdx = ((next_rd & next_rdx) | (next_rd & this_rs2) | (next_rdx & this_rs2)) << 1;
				next_rd = next_rdt;
			end else begin
				next_rdt = 0;
				for (j = 0; j < 64; j = j + CARRY_CHAIN)
					{next_rdt[j+CARRY_CHAIN-1], next_rd[j +: CARRY_CHAIN]} =
							next_rd[j +: CARRY_CHAIN] + next_rdx[j +: CARRY_CHAIN] + this_rs2[j +: CARRY_CHAIN];
				next_rdx = next_rdt << 1;
			end
			next_rs1 = next_rs1 >> 1;
			next_rs2 = next_rs2 << 1;
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_50 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2273–2306

```verilog
always @(posedge clk) begin
		mul_finish <= 0;
		if (!resetn) begin
			mul_waiting <= 1;
		end else
		if (mul_waiting) begin
			if (instr_rs1_signed)
				rs1 <= $signed(pcpi_rs1);
			else
				rs1 <= $unsigned(pcpi_rs1);

			if (instr_rs2_signed)
				rs2 <= $signed(pcpi_rs2);
			else
				rs2 <= $unsigned(pcpi_rs2);

			rd <= 0;
			rdx <= 0;
			mul_counter <= (instr_any_mulh ? 63 - STEPS_AT_ONCE : 31 - STEPS_AT_ONCE);
			mul_waiting <= !mul_start;
		end else begin
			rd <= next_rd;
			rdx <= next_rdx;
			rs1 <= next_rs1;
			rs2 <= next_rs2;

			mul_counter <= mul_counter - STEPS_AT_ONCE;
			if (mul_counter[6]) begin
				mul_finish <= 1;
				mul_waiting <= 1;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_51 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2307–2315

```verilog
always @(posedge clk) begin
		pcpi_wr <= 0;
		pcpi_ready <= 0;
		if (mul_finish && resetn) begin
			pcpi_wr <= 1;
			pcpi_ready <= 1;
			pcpi_rd <= instr_any_mulh ? rd >> 32 : rd;
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_53 | module picorv32_pcpi_fast_mul #( -->

# Verilog Block: `module picorv32_pcpi_fast_mul #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2318–2347

```verilog
module picorv32_pcpi_fast_mul #(
	parameter EXTRA_MUL_FFS = 0,
	parameter EXTRA_INSN_FFS = 0,
	parameter MUL_CLKGATE = 0
) (
	input clk, resetn,

	input             pcpi_valid,
	input      [31:0] pcpi_insn,
	input      [31:0] pcpi_rs1,
	input      [31:0] pcpi_rs2,
	output            pcpi_wr,
	output     [31:0] pcpi_rd,
	output            pcpi_wait,
	output            pcpi_ready
);
	reg instr_mul, instr_mulh, instr_mulhsu, instr_mulhu;
	wire instr_any_mul = |{instr_mul, instr_mulh, instr_mulhsu, instr_mulhu};
	wire instr_any_mulh = |{instr_mulh, instr_mulhsu, instr_mulhu};
	wire instr_rs1_signed = |{instr_mulh, instr_mulhsu};
	wire instr_rs2_signed = |{instr_mulh};

	reg shift_out;
	reg [3:0] active;
	reg [32:0] rs1, rs2, rs1_q, rs2_q;
	reg [63:0] rd, rd_q;

	wire pcpi_insn_valid = pcpi_valid && pcpi_insn[6:0] == 7'b0110011 && pcpi_insn[31:25] == 7'b0000001;
	reg pcpi_insn_valid_q;
```

---
<!-- chunk_id=picorv32_picorv32_54 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2348–2363

```verilog
always @* begin
		instr_mul = 0;
		instr_mulh = 0;
		instr_mulhsu = 0;
		instr_mulhu = 0;

		if (resetn && (EXTRA_INSN_FFS ? pcpi_insn_valid_q : pcpi_insn_valid)) begin
			case (pcpi_insn[14:12])
				3'b000: instr_mul = 1;
				3'b001: instr_mulh = 1;
				3'b010: instr_mulhsu = 1;
				3'b011: instr_mulhu = 1;
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_55 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2364–2377

```verilog
always @(posedge clk) begin
		pcpi_insn_valid_q <= pcpi_insn_valid;
		if (!MUL_CLKGATE || active[0]) begin
			rs1_q <= rs1;
			rs2_q <= rs2;
		end
		if (!MUL_CLKGATE || active[1]) begin
			rd <= $signed(EXTRA_MUL_FFS ? rs1_q : rs1) * $signed(EXTRA_MUL_FFS ? rs2_q : rs2);
		end
		if (!MUL_CLKGATE || active[2]) begin
			rd_q <= rd;
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_56 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2378–2412

```verilog
always @(posedge clk) begin
		if (instr_any_mul && !(EXTRA_MUL_FFS ? active[3:0] : active[1:0])) begin
			if (instr_rs1_signed)
				rs1 <= $signed(pcpi_rs1);
			else
				rs1 <= $unsigned(pcpi_rs1);

			if (instr_rs2_signed)
				rs2 <= $signed(pcpi_rs2);
			else
				rs2 <= $unsigned(pcpi_rs2);
			active[0] <= 1;
		end else begin
			active[0] <= 0;
		end

		active[3:1] <= active;
		shift_out <= instr_any_mulh;

		if (!resetn)
			active <= 0;
	end

	assign pcpi_wr = active[EXTRA_MUL_FFS ? 3 : 1];
	assign pcpi_wait = 0;
	assign pcpi_ready = active[EXTRA_MUL_FFS ? 3 : 1];
`ifdef RISCV_FORMAL_ALTOPS
	assign pcpi_rd =
			instr_mul    ? (pcpi_rs1 + pcpi_rs2) ^ 32'h5876063e :
			instr_mulh   ? (pcpi_rs1 + pcpi_rs2) ^ 32'hf6583fb7 :
			instr_mulhsu ? (pcpi_rs1 - pcpi_rs2) ^ 32'hecfbe137 :
			instr_mulhu  ? (pcpi_rs1 + pcpi_rs2) ^ 32'h949ce5e8 : 1'bx;
`else
	assign pcpi_rd = shift_out ? (EXTRA_MUL_FFS ? rd_q : rd) >> 32 : (EXTRA_MUL_FFS ? rd_q : rd);
`endif
```

---
<!-- chunk_id=picorv32_picorv32_57 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2413–2419

```verilog
endmodule


/***************************************************************
 * picorv32_pcpi_div
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_58 | module picorv32_pcpi_div ( -->

# Verilog Block: `module picorv32_pcpi_div (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2420–2437

```verilog
module picorv32_pcpi_div (
	input clk, resetn,

	input             pcpi_valid,
	input      [31:0] pcpi_insn,
	input      [31:0] pcpi_rs1,
	input      [31:0] pcpi_rs2,
	output reg        pcpi_wr,
	output reg [31:0] pcpi_rd,
	output reg        pcpi_wait,
	output reg        pcpi_ready
);
	reg instr_div, instr_divu, instr_rem, instr_remu;
	wire instr_any_div_rem = |{instr_div, instr_divu, instr_rem, instr_remu};

	reg pcpi_wait_q;
	wire start = pcpi_wait && !pcpi_wait_q;
```

---
<!-- chunk_id=picorv32_picorv32_59 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2438–2463

```verilog
always @(posedge clk) begin
		instr_div <= 0;
		instr_divu <= 0;
		instr_rem <= 0;
		instr_remu <= 0;

		if (resetn && pcpi_valid && !pcpi_ready && pcpi_insn[6:0] == 7'b0110011 && pcpi_insn[31:25] == 7'b0000001) begin
			case (pcpi_insn[14:12])
				3'b100: instr_div <= 1;
				3'b101: instr_divu <= 1;
				3'b110: instr_rem <= 1;
				3'b111: instr_remu <= 1;
			endcase
		end

		pcpi_wait <= instr_any_div_rem && resetn;
		pcpi_wait_q <= pcpi_wait && resetn;
	end

	reg [31:0] dividend;
	reg [62:0] divisor;
	reg [31:0] quotient;
	reg [31:0] quotient_msk;
	reg running;
	reg outsign;
```

---
<!-- chunk_id=picorv32_picorv32_60 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2464–2509

```verilog
always @(posedge clk) begin
		pcpi_ready <= 0;
		pcpi_wr <= 0;
		pcpi_rd <= 'bx;

		if (!resetn) begin
			running <= 0;
		end else
		if (start) begin
			running <= 1;
			dividend <= (instr_div || instr_rem) && pcpi_rs1[31] ? -pcpi_rs1 : pcpi_rs1;
			divisor <= ((instr_div || instr_rem) && pcpi_rs2[31] ? -pcpi_rs2 : pcpi_rs2) << 31;
			outsign <= (instr_div && (pcpi_rs1[31] != pcpi_rs2[31]) && |pcpi_rs2) || (instr_rem && pcpi_rs1[31]);
			quotient <= 0;
			quotient_msk <= 1 << 31;
		end else
		if (!quotient_msk && running) begin
			running <= 0;
			pcpi_ready <= 1;
			pcpi_wr <= 1;
`ifdef RISCV_FORMAL_ALTOPS
			case (1)
				instr_div:  pcpi_rd <= (pcpi_rs1 - pcpi_rs2) ^ 32'h7f8529ec;
				instr_divu: pcpi_rd <= (pcpi_rs1 - pcpi_rs2) ^ 32'h10e8fd70;
				instr_rem:  pcpi_rd <= (pcpi_rs1 - pcpi_rs2) ^ 32'h8da68fa5;
				instr_remu: pcpi_rd <= (pcpi_rs1 - pcpi_rs2) ^ 32'h3138d0e1;
			endcase
`else
			if (instr_div || instr_divu)
				pcpi_rd <= outsign ? -quotient : quotient;
			else
				pcpi_rd <= outsign ? -dividend : dividend;
`endif
		end else begin
			if (divisor <= dividend) begin
				dividend <= dividend - divisor;
				quotient <= quotient | quotient_msk;
			end
			divisor <= divisor >> 1;
`ifdef RISCV_FORMAL_ALTOPS
			quotient_msk <= quotient_msk >> 5;
`else
			quotient_msk <= quotient_msk >> 1;
`endif
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_61 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2510–2516

```verilog
endmodule


/***************************************************************
 * picorv32_axi
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_62 | module picorv32_axi #( -->

# Verilog Block: `module picorv32_axi #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2517–2723

```verilog
module picorv32_axi #(
	parameter [ 0:0] ENABLE_COUNTERS = 1,
	parameter [ 0:0] ENABLE_COUNTERS64 = 1,
	parameter [ 0:0] ENABLE_REGS_16_31 = 1,
	parameter [ 0:0] ENABLE_REGS_DUALPORT = 1,
	parameter [ 0:0] TWO_STAGE_SHIFT = 1,
	parameter [ 0:0] BARREL_SHIFTER = 0,
	parameter [ 0:0] TWO_CYCLE_COMPARE = 0,
	parameter [ 0:0] TWO_CYCLE_ALU = 0,
	parameter [ 0:0] COMPRESSED_ISA = 0,
	parameter [ 0:0] CATCH_MISALIGN = 1,
	parameter [ 0:0] CATCH_ILLINSN = 1,
	parameter [ 0:0] ENABLE_PCPI = 0,
	parameter [ 0:0] ENABLE_MUL = 0,
	parameter [ 0:0] ENABLE_FAST_MUL = 0,
	parameter [ 0:0] ENABLE_DIV = 0,
	parameter [ 0:0] ENABLE_IRQ = 0,
	parameter [ 0:0] ENABLE_IRQ_QREGS = 1,
	parameter [ 0:0] ENABLE_IRQ_TIMER = 1,
	parameter [ 0:0] ENABLE_TRACE = 0,
	parameter [ 0:0] REGS_INIT_ZERO = 0,
	parameter [31:0] MASKED_IRQ = 32'h 0000_0000,
	parameter [31:0] LATCHED_IRQ = 32'h ffff_ffff,
	parameter [31:0] PROGADDR_RESET = 32'h 0000_0000,
	parameter [31:0] PROGADDR_IRQ = 32'h 0000_0010,
	parameter [31:0] STACKADDR = 32'h ffff_ffff
) (
	input clk, resetn,
	output trap,

	// AXI4-lite master memory interface

	output        mem_axi_awvalid,
	input         mem_axi_awready,
	output [31:0] mem_axi_awaddr,
	output [ 2:0] mem_axi_awprot,

	output        mem_axi_wvalid,
	input         mem_axi_wready,
	output [31:0] mem_axi_wdata,
	output [ 3:0] mem_axi_wstrb,

	input         mem_axi_bvalid,
	output        mem_axi_bready,

	output        mem_axi_arvalid,
	input         mem_axi_arready,
	output [31:0] mem_axi_araddr,
	output [ 2:0] mem_axi_arprot,

	input         mem_axi_rvalid,
	output        mem_axi_rready,
	input  [31:0] mem_axi_rdata,

	// Pico Co-Processor Interface (PCPI)
	output        pcpi_valid,
	output [31:0] pcpi_insn,
	output [31:0] pcpi_rs1,
	output [31:0] pcpi_rs2,
	input         pcpi_wr,
	input  [31:0] pcpi_rd,
	input         pcpi_wait,
	input         pcpi_ready,

	// IRQ interface
	input  [31:0] irq,
	output [31:0] eoi,

`ifdef RISCV_FORMAL
	output        rvfi_valid,
	output [63:0] rvfi_order,
	output [31:0] rvfi_insn,
	output        rvfi_trap,
	output        rvfi_halt,
	output        rvfi_intr,
	output [ 4:0] rvfi_rs1_addr,
	output [ 4:0] rvfi_rs2_addr,
	output [31:0] rvfi_rs1_rdata,
	output [31:0] rvfi_rs2_rdata,
	output [ 4:0] rvfi_rd_addr,
	output [31:0] rvfi_rd_wdata,
	output [31:0] rvfi_pc_rdata,
	output [31:0] rvfi_pc_wdata,
	output [31:0] rvfi_mem_addr,
	output [ 3:0] rvfi_mem_rmask,
	output [ 3:0] rvfi_mem_wmask,
	output [31:0] rvfi_mem_rdata,
	output [31:0] rvfi_mem_wdata,
`endif

	// Trace Interface
	output        trace_valid,
	output [35:0] trace_data
);
	wire        mem_valid;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [ 3:0] mem_wstrb;
	wire        mem_instr;
	wire        mem_ready;
	wire [31:0] mem_rdata;

	picorv32_axi_adapter axi_adapter (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.mem_axi_awvalid(mem_axi_awvalid),
		.mem_axi_awready(mem_axi_awready),
		.mem_axi_awaddr (mem_axi_awaddr ),
		.mem_axi_awprot (mem_axi_awprot ),
		.mem_axi_wvalid (mem_axi_wvalid ),
		.mem_axi_wready (mem_axi_wready ),
		.mem_axi_wdata  (mem_axi_wdata  ),
		.mem_axi_wstrb  (mem_axi_wstrb  ),
		.mem_axi_bvalid (mem_axi_bvalid ),
		.mem_axi_bready (mem_axi_bready ),
		.mem_axi_arvalid(mem_axi_arvalid),
		.mem_axi_arready(mem_axi_arready),
		.mem_axi_araddr (mem_axi_araddr ),
		.mem_axi_arprot (mem_axi_arprot ),
		.mem_axi_rvalid (mem_axi_rvalid ),
		.mem_axi_rready (mem_axi_rready ),
		.mem_axi_rdata  (mem_axi_rdata  ),
		.mem_valid      (mem_valid      ),
		.mem_instr      (mem_instr      ),
		.mem_ready      (mem_ready      ),
		.mem_addr       (mem_addr       ),
		.mem_wdata      (mem_wdata      ),
		.mem_wstrb      (mem_wstrb      ),
		.mem_rdata      (mem_rdata      )
	);

	picorv32 #(
		.ENABLE_COUNTERS     (ENABLE_COUNTERS     ),
		.ENABLE_COUNTERS64   (ENABLE_COUNTERS64   ),
		.ENABLE_REGS_16_31   (ENABLE_REGS_16_31   ),
		.ENABLE_REGS_DUALPORT(ENABLE_REGS_DUALPORT),
		.TWO_STAGE_SHIFT     (TWO_STAGE_SHIFT     ),
		.BARREL_SHIFTER      (BARREL_SHIFTER      ),
		.TWO_CYCLE_COMPARE   (TWO_CYCLE_COMPARE   ),
		.TWO_CYCLE_ALU       (TWO_CYCLE_ALU       ),
		.COMPRESSED_ISA      (COMPRESSED_ISA      ),
		.CATCH_MISALIGN      (CATCH_MISALIGN      ),
		.CATCH_ILLINSN       (CATCH_ILLINSN       ),
		.ENABLE_PCPI         (ENABLE_PCPI         ),
		.ENABLE_MUL          (ENABLE_MUL          ),
		.ENABLE_FAST_MUL     (ENABLE_FAST_MUL     ),
		.ENABLE_DIV          (ENABLE_DIV          ),
		.ENABLE_IRQ          (ENABLE_IRQ          ),
		.ENABLE_IRQ_QREGS    (ENABLE_IRQ_QREGS    ),
		.ENABLE_IRQ_TIMER    (ENABLE_IRQ_TIMER    ),
		.ENABLE_TRACE        (ENABLE_TRACE        ),
		.REGS_INIT_ZERO      (REGS_INIT_ZERO      ),
		.MASKED_IRQ          (MASKED_IRQ          ),
		.LATCHED_IRQ         (LATCHED_IRQ         ),
		.PROGADDR_RESET      (PROGADDR_RESET      ),
		.PROGADDR_IRQ        (PROGADDR_IRQ        ),
		.STACKADDR           (STACKADDR           )
	) picorv32_core (
		.clk      (clk   ),
		.resetn   (resetn),
		.trap     (trap  ),

		.mem_valid(mem_valid),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_rdata(mem_rdata),

		.pcpi_valid(pcpi_valid),
		.pcpi_insn (pcpi_insn ),
		.pcpi_rs1  (pcpi_rs1  ),
		.pcpi_rs2  (pcpi_rs2  ),
		.pcpi_wr   (pcpi_wr   ),
		.pcpi_rd   (pcpi_rd   ),
		.pcpi_wait (pcpi_wait ),
		.pcpi_ready(pcpi_ready),

		.irq(irq),
		.eoi(eoi),

`ifdef RISCV_FORMAL
		.rvfi_valid    (rvfi_valid    ),
		.rvfi_order    (rvfi_order    ),
		.rvfi_insn     (rvfi_insn     ),
		.rvfi_trap     (rvfi_trap     ),
		.rvfi_halt     (rvfi_halt     ),
		.rvfi_intr     (rvfi_intr     ),
		.rvfi_rs1_addr (rvfi_rs1_addr ),
		.rvfi_rs2_addr (rvfi_rs2_addr ),
		.rvfi_rs1_rdata(rvfi_rs1_rdata),
		.rvfi_rs2_rdata(rvfi_rs2_rdata),
		.rvfi_rd_addr  (rvfi_rd_addr  ),
		.rvfi_rd_wdata (rvfi_rd_wdata ),
		.rvfi_pc_rdata (rvfi_pc_rdata ),
		.rvfi_pc_wdata (rvfi_pc_wdata ),
		.rvfi_mem_addr (rvfi_mem_addr ),
		.rvfi_mem_rmask(rvfi_mem_rmask),
		.rvfi_mem_wmask(rvfi_mem_wmask),
		.rvfi_mem_rdata(rvfi_mem_rdata),
		.rvfi_mem_wdata(rvfi_mem_wdata),
`endif

		.trace_valid(trace_valid),
		.trace_data (trace_data)
	);
```

---
<!-- chunk_id=picorv32_picorv32_63 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2724–2730

```verilog
endmodule


/***************************************************************
 * picorv32_axi_adapter
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_64 | module picorv32_axi_adapter ( -->

# Verilog Block: `module picorv32_axi_adapter (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2731–2789

```verilog
module picorv32_axi_adapter (
	input clk, resetn,

	// AXI4-lite master memory interface

	output        mem_axi_awvalid,
	input         mem_axi_awready,
	output [31:0] mem_axi_awaddr,
	output [ 2:0] mem_axi_awprot,

	output        mem_axi_wvalid,
	input         mem_axi_wready,
	output [31:0] mem_axi_wdata,
	output [ 3:0] mem_axi_wstrb,

	input         mem_axi_bvalid,
	output        mem_axi_bready,

	output        mem_axi_arvalid,
	input         mem_axi_arready,
	output [31:0] mem_axi_araddr,
	output [ 2:0] mem_axi_arprot,

	input         mem_axi_rvalid,
	output        mem_axi_rready,
	input  [31:0] mem_axi_rdata,

	// Native PicoRV32 memory interface

	input         mem_valid,
	input         mem_instr,
	output        mem_ready,
	input  [31:0] mem_addr,
	input  [31:0] mem_wdata,
	input  [ 3:0] mem_wstrb,
	output [31:0] mem_rdata
);
	reg ack_awvalid;
	reg ack_arvalid;
	reg ack_wvalid;
	reg xfer_done;

	assign mem_axi_awvalid = mem_valid && |mem_wstrb && !ack_awvalid;
	assign mem_axi_awaddr = mem_addr;
	assign mem_axi_awprot = 0;

	assign mem_axi_arvalid = mem_valid && !mem_wstrb && !ack_arvalid;
	assign mem_axi_araddr = mem_addr;
	assign mem_axi_arprot = mem_instr ? 3'b100 : 3'b000;

	assign mem_axi_wvalid = mem_valid && |mem_wstrb && !ack_wvalid;
	assign mem_axi_wdata = mem_wdata;
	assign mem_axi_wstrb = mem_wstrb;

	assign mem_ready = mem_axi_bvalid || mem_axi_rvalid;
	assign mem_axi_bready = mem_valid && |mem_wstrb;
	assign mem_axi_rready = mem_valid && !mem_wstrb;
	assign mem_rdata = mem_axi_rdata;
```

---
<!-- chunk_id=picorv32_picorv32_65 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2790–2807

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			ack_awvalid <= 0;
		end else begin
			xfer_done <= mem_valid && mem_ready;
			if (mem_axi_awready && mem_axi_awvalid)
				ack_awvalid <= 1;
			if (mem_axi_arready && mem_axi_arvalid)
				ack_arvalid <= 1;
			if (mem_axi_wready && mem_axi_wvalid)
				ack_wvalid <= 1;
			if (xfer_done || !mem_valid) begin
				ack_awvalid <= 0;
				ack_arvalid <= 0;
				ack_wvalid <= 0;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picorv32_66 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2808–2814

```verilog
endmodule


/***************************************************************
 * picorv32_wb
 ***************************************************************/
```

---
<!-- chunk_id=picorv32_picorv32_67 | module picorv32_wb #( -->

# Verilog Block: `module picorv32_wb #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2815–2997

```verilog
module picorv32_wb #(
	parameter [ 0:0] ENABLE_COUNTERS = 1,
	parameter [ 0:0] ENABLE_COUNTERS64 = 1,
	parameter [ 0:0] ENABLE_REGS_16_31 = 1,
	parameter [ 0:0] ENABLE_REGS_DUALPORT = 1,
	parameter [ 0:0] TWO_STAGE_SHIFT = 1,
	parameter [ 0:0] BARREL_SHIFTER = 0,
	parameter [ 0:0] TWO_CYCLE_COMPARE = 0,
	parameter [ 0:0] TWO_CYCLE_ALU = 0,
	parameter [ 0:0] COMPRESSED_ISA = 0,
	parameter [ 0:0] CATCH_MISALIGN = 1,
	parameter [ 0:0] CATCH_ILLINSN = 1,
	parameter [ 0:0] ENABLE_PCPI = 0,
	parameter [ 0:0] ENABLE_MUL = 0,
	parameter [ 0:0] ENABLE_FAST_MUL = 0,
	parameter [ 0:0] ENABLE_DIV = 0,
	parameter [ 0:0] ENABLE_IRQ = 0,
	parameter [ 0:0] ENABLE_IRQ_QREGS = 1,
	parameter [ 0:0] ENABLE_IRQ_TIMER = 1,
	parameter [ 0:0] ENABLE_TRACE = 0,
	parameter [ 0:0] REGS_INIT_ZERO = 0,
	parameter [31:0] MASKED_IRQ = 32'h 0000_0000,
	parameter [31:0] LATCHED_IRQ = 32'h ffff_ffff,
	parameter [31:0] PROGADDR_RESET = 32'h 0000_0000,
	parameter [31:0] PROGADDR_IRQ = 32'h 0000_0010,
	parameter [31:0] STACKADDR = 32'h ffff_ffff
) (
	output trap,

	// Wishbone interfaces
	input wb_rst_i,
	input wb_clk_i,

	output reg [31:0] wbm_adr_o,
	output reg [31:0] wbm_dat_o,
	input [31:0] wbm_dat_i,
	output reg wbm_we_o,
	output reg [3:0] wbm_sel_o,
	output reg wbm_stb_o,
	input wbm_ack_i,
	output reg wbm_cyc_o,

	// Pico Co-Processor Interface (PCPI)
	output        pcpi_valid,
	output [31:0] pcpi_insn,
	output [31:0] pcpi_rs1,
	output [31:0] pcpi_rs2,
	input         pcpi_wr,
	input  [31:0] pcpi_rd,
	input         pcpi_wait,
	input         pcpi_ready,

	// IRQ interface
	input  [31:0] irq,
	output [31:0] eoi,

`ifdef RISCV_FORMAL
	output        rvfi_valid,
	output [63:0] rvfi_order,
	output [31:0] rvfi_insn,
	output        rvfi_trap,
	output        rvfi_halt,
	output        rvfi_intr,
	output [ 4:0] rvfi_rs1_addr,
	output [ 4:0] rvfi_rs2_addr,
	output [31:0] rvfi_rs1_rdata,
	output [31:0] rvfi_rs2_rdata,
	output [ 4:0] rvfi_rd_addr,
	output [31:0] rvfi_rd_wdata,
	output [31:0] rvfi_pc_rdata,
	output [31:0] rvfi_pc_wdata,
	output [31:0] rvfi_mem_addr,
	output [ 3:0] rvfi_mem_rmask,
	output [ 3:0] rvfi_mem_wmask,
	output [31:0] rvfi_mem_rdata,
	output [31:0] rvfi_mem_wdata,
`endif

	// Trace Interface
	output        trace_valid,
	output [35:0] trace_data,

	output mem_instr
);
	wire        mem_valid;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [ 3:0] mem_wstrb;
	reg         mem_ready;
	reg [31:0] mem_rdata;

	wire clk;
	wire resetn;

	assign clk = wb_clk_i;
	assign resetn = ~wb_rst_i;

	picorv32 #(
		.ENABLE_COUNTERS     (ENABLE_COUNTERS     ),
		.ENABLE_COUNTERS64   (ENABLE_COUNTERS64   ),
		.ENABLE_REGS_16_31   (ENABLE_REGS_16_31   ),
		.ENABLE_REGS_DUALPORT(ENABLE_REGS_DUALPORT),
		.TWO_STAGE_SHIFT     (TWO_STAGE_SHIFT     ),
		.BARREL_SHIFTER      (BARREL_SHIFTER      ),
		.TWO_CYCLE_COMPARE   (TWO_CYCLE_COMPARE   ),
		.TWO_CYCLE_ALU       (TWO_CYCLE_ALU       ),
		.COMPRESSED_ISA      (COMPRESSED_ISA      ),
		.CATCH_MISALIGN      (CATCH_MISALIGN      ),
		.CATCH_ILLINSN       (CATCH_ILLINSN       ),
		.ENABLE_PCPI         (ENABLE_PCPI         ),
		.ENABLE_MUL          (ENABLE_MUL          ),
		.ENABLE_FAST_MUL     (ENABLE_FAST_MUL     ),
		.ENABLE_DIV          (ENABLE_DIV          ),
		.ENABLE_IRQ          (ENABLE_IRQ          ),
		.ENABLE_IRQ_QREGS    (ENABLE_IRQ_QREGS    ),
		.ENABLE_IRQ_TIMER    (ENABLE_IRQ_TIMER    ),
		.ENABLE_TRACE        (ENABLE_TRACE        ),
		.REGS_INIT_ZERO      (REGS_INIT_ZERO      ),
		.MASKED_IRQ          (MASKED_IRQ          ),
		.LATCHED_IRQ         (LATCHED_IRQ         ),
		.PROGADDR_RESET      (PROGADDR_RESET      ),
		.PROGADDR_IRQ        (PROGADDR_IRQ        ),
		.STACKADDR           (STACKADDR           )
	) picorv32_core (
		.clk      (clk   ),
		.resetn   (resetn),
		.trap     (trap  ),

		.mem_valid(mem_valid),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_rdata(mem_rdata),

		.pcpi_valid(pcpi_valid),
		.pcpi_insn (pcpi_insn ),
		.pcpi_rs1  (pcpi_rs1  ),
		.pcpi_rs2  (pcpi_rs2  ),
		.pcpi_wr   (pcpi_wr   ),
		.pcpi_rd   (pcpi_rd   ),
		.pcpi_wait (pcpi_wait ),
		.pcpi_ready(pcpi_ready),

		.irq(irq),
		.eoi(eoi),

`ifdef RISCV_FORMAL
		.rvfi_valid    (rvfi_valid    ),
		.rvfi_order    (rvfi_order    ),
		.rvfi_insn     (rvfi_insn     ),
		.rvfi_trap     (rvfi_trap     ),
		.rvfi_halt     (rvfi_halt     ),
		.rvfi_intr     (rvfi_intr     ),
		.rvfi_rs1_addr (rvfi_rs1_addr ),
		.rvfi_rs2_addr (rvfi_rs2_addr ),
		.rvfi_rs1_rdata(rvfi_rs1_rdata),
		.rvfi_rs2_rdata(rvfi_rs2_rdata),
		.rvfi_rd_addr  (rvfi_rd_addr  ),
		.rvfi_rd_wdata (rvfi_rd_wdata ),
		.rvfi_pc_rdata (rvfi_pc_rdata ),
		.rvfi_pc_wdata (rvfi_pc_wdata ),
		.rvfi_mem_addr (rvfi_mem_addr ),
		.rvfi_mem_rmask(rvfi_mem_rmask),
		.rvfi_mem_wmask(rvfi_mem_wmask),
		.rvfi_mem_rdata(rvfi_mem_rdata),
		.rvfi_mem_wdata(rvfi_mem_wdata),
`endif

		.trace_valid(trace_valid),
		.trace_data (trace_data)
	);

	localparam IDLE = 2'b00;
	localparam WBSTART = 2'b01;
	localparam WBEND = 2'b10;

	reg [1:0] state;

	wire we;
	assign we = (mem_wstrb[0] | mem_wstrb[1] | mem_wstrb[2] | mem_wstrb[3]);
```

---
<!-- chunk_id=picorv32_picorv32_68 | always @(posedge wb_clk_i) begin -->

# Verilog Block: `always @(posedge wb_clk_i) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picorv32.v` | Lines 2998–3048

```verilog
always @(posedge wb_clk_i) begin
		if (wb_rst_i) begin
			wbm_adr_o <= 0;
			wbm_dat_o <= 0;
			wbm_we_o <= 0;
			wbm_sel_o <= 0;
			wbm_stb_o <= 0;
			wbm_cyc_o <= 0;
			state <= IDLE;
		end else begin
			case (state)
				IDLE: begin
					if (mem_valid) begin
						wbm_adr_o <= mem_addr;
						wbm_dat_o <= mem_wdata;
						wbm_we_o <= we;
						wbm_sel_o <= mem_wstrb;

						wbm_stb_o <= 1'b1;
						wbm_cyc_o <= 1'b1;
						state <= WBSTART;
					end else begin
						mem_ready <= 1'b0;

						wbm_stb_o <= 1'b0;
						wbm_cyc_o <= 1'b0;
						wbm_we_o <= 1'b0;
					end
				end
				WBSTART:begin
					if (wbm_ack_i) begin
						mem_rdata <= wbm_dat_i;
						mem_ready <= 1'b1;

						state <= WBEND;

						wbm_stb_o <= 1'b0;
						wbm_cyc_o <= 1'b0;
						wbm_we_o <= 1'b0;
					end
				end
				WBEND: begin
					mem_ready <= 1'b0;

					state <= IDLE;
				end
				default:
					state <= IDLE;
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_Makefile_0 | ---- iCE40 HX8K Breakout Board ---- -->

# ---- iCE40 HX8K Breakout Board ----

hx8ksim: hx8kdemo_tb.vvp hx8kdemo_fw.hex
	vvp -N $< +firmware=hx8kdemo_fw.hex

hx8ksynsim: hx8kdemo_syn_tb.vvp hx8kdemo_fw.hex
	vvp -N $< +firmware=hx8kdemo_fw.hex

hx8kdemo.json: hx8kdemo.v spimemio.v simpleuart.v picosoc.v ../picorv32.v
	yosys -ql hx8kdemo.log -p 'synth_ice40 -top hx8kdemo -json hx8kdemo.json' $^

hx8kdemo_tb.vvp: hx8kdemo_tb.v hx8kdemo.v spimemio.v simpleuart.v picosoc.v ../picorv32.v spiflash.v
	iverilog -s testbench -o $@ $^ `yosys-config --datdir/ice40/cells_sim.v` -DNO_ICE40_DEFAULT_ASSIGNMENTS

hx8kdemo_syn_tb.vvp: hx8kdemo_tb.v hx8kdemo_syn.v spiflash.v
	iverilog -s testbench -o $@ $^ `yosys-config --datdir/ice40/cells_sim.v` -DNO_ICE40_DEFAULT_ASSIGNMENTS

hx8kdemo_syn.v: hx8kdemo.json
	yosys -p 'read_json hx8kdemo.json; write_verilog hx8kdemo_syn.v'

hx8kdemo.asc: hx8kdemo.pcf hx8kdemo.json
	nextpnr-ice40 --hx8k --package ct256 --asc hx8kdemo.asc --json hx8kdemo.json --pcf hx8kdemo.pcf

hx8kdemo.bin: hx8kdemo.asc
	icetime -d hx8k -c 12 -mtr hx8kdemo.rpt hx8kdemo.asc
	icepack hx8kdemo.asc hx8kdemo.bin

hx8kprog: hx8kdemo.bin hx8kdemo_fw.bin
	iceprog hx8kdemo.bin
	iceprog -o 1M hx8kdemo_fw.bin

hx8kprog_fw: hx8kdemo_fw.bin
	iceprog -o 1M hx8kdemo_fw.bin

hx8kdemo_sections.lds: sections.lds
	$(CROSS)cpp -P -DHX8KDEMO -o $@ $^

hx8kdemo_fw.elf: hx8kdemo_sections.lds start.s firmware.c
	$(CROSS)gcc $(CFLAGS) -DHX8KDEMO -mabi=ilp32 -march=rv32imc -Wl,--build-id=none,-Bstatic,-T,hx8kdemo_sections.lds,--strip-debug -ffreestanding -nostdlib -o hx8kdemo_fw.elf start.s firmware.c

hx8kdemo_fw.hex: hx8kdemo_fw.elf
	$(CROSS)objcopy -O verilog hx8kdemo_fw.elf hx8kdemo_fw.hex

hx8kdemo_fw.bin: hx8kdemo_fw.elf
	$(CROSS)objcopy -O binary hx8kdemo_fw.elf hx8kdemo_fw.bin

---
<!-- chunk_id=picorv32_picosoc_Makefile_1 | ---- iCE40 IceBreaker Board ---- -->

# ---- iCE40 IceBreaker Board ----

icebsim: icebreaker_tb.vvp icebreaker_fw.hex
	vvp -N $< +firmware=icebreaker_fw.hex

icebsynsim: icebreaker_syn_tb.vvp icebreaker_fw.hex
	vvp -N $< +firmware=icebreaker_fw.hex

icebreaker.json: icebreaker.v ice40up5k_spram.v spimemio.v simpleuart.v picosoc.v ../picorv32.v
	yosys -ql icebreaker.log -p 'synth_ice40 -dsp -top icebreaker -json icebreaker.json' $^

icebreaker_tb.vvp: icebreaker_tb.v icebreaker.v ice40up5k_spram.v spimemio.v simpleuart.v picosoc.v ../picorv32.v spiflash.v
	iverilog -s testbench -o $@ $^ `yosys-config --datdir/ice40/cells_sim.v` -DNO_ICE40_DEFAULT_ASSIGNMENTS

icebreaker_syn_tb.vvp: icebreaker_tb.v icebreaker_syn.v spiflash.v
	iverilog -s testbench -o $@ $^ `yosys-config --datdir/ice40/cells_sim.v` -DNO_ICE40_DEFAULT_ASSIGNMENTS

icebreaker_syn.v: icebreaker.json
	yosys -p 'read_json icebreaker.json; write_verilog icebreaker_syn.v'

icebreaker.asc: icebreaker.pcf icebreaker.json
	nextpnr-ice40 --freq 13 --up5k --package sg48 --asc icebreaker.asc --pcf icebreaker.pcf --json icebreaker.json

icebreaker.bin: icebreaker.asc
	icetime -d up5k -c 12 -mtr icebreaker.rpt icebreaker.asc
	icepack icebreaker.asc icebreaker.bin

icebprog: icebreaker.bin icebreaker_fw.bin
	iceprog icebreaker.bin
	iceprog -o 1M icebreaker_fw.bin

icebprog_fw: icebreaker_fw.bin
	iceprog -o 1M icebreaker_fw.bin

icebreaker_sections.lds: sections.lds
	$(CROSS)cpp -P -DICEBREAKER -o $@ $^

icebreaker_fw.elf: icebreaker_sections.lds start.s firmware.c
	$(CROSS)gcc $(CFLAGS) -DICEBREAKER -mabi=ilp32 -march=rv32ic -Wl,-Bstatic,-T,icebreaker_sections.lds,--strip-debug -ffreestanding -nostdlib -o icebreaker_fw.elf start.s firmware.c

icebreaker_fw.hex: icebreaker_fw.elf
	$(CROSS)objcopy -O verilog icebreaker_fw.elf icebreaker_fw.hex

icebreaker_fw.bin: icebreaker_fw.elf
	$(CROSS)objcopy -O binary icebreaker_fw.elf icebreaker_fw.bin

---
<!-- chunk_id=picorv32_picosoc_Makefile_2 | ---- Testbench for SPI Flash Model ---- -->

# ---- Testbench for SPI Flash Model ----

spiflash_tb: spiflash_tb.vvp icebreaker_fw.hex
	vvp -N $< +firmware=icebreaker_fw.hex

spiflash_tb.vvp: spiflash.v spiflash_tb.v
	iverilog -s testbench -o $@ $^

---
<!-- chunk_id=picorv32_picosoc_Makefile_3 | ---- ASIC Synthesis Tests ---- -->

# ---- ASIC Synthesis Tests ----

cmos.log: spimemio.v simpleuart.v picosoc.v ../picorv32.v
	yosys -l cmos.log -p 'synth -top picosoc; abc -g cmos2; opt -fast; stat' $^

---
<!-- chunk_id=picorv32_picosoc_Makefile_4 | ---- Clean ---- -->

# ---- Clean ----

clean:
	rm -f testbench.vvp testbench.vcd spiflash_tb.vvp spiflash_tb.vcd
	rm -f hx8kdemo_fw.elf hx8kdemo_fw.hex hx8kdemo_fw.bin cmos.log
	rm -f icebreaker_fw.elf icebreaker_fw.hex icebreaker_fw.bin
	rm -f hx8kdemo.json hx8kdemo.log hx8kdemo.asc hx8kdemo.rpt hx8kdemo.bin
	rm -f hx8kdemo_syn.v hx8kdemo_syn_tb.vvp hx8kdemo_tb.vvp
	rm -f icebreaker.json icebreaker.log icebreaker.asc icebreaker.rpt icebreaker.bin
	rm -f icebreaker_syn.v icebreaker_syn_tb.vvp icebreaker_tb.vvp

.PHONY: spiflash_tb clean
.PHONY: hx8kprog hx8kprog_fw hx8ksim hx8ksynsim
.PHONY: icebprog icebprog_fw icebsim icebsynsim

---
<!-- chunk_id=picorv32_picosoc_README_0 | Memory map: -->

### Memory map:

| Address Range            | Description                             |
| ------------------------ | --------------------------------------- |
| 0x00000000 .. 0x00FFFFFF | Internal SRAM                           |
| 0x01000000 .. 0x01FFFFFF | External Serial Flash                   |
| 0x02000000 .. 0x02000003 | SPI Flash Controller Config Register    |
| 0x02000004 .. 0x02000007 | UART Clock Divider Register             |
| 0x02000008 .. 0x0200000B | UART Send/Recv Data Register            |
| 0x03000000 .. 0xFFFFFFFF | Memory mapped user peripherals          |

Reading from the addresses in the internal SRAM region beyond the end of the
physical SRAM will read from the corresponding addresses in serial flash.

Reading from the UART Send/Recv Data Register will return the last received
byte, or -1 (all 32 bits set) when the receive buffer is empty.

The UART Clock Divider Register must be set to the system clock frequency
divided by the baud rate.

The example design (hx8kdemo.v) has the 8 LEDs on the iCE40-HX8K Breakout Board
mapped to the low byte of the 32 bit word at address 0x03000000.

---
<!-- chunk_id=picorv32_picosoc_README_1 | SPI Flash Controller Config Register: -->

### SPI Flash Controller Config Register:

| Bit(s) | Description                                               |
| -----: | --------------------------------------------------------- |
|     31 | MEMIO Enable (reset=1, set to 0 to bit bang SPI commands) |
|  30:23 | Reserved (read 0)                                         |
|     22 | DDR Enable bit (reset=0)                                  |
|     21 | QSPI Enable bit (reset=0)                                 |
|     20 | CRM Enable bit (reset=0)                                  |
|  19:16 | Read latency (dummy) cycles (reset=8)                     |
|  15:12 | Reserved (read 0)                                         |
|   11:8 | IO Output enable bits in bit bang mode                    |
|    7:6 | Reserved (read 0)                                         |
|      5 | Chip select (CS) line in bit bang mode                    |
|      4 | Serial clock line in bit bang mode                        |
|    3:0 | IO data bits in bit bang mode                             |

The following settings for CRM/DDR/QSPI modes are valid:

| CRM | QSPI | DDR | Read Command Byte     | Mode Byte |
| :-: | :--: | :-: | :-------------------- | :-------: |
|   0 |    0 |   0 | 03h Read              | N/A       |
|   0 |    0 |   1 | BBh Dual I/O Read     | FFh       |
|   1 |    0 |   1 | BBh Dual I/O Read     | A5h       |
|   0 |    1 |   0 | EBh Quad I/O Read     | FFh       |
|   1 |    1 |   0 | EBh Quad I/O Read     | A5h       |
|   0 |    1 |   1 | EDh DDR Quad I/O Read | FFh       |
|   1 |    1 |   1 | EDh DDR Quad I/O Read | A5h       |

The following plot visualizes the relative performance of the different configurations:

![](performance.png)

Consult the datasheet for your SPI flash to learn which configurations are supported
by the chip and what the maximum clock frequencies are for each configuration.

For Quad I/O mode the QUAD flag in CR1V must be set before enabling Quad I/O in the
SPI master. Either set it by writing the corresponding bit in CR1NV once, or by writing
it from your device firmware at every bootup. (See `set_flash_qspi_flag()` in
`firmware.c` for an example for the latter.)

Note that some changes to the Lattice iCE40-HX8K Breakout Board are required to support
the faster configurations: (1) The flash chip must be replaced with one that supports the
faster read commands and (2) the IO2 and IO3 pins on the flash chip must be connected to
the FPGA IO pins T9 and T8 (near the center of J3).

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo.v` | Lines 1–19

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_1 | module hx8kdemo ( -->

# Verilog Block: `module hx8kdemo (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo.v` | Lines 20–47

```verilog
module hx8kdemo (
	input clk,

	output ser_tx,
	input ser_rx,

	output [7:0] leds,

	output flash_csb,
	output flash_clk,
	inout  flash_io0,
	inout  flash_io1,
	inout  flash_io2,
	inout  flash_io3,

	output debug_ser_tx,
	output debug_ser_rx,

	output debug_flash_csb,
	output debug_flash_clk,
	output debug_flash_io0,
	output debug_flash_io1,
	output debug_flash_io2,
	output debug_flash_io3
);
	reg [5:0] reset_cnt = 0;
	wire resetn = &reset_cnt;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo.v` | Lines 48–76

```verilog
always @(posedge clk) begin
		reset_cnt <= reset_cnt + !resetn;
	end

	wire flash_io0_oe, flash_io0_do, flash_io0_di;
	wire flash_io1_oe, flash_io1_do, flash_io1_di;
	wire flash_io2_oe, flash_io2_do, flash_io2_di;
	wire flash_io3_oe, flash_io3_do, flash_io3_di;

	SB_IO #(
		.PIN_TYPE(6'b 1010_01),
		.PULLUP(1'b 0)
	) flash_io_buf [3:0] (
		.PACKAGE_PIN({flash_io3, flash_io2, flash_io1, flash_io0}),
		.OUTPUT_ENABLE({flash_io3_oe, flash_io2_oe, flash_io1_oe, flash_io0_oe}),
		.D_OUT_0({flash_io3_do, flash_io2_do, flash_io1_do, flash_io0_do}),
		.D_IN_0({flash_io3_di, flash_io2_di, flash_io1_di, flash_io0_di})
	);

	wire        iomem_valid;
	reg         iomem_ready;
	wire [3:0]  iomem_wstrb;
	wire [31:0] iomem_addr;
	wire [31:0] iomem_wdata;
	reg  [31:0] iomem_rdata;

	reg [31:0] gpio;
	assign leds = gpio;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo.v` | Lines 77–138

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			gpio <= 0;
		end else begin
			iomem_ready <= 0;
			if (iomem_valid && !iomem_ready && iomem_addr[31:24] == 8'h 03) begin
				iomem_ready <= 1;
				iomem_rdata <= gpio;
				if (iomem_wstrb[0]) gpio[ 7: 0] <= iomem_wdata[ 7: 0];
				if (iomem_wstrb[1]) gpio[15: 8] <= iomem_wdata[15: 8];
				if (iomem_wstrb[2]) gpio[23:16] <= iomem_wdata[23:16];
				if (iomem_wstrb[3]) gpio[31:24] <= iomem_wdata[31:24];
			end
		end
	end

	picosoc soc (
		.clk          (clk         ),
		.resetn       (resetn      ),

		.ser_tx       (ser_tx      ),
		.ser_rx       (ser_rx      ),

		.flash_csb    (flash_csb   ),
		.flash_clk    (flash_clk   ),

		.flash_io0_oe (flash_io0_oe),
		.flash_io1_oe (flash_io1_oe),
		.flash_io2_oe (flash_io2_oe),
		.flash_io3_oe (flash_io3_oe),

		.flash_io0_do (flash_io0_do),
		.flash_io1_do (flash_io1_do),
		.flash_io2_do (flash_io2_do),
		.flash_io3_do (flash_io3_do),

		.flash_io0_di (flash_io0_di),
		.flash_io1_di (flash_io1_di),
		.flash_io2_di (flash_io2_di),
		.flash_io3_di (flash_io3_di),

		.irq_5        (1'b0        ),
		.irq_6        (1'b0        ),
		.irq_7        (1'b0        ),

		.iomem_valid  (iomem_valid ),
		.iomem_ready  (iomem_ready ),
		.iomem_wstrb  (iomem_wstrb ),
		.iomem_addr   (iomem_addr  ),
		.iomem_wdata  (iomem_wdata ),
		.iomem_rdata  (iomem_rdata )
	);

	assign debug_ser_tx = ser_tx;
	assign debug_ser_rx = ser_rx;

	assign debug_flash_csb = flash_csb;
	assign debug_flash_clk = flash_clk;
	assign debug_flash_io0 = flash_io0_di;
	assign debug_flash_io1 = flash_io1_di;
	assign debug_flash_io2 = flash_io2_di;
	assign debug_flash_io3 = flash_io3_di;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_tb_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo_tb.v` | Lines 1–21

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_tb_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo_tb.v` | Lines 22–28

```verilog
module testbench;
	reg clk;
	always #5 clk = (clk === 1'b0);

	localparam ser_half_period = 53;
	event ser_sample;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_tb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo_tb.v` | Lines 29–41

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);

		repeat (6) begin
			repeat (50000) @(posedge clk);
			$display("+50000 cycles");
		end
		$finish;
	end

	integer cycle_cnt = 0;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_tb_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo_tb.v` | Lines 42–57

```verilog
always @(posedge clk) begin
		cycle_cnt <= cycle_cnt + 1;
	end

	wire [7:0] leds;

	wire ser_rx;
	wire ser_tx;

	wire flash_csb;
	wire flash_clk;
	wire flash_io0;
	wire flash_io1;
	wire flash_io2;
	wire flash_io3;
```

---
<!-- chunk_id=picorv32_picosoc_hx8kdemo_tb_4 | always @(leds) begin -->

# Verilog Block: `always @(leds) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/hx8kdemo_tb.v` | Lines 58–107

```verilog
always @(leds) begin
		#1 $display("%b", leds);
	end

	hx8kdemo uut (
		.clk      (clk      ),
		.leds     (leds     ),
		.ser_rx   (ser_rx   ),
		.ser_tx   (ser_tx   ),
		.flash_csb(flash_csb),
		.flash_clk(flash_clk),
		.flash_io0(flash_io0),
		.flash_io1(flash_io1),
		.flash_io2(flash_io2),
		.flash_io3(flash_io3)
	);

	spiflash spiflash (
		.csb(flash_csb),
		.clk(flash_clk),
		.io0(flash_io0),
		.io1(flash_io1),
		.io2(flash_io2),
		.io3(flash_io3)
	);

	reg [7:0] buffer;

	always begin
		@(negedge ser_tx);

		repeat (ser_half_period) @(posedge clk);
		-> ser_sample; // start bit

		repeat (8) begin
			repeat (ser_half_period) @(posedge clk);
			repeat (ser_half_period) @(posedge clk);
			buffer = {ser_tx, buffer[7:1]};
			-> ser_sample; // data bit
		end

		repeat (ser_half_period) @(posedge clk);
		repeat (ser_half_period) @(posedge clk);
		-> ser_sample; // stop bit

		if (buffer < 32 || buffer >= 127)
			$display("Serial data: %d", buffer);
		else
			$display("Serial data: '%c'", buffer);
	end
```

---
<!-- chunk_id=picorv32_picosoc_ice40up5k_spram_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/ice40up5k_spram.v` | Lines 1–20

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */
```

---
<!-- chunk_id=picorv32_picosoc_ice40up5k_spram_1 | module ice40up5k_spram #( -->

# Verilog Block: `module ice40up5k_spram #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/ice40up5k_spram.v` | Lines 21–90

```verilog
module ice40up5k_spram #(
	// We current always use the whole SPRAM (128 kB)
	parameter integer WORDS = 32768
) (
	input clk,
	input [3:0] wen,
	input [21:0] addr,
	input [31:0] wdata,
	output [31:0] rdata
);

	wire cs_0, cs_1;
	wire [31:0] rdata_0, rdata_1;

	assign cs_0 = !addr[14];
	assign cs_1 = addr[14];
	assign rdata = addr[14] ? rdata_1 : rdata_0;

	SB_SPRAM256KA ram00 (
		.ADDRESS(addr[13:0]),
		.DATAIN(wdata[15:0]),
		.MASKWREN({wen[1], wen[1], wen[0], wen[0]}),
		.WREN(wen[1]|wen[0]),
		.CHIPSELECT(cs_0),
		.CLOCK(clk),
		.STANDBY(1'b0),
		.SLEEP(1'b0),
		.POWEROFF(1'b1),
		.DATAOUT(rdata_0[15:0])
	);

	SB_SPRAM256KA ram01 (
		.ADDRESS(addr[13:0]),
		.DATAIN(wdata[31:16]),
		.MASKWREN({wen[3], wen[3], wen[2], wen[2]}),
		.WREN(wen[3]|wen[2]),
		.CHIPSELECT(cs_0),
		.CLOCK(clk),
		.STANDBY(1'b0),
		.SLEEP(1'b0),
		.POWEROFF(1'b1),
		.DATAOUT(rdata_0[31:16])
	);

	SB_SPRAM256KA ram10 (
		.ADDRESS(addr[13:0]),
		.DATAIN(wdata[15:0]),
		.MASKWREN({wen[1], wen[1], wen[0], wen[0]}),
		.WREN(wen[1]|wen[0]),
		.CHIPSELECT(cs_1),
		.CLOCK(clk),
		.STANDBY(1'b0),
		.SLEEP(1'b0),
		.POWEROFF(1'b1),
		.DATAOUT(rdata_1[15:0])
	);

	SB_SPRAM256KA ram11 (
		.ADDRESS(addr[13:0]),
		.DATAIN(wdata[31:16]),
		.MASKWREN({wen[3], wen[3], wen[2], wen[2]}),
		.WREN(wen[3]|wen[2]),
		.CHIPSELECT(cs_1),
		.CLOCK(clk),
		.STANDBY(1'b0),
		.SLEEP(1'b0),
		.POWEROFF(1'b1),
		.DATAOUT(rdata_1[31:16])
	);
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker.v` | Lines 1–23

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`ifdef PICOSOC_V
`error "icebreaker.v must be read before picosoc.v!"
`endif
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_1 | `define PICOSOC_MEM ice40up5k_spram -->

# Verilog Block: ``define PICOSOC_MEM ice40up5k_spram`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker.v` | Lines 24–25

```verilog
`define PICOSOC_MEM ice40up5k_spram
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_2 | module icebreaker ( -->

# Verilog Block: `module icebreaker (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker.v` | Lines 26–52

```verilog
module icebreaker (
	input clk,

	output ser_tx,
	input ser_rx,

	output led1,
	output led2,
	output led3,
	output led4,
	output led5,

	output ledr_n,
	output ledg_n,

	output flash_csb,
	output flash_clk,
	inout  flash_io0,
	inout  flash_io1,
	inout  flash_io2,
	inout  flash_io3
);
	parameter integer MEM_WORDS = 32768;

	reg [5:0] reset_cnt = 0;
	wire resetn = &reset_cnt;
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker.v` | Lines 53–92

```verilog
always @(posedge clk) begin
		reset_cnt <= reset_cnt + !resetn;
	end

	wire [7:0] leds;

	assign led1 = leds[1];
	assign led2 = leds[2];
	assign led3 = leds[3];
	assign led4 = leds[4];
	assign led5 = leds[5];

	assign ledr_n = !leds[6];
	assign ledg_n = !leds[7];

	wire flash_io0_oe, flash_io0_do, flash_io0_di;
	wire flash_io1_oe, flash_io1_do, flash_io1_di;
	wire flash_io2_oe, flash_io2_do, flash_io2_di;
	wire flash_io3_oe, flash_io3_do, flash_io3_di;

	SB_IO #(
		.PIN_TYPE(6'b 1010_01),
		.PULLUP(1'b 0)
	) flash_io_buf [3:0] (
		.PACKAGE_PIN({flash_io3, flash_io2, flash_io1, flash_io0}),
		.OUTPUT_ENABLE({flash_io3_oe, flash_io2_oe, flash_io1_oe, flash_io0_oe}),
		.D_OUT_0({flash_io3_do, flash_io2_do, flash_io1_do, flash_io0_do}),
		.D_IN_0({flash_io3_di, flash_io2_di, flash_io1_di, flash_io0_di})
	);

	wire        iomem_valid;
	reg         iomem_ready;
	wire [3:0]  iomem_wstrb;
	wire [31:0] iomem_addr;
	wire [31:0] iomem_wdata;
	reg  [31:0] iomem_rdata;

	reg [31:0] gpio;
	assign leds = gpio;
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker.v` | Lines 93–150

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			gpio <= 0;
		end else begin
			iomem_ready <= 0;
			if (iomem_valid && !iomem_ready && iomem_addr[31:24] == 8'h 03) begin
				iomem_ready <= 1;
				iomem_rdata <= gpio;
				if (iomem_wstrb[0]) gpio[ 7: 0] <= iomem_wdata[ 7: 0];
				if (iomem_wstrb[1]) gpio[15: 8] <= iomem_wdata[15: 8];
				if (iomem_wstrb[2]) gpio[23:16] <= iomem_wdata[23:16];
				if (iomem_wstrb[3]) gpio[31:24] <= iomem_wdata[31:24];
			end
		end
	end

	picosoc #(
		.BARREL_SHIFTER(0),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0),
		.ENABLE_FAST_MUL(1),
		.MEM_WORDS(MEM_WORDS)
	) soc (
		.clk          (clk         ),
		.resetn       (resetn      ),

		.ser_tx       (ser_tx      ),
		.ser_rx       (ser_rx      ),

		.flash_csb    (flash_csb   ),
		.flash_clk    (flash_clk   ),

		.flash_io0_oe (flash_io0_oe),
		.flash_io1_oe (flash_io1_oe),
		.flash_io2_oe (flash_io2_oe),
		.flash_io3_oe (flash_io3_oe),

		.flash_io0_do (flash_io0_do),
		.flash_io1_do (flash_io1_do),
		.flash_io2_do (flash_io2_do),
		.flash_io3_do (flash_io3_do),

		.flash_io0_di (flash_io0_di),
		.flash_io1_di (flash_io1_di),
		.flash_io2_di (flash_io2_di),
		.flash_io3_di (flash_io3_di),

		.irq_5        (1'b0        ),
		.irq_6        (1'b0        ),
		.irq_7        (1'b0        ),

		.iomem_valid  (iomem_valid ),
		.iomem_ready  (iomem_ready ),
		.iomem_wstrb  (iomem_wstrb ),
		.iomem_addr   (iomem_addr  ),
		.iomem_wdata  (iomem_wdata ),
		.iomem_rdata  (iomem_rdata )
	);
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_tb_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker_tb.v` | Lines 1–21

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_tb_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker_tb.v` | Lines 22–28

```verilog
module testbench;
	reg clk;
	always #5 clk = (clk === 1'b0);

	localparam ser_half_period = 53;
	event ser_sample;
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_tb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker_tb.v` | Lines 29–41

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);

		repeat (6) begin
			repeat (50000) @(posedge clk);
			$display("+50000 cycles");
		end
		$finish;
	end

	integer cycle_cnt = 0;
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_tb_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker_tb.v` | Lines 42–60

```verilog
always @(posedge clk) begin
		cycle_cnt <= cycle_cnt + 1;
	end

	wire led1, led2, led3, led4, led5;
	wire ledr_n, ledg_n;

	wire [6:0] leds = {!ledg_n, !ledr_n, led5, led4, led3, led2, led1};

	wire ser_rx;
	wire ser_tx;

	wire flash_csb;
	wire flash_clk;
	wire flash_io0;
	wire flash_io1;
	wire flash_io2;
	wire flash_io3;
```

---
<!-- chunk_id=picorv32_picosoc_icebreaker_tb_4 | always @(leds) begin -->

# Verilog Block: `always @(leds) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/icebreaker_tb.v` | Lines 61–121

```verilog
always @(leds) begin
		#1 $display("%b", leds);
	end

	icebreaker #(
		// We limit the amount of memory in simulation
		// in order to avoid reduce simulation time
		// required for intialization of RAM
		.MEM_WORDS(256)
	) uut (
		.clk      (clk      ),
		.led1     (led1     ),
		.led2     (led2     ),
		.led3     (led3     ),
		.led4     (led4     ),
		.led5     (led5     ),
		.ledr_n   (ledr_n   ),
		.ledg_n   (ledg_n   ),
		.ser_rx   (ser_rx   ),
		.ser_tx   (ser_tx   ),
		.flash_csb(flash_csb),
		.flash_clk(flash_clk),
		.flash_io0(flash_io0),
		.flash_io1(flash_io1),
		.flash_io2(flash_io2),
		.flash_io3(flash_io3)
	);

	spiflash spiflash (
		.csb(flash_csb),
		.clk(flash_clk),
		.io0(flash_io0),
		.io1(flash_io1),
		.io2(flash_io2),
		.io3(flash_io3)
	);

	reg [7:0] buffer;

	always begin
		@(negedge ser_tx);

		repeat (ser_half_period) @(posedge clk);
		-> ser_sample; // start bit

		repeat (8) begin
			repeat (ser_half_period) @(posedge clk);
			repeat (ser_half_period) @(posedge clk);
			buffer = {ser_tx, buffer[7:1]};
			-> ser_sample; // data bit
		end

		repeat (ser_half_period) @(posedge clk);
		repeat (ser_half_period) @(posedge clk);
		-> ser_sample; // stop bit

		if (buffer < 32 || buffer >= 127)
			$display("Serial data: %d", buffer);
		else
			$display("Serial data: '%c'", buffer);
	end
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 1–24

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`ifndef PICORV32_REGS
`ifdef PICORV32_V
`error "picosoc.v must be read before picorv32.v!"
`endif
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_1 | `define PICORV32_REGS picosoc_regs -->

# Verilog Block: ``define PICORV32_REGS picosoc_regs`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 25–28

```verilog
`define PICORV32_REGS picosoc_regs
`endif

`ifndef PICOSOC_MEM
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_2 | `define PICOSOC_MEM picosoc_mem -->

# Verilog Block: ``define PICOSOC_MEM picosoc_mem`

> **Block Comment:** this macro can be used to check if the verilog files in your design are read in the correct order.

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 29–33

```verilog
`define PICOSOC_MEM picosoc_mem
`endif

// this macro can be used to check if the verilog files in your
// design are read in the correct order.
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_4 | module picosoc ( -->

# Verilog Block: `module picosoc (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 36–88

```verilog
module picosoc (
	input clk,
	input resetn,

	output        iomem_valid,
	input         iomem_ready,
	output [ 3:0] iomem_wstrb,
	output [31:0] iomem_addr,
	output [31:0] iomem_wdata,
	input  [31:0] iomem_rdata,

	input  irq_5,
	input  irq_6,
	input  irq_7,

	output ser_tx,
	input  ser_rx,

	output flash_csb,
	output flash_clk,

	output flash_io0_oe,
	output flash_io1_oe,
	output flash_io2_oe,
	output flash_io3_oe,

	output flash_io0_do,
	output flash_io1_do,
	output flash_io2_do,
	output flash_io3_do,

	input  flash_io0_di,
	input  flash_io1_di,
	input  flash_io2_di,
	input  flash_io3_di
);
	parameter [0:0] BARREL_SHIFTER = 1;
	parameter [0:0] ENABLE_MUL = 1;
	parameter [0:0] ENABLE_DIV = 1;
	parameter [0:0] ENABLE_FAST_MUL = 0;
	parameter [0:0] ENABLE_COMPRESSED = 1;
	parameter [0:0] ENABLE_COUNTERS = 1;
	parameter [0:0] ENABLE_IRQ_QREGS = 0;

	parameter integer MEM_WORDS = 256;
	parameter [31:0] STACKADDR = (4*MEM_WORDS);       // end of memory
	parameter [31:0] PROGADDR_RESET = 32'h 0010_0000; // 1 MB into flash
	parameter [31:0] PROGADDR_IRQ = 32'h 0000_0000;

	reg [31:0] irq;
	wire irq_stall = 0;
	wire irq_uart = 0;
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_5 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 89–207

```verilog
always @* begin
		irq = 0;
		irq[3] = irq_stall;
		irq[4] = irq_uart;
		irq[5] = irq_5;
		irq[6] = irq_6;
		irq[7] = irq_7;
	end

	wire mem_valid;
	wire mem_instr;
	wire mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	wire [31:0] mem_rdata;

	wire spimem_ready;
	wire [31:0] spimem_rdata;

	reg ram_ready;
	wire [31:0] ram_rdata;

	assign iomem_valid = mem_valid && (mem_addr[31:24] > 8'h 01);
	assign iomem_wstrb = mem_wstrb;
	assign iomem_addr = mem_addr;
	assign iomem_wdata = mem_wdata;

	wire spimemio_cfgreg_sel = mem_valid && (mem_addr == 32'h 0200_0000);
	wire [31:0] spimemio_cfgreg_do;

	wire        simpleuart_reg_div_sel = mem_valid && (mem_addr == 32'h 0200_0004);
	wire [31:0] simpleuart_reg_div_do;

	wire        simpleuart_reg_dat_sel = mem_valid && (mem_addr == 32'h 0200_0008);
	wire [31:0] simpleuart_reg_dat_do;
	wire        simpleuart_reg_dat_wait;

	assign mem_ready = (iomem_valid && iomem_ready) || spimem_ready || ram_ready || spimemio_cfgreg_sel ||
			simpleuart_reg_div_sel || (simpleuart_reg_dat_sel && !simpleuart_reg_dat_wait);

	assign mem_rdata = (iomem_valid && iomem_ready) ? iomem_rdata : spimem_ready ? spimem_rdata : ram_ready ? ram_rdata :
			spimemio_cfgreg_sel ? spimemio_cfgreg_do : simpleuart_reg_div_sel ? simpleuart_reg_div_do :
			simpleuart_reg_dat_sel ? simpleuart_reg_dat_do : 32'h 0000_0000;

	picorv32 #(
		.STACKADDR(STACKADDR),
		.PROGADDR_RESET(PROGADDR_RESET),
		.PROGADDR_IRQ(PROGADDR_IRQ),
		.BARREL_SHIFTER(BARREL_SHIFTER),
		.COMPRESSED_ISA(ENABLE_COMPRESSED),
		.ENABLE_COUNTERS(ENABLE_COUNTERS),
		.ENABLE_MUL(ENABLE_MUL),
		.ENABLE_DIV(ENABLE_DIV),
		.ENABLE_FAST_MUL(ENABLE_FAST_MUL),
		.ENABLE_IRQ(1),
		.ENABLE_IRQ_QREGS(ENABLE_IRQ_QREGS)
	) cpu (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  ),
		.irq         (irq        )
	);

	spimemio spimemio (
		.clk    (clk),
		.resetn (resetn),
		.valid  (mem_valid && mem_addr >= 4*MEM_WORDS && mem_addr < 32'h 0200_0000),
		.ready  (spimem_ready),
		.addr   (mem_addr[23:0]),
		.rdata  (spimem_rdata),

		.flash_csb    (flash_csb   ),
		.flash_clk    (flash_clk   ),

		.flash_io0_oe (flash_io0_oe),
		.flash_io1_oe (flash_io1_oe),
		.flash_io2_oe (flash_io2_oe),
		.flash_io3_oe (flash_io3_oe),

		.flash_io0_do (flash_io0_do),
		.flash_io1_do (flash_io1_do),
		.flash_io2_do (flash_io2_do),
		.flash_io3_do (flash_io3_do),

		.flash_io0_di (flash_io0_di),
		.flash_io1_di (flash_io1_di),
		.flash_io2_di (flash_io2_di),
		.flash_io3_di (flash_io3_di),

		.cfgreg_we(spimemio_cfgreg_sel ? mem_wstrb : 4'b 0000),
		.cfgreg_di(mem_wdata),
		.cfgreg_do(spimemio_cfgreg_do)
	);

	simpleuart simpleuart (
		.clk         (clk         ),
		.resetn      (resetn      ),

		.ser_tx      (ser_tx      ),
		.ser_rx      (ser_rx      ),

		.reg_div_we  (simpleuart_reg_div_sel ? mem_wstrb : 4'b 0000),
		.reg_div_di  (mem_wdata),
		.reg_div_do  (simpleuart_reg_div_do),

		.reg_dat_we  (simpleuart_reg_dat_sel ? mem_wstrb[0] : 1'b 0),
		.reg_dat_re  (simpleuart_reg_dat_sel && !mem_wstrb),
		.reg_dat_di  (mem_wdata),
		.reg_dat_do  (simpleuart_reg_dat_do),
		.reg_dat_wait(simpleuart_reg_dat_wait)
	);
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_6 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 208–219

```verilog
always @(posedge clk)
		ram_ready <= mem_valid && !mem_ready && mem_addr < 4*MEM_WORDS;

	`PICOSOC_MEM #(
		.WORDS(MEM_WORDS)
	) memory (
		.clk(clk),
		.wen((mem_valid && !mem_ready && mem_addr < 4*MEM_WORDS) ? mem_wstrb : 4'b0),
		.addr(mem_addr[23:2]),
		.wdata(mem_wdata),
		.rdata(ram_rdata)
	);
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_7 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 220–224

```verilog
endmodule

// Implementation note:
// Replace the following two modules with wrappers for your SRAM cells.
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_8 | module picosoc_regs ( -->

# Verilog Block: `module picosoc_regs (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 225–235

```verilog
module picosoc_regs (
	input clk, wen,
	input [5:0] waddr,
	input [5:0] raddr1,
	input [5:0] raddr2,
	input [31:0] wdata,
	output [31:0] rdata1,
	output [31:0] rdata2
);
	reg [31:0] regs [0:31];
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_9 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 236–240

```verilog
always @(posedge clk)
		if (wen) regs[waddr[4:0]] <= wdata;

	assign rdata1 = regs[raddr1[4:0]];
	assign rdata2 = regs[raddr2[4:0]];
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_11 | module picosoc_mem #( -->

# Verilog Block: `module picosoc_mem #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 243–253

```verilog
module picosoc_mem #(
	parameter integer WORDS = 256
) (
	input clk,
	input [3:0] wen,
	input [21:0] addr,
	input [31:0] wdata,
	output reg [31:0] rdata
);
	reg [31:0] mem [0:WORDS-1];
```

---
<!-- chunk_id=picorv32_picosoc_picosoc_12 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/picosoc.v` | Lines 254–260

```verilog
always @(posedge clk) begin
		rdata <= mem[addr];
		if (wen[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
		if (wen[1]) mem[addr][15: 8] <= wdata[15: 8];
		if (wen[2]) mem[addr][23:16] <= wdata[23:16];
		if (wen[3]) mem[addr][31:24] <= wdata[31:24];
	end
```

---
<!-- chunk_id=picorv32_picosoc_simpleuart_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/simpleuart.v` | Lines 1–19

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */
```

---
<!-- chunk_id=picorv32_picosoc_simpleuart_1 | module simpleuart #(parameter integer DEFAULT_DIV = 1) ( -->

# Verilog Block: `module simpleuart #(parameter integer DEFAULT_DIV = 1) (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/simpleuart.v` | Lines 20–54

```verilog
module simpleuart #(parameter integer DEFAULT_DIV = 1) (
	input clk,
	input resetn,

	output ser_tx,
	input  ser_rx,

	input   [3:0] reg_div_we,
	input  [31:0] reg_div_di,
	output [31:0] reg_div_do,

	input         reg_dat_we,
	input         reg_dat_re,
	input  [31:0] reg_dat_di,
	output [31:0] reg_dat_do,
	output        reg_dat_wait
);
	reg [31:0] cfg_divider;

	reg [3:0] recv_state;
	reg [31:0] recv_divcnt;
	reg [7:0] recv_pattern;
	reg [7:0] recv_buf_data;
	reg recv_buf_valid;

	reg [9:0] send_pattern;
	reg [3:0] send_bitcnt;
	reg [31:0] send_divcnt;
	reg send_dummy;

	assign reg_div_do = cfg_divider;

	assign reg_dat_wait = reg_dat_we && (send_bitcnt || send_dummy);
	assign reg_dat_do = recv_buf_valid ? recv_buf_data : ~0;
```

---
<!-- chunk_id=picorv32_picosoc_simpleuart_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/simpleuart.v` | Lines 55–65

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			cfg_divider <= DEFAULT_DIV;
		end else begin
			if (reg_div_we[0]) cfg_divider[ 7: 0] <= reg_div_di[ 7: 0];
			if (reg_div_we[1]) cfg_divider[15: 8] <= reg_div_di[15: 8];
			if (reg_div_we[2]) cfg_divider[23:16] <= reg_div_di[23:16];
			if (reg_div_we[3]) cfg_divider[31:24] <= reg_div_di[31:24];
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_simpleuart_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/simpleuart.v` | Lines 66–108

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			recv_state <= 0;
			recv_divcnt <= 0;
			recv_pattern <= 0;
			recv_buf_data <= 0;
			recv_buf_valid <= 0;
		end else begin
			recv_divcnt <= recv_divcnt + 1;
			if (reg_dat_re)
				recv_buf_valid <= 0;
			case (recv_state)
				0: begin
					if (!ser_rx)
						recv_state <= 1;
					recv_divcnt <= 0;
				end
				1: begin
					if (2*recv_divcnt > cfg_divider) begin
						recv_state <= 2;
						recv_divcnt <= 0;
					end
				end
				10: begin
					if (recv_divcnt > cfg_divider) begin
						recv_buf_data <= recv_pattern;
						recv_buf_valid <= 1;
						recv_state <= 0;
					end
				end
				default: begin
					if (recv_divcnt > cfg_divider) begin
						recv_pattern <= {ser_rx, recv_pattern[7:1]};
						recv_state <= recv_state + 1;
						recv_divcnt <= 0;
					end
				end
			endcase
		end
	end

	assign ser_tx = send_pattern[0];
```

---
<!-- chunk_id=picorv32_picosoc_simpleuart_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/simpleuart.v` | Lines 109–136

```verilog
always @(posedge clk) begin
		if (reg_div_we)
			send_dummy <= 1;
		send_divcnt <= send_divcnt + 1;
		if (!resetn) begin
			send_pattern <= ~0;
			send_bitcnt <= 0;
			send_divcnt <= 0;
			send_dummy <= 1;
		end else begin
			if (send_dummy && !send_bitcnt) begin
				send_pattern <= ~0;
				send_bitcnt <= 15;
				send_divcnt <= 0;
				send_dummy <= 0;
			end else
			if (reg_dat_we && !send_bitcnt) begin
				send_pattern <= {1'b1, reg_dat_di[7:0], 1'b0};
				send_bitcnt <= 10;
				send_divcnt <= 0;
			end else
			if (send_divcnt > cfg_divider && send_bitcnt) begin
				send_pattern <= {1'b1, send_pattern[9:1]};
				send_bitcnt <= send_bitcnt - 1;
				send_divcnt <= 0;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 1–38

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`timescale 1 ns / 1 ps

//
// Simple SPI flash simulation model
//
// This model samples io input signals 1ns before the SPI clock edge and
// updates output signals 1ns after the SPI clock edge.
//
// Supported commands:
//    AB, B9, FF, 03, BB, EB, ED
//
// Well written SPI flash data sheets:
//    Cypress S25FL064L http://www.cypress.com/file/316661/download
//    Cypress S25FL128L http://www.cypress.com/file/316171/download
//
// SPI flash used on iCEBreaker board:
//    https://www.winbond.com/resource-files/w25q128jv%20dtr%20revb%2011042016.pdf
//
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_1 | module spiflash ( -->

# Verilog Block: `module spiflash (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 39–104

```verilog
module spiflash (
	input csb,
	input clk,
	inout io0, // MOSI
	inout io1, // MISO
	inout io2,
	inout io3
);
	localparam verbose = 0;
	localparam integer latency = 8;

	reg [7:0] buffer;
	integer bitcount = 0;
	integer bytecount = 0;
	integer dummycount = 0;

	reg [7:0] spi_cmd;
	reg [7:0] xip_cmd = 0;
	reg [23:0] spi_addr;

	reg [7:0] spi_in;
	reg [7:0] spi_out;
	reg spi_io_vld;

	reg powered_up = 0;

	localparam [3:0] mode_spi         = 1;
	localparam [3:0] mode_dspi_rd     = 2;
	localparam [3:0] mode_dspi_wr     = 3;
	localparam [3:0] mode_qspi_rd     = 4;
	localparam [3:0] mode_qspi_wr     = 5;
	localparam [3:0] mode_qspi_ddr_rd = 6;
	localparam [3:0] mode_qspi_ddr_wr = 7;

	reg [3:0] mode = 0;
	reg [3:0] next_mode = 0;

	reg io0_oe = 0;
	reg io1_oe = 0;
	reg io2_oe = 0;
	reg io3_oe = 0;

	reg io0_dout = 0;
	reg io1_dout = 0;
	reg io2_dout = 0;
	reg io3_dout = 0;

	assign #1 io0 = io0_oe ? io0_dout : 1'bz;
	assign #1 io1 = io1_oe ? io1_dout : 1'bz;
	assign #1 io2 = io2_oe ? io2_dout : 1'bz;
	assign #1 io3 = io3_oe ? io3_dout : 1'bz;

	wire io0_delayed;
	wire io1_delayed;
	wire io2_delayed;
	wire io3_delayed;

	assign #1 io0_delayed = io0;
	assign #1 io1_delayed = io1;
	assign #1 io2_delayed = io2;
	assign #1 io3_delayed = io3;

	// 16 MB (128Mb) Flash
	reg [7:0] memory [0:16*1024*1024-1];

	reg [1023:0] firmware_file;
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 105–110

```verilog
initial begin
		if (!$value$plusargs("firmware=%s", firmware_file))
			firmware_file = "firmware.hex";
		$readmemh(firmware_file, memory);
	end
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_3 | task spi_action; -->

# Verilog Block: `task spi_action;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 111–230

```verilog
task spi_action;
		begin
			spi_in = buffer;

			if (bytecount == 1) begin
				spi_cmd = buffer;

				if (spi_cmd == 8'h ab)
					powered_up = 1;

				if (spi_cmd == 8'h b9)
					powered_up = 0;

				if (spi_cmd == 8'h ff)
					xip_cmd = 0;
			end

			if (powered_up && spi_cmd == 'h 03) begin
				if (bytecount == 2)
					spi_addr[23:16] = buffer;

				if (bytecount == 3)
					spi_addr[15:8] = buffer;

				if (bytecount == 4)
					spi_addr[7:0] = buffer;

				if (bytecount >= 4) begin
					buffer = memory[spi_addr];
					spi_addr = spi_addr + 1;
				end
			end

			if (powered_up && spi_cmd == 'h bb) begin
				if (bytecount == 1)
					mode = mode_dspi_rd;

				if (bytecount == 2)
					spi_addr[23:16] = buffer;

				if (bytecount == 3)
					spi_addr[15:8] = buffer;

				if (bytecount == 4)
					spi_addr[7:0] = buffer;

				if (bytecount == 5) begin
					xip_cmd = (buffer == 8'h a5) ? spi_cmd : 8'h 00;
					mode = mode_dspi_wr;
					dummycount = latency;
				end

				if (bytecount >= 5) begin
					buffer = memory[spi_addr];
					spi_addr = spi_addr + 1;
				end
			end

			if (powered_up && spi_cmd == 'h eb) begin
				if (bytecount == 1)
					mode = mode_qspi_rd;

				if (bytecount == 2)
					spi_addr[23:16] = buffer;

				if (bytecount == 3)
					spi_addr[15:8] = buffer;

				if (bytecount == 4)
					spi_addr[7:0] = buffer;

				if (bytecount == 5) begin
					xip_cmd = (buffer == 8'h a5) ? spi_cmd : 8'h 00;
					mode = mode_qspi_wr;
					dummycount = latency;
				end

				if (bytecount >= 5) begin
					buffer = memory[spi_addr];
					spi_addr = spi_addr + 1;
				end
			end

			if (powered_up && spi_cmd == 'h ed) begin
				if (bytecount == 1)
					next_mode = mode_qspi_ddr_rd;

				if (bytecount == 2)
					spi_addr[23:16] = buffer;

				if (bytecount == 3)
					spi_addr[15:8] = buffer;

				if (bytecount == 4)
					spi_addr[7:0] = buffer;

				if (bytecount == 5) begin
					xip_cmd = (buffer == 8'h a5) ? spi_cmd : 8'h 00;
					mode = mode_qspi_ddr_wr;
					dummycount = latency;
				end

				if (bytecount >= 5) begin
					buffer = memory[spi_addr];
					spi_addr = spi_addr + 1;
				end
			end

			spi_out = buffer;
			spi_io_vld = 1;

			if (verbose) begin
				if (bytecount == 1)
					$write("<SPI-START>");
				$write("<SPI:%02x:%02x>", spi_in, spi_out);
			end

		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_4 | task ddr_rd_edge; -->

# Verilog Block: `task ddr_rd_edge;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 231–242

```verilog
task ddr_rd_edge;
		begin
			buffer = {buffer, io3_delayed, io2_delayed, io1_delayed, io0_delayed};
			bitcount = bitcount + 4;
			if (bitcount == 8) begin
				bitcount = 0;
				bytecount = bytecount + 1;
				spi_action;
			end
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_5 | task ddr_wr_edge; -->

# Verilog Block: `task ddr_wr_edge;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 243–264

```verilog
task ddr_wr_edge;
		begin
			io0_oe = 1;
			io1_oe = 1;
			io2_oe = 1;
			io3_oe = 1;

			io0_dout = buffer[4];
			io1_dout = buffer[5];
			io2_dout = buffer[6];
			io3_dout = buffer[7];

			buffer = {buffer, 4'h 0};
			bitcount = bitcount + 4;
			if (bitcount == 8) begin
				bitcount = 0;
				bytecount = bytecount + 1;
				spi_action;
			end
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_6 | always @(csb) begin -->

# Verilog Block: `always @(csb) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 265–287

```verilog
always @(csb) begin
		if (csb) begin
			if (verbose) begin
				$display("");
				$fflush;
			end
			buffer = 0;
			bitcount = 0;
			bytecount = 0;
			mode = mode_spi;
			io0_oe = 0;
			io1_oe = 0;
			io2_oe = 0;
			io3_oe = 0;
		end else
		if (xip_cmd) begin
			buffer = xip_cmd;
			bitcount = 0;
			bytecount = 1;
			spi_action;
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_7 | always @(csb, clk) begin -->

# Verilog Block: `always @(csb, clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 288–366

```verilog
always @(csb, clk) begin
		spi_io_vld = 0;
		if (!csb && !clk) begin
			if (dummycount > 0) begin
				io0_oe = 0;
				io1_oe = 0;
				io2_oe = 0;
				io3_oe = 0;
			end else
			case (mode)
				mode_spi: begin
					io0_oe = 0;
					io1_oe = 1;
					io2_oe = 0;
					io3_oe = 0;
					io1_dout = buffer[7];
				end
				mode_dspi_rd: begin
					io0_oe = 0;
					io1_oe = 0;
					io2_oe = 0;
					io3_oe = 0;
				end
				mode_dspi_wr: begin
					io0_oe = 1;
					io1_oe = 1;
					io2_oe = 0;
					io3_oe = 0;
					io0_dout = buffer[6];
					io1_dout = buffer[7];
				end
				mode_qspi_rd: begin
					io0_oe = 0;
					io1_oe = 0;
					io2_oe = 0;
					io3_oe = 0;
				end
				mode_qspi_wr: begin
					io0_oe = 1;
					io1_oe = 1;
					io2_oe = 1;
					io3_oe = 1;
					io0_dout = buffer[4];
					io1_dout = buffer[5];
					io2_dout = buffer[6];
					io3_dout = buffer[7];
				end
				mode_qspi_ddr_rd: begin
					ddr_rd_edge;
				end
				mode_qspi_ddr_wr: begin
					ddr_wr_edge;
				end
			endcase
			if (next_mode) begin
				case (next_mode)
					mode_qspi_ddr_rd: begin
						io0_oe = 0;
						io1_oe = 0;
						io2_oe = 0;
						io3_oe = 0;
					end
					mode_qspi_ddr_wr: begin
						io0_oe = 1;
						io1_oe = 1;
						io2_oe = 1;
						io3_oe = 1;
						io0_dout = buffer[4];
						io1_dout = buffer[5];
						io2_dout = buffer[6];
						io3_dout = buffer[7];
					end
				endcase
				mode = next_mode;
				next_mode = 0;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_8 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash.v` | Lines 367–408

```verilog
always @(posedge clk) begin
		if (!csb) begin
			if (dummycount > 0) begin
				dummycount = dummycount - 1;
			end else
			case (mode)
				mode_spi: begin
					buffer = {buffer, io0};
					bitcount = bitcount + 1;
					if (bitcount == 8) begin
						bitcount = 0;
						bytecount = bytecount + 1;
						spi_action;
					end
				end
				mode_dspi_rd, mode_dspi_wr: begin
					buffer = {buffer, io1, io0};
					bitcount = bitcount + 2;
					if (bitcount == 8) begin
						bitcount = 0;
						bytecount = bytecount + 1;
						spi_action;
					end
				end
				mode_qspi_rd, mode_qspi_wr: begin
					buffer = {buffer, io3, io2, io1, io0};
					bitcount = bitcount + 4;
					if (bitcount == 8) begin
						bitcount = 0;
						bytecount = bytecount + 1;
						spi_action;
					end
				end
				mode_qspi_ddr_rd: begin
					ddr_rd_edge;
				end
				mode_qspi_ddr_wr: begin
					ddr_wr_edge;
				end
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 1–21

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 22–61

```verilog
module testbench;
	reg flash_csb = 1;
	reg flash_clk = 0;

	wire flash_io0;
	wire flash_io1;
	wire flash_io2;
	wire flash_io3;

	reg flash_io0_oe = 0;
	reg flash_io1_oe = 0;
	reg flash_io2_oe = 0;
	reg flash_io3_oe = 0;

	reg flash_io0_dout = 0;
	reg flash_io1_dout = 0;
	reg flash_io2_dout = 0;
	reg flash_io3_dout = 0;

	assign flash_io0 = flash_io0_oe ? flash_io0_dout : 1'bz;
	assign flash_io1 = flash_io1_oe ? flash_io1_dout : 1'bz;
	assign flash_io2 = flash_io2_oe ? flash_io2_dout : 1'bz;
	assign flash_io3 = flash_io3_oe ? flash_io3_dout : 1'bz;

	spiflash uut (
		.csb(flash_csb),
		.clk(flash_clk),
		.io0(flash_io0),
		.io1(flash_io1),
		.io2(flash_io2),
		.io3(flash_io3)
	);

	localparam [23:0] offset = 24'h100000;
	localparam [31:0] word0 = 32'h 00000093;
	localparam [31:0] word1 = 32'h 00000193;

	reg [7:0] rdata;
	integer errcount = 0;
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_2 | task expect; -->

# Verilog Block: `task expect;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 62–71

```verilog
task expect;
		input [7:0] data;
		begin
			if (data !== rdata) begin
				$display("ERROR: Got %x (%b) but expected %x (%b).", rdata, rdata, data, data);
				errcount = errcount + 1;
			end
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_3 | task xfer_begin; -->

# Verilog Block: `task xfer_begin;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 72–80

```verilog
task xfer_begin;
		begin
			#5;
			flash_csb = 0;
			$display("-- BEGIN");
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_4 | task xfer_dummy; -->

# Verilog Block: `task xfer_dummy;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 81–95

```verilog
task xfer_dummy;
		begin
			flash_io0_oe = 0;
			flash_io1_oe = 0;
			flash_io2_oe = 0;
			flash_io3_oe = 0;

			#5;
			flash_clk = 1;
			#5;
			flash_clk = 0;
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_5 | task xfer_end; -->

# Verilog Block: `task xfer_end;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 96–109

```verilog
task xfer_end;
		begin
			#5;
			flash_csb = 1;
			flash_io0_oe = 0;
			flash_io1_oe = 0;
			flash_io2_oe = 0;
			flash_io3_oe = 0;
			$display("-- END");
			$display("");
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_6 | task xfer_spi; -->

# Verilog Block: `task xfer_spi;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 110–132

```verilog
task xfer_spi;
		input [7:0] data;
		integer i;
		begin
			flash_io0_oe = 1;
			flash_io1_oe = 0;
			flash_io2_oe = 0;
			flash_io3_oe = 0;

			for (i = 0; i < 8; i=i+1) begin
				flash_io0_dout = data[7-i];
				#5;
				flash_clk = 1;
				rdata[7-i] = flash_io1;
				#5;
				flash_clk = 0;
			end

			$display("--  SPI SDR  %02x %02x", data, rdata);
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_7 | task xfer_qspi_wr; -->

# Verilog Block: `task xfer_qspi_wr;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 133–166

```verilog
task xfer_qspi_wr;
		input [7:0] data;
		integer i;
		begin
			flash_io0_oe = 1;
			flash_io1_oe = 1;
			flash_io2_oe = 1;
			flash_io3_oe = 1;

			flash_io0_dout = data[4];
			flash_io1_dout = data[5];
			flash_io2_dout = data[6];
			flash_io3_dout = data[7];

			#5;
			flash_clk = 1;

			#5;
			flash_clk = 0;
			flash_io0_dout = data[0];
			flash_io1_dout = data[1];
			flash_io2_dout = data[2];
			flash_io3_dout = data[3];

			#5;
			flash_clk = 1;
			#5;
			flash_clk = 0;

			$display("-- QSPI SDR  %02x --", data);
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_8 | task xfer_qspi_rd; -->

# Verilog Block: `task xfer_qspi_rd;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 167–199

```verilog
task xfer_qspi_rd;
		integer i;
		begin
			flash_io0_oe = 0;
			flash_io1_oe = 0;
			flash_io2_oe = 0;
			flash_io3_oe = 0;

			#5;
			flash_clk = 1;
			rdata[4] = flash_io0;
			rdata[5] = flash_io1;
			rdata[6] = flash_io2;
			rdata[7] = flash_io3;

			#5;
			flash_clk = 0;

			#5;
			flash_clk = 1;
			rdata[0] = flash_io0;
			rdata[1] = flash_io1;
			rdata[2] = flash_io2;
			rdata[3] = flash_io3;

			#5;
			flash_clk = 0;

			$display("-- QSPI SDR  -- %02x", rdata);
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_9 | task xfer_qspi_ddr_wr; -->

# Verilog Block: `task xfer_qspi_ddr_wr;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 200–228

```verilog
task xfer_qspi_ddr_wr;
		input [7:0] data;
		integer i;
		begin
			flash_io0_oe = 1;
			flash_io1_oe = 1;
			flash_io2_oe = 1;
			flash_io3_oe = 1;

			flash_io0_dout = data[4];
			flash_io1_dout = data[5];
			flash_io2_dout = data[6];
			flash_io3_dout = data[7];

			#5;
			flash_clk = 1;
			flash_io0_dout = data[0];
			flash_io1_dout = data[1];
			flash_io2_dout = data[2];
			flash_io3_dout = data[3];

			#5;
			flash_clk = 0;

			$display("-- QSPI DDR  %02x --", data);
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_10 | task xfer_qspi_ddr_rd; -->

# Verilog Block: `task xfer_qspi_ddr_rd;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 229–255

```verilog
task xfer_qspi_ddr_rd;
		integer i;
		begin
			flash_io0_oe = 0;
			flash_io1_oe = 0;
			flash_io2_oe = 0;
			flash_io3_oe = 0;

			#5;
			flash_clk = 1;
			rdata[4] = flash_io0;
			rdata[5] = flash_io1;
			rdata[6] = flash_io2;
			rdata[7] = flash_io3;

			#5;
			flash_clk = 0;
			rdata[0] = flash_io0;
			rdata[1] = flash_io1;
			rdata[2] = flash_io2;
			rdata[3] = flash_io3;

			$display("-- QSPI DDR  -- %02x", rdata);
			#5;
		end
	endtask
```

---
<!-- chunk_id=picorv32_picosoc_spiflash_tb_11 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spiflash_tb.v` | Lines 256–365

```verilog
initial begin
		$dumpfile("spiflash_tb.vcd");
		$dumpvars(0, testbench);
		$display("");

		$display("Reset (FFh)");
		xfer_begin;
		xfer_spi(8'h ff);
		xfer_end;

		$display("Power Up (ABh)");
		xfer_begin;
		xfer_spi(8'h ab);
		xfer_end;

		$display("Read Data (03h)");
		xfer_begin;
		xfer_spi(8'h 03);
		xfer_spi(offset[23:16]);
		xfer_spi(offset[15:8]);
		xfer_spi(offset[7:0]);
		xfer_spi(8'h 00); expect(word0[7:0]);
		xfer_spi(8'h 00); expect(word0[15:8]);
		xfer_spi(8'h 00); expect(word0[23:16]);
		xfer_spi(8'h 00); expect(word0[31:24]);
		xfer_spi(8'h 00); expect(word1[7:0]);
		xfer_spi(8'h 00); expect(word1[15:8]);
		xfer_spi(8'h 00); expect(word1[23:16]);
		xfer_spi(8'h 00); expect(word1[31:24]);
		xfer_end;

		$display("Quad I/O Read (EBh)");
		xfer_begin;
		xfer_spi(8'h eb);
		xfer_qspi_wr(offset[23:16]);
		xfer_qspi_wr(offset[15:8]);
		xfer_qspi_wr(offset[7:0]);
		xfer_qspi_wr(8'h a5);
		repeat (8) xfer_dummy;
		xfer_qspi_rd; expect(word0[7:0]);
		xfer_qspi_rd; expect(word0[15:8]);
		xfer_qspi_rd; expect(word0[23:16]);
		xfer_qspi_rd; expect(word0[31:24]);
		xfer_qspi_rd; expect(word1[7:0]);
		xfer_qspi_rd; expect(word1[15:8]);
		xfer_qspi_rd; expect(word1[23:16]);
		xfer_qspi_rd; expect(word1[31:24]);
		xfer_end;

		$display("Continous Quad I/O Read");
		xfer_begin;
		xfer_qspi_wr(offset[23:16]);
		xfer_qspi_wr(offset[15:8]);
		xfer_qspi_wr(offset[7:0]);
		xfer_qspi_wr(8'h ff);
		repeat (8) xfer_dummy;
		xfer_qspi_rd; expect(word0[7:0]);
		xfer_qspi_rd; expect(word0[15:8]);
		xfer_qspi_rd; expect(word0[23:16]);
		xfer_qspi_rd; expect(word0[31:24]);
		xfer_qspi_rd; expect(word1[7:0]);
		xfer_qspi_rd; expect(word1[15:8]);
		xfer_qspi_rd; expect(word1[23:16]);
		xfer_qspi_rd; expect(word1[31:24]);
		xfer_end;

		$display("DDR Quad I/O Read (EDh)");
		xfer_begin;
		xfer_spi(8'h ed);
		xfer_qspi_ddr_wr(offset[23:16]);
		xfer_qspi_ddr_wr(offset[15:8]);
		xfer_qspi_ddr_wr(offset[7:0]);
		xfer_qspi_ddr_wr(8'h a5);
		repeat (8) xfer_dummy;
		xfer_qspi_ddr_rd; expect(word0[7:0]);
		xfer_qspi_ddr_rd; expect(word0[15:8]);
		xfer_qspi_ddr_rd; expect(word0[23:16]);
		xfer_qspi_ddr_rd; expect(word0[31:24]);
		xfer_qspi_ddr_rd; expect(word1[7:0]);
		xfer_qspi_ddr_rd; expect(word1[15:8]);
		xfer_qspi_ddr_rd; expect(word1[23:16]);
		xfer_qspi_ddr_rd; expect(word1[31:24]);
		xfer_end;

		$display("Continous DDR Quad I/O Read");
		xfer_begin;
		xfer_qspi_ddr_wr(offset[23:16]);
		xfer_qspi_ddr_wr(offset[15:8]);
		xfer_qspi_ddr_wr(offset[7:0]);
		xfer_qspi_ddr_wr(8'h ff);
		repeat (8) xfer_dummy;
		xfer_qspi_ddr_rd; expect(word0[7:0]);
		xfer_qspi_ddr_rd; expect(word0[15:8]);
		xfer_qspi_ddr_rd; expect(word0[23:16]);
		xfer_qspi_ddr_rd; expect(word0[31:24]);
		xfer_qspi_ddr_rd; expect(word1[7:0]);
		xfer_qspi_ddr_rd; expect(word1[15:8]);
		xfer_qspi_ddr_rd; expect(word1[23:16]);
		xfer_qspi_ddr_rd; expect(word1[31:24]);
		xfer_end;

		#5;

		if (errcount) begin
			$display("FAIL");
			$stop;
		end else begin
			$display("PASS");
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_0 | /* -->

# Verilog Block: `/*`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 1–19

```verilog
/*
 *  PicoSoC - A simple example SoC using PicoRV32
 *
 *  Copyright (C) 2017  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_1 | module spimemio ( -->

# Verilog Block: `module spimemio (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 20–98

```verilog
module spimemio (
	input clk, resetn,

	input valid,
	output ready,
	input [23:0] addr,
	output reg [31:0] rdata,

	output flash_csb,
	output flash_clk,

	output flash_io0_oe,
	output flash_io1_oe,
	output flash_io2_oe,
	output flash_io3_oe,

	output flash_io0_do,
	output flash_io1_do,
	output flash_io2_do,
	output flash_io3_do,

	input  flash_io0_di,
	input  flash_io1_di,
	input  flash_io2_di,
	input  flash_io3_di,

	input   [3:0] cfgreg_we,
	input  [31:0] cfgreg_di,
	output [31:0] cfgreg_do
);
	reg        xfer_resetn;
	reg        din_valid;
	wire       din_ready;
	reg  [7:0] din_data;
	reg  [3:0] din_tag;
	reg        din_cont;
	reg        din_qspi;
	reg        din_ddr;
	reg        din_rd;

	wire       dout_valid;
	wire [7:0] dout_data;
	wire [3:0] dout_tag;

	reg [23:0] buffer;

	reg [23:0] rd_addr;
	reg rd_valid;
	reg rd_wait;
	reg rd_inc;

	assign ready = valid && (addr == rd_addr) && rd_valid;
	wire jump = valid && !ready && (addr != rd_addr+4) && rd_valid;

	reg softreset;

	reg       config_en;      // cfgreg[31]
	reg       config_ddr;     // cfgreg[22]
	reg       config_qspi;    // cfgreg[21]
	reg       config_cont;    // cfgreg[20]
	reg [3:0] config_dummy;   // cfgreg[19:16]
	reg [3:0] config_oe;      // cfgreg[11:8]
	reg       config_csb;     // cfgreg[5]
	reg       config_clk;     // cfgref[4]
	reg [3:0] config_do;      // cfgreg[3:0]

	assign cfgreg_do[31] = config_en;
	assign cfgreg_do[30:23] = 0;
	assign cfgreg_do[22] = config_ddr;
	assign cfgreg_do[21] = config_qspi;
	assign cfgreg_do[20] = config_cont;
	assign cfgreg_do[19:16] = config_dummy;
	assign cfgreg_do[15:12] = 0;
	assign cfgreg_do[11:8] = {flash_io3_oe, flash_io2_oe, flash_io1_oe, flash_io0_oe};
	assign cfgreg_do[7:6] = 0;
	assign cfgreg_do[5] = flash_csb;
	assign cfgreg_do[4] = flash_clk;
	assign cfgreg_do[3:0] = {flash_io3_di, flash_io2_di, flash_io1_di, flash_io0_di};
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 99–150

```verilog
always @(posedge clk) begin
		softreset <= !config_en || cfgreg_we;
		if (!resetn) begin
			softreset <= 1;
			config_en <= 1;
			config_csb <= 0;
			config_clk <= 0;
			config_oe <= 0;
			config_do <= 0;
			config_ddr <= 0;
			config_qspi <= 0;
			config_cont <= 0;
			config_dummy <= 8;
		end else begin
			if (cfgreg_we[0]) begin
				config_csb <= cfgreg_di[5];
				config_clk <= cfgreg_di[4];
				config_do <= cfgreg_di[3:0];
			end
			if (cfgreg_we[1]) begin
				config_oe <= cfgreg_di[11:8];
			end
			if (cfgreg_we[2]) begin
				config_ddr <= cfgreg_di[22];
				config_qspi <= cfgreg_di[21];
				config_cont <= cfgreg_di[20];
				config_dummy <= cfgreg_di[19:16];
			end
			if (cfgreg_we[3]) begin
				config_en <= cfgreg_di[31];
			end
		end
	end

	wire xfer_csb;
	wire xfer_clk;

	wire xfer_io0_oe;
	wire xfer_io1_oe;
	wire xfer_io2_oe;
	wire xfer_io3_oe;

	wire xfer_io0_do;
	wire xfer_io1_do;
	wire xfer_io2_do;
	wire xfer_io3_do;

	reg xfer_io0_90;
	reg xfer_io1_90;
	reg xfer_io2_90;
	reg xfer_io3_90;
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_3 | always @(negedge clk) begin -->

# Verilog Block: `always @(negedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 151–206

```verilog
always @(negedge clk) begin
		xfer_io0_90 <= xfer_io0_do;
		xfer_io1_90 <= xfer_io1_do;
		xfer_io2_90 <= xfer_io2_do;
		xfer_io3_90 <= xfer_io3_do;
	end

	assign flash_csb = config_en ? xfer_csb : config_csb;
	assign flash_clk = config_en ? xfer_clk : config_clk;

	assign flash_io0_oe = config_en ? xfer_io0_oe : config_oe[0];
	assign flash_io1_oe = config_en ? xfer_io1_oe : config_oe[1];
	assign flash_io2_oe = config_en ? xfer_io2_oe : config_oe[2];
	assign flash_io3_oe = config_en ? xfer_io3_oe : config_oe[3];

	assign flash_io0_do = config_en ? (config_ddr ? xfer_io0_90 : xfer_io0_do) : config_do[0];
	assign flash_io1_do = config_en ? (config_ddr ? xfer_io1_90 : xfer_io1_do) : config_do[1];
	assign flash_io2_do = config_en ? (config_ddr ? xfer_io2_90 : xfer_io2_do) : config_do[2];
	assign flash_io3_do = config_en ? (config_ddr ? xfer_io3_90 : xfer_io3_do) : config_do[3];

	wire xfer_dspi = din_ddr && !din_qspi;
	wire xfer_ddr = din_ddr && din_qspi;

	spimemio_xfer xfer (
		.clk          (clk         ),
		.resetn       (xfer_resetn ),
		.din_valid    (din_valid   ),
		.din_ready    (din_ready   ),
		.din_data     (din_data    ),
		.din_tag      (din_tag     ),
		.din_cont     (din_cont    ),
		.din_dspi     (xfer_dspi   ),
		.din_qspi     (din_qspi    ),
		.din_ddr      (xfer_ddr    ),
		.din_rd       (din_rd      ),
		.dout_valid   (dout_valid  ),
		.dout_data    (dout_data   ),
		.dout_tag     (dout_tag    ),
		.flash_csb    (xfer_csb    ),
		.flash_clk    (xfer_clk    ),
		.flash_io0_oe (xfer_io0_oe ),
		.flash_io1_oe (xfer_io1_oe ),
		.flash_io2_oe (xfer_io2_oe ),
		.flash_io3_oe (xfer_io3_oe ),
		.flash_io0_do (xfer_io0_do ),
		.flash_io1_do (xfer_io1_do ),
		.flash_io2_do (xfer_io2_do ),
		.flash_io3_do (xfer_io3_do ),
		.flash_io0_di (flash_io0_di),
		.flash_io1_di (flash_io1_di),
		.flash_io2_di (flash_io2_di),
		.flash_io3_di (flash_io3_di)
	);

	reg [3:0] state;
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 207–375

```verilog
always @(posedge clk) begin
		xfer_resetn <= 1;
		din_valid <= 0;

		if (!resetn || softreset) begin
			state <= 0;
			xfer_resetn <= 0;
			rd_valid <= 0;
			din_tag <= 0;
			din_cont <= 0;
			din_qspi <= 0;
			din_ddr <= 0;
			din_rd <= 0;
		end else begin
			if (dout_valid && dout_tag == 1) buffer[ 7: 0] <= dout_data;
			if (dout_valid && dout_tag == 2) buffer[15: 8] <= dout_data;
			if (dout_valid && dout_tag == 3) buffer[23:16] <= dout_data;
			if (dout_valid && dout_tag == 4) begin
				rdata <= {dout_data, buffer};
				rd_addr <= rd_inc ? rd_addr + 4 : addr;
				rd_valid <= 1;
				rd_wait <= rd_inc;
				rd_inc <= 1;
			end

			if (valid)
				rd_wait <= 0;

			case (state)
				0: begin
					din_valid <= 1;
					din_data <= 8'h ff;
					din_tag <= 0;
					if (din_ready) begin
						din_valid <= 0;
						state <= 1;
					end
				end
				1: begin
					if (dout_valid) begin
						xfer_resetn <= 0;
						state <= 2;
					end
				end
				2: begin
					din_valid <= 1;
					din_data <= 8'h ab;
					din_tag <= 0;
					if (din_ready) begin
						din_valid <= 0;
						state <= 3;
					end
				end
				3: begin
					if (dout_valid) begin
						xfer_resetn <= 0;
						state <= 4;
					end
				end
				4: begin
					rd_inc <= 0;
					din_valid <= 1;
					din_tag <= 0;
					case ({config_ddr, config_qspi})
						2'b11: din_data <= 8'h ED;
						2'b01: din_data <= 8'h EB;
						2'b10: din_data <= 8'h BB;
						2'b00: din_data <= 8'h 03;
					endcase
					if (din_ready) begin
						din_valid <= 0;
						state <= 5;
					end
				end
				5: begin
					if (valid && !ready) begin
						din_valid <= 1;
						din_tag <= 0;
						din_data <= addr[23:16];
						din_qspi <= config_qspi;
						din_ddr <= config_ddr;
						if (din_ready) begin
							din_valid <= 0;
							state <= 6;
						end
					end
				end
				6: begin
					din_valid <= 1;
					din_tag <= 0;
					din_data <= addr[15:8];
					if (din_ready) begin
						din_valid <= 0;
						state <= 7;
					end
				end
				7: begin
					din_valid <= 1;
					din_tag <= 0;
					din_data <= addr[7:0];
					if (din_ready) begin
						din_valid <= 0;
						din_data <= 0;
						state <= config_qspi || config_ddr ? 8 : 9;
					end
				end
				8: begin
					din_valid <= 1;
					din_tag <= 0;
					din_data <= config_cont ? 8'h A5 : 8'h FF;
					if (din_ready) begin
						din_rd <= 1;
						din_data <= config_dummy;
						din_valid <= 0;
						state <= 9;
					end
				end
				9: begin
					din_valid <= 1;
					din_tag <= 1;
					if (din_ready) begin
						din_valid <= 0;
						state <= 10;
					end
				end
				10: begin
					din_valid <= 1;
					din_data <= 8'h 00;
					din_tag <= 2;
					if (din_ready) begin
						din_valid <= 0;
						state <= 11;
					end
				end
				11: begin
					din_valid <= 1;
					din_tag <= 3;
					if (din_ready) begin
						din_valid <= 0;
						state <= 12;
					end
				end
				12: begin
					if (!rd_wait || valid) begin
						din_valid <= 1;
						din_tag <= 4;
						if (din_ready) begin
							din_valid <= 0;
							state <= 9;
						end
					end
				end
			endcase

			if (jump) begin
				rd_inc <= 0;
				rd_valid <= 0;
				xfer_resetn <= 0;
				if (config_cont) begin
					state <= 5;
				end else begin
					state <= 4;
					din_qspi <= 0;
					din_ddr <= 0;
				end
				din_rd <= 0;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_6 | module spimemio_xfer ( -->

# Verilog Block: `module spimemio_xfer (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 378–435

```verilog
module spimemio_xfer (
	input clk, resetn,

	input            din_valid,
	output           din_ready,
	input      [7:0] din_data,
	input      [3:0] din_tag,
	input            din_cont,
	input            din_dspi,
	input            din_qspi,
	input            din_ddr,
	input            din_rd,

	output           dout_valid,
	output     [7:0] dout_data,
	output     [3:0] dout_tag,

	output reg flash_csb,
	output reg flash_clk,

	output reg flash_io0_oe,
	output reg flash_io1_oe,
	output reg flash_io2_oe,
	output reg flash_io3_oe,

	output reg flash_io0_do,
	output reg flash_io1_do,
	output reg flash_io2_do,
	output reg flash_io3_do,

	input      flash_io0_di,
	input      flash_io1_di,
	input      flash_io2_di,
	input      flash_io3_di
);
	reg [7:0] obuffer;
	reg [7:0] ibuffer;

	reg [3:0] count;
	reg [3:0] dummy_count;

	reg xfer_cont;
	reg xfer_dspi;
	reg xfer_qspi;
	reg xfer_ddr;
	reg xfer_ddr_q;
	reg xfer_rd;
	reg [3:0] xfer_tag;
	reg [3:0] xfer_tag_q;

	reg [7:0] next_obuffer;
	reg [7:0] next_ibuffer;
	reg [3:0] next_count;

	reg fetch;
	reg next_fetch;
	reg last_fetch;
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_7 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 436–446

```verilog
always @(posedge clk) begin
		xfer_ddr_q <= xfer_ddr;
		xfer_tag_q <= xfer_tag;
	end

	assign din_ready = din_valid && resetn && next_fetch;

	assign dout_valid = (xfer_ddr_q ? fetch && !last_fetch : next_fetch && !fetch) && resetn;
	assign dout_data = ibuffer;
	assign dout_tag = xfer_tag_q;
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_8 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 447–534

```verilog
always @* begin
		flash_io0_oe = 0;
		flash_io1_oe = 0;
		flash_io2_oe = 0;
		flash_io3_oe = 0;

		flash_io0_do = 0;
		flash_io1_do = 0;
		flash_io2_do = 0;
		flash_io3_do = 0;

		next_obuffer = obuffer;
		next_ibuffer = ibuffer;
		next_count = count;
		next_fetch = 0;

		if (dummy_count == 0) begin
			casez ({xfer_ddr, xfer_qspi, xfer_dspi})
				3'b 000: begin
					flash_io0_oe = 1;
					flash_io0_do = obuffer[7];

					if (flash_clk) begin
						next_obuffer = {obuffer[6:0], 1'b 0};
						next_count = count - |count;
					end else begin
						next_ibuffer = {ibuffer[6:0], flash_io1_di};
					end

					next_fetch = (next_count == 0);
				end
				3'b 01?: begin
					flash_io0_oe = !xfer_rd;
					flash_io1_oe = !xfer_rd;
					flash_io2_oe = !xfer_rd;
					flash_io3_oe = !xfer_rd;

					flash_io0_do = obuffer[4];
					flash_io1_do = obuffer[5];
					flash_io2_do = obuffer[6];
					flash_io3_do = obuffer[7];

					if (flash_clk) begin
						next_obuffer = {obuffer[3:0], 4'b 0000};
						next_count = count - {|count, 2'b00};
					end else begin
						next_ibuffer = {ibuffer[3:0], flash_io3_di, flash_io2_di, flash_io1_di, flash_io0_di};
					end

					next_fetch = (next_count == 0);
				end
				3'b 11?: begin
					flash_io0_oe = !xfer_rd;
					flash_io1_oe = !xfer_rd;
					flash_io2_oe = !xfer_rd;
					flash_io3_oe = !xfer_rd;

					flash_io0_do = obuffer[4];
					flash_io1_do = obuffer[5];
					flash_io2_do = obuffer[6];
					flash_io3_do = obuffer[7];

					next_obuffer = {obuffer[3:0], 4'b 0000};
					next_ibuffer = {ibuffer[3:0], flash_io3_di, flash_io2_di, flash_io1_di, flash_io0_di};
					next_count = count - {|count, 2'b00};

					next_fetch = (next_count == 0);
				end
				3'b ??1: begin
					flash_io0_oe = !xfer_rd;
					flash_io1_oe = !xfer_rd;

					flash_io0_do = obuffer[6];
					flash_io1_do = obuffer[7];

					if (flash_clk) begin
						next_obuffer = {obuffer[5:0], 2'b 00};
						next_count = count - {|count, 1'b0};
					end else begin
						next_ibuffer = {ibuffer[5:0], flash_io1_di, flash_io0_di};
					end

					next_fetch = (next_count == 0);
				end
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_spimemio_9 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/spimemio.v` | Lines 535–578

```verilog
always @(posedge clk) begin
		if (!resetn) begin
			fetch <= 1;
			last_fetch <= 1;
			flash_csb <= 1;
			flash_clk <= 0;
			count <= 0;
			dummy_count <= 0;
			xfer_tag <= 0;
			xfer_cont <= 0;
			xfer_dspi <= 0;
			xfer_qspi <= 0;
			xfer_ddr <= 0;
			xfer_rd <= 0;
		end else begin
			fetch <= next_fetch;
			last_fetch <= xfer_ddr ? fetch : 1;
			if (dummy_count) begin
				flash_clk <= !flash_clk && !flash_csb;
				dummy_count <= dummy_count - flash_clk;
			end else
			if (count) begin
				flash_clk <= !flash_clk && !flash_csb;
				obuffer <= next_obuffer;
				ibuffer <= next_ibuffer;
				count <= next_count;
			end
			if (din_valid && din_ready) begin
				flash_csb <= 0;
				flash_clk <= 0;

				count <= 8;
				dummy_count <= din_rd ? din_data : 0;
				obuffer <= din_data;

				xfer_tag <= din_tag;
				xfer_cont <= din_cont;
				xfer_dspi <= din_dspi;
				xfer_qspi <= din_qspi;
				xfer_ddr <= din_ddr;
				xfer_rd <= din_rd;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_picosoc_start_asm | Assembly Test: PICORV32_PICOSOC_START -->

# Assembly Test: `PICORV32_PICOSOC_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/picosoc/start.s`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text

start:

# zero-initialize register file
addi x1, zero, 0
# x2 (sp) is initialized by reset
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

# Update LEDs
li a0, 0x03000000
li a1, 1
sw a1, 0(a0)

# zero initialize entire scratchpad memory
li a0, 0x00000000
setmemloop:
sw a0, 0(a0)
addi a0, a0, 4
blt a0, sp, setmemloop

# Update LEDs
li a0, 0x03000000
li a1, 3
sw a1, 0(a0)

# copy data section
la a0, _sidata
la a1, _sdata
la a2, _edata
bge a1, a2, end_init_data
loop_init_data:
lw a3, 0(a0)
sw a3, 0(a1)
addi a0, a0, 4
addi a1, a1, 4
blt a1, a2, loop_init_data
end_init_data:

# Update LEDs
li a0, 0x03000000
li a1, 7
sw a1, 0(a0)

# zero-init bss section
la a0, _sbss
la a1, _ebss
bge a0, a1, end_init_bss
loop_init_bss:
sw zero, 0(a0)
addi a0, a0, 4
blt a0, a1, loop_init_bss
end_init_bss:

# Update LEDs
li a0, 0x03000000
li a1, 15
sw a1, 0(a0)

# call main
call main
loop:
j loop

.global flashio_worker_begin
.global flashio_worker_end

.balign 4

flashio_worker_begin:
# a0 ... data pointer
# a1 ... data length
# a2 ... optional WREN cmd (0 = disable)

# address of SPI ctrl reg
li   t0, 0x02000000

# Set CS high, IO0 is output
li   t1, 0x120
sh   t1, 0(t0)

# Enable Manual SPI Ctrl
sb   zero, 3(t0)

# Send optional WREN cmd
beqz a2, flashio_worker_L1
li   t5, 8
andi t2, a2, 0xff
flashio_worker_L4:
srli t4, t2, 7
sb   t4, 0(t0)
ori  t4, t4, 0x10
sb   t4, 0(t0)
slli t2, t2, 1
andi t2, t2, 0xff
addi t5, t5, -1
bnez t5, flashio_worker_L4
sb   t1, 0(t0)

# SPI transfer
flashio_worker_L1:
beqz a1, flashio_worker_L3
li   t5, 8
lbu  t2, 0(a0)
flashio_worker_L2:
srli t4, t2, 7
sb   t4, 0(t0)
ori  t4, t4, 0x10
sb   t4, 0(t0)
lbu  t4, 0(t0)
andi t4, t4, 2
srli t4, t4, 1
slli t2, t2, 1
or   t2, t2, t4
andi t2, t2, 0xff
addi t5, t5, -1
bnez t5, flashio_worker_L2
sb   t2, 0(a0)
addi a0, a0, 1
addi a1, a1, -1
j    flashio_worker_L1
flashio_worker_L3:

# Back to MEMIO mode
li   t1, 0x80
sb   t1, 3(t0)

ret

.balign 4
flashio_worker_end:
```

---
<!-- chunk_id=picorv32_scripts_csmith_Makefile_0 | picorv32_scripts_csmith_Makefile -->

RISCV_TOOLS_DIR = /opt/riscv32imc
RISCV_TOOLS_PREFIX = $(RISCV_TOOLS_DIR)/bin/riscv32-unknown-elf-
CSMITH_INCDIR = $(shell ls -d /usr/local/include/csmith-* | head -n1)
CC = $(RISCV_TOOLS_PREFIX)gcc
SHELL = /bin/bash

help:
	@echo "Usage: make { loop | verilator | iverilog | spike }"

loop: riscv-fesvr/build.ok riscv-isa-sim/build.ok obj_dir/Vtestbench
	+set -e; x() { echo "$$*" >&2; "$$@"; }; i=1; j=1; while true; do echo; echo; \
		echo "---------------- $$((i++)) ($$j) ----------------"; \
		x rm -f test.hex test.elf test.c test_ref test.ld output_ref.txt output_sim.txt; \
		x make spike test.hex || { echo SKIP; continue; }; x rm -f output_sim.txt; \
		x obj_dir/Vtestbench | grep -v '$$finish' > output_sim.txt; \
		x diff -u output_ref.txt output_sim.txt; echo OK; ! ((j++)); \
	done

verilator: test_ref test.hex obj_dir/Vtestbench
	timeout 2 ./test_ref > output_ref.txt && cat output_ref.txt
	obj_dir/Vtestbench | grep -v '$$finish' > output_sim.txt
	diff -u output_ref.txt output_sim.txt

iverilog: test_ref test.hex testbench.vvp
	timeout 2 ./test_ref > output_ref.txt && cat output_ref.txt
	vvp -N testbench.vvp > output_sim.txt
	diff -u output_ref.txt output_sim.txt

spike: riscv-fesvr/build.ok riscv-isa-sim/build.ok test_ref test.elf
	timeout 2 ./test_ref > output_ref.txt && cat output_ref.txt
	LD_LIBRARY_PATH="./riscv-isa-sim:./riscv-fesvr" ./riscv-isa-sim/spike test.elf > output_sim.txt
	diff -u output_ref.txt output_sim.txt

riscv-fesvr/build.ok:
	rm -rf riscv-fesvr
	git clone https://github.com/riscv/riscv-fesvr.git riscv-fesvr
	+cd riscv-fesvr && git checkout 1c02bd6 && ./configure && make && touch build.ok

riscv-isa-sim/build.ok: riscv-fesvr/build.ok
	rm -rf riscv-isa-sim
	git clone https://github.com/riscv/riscv-isa-sim.git riscv-isa-sim
	cd riscv-isa-sim && git checkout 10ae74e
	cd riscv-isa-sim && patch -p1 < ../riscv-isa-sim.diff
	cd riscv-isa-sim && LDFLAGS="-L../riscv-fesvr" ./configure --with-isa=RV32IMC
	+cd riscv-isa-sim && ln -s ../riscv-fesvr/fesvr . && make && touch build.ok

testbench.vvp: testbench.v ../../picorv32.v
	iverilog -o testbench.vvp testbench.v ../../picorv32.v
	chmod -x testbench.vvp

obj_dir/Vtestbench: testbench.v testbench.cc ../../picorv32.v
	verilator --exe -Wno-fatal --cc --top-module testbench testbench.v ../../picorv32.v testbench.cc
	$(MAKE) -C obj_dir -f Vtestbench.mk

test.hex: test.elf
	$(RISCV_TOOLS_PREFIX)objcopy -O verilog test.elf test.hex

start.elf: start.S start.ld
	$(CC) -nostdlib -o start.elf start.S -T start.ld
	chmod -x start.elf

test_ref: test.c
	gcc -m32 -o test_ref -w -Os -I $(CSMITH_INCDIR) test.c

test.elf: test.c syscalls.c start.S
	sed -e '/SECTIONS/,+1 s/{/{ . = 0x00000000; .start : { *(.text.start) } application_entry_point = 0x00010000;/;' \
		$(RISCV_TOOLS_DIR)/riscv32-unknown-elf/lib/riscv.ld > test.ld
	$(CC) -o test.elf -w -Os -I $(CSMITH_INCDIR) -T test.ld test.c syscalls.c start.S
	chmod -x test.elf

test.c:
	echo "integer size = 4" > platform.info
	echo "pointer size = 4" >> platform.info
	csmith --no-packed-struct -o test.c
	gawk '/Seed:/ {print$$2,$$3;}' test.c

clean:
	rm -rf platform.info test.c test.ld test.elf test.hex test_ref obj_dir
	rm -rf testbench.vvp testbench.vcd output_ref.txt output_sim.txt

mrproper: clean
	rm -rf riscv-fesvr riscv-isa-sim

.PHONY: help loop verilator iverilog spike clean mrproper

---
<!-- chunk_id=picorv32_scripts_csmith_riscv-isa-sim_0 | picorv32_scripts_csmith_riscv-isa-sim -->

diff --git a/riscv/execute.cc b/riscv/execute.cc
index 5c3fdf7..4d914b3 100644
--- a/riscv/execute.cc
+++ b/riscv/execute.cc
@@ -124,6 +124,10 @@ miss:
     }
 
     state.minstret += instret;
+    if (state.minstret > 1000000) {
+        printf("Reached limit of 1000000 instructions.\n");
+	exit(0);
+    }
     n -= instret;
   }
 }
diff --git a/riscv/insns/c_ebreak.h b/riscv/insns/c_ebreak.h
index a17200f..f06d8d9 100644
--- a/riscv/insns/c_ebreak.h
+++ b/riscv/insns/c_ebreak.h
@@ -1,2 +1,4 @@
 require_extension('C');
+
+exit(0);
 throw trap_breakpoint();
diff --git a/riscv/insns/sbreak.h b/riscv/insns/sbreak.h
index c22776c..d38bd22 100644
--- a/riscv/insns/sbreak.h
+++ b/riscv/insns/sbreak.h
@@ -1 +1,2 @@
+exit(0);
 throw trap_breakpoint();
diff --git a/riscv/mmu.h b/riscv/mmu.h
index b9948c5..bee1f8b 100644
--- a/riscv/mmu.h
+++ b/riscv/mmu.h
@@ -67,7 +67,8 @@ public:
       if (addr & (sizeof(type##_t)-1)) \
         throw trap_store_address_misaligned(addr); \
       reg_t vpn = addr >> PGSHIFT; \
-      if (likely(tlb_store_tag[vpn % TLB_ENTRIES] == vpn)) \
+      if (addr == 0x10000000) putchar(val), fflush(stdout); \
+      else if (likely(tlb_store_tag[vpn % TLB_ENTRIES] == vpn)) \
         *(type##_t*)(tlb_data[vpn % TLB_ENTRIES] + addr) = val; \
       else \
         store_slow_path(addr, sizeof(type##_t), (const uint8_t*)&val); \
diff --git a/riscv/processor.cc b/riscv/processor.cc
index 3b834c5..f407543 100644
--- a/riscv/processor.cc
+++ b/riscv/processor.cc
@@ -201,9 +201,9 @@ void processor_t::set_privilege(reg_t prv)
 
 void processor_t::take_trap(trap_t& t, reg_t epc)
 {
-  if (debug)
-    fprintf(stderr, "core %3d: exception %s, epc 0x%016" PRIx64 "\n",
-            id, t.name(), epc);
+  printf("core %3d: exception %s, epc 0x%016" PRIx64 "\n",
+         id, t.name(), epc);
+  exit(0);
 
   // by default, trap to M-mode, unless delegated to S-mode
   reg_t bit = t.cause();

---
<!-- chunk_id=picorv32_scripts_csmith_start_asm | Assembly Test: PICORV32_SCRIPTS_CSMITH_START -->

# Assembly Test: `PICORV32_SCRIPTS_CSMITH_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text.start
.global application_entry_point

/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */
lui sp, %hi(4*1024*1024)
addi sp, sp, %lo(4*1024*1024)

/* push zeros on the stack for argc and argv */
/* (stack is aligned to 16 bytes in riscv calling convention) */
addi sp,sp,-16
sw zero,0(sp)
sw zero,4(sp)
sw zero,8(sp)
sw zero,12(sp)

/* jump to libc init */
j application_entry_point
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_0 | picorv32_scripts_csmith_testbench -->

#include "Vtestbench.h"
#include "verilated.h"

int main(int argc, char **argv, char **env)
{
	Verilated::commandArgs(argc, argv);
	Vtestbench* top = new Vtestbench;

	top->clk = 0;
	while (!Verilated::gotFinish()) {
		top->clk = !top->clk;
		top->eval();
	}

	delete top;
	exit(0);
}

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_1 | module testbench ( -->

# Verilog Block: `module testbench (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 3–16

```verilog
module testbench (
`ifdef VERILATOR
	input clk
`endif
);
`ifndef VERILATOR
	reg clk = 1;
	always #5 clk = ~clk;
`endif

	reg resetn = 0;
	integer resetn_cnt = 0;
	wire trap;
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 17–21

```verilog
initial begin
		// $dumpfile("testbench.vcd");
		// $dumpvars(0, testbench);
	end
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 22–39

```verilog
always @(posedge clk) begin
		if (resetn_cnt < 100)
			resetn_cnt <= resetn_cnt + 1;
		else
			resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	wire mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	wire [31:0] mem_rdata;

	reg [31:0] x32 = 314159265;
	reg [31:0] next_x32;
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 40–67

```verilog
always @(posedge clk) begin
		if (resetn) begin
			next_x32 = x32;
			next_x32 = next_x32 ^ (next_x32 << 13);
			next_x32 = next_x32 ^ (next_x32 >> 17);
			next_x32 = next_x32 ^ (next_x32 << 5);
			x32 <= next_x32;
		end
	end

	picorv32 #(
		.COMPRESSED_ISA(1),
		.ENABLE_MUL(1),
		.ENABLE_DIV(1)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	reg [7:0] memory [0:4*1024*1024-1];
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_5 | initial $readmemh("test.hex", memory); -->

# Verilog Block: `initial $readmemh("test.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 68–76

```verilog
initial $readmemh("test.hex", memory);

	assign mem_ready = x32[0] && mem_valid;

	assign mem_rdata[ 7: 0] = memory[mem_addr + 0];
	assign mem_rdata[15: 8] = memory[mem_addr + 1];
	assign mem_rdata[23:16] = memory[mem_addr + 2];
	assign mem_rdata[31:24] = memory[mem_addr + 3];
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_6 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 77–92

```verilog
always @(posedge clk) begin
		if (mem_valid && mem_ready) begin
			if (mem_wstrb && mem_addr == 'h10000000) begin
				$write("%c", mem_wdata[ 7: 0]);
`ifndef VERILATOR
				$fflush;
`endif
			end else begin
				if (mem_wstrb[0]) memory[mem_addr + 0] <= mem_wdata[ 7: 0];
				if (mem_wstrb[1]) memory[mem_addr + 1] <= mem_wdata[15: 8];
				if (mem_wstrb[2]) memory[mem_addr + 2] <= mem_wdata[23:16];
				if (mem_wstrb[3]) memory[mem_addr + 3] <= mem_wdata[31:24];
			end
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_csmith_testbench_7 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/csmith/testbench.v` | Lines 93–99

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			// repeat (10) @(posedge clk);
			// $display("TRAP");
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_Makefile_0 | picorv32_scripts_cxxdemo_Makefile -->

RISCV_TOOLS_PREFIX = /opt/riscv32ic/bin/riscv32-unknown-elf-
CXX = $(RISCV_TOOLS_PREFIX)g++
CC = $(RISCV_TOOLS_PREFIX)gcc
AS = $(RISCV_TOOLS_PREFIX)gcc
CXXFLAGS = -MD -Os -Wall -std=c++11
CFLAGS = -MD -Os -Wall -std=c++11
LDFLAGS = -Wl,--gc-sections
LDLIBS = -lstdc++

test: testbench.vvp firmware32.hex
	vvp -N testbench.vvp

testbench.vvp: testbench.v ../../picorv32.v
	iverilog -o testbench.vvp testbench.v ../../picorv32.v
	chmod -x testbench.vvp

firmware32.hex: firmware.elf start.elf hex8tohex32.py
	$(RISCV_TOOLS_PREFIX)objcopy -O verilog start.elf start.tmp
	$(RISCV_TOOLS_PREFIX)objcopy -O verilog firmware.elf firmware.tmp
	cat start.tmp firmware.tmp > firmware.hex
	python3 hex8tohex32.py firmware.hex > firmware32.hex
	rm -f start.tmp firmware.tmp

firmware.elf: firmware.o syscalls.o
	$(CC) $(LDFLAGS) -o $@ $^ -T ../../firmware/riscv.ld $(LDLIBS)
	chmod -x firmware.elf

start.elf: start.S start.ld
	$(CC) -nostdlib -o start.elf start.S -T start.ld $(LDLIBS)
	chmod -x start.elf

clean:
	rm -f *.o *.d *.tmp start.elf
	rm -f firmware.elf firmware.hex firmware32.hex
	rm -f testbench.vvp testbench.vcd

-include *.d
.PHONY: test clean

---
<!-- chunk_id=picorv32_scripts_cxxdemo_firmware_0 | picorv32_scripts_cxxdemo_firmware -->

#include <stdio.h>
#include <iostream>
#include <vector>
#include <algorithm>

class ExampleBaseClass
{
public:
	ExampleBaseClass() {
		std::cout << "ExampleBaseClass()" << std::endl;
	}

	virtual ~ExampleBaseClass() {
		std::cout << "~ExampleBaseClass()" << std::endl;
	}

	virtual void print_something_virt() {
		std::cout << "ExampleBaseClass::print_something_virt()" << std::endl;
	}

	void print_something_novirt() {
		std::cout << "ExampleBaseClass::print_something_novirt()" << std::endl;
	}
};

class ExampleSubClass : public ExampleBaseClass
{
public:
	ExampleSubClass() {
		std::cout << "ExampleSubClass()" << std::endl;
	}

	virtual ~ExampleSubClass() {
		std::cout << "~ExampleSubClass()" << std::endl;
	}

	virtual void print_something_virt() {
		std::cout << "ExampleSubClass::print_something_virt()" << std::endl;
	}

	void print_something_novirt() {
		std::cout << "ExampleSubClass::print_something_novirt()" << std::endl;
	}
};

int main()
{
	printf("Hello World, C!\n");

	std::cout << "Hello World, C++!" << std::endl;

	ExampleBaseClass *obj = new ExampleBaseClass;
	obj->print_something_virt();
	obj->print_something_novirt();
	delete obj;

	obj = new ExampleSubClass;
	obj->print_something_virt();
	obj->print_something_novirt();
	delete obj;

	std::vector<unsigned int> some_ints;
	some_ints.push_back(0x48c9b3e4);
	some_ints.push_back(0x79109b6a);
	some_ints.push_back(0x16155039);
	some_ints.push_back(0xa3635c9a);
	some_ints.push_back(0x8d2f4702);
	some_ints.push_back(0x38d232ae);
	some_ints.push_back(0x93924a17);
	some_ints.push_back(0x62b895cc);
	some_ints.push_back(0x6130d459);
	some_ints.push_back(0x837c8b44);
	some_ints.push_back(0x3d59b4fe);
	some_ints.push_back(0x444914d8);
	some_ints.push_back(0x3a3dc660);
	some_ints.push_back(0xe5a121ef);
	some_ints.push_back(0xff00866d);
	some_ints.push_back(0xb843b879);

	std::sort(some_ints.begin(), some_ints.end());

	for (auto n : some_ints)
		std::cout << std::hex << n << std::endl;

	std::cout << "All done." << std::endl;
	return 0;
}

---
<!-- chunk_id=picorv32_scripts_cxxdemo_start_asm | Assembly Test: PICORV32_SCRIPTS_CXXDEMO_START -->

# Assembly Test: `PICORV32_SCRIPTS_CXXDEMO_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text
.global _ftext
.global _pvstart

_pvstart:
/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */
lui sp, %hi(4*1024*1024)
addi sp, sp, %lo(4*1024*1024)

/* push zeros on the stack for argc and argv */
/* (stack is aligned to 16 bytes in riscv calling convention) */
addi sp,sp,-16
sw zero,0(sp)
sw zero,4(sp)
sw zero,8(sp)
sw zero,12(sp)

/* jump to libc init */
j _ftext
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 1–5

```verilog
`timescale 1 ns / 1 ps
`undef VERBOSE_MEM
`undef WRITE_VCD
`undef MEM8BIT
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 6–12

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 13–43

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg  [31:0] mem_rdata;

	picorv32 #(
		.COMPRESSED_ISA(1)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	localparam MEM_SIZE = 4*1024*1024;
`ifdef MEM8BIT
	reg [7:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_3 | initial $readmemh("firmware.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 44–46

```verilog
initial $readmemh("firmware.hex", memory);
`else
	reg [31:0] memory [0:MEM_SIZE/4-1];
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_4 | initial $readmemh("firmware32.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware32.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 47–49

```verilog
initial $readmemh("firmware32.hex", memory);
`endif
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 50–100

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		if (mem_valid && !mem_ready) begin
			mem_ready <= 1;
			mem_rdata <= 'bx;
			case (1)
				mem_addr < MEM_SIZE: begin
`ifdef MEM8BIT
					if (|mem_wstrb) begin
						if (mem_wstrb[0]) memory[mem_addr + 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr + 1] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr + 2] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr + 3] <= mem_wdata[31:24];
					end else begin
						mem_rdata <= {memory[mem_addr+3], memory[mem_addr+2], memory[mem_addr+1], memory[mem_addr]};
					end
`else
					if (|mem_wstrb) begin
						if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					end else begin
						mem_rdata <= memory[mem_addr >> 2];
					end
`endif
				end
				mem_addr == 32'h 1000_0000: begin
					$write("%c", mem_wdata[7:0]);
				end
			endcase
		end
		if (mem_valid && mem_ready) begin
`ifdef VERBOSE_MEM
			if (|mem_wstrb)
				$display("WR: ADDR=%x DATA=%x MASK=%b", mem_addr, mem_wdata, mem_wstrb);
			else
				$display("RD: ADDR=%x DATA=%x%s", mem_addr, mem_rdata, mem_instr ? " INSN" : "");
`endif
			if (^mem_addr === 1'bx ||
					(mem_wstrb[0] && ^mem_wdata[ 7: 0] == 1'bx) ||
					(mem_wstrb[1] && ^mem_wdata[15: 8] == 1'bx) ||
					(mem_wstrb[2] && ^mem_wdata[23:16] == 1'bx) ||
					(mem_wstrb[3] && ^mem_wdata[31:24] == 1'bx)) begin
				$display("CRITICAL UNDEF MEM TRANSACTION");
				$finish;
			end
		end
	end

`ifdef WRITE_VCD
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_6 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 101–106

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);
	end
`endif
```

---
<!-- chunk_id=picorv32_scripts_cxxdemo_testbench_7 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/cxxdemo/testbench.v` | Lines 107–113

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			repeat (10) @(posedge clk);
			$display("TRAP");
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_0 | set to 4 for simulation -->

# set to 4 for simulation
FIRMWARE_COUNTER_BITS=18

all: example.bin

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_2 | firmware generation -->

## firmware generation

firmware.elf: firmware.S firmware.c firmware.lds
	$(TOOLCHAIN_PREFIX)gcc \
		-DSHIFT_COUNTER_BITS=$(FIRMWARE_COUNTER_BITS) \
		-march=rv32i -Os -ffreestanding -nostdlib \
		-o $@ firmware.S firmware.c \
		--std=gnu99 -Wl,-Bstatic,-T,firmware.lds,-Map,firmware.map,--strip-debug
	chmod -x $@

firmware.bin: firmware.elf
	$(TOOLCHAIN_PREFIX)objcopy -O binary $< $@
	chmod -x $@

firmware.hex: firmware.bin
	python3 ../../firmware/makehex.py $< 128 > $@

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_4 | main flow: synth/p&r/bitstream -->

## main flow: synth/p&r/bitstream

synth.json: example.v ../../picorv32.v firmware.hex
	yosys -v3 -l synth.log -p 'synth_ice40 -top top -json $@; write_verilog -attr2comment synth.v' $(filter %.v, $^)

example.asc: synth.json example.pcf
	nextpnr-ice40 --hx8k --package ct256 --json $< --pcf example.pcf --asc $@

example.bin: example.asc
	icepack $< $@

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_6 | icarus simulation -->

## icarus simulation

example_tb.vvp: example.v example_tb.v ../../picorv32.v firmware.hex
	iverilog -o $@ -s testbench $(filter %.v, $^)
	chmod -x $@

example_sim: example_tb.vvp
	vvp -N $<

example_sim_vcd: example_tb.vvp
	vvp -N $< +vcd

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_8 | post-synth simulation -->

## post-synth simulation

synth_tb.vvp: example_tb.v synth.json
	iverilog -o $@ -s testbench synth.v example_tb.v $(ICE40_SIM_CELLS)
	chmod -x $@

synth_sim: synth_tb.vvp
	vvp -N $<

synth_sim_vcd: synth_tb.vvp
	vvp -N $< +vcd

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_10 | post-route simulation -->

## post-route simulation

route.v: example.asc example.pcf
	icebox_vlog -L -n top -sp example.pcf $< > $@

route_tb.vvp: route.v example_tb.v
	iverilog -o $@ -s testbench $^ $(ICE40_SIM_CELLS)
	chmod -x $@

route_sim: route_tb.vvp
	vvp -N $<

route_sim_vcd: route_tb.vvp
	vvp -N $< +vcd

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_12 | miscellaneous targets -->

## miscellaneous targets

prog_sram: example.bin
	iceprog -S $<

timing: example.asc example.pcf
	icetime -c 62 -tmd hx8k -P ct256 -p example.pcf -t $<

view: example.vcd
	gtkwave $< example.gtkw

---
<!-- chunk_id=picorv32_scripts_icestorm_Makefile_14 | el fin -->

## el fin

clean:
	rm -f firmware.elf firmware.map firmware.bin firmware.hex
	rm -f synth.log synth.v synth.json route.v example.asc example.bin
	rm -f example_tb.vvp synth_tb.vvp route_tb.vvp example.vcd

.PHONY: all prog_sram view clean
.PHONY: example_sim synth_sim route_sim timing
.PHONY: example_sim_vcd synth_sim_vcd route_sim_vcd

---
<!-- chunk_id=picorv32_scripts_icestorm_example_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_1 | module top ( -->

# Verilog Block: `module top (`

> **Block Comment:** -------------------------------

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example.v` | Lines 3–12

```verilog
module top (
	input clk,
	output reg LED0, LED1, LED2, LED3, LED4, LED5, LED6, LED7
);
	// -------------------------------
	// Reset Generator

	reg [7:0] resetn_counter = 0;
	wire resetn = &resetn_counter;
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example.v` | Lines 13–54

```verilog
always @(posedge clk) begin
		if (!resetn)
			resetn_counter <= resetn_counter + 1;
	end


	// -------------------------------
	// PicoRV32 Core

	wire mem_valid;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;

	reg mem_ready;
	reg [31:0] mem_rdata;

	picorv32 #(
		.ENABLE_COUNTERS(0),
		.LATCHED_MEM_RDATA(1),
		.TWO_STAGE_SHIFT(0),
		.TWO_CYCLE_ALU(1),
		.CATCH_MISALIGN(0),
		.CATCH_ILLINSN(0)
	) cpu (
		.clk      (clk      ),
		.resetn   (resetn   ),
		.mem_valid(mem_valid),
		.mem_ready(mem_ready),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_rdata(mem_rdata)
	);


	// -------------------------------
	// Memory/IO Interface

	// 128 32bit words = 512 bytes memory
	localparam MEM_SIZE = 128;
	reg [31:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_3 | initial $readmemh("firmware.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example.v` | Lines 55–56

```verilog
initial $readmemh("firmware.hex", memory);
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example.v` | Lines 57–79

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		if (resetn && mem_valid && !mem_ready) begin
			(* parallel_case *)
			case (1)
				!mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					mem_rdata <= memory[mem_addr >> 2];
					mem_ready <= 1;
				end
				|mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
					if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
					if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
					if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					mem_ready <= 1;
				end
				|mem_wstrb && mem_addr == 32'h1000_0000: begin
					{LED7, LED6, LED5, LED4, LED3, LED2, LED1, LED0} <= mem_wdata;
					mem_ready <= 1;
				end
			endcase
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_tb_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example_tb.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_tb_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example_tb.v` | Lines 3–19

```verilog
module testbench;
	reg clk = 1;
	always #5 clk = ~clk;
	wire LED0, LED1, LED2, LED3, LED4, LED5, LED6, LED7;

	top uut (
		.clk(clk),
		.LED0(LED0),
		.LED1(LED1),
		.LED2(LED2),
		.LED3(LED3),
		.LED4(LED4),
		.LED5(LED5),
		.LED6(LED6),
		.LED7(LED7)
	);
```

---
<!-- chunk_id=picorv32_scripts_icestorm_example_tb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/example_tb.v` | Lines 20–29

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("example.vcd");
			$dumpvars(0, testbench);
		end

		$monitor(LED7, LED6, LED5, LED4, LED3, LED2, LED1, LED0);
		repeat (10000) @(posedge clk);
		$finish;
	end
```

---
<!-- chunk_id=picorv32_scripts_icestorm_firmware_asm | Assembly Test: PICORV32_SCRIPTS_ICESTORM_FIRMWARE -->

# Assembly Test: `PICORV32_SCRIPTS_ICESTORM_FIRMWARE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/icestorm/firmware.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .init
.global main

/* set stack pointer */
lui sp, %hi(512)
addi sp, sp, %lo(512)

/* call main */
jal ra, main

/* break */
ebreak
```

---
<!-- chunk_id=picorv32_scripts_icestorm_readme_0 | picorv32_scripts_icestorm_readme -->

To build the example LED-blinking firmware for an HX8K Breakout Board and get
a timing report (checked against the default 12MHz oscillator):

    $ make clean example.bin timing

To run all the simulation tests:

    $ make clean example_sim synth_sim route_sim FIRMWARE_COUNTER_BITS=4

(You must run the `clean` target to rebuild the firmware with the updated
`FIRMWARE_COUNTER_BITS` parameter; the firmware source must be recompiled for
simulation vs hardware, but this is not tracked as a Makefile dependency.)

---
<!-- chunk_id=picorv32_scripts_presyn_Makefile_0 | picorv32_scripts_presyn_Makefile -->

TOOLCHAIN_PREFIX = /opt/riscv32ic/bin/riscv32-unknown-elf-

run: testbench.vvp firmware.hex
	vvp -N testbench.vvp

firmware.hex: firmware.S firmware.c firmware.lds
	$(TOOLCHAIN_PREFIX)gcc -Os -ffreestanding -nostdlib -o firmware.elf firmware.S firmware.c \
		 --std=gnu99 -Wl,-Bstatic,-T,firmware.lds,-Map,firmware.map,--strip-debug -lgcc
	$(TOOLCHAIN_PREFIX)objcopy -O binary firmware.elf firmware.bin
	python3 ../../firmware/makehex.py firmware.bin 4096 > firmware.hex

picorv32_presyn.v: picorv32_presyn.ys picorv32_regs.txt ../../picorv32.v
	yosys -v0 picorv32_presyn.ys

testbench.vvp: testbench.v picorv32_presyn.v
	iverilog -o testbench.vvp testbench.v picorv32_presyn.v

clean:
	rm -f firmware.bin firmware.elf firmware.hex firmware.map
	rm -f picorv32_presyn.v testbench.vvp testbench.vcd

---
<!-- chunk_id=picorv32_scripts_presyn_README_0 | picorv32_scripts_presyn_README -->

A simple example for how to use Yosys to "pre-synthesize" PicoRV32 in
a way that can utilize an external memory module for the register file.

See also:
https://github.com/cliffordwolf/picorv32/issues/30

---
<!-- chunk_id=picorv32_scripts_presyn_firmware_asm | Assembly Test: PICORV32_SCRIPTS_PRESYN_FIRMWARE -->

# Assembly Test: `PICORV32_SCRIPTS_PRESYN_FIRMWARE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/firmware.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .init
.global main

entry:

/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */
lui sp, %hi(16*1024)
addi sp, sp, %lo(16*1024)

/* call main */
jal ra, main

/* break */
ebreak
```

---
<!-- chunk_id=picorv32_scripts_presyn_picorv32_presyn_0 | picorv32_scripts_presyn_picorv32_presyn -->

read_verilog ../../picorv32.v
chparam -set COMPRESSED_ISA 1 picorv32
prep -top picorv32
memory_bram -rules picorv32_regs.txt
write_verilog -noattr picorv32_presyn.v

---
<!-- chunk_id=picorv32_scripts_presyn_picorv32_regs_0 | picorv32_scripts_presyn_picorv32_regs -->

bram picorv32_regs
  init 0
  abits 5
  dbits 32
  groups 2
  ports  2 1
  wrmode 0 1
  enable 0 1
  transp 0 0
  clocks 1 1
  clkpol 1 1
endbram

match picorv32_regs
  make_transp
endmatch

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_0 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 1–5

```verilog
module testbench;
	reg clk = 1;
	always #5 clk = ~clk;

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_1 | always @(posedge clk) resetn <= 1; -->

# Verilog Block: `always @(posedge clk) resetn <= 1;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 6–33

```verilog
always @(posedge clk) resetn <= 1;

	wire        trap;
	wire        mem_valid;
	wire        mem_instr;
	reg         mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0]  mem_wstrb;
	reg  [31:0] mem_rdata;

	picorv32 UUT (
		.clk      (clk      ),
		.resetn   (resetn   ),
		.trap     (trap     ),
		.mem_valid(mem_valid),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_rdata(mem_rdata)
	);

	// 4096 32bit words = 16kB memory
	localparam MEM_SIZE = 4096;

	reg [31:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_2 | initial $readmemh("firmware.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 34–35

```verilog
initial $readmemh("firmware.hex", memory);
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 36–62

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		mem_rdata <= 'bx;

		if (resetn && mem_valid && !mem_ready) begin
			mem_ready <= 1;
			if (mem_wstrb) begin
				if (mem_addr == 32'h1000_0000) begin
					$write("%c", mem_wdata[7:0]);
					$fflush;
				end else begin
					if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
					if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
					if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
					if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
				end
			end else begin
				mem_rdata <= memory[mem_addr >> 2];
			end
		end

		if (resetn && trap) begin
			$display("TRAP.");
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_4 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 63–66

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);
	end
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_6 | module picorv32_regs ( -->

# Verilog Block: `module picorv32_regs (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 69–75

```verilog
module picorv32_regs (
	input [4:0] A1ADDR, A2ADDR, B1ADDR,
	output reg [31:0] A1DATA, A2DATA,
	input [31:0] B1DATA,
	input B1EN, CLK1
);
	reg [31:0] memory [0:31];
```

---
<!-- chunk_id=picorv32_scripts_presyn_testbench_7 | always @(posedge CLK1) begin -->

# Verilog Block: `always @(posedge CLK1) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/presyn/testbench.v` | Lines 76–80

```verilog
always @(posedge CLK1) begin
		A1DATA <= memory[A1ADDR];
		A2DATA <= memory[A2ADDR];
		if (B1EN) memory[B1ADDR] <= B1DATA;
	end
```

---
<!-- chunk_id=picorv32_scripts_quartus_Makefile_0 | picorv32_scripts_quartus_Makefile -->

export QUARTUS_ROOTDIR = /opt/altera_lite/16.0
export QUARTUS_BIN = $(QUARTUS_ROOTDIR)/quartus/bin

VLOG = iverilog
TOOLCHAIN_PREFIX = /opt/riscv32i/bin/riscv32-unknown-elf-

help:
	@echo ""
	@echo "Simple synthesis tests:"
	@echo "  make synth_area_{small|regular|large}"
	@echo "  make synth_speed"
	@echo ""
	@echo "Example system:"
	@echo "  make synth_system"
	@echo "  make sim_system"
	@echo ""
	@echo "Timing and Utilization Evaluation:"
	@echo "  make table.txt"
	@echo "  make area"
	@echo ""

synth_%:
	rm -f $@.log
	mkdir -p $@_build
	cp $@.qsf $@_build
	cd $@_build && $(QUARTUS_BIN)/quartus_map $@.qsf
	cd $@_build && $(QUARTUS_BIN)/quartus_fit --read_settings_files=off -write_settings_files=off $@ -c $@
	cd $@_build && $(QUARTUS_BIN)/quartus_sta $@ -c $@
	-cd $@_build && grep -A3 "Total logic elements" output_files/$@.fit.summary
	-cd $@_build && grep -B1 "Slack" output_files/$@.sta.summary

synth_system: firmware.hex

sim_system: firmware.hex system_tb.v system.v ../../picorv32.v
	$(VLOG) -o system_tb system_tb.v system.v ../../picorv32.v
	./system_tb

firmware.hex: firmware.S firmware.c firmware.lds
	$(TOOLCHAIN_PREFIX)gcc -Os -ffreestanding -nostdlib -o firmware.elf firmware.S firmware.c \
		 --std=gnu99 -Wl,-Bstatic,-T,firmware.lds,-Map,firmware.map,--strip-debug -lgcc
	$(TOOLCHAIN_PREFIX)objcopy -O binary firmware.elf firmware.bin
	python3 ../../firmware/makehex.py firmware.bin 4096 > firmware.hex

tab_%/results.txt:
	bash tabtest.sh $@

area: synth_area_small synth_area_regular synth_area_large
	-grep -A3 "Total logic elements" synth_area_*_build/output_files/synth_area_*.fit.summary

table.txt: tab_small_ep4ce_c7/results.txt
table.txt: tab_small_ep4cgx_c7/results.txt
table.txt: tab_small_5cgx_c7/results.txt

table.txt:
	bash table.sh > table.txt

clean:
	rm -rf firmware.bin firmware.elf firmware.hex firmware.map synth_*.log
	rm -rf table.txt tab_*/
	rm -rf synth_*_build

---
<!-- chunk_id=picorv32_scripts_quartus_firmware_asm | Assembly Test: PICORV32_SCRIPTS_QUARTUS_FIRMWARE -->

# Assembly Test: `PICORV32_SCRIPTS_QUARTUS_FIRMWARE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/firmware.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .init
.global main

/* set stack pointer */
lui sp, %hi(16*1024)
addi sp, sp, %lo(16*1024)

/* call main */
jal ra, main

/* break */
ebreak
```

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_0 | picorv32_scripts_quartus_synth_area -->

create_clock -period 20.00 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_large_0 | picorv32_scripts_quartus_synth_area_large -->

set_global_assignment -name DEVICE ep4ce40f29c7
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY top_large
set_global_assignment -name VERILOG_FILE ../synth_area_top.v
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE ../synth_area.sdc

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_regular_0 | picorv32_scripts_quartus_synth_area_regular -->

set_global_assignment -name DEVICE ep4ce40f29c7
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY top_regular
set_global_assignment -name VERILOG_FILE ../synth_area_top.v
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE ../synth_area.sdc

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_small_0 | picorv32_scripts_quartus_synth_area_small -->

set_global_assignment -name DEVICE ep4ce40f29c7
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY top_small
set_global_assignment -name VERILOG_FILE ../synth_area_top.v
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE ../synth_area.sdc

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_top_1 | module top_small ( -->

# Verilog Block: `module top_small (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/synth_area_top.v` | Lines 2–30

```verilog
module top_small (
	input clk, resetn,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata
);
	picorv32 #(
		.ENABLE_COUNTERS(0),
		.LATCHED_MEM_RDATA(1),
		.TWO_STAGE_SHIFT(0),
		.CATCH_MISALIGN(0),
		.CATCH_ILLINSN(0)
	) picorv32 (
		.clk      (clk      ),
		.resetn   (resetn   ),
		.mem_valid(mem_valid),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_rdata(mem_rdata)
	);
```

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_top_3 | module top_regular ( -->

# Verilog Block: `module top_regular (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/synth_area_top.v` | Lines 33–69

```verilog
module top_regular (
	input clk, resetn,
	output trap,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata,

	// Look-Ahead Interface
	output        mem_la_read,
	output        mem_la_write,
	output [31:0] mem_la_addr,
	output [31:0] mem_la_wdata,
	output [ 3:0] mem_la_wstrb
);
	picorv32 picorv32 (
		.clk         (clk         ),
		.resetn      (resetn      ),
		.trap        (trap        ),
		.mem_valid   (mem_valid   ),
		.mem_instr   (mem_instr   ),
		.mem_ready   (mem_ready   ),
		.mem_addr    (mem_addr    ),
		.mem_wdata   (mem_wdata   ),
		.mem_wstrb   (mem_wstrb   ),
		.mem_rdata   (mem_rdata   ),
		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb)
	);
```

---
<!-- chunk_id=picorv32_scripts_quartus_synth_area_top_5 | module top_large ( -->

# Verilog Block: `module top_large (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/synth_area_top.v` | Lines 72–138

```verilog
module top_large (
	input clk, resetn,
	output trap,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata,

	// Look-Ahead Interface
	output        mem_la_read,
	output        mem_la_write,
	output [31:0] mem_la_addr,
	output [31:0] mem_la_wdata,
	output [ 3:0] mem_la_wstrb,

	// Pico Co-Processor Interface (PCPI)
	output        pcpi_valid,
	output [31:0] pcpi_insn,
	output [31:0] pcpi_rs1,
	output [31:0] pcpi_rs2,
	input         pcpi_wr,
	input  [31:0] pcpi_rd,
	input         pcpi_wait,
	input         pcpi_ready,

	// IRQ Interface
	input  [31:0] irq,
	output [31:0] eoi
);
	picorv32 #(
		.COMPRESSED_ISA(1),
		.BARREL_SHIFTER(1),
		.ENABLE_PCPI(1),
		.ENABLE_MUL(1),
		.ENABLE_IRQ(1)
	) picorv32 (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.trap           (trap           ),
		.mem_valid      (mem_valid      ),
		.mem_instr      (mem_instr      ),
		.mem_ready      (mem_ready      ),
		.mem_addr       (mem_addr       ),
		.mem_wdata      (mem_wdata      ),
		.mem_wstrb      (mem_wstrb      ),
		.mem_rdata      (mem_rdata      ),
		.mem_la_read    (mem_la_read    ),
		.mem_la_write   (mem_la_write   ),
		.mem_la_addr    (mem_la_addr    ),
		.mem_la_wdata   (mem_la_wdata   ),
		.mem_la_wstrb   (mem_la_wstrb   ),
		.pcpi_valid     (pcpi_valid     ),
		.pcpi_insn      (pcpi_insn      ),
		.pcpi_rs1       (pcpi_rs1       ),
		.pcpi_rs2       (pcpi_rs2       ),
		.pcpi_wr        (pcpi_wr        ),
		.pcpi_rd        (pcpi_rd        ),
		.pcpi_wait      (pcpi_wait      ),
		.pcpi_ready     (pcpi_ready     ),
		.irq            (irq            ),
		.eoi            (eoi            )
	);
```

---
<!-- chunk_id=picorv32_scripts_quartus_synth_speed_0 | picorv32_scripts_quartus_synth_speed -->

set_global_assignment -name DEVICE ep4ce40f29c7
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY picorv32_axi
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE ../synth_speed.sdc

---
<!-- chunk_id=picorv32_scripts_quartus_synth_speed_0 | picorv32_scripts_quartus_synth_speed -->

create_clock -period 2.5 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_quartus_synth_system_0 | picorv32_scripts_quartus_synth_system -->

set_global_assignment -name DEVICE ep4ce40f29c7
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY system
set_global_assignment -name VERILOG_FILE ../system.v
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE ../synth_system.sdc

---
<!-- chunk_id=picorv32_scripts_quartus_synth_system_0 | picorv32_scripts_quartus_synth_system -->

create_clock -period 10.00 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_quartus_synth_system_0 | write_mem_info -force synth_system.mmi -->

# write_mem_info -force synth_system.mmi

---
<!-- chunk_id=picorv32_scripts_quartus_system_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_1 | module system ( -->

# Verilog Block: `module system (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 3–48

```verilog
module system (
	input            clk,
	input            resetn,
	output           trap,
	output reg [7:0] out_byte,
	output reg       out_byte_en
);
	// set this to 0 for better timing but less performance/MHz
	parameter FAST_MEMORY = 0;

	// 4096 32bit words = 16kB memory
	parameter MEM_SIZE = 4096;

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg [31:0] mem_rdata;

	wire mem_la_read;
	wire mem_la_write;
	wire [31:0] mem_la_addr;
	wire [31:0] mem_la_wdata;
	wire [3:0] mem_la_wstrb;

	picorv32 picorv32_core (
		.clk         (clk         ),
		.resetn      (resetn      ),
		.trap        (trap        ),
		.mem_valid   (mem_valid   ),
		.mem_instr   (mem_instr   ),
		.mem_ready   (mem_ready   ),
		.mem_addr    (mem_addr    ),
		.mem_wdata   (mem_wdata   ),
		.mem_wstrb   (mem_wstrb   ),
		.mem_rdata   (mem_rdata   ),
		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb)
	);

	reg [31:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_2 | initial $readmemh("firmware.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 49–53

```verilog
initial $readmemh("firmware.hex", memory);

	reg [31:0] m_read_data;
	reg m_read_en;
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_3 | generate if (FAST_MEMORY) begin -->

# Verilog Block: `generate if (FAST_MEMORY) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 54–54

```verilog
generate if (FAST_MEMORY) begin
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 55–71

```verilog
always @(posedge clk) begin
			mem_ready <= 1;
			out_byte_en <= 0;
			mem_rdata <= memory[mem_la_addr >> 2];
			if (mem_la_write && (mem_la_addr >> 2) < MEM_SIZE) begin
				if (mem_la_wstrb[0]) memory[mem_la_addr >> 2][ 7: 0] <= mem_la_wdata[ 7: 0];
				if (mem_la_wstrb[1]) memory[mem_la_addr >> 2][15: 8] <= mem_la_wdata[15: 8];
				if (mem_la_wstrb[2]) memory[mem_la_addr >> 2][23:16] <= mem_la_wdata[23:16];
				if (mem_la_wstrb[3]) memory[mem_la_addr >> 2][31:24] <= mem_la_wdata[31:24];
			end
			else
			if (mem_la_write && mem_la_addr == 32'h1000_0000) begin
				out_byte_en <= 1;
				out_byte <= mem_la_wdata;
			end
		end
	end else begin
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system.v` | Lines 72–100

```verilog
always @(posedge clk) begin
			m_read_en <= 0;
			mem_ready <= mem_valid && !mem_ready && m_read_en;

			m_read_data <= memory[mem_addr >> 2];
			mem_rdata <= m_read_data;

			out_byte_en <= 0;

			(* parallel_case *)
			case (1)
				mem_valid && !mem_ready && !mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					m_read_en <= 1;
				end
				mem_valid && !mem_ready && |mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
					if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
					if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
					if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					mem_ready <= 1;
				end
				mem_valid && !mem_ready && |mem_wstrb && mem_addr == 32'h1000_0000: begin
					out_byte_en <= 1;
					out_byte <= mem_wdata;
					mem_ready <= 1;
				end
			endcase
		end
	end endgenerate
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_tb_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system_tb.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_tb_1 | module system_tb; -->

# Verilog Block: `module system_tb;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system_tb.v` | Lines 3–7

```verilog
module system_tb;
	reg clk = 1;
	always #5 clk = ~clk;

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_tb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system_tb.v` | Lines 8–28

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("system.vcd");
			$dumpvars(0, system_tb);
		end
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire trap;
	wire [7:0] out_byte;
	wire out_byte_en;

	system uut (
		.clk        (clk        ),
		.resetn     (resetn     ),
		.trap       (trap       ),
		.out_byte   (out_byte   ),
		.out_byte_en(out_byte_en)
	);
```

---
<!-- chunk_id=picorv32_scripts_quartus_system_tb_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/system_tb.v` | Lines 29–37

```verilog
always @(posedge clk) begin
		if (resetn && out_byte_en) begin
			$write("%c", out_byte);
			$fflush;
		end
		if (resetn && trap) begin
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_quartus_table_0 | picorv32_scripts_quartus_table -->

#!/bin/bash

dashes="----------------------------------------------------------------"
printf '| %-25s | %-10s | %-20s |\n' "Device" "Speedgrade" "Clock Period (Freq.)"
printf '|:%.25s |:%.10s:| %.20s:|\n' $dashes $dashes $dashes

for x in $( grep -H . tab_*/results.txt )
do
	read _ size device grade _ speed < <( echo "$x" | tr _/: ' ' )
	case "$device" in
		ep4ce)  d="Altera Cyclone IV E" ;;
		ep4cgx) d="Altera Cyclone IV GX" ;;
		5cgx)   d="Altera Cyclone V GX" ;;
	esac
	speedtxt=$( printf '%s.%s ns (%d MHz)' ${speed%?} ${speed#?} $((10000 / speed)) )
	printf '| %-25s | %-10s | %20s |\n' "$d" "-$grade" "$speedtxt"
done

---
<!-- chunk_id=picorv32_scripts_quartus_tabtest_0 | rm -rf tab_${ip}_${dev}_${grade} -->

# rm -rf tab_${ip}_${dev}_${grade}
mkdir -p tab_${ip}_${dev}_${grade}
cd tab_${ip}_${dev}_${grade}

max_speed=99
min_speed=01
best_speed=99

synth_case() {
	if [ -f test_${1}.txt ]; then
		echo "Reusing cached tab_${ip}_${dev}_${grade}/test_${1}."
		return
	fi

	case "${dev}" in
		ep4ce)  al_device="ep4ce30f23${grade}" ;;
		ep4cgx) al_device="ep4cgx50df27${grade}" ;;
		5cgx)   al_device="5cgxbc9c6f23${grade}" ;;
	esac

	cat > test_${1}.qsf <<- EOT
set_global_assignment -name DEVICE ${al_device}
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name TOP_LEVEL_ENTITY top
set_global_assignment -name VERILOG_FILE ../tabtest.v
set_global_assignment -name VERILOG_FILE ../../../picorv32.v
set_global_assignment -name SDC_FILE test_${1}.sdc
	EOT

	cat > test_${1}.sdc <<- EOT
		create_clock -period ${speed%?}.${speed#?} [get_ports clk]
	EOT

	echo "Running tab_${ip}_${dev}_${grade}/test_${1}.."

    if ! $QUARTUS_BIN/quartus_map test_${1}; then
        exit 1
    fi
    if ! $QUARTUS_BIN/quartus_fit --read_settings_files=off --write_settings_files=off test_${1} -c test_${1}; then
        exit 1
    fi
    if ! $QUARTUS_BIN/quartus_sta test_${1} -c test_${1}; then
        exit 1
    fi

	cp output_files/test_${1}.sta.summary test_${1}.txt
}

countdown=7
while [ $countdown -gt 0 ]; do
    speed=$(((max_speed+min_speed)/2))
	synth_case $speed

    if grep -q '^Slack : -' test_${speed}.txt; then
		echo "        tab_${ip}_${dev}_${grade}/test_${speed} VIOLATED"
        min_speed=$((speed))
    elif grep -q '^Slack : [^-]' test_${speed}.txt; then
		echo "        tab_${ip}_${dev}_${grade}/test_${speed} MET"
		[ $speed -lt $best_speed ] && best_speed=$speed
        max_speed=$((speed))
	else
		echo "ERROR: No slack line found in $PWD/test_${speed}.txt!"
		exit 1
	fi

    countdown=$((countdown-1))
done

echo "-----------------------"
echo "Best speed for tab_${ip}_${dev}_${grade}: $best_speed"
echo "-----------------------"
echo $best_speed > results.txt

---
<!-- chunk_id=picorv32_scripts_quartus_tabtest_1 | module top ( -->

# Verilog Block: `module top (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/tabtest.v` | Lines 2–100

```verilog
module top (
	input clk, io_resetn,
	output io_trap,

	output        io_mem_axi_awvalid,
	input         io_mem_axi_awready,
	output [31:0] io_mem_axi_awaddr,
	output [ 2:0] io_mem_axi_awprot,

	output        io_mem_axi_wvalid,
	input         io_mem_axi_wready,
	output [31:0] io_mem_axi_wdata,
	output [ 3:0] io_mem_axi_wstrb,

	input         io_mem_axi_bvalid,
	output        io_mem_axi_bready,

	output        io_mem_axi_arvalid,
	input         io_mem_axi_arready,
	output [31:0] io_mem_axi_araddr,
	output [ 2:0] io_mem_axi_arprot,

	input         io_mem_axi_rvalid,
	output        io_mem_axi_rready,
	input  [31:0] io_mem_axi_rdata,

	input  [31:0] io_irq,
	output [31:0] io_eoi
);
	wire resetn;
	wire trap;
	wire mem_axi_awvalid;
	wire mem_axi_awready;
	wire [31:0] mem_axi_awaddr;
	wire [2:0] mem_axi_awprot;
	wire mem_axi_wvalid;
	wire mem_axi_wready;
	wire [31:0] mem_axi_wdata;
	wire [3:0] mem_axi_wstrb;
	wire mem_axi_bvalid;
	wire mem_axi_bready;
	wire mem_axi_arvalid;
	wire mem_axi_arready;
	wire [31:0] mem_axi_araddr;
	wire [2:0] mem_axi_arprot;
	wire mem_axi_rvalid;
	wire mem_axi_rready;
	wire [31:0] mem_axi_rdata;
	wire [31:0] irq;
	wire [31:0] eoi;

	delay4 #( 1) delay_resetn          (clk, io_resetn         ,    resetn         );
	delay4 #( 1) delay_trap            (clk,    trap           , io_trap           );
	delay4 #( 1) delay_mem_axi_awvalid (clk,    mem_axi_awvalid, io_mem_axi_awvalid);
	delay4 #( 1) delay_mem_axi_awready (clk, io_mem_axi_awready,    mem_axi_awready);
	delay4 #(32) delay_mem_axi_awaddr  (clk,    mem_axi_awaddr , io_mem_axi_awaddr );
	delay4 #( 3) delay_mem_axi_awprot  (clk,    mem_axi_awprot , io_mem_axi_awprot );
	delay4 #( 1) delay_mem_axi_wvalid  (clk,    mem_axi_wvalid , io_mem_axi_wvalid );
	delay4 #( 1) delay_mem_axi_wready  (clk, io_mem_axi_wready ,    mem_axi_wready );
	delay4 #(32) delay_mem_axi_wdata   (clk,    mem_axi_wdata  , io_mem_axi_wdata  );
	delay4 #( 4) delay_mem_axi_wstrb   (clk,    mem_axi_wstrb  , io_mem_axi_wstrb  );
	delay4 #( 1) delay_mem_axi_bvalid  (clk, io_mem_axi_bvalid ,    mem_axi_bvalid );
	delay4 #( 1) delay_mem_axi_bready  (clk,    mem_axi_bready , io_mem_axi_bready );
	delay4 #( 1) delay_mem_axi_arvalid (clk,    mem_axi_arvalid, io_mem_axi_arvalid);
	delay4 #( 1) delay_mem_axi_arready (clk, io_mem_axi_arready,    mem_axi_arready);
	delay4 #(32) delay_mem_axi_araddr  (clk,    mem_axi_araddr , io_mem_axi_araddr );
	delay4 #( 3) delay_mem_axi_arprot  (clk,    mem_axi_arprot , io_mem_axi_arprot );
	delay4 #( 1) delay_mem_axi_rvalid  (clk, io_mem_axi_rvalid ,    mem_axi_rvalid );
	delay4 #( 1) delay_mem_axi_rready  (clk,    mem_axi_rready , io_mem_axi_rready );
	delay4 #(32) delay_mem_axi_rdata   (clk, io_mem_axi_rdata  ,    mem_axi_rdata  );
	delay4 #(32) delay_irq             (clk, io_irq            ,    irq            );
	delay4 #(32) delay_eoi             (clk,    eoi            , io_eoi            );

	picorv32_axi #(
		.TWO_CYCLE_ALU(1)
	) cpu (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.trap           (trap           ),
		.mem_axi_awvalid(mem_axi_awvalid),
		.mem_axi_awready(mem_axi_awready),
		.mem_axi_awaddr (mem_axi_awaddr ),
		.mem_axi_awprot (mem_axi_awprot ),
		.mem_axi_wvalid (mem_axi_wvalid ),
		.mem_axi_wready (mem_axi_wready ),
		.mem_axi_wdata  (mem_axi_wdata  ),
		.mem_axi_wstrb  (mem_axi_wstrb  ),
		.mem_axi_bvalid (mem_axi_bvalid ),
		.mem_axi_bready (mem_axi_bready ),
		.mem_axi_arvalid(mem_axi_arvalid),
		.mem_axi_arready(mem_axi_arready),
		.mem_axi_araddr (mem_axi_araddr ),
		.mem_axi_arprot (mem_axi_arprot ),
		.mem_axi_rvalid (mem_axi_rvalid ),
		.mem_axi_rready (mem_axi_rready ),
		.mem_axi_rdata  (mem_axi_rdata  ),
		.irq            (irq            ),
		.eoi            (eoi            )
	);
```

---
<!-- chunk_id=picorv32_scripts_quartus_tabtest_3 | module delay4 #( -->

# Verilog Block: `module delay4 #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/tabtest.v` | Lines 103–110

```verilog
module delay4 #(
	parameter WIDTH = 1
) (
	input clk,
	input [WIDTH-1:0] in,
	output reg [WIDTH-1:0] out
);
	reg [WIDTH-1:0] q1, q2, q3;
```

---
<!-- chunk_id=picorv32_scripts_quartus_tabtest_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/quartus/tabtest.v` | Lines 111–116

```verilog
always @(posedge clk) begin
		q1 <= in;
		q2 <= q1;
		q3 <= q2;
		out <= q3;
	end
```

---
<!-- chunk_id=picorv32_scripts_romload_Makefile_0 | picorv32_scripts_romload_Makefile -->

ifndef RISCV_TOOLS_PREFIX
RISCV_TOOLS_PREFIX = /opt/riscv32ic/bin/riscv32-unknown-elf-
endif
CXX = $(RISCV_TOOLS_PREFIX)g++ -march=rv32i
CC = $(RISCV_TOOLS_PREFIX)gcc -march=rv32i
AS = $(RISCV_TOOLS_PREFIX)gcc -march=rv32i
CXXFLAGS = -MD -Os -Wall -std=c++11
CCFLAGS = -MD -Os -Wall
#LDFLAGS = -Wl,--gc-sections,--no-relax
LDFLAGS = -Wl,--gc-sections
LDLIBS =

test: testbench.vvp firmware32.hex
	vvp -l testbench.log -N testbench.vvp

testbench.vvp: testbench.v ../../picorv32.v firmware_dbg.v
	iverilog -o testbench.vvp testbench.v ../../picorv32.v
	chmod -x testbench.vvp

firmware32.hex: firmware.elf hex8tohex32.py
	$(RISCV_TOOLS_PREFIX)objcopy -O verilog firmware.elf firmware.tmp
	python3 hex8tohex32.py firmware.tmp > firmware32.hex


firmware_dbg.v: firmware.map
	python3 map2debug.py

start.o: start.S
	$(CC) -c -nostdlib start.S $(LDLIBS)

firmware.elf: firmware.o syscalls.o start.o
	$(CC) $(LDFLAGS),-Map=firmware.map -o $@ $^ -T sections.ld $(LDLIBS)
	chmod -x firmware.elf

clean:
	rm -f *.o *.d *.tmp start.elf
	rm -f firmware.elf firmware.hex firmware32.hex
	rm -f testbench.vvp testbench.vcd

-include *.d
.PHONY: test clean

---
<!-- chunk_id=picorv32_scripts_romload_start_asm | Assembly Test: PICORV32_SCRIPTS_ROMLOAD_START -->

# Assembly Test: `PICORV32_SCRIPTS_ROMLOAD_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text
.global _start
.global _pvstart

_pvstart:
/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */

lui sp, %hi(4*1024*1024)
addi sp, sp, %lo(4*1024*1024)

/* push zeros on the stack for argc and argv */
/* (stack is aligned to 16 bytes in riscv calling convention) */
addi sp,sp,-16
sw zero,0(sp)
sw zero,4(sp)
sw zero,8(sp)
sw zero,12(sp)

j _start
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 1–7

```verilog
`timescale 1 ns / 1 ps
`undef VERBOSE_MEM
//`undef WRITE_VCD
`undef MEM8BIT

// define the size of our ROM
// simulates ROM by suppressing writes below this address
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_1 | `define ROM_SIZE 32'h0001_00FF -->

# Verilog Block: ``define ROM_SIZE 32'h0001_00FF`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 8–9

```verilog
`define ROM_SIZE 32'h0001_00FF
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_2 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 10–16

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_3 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 17–50

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg  [31:0] mem_rdata;

`include "firmware_dbg.v"

	picorv32 #(
		.COMPRESSED_ISA(1),
		.PROGADDR_RESET(32'h100)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	localparam MEM_SIZE = 4*1024*1024;
`ifdef MEM8BIT
	reg [7:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_4 | initial -->

# Verilog Block: `initial`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 51–59

```verilog
initial 
		$readmemh("firmware.hex", memory);
	end
`else
	reg [31:0] memory [0:MEM_SIZE/4-1];
	integer x;

	// simulate hardware assist of clearing RAM and copying ROM data into
	// memory
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_5 | initial -->

# Verilog Block: `initial`

> **Block Comment:** load rom contents

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 60–71

```verilog
initial
	begin
		// clear memory
		for (x=0; x<MEM_SIZE/4; x=x+1) memory[x] = 0;
		// load rom contents
		$readmemh("firmware32.hex", memory);
		// copy .data section
		for (x=0; x<(`C_SYM__BSS_START - `C_SYM___GLOBAL_POINTER); x=x+4)
			memory[(`C_SYM___GLOBAL_POINTER+x)/4] = memory[(`C_SYM__DATA_LMA+x)/4];
	end
`endif
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_6 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 72–126

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		if (mem_valid && !mem_ready) begin
			mem_ready <= 1;
			mem_rdata <= 'bx;
			case (1)
				mem_addr < MEM_SIZE: begin
`ifdef MEM8BIT
					if (|mem_wstrb) begin
						if (mem_wstrb[0]) memory[mem_addr + 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr + 1] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr + 2] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr + 3] <= mem_wdata[31:24];
					end else begin
						mem_rdata <= {memory[mem_addr+3], memory[mem_addr+2], memory[mem_addr+1], memory[mem_addr]};
					end
`else
					if ((|mem_wstrb) && (mem_addr >= `ROM_SIZE)) begin
						if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					end else begin
						mem_rdata <= memory[mem_addr >> 2];
					end
`endif
				end
				mem_addr == 32'h 1000_0000: begin
					$write("%c", mem_wdata[7:0]);
				end
			endcase
		end
		if (mem_valid && mem_ready) begin
`ifdef FIRMWARE_DEBUG_ADDR
			firmware_dbg(mem_addr);
`endif
			if ((mem_wstrb == 4'h0) && (mem_rdata === 32'bx)) $display("READ FROM UNITIALIZED ADDR=%x", mem_addr);
`ifdef VERBOSE_MEM
			if (|mem_wstrb)
				$display("WR: ADDR=%x DATA=%x MASK=%b", mem_addr, mem_wdata, mem_wstrb);
			else
				$display("RD: ADDR=%x DATA=%x%s", mem_addr, mem_rdata, mem_instr ? " INSN" : "");
`endif
			if (^mem_addr === 1'bx ||
					(mem_wstrb[0] && ^mem_wdata[ 7: 0] == 1'bx) ||
					(mem_wstrb[1] && ^mem_wdata[15: 8] == 1'bx) ||
					(mem_wstrb[2] && ^mem_wdata[23:16] == 1'bx) ||
					(mem_wstrb[3] && ^mem_wdata[31:24] == 1'bx)) begin
				$display("CRITICAL UNDEF MEM TRANSACTION");
				$finish;
			end
		end
	end

`ifdef WRITE_VCD
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_7 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 127–132

```verilog
initial begin
		$dumpfile("testbench.vcd");
		$dumpvars(0, testbench);
	end
`endif
```

---
<!-- chunk_id=picorv32_scripts_romload_testbench_8 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/romload/testbench.v` | Lines 133–139

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			repeat (10) @(posedge clk);
			$display("TRAP");
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck_0 | yosys-smtbmc -t 50 -i -s boolector --dump-vcd output.vcd --dump-smtc output.smtc axicheck.smt2 -->

# yosys-smtbmc -t 50 -i -s boolector --dump-vcd output.vcd --dump-smtc output.smtc axicheck.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck_0 | module testbench ( -->

# Verilog Block: `module testbench (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck.v` | Lines 1–28

```verilog
module testbench (
	input         clk,
	output        trap,

	output        mem_axi_awvalid,
	input         mem_axi_awready,
	output [31:0] mem_axi_awaddr,
	output [ 2:0] mem_axi_awprot,

	output        mem_axi_wvalid,
	input         mem_axi_wready,
	output [31:0] mem_axi_wdata,
	output [ 3:0] mem_axi_wstrb,

	input         mem_axi_bvalid,
	output        mem_axi_bready,

	output        mem_axi_arvalid,
	input         mem_axi_arready,
	output [31:0] mem_axi_araddr,
	output [ 2:0] mem_axi_arprot,

	input         mem_axi_rvalid,
	output        mem_axi_rready,
	input  [31:0] mem_axi_rdata
);
	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck_1 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck.v` | Lines 29–76

```verilog
always @(posedge clk)
		resetn <= 1;

	picorv32_axi #(
		.ENABLE_COUNTERS(1),
		.ENABLE_COUNTERS64(1),
		.ENABLE_REGS_16_31(1),
		.ENABLE_REGS_DUALPORT(1),
		.BARREL_SHIFTER(1),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.CATCH_MISALIGN(1),
		.CATCH_ILLINSN(1)
	) uut (
		.clk             (clk            ),
		.resetn          (resetn         ),
		.trap            (trap           ),
		.mem_axi_awvalid (mem_axi_awvalid),
		.mem_axi_awready (mem_axi_awready),
		.mem_axi_awaddr  (mem_axi_awaddr ),
		.mem_axi_awprot  (mem_axi_awprot ),
		.mem_axi_wvalid  (mem_axi_wvalid ),
		.mem_axi_wready  (mem_axi_wready ),
		.mem_axi_wdata   (mem_axi_wdata  ),
		.mem_axi_wstrb   (mem_axi_wstrb  ),
		.mem_axi_bvalid  (mem_axi_bvalid ),
		.mem_axi_bready  (mem_axi_bready ),
		.mem_axi_arvalid (mem_axi_arvalid),
		.mem_axi_arready (mem_axi_arready),
		.mem_axi_araddr  (mem_axi_araddr ),
		.mem_axi_arprot  (mem_axi_arprot ),
		.mem_axi_rvalid  (mem_axi_rvalid ),
		.mem_axi_rready  (mem_axi_rready ),
		.mem_axi_rdata   (mem_axi_rdata  )
	);

	reg expect_bvalid_aw = 0;
	reg expect_bvalid_w  = 0;
	reg expect_rvalid    = 0;

	reg [3:0] timeout_aw = 0;
	reg [3:0] timeout_w  = 0;
	reg [3:0] timeout_b  = 0;
	reg [3:0] timeout_ar = 0;
	reg [3:0] timeout_r  = 0;
	reg [3:0] timeout_ex = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck.v` | Lines 77–93

```verilog
always @(posedge clk) begin
		timeout_aw <= !mem_axi_awvalid || mem_axi_awready ? 0 : timeout_aw + 1;
		timeout_w  <= !mem_axi_wvalid  || mem_axi_wready  ? 0 : timeout_w  + 1;
		timeout_b  <= !mem_axi_bvalid  || mem_axi_bready  ? 0 : timeout_b  + 1;
		timeout_ar <= !mem_axi_arvalid || mem_axi_arready ? 0 : timeout_ar + 1;
		timeout_r  <= !mem_axi_rvalid  || mem_axi_rready  ? 0 : timeout_r  + 1;
		timeout_ex <= !{expect_bvalid_aw, expect_bvalid_w, expect_rvalid} ? 0 : timeout_ex + 1;
		restrict(timeout_aw != 15);
		restrict(timeout_w  != 15);
		restrict(timeout_b  != 15);
		restrict(timeout_ar != 15);
		restrict(timeout_r  != 15);
		restrict(timeout_ex != 15);
		restrict(!trap);

	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck.v` | Lines 94–209

```verilog
always @(posedge clk) begin
		if (resetn) begin
			if (!$past(resetn)) begin
				assert(!mem_axi_awvalid);
				assert(!mem_axi_wvalid );
				assume(!mem_axi_bvalid );
				assert(!mem_axi_arvalid);
				assume(!mem_axi_rvalid );
			end else begin
				// Only one read/write transaction in flight at each point in time

				if (expect_bvalid_aw) begin
					assert(!mem_axi_awvalid);
				end

				if (expect_bvalid_w) begin
					assert(!mem_axi_wvalid);
				end

				if (expect_rvalid) begin
					assert(!mem_axi_arvalid);
				end

				expect_bvalid_aw = expect_bvalid_aw || (mem_axi_awvalid && mem_axi_awready);
				expect_bvalid_w  = expect_bvalid_w  || (mem_axi_wvalid  && mem_axi_wready );
				expect_rvalid    = expect_rvalid    || (mem_axi_arvalid && mem_axi_arready);

				if (expect_bvalid_aw || expect_bvalid_w) begin
					assert(!expect_rvalid);
				end

				if (expect_rvalid) begin
					assert(!expect_bvalid_aw);
					assert(!expect_bvalid_w);
				end

				if (!expect_bvalid_aw || !expect_bvalid_w) begin
					assume(!mem_axi_bvalid);
				end

				if (!expect_rvalid) begin
					assume(!mem_axi_rvalid);
				end

				if (mem_axi_bvalid && mem_axi_bready) begin
					expect_bvalid_aw = 0;
					expect_bvalid_w = 0;
				end

				if (mem_axi_rvalid && mem_axi_rready) begin
					expect_rvalid = 0;
				end

				// Check AXI Master Streams

				if ($past(mem_axi_awvalid && !mem_axi_awready)) begin
					assert(mem_axi_awvalid);
					assert($stable(mem_axi_awaddr));
					assert($stable(mem_axi_awprot));
				end
				if ($fell(mem_axi_awvalid)) begin
					assert($past(mem_axi_awready));
				end
				if ($fell(mem_axi_awready)) begin
					assume($past(mem_axi_awvalid));
				end

				if ($past(mem_axi_arvalid && !mem_axi_arready)) begin
					assert(mem_axi_arvalid);
					assert($stable(mem_axi_araddr));
					assert($stable(mem_axi_arprot));
				end
				if ($fell(mem_axi_arvalid)) begin
					assert($past(mem_axi_arready));
				end
				if ($fell(mem_axi_arready)) begin
					assume($past(mem_axi_arvalid));
				end

				if ($past(mem_axi_wvalid && !mem_axi_wready)) begin
					assert(mem_axi_wvalid);
					assert($stable(mem_axi_wdata));
					assert($stable(mem_axi_wstrb));
				end
				if ($fell(mem_axi_wvalid)) begin
					assert($past(mem_axi_wready));
				end
				if ($fell(mem_axi_wready)) begin
					assume($past(mem_axi_wvalid));
				end

				// Check AXI Slave Streams

				if ($past(mem_axi_bvalid && !mem_axi_bready)) begin
					assume(mem_axi_bvalid);
				end
				if ($fell(mem_axi_bvalid)) begin
					assume($past(mem_axi_bready));
				end
				if ($fell(mem_axi_bready)) begin
					assert($past(mem_axi_bvalid));
				end

				if ($past(mem_axi_rvalid && !mem_axi_rready)) begin
					assume(mem_axi_rvalid);
					assume($stable(mem_axi_rdata));
				end
				if ($fell(mem_axi_rvalid)) begin
					assume($past(mem_axi_rready));
				end
				if ($fell(mem_axi_rready)) begin
					assert($past(mem_axi_rvalid));
				end
			end
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck2_0 | picorv32_scripts_smtbmc_axicheck2 -->

#!/bin/bash

set -ex

yosys -ql axicheck2.yslog \
	-p 'read_verilog -formal -norestrict -assume-asserts ../../picorv32.v' \
	-p 'read_verilog -formal axicheck2.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires axicheck2.smt2'

yosys-smtbmc -t 6 -s yices --dump-vcd output.vcd --dump-smtc output.smtc --smtc axicheck2.smtc axicheck2.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck2_0 | picorv32_scripts_smtbmc_axicheck2 -->

initial
assume (= [uut_0] [uut_1])

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck2_0 | module testbench ( -->

# Verilog Block: `module testbench (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck2.v` | Lines 1–113

```verilog
module testbench (
	input         clk,
	input         resetn,
	output        trap_0,
	output        trap_1,

	output        mem_axi_awvalid_0,
	input         mem_axi_awready_0,
	output [31:0] mem_axi_awaddr_0,
	output [ 2:0] mem_axi_awprot_0,

	output        mem_axi_awvalid_1,
	input         mem_axi_awready_1,
	output [31:0] mem_axi_awaddr_1,
	output [ 2:0] mem_axi_awprot_1,

	output        mem_axi_wvalid_0,
	input         mem_axi_wready_0,
	output [31:0] mem_axi_wdata_0,
	output [ 3:0] mem_axi_wstrb_0,

	output        mem_axi_wvalid_1,
	input         mem_axi_wready_1,
	output [31:0] mem_axi_wdata_1,
	output [ 3:0] mem_axi_wstrb_1,

	input         mem_axi_bvalid,
	output        mem_axi_bready_0,
	output        mem_axi_bready_1,

	output        mem_axi_arvalid_0,
	input         mem_axi_arready_0,
	output [31:0] mem_axi_araddr_0,
	output [ 2:0] mem_axi_arprot_0,

	output        mem_axi_arvalid_1,
	input         mem_axi_arready_1,
	output [31:0] mem_axi_araddr_1,
	output [ 2:0] mem_axi_arprot_1,

	input         mem_axi_rvalid,
	output        mem_axi_rready_0,
	output        mem_axi_rready_1,
	input  [31:0] mem_axi_rdata
);
	picorv32_axi #(
		.ENABLE_COUNTERS(1),
		.ENABLE_COUNTERS64(1),
		.ENABLE_REGS_16_31(1),
		.ENABLE_REGS_DUALPORT(1),
		.BARREL_SHIFTER(1),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.CATCH_MISALIGN(1),
		.CATCH_ILLINSN(1)
	) uut_0 (
		.clk             (clk              ),
		.resetn          (resetn           ),
		.trap            (trap_0           ),
		.mem_axi_awvalid (mem_axi_awvalid_0),
		.mem_axi_awready (mem_axi_awready_0),
		.mem_axi_awaddr  (mem_axi_awaddr_0 ),
		.mem_axi_awprot  (mem_axi_awprot_0 ),
		.mem_axi_wvalid  (mem_axi_wvalid_0 ),
		.mem_axi_wready  (mem_axi_wready_0 ),
		.mem_axi_wdata   (mem_axi_wdata_0  ),
		.mem_axi_wstrb   (mem_axi_wstrb_0  ),
		.mem_axi_bvalid  (mem_axi_bvalid   ),
		.mem_axi_bready  (mem_axi_bready_0 ),
		.mem_axi_arvalid (mem_axi_arvalid_0),
		.mem_axi_arready (mem_axi_arready_0),
		.mem_axi_araddr  (mem_axi_araddr_0 ),
		.mem_axi_arprot  (mem_axi_arprot_0 ),
		.mem_axi_rvalid  (mem_axi_rvalid   ),
		.mem_axi_rready  (mem_axi_rready_0 ),
		.mem_axi_rdata   (mem_axi_rdata    )
	);

	picorv32_axi #(
		.ENABLE_COUNTERS(1),
		.ENABLE_COUNTERS64(1),
		.ENABLE_REGS_16_31(1),
		.ENABLE_REGS_DUALPORT(1),
		.BARREL_SHIFTER(1),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.CATCH_MISALIGN(1),
		.CATCH_ILLINSN(1)
	) uut_1 (
		.clk             (clk              ),
		.resetn          (resetn           ),
		.trap            (trap_1           ),
		.mem_axi_awvalid (mem_axi_awvalid_1),
		.mem_axi_awready (mem_axi_awready_1),
		.mem_axi_awaddr  (mem_axi_awaddr_1 ),
		.mem_axi_awprot  (mem_axi_awprot_1 ),
		.mem_axi_wvalid  (mem_axi_wvalid_1 ),
		.mem_axi_wready  (mem_axi_wready_1 ),
		.mem_axi_wdata   (mem_axi_wdata_1  ),
		.mem_axi_wstrb   (mem_axi_wstrb_1  ),
		.mem_axi_bvalid  (mem_axi_bvalid   ),
		.mem_axi_bready  (mem_axi_bready_1 ),
		.mem_axi_arvalid (mem_axi_arvalid_1),
		.mem_axi_arready (mem_axi_arready_1),
		.mem_axi_araddr  (mem_axi_araddr_1 ),
		.mem_axi_arprot  (mem_axi_arprot_1 ),
		.mem_axi_rvalid  (mem_axi_rvalid   ),
		.mem_axi_rready  (mem_axi_rready_1 ),
		.mem_axi_rdata   (mem_axi_rdata    )
	);
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_axicheck2_1 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/axicheck2.v` | Lines 114–146

```verilog
always @(posedge clk) begin
		if (resetn && $past(resetn)) begin
			assert(trap_0            == trap_1           );
			assert(mem_axi_awvalid_0 == mem_axi_awvalid_1);
			assert(mem_axi_awaddr_0  == mem_axi_awaddr_1 );
			assert(mem_axi_awprot_0  == mem_axi_awprot_1 );
			assert(mem_axi_wvalid_0  == mem_axi_wvalid_1 );
			assert(mem_axi_wdata_0   == mem_axi_wdata_1  );
			assert(mem_axi_wstrb_0   == mem_axi_wstrb_1  );
			assert(mem_axi_bready_0  == mem_axi_bready_1 );
			assert(mem_axi_arvalid_0 == mem_axi_arvalid_1);
			assert(mem_axi_araddr_0  == mem_axi_araddr_1 );
			assert(mem_axi_arprot_0  == mem_axi_arprot_1 );
			assert(mem_axi_rready_0  == mem_axi_rready_1 );

			if (mem_axi_awvalid_0) assume(mem_axi_awready_0 == mem_axi_awready_1);
			if (mem_axi_wvalid_0 ) assume(mem_axi_wready_0  == mem_axi_wready_1 );
			if (mem_axi_arvalid_0) assume(mem_axi_arready_0 == mem_axi_arready_1);

			if ($fell(mem_axi_awready_0)) assume($past(mem_axi_awvalid_0));
			if ($fell(mem_axi_wready_0 )) assume($past(mem_axi_wvalid_0 ));
			if ($fell(mem_axi_arready_0)) assume($past(mem_axi_arvalid_0));

			if ($fell(mem_axi_awready_1)) assume($past(mem_axi_awvalid_1));
			if ($fell(mem_axi_wready_1 )) assume($past(mem_axi_wvalid_1 ));
			if ($fell(mem_axi_arready_1)) assume($past(mem_axi_arvalid_1));

			if ($fell(mem_axi_bvalid)) assume($past(mem_axi_bready_0));
			if ($fell(mem_axi_rvalid)) assume($past(mem_axi_rready_0));

			if (mem_axi_rvalid && $past(mem_axi_rvalid)) assume($stable(mem_axi_rdata));
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_mulcmp_0 | picorv32_scripts_smtbmc_mulcmp -->

#!/bin/bash

set -ex

yosys -ql mulcmp.yslog \
        -p 'read_verilog -formal -norestrict -assume-asserts ../../picorv32.v' \
        -p 'read_verilog -formal mulcmp.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires mulcmp.smt2'

yosys-smtbmc -s yices -t 100 --dump-vcd output.vcd --dump-smtc output.smtc mulcmp.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_mulcmp_0 | module testbench(input clk, mem_ready_0, mem_ready_1); -->

# Verilog Block: `module testbench(input clk, mem_ready_0, mem_ready_1);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/mulcmp.v` | Lines 1–4

```verilog
module testbench(input clk, mem_ready_0, mem_ready_1);

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_mulcmp_1 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/mulcmp.v` | Lines 5–56

```verilog
always @(posedge clk)
		resetn <= 1;

	reg          pcpi_valid_0 = 1;
	reg          pcpi_valid_1 = 1;

	wire [31:0] pcpi_insn = $anyconst;
	wire [31:0] pcpi_rs1 = $anyconst;
	wire [31:0] pcpi_rs2 = $anyconst;

	wire        pcpi_wr_0;
	wire [31:0] pcpi_rd_0;
	wire        pcpi_wait_0;
	wire        pcpi_ready_0;

	wire        pcpi_wr_1;
	wire [31:0] pcpi_rd_1;
	wire        pcpi_wait_1;
	wire        pcpi_ready_1;

	reg         pcpi_wr_ref;
	reg  [31:0] pcpi_rd_ref;
	reg         pcpi_ready_ref = 0;

	picorv32_pcpi_mul mul_0 (
		.clk       (clk         ),
		.resetn    (resetn      ),
		.pcpi_valid(pcpi_valid_0),
		.pcpi_insn (pcpi_insn   ),
		.pcpi_rs1  (pcpi_rs1    ),
		.pcpi_rs2  (pcpi_rs2    ),
		.pcpi_wr   (pcpi_wr_0   ),
		.pcpi_rd   (pcpi_rd_0   ),
		.pcpi_wait (pcpi_wait_0 ),
		.pcpi_ready(pcpi_ready_0),

	);

	picorv32_pcpi_fast_mul mul_1 (
		.clk       (clk         ),
		.resetn    (resetn      ),
		.pcpi_valid(pcpi_valid_1),
		.pcpi_insn (pcpi_insn   ),
		.pcpi_rs1  (pcpi_rs1    ),
		.pcpi_rs2  (pcpi_rs2    ),
		.pcpi_wr   (pcpi_wr_1   ),
		.pcpi_rd   (pcpi_rd_1   ),
		.pcpi_wait (pcpi_wait_1 ),
		.pcpi_ready(pcpi_ready_1),

	);
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_mulcmp_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/mulcmp.v` | Lines 57–86

```verilog
always @(posedge clk) begin
		if (resetn) begin
			if (pcpi_ready_0 && pcpi_ready_1) begin
				assert(pcpi_wr_0 == pcpi_wr_1);
				assert(pcpi_rd_0 == pcpi_rd_1);
			end

			if (pcpi_ready_0) begin
				pcpi_valid_0 <= 0;
				pcpi_wr_ref <= pcpi_wr_0;
				pcpi_rd_ref <= pcpi_rd_0;
				pcpi_ready_ref <= 1;
				if (pcpi_ready_ref) begin
					assert(pcpi_wr_0 == pcpi_wr_ref);
					assert(pcpi_rd_0 == pcpi_rd_ref);
				end
			end

			if (pcpi_ready_1) begin
				pcpi_valid_1 <= 0;
				pcpi_wr_ref <= pcpi_wr_1;
				pcpi_rd_ref <= pcpi_rd_1;
				pcpi_ready_ref <= 1;
				if (pcpi_ready_ref) begin
					assert(pcpi_wr_1 == pcpi_wr_ref);
					assert(pcpi_rd_1 == pcpi_rd_ref);
				end
			end
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_notrap_validop_0 | picorv32_scripts_smtbmc_notrap_validop -->

#!/bin/bash

set -ex

yosys -ql notrap_validop.yslog \
        -p 'read_verilog -formal -norestrict -assume-asserts ../../picorv32.v' \
        -p 'read_verilog -formal notrap_validop.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires notrap_validop.smt2'

yosys-smtbmc -s yices -t 30 --dump-vcd output.vcd --dump-smtc output.smtc notrap_validop.smt2
yosys-smtbmc -s yices -i -t 30 --dump-vcd output.vcd --dump-smtc output.smtc notrap_validop.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_notrap_validop_0 | module testbench(input clk, mem_ready); -->

# Verilog Block: `module testbench(input clk, mem_ready);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/notrap_validop.v` | Lines 1–4

```verilog
module testbench(input clk, mem_ready);
	`include "opcode.v"

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_notrap_validop_1 | always @(posedge clk) resetn <= 1; -->

# Verilog Block: `always @(posedge clk) resetn <= 1;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/notrap_validop.v` | Lines 5–15

```verilog
always @(posedge clk) resetn <= 1;

	(* keep *) wire trap, mem_valid, mem_instr;
	(* keep *) wire [3:0] mem_wstrb;
	(* keep *) wire [31:0] mem_addr, mem_wdata, mem_rdata;
	(* keep *) wire [35:0] trace_data;

	reg [31:0] mem [0:2**30-1];

	assign mem_rdata = mem[mem_addr >> 2];
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_notrap_validop_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/notrap_validop.v` | Lines 16–26

```verilog
always @(posedge clk) begin
		if (resetn && mem_valid && mem_ready) begin
			if (mem_wstrb[3]) mem[mem_addr >> 2][31:24] <= mem_wdata[31:24];
			if (mem_wstrb[2]) mem[mem_addr >> 2][23:16] <= mem_wdata[23:16];
			if (mem_wstrb[1]) mem[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
			if (mem_wstrb[0]) mem[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
		end
	end

	reg [1:0] mem_ready_stall = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_notrap_validop_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/notrap_validop.v` | Lines 27–66

```verilog
always @(posedge clk) begin
		mem_ready_stall <= {mem_ready_stall, mem_valid && !mem_ready};
		restrict(&mem_ready_stall == 0);

		if (mem_instr && mem_ready && mem_valid) begin
			assume(opcode_valid(mem_rdata));
			assume(!opcode_branch(mem_rdata));
			assume(!opcode_load(mem_rdata));
			assume(!opcode_store(mem_rdata));
		end

		if (!mem_valid)
			assume(!mem_ready);

		if (resetn)
			assert(!trap);
	end

	picorv32 #(
		// change this settings as you like
		.ENABLE_REGS_DUALPORT(1),
		.TWO_STAGE_SHIFT(1),
		.BARREL_SHIFTER(0),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0)
	) cpu (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_0 | function opcode_jump; -->

# Verilog Block: `function opcode_jump;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 1–9

```verilog
function opcode_jump;
	input [31:0] opcode;
	begin
		opcode_jump = 0;
		if (opcode[6:0] == 7'b1101111) opcode_jump = 1; // JAL
		if (opcode[14:12] == 3'b000 && opcode[6:0] == 7'b1100111) opcode_jump = 1; // JALR
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_1 | function opcode_branch; -->

# Verilog Block: `function opcode_branch;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 10–22

```verilog
function opcode_branch;
	input [31:0] opcode;
	begin
		opcode_branch = 0;
		if (opcode[14:12] == 3'b000 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BEQ
		if (opcode[14:12] == 3'b001 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BNE
		if (opcode[14:12] == 3'b100 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BLT
		if (opcode[14:12] == 3'b101 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BGE
		if (opcode[14:12] == 3'b110 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BLTU
		if (opcode[14:12] == 3'b111 && opcode[6:0] == 7'b1100011) opcode_branch = 1; // BGEU
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_2 | function opcode_load; -->

# Verilog Block: `function opcode_load;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 23–34

```verilog
function opcode_load;
	input [31:0] opcode;
	begin
		opcode_load = 0;
		if (opcode[14:12] == 3'b000 && opcode[6:0] == 7'b0000011) opcode_load = 1; // LB
		if (opcode[14:12] == 3'b001 && opcode[6:0] == 7'b0000011) opcode_load = 1; // LH
		if (opcode[14:12] == 3'b010 && opcode[6:0] == 7'b0000011) opcode_load = 1; // LW
		if (opcode[14:12] == 3'b100 && opcode[6:0] == 7'b0000011) opcode_load = 1; // LBU
		if (opcode[14:12] == 3'b101 && opcode[6:0] == 7'b0000011) opcode_load = 1; // LHU
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_3 | function opcode_store; -->

# Verilog Block: `function opcode_store;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 35–44

```verilog
function opcode_store;
	input [31:0] opcode;
	begin
		opcode_store = 0;
		if (opcode[14:12] == 3'b000 && opcode[6:0] == 7'b0100011) opcode_store = 1; // SB
		if (opcode[14:12] == 3'b001 && opcode[6:0] == 7'b0100011) opcode_store = 1; // SH
		if (opcode[14:12] == 3'b010 && opcode[6:0] == 7'b0100011) opcode_store = 1; // SW
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_4 | function opcode_alui; -->

# Verilog Block: `function opcode_alui;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 45–60

```verilog
function opcode_alui;
	input [31:0] opcode;
	begin
		opcode_alui = 0;
		if (opcode[14:12] == 3'b000 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // ADDI
		if (opcode[14:12] == 3'b010 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // SLTI
		if (opcode[14:12] == 3'b011 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // SLTIU
		if (opcode[14:12] == 3'b100 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // XORI
		if (opcode[14:12] == 3'b110 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // ORI
		if (opcode[14:12] == 3'b111 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // ANDI
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b001 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // SLLI
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b101 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // SRLI
		if (opcode[31:25] == 7'b0100000 && opcode[14:12] == 3'b101 && opcode[6:0] == 7'b0010011) opcode_alui = 1; // SRAI
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_5 | function opcode_alu; -->

# Verilog Block: `function opcode_alu;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 61–77

```verilog
function opcode_alu;
	input [31:0] opcode;
	begin
		opcode_alu = 0;
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b000 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // ADD
		if (opcode[31:25] == 7'b0100000 && opcode[14:12] == 3'b000 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SUB
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b001 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SLL
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b010 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SLT
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b011 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SLTU
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b100 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // XOR
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b101 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SRL
		if (opcode[31:25] == 7'b0100000 && opcode[14:12] == 3'b101 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // SRA
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b110 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // OR
		if (opcode[31:25] == 7'b0000000 && opcode[14:12] == 3'b111 && opcode[6:0] == 7'b0110011) opcode_alu = 1; // AND
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_6 | function opcode_sys; -->

# Verilog Block: `function opcode_sys;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 78–91

```verilog
function opcode_sys;
	input [31:0] opcode;
	begin
		opcode_sys = 0;
		if (opcode[31:20] == 12'hC00 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDCYCLE
		if (opcode[31:20] == 12'hC01 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDTIME
		if (opcode[31:20] == 12'hC02 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDINSTRET
		if (opcode[31:20] == 12'hC80 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDCYCLEH
		if (opcode[31:20] == 12'hC81 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDTIMEH
		if (opcode[31:20] == 12'hC82 && opcode[19:12] == 3'b010 && opcode[6:0] == 7'b1110011) opcode_sys = 1; // RDINSTRETH
	end

endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_opcode_7 | function opcode_valid; -->

# Verilog Block: `function opcode_valid;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/opcode.v` | Lines 92–104

```verilog
function opcode_valid;
	input [31:0] opcode;
	begin
		opcode_valid = 0;
		if (opcode_jump  (opcode)) opcode_valid = 1;
		if (opcode_branch(opcode)) opcode_valid = 1;
		if (opcode_load  (opcode)) opcode_valid = 1;
		if (opcode_store (opcode)) opcode_valid = 1;
		if (opcode_alui  (opcode)) opcode_valid = 1;
		if (opcode_alu   (opcode)) opcode_valid = 1;
		if (opcode_sys   (opcode)) opcode_valid = 1;
	end
endfunction
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_0 | picorv32_scripts_smtbmc_tracecmp -->

[*]
[*] GTKWave Analyzer v3.3.65 (w)1999-2015 BSI
[*] Fri Aug 26 15:42:37 2016
[*]
[dumpfile] "/home/clifford/Work/picorv32/scripts/smtbmc/output.vcd"
[dumpfile_mtime] "Fri Aug 26 15:33:18 2016"
[dumpfile_size] 80106
[savefile] "/home/clifford/Work/picorv32/scripts/smtbmc/tracecmp.gtkw"
[timestart] 0
[size] 1216 863
[pos] -1 -1
*-2.860312 10 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1 -1
[treeopen] testbench.
[sst_width] 241
[signals_width] 337
[sst_expanded] 1
[sst_vpaned_height] 252
@28
smt_clock
testbench.resetn
testbench.trap_0
testbench.trap_1
@200
-
-Trace CMP
@28
testbench.trace_valid_0
testbench.trace_valid_1
@22
testbench.trace_data_0[35:0]
testbench.trace_data_1[35:0]
@420
testbench.trace_balance[7:0]
@200
-
-CPU #0
@28
testbench.mem_valid_0
testbench.mem_ready_0
testbench.mem_instr_0
@22
testbench.mem_addr_0[31:0]
testbench.mem_rdata_0[31:0]
testbench.mem_wdata_0[31:0]
@28
testbench.mem_wstrb_0[3:0]
@22
testbench.cpu_0.cpu_state[7:0]
@28
testbench.cpu_0.mem_state[1:0]
@200
-
-CPU #1
@28
testbench.mem_valid_1
testbench.mem_ready_1
testbench.mem_instr_1
@22
testbench.mem_addr_1[31:0]
testbench.mem_rdata_1[31:0]
testbench.mem_wdata_1[31:0]
@28
testbench.mem_wstrb_1[3:0]
@22
testbench.cpu_1.cpu_state[7:0]
@28
testbench.cpu_1.mem_state[1:0]
@200
-
[pattern_trace] 1
[pattern_trace] 0

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_0 | picorv32_scripts_smtbmc_tracecmp -->

#!/bin/bash

set -ex

yosys -ql tracecmp.yslog \
        -p 'read_verilog -formal -norestrict -assume-asserts ../../picorv32.v' \
        -p 'read_verilog -formal tracecmp.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires tracecmp.smt2'

yosys-smtbmc -s yices --smtc tracecmp.smtc --dump-vcd output.vcd --dump-smtc output.smtc tracecmp.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_0 | assume (= [mem_ready_0] [mem_ready_1]) -->

# assume (= [mem_ready_0] [mem_ready_1])

always -1
assert (=> (= [trace_balance] #x00) (= [trace_data_0] [trace_data_1]))

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_0 | module testbench(input clk, mem_ready_0, mem_ready_1); -->

# Verilog Block: `module testbench(input clk, mem_ready_0, mem_ready_1);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp.v` | Lines 1–5

```verilog
module testbench(input clk, mem_ready_0, mem_ready_1);
	// set this to 1 to test generation of counter examples
	localparam ENABLE_COUNTERS = 0;

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_1 | always @(posedge clk) resetn <= 1; -->

# Verilog Block: `always @(posedge clk) resetn <= 1;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp.v` | Lines 6–23

```verilog
always @(posedge clk) resetn <= 1;

	(* keep *) wire trap_0, trace_valid_0, mem_valid_0, mem_instr_0;
	(* keep *) wire [3:0] mem_wstrb_0;
	(* keep *) wire [31:0] mem_addr_0, mem_wdata_0, mem_rdata_0;
	(* keep *) wire [35:0] trace_data_0;

	(* keep *) wire trap_1, trace_valid_1, mem_valid_1, mem_instr_1;
	(* keep *) wire [3:0] mem_wstrb_1;
	(* keep *) wire [31:0] mem_addr_1, mem_wdata_1, mem_rdata_1;
	(* keep *) wire [35:0] trace_data_1;

	reg [31:0] mem_0 [0:2**30-1];
	reg [31:0] mem_1 [0:2**30-1];

	assign mem_rdata_0 = mem_0[mem_addr_0 >> 2];
	assign mem_rdata_1 = mem_1[mem_addr_1 >> 2];
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_2 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp.v` | Lines 24–41

```verilog
always @(posedge clk) begin
		if (resetn && mem_valid_0 && mem_ready_0) begin
			if (mem_wstrb_0[3]) mem_0[mem_addr_0 >> 2][31:24] <= mem_wdata_0[31:24];
			if (mem_wstrb_0[2]) mem_0[mem_addr_0 >> 2][23:16] <= mem_wdata_0[23:16];
			if (mem_wstrb_0[1]) mem_0[mem_addr_0 >> 2][15: 8] <= mem_wdata_0[15: 8];
			if (mem_wstrb_0[0]) mem_0[mem_addr_0 >> 2][ 7: 0] <= mem_wdata_0[ 7: 0];
		end
		if (resetn && mem_valid_1 && mem_ready_1) begin
			if (mem_wstrb_1[3]) mem_1[mem_addr_1 >> 2][31:24] <= mem_wdata_1[31:24];
			if (mem_wstrb_1[2]) mem_1[mem_addr_1 >> 2][23:16] <= mem_wdata_1[23:16];
			if (mem_wstrb_1[1]) mem_1[mem_addr_1 >> 2][15: 8] <= mem_wdata_1[15: 8];
			if (mem_wstrb_1[0]) mem_1[mem_addr_1 >> 2][ 7: 0] <= mem_wdata_1[ 7: 0];
		end
	end

	(* keep *) reg [7:0] trace_balance;
	reg [7:0] trace_balance_q;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_3 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp.v` | Lines 42–47

```verilog
always @* begin
		trace_balance = trace_balance_q;
		if (trace_valid_0) trace_balance = trace_balance + 1;
		if (trace_valid_1) trace_balance = trace_balance - 1;
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp.v` | Lines 48–108

```verilog
always @(posedge clk) begin
		trace_balance_q <= resetn ? trace_balance : 0;
	end

	picorv32 #(
		// do not change this settings
		.ENABLE_COUNTERS(ENABLE_COUNTERS),
		.ENABLE_TRACE(1),

		// change this settings as you like
		.ENABLE_REGS_DUALPORT(1),
		.TWO_STAGE_SHIFT(1),
		.BARREL_SHIFTER(0),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0)
	) cpu_0 (
		.clk         (clk          ),
		.resetn      (resetn       ),
		.trap        (trap_0       ),
		.mem_valid   (mem_valid_0  ),
		.mem_instr   (mem_instr_0  ),
		.mem_ready   (mem_ready_0  ),
		.mem_addr    (mem_addr_0   ),
		.mem_wdata   (mem_wdata_0  ),
		.mem_wstrb   (mem_wstrb_0  ),
		.mem_rdata   (mem_rdata_0  ),
		.trace_valid (trace_valid_0),
		.trace_data  (trace_data_0 )
	);

	picorv32 #(
		// do not change this settings
		.ENABLE_COUNTERS(ENABLE_COUNTERS),
		.ENABLE_TRACE(1),

		// change this settings as you like
		.ENABLE_REGS_DUALPORT(1),
		.TWO_STAGE_SHIFT(1),
		.BARREL_SHIFTER(0),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(0),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0)
	) cpu_1 (
		.clk         (clk          ),
		.resetn      (resetn       ),
		.trap        (trap_1       ),
		.mem_valid   (mem_valid_1  ),
		.mem_instr   (mem_instr_1  ),
		.mem_ready   (mem_ready_1  ),
		.mem_addr    (mem_addr_1   ),
		.mem_wdata   (mem_wdata_1  ),
		.mem_wstrb   (mem_wstrb_1  ),
		.mem_rdata   (mem_rdata_1  ),
		.trace_valid (trace_valid_1),
		.trace_data  (trace_data_1 )
	);
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_0 | picorv32_scripts_smtbmc_tracecmp2 -->

#!/bin/bash

set -ex

yosys -ql tracecmp2.yslog \
        -p 'read_verilog -formal -norestrict -assume-asserts ../../picorv32.v' \
        -p 'read_verilog -formal tracecmp2.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires tracecmp2.smt2'

yosys-smtbmc -s boolector --smtc tracecmp2.smtc --dump-vcd output.vcd --dump-smtc output.smtc tracecmp2.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_0 | picorv32_scripts_smtbmc_tracecmp2 -->

initial
assume (= [cpu_0.cpuregs] [cpu_1.cpuregs])

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_0 | module testbench( -->

# Verilog Block: `module testbench(`

> **Block Comment:** set this to 1 to test generation of counterexamples

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 1–8

```verilog
module testbench(
	input clk, mem_ready_0, mem_ready_1,
	input [31:0] mem_rdata
);
	// set this to 1 to test generation of counterexamples
	localparam ENABLE_COUNTERS = 0;

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_1 | always @(posedge clk) resetn <= 1; -->

# Verilog Block: `always @(posedge clk) resetn <= 1;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 9–33

```verilog
always @(posedge clk) resetn <= 1;

	(* keep *) wire trap_0, trace_valid_0, mem_valid_0, mem_instr_0;
	(* keep *) wire [3:0] mem_wstrb_0;
	(* keep *) wire [31:0] mem_addr_0, mem_wdata_0, mem_rdata_0;
	(* keep *) wire [35:0] trace_data_0;

	(* keep *) wire trap_1, trace_valid_1, mem_valid_1, mem_instr_1;
	(* keep *) wire [3:0] mem_wstrb_1;
	(* keep *) wire [31:0] mem_addr_1, mem_wdata_1, mem_rdata_1;
	(* keep *) wire [35:0] trace_data_1;

	reg [31:0] last_mem_rdata;

	assign mem_rdata_0 = mem_rdata;
	assign mem_rdata_1 = mem_rdata;

	wire mem_xfer_0 = resetn && mem_valid_0 && mem_ready_0;
	wire mem_xfer_1 = resetn && mem_valid_1 && mem_ready_1;

	reg [1:0] cmp_mem_state = 0;
	reg [31:0] cmp_mem_addr;
	reg [31:0] cmp_mem_wdata;
	reg [3:0] cmp_mem_wstrb;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_2 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 34–40

```verilog
always @* begin
		if (mem_valid_0 == 0)
			assume(!mem_ready_0 == 0);
		if (mem_valid_1 == 0)
			assume(mem_ready_1 == 0);
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 41–46

```verilog
always @(posedge clk) begin
		if (cmp_mem_state)
			assume(last_mem_rdata == mem_rdata);
		last_mem_rdata <= mem_rdata;
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 47–102

```verilog
always @(posedge clk) begin
		case (cmp_mem_state)
			2'b 00: begin
				case ({mem_xfer_1, mem_xfer_0})
					2'b 11: begin
						assert(mem_addr_0 == mem_addr_1);
						assert(mem_wstrb_0 == mem_wstrb_1);
						if (mem_wstrb_0[3]) assert(mem_wdata_0[31:24] == mem_wdata_1[31:24]);
						if (mem_wstrb_0[2]) assert(mem_wdata_0[23:16] == mem_wdata_1[23:16]);
						if (mem_wstrb_0[1]) assert(mem_wdata_0[15: 8] == mem_wdata_1[15: 8]);
						if (mem_wstrb_0[0]) assert(mem_wdata_0[ 7: 0] == mem_wdata_1[ 7: 0]);
					end
					2'b 01: begin
						cmp_mem_state <= 2'b 01;
						cmp_mem_addr <= mem_addr_0;
						cmp_mem_wdata <= mem_wdata_0;
						cmp_mem_wstrb <= mem_wstrb_0;
					end
					2'b 10: begin
						cmp_mem_state <= 2'b 10;
						cmp_mem_addr <= mem_addr_1;
						cmp_mem_wdata <= mem_wdata_1;
						cmp_mem_wstrb <= mem_wstrb_1;
					end
				endcase
			end
			2'b 01: begin
				assume(!mem_xfer_0);
				if (mem_xfer_1) begin
					cmp_mem_state <= 2'b 00;
					assert(cmp_mem_addr == mem_addr_1);
					assert(cmp_mem_wstrb == mem_wstrb_1);
					if (cmp_mem_wstrb[3]) assert(cmp_mem_wdata[31:24] == mem_wdata_1[31:24]);
					if (cmp_mem_wstrb[2]) assert(cmp_mem_wdata[23:16] == mem_wdata_1[23:16]);
					if (cmp_mem_wstrb[1]) assert(cmp_mem_wdata[15: 8] == mem_wdata_1[15: 8]);
					if (cmp_mem_wstrb[0]) assert(cmp_mem_wdata[ 7: 0] == mem_wdata_1[ 7: 0]);
				end
			end
			2'b 10: begin
				assume(!mem_xfer_1);
				if (mem_xfer_0) begin
					cmp_mem_state <= 2'b 00;
					assert(cmp_mem_addr == mem_addr_0);
					assert(cmp_mem_wstrb == mem_wstrb_0);
					if (cmp_mem_wstrb[3]) assert(cmp_mem_wdata[31:24] == mem_wdata_0[31:24]);
					if (cmp_mem_wstrb[2]) assert(cmp_mem_wdata[23:16] == mem_wdata_0[23:16]);
					if (cmp_mem_wstrb[1]) assert(cmp_mem_wdata[15: 8] == mem_wdata_0[15: 8]);
					if (cmp_mem_wstrb[0]) assert(cmp_mem_wdata[ 7: 0] == mem_wdata_0[ 7: 0]);
				end
			end
		endcase
	end

	reg [1:0] cmp_trace_state = 0;
	reg [35:0] cmp_trace_data;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp2_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp2.v` | Lines 103–195

```verilog
always @(posedge clk) begin
		if (resetn) begin
			case (cmp_trace_state)
				2'b 00: begin
					case ({trace_valid_1, trace_valid_0})
						2'b 11: begin
							assert(trace_data_0 == trace_data_1);
						end
						2'b 01: begin
							cmp_trace_state <= 2'b 01;
							cmp_trace_data <= trace_data_0;
						end
						2'b 10: begin
							cmp_trace_state <= 2'b 10;
							cmp_trace_data <= trace_data_1;
						end
					endcase
				end
				2'b 01: begin
					assume(!trace_valid_0);
					if (trace_valid_1) begin
						cmp_trace_state <= 2'b 00;
						assert(cmp_trace_data == trace_data_1);
					end
				end
				2'b 10: begin
					assume(!trace_valid_1);
					if (trace_valid_0) begin
						cmp_trace_state <= 2'b 00;
						assert(cmp_trace_data == trace_data_0);
					end
				end
			endcase
		end
	end

	picorv32 #(
		// do not change this settings
		.ENABLE_COUNTERS(ENABLE_COUNTERS),
		.ENABLE_TRACE(1),

		// change this settings as you like
		.ENABLE_REGS_DUALPORT(1),
		.TWO_STAGE_SHIFT(0),
		.BARREL_SHIFTER(0),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(1),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0)
	) cpu_0 (
		.clk         (clk          ),
		.resetn      (resetn       ),
		.trap        (trap_0       ),
		.mem_valid   (mem_valid_0  ),
		.mem_instr   (mem_instr_0  ),
		.mem_ready   (mem_ready_0  ),
		.mem_addr    (mem_addr_0   ),
		.mem_wdata   (mem_wdata_0  ),
		.mem_wstrb   (mem_wstrb_0  ),
		.mem_rdata   (mem_rdata_0  ),
		.trace_valid (trace_valid_0),
		.trace_data  (trace_data_0 )
	);

	picorv32 #(
		// do not change this settings
		.ENABLE_COUNTERS(ENABLE_COUNTERS),
		.ENABLE_TRACE(1),

		// change this settings as you like
		.ENABLE_REGS_DUALPORT(1),
		.TWO_STAGE_SHIFT(1),
		.BARREL_SHIFTER(0),
		.TWO_CYCLE_COMPARE(0),
		.TWO_CYCLE_ALU(0),
		.COMPRESSED_ISA(1),
		.ENABLE_MUL(0),
		.ENABLE_DIV(0)
	) cpu_1 (
		.clk         (clk          ),
		.resetn      (resetn       ),
		.trap        (trap_1       ),
		.mem_valid   (mem_valid_1  ),
		.mem_instr   (mem_instr_1  ),
		.mem_ready   (mem_ready_1  ),
		.mem_addr    (mem_addr_1   ),
		.mem_wdata   (mem_wdata_1  ),
		.mem_wstrb   (mem_wstrb_1  ),
		.mem_rdata   (mem_rdata_1  ),
		.trace_valid (trace_valid_1),
		.trace_data  (trace_data_1 )
	);
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_0 | picorv32_scripts_smtbmc_tracecmp3 -->

#!/bin/bash

set -ex

yosys -l tracecmp3.yslog \
        -p 'read_verilog ../../picorv32.v' \
        -p 'read_verilog -formal tracecmp3.v' \
	-p 'prep -top testbench -nordff' \
	-p 'write_smt2 -wires tracecmp3.smt2' \
	-p 'miter -assert -flatten testbench miter' \
	-p 'hierarchy -top miter; memory_map; opt -full' \
	-p 'techmap; opt; abc; opt -fast' \
	-p 'write_blif tracecmp3.blif'

yosys-abc -c 'read_blif tracecmp3.blif; undc; strash; zero; sim3 -v; undc -c; write_cex -n tracecmp3.cex'
yosys-smtbmc -s yices --cex tracecmp3.cex --dump-vcd output.vcd --dump-smtc output.smtc tracecmp3.smt2

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_0 | Block at line 1 -->

# Verilog Block: `Block at line 1`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp3.v` | Lines 1–3

```verilog
// Based on the benchmark from 2016 Yosys-SMTBMC presentation, which in turn is
// based on the tracecmp2 test from this directory.
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_1 | module testbench ( -->

# Verilog Block: `module testbench (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp3.v` | Lines 4–14

```verilog
module testbench (
	input clk,
	input [31:0] mem_rdata_in,

	input             pcpi_wr,
	input      [31:0] pcpi_rd,
	input             pcpi_wait,
	input             pcpi_ready
);
	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_2 | always @(posedge clk) -->

# Verilog Block: `always @(posedge clk)`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp3.v` | Lines 15–54

```verilog
always @(posedge clk)
		resetn <= 1;

	wire        cpu0_trap;
	wire        cpu0_mem_valid;
	wire        cpu0_mem_instr;
	wire        cpu0_mem_ready;
	wire [31:0] cpu0_mem_addr;
	wire [31:0] cpu0_mem_wdata;
	wire [3:0]  cpu0_mem_wstrb;
	wire [31:0] cpu0_mem_rdata;
	wire        cpu0_trace_valid;
	wire [35:0] cpu0_trace_data;

	wire        cpu1_trap;
	wire        cpu1_mem_valid;
	wire        cpu1_mem_instr;
	wire        cpu1_mem_ready;
	wire [31:0] cpu1_mem_addr;
	wire [31:0] cpu1_mem_wdata;
	wire [3:0]  cpu1_mem_wstrb;
	wire [31:0] cpu1_mem_rdata;
	wire        cpu1_trace_valid;
	wire [35:0] cpu1_trace_data;

	wire        mem_ready;
	wire [31:0] mem_rdata;

	assign mem_ready = cpu0_mem_valid && cpu1_mem_valid;
	assign mem_rdata = mem_rdata_in;

	assign cpu0_mem_ready = mem_ready;
	assign cpu0_mem_rdata = mem_rdata;

	assign cpu1_mem_ready = mem_ready;
	assign cpu1_mem_rdata = mem_rdata;

	reg [ 2:0] trace_balance = 3'b010;
	reg [35:0] trace_buffer_cpu0 = 0, trace_buffer_cpu1 = 0;
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp3.v` | Lines 55–70

```verilog
always @(posedge clk) begin
		if (resetn) begin
			if (cpu0_trace_valid)
				trace_buffer_cpu0 <= cpu0_trace_data;

			if (cpu1_trace_valid)
				trace_buffer_cpu1 <= cpu1_trace_data;

			if (cpu0_trace_valid && !cpu1_trace_valid)
				trace_balance <= trace_balance << 1;

			if (!cpu0_trace_valid && cpu1_trace_valid)
				trace_balance <= trace_balance >> 1;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_smtbmc_tracecmp3_4 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/smtbmc/tracecmp3.v` | Lines 71–134

```verilog
always @* begin
		if (resetn && cpu0_mem_ready) begin
			assert(cpu0_mem_addr == cpu1_mem_addr);
			assert(cpu0_mem_wstrb == cpu1_mem_wstrb);
			if (cpu0_mem_wstrb[3]) assert(cpu0_mem_wdata[31:24] == cpu1_mem_wdata[31:24]);
			if (cpu0_mem_wstrb[2]) assert(cpu0_mem_wdata[23:16] == cpu1_mem_wdata[23:16]);
			if (cpu0_mem_wstrb[1]) assert(cpu0_mem_wdata[15: 8] == cpu1_mem_wdata[15: 8]);
			if (cpu0_mem_wstrb[0]) assert(cpu0_mem_wdata[ 7: 0] == cpu1_mem_wdata[ 7: 0]);
		end
		if (trace_balance == 3'b010) begin
			assert(trace_buffer_cpu0 == trace_buffer_cpu1);
		end
	end

	picorv32 #(
		.ENABLE_COUNTERS(0),
		.REGS_INIT_ZERO(1),
		.COMPRESSED_ISA(1),
		.ENABLE_TRACE(1),

		.TWO_STAGE_SHIFT(0),
		.ENABLE_PCPI(1)
	) cpu0 (
		.clk         (clk             ),
		.resetn      (resetn          ),
		.trap        (cpu0_trap       ),
		.mem_valid   (cpu0_mem_valid  ),
		.mem_instr   (cpu0_mem_instr  ),
		.mem_ready   (cpu0_mem_ready  ),
		.mem_addr    (cpu0_mem_addr   ),
		.mem_wdata   (cpu0_mem_wdata  ),
		.mem_wstrb   (cpu0_mem_wstrb  ),
		.mem_rdata   (cpu0_mem_rdata  ),
		.pcpi_wr     (pcpi_wr         ),
		.pcpi_rd     (pcpi_rd         ),
		.pcpi_wait   (pcpi_wait       ),
		.pcpi_ready  (pcpi_ready      ),
		.trace_valid (cpu0_trace_valid),
		.trace_data  (cpu0_trace_data )
	);

	picorv32 #(
		.ENABLE_COUNTERS(0),
		.REGS_INIT_ZERO(1),
		.COMPRESSED_ISA(1),
		.ENABLE_TRACE(1),

		.TWO_STAGE_SHIFT(1),
		.TWO_CYCLE_COMPARE(1),
		.TWO_CYCLE_ALU(1)
	) cpu1 (
		.clk         (clk             ),
		.resetn      (resetn          ),
		.trap        (cpu1_trap       ),
		.mem_valid   (cpu1_mem_valid  ),
		.mem_instr   (cpu1_mem_instr  ),
		.mem_ready   (cpu1_mem_ready  ),
		.mem_addr    (cpu1_mem_addr   ),
		.mem_wdata   (cpu1_mem_wdata  ),
		.mem_wstrb   (cpu1_mem_wstrb  ),
		.mem_rdata   (cpu1_mem_rdata  ),
		.trace_valid (cpu1_trace_valid),
		.trace_data  (cpu1_trace_data )
	);
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_README_0 | picorv32_scripts_tomthumbtg_README -->

Testing PicoRV32 using the test case generator from
the Tom Thumb RISC-V CPU project:

https://github.com/maikmerten/riscv-tomthumb
https://github.com/maikmerten/riscv-tomthumb-testgen

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_run_0 | picorv32_scripts_tomthumbtg_run -->

#!/bin/bash

set -ex

if [ ! -f testgen.tgz ]; then
	rm -f testgen.tgz.part
	wget -O testgen.tgz.part http://maikmerten.de/testgen.tgz
	mv testgen.tgz.part testgen.tgz
fi

rm -rf tests testgen/
tar xvzf testgen.tgz

iverilog -o testbench_a -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=0
iverilog -o testbench_b -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=1 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=0
iverilog -o testbench_c -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=1 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=0

iverilog -o testbench_d -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=0
iverilog -o testbench_e -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=1 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=0
iverilog -o testbench_f -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=1 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=0

iverilog -o testbench_g -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=1
iverilog -o testbench_h -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=1 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=1
iverilog -o testbench_i -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=1 -DTWO_CYCLE_COMPARE=0 -DTWO_CYCLE_ALU=1

iverilog -o testbench_j -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=1
iverilog -o testbench_k -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=1 -DBARREL_SHIFTER=0 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=1
iverilog -o testbench_l -s testbench testbench.v ../../picorv32.v -DTWO_STAGE_SHIFT=0 -DBARREL_SHIFTER=1 -DTWO_CYCLE_COMPARE=1 -DTWO_CYCLE_ALU=1

mkdir -p tests
for i in {0..999}; do
	fn="tests/test_`printf '%03d' $i`"

	{
		cat start.S
		java -jar testgen/tomthumb-testgen-1.0-SNAPSHOT.jar
	} > $fn.s

	riscv32-unknown-elf-gcc -ffreestanding -nostdlib -Wl,-Bstatic,-T,sections.lds -o $fn.elf $fn.s
	riscv32-unknown-elf-objcopy -O binary $fn.elf $fn.bin
	python3 ../../firmware/makehex.py $fn.bin 16384 > $fn.hex
	for tb in testbench_{a,b,c,d,e,f,g,h,i,j,k,l}; do vvp -N $tb +hex=$fn.hex; done
done

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_start_asm | Assembly Test: PICORV32_SCRIPTS_TOMTHUMBTG_START -->

# Assembly Test: `PICORV32_SCRIPTS_TOMTHUMBTG_START`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/start.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .text.start
.global testcollection

/* zero-initialize all registers */
addi x1, zero, 0
addi x2, zero, 0
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

/* set stack pointer */
lui sp, %hi(64*1024)
addi sp, sp, %lo(64*1024)

/* push zeros on the stack for argc and argv */
/* (stack is aligned to 16 bytes in riscv calling convention) */
addi sp,sp,-16
sw zero,0(sp)
sw zero,4(sp)
sw zero,8(sp)
sw zero,12(sp)

/* call test */
call testcollection

/* write test results */
lui x1, %hi(0x10000000)
addi x1, x1, %lo(0x10000000)
sw x5, 0(x1)

ebreak
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 3–9

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 10–43

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg  [31:0] mem_rdata;

	picorv32 #(
		.TWO_STAGE_SHIFT(`TWO_STAGE_SHIFT),
		.BARREL_SHIFTER(`BARREL_SHIFTER),
		.TWO_CYCLE_COMPARE(`TWO_CYCLE_COMPARE),
		.TWO_CYCLE_ALU(`TWO_CYCLE_ALU)
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	reg [31:0] memory [0:16*1024-1];
	reg [1023:0] hex_filename;
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_3 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 44–48

```verilog
initial begin
		if ($value$plusargs("hex=%s", hex_filename))
			$readmemh(hex_filename, memory);
	end
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_4 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 49–53

```verilog
initial begin
		// $dumpfile("testbench.vcd");
		// $dumpvars(0, testbench);
	end
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 54–61

```verilog
always @(posedge clk) begin
		if (resetn && trap) begin
			repeat (10) @(posedge clk);
			$display("TRAP");
			$stop;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_tomthumbtg_testbench_6 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/tomthumbtg/testbench.v` | Lines 62–82

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		if (mem_valid && !mem_ready) begin
			mem_ready <= 1;
			if (mem_addr == 32'h 1000_0000) begin
				if (mem_wdata != -32'd1) begin
					$display("Failed test case: %d", mem_wdata);
					$stop;
				end else begin
					$display("OK.");
					$finish;
				end
			end else begin
				mem_rdata <= memory[mem_addr >> 2];
				if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
				if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
				if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
				if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
			end
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_torture_Makefile_0 | Icarus Verilog -->

# Icarus Verilog
#TESTBENCH_EXE = tests/testbench.vvp

---
<!-- chunk_id=picorv32_scripts_torture_Makefile_1 | Verilator -->

# Verilator
TESTBENCH_EXE = obj_dir/Vtestbench

test: riscv-torture/build.ok riscv-isa-sim/build.ok
	bash test.sh

riscv-torture/build.ok: riscv-torture-rv32.diff
	rm -rf riscv-torture
	git clone https://github.com/ucb-bar/riscv-torture.git riscv-torture
	cd riscv-torture && git checkout 2bc0c42
	cd riscv-torture && patch -p1 < ../riscv-torture-rv32.diff
	cd riscv-torture && patch -p1 < ../riscv-torture-genloop.diff
	cd riscv-torture && ./sbt generator/run && touch build.ok

riscv-fesvr/build.ok:
	rm -rf riscv-fesvr
	git clone https://github.com/riscv/riscv-fesvr.git riscv-fesvr
	+cd riscv-fesvr && git checkout 1c02bd6 && ./configure && make && touch build.ok

riscv-isa-sim/build.ok: riscv-fesvr/build.ok
	rm -rf riscv-isa-sim
	git clone https://github.com/riscv/riscv-isa-sim.git riscv-isa-sim
	cd riscv-isa-sim && git checkout 10ae74e
	cd riscv-isa-sim && patch -p1 < ../riscv-isa-sim-sbreak.diff
	cd riscv-isa-sim && patch -p1 < ../riscv-isa-sim-notrap.diff
	cd riscv-isa-sim && LDFLAGS="-L../riscv-fesvr" ./configure --with-isa=RV32IMC
	+cd riscv-isa-sim && ln -s ../riscv-fesvr/fesvr . && make && touch build.ok

batch_size = 1000
batch_list = $(shell bash -c 'for i in {0..$(shell expr $(batch_size) - 1)}; do printf "%03d\n" $$i; done')

batch: $(addprefix tests/test_,$(addsuffix .ok,$(batch_list)))

config.vh: config.py riscv-torture/build.ok
	python3 config.py

obj_dir/Vtestbench: testbench.v testbench.cc ../../picorv32.v config.vh
	verilator --exe -Wno-fatal -DDEBUGASM --cc --top-module testbench testbench.v ../../picorv32.v testbench.cc
	$(MAKE) -C obj_dir -f Vtestbench.mk

tests/testbench.vvp: testbench.v ../../picorv32.v
	mkdir -p tests
	iverilog -o tests/testbench.vvp testbench.v ../../picorv32.v

tests/generated.ok: config.vh riscv-torture/build.ok
	mkdir -p tests
	rm -f riscv-torture/output/test_*
	cd riscv-torture && ./sbt 'generator/run -C config/test.config -n $(batch_size)'
	touch tests/generated.ok

define test_template
tests/test_$(1).S: tests/generated.ok
	mv riscv-torture/output/test_$(1).S tests/
	touch tests/test_$(1).S

tests/test_$(1).elf: tests/test_$(1).S
	riscv32-unknown-elf-gcc `sed '/march=/ ! d; s,^// ,-,; y/RVIMC/rvimc/;' config.vh` -ffreestanding -nostdlib \
			-Wl,-Bstatic,-T,sections.lds -I. -o tests/test_$(1).elf tests/test_$(1).S

tests/test_$(1).bin: tests/test_$(1).elf
	riscv32-unknown-elf-objcopy -O binary tests/test_$(1).elf tests/test_$(1).bin

tests/test_$(1).dmp: tests/test_$(1).elf
	riscv32-unknown-elf-objdump -d tests/test_$(1).elf > tests/test_$(1).dmp

tests/test_$(1).hex: tests/test_$(1).bin
	python3 ../../firmware/makehex.py tests/test_$(1).bin 4096 > tests/test_$(1).hex

tests/test_$(1).ref: tests/test_$(1).elf riscv-isa-sim/build.ok
	LD_LIBRARY_PATH="./riscv-isa-sim:./riscv-fesvr" ./riscv-isa-sim/spike tests/test_$(1).elf > tests/test_$(1).ref

tests/test_$(1).ok: $(TESTBENCH_EXE) tests/test_$(1).hex tests/test_$(1).ref tests/test_$(1).dmp
	$(TESTBENCH_EXE) +hex=tests/test_$(1).hex +ref=tests/test_$(1).ref > tests/test_$(1).out
	grep -q PASSED tests/test_$(1).out || { cat tests/test_$(1).out; false; }
	python3 asmcheck.py tests/test_$(1).out tests/test_$(1).dmp
	mv tests/test_$(1).out tests/test_$(1).ok
endef

$(foreach id,$(batch_list),$(eval $(call test_template,$(id))))

loop:
	date +"%s %Y-%m-%d %H:%M:%S START" >> .looplog
	+set -ex; while true; do \
	  rm -rf tests obj_dir config.vh; $(MAKE) batch; \
	  date +"%s %Y-%m-%d %H:%M:%S NEXT" >> .looplog; \
	done

clean:
	rm -rf tests obj_dir
	rm -f config.vh test.S test.elf test.bin
	rm -f test.hex test.ref test.vvp test.vcd

mrproper: clean
	rm -rf riscv-torture riscv-fesvr riscv-isa-sim

.PHONY: test batch loop clean mrproper

---
<!-- chunk_id=picorv32_scripts_torture_README_0 | picorv32_scripts_torture_README -->

Use UCB-BAR's RISC-V Torture Test Generator to test PicoRV32.

You might need to install the following addition dependecies:

sudo apt-get install python3-pip
pip3 install numpy

---
<!-- chunk_id=picorv32_scripts_torture_riscv-isa-sim-notrap_0 | picorv32_scripts_torture_riscv-isa-sim-notrap -->

diff --git a/riscv/processor.cc b/riscv/processor.cc
index 3b834c5..e112029 100644
--- a/riscv/processor.cc
+++ b/riscv/processor.cc
@@ -201,9 +201,10 @@ void processor_t::set_privilege(reg_t prv)
 
 void processor_t::take_trap(trap_t& t, reg_t epc)
 {
-  if (debug)
+  // if (debug)
     fprintf(stderr, "core %3d: exception %s, epc 0x%016" PRIx64 "\n",
             id, t.name(), epc);
+  exit(1);
 
   // by default, trap to M-mode, unless delegated to S-mode
   reg_t bit = t.cause();

---
<!-- chunk_id=picorv32_scripts_torture_riscv-isa-sim-sbreak_0 | picorv32_scripts_torture_riscv-isa-sim-sbreak -->

diff --git a/riscv/insns/c_ebreak.h b/riscv/insns/c_ebreak.h
index a17200f..af3a7ad 100644
--- a/riscv/insns/c_ebreak.h
+++ b/riscv/insns/c_ebreak.h
@@ -1,2 +1,9 @@
 require_extension('C');
+
+for (int i = 0; i < 16*1024; i += 4) {
+  unsigned int dat = MMU.load_int32(i);
+  printf("%08x\n", dat);
+}
+exit(0);
+
 throw trap_breakpoint();
diff --git a/riscv/insns/sbreak.h b/riscv/insns/sbreak.h
index c22776c..31397dd 100644
--- a/riscv/insns/sbreak.h
+++ b/riscv/insns/sbreak.h
@@ -1 +1,7 @@
+for (int i = 0; i < 16*1024; i += 4) {
+  unsigned int dat = MMU.load_int32(i);
+  printf("%08x\n", dat);
+}
+exit(0);
+
 throw trap_breakpoint();

---
<!-- chunk_id=picorv32_scripts_torture_riscv-torture-genloop_0 | picorv32_scripts_torture_riscv-torture-genloop -->

diff --git a/generator/src/main/scala/main.scala b/generator/src/main/scala/main.scala
index 7c78982..1572771 100644
--- a/generator/src/main/scala/main.scala
+++ b/generator/src/main/scala/main.scala
@@ -8,7 +8,7 @@ import java.util.Properties
 import scala.collection.JavaConversions._
 
 case class Options(var outFileName: String = "test",
-  var confFileName: String = "config/default.config")
+  var confFileName: String = "config/default.config", var numOutFiles: Int = 0)
 
 object Generator extends App
 {
@@ -17,15 +17,25 @@ object Generator extends App
     val parser = new OptionParser[Options]("generator/run") {
       opt[String]('C', "config") valueName("<file>") text("config file") action {(s: String, c) => c.copy(confFileName = s)}
       opt[String]('o', "output") valueName("<filename>") text("output filename") action {(s: String, c) => c.copy(outFileName = s)}
+      opt[Int]('n', "numfiles") valueName("<num_files>") text("number of output files") action {(n: Int, c) => c.copy(numOutFiles = n)}
     }
     parser.parse(args, Options()) match {
       case Some(opts) =>
-        generate(opts.confFileName, opts.outFileName)
+        generate_loop(opts.confFileName, opts.outFileName, opts.numOutFiles)
       case None =>
         System.exit(1) //error message printed by parser
     }
   }
 
+  def generate_loop(confFile: String, outFileName: String, numOutFiles: Int) = {
+    if (numOutFiles > 0) {
+      for (i <- 0 to (numOutFiles-1))
+        generate(confFile, outFileName + ("_%03d" format (i)))
+    } else {
+      generate(confFile, outFileName)
+    }
+  }
+
   def generate(confFile: String, outFileName: String): String = {
     val config = new Properties()
     val in = new FileInputStream(confFile)

---
<!-- chunk_id=picorv32_scripts_torture_riscv-torture-rv32_0 | picorv32_scripts_torture_riscv-torture-rv32 -->

diff --git a/config/default.config b/config/default.config
index b671223..c0b2bb4 100644
--- a/config/default.config
+++ b/config/default.config
@@ -1,18 +1,18 @@
 torture.generator.nseqs     1000
 torture.generator.memsize   1024
 torture.generator.fprnd     0
-torture.generator.amo       true
+torture.generator.amo       false
 torture.generator.mul       true
 torture.generator.divider   true
 torture.generator.run_twice true
 
 torture.generator.mix.xmem    10
 torture.generator.mix.xbranch 20
-torture.generator.mix.xalu    50
-torture.generator.mix.fgen    10
-torture.generator.mix.fpmem   5
-torture.generator.mix.fax     3
-torture.generator.mix.fdiv    2
+torture.generator.mix.xalu    70
+torture.generator.mix.fgen    0
+torture.generator.mix.fpmem   0
+torture.generator.mix.fax     0
+torture.generator.mix.fdiv    0
 torture.generator.mix.vec     0
 
 torture.generator.vec.vf 1
diff --git a/generator/src/main/scala/HWRegPool.scala b/generator/src/main/scala/HWRegPool.scala
index de2ad8d..864bcc4 100644
--- a/generator/src/main/scala/HWRegPool.scala
+++ b/generator/src/main/scala/HWRegPool.scala
@@ -86,7 +86,7 @@ trait PoolsMaster extends HWRegPool
 
 class XRegsPool extends ScalarRegPool
 {
-  val (name, regname, ldinst, stinst) = ("xreg", "reg_x", "ld", "sd")
+  val (name, regname, ldinst, stinst) = ("xreg", "reg_x", "lw", "sw")
   
   hwregs += new HWReg("x0", true, false)
   for (i <- 1 to 31)
diff --git a/generator/src/main/scala/Prog.scala b/generator/src/main/scala/Prog.scala
index 6fb49e2..685c2f8 100644
--- a/generator/src/main/scala/Prog.scala
+++ b/generator/src/main/scala/Prog.scala
@@ -385,7 +385,7 @@ class Prog(memsize: Int, veccfg: Map[String,String], run_twice: Boolean)
     "\n" +
     (if (using_vec) "RVTEST_RV64UV\n"
      else if (using_fpu) "RVTEST_RV64UF\n"
-     else "RVTEST_RV64U\n") +
+     else "RVTEST_RV32U\n") +
     "RVTEST_CODE_BEGIN\n" +
     (if (using_vec) init_vector() else "") + 
     "\n" +
diff --git a/generator/src/main/scala/Rand.scala b/generator/src/main/scala/Rand.scala
index a677d2d..ec0745f 100644
--- a/generator/src/main/scala/Rand.scala
+++ b/generator/src/main/scala/Rand.scala
@@ -15,7 +15,7 @@ object Rand
     low + Random.nextInt(span)
   }
 
-  def rand_shamt() = rand_range(0, 63)
+  def rand_shamt() = rand_range(0, 31)
   def rand_shamtw() = rand_range(0, 31)
   def rand_seglen() = rand_range(0, 7)
   def rand_imm() = rand_range(-2048, 2047)
diff --git a/generator/src/main/scala/SeqALU.scala b/generator/src/main/scala/SeqALU.scala
index a1f27a5..18d6d7b 100644
--- a/generator/src/main/scala/SeqALU.scala
+++ b/generator/src/main/scala/SeqALU.scala
@@ -68,17 +68,12 @@ class SeqALU(xregs: HWRegPool, use_mul: Boolean, use_div: Boolean) extends InstS
   candidates += seq_src1_immfn(SRAI, rand_shamt)
   candidates += seq_src1_immfn(ORI, rand_imm)
   candidates += seq_src1_immfn(ANDI, rand_imm)
-  candidates += seq_src1_immfn(ADDIW, rand_imm)
-  candidates += seq_src1_immfn(SLLIW, rand_shamtw)
-  candidates += seq_src1_immfn(SRLIW, rand_shamtw)
-  candidates += seq_src1_immfn(SRAIW, rand_shamtw)
 
   val oplist = new ArrayBuffer[Opcode]
 
   oplist += (ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND)
-  oplist += (ADDW, SUBW, SLLW, SRLW, SRAW)
-  if (use_mul) oplist += (MUL, MULH, MULHSU, MULHU, MULW)
-  if (use_div) oplist += (DIV, DIVU, REM, REMU, DIVW, DIVUW, REMW, REMUW)
+  if (use_mul) oplist += (MUL, MULH, MULHSU, MULHU)
+  if (use_div) oplist += (DIV, DIVU, REM, REMU)
 
   for (op <- oplist)
   {
diff --git a/generator/src/main/scala/SeqBranch.scala b/generator/src/main/scala/SeqBranch.scala
index bba9895..0d257d7 100644
--- a/generator/src/main/scala/SeqBranch.scala
+++ b/generator/src/main/scala/SeqBranch.scala
@@ -75,7 +75,7 @@ class SeqBranch(xregs: HWRegPool) extends InstSeq
     val reg_mask = reg_write_visible(xregs)
 
     insts += ADDI(reg_one, reg_read_zero(xregs), Imm(1))
-    insts += SLL(reg_one, reg_one, Imm(63))
+    insts += SLL(reg_one, reg_one, Imm(31))
     insts += ADDI(reg_mask, reg_read_zero(xregs), Imm(-1))
     insts += XOR(reg_mask, reg_mask, reg_one)
     insts += AND(reg_dst1, reg_src, reg_mask)
@@ -95,7 +95,7 @@ class SeqBranch(xregs: HWRegPool) extends InstSeq
     val reg_mask = reg_write_visible(xregs)
 
     insts += ADDI(reg_one, reg_read_zero(xregs), Imm(1))
-    insts += SLL(reg_one, reg_one, Imm(63))
+    insts += SLL(reg_one, reg_one, Imm(31))
     insts += ADDI(reg_mask, reg_read_zero(xregs), Imm(-1))
     insts += XOR(reg_mask, reg_mask, reg_one)
     insts += AND(reg_dst1, reg_src1, reg_mask)
diff --git a/generator/src/main/scala/SeqMem.scala b/generator/src/main/scala/SeqMem.scala
index 3c180ed..89200f6 100644
--- a/generator/src/main/scala/SeqMem.scala
+++ b/generator/src/main/scala/SeqMem.scala
@@ -51,7 +51,7 @@ class SeqMem(xregs: HWRegPool, mem: Mem, use_amo: Boolean) extends InstSeq
 
        def getRandOpAndAddr (dw_addr: Int, is_store: Boolean): (Opcode, Int) =
        {
-          val typ = AccessType.values.toIndexedSeq(rand_range(0,6))
+          val typ = AccessType.values.toIndexedSeq(rand_range(0,4))
           if (is_store)
           {
              if      (typ == byte  || typ ==ubyte)  (SB, dw_addr + rand_addr_b(8))
@@ -110,13 +110,10 @@ class SeqMem(xregs: HWRegPool, mem: Mem, use_amo: Boolean) extends InstSeq
   candidates += seq_load_addrfn(LH, rand_addr_h)
   candidates += seq_load_addrfn(LHU, rand_addr_h)
   candidates += seq_load_addrfn(LW, rand_addr_w)
-  candidates += seq_load_addrfn(LWU, rand_addr_w)
-  candidates += seq_load_addrfn(LD, rand_addr_d)
 
   candidates += seq_store_addrfn(SB, rand_addr_b)
   candidates += seq_store_addrfn(SH, rand_addr_h)
   candidates += seq_store_addrfn(SW, rand_addr_w)
-  candidates += seq_store_addrfn(SD, rand_addr_d)
 
   if (use_amo) 
   {

---
<!-- chunk_id=picorv32_scripts_torture_test_0 | Generate test case -->

## Generate test case

if ! test -f config.vh; then
	python3 config.py
fi

if ! test -f test.S; then
	cd riscv-torture
	./sbt "generator/run -C config/test.config"
	cp output/test.S ../test.S
	cd ..
fi

---
<!-- chunk_id=picorv32_scripts_torture_test_1 | Compile test case and create reference -->

## Compile test case and create reference

riscv32-unknown-elf-gcc `sed '/march=/ ! d; s,^// ,-,; y/RVIMC/rvimc/;' config.vh` -ffreestanding -nostdlib -Wl,-Bstatic,-T,sections.lds -o test.elf test.S
LD_LIBRARY_PATH="./riscv-isa-sim:./riscv-fesvr" ./riscv-isa-sim/spike test.elf > test.ref
riscv32-unknown-elf-objcopy -O binary test.elf test.bin
python3 ../../firmware/makehex.py test.bin 4096 > test.hex

---
<!-- chunk_id=picorv32_scripts_torture_test_2 | Run test -->

## Run test

iverilog -o test.vvp testbench.v ../../picorv32.v
vvp test.vvp +vcd +hex=test.hex +ref=test.ref

---
<!-- chunk_id=picorv32_scripts_torture_testbench_0 | picorv32_scripts_torture_testbench -->

#include "Vtestbench.h"
#include "verilated.h"

int main(int argc, char **argv, char **env)
{
	Verilated::commandArgs(argc, argv);
	Vtestbench* top = new Vtestbench;

	top->clk = 0;
	while (!Verilated::gotFinish()) {
		top->clk = !top->clk;
		top->eval();
	}

	delete top;
	exit(0);
}

---
<!-- chunk_id=picorv32_scripts_torture_testbench_0 | module testbench ( -->

# Verilog Block: `module testbench (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/torture/testbench.v` | Lines 1–29

```verilog
module testbench (
`ifdef VERILATOR
	input clk
`endif
);
`ifndef VERILATOR
	reg clk = 1;
	always #5 clk = ~clk;
`endif
	reg resetn = 0;
	wire trap;

	wire        mem_valid;
	wire        mem_instr;
	reg         mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0]  mem_wstrb;
	reg  [31:0] mem_rdata;

	wire        mem_la_read;
	wire        mem_la_write;
	wire [31:0] mem_la_addr;
	wire [31:0] mem_la_wdata;
	wire [3:0]  mem_la_wstrb;

	reg [31:0] x32 = 314159265;
	reg [31:0] next_x32;
```

---
<!-- chunk_id=picorv32_scripts_torture_testbench_1 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/torture/testbench.v` | Lines 30–70

```verilog
always @(posedge clk) begin
		if (resetn) begin
			next_x32 = x32;
			next_x32 = next_x32 ^ (next_x32 << 13);
			next_x32 = next_x32 ^ (next_x32 >> 17);
			next_x32 = next_x32 ^ (next_x32 << 5);
			x32 <= next_x32;
		end
	end

	picorv32 #(
`include "config.vh"
	) uut (
		.clk         (clk         ),
		.resetn      (resetn      ),
		.trap        (trap        ),

		.mem_valid   (mem_valid   ),
		.mem_instr   (mem_instr   ),
		.mem_ready   (mem_ready   ),
		.mem_addr    (mem_addr    ),
		.mem_wdata   (mem_wdata   ),
		.mem_wstrb   (mem_wstrb   ),
		.mem_rdata   (mem_rdata   ),

		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb)
	);

	localparam integer filename_len = 18;
	reg [8*filename_len-1:0] hex_filename;
	reg [8*filename_len-1:0] ref_filename;

	reg [31:0] memory [0:4095];
	reg [31:0] memory_ref [0:4095];
	integer i, errcount;
	integer cycle = 0;
```

---
<!-- chunk_id=picorv32_scripts_torture_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/torture/testbench.v` | Lines 71–81

```verilog
initial begin
		if ($value$plusargs("hex=%s", hex_filename)) $readmemh(hex_filename, memory);
		if ($value$plusargs("ref=%s", ref_filename)) $readmemh(ref_filename, memory_ref);
`ifndef VERILATOR
		if ($test$plusargs("vcd")) begin
			$dumpfile("test.vcd");
			$dumpvars(0, testbench);
		end
`endif
	end
```

---
<!-- chunk_id=picorv32_scripts_torture_testbench_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/torture/testbench.v` | Lines 82–133

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		mem_rdata <= 'bx;

		if (!trap || !resetn) begin
			if (x32[0] && resetn) begin
				if (mem_la_read) begin
					mem_ready <= 1;
					mem_rdata <= memory[mem_la_addr >> 2];
				end else
				if (mem_la_write) begin
					mem_ready <= 1;
					if (mem_la_wstrb[0]) memory[mem_la_addr >> 2][ 7: 0] <= mem_la_wdata[ 7: 0];
					if (mem_la_wstrb[1]) memory[mem_la_addr >> 2][15: 8] <= mem_la_wdata[15: 8];
					if (mem_la_wstrb[2]) memory[mem_la_addr >> 2][23:16] <= mem_la_wdata[23:16];
					if (mem_la_wstrb[3]) memory[mem_la_addr >> 2][31:24] <= mem_la_wdata[31:24];
				end else
				if (mem_valid && !mem_ready) begin
					mem_ready <= 1;
					if (mem_wstrb) begin
						if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
						if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
						if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
						if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					end else begin
						mem_rdata <= memory[mem_addr >> 2];
					end
				end
			end
		end else begin
			errcount = 0;
			for (i=0; i < 4096; i=i+1) begin
				if (memory[i] !== memory_ref[i]) begin
					$display("Signature check failed at %04x: mem=%08x ref=%08x", i << 2, memory[i], memory_ref[i]);
					errcount = errcount + 1;
				end
			end
			if (errcount)
				$display("FAILED: Got %1d errors for %1s => %1s!", errcount, hex_filename, ref_filename);
			else
				$display("PASSED %1s => %1s.", hex_filename, ref_filename);
			$finish;
		end

		if (cycle > 100000) begin
			$display("FAILED: Timeout!");
			$finish;
		end

		resetn <= cycle > 10;
		cycle <= cycle + 1;
	end
```

---
<!-- chunk_id=picorv32_scripts_vivado_Makefile_0 | work-around for http://svn.clifford.at/handicraft/2016/vivadosig11 -->

# work-around for http://svn.clifford.at/handicraft/2016/vivadosig11
export RDI_VERBOSE = False

help:
	@echo ""
	@echo "Simple synthesis tests:"
	@echo "  make synth_area_{small|regular|large}"
	@echo "  make synth_speed"
	@echo ""
	@echo "Example system:"
	@echo "  make synth_system"
	@echo "  make sim_system"
	@echo ""
	@echo "Timing and Utilization Evaluation:"
	@echo "  make table.txt"
	@echo "  make area"
	@echo ""

synth_%:
	rm -f $@.log
	$(VIVADO) -nojournal -log $@.log -mode batch -source $@.tcl
	rm -rf .Xil fsm_encoding.os synth_*.backup.log usage_statistics_webtalk.*
	-grep -B4 -A10 'Slice LUTs' $@.log
	-grep -B1 -A9 ^Slack $@.log && echo

synth_system: firmware.hex

sim_system:
	$(XVLOG) system_tb.v synth_system.v
	$(XVLOG) $(GLBL)
	$(XELAB) -L unifast_ver -L unisims_ver -R system_tb glbl

firmware.hex: firmware.S firmware.c firmware.lds
	$(TOOLCHAIN_PREFIX)gcc -Os -ffreestanding -nostdlib -o firmware.elf firmware.S firmware.c \
		 --std=gnu99 -Wl,-Bstatic,-T,firmware.lds,-Map,firmware.map,--strip-debug -lgcc
	$(TOOLCHAIN_PREFIX)objcopy -O binary firmware.elf firmware.bin
	python3 ../../firmware/makehex.py firmware.bin 4096 > firmware.hex

tab_%/results.txt:
	bash tabtest.sh $@

area: synth_area_small synth_area_regular synth_area_large
	-grep -B4 -A10 'Slice LUTs' synth_area_small.log synth_area_regular.log synth_area_large.log

table.txt: tab_small_xc7k_2/results.txt  tab_small_xc7k_3/results.txt
table.txt: tab_small_xc7v_2/results.txt  tab_small_xc7v_3/results.txt
table.txt: tab_small_xcku_2/results.txt  tab_small_xcku_3/results.txt
table.txt: tab_small_xcvu_2/results.txt  tab_small_xcvu_3/results.txt
table.txt: tab_small_xckup_2/results.txt tab_small_xckup_3/results.txt
table.txt: tab_small_xcvup_2/results.txt tab_small_xcvup_3/results.txt

table.txt:
	bash table.sh > table.txt

clean:
	rm -rf .Xil/ firmware.bin firmware.elf firmware.hex firmware.map synth_*.log
	rm -rf synth_*.mmi synth_*.bit synth_system.v table.txt tab_*/ webtalk.jou
	rm -rf webtalk.log webtalk_*.jou webtalk_*.log xelab.* xsim[._]* xvlog.*

---
<!-- chunk_id=picorv32_scripts_vivado_firmware_asm | Assembly Test: PICORV32_SCRIPTS_VIVADO_FIRMWARE -->

# Assembly Test: `PICORV32_SCRIPTS_VIVADO_FIRMWARE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/firmware.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
.section .init
.global main

/* set stack pointer */
lui sp, %hi(16*1024)
addi sp, sp, %lo(16*1024)

/* call main */
jal ra, main

/* break */
ebreak
```

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_0 | picorv32_scripts_vivado_synth_area -->

read_verilog ../../picorv32.v
read_xdc synth_area.xdc

synth_design -part xc7k70t-fbg676 -top picorv32_axi
opt_design -resynth_seq_area

report_utilization
report_timing

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_0 | picorv32_scripts_vivado_synth_area -->

create_clock -period 20.00 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_large_0 | picorv32_scripts_vivado_synth_area_large -->

read_verilog ../../picorv32.v
read_verilog synth_area_top.v
read_xdc synth_area.xdc

synth_design -part xc7k70t-fbg676 -top top_large
opt_design -sweep -propconst -resynth_seq_area
opt_design -directive ExploreSequentialArea

report_utilization
report_timing

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_regular_0 | picorv32_scripts_vivado_synth_area_regular -->

read_verilog ../../picorv32.v
read_verilog synth_area_top.v
read_xdc synth_area.xdc

synth_design -part xc7k70t-fbg676 -top top_regular
opt_design -sweep -propconst -resynth_seq_area
opt_design -directive ExploreSequentialArea

report_utilization
report_timing

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_small_0 | picorv32_scripts_vivado_synth_area_small -->

read_verilog ../../picorv32.v
read_verilog synth_area_top.v
read_xdc synth_area.xdc

synth_design -part xc7k70t-fbg676 -top top_small
opt_design -sweep -propconst -resynth_seq_area
opt_design -directive ExploreSequentialArea

report_utilization
report_timing

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_top_1 | module top_small ( -->

# Verilog Block: `module top_small (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/synth_area_top.v` | Lines 2–30

```verilog
module top_small (
	input clk, resetn,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata
);
	picorv32 #(
		.ENABLE_COUNTERS(0),
		.LATCHED_MEM_RDATA(1),
		.TWO_STAGE_SHIFT(0),
		.CATCH_MISALIGN(0),
		.CATCH_ILLINSN(0)
	) picorv32 (
		.clk      (clk      ),
		.resetn   (resetn   ),
		.mem_valid(mem_valid),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_rdata(mem_rdata)
	);
```

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_top_3 | module top_regular ( -->

# Verilog Block: `module top_regular (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/synth_area_top.v` | Lines 33–69

```verilog
module top_regular (
	input clk, resetn,
	output trap,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata,

	// Look-Ahead Interface
	output        mem_la_read,
	output        mem_la_write,
	output [31:0] mem_la_addr,
	output [31:0] mem_la_wdata,
	output [ 3:0] mem_la_wstrb
);
	picorv32 picorv32 (
		.clk         (clk         ),
		.resetn      (resetn      ),
		.trap        (trap        ),
		.mem_valid   (mem_valid   ),
		.mem_instr   (mem_instr   ),
		.mem_ready   (mem_ready   ),
		.mem_addr    (mem_addr    ),
		.mem_wdata   (mem_wdata   ),
		.mem_wstrb   (mem_wstrb   ),
		.mem_rdata   (mem_rdata   ),
		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb)
	);
```

---
<!-- chunk_id=picorv32_scripts_vivado_synth_area_top_5 | module top_large ( -->

# Verilog Block: `module top_large (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/synth_area_top.v` | Lines 72–138

```verilog
module top_large (
	input clk, resetn,
	output trap,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata,

	// Look-Ahead Interface
	output        mem_la_read,
	output        mem_la_write,
	output [31:0] mem_la_addr,
	output [31:0] mem_la_wdata,
	output [ 3:0] mem_la_wstrb,

	// Pico Co-Processor Interface (PCPI)
	output        pcpi_valid,
	output [31:0] pcpi_insn,
	output [31:0] pcpi_rs1,
	output [31:0] pcpi_rs2,
	input         pcpi_wr,
	input  [31:0] pcpi_rd,
	input         pcpi_wait,
	input         pcpi_ready,

	// IRQ Interface
	input  [31:0] irq,
	output [31:0] eoi
);
	picorv32 #(
		.COMPRESSED_ISA(1),
		.BARREL_SHIFTER(1),
		.ENABLE_PCPI(1),
		.ENABLE_MUL(1),
		.ENABLE_IRQ(1)
	) picorv32 (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.trap           (trap           ),
		.mem_valid      (mem_valid      ),
		.mem_instr      (mem_instr      ),
		.mem_ready      (mem_ready      ),
		.mem_addr       (mem_addr       ),
		.mem_wdata      (mem_wdata      ),
		.mem_wstrb      (mem_wstrb      ),
		.mem_rdata      (mem_rdata      ),
		.mem_la_read    (mem_la_read    ),
		.mem_la_write   (mem_la_write   ),
		.mem_la_addr    (mem_la_addr    ),
		.mem_la_wdata   (mem_la_wdata   ),
		.mem_la_wstrb   (mem_la_wstrb   ),
		.pcpi_valid     (pcpi_valid     ),
		.pcpi_insn      (pcpi_insn      ),
		.pcpi_rs1       (pcpi_rs1       ),
		.pcpi_rs2       (pcpi_rs2       ),
		.pcpi_wr        (pcpi_wr        ),
		.pcpi_rd        (pcpi_rd        ),
		.pcpi_wait      (pcpi_wait      ),
		.pcpi_ready     (pcpi_ready     ),
		.irq            (irq            ),
		.eoi            (eoi            )
	);
```

---
<!-- chunk_id=picorv32_scripts_vivado_synth_speed_0 | picorv32_scripts_vivado_synth_speed -->

read_verilog ../../picorv32.v
read_xdc synth_speed.xdc

synth_design -part xc7k70t-fbg676 -top picorv32_axi
opt_design
place_design
phys_opt_design
route_design

report_utilization
report_timing

---
<!-- chunk_id=picorv32_scripts_vivado_synth_speed_0 | picorv32_scripts_vivado_synth_speed -->

create_clock -period 2.50 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_vivado_synth_system_0 | write_mem_info -force synth_system.mmi -->

# write_mem_info -force synth_system.mmi

---
<!-- chunk_id=picorv32_scripts_vivado_synth_system_0 | XDC File for Basys3 Board -->

# XDC File for Basys3 Board
###########################

set_property PACKAGE_PIN W5 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
create_clock -period 10.00 [get_ports clk]

---
<!-- chunk_id=picorv32_scripts_vivado_synth_system_1 | Pmod Header JA (JA0..JA7) -->

# Pmod Header JA (JA0..JA7)
set_property PACKAGE_PIN J1 [get_ports {out_byte[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[0]}]
set_property PACKAGE_PIN L2 [get_ports {out_byte[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[1]}]
set_property PACKAGE_PIN J2 [get_ports {out_byte[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[2]}]
set_property PACKAGE_PIN G2 [get_ports {out_byte[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[3]}]
set_property PACKAGE_PIN H1 [get_ports {out_byte[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[4]}]
set_property PACKAGE_PIN K2 [get_ports {out_byte[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[5]}]
set_property PACKAGE_PIN H2 [get_ports {out_byte[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[6]}]
set_property PACKAGE_PIN G3 [get_ports {out_byte[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte[7]}]

---
<!-- chunk_id=picorv32_scripts_vivado_synth_system_2 | Pmod Header JB (JB0..JB2) -->

# Pmod Header JB (JB0..JB2)
set_property PACKAGE_PIN A14 [get_ports {resetn}]
set_property IOSTANDARD LVCMOS33 [get_ports {resetn}]
set_property PACKAGE_PIN A16 [get_ports {trap}]
set_property IOSTANDARD LVCMOS33 [get_ports {trap}]
set_property PACKAGE_PIN B15 [get_ports {out_byte_en}]
set_property IOSTANDARD LVCMOS33 [get_ports {out_byte_en}]

---
<!-- chunk_id=picorv32_scripts_vivado_system_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_1 | module system ( -->

# Verilog Block: `module system (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 3–48

```verilog
module system (
	input            clk,
	input            resetn,
	output           trap,
	output reg [7:0] out_byte,
	output reg       out_byte_en
);
	// set this to 0 for better timing but less performance/MHz
	parameter FAST_MEMORY = 1;

	// 4096 32bit words = 16kB memory
	parameter MEM_SIZE = 4096;

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg [31:0] mem_rdata;

	wire mem_la_read;
	wire mem_la_write;
	wire [31:0] mem_la_addr;
	wire [31:0] mem_la_wdata;
	wire [3:0] mem_la_wstrb;

	picorv32 picorv32_core (
		.clk         (clk         ),
		.resetn      (resetn      ),
		.trap        (trap        ),
		.mem_valid   (mem_valid   ),
		.mem_instr   (mem_instr   ),
		.mem_ready   (mem_ready   ),
		.mem_addr    (mem_addr    ),
		.mem_wdata   (mem_wdata   ),
		.mem_wstrb   (mem_wstrb   ),
		.mem_rdata   (mem_rdata   ),
		.mem_la_read (mem_la_read ),
		.mem_la_write(mem_la_write),
		.mem_la_addr (mem_la_addr ),
		.mem_la_wdata(mem_la_wdata),
		.mem_la_wstrb(mem_la_wstrb)
	);

	reg [31:0] memory [0:MEM_SIZE-1];
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_2 | initial $readmemh("firmware.hex", memory); -->

# Verilog Block: `initial $readmemh("firmware.hex", memory);`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 49–53

```verilog
initial $readmemh("firmware.hex", memory);

	reg [31:0] m_read_data;
	reg m_read_en;
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_3 | generate if (FAST_MEMORY) begin -->

# Verilog Block: `generate if (FAST_MEMORY) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 54–54

```verilog
generate if (FAST_MEMORY) begin
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 55–71

```verilog
always @(posedge clk) begin
			mem_ready <= 1;
			out_byte_en <= 0;
			mem_rdata <= memory[mem_la_addr >> 2];
			if (mem_la_write && (mem_la_addr >> 2) < MEM_SIZE) begin
				if (mem_la_wstrb[0]) memory[mem_la_addr >> 2][ 7: 0] <= mem_la_wdata[ 7: 0];
				if (mem_la_wstrb[1]) memory[mem_la_addr >> 2][15: 8] <= mem_la_wdata[15: 8];
				if (mem_la_wstrb[2]) memory[mem_la_addr >> 2][23:16] <= mem_la_wdata[23:16];
				if (mem_la_wstrb[3]) memory[mem_la_addr >> 2][31:24] <= mem_la_wdata[31:24];
			end
			else
			if (mem_la_write && mem_la_addr == 32'h1000_0000) begin
				out_byte_en <= 1;
				out_byte <= mem_la_wdata;
			end
		end
	end else begin
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system.v` | Lines 72–100

```verilog
always @(posedge clk) begin
			m_read_en <= 0;
			mem_ready <= mem_valid && !mem_ready && m_read_en;

			m_read_data <= memory[mem_addr >> 2];
			mem_rdata <= m_read_data;

			out_byte_en <= 0;

			(* parallel_case *)
			case (1)
				mem_valid && !mem_ready && !mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					m_read_en <= 1;
				end
				mem_valid && !mem_ready && |mem_wstrb && (mem_addr >> 2) < MEM_SIZE: begin
					if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
					if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
					if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
					if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
					mem_ready <= 1;
				end
				mem_valid && !mem_ready && |mem_wstrb && mem_addr == 32'h1000_0000: begin
					out_byte_en <= 1;
					out_byte <= mem_wdata;
					mem_ready <= 1;
				end
			endcase
		end
	end endgenerate
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_tb_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system_tb.v` | Lines 1–2

```verilog
`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_tb_1 | module system_tb; -->

# Verilog Block: `module system_tb;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system_tb.v` | Lines 3–7

```verilog
module system_tb;
	reg clk = 1;
	always #5 clk = ~clk;

	reg resetn = 0;
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_tb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system_tb.v` | Lines 8–28

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("system.vcd");
			$dumpvars(0, system_tb);
		end
		repeat (100) @(posedge clk);
		resetn <= 1;
	end

	wire trap;
	wire [7:0] out_byte;
	wire out_byte_en;

	system uut (
		.clk        (clk        ),
		.resetn     (resetn     ),
		.trap       (trap       ),
		.out_byte   (out_byte   ),
		.out_byte_en(out_byte_en)
	);
```

---
<!-- chunk_id=picorv32_scripts_vivado_system_tb_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/system_tb.v` | Lines 29–37

```verilog
always @(posedge clk) begin
		if (resetn && out_byte_en) begin
			$write("%c", out_byte);
			$fflush;
		end
		if (resetn && trap) begin
			$finish;
		end
	end
```

---
<!-- chunk_id=picorv32_scripts_vivado_table_0 | picorv32_scripts_vivado_table -->

#!/bin/bash

dashes="----------------------------------------------------------------"
printf '| %-25s | %-10s | %-20s |\n' "Device" "Speedgrade" "Clock Period (Freq.)"
printf '|:%.25s |:%.10s:| %.20s:|\n' $dashes $dashes $dashes

for x in $( grep -H . tab_*/results.txt )
do
	read _ size device grade _ speed < <( echo "$x" | tr _/: ' ' )
	case "$device" in
		xc7a) d="Xilinx Artix-7T" ;;
		xc7k) d="Xilinx Kintex-7T" ;;
		xc7v) d="Xilinx Virtex-7T" ;;
		xcku) d="Xilinx Kintex UltraScale" ;;
		xcvu) d="Xilinx Virtex UltraScale" ;;
		xckup) d="Xilinx Kintex UltraScale+" ;;
		xcvup) d="Xilinx Virtex UltraScale+" ;;
	esac
	speedtxt=$( printf '%s.%s ns (%d MHz)' ${speed%?} ${speed#?} $((10000 / speed)) )
	printf '| %-25s | %-10s | %20s |\n' "$d" "-$grade" "$speedtxt"
done

---
<!-- chunk_id=picorv32_scripts_vivado_tabtest_0 | rm -rf tab_${ip}_${dev}_${grade} -->

# rm -rf tab_${ip}_${dev}_${grade}
mkdir -p tab_${ip}_${dev}_${grade}
cd tab_${ip}_${dev}_${grade}

best_speed=99
speed=20
step=16

synth_case() {
	if [ -f test_${1}.txt ]; then
		echo "Reusing cached tab_${ip}_${dev}_${grade}/test_${1}."
		return
	fi

	case "${dev}" in
		xc7k) xl_device="xc7k70t-fbg676-${grade}" ;;
		xc7v) xl_device="xc7v585t-ffg1761-${grade}" ;;
		xcku) xl_device="xcku035-fbva676-${grade}-e" ;;
		xcvu) xl_device="xcvu065-ffvc1517-${grade}-e" ;;
		xckup) xl_device="xcku3p-ffva676-${grade}-e" ;;
		xcvup) xl_device="xcvu3p-ffvc1517-${grade}-e" ;;
	esac

	cat > test_${1}.tcl <<- EOT
		read_verilog ../tabtest.v
		read_verilog ../../../picorv32.v
		read_xdc test_${1}.xdc
		synth_design -flatten_hierarchy full -part ${xl_device} -top top
		opt_design -sweep -remap -propconst
		opt_design -directive Explore
		place_design -directive Explore
		phys_opt_design -retime -rewire -critical_pin_opt -placement_opt -critical_cell_opt
		route_design -directive Explore
		place_design -post_place_opt
		phys_opt_design -retime
		route_design -directive NoTimingRelaxation
		report_utilization
		report_timing
	EOT

	cat > test_${1}.xdc <<- EOT
		create_clock -period ${speed%?}.${speed#?} [get_ports clk]
	EOT

	echo "Running tab_${ip}_${dev}_${grade}/test_${1}.."
	if ! $VIVADO -nojournal -log test_${1}.log -mode batch -source test_${1}.tcl > /dev/null 2>&1; then
		cat test_${1}.log
		exit 1
	fi
	mv test_${1}.log test_${1}.txt
}

got_violated=false
got_met=false

countdown=2
while [ $countdown -gt 0 ]; do
	synth_case $speed

	if grep -q '^Slack.*(VIOLATED)' test_${speed}.txt; then
		echo "        tab_${ip}_${dev}_${grade}/test_${speed} VIOLATED"
		step=$((step / 2))
		speed=$((speed + step))
		got_violated=true
	elif grep -q '^Slack.*(MET)' test_${speed}.txt; then
		echo "        tab_${ip}_${dev}_${grade}/test_${speed} MET"
		[ $speed -lt $best_speed ] && best_speed=$speed
		step=$((step / 2))
		speed=$((speed - step))
		got_met=true
	else
		echo "ERROR: No slack line found in $PWD/test_${speed}.txt!"
		exit 1
	fi

	if [ $step -eq 0 ]; then
		countdown=$((countdown - 1))
		speed=$((best_speed - 2))
		step=1
	fi
done

if ! $got_violated; then
	echo "ERROR: No timing violated in $PWD!"
	exit 1
fi

if ! $got_met; then
	echo "ERROR: No timing met in $PWD!"
	exit 1
fi


echo "-----------------------"
echo "Best speed for tab_${ip}_${dev}_${grade}: $best_speed"
echo "-----------------------"
echo $best_speed > results.txt

---
<!-- chunk_id=picorv32_scripts_vivado_tabtest_1 | module top ( -->

# Verilog Block: `module top (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/tabtest.v` | Lines 2–100

```verilog
module top (
	input clk, io_resetn,
	output io_trap,

	output        io_mem_axi_awvalid,
	input         io_mem_axi_awready,
	output [31:0] io_mem_axi_awaddr,
	output [ 2:0] io_mem_axi_awprot,

	output        io_mem_axi_wvalid,
	input         io_mem_axi_wready,
	output [31:0] io_mem_axi_wdata,
	output [ 3:0] io_mem_axi_wstrb,

	input         io_mem_axi_bvalid,
	output        io_mem_axi_bready,

	output        io_mem_axi_arvalid,
	input         io_mem_axi_arready,
	output [31:0] io_mem_axi_araddr,
	output [ 2:0] io_mem_axi_arprot,

	input         io_mem_axi_rvalid,
	output        io_mem_axi_rready,
	input  [31:0] io_mem_axi_rdata,

	input  [31:0] io_irq,
	output [31:0] io_eoi
);
	wire resetn;
	wire trap;
	wire mem_axi_awvalid;
	wire mem_axi_awready;
	wire [31:0] mem_axi_awaddr;
	wire [2:0] mem_axi_awprot;
	wire mem_axi_wvalid;
	wire mem_axi_wready;
	wire [31:0] mem_axi_wdata;
	wire [3:0] mem_axi_wstrb;
	wire mem_axi_bvalid;
	wire mem_axi_bready;
	wire mem_axi_arvalid;
	wire mem_axi_arready;
	wire [31:0] mem_axi_araddr;
	wire [2:0] mem_axi_arprot;
	wire mem_axi_rvalid;
	wire mem_axi_rready;
	wire [31:0] mem_axi_rdata;
	wire [31:0] irq;
	wire [31:0] eoi;

	delay4 #( 1) delay_resetn          (clk, io_resetn         ,    resetn         );
	delay4 #( 1) delay_trap            (clk,    trap           , io_trap           );
	delay4 #( 1) delay_mem_axi_awvalid (clk,    mem_axi_awvalid, io_mem_axi_awvalid);
	delay4 #( 1) delay_mem_axi_awready (clk, io_mem_axi_awready,    mem_axi_awready);
	delay4 #(32) delay_mem_axi_awaddr  (clk,    mem_axi_awaddr , io_mem_axi_awaddr );
	delay4 #( 3) delay_mem_axi_awprot  (clk,    mem_axi_awprot , io_mem_axi_awprot );
	delay4 #( 1) delay_mem_axi_wvalid  (clk,    mem_axi_wvalid , io_mem_axi_wvalid );
	delay4 #( 1) delay_mem_axi_wready  (clk, io_mem_axi_wready ,    mem_axi_wready );
	delay4 #(32) delay_mem_axi_wdata   (clk,    mem_axi_wdata  , io_mem_axi_wdata  );
	delay4 #( 4) delay_mem_axi_wstrb   (clk,    mem_axi_wstrb  , io_mem_axi_wstrb  );
	delay4 #( 1) delay_mem_axi_bvalid  (clk, io_mem_axi_bvalid ,    mem_axi_bvalid );
	delay4 #( 1) delay_mem_axi_bready  (clk,    mem_axi_bready , io_mem_axi_bready );
	delay4 #( 1) delay_mem_axi_arvalid (clk,    mem_axi_arvalid, io_mem_axi_arvalid);
	delay4 #( 1) delay_mem_axi_arready (clk, io_mem_axi_arready,    mem_axi_arready);
	delay4 #(32) delay_mem_axi_araddr  (clk,    mem_axi_araddr , io_mem_axi_araddr );
	delay4 #( 3) delay_mem_axi_arprot  (clk,    mem_axi_arprot , io_mem_axi_arprot );
	delay4 #( 1) delay_mem_axi_rvalid  (clk, io_mem_axi_rvalid ,    mem_axi_rvalid );
	delay4 #( 1) delay_mem_axi_rready  (clk,    mem_axi_rready , io_mem_axi_rready );
	delay4 #(32) delay_mem_axi_rdata   (clk, io_mem_axi_rdata  ,    mem_axi_rdata  );
	delay4 #(32) delay_irq             (clk, io_irq            ,    irq            );
	delay4 #(32) delay_eoi             (clk,    eoi            , io_eoi            );

	picorv32_axi #(
		.TWO_CYCLE_ALU(1)
	) cpu (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.trap           (trap           ),
		.mem_axi_awvalid(mem_axi_awvalid),
		.mem_axi_awready(mem_axi_awready),
		.mem_axi_awaddr (mem_axi_awaddr ),
		.mem_axi_awprot (mem_axi_awprot ),
		.mem_axi_wvalid (mem_axi_wvalid ),
		.mem_axi_wready (mem_axi_wready ),
		.mem_axi_wdata  (mem_axi_wdata  ),
		.mem_axi_wstrb  (mem_axi_wstrb  ),
		.mem_axi_bvalid (mem_axi_bvalid ),
		.mem_axi_bready (mem_axi_bready ),
		.mem_axi_arvalid(mem_axi_arvalid),
		.mem_axi_arready(mem_axi_arready),
		.mem_axi_araddr (mem_axi_araddr ),
		.mem_axi_arprot (mem_axi_arprot ),
		.mem_axi_rvalid (mem_axi_rvalid ),
		.mem_axi_rready (mem_axi_rready ),
		.mem_axi_rdata  (mem_axi_rdata  ),
		.irq            (irq            ),
		.eoi            (eoi            )
	);
```

---
<!-- chunk_id=picorv32_scripts_vivado_tabtest_3 | module delay4 #( -->

# Verilog Block: `module delay4 #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/tabtest.v` | Lines 103–110

```verilog
module delay4 #(
	parameter WIDTH = 1
) (
	input clk,
	input [WIDTH-1:0] in,
	output reg [WIDTH-1:0] out
);
	reg [WIDTH-1:0] q1, q2, q3;
```

---
<!-- chunk_id=picorv32_scripts_vivado_tabtest_4 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/vivado/tabtest.v` | Lines 111–116

```verilog
always @(posedge clk) begin
		q1 <= in;
		q2 <= q1;
		q3 <= q2;
		out <= q3;
	end
```

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_README_0 | picorv32_scripts_yosys-cmp_README -->

Synthesis results for the PicoRV32 core (in its default configuration) with Yosys 0.5+383 (git sha1 8648089), Synplify Pro and Lattice LSE from iCEcube2.2014.08, and Xilinx Vivado 2015.3.

No timing constraints were used for synthesis; only resource utilisation is compared.

Last updated: 2015-10-30


Results for iCE40 Synthesis
---------------------------

| Cell          | Yosys | Synplify Pro | Lattice LSE |
|:--------------|------:|-------------:|------------:|
| `SB_CARRY`    |   405 |          349 |         309 |
| `SB_DFF`      |   125 |          256 |         114 |
| `SB_DFFE`     |   251 |          268 |          76 |
| `SB_DFFESR`   |   172 |           39 |         147 |
| `SB_DFFESS`   |     1 |            0 |          69 |
| `SB_DFFSR`    |    69 |          137 |         134 |
| `SB_DFFSS`    |     0 |            0 |          36 |
| `SB_LUT4`     |  1795 |         1657 |        1621 |
| `SB_RAM40_4K` |     4 |            4 |           4 |

Summary:

| Cell          | Yosys | Synplify Pro | Lattice LSE |
|:--------------|------:|-------------:|------------:|
| `SB_CARRY`    |   405 |          349 |         309 |
| `SB_DFF*`     |   618 |          700 |         576 |
| `SB_LUT4`     |  1795 |         1657 |        1621 |
| `SB_RAM40_4K` |     4 |            4 |           4 |


Results for Xilinx 7-Series Synthesis
-------------------------------------

| Cell        | Yosys | Vivado |
|:------------|------:|-------:|
| `FDRE`      |   671 |    553 |
| `FDSE`      |     0 |     21 |
| `LUT1`      |    41 |    160 |
| `LUT2`      |   517 |    122 |
| `LUT3`      |    77 |    120 |
| `LUT4`      |   136 |    204 |
| `LUT5`      |   142 |    135 |
| `LUT6`      |   490 |    405 |
| `MUXF7`     |    54 |      0 |
| `MUXF8`     |    15 |      0 |
| `MUXCY`     |   420 |      0 |
| `XORCY`     |   359 |      0 |
| `CARRY4`    |     0 |     83 |
| `RAMD32`    |     0 |     72 |
| `RAMS32`    |     0 |     24 |
| `RAM64X1D`  |    64 |      0 |

Summary:

| Cell        | Yosys | Vivado |
|:------------|------:|-------:|
| `FD*`       |   671 |    574 |
| `LUT*`      |  1403 |   1146 |

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_lse_0 | picorv32_scripts_yosys-cmp_lse -->

#!/bin/bash

set -ex

rm -rf lse.tmp
mkdir lse.tmp
cd lse.tmp

cat > lse.prj << EOT
#device
-a SBTiCE40
-d iCE40HX8K
-t CT256
#constraint file

#options
-frequency 200
-optimization_goal Area
-twr_paths 3
-bram_utilization 100.00
-ramstyle Auto
-romstyle Auto
-use_carry_chain 1
-carry_chain_length 0
-resource_sharing 1
-propagate_constants 1
-remove_duplicate_regs 1
-max_fanout 10000
-fsm_encoding_style Auto
-use_io_insertion 1
-use_io_reg auto
-ifd
-resolve_mixed_drivers 0
-RWCheckOnRam 0
-fix_gated_clocks 1
-top picorv32

-ver "../../../picorv32.v"
-p "."

#set result format/file last
-output_edif output.edf

#set log file
-logfile "lse.log"
EOT

icecubedir="${ICECUBEDIR:-/opt/lscc/iCEcube2.2014.08}"
export FOUNDRY="$icecubedir/LSE"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:}$icecubedir/LSE/bin/lin"
"$icecubedir"/LSE/bin/lin/synthesis -f lse.prj

grep 'viewRef.*cellRef' output.edf | sed 's,.*cellRef *,,; s,[ )].*,,;' | sort | uniq -c

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_0 | implementation attributes -->

# implementation attributes
set_option -vlog_std v2001
set_option -project_relative_includes 1

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_1 | device options -->

# device options
set_option -technology SBTiCE40
set_option -part iCE40HX8K
set_option -package CT256
set_option -speed_grade
set_option -part_companion ""

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_2 | compilation/mapping options -->

# compilation/mapping options
set_option -top_module "picorv32"

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_3 | mapper_options -->

# mapper_options
set_option -frequency auto
set_option -write_verilog 0
set_option -write_vhdl 0

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_4 | Silicon Blue iCE40 -->

# Silicon Blue iCE40
set_option -maxfan 10000
set_option -disable_io_insertion 0
set_option -pipe 1
set_option -retiming 0
set_option -update_models_cp 0
set_option -fixgatedclocks 2
set_option -fixgeneratedclocks 0

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_5 | NFilter -->

# NFilter
set_option -popfeed 0
set_option -constprop 0
set_option -createhierarchy 0

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_6 | sequential_optimization_options -->

# sequential_optimization_options
set_option -symbolic_fsm_compiler 1

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_7 | Compiler Options -->

# Compiler Options
set_option -compiler_compatible 0
set_option -resource_sharing 1

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_8 | automatic place and route (vendor) options -->

# automatic place and route (vendor) options
set_option -write_apr_constraint 1

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_synplify_9 | set result format/file last -->

# set result format/file last
project -result_format edif
project -result_file impl.edf
impl -active impl
project -run synthesis -clean
EOT

icecubedir="${ICECUBEDIR:-/opt/lscc/iCEcube2.2014.08}"
export SBT_DIR="$icecubedir/sbt_backend"
export SYNPLIFY_PATH="$icecubedir/synpbase"
export LM_LICENSE_FILE="$icecubedir/license.dat"
export TCL_LIBRARY="$icecubedir/sbt_backend/bin/linux/lib/tcl8.4"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:}$icecubedir/sbt_backend/bin/linux/opt"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:}$icecubedir/sbt_backend/bin/linux/opt/synpwrap"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:}$icecubedir/sbt_backend/lib/linux/opt"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:}$icecubedir/LSE/bin/lin"
"$icecubedir"/sbt_backend/bin/linux/opt/synpwrap/synpwrap -prj impl_syn.prj -log impl.srr

grep 'instance.*cellRef' impl/impl.edf | sed 's,.*cellRef *,,; s,[ )].*,,;' | sort | uniq -c

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_vivado_0 | picorv32_scripts_yosys-cmp_vivado -->

read_verilog ../../picorv32.v
synth_design -part xc7k70t-fbg676 -top picorv32
report_utilization

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_yosys_ice40_0 | picorv32_scripts_yosys-cmp_yosys_ice40 -->

read_verilog ../../picorv32.v
synth_ice40 -top picorv32

---
<!-- chunk_id=picorv32_scripts_yosys-cmp_yosys_xilinx_0 | picorv32_scripts_yosys-cmp_yosys_xilinx -->

read_verilog ../../picorv32.v
synth_xilinx -top picorv32

---
<!-- chunk_id=picorv32_scripts_yosys_synth_gates_0 | picorv32_scripts_yosys_synth_gates -->

library(gates) {
  cell(NOT) {
    area: 2; // 7404 hex inverter
    pin(A) { direction: input; }
    pin(Y) { direction: output;
              function: "A'"; }
  }
  cell(BUF) {
    area: 4; // 2x 7404 hex inverter
    pin(A) { direction: input; }
    pin(Y) { direction: output;
              function: "A"; }
  }
  cell(NAND) {
    area: 3; // 7400 quad 2-input NAND gate
    pin(A) { direction: input; }
    pin(B) { direction: input; }
    pin(Y) { direction: output;
             function: "(A*B)'"; }
  }
  cell(NOR) {
    area: 3; // 7402 quad 2-input NOR gate
    pin(A) { direction: input; }
    pin(B) { direction: input; }
    pin(Y) { direction: output;
             function: "(A+B)'"; }
  }
  cell(DFF) {
    area: 6; // 7474 dual D positive edge triggered flip-flop
    ff(IQ, IQN) { clocked_on: C;
                  next_state: D; }
    pin(C) { direction: input;
                 clock: true; }
    pin(D) { direction: input; }
    pin(Q) { direction: output;
              function: "IQ"; }
  }
}

---
<!-- chunk_id=picorv32_scripts_yosys_synth_gates_0 | module top ( -->

# Verilog Block: `module top (`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/scripts/yosys/synth_gates.v` | Lines 1–29

```verilog
module top (
	input clk, resetn,

	output        mem_valid,
	output        mem_instr,
	input         mem_ready,

	output [31:0] mem_addr,
	output [31:0] mem_wdata,
	output [ 3:0] mem_wstrb,
	input  [31:0] mem_rdata
);
	picorv32 #(
		.ENABLE_COUNTERS(0),
		.LATCHED_MEM_RDATA(1),
		.TWO_STAGE_SHIFT(0),
		.CATCH_MISALIGN(0),
		.CATCH_ILLINSN(0)
	) picorv32 (
		.clk      (clk      ),
		.resetn   (resetn   ),
		.mem_valid(mem_valid),
		.mem_instr(mem_instr),
		.mem_ready(mem_ready),
		.mem_addr (mem_addr ),
		.mem_wdata(mem_wdata),
		.mem_wstrb(mem_wstrb),
		.mem_rdata(mem_rdata)
	);
```

---
<!-- chunk_id=picorv32_scripts_yosys_synth_gates_0 | picorv32_scripts_yosys_synth_gates -->

read_verilog synth_gates.v
read_verilog ../../picorv32.v

hierarchy -top top
proc; flatten

synth

dfflibmap -prepare -liberty synth_gates.lib
abc -dff -liberty synth_gates.lib
dfflibmap -liberty synth_gates.lib

stat
write_blif synth_gates.blif

---
<!-- chunk_id=picorv32_scripts_yosys_synth_osu018_0 | picorv32_scripts_yosys_synth_osu018 -->

#!/bin/bash
set -ex
if test ! -s osu018_stdcells.lib; then
	wget --continue -O osu018_stdcells.lib.part http://vlsiarch.ecen.okstate.edu/flows/MOSIS_SCMOS/`
			`latest/cadence/lib/tsmc018/signalstorm/osu018_stdcells.lib
	mv osu018_stdcells.lib.part osu018_stdcells.lib
fi
yosys -p 'synth -top picorv32; dfflibmap -liberty osu018_stdcells.lib; abc -liberty osu018_stdcells.lib; stat' ../../picorv32.v

---
<!-- chunk_id=picorv32_scripts_yosys_synth_sim_0 | yosys synthesis script for post-synthesis simulation (make test_synth) -->

# yosys synthesis script for post-synthesis simulation (make test_synth)

read_verilog picorv32.v
chparam -set COMPRESSED_ISA 1 -set ENABLE_MUL 1 -set ENABLE_DIV 1 \
        -set ENABLE_IRQ 1 -set ENABLE_TRACE 1 picorv32_axi
hierarchy -top picorv32_axi
synth
write_verilog synth.v

---
<!-- chunk_id=picorv32_shell_0 | nix.shell: PicoRV32 Development Environment -->

# nix.shell: PicoRV32 Development Environment

---
<!-- chunk_id=picorv32_shell_1 | # This file allows you to use the Nix Package Manager (https://nixos.org/nix) -->

#
# This file allows you to use the Nix Package Manager (https://nixos.org/nix)

---
<!-- chunk_id=picorv32_shell_2 | in order to download, install, and prepare a working environment for doing -->

# in order to download, install, and prepare a working environment for doing

---
<!-- chunk_id=picorv32_shell_3 | PicoRV32/PicoSoC development on _any_ existing Linux distribution, provided -->

# PicoRV32/PicoSoC development on _any_ existing Linux distribution, provided

---
<!-- chunk_id=picorv32_shell_6 | #   - Synthesis: Recent Yosys and SymbiYosys -->

#
#   - Synthesis: Recent Yosys and SymbiYosys

---
<!-- chunk_id=picorv32_shell_7 | - Place and Route: arachne-pnr and nextpnr (ICE40, ECP5, Python, no GUI) -->

#   - Place and Route: arachne-pnr and nextpnr (ICE40, ECP5, Python, no GUI)

---
<!-- chunk_id=picorv32_shell_8 | - Packing: Project IceStorm (Trellis tools may be included later?) -->

#   - Packing: Project IceStorm (Trellis tools may be included later?)

---
<!-- chunk_id=picorv32_shell_9 | - SMT Solvers: Z3 4.7.x, Yices 2.6.x, and Boolector 3.0.x -->

#   - SMT Solvers: Z3 4.7.x, Yices 2.6.x, and Boolector 3.0.x

---
<!-- chunk_id=picorv32_shell_10 | - Verification: Recent Verilator, Recent (unreleased) Icarus Verilog -->

#   - Verification: Recent Verilator, Recent (unreleased) Icarus Verilog

---
<!-- chunk_id=picorv32_shell_11 | - A bare-metal RISC-V cross compiler toolchain, based on GCC 8.2.x -->

#   - A bare-metal RISC-V cross compiler toolchain, based on GCC 8.2.x

---
<!-- chunk_id=picorv32_shell_12 | # With these tools, you can immediately begin development, simulation, firmware -->

#
# With these tools, you can immediately begin development, simulation, firmware

---
<!-- chunk_id=picorv32_shell_13 | hacking, etc with almost no need to fiddle with recent tools yourself. Almost -->

# hacking, etc with almost no need to fiddle with recent tools yourself. Almost

---
<!-- chunk_id=picorv32_shell_14 | all of the tools will be downloaded on-demand (except the GCC toolchain) -->

# all of the tools will be downloaded on-demand (except the GCC toolchain)

---
<!-- chunk_id=picorv32_shell_15 | meaning you don't have to compile any recent tools yourself. Due to the -->

# meaning you don't have to compile any recent tools yourself. Due to the

---
<!-- chunk_id=picorv32_shell_16 | "hermetic" nature of Nix, these packages should also work on practically any -->

# "hermetic" nature of Nix, these packages should also work on practically any

---
<!-- chunk_id=picorv32_shell_18 | # (This environment should also be suitable for running riscv-formal test -->

#
# (This environment should also be suitable for running riscv-formal test

---
<!-- chunk_id=picorv32_shell_19 | harnesses on PicoRV32, as well. In fact it is probably useful for almost -->

# harnesses on PicoRV32, as well. In fact it is probably useful for almost

---
<!-- chunk_id=picorv32_shell_20 | _any_ RTL implementation of the RV32I core.) -->

# _any_ RTL implementation of the RV32I core.)

---
<!-- chunk_id=picorv32_shell_23 | # At the top-level of the picorv32 directory, simply run the 'nix-shell' command, -->

#
# At the top-level of the picorv32 directory, simply run the 'nix-shell' command,

---
<!-- chunk_id=picorv32_shell_24 | which will then drop you into a bash prompt: -->

# which will then drop you into a bash prompt:

---
<!-- chunk_id=picorv32_shell_30 | When you run 'nix-shell', you will automatically begin downloading all of the -->

# When you run 'nix-shell', you will automatically begin downloading all of the

---
<!-- chunk_id=picorv32_shell_31 | various tools you need from an upstream "cache", so most of this will execute -->

# various tools you need from an upstream "cache", so most of this will execute

---
<!-- chunk_id=picorv32_shell_32 | very quickly. However, this may take a while, as you will at least have to -->

# very quickly. However, this may take a while, as you will at least have to

---
<!-- chunk_id=picorv32_shell_33 | build a cross-compiled RISC-V toolchain, which may take some time. (These -->

# build a cross-compiled RISC-V toolchain, which may take some time. (These

---
<!-- chunk_id=picorv32_shell_34 | binaries are not available from the cache, so they must be built by you.) Once -->

# binaries are not available from the cache, so they must be built by you.) Once

---
<!-- chunk_id=picorv32_shell_35 | you have done this once, you do not need to do it again. -->

# you have done this once, you do not need to do it again.

---
<!-- chunk_id=picorv32_shell_36 | # At this point, once you are inside the shell, you can begin running tests -->

#
# At this point, once you are inside the shell, you can begin running tests

---
<!-- chunk_id=picorv32_shell_37 | like normal. For example, to run the Verilator tests with the included test -->

# like normal. For example, to run the Verilator tests with the included test

---
<!-- chunk_id=picorv32_shell_38 | firmware, which is substantially faster than Icarus: -->

# firmware, which is substantially faster than Icarus:

---
<!-- chunk_id=picorv32_shell_39 | #     [nix-shell:~/src/picorv32]$ make test_verilator TOOLCHAIN_PREFIX=riscv32-unknown-elf- -->

#
#     [nix-shell:~/src/picorv32]$ make test_verilator TOOLCHAIN_PREFIX=riscv32-unknown-elf-

---
<!-- chunk_id=picorv32_shell_42 | Note that you must override TOOLCHAIN_PREFIX (in the top-level Makefile, it -->

# Note that you must override TOOLCHAIN_PREFIX (in the top-level Makefile, it

---
<!-- chunk_id=picorv32_shell_44 | # This will work immediately with no extra fiddling necessary. You can also run -->

#
# This will work immediately with no extra fiddling necessary. You can also run

---
<!-- chunk_id=picorv32_shell_45 | formal verification tests using a provided SMT solver, for example, yices and -->

# formal verification tests using a provided SMT solver, for example, yices and

---
<!-- chunk_id=picorv32_shell_46 | boolector (Z3 is not used since it does not complete in a reasonable amount -->

# boolector (Z3 is not used since it does not complete in a reasonable amount

---
<!-- chunk_id=picorv32_shell_48 | #     [nix-shell:~/src/picorv32]$ make check-yices check-boolector -->

#
#     [nix-shell:~/src/picorv32]$ make check-yices check-boolector

---
<!-- chunk_id=picorv32_shell_50 | # You can also run the PicoSoC tests and build bitstreams. To run the -->

#
# You can also run the PicoSoC tests and build bitstreams. To run the

---
<!-- chunk_id=picorv32_shell_51 | simulation tests and then build bitstreams for the HX8K and IceBreaker -->

# simulation tests and then build bitstreams for the HX8K and IceBreaker

---
<!-- chunk_id=picorv32_shell_53 | #     [nix-shell:~/src/picorv32]$ cd picosoc/ -->

#
#     [nix-shell:~/src/picorv32]$ cd picosoc/

---
<!-- chunk_id=picorv32_shell_54 | [nix-shell:~/src/picorv32/picosoc]$ make hx8ksynsim icebsynsim -->

#     [nix-shell:~/src/picorv32/picosoc]$ make hx8ksynsim icebsynsim

---
<!-- chunk_id=picorv32_shell_56 | [nix-shell:~/src/picorv32/picosoc]$ make hx8kdemo.bin icebreaker.bin -->

#     [nix-shell:~/src/picorv32/picosoc]$ make hx8kdemo.bin icebreaker.bin

---
<!-- chunk_id=picorv32_shell_58 | # The HX8K simulation and IceBreaker simulation will be synthesized with Yosys -->

#
# The HX8K simulation and IceBreaker simulation will be synthesized with Yosys

---
<!-- chunk_id=picorv32_shell_59 | and then run with Icarus Verilog. The bitstreams for HX8K and IceBreaker will -->

# and then run with Icarus Verilog. The bitstreams for HX8K and IceBreaker will

---
<!-- chunk_id=picorv32_shell_60 | be P&R'd with arachne-pnr and nextpnr, respectively. -->

# be P&R'd with arachne-pnr and nextpnr, respectively.

---
<!-- chunk_id=picorv32_shell_62 | TODO FIXME: fix this to a specific version of nixpkgs. -->

# TODO FIXME: fix this to a specific version of nixpkgs.

---
<!-- chunk_id=picorv32_shell_63 | ALSO: maybe use cachix to make it easier for contributors(?) -->

# ALSO: maybe use cachix to make it easier for contributors(?)
with import <nixpkgs> {};

let
  # risc-v toolchain source code. TODO FIXME: this should be replaced with
  # upstream versions of GCC. in the future we could also include LLVM (the
  # upstream nixpkgs LLVM expression should be built with it in time)
  riscv-toolchain-ver = "8.2.0";
  riscv-src = pkgs.fetchFromGitHub {
    owner  = "riscv";
    repo   = "riscv-gnu-toolchain";
    rev    = "c3ad5556197e374c25bc475ffc9285b831f869f8";
    sha256 = "1j9y3ai42xzzph9rm116sxfzhdlrjrk4z0v4yrk197j72isqyxbc";
    fetchSubmodules = true;
  };

  # given an architecture like 'rv32i', this will generate the given
  # toolchain derivation based on the above source code.
  make-riscv-toolchain = arch:
    stdenv.mkDerivation rec {
      name    = "riscv-${arch}-toolchain-${version}";
      version = "${riscv-toolchain-ver}-${builtins.substring 0 7 src.rev}";
      src     = riscv-src;

      configureFlags   = [ "--with-arch=${arch}" ];
      installPhase     = ":"; # 'make' installs on its own
      hardeningDisable = [ "all" ];
      enableParallelBuilding = true;

      # Stripping/fixups break the resulting libgcc.a archives, somehow.
      # Maybe something in stdenv that does this...
      dontStrip = true;
      dontFixup = true;

      nativeBuildInputs = with pkgs; [ curl gawk texinfo bison flex gperf ];
      buildInputs = with pkgs; [ libmpc mpfr gmp expat ];
    };

  riscv-toolchain = make-riscv-toolchain architecture;

  # These are all the packages that will be available inside the nix-shell
  # environment.
  buildInputs = with pkgs;
    # these are generally useful packages for tests, verification, synthesis
    # and deployment, etc
    [ python3 gcc
      yosys symbiyosys nextpnr arachne-pnr icestorm
      z3 boolector yices
      verilog verilator
      # also include the RISC-V toolchain
      riscv-toolchain
    ];

---
<!-- chunk_id=picorv32_shell_64 | Export a usable shell environment -->

# Export a usable shell environment
in runCommand "picorv32-shell" { inherit buildInputs; } ""

---
<!-- chunk_id=picorv32_testbench_0 | picorv32_testbench -->

#include "Vpicorv32_wrapper.h"
#include "verilated_vcd_c.h"

int main(int argc, char **argv, char **env)
{
	printf("Built with %s %s.\n", Verilated::productName(), Verilated::productVersion());
	printf("Recommended: Verilator 4.0 or later.\n");

	Verilated::commandArgs(argc, argv);
	Vpicorv32_wrapper* top = new Vpicorv32_wrapper;

	// Tracing (vcd)
	VerilatedVcdC* tfp = NULL;
	const char* flag_vcd = Verilated::commandArgsPlusMatch("vcd");
	if (flag_vcd && 0==strcmp(flag_vcd, "+vcd")) {
		Verilated::traceEverOn(true);
		tfp = new VerilatedVcdC;
		top->trace (tfp, 99);
		tfp->open("testbench.vcd");
	}

	// Tracing (data bus, see showtrace.py)
	FILE *trace_fd = NULL;
	const char* flag_trace = Verilated::commandArgsPlusMatch("trace");
	if (flag_trace && 0==strcmp(flag_trace, "+trace")) {
		trace_fd = fopen("testbench.trace", "w");
	}

	top->clk = 0;
	int t = 0;
	while (!Verilated::gotFinish()) {
		if (t > 200)
			top->resetn = 1;
		top->clk = !top->clk;
		top->eval();
		if (tfp) tfp->dump (t);
		if (trace_fd && top->clk && top->trace_valid) fprintf(trace_fd, "%9.9lx\n", top->trace_data);
		t += 5;
	}
	if (tfp) tfp->close();
	delete top;
	exit(0);
}

---
<!-- chunk_id=picorv32_testbench_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Block Comment:** This is free and unencumbered software released into the public domain.  Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, and by any

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 1–10

```verilog
// This is free and unencumbered software released into the public domain.
//
// Anyone is free to copy, modify, publish, use, compile, sell, or
// distribute this software, either in source code form or as a compiled
// binary, for any purpose, commercial or non-commercial, and by any
// means.

`timescale 1 ns / 1 ps

`ifndef VERILATOR
```

---
<!-- chunk_id=picorv32_testbench_1 | module testbench #( -->

# Verilog Block: `module testbench #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 11–20

```verilog
module testbench #(
	parameter AXI_TEST = 0,
	parameter VERBOSE = 0
);
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_testbench_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 21–25

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 1;
	end
```

---
<!-- chunk_id=picorv32_testbench_3 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 26–39

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("testbench.vcd");
			$dumpvars(0, testbench);
		end
		repeat (1000000) @(posedge clk);
		$display("TIMEOUT");
		$finish;
	end

	wire trace_valid;
	wire [35:0] trace_data;
	integer trace_file;
```

---
<!-- chunk_id=picorv32_testbench_4 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 40–63

```verilog
initial begin
		if ($test$plusargs("trace")) begin
			trace_file = $fopen("testbench.trace", "w");
			repeat (10) @(posedge clk);
			while (!trap) begin
				@(posedge clk);
				if (trace_valid)
					$fwrite(trace_file, "%x\n", trace_data);
			end
			$fclose(trace_file);
			$display("Finished writing testbench.trace.");
		end
	end

	picorv32_wrapper #(
		.AXI_TEST (AXI_TEST),
		.VERBOSE  (VERBOSE)
	) top (
		.clk(clk),
		.resetn(resetn),
		.trap(trap),
		.trace_valid(trace_valid),
		.trace_data(trace_data)
	);
```

---
<!-- chunk_id=picorv32_testbench_6 | module picorv32_wrapper #( -->

# Verilog Block: `module picorv32_wrapper #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 67–80

```verilog
module picorv32_wrapper #(
	parameter AXI_TEST = 0,
	parameter VERBOSE = 0
) (
	input clk,
	input resetn,
	output trap,
	output trace_valid,
	output [35:0] trace_data
);
	wire tests_passed;
	reg [31:0] irq = 0;

	reg [15:0] count_cycle = 0;
```

---
<!-- chunk_id=picorv32_testbench_7 | always @(posedge clk) count_cycle <= resetn ? count_cycle + 1 : 0; -->

# Verilog Block: `always @(posedge clk) count_cycle <= resetn ? count_cycle + 1 : 0;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 81–82

```verilog
always @(posedge clk) count_cycle <= resetn ? count_cycle + 1 : 0;
```

---
<!-- chunk_id=picorv32_testbench_8 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 83–249

```verilog
always @* begin
		irq = 0;
		irq[4] = &count_cycle[12:0];
		irq[5] = &count_cycle[15:0];
	end

	wire        mem_axi_awvalid;
	wire        mem_axi_awready;
	wire [31:0] mem_axi_awaddr;
	wire [ 2:0] mem_axi_awprot;

	wire        mem_axi_wvalid;
	wire        mem_axi_wready;
	wire [31:0] mem_axi_wdata;
	wire [ 3:0] mem_axi_wstrb;

	wire        mem_axi_bvalid;
	wire        mem_axi_bready;

	wire        mem_axi_arvalid;
	wire        mem_axi_arready;
	wire [31:0] mem_axi_araddr;
	wire [ 2:0] mem_axi_arprot;

	wire        mem_axi_rvalid;
	wire        mem_axi_rready;
	wire [31:0] mem_axi_rdata;

	axi4_memory #(
		.AXI_TEST (AXI_TEST),
		.VERBOSE  (VERBOSE)
	) mem (
		.clk             (clk             ),
		.mem_axi_awvalid (mem_axi_awvalid ),
		.mem_axi_awready (mem_axi_awready ),
		.mem_axi_awaddr  (mem_axi_awaddr  ),
		.mem_axi_awprot  (mem_axi_awprot  ),

		.mem_axi_wvalid  (mem_axi_wvalid  ),
		.mem_axi_wready  (mem_axi_wready  ),
		.mem_axi_wdata   (mem_axi_wdata   ),
		.mem_axi_wstrb   (mem_axi_wstrb   ),

		.mem_axi_bvalid  (mem_axi_bvalid  ),
		.mem_axi_bready  (mem_axi_bready  ),

		.mem_axi_arvalid (mem_axi_arvalid ),
		.mem_axi_arready (mem_axi_arready ),
		.mem_axi_araddr  (mem_axi_araddr  ),
		.mem_axi_arprot  (mem_axi_arprot  ),

		.mem_axi_rvalid  (mem_axi_rvalid  ),
		.mem_axi_rready  (mem_axi_rready  ),
		.mem_axi_rdata   (mem_axi_rdata   ),

		.tests_passed    (tests_passed    )
	);

`ifdef RISCV_FORMAL
	wire        rvfi_valid;
	wire [63:0] rvfi_order;
	wire [31:0] rvfi_insn;
	wire        rvfi_trap;
	wire        rvfi_halt;
	wire        rvfi_intr;
	wire [4:0]  rvfi_rs1_addr;
	wire [4:0]  rvfi_rs2_addr;
	wire [31:0] rvfi_rs1_rdata;
	wire [31:0] rvfi_rs2_rdata;
	wire [4:0]  rvfi_rd_addr;
	wire [31:0] rvfi_rd_wdata;
	wire [31:0] rvfi_pc_rdata;
	wire [31:0] rvfi_pc_wdata;
	wire [31:0] rvfi_mem_addr;
	wire [3:0]  rvfi_mem_rmask;
	wire [3:0]  rvfi_mem_wmask;
	wire [31:0] rvfi_mem_rdata;
	wire [31:0] rvfi_mem_wdata;
`endif

	picorv32_axi #(
`ifndef SYNTH_TEST
`ifdef SP_TEST
		.ENABLE_REGS_DUALPORT(0),
`endif
`ifdef COMPRESSED_ISA
		.COMPRESSED_ISA(1),
`endif
		.ENABLE_MUL(1),
		.ENABLE_DIV(1),
		.ENABLE_IRQ(1),
		.ENABLE_TRACE(1)
`endif
	) uut (
		.clk            (clk            ),
		.resetn         (resetn         ),
		.trap           (trap           ),
		.mem_axi_awvalid(mem_axi_awvalid),
		.mem_axi_awready(mem_axi_awready),
		.mem_axi_awaddr (mem_axi_awaddr ),
		.mem_axi_awprot (mem_axi_awprot ),
		.mem_axi_wvalid (mem_axi_wvalid ),
		.mem_axi_wready (mem_axi_wready ),
		.mem_axi_wdata  (mem_axi_wdata  ),
		.mem_axi_wstrb  (mem_axi_wstrb  ),
		.mem_axi_bvalid (mem_axi_bvalid ),
		.mem_axi_bready (mem_axi_bready ),
		.mem_axi_arvalid(mem_axi_arvalid),
		.mem_axi_arready(mem_axi_arready),
		.mem_axi_araddr (mem_axi_araddr ),
		.mem_axi_arprot (mem_axi_arprot ),
		.mem_axi_rvalid (mem_axi_rvalid ),
		.mem_axi_rready (mem_axi_rready ),
		.mem_axi_rdata  (mem_axi_rdata  ),
		.irq            (irq            ),
`ifdef RISCV_FORMAL
		.rvfi_valid     (rvfi_valid     ),
		.rvfi_order     (rvfi_order     ),
		.rvfi_insn      (rvfi_insn      ),
		.rvfi_trap      (rvfi_trap      ),
		.rvfi_halt      (rvfi_halt      ),
		.rvfi_intr      (rvfi_intr      ),
		.rvfi_rs1_addr  (rvfi_rs1_addr  ),
		.rvfi_rs2_addr  (rvfi_rs2_addr  ),
		.rvfi_rs1_rdata (rvfi_rs1_rdata ),
		.rvfi_rs2_rdata (rvfi_rs2_rdata ),
		.rvfi_rd_addr   (rvfi_rd_addr   ),
		.rvfi_rd_wdata  (rvfi_rd_wdata  ),
		.rvfi_pc_rdata  (rvfi_pc_rdata  ),
		.rvfi_pc_wdata  (rvfi_pc_wdata  ),
		.rvfi_mem_addr  (rvfi_mem_addr  ),
		.rvfi_mem_rmask (rvfi_mem_rmask ),
		.rvfi_mem_wmask (rvfi_mem_wmask ),
		.rvfi_mem_rdata (rvfi_mem_rdata ),
		.rvfi_mem_wdata (rvfi_mem_wdata ),
`endif
		.trace_valid    (trace_valid    ),
		.trace_data     (trace_data     )
	);

`ifdef RISCV_FORMAL
	picorv32_rvfimon rvfi_monitor (
		.clock          (clk           ),
		.reset          (!resetn       ),
		.rvfi_valid     (rvfi_valid    ),
		.rvfi_order     (rvfi_order    ),
		.rvfi_insn      (rvfi_insn     ),
		.rvfi_trap      (rvfi_trap     ),
		.rvfi_halt      (rvfi_halt     ),
		.rvfi_intr      (rvfi_intr     ),
		.rvfi_rs1_addr  (rvfi_rs1_addr ),
		.rvfi_rs2_addr  (rvfi_rs2_addr ),
		.rvfi_rs1_rdata (rvfi_rs1_rdata),
		.rvfi_rs2_rdata (rvfi_rs2_rdata),
		.rvfi_rd_addr   (rvfi_rd_addr  ),
		.rvfi_rd_wdata  (rvfi_rd_wdata ),
		.rvfi_pc_rdata  (rvfi_pc_rdata ),
		.rvfi_pc_wdata  (rvfi_pc_wdata ),
		.rvfi_mem_addr  (rvfi_mem_addr ),
		.rvfi_mem_rmask (rvfi_mem_rmask),
		.rvfi_mem_wmask (rvfi_mem_wmask),
		.rvfi_mem_rdata (rvfi_mem_rdata),
		.rvfi_mem_wdata (rvfi_mem_wdata)
	);
`endif

	reg [1023:0] firmware_file;
```

---
<!-- chunk_id=picorv32_testbench_9 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 250–256

```verilog
initial begin
		if (!$value$plusargs("firmware=%s", firmware_file))
			firmware_file = "firmware/firmware.hex";
		$readmemh(firmware_file, mem.memory);
	end

	integer cycle_counter;
```

---
<!-- chunk_id=picorv32_testbench_10 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 257–274

```verilog
always @(posedge clk) begin
		cycle_counter <= resetn ? cycle_counter + 1 : 0;
		if (resetn && trap) begin
`ifndef VERILATOR
			repeat (10) @(posedge clk);
`endif
			$display("TRAP after %1d clock cycles", cycle_counter);
			if (tests_passed) begin
				$display("ALL TESTS PASSED.");
				$finish;
			end else begin
				$display("ERROR!");
				if ($test$plusargs("noerror"))
					$finish;
				$stop;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_testbench_12 | module axi4_memory #( -->

# Verilog Block: `module axi4_memory #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 277–309

```verilog
module axi4_memory #(
	parameter AXI_TEST = 0,
	parameter VERBOSE = 0
) (
	/* verilator lint_off MULTIDRIVEN */

	input             clk,
	input             mem_axi_awvalid,
	output reg        mem_axi_awready,
	input      [31:0] mem_axi_awaddr,
	input      [ 2:0] mem_axi_awprot,

	input             mem_axi_wvalid,
	output reg        mem_axi_wready,
	input      [31:0] mem_axi_wdata,
	input      [ 3:0] mem_axi_wstrb,

	output reg        mem_axi_bvalid,
	input             mem_axi_bready,

	input             mem_axi_arvalid,
	output reg        mem_axi_arready,
	input      [31:0] mem_axi_araddr,
	input      [ 2:0] mem_axi_arprot,

	output reg        mem_axi_rvalid,
	input             mem_axi_rready,
	output reg [31:0] mem_axi_rdata,

	output reg        tests_passed
);
	reg [31:0]   memory [0:128*1024/4-1] /* verilator public */;
	reg verbose;
```

---
<!-- chunk_id=picorv32_testbench_13 | initial verbose = $test$plusargs("verbose") || VERBOSE; -->

# Verilog Block: `initial verbose = $test$plusargs("verbose") || VERBOSE;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 310–312

```verilog
initial verbose = $test$plusargs("verbose") || VERBOSE;

	reg axi_test;
```

---
<!-- chunk_id=picorv32_testbench_14 | initial axi_test = $test$plusargs("axi_test") || AXI_TEST; -->

# Verilog Block: `initial axi_test = $test$plusargs("axi_test") || AXI_TEST;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 313–314

```verilog
initial axi_test = $test$plusargs("axi_test") || AXI_TEST;
```

---
<!-- chunk_id=picorv32_testbench_15 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 315–325

```verilog
initial begin
		mem_axi_awready = 0;
		mem_axi_wready = 0;
		mem_axi_bvalid = 0;
		mem_axi_arready = 0;
		mem_axi_rvalid = 0;
		tests_passed = 0;
	end

	reg [63:0] xorshift64_state = 64'd88172645463325252;
```

---
<!-- chunk_id=picorv32_testbench_16 | task xorshift64_next; -->

# Verilog Block: `task xorshift64_next;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 326–338

```verilog
task xorshift64_next;
		begin
			// see page 4 of Marsaglia, George (July 2003). "Xorshift RNGs". Journal of Statistical Software 8 (14).
			xorshift64_state = xorshift64_state ^ (xorshift64_state << 13);
			xorshift64_state = xorshift64_state ^ (xorshift64_state >>  7);
			xorshift64_state = xorshift64_state ^ (xorshift64_state << 17);
		end
	endtask

	reg [2:0] fast_axi_transaction = ~0;
	reg [4:0] async_axi_transaction = ~0;
	reg [4:0] delay_axi_transaction = 0;
```

---
<!-- chunk_id=picorv32_testbench_17 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 339–359

```verilog
always @(posedge clk) begin
		if (axi_test) begin
				xorshift64_next;
				{fast_axi_transaction, async_axi_transaction, delay_axi_transaction} <= xorshift64_state;
		end
	end

	reg latched_raddr_en = 0;
	reg latched_waddr_en = 0;
	reg latched_wdata_en = 0;

	reg fast_raddr = 0;
	reg fast_waddr = 0;
	reg fast_wdata = 0;

	reg [31:0] latched_raddr;
	reg [31:0] latched_waddr;
	reg [31:0] latched_wdata;
	reg [ 3:0] latched_wstrb;
	reg        latched_rinsn;
```

---
<!-- chunk_id=picorv32_testbench_18 | task handle_axi_arvalid; begin -->

# Verilog Block: `task handle_axi_arvalid; begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 360–367

```verilog
task handle_axi_arvalid; begin
		mem_axi_arready <= 1;
		latched_raddr = mem_axi_araddr;
		latched_rinsn = mem_axi_arprot[2];
		latched_raddr_en = 1;
		fast_raddr <= 1;
	end endtask
```

---
<!-- chunk_id=picorv32_testbench_19 | task handle_axi_awvalid; begin -->

# Verilog Block: `task handle_axi_awvalid; begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 368–374

```verilog
task handle_axi_awvalid; begin
		mem_axi_awready <= 1;
		latched_waddr = mem_axi_awaddr;
		latched_waddr_en = 1;
		fast_waddr <= 1;
	end endtask
```

---
<!-- chunk_id=picorv32_testbench_20 | task handle_axi_wvalid; begin -->

# Verilog Block: `task handle_axi_wvalid; begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 375–382

```verilog
task handle_axi_wvalid; begin
		mem_axi_wready <= 1;
		latched_wdata = mem_axi_wdata;
		latched_wstrb = mem_axi_wstrb;
		latched_wdata_en = 1;
		fast_wdata <= 1;
	end endtask
```

---
<!-- chunk_id=picorv32_testbench_21 | task handle_axi_rvalid; begin -->

# Verilog Block: `task handle_axi_rvalid; begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 383–395

```verilog
task handle_axi_rvalid; begin
		if (verbose)
			$display("RD: ADDR=%08x DATA=%08x%s", latched_raddr, memory[latched_raddr >> 2], latched_rinsn ? " INSN" : "");
		if (latched_raddr < 128*1024) begin
			mem_axi_rdata <= memory[latched_raddr >> 2];
			mem_axi_rvalid <= 1;
			latched_raddr_en = 0;
		end else begin
			$display("OUT-OF-BOUNDS MEMORY READ FROM %08x", latched_raddr);
			$finish;
		end
	end endtask
```

---
<!-- chunk_id=picorv32_testbench_22 | task handle_axi_bvalid; begin -->

# Verilog Block: `task handle_axi_bvalid; begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 396–429

```verilog
task handle_axi_bvalid; begin
		if (verbose)
			$display("WR: ADDR=%08x DATA=%08x STRB=%04b", latched_waddr, latched_wdata, latched_wstrb);
		if (latched_waddr < 128*1024) begin
			if (latched_wstrb[0]) memory[latched_waddr >> 2][ 7: 0] <= latched_wdata[ 7: 0];
			if (latched_wstrb[1]) memory[latched_waddr >> 2][15: 8] <= latched_wdata[15: 8];
			if (latched_wstrb[2]) memory[latched_waddr >> 2][23:16] <= latched_wdata[23:16];
			if (latched_wstrb[3]) memory[latched_waddr >> 2][31:24] <= latched_wdata[31:24];
		end else
		if (latched_waddr == 32'h1000_0000) begin
			if (verbose) begin
				if (32 <= latched_wdata && latched_wdata < 128)
					$display("OUT: '%c'", latched_wdata[7:0]);
				else
					$display("OUT: %3d", latched_wdata);
			end else begin
				$write("%c", latched_wdata[7:0]);
`ifndef VERILATOR
				$fflush();
`endif
			end
		end else
		if (latched_waddr == 32'h2000_0000) begin
			if (latched_wdata == 123456789)
				tests_passed = 1;
		end else begin
			$display("OUT-OF-BOUNDS MEMORY WRITE TO %08x", latched_waddr);
			$finish;
		end
		mem_axi_bvalid <= 1;
		latched_waddr_en = 0;
		latched_wdata_en = 0;
	end endtask
```

---
<!-- chunk_id=picorv32_testbench_23 | always @(negedge clk) begin -->

# Verilog Block: `always @(negedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 430–437

```verilog
always @(negedge clk) begin
		if (mem_axi_arvalid && !(latched_raddr_en || fast_raddr) && async_axi_transaction[0]) handle_axi_arvalid;
		if (mem_axi_awvalid && !(latched_waddr_en || fast_waddr) && async_axi_transaction[1]) handle_axi_awvalid;
		if (mem_axi_wvalid  && !(latched_wdata_en || fast_wdata) && async_axi_transaction[2]) handle_axi_wvalid;
		if (!mem_axi_rvalid && latched_raddr_en && async_axi_transaction[3]) handle_axi_rvalid;
		if (!mem_axi_bvalid && latched_waddr_en && latched_wdata_en && async_axi_transaction[4]) handle_axi_bvalid;
	end
```

---
<!-- chunk_id=picorv32_testbench_24 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench.v` | Lines 438–478

```verilog
always @(posedge clk) begin
		mem_axi_arready <= 0;
		mem_axi_awready <= 0;
		mem_axi_wready <= 0;

		fast_raddr <= 0;
		fast_waddr <= 0;
		fast_wdata <= 0;

		if (mem_axi_rvalid && mem_axi_rready) begin
			mem_axi_rvalid <= 0;
		end

		if (mem_axi_bvalid && mem_axi_bready) begin
			mem_axi_bvalid <= 0;
		end

		if (mem_axi_arvalid && mem_axi_arready && !fast_raddr) begin
			latched_raddr = mem_axi_araddr;
			latched_rinsn = mem_axi_arprot[2];
			latched_raddr_en = 1;
		end

		if (mem_axi_awvalid && mem_axi_awready && !fast_waddr) begin
			latched_waddr = mem_axi_awaddr;
			latched_waddr_en = 1;
		end

		if (mem_axi_wvalid && mem_axi_wready && !fast_wdata) begin
			latched_wdata = mem_axi_wdata;
			latched_wstrb = mem_axi_wstrb;
			latched_wdata_en = 1;
		end

		if (mem_axi_arvalid && !(latched_raddr_en || fast_raddr) && !delay_axi_transaction[0]) handle_axi_arvalid;
		if (mem_axi_awvalid && !(latched_waddr_en || fast_waddr) && !delay_axi_transaction[1]) handle_axi_awvalid;
		if (mem_axi_wvalid  && !(latched_wdata_en || fast_wdata) && !delay_axi_transaction[2]) handle_axi_wvalid;

		if (!mem_axi_rvalid && latched_raddr_en && !delay_axi_transaction[3]) handle_axi_rvalid;
		if (!mem_axi_bvalid && latched_waddr_en && latched_wdata_en && !delay_axi_transaction[4]) handle_axi_bvalid;
	end
```

---
<!-- chunk_id=picorv32_testbench_ez_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Block Comment:** This is free and unencumbered software released into the public domain.  Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, and by any

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 1–9

```verilog
// This is free and unencumbered software released into the public domain.
//
// Anyone is free to copy, modify, publish, use, compile, sell, or
// distribute this software, either in source code form or as a compiled
// binary, for any purpose, commercial or non-commercial, and by any
// means.

`timescale 1 ns / 1 ps
```

---
<!-- chunk_id=picorv32_testbench_ez_1 | module testbench; -->

# Verilog Block: `module testbench;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 10–16

```verilog
module testbench;
	reg clk = 1;
	reg resetn = 0;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_testbench_ez_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 17–35

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("testbench.vcd");
			$dumpvars(0, testbench);
		end
		repeat (100) @(posedge clk);
		resetn <= 1;
		repeat (1000) @(posedge clk);
		$finish;
	end

	wire mem_valid;
	wire mem_instr;
	reg mem_ready;
	wire [31:0] mem_addr;
	wire [31:0] mem_wdata;
	wire [3:0] mem_wstrb;
	reg  [31:0] mem_rdata;
```

---
<!-- chunk_id=picorv32_testbench_ez_3 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 36–62

```verilog
always @(posedge clk) begin
		if (mem_valid && mem_ready) begin
			if (mem_instr)
				$display("ifetch 0x%08x: 0x%08x", mem_addr, mem_rdata);
			else if (mem_wstrb)
				$display("write  0x%08x: 0x%08x (wstrb=%b)", mem_addr, mem_wdata, mem_wstrb);
			else
				$display("read   0x%08x: 0x%08x", mem_addr, mem_rdata);
		end
	end

	picorv32 #(
	) uut (
		.clk         (clk        ),
		.resetn      (resetn     ),
		.trap        (trap       ),
		.mem_valid   (mem_valid  ),
		.mem_instr   (mem_instr  ),
		.mem_ready   (mem_ready  ),
		.mem_addr    (mem_addr   ),
		.mem_wdata   (mem_wdata  ),
		.mem_wstrb   (mem_wstrb  ),
		.mem_rdata   (mem_rdata  )
	);

	reg [31:0] memory [0:255];
```

---
<!-- chunk_id=picorv32_testbench_ez_4 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 63–71

```verilog
initial begin
		memory[0] = 32'h 3fc00093; //       li      x1,1020
		memory[1] = 32'h 0000a023; //       sw      x0,0(x1)
		memory[2] = 32'h 0000a103; // loop: lw      x2,0(x1)
		memory[3] = 32'h 00110113; //       addi    x2,x2,1
		memory[4] = 32'h 0020a023; //       sw      x2,0(x1)
		memory[5] = 32'h ff5ff06f; //       j       <loop>
	end
```

---
<!-- chunk_id=picorv32_testbench_ez_5 | always @(posedge clk) begin -->

# Verilog Block: `always @(posedge clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_ez.v` | Lines 72–85

```verilog
always @(posedge clk) begin
		mem_ready <= 0;
		if (mem_valid && !mem_ready) begin
			if (mem_addr < 1024) begin
				mem_ready <= 1;
				mem_rdata <= memory[mem_addr >> 2];
				if (mem_wstrb[0]) memory[mem_addr >> 2][ 7: 0] <= mem_wdata[ 7: 0];
				if (mem_wstrb[1]) memory[mem_addr >> 2][15: 8] <= mem_wdata[15: 8];
				if (mem_wstrb[2]) memory[mem_addr >> 2][23:16] <= mem_wdata[23:16];
				if (mem_wstrb[3]) memory[mem_addr >> 2][31:24] <= mem_wdata[31:24];
			end
			/* add memory-mapped IO here */
		end
	end
```

---
<!-- chunk_id=picorv32_testbench_wb_0 | `timescale 1 ns / 1 ps -->

# Verilog Block: ``timescale 1 ns / 1 ps`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 1–3

```verilog
`timescale 1 ns / 1 ps

`ifndef VERILATOR
```

---
<!-- chunk_id=picorv32_testbench_wb_1 | module testbench #( -->

# Verilog Block: `module testbench #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 4–12

```verilog
module testbench #(
	parameter VERBOSE = 0
);
	reg clk = 1;
	reg resetn = 1;
	wire trap;

	always #5 clk = ~clk;
```

---
<!-- chunk_id=picorv32_testbench_wb_2 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 13–17

```verilog
initial begin
		repeat (100) @(posedge clk);
		resetn <= 0;
	end
```

---
<!-- chunk_id=picorv32_testbench_wb_3 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 18–31

```verilog
initial begin
		if ($test$plusargs("vcd")) begin
			$dumpfile("testbench.vcd");
			$dumpvars(0, testbench);
		end
		repeat (1000000) @(posedge clk);
		$display("TIMEOUT");
		$finish;
	end

	wire trace_valid;
	wire [35:0] trace_data;
	integer trace_file;
```

---
<!-- chunk_id=picorv32_testbench_wb_4 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 32–54

```verilog
initial begin
		if ($test$plusargs("trace")) begin
			trace_file = $fopen("testbench.trace", "w");
			repeat (10) @(posedge clk);
			while (!trap) begin
				@(posedge clk);
				if (trace_valid)
					$fwrite(trace_file, "%x\n", trace_data);
			end
			$fclose(trace_file);
			$display("Finished writing testbench.trace.");
		end
	end

	picorv32_wrapper #(
		.VERBOSE (VERBOSE)
	) top (
		.wb_clk(clk),
		.wb_rst(resetn),
		.trap(trap),
		.trace_valid(trace_valid),
		.trace_data(trace_data)
	);
```

---
<!-- chunk_id=picorv32_testbench_wb_6 | module picorv32_wrapper #( -->

# Verilog Block: `module picorv32_wrapper #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 58–71

```verilog
module picorv32_wrapper #(
	parameter VERBOSE = 0
) (
	input wb_clk,
	input wb_rst,
	output trap,
	output trace_valid,
	output [35:0] trace_data
);
	wire tests_passed;
	reg [31:0] irq = 0;
	wire mem_instr;

	reg [15:0] count_cycle = 0;
```

---
<!-- chunk_id=picorv32_testbench_wb_7 | always @(posedge wb_clk) count_cycle <= !wb_rst ? count_cycle + 1 : 0; -->

# Verilog Block: `always @(posedge wb_clk) count_cycle <= !wb_rst ? count_cycle + 1 : 0;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 72–73

```verilog
always @(posedge wb_clk) count_cycle <= !wb_rst ? count_cycle + 1 : 0;
```

---
<!-- chunk_id=picorv32_testbench_wb_8 | always @* begin -->

# Verilog Block: `always @* begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 74–142

```verilog
always @* begin
		irq = 0;
		irq[4] = &count_cycle[12:0];
		irq[5] = &count_cycle[15:0];
	end

	wire [31:0] wb_m2s_adr;
	wire [31:0] wb_m2s_dat;
	wire [3:0] wb_m2s_sel;
	wire wb_m2s_we;
	wire wb_m2s_cyc;
	wire wb_m2s_stb;
	wire [31:0] wb_s2m_dat;
	wire wb_s2m_ack;

	wb_ram #(
		.depth (128*1024),
		.VERBOSE (VERBOSE)
	) ram ( // Wishbone interface
		.wb_clk_i(wb_clk),
		.wb_rst_i(wb_rst),

		.wb_adr_i(wb_m2s_adr),
		.wb_dat_i(wb_m2s_dat),
		.wb_stb_i(wb_m2s_stb),
		.wb_cyc_i(wb_m2s_cyc),
		.wb_dat_o(wb_s2m_dat),
		.wb_ack_o(wb_s2m_ack),
		.wb_sel_i(wb_m2s_sel),
		.wb_we_i(wb_m2s_we),

		.mem_instr(mem_instr),
		.tests_passed(tests_passed)
	);

	picorv32_wb #(
`ifndef SYNTH_TEST
`ifdef SP_TEST
		.ENABLE_REGS_DUALPORT(0),
`endif
`ifdef COMPRESSED_ISA
		.COMPRESSED_ISA(1),
`endif
		.ENABLE_MUL(1),
		.ENABLE_DIV(1),
		.ENABLE_IRQ(1),
		.ENABLE_TRACE(1)
`endif
	) uut (
		.trap (trap),
		.irq (irq),
		.trace_valid (trace_valid),
		.trace_data (trace_data),
		.mem_instr(mem_instr),

		.wb_clk_i(wb_clk),
		.wb_rst_i(wb_rst),

		.wbm_adr_o(wb_m2s_adr),
		.wbm_dat_i(wb_s2m_dat),
		.wbm_stb_o(wb_m2s_stb),
		.wbm_ack_i(wb_s2m_ack),
		.wbm_cyc_o(wb_m2s_cyc),
		.wbm_dat_o(wb_m2s_dat),
		.wbm_we_o(wb_m2s_we),
		.wbm_sel_o(wb_m2s_sel)
	);

	reg [1023:0] firmware_file;
```

---
<!-- chunk_id=picorv32_testbench_wb_9 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 143–149

```verilog
initial begin
		if (!$value$plusargs("firmware=%s", firmware_file))
			firmware_file = "firmware/firmware.hex";
		$readmemh(firmware_file, ram.mem);
	end

	integer cycle_counter;
```

---
<!-- chunk_id=picorv32_testbench_wb_10 | always @(posedge wb_clk) begin -->

# Verilog Block: `always @(posedge wb_clk) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 150–167

```verilog
always @(posedge wb_clk) begin
		cycle_counter <= !wb_rst ? cycle_counter + 1 : 0;
		if (!wb_rst && trap) begin
`ifndef VERILATOR
			repeat (10) @(posedge wb_clk);
`endif
			$display("TRAP after %1d clock cycles", cycle_counter);
			if (tests_passed) begin
				$display("ALL TESTS PASSED.");
				$finish;
			end else begin
				$display("ERROR!");
				if ($test$plusargs("noerror"))
					$finish;
				$stop;
			end
		end
	end
```

---
<!-- chunk_id=picorv32_testbench_wb_11 | endmodule -->

# Verilog Block: `endmodule`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 168–188

```verilog
endmodule

/* ISC License
 *
 * Verilog on-chip RAM with Wishbone interface
 *
 * Copyright (C) 2014, 2016 Olof Kindgren <olof.kindgren@gmail.com>
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */
```

---
<!-- chunk_id=picorv32_testbench_wb_12 | module wb_ram #( -->

# Verilog Block: `module wb_ram #(`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 189–211

```verilog
module wb_ram #(
	parameter depth = 256,
	parameter memfile = "",
	parameter VERBOSE = 0
) (
	input wb_clk_i,
	input wb_rst_i,

	input [31:0] wb_adr_i,
	input [31:0] wb_dat_i,
	input [3:0] wb_sel_i,
	input wb_we_i,
	input wb_cyc_i,
	input wb_stb_i,

	output reg wb_ack_o,
	output reg [31:0] wb_dat_o,

	input mem_instr,
	output reg tests_passed
);

	reg verbose;
```

---
<!-- chunk_id=picorv32_testbench_wb_13 | initial verbose = $test$plusargs("verbose") || VERBOSE; -->

# Verilog Block: `initial verbose = $test$plusargs("verbose") || VERBOSE;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 212–213

```verilog
initial verbose = $test$plusargs("verbose") || VERBOSE;
```

---
<!-- chunk_id=picorv32_testbench_wb_14 | initial tests_passed = 0; -->

# Verilog Block: `initial tests_passed = 0;`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 214–218

```verilog
initial tests_passed = 0;

	reg [31:0] adr_r;
	wire valid = wb_cyc_i & wb_stb_i;
```

---
<!-- chunk_id=picorv32_testbench_wb_15 | always @(posedge wb_clk_i) begin -->

# Verilog Block: `always @(posedge wb_clk_i) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 219–240

```verilog
always @(posedge wb_clk_i) begin
		adr_r <= wb_adr_i;
		// Ack generation
		wb_ack_o <= valid & !wb_ack_o;
		if (wb_rst_i)
		begin
			adr_r <= {32{1'b0}};
			wb_ack_o <= 1'b0;
		end
	end

	wire ram_we = wb_we_i & valid & wb_ack_o;

	wire [31:0] waddr = adr_r[31:2];
	wire [31:0] raddr = wb_adr_i[31:2];
	wire [3:0] we = {4{ram_we}} & wb_sel_i;

	wire [$clog2(depth/4)-1:0] raddr2 = raddr[$clog2(depth/4)-1:0];
	wire [$clog2(depth/4)-1:0] waddr2 = waddr[$clog2(depth/4)-1:0];

	reg [31:0] mem [0:depth/4-1] /* verilator public */;
```

---
<!-- chunk_id=picorv32_testbench_wb_16 | always @(posedge wb_clk_i) begin -->

# Verilog Block: `always @(posedge wb_clk_i) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 241–265

```verilog
always @(posedge wb_clk_i) begin
		if (ram_we) begin
			if (verbose)
				$display("WR: ADDR=%08x DATA=%08x STRB=%04b",
					adr_r, wb_dat_i, we);

			if (adr_r[31:0] == 32'h1000_0000)
				if (verbose) begin
					if (32 <= wb_dat_i[7:0] && wb_dat_i[7:0] < 128)
						$display("OUT: '%c'", wb_dat_i[7:0]);
					else
						$display("OUT: %3d", wb_dat_i[7:0]);
				end else begin
					$write("%c", wb_dat_i[7:0]);
`ifndef VERILATOR
					$fflush();
`endif
				end
			else
			if (adr_r[31:0] == 32'h2000_0000)
				if (wb_dat_i[31:0] == 123456789)
					tests_passed = 1;
		end
	end
```

---
<!-- chunk_id=picorv32_testbench_wb_17 | always @(posedge wb_clk_i) begin -->

# Verilog Block: `always @(posedge wb_clk_i) begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 266–288

```verilog
always @(posedge wb_clk_i) begin
		if (waddr2 < 128 * 1024 / 4) begin
			if (we[0])
				mem[waddr2][7:0] <= wb_dat_i[7:0];

			if (we[1])
				mem[waddr2][15:8] <= wb_dat_i[15:8];

			if (we[2])
				mem[waddr2][23:16] <= wb_dat_i[23:16];

			if (we[3])
				mem[waddr2][31:24] <= wb_dat_i[31:24];

		end

		if (valid & wb_ack_o & !ram_we)
			if (verbose)
				$display("RD: ADDR=%08x DATA=%08x%s", adr_r, mem[raddr2], mem_instr ? " INSN" : "");

		wb_dat_o <= mem[raddr2];
	end
```

---
<!-- chunk_id=picorv32_testbench_wb_18 | initial begin -->

# Verilog Block: `initial begin`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/testbench_wb.v` | Lines 289–292

```verilog
initial begin
		if (memfile != "")
			$readmemh(memfile, mem);
	end
```

---
<!-- chunk_id=picorv32_tests_LICENSE_0 | picorv32_tests_LICENSE -->

Copyright (c) 2012-2015, The Regents of the University of California (Regents).
All Rights Reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. Neither the name of the Regents nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING
OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS
BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED
HEREUNDER IS PROVIDED "AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE
MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.

---
<!-- chunk_id=picorv32_tests_README_0 | picorv32_tests_README -->

Tests from https://github.com/riscv/riscv-tests/tree/master/isa/rv32ui

---
<!-- chunk_id=picorv32_tests_add_asm | Assembly Test: PICORV32_TESTS_ADD -->

# Assembly Test: `PICORV32_TESTS_ADD`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/add.S`

## Parsed Test Vectors (37 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000002",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0000000a",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff8000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fff8000",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00007fff",
      "0x00000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffffff",
      "0x7fffffff",
      "0x00000000"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80007ffe",
      "0x7fffffff",
      "0x00007fff"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80007fff",
      "0x80000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fff7fff",
      "0x7fffffff",
      "0xffff8000"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x00000000",
      "0xffffffff"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x00000001",
      "0x7fffffff"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "26",
      "13"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "add",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "add",
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "add",
      "26",
      "15",
      "11"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "add",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "add",
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "add",
      "26",
      "15",
      "11"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "add",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "add",
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "add",
      "26",
      "15",
      "11"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "add",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "add",
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "add",
      "26",
      "15",
      "11"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "add",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "add",
      "25",
      "14",
      "11"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "add",
      "26",
      "15",
      "11"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "15",
      "15"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "16",
      "30"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# add.S
#-----------------------------------------------------------------------------
#
# Test add instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  add, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  add, 0x00000002, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  add, 0x0000000a, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  add, 0xffff8000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  add, 0x80000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  add, 0x7fff8000, 0x80000000, 0xffff8000 );

  TEST_RR_OP( 8,  add, 0x00007fff, 0x00000000, 0x00007fff );
  TEST_RR_OP( 9,  add, 0x7fffffff, 0x7fffffff, 0x00000000 );
  TEST_RR_OP( 10, add, 0x80007ffe, 0x7fffffff, 0x00007fff );

  TEST_RR_OP( 11, add, 0x80007fff, 0x80000000, 0x00007fff );
  TEST_RR_OP( 12, add, 0x7fff7fff, 0x7fffffff, 0xffff8000 );

  TEST_RR_OP( 13, add, 0xffffffff, 0x00000000, 0xffffffff );
  TEST_RR_OP( 14, add, 0x00000000, 0xffffffff, 0x00000001 );
  TEST_RR_OP( 15, add, 0xfffffffe, 0xffffffff, 0xffffffff );

  TEST_RR_OP( 16, add, 0x80000000, 0x00000001, 0x7fffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 17, add, 24, 13, 11 );
  TEST_RR_SRC2_EQ_DEST( 18, add, 25, 14, 11 );
  TEST_RR_SRC12_EQ_DEST( 19, add, 26, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 20, 0, add, 24, 13, 11 );
  TEST_RR_DEST_BYPASS( 21, 1, add, 25, 14, 11 );
  TEST_RR_DEST_BYPASS( 22, 2, add, 26, 15, 11 );

  TEST_RR_SRC12_BYPASS( 23, 0, 0, add, 24, 13, 11 );
  TEST_RR_SRC12_BYPASS( 24, 0, 1, add, 25, 14, 11 );
  TEST_RR_SRC12_BYPASS( 25, 0, 2, add, 26, 15, 11 );
  TEST_RR_SRC12_BYPASS( 26, 1, 0, add, 24, 13, 11 );
  TEST_RR_SRC12_BYPASS( 27, 1, 1, add, 25, 14, 11 );
  TEST_RR_SRC12_BYPASS( 28, 2, 0, add, 26, 15, 11 );

  TEST_RR_SRC21_BYPASS( 29, 0, 0, add, 24, 13, 11 );
  TEST_RR_SRC21_BYPASS( 30, 0, 1, add, 25, 14, 11 );
  TEST_RR_SRC21_BYPASS( 31, 0, 2, add, 26, 15, 11 );
  TEST_RR_SRC21_BYPASS( 32, 1, 0, add, 24, 13, 11 );
  TEST_RR_SRC21_BYPASS( 33, 1, 1, add, 25, 14, 11 );
  TEST_RR_SRC21_BYPASS( 34, 2, 0, add, 26, 15, 11 );

  TEST_RR_ZEROSRC1( 35, add, 15, 15 );
  TEST_RR_ZEROSRC2( 36, add, 32, 32 );
  TEST_RR_ZEROSRC12( 37, add, 0 );
  TEST_RR_ZERODEST( 38, add, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_addi_asm | Assembly Test: PICORV32_TESTS_ADDI -->

# Assembly Test: `PICORV32_TESTS_ADDI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/addi.S`

## Parsed Test Vectors (24 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000002",
      "0x00000001",
      "0x001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0000000a",
      "0x00000003",
      "0x007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xfffff800",
      "0x00000000",
      "0x800"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x80000000",
      "0x80000000",
      "0x000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7ffff800",
      "0x80000000",
      "0x800"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x000007ff",
      "0x00000000",
      "0x7ff"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7fffffff",
      "0x7fffffff",
      "0x000"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x800007fe",
      "0x7fffffff",
      "0x7ff"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x800007ff",
      "0x80000000",
      "0x7ff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7ffff7ff",
      "0x7fffffff",
      "0x800"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffffff",
      "0x00000000",
      "0xfff"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0xffffffff",
      "0x001"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "0xfff"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x80000000",
      "0x7fffffff",
      "0x001"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "addi",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "addi",
      "23",
      "13",
      "10"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "addi",
      "22",
      "13",
      "9"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "addi",
      "24",
      "13",
      "11"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "addi",
      "23",
      "13",
      "10"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "addi",
      "22",
      "13",
      "9"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "33",
      "50"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# addi.S
#-----------------------------------------------------------------------------
#
# Test addi instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  addi, 0x00000000, 0x00000000, 0x000 );
  TEST_IMM_OP( 3,  addi, 0x00000002, 0x00000001, 0x001 );
  TEST_IMM_OP( 4,  addi, 0x0000000a, 0x00000003, 0x007 );

  TEST_IMM_OP( 5,  addi, 0xfffff800, 0x00000000, 0x800 );
  TEST_IMM_OP( 6,  addi, 0x80000000, 0x80000000, 0x000 );
  TEST_IMM_OP( 7,  addi, 0x7ffff800, 0x80000000, 0x800 );

  TEST_IMM_OP( 8,  addi, 0x000007ff, 0x00000000, 0x7ff );
  TEST_IMM_OP( 9,  addi, 0x7fffffff, 0x7fffffff, 0x000 );
  TEST_IMM_OP( 10, addi, 0x800007fe, 0x7fffffff, 0x7ff );

  TEST_IMM_OP( 11, addi, 0x800007ff, 0x80000000, 0x7ff );
  TEST_IMM_OP( 12, addi, 0x7ffff7ff, 0x7fffffff, 0x800 );

  TEST_IMM_OP( 13, addi, 0xffffffff, 0x00000000, 0xfff );
  TEST_IMM_OP( 14, addi, 0x00000000, 0xffffffff, 0x001 );
  TEST_IMM_OP( 15, addi, 0xfffffffe, 0xffffffff, 0xfff );

  TEST_IMM_OP( 16, addi, 0x80000000, 0x7fffffff, 0x001 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, addi, 24, 13, 11 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, addi, 24, 13, 11 );
  TEST_IMM_DEST_BYPASS( 19, 1, addi, 23, 13, 10 );
  TEST_IMM_DEST_BYPASS( 20, 2, addi, 22, 13,  9 );

  TEST_IMM_SRC1_BYPASS( 21, 0, addi, 24, 13, 11 );
  TEST_IMM_SRC1_BYPASS( 22, 1, addi, 23, 13, 10 );
  TEST_IMM_SRC1_BYPASS( 23, 2, addi, 22, 13,  9 );

  TEST_IMM_ZEROSRC1( 24, addi, 32, 32 );
  TEST_IMM_ZERODEST( 25, addi, 33, 50 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_and_asm | Assembly Test: PICORV32_TESTS_AND -->

# Assembly Test: `PICORV32_TESTS_AND`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/and.S`

## Parsed Test Vectors (26 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0xf000f000",
      "0xf00ff00f",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0xff00ff00",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "and",
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "and",
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "and",
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "and",
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "and",
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "and",
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "and",
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "and",
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "and",
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "and",
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "and",
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "and",
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "and",
      "0x0f000f00",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "and",
      "0x00f000f0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "and",
      "0x000f000f",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0",
      "0x00ff00ff"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "0x11111111",
      "0x22222222"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# and.S
#-----------------------------------------------------------------------------
#
# Test and instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, and, 0xf000f000, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_EQ_DEST( 8, and, 0xff00ff00, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, and, 0x0f000f00, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, and, 0x00f000f0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, and, 0x000f000f, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, and, 0, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, and, 0, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, and, 0 );
  TEST_RR_ZERODEST( 27, and, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_andi_asm | Assembly Test: PICORV32_TESTS_ANDI -->

# Assembly Test: `PICORV32_TESTS_ANDI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/andi.S`

## Parsed Test Vectors (13 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xff00ff00",
      "0xff00ff00",
      "0xf0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x000000f0",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0000000f",
      "0x00ff00ff",
      "0x70f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0x00000000",
      "0xff00ff00",
      "0x0f0"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "andi",
      "0x00000700",
      "0x0ff00ff0",
      "0x70f"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "andi",
      "0x000000f0",
      "0x00ff00ff",
      "0x0f0"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "andi",
      "0xf00ff00f",
      "0xf00ff00f",
      "0xf0f"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "andi",
      "0x00000700",
      "0x0ff00ff0",
      "0x70f"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "andi",
      "0x000000f0",
      "0x00ff00ff",
      "0x0f0"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "andi",
      "0x0000000f",
      "0xf00ff00f",
      "0x70f"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0",
      "0x0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "0x00ff00ff",
      "0x70f"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# andi.S
#-----------------------------------------------------------------------------
#
# Test andi instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, andi, 0xff00ff00, 0xff00ff00, 0xf0f );
  TEST_IMM_OP( 3, andi, 0x000000f0, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, andi, 0x0000000f, 0x00ff00ff, 0x70f );
  TEST_IMM_OP( 5, andi, 0x00000000, 0xf00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, andi, 0x00000000, 0xff00ff00, 0x0f0 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, andi, 0x00000700, 0x0ff00ff0, 0x70f );
  TEST_IMM_DEST_BYPASS( 8,  1, andi, 0x000000f0, 0x00ff00ff, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 9,  2, andi, 0xf00ff00f, 0xf00ff00f, 0xf0f );

  TEST_IMM_SRC1_BYPASS( 10, 0, andi, 0x00000700, 0x0ff00ff0, 0x70f );
  TEST_IMM_SRC1_BYPASS( 11, 1, andi, 0x000000f0, 0x00ff00ff, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 12, 2, andi, 0x0000000f, 0xf00ff00f, 0x70f );

  TEST_IMM_ZEROSRC1( 13, andi, 0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, andi, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_auipc_asm | Assembly Test: PICORV32_TESTS_AUIPC -->

# Assembly Test: `PICORV32_TESTS_AUIPC`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/auipc.S`

## Parsed Test Vectors (2 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_CASE",
    "args": [
      "10000",
      "\\\n    .align 3; \\\n    lla a0",
      "1f + 10000; \\\n    jal a1",
      "1f; \\\n    1: sub a0",
      "a0",
      "a1; \\"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "args": [
      "-10000",
      "\\\n    .align 3; \\\n    lla a0",
      "1f - 10000; \\\n    jal a1",
      "1f; \\\n    1: sub a0",
      "a0",
      "a1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# auipc.S
#-----------------------------------------------------------------------------
#
# Test auipc instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  TEST_CASE(2, a0, 10000, \
    .align 3; \
    lla a0, 1f + 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

  TEST_CASE(3, a0, -10000, \
    .align 3; \
    lla a0, 1f - 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_beq_asm | Assembly Test: PICORV32_TESTS_BEQ -->

# Assembly Test: `PICORV32_TESTS_BEQ`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/beq.S`

## Parsed Test Vectors (20 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "-1"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0",
      "1"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "0"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-1",
      "1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "beq",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    beq x0",
      "x0",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# beq.S
#-----------------------------------------------------------------------------
#
# Test beq instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, beq,  0,  0 );
  TEST_BR2_OP_TAKEN( 3, beq,  1,  1 );
  TEST_BR2_OP_TAKEN( 4, beq, -1, -1 );

  TEST_BR2_OP_NOTTAKEN( 5, beq,  0,  1 );
  TEST_BR2_OP_NOTTAKEN( 6, beq,  1,  0 );
  TEST_BR2_OP_NOTTAKEN( 7, beq, -1,  1 );
  TEST_BR2_OP_NOTTAKEN( 8, beq,  1, -1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, beq, 0, -1 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, beq, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, beq, 0, -1 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    beq x0, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_bge_asm | Assembly Test: PICORV32_TESTS_BGE -->

# Assembly Test: `PICORV32_TESTS_BGE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/bge.S`

## Parsed Test Vectors (23 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "-1"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "-2"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-1",
      "1"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-2",
      "-1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-2",
      "1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bge",
      "-1",
      "0"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    bge x1",
      "x0",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bge.S
#-----------------------------------------------------------------------------
#
# Test bge instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bge,  0,  0 );
  TEST_BR2_OP_TAKEN( 3, bge,  1,  1 );
  TEST_BR2_OP_TAKEN( 4, bge, -1, -1 );
  TEST_BR2_OP_TAKEN( 5, bge,  1,  0 );
  TEST_BR2_OP_TAKEN( 6, bge,  1, -1 );
  TEST_BR2_OP_TAKEN( 7, bge, -1, -2 );

  TEST_BR2_OP_NOTTAKEN(  8, bge,  0,  1 );
  TEST_BR2_OP_NOTTAKEN(  9, bge, -1,  1 );
  TEST_BR2_OP_NOTTAKEN( 10, bge, -2, -1 );
  TEST_BR2_OP_NOTTAKEN( 11, bge, -2,  1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 12, 0, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 13, 0, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 14, 0, 2, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 15, 1, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 16, 1, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 17, 2, 0, bge, -1, 0 );

  TEST_BR2_SRC12_BYPASS( 18, 0, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 19, 0, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 20, 0, 2, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 21, 1, 0, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 22, 1, 1, bge, -1, 0 );
  TEST_BR2_SRC12_BYPASS( 23, 2, 0, bge, -1, 0 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 24, x1, 3, \
    li  x1, 1; \
    bge x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_bgeu_asm | Assembly Test: PICORV32_TESTS_BGEU -->

# Assembly Test: `PICORV32_TESTS_BGEU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/bgeu.S`

## Parsed Test Vectors (23 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0x00000001",
      "0x00000000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0xffffffff",
      "0xfffffffe"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0xffffffff",
      "0x00000000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0x00000000",
      "0x00000001"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0xfffffffe",
      "0xffffffff"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0x00000000",
      "0xffffffff"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0x7fffffff",
      "0x80000000"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bgeu",
      "0xefffffff",
      "0xf0000000"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    bgeu x1",
      "x0",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bgeu.S
#-----------------------------------------------------------------------------
#
# Test bgeu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bgeu, 0x00000000, 0x00000000 );
  TEST_BR2_OP_TAKEN( 3, bgeu, 0x00000001, 0x00000001 );
  TEST_BR2_OP_TAKEN( 4, bgeu, 0xffffffff, 0xffffffff );
  TEST_BR2_OP_TAKEN( 5, bgeu, 0x00000001, 0x00000000 );
  TEST_BR2_OP_TAKEN( 6, bgeu, 0xffffffff, 0xfffffffe );
  TEST_BR2_OP_TAKEN( 7, bgeu, 0xffffffff, 0x00000000 );

  TEST_BR2_OP_NOTTAKEN(  8, bgeu, 0x00000000, 0x00000001 );
  TEST_BR2_OP_NOTTAKEN(  9, bgeu, 0xfffffffe, 0xffffffff );
  TEST_BR2_OP_NOTTAKEN( 10, bgeu, 0x00000000, 0xffffffff );
  TEST_BR2_OP_NOTTAKEN( 11, bgeu, 0x7fffffff, 0x80000000 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 12, 0, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 13, 0, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 14, 0, 2, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 15, 1, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 16, 1, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 17, 2, 0, bgeu, 0xefffffff, 0xf0000000 );

  TEST_BR2_SRC12_BYPASS( 18, 0, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 19, 0, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 20, 0, 2, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 21, 1, 0, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 22, 1, 1, bgeu, 0xefffffff, 0xf0000000 );
  TEST_BR2_SRC12_BYPASS( 23, 2, 0, bgeu, 0xefffffff, 0xf0000000 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 24, x1, 3, \
    li  x1, 1; \
    bgeu x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_blt_asm | Assembly Test: PICORV32_TESTS_BLT -->

# Assembly Test: `PICORV32_TESTS_BLT`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/blt.S`

## Parsed Test Vectors (20 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0",
      "1"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-2",
      "-1"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-1",
      "-2"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "-2"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "blt",
      "0",
      "-1"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    blt x0",
      "x1",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# blt.S
#-----------------------------------------------------------------------------
#
# Test blt instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, blt,  0,  1 );
  TEST_BR2_OP_TAKEN( 3, blt, -1,  1 );
  TEST_BR2_OP_TAKEN( 4, blt, -2, -1 );

  TEST_BR2_OP_NOTTAKEN( 5, blt,  1,  0 );
  TEST_BR2_OP_NOTTAKEN( 6, blt,  1, -1 );
  TEST_BR2_OP_NOTTAKEN( 7, blt, -1, -2 );
  TEST_BR2_OP_NOTTAKEN( 8, blt,  1, -2 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, blt, 0, -1 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, blt, 0, -1 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, blt, 0, -1 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    blt x0, x1, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_bltu_asm | Assembly Test: PICORV32_TESTS_BLTU -->

# Assembly Test: `PICORV32_TESTS_BLTU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/bltu.S`

## Parsed Test Vectors (20 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0x00000000",
      "0x00000001"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0xfffffffe",
      "0xffffffff"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0x00000000",
      "0xffffffff"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0x00000001",
      "0x00000000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0xffffffff",
      "0xfffffffe"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0xffffffff",
      "0x00000000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0x80000000",
      "0x7fffffff"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bltu",
      "0xf0000000",
      "0xefffffff"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    bltu x0",
      "x1",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bltu.S
#-----------------------------------------------------------------------------
#
# Test bltu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bltu, 0x00000000, 0x00000001 );
  TEST_BR2_OP_TAKEN( 3, bltu, 0xfffffffe, 0xffffffff );
  TEST_BR2_OP_TAKEN( 4, bltu, 0x00000000, 0xffffffff );

  TEST_BR2_OP_NOTTAKEN( 5, bltu, 0x00000001, 0x00000000 );
  TEST_BR2_OP_NOTTAKEN( 6, bltu, 0xffffffff, 0xfffffffe );
  TEST_BR2_OP_NOTTAKEN( 7, bltu, 0xffffffff, 0x00000000 );
  TEST_BR2_OP_NOTTAKEN( 8, bltu, 0x80000000, 0x7fffffff );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, bltu, 0xf0000000, 0xefffffff );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, bltu, 0xf0000000, 0xefffffff );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, bltu, 0xf0000000, 0xefffffff );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    bltu x0, x1, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_bne_asm | Assembly Test: PICORV32_TESTS_BNE -->

# Assembly Test: `PICORV32_TESTS_BNE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/bne.S`

## Parsed Test Vectors (20 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "0",
      "1"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "-1",
      "1"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_BR2_OP_TAKEN",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "0",
      "0"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "1",
      "1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_BR2_OP_NOTTAKEN",
    "args": [
      "-1",
      "-1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "2",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "1",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_BR2_SRC12_BYPASS",
    "args": [
      "0",
      "bne",
      "0",
      "0"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    bne x1",
      "x0",
      "1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# bne.S
#-----------------------------------------------------------------------------
#
# Test bne instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Branch tests
  #-------------------------------------------------------------

  # Each test checks both forward and backward branches

  TEST_BR2_OP_TAKEN( 2, bne,  0,  1 );
  TEST_BR2_OP_TAKEN( 3, bne,  1,  0 );
  TEST_BR2_OP_TAKEN( 4, bne, -1,  1 );
  TEST_BR2_OP_TAKEN( 5, bne,  1, -1 );

  TEST_BR2_OP_NOTTAKEN( 6, bne,  0,  0 );
  TEST_BR2_OP_NOTTAKEN( 7, bne,  1,  1 );
  TEST_BR2_OP_NOTTAKEN( 8, bne, -1, -1 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_BR2_SRC12_BYPASS( 9,  0, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 10, 0, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 11, 0, 2, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 12, 1, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 13, 1, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 14, 2, 0, bne, 0, 0 );

  TEST_BR2_SRC12_BYPASS( 15, 0, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 16, 0, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 17, 0, 2, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 18, 1, 0, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 19, 1, 1, bne, 0, 0 );
  TEST_BR2_SRC12_BYPASS( 20, 2, 0, bne, 0, 0 );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 21, x1, 3, \
    li  x1, 1; \
    bne x1, x0, 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_div_asm | Assembly Test: PICORV32_TESTS_DIV -->

# Assembly Test: `PICORV32_TESTS_DIV`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/div.S`

## Parsed Test Vectors (9 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "3",
      "20",
      "6"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "-3",
      "-20",
      "6"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "-3",
      "20",
      "-6"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "3",
      "-20",
      "-6"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "-1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "-1<<31",
      "0"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "1",
      "0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "0",
      "0"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# div.S
#-----------------------------------------------------------------------------
#
# Test div instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, div,  3,  20,   6 );
  TEST_RR_OP( 3, div, -3, -20,   6 );
  TEST_RR_OP( 4, div, -3,  20,  -6 );
  TEST_RR_OP( 5, div,  3, -20,  -6 );

  TEST_RR_OP( 6, div, -1<<31, -1<<31,  1 );
  TEST_RR_OP( 7, div, -1<<31, -1<<31, -1 );

  TEST_RR_OP( 8, div, -1, -1<<31, 0 );
  TEST_RR_OP( 9, div, -1,      1, 0 );
  TEST_RR_OP(10, div, -1,      0, 0 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_divu_asm | Assembly Test: PICORV32_TESTS_DIVU -->

# Assembly Test: `PICORV32_TESTS_DIVU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/divu.S`

## Parsed Test Vectors (9 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "3",
      "20",
      "6"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "715827879",
      "-20",
      "6"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "20",
      "-6"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "-20",
      "-6"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "-1<<31",
      "-1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "-1<<31",
      "0"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "1",
      "0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "-1",
      "0",
      "0"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# divu.S
#-----------------------------------------------------------------------------
#
# Test divu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, divu,                   3,  20,   6 );
  TEST_RR_OP( 3, divu,           715827879, -20,   6 );
  TEST_RR_OP( 4, divu,                   0,  20,  -6 );
  TEST_RR_OP( 5, divu,                   0, -20,  -6 );

  TEST_RR_OP( 6, divu, -1<<31, -1<<31,  1 );
  TEST_RR_OP( 7, divu,     0,  -1<<31, -1 );

  TEST_RR_OP( 8, divu, -1, -1<<31, 0 );
  TEST_RR_OP( 9, divu, -1,      1, 0 );
  TEST_RR_OP(10, divu, -1,      0, 0 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_j_asm | Assembly Test: PICORV32_TESTS_J -->

# Assembly Test: `PICORV32_TESTS_J`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/j.S`

## Parsed Test Vectors (1 total)

```json
[
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x1",
      "1; \\\n    j 1f; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# j.S
#-----------------------------------------------------------------------------
#
# Test j instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Test basic
  #-------------------------------------------------------------

  li  TESTNUM, 2;
  j test_2;
  j fail;
test_2:

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 3, x1, 3, \
    li  x1, 1; \
    j 1f; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_jal_asm | Assembly Test: PICORV32_TESTS_JAL -->

# Assembly Test: `PICORV32_TESTS_JAL`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/jal.S`

## Parsed Test Vectors (1 total)

```json
[
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "args": [
      "3",
      "\\\n    li  x2",
      "1; \\\n    jal 1f; \\\n    addi x2",
      "x2",
      "1; \\\n    addi x2",
      "x2",
      "1; \\\n    addi x2",
      "x2",
      "1; \\\n    addi x2",
      "x2",
      "1; \\\n1:  addi x2",
      "x2",
      "1; \\\n    addi x2",
      "x2",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# jal.S
#-----------------------------------------------------------------------------
#
# Test jal instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

.option norvc

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Test 2: Basic test
  #-------------------------------------------------------------

test_2:
  li  TESTNUM, 2
  li  ra, 0

linkaddr_2:
  jal target_2
  nop
  nop

  j fail

target_2:
  la  x2, linkaddr_2
  addi x2, x2, 4
  bne x2, ra, fail

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 3, x2, 3, \
    li  x2, 1; \
    jal 1f; \
    addi x2, x2, 1; \
    addi x2, x2, 1; \
    addi x2, x2, 1; \
    addi x2, x2, 1; \
1:  addi x2, x2, 1; \
    addi x2, x2, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_jalr_asm | Assembly Test: PICORV32_TESTS_JALR -->

# Assembly Test: `PICORV32_TESTS_JALR`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/jalr.S`

## Parsed Test Vectors (4 total)

```json
[
  {
    "test_id": 4,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "args": [
      "jalr"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "args": [
      "jalr"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_JALR_SRC1_BYPASS",
    "args": [
      "jalr"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_CASE",
    "args": [
      "4",
      "\\\n    li  x1",
      "1; \\\n    la  x2",
      "1f;\n    jalr x19",
      "x2",
      "-4; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\\n1:  addi x1",
      "x1",
      "1; \\\n    addi x1",
      "x1",
      "1; \\"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# jalr.S
#-----------------------------------------------------------------------------
#
# Test jalr instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

.option norvc

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Test 2: Basic test
  #-------------------------------------------------------------

test_2:
  li  TESTNUM, 2
  li  x31, 0
  la  x2, target_2

linkaddr_2:
  jalr x19, x2, 0
  nop
  nop

  j fail

target_2:
  la  x1, linkaddr_2
  addi x1, x1, 4
  bne x1, x19, fail

  #-------------------------------------------------------------
  # Test 3: Check r0 target and that r31 is not modified
  #-------------------------------------------------------------

test_3:
  li  TESTNUM, 3
  li  x31, 0
  la  x3, target_3

linkaddr_3:
  jalr x0, x3, 0
  nop

  j fail

target_3:
  bne x31, x0, fail

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_JALR_SRC1_BYPASS( 4, 0, jalr );
  TEST_JALR_SRC1_BYPASS( 5, 1, jalr );
  TEST_JALR_SRC1_BYPASS( 6, 2, jalr );

  #-------------------------------------------------------------
  # Test delay slot instructions not executed nor bypassed
  #-------------------------------------------------------------

  TEST_CASE( 7, x1, 4, \
    li  x1, 1; \
    la  x2, 1f;
    jalr x19, x2, -4; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
    addi x1, x1, 1; \
1:  addi x1, x1, 1; \
    addi x1, x1, 1; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lb_asm | Assembly Test: PICORV32_TESTS_LB -->

# Assembly Test: `PICORV32_TESTS_LB`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lb.S`

## Parsed Test Vectors (18 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "args": [
      "0xffffffff",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000000",
      "1",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "args": [
      "0xfffffff0",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000000f",
      "3",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "args": [
      "0xffffffff",
      "-3",
      "tdat4"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000000",
      "-2",
      "tdat4"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "args": [
      "0xfffffff0",
      "-1",
      "tdat4"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000000f",
      "0",
      "tdat4"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0xffffffff",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-32; \\\n    lb x3",
      "32(x1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0x00000000",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-6; \\\n    lb x3",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lb",
      "0xfffffff0",
      "1",
      "tdat2"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lb",
      "0x0000000f",
      "1",
      "tdat3"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lb",
      "0x00000000",
      "1",
      "tdat1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lb",
      "0xfffffff0",
      "1",
      "tdat2"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lb",
      "0x0000000f",
      "1",
      "tdat3"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lb",
      "0x00000000",
      "1",
      "tdat1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lb  x2",
      "0(x3"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lb  x2",
      "0(x3"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lb.S
#-----------------------------------------------------------------------------
#
# Test lb instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lb, 0xffffffff, 0,  tdat );
  TEST_LD_OP( 3, lb, 0x00000000, 1,  tdat );
  TEST_LD_OP( 4, lb, 0xfffffff0, 2,  tdat );
  TEST_LD_OP( 5, lb, 0x0000000f, 3, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lb, 0xffffffff, -3, tdat4 );
  TEST_LD_OP( 7, lb, 0x00000000, -2,  tdat4 );
  TEST_LD_OP( 8, lb, 0xfffffff0, -1,  tdat4 );
  TEST_LD_OP( 9, lb, 0x0000000f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0xffffffff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lb x3, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0x00000000, \
    la  x1, tdat; \
    addi x1, x1, -6; \
    lb x3, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lb, 0xfffffff0, 1, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lb, 0x0000000f, 1, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lb, 0x00000000, 1, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lb, 0xfffffff0, 1, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lb, 0x0000000f, 1, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lb, 0x00000000, 1, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x3, tdat; \
    lb  x2, 0(x3); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x3, tdat; \
    lb  x2, 0(x3); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xff
tdat2:  .byte 0x00
tdat3:  .byte 0xf0
tdat4:  .byte 0x0f

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lbu_asm | Assembly Test: PICORV32_TESTS_LBU -->

# Assembly Test: `PICORV32_TESTS_LBU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lbu.S`

## Parsed Test Vectors (18 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000000",
      "1",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000f0",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000000f",
      "3",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "-3",
      "tdat4"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000000",
      "-2",
      "tdat4"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000f0",
      "-1",
      "tdat4"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000000f",
      "0",
      "tdat4"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x000000ff",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-32; \\\n    lbu x3",
      "32(x1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0x00000000",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-6; \\\n    lbu x3",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lbu",
      "0x000000f0",
      "1",
      "tdat2"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lbu",
      "0x0000000f",
      "1",
      "tdat3"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lbu",
      "0x00000000",
      "1",
      "tdat1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lbu",
      "0x000000f0",
      "1",
      "tdat2"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lbu",
      "0x0000000f",
      "1",
      "tdat3"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lbu",
      "0x00000000",
      "1",
      "tdat1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lbu  x2",
      "0(x3"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lbu  x2",
      "0(x3"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lbu.S
#-----------------------------------------------------------------------------
#
# Test lbu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lbu, 0x000000ff, 0,  tdat );
  TEST_LD_OP( 3, lbu, 0x00000000, 1,  tdat );
  TEST_LD_OP( 4, lbu, 0x000000f0, 2,  tdat );
  TEST_LD_OP( 5, lbu, 0x0000000f, 3, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lbu, 0x000000ff, -3, tdat4 );
  TEST_LD_OP( 7, lbu, 0x00000000, -2,  tdat4 );
  TEST_LD_OP( 8, lbu, 0x000000f0, -1,  tdat4 );
  TEST_LD_OP( 9, lbu, 0x0000000f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lbu x3, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0x00000000, \
    la  x1, tdat; \
    addi x1, x1, -6; \
    lbu x3, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lbu, 0x000000f0, 1, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lbu, 0x0000000f, 1, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lbu, 0x00000000, 1, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lbu, 0x000000f0, 1, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lbu, 0x0000000f, 1, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lbu, 0x00000000, 1, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x3, tdat; \
    lbu  x2, 0(x3); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x3, tdat; \
    lbu  x2, 0(x3); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xff
tdat2:  .byte 0x00
tdat3:  .byte 0xf0
tdat4:  .byte 0x0f

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lh_asm | Assembly Test: PICORV32_TESTS_LH -->

# Assembly Test: `PICORV32_TESTS_LH`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lh.S`

## Parsed Test Vectors (18 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "args": [
      "0xffffff00",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000ff0",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "args": [
      "0xfffff00f",
      "6",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "-6",
      "tdat4"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "args": [
      "0xffffff00",
      "-4",
      "tdat4"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000ff0",
      "-2",
      "tdat4"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "args": [
      "0xfffff00f",
      "0",
      "tdat4"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x000000ff",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-32; \\\n    lh x3",
      "32(x1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0xffffff00",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-5; \\\n    lh x3",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lh",
      "0x00000ff0",
      "2",
      "tdat2"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lh",
      "0xfffff00f",
      "2",
      "tdat3"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lh",
      "0xffffff00",
      "2",
      "tdat1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lh",
      "0x00000ff0",
      "2",
      "tdat2"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lh",
      "0xfffff00f",
      "2",
      "tdat3"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lh",
      "0xffffff00",
      "2",
      "tdat1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lh  x2",
      "0(x3"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lh  x2",
      "0(x3"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lh.S
#-----------------------------------------------------------------------------
#
# Test lh instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lh, 0x000000ff, 0,  tdat );
  TEST_LD_OP( 3, lh, 0xffffff00, 2,  tdat );
  TEST_LD_OP( 4, lh, 0x00000ff0, 4,  tdat );
  TEST_LD_OP( 5, lh, 0xfffff00f, 6, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lh, 0x000000ff, -6,  tdat4 );
  TEST_LD_OP( 7, lh, 0xffffff00, -4,  tdat4 );
  TEST_LD_OP( 8, lh, 0x00000ff0, -2,  tdat4 );
  TEST_LD_OP( 9, lh, 0xfffff00f,  0, tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lh x3, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0xffffff00, \
    la  x1, tdat; \
    addi x1, x1, -5; \
    lh x3, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lh, 0x00000ff0, 2, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lh, 0xfffff00f, 2, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lh, 0xffffff00, 2, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lh, 0x00000ff0, 2, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lh, 0xfffff00f, 2, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lh, 0xffffff00, 2, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x3, tdat; \
    lh  x2, 0(x3); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x3, tdat; \
    lh  x2, 0(x3); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0x00ff
tdat2:  .half 0xff00
tdat3:  .half 0x0ff0
tdat4:  .half 0xf00f

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lhu_asm | Assembly Test: PICORV32_TESTS_LHU -->

# Assembly Test: `PICORV32_TESTS_LHU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lhu.S`

## Parsed Test Vectors (18 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000ff00",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000ff0",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000f00f",
      "6",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "args": [
      "0x000000ff",
      "-6",
      "tdat4"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000ff00",
      "-4",
      "tdat4"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00000ff0",
      "-2",
      "tdat4"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0000f00f",
      "0",
      "tdat4"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x000000ff",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-32; \\\n    lhu x3",
      "32(x1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0x0000ff00",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-5; \\\n    lhu x3",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lhu",
      "0x00000ff0",
      "2",
      "tdat2"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lhu",
      "0x0000f00f",
      "2",
      "tdat3"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lhu",
      "0x0000ff00",
      "2",
      "tdat1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lhu",
      "0x00000ff0",
      "2",
      "tdat2"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lhu",
      "0x0000f00f",
      "2",
      "tdat3"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lhu",
      "0x0000ff00",
      "2",
      "tdat1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lhu  x2",
      "0(x3"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lhu  x2",
      "0(x3"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lhu.S
#-----------------------------------------------------------------------------
#
# Test lhu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lhu, 0x000000ff, 0,  tdat );
  TEST_LD_OP( 3, lhu, 0x0000ff00, 2,  tdat );
  TEST_LD_OP( 4, lhu, 0x00000ff0, 4,  tdat );
  TEST_LD_OP( 5, lhu, 0x0000f00f, 6, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lhu, 0x000000ff, -6,  tdat4 );
  TEST_LD_OP( 7, lhu, 0x0000ff00, -4,  tdat4 );
  TEST_LD_OP( 8, lhu, 0x00000ff0, -2,  tdat4 );
  TEST_LD_OP( 9, lhu, 0x0000f00f,  0, tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x000000ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lhu x3, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0x0000ff00, \
    la  x1, tdat; \
    addi x1, x1, -5; \
    lhu x3, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lhu, 0x00000ff0, 2, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lhu, 0x0000f00f, 2, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lhu, 0x0000ff00, 2, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lhu, 0x00000ff0, 2, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lhu, 0x0000f00f, 2, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lhu, 0x0000ff00, 2, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x3, tdat; \
    lhu  x2, 0(x3); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x3, tdat; \
    lhu  x2, 0(x3); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0x00ff
tdat2:  .half 0xff00
tdat3:  .half 0x0ff0
tdat4:  .half 0xf00f

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lui_asm | Assembly Test: PICORV32_TESTS_LUI -->

# Assembly Test: `PICORV32_TESTS_LUI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lui.S`

## Parsed Test Vectors (5 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_CASE",
    "args": [
      "0x00000000",
      "lui x1",
      "0x00000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_CASE",
    "args": [
      "0xfffff800",
      "lui x1",
      "0xfffff;sra x1",
      "x1",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_CASE",
    "args": [
      "0x000007ff",
      "lui x1",
      "0x7ffff;sra x1",
      "x1",
      "20"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_CASE",
    "args": [
      "0xfffff800",
      "lui x1",
      "0x80000;sra x1",
      "x1",
      "20"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_CASE",
    "args": [
      "0",
      "lui x0",
      "0x80000"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lui.S
#-----------------------------------------------------------------------------
#
# Test lui instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_CASE( 2, x1, 0x00000000, lui x1, 0x00000 );
  TEST_CASE( 3, x1, 0xfffff800, lui x1, 0xfffff;sra x1,x1,1);
  TEST_CASE( 4, x1, 0x000007ff, lui x1, 0x7ffff;sra x1,x1,20);
  TEST_CASE( 5, x1, 0xfffff800, lui x1, 0x80000;sra x1,x1,20);

  TEST_CASE( 6, x0, 0, lui x0, 0x80000 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_lw_asm | Assembly Test: PICORV32_TESTS_LW -->

# Assembly Test: `PICORV32_TESTS_LW`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/lw.S`

## Parsed Test Vectors (18 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00ff00ff",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_LD_OP",
    "args": [
      "0xff00ff00",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0ff00ff0",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_LD_OP",
    "args": [
      "0xf00ff00f",
      "12",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_LD_OP",
    "args": [
      "0x00ff00ff",
      "-12",
      "tdat4"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_LD_OP",
    "args": [
      "0xff00ff00",
      "-8",
      "tdat4"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_LD_OP",
    "args": [
      "0x0ff00ff0",
      "-4",
      "tdat4"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_LD_OP",
    "args": [
      "0xf00ff00f",
      "0",
      "tdat4"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x00ff00ff",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-32; \\\n    lw x3",
      "32(x1"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0xff00ff00",
      "\\\n    la  x1",
      "tdat; \\\n    addi x1",
      "x1",
      "-3; \\\n    lw x3",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lw",
      "0x0ff00ff0",
      "4",
      "tdat2"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lw",
      "0xf00ff00f",
      "4",
      "tdat3"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_LD_DEST_BYPASS",
    "args": [
      "lw",
      "0xff00ff00",
      "4",
      "tdat1"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lw",
      "0x0ff00ff0",
      "4",
      "tdat2"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lw",
      "0xf00ff00f",
      "4",
      "tdat3"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_LD_SRC1_BYPASS",
    "args": [
      "lw",
      "0xff00ff00",
      "4",
      "tdat1"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lw  x2",
      "0(x3"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_CASE",
    "args": [
      "2",
      "\\\n    la  x3",
      "tdat; \\\n    lw  x2",
      "0(x3"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# lw.S
#-----------------------------------------------------------------------------
#
# Test lw instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_LD_OP( 2, lw, 0x00ff00ff, 0,  tdat );
  TEST_LD_OP( 3, lw, 0xff00ff00, 4,  tdat );
  TEST_LD_OP( 4, lw, 0x0ff00ff0, 8,  tdat );
  TEST_LD_OP( 5, lw, 0xf00ff00f, 12, tdat );

  # Test with negative offset

  TEST_LD_OP( 6, lw, 0x00ff00ff, -12, tdat4 );
  TEST_LD_OP( 7, lw, 0xff00ff00, -8,  tdat4 );
  TEST_LD_OP( 8, lw, 0x0ff00ff0, -4,  tdat4 );
  TEST_LD_OP( 9, lw, 0xf00ff00f, 0,   tdat4 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x00ff00ff, \
    la  x1, tdat; \
    addi x1, x1, -32; \
    lw x3, 32(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0xff00ff00, \
    la  x1, tdat; \
    addi x1, x1, -3; \
    lw x3, 7(x1); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_LD_DEST_BYPASS( 12, 0, lw, 0x0ff00ff0, 4, tdat2 );
  TEST_LD_DEST_BYPASS( 13, 1, lw, 0xf00ff00f, 4, tdat3 );
  TEST_LD_DEST_BYPASS( 14, 2, lw, 0xff00ff00, 4, tdat1 );

  TEST_LD_SRC1_BYPASS( 15, 0, lw, 0x0ff00ff0, 4, tdat2 );
  TEST_LD_SRC1_BYPASS( 16, 1, lw, 0xf00ff00f, 4, tdat3 );
  TEST_LD_SRC1_BYPASS( 17, 2, lw, 0xff00ff00, 4, tdat1 );

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  TEST_CASE( 18, x2, 2, \
    la  x3, tdat; \
    lw  x2, 0(x3); \
    li  x2, 2; \
  )

  TEST_CASE( 19, x2, 2, \
    la  x3, tdat; \
    lw  x2, 0(x3); \
    nop; \
    li  x2, 2; \
  )

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .word 0x00ff00ff
tdat2:  .word 0xff00ff00
tdat3:  .word 0x0ff00ff0
tdat4:  .word 0xf00ff00f

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_mul_asm | Assembly Test: PICORV32_TESTS_MUL -->

# Assembly Test: `PICORV32_TESTS_MUL`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/mul.S`

## Parsed Test Vectors (36 total)

```json
[
  {
    "test_id": 32,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00001200",
      "0x00007e00",
      "0xb6db6db7"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00001240",
      "0x00007fc0",
      "0xb6db6db7"
    ]
  },
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000001",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000015",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0000ff7f",
      "0xaaaaaaab",
      "0x0002fe7d"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0000ff7f",
      "0x0002fe7d",
      "0xaaaaaaab"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0xff000000",
      "0xff000000"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000001",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x00000001",
      "0xffffffff"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "169",
      "13"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mul",
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mul",
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mul",
      "165",
      "15",
      "11"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mul",
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mul",
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "mul",
      "165",
      "15",
      "11"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mul",
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mul",
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mul",
      "165",
      "15",
      "11"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mul",
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mul",
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "mul",
      "165",
      "15",
      "11"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mul",
      "143",
      "13",
      "11"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mul",
      "154",
      "14",
      "11"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mul",
      "165",
      "15",
      "11"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "31"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0",
      "32"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "33",
      "34"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# mul.S
#-----------------------------------------------------------------------------
#
# Test mul instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP(32,  mul, 0x00001200, 0x00007e00, 0xb6db6db7 );
  TEST_RR_OP(33,  mul, 0x00001240, 0x00007fc0, 0xb6db6db7 );

  TEST_RR_OP( 2,  mul, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  mul, 0x00000001, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  mul, 0x00000015, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  mul, 0x00000000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  mul, 0x00000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  mul, 0x00000000, 0x80000000, 0xffff8000 );

  TEST_RR_OP(30,  mul, 0x0000ff7f, 0xaaaaaaab, 0x0002fe7d );
  TEST_RR_OP(31,  mul, 0x0000ff7f, 0x0002fe7d, 0xaaaaaaab );

  TEST_RR_OP(34,  mul, 0x00000000, 0xff000000, 0xff000000 );

  TEST_RR_OP(35,  mul, 0x00000001, 0xffffffff, 0xffffffff );
  TEST_RR_OP(36,  mul, 0xffffffff, 0xffffffff, 0x00000001 );
  TEST_RR_OP(37,  mul, 0xffffffff, 0x00000001, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 8, mul, 143, 13, 11 );
  TEST_RR_SRC2_EQ_DEST( 9, mul, 154, 14, 11 );
  TEST_RR_SRC12_EQ_DEST( 10, mul, 169, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 11, 0, mul, 143, 13, 11 );
  TEST_RR_DEST_BYPASS( 12, 1, mul, 154, 14, 11 );
  TEST_RR_DEST_BYPASS( 13, 2, mul, 165, 15, 11 );

  TEST_RR_SRC12_BYPASS( 14, 0, 0, mul, 143, 13, 11 );
  TEST_RR_SRC12_BYPASS( 15, 0, 1, mul, 154, 14, 11 );
  TEST_RR_SRC12_BYPASS( 16, 0, 2, mul, 165, 15, 11 );
  TEST_RR_SRC12_BYPASS( 17, 1, 0, mul, 143, 13, 11 );
  TEST_RR_SRC12_BYPASS( 18, 1, 1, mul, 154, 14, 11 );
  TEST_RR_SRC12_BYPASS( 19, 2, 0, mul, 165, 15, 11 );

  TEST_RR_SRC21_BYPASS( 20, 0, 0, mul, 143, 13, 11 );
  TEST_RR_SRC21_BYPASS( 21, 0, 1, mul, 154, 14, 11 );
  TEST_RR_SRC21_BYPASS( 22, 0, 2, mul, 165, 15, 11 );
  TEST_RR_SRC21_BYPASS( 23, 1, 0, mul, 143, 13, 11 );
  TEST_RR_SRC21_BYPASS( 24, 1, 1, mul, 154, 14, 11 );
  TEST_RR_SRC21_BYPASS( 25, 2, 0, mul, 165, 15, 11 );

  TEST_RR_ZEROSRC1( 26, mul, 0, 31 );
  TEST_RR_ZEROSRC2( 27, mul, 0, 32 );
  TEST_RR_ZEROSRC12( 28, mul, 0 );
  TEST_RR_ZERODEST( 29, mul, 33, 34 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_mulh_asm | Assembly Test: PICORV32_TESTS_MULH -->

# Assembly Test: `PICORV32_TESTS_MULH`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/mulh.S`

## Parsed Test Vectors (34 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff0081",
      "0xaaaaaaab",
      "0x0002fe7d"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff0081",
      "0x0002fe7d",
      "0xaaaaaaab"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00010000",
      "0xff000000",
      "0xff000000"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x00000001",
      "0xffffffff"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "43264",
      "13<<20"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulh",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulh",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulh",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulh",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulh",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "mulh",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulh",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulh",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulh",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulh",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulh",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "mulh",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulh",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulh",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulh",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "31<<26"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0",
      "32<<26"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "33<<20",
      "34<<20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# mulh.S
#-----------------------------------------------------------------------------
#
# Test mulh instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  mulh, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  mulh, 0x00000000, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  mulh, 0x00000000, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  mulh, 0x00000000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  mulh, 0x00000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  mulh, 0x00000000, 0x80000000, 0x00000000 );

  TEST_RR_OP(30,  mulh, 0xffff0081, 0xaaaaaaab, 0x0002fe7d );
  TEST_RR_OP(31,  mulh, 0xffff0081, 0x0002fe7d, 0xaaaaaaab );

  TEST_RR_OP(32,  mulh, 0x00010000, 0xff000000, 0xff000000 );

  TEST_RR_OP(33,  mulh, 0x00000000, 0xffffffff, 0xffffffff );
  TEST_RR_OP(34,  mulh, 0xffffffff, 0xffffffff, 0x00000001 );
  TEST_RR_OP(35,  mulh, 0xffffffff, 0x00000001, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 8, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC2_EQ_DEST( 9, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_EQ_DEST( 10, mulh, 43264, 13<<20 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 11, 0, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 12, 1, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 13, 2, mulh, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC12_BYPASS( 14, 0, 0, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 15, 0, 1, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 16, 0, 2, mulh, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 17, 1, 0, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 18, 1, 1, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 19, 2, 0, mulh, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC21_BYPASS( 20, 0, 0, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 21, 0, 1, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 22, 0, 2, mulh, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 23, 1, 0, mulh, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 24, 1, 1, mulh, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 25, 2, 0, mulh, 42240, 15<<20, 11<<20 );

  TEST_RR_ZEROSRC1( 26, mulh, 0, 31<<26 );
  TEST_RR_ZEROSRC2( 27, mulh, 0, 32<<26 );
  TEST_RR_ZEROSRC12( 28, mulh, 0 );
  TEST_RR_ZERODEST( 29, mulh, 33<<20, 34<<20 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_mulhsu_asm | Assembly Test: PICORV32_TESTS_MULHSU -->

# Assembly Test: `PICORV32_TESTS_MULHSU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/mulhsu.S`

## Parsed Test Vectors (34 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80004000",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff0081",
      "0xaaaaaaab",
      "0x0002fe7d"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0001fefe",
      "0x0002fe7d",
      "0xaaaaaaab"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff010000",
      "0xff000000",
      "0xff000000"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0xffffffff"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "43264",
      "13<<20"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhsu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhsu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhsu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulhsu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "mulhsu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulhsu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulhsu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "mulhsu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulhsu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhsu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "31<<26"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0",
      "32<<26"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "33<<20",
      "34<<20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# mulhsu.S
#-----------------------------------------------------------------------------
#
# Test mulhsu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  mulhsu, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  mulhsu, 0x00000000, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  mulhsu, 0x00000000, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  mulhsu, 0x00000000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  mulhsu, 0x00000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  mulhsu, 0x80004000, 0x80000000, 0xffff8000 );

  TEST_RR_OP(30,  mulhsu, 0xffff0081, 0xaaaaaaab, 0x0002fe7d );
  TEST_RR_OP(31,  mulhsu, 0x0001fefe, 0x0002fe7d, 0xaaaaaaab );

  TEST_RR_OP(32,  mulhsu, 0xff010000, 0xff000000, 0xff000000 );

  TEST_RR_OP(33,  mulhsu, 0xffffffff, 0xffffffff, 0xffffffff );
  TEST_RR_OP(34,  mulhsu, 0xffffffff, 0xffffffff, 0x00000001 );
  TEST_RR_OP(35,  mulhsu, 0x00000000, 0x00000001, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 8, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC2_EQ_DEST( 9, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_EQ_DEST( 10, mulhsu, 43264, 13<<20 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 11, 0, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 12, 1, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 13, 2, mulhsu, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC12_BYPASS( 14, 0, 0, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 15, 0, 1, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 16, 0, 2, mulhsu, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 17, 1, 0, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 18, 1, 1, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 19, 2, 0, mulhsu, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC21_BYPASS( 20, 0, 0, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 21, 0, 1, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 22, 0, 2, mulhsu, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 23, 1, 0, mulhsu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 24, 1, 1, mulhsu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 25, 2, 0, mulhsu, 42240, 15<<20, 11<<20 );

  TEST_RR_ZEROSRC1( 26, mulhsu, 0, 31<<26 );
  TEST_RR_ZEROSRC2( 27, mulhsu, 0, 32<<26 );
  TEST_RR_ZEROSRC12( 28, mulhsu, 0 );
  TEST_RR_ZERODEST( 29, mulhsu, 33<<20, 34<<20 );



  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_mulhu_asm | Assembly Test: PICORV32_TESTS_MULHU -->

# Assembly Test: `PICORV32_TESTS_MULHU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/mulhu.S`

## Parsed Test Vectors (34 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffc000",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0001fefe",
      "0xaaaaaaab",
      "0x0002fe7d"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0001fefe",
      "0x0002fe7d",
      "0xaaaaaaab"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfe010000",
      "0xff000000",
      "0xff000000"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0xffffffff"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "43264",
      "13<<20"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "mulhu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulhu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "mulhu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "mulhu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "mulhu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulhu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "mulhu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhu",
      "36608",
      "13<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "mulhu",
      "39424",
      "14<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "mulhu",
      "42240",
      "15<<20",
      "11<<20"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "31<<26"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0",
      "32<<26"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "33<<20",
      "34<<20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# mulhu.S
#-----------------------------------------------------------------------------
#
# Test mulhu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  mulhu, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  mulhu, 0x00000000, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  mulhu, 0x00000000, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  mulhu, 0x00000000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  mulhu, 0x00000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  mulhu, 0x7fffc000, 0x80000000, 0xffff8000 );

  TEST_RR_OP(30,  mulhu, 0x0001fefe, 0xaaaaaaab, 0x0002fe7d );
  TEST_RR_OP(31,  mulhu, 0x0001fefe, 0x0002fe7d, 0xaaaaaaab );

  TEST_RR_OP(32,  mulhu, 0xfe010000, 0xff000000, 0xff000000 );

  TEST_RR_OP(33,  mulhu, 0xfffffffe, 0xffffffff, 0xffffffff );
  TEST_RR_OP(34,  mulhu, 0x00000000, 0xffffffff, 0x00000001 );
  TEST_RR_OP(35,  mulhu, 0x00000000, 0x00000001, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 8, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC2_EQ_DEST( 9, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_EQ_DEST( 10, mulhu, 43264, 13<<20 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 11, 0, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 12, 1, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_DEST_BYPASS( 13, 2, mulhu, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC12_BYPASS( 14, 0, 0, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 15, 0, 1, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 16, 0, 2, mulhu, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 17, 1, 0, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 18, 1, 1, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC12_BYPASS( 19, 2, 0, mulhu, 42240, 15<<20, 11<<20 );

  TEST_RR_SRC21_BYPASS( 20, 0, 0, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 21, 0, 1, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 22, 0, 2, mulhu, 42240, 15<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 23, 1, 0, mulhu, 36608, 13<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 24, 1, 1, mulhu, 39424, 14<<20, 11<<20 );
  TEST_RR_SRC21_BYPASS( 25, 2, 0, mulhu, 42240, 15<<20, 11<<20 );

  TEST_RR_ZEROSRC1( 26, mulhu, 0, 31<<26 );
  TEST_RR_ZEROSRC2( 27, mulhu, 0, 32<<26 );
  TEST_RR_ZEROSRC12( 28, mulhu, 0 );
  TEST_RR_ZERODEST( 29, mulhu, 33<<20, 34<<20 );


  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_or_asm | Assembly Test: PICORV32_TESTS_OR -->

# Assembly Test: `PICORV32_TESTS_OR`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/or.S`

## Parsed Test Vectors (26 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0xf0fff0ff",
      "0xf00ff00f",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0xff00ff00",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "or",
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "or",
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "or",
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "or",
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "or",
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "or",
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "or",
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "or",
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "or",
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "or",
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "or",
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "or",
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "or",
      "0xff0fff0f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "or",
      "0xfff0fff0",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "or",
      "0x0fff0fff",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0xff00ff00",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0x00ff00ff",
      "0x00ff00ff"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "0x11111111",
      "0x22222222"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# or.S
#-----------------------------------------------------------------------------
#
# Test or instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, or, 0xf0fff0ff, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_EQ_DEST( 8, or, 0xff00ff00, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, or, 0xff0fff0f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, or, 0xfff0fff0, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, or, 0x0fff0fff, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, or, 0xff00ff00, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, or, 0x00ff00ff, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, or, 0 );
  TEST_RR_ZERODEST( 27, or, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_ori_asm | Assembly Test: PICORV32_TESTS_ORI -->

# Assembly Test: `PICORV32_TESTS_ORI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/ori.S`

## Parsed Test Vectors (13 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffff0f",
      "0xff00ff00",
      "0xf0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0ff00ff0",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00ff07ff",
      "0x00ff00ff",
      "0x70f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0xff00fff0",
      "0xff00ff00",
      "0x0f0"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "ori",
      "0x0ff00ff0",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "ori",
      "0x00ff07ff",
      "0x00ff00ff",
      "0x70f"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "ori",
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "ori",
      "0x0ff00ff0",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "ori",
      "0xffffffff",
      "0x00ff00ff",
      "0xf0f"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "ori",
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0x0f0",
      "0x0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "0x00ff00ff",
      "0x70f"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# ori.S
#-----------------------------------------------------------------------------
#
# Test ori instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, ori, 0xffffff0f, 0xff00ff00, 0xf0f );
  TEST_IMM_OP( 3, ori, 0x0ff00ff0, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, ori, 0x00ff07ff, 0x00ff00ff, 0x70f );
  TEST_IMM_OP( 5, ori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, ori, 0xff00fff0, 0xff00ff00, 0x0f0 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, ori, 0x0ff00ff0, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 8,  1, ori, 0x00ff07ff, 0x00ff00ff, 0x70f );
  TEST_IMM_DEST_BYPASS( 9,  2, ori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  TEST_IMM_SRC1_BYPASS( 10, 0, ori, 0x0ff00ff0, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 11, 1, ori, 0xffffffff, 0x00ff00ff, 0xf0f );
  TEST_IMM_SRC1_BYPASS( 12, 2, ori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  TEST_IMM_ZEROSRC1( 13, ori, 0x0f0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, ori, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_rem_asm | Assembly Test: PICORV32_TESTS_REM -->

# Assembly Test: `PICORV32_TESTS_REM`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/rem.S`

## Parsed Test Vectors (9 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "2",
      "20",
      "6"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "-2",
      "-20",
      "6"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "2",
      "20",
      "-6"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "-2",
      "-20",
      "-6"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "-1<<31",
      "1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "-1<<31",
      "-1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "0"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "1",
      "0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0",
      "0"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# rem.S
#-----------------------------------------------------------------------------
#
# Test rem instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, rem,  2,  20,   6 );
  TEST_RR_OP( 3, rem, -2, -20,   6 );
  TEST_RR_OP( 4, rem,  2,  20,  -6 );
  TEST_RR_OP( 5, rem, -2, -20,  -6 );

  TEST_RR_OP( 6, rem,  0, -1<<31,  1 );
  TEST_RR_OP( 7, rem,  0, -1<<31, -1 );

  TEST_RR_OP( 8, rem, -1<<31, -1<<31, 0 );
  TEST_RR_OP( 9, rem,      1,      1, 0 );
  TEST_RR_OP(10, rem,      0,      0, 0 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_remu_asm | Assembly Test: PICORV32_TESTS_REMU -->

# Assembly Test: `PICORV32_TESTS_REMU`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/remu.S`

## Parsed Test Vectors (9 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "2",
      "20",
      "6"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "2",
      "-20",
      "6"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "20",
      "20",
      "-6"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "-20",
      "-20",
      "-6"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "-1<<31",
      "1"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "-1"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "-1<<31",
      "-1<<31",
      "0"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "1",
      "0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0",
      "0"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# remu.S
#-----------------------------------------------------------------------------
#
# Test remu instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, remu,   2,  20,   6 );
  TEST_RR_OP( 3, remu,   2, -20,   6 );
  TEST_RR_OP( 4, remu,  20,  20,  -6 );
  TEST_RR_OP( 5, remu, -20, -20,  -6 );

  TEST_RR_OP( 6, remu,      0, -1<<31,  1 );
  TEST_RR_OP( 7, remu, -1<<31, -1<<31, -1 );

  TEST_RR_OP( 8, remu, -1<<31, -1<<31, 0 );
  TEST_RR_OP( 9, remu,      1,      1, 0 );
  TEST_RR_OP(10, remu,      0,      0, 0 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sb_asm | Assembly Test: PICORV32_TESTS_SB -->

# Assembly Test: `PICORV32_TESTS_SB`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sb.S`

## Parsed Test Vectors (22 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0xffffffaa",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0x00000000",
      "1",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0xffffefa0",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0x0000000a",
      "3",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0xffffffaa",
      "-3",
      "tdat8"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0x00000000",
      "-2",
      "tdat8"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0xffffffa0",
      "-1",
      "tdat8"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "args": [
      "sb",
      "0x0000000a",
      "0",
      "tdat8"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x78",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x12345678; \\\n    addi x4",
      "x1",
      "-32; \\\n    sb x2",
      "32(x4"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0xffffff98",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x00003098; \\\n    addi x1",
      "x1",
      "-6; \\\n    sb x2",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0xffffffdd",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lb",
      "sb",
      "0xffffffcd",
      "1",
      "tdat"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "2",
      "lb",
      "sb",
      "0xffffffcc",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0xffffffbc",
      "3",
      "tdat"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lb",
      "sb",
      "0xffffffbb",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0xffffffab",
      "5",
      "tdat"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0x33",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lb",
      "sb",
      "0x23",
      "1",
      "tdat"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "2",
      "lb",
      "sb",
      "0x22",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0x12",
      "3",
      "tdat"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lb",
      "sb",
      "0x11",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lb",
      "sb",
      "0x01",
      "5",
      "tdat"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sb.S
#-----------------------------------------------------------------------------
#
# Test sb instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lb, sb, 0xffffffaa, 0, tdat );
  TEST_ST_OP( 3, lb, sb, 0x00000000, 1, tdat );
  TEST_ST_OP( 4, lh, sb, 0xffffefa0, 2, tdat );
  TEST_ST_OP( 5, lb, sb, 0x0000000a, 3, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lb, sb, 0xffffffaa, -3, tdat8 );
  TEST_ST_OP( 7, lb, sb, 0x00000000, -2, tdat8 );
  TEST_ST_OP( 8, lb, sb, 0xffffffa0, -1, tdat8 );
  TEST_ST_OP( 9, lb, sb, 0x0000000a, 0,  tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x78, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sb x2, 32(x4); \
    lb x3, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0xffffff98, \
    la  x1, tdat9; \
    li  x2, 0x00003098; \
    addi x1, x1, -6; \
    sb x2, 7(x1); \
    la  x4, tdat10; \
    lb x3, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lb, sb, 0xffffffdd, 0, tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lb, sb, 0xffffffcd, 1, tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lb, sb, 0xffffffcc, 2, tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lb, sb, 0xffffffbc, 3, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lb, sb, 0xffffffbb, 4, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lb, sb, 0xffffffab, 5, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lb, sb, 0x33, 0, tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lb, sb, 0x23, 1, tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lb, sb, 0x22, 2, tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lb, sb, 0x12, 3, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lb, sb, 0x11, 4, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lb, sb, 0x01, 5, tdat );

  li a0, 0xef
  la a1, tdat
  sb a0, 3(a1)

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .byte 0xef
tdat2:  .byte 0xef
tdat3:  .byte 0xef
tdat4:  .byte 0xef
tdat5:  .byte 0xef
tdat6:  .byte 0xef
tdat7:  .byte 0xef
tdat8:  .byte 0xef
tdat9:  .byte 0xef
tdat10: .byte 0xef

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sh_asm | Assembly Test: PICORV32_TESTS_SH -->

# Assembly Test: `PICORV32_TESTS_SH`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sh.S`

## Parsed Test Vectors (22 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0x000000aa",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0xffffaa00",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0xbeef0aa0",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0xffffa00a",
      "6",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0x000000aa",
      "-6",
      "tdat8"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0xffffaa00",
      "-4",
      "tdat8"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0x00000aa0",
      "-2",
      "tdat8"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "args": [
      "sh",
      "0xffffa00a",
      "0",
      "tdat8"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x5678",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x12345678; \\\n    addi x4",
      "x1",
      "-32; \\\n    sh x2",
      "32(x4"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0x3098",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x00003098; \\\n    addi x1",
      "x1",
      "-5; \\\n    sh x2",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0xffffccdd",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lh",
      "sh",
      "0xffffbccd",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "2",
      "lh",
      "sh",
      "0xffffbbcc",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0xffffabbc",
      "6",
      "tdat"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lh",
      "sh",
      "0xffffaabb",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0xffffdaab",
      "10",
      "tdat"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0x2233",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lh",
      "sh",
      "0x1223",
      "2",
      "tdat"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "2",
      "lh",
      "sh",
      "0x1122",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0x0112",
      "6",
      "tdat"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lh",
      "sh",
      "0x0011",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lh",
      "sh",
      "0x3001",
      "10",
      "tdat"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sh.S
#-----------------------------------------------------------------------------
#
# Test sh instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lh, sh, 0x000000aa, 0, tdat );
  TEST_ST_OP( 3, lh, sh, 0xffffaa00, 2, tdat );
  TEST_ST_OP( 4, lw, sh, 0xbeef0aa0, 4, tdat );
  TEST_ST_OP( 5, lh, sh, 0xffffa00a, 6, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lh, sh, 0x000000aa, -6, tdat8 );
  TEST_ST_OP( 7, lh, sh, 0xffffaa00, -4, tdat8 );
  TEST_ST_OP( 8, lh, sh, 0x00000aa0, -2, tdat8 );
  TEST_ST_OP( 9, lh, sh, 0xffffa00a, 0,  tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x5678, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sh x2, 32(x4); \
    lh x3, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0x3098, \
    la  x1, tdat9; \
    li  x2, 0x00003098; \
    addi x1, x1, -5; \
    sh x2, 7(x1); \
    la  x4, tdat10; \
    lh x3, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lh, sh, 0xffffccdd, 0,  tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lh, sh, 0xffffbccd, 2,  tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lh, sh, 0xffffbbcc, 4,  tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lh, sh, 0xffffabbc, 6, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lh, sh, 0xffffaabb, 8, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lh, sh, 0xffffdaab, 10, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lh, sh, 0x2233, 0,  tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lh, sh, 0x1223, 2,  tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lh, sh, 0x1122, 4,  tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lh, sh, 0x0112, 6, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lh, sh, 0x0011, 8, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lh, sh, 0x3001, 10, tdat );

  li a0, 0xbeef
  la a1, tdat
  sh a0, 6(a1)

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .half 0xbeef
tdat2:  .half 0xbeef
tdat3:  .half 0xbeef
tdat4:  .half 0xbeef
tdat5:  .half 0xbeef
tdat6:  .half 0xbeef
tdat7:  .half 0xbeef
tdat8:  .half 0xbeef
tdat9:  .half 0xbeef
tdat10: .half 0xbeef

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_simple_asm | Assembly Test: PICORV32_TESTS_SIMPLE -->

# Assembly Test: `PICORV32_TESTS_SIMPLE`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/simple.S`

## Parsed Test Vectors (0 total)

```json
[]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# simple.S
#-----------------------------------------------------------------------------
#
# This is the most basic self checking test. If your simulator does not
# pass thiss then there is little chance that it will pass any of the
# more complicated self checking tests.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

RVTEST_PASS

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sll_asm | Assembly Test: PICORV32_TESTS_SLL -->

# Assembly Test: `PICORV32_TESTS_SLL`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sll.S`

## Parsed Test Vectors (42 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000001",
      "0x00000001",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000002",
      "0x00000001",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffff80",
      "0xffffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffc000",
      "0xffffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0xffffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0x42424242",
      "0x21212121",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0x90909080",
      "0x21212121",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "0x48484000",
      "0x21212121",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x21212121",
      "31"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0xffffffe0"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "args": [
      "0x42424242",
      "0x21212121",
      "0xffffffe1"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "args": [
      "0x90909080",
      "0x21212121",
      "0xffffffe7"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "args": [
      "0x48484000",
      "0x21212121",
      "0xffffffee"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x21212120",
      "0xffffffff"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "24",
      "3"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sll",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sll",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sll",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sll",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sll",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "sll",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sll",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sll",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sll",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sll",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sll",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "sll",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sll",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sll",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sll",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "15"
    ]
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "1024",
      "2048"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sll.S
#-----------------------------------------------------------------------------
#
# Test sll instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sll, 0x00000001, 0x00000001, 0  );
  TEST_RR_OP( 3,  sll, 0x00000002, 0x00000001, 1  );
  TEST_RR_OP( 4,  sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_OP( 5,  sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_OP( 6,  sll, 0x80000000, 0x00000001, 31 );

  TEST_RR_OP( 7,  sll, 0xffffffff, 0xffffffff, 0  );
  TEST_RR_OP( 8,  sll, 0xfffffffe, 0xffffffff, 1  );
  TEST_RR_OP( 9,  sll, 0xffffff80, 0xffffffff, 7  );
  TEST_RR_OP( 10, sll, 0xffffc000, 0xffffffff, 14 );
  TEST_RR_OP( 11, sll, 0x80000000, 0xffffffff, 31 );

  TEST_RR_OP( 12, sll, 0x21212121, 0x21212121, 0  );
  TEST_RR_OP( 13, sll, 0x42424242, 0x21212121, 1  );
  TEST_RR_OP( 14, sll, 0x90909080, 0x21212121, 7  );
  TEST_RR_OP( 15, sll, 0x48484000, 0x21212121, 14 );
  TEST_RR_OP( 16, sll, 0x80000000, 0x21212121, 31 );

  # Verify that shifts only use bottom five bits

  TEST_RR_OP( 17, sll, 0x21212121, 0x21212121, 0xffffffe0 );
  TEST_RR_OP( 18, sll, 0x42424242, 0x21212121, 0xffffffe1 );
  TEST_RR_OP( 19, sll, 0x90909080, 0x21212121, 0xffffffe7 );
  TEST_RR_OP( 20, sll, 0x48484000, 0x21212121, 0xffffffee );
  TEST_RR_OP( 21, sll, 0x00000000, 0x21212120, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC2_EQ_DEST( 23, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, sll, 24, 3 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_DEST_BYPASS( 26, 1, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, sll, 0x80000000, 0x00000001, 31 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, sll, 0x80000000, 0x00000001, 31 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, sll, 0x80000000, 0x00000001, 31 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, sll, 0x80000000, 0x00000001, 31 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, sll, 0x00000080, 0x00000001, 7  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, sll, 0x00004000, 0x00000001, 14 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, sll, 0x80000000, 0x00000001, 31 );

  TEST_RR_ZEROSRC1( 40, sll, 0, 15 );
  TEST_RR_ZEROSRC2( 41, sll, 32, 32 );
  TEST_RR_ZEROSRC12( 42, sll, 0 );
  TEST_RR_ZERODEST( 43, sll, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_slli_asm | Assembly Test: PICORV32_TESTS_SLLI -->

# Assembly Test: `PICORV32_TESTS_SLLI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/slli.S`

## Parsed Test Vectors (24 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000001",
      "0x00000001",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000002",
      "0x00000001",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffff80",
      "0xffffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffc000",
      "0xffffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x80000000",
      "0xffffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x42424242",
      "0x21212121",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x90909080",
      "0x21212121",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x48484000",
      "0x21212121",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x80000000",
      "0x21212121",
      "31"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slli",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slli",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slli",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slli",
      "0x00000080",
      "0x00000001",
      "7"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slli",
      "0x00004000",
      "0x00000001",
      "14"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slli",
      "0x80000000",
      "0x00000001",
      "31"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0",
      "31"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "33",
      "20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slli.S
#-----------------------------------------------------------------------------
#
# Test slli instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  slli, 0x00000001, 0x00000001, 0  );
  TEST_IMM_OP( 3,  slli, 0x00000002, 0x00000001, 1  );
  TEST_IMM_OP( 4,  slli, 0x00000080, 0x00000001, 7  );
  TEST_IMM_OP( 5,  slli, 0x00004000, 0x00000001, 14 );
  TEST_IMM_OP( 6,  slli, 0x80000000, 0x00000001, 31 );

  TEST_IMM_OP( 7,  slli, 0xffffffff, 0xffffffff, 0  );
  TEST_IMM_OP( 8,  slli, 0xfffffffe, 0xffffffff, 1  );
  TEST_IMM_OP( 9,  slli, 0xffffff80, 0xffffffff, 7  );
  TEST_IMM_OP( 10, slli, 0xffffc000, 0xffffffff, 14 );
  TEST_IMM_OP( 11, slli, 0x80000000, 0xffffffff, 31 );

  TEST_IMM_OP( 12, slli, 0x21212121, 0x21212121, 0  );
  TEST_IMM_OP( 13, slli, 0x42424242, 0x21212121, 1  );
  TEST_IMM_OP( 14, slli, 0x90909080, 0x21212121, 7  );
  TEST_IMM_OP( 15, slli, 0x48484000, 0x21212121, 14 );
  TEST_IMM_OP( 16, slli, 0x80000000, 0x21212121, 31 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, slli, 0x00000080, 0x00000001, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, slli, 0x00000080, 0x00000001, 7  );
  TEST_IMM_DEST_BYPASS( 19, 1, slli, 0x00004000, 0x00000001, 14 );
  TEST_IMM_DEST_BYPASS( 20, 2, slli, 0x80000000, 0x00000001, 31 );

  TEST_IMM_SRC1_BYPASS( 21, 0, slli, 0x00000080, 0x00000001, 7  );
  TEST_IMM_SRC1_BYPASS( 22, 1, slli, 0x00004000, 0x00000001, 14 );
  TEST_IMM_SRC1_BYPASS( 23, 2, slli, 0x80000000, 0x00000001, 31 );

  TEST_IMM_ZEROSRC1( 24, slli, 0, 31 );
  TEST_IMM_ZERODEST( 25, slli, 33, 20 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_slt_asm | Assembly Test: PICORV32_TESTS_SLT -->

# Assembly Test: `PICORV32_TESTS_SLT`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/slt.S`

## Parsed Test Vectors (37 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x00000007",
      "0x00000003"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0x00000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0x00000000"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0x00007fff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0x80000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0xffff8000"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0x00000000",
      "0xffffffff"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "1",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "args": [
      "0",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0",
      "14",
      "13"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "1",
      "11",
      "13"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0",
      "13"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "slt",
      "1",
      "11",
      "13"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "slt",
      "0",
      "14",
      "13"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "slt",
      "1",
      "12",
      "13"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "slt",
      "0",
      "14",
      "13"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "slt",
      "1",
      "11",
      "13"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "slt",
      "0",
      "15",
      "13"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "slt",
      "1",
      "10",
      "13"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "slt",
      "0",
      "16",
      "13"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "slt",
      "1",
      "9",
      "13"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "slt",
      "0",
      "17",
      "13"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "slt",
      "1",
      "8",
      "13"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "slt",
      "0",
      "18",
      "13"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "slt",
      "1",
      "7",
      "13"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "slt",
      "0",
      "19",
      "13"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "slt",
      "1",
      "6",
      "13"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "-1"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "1",
      "-1"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "16",
      "30"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slt.S
#-----------------------------------------------------------------------------
#
# Test slt instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  slt, 0, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  slt, 0, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  slt, 1, 0x00000003, 0x00000007 );
  TEST_RR_OP( 5,  slt, 0, 0x00000007, 0x00000003 );

  TEST_RR_OP( 6,  slt, 0, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 7,  slt, 1, 0x80000000, 0x00000000 );
  TEST_RR_OP( 8,  slt, 1, 0x80000000, 0xffff8000 );

  TEST_RR_OP( 9,  slt, 1, 0x00000000, 0x00007fff );
  TEST_RR_OP( 10, slt, 0, 0x7fffffff, 0x00000000 );
  TEST_RR_OP( 11, slt, 0, 0x7fffffff, 0x00007fff );

  TEST_RR_OP( 12, slt, 1, 0x80000000, 0x00007fff );
  TEST_RR_OP( 13, slt, 0, 0x7fffffff, 0xffff8000 );

  TEST_RR_OP( 14, slt, 0, 0x00000000, 0xffffffff );
  TEST_RR_OP( 15, slt, 1, 0xffffffff, 0x00000001 );
  TEST_RR_OP( 16, slt, 0, 0xffffffff, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 17, slt, 0, 14, 13 );
  TEST_RR_SRC2_EQ_DEST( 18, slt, 1, 11, 13 );
  TEST_RR_SRC12_EQ_DEST( 19, slt, 0, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 20, 0, slt, 1, 11, 13 );
  TEST_RR_DEST_BYPASS( 21, 1, slt, 0, 14, 13 );
  TEST_RR_DEST_BYPASS( 22, 2, slt, 1, 12, 13 );

  TEST_RR_SRC12_BYPASS( 23, 0, 0, slt, 0, 14, 13 );
  TEST_RR_SRC12_BYPASS( 24, 0, 1, slt, 1, 11, 13 );
  TEST_RR_SRC12_BYPASS( 25, 0, 2, slt, 0, 15, 13 );
  TEST_RR_SRC12_BYPASS( 26, 1, 0, slt, 1, 10, 13 );
  TEST_RR_SRC12_BYPASS( 27, 1, 1, slt, 0, 16, 13 );
  TEST_RR_SRC12_BYPASS( 28, 2, 0, slt, 1,  9, 13 );

  TEST_RR_SRC21_BYPASS( 29, 0, 0, slt, 0, 17, 13 );
  TEST_RR_SRC21_BYPASS( 30, 0, 1, slt, 1,  8, 13 );
  TEST_RR_SRC21_BYPASS( 31, 0, 2, slt, 0, 18, 13 );
  TEST_RR_SRC21_BYPASS( 32, 1, 0, slt, 1,  7, 13 );
  TEST_RR_SRC21_BYPASS( 33, 1, 1, slt, 0, 19, 13 );
  TEST_RR_SRC21_BYPASS( 34, 2, 0, slt, 1,  6, 13 );

  TEST_RR_ZEROSRC1( 35, slt, 0, -1 );
  TEST_RR_ZEROSRC2( 36, slt, 1, -1 );
  TEST_RR_ZEROSRC12( 37, slt, 0 );
  TEST_RR_ZERODEST( 38, slt, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_slti_asm | Assembly Test: PICORV32_TESTS_SLTI -->

# Assembly Test: `PICORV32_TESTS_SLTI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/slti.S`

## Parsed Test Vectors (24 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x00000000",
      "0x000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x00000001",
      "0x001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0x00000003",
      "0x007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x00000007",
      "0x003"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x00000000",
      "0x800"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0x80000000",
      "0x000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0x80000000",
      "0x800"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0x00000000",
      "0x7ff"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0x000"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0x7ff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0x80000000",
      "0x7ff"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x7fffffff",
      "0x800"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0x00000000",
      "0xfff"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "args": [
      "1",
      "0xffffffff",
      "0x001"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "args": [
      "0",
      "0xffffffff",
      "0xfff"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "1",
      "11",
      "13"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slti",
      "0",
      "15",
      "10"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slti",
      "1",
      "10",
      "16"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "slti",
      "0",
      "16",
      "9"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slti",
      "1",
      "11",
      "15"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slti",
      "0",
      "17",
      "8"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "slti",
      "1",
      "12",
      "14"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0",
      "0xfff"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "0x00ff00ff",
      "0xfff"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# slti.S
#-----------------------------------------------------------------------------
#
# Test slti instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  slti, 0, 0x00000000, 0x000 );
  TEST_IMM_OP( 3,  slti, 0, 0x00000001, 0x001 );
  TEST_IMM_OP( 4,  slti, 1, 0x00000003, 0x007 );
  TEST_IMM_OP( 5,  slti, 0, 0x00000007, 0x003 );

  TEST_IMM_OP( 6,  slti, 0, 0x00000000, 0x800 );
  TEST_IMM_OP( 7,  slti, 1, 0x80000000, 0x000 );
  TEST_IMM_OP( 8,  slti, 1, 0x80000000, 0x800 );

  TEST_IMM_OP( 9,  slti, 1, 0x00000000, 0x7ff );
  TEST_IMM_OP( 10, slti, 0, 0x7fffffff, 0x000 );
  TEST_IMM_OP( 11, slti, 0, 0x7fffffff, 0x7ff );

  TEST_IMM_OP( 12, slti, 1, 0x80000000, 0x7ff );
  TEST_IMM_OP( 13, slti, 0, 0x7fffffff, 0x800 );

  TEST_IMM_OP( 14, slti, 0, 0x00000000, 0xfff );
  TEST_IMM_OP( 15, slti, 1, 0xffffffff, 0x001 );
  TEST_IMM_OP( 16, slti, 0, 0xffffffff, 0xfff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, sltiu, 1, 11, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, slti, 0, 15, 10 );
  TEST_IMM_DEST_BYPASS( 19, 1, slti, 1, 10, 16 );
  TEST_IMM_DEST_BYPASS( 20, 2, slti, 0, 16,  9 );

  TEST_IMM_SRC1_BYPASS( 21, 0, slti, 1, 11, 15 );
  TEST_IMM_SRC1_BYPASS( 22, 1, slti, 0, 17,  8 );
  TEST_IMM_SRC1_BYPASS( 23, 2, slti, 1, 12, 14 );

  TEST_IMM_ZEROSRC1( 24, slti, 0, 0xfff );
  TEST_IMM_ZERODEST( 25, slti, 0x00ff00ff, 0xfff );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sra_asm | Assembly Test: PICORV32_TESTS_SRA -->

# Assembly Test: `PICORV32_TESTS_SRA`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sra.S`

## Parsed Test Vectors (42 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x80000000",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0xc0000000",
      "0x80000000",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x80000001",
      "31"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffffff",
      "0x7fffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "0x3fffffff",
      "0x7fffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00ffffff",
      "0x7fffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0001ffff",
      "0x7fffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x7fffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "0x81818181",
      "0x81818181",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0xc0c0c0c0",
      "0x81818181",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff030303",
      "0x81818181",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffe0606",
      "0x81818181",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x81818181",
      "31"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "args": [
      "0x81818181",
      "0x81818181",
      "0xffffffc0"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "args": [
      "0xc0c0c0c0",
      "0x81818181",
      "0xffffffc1"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff030303",
      "0x81818181",
      "0xffffffc7"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffe0606",
      "0x81818181",
      "0xffffffce"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0x81818181",
      "0xffffffff"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0",
      "7"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sra",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sra",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sra",
      "0xffffffff",
      "0x80000000",
      "31"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sra",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sra",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "sra",
      "0xffffffff",
      "0x80000000",
      "31"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sra",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sra",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sra",
      "0xffffffff",
      "0x80000000",
      "31"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sra",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sra",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "sra",
      "0xffffffff",
      "0x80000000",
      "31"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sra",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sra",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sra",
      "0xffffffff",
      "0x80000000",
      "31"
    ]
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "15"
    ]
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "1024",
      "2048"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sra.S
#-----------------------------------------------------------------------------
#
# Test sra instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sra, 0x80000000, 0x80000000, 0  );
  TEST_RR_OP( 3,  sra, 0xc0000000, 0x80000000, 1  );
  TEST_RR_OP( 4,  sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_OP( 5,  sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_OP( 6,  sra, 0xffffffff, 0x80000001, 31 );

  TEST_RR_OP( 7,  sra, 0x7fffffff, 0x7fffffff, 0  );
  TEST_RR_OP( 8,  sra, 0x3fffffff, 0x7fffffff, 1  );
  TEST_RR_OP( 9,  sra, 0x00ffffff, 0x7fffffff, 7  );
  TEST_RR_OP( 10, sra, 0x0001ffff, 0x7fffffff, 14 );
  TEST_RR_OP( 11, sra, 0x00000000, 0x7fffffff, 31 );

  TEST_RR_OP( 12, sra, 0x81818181, 0x81818181, 0  );
  TEST_RR_OP( 13, sra, 0xc0c0c0c0, 0x81818181, 1  );
  TEST_RR_OP( 14, sra, 0xff030303, 0x81818181, 7  );
  TEST_RR_OP( 15, sra, 0xfffe0606, 0x81818181, 14 );
  TEST_RR_OP( 16, sra, 0xffffffff, 0x81818181, 31 );

  # Verify that shifts only use bottom five bits

  TEST_RR_OP( 17, sra, 0x81818181, 0x81818181, 0xffffffc0 );
  TEST_RR_OP( 18, sra, 0xc0c0c0c0, 0x81818181, 0xffffffc1 );
  TEST_RR_OP( 19, sra, 0xff030303, 0x81818181, 0xffffffc7 );
  TEST_RR_OP( 20, sra, 0xfffe0606, 0x81818181, 0xffffffce );
  TEST_RR_OP( 21, sra, 0xffffffff, 0x81818181, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_SRC2_EQ_DEST( 23, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, sra, 0, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_DEST_BYPASS( 26, 1, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, sra, 0xffffffff, 0x80000000, 31 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, sra, 0xffffffff, 0x80000000, 31 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, sra, 0xffffffff, 0x80000000, 31 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, sra, 0xffffffff, 0x80000000, 31 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, sra, 0xff000000, 0x80000000, 7  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, sra, 0xfffe0000, 0x80000000, 14 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, sra, 0xffffffff, 0x80000000, 31 );

  TEST_RR_ZEROSRC1( 40, sra, 0, 15 );
  TEST_RR_ZEROSRC2( 41, sra, 32, 32 );
  TEST_RR_ZEROSRC12( 42, sra, 0 );
  TEST_RR_ZERODEST( 43, sra, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_srai_asm | Assembly Test: PICORV32_TESTS_SRAI -->

# Assembly Test: `PICORV32_TESTS_SRAI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/srai.S`

## Parsed Test Vectors (24 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xc0000000",
      "0x80000000",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffffff",
      "0x80000001",
      "31"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7fffffff",
      "0x7fffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x3fffffff",
      "0x7fffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00ffffff",
      "0x7fffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0001ffff",
      "0x7fffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0x7fffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x81818181",
      "0x81818181",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xc0c0c0c0",
      "0x81818181",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xff030303",
      "0x81818181",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xfffe0606",
      "0x81818181",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffffff",
      "0x81818181",
      "31"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srai",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srai",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srai",
      "0xffffffff",
      "0x80000001",
      "31"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srai",
      "0xff000000",
      "0x80000000",
      "7"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srai",
      "0xfffe0000",
      "0x80000000",
      "14"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srai",
      "0xffffffff",
      "0x80000001",
      "31"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0",
      "31"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "33",
      "20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srai.S
#-----------------------------------------------------------------------------
#
# Test srai instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  srai, 0x00000000, 0x00000000, 0  );
  TEST_IMM_OP( 3,  srai, 0xc0000000, 0x80000000, 1  );
  TEST_IMM_OP( 4,  srai, 0xff000000, 0x80000000, 7  );
  TEST_IMM_OP( 5,  srai, 0xfffe0000, 0x80000000, 14 );
  TEST_IMM_OP( 6,  srai, 0xffffffff, 0x80000001, 31 );

  TEST_IMM_OP( 7,  srai, 0x7fffffff, 0x7fffffff, 0  );
  TEST_IMM_OP( 8,  srai, 0x3fffffff, 0x7fffffff, 1  );
  TEST_IMM_OP( 9,  srai, 0x00ffffff, 0x7fffffff, 7  );
  TEST_IMM_OP( 10, srai, 0x0001ffff, 0x7fffffff, 14 );
  TEST_IMM_OP( 11, srai, 0x00000000, 0x7fffffff, 31 );

  TEST_IMM_OP( 12, srai, 0x81818181, 0x81818181, 0  );
  TEST_IMM_OP( 13, srai, 0xc0c0c0c0, 0x81818181, 1  );
  TEST_IMM_OP( 14, srai, 0xff030303, 0x81818181, 7  );
  TEST_IMM_OP( 15, srai, 0xfffe0606, 0x81818181, 14 );
  TEST_IMM_OP( 16, srai, 0xffffffff, 0x81818181, 31 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 17, srai, 0xff000000, 0x80000000, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 18, 0, srai, 0xff000000, 0x80000000, 7  );
  TEST_IMM_DEST_BYPASS( 19, 1, srai, 0xfffe0000, 0x80000000, 14 );
  TEST_IMM_DEST_BYPASS( 20, 2, srai, 0xffffffff, 0x80000001, 31 );

  TEST_IMM_SRC1_BYPASS( 21, 0, srai, 0xff000000, 0x80000000, 7 );
  TEST_IMM_SRC1_BYPASS( 22, 1, srai, 0xfffe0000, 0x80000000, 14 );
  TEST_IMM_SRC1_BYPASS( 23, 2, srai, 0xffffffff, 0x80000001, 31 );

  TEST_IMM_ZEROSRC1( 24, srai, 0, 31 );
  TEST_IMM_ZERODEST( 25, srai, 33, 20 );
#
  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_srl_asm | Assembly Test: PICORV32_TESTS_SRL -->

# Assembly Test: `PICORV32_TESTS_SRL`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/srl.S`

## Parsed Test Vectors (42 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff8000",
      "0xffff8000",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0001ffff",
      "0xffff8001",
      "15"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffffff",
      "0xffffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "0x01ffffff",
      "0xffffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0003ffff",
      "0xffffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000001",
      "0xffffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0x10909090",
      "0x21212121",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00424242",
      "0x21212121",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00008484",
      "0x21212121",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x21212121",
      "31"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0xffffffe0"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_OP",
    "args": [
      "0x10909090",
      "0x21212121",
      "0xffffffe1"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00424242",
      "0x21212121",
      "0xffffffe7"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00008484",
      "0x21212121",
      "0xffffffee"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x21212121",
      "0xffffffff"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0",
      "7"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "srl",
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "srl",
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "srl",
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "srl",
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 38,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "srl",
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 39,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 40,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0",
      "15"
    ]
  },
  {
    "test_id": 41,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 42,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 43,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "1024",
      "2048"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srl.S
#-----------------------------------------------------------------------------
#
# Test srl instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  srl, 0xffff8000, 0xffff8000, 0  );
  TEST_RR_OP( 3,  srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_OP( 4,  srl, 0x01ffff00, 0xffff8000, 7  );
  TEST_RR_OP( 5,  srl, 0x0003fffe, 0xffff8000, 14 );
  TEST_RR_OP( 6,  srl, 0x0001ffff, 0xffff8001, 15 );

  TEST_RR_OP( 7,  srl, 0xffffffff, 0xffffffff, 0  );
  TEST_RR_OP( 8,  srl, 0x7fffffff, 0xffffffff, 1  );
  TEST_RR_OP( 9,  srl, 0x01ffffff, 0xffffffff, 7  );
  TEST_RR_OP( 10, srl, 0x0003ffff, 0xffffffff, 14 );
  TEST_RR_OP( 11, srl, 0x00000001, 0xffffffff, 31 );

  TEST_RR_OP( 12, srl, 0x21212121, 0x21212121, 0  );
  TEST_RR_OP( 13, srl, 0x10909090, 0x21212121, 1  );
  TEST_RR_OP( 14, srl, 0x00424242, 0x21212121, 7  );
  TEST_RR_OP( 15, srl, 0x00008484, 0x21212121, 14 );
  TEST_RR_OP( 16, srl, 0x00000000, 0x21212121, 31 );

  # Verify that shifts only use bottom five bits

  TEST_RR_OP( 17, srl, 0x21212121, 0x21212121, 0xffffffe0 );
  TEST_RR_OP( 18, srl, 0x10909090, 0x21212121, 0xffffffe1 );
  TEST_RR_OP( 19, srl, 0x00424242, 0x21212121, 0xffffffe7 );
  TEST_RR_OP( 20, srl, 0x00008484, 0x21212121, 0xffffffee );
  TEST_RR_OP( 21, srl, 0x00000000, 0x21212121, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 22, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_SRC2_EQ_DEST( 23, srl, 0x0003fffe, 0xffff8000, 14 );
  TEST_RR_SRC12_EQ_DEST( 24, srl, 0, 7 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 25, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_DEST_BYPASS( 26, 1, srl, 0x0003fffe, 0xffff8000, 14 );
  TEST_RR_DEST_BYPASS( 27, 2, srl, 0x0001ffff, 0xffff8000, 15 );

  TEST_RR_SRC12_BYPASS( 28, 0, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_SRC12_BYPASS( 29, 0, 1, srl, 0x01ffff00, 0xffff8000, 7 );
  TEST_RR_SRC12_BYPASS( 30, 0, 2, srl, 0x0001ffff, 0xffff8000, 15 );
  TEST_RR_SRC12_BYPASS( 31, 1, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_SRC12_BYPASS( 32, 1, 1, srl, 0x01ffff00, 0xffff8000, 7 );
  TEST_RR_SRC12_BYPASS( 33, 2, 0, srl, 0x0001ffff, 0xffff8000, 15 );

  TEST_RR_SRC21_BYPASS( 34, 0, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_SRC21_BYPASS( 35, 0, 1, srl, 0x01ffff00, 0xffff8000, 7 );
  TEST_RR_SRC21_BYPASS( 36, 0, 2, srl, 0x0001ffff, 0xffff8000, 15 );
  TEST_RR_SRC21_BYPASS( 37, 1, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_RR_SRC21_BYPASS( 38, 1, 1, srl, 0x01ffff00, 0xffff8000, 7 );
  TEST_RR_SRC21_BYPASS( 39, 2, 0, srl, 0x0001ffff, 0xffff8000, 15 );

  TEST_RR_ZEROSRC1( 40, srl, 0, 15 );
  TEST_RR_ZEROSRC2( 41, srl, 32, 32 );
  TEST_RR_ZEROSRC12( 42, srl, 0 );
  TEST_RR_ZERODEST( 43, srl, 1024, 2048 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_srli_asm | Assembly Test: PICORV32_TESTS_SRLI -->

# Assembly Test: `PICORV32_TESTS_SRLI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/srli.S`

## Parsed Test Vectors (24 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffff8000",
      "0xffff8000",
      "0"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x01ffff00",
      "0xffff8000",
      "7"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0001ffff",
      "0xffff8001",
      "15"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xffffffff",
      "0xffffffff",
      "0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x7fffffff",
      "0xffffffff",
      "1"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x01ffffff",
      "0xffffffff",
      "7"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0003ffff",
      "0xffffffff",
      "14"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000001",
      "0xffffffff",
      "31"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x21212121",
      "0x21212121",
      "0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x10909090",
      "0x21212121",
      "1"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00424242",
      "0x21212121",
      "7"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00008484",
      "0x21212121",
      "14"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00000000",
      "0x21212121",
      "31"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srl",
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srl",
      "0x7fffc000",
      "0xffff8000",
      "1"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srl",
      "0x0003fffe",
      "0xffff8000",
      "14"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "srl",
      "0x0001ffff",
      "0xffff8000",
      "15"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0",
      "31"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "33",
      "20"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# srli.S
#-----------------------------------------------------------------------------
#
# Test srli instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2,  srli, 0xffff8000, 0xffff8000, 0  );
  TEST_IMM_OP( 3,  srli, 0x7fffc000, 0xffff8000, 1  );
  TEST_IMM_OP( 4,  srli, 0x01ffff00, 0xffff8000, 7  );
  TEST_IMM_OP( 5,  srli, 0x0003fffe, 0xffff8000, 14 );
  TEST_IMM_OP( 6,  srli, 0x0001ffff, 0xffff8001, 15 );

  TEST_IMM_OP( 7,  srli, 0xffffffff, 0xffffffff, 0  );
  TEST_IMM_OP( 8,  srli, 0x7fffffff, 0xffffffff, 1  );
  TEST_IMM_OP( 9,  srli, 0x01ffffff, 0xffffffff, 7  );
  TEST_IMM_OP( 10, srli, 0x0003ffff, 0xffffffff, 14 );
  TEST_IMM_OP( 11, srli, 0x00000001, 0xffffffff, 31 );

  TEST_IMM_OP( 12, srli, 0x21212121, 0x21212121, 0  );
  TEST_IMM_OP( 13, srli, 0x10909090, 0x21212121, 1  );
  TEST_IMM_OP( 14, srli, 0x00424242, 0x21212121, 7  );
  TEST_IMM_OP( 15, srli, 0x00008484, 0x21212121, 14 );
  TEST_IMM_OP( 16, srli, 0x00000000, 0x21212121, 31 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 21, srli, 0x7fffc000, 0xffff8000, 1  );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 22, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_IMM_DEST_BYPASS( 23, 1, srl, 0x0003fffe, 0xffff8000, 14 );
  TEST_IMM_DEST_BYPASS( 24, 2, srl, 0x0001ffff, 0xffff8000, 15 );

  TEST_IMM_SRC1_BYPASS( 25, 0, srl, 0x7fffc000, 0xffff8000, 1  );
  TEST_IMM_SRC1_BYPASS( 26, 1, srl, 0x0003fffe, 0xffff8000, 14 );
  TEST_IMM_SRC1_BYPASS( 27, 2, srl, 0x0001ffff, 0xffff8000, 15 );


  TEST_IMM_ZEROSRC1( 28, srli, 0, 31 );
  TEST_IMM_ZERODEST( 29, srli, 33, 20 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sub_asm | Assembly Test: PICORV32_TESTS_SUB -->

# Assembly Test: `PICORV32_TESTS_SUB`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sub.S`

## Parsed Test Vectors (36 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0x00000001",
      "0x00000001"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffffffc",
      "0x00000003",
      "0x00000007"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00008000",
      "0x00000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80000000",
      "0x80000000",
      "0x00000000"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80008000",
      "0x80000000",
      "0xffff8000"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_OP",
    "args": [
      "0xffff8001",
      "0x00000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fffffff",
      "0x7fffffff",
      "0x00000000"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fff8000",
      "0x7fffffff",
      "0x00007fff"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_OP",
    "args": [
      "0x7fff8001",
      "0x80000000",
      "0x00007fff"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_OP",
    "args": [
      "0x80007fff",
      "0x7fffffff",
      "0xffff8000"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000001",
      "0x00000000",
      "0xffffffff"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_OP",
    "args": [
      "0xfffffffe",
      "0xffffffff",
      "0x00000001"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00000000",
      "0xffffffff",
      "0xffffffff"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0",
      "13"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sub",
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sub",
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "sub",
      "4",
      "15",
      "11"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sub",
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sub",
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "sub",
      "4",
      "15",
      "11"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sub",
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "sub",
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "sub",
      "4",
      "15",
      "11"
    ]
  },
  {
    "test_id": 28,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sub",
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 29,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sub",
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 30,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "sub",
      "4",
      "15",
      "11"
    ]
  },
  {
    "test_id": 31,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sub",
      "2",
      "13",
      "11"
    ]
  },
  {
    "test_id": 32,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "sub",
      "3",
      "14",
      "11"
    ]
  },
  {
    "test_id": 33,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "sub",
      "4",
      "15",
      "11"
    ]
  },
  {
    "test_id": 34,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "15",
      "-15"
    ]
  },
  {
    "test_id": 35,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "32",
      "32"
    ]
  },
  {
    "test_id": 36,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 37,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "16",
      "30"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sub.S
#-----------------------------------------------------------------------------
#
# Test sub instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Arithmetic tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2,  sub, 0x00000000, 0x00000000, 0x00000000 );
  TEST_RR_OP( 3,  sub, 0x00000000, 0x00000001, 0x00000001 );
  TEST_RR_OP( 4,  sub, 0xfffffffc, 0x00000003, 0x00000007 );

  TEST_RR_OP( 5,  sub, 0x00008000, 0x00000000, 0xffff8000 );
  TEST_RR_OP( 6,  sub, 0x80000000, 0x80000000, 0x00000000 );
  TEST_RR_OP( 7,  sub, 0x80008000, 0x80000000, 0xffff8000 );

  TEST_RR_OP( 8,  sub, 0xffff8001, 0x00000000, 0x00007fff );
  TEST_RR_OP( 9,  sub, 0x7fffffff, 0x7fffffff, 0x00000000 );
  TEST_RR_OP( 10, sub, 0x7fff8000, 0x7fffffff, 0x00007fff );

  TEST_RR_OP( 11, sub, 0x7fff8001, 0x80000000, 0x00007fff );
  TEST_RR_OP( 12, sub, 0x80007fff, 0x7fffffff, 0xffff8000 );

  TEST_RR_OP( 13, sub, 0x00000001, 0x00000000, 0xffffffff );
  TEST_RR_OP( 14, sub, 0xfffffffe, 0xffffffff, 0x00000001 );
  TEST_RR_OP( 15, sub, 0x00000000, 0xffffffff, 0xffffffff );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 16, sub, 2, 13, 11 );
  TEST_RR_SRC2_EQ_DEST( 17, sub, 3, 14, 11 );
  TEST_RR_SRC12_EQ_DEST( 18, sub, 0, 13 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 19, 0, sub, 2, 13, 11 );
  TEST_RR_DEST_BYPASS( 20, 1, sub, 3, 14, 11 );
  TEST_RR_DEST_BYPASS( 21, 2, sub, 4, 15, 11 );

  TEST_RR_SRC12_BYPASS( 22, 0, 0, sub, 2, 13, 11 );
  TEST_RR_SRC12_BYPASS( 23, 0, 1, sub, 3, 14, 11 );
  TEST_RR_SRC12_BYPASS( 24, 0, 2, sub, 4, 15, 11 );
  TEST_RR_SRC12_BYPASS( 25, 1, 0, sub, 2, 13, 11 );
  TEST_RR_SRC12_BYPASS( 26, 1, 1, sub, 3, 14, 11 );
  TEST_RR_SRC12_BYPASS( 27, 2, 0, sub, 4, 15, 11 );

  TEST_RR_SRC21_BYPASS( 28, 0, 0, sub, 2, 13, 11 );
  TEST_RR_SRC21_BYPASS( 29, 0, 1, sub, 3, 14, 11 );
  TEST_RR_SRC21_BYPASS( 30, 0, 2, sub, 4, 15, 11 );
  TEST_RR_SRC21_BYPASS( 31, 1, 0, sub, 2, 13, 11 );
  TEST_RR_SRC21_BYPASS( 32, 1, 1, sub, 3, 14, 11 );
  TEST_RR_SRC21_BYPASS( 33, 2, 0, sub, 4, 15, 11 );

  TEST_RR_ZEROSRC1( 34, sub, 15, -15 );
  TEST_RR_ZEROSRC2( 35, sub, 32, 32 );
  TEST_RR_ZEROSRC12( 36, sub, 0 );
  TEST_RR_ZERODEST( 37, sub, 16, 30 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_sw_asm | Assembly Test: PICORV32_TESTS_SW -->

# Assembly Test: `PICORV32_TESTS_SW`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/sw.S`

## Parsed Test Vectors (22 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0x00aa00aa",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0xaa00aa00",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0x0aa00aa0",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0xa00aa00a",
      "12",
      "tdat"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0x00aa00aa",
      "-12",
      "tdat8"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0xaa00aa00",
      "-8",
      "tdat8"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0x0aa00aa0",
      "-4",
      "tdat8"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_ST_OP",
    "args": [
      "sw",
      "0xa00aa00a",
      "0",
      "tdat8"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_CASE",
    "args": [
      "0x12345678",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x12345678; \\\n    addi x4",
      "x1",
      "-32; \\\n    sw x2",
      "32(x4"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_CASE",
    "args": [
      "0x58213098",
      "\\\n    la  x1",
      "tdat9; \\\n    li  x2",
      "0x58213098; \\\n    addi x1",
      "x1",
      "-3; \\\n    sw x2",
      "7(x1"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0xaabbccdd",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lw",
      "sw",
      "0xdaabbccd",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "2",
      "lw",
      "sw",
      "0xddaabbcc",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0xcddaabbc",
      "12",
      "tdat"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "1",
      "lw",
      "sw",
      "0xccddaabb",
      "16",
      "tdat"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_ST_SRC12_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0xbccddaab",
      "20",
      "tdat"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0x00112233",
      "0",
      "tdat"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lw",
      "sw",
      "0x30011223",
      "4",
      "tdat"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "2",
      "lw",
      "sw",
      "0x33001122",
      "8",
      "tdat"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0x23300112",
      "12",
      "tdat"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "1",
      "lw",
      "sw",
      "0x22330011",
      "16",
      "tdat"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_ST_SRC21_BYPASS",
    "args": [
      "0",
      "lw",
      "sw",
      "0x12233001",
      "20",
      "tdat"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# sw.S
#-----------------------------------------------------------------------------
#
# Test sw instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  TEST_ST_OP( 2, lw, sw, 0x00aa00aa, 0,  tdat );
  TEST_ST_OP( 3, lw, sw, 0xaa00aa00, 4,  tdat );
  TEST_ST_OP( 4, lw, sw, 0x0aa00aa0, 8,  tdat );
  TEST_ST_OP( 5, lw, sw, 0xa00aa00a, 12, tdat );

  # Test with negative offset

  TEST_ST_OP( 6, lw, sw, 0x00aa00aa, -12, tdat8 );
  TEST_ST_OP( 7, lw, sw, 0xaa00aa00, -8,  tdat8 );
  TEST_ST_OP( 8, lw, sw, 0x0aa00aa0, -4,  tdat8 );
  TEST_ST_OP( 9, lw, sw, 0xa00aa00a, 0,   tdat8 );

  # Test with a negative base

  TEST_CASE( 10, x3, 0x12345678, \
    la  x1, tdat9; \
    li  x2, 0x12345678; \
    addi x4, x1, -32; \
    sw x2, 32(x4); \
    lw x3, 0(x1); \
  )

  # Test with unaligned base

  TEST_CASE( 11, x3, 0x58213098, \
    la  x1, tdat9; \
    li  x2, 0x58213098; \
    addi x1, x1, -3; \
    sw x2, 7(x1); \
    la  x4, tdat10; \
    lw x3, 0(x4); \
  )

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_ST_SRC12_BYPASS( 12, 0, 0, lw, sw, 0xaabbccdd, 0,  tdat );
  TEST_ST_SRC12_BYPASS( 13, 0, 1, lw, sw, 0xdaabbccd, 4,  tdat );
  TEST_ST_SRC12_BYPASS( 14, 0, 2, lw, sw, 0xddaabbcc, 8,  tdat );
  TEST_ST_SRC12_BYPASS( 15, 1, 0, lw, sw, 0xcddaabbc, 12, tdat );
  TEST_ST_SRC12_BYPASS( 16, 1, 1, lw, sw, 0xccddaabb, 16, tdat );
  TEST_ST_SRC12_BYPASS( 17, 2, 0, lw, sw, 0xbccddaab, 20, tdat );

  TEST_ST_SRC21_BYPASS( 18, 0, 0, lw, sw, 0x00112233, 0,  tdat );
  TEST_ST_SRC21_BYPASS( 19, 0, 1, lw, sw, 0x30011223, 4,  tdat );
  TEST_ST_SRC21_BYPASS( 20, 0, 2, lw, sw, 0x33001122, 8,  tdat );
  TEST_ST_SRC21_BYPASS( 21, 1, 0, lw, sw, 0x23300112, 12, tdat );
  TEST_ST_SRC21_BYPASS( 22, 1, 1, lw, sw, 0x22330011, 16, tdat );
  TEST_ST_SRC21_BYPASS( 23, 2, 0, lw, sw, 0x12233001, 20, tdat );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

tdat:
tdat1:  .word 0xdeadbeef
tdat2:  .word 0xdeadbeef
tdat3:  .word 0xdeadbeef
tdat4:  .word 0xdeadbeef
tdat5:  .word 0xdeadbeef
tdat6:  .word 0xdeadbeef
tdat7:  .word 0xdeadbeef
tdat8:  .word 0xdeadbeef
tdat9:  .word 0xdeadbeef
tdat10: .word 0xdeadbeef

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_xor_asm | Assembly Test: PICORV32_TESTS_XOR -->

# Assembly Test: `PICORV32_TESTS_XOR`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/xor.S`

## Parsed Test Vectors (26 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_RR_OP",
    "args": [
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_RR_OP",
    "args": [
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_RR_OP",
    "args": [
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_RR_OP",
    "args": [
      "0x00ff00ff",
      "0xf00ff00f",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_RR_SRC1_EQ_DEST",
    "args": [
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_RR_SRC2_EQ_DEST",
    "args": [
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_RR_SRC12_EQ_DEST",
    "args": [
      "0x00000000",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "xor",
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "xor",
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_RR_DEST_BYPASS",
    "args": [
      "xor",
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "xor",
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "xor",
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "2",
      "xor",
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 15,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "xor",
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 16,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "1",
      "xor",
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 17,
    "macro": "TEST_RR_SRC12_BYPASS",
    "args": [
      "0",
      "xor",
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 18,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "xor",
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 19,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "xor",
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 20,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "2",
      "xor",
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 21,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "xor",
      "0xf00ff00f",
      "0xff00ff00",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 22,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "1",
      "xor",
      "0xff00ff00",
      "0x0ff00ff0",
      "0xf0f0f0f0"
    ]
  },
  {
    "test_id": 23,
    "macro": "TEST_RR_SRC21_BYPASS",
    "args": [
      "0",
      "xor",
      "0x0ff00ff0",
      "0x00ff00ff",
      "0x0f0f0f0f"
    ]
  },
  {
    "test_id": 24,
    "macro": "TEST_RR_ZEROSRC1",
    "args": [
      "0xff00ff00",
      "0xff00ff00"
    ]
  },
  {
    "test_id": 25,
    "macro": "TEST_RR_ZEROSRC2",
    "args": [
      "0x00ff00ff",
      "0x00ff00ff"
    ]
  },
  {
    "test_id": 26,
    "macro": "TEST_RR_ZEROSRC12",
    "args": [
      "0"
    ]
  },
  {
    "test_id": 27,
    "macro": "TEST_RR_ZERODEST",
    "args": [
      "0x11111111",
      "0x22222222"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# xor.S
#-----------------------------------------------------------------------------
#
# Test xor instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_RR_OP( 2, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_OP( 3, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_OP( 4, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_OP( 5, xor, 0x00ff00ff, 0xf00ff00f, 0xf0f0f0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_RR_SRC1_EQ_DEST( 6, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC2_EQ_DEST( 7, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_EQ_DEST( 8, xor, 0x00000000, 0xff00ff00 );

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_RR_DEST_BYPASS( 9,  0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_DEST_BYPASS( 10, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_DEST_BYPASS( 11, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC12_BYPASS( 12, 0, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 13, 0, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 14, 0, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 15, 1, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC12_BYPASS( 16, 1, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC12_BYPASS( 17, 2, 0, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_SRC21_BYPASS( 18, 0, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 19, 0, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 20, 0, 2, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 21, 1, 0, xor, 0xf00ff00f, 0xff00ff00, 0x0f0f0f0f );
  TEST_RR_SRC21_BYPASS( 22, 1, 1, xor, 0xff00ff00, 0x0ff00ff0, 0xf0f0f0f0 );
  TEST_RR_SRC21_BYPASS( 23, 2, 0, xor, 0x0ff00ff0, 0x00ff00ff, 0x0f0f0f0f );

  TEST_RR_ZEROSRC1( 24, xor, 0xff00ff00, 0xff00ff00 );
  TEST_RR_ZEROSRC2( 25, xor, 0x00ff00ff, 0x00ff00ff );
  TEST_RR_ZEROSRC12( 26, xor, 0 );
  TEST_RR_ZERODEST( 27, xor, 0x11111111, 0x22222222 );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```

---
<!-- chunk_id=picorv32_tests_xori_asm | Assembly Test: PICORV32_TESTS_XORI -->

# Assembly Test: `PICORV32_TESTS_XORI`

> **Source:** `https://raw.githubusercontent.com/YosysHQ/picorv32/main/tests/xori.S`

## Parsed Test Vectors (13 total)

```json
[
  {
    "test_id": 2,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xff00f00f",
      "0x00ff0f00",
      "0xf0f"
    ]
  },
  {
    "test_id": 3,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x0ff00f00",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 4,
    "macro": "TEST_IMM_OP",
    "args": [
      "0x00ff0ff0",
      "0x00ff08ff",
      "0x70f"
    ]
  },
  {
    "test_id": 5,
    "macro": "TEST_IMM_OP",
    "args": [
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 6,
    "macro": "TEST_IMM_SRC1_EQ_DEST",
    "args": [
      "0xff00f00f",
      "0xff00f700",
      "0x70f"
    ]
  },
  {
    "test_id": 7,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "xori",
      "0x0ff00f00",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 8,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "xori",
      "0x00ff0ff0",
      "0x00ff08ff",
      "0x70f"
    ]
  },
  {
    "test_id": 9,
    "macro": "TEST_IMM_DEST_BYPASS",
    "args": [
      "xori",
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 10,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "xori",
      "0x0ff00f00",
      "0x0ff00ff0",
      "0x0f0"
    ]
  },
  {
    "test_id": 11,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "xori",
      "0x00ff0ff0",
      "0x00ff0fff",
      "0x00f"
    ]
  },
  {
    "test_id": 12,
    "macro": "TEST_IMM_SRC1_BYPASS",
    "args": [
      "xori",
      "0xf00ff0ff",
      "0xf00ff00f",
      "0x0f0"
    ]
  },
  {
    "test_id": 13,
    "macro": "TEST_IMM_ZEROSRC1",
    "args": [
      "0x0f0",
      "0x0f0"
    ]
  },
  {
    "test_id": 14,
    "macro": "TEST_IMM_ZERODEST",
    "args": [
      "0x00ff00ff",
      "0x70f"
    ]
  }
]
```

## Raw Assembly Source

```asm
# See LICENSE for license details.

#*****************************************************************************
# xori.S
#-----------------------------------------------------------------------------
#
# Test xori instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV32U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Logical tests
  #-------------------------------------------------------------

  TEST_IMM_OP( 2, xori, 0xff00f00f, 0x00ff0f00, 0xf0f );
  TEST_IMM_OP( 3, xori, 0x0ff00f00, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_OP( 4, xori, 0x00ff0ff0, 0x00ff08ff, 0x70f );
  TEST_IMM_OP( 5, xori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  #-------------------------------------------------------------
  # Source/Destination tests
  #-------------------------------------------------------------

  TEST_IMM_SRC1_EQ_DEST( 6, xori, 0xff00f00f, 0xff00f700, 0x70f );

   #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  TEST_IMM_DEST_BYPASS( 7,  0, xori, 0x0ff00f00, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_DEST_BYPASS( 8,  1, xori, 0x00ff0ff0, 0x00ff08ff, 0x70f );
  TEST_IMM_DEST_BYPASS( 9,  2, xori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  TEST_IMM_SRC1_BYPASS( 10, 0, xori, 0x0ff00f00, 0x0ff00ff0, 0x0f0 );
  TEST_IMM_SRC1_BYPASS( 11, 1, xori, 0x00ff0ff0, 0x00ff0fff, 0x00f );
  TEST_IMM_SRC1_BYPASS( 12, 2, xori, 0xf00ff0ff, 0xf00ff00f, 0x0f0 );

  TEST_IMM_ZEROSRC1( 13, xori, 0x0f0, 0x0f0 );
  TEST_IMM_ZERODEST( 14, xori, 0x00ff00ff, 0x70f );

  TEST_PASSFAIL

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
```