# 04 QA Report — 채팅 UI 전면 교체 검토

대상: `C:\research\food_agent\src\main.py`
검토일: 2026-05-30
판정: **통과 (PASS) — CRITICAL/HIGH 이슈 없음.** LOW 4건, 개선 권고 다수.

---

## 요약

| 심각도 | 건수 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 4 |

`python -m py_compile` 통과. 8개 체크리스트 항목 전부 충족. 채팅 플로우 상태머신, XSS 이스케이프, 파싱 실패 처리, 인분/수정 누적 로직 모두 정상.

---

## 1. 문법 및 구조 — 통과

- `python -m py_compile src/main.py` → 성공.
- `st.set_page_config` 단 1회 호출 (L358). 구 UI 호출(L21)은 주석 처리됨.
- `import html` 존재 (L2).

## 2. session_state — 통과

- 10개 키 모두 `SESSION_DEFAULTS`에 정의 (L483-494): step, image_bytes, mime_type, vision_result, servings, extra_requests, recipe_result, chat_history, recipe_confirmed, awaiting_revision.
- `chat_history` 기본값 `[]`. `init_session_state`(L497-501)가 `[] if isinstance(val, list) else val`로 매 init마다 새 list 생성 → mutable default 공유 버그 없음.
- `reset_all`(L540-554)이 10개 키 모두 초기화. 동일하게 list는 새 객체 할당.

## 3. 채팅 히스토리 — 통과

- `render_chat_history`(L579) 존재.
- AI 버블(L587)은 raw HTML 허용, USER 버블(L599)은 `html.escape()` 적용 → XSS 차단 정상.
- `add_ai_message`(L566-571) 직전 AI 메시지와 content 동일 시 skip하는 중복 방지 로직 존재. rerun 반복 시 동일 안내 중복 누적 방지됨.

## 4. 레시피 카드 HTML — 통과

- `build_recipe_card_html`(L605)에서 dish_name, introduction, cooking_time, difficulty_kor, servings, ingredient, step_text 모두 `html.escape()` 처리.
- `fmt_ingredient`(L557-563): dict이면 name/amount 조합, 그 외 `str(ing)` fallback. 문자열 배열 스키마와 호환.
- difficulty → 한국어 변환: `DIFFICULTY_LABELS`(L508) "easy"→"쉬움" 등. 미정의 값은 원문 또는 "-" fallback.

## 5. 파이프라인 호출 — 통과

- `save_recipe`(L851) 반환값 `saved_path`를 받아 확정 메시지에 표시(L855). 반환값 사용 확인.
- `build_naver_shopping_url`(L862): **올바른 방향** — raw `item`을 builder에 전달하고 내부에서 `quote()`(L342)로 URL 인코딩. 표시 텍스트는 별도로 `html.escape(str(item))`(L865). URL에 escape된 문자열을 넣는 역방향 버그 없음.
- `generate_recipe` 재호출 시 `extra_requests` 누적: 수정 입력 시 `f"{existing} / {cleaned}"`(L898)로 기존 요청에 이어붙임. 누적 정상.

## 6. 확정/수정 플로우 — 통과

- 확정(L848): `save_recipe` → missing_ingredients 쇼핑 링크 생성 → `recipe_confirmed = True`(L870).
- 수정(L873): `awaiting_revision = True`(L880) → 입력 대기 분기로 전환.
- 수정 입력(L890-904): extra_requests 누적 → `recipe_result = None`(L902) → `awaiting_revision = False`(L903) → rerun.
- 재생성 후: step은 4 유지, `recipe_result is None`이므로 자동 재생성(L814) 후 `recipe_confirmed`/`awaiting_revision` 모두 False 상태로 복귀 → 확정/수정 버튼 분기(L842) 재진입 가능. 루프 정상.

## 7. st.chat_input 사용 — 통과

- step별 가드(`if step == N:`) + 각 step 끝 `st.stop()`(L742, L777, L808)으로 동시 렌더링 차단.
- Step 4는 `st.stop()`이 없으나 `chat_input`은 `awaiting_revision` 분기(L890-891)에서만 조건부 렌더. 한 rerun에 chat_input 1개만 존재 보장.

## 8. 재료 형식 — 통과

- `build_recipe_prompt`(L174, L189) ingredients 스키마가 문자열 배열 `["닭고기(200g)", "간장(2큰술)"]` 형식 명시.
- UI는 `fmt_ingredient()`(L623)로 렌더 — 문자열이면 그대로, 혹시 dict가 와도 fallback 처리.

---

## LOW 이슈 (선택 개선)

### [LOW-1] 쇼핑 링크 href에 url 미이스케이프 — L864
`f'<a href="{url}" ...>'`에서 `url`이 attribute 컨텍스트로 직접 삽입됨. `build_naver_shopping_url`이 `quote()`로 query 값을 percent-encode하고 base URL이 고정이라 실제 악용 경로는 없음. 방어적으로 `html.escape(url, quote=True)`를 적용하면 더 견고함.

### [LOW-2] Step 4에 명시적 `st.stop()` 부재 — L812~905
다른 step과 달리 Step 4 끝에 `st.stop()`이 없다. 현재는 마지막 블록이라 동작상 문제 없으나, 추후 Step 5 등 하위 블록 추가 시 의도치 않은 렌더가 발생할 수 있다. 일관성을 위해 블록 말미에 `st.stop()` 추가 권고.

### [LOW-3] Step 4 비-수정 분기에서 chat_input 없음으로 인한 입력 차단은 정상이나, 확정 후 재시작 외 경로 부재 — L884-887
확정 완료(`recipe_confirmed`) 상태에서는 "처음부터 다시"만 가능. 의도된 설계이면 무방. (정보성)

### [LOW-4] `parse_servings` 한국어 수사 미지원 — L199-218
"세 명", "다섯 인분" 등 한글 수사는 `\d+` 미매치로 None 처리되어 기본값 2인분으로 폴백. 의도된 보수적 동작(주석에 명시)이나, UX상 한글 수사 매핑 추가를 고려할 수 있음.

---

## 경계면 정합성 (pipeline ↔ UI)

vision_result 키(is_food, non_food_reason, dish_name, ingredients, characteristics)와 recipe 키(dish_name, introduction, cooking_time, difficulty, servings, ingredients, steps, missing_ingredients) 모두 UI의 `.get()` 호출과 필드명 일치. silent key mismatch 없음.

## 프롬프트 인젝션 / f-string

- `build_recipe_prompt`의 JSON 스키마 블록은 `{{ }}`로 정확히 이스케이프(L183-192), `{servings}` 등 의도된 보간만 단일 중괄호.
- `extra_requests`, `source_md`, `feedback_md`가 프롬프트에 평문 삽입되나, 출력이 `response_format=json_object`로 강제되고 표시 단계에서 전부 `html.escape` 처리되어 화면 인젝션 위험 없음. (모델 레벨 프롬프트 인젝션은 별도 정책 영역.)

## 의존성

`requirements.txt`에 streamlit, groq, python-dotenv 존재. 신규 import(html, base64, json, mimetypes, re, time, urllib, datetime)는 모두 표준 라이브러리로 추가 의존성 불필요.
