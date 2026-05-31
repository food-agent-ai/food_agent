# 이 파일은 사용자가 장바구니 레시피 중 하나를 골라
# "요리 완료" 처리를 할 수 있게 하는 실행용 CLI 파일이다.
# 완료 시 source.md/source.json을 업데이트하고 completed 폴더에 완료 기록을 추가한다.

from cart_json_to_pdf import cart_json_to_pdf
from cart_update import (
    list_pending_cart_items,
    load_cart_item,
    save_completed_copy,
)
from source_update import calculate_source_update, load_source_data, save_source_data_to_md


def _print_ingredient_changes(result):
    used = result.get("used_ingredients", [])
    blocked = result.get("blocked_ingredients", [])
    missing = result.get("missing_ingredients", [])

    print("\n자동 차감 가능:")
    if used:
        for item in used:
            print(f"- {item['name']} {item['amount']}: {item['before']} -> {item['after']}")
    else:
        print("- 없음")

    print("\n자동 차감 불가:")
    if blocked:
        for item in blocked:
            print(f"- {item['name']} {item.get('amount', '')}: {item['reason']}")
    else:
        print("- 없음")

    print("\n추가 준비 필요 재료:")
    if missing:
        for item in missing:
            amount = item.get("amount", "")
            print(f"- {item.get('name', '')} {amount}".strip())
    else:
        print("- 없음")


def _select_cart_item():
    items = list_pending_cart_items()

    if not items:
        print("완료 처리할 장바구니 레시피가 없습니다.")
        return None

    print("완료 처리할 레시피를 선택하세요.\n")
    for index, item in enumerate(items, start=1):
        print(f"{index}. {item['dish_name']} - {item['path'].name}")

    while True:
        raw_choice = input("\n번호 입력: ").strip()

        if not raw_choice.isdigit():
            print("숫자를 입력해주세요.")
            continue

        choice = int(raw_choice)
        if 1 <= choice <= len(items):
            return items[choice - 1]["path"]

        print("목록에 있는 번호를 입력해주세요.")


def complete_recipe():
    json_path = _select_cart_item()
    if json_path is None:
        return

    recipe_data = load_cart_item(json_path)
    source_data = load_source_data()
    result = calculate_source_update(source_data, recipe_data)

    _print_ingredient_changes(result)

    confirm = input("\n이 레시피를 완료 처리할까요? (y/n): ").strip().lower()
    if confirm != "y":
        print("완료 처리를 취소했습니다.")
        return

    save_source_data_to_md(result["updated_source"])
    completed_json_path = save_completed_copy(json_path, result)
    html_path, pdf_path = cart_json_to_pdf(completed_json_path)

    print("\nsource.md 업데이트 완료")
    print(f"{json_path.name} 완료 처리 완료")
    print(f"cart 원본 유지: {json_path}")
    print(f"completed JSON 추가 완료: {completed_json_path}")
    print(f"completed HTML 추가 완료: {html_path}")
    print(f"completed PDF 추가 완료: {pdf_path}")

    if result.get("blocked_ingredients") or result.get("missing_ingredients"):
        print("\n자동으로 처리하지 못한 재료가 있습니다.")
        print("- 수량이 없는 재료는 자동 차감하지 않았습니다.")
        print("- 없는 재료를 새로 준비했다면 source.md에 직접 추가해주세요.")


if __name__ == "__main__":
    complete_recipe()
