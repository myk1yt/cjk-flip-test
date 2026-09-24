#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoo Code Custom Mode CJK-Flip Evaluation Scorer (score_results.py)

Deterministic Scoring Engine for CJK-Flip Test Pack.
Evaluates LLM responses across 8 categories (40 prompts, 290+ checks)
using exact deterministic rules with zero external dependencies.

Features:
- Marker extraction (⟪ ... ⟫, 《 ... 》, ⟨ ... ⟩) with template echo filtration
- Unicode normalization (NFKC, fullwidth/halfwidth, NFC, whitespace/punct filtering)
- Check handlers: exact, contains, regex, char_count, numeric, json_schema, levenshtein0, chrf
- General extract_regex support across all check types
- Category x Provider accuracy matrix (stdout + results_summary.md)
- Pairwise provider difference (%p) & detailed failures.csv
- Multi-run analysis (--runs): per-run breakdown, run average (회차 평균), cross-run disagreement rate
"""

import os
import sys
import re
import json
import csv
import math
import html
import argparse
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ==============================================================================
# 1. Text Normalization & Helper Algorithms
# ==============================================================================

def normalize_unicode(s: str) -> str:
    """Normalize unicode to standard NFC after NFKC decomposition."""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKC", s)
    s = unicodedata.normalize("NFC", s)
    return s

def normalize_text(s: str, option: str = "none") -> str:
    """Apply check-specific normalization."""
    if not isinstance(s, str):
        s = str(s)
    s = normalize_unicode(s)
    
    if option == "none":
        return s.strip()
    elif option == "ignore_whitespace":
        return re.sub(r"\s+", "", s)
    elif option == "ignore_punctuation":
        # Strip ASCII + CJK punctuation (、。 「」 『』 【】 〖〗 ・ ー ～ … — ‥ ･ ﹁ ﹂ etc.)
        s_no_punct = re.sub(r"[\s\.,\/#!$%\^&\*;:{}=\-_`~()\[\]<>《》⟪⟫'\"?+、。・･ー‐‑‒–―—…‥「」『』【】〖〗﹁﹂﹃﹄〈〉⟨⟩〜]+", "", s)
        return s_no_punct
    elif option == "case_fold":
        return s.strip().lower()
    elif option == "strip":
        return s.strip()
    elif option == "lines":
        lines = [line.strip() for line in s.splitlines() if line.strip()]
        return "\n".join(lines)
    return s.strip()

def extract_marker_content_detailed(text: str) -> Tuple[str, bool, str]:
    """
    Like extract_marker_content but also reports the marker source:
    Returns (extracted_content, marker_found_flag, marker_source) where marker_source is
    one of "primary" (⟪...⟫), "unclosed" (truncated ⟪ at EOF), "fallback" (《》/⟨⟩ pair),
    or "none" (no usable marker; content is the raw text).
    """
    if not text:
        return "", False, "none"

    placeholders = {
        "[이곳에 답변 작성]",
        "이곳에 답변 작성",
        "[답변 작성]",
        "[여기에 답변 작성]"
    }

    def clean_match(m_str: str) -> str:
        cleaned = m_str.strip()
        # Clean markdown code block wraps if leaked inside marker
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\r?\n", "", cleaned)
        cleaned = re.sub(r"\r?\n```$", "", cleaned.strip()).strip()
        return cleaned

    # 1. Primary mathematical double angle brackets ⟪ ... ⟫ (U+27EA / U+27EB)
    pattern1 = re.compile(r"⟪([\s\S]*?)⟫")
    matches1 = pattern1.findall(text)
    if matches1:
        valid = [m for m in matches1 if m.strip() not in placeholders]
        if valid:
            return clean_match(valid[-1]), True, "primary"

    # 2. Check for unclosed opening marker ⟪ (e.g. truncated response at EOF)
    if "⟪" in text:
        idx = text.rfind("⟪")
        tail = text[idx + 1:].strip()
        tail = re.sub(r"⟫.*$", "", tail, flags=re.DOTALL).strip()
        if tail and tail not in placeholders:
            return clean_match(tail), True, "unclosed"

    # 3. Fallback: fullwidth 《...》 / mathematical ⟨...⟩ pairs.
    #    Used ONLY when exactly ONE valid pair exists in the whole text;
    #    multiple pairs mean prose citations (e.g. "《論語》를 인용"), not an answer marker.
    pattern2 = re.compile(r"《([\s\S]*?)》")
    pattern3 = re.compile(r"⟨([\s\S]*?)⟩")
    fallback_valid = (
        [m for m in pattern2.findall(text) if m.strip() and m.strip() not in placeholders]
        + [m for m in pattern3.findall(text) if m.strip() and m.strip() not in placeholders]
    )
    if len(fallback_valid) == 1:
        return clean_match(fallback_valid[0]), True, "fallback"

    # Marker missing (zero or multiple fallback pairs)
    return clean_match(text), False, "none"


def extract_marker_content(text: str) -> Tuple[str, bool]:
    """
    Extract content strictly enclosed between ⟪ and ⟫ markers.
    Handles:
    - Primary markers ⟪ ... ⟫ (U+27EA / U+27EB)
    - Fullwidth CJK angle brackets 《 ... 》 (U+300A / U+300B)
    - Mathematical angle brackets ⟨ ... ⟩ (U+27E8 / U+27E9)
    - Echoed prompt template filtration (skipping '[이곳에 답변 작성]')
    - Truncated unclosed opening marker ⟪ recovery
    - Stripping code fences inside marker
    Fallback brackets are trusted only when exactly ONE pair exists in the text.
    Returns (extracted_content, marker_found_flag).
    """
    content, found, _ = extract_marker_content_detailed(text)
    return content, found

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute standard Levenshtein distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def compute_chrf(hypothesis: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """
    Compute chrF score (character n-gram F-score) between hypothesis and reference.
    Standard MT evaluation metric (Popovic, 2015).
    """
    hyp = normalize_text(hypothesis, "ignore_whitespace")
    ref = normalize_text(reference, "ignore_whitespace")
    
    if not hyp and not ref:
        return 1.0
    if not hyp or not ref:
        return 0.0
    
    effective_n = min(max_n, len(hyp), len(ref))
    if effective_n == 0:
        return 1.0 if hyp == ref else 0.0
    
    f_scores = []
    for n in range(1, effective_n + 1):
        hyp_ngrams = Counter([hyp[i:i+n] for i in range(len(hyp) - n + 1)])
        ref_ngrams = Counter([ref[i:i+n] for i in range(len(ref) - n + 1)])
        
        overlap = sum((hyp_ngrams & ref_ngrams).values())
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())
        
        prec = overlap / hyp_total if hyp_total > 0 else 0.0
        rec = overlap / ref_total if ref_total > 0 else 0.0
        
        if (beta**2 * prec + rec) > 0:
            f = (1 + beta**2) * (prec * rec) / (beta**2 * prec + rec)
        else:
            f = 0.0
        f_scores.append(f)
        
    return sum(f_scores) / len(f_scores) if f_scores else 0.0

def validate_json_schema(data: Any, schema: dict) -> Tuple[bool, str]:
    """Lightweight recursive JSON Schema validator."""
    expected_type = schema.get("type")
    
    if expected_type == "object":
        if not isinstance(data, dict):
            return False, f"Expected object, got {type(data).__name__}"
        required_keys = schema.get("required", [])
        for k in required_keys:
            if k not in data:
                return False, f"Missing required property '{k}'"
        props = schema.get("properties", {})
        for k, prop_schema in props.items():
            if k in data:
                val = data[k]
                ok, msg = validate_json_schema(val, prop_schema)
                if not ok:
                    return False, f"Property '{k}': {msg}"
    elif expected_type == "array":
        if not isinstance(data, list):
            return False, f"Expected array, got {type(data).__name__}"
        if "minItems" in schema and len(data) < schema["minItems"]:
            return False, f"Array length {len(data)} < minItems {schema['minItems']}"
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            return False, f"Array length {len(data)} > maxItems {schema['maxItems']}"
    elif expected_type == "string":
        if not isinstance(data, str):
            return False, f"Expected string, got {type(data).__name__}"
    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            return False, f"Expected integer, got {type(data).__name__}"
    elif expected_type in ("number", "float"):
        if not (isinstance(data, (int, float)) and not isinstance(data, bool)):
            return False, f"Expected number, got {type(data).__name__}"
    elif expected_type == "boolean":
        if not isinstance(data, bool):
            return False, f"Expected boolean, got {type(data).__name__}"
            
    if "const" in schema:
        if data != schema["const"]:
            return False, f"Value '{data}' != const '{schema['const']}'"
            
    return True, "Valid"

# ==============================================================================
# 2. Check Evaluation Core Engine
# ==============================================================================

def evaluate_check(check: dict, actual_raw: str, marker_found: bool) -> Tuple[bool, float, str]:
    """
    Evaluate a single check.
    Returns (passed, awarded_points, detail_message).
    """
    chk_id = check.get("id", "CHK")
    chk_type = check.get("type", "exact")
    norm_opt = check.get("norm", "none")
    points = float(check.get("points", 1))
    expected = check.get("expected")
    
    # Marker gate: ALL check types require the ⟪ ⟫ answer marker.
    # No full-text fallback credit for format-ignoring outputs (F8 fairness).
    if not marker_found:
        return False, 0.0, "마커 누락 (marker missing): ⟪ ⟫ 출력 없음"

    # Support extract_regex across all check types
    target_raw = actual_raw
    if "extract_regex" in check:
        m = re.search(check["extract_regex"], actual_raw, flags=re.MULTILINE)
        if m:
            target_raw = m.group(1) if m.groups() else m.group(0)
        else:
            return False, 0.0, f"Extraction pattern '{check['extract_regex']}' not found in output"

    norm_actual = normalize_text(target_raw, norm_opt)

    if chk_type == "exact":
        if "char_index" in check:
            idx = int(check["char_index"])
            raw_no_ws = re.sub(r"\s+", "", target_raw)
            clean_actual = normalize_unicode(raw_no_ws)
            # M-4 diagnostic: NFKC normalization must not silently shift char_index positions
            nfkc_note = ""
            if len(clean_actual) != len(raw_no_ws):
                nfkc_note = f" [진단: NFKC 정규화로 길이 {len(raw_no_ws)}→{len(clean_actual)} 변경]"
            norm_expected = normalize_unicode(normalize_text(str(expected), norm_opt))
            if 0 <= idx < len(clean_actual):
                actual_char = clean_actual[idx]
                passed = (actual_char == norm_expected)
                msg = f"Char index {idx} ('{actual_char}' == '{norm_expected}')" if passed else f"Char index {idx} mismatch: expected '{norm_expected}', got '{actual_char}'{nfkc_note}"
                return passed, (points if passed else 0.0), msg
            else:
                return False, 0.0, f"Output length {len(clean_actual)} too short for index {idx}{nfkc_note}"
        else:
            norm_expected = normalize_text(str(expected), norm_opt)
            passed = (norm_actual == norm_expected)
            msg = f"exact match ({norm_actual} == {norm_expected})" if passed else f"Mismatch: expected '{norm_expected}', got '{norm_actual}'"
            return passed, (points if passed else 0.0), msg

    elif chk_type == "contains":
        norm_expected = normalize_text(str(expected), norm_opt)
        passed = (norm_expected in norm_actual)
        msg = f"contains '{norm_expected}'" if passed else f"Substring '{norm_expected}' not found in output"
        return passed, (points if passed else 0.0), msg

    elif chk_type == "regex":
        pattern_str = str(expected)
        try:
            passed = bool(re.search(pattern_str, norm_actual, re.DOTALL))
            msg = f"Regex pattern '{pattern_str}' matched" if passed else f"Regex '{pattern_str}' did not match"
            return passed, (points if passed else 0.0), msg
        except re.error as e:
            return False, 0.0, f"Regex syntax error: {e}"

    elif chk_type == "char_count":
        expected_count = int(expected)
        tol = int(check.get("tolerance", 0))
        target_text = norm_actual
        if norm_opt == "lines":
            lines = [l for l in target_raw.splitlines() if l.strip()]
            actual_count = len(lines)
            passed = abs(actual_count - expected_count) <= tol
            msg = f"Line count {actual_count} (expected {expected_count} ± {tol})" if passed else f"Line count mismatch: got {actual_count}, expected {expected_count} ± {tol}"
            return passed, (points if passed else 0.0), msg

        actual_count = len(target_text)
        passed = abs(actual_count - expected_count) <= tol
        msg = f"Count {actual_count} (expected {expected_count} ± {tol})" if passed else f"Count mismatch: got {actual_count}, expected {expected_count} ± {tol}"
        return passed, (points if passed else 0.0), msg

    elif chk_type == "numeric":
        epsilon = float(check.get("epsilon", 0.0))
        # Search for numbers in target_raw after normalizing fullwidth decimal point and thousands commas
        cleaned_num_text = target_raw.replace("．", ".").replace("，", ",")
        cleaned_num_text = re.sub(r"(?<=\d),(?=\d)", "", cleaned_num_text)
        numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cleaned_num_text)
        if not numbers:
            return False, 0.0, "No numeric value found in output"
        
        target = float(expected)
        found_match = False
        best_val = None
        for n_str in numbers:
            try:
                val = float(n_str)
                if abs(val - target) <= (epsilon + 1e-9):
                    found_match = True
                    best_val = val
                    break
            except ValueError:
                continue
                
        msg = f"Numeric match {best_val} ~ {target}" if found_match else f"No numeric value matching {target} (found: {numbers})"
        return found_match, (points if found_match else 0.0), msg

    elif chk_type == "json_schema":
        # Parse JSON robustly
        try:
            cleaned = target_raw.strip()
            # If wrapped in markdown code fence, extract fence contents
            m_code = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
            if m_code:
                cleaned = m_code.group(1).strip()
            parsed_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return False, 0.0, f"Invalid JSON syntax: {e}"
            
        schema_dict = json.loads(expected) if isinstance(expected, str) else expected
        is_valid, err_msg = validate_json_schema(parsed_data, schema_dict)
        msg = "JSON Schema Valid" if is_valid else f"JSON Schema Error: {err_msg}"
        return is_valid, (points if is_valid else 0.0), msg

    elif chk_type == "levenshtein0":
        max_dist = int(check.get("max_dist", 0))
        norm_expected = normalize_text(str(expected), norm_opt)
        dist = levenshtein_distance(norm_actual, norm_expected)
        # If target has multiple lines and dist > max_dist, attempt line-level match
        if dist > max_dist and "extract_regex" not in check and "\n" in target_raw:
            for line in target_raw.splitlines():
                l_norm = normalize_text(line, norm_opt)
                d = levenshtein_distance(l_norm, norm_expected)
                if d < dist:
                    dist = d
        passed = (dist <= max_dist)
        msg = f"Levenshtein distance {dist} <= {max_dist}" if passed else f"Levenshtein distance {dist} > {max_dist}"
        return passed, (points if passed else 0.0), msg

    elif chk_type == "chrf":
        threshold = float(check.get("threshold", 0.70))
        score = compute_chrf(target_raw, str(expected))
        # If multi-line response and initial score fails threshold, evaluate candidate lines
        if score < threshold and "extract_regex" not in check and "\n" in target_raw:
            for line in target_raw.splitlines():
                l_clean = re.sub(r"^\s*(?:[0-9]+단계|[0-9]+\.|\w+)\s*(?:\([^)]*\))?\s*:\s*", "", line).strip()
                if l_clean:
                    s_line = compute_chrf(l_clean, str(expected))
                    if s_line > score:
                        score = s_line
        passed = (score >= threshold)
        msg = f"chrF score {score:.3f} >= {threshold:.2f}" if passed else f"chrF score {score:.3f} < {threshold:.2f}"
        return passed, (points if passed else 0.0), msg

    return False, 0.0, f"Unknown check type: {chk_type}"

# ==============================================================================
# 3. Test Pack Evaluation Orchestrator
# ==============================================================================

def load_master_checks(master_path: Path) -> dict:
    """Load checks_master.json specification."""
    if not master_path.exists():
        raise FileNotFoundError(f"Master checks file not found at: {master_path}")
    with open(master_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_mega_batch(text: str, source_name: str = "") -> Dict[str, str]:
    """
    Parses a single MEGA.md content containing multiple prompts (T01~T40).
    Headers are matched ONLY at line start with an explicit banner/heading opener,
    e.g. === [Txx] === (also tolerates ===[Txx]===, === Txx ===, --- [Txx] ---,
    ## [Txx], ### **[Txx]** (카테고리), markdown bold wrap, single digit T1~T9).
    In-body references like "- [T03] 문항과 동일" are never treated as headers.
    A monotonic guard drops regressive duplicate banners, and a warning is printed
    to stderr when the parsed question count != 40 instead of silently proceeding.
    Returns dict mapping prompt_id (e.g. 'T01') to raw response snippet.
    """
    if not text:
        return {}

    # Banner shape: opener (=== / --- / ##) + T-id + optional closer, header line only.
    pattern = re.compile(
        r"(?:^|\r?\n)[ \t]*(?:"
        r"(?:\*{0,2}[ \t]*(?:={2,}|-{2,})[ \t]*\[?[ \t]*T0*(40|[1-3]\d|[1-9])\b[ \t]*\]?(?:[ \t]+[^=\-\r\n]*?)?[ \t]*(?:={2,}|-{2,})?[ \t]*\*{0,2}[ \t]*)"
        r"|"
        r"(?:#{1,6}[ \t]*\*{0,2}[ \t]*\[?[ \t]*T0*(40|[1-3]\d|[1-9])\b[ \t]*\]?(?:[ \t]*\*{0,2})?[ \t]*[^\r\n]*?)"
        r")(?:\r?\n|$)",
        re.IGNORECASE
    )

    matches = list(pattern.finditer(text))

    valid_matches = []
    last_num = 0
    for match in matches:
        num = int(match.group(1) or match.group(2))
        if num > last_num:
            valid_matches.append((num, match))
            last_num = num

    parsed = {}
    for i, (num, match) in enumerate(valid_matches):
        pid = f"T{num:02d}"
        start = match.end()
        end = valid_matches[i + 1][1].start() if i + 1 < len(valid_matches) else len(text)
        item_text = text[start:end].strip()
        parsed[pid] = item_text

    if len(parsed) != 40:
        src = f" ({source_name})" if source_name else ""
        print(
            f"[WARNING] MEGA 파싱{src}: 배너 {len(matches)}개, 고유 문항 {len(parsed)}개 "
            f"(기대 40개). 본문/헤더 错位 가능성을 확인하세요: {sorted(parsed.keys())}",
            file=sys.stderr
        )

    return parsed

def discover_responses(responses_dir: Path, is_runs_mode: bool = False, return_modes: bool = False):
    """
    Discover response files supporting both Mega-Batch (MEGA.md) and Individual (T01.md~T40.md) formats.
    Returns:
        If return_modes is False: { provider: { prompt_id: { run_id: file_content } } }
        If return_modes is True: (data, provider_modes) where provider_modes is { provider: "mega" | "individual" }
    """
    data = {}
    provider_modes = {}
    if not responses_dir.exists():
        return (data, provider_modes) if return_modes else data
        
    for provider_dir in sorted(responses_dir.iterdir()):
        if not provider_dir.is_dir():
            continue
        provider = provider_dir.name
        data[provider] = {}
        
        # Case-insensitive search for MEGA files
        mega_files = sorted([
            f for f in provider_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".md" and f.stem.lower().startswith("mega")
        ], key=lambda x: x.name)
        
        if mega_files:
            provider_modes[provider] = "mega"
            for file in mega_files:
                parts = file.stem.split(".")
                if len(parts) > 1 and parts[1].lower() in ("r1", "r2", "r3"):
                    run_id = parts[1].lower()
                elif "_" in file.stem and file.stem.split("_")[1].lower() in ("r1", "r2", "r3"):
                    run_id = file.stem.split("_")[1].lower()
                elif file.stem.lower() == "mega":
                    # Bare MEGA.md is the canonical first run slot
                    run_id = "r1"
                else:
                    # Non-run MEGA file (e.g. MEGA_part2.md): single-mode content stored
                    # in its own slot so it never clobbers the real r1 slot.
                    run_id = "single"

                content = file.read_text(encoding="utf-8")
                parsed_prompts = parse_mega_batch(content, source_name=f"{provider}/{file.name}")
                for pid, snippet in parsed_prompts.items():
                    if pid not in data[provider]:
                        data[provider][pid] = {}
                    data[provider][pid][run_id] = snippet
        else:
            provider_modes[provider] = "individual"
            # Case-insensitive search for T01.md ~ T40.md
            t_files = sorted([
                f for f in provider_dir.iterdir()
                if f.is_file() and f.suffix.lower() == ".md" and re.match(r"^t0*(40|[1-3]\d|[1-9])\b", f.name, re.IGNORECASE)
            ], key=lambda x: x.name)
            
            for file in t_files:
                parts = file.stem.split(".")
                m = re.match(r"^t0*(40|[1-3]\d|[1-9])\b", parts[0], re.IGNORECASE)
                prompt_id = f"T{int(m.group(1)):02d}" if m else parts[0].upper()
                run_id = parts[1].lower() if len(parts) > 1 and parts[1].lower().startswith("r") else "r1"
                
                content = file.read_text(encoding="utf-8")
                if prompt_id not in data[provider]:
                    data[provider][prompt_id] = {}
                data[provider][prompt_id][run_id] = content
                
    return (data, provider_modes) if return_modes else data

def run_scoring(master_path: Path, responses_dir: Path, is_runs_mode: bool = False) -> dict:
    """Run full evaluation matrix across all providers and prompts."""
    master = load_master_checks(master_path)
    prompts_meta = master["prompts"]
    categories = master["categories"]
    discovered, provider_modes = discover_responses(responses_dir, is_runs_mode, return_modes=True)
    
    results = {
        "is_runs_mode": is_runs_mode,
        "providers": list(discovered.keys()),
        "provider_modes": provider_modes,
        "categories": categories,
        "provider_scores": {},
        "provider_runs": {},          # { provider: { run_id: { accuracy, total_points, ... } } }
        "failures": [],
        "pairwise_diff": {},
        "run_disagreements": {},
        "truncation_warnings": {}
    }
    
    for provider, p_data in discovered.items():
        is_mega = provider_modes.get(provider) == "mega"
        # Identify all distinct run IDs present for this provider
        all_runs = sorted(list(set(run_id for runs in p_data.values() for run_id in runs.keys())))
        if not all_runs:
            all_runs = ["r1"]
            
        results["provider_runs"][provider] = {}
        
        # Target runs to evaluate:
        # If is_runs_mode: evaluate only r1/r2/r3 run slots ("single" slot excluded)
        # If single-run mode: evaluate 'r1' if present, otherwise the first available slot
        if is_runs_mode:
            run_slots = [r for r in all_runs if r in ("r1", "r2", "r3")]
            target_runs = run_slots if run_slots else all_runs
        else:
            target_runs = ["r1"] if "r1" in all_runs else all_runs[:1]
            
        # Check truncation for Mega-Batch mode across the evaluated target_runs
        if is_mega:
            all_pids = sorted(prompts_meta.keys())
            for rid in target_runs:
                missing_in_run = [pid for pid in all_pids if not p_data.get(pid, {}).get(rid, "")]
                if missing_in_run:
                    first_missing = missing_in_run[0]
                    run_tag = f"[{rid}] " if is_runs_mode and len(target_runs) > 1 else ""
                    warn_msg = f"⚠️ {run_tag}{first_missing}부터 응답 누락 감지: Max Output Tokens 설정을 4,096~8,192로 늘리세요"
                    w_key = provider if provider not in results["truncation_warnings"] else f"{provider}_{rid}"
                    results["truncation_warnings"][w_key] = {
                        "provider": provider,
                        "run": rid,
                        "first_missing": first_missing,
                        "missing_count": len(missing_in_run),
                        "missing_pids": missing_in_run,
                        "message": warn_msg
                    }
        
        run_scores_list = []
        run_earned_list = []
        cat_scores_per_run = {cat: [] for cat in categories}
        run_extracted_contents = {pid: [] for pid in prompts_meta.keys()}
        
        for run_id in target_runs:
            run_total_points = 0.0
            run_max_points = 0.0
            run_total_checks = 0
            run_passed_checks = 0
            run_category_scores = {
                cat: {"points": 0.0, "max_points": 0.0, "passed": 0, "total": 0, "pct": 0.0}
                for cat in categories
            }
            
            for pid, p_info in prompts_meta.items():
                cat = p_info["category"]
                checks = p_info["checks"]
                runs_dict = p_data.get(pid, {})
                
                # No r1 backfill in any mode: a missing run scores as empty
                raw_resp = runs_dict.get(run_id, "")
                
                if not raw_resp:
                    run_extracted_contents[pid].append("")
                    actual_label = "TRUNCATED_OR_MISSING" if is_mega else "FILE_MISSING"
                    fail_reason = "Response truncated or missing in Mega-Batch (Token Limit Exceeded)" if is_mega else "Response file missing"
                    for chk in checks:
                        pts = float(chk.get("points", 1))
                        run_max_points += pts
                        run_total_checks += 1
                        run_category_scores[cat]["max_points"] += pts
                        run_category_scores[cat]["total"] += 1
                        results["failures"].append({
                            "provider": provider,
                            "run": run_id,
                            "prompt_id": pid,
                            "category": cat,
                            "check_id": chk["id"],
                            "check_type": chk["type"],
                            "expected": str(chk.get("expected", ""))[:50],
                            "actual": actual_label,
                            "passed": False,
                            "points": 0.0,
                            "reason": fail_reason
                        })
                    continue
                    
                content, marker_found, marker_source = extract_marker_content_detailed(raw_resp)
                run_extracted_contents[pid].append(content)
                
                for chk in checks:
                    pts = float(chk.get("points", 1))
                    passed, awarded, reason = evaluate_check(chk, content, marker_found)
                    
                    run_max_points += pts
                    run_total_checks += 1
                    run_category_scores[cat]["max_points"] += pts
                    run_category_scores[cat]["total"] += 1
                    
                    if passed:
                        run_total_points += awarded
                        run_passed_checks += 1
                        run_category_scores[cat]["points"] += awarded
                        run_category_scores[cat]["passed"] += 1
                    else:
                        # M-2: note in the miss reason when the answer came from a 《》/⟨⟩ fallback marker
                        if marker_source == "fallback":
                            reason = f"폴드백 마커 사용 (《》/⟨⟩): {reason}"
                        results["failures"].append({
                            "provider": provider,
                            "run": run_id,
                            "prompt_id": pid,
                            "category": cat,
                            "check_id": chk["id"],
                            "check_type": chk["type"],
                            "expected": str(chk.get("expected", ""))[:50],
                            "actual": content[:50].replace("\n", " "),
                            "passed": False,
                            "points": 0.0,
                            "reason": reason
                        })
                        
            run_acc = (run_total_points / run_max_points * 100.0) if run_max_points > 0 else 0.0
            for cat, c_data in run_category_scores.items():
                c_data["pct"] = (c_data["points"] / c_data["max_points"] * 100.0) if c_data["max_points"] > 0 else 0.0
                cat_scores_per_run[cat].append(c_data["pct"])
                
            results["provider_runs"][provider][run_id] = {
                "total_points": run_total_points,
                "max_points": run_max_points,
                "total_checks": run_total_checks,
                "passed_checks": run_passed_checks,
                "accuracy": run_acc,
                "category_scores": run_category_scores
            }
            run_scores_list.append(run_acc)
            run_earned_list.append(run_total_points)

        # Compute summary scores (Single-run or Multi-run Average)
        mean_acc = sum(run_scores_list) / len(run_scores_list) if run_scores_list else 0.0
        # I-2: run-average earned points so runs-mode cards stay consistent with avg accuracy
        avg_points = sum(run_earned_list) / len(run_earned_list) if run_earned_list else 0.0
        ref_run = results["provider_runs"][provider].get("r1", list(results["provider_runs"][provider].values())[0])
        
        cat_averages = {}
        for cat in categories:
            cat_list = cat_scores_per_run[cat]
            cat_mean = sum(cat_list) / len(cat_list) if cat_list else 0.0
            cat_averages[cat] = {
                "points": ref_run["category_scores"][cat]["points"],
                "max_points": ref_run["category_scores"][cat]["max_points"],
                "passed": ref_run["category_scores"][cat]["passed"],
                "total": ref_run["category_scores"][cat]["total"],
                "pct": cat_mean
            }
            
        results["provider_scores"][provider] = {
            "total_points": ref_run["total_points"],
            "max_points": ref_run["max_points"],
            "avg_points": avg_points,
            "total_checks": ref_run["total_checks"],
            "passed_checks": ref_run["passed_checks"],
            "accuracy": mean_acc,
            "category_scores": cat_averages
        }
        
        # Calculate cross-run output disagreement rate if multiple runs
        total_pairs = 0
        diff_pairs = 0
        for pid, contents in run_extracted_contents.items():
            n = len(contents)
            if n > 1:
                for i in range(n):
                    for j in range(i + 1, n):
                        total_pairs += 1
                        if normalize_text(contents[i], "ignore_whitespace") != normalize_text(contents[j], "ignore_whitespace"):
                            diff_pairs += 1
        if total_pairs > 0:
            results["run_disagreements"][provider] = (diff_pairs / total_pairs) * 100.0

    # Pairwise comparison if >= 2 providers
    providers = results["providers"]
    if len(providers) >= 2:
        for i in range(len(providers)):
            for j in range(i + 1, len(providers)):
                p1, p2 = providers[i], providers[j]
                pair_key = f"{p1} vs {p2}"
                acc1 = results["provider_scores"][p1]["accuracy"]
                acc2 = results["provider_scores"][p2]["accuracy"]
                overall_diff = acc1 - acc2
                cat_diffs = {}
                for cat in categories:
                    c1 = results["provider_scores"][p1]["category_scores"][cat]["pct"]
                    c2 = results["provider_scores"][p2]["category_scores"][cat]["pct"]
                    cat_diffs[cat] = c1 - c2
                results["pairwise_diff"][pair_key] = {
                    "overall_diff_pp": overall_diff,
                    "category_diffs": cat_diffs
                }
                
    return results

# ==============================================================================
# 4. Formatted Reporting (stdout + Markdown + CSV)
# ==============================================================================

def format_summary_markdown(results: dict) -> str:
    """Generate professional Markdown summary."""
    providers = results["providers"]
    categories = results["categories"]
    is_runs_mode = results.get("is_runs_mode", False)
    
    avg_note = " (회차 평균 / Run Average)" if is_runs_mode else ""
    
    lines = [
        "# Zoo Code Custom Mode: CJK-Flip Evaluation Summary",
        "",
        "> **측정 대상 명명**: 본 결과는 '모델 품질'이 아니라 **'동일 하네스 조건에서의 프로바이더 간 출력 차이'**를 나타냅니다.",
        ""
    ]
    
    if results.get("truncation_warnings"):
        lines.append("## ⚠️ 토큰 절단 진단 경고 (Truncation Diagnostic Warnings)")
        lines.append("")
        for p, w_info in results["truncation_warnings"].items():
            lines.append(f"> **{p}**: {w_info['message']} (누락 문항: {w_info['first_missing']} 외 {w_info['missing_count']-1}개)")
        lines.append("")

    lines.extend([
        f"## 1. 카테고리별 정확도 매트릭스{avg_note}",
        ""
    ])
    
    if not providers:
        lines.append("평가 대상 프로바이더 응답 파일이 발견되지 않았습니다.")
        return "\n".join(lines)
        
    header = "| 카테고리 | " + " | ".join([f"**{p}**" for p in providers]) + " |"
    sep = "| :--- | " + " | ".join([":---:" for _ in providers]) + " |"
    lines.append(header)
    lines.append(sep)
    
    for cat in categories:
        row = [f"`{cat}`"]
        for p in providers:
            pct = results["provider_scores"][p]["category_scores"][cat]["pct"]
            row.append(f"{pct:.1f}%")
        lines.append("| " + " | ".join(row) + " |")
        
    # Total row
    tot_label = "**전체 정확도 (Run Average)**" if is_runs_mode else "**전체 정확도 (Overall)**"
    tot_row = [tot_label]
    for p in providers:
        tot_acc = results["provider_scores"][p]["accuracy"]
        tot_row.append(f"**{tot_acc:.2f}%**")
    lines.append("| " + " | ".join(tot_row) + " |")
    lines.append("")
    
    # Pairwise comparison
    if results["pairwise_diff"]:
        lines.append("## 2. 프로바이더 쌍별 미세 차이 분석 (%p)")
        lines.append("")
        for pair_name, diff_data in results["pairwise_diff"].items():
            lines.append(f"### ◈ {pair_name}")
            lines.append(f"- **전체 편차**: **{diff_data['overall_diff_pp']:+.2f}%p**")
            lines.append("")
            lines.append("| 카테고리 | 편차 (%p) |")
            lines.append("| :--- | :---: |")
            for cat, c_diff in diff_data["category_diffs"].items():
                lines.append(f"| `{cat}` | {c_diff:+.1f}%p |")
            lines.append("")
            
    # Multi-run breakdown and Run Average
    has_multi_runs = is_runs_mode or any(len(runs) > 1 for runs in results.get("provider_runs", {}).values())
    if has_multi_runs and results.get("provider_runs"):
        lines.append("## 3. 다회차 실행 결과 및 회차 평균 (Multi-Run Breakdown & Run Average)")
        lines.append("")
        lines.append("| 프로바이더 | 회차 (Run) | 점수 | 정확도 (%) |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for p, runs_dict in results["provider_runs"].items():
            run_accs = []
            for run_id, r_stats in sorted(runs_dict.items()):
                lines.append(f"| {p} | `{run_id}` | {r_stats['total_points']:.1f} / {r_stats['max_points']:.1f} | {r_stats['accuracy']:.2f}% |")
                run_accs.append(r_stats['accuracy'])
            avg_acc = sum(run_accs) / len(run_accs) if run_accs else 0.0
            lines.append(f"| **{p}** | **회차 평균 (Average)** | - | **{avg_acc:.2f}%** |")
        lines.append("")

    # Cross-Run Disagreement Rate
    if results["run_disagreements"]:
        lines.append("## 4. 회차 간 출력 불일치율 (Cross-Run Disagreement Rate)")
        lines.append("")
        lines.append("| 프로바이더 | 회차 간 불일치율 (%) |")
        lines.append("| :--- | :---: |")
        for p, rate in results["run_disagreements"].items():
            lines.append(f"| **{p}** | {rate:.2f}% |")
        lines.append("")
        
    return "\n".join(lines)

def write_failures_csv(failures: list, csv_path: Path):
    """Write failure rows to failures.csv; remove a stale CSV from a previous run when zero failures."""
    if not failures:
        if csv_path.exists():
            csv_path.unlink()
            print(f"[INFO] 실패 0건: 이전 실행의 {csv_path.name} 삭제 (stale 산출물 정리)")
        return
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "provider", "run", "prompt_id", "category", "check_id", "check_type", "expected", "actual", "passed", "points", "reason"
        ])
        writer.writeheader()
        for row in failures:
            writer.writerow(row)

def generate_html_report(results: dict, output_path: Path) -> str:
    """
    Generate responsive, standalone HTML5 visual dashboard with embedded SVG charts.
    Zero external dependencies (pure Python standard library).
    """
    providers = results.get("providers", [])
    categories = results.get("categories", [])
    is_runs_mode = results.get("is_runs_mode", False)
    provider_scores = results.get("provider_scores", {})
    provider_runs = results.get("provider_runs", {})
    provider_modes = results.get("provider_modes", {})
    truncation_warnings = results.get("truncation_warnings", {})
    failures = results.get("failures", [])
    pairwise_diff = results.get("pairwise_diff", {})
    run_disagreements = results.get("run_disagreements", {})

    COLORS = ["#2563eb", "#10b981", "#d97706", "#8b5cf6", "#ec4899", "#06b6d4"]
    provider_colors = {p: COLORS[i % len(COLORS)] for i, p in enumerate(providers)}

    # Shared grouped-bar plot geometry for the accuracy charts
    plot_w = 870.0
    margin_left = 60.0
    y_0 = 350.0

    def acc_grid_lines(plot_h: float, y_max: float, ticks: Tuple[float, ...]) -> List[str]:
        lines = []
        for tick in ticks:
            y_pos = y_0 - (tick / y_max) * plot_h
            lines.append(
                f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="940" y2="{y_pos:.1f}" stroke="currentColor" stroke-dasharray="3,3" opacity="0.15" />'
            )
            lines.append(
                f'<text x="{margin_left - 10}" y="{y_pos + 4:.1f}" text-anchor="end" font-size="11" fill="currentColor" opacity="0.7">{tick:.0f}%</text>'
            )
        return lines

    # 1. Category Grouped Bar Chart SVG (one bar per provider, runs-average accuracy)
    cat_plot_h = 290.0
    grid_lines = acc_grid_lines(cat_plot_h, 100.0, (0, 20, 40, 60, 80, 100))

    # Categories slots
    num_cats = len(categories) if categories else 1
    slot_w = plot_w / float(num_cats)
    num_p = max(1, len(providers))
    raw_bar_w = (slot_w - 20) / num_p - 4
    bar_w = max(4.0, min(32.0, raw_bar_w))
    bar_gap = max(1.0, 4.0 if num_p <= 4 else 2.0)
    total_group_bars_w = num_p * bar_w + (num_p - 1) * bar_gap
    group_offset = (slot_w - total_group_bars_w) / 2.0

    svg_cat_bars = []
    cat_labels = []
    for cat_i, cat in enumerate(categories):
        slot_x = margin_left + cat_i * slot_w
        cat_short_code = cat.split("_")[0]
        cat_short_name = cat.split("_")[1] if "_" in cat else cat

        for p_i, p in enumerate(providers):
            pct = provider_scores.get(p, {}).get("category_scores", {}).get(cat, {}).get("pct", 0.0)
            bar_h = (pct / 100.0) * cat_plot_h
            bx = slot_x + group_offset + p_i * (bar_w + bar_gap)
            by = y_0 - bar_h
            col = provider_colors.get(p, "#2563eb")
            svg_cat_bars.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="4" fill="{col}">'
                f'<title>{html.escape(p)}: {cat} = {pct:.1f}%</title></rect>'
            )
            if bar_w >= 20.0:
                val_y = max(15.0, by - 6.0)
                svg_cat_bars.append(
                    f'<text x="{bx + bar_w/2.0:.1f}" y="{val_y:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="currentColor">{pct:.1f}%</text>'
                )
            elif bar_w >= 13.0:
                val_y = max(15.0, by - 6.0)
                svg_cat_bars.append(
                    f'<text x="{bx + bar_w/2.0:.1f}" y="{val_y:.1f}" text-anchor="middle" font-size="9" font-weight="600" fill="currentColor">{pct:.0f}%</text>'
                )

        cat_labels.append(
            f'<text x="{slot_x + slot_w/2.0:.1f}" y="{y_0 + 22}" text-anchor="middle" font-size="12" font-weight="700" fill="currentColor">{cat_short_code}</text>'
        )
        cat_labels.append(
            f'<text x="{slot_x + slot_w/2.0:.1f}" y="{y_0 + 38}" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.75">{cat_short_name}</text>'
        )

    # HTML Legend (Responsive, non-clipped)
    html_legend_items = []
    for p in providers:
        col = provider_colors.get(p, "#2563eb")
        acc = provider_scores.get(p, {}).get("accuracy", 0.0)
        html_legend_items.append(
            f'<div class="legend-item"><span class="legend-color-dot" style="background-color: {col};"></span>'
            f'<span class="legend-text"><strong>{html.escape(p)}</strong> ({acc:.1f}%)</span></div>'
        )
    html_legend = f'<div class="chart-legend">{" ".join(html_legend_items)}</div>' if html_legend_items else ""

    svg_category_chart = f"""
    <svg viewBox="0 0 960 420" class="chart-svg" xmlns="http://www.w3.org/2000/svg">
        <g class="grid-lines">{' '.join(grid_lines)}</g>
        <g class="bars">{' '.join(svg_cat_bars)}</g>
        <g class="labels">{' '.join(cat_labels)}</g>
    </svg>
    """

    # 2. Per-Run Grouped Bar Chart SVG (r1/r2/r3 shade bars + run-average marker line)
    svg_run_chart_section = ""
    if providers and provider_runs:
        run_plot_h = 285.0
        run_y_max = 110.0  # headroom above 100% keeps the average marker label clear of bar tops
        run_grid = acc_grid_lines(run_plot_h, run_y_max, (0, 20, 40, 60, 80, 100))
        run_slot_w = plot_w / float(len(providers))
        run_shades = (1.0, 0.62, 0.35)

        run_bars = []
        run_markers = []
        run_labels = []
        for p_i, p in enumerate(providers):
            runs_dict = provider_runs.get(p, {})
            run_ids = sorted(runs_dict.keys())
            slot_x = margin_left + p_i * run_slot_w
            cx = slot_x + run_slot_w / 2.0
            num_runs = max(1, len(run_ids))
            run_bar_w = max(10.0, min(46.0, (run_slot_w - 70.0) / num_runs - 8.0))
            run_gap = 8.0
            run_group_w = num_runs * run_bar_w + (num_runs - 1) * run_gap
            run_offset = (run_slot_w - run_group_w) / 2.0
            col = provider_colors.get(p, "#2563eb")

            for r_i, rid in enumerate(run_ids):
                racc = runs_dict[rid].get("accuracy", 0.0)
                shade = run_shades[r_i % len(run_shades)]
                bar_h = (racc / run_y_max) * run_plot_h
                bx = slot_x + run_offset + r_i * (run_bar_w + run_gap)
                by = y_0 - bar_h
                run_bars.append(
                    f'<rect x="{bx:.1f}" y="{by:.1f}" width="{run_bar_w:.1f}" height="{bar_h:.1f}" rx="4" fill="{col}" opacity="{shade}">'
                    f'<title>{html.escape(p)} {rid}: {racc:.2f}%</title></rect>'
                )
                if run_bar_w >= 18.0:
                    run_bars.append(
                        f'<text x="{bx + run_bar_w/2.0:.1f}" y="{max(15.0, by - 6.0):.1f}" text-anchor="middle" font-size="9.5" font-weight="600" fill="currentColor">{racc:.1f}%</text>'
                    )

            avg_acc = provider_scores.get(p, {}).get("accuracy", 0.0)
            avg_y = y_0 - (avg_acc / run_y_max) * run_plot_h
            run_markers.append(
                f'<line x1="{slot_x + 6:.1f}" y1="{avg_y:.1f}" x2="{slot_x + run_slot_w - 6:.1f}" y2="{avg_y:.1f}" '
                f'stroke="currentColor" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.55" />'
            )
            run_markers.append(
                f'<circle cx="{cx:.1f}" cy="{avg_y:.1f}" r="4.5" fill="{col}" stroke="currentColor" stroke-width="1.5" />'
            )
            run_markers.append(
                f'<text x="{cx:.1f}" y="{avg_y - 10:.1f}" text-anchor="middle" font-size="10.5" font-weight="700" fill="currentColor">평균 {avg_acc:.2f}%</text>'
            )

            p_short = p if len(p) <= 20 else p[:18] + "…"
            run_labels.append(
                f'<text x="{cx:.1f}" y="{y_0 + 22}" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">{html.escape(p_short)}</text>'
            )

        run_legend_items = []
        for p in providers:
            col = provider_colors.get(p, "#2563eb")
            run_legend_items.append(
                f'<div class="legend-item"><span class="legend-color-dot" style="background-color: {col};"></span>'
                f'<span class="legend-text"><strong>{html.escape(p)}</strong></span></div>'
            )
        for shade, rid in zip(run_shades, ("r1", "r2", "r3")):
            run_legend_items.append(
                f'<div class="legend-item"><span class="legend-color-dot" style="background-color: var(--text-muted); opacity: {shade};"></span>'
                f'<span class="legend-text">{rid}</span></div>'
            )
        run_chart_legend = f'<div class="chart-legend">{" ".join(run_legend_items)}</div>'

        svg_run_chart_section = f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <h3>📈 회차별 정확도 그룹 차트 (Per-Run Accuracy)</h3>
                    <span class="badge badge-accent">r1 / r2 / r3 명도 막대 + 회차 평균 마커 (%)</span>
                </div>
                {run_chart_legend}
            </div>
            <svg viewBox="0 0 960 420" class="chart-svg" xmlns="http://www.w3.org/2000/svg">
                <g class="grid-lines">{' '.join(run_grid)}</g>
                <g class="bars">{' '.join(run_bars)}</g>
                <g class="run-avg-markers">{' '.join(run_markers)}</g>
                <g class="labels">{' '.join(run_labels)}</g>
            </svg>
        </div>
        """

    # 2. Pairwise Divergence Chart SVG (All pairs rendered)
    pairwise_charts_html = []
    if len(providers) >= 2 and pairwise_diff:
        for pair_key, diff_info in pairwise_diff.items():
            cat_diffs = diff_info.get("category_diffs", {})
            max_d = 5.0
            if cat_diffs:
                max_d = max(5.0, max(abs(v) for v in cat_diffs.values()))
            max_d = math.ceil(max_d / 5.0) * 5.0

            p_center = 500.0
            p_avail = 300.0
            p_scale = p_avail / max_d

            p_grid = [
                f'<line x1="{p_center - p_avail}" y1="35" x2="{p_center - p_avail}" y2="330" stroke="currentColor" stroke-dasharray="2,2" opacity="0.15" />',
                f'<text x="{p_center - p_avail}" y="25" text-anchor="middle" font-size="10" fill="currentColor">-{max_d:.0f}%p</text>',
                f'<line x1="{p_center - p_avail/2}" y1="35" x2="{p_center - p_avail/2}" y2="330" stroke="currentColor" stroke-dasharray="2,2" opacity="0.15" />',
                f'<text x="{p_center - p_avail/2}" y="25" text-anchor="middle" font-size="10" fill="currentColor">-{max_d/2:.1f}%p</text>',
                f'<line x1="{p_center}" y1="35" x2="{p_center}" y2="330" stroke="currentColor" stroke-width="2" opacity="0.5" />',
                f'<text x="{p_center}" y="25" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">0.0%p</text>',
                f'<line x1="{p_center + p_avail/2}" y1="35" x2="{p_center + p_avail/2}" y2="330" stroke="currentColor" stroke-dasharray="2,2" opacity="0.15" />',
                f'<text x="{p_center + p_avail/2}" y="25" text-anchor="middle" font-size="10" fill="currentColor">+{max_d/2:.1f}%p</text>',
                f'<line x1="{p_center + p_avail}" y1="35" x2="{p_center + p_avail}" y2="330" stroke="currentColor" stroke-dasharray="2,2" opacity="0.15" />',
                f'<text x="{p_center + p_avail}" y="25" text-anchor="middle" font-size="10" fill="currentColor">+{max_d:.0f}%p</text>',
            ]

            p_bars = []
            for c_i, cat in enumerate(categories):
                cdiff = cat_diffs.get(cat, 0.0)
                c_code = cat.split("_")[0]
                c_name = cat.split("_")[1] if "_" in cat else cat
                row_y = 48.0 + c_i * 34.0
                p_bars.append(
                    f'<text x="{p_center - p_avail - 15}" y="{row_y + 14}" text-anchor="end" font-size="11" font-weight="600" fill="currentColor">{c_code} {c_name}</text>'
                )
                if cdiff >= 0:
                    bw = cdiff * p_scale
                    p_bars.append(
                        f'<rect x="{p_center:.1f}" y="{row_y:.1f}" width="{bw:.1f}" height="20" rx="3" fill="#10b981">'
                        f'<title>{c_code}: +{cdiff:.1f}%p</title></rect>'
                    )
                    p_bars.append(
                        f'<text x="{p_center + bw + 6:.1f}" y="{row_y + 15}" text-anchor="start" font-size="11" font-weight="700" fill="#10b981">+{cdiff:.1f}%p</text>'
                    )
                else:
                    bw = abs(cdiff) * p_scale
                    bx = p_center - bw
                    p_bars.append(
                        f'<rect x="{bx:.1f}" y="{row_y:.1f}" width="{bw:.1f}" height="20" rx="3" fill="#ef4444">'
                        f'<title>{c_code}: {cdiff:.1f}%p</title></rect>'
                    )
                    p_bars.append(
                        f'<text x="{bx - 6:.1f}" y="{row_y + 15}" text-anchor="end" font-size="11" font-weight="700" fill="#ef4444">{cdiff:.1f}%p</text>'
                    )

            pairwise_charts_html.append(f"""
            <div class="card">
                <div class="card-header">
                    <h3>⚖️ 프로바이더 간 편차 분석 (%p Divergence Chart)</h3>
                    <span class="badge badge-accent"><strong>{html.escape(pair_key)}</strong>: 전체 편차 <strong>{diff_info.get('overall_diff_pp', 0.0):+.2f}%p</strong></span>
                </div>
                <svg viewBox="0 0 960 360" class="chart-svg" xmlns="http://www.w3.org/2000/svg">
                    <g class="diff-grid">{' '.join(p_grid)}</g>
                    <g class="diff-bars">{' '.join(p_bars)}</g>
                </svg>
            </div>
            """)
    svg_pairwise_chart = "\n".join(pairwise_charts_html)

    # 3. Provider Summary Cards
    cards_html = []
    if not providers:
        cards_html.append("""
        <div class="card empty-card" style="text-align: center; padding: 40px 20px; grid-column: 1 / -1;">
            <h3 style="font-size: 20px; margin-bottom: 10px; color: var(--warning);">⚠️ 평가 대상 응답 파일 없음 (No Responses Found)</h3>
            <p style="color: var(--text-secondary); max-width: 600px; margin: 0 auto 16px;">
                <code>responses/{provider}/MEGA.md</code> 또는 <code>responses/{provider}/T01.md</code> 파일이 발견되지 않았습니다.
            </p>
            <p style="font-size: 13px; color: var(--text-muted);">
                <code>flip-test-pack/responses/sample_fp8/</code> 또는 <code>sample_fp4/</code> 디렉토리를 참조하여 응답 파일을 배치한 후 다시 실행하십시오.
            </p>
        </div>
        """)
    for p in providers:
        sc = provider_scores.get(p, {})
        acc = sc.get("accuracy", 0.0)
        mode = provider_modes.get(p, "individual")
        mode_badge = '<span class="badge badge-mega">⚡ 메가 배치 (Mega-Batch)</span>' if mode == "mega" else '<span class="badge badge-individual">📄 개별 파일 (Individual)</span>'
        
        status_pill = '<span class="status-pill status-perfect">🏆 무손실 (100%)</span>' if acc >= 99.9 else (
            '<span class="status-pill status-high">⚡ 고품질 (High)</span>' if acc >= 95.0 else (
                '<span class="status-pill status-warning">⚠️ 미세 손실 (Minor Loss)</span>' if acc >= 90.0 else
                '<span class="status-pill status-danger">❌ 열화 (Degraded)</span>'
            )
        )

        p_fails = [f for f in failures if f["provider"] == p]

        if is_runs_mode:
            pts_label = "평균 획득 점수 (회차 평균)"
            pts_earned = sc.get("avg_points", sc.get("total_points", 0.0))
        else:
            pts_label = "총 획득 점수"
            pts_earned = sc.get("total_points", 0.0)

        runs_breakdown_html = ""
        p_runs = provider_runs.get(p, {})
        if len(p_runs) > 1 or is_runs_mode:
            run_items = []
            for rid, rst in sorted(p_runs.items()):
                run_items.append(f'<span class="run-chip">{rid}: <strong>{rst["accuracy"]:.1f}%</strong></span>')
            dis_rate = run_disagreements.get(p, 0.0)
            runs_breakdown_html = f"""
            <div class="runs-container">
                <div class="runs-chips">{' '.join(run_items)}</div>
                <div class="disagreement-stat">회차 간 불일치율: <strong>{dis_rate:.2f}%</strong></div>
            </div>
            """

        cards_html.append(f"""
        <div class="summary-card">
            <div class="summary-card-top">
                <h3 class="provider-title">{html.escape(p)}</h3>
                {mode_badge}
            </div>
            <div class="score-row">
                <span class="score-number">{acc:.2f}<span class="score-pct">%</span></span>
                {status_pill}
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {acc:.2f}%; background-color: {provider_colors.get(p, '#2563eb')};"></div>
            </div>
            <div class="metrics-grid">
                <div class="metric-item">
                    <span class="metric-label">체크 통과율</span>
                    <span class="metric-val">{sc.get('passed_checks', 0)} / {sc.get('total_checks', 0)} ({sc.get('passed_checks', 0)/(sc.get('total_checks', 1) or 1)*100:.1f}%)</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">{pts_label}</span>
                    <span class="metric-val">{pts_earned:.1f} / {sc.get('max_points', 0.0):.1f} pt</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">실패 체크 건수</span>
                    <span class="metric-val failure-count">{len(p_fails)}건</span>
                </div>
            </div>
            {runs_breakdown_html}
        </div>
        """)

    # 4. Truncation Warning Banners
    truncation_banners_html = ""
    if truncation_warnings:
        banner_items = []
        for p, w_info in truncation_warnings.items():
            banner_items.append(f"""
            <div class="truncation-item">
                <div class="truncation-header">
                    <span class="trunc-badge">⚠️ 토큰 한도 절단 (Truncation)</span>
                    <strong>{html.escape(p)}</strong>: {html.escape(w_info['message'])}
                </div>
                <p class="truncation-desc">
                    API 프로바이더의 <code>max_tokens</code> 출력 제한으로 인해 <strong>{w_info['first_missing']}</strong> 문항부터 출력이 중단되었습니다.
                    누락된 {w_info['missing_count']}개 문항은 모두 0점으로 처리되었습니다. API 호출 시 Max Output Tokens 설정을 <strong>4,096 ~ 8,192</strong>로 상향하십시오.
                </p>
            </div>
            """)
        truncation_banners_html = f"""
        <div class="truncation-box">
            <div class="truncation-icon">⚠️</div>
            <div class="truncation-body">
                <h3>토큰 절단(Token Truncation) 감지 경고</h3>
                {' '.join(banner_items)}
            </div>
        </div>
        """

    # 5. Failed Items Accordion
    failures_html = ""
    if failures:
        fail_items_html = []
        for idx, f in enumerate(failures):
            fail_items_html.append(f"""
            <details class="fail-accordion-item" {'open' if idx < 3 else ''}>
                <summary>
                    <span class="badge badge-fail">실패</span>
                    <span class="fail-prompt-id">[{f['prompt_id']}]</span>
                    <strong>{f['check_id']}</strong> ({f['category']}) &mdash; <em>{html.escape(f['provider'])} ({f['run']})</em>
                </summary>
                <div class="fail-content">
                    <div class="fail-grid">
                        <div class="fail-col">
                            <span class="fail-field-label">기대값 (Expected) [유형: <code>{f['check_type']}</code>]:</span>
                            <pre class="code-box expected-box"><code>{html.escape(str(f['expected']))}</code></pre>
                        </div>
                        <div class="fail-col">
                            <span class="fail-field-label">실제 출력값 (Actual):</span>
                            <pre class="code-box actual-box"><code>{html.escape(str(f['actual']))}</code></pre>
                        </div>
                    </div>
                    <div class="fail-reason">
                        <strong>판정 사유:</strong> {html.escape(f['reason'])}
                    </div>
                </div>
            </details>
            """)
        failures_html = f"""
        <div class="card">
            <div class="card-header">
                <h3>🔍 실패 체크 상세 내역 (Failure Breakdown)</h3>
                <span class="badge badge-fail">총 {len(failures)}건 실패</span>
            </div>
            <div class="fail-list">
                {' '.join(fail_items_html)}
            </div>
        </div>
        """
    elif not providers:
        failures_html = """
        <div class="card empty-card" style="text-align: center; padding: 32px 20px;">
            <h3 style="font-size: 18px; margin-bottom: 8px; color: var(--text-secondary);">평가 결과 없음 (No Results)</h3>
            <p style="color: var(--text-muted); font-size: 13px;">채점할 프로바이더 응답이 없어 검증 체크가 수행되지 않았습니다.</p>
        </div>
        """
    else:
        failures_html = """
        <div class="card all-pass-card">
            <h3>🎉 전수 체크 100% 통과 (Zero Failures)</h3>
            <p>모든 평가 문항과 결정적 체크 항목을 100% 무결점으로 통과하였습니다.</p>
        </div>
        """

    # Multi-Run Section
    multi_run_section = ""
    has_multiruns = is_runs_mode or any(len(runs) > 1 for runs in provider_runs.values())
    if has_multiruns and provider_runs:
        run_table_rows = []
        for p, runs_dict in sorted(provider_runs.items()):
            acc_list = []
            for rid, rstats in sorted(runs_dict.items()):
                run_table_rows.append(f"""
                <tr>
                    <td><strong>{html.escape(p)}</strong></td>
                    <td><span class="run-tag">{rid}</span></td>
                    <td>{rstats['total_points']:.1f} / {rstats['max_points']:.1f} pt</td>
                    <td><strong>{rstats['accuracy']:.2f}%</strong></td>
                    <td>{rstats['passed_checks']} / {rstats['total_checks']}</td>
                </tr>
                """)
                acc_list.append(rstats['accuracy'])
            avg_acc = sum(acc_list) / len(acc_list) if acc_list else 0.0
            dis_r = run_disagreements.get(p, 0.0)
            run_table_rows.append(f"""
            <tr class="row-avg">
                <td><strong>{html.escape(p)}</strong></td>
                <td><strong>회차 평균 (Average)</strong></td>
                <td>-</td>
                <td><strong class="color-accent">{avg_acc:.2f}%</strong></td>
                <td>불일치율: <strong>{dis_r:.2f}%</strong></td>
            </tr>
            """)

        multi_run_section = f"""
        <div class="card">
            <div class="card-header">
                <h3>🔁 다회차 실행 결과 및 회차 평균 (Multi-Run Analysis)</h3>
                <span class="badge badge-accent">반복 실행 분산 검증</span>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>프로바이더</th>
                        <th>회차 (Run)</th>
                        <th>획득 점수</th>
                        <th>정확도 (%)</th>
                        <th>체크 통과수 / 비고</th>
                    </tr>
                </thead>
                <tbody>
                    {' '.join(run_table_rows)}
                </tbody>
            </table>
        </div>
        """

    # 6. Failure Count by Category Chart SVG (stacked per provider)
    svg_fail_chart_section = ""
    if failures and providers:
        CAT_COLORS = ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#14b8a6", "#3b82f6", "#a855f7", "#64748b"]
        cat_color_map = {c: CAT_COLORS[i % len(CAT_COLORS)] for i, c in enumerate(categories)}
        fail_by_pc = {p: {c: 0 for c in categories} for p in providers}
        for f in failures:
            f_p, f_c = f.get("provider"), f.get("category")
            if f_p in fail_by_pc and f_c in fail_by_pc[f_p]:
                fail_by_pc[f_p][f_c] += 1
        max_total_fails = max((sum(fail_by_pc[p].values()) for p in providers), default=0)
        fail_y_max = float(max(5, math.ceil(max_total_fails / 5.0) * 5))
        fail_plot_h = 285.0
        fail_step = fail_y_max / 5.0
        fail_grid = []
        for i in range(6):
            t = fail_step * i
            y_pos = y_0 - (t / fail_y_max) * fail_plot_h
            fail_grid.append(
                f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="940" y2="{y_pos:.1f}" stroke="currentColor" stroke-dasharray="3,3" opacity="0.15" />'
            )
            fail_grid.append(
                f'<text x="{margin_left - 10}" y="{y_pos + 4:.1f}" text-anchor="end" font-size="11" fill="currentColor" opacity="0.7">{t:.0f}건</text>'
            )
        fail_slot_w = plot_w / float(len(providers))
        fail_bars = []
        fail_labels = []
        for p_i, p in enumerate(providers):
            slot_x = margin_left + p_i * fail_slot_w
            cx = slot_x + fail_slot_w / 2.0
            f_bar_w = min(90.0, fail_slot_w - 70.0)
            bx = cx - f_bar_w / 2.0
            stack_y = y_0
            for cat in categories:
                cnt = fail_by_pc[p][cat]
                if cnt <= 0:
                    continue
                seg_h = (cnt / fail_y_max) * fail_plot_h
                stack_y -= seg_h
                fail_bars.append(
                    f'<rect x="{bx:.1f}" y="{stack_y:.1f}" width="{f_bar_w:.1f}" height="{seg_h:.1f}" fill="{cat_color_map[cat]}">'
                    f'<title>{html.escape(p)} · {cat}: {cnt}건</title></rect>'
                )
                if seg_h >= 16.0:
                    fail_bars.append(
                        f'<text x="{cx:.1f}" y="{stack_y + seg_h/2.0 + 4:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">{cnt}</text>'
                    )
            total_f = sum(fail_by_pc[p].values())
            fail_labels.append(
                f'<text x="{cx:.1f}" y="{max(15.0, stack_y - 8.0):.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">{total_f}건</text>'
            )
            p_short = p if len(p) <= 20 else p[:18] + "…"
            fail_labels.append(
                f'<text x="{cx:.1f}" y="{y_0 + 22}" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">{html.escape(p_short)}</text>'
            )

        fail_legend_items = []
        for cat in categories:
            c_code = cat.split("_")[0]
            c_name = cat.split("_")[1] if "_" in cat else cat
            fail_legend_items.append(
                f'<div class="legend-item"><span class="legend-color-dot" style="background-color: {cat_color_map[cat]};"></span>'
                f'<span class="legend-text">{c_code} {html.escape(c_name)}</span></div>'
            )
        fail_chart_legend = f'<div class="chart-legend">{" ".join(fail_legend_items)}</div>'

        svg_fail_chart_section = f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <h3>📉 실패 건수 카테고리 분포 (Failure Count by Category)</h3>
                    <span class="badge badge-fail">누적 실패 체크 {len(failures)}건</span>
                </div>
                {fail_chart_legend}
            </div>
            <svg viewBox="0 0 960 420" class="chart-svg" xmlns="http://www.w3.org/2000/svg">
                <g class="grid-lines">{' '.join(fail_grid)}</g>
                <g class="bars">{' '.join(fail_bars)}</g>
                <g class="labels">{' '.join(fail_labels)}</g>
            </svg>
        </div>
        """

    # Assemble HTML
    html_doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zoo Code Custom Mode — CJK-Flip 평가 결과 대시보드</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --card-border: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --accent: #2563eb;
            --accent-light: #eff6ff;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --code-bg: #f1f5f9;
        }}
        body.dark {{
            --bg-color: #0b0f19;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --accent-light: rgba(59, 130, 246, 0.15);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --code-bg: #0f172a;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Malgun Gothic", Dotum, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 24px 16px;
            transition: background-color 0.2s ease, color 0.2s ease;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
            gap: 16px;
        }}
        .title-group h1 {{
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 6px;
        }}
        .subtitle {{
            font-size: 14px;
            color: var(--text-secondary);
        }}
        .header-actions {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .theme-btn {{
            background: var(--card-bg);
            color: var(--text-primary);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all 0.2s;
        }}
        .theme-btn:hover {{
            background: var(--accent-light);
            border-color: var(--accent);
        }}
        .meta-pills {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        .pill {{
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 9999px;
            background: var(--code-bg);
            border: 1px solid var(--card-border);
            color: var(--text-secondary);
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .card-header h3 {{
            font-size: 18px;
            font-weight: 700;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        .summary-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .summary-card-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .provider-title {{
            font-size: 18px;
            font-weight: 800;
        }}
        .score-row {{
            display: flex;
            align-items: baseline;
            gap: 12px;
        }}
        .score-number {{
            font-size: 38px;
            font-weight: 900;
            line-height: 1;
        }}
        .score-pct {{
            font-size: 20px;
            font-weight: 700;
            color: var(--text-muted);
        }}
        .status-pill {{
            font-size: 12px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 9999px;
        }}
        .status-perfect {{ background: rgba(16, 185, 129, 0.15); color: #10b981; }}
        .status-high {{ background: rgba(37, 99, 235, 0.15); color: #2563eb; }}
        .status-warning {{ background: rgba(245, 158, 11, 0.15); color: #f59e0b; }}
        .status-danger {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; }}
        .progress-bar-bg {{
            height: 8px;
            background: var(--card-border);
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.6s ease;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 13px;
            padding-top: 6px;
            border-top: 1px solid var(--card-border);
        }}
        .metric-item {{
            display: flex;
            flex-direction: column;
        }}
        .metric-label {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .metric-val {{
            font-weight: 600;
        }}
        .failure-count {{
            color: var(--danger);
        }}
        .badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
        }}
        .badge-mega {{ background: rgba(59, 130, 246, 0.15); color: #3b82f6; }}
        .badge-individual {{ background: var(--code-bg); color: var(--text-secondary); }}
        .badge-accent {{ background: var(--accent-light); color: var(--accent); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; }}
        .chart-legend {{
            display: flex;
            gap: 14px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: var(--text-primary);
        }}
        .legend-color-dot {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
            display: inline-block;
        }}
        .runs-container {{
            margin-top: 6px;
            padding-top: 8px;
            border-top: 1px dashed var(--card-border);
            font-size: 12px;
        }}
        .runs-chips {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 4px;
        }}
        .run-chip {{
            background: var(--code-bg);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .disagreement-stat {{
            color: var(--text-secondary);
        }}
        .chart-svg {{
            width: 100%;
            height: auto;
            max-height: 480px;
            display: block;
        }}
        .truncation-box {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(245, 158, 11, 0.08));
            border: 2px solid var(--warning);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 24px;
            display: flex;
            gap: 16px;
            align-items: flex-start;
        }}
        .truncation-icon {{
            font-size: 32px;
            line-height: 1;
        }}
        .truncation-body h3 {{
            color: var(--danger);
            font-size: 17px;
            margin-bottom: 6px;
        }}
        .truncation-item {{
            margin-top: 8px;
        }}
        .trunc-badge {{
            background: var(--danger);
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            margin-right: 6px;
        }}
        .truncation-desc {{
            font-size: 13px;
            margin-top: 4px;
            color: var(--text-secondary);
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        .report-table th, .report-table td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--card-border);
        }}
        .report-table th {{
            background: var(--code-bg);
            font-weight: 700;
            color: var(--text-secondary);
        }}
        .row-avg {{
            background: var(--accent-light);
            font-weight: 700;
        }}
        .color-accent {{
            color: var(--accent);
        }}
        .run-tag {{
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }}
        .fail-accordion-item {{
            border: 1px solid var(--card-border);
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
            background: var(--card-bg);
        }}
        .fail-accordion-item summary {{
            padding: 12px 16px;
            cursor: pointer;
            font-size: 14px;
            background: var(--code-bg);
            display: flex;
            align-items: center;
            gap: 8px;
            user-select: none;
        }}
        .fail-accordion-item summary:hover {{
            opacity: 0.9;
        }}
        .fail-prompt-id {{
            font-weight: 700;
            font-family: monospace;
        }}
        .fail-content {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .fail-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }}
        @media (max-width: 768px) {{
            .fail-grid {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; align-items: stretch; }}
        }}
        .fail-col {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .fail-field-label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
        }}
        .code-box {{
            background: var(--code-bg);
            padding: 10px;
            border-radius: 6px;
            font-family: Consolas, monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 140px;
            overflow-y: auto;
            border: 1px solid var(--card-border);
        }}
        .actual-box {{
            border-color: rgba(239, 68, 68, 0.4);
            background: rgba(239, 68, 68, 0.04);
        }}
        .fail-reason {{
            font-size: 13px;
            padding: 8px 12px;
            background: var(--code-bg);
            border-left: 3px solid var(--danger);
            border-radius: 4px;
        }}
        .all-pass-card {{
            text-align: center;
            padding: 36px 20px;
            color: var(--success);
        }}
        .all-pass-card h3 {{
            font-size: 20px;
            margin-bottom: 8px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 36px;
            padding-top: 18px;
            border-top: 1px solid var(--card-border);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="title-group">
                <h1>Zoo Code Custom Mode — CJK-Flip 평가 결과 대시보드</h1>
                <p class="subtitle">동일 하네스 조건에서의 프로바이더 간 결정적 출력 차이 정밀 분석</p>
                <div class="meta-pills">
                    <span class="pill">평가 문항: 40개</span>
                    <span class="pill">결정적 체크: 298개</span>
                    <span class="pill">모드: {'다회차 분석 (--runs)' if is_runs_mode else '단일 회차 (Standard)'}</span>
                </div>
            </div>
            <div class="header-actions">
                <button class="theme-btn" onclick="toggleTheme()">🌓 테마 전환</button>
            </div>
        </header>

        {truncation_banners_html}

        <section class="cards-grid">
            {' '.join(cards_html)}
        </section>

        <section class="card">
            <div class="card-header">
                <div>
                    <h3>📊 카테고리별 정확도 그룹 차트 (Category-Level Accuracy)</h3>
                    <span class="badge badge-accent">프로바이더별 회차 평균 정확도 (%)</span>
                </div>
                {html_legend}
            </div>
            {svg_category_chart}
        </section>

        {svg_run_chart_section}

        {svg_pairwise_chart}

        {multi_run_section}

        {failures_html}

        {svg_fail_chart_section}

        <footer class="footer">
            <p><strong>측정 대상 명명</strong>: 본 결과는 '모델 품질'이 아니라 <strong>'동일 하네스 조건에서의 프로바이더 간 출력 차이'</strong>를 나타냅니다.</p>
            <p>CJK-Flip Test Pack &bull; 100% Deterministic Rule Engine &bull; Zero External Dependency</p>
        </footer>
    </div>

    <script>
    function toggleTheme() {{
        document.body.classList.toggle('dark');
        const isDark = document.body.classList.contains('dark');
        localStorage.setItem('cjk_flip_theme', isDark ? 'dark' : 'light');
    }}
    (function() {{
        const saved = localStorage.getItem('cjk_flip_theme');
        if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
            document.body.classList.add('dark');
        }}
    }})();
    </script>
</body>
</html>
"""
    output_path.write_text(html_doc, encoding="utf-8")
    return html_doc

# ==============================================================================
# 5. CLI Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Scoring Engine for CJK-Flip Test Pack"
    )
    parser.add_argument(
        "--master",
        type=str,
        default=str(Path(__file__).resolve().parent / "checks_master.json"),
        help="Path to checks_master.json"
    )
    parser.add_argument(
        "--responses",
        type=str,
        default=str(Path(__file__).resolve().parent / "responses"),
        help="Path to responses/ directory containing provider subdirectories"
    )
    parser.add_argument(
        "--runs",
        action="store_true",
        help="Enable multi-run analysis (evaluates Txx.r1.md, Txx.r2.md, etc.)"
    )
    parser.add_argument(
        "--output-summary",
        type=str,
        default=str(Path(__file__).resolve().parent / "results_summary.md"),
        help="File path to write markdown results summary"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=str(Path(__file__).resolve().parent / "failures.csv"),
        help="File path to write failures.csv"
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default=str(Path(__file__).resolve().parent / "report.html"),
        help="File path to write HTML results dashboard"
    )
    
    args = parser.parse_args()

    master_path = Path(args.master)
    responses_path = Path(args.responses)
    summary_path = Path(args.output_summary)
    csv_path = Path(args.output_csv)
    html_path = Path(args.output_html)

    if not master_path.exists():
        print(f"[ERROR] checks_master.json not found at {master_path}", file=sys.stderr)
        sys.exit(1)

    pack_dir = Path(__file__).resolve().parent

    results = run_scoring(master_path, responses_path, is_runs_mode=args.runs)
    markdown_report = format_summary_markdown(results)

    # Print to stdout
    print(markdown_report)

    # Save results_summary.md
    summary_path.write_text(markdown_report, encoding="utf-8")
    print(f"\n[INFO] Saved results summary to: {summary_path}")

    # Save failures.csv (write_failures_csv also removes a stale CSV on zero failures)
    write_failures_csv(results["failures"], csv_path)
    if results["failures"]:
        print(f"[INFO] Saved {len(results['failures'])} check failures to: {csv_path}")
    else:
        if results.get("providers"):
            print("[INFO] Zero check failures detected! 100% pass rate.")
        else:
            print("[INFO] No providers found to score.")

    # Save report.html
    generate_html_report(results, html_path)
    print(f"[INFO] Saved visual HTML dashboard to: {html_path}")

    # Ensure pack_dir copy of report.html is always kept up to date
    pack_report = pack_dir / "report.html"
    if html_path.resolve() != pack_report.resolve():
        try:
            generate_html_report(results, pack_report)
        except Exception:
            pass

    # Print truncation warnings if any
    if results.get("truncation_warnings"):
        print("\n" + "=" * 80)
        for p, w_info in results["truncation_warnings"].items():
            print(f"⚠️ [진단 경고] {p}: {w_info['message']}")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
