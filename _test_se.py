import sys
sys.path.insert(0, '.')
from systems_engineer import build_from_files, microarch_to_cheatsheet

print('=== Building microarch.yaml from offline ISA + default facts ===')
microarch = build_from_files('riscv32', output_path='microarch.yaml')

print()
print('=== Encoding summary ===')
alu = microarch['alu']
imm = microarch['imm_type']
wb  = microarch['writeback']
mem = microarch['mem_size']
icd = microarch['instruction_icd']
print(f'ALU bus width  : {alu["width"]} bits  ({len(alu["encoding"])} operations)')
print(f'IMM bus width  : {imm["width"]} bits  ({len(imm["encoding"])} formats)')
print(f'WB  bus width  : {wb["width"]} bits  ({len(wb["encoding"])} sources)')
print(f'MEM bus width  : {mem["width"]} bits  ({len(mem["encoding"])} sizes)')
print(f'Instructions   : {len(icd)}')

print()
print('=== ALU encoding (no overlaps) ===')
for k, v in alu['binary'].items():
    print(f'  {k:<5} = {alu["width"]}\'b{v}')

print()
print('=== IMM encoding ===')
for k, v in imm['binary'].items():
    print(f'  {k} = {imm["width"]}\'b{v}')

print()
print('=== Dynamic Cheatsheet (first 5 instructions) ===')
cs = microarch_to_cheatsheet(microarch)
lines = cs.splitlines()
for line in lines[:7]:
    print(line)
print(f'  ... ({len(lines)-2} instruction rows total)')
print(f'Total cheatsheet: {len(cs)} chars, ~{len(cs)//4} tokens')
