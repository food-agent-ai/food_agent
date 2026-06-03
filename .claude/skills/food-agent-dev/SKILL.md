---
name: food-agent-dev
description: >
  food-agent 프로젝트(Streamlit + Gemini Vision 기반 음식 레시피 생성기)의 기능 추가, 수정, 개선, 디버깅,
  코드 리뷰 요청 시 에이전트 팀을 조율하여 개발을 실행하는 오케스트레이터 스킬.
  "레시피 기능 추가", "Gemini 프롬프트 수정", "UI 개선", "쇼핑 API 연동", "재료 추출 로직 수정",
  "source.md 기능", "Streamlit 컴포넌트", "에러 핸들링 강화", "다시 실행", "재실행", "이전 결과 개선"
  등 food-agent 개발 관련 모든 요청에 이 스킬을 반드시 사용하라.
---

# food-agent 개발 오케스트레이터

## 프로젝트 컨텍스트

- **앱**: `src/main.py` — Streamlit + Gemini 2.5 Flash 음식 레시피 생성기
- **모델**: `gemini-2.5-flash` (Gemini Vision)
- **핵심 흐름**: 이미지 업로드 → Gemini Vision 분석 → JSON 파싱 → Streamlit 표시
- **주요 JSON 필드**: `is_food`, `dish_guess`, `recipe`, `ingredient_extraction`, `md_export`, `warnings`
- **설정**: `.env`의 `GEMINI_API_KEY`, 프로젝트 루트의 `source.md`
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

## Phase 0.5: UI 변경 시 사전 검사 (필수)

**UI/CSS/레이아웃 변경이 포함된 경우 반드시 수행.** 추측으로 CSS를 작성하지 말 것.

### 목적
기존 DOM 구조와 실제 적용된 CSS를 먼저 파악해 정확한 셀렉터와 원인을 찾는다.

### 절차
1. **앱 실행 확인** — `http://localhost:8501` 에 앱이 뜨는지 확인 (안 뜨면 실행 후 진행)
2. **Chrome DevTools JS로 실제 구조 파악**:
   ```js
   // 수정할 요소의 computed styles
   const el = document.querySelector('YOUR_SELECTOR');
   const s = window.getComputedStyle(el);
   ({padding: s.padding, margin: s.margin, display: s.display})

   // 실제 DOM 위치 확인
   el.getBoundingClientRect()

   // 부모 체인 확인
   let p = el; let chain = [];
   while(p && chain.length < 5) { chain.push(p.tagName + '.' + p.className.slice(0,40)); p = p.parentElement; }
   chain
   ```
3. **원인 확인 후 CSS 작성** — 실제 셀렉터와 computed value를 기반으로 fix 작성

### Streamlit CSS 작업 규칙
- `st.markdown('<div class="X">')` 로 만든 div는 **자식 Streamlit 컴포넌트를 감싸지 못함** — 빈 div로 남음. padding/layout이 필요하면 Streamlit의 실제 컨테이너(`[data-testid="stVerticalBlock"]`, `[data-testid="stMainBlockContainer"]` 등)에 적용
- CSS 셀렉터 작성 전 JS로 실제 class/testid 확인 필수
- `!important` 남발 금지 — computed style이 이미 0이면 `!important`로 덮어도 동일

### ui-developer에게 지시 시 포함할 내용
- 수정 전 Chrome DevTools로 확인한 실제 computed styles 스냅샷
- 정확한 CSS 셀렉터 (추측 금지)
- 기대하는 computed value 변경 내용

### Visual Verification (필수)

**computed styles만으로는 완전하지 않음** — 레이아웃 적절성, 여백 균형, 시각적 일관성은 사람의 눈으로만 검증 가능.

**검증 프로세스:**
1. **Computed style 확인** (DevTools JS)
   - 수치적 정확성 검증 (gap, padding, margin, width 등)
   - 예: `gap: 0px`, `padding: 0px 24px`, `top: 0px`
2. **Screenshot 캡처** (verifier-streamlit)
   - 앱 실행 후 해당 뷰 스크린샷
   - 여러 뷰포트 크기 테스트 (mobile/tablet/desktop)
3. **Visual 검수** (육안)
   - 좌우 여백이 동일한가?
   - 칩의 간격과 정렬이 의도한 대로인가?
   - 레이아웃이 디자인과 일치하는가?

**QA에서 image 기반 검증이 필수인 이유:**
- computed style `gap: 0px` ≠ visual adequacy (실제로 topbar 위치가 맞는지 확인)
- CSS 규칙이 존재 ≠ CSS가 제대로 선택되었는지 (selector mismatch)
- Streamlit의 동적 클래스 생성으로 인해 스타일 충돌 가능성 높음

---

## Phase 1: 요구사항 분석

**실행 모드: 서브에이전트 (Plan)**

Plan 에이전트를 호출하여 사용자 요청을 분석한다:

```
사용자 요청을 분석하여 _workspace/01_requirements.md에 다음을 작성하라:

1. 요청 요약 (한 줄)
2. 영향 범위:
   - [ ] 파이프라인 변경 (Gemini API, 프롬프트, JSON 스키마, 재료 추출)
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
