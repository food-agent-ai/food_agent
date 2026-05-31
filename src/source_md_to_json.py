# 이 파일은 source.md 파일을 읽어서
# 섹션(재료/사용자 선호)별로 사용자 입력을 파싱하고
# 최종적으로 아래 형식의 source.json 형태로 저장한다.

"""
{
  "ingredients": [
    {
      "name": "양파",
      "amount": "5개"
    },
    {
      "name": "간장",
      "amount": ""
    },
    {
      "name": "설탕",
      "amount": "500g"
    }
  ],
  "user_preferences": [
    "짠 음식을 싫어해요.",
    "토마토 알러지가 있어요.",
    "매운 음식을 좋아해요."
  ]
}
"""

from pathlib import Path
import json
import re


INGREDIENT_PATTERN = re.compile(r"^(.+?)\((.*?)\)$")
INGREDIENT_WITH_AMOUNT_PATTERN = re.compile(r"^(.+?)\s+(\S+)$")
BASE_DIR = Path(__file__).resolve().parents[1]


def _clean_bullet(line: str) -> str:
    line = line.strip()

    if re.fullmatch(r"-{3,}", line):
        return ""

    if not line.startswith("-"):
        return ""

    return line[1:].strip()


def _get_input_items(section_text: str) -> list[str]:
    items = []
    in_input = False

    for line in section_text.splitlines():
        stripped = line.strip()

        if stripped.startswith("입력:"):
            in_input = True
            continue

        if in_input:
            item = _clean_bullet(stripped)
            if item:
                items.append(item)

    return items


def _split_sections(text: str) -> dict[str, str]:
    sections = {}
    current_title = None
    current_lines = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_title:
                sections[current_title] = "\n".join(current_lines)

            current_title = line.replace("##", "", 1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_title:
        sections[current_title] = "\n".join(current_lines)

    return sections


def _parse_ingredient(raw: str) -> dict[str, str]:
    match = INGREDIENT_PATTERN.match(raw)

    if match:
        name, amount = match.groups()
        return {
            "name": name.strip(),
            "amount": amount.strip(),
        }

    match = INGREDIENT_WITH_AMOUNT_PATTERN.match(raw)

    if match:
        name, amount = match.groups()
        return {
            "name": name.strip(),
            "amount": amount.strip(),
        }

    return {
        "name": raw.strip(),
        "amount": "",
    }


def parse_source_md(source_path) -> dict:
    text = Path(source_path).read_text(encoding="utf-8")
    sections = _split_sections(text)

    ingredient_items = []
    preference_items = []

    for title, body in sections.items():
        if "재료" in title:
            ingredient_items = _get_input_items(body)
        elif "사용자 특성" in title:
            preference_items = _get_input_items(body)

    return {
        "ingredients": [_parse_ingredient(item) for item in ingredient_items],
        "user_preferences": preference_items,
    }


def source_md_to_json(
    source_path=BASE_DIR / "data" / "source.md",
    output_path=BASE_DIR / "data" / "source.json",
) -> dict:
    data = parse_source_md(source_path)
    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    output_path = BASE_DIR / "data" / "source.json"
    data = source_md_to_json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n저장 완료: {output_path}")