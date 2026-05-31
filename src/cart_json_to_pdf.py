# 이 파일은 cart/json 에 있는 모든 레시피를 읽고 
# 사용자가 보기 편하도록 html를 거쳐
# 아래와 같은 pdf 형식으로 저장한다.

"""
오이 계란 샌드위치

요약
오이와 계란을 활용한 간단한 샌드위치

기본 정보
- 인분: 1인분
- 조리 시간: 15분
- 난이도: easy

필요한 재료
- 식빵 2개
- 오이 1개
- 계란 2알
- 마요네즈 2큰술

현재 있는 재료
- 식빵: 필요 2개 / 보유 10개
- 오이: 필요 1개 / 보유량 모름
- 계란: 필요 2알 / 보유 2알

없는 재료
- 마요네즈 2큰술

조리 도구
칼, 도마, 볼, 숟가락

조리 기기
가스레인지

조리 순서
1. 계란을 삶아 껍질을 벗긴 뒤 볼에 넣고 으깬다.
2. 오이를 얇게 썬다.
3. 으깬 계란에 마요네즈를 넣고 섞는다.
4. 식빵 위에 오이와 계란 속을 올린다.
5. 다른 식빵으로 덮어 샌드위치를 완성한다.
"""

from pathlib import Path
import argparse
import html
import json
import shutil
import subprocess


BASE_DIR = Path(__file__).resolve().parents[1]
CART_DIR = BASE_DIR / "cart"
JSON_DIR = CART_DIR / "json"
HTML_DIR = CART_DIR / "html"
PDF_DIR = CART_DIR / "pdf"


def _output_path_for(json_path, output_type):
    json_path = Path(json_path)

    if json_path.parent.name == "json":
        return json_path.parent.parent / output_type / f"{json_path.stem}.{output_type}"

    return CART_DIR / output_type / f"{json_path.stem}.{output_type}"


def _pdf_path_for_html(html_path):
    html_path = Path(html_path)

    if html_path.parent.name == "html":
        return html_path.parent.parent / "pdf" / f"{html_path.stem}.pdf"

    return PDF_DIR / f"{html_path.stem}.pdf"


def _text(value, default="-"):
    if value is None or value == "":
        return default
    return str(value)


def _escape(value):
    return html.escape(_text(value), quote=True)


def _ingredient_text(item):
    name = _text(item.get("name"), "")
    amount = _text(item.get("amount"), "")
    return f"{name} {amount}".strip()


def _render_list(items):
    if not items:
        return "<p class=\"empty\">없음</p>"

    rows = []
    for item in items:
        rows.append(f"<li>{_escape(item)}</li>")
    return "<ul>" + "\n".join(rows) + "</ul>"


def _render_ingredient_list(items):
    if not items:
        return "<p class=\"empty\">없음</p>"

    rows = []
    for item in items:
        rows.append(f"<li>{_escape(_ingredient_text(item))}</li>")
    return "<ul>" + "\n".join(rows) + "</ul>"


def _render_available_ingredients(items):
    if not items:
        return "<p class=\"empty\">없음</p>"

    rows = []
    for item in items:
        name = _escape(item.get("name"))
        required = _escape(item.get("required_amount"))
        current = _escape(item.get("current_amount"),) if item.get("current_amount") else "보유량 모름"
        rows.append(f"<li><strong>{name}</strong>: 필요 {required} / 보유 {current}</li>")
    return "<ul>" + "\n".join(rows) + "</ul>"


def _render_steps(steps):
    if not steps:
        return "<p class=\"empty\">없음</p>"

    rows = []
    for step in steps:
        rows.append(f"<li>{_escape(step)}</li>")
    return "<ol>" + "\n".join(rows) + "</ol>"


def cart_json_to_html_text(data):
    recipe = data.get("recipe", {})
    ingredient_check = data.get("ingredient_check", {})

    dish_name = _escape(data.get("dish_name", "레시피"))
    summary = _escape(data.get("summary", ""))
    servings = _escape(data.get("servings", recipe.get("servings", "-")))
    cooking_time = _escape(recipe.get("cooking_time", "-"))
    difficulty = _escape(recipe.get("difficulty", "-"))

    ingredients = _render_ingredient_list(recipe.get("ingredients", []))
    available = _render_available_ingredients(ingredient_check.get("available_ingredients", []))
    missing = _render_ingredient_list(ingredient_check.get("missing_ingredients", []))
    optional = _render_ingredient_list(ingredient_check.get("optional_ingredients", []))
    tools = _render_list(recipe.get("cooking_tools", []))
    equipment = _render_list(recipe.get("cooking_equipment", []))
    steps = _render_steps(recipe.get("steps", []))

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{dish_name}</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm;
    }}

    body {{
      color: #202124;
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
        "Malgun Gothic", "Noto Sans KR", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.65;
      margin: 0;
    }}

    h1 {{
      border-bottom: 2px solid #202124;
      font-size: 28px;
      line-height: 1.25;
      margin: 0 0 12px;
      padding-bottom: 12px;
    }}

    h2 {{
      font-size: 17px;
      margin: 24px 0 8px;
    }}

    p {{
      margin: 0;
    }}

    ul, ol {{
      margin: 0;
      padding-left: 22px;
    }}

    li {{
      margin: 3px 0;
    }}

    .summary {{
      color: #4b5563;
      font-size: 15px;
      margin-bottom: 18px;
    }}

    .meta {{
      border: 1px solid #d8dee4;
      border-radius: 8px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      margin: 18px 0 22px;
      overflow: hidden;
    }}

    .meta div {{
      padding: 10px 12px;
    }}

    .meta div + div {{
      border-left: 1px solid #d8dee4;
    }}

    .label {{
      color: #6b7280;
      display: block;
      font-size: 12px;
      margin-bottom: 2px;
    }}

    .section {{
      break-inside: avoid;
    }}

    .empty {{
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <h1>{dish_name}</h1>
  <p class="summary">{summary}</p>

  <div class="meta">
    <div><span class="label">인분</span>{servings}인분</div>
    <div><span class="label">조리 시간</span>{cooking_time}</div>
    <div><span class="label">난이도</span>{difficulty}</div>
  </div>

  <section class="section">
    <h2>필요한 재료</h2>
    {ingredients}
  </section>

  <section class="section">
    <h2>현재 있는 재료</h2>
    {available}
  </section>

  <section class="section">
    <h2>없는 재료</h2>
    {missing}
  </section>

  <section class="section">
    <h2>선택 재료</h2>
    {optional}
  </section>

  <section class="section">
    <h2>조리 도구</h2>
    {tools}
  </section>

  <section class="section">
    <h2>조리 기기</h2>
    {equipment}
  </section>

  <section>
    <h2>조리 순서</h2>
    {steps}
  </section>
</body>
</html>
"""


def json_to_html_file(json_path, html_path=None):
    json_path = Path(json_path)
    if html_path is None:
        html_path = _output_path_for(json_path, "html")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    html_text = cart_json_to_html_text(data)

    html_path = Path(html_path)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_text, encoding="utf-8")
    return html_path


def _register_korean_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "AppleGothic"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name

    font_paths = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf",
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            return font_name

    return "Helvetica"


def _paragraph(text, style):
    from reportlab.platypus import Paragraph

    escaped = html.escape(_text(text), quote=False).replace("\n", "<br/>")
    return Paragraph(escaped, style)


def _pdf_section(story, title, body_items, styles, ordered=False):
    from reportlab.platypus import Spacer

    story.append(_paragraph(title, styles["section"]))

    if not body_items:
        story.append(_paragraph("없음", styles["body"]))
    else:
        for index, item in enumerate(body_items, start=1):
            prefix = f"{index}. " if ordered else "- "
            story.append(_paragraph(prefix + item, styles["body"]))

    story.append(Spacer(1, 8))


def _cart_data_to_pdf(data, pdf_path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = _register_korean_font()
    recipe = data.get("recipe", {})
    ingredient_check = data.get("ingredient_check", {})

    styles = {
        "title": ParagraphStyle(
            "Title",
            fontName=font_name,
            fontSize=24,
            leading=30,
            spaceAfter=10,
        ),
        "summary": ParagraphStyle(
            "Summary",
            fontName=font_name,
            fontSize=11,
            leading=17,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName=font_name,
            fontSize=15,
            leading=20,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=font_name,
            fontSize=10.5,
            leading=16,
        ),
        "meta": ParagraphStyle(
            "Meta",
            fontName=font_name,
            fontSize=10.5,
            leading=15,
        ),
    }

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story = [
        _paragraph(data.get("dish_name", "레시피"), styles["title"]),
        _paragraph(data.get("summary", ""), styles["summary"]),
    ]

    meta_rows = [
        [
            _paragraph(f"인분\n{_text(data.get('servings', recipe.get('servings')))}인분", styles["meta"]),
            _paragraph(f"조리 시간\n{_text(recipe.get('cooking_time'))}", styles["meta"]),
            _paragraph(f"난이도\n{_text(recipe.get('difficulty'))}", styles["meta"]),
        ]
    ]
    meta_table = Table(meta_rows, colWidths=[52 * mm, 52 * mm, 52 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8dee4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8dee4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 10)])

    ingredients = [_ingredient_text(item) for item in recipe.get("ingredients", [])]
    available = []
    for item in ingredient_check.get("available_ingredients", []):
        current = item.get("current_amount") or "보유량 모름"
        available.append(
            f"{_text(item.get('name'))}: 필요 {_text(item.get('required_amount'))} / 보유 {current}"
        )
    missing = [_ingredient_text(item) for item in ingredient_check.get("missing_ingredients", [])]
    optional = [_ingredient_text(item) for item in ingredient_check.get("optional_ingredients", [])]

    _pdf_section(story, "필요한 재료", ingredients, styles)
    _pdf_section(story, "현재 있는 재료", available, styles)
    _pdf_section(story, "없는 재료", missing, styles)
    _pdf_section(story, "선택 재료", optional, styles)
    _pdf_section(story, "조리 도구", recipe.get("cooking_tools", []), styles)
    _pdf_section(story, "조리 기기", recipe.get("cooking_equipment", []), styles)
    _pdf_section(story, "조리 순서", recipe.get("steps", []), styles, ordered=True)

    doc.build(story)


def json_to_pdf_file(json_path, pdf_path=None):
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return None

    json_path = Path(json_path)
    if pdf_path is None:
        pdf_path = _output_path_for(json_path, "pdf")

    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    _cart_data_to_pdf(data, pdf_path)
    return pdf_path


def _pdf_with_playwright(html_path, pdf_path):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(Path(html_path).resolve().as_uri(), wait_until="networkidle")
        page.pdf(path=str(pdf_path), format="A4", print_background=True)
        browser.close()
    return True


def _pdf_with_weasyprint(html_path, pdf_path):
    try:
        from weasyprint import HTML
    except ImportError:
        return False

    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    return True


def _chrome_paths():
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    return [Path(path) for path in candidates if path and Path(path).exists()]


def _pdf_with_chrome(html_path, pdf_path):
    chrome_paths = _chrome_paths()
    if not chrome_paths:
        return False

    command = [
        str(chrome_paths[0]),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        Path(html_path).resolve().as_uri(),
    ]
    subprocess.run(command, check=True)
    return True


def _pdf_with_cupsfilter(html_path, pdf_path):
    cupsfilter = shutil.which("cupsfilter")
    if not cupsfilter:
        return False

    command = [
        cupsfilter,
        "-m",
        "application/pdf",
        str(Path(html_path).resolve()),
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    Path(pdf_path).write_bytes(result.stdout)
    return True


def html_to_pdf_file(html_path, pdf_path=None):
    html_path = Path(html_path)
    if pdf_path is None:
        pdf_path = _pdf_path_for_html(html_path)

    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    for pdf_maker in (
        _pdf_with_playwright,
        _pdf_with_weasyprint,
        _pdf_with_chrome,
        _pdf_with_cupsfilter,
    ):
        try:
            if pdf_maker(html_path, pdf_path):
                return pdf_path
        except Exception:
            continue

    raise RuntimeError(
        "PDF 생성 도구를 찾지 못했습니다. HTML 파일은 생성되었습니다. "
        "playwright, weasyprint, Chrome, 또는 cupsfilter 중 하나가 필요합니다."
    )


def cart_json_to_pdf(json_path):
    html_path = json_to_html_file(json_path)
    pdf_path = json_to_pdf_file(json_path)

    if pdf_path is None:
        pdf_path = html_to_pdf_file(html_path)

    return html_path, pdf_path


def _target_json_paths(path_text=None):
    if path_text:
        path = Path(path_text)
        if path.is_dir():
            return sorted(path.glob("*.json"))
        return [path]

    return sorted(JSON_DIR.glob("*.json"))


def main():
    parser = argparse.ArgumentParser(description="cart JSON 파일을 HTML/PDF로 변환합니다.")
    parser.add_argument("path", nargs="?", help="변환할 JSON 파일 또는 JSON 폴더")
    args = parser.parse_args()

    json_paths = _target_json_paths(args.path)
    if not json_paths:
        raise FileNotFoundError(f"변환할 JSON 파일이 없습니다: {JSON_DIR}")

    for json_path in json_paths:
        html_path, pdf_path = cart_json_to_pdf(json_path)
        print(f"HTML 저장 완료: {html_path}")
        print(f"PDF 저장 완료: {pdf_path}")


if __name__ == "__main__":
    main()
