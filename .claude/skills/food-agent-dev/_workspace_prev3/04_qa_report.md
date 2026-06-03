# 04_qa_report — QA 검증 결과

검증일: 2026-06-01
대상: `src/main.py` (3073줄) · 브랜치 `APIprompt`
입력: `02_pipeline_changes.md`, `03_ui_changes.md`, `01_requirements.md`

---

## 파이프라인 체크리스트

| # | 항목 | 판정 | 근거 |
|---|------|------|------|
| P1 | `from groq import Groq` 없음 | PASS | grep 매치 0건 |
| P2 | GROQ_VISION_MODEL/GROQ_TEXT_MODEL 상수 없음 | PASS | grep 매치 0건 (현재 GEMINI_* 상수만, L18–19) |
| P3 | `client = get_ai_client()` 할당 없음 | PASS | 할당 grep 0건. 단독 호출만 4곳(L2768/2854/2935/2953) |
| P4 | `analyze_food_image()` client 파라미터 없음 | PASS | `def analyze_food_image(image_bytes, mime_type)` (L332) |
| P5 | `generate_recipe()` client 파라미터 없음 | PASS | `def generate_recipe(vision_result, servings, extra_requests)` (L354) |
| P6 | build_shopping_html을 confirm_recipe 핸들러 내에서만 호출 | **FAIL** | L2993(confirm_recipe 핸들러) 외에 **L2754(load_recipe_pending 핸들러)** 에서도 호출됨. 저장 레시피 재오픈 시 쇼핑 섹션 표시 경로로 의도된 것일 수 있으나, 체크리스트 "~내에서만" 조건과 불일치 |
| P7 | 검색어 `f"{dish_name} {ingredient}"` (용 없음) | PASS | L444 정확히 일치 |
| P8 | _NAVER_STOP_WORDS 의류/전자/인테리어 포함 | PASS | L429(의류·패션·가방), L430(인테리어·가구), L431(전자·가전) 등 |
| P9 | requirements.txt에 groq 없음 | PASS | streamlit / python-dotenv / requests / google-generativeai 만 |
| P10 | py_compile 통과 | PASS | COMPILE_OK |

## UI/CSS 체크리스트

| # | 항목 | 판정 | 근거 |
|---|------|------|------|
| U1 | st.markdown HTML 내 `onclick=` 없음 | PASS | grep 0건 |
| U2 | `material-symbols-outlined` 없음 | PASS | grep 0건 |
| U3 | `@st.dialog("완료 처리")` 정확히 1개 | PASS | L2367 단 1건 |
| U4 | `data-complete` JS listener 없음 | PASS | grep 0건 |
| U5 | `.composer-wrap` 없음 / chat_input CSS 존재 | PASS | composer-* 0건, stChatInputContainer CSS L926~ |
| U6 | `st.write("")` + footer caption 없음 | PASS | grep 0건 |
| U7 | stHeader display:none 있음 | PASS | L900–901 |
| U8 | stFileUploader height:0 숨김 있음 | PASS | L919–923 (height:0 + opacity:0 + abs) |
| U9 | st.chat_input CSS 있음 | PASS | L926/932/943/947/954 |
| U10 | stVerticalBlockBorderWrapper CSS 있음 | PASS | L1592/1601/1602 |

## 기능 무결성 체크리스트

| # | 항목 | 판정 | 근거 |
|---|------|------|------|
| F1 | step2→3 전환 3경로 add_ai_message | PASS | serv 루프 L2894 · serv_skip L2901 · chat_input L3042 |
| F2 | step3 블록 시작 add_ai_message 없음 | PASS | L2908–2912 render_chat_history → columns만, 호출 없음 |
| F3 | _show_completion_dialog 1개 + dlg_cancel/dlg_confirm | PASS | def L2368 단일, key=dlg_cancel(L2432)/dlg_confirm(L2437) |
| F4 | data-del + data-del-pref JS listener 유지 | PASS | L2556/2615 버튼, L2677/2688 listener |
| F5 | st.container(border=True) kitchen 패널 2개 | PASS | L2565, L2623 |
| F6 | st.columns([1,1,1,1,1.5]) step2 chips | PASS | L2888 |
| F7 | st.columns(5) step3 chips (하드코딩) | PASS | L2912 (quick_prefs 4 + skip 1) |
| F8 | step4 review st.columns(3)+3버튼 | PASS | L2965 columns(3) + confirm_recipe/request_revision/reanalyze_btn L2968–2973 |
| F9 | kitchen_complete_target 세팅 후 _show_completion_dialog() | PASS | 세팅 L2529 → 가드 후 호출 L2460–2461 |
| F10 | load_recipe_pending 세팅 + view="chat" "레시피 보기" | PASS | "레시피 보기" 버튼 L2520–2522 (view="chat" + load_recipe_pending) |

---

## 추가 확인 (요청 외 검증)

- **f-string 중괄호 이스케이프**: `build_recipe_prompt` JSON 스키마 블록 `{{`/`}}` 정확(L215/224). `{servings}` 등 의도된 보간만 단일 중괄호. PASS
- **프롬프트 인젝션/특수문자**: `build_recipe_prompt`의 source_md/feedback_md/extra_requests는 f-string 직접 삽입이나 LLM 프롬프트 컨텍스트라 코드 실행 위험 없음. HTML 출력 경로(`build_shopping_html` 등)는 `html.escape` 일관 적용 확인.
- **환경변수 노출**: NAVER 키는 헤더에만 사용, UI 노출 없음.

---

## 종합 판정

총 30개 항목 중 **29 PASS / 1 FAIL**. FAIL은 P6 단 1건이며, 치명적 결함이 아니라 **체크리스트 해석 차이**다. `build_shopping_html`은 confirm_recipe 핸들러(L2993)뿐 아니라 저장 레시피 재오픈 핸들러(load_recipe_pending, L2754)에서도 호출된다. 후자는 보관함 레시피를 다시 열 때 쇼핑 섹션을 재구성하는 의도된 기능으로 보이며, 데이터 손실·크래시 위험은 없다. 다만 체크리스트의 "confirm_recipe 핸들러 내에서만" 문구와는 어긋나므로, 의도된 동작인지 오케스트레이터 판단이 필요하다. 파이프라인(P1–P5,P7–P10), UI/CSS(U1–U10), 기능 무결성(F1–F10) 핵심 항목은 모두 통과했고 py_compile도 정상이다. 에스컬레이션 불요, 권고 수준 1건.
