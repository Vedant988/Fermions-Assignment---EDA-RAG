import streamlit as st
import os
import json
import time
from dotenv import load_dotenv
from groq import Groq

# Load variables from .env
load_dotenv()

st.set_page_config(layout="wide", page_title="The Architect: Phase 1 🧠")

st.title("CPU Architect: Phase 1 (Planning) 🧠")
st.markdown("Generating the precise RTL blueprint and data paths for the RV32I processor.")

# Sidebar configurations
st.sidebar.header("Backend Connection")
api_key_input = st.sidebar.text_input("Groq API Key (Overrides GROQ_API_KEY in .env)", 
                                      value=os.getenv("GROQ_API_KEY", ""), 
                                      type="password")

st.sidebar.info("Model Locked: `openai/gpt-oss-20b` (Selected for its deep understanding of RISC-V specific data paths).")

st.header("Prompt Setup")
user_prompt = st.text_area("High-Level User Request", 
                           "Generate a single-cycle RV32I processor that passes the riscv-tests.", 
                           height=100)

system_prompt = """You are 'The Architect', the first phase of an automated physical design flow. 
Your goal is NOT just to 'describe' a CPU. Your objective is to generate a deterministic RTL hardware contract with strict interfaces, precise behavior, and concrete module boundaries so that a downstream Phase 2 Verilog writer can directly consume it without ANY guessing.
Output a strict JSON hardware contract. DO NOT WRITE VERILOG OR CODE.

CRITICAL INSTRUCTION SUPPORT: 
If an RV32I core is requested, you must explicitly plan for the following instructions to ensure it passes riscv-tests:
- Arithmetic/logic: ADD, SUB, AND, OR, XOR, SLT, SLTU, SLL, SRL, SRA
- Immediate versions: ADDI, ANDI, ORI, XORI, SLTI, SLTIU, SLLI, SRLI, SRAI
- Upper immediates: LUI, AUIPC
- Branches: BEQ, BNE, BLT, BGE, BLTU, BGEU
- Loads: LB, LH, LW, LBU, LHU
- Stores: SB, SH, SW
- Jumps: JAL, JALR

Your output must be ONLY valid JSON in this exact schema:
{
    "assumptions": ["Logical assumptions made to fill in gaps (e.g. active high resets)"],
    "restrictions": ["Things strictly out of scope (e.g. NO floating point)"],
    "instructions_coverage": {
        "must_support": [{"category": "...", "instructions": ["..."]}],
        "optional_or_ignored": ["..."],
        "not_required_for_riscv_tests": ["ECALL", "EBREAK", "FENCE", "..."]
    },
    "top_level_interfaces": [
        {"port_name": "...", "direction": "...", "width": "...", "description": "..."}
    ],
    "datapath": ["Description of the primary datapath connections (e.g. PC -> IMEM -> Decoder...)"],
    "control_signals": [
        {"signal": "...", "purpose": "..."}
    ],
    "memory_map": ["List of critical memory regions (e.g. instruction mem, data mem, MMIO)"],
    "reset_behavior": ["What happens exactly on reset (e.g. PC=0, Reg[0]=0)"],
    "pc_update_rules": ["Rules governing how the PC is updated on next cycle"],
    "load_store_rules": ["Rules handling memory misalignment or byte masking"],
    "branch_rules": ["How branch conditions are evaluated and handled"],
    "testbench_requirements": ["What the testbench must implement to pass riscv-tests"],
    "module_order": ["register file", "immediate generator", "ALU", "control unit", "branch unit", "load/store unit", "top module"],
    "modules": [
        {
            "module_name": "...",
            "purpose": "...",
            "inputs": [{"name": "...", "width": "...", "description": "..."}],
            "outputs": [{"name": "...", "width": "...", "description": "..."}],
            "internal_behavior": ["State what it computes or registers internally"],
            "depends_on": ["SubModule1", "SubModule2", "Or empty if leaf node"],
            "corner_cases": ["Wait states, zero handling, overflow mapping, etc"]
        }
    ]
}
"""

if st.button("Generate Architectural Blueprint", type="primary", use_container_width=True):
    if not api_key_input:
        st.error("Please enter a Groq API Key.")
        st.stop()
        
    client = Groq(api_key=api_key_input)
    
    # UI "Thinking" feeling
    status_text = st.empty()
    status_text.info("🧠 The Architect is deeply analyzing the RISC-V specifications. Please wait...")
    
    output_placeholder = st.empty()
    full_response = ""
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, 
            max_tokens=7000, 
            top_p=1,
            stream=True,
            stop=None
        )
        
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            full_response += content
            output_placeholder.code(full_response, language="json")
        
        status_text.success("✅ Architectural Blueprint Finalized.")
        
        # Robust JSON extraction
        clean_text = full_response
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            clean_text = clean_text[start_idx:end_idx+1]
        else:
            clean_text = clean_text.strip()
            
        try:
            parsed = json.loads(clean_text)
            output_placeholder.empty() # Clear raw JSON
            
            # Save artifacts locally
            os.makedirs("output_artifacts", exist_ok=True)
            with open("output_artifacts/prompt_used.txt", "w") as f:
                f.write(f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER PROMPT ---\n{user_prompt}")
            with open("output_artifacts/model_output_raw.txt", "w") as f:
                f.write(full_response)
            with open("output_artifacts/blueprint.json", "w") as f:
                f.write(clean_text)
            with open("output_artifacts/validated_blueprint.json", "w") as f:
                json.dump(parsed, f, indent=4)
                
            st.success("💾 Blueprint and raw artifacts successfully saved to `output_artifacts/` directory!")
            
            # Neatly layout the plan
            st.title("📋 Full Implementation Blueprint")
            
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🤔 Assumptions & 🚧 Restrictions", expanded=True):
                    st.markdown("**Assumptions:**")
                    for a in parsed.get("assumptions", []): st.markdown(f"- {a}")
                    st.markdown("**Restrictions:**")
                    for r in parsed.get("restrictions", []): st.markdown(f"- {r}")
                
                with st.expander("🔄 Reset & PC Rules", expanded=True):
                    st.markdown("**Reset Behavior:**")
                    for r in parsed.get("reset_behavior", []): st.markdown(f"- {r}")
                    st.markdown("**PC Update Rules:**")
                    for p in parsed.get("pc_update_rules", []): st.markdown(f"- {p}")

            with c2:
                with st.expander("🔌 Top Level Interfaces", expanded=True):
                    if "top_level_interfaces" in parsed: st.table(parsed["top_level_interfaces"])
                
                with st.expander("🎛️ Control Signals", expanded=True):
                    if "control_signals" in parsed: st.table(parsed["control_signals"])
                    
            st.divider()
            st.subheader("Data Path & Logic Rules")
            c3, c4 = st.columns(2)
            with c3:
                with st.expander("🏎️ Datapath Connectivity", expanded=True):
                    for d in parsed.get("datapath", []): st.markdown(f"- {d}")
                with st.expander("⚖️ Branch Rules", expanded=True):
                    for b in parsed.get("branch_rules", []): st.markdown(f"- {b}")
                    
            with c4:
                with st.expander("📦 Memory Map", expanded=True):
                    for m in parsed.get("memory_map", []): st.markdown(f"- {m}")
                with st.expander("💾 Load/Store Rules", expanded=True):
                    for ls in parsed.get("load_store_rules", []): st.markdown(f"- {ls}")

            st.divider()
            c5, c6 = st.columns(2)
            with c5:
                with st.expander("🎯 Instruction Coverage Strategy", expanded=True):
                    cov = parsed.get("instructions_coverage", {})
                    st.markdown("**✅ Must Support:**")
                    for cat in cov.get("must_support", []): st.markdown(f"- **{cat['category']}**: {', '.join(cat['instructions'])}")
                    st.markdown("**⚠️ Optional / Ignored:**")
                    st.markdown(f"{', '.join(cov.get('optional_or_ignored', []))}")
                    st.markdown("**🚫 Not Required for riscv-tests:**")
                    st.markdown(f"{', '.join(cov.get('not_required_for_riscv_tests', []))}")
            with c6:
                with st.expander("🧪 Testbench Requirements", expanded=True):
                    for tb in parsed.get("testbench_requirements", []): st.markdown(f"- {tb}")

            st.divider()
            st.subheader("🧩 Hardware Modules & Instantiation")
            with st.expander("🏗️ Component Build Order", expanded=True):
                ordered = parsed.get("module_order", [])
                st.markdown(" ➡️ ".join([f"`{m}`" for m in ordered]))
                
            for mod in parsed.get("modules", []):
                with st.expander(f"📦 {mod.get('module_name', 'Unknown')} - {mod.get('purpose', '')}"):
                    st.markdown("**🔗 Dependencies:** " + (", ".join([f"`{d}`" for d in mod.get("depends_on", [])]) if mod.get("depends_on") else "None (Leaf Module)"))
                    
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        st.markdown("**📥 Inputs:**")
                        if mod.get("inputs"): st.table(mod["inputs"])
                    with mc2:
                        st.markdown("**📤 Outputs:**")
                        if mod.get("outputs"): st.table(mod["outputs"])
                    
                    st.markdown("**⚙️ Internal Behavior:**")
                    for ib in mod.get("internal_behavior", []): st.markdown(f"- {ib}")
                    
                    st.markdown("**⚠️ Corner Cases to Handle:**")
                    for cc in mod.get("corner_cases", []): st.markdown(f"- {cc}")
                        
        except json.JSONDecodeError:
            st.error("❌ Failed to parse the Architect's JSON.")
            st.code(clean_text)
            
    except Exception as e:
        status_text.error(f"API Error: {e}")
