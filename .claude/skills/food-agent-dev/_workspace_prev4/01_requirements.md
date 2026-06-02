# 요구사항 분석 — QA + 이미지 버그 수정

## 요청 요약
QA 발견 3개 + 이미지 분석 4개 (총 7개 UI 버그) 수정. UI 전용.

## 영향 범위
- UI 변경만 (src/main.py)

## 에이전트 할당
- pipeline-developer: 없음 (스킵)
- ui-developer: 전체 7개 항목

---

## Phase 0.5 DevTools 측정 결과

### 사이드바 오버레이 측정
- 비주얼 카드 top=487, height=26 → bottom=513
- 버튼 top=474, height=50 → bottom=524
- 버튼이 비주얼 카드보다 12px 위에서 시작. 버튼(height=50) > 카드(height=26) → 차이 24px이 다음 아이템 밀어냄

### 항상 활성화 뱃지
- class: topbar-status (앱 코드에서 렌더링)

---

## 항목별 수정 명세

### [1] IMG-1: 인분 칩 전체 너비 분산 (Critical)
- 원인: st.columns(5) 균등 분할 + quick-reply-wrap div가 Streamlit 컴포넌트 감싸기 실패
- 수정: st.container(key="step2_chips") / st.container(key="step3_chips") 로 감싼 뒤
  CSS로 해당 컨테이너 내 stHorizontalBlock 타겟팅
  column: flex 0 0 auto, width auto
  stHorizontalBlock: flex-wrap wrap, gap 8px, padding-left 48px

### [2] QA-1+IMG-2: 사이드바 아이템 과도한 여백
- 원인: 버튼 height=50, 카드 height=26 → 24px 차이가 여백 생성
- 수정: CSS로 st-key-sb_recipe_ 컨테이너 height 조정
  [class*="st-key-sb_recipe_"] { min-height: 0 !important; height: auto !important; }
  [class*="st-key-sb_recipe_"] button { height: 46px !important; }

### [3] QA-2: topbar 우측 스크롤바 비대칭
- 수정: body 또는 stMain에 scrollbar-gutter: stable 추가

### [4] QA-3: day-separator topbar 뒤 비침
- 수정: .chat-wrap padding-top 추가 또는 .day-sep scroll-margin-top 설정

### [5] IMG-3: 채팅 하단 빈 공간 과다
- 원인: quick-reply-wrap close div 태그 + flex spacing
- 수정: Step 2/3에서 st.markdown('</div>') 제거 또는 CSS margin 조정

### [6] IMG-4: 항상 활성화 뱃지
- class: topbar-status
- 수정: .topbar-status { display: none !important; } 또는 내용 대체

## 수정 파일
- src/main.py (CSS + Python Step 2/3 + render_sidebar)
