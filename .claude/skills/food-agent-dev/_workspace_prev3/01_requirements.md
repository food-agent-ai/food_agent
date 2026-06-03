# 01_requirements.md — food-agent 현황 분석

분석 기준일: 2026-06-01
파일: src/main.py (3159줄)

---

## CRITICAL

### C-01: @st.dialog("완료 처리") 중복 정의 (라인 2384, 2459)
두 개의 _show_completion_dialog 함수가 정의됨. 후방 정의가 전방을 덮어쓰므로 전방(2384–2456) 삭제 필요.
- 담당: ui-developer

### C-02: Step 3 add_ai_message() 순서 오류 (라인 2993–2997)
render_chat_history() 앞에서 호출 → rerun마다 중복 시도. step 2→3 전환 시점으로 이동 필요.
- 담당: ui-developer

---

## HIGH

### H-01: client = get_ai_client() 불필요 할당 (라인 2855, 2941, 3023)
client 변수가 None이고 파이프라인 함수에 전달 안 됨. 단독 get_ai_client() 호출로 교체.
- 담당: pipeline-developer

### H-02: 사이드바 sb-recipe - "열기" 텍스트 버튼 노출 (디자인 의도 불일치)
전체 행이 클릭 가능해야 하는 디자인과 달리 별도 "열기" 버튼이 노출됨.
- 담당: ui-developer

### H-05: kitchen data-complete JS listener 잔존 데드코드 (라인 2752–2761)
완료 처리 버튼이 이미 st.columns + st.button으로 교체됐으나 JS listener 코드가 남아있음.
- 담당: ui-developer

---

## MEDIUM

### M-01: composer-wrap 데드 CSS 블록 (라인 1261–1280)
HTML composer 제거됐으나 CSS 잔존.
- 담당: ui-developer

### M-02: 완료 처리 다이얼로그 내 st.caption() — complete-line HTML 스타일 불일치
디자인 시스템의 .complete-line HTML을 사용해야 함.
- 담당: ui-developer

### M-04: Step 3 add_ai_message 중복 삽입 위험 (C-02와 연관)

---

## LOW

### L-01: _NAVER_STOP_WORDS 비식품 키워드 추가 여지
- 담당: pipeline-developer

### L-02: sb-foot에서 sb-brand-name 클래스 재사용 → 별도 스타일로 분리
- 담당: ui-developer

### L-03: 사이드바 빈 레시피 목록 - st.caption() → HTML 스타일 통일
- 담당: ui-developer

---

## pipeline-developer 작업 목록

| 우선순위 | 작업 | 라인 |
|---|---|---|
| HIGH | get_ai_client() 불필요 client= 할당 3곳 제거 | 2855, 2941, 3023 |
| LOW | _NAVER_STOP_WORDS 추가 검토 | 420–429 |

## ui-developer 작업 목록

| 우선순위 | 작업 | 라인 |
|---|---|---|
| CRITICAL | @st.dialog 중복 정의 제거 | 2384–2456 |
| HIGH | Step 3 add_ai_message 순서 이동 | 2993–2997 |
| HIGH | data-complete JS listener 제거 | 2752–2761 |
| HIGH | st.columns(len(...)+1) → st.columns(5) | 3000 |
| MEDIUM | composer-wrap 데드 CSS 제거 | 1261–1280 |
| MEDIUM | 다이얼로그 st.caption() → complete-line HTML | 2425, 2431 |
| LOW | sb-foot 클래스 정리 | 2119–2129 |
| LOW | 빈 사이드바 레시피 st.caption → HTML | 2085 |
