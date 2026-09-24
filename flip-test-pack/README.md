🌐 [English](README.md) | [한국어](README_KO.md)

# CJK-Flip Test Pack for Zoo Code Custom Mode
## Identical Injection & Deterministic Evaluation Kit (Zero-External-Dependency)

> [!IMPORTANT]
> **Measurement Target Declaration**  
> All metrics and numerical scores produced by this test pack do **NOT** indicate the "general intelligence or overall capability of the model."  
> These results solely and objectively measure and report the **"Output Divergence across Providers/Quantizations under Identical Harness Conditions (Zoo Code Custom Mode) with Identical Prompt Injections."**

---

## 0. Background, Objective, and Experimental Design

### 0.1 Background and Problem Statement
Even when running identical foundational model weights, VS Code-based LLM assistants (such as Zoo Code) exhibit subtle output divergence and quality degradation depending on backend serving providers (Anthropic Direct, OpenAI Direct, OpenRouter, DeepInfra, Together, local Ollama/vLLM, etc.) and quantization precision levels (FP16, FP8, INT8, FP4, AWQ, GGUF Q4_K_M, etc.).

In particular, **CJK (Chinese, Japanese, Korean) multilingual processing** exhibits notable vulnerabilities:
1. **Low-Frequency Token Loss**: Token embeddings for rare Hanzi/Hanja, obscure characters (僻字), and personal/geographical proper nouns are the first to degrade during aggressive quantization (such as FP4).
2. **Glyph Confusion**: When 1:1 glyph conversions between Simplified Chinese, Traditional Chinese (Orthodox), Japanese Shinjitai (新字体), and Kyujitai (舊字體) are requested without contextual hints, model conversion accuracy drops sharply under quantization.
3. **Strict Format Deviations**: Compliance with JSON schemas, sentence count constraints, and negative constraints (e.g., prohibition of Chinese characters) tends to collapse in lighter-weight or heavily quantized backends.

### 0.2 Experimental Design Principles
- **Strictly Controlled Variables**: Zoo Code Custom Mode configuration (`test_cjk_flip`), temperature, prompt injection sequence, test prompts, and workspace directory environment are 100% fixed and held constant.
- **Sole Independent Variable**: Only the Zoo Code **backend provider configuration (Provider Profile / Quantization)** is swapped.
- **Dependent Variables**: Pass/fail outcomes across **298 deterministic checks** distributed across 40 prompts in 8 domains, alongside category-level accuracy differentials (%p).

---

## 1. Directory and Artifact Structure

```text
flip-test-pack/
├── README.md              # Setup, execution, evaluation procedures, control checklist, limitations, and assumptions (This document, English)
├── README_KO.md           # Korean Documentation (한국어 상세 가이드)
├── run_score.bat          # [1-Click] Windows Explorer double-click single-run evaluation & auto-popup browser dashboard (English default)
├── run_score_ko.bat       # [1-Click] Windows Explorer double-click single-run evaluation in Korean mode
├── run_score_runs.bat     # [1-Click] Windows Explorer double-click multi-run evaluation (--runs) & auto-popup browser dashboard
├── report.html            # Pure HTML5 + inline SVG/CSS responsive visual dashboard report
├── run_manifest.md        # Experiment manifest logging timestamps, model IDs, quantization tiers, and client versions
├── checks_master.json     # Master specification of 298 checks across 40 prompts (JSON schemas & ground truth)
├── data_validation.log    # Audit log of 100% independent recalculation & 20% random sample cross-verification
├── score_results.py       # Zero-dependency deterministic evaluation & HTML dashboard generation script (Python stdlib)
├── prompts/
│   ├── MEGA_BATCH.md      # [1-Click Copy-Paste] Unified Mega-Batch prompt containing all 40 questions (F1–F10)
│   ├── T01.md ~ T05.md    # [F1] Language Identity Flip (5 questions)
│   ├── T06.md ~ T10.md    # [F3] Glyph Transformation: Simp↔Trad, Shin↔Kyu (5 questions, 130 checks)
│   ├── T11.md ~ T15.md    # [F6] Precision String Manipulation (5 questions)
│   ├── T16.md ~ T20.md    # [F7] Long-Context Exact Citation (5 questions, 300–500 character excerpt slicing)
│   ├── T21.md ~ T25.md    # [F8] Output Format Constraints (5 questions, JSON/CSV/sentence count/negative constraints)
│   ├── T26.md ~ T30.md    # [F4] Round-Trip Translation (5 questions, chrF score & glossary preservation)
│   ├── T31.md ~ T35.md    # [F9] Rare Hanzi & Classical Idioms (5 questions, low-frequency tokens)
│   └── T36.md ~ T40.md    # [F10] Multi-Step Reasoning (5 questions, intermediate steps & final conclusions)
├── responses/             # Directory where user saves provider responses (auto-detects Mega-Batch / individual files)
│   ├── sample_fp8/        # [Sample] Lossless FP8 reference response (MEGA.md + T01~T40.md, 100% pass)
│   └── sample_fp4/        # [Sample] FP4-level quantization degradation response (MEGA.md + T01~T40.md, 97.23% pass)
└── tests/
    └── test_scorer.py     # Scorer self-verification test suite (58 tests covering Mega-Batch, truncation, fairness, HTML)
```

---

## 2. Test Prompt Category Architecture (Total 40 Questions · 298 Checks)

| Category Code | Category Name | Questions | Checks | Primary Discriminative Target & Quantization Sensitivity |
| :---: | :--- | :---: | :---: | :--- |
| **F1** | Language Identity Flip | 5 | 25 | Identification of ambiguous Hanzi-heavy text language (Mixed Script / Japanese / Simplified / Traditional) and accurate Korean rendering |
| **F3** | Glyph Transformation | 5 | 130 | 1:1 mapping of 25 characters across Simplified↔Traditional, Shinjitai↔Kyujitai (1 check per character, core check density) |
| **F6** | Precision String Manipulation | 5 | 24 | CJK character counts, N-th character extraction, even-index subsequence, string reversal, specific character frequency counts |
| **F7** | Long-Context Exact Citation | 5 | 20 | Lossless verbatim reproduction of programmatically sliced passages from 300–500 character CJK source texts |
| **F8** | Output Format Constraints | 5 | 24 | Strict JSON schemas, exact 3-sentence counts, prohibition of Chinese/English characters (negative constraints), CSV formatting |
| **F4** | Round-Trip Translation | 5 | 25 | Two-stage round-trip translation (Korean → Japanese/Chinese → Korean), mandatory glossary retention, chrF character n-gram similarity |
| **F9** | Rare Hanzi & Classical Idioms | 5 | 25 | Ultra-rare repeated characters (疊字), polyphonic characters (多音字), classical idioms, Joseon official title standard readings and glosses |
| **F10** | Multi-Step Reasoning | 5 | 25 | Sexagenary cycle year calculation, Hanzi total stroke count cipher sequences, 5x5 Baduk grid coordinates, traditional measurement conversions |
| **Total** | **8 Categories** | **40** | **298** | **High discriminative resolution capable of detecting fine-grained 0.5%p differentials (FP4 vs. FP8)** |

### Common Strict Authoring Guidelines
1. **Fully Self-Contained**: All reading passages, character lists, formulas, and glossaries are 100% embedded within prompt bodies, requiring no external web search or file lookup.
2. **Marker Isolation (`⟪ ... ⟫`)**: Responses must be enclosed strictly within the Unicode markers `⟪` and `⟫`. This eliminates extraneous conversational pleasantries or preamble and allows precise extraction of raw model output.
3. **Standardized Metadata**: Every prompt file (`Txx.md`) explicitly specifies its category, difficulty rating (1–3), anticipated sensitivity tags (`quant-sensitive`, `format-sensitive`, `rare-token`), and a one-sentence rationale for quantization sensitivity.

---

## 3. Answer Key Reliability & Mathematical/Algorithmic Verification Proof

The answer keys in this test pack were not manually transcribed or intuited; they were **100% verified mathematically and programmatically** via the generator script (`generate_pack.py`):

1. **1:1 Glyph Mapping & 20% Random Sample Independent Cross-Verification**:
   - The 125 glyph conversions in F3 (T06–T10) were fully validated against the Unicode CJK Unified Ideographs standard block, Kangxi Dictionary tables, and official Shinjitai/Kyujitai conversion tables.
   - An independent **20% random sample (25 characters)** was extracted and cross-checked against standard Unicode character names.
2. **Deterministic String Operations & Reversal Recalculation**:
   - Character counts, N-th index characters, character frequency counts, and reversed strings in F6 (T11–T15) were independently recalculated and verified using Python standard string slicing and Counter algorithms.
3. **F7 Long-Context Algorithmic Slicing**:
   - The 300–500 character passages (`text16`–`text20`) were defined in code, and target slice segments were extracted directly via programmatic index slicing (`text[start:end]`), completely precluding human typographical errors.
4. **Validation Record (`data_validation.log`)**:
   - All 298 checks across all 40 questions passed validation with zero errors, and the detailed audit log is preserved in `data_validation.log`.

---

## 4. Step-by-Step Execution Guide

### 📋 Which Prompts to Inject? (Prompt File Location & Copy Guide)

> [!TIP]
> ### 🎯 Exactly What to Copy & Where to Save (Quick Reference)
> *"Which file should I open and what exact prompt do I copy?"* — Choose either **Method 1 (Strongly Recommended)** or **Method 2** below:
>
> | Injection Mode | Source Prompt File to Open | What Exactly to Copy | Where to Paste | Where to Save Model Output |
> | :--- | :--- | :--- | :--- | :--- |
> | **🌟 Method 1 (Strongly Recommended)<br>1-Click Mega-Batch** | **[`prompts/MEGA_BATCH.md`](prompts/MEGA_BATCH.md)**<br>*(from repo root: `flip-test-pack/prompts/MEGA_BATCH.md`)* | **Select All (Ctrl+A, Ctrl+C)**<br>Entire file contains all 40 questions (T01~T40, 298 checks) | Zoo Code chat box with **`test_cjk_flip`** mode active | **[`responses/{provider}/MEGA.md`](responses/)**<br>*(single file containing full model response)* |
> | **🔹 Method 2<br>Individual Question Mode** | **[`prompts/T01.md`](prompts/T01.md)** through **[`T40.md`](prompts/T40.md)**<br>*(40 separate files in [**`prompts/`**](prompts/))* | Content inside the **`## 복붙용 프롬프트`** (`## Copy-Paste Prompt`) code block only | Zoo Code chat box with **`test_cjk_flip`** mode active | **[`responses/{provider}/T01.md`](responses/)** through **`T40.md`**<br>*(40 separate response files)* |

### Step 1: Controlled Environment Setup (Zoo Code Custom Mode)
1. Create an empty folder and open it in VS Code (ensuring a clean workspace free from global instruction files like `.cursorrules`, `.windsurfrules`, or `.gemini/rules`).
2. Open the Zoo Code extension and create a new Custom Mode:
   - **Mode Name**: `test_cjk_flip` (or `test_cjp_flip`)
   - **Role Definition**: Enter the following single English sentence verbatim:
     > `Perform only the given task and provide no unnecessary explanations.`
   - **Tool Permissions (Tools/MCP)**: Revoke all tool permissions (File Edit, Write, Terminal, MCP, etc.) completely (**`None`**) to prevent the model from creating scratch scripts or altering workspace files.
3. If the provider profile supports temperature configuration, lock it to **`0`**.
4. **Single Independent Variable Isolation**: Maintain the exact same mode configuration, empty workspace, and prompt injection sequence across all runs, varying **only the backend provider configuration (Provider Profile / Quantization)**.

### Step 2: Running Provider A (Mega-Batch or Individual Mode)
- **Method 1 (Strongly Recommended: 1-Click Copy-Paste Mega-Batch Mode)**:
  1. In Zoo Code, select the **`test_cjk_flip`** mode and set the target provider (Provider A).
  2. Open **[`prompts/MEGA_BATCH.md`](prompts/MEGA_BATCH.md)** (from repo root: `flip-test-pack/prompts/MEGA_BATCH.md`), copy the entire file contents (**Ctrl+A, Ctrl+C**), and paste it into the Zoo Code chat input box once.
  3. Copy the model's complete output containing all 40 question blocks (`=== [T01] ===` through `=== [T40] ===`) and save it as a single file at:
     **[`responses/{provider-a}/MEGA.md`](responses/)** (from repo root: `flip-test-pack/responses/{provider-a}/MEGA.md`).
- **Method 2 (Traditional Individual Mode)**:
  1. Verify **`test_cjk_flip`** mode is active in Zoo Code and target Provider A.
  2. Open each prompt file from **[`prompts/T01.md`](prompts/T01.md)** through **[`T40.md`](prompts/T40.md)** (in [**`prompts/`**](prompts/)) sequentially, copy the text inside the **`## 복붙용 프롬프트`** (`## Copy-Paste Prompt`) code block, and paste it into Zoo Code.
  3. Save each individual response to **[`responses/{provider-a}/T01.md`](responses/)** through **`T40.md`**.

### Step 3: Running Provider B
1. In Zoo Code, switch the profile to **Provider B** (e.g., `openrouter-q4` or `provider_fp4`).
2. Execute prompt injection using the identical method:
   - **Method 1 (Mega-Batch)**: Paste from **[`prompts/MEGA_BATCH.md`](prompts/MEGA_BATCH.md)** and save full response to **[`responses/{provider-b}/MEGA.md`](responses/)**.
   - **Method 2 (Individual)**: Paste from **[`prompts/T01.md`](prompts/T01.md)** ~ **[`T40.md`](prompts/T40.md)** (in [**`prompts/`**](prompts/)) and save responses to **[`responses/{provider-b}/T01.md`](responses/)** ~ **`T40.md`**.
*(Conducting runs in close succession is recommended to minimize temporal or server load variations).*

### Step 4: 1-Click Automated Evaluation & Dashboard Inspection
- **Method 1 (Windows Explorer Double-Click — Fastest & Most Convenient)**:
  - Double-click **`run_score.bat`** (or **`run_score_ko.bat`** for Korean mode) in either the repository root or the `flip-test-pack/` directory.
  - The Python runtime is detected automatically, scoring executes, and **the visual dashboard (`report.html`) opens immediately in your default web browser.**
- **Method 2 (Terminal CLI Manual Execution)**:
  ```bash
  # Inside the flip-test-pack directory:
  python score_results.py

  # Or from the repository root:
  python flip-test-pack/score_results.py
  ```
- **Generated Artifacts**:
  1. stdout terminal: Instant **Category × Provider Accuracy Matrix** and **Pairwise Provider Deltas (%p)**
  2. `report.html`: **Responsive dashboard featuring inline SVG bar charts, diverging delta charts, summary cards, and failure detail accordions**
  3. `results_summary.md`: Auto-generated Markdown summary report
  4. `failures.csv`: Detailed log of failed checks (omitted automatically on 100% pass)

### Step 5: Fine-Grained Convergence Verification (Repeated Runs)
- When the accuracy delta between two providers is subtle (**0.5%p to 2.0%p, typical of FP4 vs. FP8 differences**), perform **3 repeated runs on the specific provider pair** rather than exhaustive testing across all models.
- Add multi-run files (`MEGA.r2.md`, `MEGA.r3.md` for Mega-Batch; `Txx.r2.md`, `Txx.r3.md` for Individual Mode) and run:
  - **Double-click**: **`run_score_runs.bat`**
  - **CLI**: `python score_results.py --runs`
- This visualizes the run-average accuracy alongside the **Cross-Run Disagreement Rate**, helping discern whether deviations stem from stochastic sampling noise or systemic quantization weight degradation.

### Step 6: Experiment Documentation
- Record provider names, official model IDs, quantization designations, run timestamps, and Zoo Code versions in `run_manifest.md` to ensure reproducibility.

---

## 5. Control Checklist

| Inspection Item | Control Standard | Verified |
| :--- | :--- | :---: |
| **Prompt Injection** | Injected from T01 to T40 (or MEGA_BATCH) in identical sequence without omissions | [ ] |
| **Custom Mode** | `test_cjk_flip` mode active (Role: `Perform only the given task and provide no unnecessary explanations.`) | [ ] |
| **Tool Permissions** | All Zoo Code Tool/MCP/Terminal/File-Edit permissions fully disabled (`None`) | [ ] |
| **Single Independent Variable** | Environment and mode 100% identical; only Provider Profile / Quantization altered | [ ] |
| **Temperature** | Fixed to `0.0` in provider profile (when supported) | [ ] |
| **Environment Isolation** | Empty workspace used; no global rule files (`.cursorrules`, etc.) or memory interference | [ ] |
| **Marker Preservation** | `⟪` and `⟫` markers preserved intact in response files | [ ] |

---

## 6. Statistical Limitations & Interpretation Guidelines

When interpreting results from this test pack, consider the following statistical boundaries:

1. **Single-Run Margin of Error**:
   - This test pack comprises 298 independent checks. Under a 95% Confidence Interval (CI) of a Binomial Distribution, the sampling error margin for a single run is approximately **±3.0%p to ±3.5%p**.
   - Consequently, **single-run results should be interpreted primarily as directional indicators**.
2. **Discerning Fine-Grained Deltas (0.5–2.0%p for FP4 vs. FP8)**:
   - To establish statistical significance for subtle performance differences between 0.5%p and 2.0%p, perform **at least 3 repeated runs (`--runs`)** on the target provider pair to verify mean convergence and cross-run disagreement rates.
3. **Uncontrollable Residual Factors (Harness Prose & Adapter Differences)**:
   - Differences in gateway-level system wrappers, tokenizer serialization nuances, or client-side stream buffering introduced by various API providers cannot be 100% controlled externally.
   - Therefore, observed deltas must never be misconstrued as absolute intrinsic model superiority, but should strictly be designated as **"Systemic Differences under Identical Harness Conditions."**

---

## 7. Operational Assumptions

To balance practical utility with scientific rigor, this test pack adopts the following reasonable assumptions:

1. **Marker-Based Extraction Hypothesis**:
   - Assumes the model can comply with formatting instructions to enclose its answer between `⟪` and `⟫` (or `《 ... 》`).
   - If markers are completely absent, it is treated as a strict formatting compliance failure, yielding 0 points on strict formatting checks (exact, json_schema, etc.).
2. **Standard Unicode Normalization Hypothesis**:
   - Variations in fullwidth/halfwidth forms and CJK compatibility ideographs are handled through NFKC and NFC normalization pipelines, ensuring scores are not unfairly penalized by pure encoding standard differences.
3. **Non-LLM Deterministic Evaluation Hypothesis**:
   - To prevent stochastic variance, evaluation costs, and non-reproducibility associated with LLM-as-a-Judge paradigms, this scorer relies **100% on deterministic rules (Exact, Regex, Numeric, Schema, Levenshtein, chrF)**.

---

## 8. Scorer CLI Options

`score_results.py` is a standalone script utilizing solely the Python 3 standard library—no `pip install` required.

```bash
# Standard evaluation (executed inside flip-test-pack/)
python score_results.py

# Multi-run evaluation mode (when repeated run files such as MEGA.r2.md or Txx.r2.md exist)
python score_results.py --runs

# Run in Korean mode
python score_results.py --lang ko

# Custom file paths and HTML dashboard output specification
python score_results.py --master checks_master.json --responses responses --output-summary results_summary.md --output-csv failures.csv --output-html report.html
```

### Running Scorer Self-Verification Unit Tests
```bash
# Run all 58 unit tests (Mega-Batch, token truncation, fairness regression, HTML dashboard generation)
python tests/test_scorer.py
```
*(All 58 tests must pass (OK) to guarantee test kit integrity).*
