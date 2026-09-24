# -*- coding: utf-8 -*-
"""
Populate sample response fixtures in flip-test-pack/responses/
- sample_fp8: ~100% fidelity (r1, r2, r3)
- sample_fp4: ~97.2% fidelity (quantization errors in F3 glyphs & F9 rare tokens, r1, r2, r3)
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PACK_DIR = BASE_DIR / "flip-test-pack"
RESP_DIR = PACK_DIR / "responses"

with open(PACK_DIR / "checks_master.json", "r", encoding="utf-8") as f:
    master = json.load(f)

fp8_dir = RESP_DIR / "sample_fp8"
fp4_dir = RESP_DIR / "sample_fp4"
fp8_dir.mkdir(parents=True, exist_ok=True)
fp4_dir.mkdir(parents=True, exist_ok=True)

for pid, pdata in master["prompts"].items():
    gt = pdata["expected_marker_content"]
    
    # FP8: perfect response (r1)
    (fp8_dir / f"{pid}.md").write_text(f"⟪\n{gt}\n⟫", encoding="utf-8")
    
    # FP4: slight degradation (r1)
    fp4_content = gt
    if pid == "T06":
        # Leave '龍' as simplified '龙' (1 character error)
        fp4_content = gt.replace("龍", "龙")
    elif pid == "T08":
        # Leave '瀧' as '滝' (1 character error)
        fp4_content = gt.replace("瀧", "滝")
    elif pid == "T31":
        # Fail extreme rare token 灪 (writes 율 instead of 울)
        fp4_content = gt.replace("5. 灪: 울", "5. 灪: 율")
    elif pid == "T37":
        # Calculation slip in intermediate step 3
        fp4_content = gt.replace("5. 최종결과: 222", "5. 최종결과: 217")
        
    (fp4_dir / f"{pid}.md").write_text(f"⟪\n{fp4_content}\n⟫", encoding="utf-8")

# Add repeated runs (r2, r3) for sensitivity-testing items (F3, F9) to support --runs out-of-the-box
for pid in ["T06", "T08", "T31", "T37"]:
    gt = master["prompts"][pid]["expected_marker_content"]
    
    # FP8: remains perfect in r2 and r3
    (fp8_dir / f"{pid}.r2.md").write_text(f"⟪\n{gt}\n⟫", encoding="utf-8")
    (fp8_dir / f"{pid}.r3.md").write_text(f"⟪\n{gt}\n⟫", encoding="utf-8")
    
    # FP4: stochastic variations across runs
    if pid == "T06":
        # r2: '門' is left as '门'
        r2_content = gt.replace("門", "门")
        # r3: both '龍' and '門' corrupted
        r3_content = gt.replace("龍", "龙").replace("門", "门")
    elif pid == "T08":
        r2_content = gt.replace("瀧", "滝")
        r3_content = gt.replace("櫻", "桜")
    elif pid == "T31":
        r2_content = gt.replace("5. 灪: 울", "5. 灪: 율")
        r3_content = gt.replace("5. 灪: 울", "5. 灪: [미상]")
    elif pid == "T37":
        r2_content = gt.replace("5. 최종결과: 222", "5. 최종결과: 220")
        r3_content = gt.replace("5. 최종결과: 222", "5. 최종결과: 222") # occasional recovery
        
    (fp4_dir / f"{pid}.r2.md").write_text(f"⟪\n{r2_content}\n⟫", encoding="utf-8")
    (fp4_dir / f"{pid}.r3.md").write_text(f"⟪\n{r3_content}\n⟫", encoding="utf-8")

# ==============================================================================
# Generate MEGA.md, MEGA.r2.md, MEGA.r3.md fixtures for 1-click Mega-Batch evaluation
# ==============================================================================
def get_fp4_content(pid: str, run: str) -> str:
    content = master["prompts"][pid]["expected_marker_content"]
    if run == "r1":
        if pid == "T06":
            return content.replace("龍", "龙")
        elif pid == "T08":
            return content.replace("瀧", "滝")
        elif pid == "T31":
            return content.replace("5. 灪: 울", "5. 灪: 율")
        elif pid == "T37":
            return content.replace("5. 최종결과: 222", "5. 최종결과: 217")
    elif run == "r2":
        if pid == "T06":
            return content.replace("門", "门")
        elif pid == "T08":
            return content.replace("瀧", "滝")
        elif pid == "T31":
            return content.replace("5. 灪: 울", "5. 灪: 율")
        elif pid == "T37":
            return content.replace("5. 최종결과: 222", "5. 최종결과: 220")
    elif run == "r3":
        if pid == "T06":
            return content.replace("龍", "龙").replace("門", "门")
        elif pid == "T08":
            return content.replace("櫻", "桜")
        elif pid == "T31":
            return content.replace("5. 灪: 울", "5. 灪: [미상]")
        elif pid == "T37":
            return content.replace("5. 최종결과: 222", "5. 최종결과: 222")
    return content

for run_suffix, run_id in [("", "r1"), (".r2", "r2"), (".r3", "r3")]:
    # FP8
    fp8_mega = []
    for pid, pdata in master["prompts"].items():
        gt = pdata["expected_marker_content"]
        fp8_mega.append(f"=== [{pid}] ===\n⟪\n{gt}\n⟫")
    (fp8_dir / f"MEGA{run_suffix}.md").write_text("\n\n".join(fp8_mega), encoding="utf-8")
    
    # FP4
    fp4_mega = []
    for pid, pdata in master["prompts"].items():
        c = get_fp4_content(pid, run_id)
        fp4_mega.append(f"=== [{pid}] ===\n⟪\n{c}\n⟫")
    (fp4_dir / f"MEGA{run_suffix}.md").write_text("\n\n".join(fp4_mega), encoding="utf-8")

print(f"Populated responses and multi-run fixtures (individual + MEGA) in {fp8_dir}")
print(f"Populated responses and multi-run fixtures (individual + MEGA) in {fp4_dir}")

