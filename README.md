# Zoo Code Custom Mode용 CJK-Flip 테스트 팩 — 동일 주입 · 자동 판정 키트

본 리포지토리는 Zoo Code Custom Mode 환경에서 프로바이더/양자화(FP4 vs FP8 등) 간 출력 품질의 미세 차이를 298개 check 단위로 정밀 판정하는 무의존성(Zero-External-Dependency) 자동 평가 키트입니다.

> **측정 대상 명명**: 본 결과는 '모델 품질'이 아니라 **'동일 하네스 조건에서의 프로바이더 간 출력 차이'**를 나타냅니다.

---

## ⚡ 윈도우 탐색기 더블클릭 빠른 실행 (One-Click Runner)

터미널이나 명령어를 직접 입력할 필요 없이, 윈도우 탐색기에서 더블클릭만으로 채점과 시각적 대시보드를 즉시 확인할 수 있습니다:

1. **`run_score.bat` 더블클릭**:
   - 시스템의 Python 환경(`py` 또는 `python`)을 자동 감지하여 단일 회차 채점을 즉시 수행합니다.
   - 채점 완료 즉시 **인라인 SVG 그래프가 포함된 시각적 대시보드(`report.html`)가 웹 브라우저에 자동 팝업**됩니다.
   - 결과를 여유 있게 확인할 수 있도록 터미널 창이 꺼지지 않고 대기합니다 (`pause`).
2. **`run_score_runs.bat` 더블클릭**:
   - 다회차 반복 분석(`--runs`)을 수행하여 회차 평균 정확도 및 회차 간 불일치율(Disagreement Rate)을 시각화합니다.

*(프로젝트 루트 및 `flip-test-pack/` 폴더 양쪽 모두에서 동일하게 더블클릭 실행을 지원합니다)*

---

## 🚀 1회 복붙용 '메가 배치(Mega-Batch)' 워크플로우

40회 반복 복사-붙여넣기 피로도를 완전히 해소하기 위해 1회 주입 규격을 지원합니다:

1. `flip-test-pack/prompts/MEGA_BATCH.md` 내용을 복사하여 Zoo Code 입력창에 1회 붙여넣습니다.
2. 모델이 출력한 40개 문항 응답 전문을 `flip-test-pack/responses/{provider}/MEGA.md` 단 1개 파일로 저장합니다.
3. `run_score.bat`를 더블클릭하면 채점기가 자동으로 메가 배치 규격을 감지하여 채점하고, 토큰 절단(Truncation) 발생 시 권장 조치 경고를 출력합니다.

---

## 📊 시각적 그래프 대시보드 (`report.html`)

외부 무거운 라이브러리(matplotlib, npm 등) 의존성 전혀 없이, Python 표준 라이브러리만으로 반응형 HTML5 + 인라인 SVG 대시보드를 생성합니다:
- **프로바이더별 종합 정확도 카드**: 점수, 통과율, 상태 뱃지, 회차 분산
- **카테고리 8종 비교 막대 그래프**: F1~F10 영역별 정확도 (%) 인라인 SVG 차트
- **프로바이더 간 편차(%p) 차트**: 양자화 손실/우위를 한눈에 파악하는 수평 발산 차트
- **실패 항목 상세 아코디언**: 오답 체크의 기대값/실제값/원인 1:1 대조
- **토큰 절단(Truncation) 진단 경고 뱃지**: `max_tokens` 부족으로 인한 누락 감지 및 가이드
- **다크/라이트 모드 지원**: 원클릭 테마 전환 및 한국어 최적화 UI

---

## 💻 CLI 수동 실행 (Command Line)

```bash
# flip-test-pack 디렉토리로 이동
cd flip-test-pack

# 채점기 자체 검증 유닛 테스트 (41개 전수 통과)
python tests/test_scorer.py

# 단일 회차 채점 및 대시보드 생성
python score_results.py

# 다회차 채점 및 회차 평균·불일치율 분석
python score_results.py --runs
```

상세한 준비·실행·판정 절차, 통제 체크리스트, 통계적 한계, 가정은 [flip-test-pack/README.md](flip-test-pack/README.md)를 참조하십시오.
