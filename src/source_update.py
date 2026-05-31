# 이 파일은 완료 처리된 레시피의 사용 재료를 기준으로
# source.md/source.json의 보유 재료 수량을 계산해서 업데이트한다.
# g, ml, 개, 알 단위만 자동 차감하고 계산 불가능한 재료는 따로 기록한다.

from datetime import date
from pathlib import Path
import json
import re

from source_md_to_json import source_md_to_json


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_MD_PATH = BASE_DIR / "data" / "source.md"
SOURCE_JSON_PATH = BASE_DIR / "data" / "source.json"
SUPPORTED_UNITS = {"g", "ml", "개", "알"}
AMOUNT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)(g|ml|개|알)$")


def _parse_amount(amount):
    amount = (amount or "").strip()
    match = AMOUNT_PATTERN.match(amount)

    if not match:
        return None

    quantity = float(match.group(1))
    if quantity.is_integer():
        quantity = int(quantity)

    return quantity, match.group(2)


def _format_amount(quantity, unit):
    if isinstance(quantity, float) and quantity.is_integer():
        quantity = int(quantity)
    return f"{quantity}{unit}"


def _is_zero_amount(amount):
    parsed = _parse_amount(amount)
    return parsed is not None and parsed[0] == 0


def _ingredient_line(item):
    name = item.get("name", "").strip()
    amount = item.get("amount", "").strip()

    if amount:
        return f"- {name}({amount})"
    return f"- {name}"


def load_source_data():
    source_md_to_json(SOURCE_MD_PATH, SOURCE_JSON_PATH)
    return json.loads(SOURCE_JSON_PATH.read_text(encoding="utf-8"))


def save_source_data_to_md(source_data):
    today = date.today().isoformat()
    ingredients = [
        item
        for item in source_data.get("ingredients", [])
        if not _is_zero_amount(item.get("amount", ""))
    ]
    user_preferences = source_data.get("user_preferences", [])
    source_data["ingredients"] = ingredients

    ingredient_lines = [_ingredient_line(item) for item in ingredients]
    preference_lines = [f"- {item}" for item in user_preferences]

    text = f"""# 내 주방 정보

최종 갱신일: {today}

---

## 1. 재료

가지고 계신 재료를 자유롭게 적어주세요.
재료명(양) 형식에 맞게 적어주세요.
양을 몰라도 괜찮습니다, 재료명만 적어주세요.
계량 단위는 g, ml로 통일해 주세요.

예시:
- 양파(5개)
- 설탕(500g)
- 설탕
- 간장
- 계란(2알)

입력:
{chr(10).join(ingredient_lines)}

---

## 2. 사용자 특성

레시피 생성 과정에서 요청사항이 있다면 적어주세요.

예시:
- 짠 음식을 싫어해요
- 토마토 알러지가 있어요
- 과일보다는 채소를 좋아해요
- 매운 음식을 좋아해요
- 다이어트 중이에요
- 비건 식단을 선호해요

입력:
{chr(10).join(preference_lines)}
"""

    SOURCE_MD_PATH.write_text(text, encoding="utf-8")
    SOURCE_JSON_PATH.write_text(
        json.dumps(source_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def calculate_source_update(source_data, recipe_data):
    source_ingredients = source_data.get("ingredients", [])
    source_by_name = {item.get("name"): item for item in source_ingredients}
    ingredient_check = recipe_data.get("ingredient_check", {})
    available = ingredient_check.get("available_ingredients", [])
    missing_ingredients = ingredient_check.get("missing_ingredients", [])

    used_ingredients = []
    blocked_ingredients = []
    updated_by_name = {
        item.get("name"): {"name": item.get("name", ""), "amount": item.get("amount", "")}
        for item in source_ingredients
    }

    for item in available:
        name = item.get("name", "").strip()
        required_amount = item.get("required_amount", "").strip()
        source_item = source_by_name.get(name)

        if not source_item:
            blocked_ingredients.append(
                {"name": name, "amount": required_amount, "reason": "source.md에 없는 재료"}
            )
            continue

        current_amount = source_item.get("amount", "").strip()
        current = _parse_amount(current_amount)
        required = _parse_amount(required_amount)

        if not current_amount:
            blocked_ingredients.append(
                {"name": name, "amount": required_amount, "reason": "현재 보유량이 비어 있어 자동 차감 불가"}
            )
            continue

        if not required:
            blocked_ingredients.append(
                {"name": name, "amount": required_amount, "reason": "필요량 단위가 지원되지 않음"}
            )
            continue

        if not current:
            blocked_ingredients.append(
                {"name": name, "amount": current_amount, "reason": "현재 보유량 단위가 지원되지 않음"}
            )
            continue

        current_quantity, current_unit = current
        required_quantity, required_unit = required

        if current_unit != required_unit:
            blocked_ingredients.append(
                {
                    "name": name,
                    "amount": required_amount,
                    "reason": f"단위가 다름: 보유 {current_unit}, 필요 {required_unit}",
                }
            )
            continue

        if current_quantity < required_quantity:
            blocked_ingredients.append(
                {
                    "name": name,
                    "amount": required_amount,
                    "reason": f"보유량 부족: 보유 {current_amount}",
                }
            )
            continue

        after_quantity = current_quantity - required_quantity
        after_amount = _format_amount(after_quantity, current_unit)
        used_ingredients.append(
            {
                "name": name,
                "amount": required_amount,
                "before": current_amount,
                "after": "삭제됨" if after_quantity == 0 else after_amount,
            }
        )

        updated_by_name[name]["amount"] = after_amount

    updated_ingredients = []
    for item in source_ingredients:
        name = item.get("name")
        updated_item = updated_by_name.get(name, item)
        if _is_zero_amount(updated_item.get("amount", "")):
            continue
        updated_ingredients.append(updated_item)

    updated_source = {
        **source_data,
        "ingredients": updated_ingredients,
    }

    return {
        "updated_source": updated_source,
        "used_ingredients": used_ingredients,
        "blocked_ingredients": blocked_ingredients,
        "missing_ingredients": missing_ingredients,
    }


def apply_source_update(recipe_data):
    source_data = load_source_data()
    result = calculate_source_update(source_data, recipe_data)
    save_source_data_to_md(result["updated_source"])
    return result
