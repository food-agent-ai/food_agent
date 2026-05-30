# 03 — UI 변경 요약 (ui-developer)

## 대상
`C:\research\food_agent\src\main.py` — line 348 이후 UI 섹션 전면 교체.
파이프라인 함수(line 1~347)는 미수정.

## 핵심 변경
기존 "스텝 인디케이터 + 폼" UI를 **단일 채팅 타임라인(chat_history) 기반 채팅앱 UI**로 전면 교체.
모든 단계의 메시지가 좌(AI)/우(USER) 버블로 누적 렌더링된다.

## 변경된 CSS / 디자인
- `.stApp` 배경 `#f0f2f5` (연회색)
- 앱 타이틀: 중앙 정렬 `<h2>🍽️ 레시피 AI</h2>`
- `.msg-ai` / `.msg-user` 버블, `.avatar-ai`(🍽️ 그라데이션 아바타)
- `.recipe-card`(흰 카드), `.recipe-meta-item`(메타 뱃지), `.ingredient-item`(재료 뱃지),
  `.step-item`/`.step-num`(번호 원형), `.shopping-link`(네이버 그린 버튼)
- 기존 `.ai-bubble`, `.step-indicator`, `.recipe-step` 클래스 제거됨

## session_state 구조 (신규 키 추가)
```python
SESSION_DEFAULTS = {
    "step": 1, "image_bytes": None, "mime_type": None, "vision_result": None,
    "servings": None, "extra_requests": None, "recipe_result": None,
    "chat_history": [],          # 신규: [{"role":"ai"|"user","content":str}]
    "recipe_confirmed": False,   # 신규
    "awaiting_revision": False,  # 신규
}
```
`init_session_state()`와 `reset_all()` 모두 신규 키 포함. 가변 기본값(list)은 매번 새 객체로 할당.

## 신규/변경 함수 (UI 헬퍼)
| 함수 | 역할 |
|------|------|
| `fmt_ingredient(ing)` | `{"name","amount"}` → `"닭고기(200g)"` 문자열. dict 아니면 str() |
| `add_ai_message(content)` | AI 메시지 추가. 직전 AI 메시지와 중복이면 무시(스텝 재진입 중복 방지) |
| `add_user_message(content)` | USER 메시지 추가 |
| `render_chat_history()` | 전체 히스토리 렌더링. AI는 HTML 그대로, USER는 `html.escape()` |
| `build_recipe_card_html(recipe)` | 레시피 dict → 레시피 카드 HTML(AI 버블 content용) |
| `get_groq_client()` / `handle_api_error()` | 기존 유지 |
| `reset_all()` | 신규 키 포함하도록 갱신 |
- 제거: `ai_bubble()`, `render_step_indicator()`

## 스키마 접근 (pipeline 준수)
- 모든 JSON 필드 접근은 `result.get("field", default)` 패턴 유지.
- ingredients는 `{"name","amount"}` 객체 배열 → `fmt_ingredient()`로 `"재료(단위)"` 변환 후 뱃지 렌더링.
- difficulty 라벨 변환: `DIFFICULTY_LABELS = {"easy":"쉬움","medium":"보통","hard":"어려움"}`.

## 단계별 플로우 (QA 테스트 포인트)
- **Step 1**: 웰컴 AI 버블 → file_uploader(key=`file_uploader_step1`) → "분석하기" 버튼(이미지 없으면 disabled).
  분석 성공 시 USER"(사진 업로드)" + AI 분석 결과(dish + 재료 4개 미리보기) 추가 후 step=2. 끝에서 `st.stop()`.
  - 비음식/JSON 파싱 실패/4MB 초과 → 기존 `st.error`+`st.stop()` 패턴 유지.
- **step>1 공통**: 업로드 이미지가 접힌 expander("📷 업로드한 사진 보기")로 표시.
- **Step 2**: AI 버블 + "건너뛰기" 버튼(key=`skip_servings`) + `st.chat_input` (인분 입력). 빈 전송/건너뛰기 → servings=None. step=3. `st.stop()`.
- **Step 3**: AI 버블 + "건너뛰기"(key=`skip_extra`) + `st.chat_input`. extra_requests 저장, recipe_result=None, step=4. `st.stop()`.
- **Step 4**:
  - recipe_result None → `generate_recipe()` 자동 호출 → 레시피 카드를 AI 버블로 추가 → `st.rerun()`.
  - 미확정·미수정: "✅ 레시피 확정하기"(primary) / "✏️ 수정 요청하기" 2-컬럼.
  - **확정**: `save_recipe()` 저장 → USER"레시피 확정!" + AI 저장 경로(code) + missing_ingredients가 있으면 `build_naver_shopping_url()` 네이버 쇼핑 링크 버블. `recipe_confirmed=True`.
  - **확정 후**: "🔄 처음부터 다시 시작" 버튼 → `reset_all()`.
  - **수정**: USER"수정 요청" + AI 안내 → `awaiting_revision=True` → `st.chat_input("수정 요청을 입력하세요")` → extra_requests에 `" / "` 누적, recipe_result=None → 재생성.

## st.chat_input 규칙 준수
- 단계마다 chat_input은 **조건부로 하나만** 렌더링 (step==2, step==3, step4 수정 대기 시 각각 별개).
- 동일 시점에 2개 이상 노출되지 않음.

## 보안 / 이스케이프
- USER 입력: 렌더링 시 `html.escape()`.
- AI HTML(레시피 카드, 재료/단계 텍스트, dish_name, introduction, saved_path, missing item): 모두 `html.escape()` 후 삽입.
- missing_ingredients의 네이버 URL은 파이프라인 `build_naver_shopping_url()`이 `quote()` 인코딩한 값 사용.

## 호환성
- 설치 Streamlit 1.57.0. `st.chat_input`(1.24+), `st.rerun`(1.27+) 모두 지원. `requirements.txt`는 `streamlit`(버전 미지정)이라 충돌 없음.
- `py_compile` 통과 확인.

## 주의 / 알려진 동작
- chat_input은 항상 페이지 하단 고정(Streamlit 기본). CSS의 `.chat-wrapper`는 정의만 존재(현재 미사용 래퍼) — 향후 컨테이너 래핑 시 활용 가능.
- `add_ai_message` 중복 가드로 step 재실행(rerun) 시 동일 AI 안내 버블이 중복 누적되지 않음.
