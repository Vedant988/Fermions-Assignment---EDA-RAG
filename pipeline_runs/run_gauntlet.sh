#!/bin/bash
PASS=0; FAIL=0; TIMEOUT=0
VTOP=/tmp/riscv_sim/obj_dir/Vtop

for bin in /tmp/riscv-tests-bin/rv32ui-p-*.bin; do
    test_name=$(basename "$bin" .bin)
    out=$("$VTOP" "$bin" 2>&1)
    if echo "$out" | grep -q 'TOHOST:PASS'; then
        echo "PASS: $test_name"
        PASS=$((PASS+1))
    elif echo "$out" | grep -q 'TOHOST:FAIL'; then
        code=$(echo "$out" | grep -o 'TOHOST:FAIL:[0-9]*' | cut -d: -f3)
        echo "FAIL: $test_name  (test case #$code)"
        FAIL=$((FAIL+1))
    else
        echo "TIMEOUT: $test_name"
        TIMEOUT=$((TIMEOUT+1))
    fi
done

echo ""
echo "================================================"
echo "Score: $PASS PASS  |  $FAIL FAIL  |  $TIMEOUT TIMEOUT"
echo "Total: $((PASS+FAIL+TIMEOUT)) tests"
if [ $FAIL -eq 0 ] && [ $TIMEOUT -eq 0 ]; then
    echo "PERFECT SCORE! RV32I Compliant!"
fi
