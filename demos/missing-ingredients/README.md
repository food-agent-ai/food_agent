# FoodRecipeDemo — 부족 재료 추출

`data/Source.md`와 레시피 필요 재료를 비교해 **없는 것만** 반환합니다.

## 파일 · 실행

```text
data/Source.md   # 보유 재료
src/missing.py   # 비교 로직
demo.py          # 예시
```

```bash
python demo.py
```

Python 3.10+, 추가 패키지 없음.

---

## LLM → `list[IngredientItem]`

```python
from src.missing import IngredientItem, missing_from_source

required = [
    IngredientItem(name="김치", amount="200g"),
    IngredientItem(name="대파", amount="1대"),
]
missing = missing_from_source(required, "data/Source.md")
```

**권장 JSON** (프롬프트에서 이 형식만 출력):

```json
{
  "ingredients": [
    { "name": "김치", "amount": "200g" },
    { "name": "대파" }
  ]
}
```

| 필드 | 설명 |
|------|------|
| `name` | 필수. 비교는 이름만 (`amount`는 판정에 미사용) |
| `amount` | 선택. UI·검색 안내용 |

**주의:** `name`과 `amount` 분리 · 조리도구/기기는 넣지 않음 ·

**JSON 변환:**

```python
required = [IngredientItem(i["name"].strip(), i.get("amount")) for i in json.loads(text)["ingredients"]]
```

**출력 → API:** `MissingIngredient.name`으로 검색, `amount`는 표시용.

---

## 파싱 · 비교

**Source.md** — `## 재료` / `## 조리도구` / `## 조리기기` 아래 `- 항목`만 읽음. **부족 비교는 `## 재료`만** 사용.

**필요 재료** — LLM이 JSON/코드로 `IngredientItem` 리스트 전달 (파일 파싱 없음).

**이름 맞추기** — `normalize_name`: 괄호·분량·공백 제거 후 비교. 완전 일치 또는 포함(`양파`↔`붉은양파`) 시 재료 있다고 판정.

---

## 연동

| 담당 | 입·출력 |
|------|---------|
| LLM | `list[IngredientItem]` |
| missing | `missing_from_source(...)` → `list[MissingIngredient]` |
| API | `MissingIngredient.name` 검색 |

상세: `src/missing.py`