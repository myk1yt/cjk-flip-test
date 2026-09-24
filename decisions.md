# decisions.md — CJK-Flip 작업 결정 로그

Append-only. 과거 항목을 덮어쓰지 않는다.

## 2026-09-25 02:15 — 채점 공정성 수정 세션 시작
- **결정**: 3개 독립 감사보고서(docs/260924_0001_session_scorer-fairness-audit/)의 교차 확인된 결함을 수정한다. 수정 전 상태를 `docs/260925_0001_scorer-fairness-fix/before_snapshot/`에 박제(감사 추적성 확보, ask 감사 권고 5번 반영).
- **전제**: 프롬프트(prompts/)는 절대 변경 금지(사용자 지시). 수정 대상은 checks_master.json(정답키), score_results.py(엔진), 테스트, .bat뿐.

## 2026-09-25 02:20 — 배점 구조(F3 집중, C26 이중 계상)는 유지
- **결정**: F3 자형변환 33.2% 가중 집중, T06/08/10 C26 완벽 본너스 2점 구조는 전 프로바이더에 대칭 적용되므로 순위 왜곡이 없어 배점 변경 없이 유지. 절대 점수 해석 시 참고용으로 보고서에 한계로 명시.

## 2026-09-25 02:22 — T05_C2(愛人)에 "연인" 허용
- **결정**: "배우자"를 우선 정답으로 유지하되 문맥상 방어 가능한 "연인"을 병용 허용. 일본어 오번역(정부/불륜상대) 함정은 여전히 걸러지므로 플립 탐지 목적 무손실. 조걸부 억울함(ask 감사 F-6) 판정 반영.

## 2026-09-25 02:50 — 런타임 산출물(report.html, results_summary.md) Git 추적 제외
- **결정**: 이전 커밋(95f433e)의 .gitignore 의도("exclude runtime generated report mirrors")에 따라 flip-test-pack/ 안의 생성물도 추적에서 제외(git rm --cached). 이유: .bat 실행마다 working tree가 더러워지는 것을 방지. failures.csv는 이미 미추적.

## 2026-09-25 02:55 — 커밋 분리 및 푸시
- **결정**: 커밋 2개로 분리(①fix: 채점 공정성 수정 ②feat: 대시보드 차트+.bat 정규화). 사용자가 "푸시까지 해줘"라고 명시 지시했으므로 origin/main 푸시 승인 처리.
