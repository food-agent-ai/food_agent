# UI 변경 요약 (03_ui_changes.md)

대상: `src/main.py`, `SKILL.md`
스키마 변경: 없음 (UI 전용)

---

## [2026-06-02] UI 버그 7개 수정 (CSS/레이아웃)

대상: `src/main.py` (CSS 섹션 + Step 2/3 Python 래퍼 + topbar HTML)

### IMG-1 (Critical): Step 2/3 인분·추가요청 칩 전체 너비 분산 → 좌측 정렬 pill
- Python: Step 2를 `with st.container(key="step2_chips")`, Step 3를 `with st.container(key="step3_chips")`로 감쌈. 기존 `st.markdown('<div class="quick-reply-wrap">')` / `</div>` 빈 div 제거.
- CSS: 기존 `.quick-reply-wrap`/`st-key-serv_`/`st-key-pref_` 스코핑 블록을 container key 기반으로 교체.
  - `[class*="st-key-step2_chips"] [data-testid="stHorizontalBlock"]` → `flex-wrap:wrap; gap:8px; padding-left:48px`
  - `[data-testid="column"]` → `flex:0 0 auto; width:auto` (콘텐츠 너비)
  - `button` → pill 스타일(`border-radius:var(--r-pill)`, `width:auto`)
- 검증: 라이브 DOM 클론 측정 — 칼럼 너비 62/62/62/62/89px (균등분산 ~140px 아님), border-radius 999px, flex-wrap wrap, padding-left 48px.

### QA-1 + IMG-2: 사이드바 레시피 아이템 간 과도한 여백
- 원인: 레시피 아이템은 [markdown 비주얼 카드] + [투명 오버레이 버튼] 2개 stElementContainer로 구성. 버튼 컨테이너가 레이아웃 높이를 차지 + stVerticalBlock의 16px gap이 카드당 2번 적용되어 ~52px 간격 발생.
- 수정: `[class*="st-key-sb_recipe_"]` 컨테이너 `height:0; overflow:visible`로 레이아웃에서 제거 → gap이 카드당 1회(16px)만 적용.
- 오버레이 버튼: `transform: translateY(-55px)`로 비주얼 카드 위에 정확히 정렬(margin-top은 프레임워크에서 clamp되어 transform 사용). btnTop/Bottom = cardTop/Bottom = 432/487, 클릭 히트 정상.
- 결과: 아이템 간 gap 52px → 16px 균일.

### QA-2: topbar 우측 스크롤바 비대칭
- `[data-testid="stMain"] { scrollbar-gutter: stable }` 추가. (computed 확인: stable)

### QA-3: day-separator topbar 뒤 비침
- `.chat-wrap { scroll-padding-top: 70px }`, `.day-sep { scroll-margin-top: 70px }` 추가.

### IMG-3: 채팅 하단 빈 공간 과다
- IMG-1의 빈 `</div>` 제거 + `[class*="st-key-step2_chips"], [class*="st-key-step3_chips"] { margin-bottom:0 }`로 해소.

### IMG-4: "항상 활성화" 뱃지 제거
- `render_chat_view()` topbar HTML에서 `<div class="topbar-status"><span class="live-dot"></span>항상 활성화</div>` 제거 (옵션 B). `.topbar-status` CSS 정의는 잔존하나 미사용·무해.
- 검증: `document.querySelector('.topbar-status')` === null.

### QA 테스트 포인트
- Step 2/3 칩: 좌측 정렬·콘텐츠 너비 pill (실제 이미지 업로드 시 육안 재확인 권장 — 본 검증은 라이브 DOM 클론으로 cascade 확인).
- 사이드바: 홈/채팅 양 뷰에서 아이템 간격 16px 균일, 클릭 정상.
- topbar: 모든 뷰 상단 고정, "항상 활성화" 뱃지 없음.

---

## [A] 사진 업로드 자동 분석 (Step 1)
- 위치: `render_chat_view()` Step 1, `else:` 분기 (~line 2843~2887)
- "사진 분석하기" 버튼 제거 → `_last_file_name` 비교로 새 파일 감지 시 즉시 자동 분석
- 분석 전후 `st.session_state["_typing"]` True/False 세팅
- 비음식(non-food) 판정 시 `_last_file_name = None`으로 리셋 → 동일 파일 재업로드 시 재분석 보장
- 기존 vision_result 처리 로직(is_food 분기 등)은 들여쓰기만 조정해 그대로 유지

## [B] 인분 선택 후 AI 확인 메시지 (Step 2)
- 위치: 인분 버튼 5종 (~line 2939~2962), chat_input Step 2 처리 (~line 3060)
- 각 인분 버튼: `add_ai_message(f"{val}인분으로 준비할게요 👍")` 추가
- 건너뛰기: `"기본 2인분으로 준비할게요 👍"`
- chat_input 직접 입력: `parse_servings` 결과로 `"{N}인분/기본 2인분으로 준비할게요 👍"` 동적 생성

## [C] 타이핑 인디케이터
- C-1: `render_chat_history()` for 루프 종료 후 `_typing` flag True면 타이핑 버블 HTML 추가 (~line 1880)
- C-2/C-3: 분석([A]) 및 레시피 생성(Step 4, ~line 2989) 전후 `_typing` True/False 세팅
- C-4: CSS `[data-testid="stSpinner"] { display:none }` 추가 (~line 1149) — spinner는 코드 유지하되 시각적으로 숨김

## [D] 퀵리플라이 칩 위치 개선 (Step 2, 3)
- CSS `.quick-reply-wrap` 추가 (~line 1149~) — padding-left 48px, flex wrap, pill 스타일
- Step 2/3 버튼을 `st.markdown('<div class="quick-reply-wrap">')` ~ `</div>`로 감싸고
  `use_container_width` 제거, `st.columns(5, gap="small")` 사용
- 주의: Streamlit columns는 markdown div의 형제로 렌더링되므로 `.quick-reply-wrap .stButton` 자손 선택자가
  실제 columns 버튼에 적용되지 않을 수 있음 (요구사항에서 인지된 Streamlit 한계). pill 스타일 미적용 시
  columns 버튼에 직접 `st-key-serv_*` / `st-key-pref_*` 스코핑 CSS로 보강 필요 (후속 QA 포인트).

## [E] 헤더 아래로 뜨는 문제
- `.topbar` CSS (~line 1056): `margin-bottom: 8px → 0`, `position: sticky; top:0; z-index:100` 추가

## [F] 메인 좌우 달라붙는 문제
- `[data-testid="stMainBlockContainer"]`에 `overflow-x: hidden` 추가 (~line 915)
- `.main { min-width:0; overflow-x:hidden }` 추가
- `.chat-wrap` padding `30px 26px 40px → 24px 32px 40px`, `box-sizing: border-box` 추가 (~line 1120)

## [G] 사이드바 "열기" 버튼 버그
- G-1: 레시피 아이템 HTML div(pointer-events:none) + 별도 "열기" 버튼 제거 →
  단일 `st.button(f"🍽️  {_name}\n{_meta}", ...)`로 통합 (~line 2096)
- G-2: CSS 교체 — `[class*="st-key-sb_recipe_"]`와 `.sb-saved` 스코프에 좌측 정렬 텍스트 버튼 스타일,
  `white-space: pre-wrap`으로 줄바꿈 label 렌더 (~line 1418)
- 주의: 현재 코드에 `.sb-saved` 래퍼 div가 사이드바 레시피 목록을 감싸고 있지 않음.
  CSS는 `st-key-sb_recipe_` 키 스코프로도 동작하도록 셀렉터를 OR로 작성해 안전.

---

## SKILL.md 업데이트
- "Groq Llama 4 Scout" → "Gemini 2.5 Flash"
- `meta-llama/llama-4-scout-17b-16e-instruct` (Groq Vision) → `gemini-2.5-flash` (Gemini Vision)
- `GROQ_API_KEY` → `GEMINI_API_KEY`
- 파이프라인 체크리스트 `Groq API, 프롬프트` → `Gemini API, 프롬프트`

---

## QA 테스트 포인트
1. 새 사진 업로드 시 버튼 없이 즉시 분석되는지 / 동일 파일 재업로드 시(특히 비음식 후) 재분석되는지
2. 인분 버튼·직접입력 모두 "N인분으로 준비할게요 👍" AI 메시지가 선행되는지
3. 분석/레시피 생성 중 타이핑 버블이 보이고 Streamlit spinner는 숨겨지는지
4. 퀵리플라이 칩이 좌측 정렬·pill 형태로 보이는지 (columns 스코핑 한계 확인 필요)
5. topbar가 스크롤 시 상단 고정되고 gap 없이 붙는지
6. 채팅 영역 좌우 여백이 확보되는지
7. 사이드바 레시피 아이템 클릭 시 채팅으로 로드되는지 / "열기" 텍스트가 사라졌는지

## 미검증 사항
- 환경에 Python 미설치로 `py_compile` 정적 검증 불가. `streamlit run src/main.py`로 런타임 확인 권장.

---

## [H] CSS/레이아웃 버그 3종 수정 (2026-06-02)

### [H-1] chat-wrap 빈 div 제거 (topbar 아래 gap 원인)
- `render_chat_view()`에서 `st.markdown('<div class="chat-wrap">', ...)` (이전 ~line 2862)와
  대응하는 닫는 `st.markdown('</div>', ...)  # .chat-wrap 닫기` (이전 ~line 3127) 두 줄 모두 제거.
- 원인: Streamlit이 이후 컴포넌트를 div 자식이 아닌 sibling으로 렌더 → chat-wrap이 빈 박스로 남아
  padding이 빈 박스에 적용되며 큰 공백 발생.

### [H-2] 좌우 여백 CSS를 실제 컨테이너에 적용
- `[data-testid="stMainBlockContainer"]` 룰 직후(~line 918)에 추가:
  - `[data-testid="stMain"] > div > [data-testid="stVerticalBlock"]` → `padding: 0 24px; box-sizing: border-box`
  - 첫 자식(topbar) → `margin-left/right: -24px; width: calc(100% + 48px)`로 full-width 유지
- 빈 chat-wrap 대신 실제 stVerticalBlock에 좌우 여백 적용.

### [H-3] 사이드바 레시피 아이템 디자인 복원 (HTML overlay 패턴)
- `render_sidebar()` 레시피 루프(~line 2162): plain 텍스트 버튼
  `st.button(f"🍽️  {_name}\n{_meta}", ...)` 제거 →
  1) `sb-recipe-wrap` HTML div(썸네일+이름+메타+상태점, `pointer-events:none`)로 비주얼 렌더
  2) `_dot_color` 미사용 (dot 색은 `dot-cart`/`dot-done` 클래스로 처리). `html.escape()`로 이름/메타 이스케이프.
  3) 제로폭 공백 라벨 `st.button("​", ...)` 오버레이로 클릭 처리 (세션 상태/rerun 로직 동일)
- CSS 교체 (~line 1477): 기존 `.sb-saved .stButton > button` + `[class*="st-key-sb_recipe_"] .stButton > button`
  텍스트 버튼 룰 전체 → `[class*="st-key-sb_recipe_"] > button` 투명 오버레이 룰로 교체
  (`background/color: transparent`, `font-size:0`, `height:50px`, `margin-top:-54px`, `z-index:1`; hover 시 `rgba(0,0,0,0.04)`).
- 사용 클래스 `sb-recipe-wrap/-thumb/-name/-meta`, `sb-status-dot`, `dot-cart`, `dot-done` 모두 기존 CSS에 존재(확인 완료).

### 검증
- `ast.parse` 정적 구문 검사 통과 (OK).

### QA 테스트 포인트 (추가)
8. topbar 아래 큰 공백이 사라졌는지
9. 채팅/홈/주방 콘텐츠가 좌우 24px 여백을 갖고 topbar는 full-width인지
10. 사이드바 레시피 아이템이 썸네일+이름+메타+상태점 디자인으로 보이고, 투명 버튼 클릭 시 채팅 로드되는지

---

## [I] 개발자 디버그 모드 (DEV MODE) (2026-06-02)

목적: Gemini API 호출 없이 더미 데이터로 채팅 플로우 각 단계(Step 1~4 + 에러/확정 화면)를 즉시 재현하여 UI 디버깅 가속.
주의: 모든 블록은 `# DEV MODE` ~ `# DEV MODE END` 주석으로 감쌈. 프로덕션 배포 전 두 블록 전체 삭제.

### [I-1] 사이드바 트리거
- 위치: `render_sidebar()` 내 `with st.sidebar:` 블록, sb-foot 프로필 직후 / nav `components.html` 직전.
- `st.button("⚙", key="_dev_toggle_btn")` 클릭 시 `st.session_state["_dev_mode"]` 토글 후 rerun.

### [I-2] 디버그 패널 본체
- 위치: `render_chat_view()` 함수 최상단 (topbar 렌더 이전).
- `_dev_mode` True일 때만 렌더. 7개 컬럼 버튼:
  - ① 초기화 → 세션 리셋, 빈 채팅
  - ② 인분선택 → Step 2 (vision 더미 + 인분 질문)
  - ③ 추가요청 → Step 3 (2인분 확정 후 추가요청 질문)
  - ④ 레시피카드 → Step 4 (레시피 카드 렌더, `build_recipe_card_html`)
  - ⑤ 비음식에러 → non-food 에러 메시지
  - ⑥ API에러 → API 오류 메시지
  - ⑦ 레시피확정 → recipe_confirmed True, 저장 완료 메시지
- 더미 데이터: `_DEV_DUMMY_VISION`(카놀리), `_DEV_DUMMY_RECIPE`(카놀리 레시피, vision_result/recipe_result 스키마 준수).
- `_dev_reset()`: step/vision_result/servings/recipe_result/chat_history 등 13개 키를 `SESSION_DEFAULTS` 기본값으로 리셋.

### 스키마 의존성
- `vision_result`: is_food, dish_name, ingredients, characteristics
- `recipe_result`: dish_name, servings, cooking_time, difficulty, ingredients[{name,amount}], steps[], tags[]
- 파이프라인 스키마 변경 시 `_DEV_DUMMY_VISION`/`_DEV_DUMMY_RECIPE` 동기화 필요.

### 검증
- `ast.parse` 정적 구문 검사 통과 (OK).
- `SESSION_DEFAULTS`(L1782), `build_recipe_card_html`(L1981), `add_ai_message`/`add_user_message`(L1930/1938) 모두 render_chat_view 이전 정의 확인.

### QA 테스트 포인트 (추가)
11. 사이드바 하단 ⚙ 클릭 시 채팅 뷰 상단에 DEV 패널 표시되는지
12. ② 인분선택 → Step 2 칩, ④ 레시피카드 → 카드 전체 렌더, ⑤/⑥ 에러 메시지 정상인지
13. ⚙ 재클릭 시 패널 숨김(_dev_mode 토글)
