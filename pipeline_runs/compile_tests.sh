#!/bin/bash
echo 'Patching riscv_test.h to bypass ecall...'
# Replace ecall in RVTEST_PASS with j write_tohost
sed -i '/^#define RVTEST_PASS/,/ecall/{s/ecall/j write_tohost/}' /tmp/riscv-tests/env/p/riscv_test.h
# Replace j fail_tohost in RVTEST_FAIL with j write_tohost
sed -i 's/j fail_tohost/j write_tohost/' /tmp/riscv-tests/env/p/riscv_test.h
echo 'Patch applied. Recompiling...'
mkdir -p /tmp/riscv-tests-bin
PASS=0; FAIL=0
for src in /tmp/riscv-tests/isa/rv32ui/*.S; do
    base=$(basename "$src" .S)
    test_name="rv32ui-p-${base}"
    riscv64-unknown-elf-gcc -march=rv32im -mabi=ilp32 -static -nostdlib -nostartfiles \
        -T/tmp/riscv-link.ld \
        -I/tmp/riscv-tests/env/p \
        -I/tmp/riscv-tests/isa/macros/scalar \
        "$src" -o "/tmp/riscv-tests/${test_name}" 2>/dev/null \
    && riscv64-unknown-elf-objcopy -O binary "/tmp/riscv-tests/${test_name}" "/tmp/riscv-tests-bin/${test_name}.bin" \
    && echo "OK: ${test_name}" && PASS=$((PASS+1)) \
    || (echo "SKIP: ${test_name}" && FAIL=$((FAIL+1)))
done
echo ""
echo "Total: $(ls /tmp/riscv-tests-bin/*.bin 2>/dev/null | wc -l) binaries compiled. PASS=$PASS FAIL=$FAIL"
