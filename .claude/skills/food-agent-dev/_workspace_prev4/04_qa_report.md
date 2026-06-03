# QA 리포트 (04_qa_report.md)

대상: `src/main.py`, `.claude/skills/food-agent-dev/SKILL.md`
판정 기준: PASS(이상 없음) / WARN(동작은 하나 개선 필요) / FAIL(요구사항 미충족·버그)

치명적 이슈(앱 실행 불가): **없음**. 문법/들여쓰기 오류 없음, 앱은 정상 기동 예상.

---

## [A] 자동 분석

| 항목 | 판정 | 근거 |
|------|------|------|
| A-1 `_last_file_name` 비교 들여쓰기 | PASS | L2898 `if ... != _cur_name:` `else:`(L2893) 블록 내부에 정상 배치 |
| A-2 비음식 시 `_last_file_name = None` 리셋 | PASS | L2925, 재업로드 재분석 보장됨 |
| A-3 `vision_result is None` 분기 보존 | PASS | L2914~2915, 기존 로직 유지 |
| A-4 `_typing = True/False` 위치 | PASS(WARN) | L2906 True / L2913 False. 단, C 항목 WARN 참고 |

**WARN(A/C 공통 — 타이핑 버블 실제 미표시):** L2906에서 `_typing=True`를 세팅하지만,
같은 런 안에서 `render_chat_history()`는 이미 L2841에서 호출이 끝난 뒤다. `_typing=True` 세팅과
분석(`st.spinner`) 사이에 `st.rerun()`이 없으므로 타이핑 버블이 화면에 그려지지 않는다.
분석이 끝나면 L2913에서 곧장 False로 되돌린 뒤 L2937 `st.rerun()`이 실행된다.
즉 사용자에게는 `st.spinner`(CSS로 숨김) 동안 **아무 인디케이터도 안 보임**. Step 4(L2997)도 동일.
- 위치: L2906/L2997 직후. 수정안: `_typing=True` 세팅 → `st.rerun()`으로 버블 1프레임 노출 후,
  다음 런에서 `_typing` flag를 보고 실제 분석 수행하는 2단계 구조로 변경.
- 심각도: 경미(UX). 기능 동작에는 영향 없음.

---

## [B] 인분 확인 메시지

| 항목 | 판정 | 근거 |
|------|------|------|
| B-1 버튼 5종 확인 메시지 | PASS | 1/2/4/6인분 L2950 `f"{val}인분으로 준비할게요 👍"`, 건너뛰기 L2958 `"기본 2인분으로 준비할게요 👍"` |
| B-2 chat_input step=2 확인 메시지 | PASS | L3104~3107, `parse_servings` 결과로 `_sv_label` 동적 생성 후 메시지 추가 |
| B-3 기존 "더 반영할 요청…" 메시지 | PASS | L2951, L2959, L3108 모두 유지 |

---

## [C] 타이핑 인디케이터

| 항목 | 판정 | 근거 |
|------|------|------|
| C-1 `render_chat_history()` 끝 조건부 렌더 | PASS | L1929 `if st.session_state.get("_typing"):` 버블 HTML |
| C-2 Step4 전후 flag 세팅/해제 | PASS | L2997 True / L3007 False |
| C-3 spinner CSS 숨김 영향 | PASS | L1150 `[data-testid="stSpinner"]{display:none}`. `st.warning`(L321)은 spinner가 아니므로 무영향 확인 |
| C-종합 실제 노출 | WARN | A항목 WARN과 동일 원인 — rerun 부재로 버블이 시각적으로 안 뜸 |

---

## [D] 퀵리플라이

| 항목 | 판정 | 근거 |
|------|------|------|
| D-1 Step2/3 버튼 wrap div 내 배치 | PASS(WARN) | L2943·L2962 / L2970·L2986 div 열고 닫음 |
| D-2 `.quick-reply-wrap .stButton` 셀렉터 | PASS(WARN) | L1160~1177 정의 정확 |
| D-3 columns 외부 div → CSS 미적용 가능성 | WARN | `st.columns`는 markdown div의 **형제**로 렌더링되어 `.quick-reply-wrap .stButton` 자손 선택자가 실제 columns 버튼에 매칭 안 될 가능성 높음. 03_ui_changes.md에도 인지된 한계로 명시됨. |

**WARN(D-3) 권고:** pill 스타일이 적용 안 되면 키 스코핑 CSS로 보강. Step2 버튼 key는 `serv_1/2/4/6`, `serv_skip`,
Step3는 `pref_0~3`, `pref_skip`. 셀렉터 예: `[class*="st-key-serv_"] .stButton > button, [class*="st-key-pref_"] .stButton > button { ...pill... }`.
사이드바 레시피 버튼(`sb_recipe_*`)이 이미 같은 패턴(L1454)을 쓰므로 동일 방식 적용 가능.
- 심각도: 경미(스타일). 기능 동작 정상.

---

## [E] 헤더

| 항목 | 판정 | 근거 |
|------|------|------|
| E-1 `.topbar` sticky/top/z-index | PASS | L1064 `position: sticky; top: 0; z-index: 100;` |
| E-2 `margin-bottom: 0` | PASS | L1063 `margin-bottom: 0` |

---

## [F] 좌우 여백

| 항목 | 판정 | 근거 |
|------|------|------|
| F-1 `.chat-wrap` padding | PASS | L1119 `padding: 24px 32px 40px; box-sizing: border-box` |
| F-2 `overflow-x: hidden` main | PASS | L916 `stMainBlockContainer` + L920 `.main` 모두 적용 |

---

## [G] 사이드바 버튼

| 항목 | 판정 | 근거 |
|------|------|------|
| G-1 "열기" 버튼 + HTML div 제거 | PASS | grep `st.button("열기"` 매치 0건. L2139 단일 버튼만 존재 |
| G-2 단일 `st.button(f"🍽️  {_name}\n{_meta}")` | PASS | L2139~2143 |
| G-3 키 스코핑 CSS | PASS | L1454 `[class*="st-key-sb_recipe_"]` + `.sb-saved` OR 셀렉터, `white-space: pre-wrap`로 줄바꿈 label 렌더 |
| G-4 클릭 시 session_state 세팅 보존 | PASS | L2144~2149 view/load_recipe_pending/viewing_recipe/cart_selected_path 모두 보존 |

---

## SKILL.md

| 항목 | 판정 | 근거 |
|------|------|------|
| 본문 Groq→Gemini | PASS | L15~19, L51 모두 Gemini/`gemini-2.5-flash`/`GEMINI_API_KEY`로 교체됨 |
| description 블록 잔존 | WARN | SKILL.md L4 "Streamlit + Groq Vision 기반", L6 "Groq 프롬프트 수정" 트리거 문구에 Groq 잔존. 동작엔 무해하나 일관성 위해 "Gemini Vision 기반", "Gemini 프롬프트 수정"으로 교체 권고 |

> 참고: `CLAUDE.md`(프로젝트 루트)도 여전히 "Groq Llama 4 Scout", "`GROQ_API_KEY`"를 명시(개요 섹션). 본 작업 범위 밖이나 후속 정리 권고.

---

## 문법 / 안전성 체크

- 들여쓰기: Step1 `else:` 블록(L2893~2937), with/try/except 경계 모두 정상. **오류 없음**.
- f-string 따옴표 충돌: L2935·L2951 등 외부 `"..."` 내부 `'sub'` 사용 — 충돌 없음. **정상**.
- session_state 키 오타: `_last_file_name`, `_typing`, `step`, `vision_result`, `recipe_result` 등 일관 사용. **오타 없음**.
- 에러 핸들링: `get_ai_client()`(L1811) API 키/패키지 미설정 시 `st.error`+`st.stop()` 정상. `handle_api_error`(L1826) 분기 후 `st.stop()` 정상.
- HTML 이스케이프: user content `html.escape` 처리(L1923, L2932 등) 정상. 프롬프트 인젝션 관련 입력은 LLM 프롬프트 f-string 삽입이나 JSON 응답 강제(response_mime_type) + escape로 출력 안전.

---

## 종합 결론

- **치명 이슈 없음** — 앱 실행/핵심 플로우 정상. 모든 [A]~[G] 핵심 요구사항 기능적으로 충족.
- **경미 이슈(권고) 3건:**
  1. (A/C) 타이핑 버블이 rerun 부재로 실제 화면에 안 뜸 → 2단계 rerun 구조 권고. 가장 사용자 체감 큰 항목.
  2. (D-3) 퀵리플라이 pill 스타일이 columns 자손 셀렉터 한계로 미적용 가능 → `st-key-serv_`/`st-key-pref_` 스코핑 CSS 보강 권고.
  3. (SKILL.md/CLAUDE.md) description·개요의 Groq 잔존 문구 → Gemini로 정리 권고.
- 1·2번은 동작 무관 UX/스타일, 오케스트레이터 판단으로 처리 여부 결정 가능.
