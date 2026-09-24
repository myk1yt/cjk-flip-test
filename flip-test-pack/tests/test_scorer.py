#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for score_results.py

Verifies:
- Text normalization & marker extraction (primary, fallbacks, template echo filter, unclosed recovery)
- All 8 check types: exact, contains, regex, char_count, numeric, json_schema, levenshtein0, chrf
- General extract_regex support
- Intentional error samples (F3 variant errors, F6 count errors, F8 format errors, Levenshtein, chrF, numeric)
- End-to-end multi-provider evaluation and multi-run breakdown + run average calculation
"""

import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add parent directory to sys.path so we can import score_results
CURRENT_DIR = Path(__file__).resolve().parent
PACK_DIR = CURRENT_DIR.parent
if str(PACK_DIR) not in sys.path:
    sys.path.insert(0, str(PACK_DIR))

import score_results as sr


class TestScorerHelpers(unittest.TestCase):
    """Test string manipulation and normalization routines."""

    def test_unicode_normalization(self):
        # NFKC compatibility decomposition & NFC composition
        raw = "（株）　ＡＢＣ　１２３"
        norm = sr.normalize_unicode(raw)
        self.assertIn("(株)", norm)
        self.assertIn("ABC", norm)
        self.assertIn("123", norm)

    def test_normalize_options(self):
        text = "  안녕, 세상! Hello, World!  \n"
        self.assertEqual(sr.normalize_text(text, "none"), "안녕, 세상! Hello, World!")
        self.assertEqual(sr.normalize_text(text, "ignore_whitespace"), "안녕,세상!Hello,World!")
        self.assertEqual(sr.normalize_text(text, "ignore_punctuation"), "안녕세상HelloWorld")
        self.assertEqual(sr.normalize_text(text, "case_fold"), "안녕, 세상! hello, world!")
        self.assertEqual(sr.normalize_text(text, "strip"), "안녕, 세상! Hello, World!")

    def test_marker_extraction(self):
        # 1. Normal standard marker
        s1 = "다음은 답변입니다:\n⟪\n1. 언어: 한국어\n2. 번역: 완료\n⟫\n이상입니다."
        content1, found1 = sr.extract_marker_content(s1)
        self.assertTrue(found1)
        self.assertEqual(content1, "1. 언어: 한국어\n2. 번역: 완료")

        # 2. Alternative fullwidth angle bracket
        s2 = "앞부분 《 핵심 결과 내용 》 뒷부분"
        content2, found2 = sr.extract_marker_content(s2)
        self.assertTrue(found2)
        self.assertEqual(content2, "핵심 결과 내용")

        # 3. Single mathematical angle brackets
        s3 = "앞 ⟨ 중간 결과 내용 ⟩ 뒤"
        content3, found3 = sr.extract_marker_content(s3)
        self.assertTrue(found3)
        self.assertEqual(content3, "중간 결과 내용")

        # 4. Echoed prompt template filtration
        s4 = "지시문:\n⟪\n[이곳에 답변 작성]\n⟫\n답변:\n⟪\n실제 모델 출력 내용\n⟫"
        content4, found4 = sr.extract_marker_content(s4)
        self.assertTrue(found4)
        self.assertEqual(content4, "실제 모델 출력 내용")

        # 5. Unclosed opening marker recovery (e.g. truncated at EOF)
        s5 = "시작 ⟪ 1. 정답: 완료"
        content5, found5 = sr.extract_marker_content(s5)
        self.assertTrue(found5)
        self.assertEqual(content5, "1. 정답: 완료")

        # 6. Missing marker
        s6 = "마커 없이 그냥 작성된 답변입니다."
        content6, found6 = sr.extract_marker_content(s6)
        self.assertFalse(found6)
        self.assertEqual(content6, "마커 없이 그냥 작성된 답변입니다.")

    def test_marker_extraction_placeholder_fallthrough(self):
        # 1. Echoed placeholder in ⟪⟫ followed by valid 《》 fallback
        s1 = "지시문:\n⟪\n[이곳에 답변 작성]\n⟫\n답변:\n《\n대체 괄호 실제 답변\n》"
        content1, found1 = sr.extract_marker_content(s1)
        self.assertTrue(found1)
        self.assertEqual(content1, "대체 괄호 실제 답변")

        # 2. Echoed placeholder in ⟪⟫ followed by unclosed ⟪ at EOF
        s2 = "지시문:\n⟪\n[이곳에 답변 작성]\n⟫\n답변:\n⟪\nEOF 절단 답변..."
        content2, found2 = sr.extract_marker_content(s2)
        self.assertTrue(found2)
        self.assertEqual(content2, "EOF 절단 답변...")

        # 3. Only placeholder present (no valid answer)
        s3 = "⟪\n[이곳에 답변 작성]\n⟫"
        content3, found3 = sr.extract_marker_content(s3)
        self.assertFalse(found3)

    def test_parse_mega_batch_guard_and_monotonicity(self):
        mega_text = (
            "=== [T01] ===\n"
            "T1: 본문 줄머리 텍스트\n"
            "T02 문항 결과입니다\n"
            "- T02 문항과의 비교 분석\n"
            "* T2 참고사항\n"
            "⟪\n정답 1\n⟫\n\n"
            "## [T02]\n"
            "⟪\n정답 2\n⟫\n\n"
            "=== [T01] ===\n"
            "오래된 질문 인용\n\n"
            "--- T03 ---\n"
            "⟪\n정답 3\n⟫\n"
        )
        parsed = sr.parse_mega_batch(mega_text)
        self.assertIn("T01", parsed)
        self.assertIn("T02", parsed)
        self.assertIn("T03", parsed)
        self.assertEqual(len(parsed), 3)
        # Verify T01 body is not truncated by 'T1:', 'T02 문항', or bullet points '- T02', '* T2'
        self.assertIn("T1: 본문 줄머리 텍스트", parsed["T01"])
        self.assertIn("T02 문항 결과입니다", parsed["T01"])
        self.assertIn("- T02 문항과의 비교 분석", parsed["T01"])
        self.assertIn("* T2 참고사항", parsed["T01"])
        self.assertIn("정답 1", parsed["T01"])
        # Verify T02 body was not cut by the regressive T01 header
        self.assertIn("오래된 질문 인용", parsed["T02"])
        # Verify T03 is parsed correctly
        self.assertEqual(parsed["T03"], "⟪\n정답 3\n⟫")

    def test_levenshtein_distance(self):
        self.assertEqual(sr.levenshtein_distance("kitten", "sitting"), 3)
        self.assertEqual(sr.levenshtein_distance("대한민국", "대한민국"), 0)
        self.assertEqual(sr.levenshtein_distance("대한민국", "대한국민"), 2)

    def test_chrf_score(self):
        # Exact match chrF is 1.0
        score_exact = sr.compute_chrf("오늘 날씨가 매우 화창합니다", "오늘 날씨가 매우 화창합니다")
        self.assertAlmostEqual(score_exact, 1.0, places=3)

        # High similarity realistic sentence from F4
        s_ref = "본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통하여 메모리 대역폭의 병목현상을 해결한다."
        s_hyp = "본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통해 메모리 대역폭의 병목현상을 해결한다."
        score_high = sr.compute_chrf(s_hyp, s_ref)
        self.assertGreater(score_high, 0.70)

        # Total mismatch
        score_low = sr.compute_chrf("완전히 다른 내용의 문자열입니다", "전혀 일치하지 않는 텍스트")
        self.assertLess(score_low, 0.30)


class TestCheckTypes(unittest.TestCase):
    """Test evaluation of individual check types across all 8 types."""

    def test_exact_check(self):
        chk = {"id": "C1", "type": "exact", "expected": "愛國發財", "norm": "none", "points": 1}
        
        # Positive
        ok, pts, _ = sr.evaluate_check(chk, "愛國發財", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 1.0)

        # Negative
        ok, pts, _ = sr.evaluate_check(chk, "爱国发财", marker_found=True)
        self.assertFalse(ok)
        self.assertEqual(pts, 0.0)

    def test_exact_char_index_check(self):
        chk = {"id": "C1_IDX", "type": "exact", "char_index": 2, "expected": "C", "norm": "none", "points": 1}
        ok, pts, _ = sr.evaluate_check(chk, "A B C D E", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 1.0)

    def test_contains_check(self):
        chk = {"id": "C2", "type": "contains", "expected": "경제산업성", "norm": "ignore_whitespace", "points": 2}
        
        ok, pts, _ = sr.evaluate_check(chk, "도쿄도 경제산업성 대신관방", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 2.0)

        ok, pts, _ = sr.evaluate_check(chk, "도쿄도 외무성 관방", marker_found=True)
        self.assertFalse(ok)
        self.assertEqual(pts, 0.0)

    def test_regex_check(self):
        chk = {"id": "C3", "type": "regex", "expected": r"^TASK-[0-9]{4}$", "norm": "none", "points": 1}
        
        ok, pts, _ = sr.evaluate_check(chk, "TASK-4081", marker_found=True)
        self.assertTrue(ok)
        
        ok, pts, _ = sr.evaluate_check(chk, "TASK-408", marker_found=True)
        self.assertFalse(ok)

    def test_char_count_check(self):
        chk = {"id": "C4", "type": "char_count", "expected": 10, "tolerance": 0, "norm": "none", "points": 1}
        
        ok, pts, _ = sr.evaluate_check(chk, "1234567890", marker_found=True)
        self.assertTrue(ok)

        # Off by one error
        ok, pts, _ = sr.evaluate_check(chk, "123456789", marker_found=True)
        self.assertFalse(ok)
        self.assertEqual(pts, 0.0)

    def test_numeric_check(self):
        chk = {"id": "C5", "type": "numeric", "expected": 2043.75, "epsilon": 0.01, "norm": "none", "points": 2}
        
        ok, pts, _ = sr.evaluate_check(chk, "합산총그램: 2043.75g 입니다.", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 2.0)

        # Out of bounds
        ok, pts, _ = sr.evaluate_check(chk, "합산총그램: 2040.00g 입니다.", marker_found=True)
        self.assertFalse(ok)

    def test_json_schema_check(self):
        schema = {
            "type": "object",
            "required": ["task_id", "score", "is_valid"],
            "properties": {
                "task_id": {"type": "string"},
                "score": {"type": "number"},
                "is_valid": {"type": "boolean", "const": True}
            }
        }
        chk = {"id": "C6", "type": "json_schema", "expected": json.dumps(schema), "norm": "none", "points": 2}

        # Valid JSON matching schema (including markdown code fence wrapping)
        valid_json = '```json\n{"task_id": "T01", "score": 95.5, "is_valid": true}\n```'
        ok, pts, _ = sr.evaluate_check(chk, valid_json, marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 2.0)

        # Missing required key
        invalid_json1 = '{"task_id": "T01", "is_valid": true}'
        ok, pts, _ = sr.evaluate_check(chk, invalid_json1, marker_found=True)
        self.assertFalse(ok)

    def test_levenshtein0_check(self):
        chk = {"id": "C7", "type": "levenshtein0", "expected": "대한민국 헌법 제1조", "max_dist": 0, "norm": "none", "points": 2}
        
        # Exact match
        ok, pts, _ = sr.evaluate_check(chk, "대한민국 헌법 제1조", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 2.0)

        # 1 character typo
        ok, pts, _ = sr.evaluate_check(chk, "대한민국 헌법 제2조", marker_found=True)
        self.assertFalse(ok)

    def test_chrf_check(self):
        chk = {
            "id": "C8",
            "type": "chrf",
            "expected": "가중치 양자화를 통해 메모리 대역폭의 병목현상을 해결한다.",
            "threshold": 0.70,
            "norm": "ignore_whitespace",
            "points": 2
        }
        
        # High similarity input
        ok, pts, _ = sr.evaluate_check(chk, "가중치 양자화를 통하여 메모리 대역폭의 병목현상을 해결한다.", marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 2.0)

        # Low similarity input
        ok, pts, _ = sr.evaluate_check(chk, "전혀 다른 내용의 문장입니다.", marker_found=True)
        self.assertFalse(ok)

    def test_extract_regex_support(self):
        chk = {
            "id": "C_EXTRACT",
            "type": "exact",
            "extract_regex": r"결과:\s*([^\r\n]+)",
            "expected": "PASS",
            "norm": "none",
            "points": 1
        }
        raw_output = "설명 문장\n결과: PASS\n추가 문장"
        ok, pts, _ = sr.evaluate_check(chk, raw_output, marker_found=True)
        self.assertTrue(ok)
        self.assertEqual(pts, 1.0)

        # Pattern without capturing group (falls back to group 0 safely without IndexError)
        chk_no_group = {
            "id": "C_EXTRACT_NOGRP",
            "type": "exact",
            "extract_regex": r"PASS",
            "expected": "PASS",
            "norm": "none",
            "points": 1
        }
        ok_ng, pts_ng, _ = sr.evaluate_check(chk_no_group, raw_output, marker_found=True)
        self.assertTrue(ok_ng)
        self.assertEqual(pts_ng, 1.0)

    def test_char_index_negative_guard(self):
        chk = {"id": "C_NEG_IDX", "type": "exact", "char_index": -1, "expected": "A", "norm": "none", "points": 1}
        ok, pts, msg = sr.evaluate_check(chk, "ABCDE", marker_found=True)
        self.assertFalse(ok)
        self.assertEqual(pts, 0.0)
        self.assertIn("too short", msg)

    def test_numeric_normalization_commas_and_fullwidth(self):
        chk = {"id": "C_NUM_NORM", "type": "numeric", "expected": 2043.75, "epsilon": 0.01, "norm": "none", "points": 1}
        
        # Standard
        ok1, _, _ = sr.evaluate_check(chk, "총 무게: 2043.75g", marker_found=True)
        self.assertTrue(ok1)
        
        # With thousands comma
        ok2, _, _ = sr.evaluate_check(chk, "총 무게: 2,043.75g", marker_found=True)
        self.assertTrue(ok2)
        
        # With fullwidth decimal point
        ok3, _, _ = sr.evaluate_check(chk, "총 무게: 2043．75g", marker_found=True)
        self.assertTrue(ok3)

        # With both comma and fullwidth decimal point
        ok4, _, _ = sr.evaluate_check(chk, "총 무게: 2,043．75g", marker_found=True)
        self.assertTrue(ok4)

        # With fullwidth comma
        ok5, _, _ = sr.evaluate_check(chk, "총 무게: 2，043.75g", marker_found=True)
        self.assertTrue(ok5)

        # With fullwidth comma and fullwidth decimal point
        ok6, _, _ = sr.evaluate_check(chk, "총 무게: 2，043．75g", marker_found=True)
        self.assertTrue(ok6)

    def test_t40_logic_anchored_regex_checks(self):
        master = sr.load_master_checks(PACK_DIR / "checks_master.json")
        t40_checks = master["prompts"]["T40"]["checks"]

        # Valid answer according to ground truth
        valid_answer = (
            "1. 乙진술: 거짓\n"
            "2. 丙진술: 참\n"
            "3. 甲진술: 거짓\n"
            "4. 참말한사람: 丙\n"
            "5. 진범: 乙"
        )
        for chk in t40_checks:
            ok, pts, msg = sr.evaluate_check(chk, valid_answer, marker_found=True)
            self.assertTrue(ok, f"Check {chk['id']} failed on valid answer: {msg}")

        # Inverted false answer that previously passed when using unanchored contains checks
        inverted_false_answer = (
            "1. 乙진술: 참\n"
            "2. 丙진술: 거짓\n"
            "3. 甲진술: 참\n"
            "4. 참말한사람: 甲\n"
            "5. 진범: 丙"
        )
        for chk in t40_checks:
            ok, pts, msg = sr.evaluate_check(chk, inverted_false_answer, marker_found=True)
            self.assertFalse(ok, f"Check {chk['id']} should have failed on inverted answer!")

    def test_numeric_line_anchoring_with_extract_regex(self):
        master = sr.load_master_checks(PACK_DIR / "checks_master.json")
        t11_c1 = next(c for c in master["prompts"]["T11"]["checks"] if c["id"] == "T11_C1")
        t11_c4 = next(c for c in master["prompts"]["T11"]["checks"] if c["id"] == "T11_C4")
        t11_c5 = next(c for c in master["prompts"]["T11"]["checks"] if c["id"] == "T11_C5")

        # Mock output where line 4 has correct count (3) but line 5 has wrong count (99)
        mock_output = (
            "1. 총글자수: 32\n"
            "2. 7번째: 民\n"
            "3. 15번째: 민\n"
            "4. 한글국빈도: 3\n"
            "5. 한자國빈도: 99\n"
            "6. 역순: xxx"
        )
        ok1, _, _ = sr.evaluate_check(t11_c1, mock_output, marker_found=True)
        self.assertTrue(ok1)
        ok4, _, _ = sr.evaluate_check(t11_c4, mock_output, marker_found=True)
        self.assertTrue(ok4)
        ok5, _, _ = sr.evaluate_check(t11_c5, mock_output, marker_found=True)
        self.assertFalse(ok5)

    def test_prompt_check_synchronizations(self):
        master = sr.load_master_checks(PACK_DIR / "checks_master.json")

        # T04_C2: accepts both '지속가능발전' and '지속 가능한 발전'
        t04_c2 = next(c for c in master["prompts"]["T04"]["checks"] if c["id"] == "T04_C2")
        ok_a, _, _ = sr.evaluate_check(t04_c2, "어휘 대조: 지속가능발전(영속발전)", marker_found=True)
        ok_b, _, _ = sr.evaluate_check(t04_c2, "어휘 대조: 지속 가능한 발전(영속발전)", marker_found=True)
        self.assertTrue(ok_a)
        self.assertTrue(ok_b)

        # T02_C5: accepts flexible translation prefixes
        t02_c5 = next(c for c in master["prompts"]["T02"]["checks"] if c["id"] == "T02_C5")
        ok_p1, _, _ = sr.evaluate_check(t02_c5, "2. 한국어 번역: 도쿄도 지요다구...", marker_found=True)
        ok_p2, _, _ = sr.evaluate_check(t02_c5, "2. 번역: 도쿄도 지요다구...", marker_found=True)
        ok_p3, _, _ = sr.evaluate_check(t02_c5, "2. 한국어 완역: 도쿄도 지요다구...", marker_found=True)
        self.assertTrue(ok_p1)
        self.assertTrue(ok_p2)
        self.assertTrue(ok_p3)

        # T38_C1: accepts brackets and parenthesis coordinates
        t38_c1 = next(c for c in master["prompts"]["T38"]["checks"] if c["id"] == "T38_C1")
        ok_coord1, _, _ = sr.evaluate_check(t38_c1, "1. 1단계좌표: (1,3)", marker_found=True)
        ok_coord2, _, _ = sr.evaluate_check(t38_c1, "1. 1단계좌표: [1, 3]", marker_found=True)
        ok_coord3, _, _ = sr.evaluate_check(t38_c1, "1. 1단계좌표: 1, 3", marker_found=True)
        self.assertTrue(ok_coord1)
        self.assertTrue(ok_coord2)
        self.assertTrue(ok_coord3)

        # F4 chrF: isolates step 2 Korean sentence from step 1 Japanese/Chinese
        t26_c5 = next(c for c in master["prompts"]["T26"]["checks"] if c["id"] == "T26_C5")
        mock_t26 = (
            "1단계(일본어): 本発明のディープラーニング推論エンジンは、重み量子化を通じてメモリ帯域幅のボトルネックを解決する。\n"
            "2단계(한국어회귀): 본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통해 메모리 대역폭의 병목현상을 해결한다."
        )
        ok_chrf, pts_chrf, _ = sr.evaluate_check(t26_c5, mock_t26, marker_found=True)
        self.assertTrue(ok_chrf)
        self.assertEqual(pts_chrf, 2.0)


class TestIntentionalErrorSamples(unittest.TestCase):
    """
    Test that intentional flaws (mimicking FP4 degradation or format violations)
    are strictly and deterministically caught.
    """

    def test_f3_character_variant_intentional_flaw(self):
        # Prompt T06: Expected '愛國發財龍馬車關開學門書長東語鳥魚點買賣歸電歡鐵銀'
        # Intentionally replace 5th char '龍' with simplified '龙', and 11th '門' with '门'
        corrupted_t06 = "愛國發財龙馬車關開學门書長東語鳥魚點買賣歸電歡鐵銀"
        
        master_path = PACK_DIR / "checks_master.json"
        master = sr.load_master_checks(master_path)
        t06_checks = master["prompts"]["T06"]["checks"]
        
        passed_count = 0
        failed_check_ids = []
        for chk in t06_checks:
            ok, pts, msg = sr.evaluate_check(chk, corrupted_t06, marker_found=True)
            if ok:
                passed_count += 1
            else:
                failed_check_ids.append(chk["id"])

        self.assertIn("T06_C05", failed_check_ids)
        self.assertIn("T06_C11", failed_check_ids)
        self.assertIn("T06_C26", failed_check_ids)
        self.assertEqual(passed_count, 23)

    def test_f8_sentence_count_intentional_flaw(self):
        flawed_t22 = "첫 번째 문장입니다. 두 번째 문장입니다. 漢字가 포함된 세 번째 문장입니다. 네 번째 문장입니다."
        
        master_path = PACK_DIR / "checks_master.json"
        master = sr.load_master_checks(master_path)
        t22_checks = master["prompts"]["T22"]["checks"]

        results = {}
        for chk in t22_checks:
            ok, pts, msg = sr.evaluate_check(chk, flawed_t22, marker_found=True)
            results[chk["id"]] = ok

        self.assertFalse(results["T22_C1"])
        self.assertFalse(results["T22_C2"])

    def test_marker_missing_fails_strict_checks(self):
        chk = {"id": "C_STRICT", "type": "exact", "expected": "정답", "points": 1}
        ok, pts, msg = sr.evaluate_check(chk, "정답", marker_found=False)
        self.assertFalse(ok)
        self.assertIn("Marker ⟪ ⟫ missing", msg)

    def test_levenshtein0_intentional_flaw(self):
        chk = {"id": "C_LEV", "type": "levenshtein0", "expected": "정확한문자열", "max_dist": 0, "points": 1}
        ok, pts, msg = sr.evaluate_check(chk, "정확한문자혈", marker_found=True)
        self.assertFalse(ok)
        self.assertIn("Levenshtein distance", msg)

    def test_chrf_intentional_flaw(self):
        chk = {"id": "C_CHRF", "type": "chrf", "expected": "표준 한국어 문장입니다.", "threshold": 0.70, "points": 1}
        ok, pts, msg = sr.evaluate_check(chk, "전혀 다른 텍스트", marker_found=True)
        self.assertFalse(ok)
        self.assertIn("chrF score", msg)

    def test_numeric_tolerance_intentional_flaw(self):
        chk = {"id": "C_NUM", "type": "numeric", "expected": 100.0, "epsilon": 0.5, "points": 1}
        ok, pts, _ = sr.evaluate_check(chk, "결과: 101.5", marker_found=True)
        self.assertFalse(ok)

    def test_char_count_intentional_flaw(self):
        chk = {"id": "C_CNT", "type": "char_count", "expected": 20, "tolerance": 0, "points": 1}
        ok, pts, _ = sr.evaluate_check(chk, "12345", marker_found=True)
        self.assertFalse(ok)


class TestEndToEndScoringPipeline(unittest.TestCase):
    """Test full directory evaluation, pairwise difference, and multi-run modes."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.responses_dir = Path(self.temp_dir) / "responses"
        self.master_path = PACK_DIR / "checks_master.json"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_with_mock_providers(self):
        master = sr.load_master_checks(self.master_path)
        
        # Provider 1: Perfect Provider (100% ground truth)
        p1_dir = self.responses_dir / "provider_fp8"
        p1_dir.mkdir(parents=True)
        for pid, pdata in master["prompts"].items():
            ans = pdata["expected_marker_content"]
            (p1_dir / f"{pid}.md").write_text(f"⟪\n{ans}\n⟫", encoding="utf-8")

        # Provider 2: Degraded Provider (Flawed in F3 and F8)
        p2_dir = self.responses_dir / "provider_fp4"
        p2_dir.mkdir(parents=True)
        for pid, pdata in master["prompts"].items():
            ans = pdata["expected_marker_content"]
            if pid == "T06":
                ans = "爱国发财龙马车关开学门书长东语鸟鱼点买卖归电欢铁银" # kept simplified!
            elif pid == "T21":
                ans = "{ broken json"
            (p2_dir / f"{pid}.md").write_text(f"⟪\n{ans}\n⟫", encoding="utf-8")

        # Run scoring in single-run mode
        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=False)

        # Assertions on Provider 1
        p1_stats = results["provider_scores"]["provider_fp8"]
        self.assertAlmostEqual(p1_stats["accuracy"], 100.0, places=1)
        self.assertEqual(p1_stats["passed_checks"], p1_stats["total_checks"])

        # Assertions on Provider 2
        p2_stats = results["provider_scores"]["provider_fp4"]
        self.assertLess(p2_stats["accuracy"], 100.0)
        self.assertGreater(len(results["failures"]), 0)

        # Assertions on Pairwise Difference
        self.assertTrue(len(results["pairwise_diff"]) > 0)
        pair_key = list(results["pairwise_diff"].keys())[0]
        diff_info = results["pairwise_diff"][pair_key]
        self.assertNotEqual(diff_info["overall_diff_pp"], 0.0)

        # Generate summary markdown report
        md_report = sr.format_summary_markdown(results)
        self.assertIn("provider_fp8", md_report)
        self.assertIn("provider_fp4", md_report)
        self.assertIn("동일 하네스 조건에서의 프로바이더 간 출력 차이", md_report)

    def test_multi_run_evaluation_and_averaging(self):
        # Create a provider with 2 runs having stochastic variance
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_stochastic"
        p_dir.mkdir(parents=True)
        
        # Populate perfect base for r1
        for pid, pdata in master["prompts"].items():
            ans = pdata["expected_marker_content"]
            (p_dir / f"{pid}.r1.md").write_text(f"⟪\n{ans}\n⟫", encoding="utf-8")
            
        # Run 2: Introduce errors in T06 and T31
        for pid, pdata in master["prompts"].items():
            ans = pdata["expected_marker_content"]
            if pid == "T06":
                ans = "爱国发财龙马车关开学门书长东语鸟鱼点买卖归电欢铁银"
            (p_dir / f"{pid}.r2.md").write_text(f"⟪\n{ans}\n⟫", encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=True)
        
        # Verify run breakdown
        p_runs = results["provider_runs"]["provider_stochastic"]
        self.assertIn("r1", p_runs)
        self.assertIn("r2", p_runs)
        self.assertAlmostEqual(p_runs["r1"]["accuracy"], 100.0, places=1)
        self.assertLess(p_runs["r2"]["accuracy"], 100.0)
        
        # Verify run average
        expected_avg = (p_runs["r1"]["accuracy"] + p_runs["r2"]["accuracy"]) / 2.0
        self.assertAlmostEqual(results["provider_scores"]["provider_stochastic"]["accuracy"], expected_avg, places=2)

        # Disagreement rate must be > 0
        self.assertIn("provider_stochastic", results["run_disagreements"])
        disagreement = results["run_disagreements"]["provider_stochastic"]
        self.assertGreater(disagreement, 0.0)

        # Markdown report must contain Run Average section
        md_report = sr.format_summary_markdown(results)
        self.assertIn("다회차 실행 결과 및 회차 평균", md_report)
        self.assertIn("회차 간 출력 불일치율", md_report)


class TestMegaBatchAndDashboard(unittest.TestCase):
    """Test Mega-Batch parsing, truncation detection, auto-detection, and HTML report generation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.responses_dir = Path(self.temp_dir) / "responses"
        self.master_path = PACK_DIR / "checks_master.json"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_mega_batch_variations(self):
        sample_text = """
**=== [T01] ===**
⟪
1. 언어: 한국어
⟫

===[T02]===
⟪
2. 번역: 완료
⟫

### **[T03]** (카테고리: F1)
⟪
3. 어휘: 성공
⟫

=== T4 ===
⟪
4. 결과: 테스트 4
⟫

--- [T05] ---
⟪
5. 결과: 테스트 5
⟫
"""
        parsed = sr.parse_mega_batch(sample_text)
        self.assertIn("T01", parsed)
        self.assertIn("T02", parsed)
        self.assertIn("T03", parsed)
        self.assertIn("T04", parsed)
        self.assertIn("T05", parsed)
        self.assertIn("1. 언어: 한국어", parsed["T01"])
        self.assertIn("2. 번역: 완료", parsed["T02"])
        self.assertIn("3. 어휘: 성공", parsed["T03"])
        self.assertIn("4. 결과: 테스트 4", parsed["T04"])
        self.assertIn("5. 결과: 테스트 5", parsed["T05"])

    def test_single_run_fallback_when_r1_absent(self):
        """Verify that a provider with only MEGA.r2.md still scores correctly in single-run mode."""
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_r2_only"
        p_dir.mkdir(parents=True)
        mega_content = []
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            mega_content.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_dir / "MEGA.r2.md").write_text("\n\n".join(mega_content), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=False)
        self.assertIn("provider_r2_only", results["provider_scores"])
        self.assertAlmostEqual(results["provider_scores"]["provider_r2_only"]["accuracy"], 100.0, places=1)
        # Should NOT trigger false truncation warnings
        self.assertNotIn("provider_r2_only", results["truncation_warnings"])

    def test_auto_detection_mega_vs_individual(self):
        master = sr.load_master_checks(self.master_path)
        
        # Provider A: Mega Batch
        p_mega = self.responses_dir / "provider_mega"
        p_mega.mkdir(parents=True)
        mega_content = []
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            mega_content.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_mega / "MEGA.md").write_text("\n\n".join(mega_content), encoding="utf-8")

        # Provider B: Individual Files
        p_indiv = self.responses_dir / "provider_indiv"
        p_indiv.mkdir(parents=True)
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            (p_indiv / f"{pid}.md").write_text(f"⟪\n{ans}\n⟫", encoding="utf-8")

        discovered, modes = sr.discover_responses(self.responses_dir, return_modes=True)
        self.assertEqual(modes["provider_mega"], "mega")
        self.assertEqual(modes["provider_indiv"], "individual")
        self.assertIn("T01", discovered["provider_mega"])
        self.assertIn("T01", discovered["provider_indiv"])

        # Run scoring on both
        results = sr.run_scoring(self.master_path, self.responses_dir)
        self.assertAlmostEqual(results["provider_scores"]["provider_mega"]["accuracy"], 100.0, places=1)
        self.assertAlmostEqual(results["provider_scores"]["provider_indiv"]["accuracy"], 100.0, places=1)

    def test_truncation_detection_and_warning(self):
        master = sr.load_master_checks(self.master_path)
        p_trunc = self.responses_dir / "provider_trunc"
        p_trunc.mkdir(parents=True)

        # Populate only T01 to T25, leaving T26~T40 missing (token limit reached)
        mega_content = []
        for pid in sorted(master["prompts"].keys())[:25]:
            ans = master["prompts"][pid]["expected_marker_content"]
            mega_content.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_trunc / "MEGA.md").write_text("\n\n".join(mega_content), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir)

        # Assert truncation detected
        self.assertIn("provider_trunc", results["truncation_warnings"])
        trunc_info = results["truncation_warnings"]["provider_trunc"]
        self.assertEqual(trunc_info["first_missing"], "T26")
        self.assertEqual(trunc_info["missing_count"], 15)
        self.assertIn("⚠️ T26부터 응답 누락 감지", trunc_info["message"])
        self.assertIn("Max Output Tokens", trunc_info["message"])

        # Assert failures recorded for missing prompts with token truncation reason
        t26_failures = [f for f in results["failures"] if f["prompt_id"] == "T26"]
        self.assertGreater(len(t26_failures), 0)
        self.assertIn("Token Limit Exceeded", t26_failures[0]["reason"])

        # Markdown report must contain the truncation diagnostic warning
        md_report = sr.format_summary_markdown(results)
        self.assertIn("토큰 절단 진단 경고", md_report)
        self.assertIn("T26부터 응답 누락 감지", md_report)

    def test_multi_run_truncation_detection(self):
        """In multi-run mode, if r1 is full but r2 is truncated, r2 truncation must be flagged."""
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_multitrunc"
        p_dir.mkdir(parents=True)

        # r1 full
        r1_items = [f"=== [{pid}] ===\n⟪\n{master['prompts'][pid]['expected_marker_content']}\n⟫" for pid in sorted(master["prompts"].keys())]
        (p_dir / "MEGA.md").write_text("\n\n".join(r1_items), encoding="utf-8")

        # r2 truncated at T30
        r2_items = [f"=== [{pid}] ===\n⟪\n{master['prompts'][pid]['expected_marker_content']}\n⟫" for pid in sorted(master["prompts"].keys())[:30]]
        (p_dir / "MEGA.r2.md").write_text("\n\n".join(r2_items), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=True)
        # Check that r2 truncation is detected
        warn_keys = list(results["truncation_warnings"].keys())
        self.assertTrue(any("r2" in k or results["truncation_warnings"][k].get("run") == "r2" for k in warn_keys))

    def test_html_report_generation(self):
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_fp8"
        p_dir.mkdir(parents=True)
        mega_content = []
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            mega_content.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_dir / "MEGA.md").write_text("\n\n".join(mega_content), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir)
        html_file = Path(self.temp_dir) / "test_report.html"
        html_content = sr.generate_html_report(results, html_file)

        # File exists
        self.assertTrue(html_file.exists())
        self.assertGreater(html_file.stat().st_size, 1000)

        # HTML content assertions
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("Zoo Code Custom Mode — CJK-Flip 평가 결과 대시보드", html_content)
        self.assertIn("Category Accuracy Matrix", html_content)
        self.assertIn("<svg viewBox=", html_content)
        self.assertIn("toggleTheme", html_content)
        self.assertIn("100.00", html_content)
        self.assertIn("메가 배치", html_content)

    def test_empty_responses_dashboard(self):
        """When responses folder is empty, report.html must show empty state, NOT 100% pass."""
        empty_resp_dir = Path(self.temp_dir) / "empty_responses"
        empty_resp_dir.mkdir(parents=True)
        results = sr.run_scoring(self.master_path, empty_resp_dir)
        html_file = Path(self.temp_dir) / "empty_report.html"
        html_content = sr.generate_html_report(results, html_file)

        self.assertIn("평가 대상 응답 파일 없음", html_content)
        self.assertNotIn("전수 체크 100% 통과", html_content)

    def test_multi_provider_dashboard_and_pairwise(self):
        """Test with 3 providers: verify legend has all providers and all pairs are rendered."""
        master = sr.load_master_checks(self.master_path)
        for pname in ["prov_a", "prov_b", "prov_c"]:
            p_dir = self.responses_dir / pname
            p_dir.mkdir(parents=True)
            items = []
            for pid in sorted(master["prompts"].keys()):
                ans = master["prompts"][pid]["expected_marker_content"]
                if pname == "prov_b" and pid == "T06":
                    ans = ans.replace("龍", "龙")
                elif pname == "prov_c" and pid in ("T06", "T08"):
                    ans = ans.replace("龍", "龙").replace("瀧", "滝")
                items.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
            (p_dir / "MEGA.md").write_text("\n\n".join(items), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir)
        self.assertEqual(len(results["providers"]), 3)
        self.assertEqual(len(results["pairwise_diff"]), 3)

        html_file = Path(self.temp_dir) / "multi_report.html"
        html_content = sr.generate_html_report(results, html_file)
        self.assertIn("prov_a", html_content)
        self.assertIn("prov_b", html_content)
        self.assertIn("prov_c", html_content)
        self.assertIn("prov_a vs prov_b", html_content)
        self.assertIn("prov_a vs prov_c", html_content)
        self.assertIn("prov_b vs prov_c", html_content)

    def test_mega_batch_multi_run_evaluation(self):
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_runs"
        p_dir.mkdir(parents=True)

        # Run 1: Perfect
        r1_items = []
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            r1_items.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_dir / "MEGA.md").write_text("\n\n".join(r1_items), encoding="utf-8")

        # Run 2: T06 variation
        r2_items = []
        for pid in sorted(master["prompts"].keys()):
            ans = master["prompts"][pid]["expected_marker_content"]
            if pid == "T06":
                ans = "爱国发财龙马车关开学门书长东语鸟鱼点买卖归电欢铁银"
            r2_items.append(f"=== [{pid}] ===\n⟪\n{ans}\n⟫")
        (p_dir / "MEGA.r2.md").write_text("\n\n".join(r2_items), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=True)
        self.assertIn("r1", results["provider_runs"]["provider_runs"])
        self.assertIn("r2", results["provider_runs"]["provider_runs"])
        self.assertAlmostEqual(results["provider_runs"]["provider_runs"]["r1"]["accuracy"], 100.0, places=1)
        self.assertLess(results["provider_runs"]["provider_runs"]["r2"]["accuracy"], 100.0)
        self.assertGreater(results["run_disagreements"]["provider_runs"], 0.0)

    def test_multi_run_truncated_run_gets_zero_and_disagreement(self):
        """In multi-run mode, truncated run r2 must get 0 points on truncated prompts without r1 copying."""
        master = sr.load_master_checks(self.master_path)
        p_dir = self.responses_dir / "provider_zero_trunc"
        p_dir.mkdir(parents=True)

        # r1 has full 40 prompts
        r1_items = [f"=== [{pid}] ===\n⟪\n{master['prompts'][pid]['expected_marker_content']}\n⟫" for pid in sorted(master["prompts"].keys())]
        (p_dir / "MEGA.md").write_text("\n\n".join(r1_items), encoding="utf-8")

        # r2 is truncated at prompt 20 (prompts 21~40 missing)
        r2_items = [f"=== [{pid}] ===\n⟪\n{master['prompts'][pid]['expected_marker_content']}\n⟫" for pid in sorted(master["prompts"].keys())[:20]]
        (p_dir / "MEGA.r2.md").write_text("\n\n".join(r2_items), encoding="utf-8")

        results = sr.run_scoring(self.master_path, self.responses_dir, is_runs_mode=True)
        
        p_runs = results["provider_runs"]["provider_zero_trunc"]
        self.assertAlmostEqual(p_runs["r1"]["accuracy"], 100.0, places=1)
        # r2 must have lower accuracy (~65.8%) because prompts 21~40 were truncated (scored 0)
        self.assertLess(p_runs["r2"]["accuracy"], 70.0)
        self.assertGreater(p_runs["r2"]["accuracy"], 60.0)
        
        # Verify failures recorded for r2 on T21~T40
        r2_failures = [f for f in results["failures"] if f["run"] == "r2"]
        self.assertGreater(len(r2_failures), 0)
        failed_pids = set(f["prompt_id"] for f in r2_failures)
        self.assertIn("T21", failed_pids)
        self.assertIn("T40", failed_pids)
        
        # Verify run disagreement rate is greater than 0
        self.assertGreater(results["run_disagreements"]["provider_zero_trunc"], 0.0)


if __name__ == "__main__":
    unittest.main()
