# 02_pipeline_changes — 파이프라인 변경 요약

날짜: 2026-06-01
대상 파일: `src/main.py`
브랜치: `APIprompt`

---

## 작업 1 (HIGH): `get_ai_client()` 불필요한 `client=` 할당 제거

`get_ai_client()`는 Gemini 클라이언트를 `genai.configure()`로 전역 설정만 수행하고 `None`을 반환한다(정의: `src/main.py:1783`). 따라서 반환값을 `client` 변수에 할당하는 것은 의미가 없고, 어디서도 `client`를 사용하지 않는다.

`render_chat_view()` 내부의 아래 3곳에서 `client = get_ai_client()` → `get_ai_client()` 로 교체:

| 위치 | 컨텍스트 |
|------|----------|
| `reanalyze_pending` 처리 직후 | 이미지 재분석 직전 |
| 파일 업로드 후 `mime_type` 저장 직후 | 최초 이미지 분석 직전 (step 1) |
| `recipe_result is None` 분기 | 레시피 생성 직전 (step 4) |

- `extract_and_save_feedback` 호출 직전(기존 `get_ai_client()`)은 이미 할당 없는 형태였으므로 그대로 유지.
- 반환값 `client`를 실제로 사용하는 곳은 없음(확인 완료). 동작 변화 없음(side-effect인 `genai.configure()` 호출은 그대로 유지됨).

## 작업 2 (LOW): `_NAVER_STOP_WORDS` 비식품 키워드 추가

네이버 쇼핑 결과 필터링용 stop word 목록(`get_shopping_items()`에서 제목에 포함 시 제외)에 비식품 카테고리 키워드 추가:

```
"의류", "패션", "가방", "신발", "악세서리", "귀걸이", "목걸이",
"인테리어", "가구", "조명", "벽지", "침구",
"전자", "가전", "핸드폰", "컴퓨터", "노트북",
"다이어리", "문구", "팬시", "장난감", "완구",
```

효과: `build_shopping_html()` / `get_shopping_items()` 검색 결과에서 위 키워드가 제목에 포함된 비식품 상품을 부분 문자열 매칭으로 추가 제외한다.

---

## 스키마 영향 / breaking change

- 없음. JSON 출력 스키마(`build_vision_prompt`, `build_recipe_prompt`), 프롬프트, 모델 상수, 재시도 로직 모두 변경하지 않았다.
- 다운스트림(`ingredient_extraction`, `md_export`, `calculate_source_update` 등)이 참조하는 필드 변경 없음 → ui-developer 협의 불필요.

## 검증

- `python -m py_compile src/main.py` → 통과 (COMPILE_OK).
- `client = get_ai_client()` 패턴 grep → 매치 0건 (잔여 할당 없음).

## QA 참고 (수동 회귀)

1. 이미지 업로드 → 분석 진행 정상(step 1) 확인.
2. 레시피 생성(step 4) 정상 확인.
3. 재분석(reanalyze) 버튼 정상 확인.
4. `missing_ingredients`가 있는 레시피에서 네이버 쇼핑 섹션에 의류/가전/문구 등 비식품 상품이 노출되지 않는지 확인.
