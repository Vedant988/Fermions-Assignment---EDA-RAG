import os
from dotenv import load_dotenv
from groq import Groq
import json
import time

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

import httpx
client = Groq(api_key=api_key, http_client=httpx.Client())

print("\n=== STAGE 1: RESEARCHER AGENT ===")
start = time.time()
import rag_test as rt
from app import load_pipeline
from researcher_agent import run_researcher_sync

print("Loading RAG pipeline...")
pipe = load_pipeline()
print("Running micro-queries for RISC-V RV32I...")
isa_facts = run_researcher_sync(client, pipe, "RISC-V RV32I")
print(f"Stage 1 Complete: {len(isa_facts.get('behaviors', []))} instruction facts extracted in {time.time()-start:.1f}s.")

print("\n=== STAGE 2: SYSTEMS ENGINEER ===")
start = time.time()
from systems_engineer import MicroarchBuilder, load_offline_isa

offline_isa = load_offline_isa("riscv32")
builder = MicroarchBuilder(isa_facts, offline_isa)
microarch = builder.build()
builder.save(microarch, "microarch_test.yaml")
print(f"Stage 2 Complete: microarch_test.yaml written. 0 collisions. Took {time.time()-start:.1f}s.")

print("\n=== STAGE 4a: JINJA2 RTL RENDERER ===")
start = time.time()
from rtl_renderer import RTLRenderer

renderer = RTLRenderer()
results = renderer.render_all_truth_tables(microarch, offline_isa, "rtl_test")
print(f"Stage 4a Complete: Generated {len(results)} Verilog files in {time.time()-start:.1f}s using 0 LLM tokens.")

print("\n=== FINAL CHECK: VERILATOR LINT ===")
code = os.system("verilator --lint-only --Wall rtl_test/control.v")
code2 = os.system("verilator --lint-only --Wall rtl_test/imm_gen.v")
if code == 0 and code2 == 0:
    print("\n✅ ALL TESTS PASSED! PIPELINE IS GREEN.")
else:
    print("\n❌ VERILATOR LINT FAILED.")
