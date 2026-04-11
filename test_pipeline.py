import os
from dotenv import load_dotenv
from groq import Groq
import app

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

import rag_test as rt
limiter = rt.RateLimiter(max_tpm=8000, max_rpm=30)

print("--- PLANNER ---")
plan_resp = app.llm_call(client, app.PLANNER_SYSTEM, "Build a single-cycle RV32I processor core that passes the riscv-tests suite.", limiter, 2048)
print(plan_resp)

plan = app.parse_json_safe(plan_resp)
if not plan:
    print("FAILED TO PARSE PLAN")
    exit(1)

print("\n--- ISA EXPERT (TESTING JUST 1 GROUP: R-Type) ---")
grp = plan["instruction_groups"][0]
print(f"Group: {grp['group']}")

# Use app.run_retrieval for "Instruction encoding, opcode... ADD SUB AND OR..."
pipe = app.load_pipeline()
query = (f"Instruction encoding, opcode, funct3, funct7, and control signals "
         f"for {grp['group']}: {', '.join(grp['instructions'])}")

parents = app.run_retrieval(pipe, query, False, client, 3, 12)
context = "\n\n---\n\n".join(
    f"[{p['section_title']}]\n{p['full_text'][:1200]}" for p in parents
)
user_msg = (f"Instructions to decode: {', '.join(grp['instructions'])}\n\n"
            f"Context from RISC-V corpus:\n{context}")

isa_resp = app.llm_call(client, app.ISA_EXPERT_SYSTEM, user_msg, limiter, 2000)
print(isa_resp)
