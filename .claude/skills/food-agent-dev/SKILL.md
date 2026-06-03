---
name: food-agent-dev
description: >
  food-agent 프로젝트(Streamlit + Groq Vision 기반 음식 레시피 생성기)의 기능 추가, 수정, 개선, 디버깅,
  코드 리뷰 요청 시 에이전트 팀을 조율하여 개발을 실행하는 오케스트레이터 스킬.
  "레시피 기능 추가", "Groq 프롬프트 수정", "UI 개선", "쇼핑 API 연동", "재료 추출 로직 수정",
  "source.md 기능", "Streamlit 컴포넌트", "에러 핸들링 강화", "다시 실행", "재실행", "이전 결과 개선"
  등 food-agent 개발 관련 모든 요청에 이 스킬을 반드시 사용하라.
---

# food-agent 개발 오케스트레이터

## 프로젝트 컨텍스트

- **앱**: `src/main.py` — Streamlit + Groq Llama 4 Scout 음식 레시피 생성기
- **모델**: `meta-llama/llama-4-scout-17b-16e-instruct` (Groq Vision)
- **핵심 흐름**: 이미지 업로드 → Groq Vision 분석 → JSON 파싱 → Streamlit 표시
- **주요 JSON 필드**: `is_food`, `dish_guess`, `recipe`, `ingredient_extraction`, `md_export`, `warnings`
- **설정**: `.env`의 `GROQ_API_KEY`, 프로젝트 루트의 `source.md`
- **에이전트**: `pipeline-developer` (AI 파이프라인), `ui-developer` (Streamlit UI), `qa-reviewer` (QA)

## 실행 모드: 하이브리드

- **Phase 1 (분석)**: 서브에이전트 (Plan) — 요구사항 분석 및 작업 분해
- **Phase 2 (개발)**: 에이전트 팀 — pipeline-developer + ui-developer 병렬 협업
- **Phase 3 (QA)**: 서브에이전트 (qa-reviewer) — 통합 검증

---

## Phase 0: 컨텍스트 확인

시작 전 기존 작업 상태를 확인하여 실행 모드를 결정한다:

1. `_workspace/` 디렉토리 존재 여부 확인
2. 분기 결정:
   - `_workspace/` 없음 → **초기 실행** (모든 Phase 실행)
   - `_workspace/` 있고 사용자가 부분 수정 요청 → **부분 재실행** (해당 에이전트만 재호출)
   - `_workspace/` 있고 새 요청 → **새 실행** (`_workspace/`를 `_workspace_prev/`로 이동 후 진행)

## Phase 1: 요구사항 분석

**실행 모드: 서브에이전트 (Plan)**

Plan 에이전트를 호출하여 사용자 요청을 분석한다:

```
사용자 요청을 분석하여 _workspace/01_requirements.md에 다음을 작성하라:

1. 요청 요약 (한 줄)
2. 영향 범위:
   - [ ] 파이프라인 변경 (Groq API, 프롬프트, JSON 스키마, 재료 추출)
   - [ ] UI 변경 (Streamlit 컴포넌트, 레이아웃, UX)
   - [ ] 양쪽 모두
3. 수정 대상 파일 목록 (src/main.py의 어느 섹션인지 명시)
4. 에이전트 할당:
   - pipeline-developer 작업: [목록]
   - ui-developer 작업: [목록]
5. 스키마 변경 여부 (pipeline → ui 협의 필요 여부)
6. 주의사항 및 리스크
```

분석 결과에 따라 Phase 2 팀 구성을 조정한다:
- 파이프라인만 변경: pipeline-developer만 호출 (ui-developer 생략 가능)
- UI만 변경: ui-developer만 호출 (pipeline-developer 생략 가능)
- 양쪽 모두: 팀 구성

## Phase 2: 개발

**실행 모드: 에이전트 팀**

`_workspace/01_requirements.md`를 기반으로 팀을 구성한다:

```
TeamCreate("food-dev-team", ["pipeline-developer", "ui-developer"])

TaskCreate 할당:
- pipeline-developer → 파이프라인 변경 작업
- ui-developer → UI 변경 작업 (스키마 변경 시 pipeline-developer 완료 후 진행)
```

**팀 조율 규칙:**
- 스키마 변경이 있으면 pipeline-developer가 먼저 `_workspace/02_pipeline_changes.md`를 작성하고, ui-developer에게 SendMessage로 통보한다.
- 스키마 변경이 없으면 두 에이전트가 병렬로 진행한다.
- 각 에이전트는 완료 후 오케스트레이터에게 SendMessage로 보고한다.

**이전 산출물 재사용:**
- 부분 재실행 시 해당 에이전트의 `_workspace/0{n}_*.md`만 덮어쓰고 나머지는 보존한다.

## Phase 3: QA

**실행 모드: 서브에이전트 (qa-reviewer)**

```
qa-reviewer를 호출:
- _workspace/02_pipeline_changes.md (있을 경우) 읽기
- _workspace/03_ui_changes.md (있을 경우) 읽기
- src/main.py 검토
- _workspace/04_qa_report.md에 결과 작성
```

QA 결과에 따라:
- 이슈 없음 → Phase 4로 진행
- 경미한 이슈 → 사용자에게 보고 후 선택적 수정
- 치명적 이슈 → 해당 에이전트 재호출하여 수정

## Phase 4: 완료 보고

사용자에게 다음을 보고한다:
1. 변경된 파일 및 핵심 변경 내용 요약
2. 새로 추가된 기능 설명
3. 앱 실행 방법: `streamlit run src/main.py`
4. QA 발견 이슈 (있을 경우)
5. 피드백 요청: "개선할 부분이 있나요?"

---

## 에러 핸들링

| 상황 | 처리 |
|------|------|
| 에이전트 1회 실패 | 다시 호출, 입력 명세 보완 |
| 2회 실패 | 해당 작업 없이 진행, 보고서에 누락 명시 |
| 스키마 불일치 발견 | qa-reviewer 즉시 에스컬레이션, pipeline·ui 양측 수정 |
| 요구사항 불명확 | Phase 1 전에 사용자에게 1~2가지 질문으로 명확화 |

---

## 데이터 흐름

```
사용자 요청
  └─ Phase 1 → _workspace/01_requirements.md
       └─ Phase 2
            ├─ pipeline-developer → src/main.py (파이프라인)
            │                    → _workspace/02_pipeline_changes.md
            └─ ui-developer      → src/main.py (UI)
                                 → _workspace/03_ui_changes.md
       └─ Phase 3 → _workspace/04_qa_report.md
  └─ Phase 4: 완료 보고
```

---

## 테스트 시나리오

### 정상 흐름
1. 요청: "레시피 JSON에 칼로리 정보 필드 추가해줘"
2. Phase 1: 파이프라인 변경 확인 (프롬프트 + 스키마 수정)
3. Phase 2: pipeline-developer가 프롬프트와 JSON 스키마 수정 → ui-developer에게 스키마 변경 통보 → ui-developer가 UI에 칼로리 표시 추가
4. Phase 3: qa-reviewer가 필드명 일치 확인
5. 완료 보고

### 에러 흐름
1. 요청: "음식 분석 결과를 CSV로 저장하는 기능 추가"
2. Phase 1: UI + 파이프라인 양측 변경 확인
3. Phase 2: pipeline-developer가 md_export 스키마에 CSV 형식 추가, ui-developer가 다운로드 버튼 구현
4. Phase 3: qa-reviewer가 `st.download_button` 사용 여부, 파일명 중복 등 확인
5. 이슈 발견 시 → 해당 에이전트 재호출

---

## 후속 작업 처리

이전 `_workspace/`가 존재하면 사용자에게 확인한다:
- "이전 개발 결과가 있습니다. 이어서 수정할까요, 새로 시작할까요?"
- 이어서 수정: 변경이 필요한 에이전트만 재호출
- 새로 시작: `_workspace/`를 `_workspace_prev/`로 이동 후 전체 실행
