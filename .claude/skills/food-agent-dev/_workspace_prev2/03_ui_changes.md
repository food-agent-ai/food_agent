# 03_ui_changes — UI 전면 교체 (ref3.jpg 챗봇 스타일 + 재분석 플로우)

대상: `C:\research\food_agent\src\main.py` (line 365 UI 섹션 ~ 파일 끝)
파이프라인 함수(line 1~362)는 변경하지 않음.

## 변경 요약

### 1. 디자인 전면 교체 (ref2 보라색 → ref3 화이트/블루 챗봇)
- CSS를 ref3.jpg 명세로 전면 교체.
  - 흰색 배경(`.stApp`, `[data-testid="stAppViewContainer"]`), 투명 헤더.
  - AI 버블: 연회색 `#F0F0F0`, 좌측, 로봇 아바타(`.msg-row-ai` / `.avatar-ai` / `.bubble-ai`).
  - USER 버블: 파랑 `#3B82F6`, 우측(`.msg-row-user` / `.bubble-user`).
  - 레시피 카드: 흰색 + 테두리 + 그림자, `step-num` 파란 원형 번호, `divider` 클래스.
  - `footer` 숨김, `#MainMenu` 숨김.
- 상단 `.chat-header` 추가: 봇 아바타 + 이름("레시피 AI") + 초록 상태점("● 항상 활성화"). sticky.
- 기존 중앙 `<h2>` 앱 타이틀 제거(헤더가 대체).

### 2. session_state 신규 키
- `reanalyze_pending: False` 추가 (재분석 트리거). `SESSION_DEFAULTS`와 `reset_all()` 양쪽 반영.

### 3. 헬퍼 변경
- `render_chat_history()`: 새 클래스(`msg-row-ai`/`bubble-ai`, `msg-row-user`/`bubble-user`)로 마크업 교체. user content `html.escape(str(...))`.
- `build_recipe_card_html()`: ref3 카드 레이아웃으로 재구성 — `step-item`을 flex(번호 + 텍스트), `divider` 클래스, intro에 회색 인라인 스타일. 모든 텍스트 `html.escape`.
- `add_ai_message` 중복 방지 로직은 기존 유지(재렌더 시 step 2/3 안내 중복 방지).

### 4. 플로우 변경
- **재분석 처리 블록**(신규): `reanalyze_pending`이 True면 step 분기보다 **먼저** 실행 → `analyze_food_image` 재호출 → vision_result 갱신, recipe_result/confirmed/awaiting 리셋 → step 4로 이동 후 `st.rerun()`. 실패 시 AI 메시지로 안내 후 플래그 해제.
- **Step 1**: 업로더 `label_visibility="collapsed"`, 버튼 "📷 사진 분석하기". 비음식 사진은 `st.warning` 대신 AI 버블 안내 + `render_chat_history()` 후 `st.stop()`. 4MB 초과 메시지 간소화.
- **Step 2**: skip 버튼 "건너뛰기 →"(full-width 아님, pill 스타일), 안내 문구 ref3 톤으로 변경. user 메시지 "건너뛰기"로 통일.
- **Step 3**: 직전 인분 선택 확인 문구("알겠어요! N인분으로 준비할게요") 추가. skip/입력 처리 동일 패턴.
- **Step 4 버튼 분기 재구성**: 기존 2분기(확정/수정 → 2버튼) → 3분기.
  - confirmed: "🔄 처음부터 다시 시작" 단일 버튼.
  - awaiting: 수정 요청 chat_input.
  - default: **3컬럼** — "✅ 레시피 확정" / "✏️ 수정 요청" / "🔍 이미지 재분석"(신규, `reanalyze_pending=True` 세팅).
- step >= 2일 때만 업로드 이미지 expander 노출(`step >= 2 and image_bytes`).

## 파이프라인 스키마 의존 (02_pipeline_changes.md 대조)
UI는 모두 `result.get("field", default)` 패턴으로 접근. 사용 필드:
- vision_result: `is_food`, `non_food_reason`, `dish_name`, `ingredients`(list)
- recipe: `dish_name`, `introduction`, `cooking_time`, `difficulty`(easy/medium/hard), `servings`, `ingredients`(str 또는 {name,amount}), `steps`(list), `missing_ingredients`(list)
스키마 필드가 누락/변경돼도 기본값으로 안전 렌더(빈 카드/"-"/"재료 정보 없음").

## QA 테스트 포인트 (qa-reviewer 참조)
1. **헤더 렌더링**: 상단 sticky 헤더(아바타/이름/상태점) 표시.
2. **버블 스타일**: AI 회색 좌측 / USER 파랑 우측 정렬 확인.
3. **Step 1 비음식 처리**: 음식 아닌 사진 업로드 시 AI 버블 안내 + 흐름 중단(에러 박스 아님).
4. **Step 1 4MB 초과**: `is_within_groq_base64_request_limit` False 시 에러 + stop.
5. **인분 파싱**: "3명" 등 자유 입력 → `parse_servings`, 빈 입력/건너뛰기 → None.
6. **재분석 신규 플로우**: step 4에서 "🔍 이미지 재분석" → 동일 이미지 재분석 → "재분석 완료" 메시지 → 동일 servings/extra로 레시피 재생성. recipe_confirmed/awaiting 리셋 확인.
7. **수정 요청**: extra_requests 누적("기존 / 신규") 후 재생성.
8. **확정 저장**: `save_recipe` 경로 표시 + `missing_ingredients` 있으면 네이버 쇼핑 링크(녹색 pill, `target="_blank"`, URL escape).
9. **처음부터 다시**: `reset_all`로 모든 상태(신규 reanalyze_pending 포함) 초기화.
10. **add_ai_message 중복 방지**: step 2/3 재렌더 시 안내 메시지 중복 없음.
11. **HTML 이스케이프**: dish_name/재료/단계/경로/쇼핑 URL 모두 escape — XSS 안전.

## 호환성
- 사용 API: `st.chat_input`, `st.columns`, `st.file_uploader(label_visibility=...)`, `use_container_width` — Streamlit 1.26+ 필요. `requirements.txt` 버전과 대조 권장.
- `py_compile` / AST 파싱 통과 확인.
