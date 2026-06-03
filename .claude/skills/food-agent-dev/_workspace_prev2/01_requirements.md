# 요구사항 분석

## 1. 요청 요약

`src/main.py` (1936줄) Streamlit 앱에 React 디자인 파일(`design_extracted/food-agent/project/recipe-ai/`) 기반의 3-뷰(home/chat/kitchen) 사이드바 네비게이션 구조를 이식하고, Bug #26 (재료 칩 단위 분리 오류)과 Bug #27 (취향 추가 버튼 입력 불가)을 함께 수정한다.

---

## 2. 영향 범위

- [x] UI 변경 (대부분 — 전체 레이아웃, 뷰 구조, CSS, 사이드바, 홈 보드, 내 주방 뷰)
- [ ] 파이프라인 변경 (보존 대상 — AI 호출, 파싱, 저장 로직 전부 그대로)

---

## 3. 현재 코드 구조 파악

### src/main.py 섹션별 역할

| 라인 범위 | 역할 |
|---|---|
| 1–16 | import 및 환경 변수 로드 |
| 18–50 | 모델 상수, 경로 상수, config 로더 (보존) |
| 53–99 | source.md/feedback.md 로더 (보존) |
| 100–242 | 프롬프트 빌더 build_vision_prompt(), build_recipe_prompt() (보존) |
| 244–280 | parse_servings(), 이미지 헬퍼 (보존) |
| 282–375 | _gemini_generate(), generate_with_retry() (보존) |
| 377–427 | analyze_food_image(), generate_recipe() — 파이프라인 공개 진입점 (보존) |
| 429–470 | save_recipe(), extract_and_save_feedback() (보존) |
| 472–557 | 네이버 쇼핑 API (보존) |
| 559–706 | _parse_ingredient_string(), parse_source_md_to_data(), save_source_data_to_md() (Bug #26 관련) |
| 709–831 | 장바구니/완료 처리 함수들 (보존) |
| 834–847 | st.set_page_config() (layout="wide"로 변경) |
| 851–1076 | CSS 스타일 (styles.css 기반으로 전면 교체) |
| 1079–1093 | 채팅 헤더 HTML (제거/교체) |
| 1097–1230 | 사이드바 (전면 교체) |
| 1232–1267 | SESSION_DEFAULTS, init_session_state() (확장 필요) |
| 1270–1311 | 공통 헬퍼 함수들 (보존) |
| 1314–1360 | handle_api_error(), reset_all() (새 키 추가) |
| 1362–1499 | fmt_ingredient(), 채팅 렌더링 헬퍼들 (보존) |
| 1501–1573 | 저장 레시피 로드, 웰컴 메시지, 재분석 처리 (보존) |
| 1576–1934 | Step 1~4 플로우 (뷰 분기 안으로 이동) |

### 보존해야 할 핵심 함수

```
build_vision_prompt() / build_recipe_prompt()     # L100~L242
parse_servings()                                  # L247
analyze_food_image() / generate_recipe()          # L382, L405
save_recipe() / extract_and_save_feedback()       # L429, L444
get_shopping_items() / build_shopping_html()      # L481, L526
parse_source_md_to_data() / save_source_data_to_md() # L604, L651
save_to_cart() / list_cart_items()                # L712, L725
calculate_source_update() / save_to_completed()  # L744, L814
get_ai_client() / generate_with_retry()           # L1286, L325
handle_api_error()                                # L1314
fmt_ingredient() / build_recipe_card_html()       # L1362, L1410
_parse_ingredient_string() / _parse_amount_val()  # L569, L578
add_ai_message() / render_chat_history()          # L1371, L1384
```

---

## 4. 디자인 파일 vs 현재 코드 대응표

| 디자인 컴포넌트 | 현재 코드 대응 | 변경 필요 여부 |
|---|---|---|
| app.jsx — view state ('home'/'chat'/'kitchen') | 없음 (단일 채팅 뷰) | **신규 구현** |
| app.jsx — Sidebar | with st.sidebar (L1098~L1230) | **전면 교체** |
| home.jsx — HomeBoard + stat-row | 없음 | **신규 구현** |
| home.jsx — board-hero | 없음 | **신규 구현** |
| home.jsx — recipe-grid / r-tile | 없음 | **신규 구현** |
| kitchen.jsx — KitchenView | 사이드바 expander에만 존재 | **신규 구현 (메인 뷰로)** |
| kitchen.jsx — ing-chips / k-ing | 없음 | **신규 구현** |
| kitchen.jsx — pref-list / pref-row | 없음 | **신규 구현** |
| kitchen.jsx — 완료 처리 대기 패널 | step4 채팅 내 (L1758~L1873) | **뷰 이동** |
| chat.jsx — ChatView 4단계 플로우 | step 1~4 분기 (L1579~L1934) | **구조 유지, 뷰 분기 안으로** |
| chat.jsx — UploadZone | st.file_uploader + st.image (L1584~L1648) | **디자인 개선** |
| styles.css — 전체 디자인 시스템 | 인라인 CSS (L851~L1076) | **교체** |

---

## 5. 에이전트 할당

### ui-developer 작업 목록

1. **CSS 전면 교체** — styles.css 기반 디자인 토큰 + Streamlit 오버라이드 통합
2. **SESSION_DEFAULTS 확장** — view, kitchen_ingredients, kitchen_preferences, adding_pref_mode 등
3. **render_sidebar() 구현** — 브랜드 + 새 레시피 버튼 + 네비(홈/채팅/주방) + 저장된 레시피 목록
4. **render_home_view() 구현** — topbar + board-hero + stat-row 4개 + recipe-grid
5. **render_kitchen_view() 구현** — topbar + 완료 대기 패널 + 재료 칩 패널 + 취향 패널
6. **render_chat_view() 구현** — 기존 Step 1~4 래핑 + 업로드 존/컴포저 디자인 개선
7. **뷰 라우팅 로직** — session_state["view"] 기반 분기
8. **Bug #26 수정** — 재료 칩 렌더링 시 _parse_ingredient_string()만 사용, 단위 분리 없음
9. **Bug #27 수정** — adding_pref_mode session_state 기반 편집 모드 구현

### pipeline-developer 작업 없음 이유

파이프라인 함수들은 순수 함수/파일 I/O로 UI와 완전히 분리되어 있다. 이번 변경은 Streamlit 렌더링 레이어만 교체하므로 파이프라인 코드 수정 불필요.

---

## 6. 새 SESSION_DEFAULTS 설계

```python
# 추가할 키들
"view": "home",                    # 'home' | 'chat' | 'kitchen'
"kitchen_ingredients": [],         # [{"name": str, "amount": str}, ...]
"kitchen_preferences": [],         # [str, ...]  (source.md 사용자 특성)
"adding_pref_mode": False,         # Bug #27 수정: 취향 추가 입력 필드 표시 여부
"adding_pref_text": "",
"home_layout": "grid",             # 'grid' | 'list'
"kitchen_complete_target": None,   # 완료 처리 대상 recipe path
"kitchen_complete_result": None,   # calculate_source_update() 결과
"kitchen_source_edit_mode": False,
"kitchen_source_edit_data": None,
```

---

## 7. Bug #26 분석

**현상**: "당근(2개)" 입력 시 "개" 탭이 별도로 생성됨

**원인 추정**: KitchenView 칩 렌더링 구현 시 amount를 `_parse_amount_val()`로 수량+단위로 분해하여 단위("개")를 별도 렌더링하는 실수.

**수정 방향**:
- `kitchen_ingredients`는 항상 `{"name": str, "amount": str}` 딕셔너리로 유지
- 칩 렌더링 시 `ing["amount"]` 를 그대로 표시 (`_parse_amount_val()` 호출 금지)
- 새 재료 입력 시: `user_input` → `_parse_ingredient_string(user_input)` → dict 저장
- `_parse_amount_val()` 는 `calculate_source_update()` 내부에서만 호출

---

## 8. Bug #27 분석

**현상**: "취향 추가" 버튼 클릭 시 편집 불가

**원인**: Streamlit에서는 React의 contentEditable 인라인 편집 패턴 사용 불가.

**수정 방향**:
```python
if st.button("+ 취향 추가"):
    st.session_state["adding_pref_mode"] = True
    st.rerun()

if st.session_state.get("adding_pref_mode"):
    new_pref = st.text_input("취향 내용", placeholder="예: 토마토 알러지")
    if st.button("추가") and new_pref.strip():
        st.session_state["kitchen_preferences"].append(new_pref.strip())
        _save_kitchen_to_source_md()
        st.session_state["adding_pref_mode"] = False
        st.rerun()
```

---

## 9. CSS 전략

1. **Styles.css 기반 CSS 변수** — `styles.css` `:root` 블록을 `st.markdown(<style>)` 으로 주입
2. **Streamlit 오버라이드 레이어** — `[data-testid="stHeader"]`, `.stApp` 등 셀렉터 유지
3. **디자인 클래스 직접 사용** — `.sb-brand`, `.topbar`, `.board-hero`, `.k-panel`, `.k-ing`, `.pref-row` 등 클래스명 그대로 HTML 렌더링
4. **layout="wide"** — `st.set_page_config(layout="wide")` 로 변경

---

## 10. 리스크 및 주의사항

1. `st.set_page_config()` — 최초 1회만 호출, L847 위치 유지
2. `chat_history` — 뷰 전환 시 session_state 유지 필수
3. `kitchen_ingredients/preferences` 변경 즉시 `save_source_data_to_md()` 호출
4. `st.chat_input()` — 채팅 뷰에서만 표시 (조건부 호출)
5. 완료 처리 플로우 — 현재 Step 4 채팅 내 → kitchen 뷰 패널로 이동
6. `layout="wide"` 전환 — 기존 CSS max-width 설정 확인
7. 취향 kind — source.md에는 텍스트만 저장 (kind는 session_state에만 유지)
8. r-tile / r-listrow — 홈 보드용 레시피 타일 렌더 함수 별도 추가 필요
