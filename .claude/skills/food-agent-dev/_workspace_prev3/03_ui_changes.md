# 03_ui_changes — UI 정리/리팩터링

대상: `src/main.py` (3164 → 약 3100여 줄)
검증: `python -m py_compile src/main.py` 통과 / `@st.dialog("완료 처리")` 1개 / `data-complete`·`composer-wrap`·`onclick=` 0개

---

## CRITICAL

### C-01: `@st.dialog("완료 처리")` 중복 정의 제거
- 첫 번째 정의(`dialog_cancel`/`dialog_confirm` 키 사용, 구 버전) 전체 삭제.
- 두 번째 정의(`dlg_cancel`/`dlg_confirm` 키 사용)만 유지.
- 결과: `_show_completion_dialog` 함수가 정확히 1개. 동일 `@st.dialog` 데코레이터가 두 번 등록되어 Streamlit이 어느 정의를 호출할지 모호하던 문제 해소.

## HIGH

### H-02: Step 3 안내 메시지(`add_ai_message`) 호출 위치 이동
- 기존: step 3 블록 상단에서 매 rerun마다 호출 → `add_ai_message`의 중복 가드가 있긴 했으나 흐름이 불명확.
- 변경: step 3 블록 상단 호출 제거. step 2 → step 3 전환 직전 3개 경로 모두에 추가:
  - 인분 칩 버튼 4개 (`serv_*` 루프)
  - 건너뛰기 버튼 (`serv_skip`)
  - 하단 `st.chat_input` step 2 핸들러
- 메시지: `"더 반영할 요청이 있나요? <span class='sub'>(없으면 건너뛰어도 돼요)</span>"`

### H-03: `data-complete` JS 리스너 제거 (데드코드)
- 완료 처리 버튼은 이미 `st.columns + st.button`(`kitchen_complete_*`)으로 직접 구현됨.
- kitchen `components.html` 내 `[data-complete]` forEach 블록 삭제.
- `data-del` / `data-del-pref` 리스너는 유지(재료/취향 칩 × 삭제 동작).
- 연관: 위 블록을 가리키던 stale 주석 1줄도 정리.

### H-04: `st.columns(len(...)+1)` → `st.columns(5)` 하드코딩
- step 3 quick_prefs 칩(4개) + 건너뛰기(1개) = 항상 5열. 동적 계산을 상수로 고정.

## MEDIUM

### M-01: `composer-*` 데드 CSS 제거
- `<style>` 내 커스텀 composer HTML용 클래스 전부 삭제:
  `.composer-wrap`, `.composer`, `.composer-box`, `.composer-box:focus-within`,
  `.composer-input`, `.composer-input::placeholder`, `.composer-send`(+hover/disabled),
  `.composer-icon-btn`(+hover).
- `st.chat_input` 관련 CSS(`[data-testid="stChatInputContainer"]` 등)는 유지.

### M-02: 완료 처리 다이얼로그 `st.caption()` → HTML 스타일
- `_blocked_d`(자동 차감 불가): `complete-line` + 앰버 `⚠` 아이콘 칩 HTML로 교체.
- `_missing_d`(구매 필요): `complete-line` + `구매` 배지 + (있으면) `chr` 수량 span HTML로 교체.
- 모든 값 `html.escape` 처리. 다이얼로그 시각 일관성 향상(used 라인과 동일한 `.complete-line` 스타일).

## LOW

### L-02: `sb-foot`의 `sb-brand-name` 클래스 제거
- 사이드바 하단 "내 주방" 라벨을 인라인 스타일(`color:var(--ink)`)로 교체. brand-name 클래스 의미 중복 제거.

### L-03: 사이드바 빈 레시피 안내 `st.caption` → HTML
- "아직 저장된 레시피가 없어요." 를 `--ink-3` 색 인라인 div로 교체(디자인 시스템 톤 일치).

---

## QA 테스트 포인트

1. **완료 처리 다이얼로그** (내 주방 → "✓ 완료 처리"):
   - 자동 차감/차감 불가/구매 필요 3개 섹션이 모두 `complete-line` 스타일로 렌더되는지.
   - `dlg_cancel`/`dlg_confirm` 버튼 동작(취소·확정 후 재료 차감 및 success 메시지).
   - 다이얼로그가 1개만 뜨는지(중복 정의 제거 확인).
2. **채팅 Step 2 → 3 전환**: 인분 칩 4개 / 건너뛰기 / 직접 입력 모든 경로에서 "더 반영할 요청이 있나요?" 메시지가 정확히 1번 표시되는지(중복 X, 누락 X).
3. **Step 3 레이아웃**: 5열(칩 4 + 건너뛰기) 정상 배치.
4. **내 주방 재료/취향 칩 × 삭제**: `data-del`/`data-del-pref` 동작 유지 확인(H-03이 이 리스너를 건드리지 않았는지).
5. **사이드바**: 저장 레시피 없을 때 안내 문구 표시 / 하단 "내 주방" 라벨 정상.

## 스키마 영향
- pipeline JSON 스키마(`used`/`blocked`/`missing` 필드 구조) 변경 없음. 모든 접근은 기존 `result.get(...)` 패턴 유지. UI 표시 방식만 변경.
