import os
import json
import asyncio
from dotenv import load_dotenv
from groq import Groq

# Import the agent and the RAG test utilities from your pipeline
from researcher_agent import ArchitectAgent
import rag_test as rt
from sentence_transformers import SentenceTransformer

# Load API key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("[ERROR] GROQ_API_KEY not found in .env")
    exit(1)
client = Groq(api_key=api_key)

print("--- INITIALIZING RAG PIPELINE ---")
parent_store, children, new_children = rt.build_hierarchy()
embedder = SentenceTransformer(rt.EMBED_MODEL)
collection = rt.build_chroma_children(new_children, embedder)
bm25, tokenize_fn = rt.build_bm25_children(children)

pipe = {
    "rt": rt,
    "parent_store": parent_store,
    "children": children,
    "bm25": bm25,
    "tokenize_fn": tokenize_fn,
    "embedder": embedder,
    "collection": collection,
}

# 1. Define the test prompt
test_prompt = input("\nEnter a hardware prompt (or press Enter for default MAC accelerator):\n> ")
if not test_prompt.strip():
    test_prompt = "Build a 16-bit MAC accelerator for INT8 weights"

# Initialize Agent
agent = ArchitectAgent(client, pipe, test_prompt)

# =========================================================
# PHASE 1.1: Classification Node
# =========================================================
print(f"\n\n[PHASE 1.1] Executing Classification Node for: '{test_prompt}'")
print("-" * 50)
classification = agent._phase_1_1_classify()
print(json.dumps(classification, indent=2))

input("\nPress Enter to continue to Phase 1.2...")

# =========================================================
# PHASE 1.2: Dynamic Question Generator
# =========================================================
print(f"\n\n[PHASE 1.2] Generating 5 Dynamic Questions for domain: {classification.get('hardware_domain')}")
print("-" * 50)
dynamic_questions = agent._phase_1_2_generate_questions(classification)
for i, q in enumerate(dynamic_questions):
    print(f"Q{i+1}: {q}")

input("\nPress Enter to continue to Phase 1.3 & 1.4...")

# =========================================================
# PHASE 1.3 & 1.4: RAG Filter + Async Extraction Engine
# =========================================================
print("\n\n[PHASE 1.3 & 1.4] Extracting answers for the first dynamic question...")
print("-" * 50)

if dynamic_questions:
    first_question = dynamic_questions[0]
else:
    first_question = "What are the critical architectural states?"

mock_mq = {
    "key": "dynamic_query_1",
    "question": first_question,
    "output_schema": "{\"answer\": \"detailed logic constraints\"}",
    "max_tokens": 300,
}

print(f"Executing search & extraction against your RAG corpus for:\n   '{first_question}'\n")

# Run just the one micro-query
key, val = asyncio.run(agent._run_micro_query(mock_mq, children))

print("\n--- LLM JSON RESULT ---")
print(json.dumps(val, indent=2))

print("\n\nTest sequence finished!")
