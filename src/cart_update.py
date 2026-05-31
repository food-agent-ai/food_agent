# 이 파일은 cart/json 폴더의 레시피 JSON을 읽고
# 장바구니에 남아 있는 레시피 목록을 찾거나
# 완료 처리된 레시피를 completed 폴더에 복사본으로 저장한다.

from datetime import date
from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[1]
CART_DIR = BASE_DIR / "cart"
COMPLETED_DIR = BASE_DIR / "completed"
CART_JSON_DIR = CART_DIR / "json"


def load_cart_item(json_path):
    json_path = Path(json_path)
    return json.loads(json_path.read_text(encoding="utf-8"))


def save_cart_item(json_path, data):
    json_path = Path(json_path)
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_pending_cart_items(cart_dir=CART_JSON_DIR):
    cart_dir = Path(cart_dir)
    items = []

    for json_path in sorted(cart_dir.glob("*.json")):
        data = load_cart_item(json_path)
        items.append(
            {
                "path": json_path,
                "dish_name": data.get("dish_name", json_path.stem),
                "summary": data.get("summary", ""),
            }
        )

    return items


def completed_json_path_for(json_path):
    json_path = Path(json_path)
    return COMPLETED_DIR / "json" / json_path.name


def save_completed_copy(json_path, completion_result):
    data = load_cart_item(json_path)
    data.pop("status", None)
    data["completed_at"] = date.today().isoformat()
    data["completion_result"] = {
        "used_ingredients": completion_result.get("used_ingredients", []),
        "blocked_ingredients": completion_result.get("blocked_ingredients", []),
        "missing_ingredients": completion_result.get("missing_ingredients", []),
    }
    completed_json_path = completed_json_path_for(json_path)
    save_cart_item(completed_json_path, data)
    return completed_json_path
