"""
부족 재료 데모 실행 파일.

서진/LLM이 넘겨줄 "필요 재료" 목록을 예시로 넣고,
data/Source.md 와 비교해 부족한 것만 출력합니다.
"""

from pathlib import Path

from src.missing import IngredientItem, missing_from_source

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "Source.md"

# 실제 연동 시: VLM/레시피 모듈이 만든 list[IngredientItem] 을 여기에 연결
REQUIRED_EXAMPLE = [
    IngredientItem("김치", "200g"),
    IngredientItem("돼지고기", "100g"),
    IngredientItem("두부", "1/2모"),
    IngredientItem("대파", "1대"),
    IngredientItem("고춧가루", "1큰술"),
]


def main() -> None:
    missing = missing_from_source(REQUIRED_EXAMPLE, SOURCE)

    print("=== 필요 재료 (입력 예시) ===")
    for r in REQUIRED_EXAMPLE:
        print(f"  - {r.name} {r.amount or ''}".strip())

    print("\n=== Source.md 재료 ===")
    from src.missing import load_source

    for name in load_source(SOURCE).ingredients:
        print(f"  - {name}")

    print("\n=== 부족 재료 (구매·검색 대상) ===")
    if not missing:
        print("  (없음 — 모두 보유)")
    for m in missing:
        print(f"  - {m.name} {m.amount or ''}  ({m.reason})".strip())


if __name__ == "__main__":
    main()