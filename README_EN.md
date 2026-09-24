🌐 [English](README_EN.md) | [한국어](README.md)

# CJK-Flip Test Pack for Zoo Code Custom Mode — Identical Injection & Deterministic Evaluation Kit

This repository provides a zero-external-dependency automated evaluation kit designed to measure fine-grained output quality divergence across LLM providers and quantization tiers (e.g., FP4 vs. FP8) in Zoo Code Custom Mode environments across 298 deterministic checks.

> **Measurement Target Declaration**: The results produced by this kit do not measure "general model intelligence or capability," but rather **"output divergence across providers/quantizations under identical harness conditions."**

---

## ⚡ 1-Click Windows Explorer Execution

You can run evaluations and launch visual dashboards directly from Windows Explorer with a simple double-click—no terminal or manual command entry required:

1. **Double-click `run_score.bat`**:
   - Automatically detects your system Python environment (`py` or `python`) and executes a single-run evaluation immediately.
   - Once evaluation completes, the **interactive visual dashboard (`report.html`) featuring inline SVG graphs pops up automatically in your default web browser**.
   - The terminal window remains open (`pause`) so you can review console logs without premature closing.
2. **Double-click `run_score_runs.bat`**:
   - Performs multi-run repeated evaluation (`--runs`), visualizing run-average accuracy and cross-run disagreement rates.

*(Double-click execution is supported from both the repository root and the `flip-test-pack/` directory).*

---

## 🛠️ Zoo Code Custom Mode Standard Configuration (`test_cjk_flip`)

To ensure strictly identical harness conditions and uncontaminated single-variable isolation, configure a dedicated Custom Mode in Zoo Code as follows:

1. **Create Custom Mode**: Set the mode name to **`test_cjk_flip`** (or `test_cjp_flip`).
2. **Role Definition**: Enter the following single English sentence verbatim to prevent conversational filler, disclaimers, or unsolicited explanations:
   > `Perform only the given task and provide no unnecessary explanations.`
3. **Tools**: Revoke all tool permissions (File Edit, Write, Terminal, MCP, etc.) completely (**`None`**) so the model cannot create scratch scripts or modify workspace files.
4. **Single Independent Variable Control**: Keep all environmental variables 100% fixed in an empty workspace, altering **only the backend provider configuration (Provider Profile / Quantization)** between runs.

---

## 🚀 1-Click "Mega-Batch" Workflow

To eliminate the operational fatigue of copying and pasting 40 separate prompts, a single-injection Mega-Batch format is fully supported:

1. In Zoo Code, select the `test_cjk_flip` mode and set the target provider.
2. Copy the entire contents of `flip-test-pack/prompts/MEGA_BATCH.md` and paste it into the Zoo Code input box once.
3. Save the model's complete output containing all 40 questions into a single file at `flip-test-pack/responses/{provider}/MEGA.md`.
4. Double-click `run_score.bat`. The scorer automatically detects the Mega-Batch format, parses each item deterministically, and issues diagnostic warnings if token truncation occurs.

---

## 📊 Visual Graph Dashboard (`report.html`)

Without relying on heavy external dependencies (such as matplotlib, npm, or chart libraries), the Python standard library generates a standalone, fully responsive HTML5 dashboard with inline SVG graphics:
- **Provider Overall Accuracy Cards**: Comprehensive score summaries, pass rates, status badges, and run-variance indicators (with run-average score aligned with accuracy).
- **8-Category Comparative Grouped Bar Charts**: Inline SVG charts breaking down provider accuracy (%) across categories F1 through F10.
- **Multi-Run Accuracy Breakdown Charts**: Luminance-tiered bars (r1/r2/r3) with run-average markers illustrating stochastic variance.
- **Failure Count Distribution Stacked Bars**: Granular category-level breakdown of failed checks for each provider.
- **Pairwise Provider Delta (%p) Charts**: Diverging horizontal bar charts highlighting quantization degradation or advantages at a glance.
- **Failure Detail Accordion**: Item-by-item 1:1 contrast showing check ID, expected value, actual model output, and failure cause.
- **Token Truncation Diagnostic Badges**: Automated detection and actionable remediation advice for output truncated due to `max_tokens` limits.
- **Dark/Light Mode Support**: Single-click instant theme toggle with accessible color contrast.

---

## 💻 CLI Manual Execution

```bash
# Navigate to the flip-test-pack directory
cd flip-test-pack

# Run scorer self-verification unit tests (all 56 pass)
python tests/test_scorer.py

# Single-run evaluation and dashboard generation
python score_results.py

# Multi-run evaluation with average accuracy and cross-run disagreement analysis
python score_results.py --runs
```

For detailed setup, execution, and evaluation procedures, control checklists, statistical limitations, and operational assumptions, see [flip-test-pack/README_EN.md](flip-test-pack/README_EN.md) (or [한국어 가이드](flip-test-pack/README.md)).
