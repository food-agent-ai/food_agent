from pathlib import Path
import re
import json


SECTION_MAP = {
    "0. 사용자 특성": "user_preferences",
    "1. 재료": "ingredients",
    "2. 조리 도구": "tools",
    "3. 조리 기기": "appliances",
}


COUNT_UNITS = {"개", "알", "장", "봉", "봉지", "팩", "캔", "병", "통", "쪽", "대", "줄", "근"}
WEIGHT_UNITS = {"g", "그램"}
VOLUME_UNITS = {"ml", "mL", "밀리리터"}
AMOUNT_WORDS = {"조금", "약간", "적당량", "한꼬집", "소량"}


def _clean_bullet(line: str) -> str:
    line = line.strip()

    # markdown separator 제거
    if re.fullmatch(r"-{3,}", line):
        return ""

    if not line.startswith("-"):
        return ""

    return line[1:].strip()

def _extract_input_items(lines: list[str]) -> list[str]:
    items = []
    in_input = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("입력:"):
            in_input = True
            continue

        if stripped.startswith("예시:"):
            in_input = False
            continue

        if in_input:
            item = _clean_bullet(stripped)
            if item:
                items.append(item)

    return items


def _parse_ingredient(raw: str) -> dict:
    raw = raw.strip()

    # 예: 설탕 500g, 간장 100ml, 양파 5개
    match = re.match(r"^(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z가-힣]+)$", raw)

    if match:
        name, quantity, original_unit = match.groups()
        quantity = float(quantity)

        if quantity.is_integer():
            quantity = int(quantity)

        if original_unit in WEIGHT_UNITS:
            unit = "g"
        elif original_unit in VOLUME_UNITS:
            unit = "ml"
        elif original_unit in COUNT_UNITS:
            unit = "count"
        else:
            unit = "unknown"

        return {
            "name": name.strip(),
            "quantity": quantity,
            "unit": unit,
            "original_unit": original_unit,
            "amount_text": None,
            "raw": raw,
        }

    # 예: 간장 조금
    parts = raw.split()
    if len(parts) >= 2 and parts[-1] in AMOUNT_WORDS:
        return {
            "name": " ".join(parts[:-1]).strip(),
            "quantity": None,
            "unit": None,
            "original_unit": None,
            "amount_text": parts[-1],
            "raw": raw,
        }

    # 예: 설탕
    return {
        "name": raw,
        "quantity": None,
        "unit": None,
        "original_unit": None,
        "amount_text": None,
        "raw": raw,
    }


def parse_source_md(source_path: str | Path) -> dict:
    source_path = Path(source_path)
    text = source_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = {
        "user_preferences": [],
        "ingredients": [],
        "tools": [],
        "appliances": [],
    }

    current_section = None
    section_lines = []

    def flush_section():
        if current_section is None:
            return

        key = SECTION_MAP.get(current_section)
        if key is None:
            return

        items = _extract_input_items(section_lines)

        if key == "ingredients":
            result[key] = [_parse_ingredient(item) for item in items]
        else:
            result[key] = items

    for line in lines:
        if line.startswith("## "):
            flush_section()
            current_section = line.replace("##", "").strip()
            section_lines = []
        else:
            section_lines.append(line)

    flush_section()
    return result


def source_md_to_json(
    source_path: str | Path = "Source.md",
    output_path: str | Path = "source.json",
) -> dict:
    data = parse_source_md(source_path)

    output_path = Path(output_path)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return data

if __name__ == "__main__":
    data = source_md_to_json(
        source_path="../Source.md",
        output_path="../source.json",
    )

    print(json.dumps(data, ensure_ascii=False, indent=2))