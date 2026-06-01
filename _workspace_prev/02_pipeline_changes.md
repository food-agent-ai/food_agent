# 02 Pipeline Changes

## 작업 요약

`src/main.py`의 파이프라인 섹션(`generate_recipe` 정의 직후, `# ═══ UI` 블록 직전)에 두 개의 헬퍼 함수를 추가했다. UI 코드(line 324 이후)는 변경하지 않았다.

## 추가된 함수 시그니처

### 1. `save_recipe(recipe: dict) -> str`

레시피 dict를 `recipes/` 폴더에 타임스탬프가 포함된 JSON 파일로 저장하고, 저장된 파일 경로를 반환한다.

- 파일명 형식: `recipes/{YYYYMMDD_HHMMSS}_{safe_name}.json`
- `safe_name`은 `recipe["dish_name"]`에서 파일명 불가 문자(`\ / : * ? " < > |`)를 제거한 값. 비어있으면 `"recipe"`로 대체.
- `os.makedirs("recipes", exist_ok=True)`로 폴더 자동 생성.
- `json.dump(..., ensure_ascii=False, indent=2)`로 한글이 깨지지 않게 저장.

### 2. `build_naver_shopping_url(ingredient: str) -> str`

재료명을 URL 인코딩하여 네이버 쇼핑 검색 URL을 생성한다.

- 반환 형식: `https://search.shopping.naver.com/search/all?query={encoded}`
- `urllib.parse.quote`로 인코딩.

## import 처리

- `os`, `re`, `json` — 파일 상단에 이미 존재. 재사용.
- `from datetime import datetime` — `save_recipe` 내부 import.
- `from urllib.parse import quote` — `build_naver_shopping_url` 내부 import.
- 중복 import 없음. (스펙 예시의 `save_recipe` 내 `import urllib.parse`는 미사용이라 제거함.)

## 사용 예시

```python
# 레시피 저장
recipe = {
    "dish_name": "김치찌개",
    "ingredients": ["김치", "돼지고기", "두부"],
    "steps": ["..."],
}
path = save_recipe(recipe)  # -> "recipes/20260530_143012_김치찌개.json"

# 재료별 네이버 쇼핑 링크
url = build_naver_shopping_url("돼지고기")
# -> "https://search.shopping.naver.com/search/all?query=%EB%8F%BC%EC%A7%80%EA%B3%A0%EA%B8%B0"
```

## 스키마 의존성 (ui-developer 참고)

- `save_recipe`는 `recipe` dict에서 **`dish_name`** 키만 읽는다(없거나 falsy면 `"recipe"`로 폴백). 그 외 키 구조에 의존하지 않으므로 기존 JSON 스키마 변경 불필요.
- breaking change 없음.

## QA / 테스트 절차 (qa-reviewer 참고)

```python
# save_recipe
assert save_recipe({"dish_name": "테스트요리"}).startswith("recipes/")
assert save_recipe({"dish_name": 'a/b:c*?"<>|'}).endswith("_abc.json")  # 불가문자 제거
assert save_recipe({}).endswith("_recipe.json")                         # dish_name 없음 폴백
assert save_recipe({"dish_name": ""}).endswith("_recipe.json")          # 빈 문자열 폴백

# build_naver_shopping_url
u = build_naver_shopping_url("  마늘 ")
assert u == "https://search.shopping.naver.com/search/all?query=%EB%A7%88%EB%8A%98"  # strip + 인코딩
```

- 구문 검증 완료: `python -c "import ast; ast.parse(...)"` → syntax OK.
