# QA 보고서

검토 대상: `C:\research\food_agent\src\main.py` (총 2542행)
검토일: 2026-05-31
검토 범위: UI 리팩토링(home/chat/kitchen 3-뷰) + Bug #26/#27 + 파이프라인 보존

> 정적 코드 분석 기준. `streamlit run` 미실행. `list_completed_items`는 파일 전체 0회 등장(정의·호출 모두 없음) — 완료 목록은 `glob.glob(f"{COMPLETED_JSON_DIR}/*.json")` 직접 조회(1742/1827/kitchen). 초기 크래시 가설 기각.

## 검증 결과 요약

| 항목 | 결과 | 비고 |
|------|------|------|
| A. 파이프라인 보존 | PASS | 19개 함수 전부 line 1~831 보존, 미수정 |
| B. Bug #26 수정 | PASS | `_parse_ingredient_string` → 단일 dict, 칩 단위 렌더 |
| C. Bug #27 수정 | PASS | `adding_pref_mode` 토글 + 종료 경로 False 복귀 |
| D. 3-뷰 라우팅 | PASS | `view` 분기 + 네비 버튼 + 3 render 함수 |
| E. 통계 카드 계산 | PASS | 4개 계산식 명세 일치 |
| F. SESSION_DEFAULTS | PASS | 신규 키 + init None→source.md 로드 |
| G. set_page_config | PASS | `layout="wide"`, 활성 호출 1회(846) |
| H. CSS 완전성 | PASS | 체크리스트 클래스 + `:root` 변수 전부 |
| I. 채팅 뷰 step 보존 | PASS | Step 1~4 + 재분석 플로우 온전 |
| J. 엣지 케이스 | WARN | 경미 이슈, 항목별 참조 |

**최종 판정: PASS (경미 이슈 동반).** 배포 차단급 결함 없음.

## 세부 검증 결과

### A. 파이프라인 보존 — PASS
19개 함수 전부 보존(미수정): build_vision_prompt(103), build_recipe_prompt(155), parse_servings(247), analyze_food_image(382), generate_recipe(405), generate_with_retry(325), _gemini_generate(282), save_recipe(429), extract_and_save_feedback(444), get_shopping_items(481), build_shopping_html(526), parse_source_md_to_data(604), save_source_data_to_md(651), save_to_cart(712), list_cart_items(725), calculate_source_update(744), save_to_completed(814), _parse_ingredient_string(569), _parse_amount_val(578). 시그니처 변경 없음.

### B. Bug #26 — PASS (코드 정독 확정)
- 입력 처리(2150~2154): `_new_ing.strip()` → `_parse_ingredient_string()`(569) → 단일 dict → `kitchen_ingredients.append()` → `_save_kitchen_to_source()`. "개" 같은 단위가 별도 항목으로 분리되지 않음.
- 칩 렌더링(2114~2135): `amount` 문자열을 그대로 `<span class="amt">`로 표시(수량/단위 분해 안 함). 코드 주석에도 "Bug #26: amount 문자열을 그대로 표시. 수량/단위 분해 금지" 명시.
- session_state에 단일 dict 저장 확인. **수정 정합성 OK.**

### C. Bug #27 — PASS (코드 정독 확정)
- 버튼(2203~2206): `not adding_pref_mode`일 때 "+ 취향 추가" → `adding_pref_mode=True`+rerun.
- 입력 모드(2207~2225): True일 때 `st.text_input`(2208) 표시.
- 추가(2216~2221): `kitchen_preferences.append()` → `_save_kitchen_to_source()`(→save_source_data_to_md) → `adding_pref_mode=False`.
- 취소(2222~2225): `adding_pref_mode=False`.
- 모든 종료 경로 초기화. **수정 정합성 OK.**

### D. 3-뷰 라우팅 — PASS
메인 디스패치(2531~2539): render_sidebar 후 view 분기 → home(1812)/kitchen(1936)/chat(2231). 네비 버튼(1723~1733) view 변경+rerun.

### E. 통계 카드 — PASS
저장(cart+completed), 장바구니(len cart), 완료(len completed glob), 보유 재료(len kitchen_ingredients) — 1825~1831, 카드 매핑 1866~1892. 명세 일치.

### F. SESSION_DEFAULTS — PASS
신규 키 1402~1411: view/kitchen_ingredients/kitchen_preferences/adding_pref_mode(+reanalyze_pending 등). init(1415~1425) None→parse_source_md_to_data. reset_all(1495)도 반영.

### G. set_page_config — PASS
846: layout="wide", 1회만 활성(43은 주석). 모듈 최상위 호출, 규칙 준수.

### H. CSS — PASS
855~1375에 k-panel*(1316~), ing-chips/k-ing/k-add(1323~), pref-*(1339~), board/board-hero/bh-title/stat-row/stat-card(1240~), r-tile/r-listrow/badge-cart/badge-done(1279~), :root 변수(861~919) 전부 존재.

### I. 채팅 step 1~4 — PASS
Step1 업로더+4MB체크+stop(2332~2334)+analyze(2340)+비음식분기(2347~2353)+파싱실패(2343); Step2 parse_servings(2392); Step3 추가요청(2399~); Step4 generate_recipe(2440)+3분기(2489~2510)+확정후액션(2513~). 재분석은 step분기 전 처리(2286~2304).

### J. 엣지 케이스 — WARN
1. kitchen None 렌더: `... or []` 방어 + init 선행 → 안전.
2. 타일 key: sb_recipe_(1762)/tile_open_(1804) prefix 분리. **단 이슈 #1 참조.**
3. st.chat_input: 미사용(0회), text_input/button 기반 → home/kitchen 레이아웃 무영향.
4. 완료 후 갱신: save_to_completed(2035/2081)+rerun → 사이드바/홈 재계산, kitchen_ingredients는 calculate_source_update(1998/2079) 갱신. 반영됨.

## 발견된 이슈

### 치명적 이슈
**없음.**

### 경미한 이슈
**#1 [중복 key 가능성] 홈 타일 button key 충돌**
cart 항목이 "이어서 완료하기"(1898~1900)와 "최근 레시피 기록"(1914~1920) 양쪽에 포함(`_all_recipes`에 `_cart_items` 그대로 추가). 두 섹션이 같은 cart 파일 렌더 시 `st.button(key=f"tile_open_{basename}")`(1804) 동일 key 2회 → StreamlitDuplicateElementKey 가능. 발현조건: 장바구니 1개+ & 홈 진입. 권장: 타일 key에 섹션 prefix(tile_open_cart_/tile_open_recent_) 또는 최근 목록서 cart 중복 제외. **런타임 1회 확인 강력 권장.**

**#2 [의존성] requirements.txt 버전 미고정**
streamlit/groq/python-dotenv/requests/google-generativeai 전부 핀 없음. label_visibility/use_container_width/type 버튼 사용 → 최소 버전 고정(예: streamlit>=1.31) 권장.

**#3 [경미] characteristics 문장 수 기준 충돌**
build_vision_prompt 내 "2~3문장"(122) vs "3문장 이상"(140) 공존. 스키마 무영향. 문구 통일 권장.

**#4 [정보] 비음식 시 step 유지** — state 리셋 후 step1 유지(2351~2353), 재업로드 정상. 의도된 동작.

## 경계면(스키마) 교차 검증 — 일치, silent bug 없음
- vision: is_food(2347)/non_food_reason(2349)/dish_name(2355)/ingredients(2356) 전부 `.get(.., default)`.
- recipe(build_recipe_card_html 1579): dish_name/introduction/cooking_time/difficulty/servings(1585~1592), ingredients→_parse_ingredient_string(1602), steps(1619), missing_ingredients(1594~1596).
- f-string `{{ }}` 이스케이프 정확(231~240).
- HTML/XSS: user content(1573)/카드(1585~)/타일(1776~1778)/쇼핑(548~549 quote=True) 전부 html.escape. 안전.
- 에러: 키 미설정 안내+stop(1459/1466), rate-limit 분류+stop(1492), 재시도 백오프(325), 파싱실패 (None,raw). 양호.
- 한국어 일관성: 신규 UI 텍스트 전부 한국어. OK.

## 권장 사항
1. (우선) 이슈 #1 런타임 확인: 장바구니 1개 둔 채 홈 진입해 DuplicateElementKey 확인.
2. (권장) 회귀 검증: 3뷰 진입 + Bug#26("당근(2개)") + Bug#27(취향추가) + 확정→완료(재료차감).
3. (권장) 이슈 #2 버전 고정.
4. (선택) 이슈 #3 문구 통일.

> 검토 범위: 파이프라인(1~831), CSS(855~1375), session_state/헬퍼(1381~1672), 사이드바(1678~1768), 홈(1774~1930), kitchen 본문(1936~2225 전문 정독 완료), 채팅(2231~2542) 전 구간 확인. Bug#26/#27는 코드 라인별 정독으로 확정. 잔여 미검증은 실런타임뿐이며, 그중 이슈 #1만 우선 확인 필요.
