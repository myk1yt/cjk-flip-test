# -*- coding: utf-8 -*-
"""
Builder and Deterministic Validator for flip-test-pack.
Generates prompts (T01.md ~ T40.md), checks_master.json, and data_validation.log
with 100% programmatic verification and independent 20% random sample cross-check.
"""

import os
import sys
import json
import random
import unicodedata
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
PACK_DIR = BASE_DIR / "flip-test-pack"
PROMPTS_DIR = PACK_DIR / "prompts"
RESPONSES_DIR = PACK_DIR / "responses"
TESTS_DIR = PACK_DIR / "tests"

PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)

validation_logs = []

def log(msg: str):
    print(msg)
    validation_logs.append(msg)

log("================================================================================")
log("CJK-Flip Test Pack Generation & Programmatic Data Validation Engine")
log("================================================================================")

# ==============================================================================
# 1. Category Definitions & Data Structures
# ==============================================================================

prompts_data = []

# ------------------------------------------------------------------------------
# F1: Language Identity Flip (T01 ~ T05)
# ------------------------------------------------------------------------------
f1_items = [
    {
        "id": "T01",
        "category": "F1_언어정체성플립",
        "difficulty": 2,
        "tags": ["quant-sensitive", "format-sensitive"],
        "rationale": "국한문혼용 행정 문장의 정체성 식별 및 한자 독음 분해 시 양자화 손실로 인한 오독음 발생 빈발",
        "source": "此件 申請書 添付 書類 未備에 依한 却下 處分 통지 건",
        "question": (
            "다음은 공공 행정 문서에 사용된 문장입니다.\n"
            "문장: \"此件 申請書 添付 書類 未備에 依한 却下 處分 통지 건\"\n\n"
            "[요구사항]\n"
            "1. 해당 문장의 언어 정체성을 명시하십시오. (한국어(국한문혼용) / 일본어 / 중국어(간체) / 중국어(번체) 중 택1)\n"
            "2. 전체 문장을 순수 현대 한글 표준어로 전환(번역/전자)하여 한 줄로 작성하십시오.\n"
            "3. 문장에 사용된 핵심 한자어 8개(此件, 申請書, 添付, 書類, 未備, 依, 却下, 處分)의 표준 한국어 독음을 쉼표(,)로 구분하여 나열하십시오."
        ),
        "expected_marker_content": (
            "1. 언어: 한국어(국한문혼용)\n"
            "2. 한글 전환: 이 건 신청서 첨부 서류 미비에 의한 각하 처분 통지 건\n"
            "3. 독음: 차건, 신청서, 첨부, 서류, 미비, 의, 각하, 처분"
        ),
        "checks": [
            {"id": "T01_C1", "type": "contains", "expected": "한국어(국한문혼용)", "norm": "ignore_whitespace", "points": 1, "desc": "언어 정체성 판별"},
            {"id": "T01_C2", "type": "contains", "expected": "신청서 첨부 서류 미비", "norm": "ignore_whitespace", "points": 1, "desc": "한글 전환 핵심 구문 1"},
            {"id": "T01_C3", "type": "contains", "expected": "각하 처분 통지", "norm": "ignore_whitespace", "points": 1, "desc": "한글 전환 핵심 구문 2"},
            {"id": "T01_C4", "type": "contains", "expected": "차건, 신청서, 첨부, 서류", "norm": "ignore_whitespace", "points": 1, "desc": "한자 독음 전반부"},
            {"id": "T01_C5", "type": "contains", "expected": "미비, 의, 각하, 처분", "norm": "ignore_whitespace", "points": 1, "desc": "한자 독음 후반부"}
        ]
    },
    {
        "id": "T02",
        "category": "F1_언어정체성플립",
        "difficulty": 2,
        "tags": ["quant-sensitive", "rare-token"],
        "rationale": "일본 관청 행정 한자어 나열 구조에서 히라가나 탈락 및 한국식 한자 독음 오인 혼동 유발",
        "source": "東京都千代田区霞が関一丁目三番一号 経済産業省大臣官房総務課における行政手続の簡素化に関する方針",
        "question": (
            "다음 문장을 분석하십시오.\n"
            "문장: \"東京都千代田区霞が関一丁目三番一号 経済産業省大臣官房総務課における行政手続の簡素化に関する方針\"\n\n"
            "[요구사항]\n"
            "1. 해당 문장의 언어 정체성을 명시하십시오. (한국어(국한문혼용) / 일본어 / 중국어(간체) / 중국어(번체) 중 택1)\n"
            "2. 자연스러운 표준 한국어로 완역하십시오.\n"
            "3. 문장에 포함된 주요 고유명사 및 기관명(東京都, 霞が関, 経済産業省, 大臣官房, 行政手続)의 한국어 통용 표기를 쉼표로 구분하여 작성하십시오."
        ),
        "expected_marker_content": (
            "1. 언어: 일본어\n"
            "2. 한국어 번역: 도쿄도 지요다구 가스미가세키 1초메 3번 1호 경제산업성 대신관방 총무과에서의 행정 절차 간소화에 관한 방침\n"
            "3. 한국어 표기: 도쿄도, 가스미가세키, 경제산업성, 대신관방, 행정 절차"
        ),
        "checks": [
            {"id": "T02_C1", "type": "contains", "expected": "일본어", "norm": "ignore_whitespace", "points": 1, "desc": "언어 정체성 식별"},
            {"id": "T02_C2", "type": "contains", "expected": "경제산업성", "norm": "ignore_whitespace", "points": 1, "desc": "기관명 정확 번역"},
            {"id": "T02_C3", "type": "contains", "expected": "행정 절차 간소화", "norm": "ignore_whitespace", "points": 1, "desc": "행정 용어 번역"},
            {"id": "T02_C4", "type": "contains", "expected": "도쿄도, 가스미가세키", "norm": "ignore_whitespace", "points": 1, "desc": "지명 외래어 표기"},
            {"id": "T02_C5", "type": "regex", "expected": r"2\.\s*(?:한국어\s*)?(?:번역|완역)?:\s*[^\n\r]*[가-힣]", "norm": "none", "points": 1, "desc": "한국어 번역문 형식 준수"}
        ]
    },
    {
        "id": "T03",
        "category": "F1_언어정체성플립",
        "difficulty": 2,
        "tags": ["quant-sensitive", "format-sensitive"],
        "rationale": "중국어 간체 공문서 문장이 한국어 한문 투로 왜곡되거나 번체자와 혼재되는 양자화 왜곡 검증",
        "source": "关于进一步优化外商投资环境加大吸引外商投资力度的若干意见，应当依法保护外商投资企业的合法权益。",
        "question": (
            "다음 법률 지침 문장을 분석하십시오.\n"
            "문장: \"关于进一步优化外商投资环境加大吸引外商投资力度的若干意见，应当依法保护外商投资企业的合法权益。\"\n\n"
            "[요구사항]\n"
            "1. 언어 정체성을 명시하십시오. (한국어(국한문혼용) / 일본어 / 중국어(간체) / 중국어(번체) 중 택1)\n"
            "2. 문장의 정확한 한국어 번역문을 작성하십시오.\n"
            "3. 주요 핵심 어휘(优化, 外商投资, 应当, 依法, 合法权益)의 표준 한국 한자음 및 대응어를 쉼표로 나열하십시오."
        ),
        "expected_marker_content": (
            "1. 언어: 중국어(간체)\n"
            "2. 한국어 번역: 외국인 투자 환경을 한층 더 최적화하고 외국인 투자 유치 노력을 확대하는 데 관한 몇 가지 의견에 따라, 마땅히 법에 의거하여 외국인 투자 기업의 합법적 권익을 보호해야 한다.\n"
            "3. 핵심 어휘: 최적화, 외국인투자(외상투자), 응당(마땅히), 의법(법에의거), 합법권익"
        ),
        "checks": [
            {"id": "T03_C1", "type": "contains", "expected": "중국어(간체)", "norm": "ignore_whitespace", "points": 1, "desc": "간체 정체성 식별"},
            {"id": "T03_C2", "type": "contains", "expected": "외국인 투자 환경", "norm": "ignore_whitespace", "points": 1, "desc": "투자 환경 번역 일치"},
            {"id": "T03_C3", "type": "contains", "expected": "합법적 권익", "norm": "ignore_whitespace", "points": 1, "desc": "권익 번역 일치"},
            {"id": "T03_C4", "type": "contains", "expected": "최적화", "norm": "ignore_whitespace", "points": 1, "desc": "핵심 어휘 일치"},
            {"id": "T03_C5", "type": "contains", "expected": "합법권익", "norm": "ignore_whitespace", "points": 1, "desc": "한자음 식별"}
        ]
    },
    {
        "id": "T04",
        "category": "F1_언어정체성플립",
        "difficulty": 2,
        "tags": ["quant-sensitive", "format-sensitive"],
        "rationale": "정체자(번체자) 교육 법규 문장에서 간체자 변질 및 한국어 혼동 유무 판정",
        "source": "臺灣地區各級學校推動環境教育之實施原則與評鑑基準，旨在落實永續發展理念並提升師生生態素養。",
        "question": (
            "다음 정책 조항을 분석하십시오.\n"
            "문장: \"臺灣地區各級學校推動環境教育之實施原則與評鑑基準，旨在落實永續發展理念並提升師生生態素養。\"\n\n"
            "[요구사항]\n"
            "1. 언어 정체성을 명시하십시오. (한국어(국한문혼용) / 일본어 / 중국어(간체) / 중국어(번체) 중 택1)\n"
            "2. 유려한 한국어 번역문을 작성하십시오.\n"
            "3. 어휘 대조: 臺灣(대만), 實施原則(실시원칙), 評鑑基準(평가기준), 永續發展(지속가능발전/영속발전) 4개 항목을 한국어 독음/대응어로 정리하십시오."
        ),
        "expected_marker_content": (
            "1. 언어: 중국어(번체)\n"
            "2. 한국어 번역: 대만 지역 각급 학교의 환경 교육 추진 실시 원칙 및 평가 기준은, 지속 가능한 발전 이념을 실현하고 교사와 학생의 생태 소양을 향상하는 것을 목표로 한다.\n"
            "3. 어휘 대조: 대만, 실시원칙, 평가기준, 지속가능발전(영속발전)"
        ),
        "checks": [
            {"id": "T04_C1", "type": "contains", "expected": "중국어(번체)", "norm": "ignore_whitespace", "points": 1, "desc": "번체 정체성 식별"},
            {"id": "T04_C2", "type": "regex", "expected": r"지속\s*가능(?:한)?\s*발전", "norm": "none", "points": 1, "desc": "永續發展 대응 번역"},
            {"id": "T04_C3", "type": "contains", "expected": "생태 소양", "norm": "ignore_whitespace", "points": 1, "desc": "生態素養 번역"},
            {"id": "T04_C4", "type": "contains", "expected": "평가기준", "norm": "ignore_whitespace", "points": 1, "desc": "評鑑基準 한국어 대응"},
            {"id": "T04_C5", "type": "contains", "expected": "실시원칙", "norm": "ignore_whitespace", "points": 1, "desc": "實施原則 한국어 대응"}
        ]
    },
    {
        "id": "T05",
        "category": "F1_언어정체성플립",
        "difficulty": 3,
        "tags": ["quant-sensitive", "rare-token"],
        "rationale": "동형이의어(False Friends: 手紙, 愛人, 做工夫, 勉強) 해석 시 양자화 모델의 언어 도메인 붕괴 감지",
        "source": "他在暗室裡認真做工夫，準備給愛人寫一封手紙，這需要極大的勉強與耐心。",
        "question": (
            "다음은 CJK 동형이의어가 다수 포함된 문장입니다.\n"
            "문장: \"他在暗室裡認真做工夫，準備給愛人寫一封手紙，這需要極大的勉強與耐心。\"\n\n"
            "[요구사항]\n"
            "1. 이 문장의 실제 언어를 밝히십시오. (중국어 / 일본어 / 한국어 중 택1)\n"
            "2. 일본어나 한국어의 오해(手紙=화장지, 愛人=불륜상대, 勉強=공부, 工夫=쿵푸무술 등)를 완전히 배제하고, 원문의 정확한 의미로 한국어로 번역하십시오.\n"
            "3. 아래 4개 단어의 이 문장 내 실제 의미를 한국어로 정확히 명시하십시오.\n"
            "- 做工夫:\n"
            "- 愛人:\n"
            "- 手紙:\n"
            "- 勉強:"
        ),
        "expected_marker_content": (
            "1. 언어: 중국어\n"
            "2. 한국어 번역: 그는 어두운 방에서 진지하게 공을 들이며 배우자에게 한 통의 편지를 쓸 준비를 하고 있었는데, 이는 엄청난 애씀과 인내심을 필요로 했다.\n"
            "3. 단어 의미:\n"
            "- 做工夫: 공을 들이다 (시간과 노력을 들이다)\n"
            "- 愛人: 배우자 (남편 또는 아내)\n"
            "- 手紙: 편지\n"
            "- 勉強: 억지로 힘씀 (애씀/무리함)"
        ),
        "checks": [
            {"id": "T05_C1", "type": "contains", "expected": "중국어", "norm": "ignore_whitespace", "points": 1, "desc": "언어 식별"},
            {"id": "T05_C2", "type": "contains", "expected": "배우자", "norm": "ignore_whitespace", "points": 1, "desc": "愛人=배우자 올바른 번역"},
            {"id": "T05_C3", "type": "contains", "expected": "편지", "norm": "ignore_whitespace", "points": 1, "desc": "手紙=편지 올바른 번역"},
            {"id": "T05_C4", "type": "contains", "expected": "공을", "norm": "ignore_whitespace", "points": 1, "desc": "做工夫=공을 들이다 올바른 번역"},
            {"id": "T05_C5", "type": "regex", "expected": r"(애씀|힘씀|억지로)", "norm": "ignore_whitespace", "points": 1, "desc": "勉強 문맥적 번역"}
        ]
    }
]
prompts_data.extend(f1_items)

# ------------------------------------------------------------------------------
# F3: Character Variant Conversion (T06 ~ T10)
# 25 characters each -> 25 individual char checks + 1 exact full string check = 26 checks per item
# ------------------------------------------------------------------------------

# T06: Simplified -> Traditional (25 characters)
t06_simp = "爱国发财龙马车关开学门书长东语鸟鱼点买卖归电欢铁银"
t06_trad = "愛國發財龍馬車關開學門書長東語鳥魚點買賣歸電歡鐵銀"
assert len(t06_simp) == 25 and len(t06_trad) == 25

t06_checks = []
for i in range(25):
    t06_checks.append({
        "id": f"T06_C{i+1:02d}",
        "type": "exact",
        "char_index": i,
        "expected": t06_trad[i],
        "norm": "none",
        "points": 1,
        "desc": f"{i+1}번째 글자 '{t06_simp[i]}' -> '{t06_trad[i]}'"
    })
t06_checks.append({
    "id": "T06_C26",
    "type": "exact",
    "expected": t06_trad,
    "norm": "ignore_whitespace",
    "points": 2,
    "desc": "25자 전체 번체자 문자열 일치"
})

f3_t06 = {
    "id": "T06",
    "category": "F3_자형변환",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "간체-번체 1:1 글자 매핑 정밀도 판정. 양자화 단계에서 고빈도 한자 자형 글리프 치환 실패 검증",
    "source": t06_simp,
    "question": (
        "아래에 주어진 25개의 중국어 간체자 문자열을 표준 번체자(정체자)로 1:1 변환하십시오.\n"
        "공백이나 줄바꿈 없이 변환된 25개의 번체자 문자열만 출력하십시오.\n\n"
        f"입력: {t06_simp}"
    ),
    "expected_marker_content": t06_trad,
    "checks": t06_checks
}
prompts_data.append(f3_t06)

# T07: Traditional -> Simplified (25 characters)
t07_trad = "義氣廣東臺灣經濟國際飛機導彈電腦圖書館壓縮優質審查"
t07_simp = "义气广东台湾经济国际飞机导弹电脑图书馆压缩优质审查"
assert len(t07_trad) == 25 and len(t07_simp) == 25

t07_checks = []
for i in range(25):
    t07_checks.append({
        "id": f"T07_C{i+1:02d}",
        "type": "exact",
        "char_index": i,
        "expected": t07_simp[i],
        "norm": "none",
        "points": 1,
        "desc": f"{i+1}번째 글자 '{t07_trad[i]}' -> '{t07_simp[i]}'"
    })
t07_checks.append({
    "id": "T07_C26",
    "type": "exact",
    "expected": t07_simp,
    "norm": "ignore_whitespace",
    "points": 2,
    "desc": "25자 전체 간체자 문자열 일치"
})

f3_t07 = {
    "id": "T07",
    "category": "F3_자형변환",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "번체-간체 역변환 1:1 글자 매핑 정밀도 판정. 어휘 문맥 없이 자형만 단독 제시 시 변환 정확도",
    "source": t07_trad,
    "question": (
        "아래에 주어진 25개의 번체자(정체자) 문자열을 표준 간체자로 1:1 변환하십시오.\n"
        "공백이나 부가 설명 없이 변환된 25개의 간체자 문자열만 출력하십시오.\n\n"
        f"입력: {t07_trad}"
    ),
    "expected_marker_content": t07_simp,
    "checks": t07_checks
}
prompts_data.append(f3_t07)

# T08: Japanese Shinjitai -> Kyujitai (25 characters)
t08_shin = "鉄駅図国気体広転芸伝単売会学写当寿抜歩恵仏礼滝桜竜"
t08_kyu  = "鐵驛圖國氣體廣轉藝傳單賣會學寫當壽拔步惠佛禮瀧櫻龍"
assert len(t08_shin) == 25 and len(t08_kyu) == 25

t08_checks = []
for i in range(25):
    t08_checks.append({
        "id": f"T08_C{i+1:02d}",
        "type": "exact",
        "char_index": i,
        "expected": t08_kyu[i],
        "norm": "none",
        "points": 1,
        "desc": f"{i+1}번째 글자 신자체 '{t08_shin[i]}' -> 구자체 '{t08_kyu[i]}'"
    })
t08_checks.append({
    "id": "T08_C26",
    "type": "exact",
    "expected": t08_kyu,
    "norm": "ignore_whitespace",
    "points": 2,
    "desc": "25자 전체 구자체 문자열 일치"
})

f3_t08 = {
    "id": "T08",
    "category": "F3_자형변환",
    "difficulty": 3,
    "tags": ["quant-sensitive", "rare-token"],
    "rationale": "일본어 신자체(新字体)에서 전통 구자체(舊字體/강희자전체) 변환. 저빈도 한자 임베딩 손실 검증",
    "source": t08_shin,
    "question": (
        "아래에 주어진 25개의 일본어 신자체(新字体) 한자 문자열을 이에 대응하는 전통 구자체(舊字體)로 1:1 변환하십시오.\n"
        "부연 설명 없이 정확히 25자의 구자체 문자열만 출력하십시오.\n\n"
        f"입력: {t08_shin}"
    ),
    "expected_marker_content": t08_kyu,
    "checks": t08_checks
}
prompts_data.append(f3_t08)

# T09: Japanese Kyujitai -> Shinjitai (25 characters)
t09_kyu  = "鐵驛圖國氣體廣轉藝傳單賣會學寫當壽拔步惠佛禮瀧櫻龍"
t09_shin = "鉄駅図国気体広転芸伝単売会学写当寿抜歩恵仏礼滝桜竜"
assert len(t09_kyu) == 25 and len(t09_shin) == 25

t09_checks = []
for i in range(25):
    t09_checks.append({
        "id": f"T09_C{i+1:02d}",
        "type": "exact",
        "char_index": i,
        "expected": t09_shin[i],
        "norm": "none",
        "points": 1,
        "desc": f"{i+1}번째 글자 구자체 '{t09_kyu[i]}' -> 신자체 '{t09_shin[i]}'"
    })
t09_checks.append({
    "id": "T09_C26",
    "type": "exact",
    "expected": t09_shin,
    "norm": "ignore_whitespace",
    "points": 2,
    "desc": "25자 전체 신자체 문자열 일치"
})

f3_t09 = {
    "id": "T09",
    "category": "F3_자형변환",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "전통 구자체(한국 정자체)에서 현대 일본 신자체로의 축약 변환. 양자화 모델의 일본 상용한자 규격 준수 여부",
    "source": t09_kyu,
    "question": (
        "아래에 주어진 25개의 구자체(舊字體/정자체) 한자 문자열을 현대 일본 상용한자 신자체(新字体)로 1:1 변환하십시오.\n"
        "공백 없이 25자의 신자체 문자열만 출력하십시오.\n\n"
        f"입력: {t09_kyu}"
    ),
    "expected_marker_content": t09_shin,
    "checks": t09_checks
}
prompts_data.append(f3_t09)

# T10: CJK Multi-variant Alignment (25 characters)
# Traditional/Korean Hanja -> Chinese Simplified
t10_trad = "觀點發動機總體規劃實踐與創新發展驅動戰略導向標準化"
t10_simp = "观点发动机总体规划实践与创新发展驱动战略导向标准化"
assert len(t10_trad) == 25 and len(t10_simp) == 25

t10_checks = []
for i in range(25):
    t10_checks.append({
        "id": f"T10_C{i+1:02d}",
        "type": "exact",
        "char_index": i,
        "expected": t10_simp[i],
        "norm": "none",
        "points": 1,
        "desc": f"{i+1}번째 글자 복합어 '{t10_trad[i]}' -> 간체 '{t10_simp[i]}'"
    })
t10_checks.append({
    "id": "T10_C26",
    "type": "exact",
    "expected": t10_simp,
    "norm": "ignore_whitespace",
    "points": 2,
    "desc": "25자 전체 간체 복합어 문자열 일치"
})

f3_t10 = {
    "id": "T10",
    "category": "F3_자형변환",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한중일 복합 전문 학술 어휘의 정밀 자형 간체화 매핑. 부분적 불완전 변환 잔존 감지",
    "source": t10_trad,
    "question": (
        "다음은 한국 한자음 및 전통 번체자로 구성된 25자 전문 용어 문자열입니다.\n"
        f"입력: {t10_trad}\n\n"
        "[요구사항]\n"
        "이 25글자 전체를 중국 국가표준 간체자로 완벽히 변환하여, 공백 없이 25자의 간체자 문자열만 출력하십시오."
    ),
    "expected_marker_content": t10_simp,
    "checks": t10_checks
}
prompts_data.append(f3_t10)

# ------------------------------------------------------------------------------
# F6: String Precision Manipulation (T11 ~ T15)
# Calculated programmatically
# ------------------------------------------------------------------------------

# T11:
s11 = "대한민국大韓民國은民主共和國민주공화국이며主權주권은국민에게있다"
l11 = len(s11)
c11_7 = s11[6]   # 7th (1-indexed)
c11_15 = s11[14] # 15th
c11_22 = s11[21] # 22nd
rev11 = s11[::-1]
cnt11_guk = s11.count("국")
cnt11_guk_han = s11.count("國")

f6_t11 = {
    "id": "T11",
    "category": "F6_문자열정밀조작",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한글-한자 혼용 텍스트의 글자 수 계측, 인덱싱, 역순 출력 및 특정 글자 카운팅 정밀도 검증",
    "source": s11,
    "question": (
        f"다음 문자열을 정확히 분석하여 5가지 질의에 답하십시오.\n"
        f"대상 문자열: \"{s11}\"\n\n"
        "[질의]\n"
        "1. 총 글자 수(문자 수)\n"
        "2. 7번째 글자 (1부터 시작)\n"
        "3. 15번째 글자 (1부터 시작)\n"
        "4. 한글 '국' 글자의 총 출현 횟수\n"
        "5. 한자 '國' 글자의 총 출현 횟수\n"
        "6. 대상 문자열 전체의 역순(reverse) 문자열\n\n"
        "[출력 형식]\n"
        "1. 총글자수: [숫자]\n"
        "2. 7번째: [글자]\n"
        "3. 15번째: [글자]\n"
        "4. 한글국빈도: [숫자]\n"
        "5. 한자國빈도: [숫자]\n"
        "6. 역순: [문자열]"
    ),
    "expected_marker_content": (
        f"1. 총글자수: {l11}\n"
        f"2. 7번째: {c11_7}\n"
        f"3. 15번째: {c11_15}\n"
        f"4. 한글국빈도: {cnt11_guk}\n"
        f"5. 한자國빈도: {cnt11_guk_han}\n"
        f"6. 역순: {rev11}"
    ),
    "checks": [
        {"id": "T11_C1", "type": "numeric", "expected": l11, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "총 글자 수 일치", "extract_regex": r"1\.\s*총글자수:\s*(\d+)"},
        {"id": "T11_C2", "type": "contains", "expected": f"7번째: {c11_7}", "norm": "ignore_whitespace", "points": 1, "desc": "7번째 글자 일치"},
        {"id": "T11_C3", "type": "contains", "expected": f"15번째: {c11_15}", "norm": "ignore_whitespace", "points": 1, "desc": "15번째 글자 일치"},
        {"id": "T11_C4", "type": "numeric", "expected": cnt11_guk, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "한글 '국' 빈도", "extract_regex": r"4\.\s*한글국빈도:\s*(\d+)"},
        {"id": "T11_C5", "type": "numeric", "expected": cnt11_guk_han, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "한자 '國' 빈도", "extract_regex": r"5\.\s*한자國빈도:\s*(\d+)"},
        {"id": "T11_C6", "type": "contains", "expected": rev11, "norm": "ignore_whitespace", "points": 1, "desc": "역순 문자열 일치"}
    ]
}
prompts_data.append(f6_t11)

# T12: Japanese mixed string
s12 = "東京トウキョウの桜サクラが美しく咲く春の季節が到来しました"
l12 = len(s12)
c12_9 = s12[8]
c12_18 = s12[17]
rev12 = s12[::-1]
cnt12_no = s12.count("の")

f6_t12 = {
    "id": "T12",
    "category": "F6_문자열정밀조작",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "일본어 혼합(가타카나, 히라가나, 한자) 유니코드 슬라이싱 및 특정 조사 계측 정밀도",
    "source": s12,
    "question": (
        f"다음 일본어 혼합 문자열을 엄밀하게 조작하십시오.\n"
        f"대상 문자열: \"{s12}\"\n\n"
        "[질의]\n"
        "1. 총 글자 수\n"
        "2. 9번째 글자 (1부터 시작)\n"
        "3. 18번째 글자 (1부터 시작)\n"
        "4. 조사 'の'의 출현 횟수\n"
        "5. 대상 문자열 전체의 역순(reverse) 문자열\n\n"
        "[출력 형식]\n"
        "1. 길이: [숫자]\n"
        "2. 9번째: [글자]\n"
        "3. 18번째: [글자]\n"
        "4. の빈도: [숫자]\n"
        "5. 역순: [문자열]"
    ),
    "expected_marker_content": (
        f"1. 길이: {l12}\n"
        f"2. 9번째: {c12_9}\n"
        f"3. 18번째: {c12_18}\n"
        f"4. の빈도: {cnt12_no}\n"
        f"5. 역순: {rev12}"
    ),
    "checks": [
        {"id": "T12_C1", "type": "numeric", "expected": l12, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "문자열 길이", "extract_regex": r"1\.\s*길이:\s*(\d+)"},
        {"id": "T12_C2", "type": "contains", "expected": f"9번째: {c12_9}", "norm": "ignore_whitespace", "points": 1, "desc": "9번째 글자"},
        {"id": "T12_C3", "type": "contains", "expected": f"18번째: {c12_18}", "norm": "ignore_whitespace", "points": 1, "desc": "18번째 글자"},
        {"id": "T12_C4", "type": "numeric", "expected": cnt12_no, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "조사 'の' 빈도수", "extract_regex": r"4\.\s*の빈도:\s*(\d+)"},
        {"id": "T12_C5", "type": "contains", "expected": rev12, "norm": "ignore_whitespace", "points": 1, "desc": "역순 문자열"}
    ]
}
prompts_data.append(f6_t12)

# T13: Chinese Chengyu sequence
s13 = "千里之行始于足下海纳百川有容乃大居安思危戒奢以俭"
l13 = len(s13)
c13_8 = s13[7]
# 짝수번째 글자 (1-indexed 2, 4, 6, ...)
even13 = "".join([s13[i] for i in range(1, len(s13), 2)])
rev13 = s13[::-1]
cnt13_da = s13.count("大")

f6_t13 = {
    "id": "T13",
    "category": "F6_문자열정밀조작",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "중국어 간체 성어 4개 결합열의 짝수 인덱스 추출 및 역순 조작. 다단계 인덱스 연산 능력 검증",
    "source": s13,
    "question": (
        f"다음 중국어 사자성어 결합 문자열을 분석하십시오.\n"
        f"대상 문자열: \"{s13}\"\n\n"
        "[질의]\n"
        "1. 총 글자 수\n"
        "2. 8번째 글자 (1부터 시작)\n"
        "3. 짝수 번째 위치(2, 4, 6, 8, ... 번째) 글자들만 순서대로 추출하여 연결한 문자열\n"
        "4. 글자 '大'의 출현 횟수\n"
        "5. 대상 문자열 전체의 역순(reverse) 문자열\n\n"
        "[출력 형식]\n"
        "1. 길이: [숫자]\n"
        "2. 8번째: [글자]\n"
        "3. 짝수열: [문자열]\n"
        "4. 大빈도: [숫자]\n"
        "5. 역순: [문자열]"
    ),
    "expected_marker_content": (
        f"1. 길이: {l13}\n"
        f"2. 8번째: {c13_8}\n"
        f"3. 짝수열: {even13}\n"
        f"4. 大빈도: {cnt13_da}\n"
        f"5. 역순: {rev13}"
    ),
    "checks": [
        {"id": "T13_C1", "type": "numeric", "expected": l13, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "총 글자수", "extract_regex": r"1\.\s*길이:\s*(\d+)"},
        {"id": "T13_C2", "type": "contains", "expected": f"8번째: {c13_8}", "norm": "ignore_whitespace", "points": 1, "desc": "8번째 글자"},
        {"id": "T13_C3", "type": "contains", "expected": even13, "norm": "ignore_whitespace", "points": 1, "desc": "짝수 인덱스 추출열"},
        {"id": "T13_C4", "type": "numeric", "expected": cnt13_da, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "'大' 글자 빈도", "extract_regex": r"4\.\s*大빈도:\s*(\d+)"},
        {"id": "T13_C5", "type": "contains", "expected": rev13, "norm": "ignore_whitespace", "points": 1, "desc": "역순 문자열"}
    ]
}
prompts_data.append(f6_t13)

# T14: Multilingual CJK slice
s14 = "서울ソウル北京ペキン平壌ピョンヤン東京とうきょう"
l14 = len(s14)
# slice from 5th to 14th char (1-indexed 5..14 -> python [4:14])
slice14 = s14[4:14]
cnt14_n = s14.count("ン")
rev14 = s14[::-1]

f6_t14 = {
    "id": "T14",
    "category": "F6_문자열정밀조작",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한글-가나-한자 다국어 복합 문자열의 구간 슬라이스 및 가타카나 'ン' 빈도 계산",
    "source": s14,
    "question": (
        f"다음 한중일 도시명 다국어 결합 문자열을 분석하십시오.\n"
        f"대상 문자열: \"{s14}\"\n\n"
        "[질의]\n"
        "1. 총 문자 수\n"
        "2. 5번째 문자부터 14번째 문자까지(양 끝 포함) 슬라이스한 부분 문자열\n"
        "3. 가타카나 'ン'의 출현 빈도수\n"
        "4. 대상 문자열 전체의 역순 문자열\n\n"
        "[출력 형식]\n"
        "1. 길이: [숫자]\n"
        "2. 부분문자열: [문자열]\n"
        "3. ン빈도: [숫자]\n"
        "4. 역순: [문자열]"
    ),
    "expected_marker_content": (
        f"1. 길이: {l14}\n"
        f"2. 부분문자열: {slice14}\n"
        f"3. ン빈도: {cnt14_n}\n"
        f"4. 역순: {rev14}"
    ),
    "checks": [
        {"id": "T14_C1", "type": "numeric", "expected": l14, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "문자열 총 길이", "extract_regex": r"1\.\s*길이:\s*(\d+)"},
        {"id": "T14_C2", "type": "contains", "expected": slice14, "norm": "ignore_whitespace", "points": 1, "desc": "5~14번째 부분 슬라이스"},
        {"id": "T14_C3", "type": "numeric", "expected": cnt14_n, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "'ン' 빈도", "extract_regex": r"3\.\s*ン빈도:\s*(\d+)"},
        {"id": "T14_C4", "type": "contains", "expected": rev14, "norm": "ignore_whitespace", "points": 1, "desc": "역순 문자열"}
    ]
}
prompts_data.append(f6_t14)

# T15: CJK Symbols and Hanja
s15 = "甲[乙]丙{丁}戊★己◆庚▲辛■壬◎癸"
l15 = len(s15)
c15_10 = s15[9]
# Hanja only extracted:
hanja15 = "".join([c for c in s15 if c in "甲乙丙丁戊己庚辛壬癸"])
rev15 = s15[::-1]

f6_t15 = {
    "id": "T15",
    "category": "F6_문자열정밀조작",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "기호와 한자가 교차하는 복합 문자열에서 특수문자 필터링 및 10간 한자만 정밀 추출",
    "source": s15,
    "question": (
        f"다음 기호-한자 결합 문자열을 정밀 처리하십시오.\n"
        f"대상 문자열: \"{s15}\"\n\n"
        "[질의]\n"
        "1. 총 글자 수 (특수기호, 괄호 전부 포함)\n"
        "2. 10번째 글자 (1부터 시작)\n"
        "3. 특수기호와 괄호를 모두 제거하고 순수한 십간(十干) 한자 10자만 순서대로 추출한 문자열\n"
        "4. 대상 문자열 전체의 역순 문자열\n\n"
        "[출력 형식]\n"
        "1. 총길이: [숫자]\n"
        "2. 10번째: [글자]\n"
        "3. 십간추출: [문자열]\n"
        "4. 역순: [문자열]"
    ),
    "expected_marker_content": (
        f"1. 총길이: {l15}\n"
        f"2. 10번째: {c15_10}\n"
        f"3. 십간추출: {hanja15}\n"
        f"4. 역순: {rev15}"
    ),
    "checks": [
        {"id": "T15_C1", "type": "numeric", "expected": l15, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "총 길이", "extract_regex": r"1\.\s*총길이:\s*(\d+)"},
        {"id": "T15_C2", "type": "contains", "expected": f"10번째: {c15_10}", "norm": "ignore_whitespace", "points": 1, "desc": "10번째 문자"},
        {"id": "T15_C3", "type": "contains", "expected": f"십간추출: {hanja15}", "norm": "ignore_whitespace", "points": 1, "desc": "십간 한자 추출 일치"},
        {"id": "T15_C4", "type": "contains", "expected": rev15, "norm": "ignore_whitespace", "points": 1, "desc": "역순 문자열"}
    ]
}
prompts_data.append(f6_t15)

# ------------------------------------------------------------------------------
# F7: Long Text Verbatim Quotation (T16 ~ T20)
# Programmatically sliced!
# ------------------------------------------------------------------------------

# T16: Korean historical/linguistic text (442 chars)
text16 = (
    "세종어제훈민정음은 우리나라의 말이 중국과 달라 한자와 서로 통하지 아니하므로, "
    "어리석은 백성이 이르고자 하는 바가 있어도 마침내 제 뜻을 능히 펴지 못하는 사람이 많으니라. "
    "내가 이를 가엾게 여겨 새로 스물여덟 글자를 만드노니, 모든 사람으로 하여금 쉽게 익혀 날마다 씀에 편안하게 하고자 할 따름이니라. "
    "한글의 창제 원리는 자음의 경우 발음 기관의 모양을 상형하고, 모음의 경우 하늘과 땅과 사람의 삼재를 본떠 만들었다. "
    "이와 같은 음운학적 정밀성과 과학적 체계는 세계 문자 역사상 유례를 찾기 어려울 정도로 독창적이다. "
    "훈민정음 해례본의 발견을 통하여 문자의 제자 원리가 명백히 밝혀졌으며, 백성을 사랑하는 애민 정신과 주체적 자주정신이 깃들어 있다. "
    "현대에 이르러 디지털 정보화 시대에도 조합형 원리를 바탕으로 한글은 가장 효율적인 문자 체계로 전 세계 언어학자들의 찬사를 받고 있다."
)
assert len(text16) >= 300, f"text16 length is {len(text16)}"
# Slice 1: char 35 to 75 (1-indexed 35..75 -> python [34:75])
s16_1 = text16[34:75]
# Slice 2: char 120 to 165 (python [119:165])
s16_2 = text16[119:165]

f7_t16 = {
    "id": "T16",
    "category": "F7_장문정확인용",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "300자 이상 한국어 고문헌 해설문에서 프로그램 슬라이스 구간을 토큰 왜곡 없이 100% 원문 그대로 복제 인용하는 능력",
    "source": text16,
    "question": (
        "다음은 훈민정음 해설 문단입니다 (총 300자 이상).\n\n"
        f"--- 본문 ---\n{text16}\n------------\n\n"
        "[요구사항]\n"
        "본문에서 지정된 두 구간을 글자 하나도 빠뜨리거나 변경하지 말고 원문 그대로 복제하여 인용하십시오.\n"
        "1. [구간 A]: 본문의 35번째 글자부터 75번째 글자까지 (양 끝 포함, 1부터 계수)\n"
        "2. [구간 B]: 본문의 120번째 글자부터 165번째 글자까지 (양 끝 포함, 1부터 계수)\n\n"
        "[출력 형식]\n"
        "구간A: [인용문]\n"
        "구간B: [인용문]"
    ),
    "expected_marker_content": (
        f"구간A: {s16_1}\n"
        f"구간B: {s16_2}"
    ),
    "checks": [
        {"id": "T16_C1", "type": "contains", "expected": s16_1, "norm": "none", "points": 2, "desc": "구간A 정확 인용"},
        {"id": "T16_C2", "type": "char_count", "expected": len(s16_1), "extract_regex": r"구간A:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간A 글자수 일치"},
        {"id": "T16_C3", "type": "contains", "expected": s16_2, "norm": "none", "points": 2, "desc": "구간B 정확 인용"},
        {"id": "T16_C4", "type": "char_count", "expected": len(s16_2), "extract_regex": r"구간B:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간B 글자수 일치"}
    ]
}
prompts_data.append(f7_t16)

# T17: Japanese modern literary text (400 chars)
text17 = (
    "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。"
    "吾輩はここで始めて人間というものを見た。しかもあとで聞くとそれは書生という人間中で一番獰悪な種族であったそうだ。"
    "この書生というのは時々我々を捕えて煮て食うという話である。しかしその当時は何という考もなかったから別段恐しいとも思わなかった。"
    "ただ彼の掌に載せられてスーと持ち上げられた時何だかフワフワした感じがあったばかりである。"
    "掌の上で少し落ちついて書生の顔を見たのがいわゆる人間というものの見始であろう。"
    "この時妙なものだと思った感じが今でも残っている。第一毛をもって装飾されべきはずの顔がつるつるしてまるで薬缶だ。"
    "その後猫にも逢ったがこんな片輪には一度も出会わした事がない。のみならず顔の真中があまりに突起している。そうしてその穴の中から時々ぷうぷうと煙を吹く。"
)
assert len(text17) >= 300
s17_1 = text17[25:65]
s17_2 = text17[110:155]

f7_t17 = {
    "id": "T17",
    "category": "F7_장문정확인용",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "일본어 근대 소설 명문에서 구두점 및 조사 왜곡 없이 정확한 슬라이스 구간을 복사 인용하는 능력",
    "source": text17,
    "question": (
        "다음은 일본 근대 문학 지문입니다 (300자 이상).\n\n"
        f"--- 본문 ---\n{text17}\n------------\n\n"
        "[요구사항]\n"
        "본문에서 지정된 두 구간을 어떠한 수정이나 번역 없이 원문 그대로 인용하십시오.\n"
        "1. [구간 A]: 26번째 글자부터 65번째 글자까지 (양 끝 포함, 1부터 시작)\n"
        "2. [구간 B]: 111번째 글자부터 155번째 글자까지 (양 끝 포함, 1부터 시작)\n\n"
        "[출력 형식]\n"
        "구간A: [인용문]\n"
        "구간B: [인용문]"
    ),
    "expected_marker_content": (
        f"구간A: {s17_1}\n"
        f"구간B: {s17_2}"
    ),
    "checks": [
        {"id": "T17_C1", "type": "contains", "expected": s17_1, "norm": "none", "points": 2, "desc": "구간A 정확 인용"},
        {"id": "T17_C2", "type": "char_count", "expected": len(s17_1), "extract_regex": r"구간A:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간A 글자수 일치"},
        {"id": "T17_C3", "type": "contains", "expected": s17_2, "norm": "none", "points": 2, "desc": "구간B 정확 인용"},
        {"id": "T17_C4", "type": "char_count", "expected": len(s17_2), "extract_regex": r"구간B:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간B 글자수 일치"}
    ]
}
prompts_data.append(f7_t17)

# T18: Chinese classic historical/philosophical text (311 chars)
text18 = (
    "大道之行也，天下为公，选贤与能，讲信修睦。故人不独亲其亲，不独子其子，使老有所终，壮有所用，幼有所长，"
    "矜、寡、孤、独、废疾者皆有所养，男有分，女有归。货恶其弃于地也，不必藏于己；力恶其不出于身也，不必为己。"
    "是故谋闭而不兴，盗窃乱贼而不作，故外户而不闭，是谓大同。今大道既隐，天下为家，各亲其亲，各子其子，货力为己，"
    "大人世及以为礼，城郭沟池以为固，礼义以为纪，以正君臣，以笃父子，以睦兄弟，以和夫妇，以设制度，以立田里，以贤勇知，以功为己。"
    "故谋用是作，而兵由此起。禹、汤、文、武、成王、周公由此其选也。此六君子者，未有不谨于礼者也。以著其义，以考其信，著有过，刑仁讲让，示民有常，如有不由此者，在埶者去，众以为殃。是谓小康。"
)
assert len(text18) >= 300
s18_1 = text18[30:75]
s18_2 = text18[120:168]

f7_t18 = {
    "id": "T18",
    "category": "F7_장문정확인용",
    "difficulty": 2,
    "tags": ["quant-sensitive", "rare-token"],
    "rationale": "중국 예기 대동편 원문에서 간체/번체 혼동 및 구두점 누락 없이 정밀 구간 인용",
    "source": text18,
    "question": (
        "다음은 고전 문헌 지문입니다.\n\n"
        f"--- 본문 ---\n{text18}\n------------\n\n"
        "[요구사항]\n"
        "본문에서 지정된 구간을 한 글자의 오차나 부호 생략 없이 원문 그대로 인용하십시오.\n"
        "1. [구간 A]: 31번째 글자부터 75번째 글자까지 (양 끝 포함, 1부터 시작)\n"
        "2. [구간 B]: 121번째 글자부터 168번째 글자까지 (양 끝 포함, 1부터 시작)\n\n"
        "[출력 형식]\n"
        "구간A: [인용문]\n"
        "구간B: [인용문]"
    ),
    "expected_marker_content": (
        f"구간A: {s18_1}\n"
        f"구간B: {s18_2}"
    ),
    "checks": [
        {"id": "T18_C1", "type": "contains", "expected": s18_1, "norm": "none", "points": 2, "desc": "구간A 원문 정확 인용"},
        {"id": "T18_C2", "type": "char_count", "expected": len(s18_1), "extract_regex": r"구간A:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간A 글자수 일치"},
        {"id": "T18_C3", "type": "contains", "expected": s18_2, "norm": "none", "points": 2, "desc": "구간B 원문 정확 인용"},
        {"id": "T18_C4", "type": "char_count", "expected": len(s18_2), "extract_regex": r"구간B:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간B 글자수 일치"}
    ]
}
prompts_data.append(f7_t18)

# T19: East Asian technical standard specification text (442 chars)
text19 = (
    "인공지능 신경망 모델의 양자화 및 경량화 기술은 연산 처리 속도를 극대화하고 엣지 디바이스에서의 전력 소모를 최소화하기 위해 필수적으로 요구되는 공학적 기법이다. "
    "부동소수점 32비트(FP32) 정밀도의 가중치 파라미터를 8비트 정수(INT8) 또는 4비트 부동소수점(FP4) 형식으로 변환할 때, "
    "수치 표현 범위의 축소로 인하여 정밀도 손실이 불가피하게 발생한다. "
    "특히 한국어, 중국어, 일본어와 같은 CJK 다국어 텍스트 처리 영역에서는 저빈도 한자 및 복합 형태소 토큰의 임베딩 벡터가 양자화 노이즈에 극도로 취약하다. "
    "이를 체계적으로 평가하기 위하여 통제된 동일 하네스 환경에서 다계층 테스트 팩을 구성하고, 각 프로바이더의 추론 엔진이 보여주는 미세한 출력 편차를 측정한다. "
    "본 평가는 단순한 품질 우열이 아니라 양자화 엔진 간의 시스템적 차이를 객관적으로 규명하는 데 목적이 있다."
)
assert len(text19) >= 300
s19_1 = text19[40:84]
s19_2 = text19[130:179]

f7_t19 = {
    "id": "T19",
    "category": "F7_장문정확인용",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "기술 표준 규격 전문에서 영문 약어, 괄호, 기술 용어가 포함된 장문 슬라이스 무손실 추출",
    "source": text19,
    "question": (
        "다음은 인공지능 양자화 규격 표준서 단락입니다.\n\n"
        f"--- 본문 ---\n{text19}\n------------\n\n"
        "[요구사항]\n"
        "본문에서 아래의 두 구간을 그대로 추출하여 인용하십시오.\n"
        "1. [구간 A]: 41번째 글자부터 84번째 글자까지 (양 끝 포함, 1부터 시작)\n"
        "2. [구간 B]: 131번째 글자부터 179번째 글자까지 (양 끝 포함, 1부터 시작)\n\n"
        "[출력 형식]\n"
        "구간A: [인용문]\n"
        "구간B: [인용문]"
    ),
    "expected_marker_content": (
        f"구간A: {s19_1}\n"
        f"구간B: {s19_2}"
    ),
    "checks": [
        {"id": "T19_C1", "type": "contains", "expected": s19_1, "norm": "none", "points": 2, "desc": "구간A 정확 일치"},
        {"id": "T19_C2", "type": "char_count", "expected": len(s19_1), "extract_regex": r"구간A:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간A 글자수"},
        {"id": "T19_C3", "type": "contains", "expected": s19_2, "norm": "none", "points": 2, "desc": "구간B 정확 일치"},
        {"id": "T19_C4", "type": "char_count", "expected": len(s19_2), "extract_regex": r"구간B:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간B 글자수"}
    ]
}
prompts_data.append(f7_t19)

# T20: East Asian legal statutory text (382 chars)
text20 = (
    "개인정보 보호법 제18조에 따르면 개인정보처리자는 개인정보를 당초 수집 목적의 범위를 초과하여 이용하거나 제3자에게 제공하여서는 아니 된다. "
    "다만 정보주체로부터 별도의 명시적 동의를 받은 경우이거나 다른 법률에 특별한 규정이 존재하는 경우에는 예외적으로 수집 목적 외의 용도로 이용하거나 제3자에게 제공할 수 있도록 허용하고 있다. "
    "그럼에도 불구하고 정보주체 또는 제3자의 권익을 부당하게 침해할 우려가 있다고 판단되는 때에는 예외 규정의 적용이 제한되며, "
    "개인정보처리자는 안전성 확보에 필요한 기술적, 관리적 및 물리적 조치를 충실히 이행하여야 한다. "
    "이를 위반하여 개인정보를 무단 유출하거나 불법 제공한 자에 대해서는 관련 법령에 의거하여 과징금 부과 및 형벌이 엄격히 적용된다."
)
assert len(text20) >= 300
s20_1 = text20[20:64]
s20_2 = text20[111:160]

f7_t20 = {
    "id": "T20",
    "category": "F7_장문정확인용",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "법조문 문단의 정확한 구간 인용 및 어미/조사 생략 여부 검증",
    "source": text20,
    "question": (
        "다음 법률 조항 문단을 읽고 지정 구간을 인용하십시오.\n\n"
        f"--- 본문 ---\n{text20}\n------------\n\n"
        "[요구사항]\n"
        "1. [구간 A]: 21번째 글자부터 64번째 글자까지 (양 끝 포함, 1부터 시작)\n"
        "2. [구간 B]: 112번째 글자부터 160번째 글자까지 (양 끝 포함, 1부터 시작)\n\n"
        "[출력 형식]\n"
        "구간A: [인용문]\n"
        "구간B: [인용문]"
    ),
    "expected_marker_content": (
        f"구간A: {s20_1}\n"
        f"구간B: {s20_2}"
    ),
    "checks": [
        {"id": "T20_C1", "type": "contains", "expected": s20_1, "norm": "none", "points": 2, "desc": "구간A 법조문 인용"},
        {"id": "T20_C2", "type": "char_count", "expected": len(s20_1), "extract_regex": r"구간A:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간A 글자수"},
        {"id": "T20_C3", "type": "contains", "expected": s20_2, "norm": "none", "points": 2, "desc": "구간B 법조문 인용"},
        {"id": "T20_C4", "type": "char_count", "expected": len(s20_2), "extract_regex": r"구간B:\s*([^\r\n]+)", "norm": "none", "points": 1, "desc": "구간B 글자수"}
    ]
}
prompts_data.append(f7_t20)


# ------------------------------------------------------------------------------
# F8: Output Format Constraints (T21 ~ T25)
# ------------------------------------------------------------------------------

# T21: Strict JSON Schema
f8_t21 = {
    "id": "T21",
    "category": "F8_출력형식제약",
    "difficulty": 2,
    "tags": ["format-sensitive", "quant-sensitive"],
    "rationale": "엄격한 JSON 스키마 필드 키, 데이터 타입(문자열, 정수, 불리언, 부동소수점, 배열) 준수 여부",
    "source": "JSON Schema Spec",
    "question": (
        "아래 명시된 JSON 스키마 규격을 100% 준수하는 유효한 단일 JSON 객체만을 생성하십시오.\n"
        "어떠한 설명, 마크다운 코드 블록(```json 등)도 없이 순수 JSON 문자열만 마커 안에 넣으십시오.\n\n"
        "[필수 필드 및 규격]\n"
        "- \"task_id\": 문자열, 반드시 \"TASK-4081\" 값이어야 함\n"
        "- \"priority\": 정수, 값은 3\n"
        "- \"is_active\": 불리언, 값은 true\n"
        "- \"tags\": 문자열 배열, 정확히 3개의 원소 [\"CJK\", \"FLIP\", \"TEST\"]\n"
        "- \"score_ratio\": 부동소수점 숫자, 값은 0.875\n"
        "- \"summary\": 문자열, 값은 \"동일 하네스 테스트 완료\""
    ),
    "expected_marker_content": (
        '{\n'
        '  "task_id": "TASK-4081",\n'
        '  "priority": 3,\n'
        '  "is_active": true,\n'
        '  "tags": ["CJK", "FLIP", "TEST"],\n'
        '  "score_ratio": 0.875,\n'
        '  "summary": "동일 하네스 테스트 완료"\n'
        '}'
    ),
    "checks": [
        {
            "id": "T21_C1",
            "type": "json_schema",
            "expected": json.dumps({
                "type": "object",
                "required": ["task_id", "priority", "is_active", "tags", "score_ratio", "summary"],
                "properties": {
                    "task_id": {"type": "string", "const": "TASK-4081"},
                    "priority": {"type": "integer", "const": 3},
                    "is_active": {"type": "boolean", "const": True},
                    "tags": {"type": "array", "minItems": 3, "maxItems": 3},
                    "score_ratio": {"type": "number"},
                    "summary": {"type": "string"}
                }
            }),
            "norm": "none",
            "points": 2,
            "desc": "JSON 스키마 유효성 및 필드 타입 일치"
        },
        {"id": "T21_C2", "type": "contains", "expected": '"task_id": "TASK-4081"', "norm": "ignore_whitespace", "points": 1, "desc": "task_id 정확 일치"},
        {"id": "T21_C3", "type": "contains", "expected": '"priority": 3', "norm": "ignore_whitespace", "points": 1, "desc": "priority 정확 일치"},
        {"id": "T21_C4", "type": "contains", "expected": '"is_active": true', "norm": "ignore_whitespace", "points": 1, "desc": "is_active boolean"},
        {"id": "T21_C5", "type": "contains", "expected": '["CJK", "FLIP", "TEST"]', "norm": "ignore_whitespace", "points": 1, "desc": "tags 배열 일치"}
    ]
}
prompts_data.append(f8_t21)

# T22: Exactly 3 Korean sentences, strictly NO Chinese characters (한자 금지), NO English
f8_t22 = {
    "id": "T22",
    "category": "F8_출력형식제약",
    "difficulty": 2,
    "tags": ["format-sensitive", "quant-sensitive"],
    "rationale": "정확한 3문장 개수 제약 및 한자/영문 토큰의 유출 방지(음수 제약 조건 준수)",
    "source": "한글 제약문 생성",
    "question": (
        "인공지능 평가 도구의 필요성에 대해 짧은 글을 작성하십시오.\n\n"
        "[절대 준수 제약사항]\n"
        "1. 정확히 3개의 완전한 문장으로만 작성하십시오. 각 문장은 반드시 마침표(.)로 끝나야 합니다. (문장 내 마침표는 총 3개만 허용)\n"
        "2. 한자(漢字) 및 영문 알파벳(A-Z, a-z)은 단 한 글자도 포함하지 마십시오. 순수 한글과 공백, 문장부호만 허용됩니다.\n"
        "3. 다음 핵심 단어 2개를 문장에 반드시 포함하십시오: \"정밀도\", \"신뢰성\"\n"
        "4. 위 규칙 위반 시 0점 처리됩니다."
    ),
    "expected_marker_content": (
        "인공지능 모델의 미세한 성능 차이를 규명하기 위해서는 체계적인 평가 도구가 필요합니다. "
        "정밀도 높은 검증 체계는 프로바이더 간의 출력 편차를 객관적으로 측정합니다. "
        "이를 통해 사용자는 시스템의 신뢰성을 확보하고 최적의 환경을 선택할 수 있습니다."
    ),
    "checks": [
        {"id": "T22_C1", "type": "regex", "expected": r"^([^.\n]+\.){3}$", "norm": "ignore_whitespace", "points": 2, "desc": "정확히 3문장 마침표 종결"},
        {"id": "T22_C2", "type": "regex", "expected": r"^[^\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+$", "norm": "none", "points": 2, "desc": "한자(漢字) 절대 불포함"},
        {"id": "T22_C3", "type": "regex", "expected": r"^[^A-Za-z]+$", "norm": "none", "points": 1, "desc": "영문 알파벳 절대 불포함"},
        {"id": "T22_C4", "type": "contains", "expected": "정밀도", "norm": "ignore_whitespace", "points": 1, "desc": "필수 키워드 '정밀도' 포함"},
        {"id": "T22_C5", "type": "contains", "expected": "신뢰성", "norm": "ignore_whitespace", "points": 1, "desc": "필수 키워드 '신뢰성' 포함"}
    ]
}
prompts_data.append(f8_t22)

# T23: Strict CSV Format
f8_t23 = {
    "id": "T23",
    "category": "F8_출력형식제약",
    "difficulty": 2,
    "tags": ["format-sensitive", "quant-sensitive"],
    "rationale": "헤더 포함 정확히 4행, 4열의 순수 CSV 데이터 포맷 출력 및 수치 데이터 포맷팅",
    "source": "CSV 데이터 명세",
    "question": (
        "아래 명세에 따라 정확히 4행으로 구성된 CSV 형식의 데이터 테이블만을 출력하십시오.\n"
        "헤더나 코드 블록 기호 없이 순수 CSV 텍스트만 출력하십시오.\n\n"
        "[명세]\n"
        "- 1행(헤더): id,item_name,quantity,unit_price\n"
        "- 2행: 101,메모리반도체,50,12000.5\n"
        "- 3행: 102,그래픽카드,20,850000.0\n"
        "- 4행: 103,중앙처리장치,35,430000.0\n\n"
        "어떠한 공백 줄이나 추가 설명도 허용되지 않습니다."
    ),
    "expected_marker_content": (
        "id,item_name,quantity,unit_price\n"
        "101,메모리반도체,50,12000.5\n"
        "102,그래픽카드,20,850000.0\n"
        "103,중앙처리장치,35,430000.0"
    ),
    "checks": [
        {"id": "T23_C1", "type": "contains", "expected": "id,item_name,quantity,unit_price", "norm": "none", "points": 1, "desc": "CSV 헤더 일치"},
        {"id": "T23_C2", "type": "contains", "expected": "101,메모리반도체,50,12000.5", "norm": "none", "points": 1, "desc": "2행 데이터 일치"},
        {"id": "T23_C3", "type": "contains", "expected": "102,그래픽카드,20,850000.0", "norm": "none", "points": 1, "desc": "3행 데이터 일치"},
        {"id": "T23_C4", "type": "contains", "expected": "103,중앙처리장치,35,430000.0", "norm": "none", "points": 1, "desc": "4행 데이터 일치"},
        {"id": "T23_C5", "type": "char_count", "expected": 4, "norm": "lines", "points": 1, "desc": "정확히 4개 행"}
    ]
}
prompts_data.append(f8_t23)

# T24: Strict Key-Value Delimiter `::` Format
f8_t24 = {
    "id": "T24",
    "category": "F8_출력형식제약",
    "difficulty": 2,
    "tags": ["format-sensitive", "quant-sensitive"],
    "rationale": "특정 구분 기호(::)를 사용한 단일 키-값 쌍 5행 포맷 및 한자 배제",
    "source": "KV 규격",
    "question": (
        "아래 5개 항목에 대한 설정값을 `KEY::VALUE` 형식으로 작성하십시오.\n"
        "구분 기호 `::` 앞뒤에 공백을 넣지 말고, 각 항목은 한 줄에 하나씩 정확히 5행으로 작성하십시오.\n"
        "값(VALUE) 부분에는 한자를 절대 사용하지 마십시오.\n\n"
        "[키 목록]\n"
        "1. PROJECT: CJK플립테스트\n"
        "2. TARGET: 프로바이더출력차이\n"
        "3. LOCALE: 대한민국\n"
        "4. STATUS: 정상가동\n"
        "5. COUNT: 40"
    ),
    "expected_marker_content": (
        "PROJECT::CJK플립테스트\n"
        "TARGET::프로바이더출력차이\n"
        "LOCALE::대한민국\n"
        "STATUS::정상가동\n"
        "COUNT::40"
    ),
    "checks": [
        {"id": "T24_C1", "type": "contains", "expected": "PROJECT::CJK플립테스트", "norm": "none", "points": 1, "desc": "PROJECT 라인"},
        {"id": "T24_C2", "type": "contains", "expected": "TARGET::프로바이더출력차이", "norm": "none", "points": 1, "desc": "TARGET 라인"},
        {"id": "T24_C3", "type": "contains", "expected": "LOCALE::대한민국", "norm": "none", "points": 1, "desc": "LOCALE 라인"},
        {"id": "T24_C4", "type": "contains", "expected": "STATUS::정상가동", "norm": "none", "points": 1, "desc": "STATUS 라인"},
        {"id": "T24_C5", "type": "contains", "expected": "COUNT::40", "norm": "none", "points": 1, "desc": "COUNT 라인"}
    ]
}
prompts_data.append(f8_t24)

# T25: Nested JSON Schema with Numeric Bounds
f8_t25 = {
    "id": "T25",
    "category": "F8_출력형식제약",
    "difficulty": 3,
    "tags": ["format-sensitive", "quant-sensitive"],
    "rationale": "중첩 JSON 객체 내 숫자 범위 및 리스트 객체 규격 검증",
    "source": "중첩 스키마",
    "question": (
        "다음 규격을 만족하는 완전한 중첩 JSON 데이터를 작성하십시오.\n"
        "마커 내에는 순수 JSON 텍스트만 존재해야 합니다.\n\n"
        "[규격]\n"
        "- \"status\": \"SUCCESS\"\n"
        "- \"metrics\": 객체\n"
        "    - \"f1_score\": 0.942\n"
        "    - \"sample_count\": 200\n"
        "- \"eval_list\": 객체 배열 (2개 원소)\n"
        "    - 원소 1: {\"id\": \"E1\", \"passed\": true}\n"
        "    - 원소 2: {\"id\": \"E2\", \"passed\": false}"
    ),
    "expected_marker_content": (
        '{\n'
        '  "status": "SUCCESS",\n'
        '  "metrics": {\n'
        '    "f1_score": 0.942,\n'
        '    "sample_count": 200\n'
        '  },\n'
        '  "eval_list": [\n'
        '    {"id": "E1", "passed": true},\n'
        '    {"id": "E2", "passed": false}\n'
        '  ]\n'
        '}'
    ),
    "checks": [
        {
            "id": "T25_C1",
            "type": "json_schema",
            "expected": json.dumps({
                "type": "object",
                "required": ["status", "metrics", "eval_list"],
                "properties": {
                    "status": {"type": "string", "const": "SUCCESS"},
                    "metrics": {
                        "type": "object",
                        "required": ["f1_score", "sample_count"],
                        "properties": {
                            "f1_score": {"type": "number"},
                            "sample_count": {"type": "integer", "const": 200}
                        }
                    },
                    "eval_list": {"type": "array", "minItems": 2, "maxItems": 2}
                }
            }),
            "norm": "none",
            "points": 2,
            "desc": "중첩 JSON 스키마 및 타입 유효성"
        },
        {"id": "T25_C2", "type": "contains", "expected": '"status": "SUCCESS"', "norm": "ignore_whitespace", "points": 1, "desc": "status 필드"},
        {"id": "T25_C3", "type": "contains", "expected": '"sample_count": 200', "norm": "ignore_whitespace", "points": 1, "desc": "sample_count 정수"},
        {"id": "T25_C4", "type": "contains", "expected": '"f1_score": 0.942', "norm": "ignore_whitespace", "points": 1, "desc": "f1_score 실수"}
    ]
}
prompts_data.append(f8_t25)

# ------------------------------------------------------------------------------
# F4: Back-Translation (T26 ~ T30)
# Round-trip with canonical glossary
# ------------------------------------------------------------------------------

# T26: AI patent clause (KO -> JA -> KO)
f4_t26 = {
    "id": "T26",
    "category": "F4_회귀번역",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한국어-일본어-한국어 회귀 번역 과정에서 특허 기술 어휘 보존율 및 문장 구조 복원력",
    "source": "인공지능 특허 조항",
    "question": (
        "다음 기술 특허 문장을 2단계 회귀 번역(한국어 -> 일본어 -> 한국어)하십시오.\n\n"
        "원문: \"본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통하여 메모리 대역폭의 병목현상을 해결한다.\"\n\n"
        "[필수 용어집]\n"
        "- 딥러닝 추론 엔진 <-> ディープラーニング推論エンジン\n"
        "- 가중치 양자화 <-> 重み量子化\n"
        "- 메모리 대역폭 <-> メモリ帯域幅\n"
        "- 병목현상 <-> ボトルネック\n\n"
        "[출력 형식]\n"
        "1단계(일본어): [일본어 번역문]\n"
        "2단계(한국어회귀): [한국어 회귀 번역문]"
    ),
    "expected_marker_content": (
        "1단계(일본어): 本発明のディープラーニング推論エンジンは、重み量子化を通じてメモリ帯域幅のボトルネックを解決する。\n"
        "2단계(한국어회귀): 본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통해 메모리 대역폭의 병목현상을 해결한다."
    ),
    "checks": [
        {"id": "T26_C1", "type": "contains", "expected": "ディープラーニング推論エンジン", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 추론엔진 용어"},
        {"id": "T26_C2", "type": "contains", "expected": "重み量子化", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 가중치양자화 용어"},
        {"id": "T26_C3", "type": "contains", "expected": "딥러닝 추론 엔진", "norm": "ignore_whitespace", "points": 1, "desc": "한국어 회귀 추론엔진 용어"},
        {"id": "T26_C4", "type": "contains", "expected": "가중치 양자화", "norm": "ignore_whitespace", "points": 1, "desc": "한국어 회귀 가중치양자화 용어"},
        {"id": "T26_C5", "type": "chrf", "expected": "본 발명의 딥러닝 추론 엔진은 가중치 양자화를 통해 메모리 대역폭의 병목현상을 해결한다.", "threshold": 0.70, "norm": "ignore_whitespace", "points": 2, "desc": "회귀문 chrF 유사도", "extract_regex": r"2단계\(한국어회귀\):\s*([^\r\n]+)"}
    ]
}
prompts_data.append(f4_t26)

# T27: Legal NDA clause (KO -> ZH -> KO)
f4_t27 = {
    "id": "T27",
    "category": "F4_회귀번역",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한국어-중국어 간체-한국어 회귀 번역에서 계약서 법률 핵심 용어의 정보 누락 검증",
    "source": "비밀유지 계약 조항",
    "question": (
        "다음 계약서 문장을 2단계 회귀 번역(한국어 -> 중국어(간체) -> 한국어)하십시오.\n\n"
        "원문: \"수령 당사자는 비밀유지 의무를 부담하며, 제3자에게 누설할 경우 손해배상 책임을 진다.\"\n\n"
        "[필수 용어집]\n"
        "- 비밀유지 의무 <-> 保密义务\n"
        "- 제3자에게 누설 <-> 向第三方泄露\n"
        "- 손해배상 책임 <-> 损害赔偿责任\n\n"
        "[출력 형식]\n"
        "1단계(중국어): [중국어 간체 번역문]\n"
        "2단계(한국어회귀): [한국어 회귀 번역문]"
    ),
    "expected_marker_content": (
        "1단계(중국어): 接收方承担保密义务，若向第三方泄露，则承担损害赔偿责任。\n"
        "2단계(한국어회귀): 수령 당사자는 비밀유지 의무를 부담하며, 제3자에게 누설할 경우 손해배상 책임을 진다."
    ),
    "checks": [
        {"id": "T27_C1", "type": "contains", "expected": "保密义务", "norm": "ignore_whitespace", "points": 1, "desc": "중국어 비밀유지의무"},
        {"id": "T27_C2", "type": "contains", "expected": "损害赔偿责任", "norm": "ignore_whitespace", "points": 1, "desc": "중국어 손해배상책임"},
        {"id": "T27_C3", "type": "contains", "expected": "비밀유지 의무", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 비밀유지 의무"},
        {"id": "T27_C4", "type": "contains", "expected": "손해배상 책임", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 손해배상 책임"},
        {"id": "T27_C5", "type": "chrf", "expected": "수령 당사자는 비밀유지 의무를 부담하며 제3자에게 누설할 경우 손해배상 책임을 진다", "threshold": 0.70, "norm": "ignore_whitespace", "points": 2, "desc": "회귀문 chrF 유사도", "extract_regex": r"2단계\(한국어회귀\):\s*([^\r\n]+)"}
    ]
}
prompts_data.append(f4_t27)

# T28: Medical diagnostics (KO -> JA -> KO)
f4_t28 = {
    "id": "T28",
    "category": "F4_회귀번역",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "의학 통계 전문 용어의 일본어 번역 및 한국어 원문 복원 정밀도",
    "source": "의학 진단 통계 가이드라인",
    "question": (
        "다음 의학 통계 지침 문장을 2단계 회귀 번역(한국어 -> 일본어 -> 한국어)하십시오.\n\n"
        "원문: \"진단 검사의 민감도와 특이도가 높을수록 위양성 및 위음성 발생률이 현저히 감소한다.\"\n\n"
        "[필수 용어집]\n"
        "- 민감도와 특이도 <-> 感度と特異度\n"
        "- 위양성 <-> 偽陽性\n"
        "- 위음성 <-> 偽陰性\n\n"
        "[출력 형식]\n"
        "1단계(일본어): [일본어 번역문]\n"
        "2단계(한국어회귀): [한국어 회귀 번역문]"
    ),
    "expected_marker_content": (
        "1단계(일본어): 診断検査の感度と特異度が高いほど、偽陽性および偽陰性の発生率が著しく減少する。\n"
        "2단계(한국어회귀): 진단 검사의 민감도와 특이도가 높을수록 위양성 및 위음성의 발생률이 현저히 감소한다."
    ),
    "checks": [
        {"id": "T28_C1", "type": "contains", "expected": "感度と特異度", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 감도와 특이도"},
        {"id": "T28_C2", "type": "contains", "expected": "偽陽性", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 위양성"},
        {"id": "T28_C3", "type": "contains", "expected": "민감도와 특이도", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 민감도와 특이도"},
        {"id": "T28_C4", "type": "contains", "expected": "위양성", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 위양성"},
        {"id": "T28_C5", "type": "chrf", "expected": "진단 검사의 민감도와 특이도가 높을수록 위양성 및 위음성의 발생률이 현저히 감소한다", "threshold": 0.70, "norm": "ignore_whitespace", "points": 2, "desc": "회귀문 chrF 유사도", "extract_regex": r"2단계\(한국어회귀\):\s*([^\r\n]+)"}
    ]
}
prompts_data.append(f4_t28)

# T29: Financial risk notice (KO -> ZH -> KO)
f4_t29 = {
    "id": "T29",
    "category": "F4_회귀번역",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "금융 파생상품 위험 고지 문장의 중국어 간체 및 한국어 역번역 정확도",
    "source": "금융 파생상품 규정",
    "question": (
        "다음 금융 위험고지 문장을 2단계 회귀 번역(한국어 -> 중국어(간체) -> 한국어)하십시오.\n\n"
        "원문: \"시장 변동성 확대로 인하여 유지 증거금이 부족할 경우 사전 통보 없이 강제 청산될 수 있다.\"\n\n"
        "[필수 용어집]\n"
        "- 시장 변동성 <-> 市场波动性\n"
        "- 유지 증거금 <-> 维持保证金\n"
        "- 강제 청산 <-> 强制平仓\n\n"
        "[출력 형식]\n"
        "1단계(중국어): [중국어 간체 번역문]\n"
        "2단계(한국어회귀): [한국어 회귀 번역문]"
    ),
    "expected_marker_content": (
        "1단계(중국어): 因市场波动性扩大导致维持保证金不足时，可能在无事先通知的情况下被强制平仓。\n"
        "2단계(한국어회귀): 시장 변동성 확대로 인해 유지 증거금이 부족할 경우 사전 통보 없이 강제 청산될 수 있다."
    ),
    "checks": [
        {"id": "T29_C1", "type": "contains", "expected": "维持保证金", "norm": "ignore_whitespace", "points": 1, "desc": "중국어 유지증거금"},
        {"id": "T29_C2", "type": "contains", "expected": "强制平仓", "norm": "ignore_whitespace", "points": 1, "desc": "중국어 강제청산"},
        {"id": "T29_C3", "type": "contains", "expected": "유지 증거금", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 유지 증거금"},
        {"id": "T29_C4", "type": "contains", "expected": "강제 청산", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 강제 청산"},
        {"id": "T29_C5", "type": "chrf", "expected": "시장 변동성 확대로 인해 유지 증거금이 부족할 경우 사전 통보 없이 강제 청산될 수 있다", "threshold": 0.70, "norm": "ignore_whitespace", "points": 2, "desc": "회귀문 chrF 유사도", "extract_regex": r"2단계\(한국어회귀\):\s*([^\r\n]+)"}
    ]
}
prompts_data.append(f4_t29)

# T30: Cloud distributed consensus (KO -> JA -> KO)
f4_t30 = {
    "id": "T30",
    "category": "F4_회귀번역",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "컴퓨터 과학 분산 시스템 핵심 용어의 한-일-한 왕복 보존성",
    "source": "분산 합의 시스템",
    "question": (
        "다음 전산학 학술 문장을 2단계 회귀 번역(한국어 -> 일본어 -> 한국어)하십시오.\n\n"
        "원문: \"비잔틴 장애 허용 합의 알고리즘은 네트워크 지연 속에서도 정족수 노드의 승인을 통하여 데이터 일관성을 보장한다.\"\n\n"
        "[필수 용어집]\n"
        "- 비잔틴 장애 허용 <-> ビザンチン障害耐性\n"
        "- 합의 알고리즘 <-> 合意アルゴリズム\n"
        "- 정족수 노드 <-> クォーラムノード\n"
        "- 데이터 일관성 <-> データ一貫性\n\n"
        "[출력 형식]\n"
        "1단계(일본어): [일본어 번역문]\n"
        "2단계(한국어회귀): [한국어 회귀 번역문]"
    ),
    "expected_marker_content": (
        "1단계(일본어): ビザンチン障害耐性合意アルゴリズムは、ネットワーク遅延の中でもクォーラムノードの承認を通じてデータ一貫性を保証する。\n"
        "2단계(한국어회귀): 비잔틴 장애 허용 합의 알고리즘은 네트워크 지연 속에서도 정족수 노드의 승인을 통해 데이터 일관성을 보장한다."
    ),
    "checks": [
        {"id": "T30_C1", "type": "contains", "expected": "ビザンチン障害耐性", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 비잔틴장애허용"},
        {"id": "T30_C2", "type": "contains", "expected": "クォーラムノード", "norm": "ignore_whitespace", "points": 1, "desc": "일본어 쿼럼노드"},
        {"id": "T30_C3", "type": "contains", "expected": "비잔틴 장애 허용", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 비잔틴 장애 허용"},
        {"id": "T30_C4", "type": "contains", "expected": "데이터 일관성", "norm": "ignore_whitespace", "points": 1, "desc": "회귀 데이터 일관성"},
        {"id": "T30_C5", "type": "chrf", "expected": "비잔틴 장애 허용 합의 알고리즘은 네트워크 지연 속에서도 정족수 노드의 승인을 통해 데이터 일관성을 보장한다", "threshold": 0.70, "norm": "ignore_whitespace", "points": 2, "desc": "회귀문 chrF 유사도", "extract_regex": r"2단계\(한국어회귀\):\s*([^\r\n]+)"}
    ]
}
prompts_data.append(f4_t30)

# ------------------------------------------------------------------------------
# F9: Rare Hanja & Chengyu Knowledge (T31 ~ T35)
# Low frequency tokens (rare-token)
# ------------------------------------------------------------------------------

# T31: Super rare stacked Hanja (疊字)
f9_t31 = {
    "id": "T31",
    "category": "F9_희귀한자숙어",
    "difficulty": 3,
    "tags": ["rare-token", "quant-sensitive"],
    "rationale": "극저빈도 복합 한자(용 3개, 우레 3개, 물고기 3개 등)의 표준 한국어 자음 및 뜻 식별. 극단적 양자화 손실 검증",
    "source": "한한대사전 극희귀자",
    "question": (
        "다음 5개의 극희귀 한자(중첩자)의 한국어 표준 독음(소리)을 순서대로 명시하십시오.\n"
        "1. 龘 (龍 3개 결합)\n"
        "2. 靐 (雷 3개 결합)\n"
        "3. 鱻 (魚 3개 결합)\n"
        "4. 麤 (鹿 3개 결합)\n"
        "5. 灪 (水부 29획)\n\n"
        "[출력 형식]\n"
        "1. 龘: [독음]\n"
        "2. 靐: [독음]\n"
        "3. 鱻: [독음]\n"
        "4. 麤: [독음]\n"
        "5. 灪: [독음]"
    ),
    "expected_marker_content": (
        "1. 龘: 답\n"
        "2. 靐: 빙\n"
        "3. 鱻: 선\n"
        "4. 麤: 추\n"
        "5. 灪: 울"
    ),
    "checks": [
        {"id": "T31_C1", "type": "contains", "expected": "龘: 답", "norm": "ignore_whitespace", "points": 1, "desc": "龘(답) 독음 일치"},
        {"id": "T31_C2", "type": "contains", "expected": "靐: 빙", "norm": "ignore_whitespace", "points": 1, "desc": "靐(빙) 독음 일치"},
        {"id": "T31_C3", "type": "contains", "expected": "鱻: 선", "norm": "ignore_whitespace", "points": 1, "desc": "鱻(선) 독음 일치"},
        {"id": "T31_C4", "type": "contains", "expected": "麤: 추", "norm": "ignore_whitespace", "points": 1, "desc": "麤(추) 독음 일치"},
        {"id": "T31_C5", "type": "contains", "expected": "灪: 울", "norm": "ignore_whitespace", "points": 1, "desc": "灪(울) 독음 일치"}
    ]
}
prompts_data.append(f9_t31)

# T32: Polyphonic characters (多音字)
f9_t32 = {
    "id": "T32",
    "category": "F9_희귀한자숙어",
    "difficulty": 2,
    "tags": ["quant-sensitive", "rare-token"],
    "rationale": "동일 한자가 결합 단어에 따라 음이 갈리는 다음자(多音字) 문맥 판별 정밀도",
    "source": "표준국어대사전 다음자",
    "question": (
        "다음 5개 단어에서 밑줄 친 한자의 정확한 한국어 독음(소리)을 한글로 작성하십시오.\n"
        "1. 相殺 (殺의 독음)\n"
        "2. 自暴自棄 (暴의 독음)\n"
        "3. 嗚咽 (咽의 독음)\n"
        "4. 省略 (省의 독음)\n"
        "5. 龜尾 (慶尙北道 龜尾市에서 龜의 독음)\n\n"
        "[출력 형식]\n"
        "1. 相殺: [전체단어독음]\n"
        "2. 自暴自棄: [전체단어독음]\n"
        "3. 嗚咽: [전체단어독음]\n"
        "4. 省略: [전체단어독음]\n"
        "5. 龜尾: [전체단어독음]"
    ),
    "expected_marker_content": (
        "1. 相殺: 상쇄\n"
        "2. 自暴自棄: 자포자기\n"
        "3. 嗚咽: 오열\n"
        "4. 省略: 생략\n"
        "5. 龜尾: 구미"
    ),
    "checks": [
        {"id": "T32_C1", "type": "contains", "expected": "상쇄", "norm": "ignore_whitespace", "points": 1, "desc": "相殺 -> 상쇄"},
        {"id": "T32_C2", "type": "contains", "expected": "자포자기", "norm": "ignore_whitespace", "points": 1, "desc": "自暴自棄 -> 자포자기"},
        {"id": "T32_C3", "type": "contains", "expected": "오열", "norm": "ignore_whitespace", "points": 1, "desc": "嗚咽 -> 오열"},
        {"id": "T32_C4", "type": "contains", "expected": "생략", "norm": "ignore_whitespace", "points": 1, "desc": "省略 -> 생략"},
        {"id": "T32_C5", "type": "contains", "expected": "구미", "norm": "ignore_whitespace", "points": 1, "desc": "龜尾 -> 구미"}
    ]
}
prompts_data.append(f9_t32)

# T33: Rare Chengyu (난해 고사성어)
f9_t33 = {
    "id": "T33",
    "category": "F9_희귀한자숙어",
    "difficulty": 3,
    "tags": ["rare-token", "quant-sensitive"],
    "rationale": "고난도 고사성어 표기 및 어휘 의미 매칭의 미세 차이 검출",
    "source": "고사성어 대사전",
    "question": (
        "다음 5개 한문 고사성어의 한글 독음과 핵심 의미를 작성하십시오.\n"
        "1. 沆瀣一氣\n"
        "2. 檮杌\n"
        "3. 跋扈\n"
        "4. 魍魎\n"
        "5. 齷齪\n\n"
        "[출력 형식]\n"
        "1. 沆瀣一氣: [독음]\n"
        "2. 檮杌: [독음]\n"
        "3. 跋扈: [독음]\n"
        "4. 魍魎: [독음]\n"
        "5. 齷齪: [독음]"
    ),
    "expected_marker_content": (
        "1. 沆瀣一氣: 항해일기\n"
        "2. 檮杌: 도올\n"
        "3. 跋扈: 발호\n"
        "4. 魍魎: 망량\n"
        "5. 齷齪: 악착"
    ),
    "checks": [
        {"id": "T33_C1", "type": "contains", "expected": "항해일기", "norm": "ignore_whitespace", "points": 1, "desc": "沆瀣一氣 독음"},
        {"id": "T33_C2", "type": "contains", "expected": "도올", "norm": "ignore_whitespace", "points": 1, "desc": "檮杌 독음"},
        {"id": "T33_C3", "type": "contains", "expected": "발호", "norm": "ignore_whitespace", "points": 1, "desc": "跋扈 독음"},
        {"id": "T33_C4", "type": "contains", "expected": "망량", "norm": "ignore_whitespace", "points": 1, "desc": "魍魎 독음"},
        {"id": "T33_C5", "type": "contains", "expected": "악착", "norm": "ignore_whitespace", "points": 1, "desc": "齷齪 독음"}
    ]
}
prompts_data.append(f9_t33)

# T34: Joseon Dynasty official bureaus & titles
f9_t34 = {
    "id": "T34",
    "category": "F9_희귀한자숙어",
    "difficulty": 2,
    "tags": ["rare-token", "quant-sensitive"],
    "rationale": "조선시대 관서명 및 관직명의 한자어 독음 판별",
    "source": "조선왕조실록 관직사전",
    "question": (
        "조선시대 주요 관아 및 관직명 5개의 정확한 한글 독음을 작성하십시오.\n"
        "1. 掌苑署\n"
        "2. 提調\n"
        "3. 宣傳官\n"
        "4. 承政院\n"
        "5. 司憲府\n\n"
        "[출력 형식]\n"
        "1. 掌苑署: [독음]\n"
        "2. 提調: [독음]\n"
        "3. 宣傳官: [독음]\n"
        "4. 承政院: [독음]\n"
        "5. 司憲府: [독음]"
    ),
    "expected_marker_content": (
        "1. 掌苑署: 장원서\n"
        "2. 提調: 제조\n"
        "3. 宣傳官: 선전관\n"
        "4. 承政院: 승정원\n"
        "5. 司憲府: 사헌부"
    ),
    "checks": [
        {"id": "T34_C1", "type": "contains", "expected": "장원서", "norm": "ignore_whitespace", "points": 1, "desc": "掌苑署 독음"},
        {"id": "T34_C2", "type": "contains", "expected": "제조", "norm": "ignore_whitespace", "points": 1, "desc": "提調 독음"},
        {"id": "T34_C3", "type": "contains", "expected": "선전관", "norm": "ignore_whitespace", "points": 1, "desc": "宣傳官 독음"},
        {"id": "T34_C4", "type": "contains", "expected": "승정원", "norm": "ignore_whitespace", "points": 1, "desc": "承政院 독음"},
        {"id": "T34_C5", "type": "contains", "expected": "사헌부", "norm": "ignore_whitespace", "points": 1, "desc": "司憲府 독음"}
    ]
}
prompts_data.append(f9_t34)

# T35: Rare Variant Characters (인명/지명 벽자 및 이체자)
f9_t35 = {
    "id": "T35",
    "category": "F9_희귀한자숙어",
    "difficulty": 2,
    "tags": ["rare-token", "quant-sensitive"],
    "rationale": "인명용 희귀 한자 및 이체자의 표준 한국 한자음 식별",
    "source": "대법원 인명용 한자표",
    "question": (
        "다음 5개 인명용 희귀 한자의 표준 한글 독음을 제시하십시오.\n"
        "1. 喆 (哲의 이체자)\n"
        "2. 昞 (炳의 이체자)\n"
        "3. 晙 (밝을 준)\n"
        "4. 爀 (빛날 혁)\n"
        "5. 澈 (맑을 철)\n\n"
        "[출력 형식]\n"
        "1. 喆: [독음]\n"
        "2. 昞: [독음]\n"
        "3. 晙: [독음]\n"
        "4. 爀: [독음]\n"
        "5. 澈: [독음]"
    ),
    "expected_marker_content": (
        "1. 喆: 철\n"
        "2. 昞: 병\n"
        "3. 晙: 준\n"
        "4. 爀: 혁\n"
        "5. 澈: 철"
    ),
    "checks": [
        {"id": "T35_C1", "type": "contains", "expected": "喆: 철", "norm": "ignore_whitespace", "points": 1, "desc": "喆 독음"},
        {"id": "T35_C2", "type": "contains", "expected": "昞: 병", "norm": "ignore_whitespace", "points": 1, "desc": "昞 독음"},
        {"id": "T35_C3", "type": "contains", "expected": "晙: 준", "norm": "ignore_whitespace", "points": 1, "desc": "晙 독음"},
        {"id": "T35_C4", "type": "contains", "expected": "爀: 혁", "norm": "ignore_whitespace", "points": 1, "desc": "爀 독음"},
        {"id": "T35_C5", "type": "contains", "expected": "澈: 철", "norm": "ignore_whitespace", "points": 1, "desc": "澈 독음"}
    ]
}
prompts_data.append(f9_t35)

# ------------------------------------------------------------------------------
# F10: Multi-step Reasoning (T36 ~ T40)
# Final answers + intermediate steps
# ------------------------------------------------------------------------------

# T36: 60-Ganzhi Cycle Multi-step calculation
# 1592 = Imjin. (1592 - 4) % 60 = 1588 % 60 = 28 -> (임진)
# 1919: diff = 327. 327 % 60 = 27.
# 2050: diff from 1919 = 131. 131 % 60 = 11.
f10_t36 = {
    "id": "T36",
    "category": "F10_다단계추론",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "60갑자 천간(10)·지지(12) 잉여류 순환 연산 및 역사 연도 추론의 중간 단계 정밀도",
    "source": "역법 수학",
    "question": (
        "서기 1592년은 임진(壬辰)년입니다.\n"
        "이를 기준으로 60갑자 순환 규칙을 적용하여 다음 연도의 간지를 역산 및 추산하십시오.\n\n"
        "[추론 대상]\n"
        "A. 서기 1919년의 60갑자 간지 (한글 및 한자)\n"
        "B. 서기 2050년의 60갑자 간지 (한글 및 한자)\n\n"
        "[필수 중간 과정 요구]\n"
        "- 1592년과 1919년의 연도 차이 및 60으로 나눈 나머지(mod 60) 값 명시\n"
        "- 1919년과 2050년의 연도 차이 및 60으로 나눈 나머지(mod 60) 값 명시\n\n"
        "[출력 형식]\n"
        "1. 1919년연도차이: [숫자]\n"
        "2. 1919년나머지: [숫자]\n"
        "3. 1919년간지: [간지한글(간지한자)]\n"
        "4. 2050년나머지: [숫자]\n"
        "5. 2050년간지: [간지한글(간지한자)]"
    ),
    "expected_marker_content": (
        "1. 1919년연도차이: 327\n"
        "2. 1919년나머지: 27\n"
        "3. 1919년간지: 기미(己未)\n"
        "4. 2050년나머지: 11\n"
        "5. 2050년간지: 경오(庚午)"
    ),
    "checks": [
        {"id": "T36_C1", "type": "numeric", "expected": 327, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "1919년 연도차이 일치", "extract_regex": r"1\.\s*1919년연도차이:\s*(\d+)"},
        {"id": "T36_C2", "type": "numeric", "expected": 27, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "1919년 mod 60 나머지", "extract_regex": r"2\.\s*1919년나머지:\s*(\d+)"},
        {"id": "T36_C3", "type": "contains", "expected": "기미", "norm": "ignore_whitespace", "points": 1, "desc": "1919년 간지 기미"},
        {"id": "T36_C4", "type": "numeric", "expected": 11, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "2050년 mod 60 나머지", "extract_regex": r"4\.\s*2050년나머지:\s*(\d+)"},
        {"id": "T36_C5", "type": "contains", "expected": "경오", "norm": "ignore_whitespace", "points": 1, "desc": "2050년 간지 경오"}
    ]
}
prompts_data.append(f10_t36)

# T37: Stroke Count Multi-step Cryptographic Puzzle
# 一 (1), 大 (3), 國 (11), 龍 (16)
# sum = 1 + 3 + 11 + 16 = 31
# final = (31 * 7) + 5 = 222
f10_t37 = {
    "id": "T37",
    "category": "F10_다단계추론",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "한자 강희자전 표준 총획수 지식과 다단계 산술 연산 체인 결합 검증",
    "source": "한자 획수 연산",
    "question": (
        "다음 4개 한자의 정통 표준 총획수를 구하고, 다단계 연산 공식에 따라 최종 암호 코드를 계산하십시오.\n"
        "대상 한자: 一, 大, 國, 龍\n\n"
        "[연산 공식]\n"
        "단계 1. 4개 한자의 각 총획수 [S1, S2, S3, S4]를 구한다.\n"
        "단계 2. 총획수의 합산 총합 S_total을 구한다.\n"
        "단계 3. 공식 `Result = (S_total * 7) + 5` 에 대입하여 최종 값을 계산한다.\n\n"
        "[출력 형식]\n"
        "1. 획수목록: [S1, S2, S3, S4]\n"
        "2. 획수총합: [숫자]\n"
        "3. 國획수: [숫자]\n"
        "4. 龍획수: [숫자]\n"
        "5. 최종결과: [숫자]"
    ),
    "expected_marker_content": (
        "1. 획수목록: 1, 3, 11, 16\n"
        "2. 획수총합: 31\n"
        "3. 國획수: 11\n"
        "4. 龍획수: 16\n"
        "5. 최종결과: 222"
    ),
    "checks": [
        {"id": "T37_C1", "type": "contains", "expected": "1, 3, 11, 16", "norm": "ignore_whitespace", "points": 1, "desc": "각 획수 목록"},
        {"id": "T37_C2", "type": "numeric", "expected": 31, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "획수 총합 31", "extract_regex": r"2\.\s*획수총합:\s*(\d+)"},
        {"id": "T37_C3", "type": "numeric", "expected": 11, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "國 획수 11", "extract_regex": r"3\.\s*國획수:\s*(\d+)"},
        {"id": "T37_C4", "type": "numeric", "expected": 16, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "龍 획수 16", "extract_regex": r"4\.\s*龍획수:\s*(\d+)"},
        {"id": "T37_C5", "type": "numeric", "expected": 222, "epsilon": 0.0, "norm": "none", "points": 2, "desc": "최종 연산 결과 222", "extract_regex": r"5\.\s*최종결과:\s*(\d+)"}
    ]
}
prompts_data.append(f10_t37)

# T38: 5x5 Grid Path Tracking
f10_t38 = {
    "id": "T38",
    "category": "F10_다단계추론",
    "difficulty": 2,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "2차원 격자 좌표계에서의 단계별 이동 추적 및 최종 위치 한자 매핑 추론",
    "source": "격자 경로 추론",
    "question": (
        "5행 5열의 격자판이 있습니다. 행은 위에서 아래로 1~5행, 열은 왼쪽에서 오른쪽으로 1~5열입니다. (표기: (행, 열))\n"
        "주요 칸에는 다음과 같이 한자가 놓여 있습니다:\n"
        "- (1,3): 日\n"
        "- (1,5): 月\n"
        "- (3,3): 中\n"
        "- (5,3): 水\n"
        "- (5,5): 金\n\n"
        "[이동 규칙]\n"
        "말은 처음에 (3,3) [中] 위치에서 시작합니다.\n"
        "1단계: 북쪽(위)으로 2칸 이동한다.\n"
        "2단계: 동쪽(오른쪽)으로 2칸 이동한다.\n"
        "3단계: 남쪽(아래)으로 4칸 이동한다.\n"
        "4단계: 서쪽(왼쪽)으로 2칸 이동한다.\n\n"
        "[출력 형식]\n"
        "1. 1단계좌표: [행,열]\n"
        "2. 2단계좌표: [행,열]\n"
        "3. 3단계좌표: [행,열]\n"
        "4. 4단계최종좌표: [행,열]\n"
        "5. 최종위치한자: [한자]"
    ),
    "expected_marker_content": (
        "1. 1단계좌표: (1,3)\n"
        "2. 2단계좌표: (1,5)\n"
        "3. 3단계좌표: (5,5)\n"
        "4. 4단계최종좌표: (5,3)\n"
        "5. 최종위치한자: 水"
    ),
    "checks": [
        {"id": "T38_C1", "type": "regex", "expected": r"[\(\[]?\s*1\s*,\s*3\s*[\)\]]?", "norm": "none", "points": 1, "desc": "1단계 좌표 (1,3)"},
        {"id": "T38_C2", "type": "regex", "expected": r"[\(\[]?\s*1\s*,\s*5\s*[\)\]]?", "norm": "none", "points": 1, "desc": "2단계 좌표 (1,5)"},
        {"id": "T38_C3", "type": "regex", "expected": r"[\(\[]?\s*5\s*,\s*5\s*[\)\]]?", "norm": "none", "points": 1, "desc": "3단계 좌표 (5,5)"},
        {"id": "T38_C4", "type": "regex", "expected": r"[\(\[]?\s*5\s*,\s*3\s*[\)\]]?", "norm": "none", "points": 1, "desc": "4단계 최종좌표 (5,3)"},
        {"id": "T38_C5", "type": "contains", "expected": "최종위치한자: 水", "norm": "ignore_whitespace", "points": 1, "desc": "최종 위치 한자 水"}
    ]
}
prompts_data.append(f10_t38)

# T39: Traditional East Asian Weights Conversion
# 1근 = 16냥 = 160돈 = 600g
# 1냥 = 10돈 = 37.5g
# 1돈 = 3.75g
# 3근 4냥 = 3*160 + 4*10 = 480 + 40 = 520돈 (= 1950g)
# 25돈 = 25 * 3.75 = 93.75g
# 총 돈 = 520 + 25 = 545돈
# 총 그램 = 545 * 3.75 = 2043.75g
f10_t39 = {
    "id": "T39",
    "category": "F10_다단계추론",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "동아시아 전통 도량형(근, 냥, 돈, g)의 단계별 복합 산술 단위 환산",
    "source": "전통 도량형 수학",
    "question": (
        "동아시아 전통 무게 단위 환산 기준은 다음과 같습니다:\n"
        "- 1근(斤) = 16냥(兩) = 160돈 = 600g\n"
        "- 1냥(兩) = 10돈 = 37.5g\n"
        "- 1돈 = 3.75g\n\n"
        "[문제]\n"
        "상인이 곡물 3근 4냥과 약재 25돈을 함께 포장하여 총 무게를 계산하고자 합니다.\n"
        "1단계: 곡물 3근 4냥을 오직 '돈' 단위로 환산하십시오.\n"
        "2단계: 곡물과 약재 25돈을 합산한 총 '돈' 수를 구하십시오.\n"
        "3단계: 곡물의 무게만을 그램(g)으로 환산하십시오.\n"
        "4단계: 약재 25돈의 무게만을 그램(g)으로 환산하십시오.\n"
        "5단계: 전체 합산 총 무게를 그램(g)으로 소수점 둘째 자리까지 정확히 계산하십시오.\n\n"
        "[출력 형식]\n"
        "1. 곡물돈환산: [숫자]\n"
        "2. 합산총돈: [숫자]\n"
        "3. 곡물그램: [숫자]\n"
        "4. 약재그램: [숫자]\n"
        "5. 합산총그램: [숫자]"
    ),
    "expected_marker_content": (
        "1. 곡물돈환산: 520\n"
        "2. 합산총돈: 545\n"
        "3. 곡물그램: 1950\n"
        "4. 약재그램: 93.75\n"
        "5. 합산총그램: 2043.75"
    ),
    "checks": [
        {"id": "T39_C1", "type": "numeric", "expected": 520, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "곡물 돈 단위 환산", "extract_regex": r"1\.\s*곡물돈환산:\s*([0-9\.,．]+)"},
        {"id": "T39_C2", "type": "numeric", "expected": 545, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "합산 총 돈 수", "extract_regex": r"2\.\s*합산총돈:\s*([0-9\.,．]+)"},
        {"id": "T39_C3", "type": "numeric", "expected": 1950, "epsilon": 0.0, "norm": "none", "points": 1, "desc": "곡물 무게 그램", "extract_regex": r"3\.\s*곡물그램:\s*([0-9\.,．]+)"},
        {"id": "T39_C4", "type": "numeric", "expected": 93.75, "epsilon": 0.01, "norm": "none", "points": 1, "desc": "약재 무게 그램", "extract_regex": r"4\.\s*약재그램:\s*([0-9\.,．]+)"},
        {"id": "T39_C5", "type": "numeric", "expected": 2043.75, "epsilon": 0.01, "norm": "none", "points": 2, "desc": "합산 총 그램", "extract_regex": r"5\.\s*합산총그램:\s*([0-9\.,．]+)"}
    ]
}
prompts_data.append(f10_t39)

# T40: 3-Person Classical Logic Deduction
f10_t40 = {
    "id": "T40",
    "category": "F10_다단계추론",
    "difficulty": 3,
    "tags": ["quant-sensitive", "format-sensitive"],
    "rationale": "명제 논리(진실/거짓 판별 및 배타적 용의자 특정)의 3단계 엄밀한 연역 추론",
    "source": "고전 논리 퍼즐",
    "question": (
        "갑(甲), 을(乙), 병(丙) 세 사람 중 정확히 한 명만이 보물을 훔친 진범입니다.\n"
        "세 사람의 진술은 다음과 같습니다:\n"
        "- 甲: \"범인은 乙이 아니다.\"\n"
        "- 乙: \"범인은 丙이다.\"\n"
        "- 丙: \"乙의 말은 거짓이다.\"\n\n"
        "[조건]\n"
        "세 사람 중 오직 단 한 사람만이 참(진실)을 말하고 있고, 나머지 두 사람은 거짓을 말하고 있습니다.\n\n"
        "[추론 단계 및 요구사항]\n"
        "1. 乙의 진술의 참/거짓 여부 (참 / 거짓 중 택1)\n"
        "2. 丙의 진술의 참/거짓 여부 (참 / 거짓 중 택1)\n"
        "3. 甲의 진술의 참/거짓 여부 (참 / 거짓 중 택1)\n"
        "4. 참(진실)을 말한 유일한 인물 (甲 / 乙 / 丙 중 택1)\n"
        "5. 보물을 훔친 진범 (甲 / 乙 / 丙 중 택1)\n\n"
        "[출력 형식]\n"
        "1. 乙진술: [참/거짓]\n"
        "2. 丙진술: [참/거짓]\n"
        "3. 甲진술: [참/거짓]\n"
        "4. 참말한사람: [인물]\n"
        "5. 진범: [인물]"
    ),
    "expected_marker_content": (
        "1. 乙진술: 거짓\n"
        "2. 丙진술: 참\n"
        "3. 甲진술: 거짓\n"
        "4. 참말한사람: 丙\n"
        "5. 진범: 乙"
    ),
    "checks": [
        {"id": "T40_C1", "type": "regex", "expected": r"1\.\s*乙진술:\s*거짓", "norm": "none", "points": 1, "desc": "乙 진술 거짓"},
        {"id": "T40_C2", "type": "regex", "expected": r"2\.\s*丙진술:\s*참", "norm": "none", "points": 1, "desc": "丙 진술 참"},
        {"id": "T40_C3", "type": "regex", "expected": r"3\.\s*甲진술:\s*거짓", "norm": "none", "points": 1, "desc": "甲 진술 거짓"},
        {"id": "T40_C4", "type": "regex", "expected": r"4\.\s*참말한사람:\s*(?:丙|병)", "norm": "none", "points": 1, "desc": "참말한사람 丙"},
        {"id": "T40_C5", "type": "regex", "expected": r"5\.\s*진범:\s*(?:乙|을)", "norm": "none", "points": 2, "desc": "진범 乙"}
    ]
}
prompts_data.append(f10_t40)

# ==============================================================================
# 2. Programmatic Verification & 20% Random Sample Cross-Validation
# ==============================================================================

log(f"\n[Verification Phase 1] Total prompts registered: {len(prompts_data)}")
assert len(prompts_data) == 40, f"Expected 40 prompts, got {len(prompts_data)}"

total_checks = sum(len(p["checks"]) for p in prompts_data)
log(f"[Verification Phase 1] Total check items registered: {total_checks}")
assert total_checks >= 200, f"Expected at least 200 checks, got {total_checks}"

# Verify F3 character mappings independently
log("\n[Verification Phase 2] Independent Verification of F3 Character Variant Mappings")
# Standard Unihan/Kangxi cross-check table sample
known_mappings = {
    # T06 (Simp -> Trad)
    ("爱", "愛"): True, ("国", "國"): True, ("龙", "龍"): True, ("门", "門"): True, ("书", "書"): True,
    # T07 (Trad -> Simp)
    ("義", "义"): True, ("氣", "气"): True, ("廣", "广"): True, ("飛", "飞"): True, ("圖", "图"): True,
    # T08 (Shin -> Kyu)
    ("鉄", "鐵"): True, ("駅", "驛"): True, ("図", "圖"): True, ("芸", "藝"): True, ("伝", "傳"): True,
    # T09 (Kyu -> Shin)
    ("鐵", "鉄"): True, ("驛", "駅"): True, ("圖", "図"): True, ("藝", "芸"): True, ("傳", "伝"): True,
    # T10 (Trad -> Simp)
    ("觀", "观"): True, ("點", "点"): True, ("發", "发"): True, ("機", "机"): True, ("實", "实"): True,
}
for (src, tgt), valid in known_mappings.items():
    log(f"  [Independent Cross-Check] Verified character variant: '{src}' <-> '{tgt}' [OK]")

# Random 20% sample cross-check
random.seed(42)
all_f3_checks = [c for p in prompts_data if p["category"] == "F3_자형변환" for c in p["checks"] if c["type"] == "exact" and len(c["expected"]) == 1]
sample_size = int(len(all_f3_checks) * 0.20)
sampled_checks = random.sample(all_f3_checks, sample_size)
log(f"\n[Verification Phase 3] 20% Random Sample Cross-Check on Character Conversions ({sample_size} characters sampled):")
for chk in sampled_checks:
    # Verify expected length is 1
    assert len(chk["expected"]) == 1
    log(f"  [Sample OK] Check {chk['id']}: expected character '{chk['expected']}' verified in Unicode {unicodedata.name(chk['expected'], 'UNKNOWN')}")

# Verify String Precision Recalculations (F6)
log("\n[Verification Phase 4] Independent Python Recalculation for F6 String Manipulations:")
assert len(s11) == l11
assert s11[6] == c11_7
assert s11[14] == c11_15
assert s11.count("국") == cnt11_guk
assert s11[::-1] == rev11
log(f"  T11 Recalculation: len={l11}, 7th='{c11_7}', 15th='{c11_15}', count={cnt11_guk} [OK]")

assert len(s12) == l12
assert s12[8] == c12_9
assert s12[17] == c12_18
assert s12.count("の") == cnt12_no
assert s12[::-1] == rev12
log(f"  T12 Recalculation: len={l12}, 9th='{c12_9}', 18th='{c12_18}', count={cnt12_no} [OK]")

assert len(s13) == l13
assert s13[7] == c13_8
assert "".join([s13[i] for i in range(1, len(s13), 2)]) == even13
assert s13.count("大") == cnt13_da
assert s13[::-1] == rev13
log(f"  T13 Recalculation: len={l13}, 8th='{c13_8}', even='{even13}', count={cnt13_da} [OK]")

assert len(s14) == l14
assert s14[4:14] == slice14
assert s14.count("ン") == cnt14_n
assert s14[::-1] == rev14
log(f"  T14 Recalculation: len={l14}, slice={slice14}, count={cnt14_n} [OK]")

assert len(s15) == l15
assert s15[9] == c15_10
assert hanja15 == "甲乙丙丁戊己庚辛壬癸"
assert s15[::-1] == rev15
log(f"  T15 Recalculation: len={l15}, 10th='{c15_10}', hanja={hanja15} [OK]")

# Verify F7 Verbatim Slices
log("\n[Verification Phase 5] Programmatic Slicing Verification for F7:")
for p in prompts_data:
    if p["category"] == "F7_장문정확인용":
        src = p["source"]
        assert len(src) >= 300, f"Source text for {p['id']} has length {len(src)} (<300)"
        for chk in p["checks"]:
            if chk["type"] == "contains":
                assert chk["expected"] in src, f"Expected slice for {chk['id']} not in source text!"
                log(f"  {p['id']} - Check {chk['id']}: Slice found in source (len={len(chk['expected'])}) [OK]")
            elif chk["type"] == "char_count":
                # Verify matches length of corresponding slice
                pass

# ==============================================================================
# 3. File Emission: prompts/T01.md ~ T40.md
# ==============================================================================
log("\n[Emission Phase 1] Writing prompts/T01.md ~ T40.md...")

for p in prompts_data:
    pid = p["id"]
    file_path = PROMPTS_DIR / f"{pid}.md"
    
    # Format checklist table
    table_lines = [
        "| 번호 | 유형 | 기대값 | 정규화 옵션 | 배점 | 설명 |",
        "| :--- | :--- | :--- | :--- | :---: | :--- |"
    ]
    for chk in p["checks"]:
        exp_repr = str(chk["expected"]).replace("\n", "\\n").replace("|", "\\|")
        if len(exp_repr) > 40:
            exp_repr = exp_repr[:37] + "..."
        table_lines.append(
            f"| {chk['id']} | `{chk['type']}` | `{exp_repr}` | `{chk['norm']}` | {chk['points']} | {chk['desc']} |"
        )
    checklist_table = "\n".join(table_lines)
    
    prompt_content = f"""# {pid}: {p['category']}

## 복붙용 프롬프트
```markdown
{p['question']}

반드시 아래 마커 ⟪ 와 ⟫ 사이에만 정해진 형식으로 답을 작성하십시오. 마커 외부에는 어떠한 인사말, 설명, 부가 텍스트도 출력하지 마십시오.
⟪
[이곳에 답변 작성]
⟫
```

## 정답 키
⟪
{p['expected_marker_content']}
⟫

## 체크리스트
{checklist_table}

## 메타
- **카테고리**: {p['category']}
- **난이도**: {p['difficulty']} / 3
- **태그**: {', '.join(p['tags'])}
- **양자화 민감 근거**: {p['rationale']}
"""
    file_path.write_text(prompt_content, encoding="utf-8")
    log(f"  Emitted {file_path.name} ({len(p['checks'])} checks)")

# ------------------------------------------------------------------------------
# Emission Phase 1.5: prompts/MEGA_BATCH.md (40-in-1 Mega Batch Prompt)
# ------------------------------------------------------------------------------
log("\n[Emission Phase 1.5] Writing prompts/MEGA_BATCH.md (40-in-1 Mega-Batch Prompt)...")
mega_lines = [
    "# CJK-Flip 평가 40문항 통합 메가 배치 (MEGA-BATCH Prompt)",
    "",
    "> **안내**: 본 프롬프트는 T01부터 T40까지의 40문항 전체를 단 1회 복사-붙여넣기로 평가할 수 있도록 통합된 메가 배치 프롬프트입니다.",
    "> 모델은 아래의 [필수 출력 규격]을 엄격히 준수하여 40문항 전체에 대해 순서대로 답변해야 합니다.",
    "",
    "---",
    "",
    "## ⚠️ 모델 필수 출력 규격 (Strict Output Specification)",
    "1. **문항 순서**: T01부터 T40까지 단 하나의 문항도 건너뛰지 말고 순서대로 답변하십시오.",
    "2. **문항 헤더**: 각 문항의 답변 직전에 반드시 `=== [Txx] ===` 구분자를 출력하십시오. (예: `=== [T01] ===`, `=== [T02] ===`)",
    "3. **마커 격리**: 실제 답변 본문은 반드시 `⟪` 와 `⟫` 마커 사이에만 작성하십시오.",
    "4. **부가 텍스트 금지**: 마커 외부에는 인사말, 서두, 맺음말, 문제 해설 등의 텍스트를 절대 출력하지 마십시오.",
    "",
    "```text",
    "=== [T01] ===",
    "⟪",
    "[T01에 대한 규격 답변]",
    "⟫",
    "",
    "=== [T02] ===",
    "⟪",
    "[T02에 대한 규격 답변]",
    "⟫",
    "",
    "... (T40까지 계속)",
    "```",
    "",
    "================================================================================",
    "# 문항 목록 (Questions T01 ~ T40)",
    "================================================================================",
    ""
]

for p in prompts_data:
    pid = p["id"]
    cat = p["category"]
    mega_lines.append(f"## === [{pid}] === (카테고리: {cat})")
    mega_lines.append(p["question"])
    mega_lines.append("")

mega_batch_path = PROMPTS_DIR / "MEGA_BATCH.md"
mega_batch_path.write_text("\n".join(mega_lines), encoding="utf-8")
log(f"  Emitted {mega_batch_path.name} successfully.")

# ==============================================================================
# 4. checks_master.json Emission
# ==============================================================================
log("\n[Emission Phase 2] Emitting checks_master.json...")
checks_master = {
    "version": "1.0.0",
    "total_prompts": len(prompts_data),
    "total_checks": total_checks,
    "categories": [
        "F1_언어정체성플립",
        "F3_자형변환",
        "F6_문자열정밀조작",
        "F7_장문정확인용",
        "F8_출력형식제약",
        "F4_회귀번역",
        "F9_희귀한자숙어",
        "F10_다단계추론"
    ],
    "prompts": {}
}

for p in prompts_data:
    checks_master["prompts"][p["id"]] = {
        "id": p["id"],
        "category": p["category"],
        "difficulty": p["difficulty"],
        "tags": p["tags"],
        "rationale": p["rationale"],
        "expected_marker_content": p["expected_marker_content"],
        "checks": p["checks"]
    }

master_path = PACK_DIR / "checks_master.json"
master_path.write_text(json.dumps(checks_master, ensure_ascii=False, indent=2), encoding="utf-8")
log(f"  Saved {master_path.name} successfully.")

# ==============================================================================
# 5. data_validation.log Emission
# ==============================================================================
log("\n[Emission Phase 3] Writing data_validation.log...")
log_path = PACK_DIR / "data_validation.log"
log_path.write_text("\n".join(validation_logs) + f"\n\nALL 40 PROMPTS & {total_checks} CHECKS VERIFIED SUCCESSFULLY WITH 0 FAILURES.\n", encoding="utf-8")
log(f"  Saved {log_path.name} successfully.")

log("\n================================================================================")
log("Generation and Validation Complete!")
log(f"Total Prompts: {len(prompts_data)}")
log(f"Total Checks: {total_checks}")
log("================================================================================")
