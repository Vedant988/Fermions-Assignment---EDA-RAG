import re

# ── Check control.v ──────────────────────────────────────────────────────────
with open('rtl_generated/control.v', encoding='utf-8') as f:
    ctrl = f.read()

lines = ctrl.splitlines()
print(f"control.v: {len(lines)} lines")

# Verify AUIPC has opcode 0010111 (not 0110111 which is LUI)
auipc_section = [l for l in lines if 'AUIPC' in l or '0010111' in l]
print("\n=== AUIPC / opcode 0010111 lines ===")
for l in auipc_section[:6]:
    print(repr(l))

# Verify LUI has opcode 0110111 
lui_section = [l for l in lines if 'LUI' in l or '0110111' in l]
print("\n=== LUI / opcode 0110111 lines ===")
for l in lui_section[:6]:
    print(repr(l))

# Check branch_type assignment exists
br_lines = [l for l in lines if 'branch_type' in l and '=' in l]
print("\n=== branch_type assignments ===")
for l in br_lines[:8]:
    print(repr(l))

# Spot-check alu_op values for ADD(0) and SRA(7)
alu_lines = [l for l in lines if 'alu_op' in l and '=' in l][:12]
print("\n=== alu_op assignments (first 12) ===")
for l in alu_lines:
    print(repr(l))

# ── Check imm_gen.v ──────────────────────────────────────────────────────────
print("\n\n=== imm_gen.v (full) ===")
with open('rtl_generated/imm_gen.v', encoding='utf-8') as f:
    imm = f.read()
# Replace em-dash so print doesn't crash
imm_safe = imm.encode('ascii', errors='replace').decode('ascii')
print(imm_safe)

print("\n=== VALIDATION SUMMARY ===")
checks = {
    "AUIPC opcode 0010111": '0010111' in ctrl and 'AUIPC' in ctrl,
    "LUI opcode 0110111":   '0110111' in ctrl and 'LUI' in ctrl,
    "branch_type assigned": 'branch_type = 3' in ctrl,
    "JAL jump_type 0":      "jump_type   = 1'b0" in ctrl,
    "JALR jump_type 1":     "jump_type   = 1'b1" in ctrl,
    "I-type imm in imm_gen": "3'b000" in imm and 'instr[31:20]' in imm,
    "J-type imm in imm_gen": "instr[19:12]" in imm and "instr[30:21]" in imm,
    "module control present": 'module control' in ctrl,
    "module imm_gen present": 'module imm_gen' in imm,
    "always_comb in control": 'always_comb' in ctrl,
    "default clause present": 'default: begin end' in ctrl,
}
all_pass = True
for name, result in checks.items():
    status = "[PASS]" if result else "[FAIL]"
    if not result:
        all_pass = False
    print(f"  {status}  {name}")

print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
