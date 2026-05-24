"""
부족한 재료 추출 

[입력]
  1) required  : LLM이 "이 요리에 필요하다"고 준 재료 목록 (IngredientItem)
  2) Source.md : 사용자가 집에 있다고 적어 둔 재료 목록

[출력]
  missing    : Source에 없어서 사야 할 재료만 (MissingIngredient)
               → 네이버 API에게 name 을 검색어로 넘기면 됨.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


# ---------------------------------------------------------------------------
# 1. 재료 데이터가 어떻게 "저장"되는지
# ---------------------------------------------------------------------------
#
# (A) Source.md — 사용자 "보유 재료" (파일로 저장)
#
#     data/Source.md 형식 (마크다운):
#
#         # Source
#         ## 재료
#         - 계란
#         - 양파
#         ## 조리도구
#         - 칼
#         ## 조리기기
#         - 가스레인지
#
#     - "## 재료" 아래 `- 항목` 만 부족 재료 비교에 사용합니다.
#     - 조리도구/조리기기 섹션은 읽기만 하고, missing 계산에는 넣지 않습니다.
#
# (B) required — 레시피가 "필요"한 재료 (코드/JSON으로 전달)
#
#      LLM이 넘겨줄 때는 보통 이런 형태입니다:
#
#         IngredientItem(name="김치", amount="200g")
#         IngredientItem(name="돼지고기", amount="100g")
#
#     name  : 재료 이름 (비교의 기준)
#     amount: 분량 (비교에는 쓰지 않음)
#
# (C) missing — 계산 결과 (메모리에만, 필요하면 나중에 log 파일로 저장)
#
#         MissingIngredient(name="김치", amount="200g", reason="재고에 없음")
#


@dataclass
class IngredientItem:
    """레시피 쪽에서 넘어오는 '필요 재료' 한 줄."""

    name: str
    amount: str | None = None


@dataclass
class MissingIngredient:
    """부족해서 구매·검색이 필요한 재료."""

    name: str
    amount: str | None
    reason: str = "재고에 없음"


@dataclass
class UserInventory:
    """Source.md 파싱 결과."""

    ingredients: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    appliances: list[str] = field(default_factory=list)


# Source.md 의 ## 제목 → UserInventory 필드 이름
_SECTION = {
    "재료": "ingredients",
    "조리도구": "tools",
    "조리기기": "appliances",
}


# ---------------------------------------------------------------------------
# 2. Source.md 파싱
# ---------------------------------------------------------------------------


def load_source(path: str | Path) -> UserInventory:
    """
    Source.md 를 한 줄씩 읽어 UserInventory 로 바꿉니다.

    규칙:
      - `## 재료` / `## 조리도구` / `## 조리기기` 를 만나면 "지금 섹션"을 바꿉
      - `- 계란` 처럼 하이픈으로 시작하면 해당 섹션 리스트에 문자열 추가
      - 그 외 줄(빈 줄, # Source 등)은 무시
    """
    path = Path(path)
    inv = UserInventory()
    section: str | None = None  # "ingredients" | "tools" | "appliances"

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            title = line[3:].strip()
            section = _SECTION.get(title)
            continue
        if section and line.startswith("- "):
            getattr(inv, section).append(line[2:].strip())

    return inv


# ---------------------------------------------------------------------------
# 3. 이름 정규화 + 유사 재료 매칭
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """
    비교 전에 이름을 통일합니다. (분량·괄호는 비교에 쓰지 않음)

    예:
      "대파 1대"     → "대파"
      "양파(중)"     → "양파"
      "돼지고기 100g" → "돼지고기"

    처리 순서:
      1) 괄호 (...) 안 내용 삭제
      2) 숫자 + g/ml/개/컵/큰술 등 분량 패턴 삭제
      3) 공백 제거 후 소문자 (영문 재료 대비)
    """
    s = re.sub(r"\([^)]*\)", "", name)
    s = re.sub(r"\d+\s*(g|ml|개|컵|큰술|작은술|줌)?", "", s, flags=re.I)
    return re.sub(r"\s+", "", s.strip().lower())


def _has_ingredient(recipe_key: str, owned_keys: set[str]) -> bool:
    """
    레시피 재료(recipe_key)가 집에 있는지 판단합니다.

    ① 완전 일치
       recipe_key == owned_key
       예: "두부" in {"두부", "양파"} → 있음

    ② 부분 문자열 포함 (유사·상위/하위 이름)
       recipe_key 가 owned 안에 포함되거나, 그 반대
       예: recipe "양파"  , owned "붉은양파" → "양파" in "붉은양파" → 있음
       예: recipe "붉은양파", owned "양파"   → "양파" in "붉은양파" → 있음

    주의 (프로토타입 한계):
      - "김치" vs "김치전" 처럼 포함만 겹치는 다른 재료는
        현재 "있음"으로 출력됨 → 보완필요
    """
    if recipe_key in owned_keys:
        return True
    return any(recipe_key in o or o in recipe_key for o in owned_keys)


# ---------------------------------------------------------------------------
# 4. 부족 재료 추출 (핵심)
# ---------------------------------------------------------------------------


def find_missing(
    required: list[IngredientItem],
    inventory: UserInventory,
) -> list[MissingIngredient]:
    """
    required 를 하나씩 보고, Source 재료에 없으면 missing 에 넣습니다.

    흐름:
      owned = Source 재료 이름들을 normalize 한 집합
      for 각 필요 재료:
          key = normalize(재료.name)
          _has_ingredient(key, owned) 이면 스킵
          아니면 MissingIngredient 로 추가 (원래 name/amount 유지)
    """
    owned = {normalize_name(x) for x in inventory.ingredients}
    missing: list[MissingIngredient] = []

    for item in required:
        key = normalize_name(item.name)
        if not key:
            continue
        if _has_ingredient(key, owned):
            continue
        missing.append(
            MissingIngredient(name=item.name, amount=item.amount)
        )

    return missing


def missing_from_source(
    required: list[IngredientItem],
    source_path: str | Path,
) -> list[MissingIngredient]:
    """Source.md 경로만 넘기면 load_source + find_missing 한 번에 실행."""
    return find_missing(required, load_source(source_path))