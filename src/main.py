import base64
import glob
import html
import json
import mimetypes
import os
import re
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# === 모델/요청 상수 (하드코딩 금지, 항상 이 상수를 참조) ===
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TEXT_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE64_REQUEST_LIMIT_BYTES = 4 * 1024 * 1024

# === Gemini 모델 상수 ===
GEMINI_VISION_MODEL = "gemini-2.5-flash"
GEMINI_TEXT_MODEL = "gemini-2.5-flash"

# === 네이버 쇼핑 API ===
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def _load_config() -> dict:
    if os.path.exists("config.json"):
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    return {"provider": "groq"}


def _get_provider() -> str:
    return _load_config().get("provider", "groq")

# ─── [OLD UI] ui-developer가 4단계 플로우로 교체 예정 (pipeline 작업 범위 외) ───
# st.set_page_config(page_title="음식 사진 레시피 생성기", page_icon="🍽️", layout="centered")
# st.title("🍽️ 음식 사진 레시피 생성기 (Groq Llama 4 Scout)")
# st.write("음식 사진을 업로드하고 **레시피 생성하기** 버튼을 눌러보세요.")

SOURCE_MD_PATH = "source.md"
FEEDBACK_MD_PATH = "feedback.md"
CART_JSON_DIR = "cart/json"
COMPLETED_JSON_DIR = "completed/json"


def load_source_md(path: str = SOURCE_MD_PATH) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    # 재료 섹션이 비어있으면 source 없음으로 처리
    parsed = parse_source_md_to_data(path)
    if not parsed.get("ingredients"):
        return ""
    return text


def load_feedback_md(path: str = FEEDBACK_MD_PATH) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# ─── [OLD UI] 단일 폼 입력. ui-developer가 4단계 session_state 플로우로 교체 예정 ───
# uploaded_file = st.file_uploader(
#     "음식 사진 업로드",
#     type=["jpg", "jpeg", "png", "webp"],
#     accept_multiple_files=False,
# )
#
# if uploaded_file is not None:
#     st.image(uploaded_file, caption="업로드한 이미지", use_container_width=True)
#
# st.subheader("사용자 설정")
# servings = st.number_input("몇 인분으로 만들까요?", min_value=1, max_value=20, value=1, step=1)
# user_preference_text = st.text_area(
#     "추가 선호사항 (선택)",
#     placeholder="예: 빨간 소스는 달지 않은 케첩 베이스, 사진에 없는 재료는 최대한 제외, 10분 내 조리 희망",
#     help="첨부 파일 외에 매번 텍스트 선호사항을 함께 전달할 수 있습니다.",
# )
#
# source_md_content = load_source_md()
# if source_md_content:
#     st.caption(f"source.md 로드 완료 ({len(source_md_content)}자)")
# else:
#     st.caption("source.md가 없어 기본 설정만 사용합니다.")
#
# feedback_md_content = load_feedback_md()
# if feedback_md_content:
#     st.caption(f"feedback.md 기억 로드 완료 ({len(feedback_md_content)}자)")

# ───────────────────────── 프롬프트 빌더 ─────────────────────────


def build_vision_prompt() -> str:
    """Call 1: 음식 판별 전용 프롬프트.

    사진을 분석해 음식 여부, 음식명, 보이는 재료, 시각적 특징을 추출한다.
    순수 JSON만 반환하도록 강제한다.
    """
    return """
너는 음식 사진을 분석하는 요리 보조 AI다.
주어진 사진을 분석하여 반드시 한국어로 응답하라.

━━━ 응답 규칙 ━━━

- 반드시 한국어로만 응답한다.
- 순수 JSON 문자열만 반환한다. 마크다운 코드블록(```)이나 설명 문장 절대 포함 금지.
- 사진이 음식이 아니면 is_food를 false로 설정하고 non_food_reason에 이유를 작성한다.
  · 이때 dish_name은 빈 문자열, ingredients는 빈 배열, characteristics는 빈 문자열로 반환한다.
- 음식이면 is_food를 true, non_food_reason은 빈 문자열로 둔다.
- ingredients에는 사진에서 시각적으로 확인 가능한 재료만 담는다.
  보이지 않는 양념·소스는 추측해 넣지 않는다.
- characteristics에는 색감·조리 형태·플레이팅 등 시각적 특징을 2~3문장으로 요약한다.

━━━ 정밀 시각 분석 지침 ━━━

[빵·베이커리·페이스트리류 정밀 판별]
- 겉면의 굽기 정도(연한 황금빛/진한 갈색/탄 정도)와 윤기(매트/글레이즈) 주의
- 층 구조가 보이면: 파이 도우·퍼프 페이스트리·크루아상·갈레트 중 구분
- 속 재료의 조리 상태 확인: 날것(생과일색)/졸인(짙고 윤기)/구운(캐러멜화/황변) 구별
- 과일 타르트·파이·갈레트·크럼블·크로스타타: 형태(원형/자유형), 가장자리 접힘, 충전물 색으로 구분
- 빵 겉면의 질감(매끄러운/거친/세몰리나 뿌림/egg wash 광택/슈거파우더)을 명시

[일반 음식 정밀 판별]
- 색감의 층·그러데이션을 명시적으로 설명 (예: "위층은 진한 갈색, 아래는 황금빛")
- 조리 방법을 시각 단서로 추론: 볶음(기름 윤기+볶음 자국), 찜(촉촉한 표면), 튀김(바삭한 외관+기름기), 구이(구운 자국·탄 부분)
- 그릇·플레이팅 스타일에서 국적(한식/일식/양식/중식 등)을 추론 단서로 활용
- 확신이 낮으면 dish_name을 "○○ 추정" 또는 "○○ 또는 ○○" 형식으로 작성하고 characteristics에 불확실 이유를 명시

[characteristics 필드 작성 기준]
- 반드시 색감, 조리 형태, 플레이팅, 추정 조리법을 포함한 3문장 이상 작성
- 빵·베이커리류면 겉면 질감·굽기·속 충전물 상태를 반드시 포함

━━━ JSON 스키마 ━━━

{
  "is_food": true,
  "non_food_reason": "",
  "dish_name": "음식명 (음식 아니면 빈 문자열)",
  "ingredients": ["사진에서 보이는 재료 목록"],
  "characteristics": "음식의 시각적 특징 요약 2~3문장"
}
""".strip()


def build_recipe_prompt(
    vision_result: dict,
    servings,
    extra_requests,
    source_md: str,
    feedback_md: str,
) -> str:
    """Call 2: 레시피 생성 전용 프롬프트.

    Call 1의 vision_result(음식명/재료/특징), 목표 인분, 추가 요청,
    source.md/feedback.md 기억을 조합한다. 순수 JSON만 반환하도록 강제한다.
    """
    vision_result = vision_result or {}
    dish_name = (vision_result.get("dish_name") or "").strip()
    vision_ingredients = vision_result.get("ingredients") or []
    characteristics = (vision_result.get("characteristics") or "").strip()

    # servings 기본값 처리
    if servings is None:
        servings = 2
        servings_note = "2인분 기준 (사용자 미지정 → 기본값)"
    else:
        servings_note = f"{servings}인분 기준"

    source_block = source_md.strip() if source_md and source_md.strip() else "(비어 있음)"
    feedback_block = feedback_md.strip() if feedback_md and feedback_md.strip() else "(비어 있음)"

    vision_ingredients_block = (
        ", ".join(str(i) for i in vision_ingredients) if vision_ingredients else "(없음)"
    )

    # 추가 요청 섹션은 값이 있을 때만 포함한다.
    extra_section = ""
    if extra_requests and str(extra_requests).strip():
        extra_section = (
            "\n[추가 요청사항]\n"
            f"{str(extra_requests).strip()}\n"
            "- source.md와 충돌하면 source.md를 우선한다.\n"
        )

    return f"""
너는 음식 사진 분석 결과를 바탕으로 레시피를 작성하는 요리 보조 AI다.
아래 분석 결과, 사용자 기억 파일, 현재 요청을 반영하여 반드시 한국어로 응답하라.

━━━ 사진 분석 결과 (Call 1) ━━━

- 음식명: {dish_name if dish_name else '(미상)'}
- 보이는 재료: {vision_ingredients_block}
- 시각적 특징: {characteristics if characteristics else '(없음)'}

━━━ 사용자 기억 파일 ━━━

[source.md] 우선순위 높음 — 사용자가 직접 관리하는 취향과 보유 재료 목록
{source_block}

[feedback.md] 자동 학습된 장기 취향 기억 — source.md와 충돌 시 source.md 우선 적용
{feedback_block}

━━━ 현재 요청 ━━━

- 목표 인분: {servings_note}
{extra_section}
━━━ 응답 규칙 ━━━

- 반드시 한국어로만 응답한다.
- 순수 JSON 문자열만 반환한다. 마크다운 코드블록(```)이나 설명 문장 절대 포함 금지.
- 모든 재료 양은 목표 인분({servings}인분) 기준으로 계산한다.
- ingredients는 문자열 배열이며 각 항목은 "재료명(단위)" 형식으로 작성한다. 예: "닭고기(200g)", "간장(2큰술)".
- steps는 조리 단계를 순서대로 담되 번호를 붙이지 말고 문장으로 작성한다.
- 취향 반영 우선순위: source.md > 추가 요청사항 > feedback.md.
- missing_ingredients: 레시피에 필요하지만 source.md 보유 재료에 없는 것들을 담는다.
  · source.md가 비어 있으면(보유 재료 정보 없음) 빈 배열로 둔다.
- difficulty는 easy, medium, hard 중 하나로만 작성한다.

━━━ JSON 스키마 ━━━

{{
  "dish_name": "음식 이름",
  "introduction": "음식 소개 2~3문장",
  "cooking_time": "예: 30분",
  "difficulty": "easy | medium | hard",
  "servings": {servings},
  "ingredients": ["닭고기(200g)", "간장(2큰술)"],
  "steps": ["조리 단계를 순서대로 작성 (번호 없이 문장으로)"],
  "missing_ingredients": ["레시피에 필요하지만 source.md 보유 재료에 없는 것들 (source.md가 비어있으면 빈 배열)"]
}}
""".strip()


# ───────────────────────── 인분 파싱 ─────────────────────────


def parse_servings(text):
    """자연어 인분 입력을 정수로 파싱한다.

    - None/공백/"알아서 해줘"/"상관없어"/"모르겠어" 등 → None
    - "2인분", "3명", "4명이서", "5명이 먹을 거야", "6인" → int
    - 아라비아 숫자(\\d+)만 신뢰. 한국어 수사("한", "두", "세" 등)는 확신 불가 → None
    """
    if text is None:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    match = re.search(r"\d+", stripped)
    if match:
        return int(match.group())

    # 아라비아 숫자가 없으면(한국어 수사 또는 "알아서"류) 확신 불가 → None
    return None


# ───────────────────────── 이미지 헬퍼 ─────────────────────────


def build_image_data_url(image_bytes, mime_type):
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_image}"


def is_within_groq_base64_request_limit(image_bytes, mime_type):
    encoded_request_size = len(build_image_data_url(image_bytes, mime_type).encode("utf-8"))
    return encoded_request_size <= GROQ_BASE64_REQUEST_LIMIT_BYTES


def _gemini_generate(messages: list) -> str:
    """Gemini API 호출. messages를 Gemini 형식으로 변환 후 텍스트 응답 반환."""
    import google.generativeai as genai  # noqa: PLC0415

    has_image = any(
        isinstance(msg.get("content"), list)
        and any(item.get("type") == "image_url" for item in msg["content"])
        for msg in messages
    )
    model_name = GEMINI_VISION_MODEL if has_image else GEMINI_TEXT_MODEL
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    parts = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append(item["text"])
                elif item.get("type") == "image_url":
                    url = item["image_url"]["url"]
                    header, b64data = url.split(",", 1)
                    mime = header.split(":")[1].split(";")[0]
                    img_bytes = base64.b64decode(b64data)
                    parts.append(
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": base64.b64encode(img_bytes).decode(),
                            }
                        }
                    )
    response = model.generate_content(parts)
    return response.text or ""


def generate_with_retry(client, messages: list, model: str, retries=3, base_delay=3):
    """범용 AI API 호출 + 지수 백오프 재시도. Groq/Gemini 양쪽 지원.

    - client: Groq 객체(Groq provider) 또는 None(Gemini provider)
    - messages: Groq/OpenAI 형식 messages 배열 (Vision은 image_url content 포함)
    - model: Groq 모델명 (Gemini는 GEMINI_* 상수를 자동 사용)
    - 응답은 .choices[0].message.content 인터페이스를 통일 반환
    """
    provider = _get_provider()

    class _NormalizedResponse:
        class _Choice:
            class _Msg:
                def __init__(self, c):
                    self.content = c
            def __init__(self, c):
                self.message = self._Msg(c)
        def __init__(self, c):
            self.choices = [self._Choice(c)]

    for attempt in range(1, retries + 1):
        try:
            if provider == "gemini":
                content = _gemini_generate(messages)
                return _NormalizedResponse(content)
            else:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_completion_tokens=4096,
                )
                return _NormalizedResponse(resp.choices[0].message.content or "")
        except Exception as e:
            err_text = str(e).lower()
            is_rate_limited = (
                "429" in err_text
                or "quota" in err_text
                or "resource_exhausted" in err_text
                or "rate limit" in err_text
                or "too many requests" in err_text
            )
            if not is_rate_limited or attempt == retries:
                raise
            wait_seconds = base_delay * (2 ** (attempt - 1))
            st.warning(
                f"요청이 많아 잠시 대기 후 재시도합니다. ({attempt}/{retries}, {wait_seconds}초 대기)"
            )
            time.sleep(wait_seconds)


# ───────────────────────── 파이프라인 오케스트레이션 ─────────────────────────
# 아래 두 함수가 UI(session_state 플로우)에서 호출하는 공개 진입점이다.
# 둘 다 (성공: dict, 실패: None) + 파싱 실패 시 raw_text를 함께 반환한다.


def analyze_food_image(client, image_bytes, mime_type):
    """Call 1: Vision 분석. (result_dict_or_None, raw_text) 반환.

    raw_text는 JSON 파싱 실패 시 UI에서 st.code()로 노출하기 위한 원문.
    """
    image_data_url = build_image_data_url(image_bytes, mime_type)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_vision_prompt()},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }
    ]
    response = generate_with_retry(client, messages, GROQ_VISION_MODEL)
    raw_text = (response.choices[0].message.content or "").strip()
    try:
        return json.loads(raw_text), raw_text
    except json.JSONDecodeError:
        return None, raw_text


def generate_recipe(client, vision_result, servings, extra_requests):
    """Call 2: 레시피 생성. (result_dict_or_None, raw_text) 반환.

    source.md/feedback.md는 매 호출 시점에 로드한다.
    servings는 parse_servings() 결과(int 또는 None)를 그대로 전달하면 된다.
    """
    source_md = load_source_md()
    feedback_md = load_feedback_md()
    prompt_text = build_recipe_prompt(
        vision_result=vision_result,
        servings=servings,
        extra_requests=extra_requests,
        source_md=source_md,
        feedback_md=feedback_md,
    )
    messages = [{"role": "user", "content": prompt_text}]
    response = generate_with_retry(client, messages, GROQ_TEXT_MODEL)
    raw_text = (response.choices[0].message.content or "").strip()
    try:
        return json.loads(raw_text), raw_text
    except json.JSONDecodeError:
        return None, raw_text


def save_recipe(recipe: dict) -> str:
    """레시피를 recipes/ 폴더에 JSON 파일로 저장한다. 저장된 경로를 반환한다."""
    from datetime import datetime

    os.makedirs("recipes", exist_ok=True)
    dish_name = str(recipe.get("dish_name") or "recipe")
    # 파일명 불가 문자 제거
    safe_name = re.sub(r'[\\/:*?"<>|]', "", dish_name).strip() or "recipe"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recipes/{timestamp}_{safe_name}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)
    return filename


def extract_and_save_feedback(client, extra_requests: str):
    """extra_requests에서 장기 취향을 LLM으로 추출해 feedback.md에 타임스탬프와 함께 append."""
    from datetime import date
    if not extra_requests or not str(extra_requests).strip():
        return
    prompt = (
        "사용자의 추가 요청사항에서 장기적인 음식 취향만 추출하라. "
        "장기 취향 예시: 알러지, 식단 제한, 선호/기피 재료, 맛 선호 등. "
        "일회성 요청 예시: 조리 시간 제한, 특정 도구 없음, 특정 레시피 조정 등 — 이것들은 제외한다. "
        "장기 취향이 없으면 빈 배열을 반환한다. 순수 JSON만 반환한다.\n\n"
        f"추가 요청사항: {extra_requests}\n\n"
        '{"preferences": ["장기 취향 1", "장기 취향 2"]}'
    )
    try:
        messages = [{"role": "user", "content": prompt}]
        response = generate_with_retry(client, messages, GROQ_TEXT_MODEL)
        result = json.loads(response.choices[0].message.content or "{}")
        preferences = result.get("preferences", [])
        if not preferences:
            return
        today = date.today().isoformat()
        lines_to_add = "\n".join(f"[{today}] - {p}" for p in preferences)
        with open(FEEDBACK_MD_PATH, "a", encoding="utf-8") as f:
            f.write(("\n" if os.path.exists(FEEDBACK_MD_PATH) else "") + lines_to_add + "\n")
    except Exception:
        pass  # feedback 업데이트 실패는 무시


_NAVER_STOP_WORDS = [
    "틀", "모양틀", "조리기", "조리도구", "프라이팬", "플레이트",
    "메이커", "커터", "성형기", "기계", "기구", "스텐", "에그팬", "쉐이퍼",
    "몰드", "액세서리", "가젯", "쿠커", "논스틱", "주방용품", "매트",
    "뒤집개", "롤러", "스프레더", "커팅기", "슬라이서", "프레서", "전용팬",
    "원형", "사각", "타원형", "삼각형", "다용도", "조리세트", "조리도구세트",
]


def get_shopping_items(dish_name: str, ingredient: str) -> list:
    """네이버 쇼핑 API로 '{dish_name}용 {ingredient}' 검색, 정확도순 상위 3개 반환.

    반환: [{"title": str, "lprice": str, "link": str}, ...]
    API 키 미설정 또는 오류 시 빈 리스트 반환.
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    keyword = f"{dish_name}용 {ingredient}"
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/shop.json",
            headers={
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            },
            params={
                "query": keyword,
                "display": 15,
                "sort": "sim",
                "exclude": "used:rental:cbshop",
            },
            timeout=5,
        )
        if resp.status_code != 200:
            return []
        products = []
        for item in resp.json().get("items", []):
            title = item["title"].replace("<b>", "").replace("</b>", "")
            if any(w in title for w in _NAVER_STOP_WORDS):
                continue
            products.append({"title": title, "lprice": item["lprice"], "link": item["link"]})
            if len(products) == 3:
                break
        return products
    except Exception:
        return []


def build_naver_shopping_url(ingredient: str) -> str:
    """네이버 쇼핑 검색 URL (API 키 없을 때 fallback)."""
    from urllib.parse import quote
    return f"https://search.shopping.naver.com/search/all?query={quote(ingredient.strip())}"


def build_shopping_html(dish_name: str, missing_ingredients: list) -> str:
    """missing_ingredients에 대한 네이버 쇼핑 검색 결과 HTML 섹션을 반환한다.

    API 키 미설정 또는 전체 검색 결과 없으면 빈 문자열 반환.
    """
    if not missing_ingredients or not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return ""
    section = "<b>🛒 필요한 재료 구매하기</b>"
    any_results = False
    for item in missing_ingredients:
        ing_name = _parse_ingredient_string(str(item))["name"]
        products = get_shopping_items(dish_name, ing_name)
        if products:
            any_results = True
            section += (
                f'<div class="shop-ing-label">'
                f'<span class="tag-amber">구매 필요</span>'
                f'&nbsp;{html.escape(ing_name)}</div>'
            )
            for p in products:
                raw_price = str(p.get("lprice", ""))
                price_str = f"₩{int(raw_price):,}" if raw_price.isdigit() else raw_price
                p_link = html.escape(str(p["link"]), quote=True)
                p_title = html.escape(str(p["title"]))
                section += (
                    f'<a href="{p_link}" target="_blank" class="shop-item">'
                    f'<span class="shop-title">{p_title}</span>'
                    f'<span class="shop-price">{price_str}</span>'
                    f'</a>'
                )
    return section if any_results else ""


# ─────────────────────────── source.md 파싱/저장 ───────────────────────────

_AMOUNT_PATTERN_STR = re.compile(
    r"^(\d+(?:\.\d+)?)(g|kg|ml|L|개|알|큰술|작은술|컵|줄기|묶음|장|쪽|톨|팩|봉|캔)$"
)
# 기준 단위로 변환: {"원래단위": ("기준단위", 배수)}
_UNIT_CONVERSIONS: dict = {"kg": ("g", 1000), "L": ("ml", 1000)}
_ING_PAREN_PATTERN = re.compile(r"^(.+?)\((.*?)\)$")


def _parse_ingredient_string(s: str) -> dict:
    """"재료명(단위)" 또는 "재료명" → {"name": "...", "amount": "..."}"""
    s = str(s).strip()
    m = _ING_PAREN_PATTERN.match(s)
    if m:
        return {"name": m.group(1).strip(), "amount": m.group(2).strip()}
    return {"name": s, "amount": ""}


def _parse_amount_val(amount: str):
    """지원 단위이면 (quantity, base_unit) 반환. kg→g, L→ml 자동 변환. 아니면 None."""
    amount = (amount or "").strip()
    m = _AMOUNT_PATTERN_STR.match(amount)
    if not m:
        return None
    q = float(m.group(1))
    unit = m.group(2)
    if unit in _UNIT_CONVERSIONS:
        base_unit, factor = _UNIT_CONVERSIONS[unit]
        q = q * factor
        unit = base_unit
    return (int(q) if q.is_integer() else q), unit


def _format_amount_val(quantity, unit: str) -> str:
    if isinstance(quantity, float) and quantity.is_integer():
        quantity = int(quantity)
    return f"{quantity}{unit}"


def _is_zero_amount_val(amount: str) -> bool:
    parsed = _parse_amount_val(amount)
    return parsed is not None and parsed[0] == 0


def parse_source_md_to_data(path: str = SOURCE_MD_PATH) -> dict:
    """source.md → {"ingredients": [{"name", "amount"}], "user_preferences": [...]}"""
    if not os.path.exists(path):
        return {"ingredients": [], "user_preferences": []}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    sections: dict = {}
    cur_title, cur_lines = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur_title:
                sections[cur_title] = "\n".join(cur_lines)
            cur_title = line.replace("##", "", 1).strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur_title:
        sections[cur_title] = "\n".join(cur_lines)

    def _get_items(section_text: str) -> list:
        items, in_input = [], False
        for line in section_text.splitlines():
            s = line.strip()
            if s.startswith("입력:"):
                in_input = True
                continue
            if in_input:
                if re.fullmatch(r"-{3,}", s):
                    continue
                if s.startswith("-"):
                    item = s[1:].strip()
                    if item:
                        items.append(item)
        return items

    ingredient_items, preference_items = [], []
    for title, body in sections.items():
        if "재료" in title:
            ingredient_items = _get_items(body)
        elif "사용자 특성" in title:
            preference_items = _get_items(body)
    return {
        "ingredients": [_parse_ingredient_string(item) for item in ingredient_items],
        "user_preferences": preference_items,
    }


def save_source_data_to_md(source_data: dict, path: str = SOURCE_MD_PATH):
    """Structured source data → source.md 파일로 저장."""
    from datetime import date
    ingredients = [
        item for item in source_data.get("ingredients", [])
        if not _is_zero_amount_val(item.get("amount", ""))
    ]
    prefs = source_data.get("user_preferences", [])

    def _ing_line(item):
        name = item.get("name", "").strip()
        amt = item.get("amount", "").strip()
        return f"- {name}({amt})" if amt else f"- {name}"

    lines = [
        "# 내 주방 정보",
        "",
        f"최종 갱신일: {date.today().isoformat()}",
        "",
        "---",
        "",
        "## 1. 재료",
        "",
        "가지고 계신 재료를 자유롭게 적어주세요.",
        "재료명(양) 형식에 맞게 적어주세요.",
        "양을 몰라도 괜찮습니다, 재료명만 적어주세요.",
        "계량 단위는 g, ml로 통일해 주세요.",
        "",
        "예시:",
        "- 양파(5개)",
        "- 설탕(500g)",
        "- 설탕",
        "- 간장",
        "- 계란(2알)",
        "",
        "입력:",
    ] + [_ing_line(item) for item in ingredients] + [
        "",
        "---",
        "",
        "## 2. 사용자 특성",
        "",
        "레시피 생성 과정에서 요청사항이 있다면 적어주세요.",
        "",
        "예시:",
        "- 짠 음식을 싫어해요",
        "- 토마토 알러지가 있어요",
        "- 과일보다는 채소를 좋아해요",
        "- 매운 음식을 좋아해요",
        "- 다이어트 중이에요",
        "- 비건 식단을 선호해요",
        "",
        "입력:",
    ] + [f"- {p}" for p in prefs] + [""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────── 장바구니 / 완료 처리 ───────────────────────────


def save_to_cart(recipe: dict) -> str:
    """레시피를 cart/json/ 폴더에 저장한다. 저장된 경로를 반환한다."""
    from datetime import datetime
    os.makedirs(CART_JSON_DIR, exist_ok=True)
    dish_name = str(recipe.get("dish_name") or "recipe")
    safe_name = re.sub(r'[\\/:*?"<>|]', "", dish_name).strip() or "recipe"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{CART_JSON_DIR}/{timestamp}_{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)
    return path


def list_cart_items() -> list:
    """cart/json/ 의 레시피 목록을 [{path, dish_name, data}] 형태로 반환한다."""
    if not os.path.exists(CART_JSON_DIR):
        return []
    items = []
    for p in sorted(glob.glob(f"{CART_JSON_DIR}/*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            items.append({
                "path": p,
                "dish_name": data.get("dish_name", os.path.basename(p)),
                "data": data,
            })
        except Exception:
            pass
    return items


def calculate_source_update(recipe: dict, source_data: dict) -> dict:
    """
    새 API 형식 레시피 + source_data → 재료 차감 결과 계산.

    반환: {"used": [...], "blocked": [...], "missing": [...], "updated_source": {...}}
    - used    : 자동 차감 가능 (name, amount, before, after)
    - blocked : 자동 차감 불가 (name, amount, reason)
    - missing : source.md에 없는 재료 (name, amount) — API missing_ingredients 기준
    - updated_source: 차감이 반영된 source_data
    """
    source_by_name = {item["name"]: item for item in source_data.get("ingredients", [])}
    all_ings = [_parse_ingredient_string(s) for s in recipe.get("ingredients", [])]
    missing_strs = recipe.get("missing_ingredients", [])
    missing_ings = [_parse_ingredient_string(s) for s in missing_strs]
    missing_names = {ing["name"] for ing in missing_ings}

    available = [ing for ing in all_ings if ing["name"] not in missing_names]
    used, blocked = [], []
    updated_by_name = {
        item["name"]: {"name": item["name"], "amount": item.get("amount", "")}
        for item in source_data.get("ingredients", [])
    }

    for ing in available:
        name, req_amount = ing["name"], ing["amount"]
        source_item = source_by_name.get(name)
        if not source_item:
            blocked.append({"name": name, "amount": req_amount, "reason": "source.md에 없는 재료"})
            continue
        cur_amount = source_item.get("amount", "").strip()
        if not cur_amount:
            blocked.append({"name": name, "amount": req_amount, "reason": "현재 보유량이 비어 있어 자동 차감 불가"})
            continue
        cur = _parse_amount_val(cur_amount)
        req = _parse_amount_val(req_amount)
        if not req:
            blocked.append({"name": name, "amount": req_amount, "reason": "필요량 단위가 지원되지 않음"})
            continue
        if not cur:
            blocked.append({"name": name, "amount": cur_amount, "reason": "현재 보유량 단위가 지원되지 않음"})
            continue
        cur_qty, cur_unit = cur
        req_qty, req_unit = req
        if cur_unit != req_unit:
            blocked.append({"name": name, "amount": req_amount, "reason": f"단위가 다름: 보유 {cur_unit}, 필요 {req_unit}"})
            continue
        if cur_qty < req_qty:
            blocked.append({"name": name, "amount": req_amount, "reason": f"보유량 부족: 보유 {cur_amount}"})
            continue
        after_qty = cur_qty - req_qty
        after_amount = _format_amount_val(after_qty, cur_unit)
        used.append({
            "name": name, "amount": req_amount,
            "before": cur_amount, "after": "삭제됨" if after_qty == 0 else after_amount,
        })
        updated_by_name[name]["amount"] = after_amount

    updated_ingredients = [
        updated_by_name.get(item["name"], item)
        for item in source_data.get("ingredients", [])
        if not _is_zero_amount_val(updated_by_name.get(item["name"], item).get("amount", ""))
    ]
    return {
        "used": used,
        "blocked": blocked,
        "missing": missing_ings,
        "updated_source": {**source_data, "ingredients": updated_ingredients},
    }


def save_to_completed(cart_path: str, completion_result: dict) -> str:
    """완료된 레시피를 completed/json/에 저장하고 cart에서 삭제한다. 저장 경로를 반환한다."""
    from datetime import date
    os.makedirs(COMPLETED_JSON_DIR, exist_ok=True)
    with open(cart_path, encoding="utf-8") as f:
        data = json.load(f)
    data["completed_at"] = date.today().isoformat()
    data["completion_result"] = {
        "used": completion_result.get("used", []),
        "blocked": completion_result.get("blocked", []),
        "missing": completion_result.get("missing", []),
    }
    basename = os.path.basename(cart_path)
    completed_path = f"{COMPLETED_JSON_DIR}/{basename}"
    with open(completed_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.remove(cart_path)
    return completed_path


# ═══════════════════════════════════════════════════════════════════════════
# UI — 3-뷰 구조 (home / chat / kitchen)
# styles.css 기반 디자인 시스템 + Streamlit 렌더링 레이어
# 파이프라인 함수(상단)는 한 줄도 수정하지 않는다.
#   · view == "home"    → 홈 보드 (히어로 + 통계 + 레시피 그리드)
#   · view == "chat"    → 채팅 플로우 (Step 1~4)
#   · view == "kitchen" → 내 주방 (재료 칩 / 취향 / 완료 처리 대기)
# ═══════════════════════════════════════════════════════════════════════════


# ─────────────────────────── PAGE CONFIG ───────────────────────────
# set_page_config는 스크립트 전체에서 최초 1회만 호출되어야 한다.
st.set_page_config(
    page_title="레시피 AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────── CSS (styles.css 기반 전면 교체) ───────────────────────────
st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');

    :root {
      /* ---- Canvas & surfaces ---- */
      --bg:        #F4F6F9;
      --bg-soft:   #EDF0F5;
      --surface:   #FFFFFF;
      --surface-2: #FAFBFC;
      --surface-3: #F5F7FA;

      /* ---- Ink ---- */
      --ink:       #14171F;
      --ink-2:     #555E6E;
      --ink-3:     #8A93A3;
      --ink-4:     #B4BBC7;

      /* ---- Lines ---- */
      --line:      #E6E9EF;
      --line-2:    #EEF1F5;
      --line-strong: #D7DCE5;

      /* ---- Brand blue ---- */
      --blue:      #2F6BFF;
      --blue-600:  #1F5BF0;
      --blue-700:  #1A4FD6;
      --blue-soft: #ECF1FF;
      --blue-soft-2: #E0E8FF;
      --blue-ink:  #1B47B8;

      /* ---- Accents ---- */
      --green:     #15A862;
      --green-soft:#E4F6EC;
      --green-ink: #0E7C48;
      --amber:     #E08600;
      --amber-soft:#FCF1DC;
      --amber-ink: #9A5B00;
      --naver:     #03C75A;
      --rose:      #E5484D;
      --rose-soft: #FCEBEC;

      /* ---- Radius ---- */
      --r-xs: 7px;
      --r-sm: 10px;
      --r-md: 14px;
      --r-lg: 18px;
      --r-xl: 24px;
      --r-pill: 999px;

      /* ---- Shadow ---- */
      --sh-xs: 0 1px 2px rgba(20,23,31,.05);
      --sh-sm: 0 1px 3px rgba(20,23,31,.06), 0 1px 2px rgba(20,23,31,.04);
      --sh-md: 0 4px 14px rgba(20,23,31,.07), 0 1px 3px rgba(20,23,31,.05);
      --sh-lg: 0 12px 34px rgba(20,23,31,.10), 0 3px 8px rgba(20,23,31,.05);
      --sh-blue: 0 6px 18px rgba(47,107,255,.28);

      /* ---- Type ---- */
      --font: 'Pretendard', -apple-system, system-ui, sans-serif;
      --mono: 'DM Mono', ui-monospace, 'SF Mono', monospace;

      --sidebar-w: 248px;
    }

    .mono { font-family: var(--mono); font-feature-settings: "tnum"; letter-spacing: -0.02em; }

    /* ============================================================
       Streamlit 오버라이드
       ============================================================ */
    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        font-family: var(--font);
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 0; }
    [data-testid="stMainBlockContainer"] { padding: 1.2rem 2rem 3rem !important; max-width: 100% !important; }
    .main .block-container { padding: 1.2rem 2rem 3rem !important; max-width: 100% !important; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden; }
    .stDeployButton { display: none !important; }
    .stButton > button {
        border-radius: var(--r-md) !important;
        font-family: var(--font) !important;
        font-weight: 700 !important;
    }
    .stFileUploader { border-radius: var(--r-lg) !important; }

    /* ============================================================
       SIDEBAR
       ============================================================ */
    .sidebar { width: var(--sidebar-w); min-width: var(--sidebar-w); background: var(--surface);
      border-right: 1px solid var(--line); display: flex; flex-direction: column; height: 100%; }
    .sb-brand { display: flex; align-items: center; gap: 11px; padding: 14px 6px 16px; }
    .sb-logo {
      width: 38px; height: 38px; border-radius: 11px;
      background: linear-gradient(155deg, var(--blue) 0%, var(--blue-700) 100%);
      display: grid; place-items: center; box-shadow: var(--sh-blue);
      color: #fff; flex-shrink: 0; font-size: 19px;
    }
    .sb-brand-name { font-weight: 800; font-size: 16px; letter-spacing: -0.02em; color: var(--ink); }
    .sb-brand-sub { font-size: 11.5px; color: var(--ink-3); margin-top: 1px; font-weight: 500; }

    .sb-new {
      margin: 4px 0 14px; display: flex; align-items: center; justify-content: center; gap: 8px;
      padding: 11px 14px; background: var(--blue); color: #fff; border: none; border-radius: var(--r-md);
      font-weight: 700; font-size: 13.5px; box-shadow: var(--sh-blue);
      transition: transform .12s ease, background .15s ease;
    }
    .sb-new:hover { background: var(--blue-600); transform: translateY(-1px); }
    .sb-new:active { transform: translateY(0); }

    .sb-nav { padding: 0; display: flex; flex-direction: column; gap: 2px; }
    .sb-nav-item {
      display: flex; align-items: center; gap: 11px; padding: 9px 12px; border-radius: var(--r-sm);
      background: none; border: none; width: 100%; text-align: left;
      color: var(--ink-2); font-weight: 600; font-size: 13.5px;
      transition: background .12s ease, color .12s ease;
    }
    .sb-nav-item:hover { background: var(--surface-3); color: var(--ink); }
    .sb-nav-item.active { background: var(--blue-soft); color: var(--blue-ink); }
    .sb-nav-item.active svg { color: var(--blue); }
    .sb-nav-item svg { color: var(--ink-3); flex-shrink: 0; }
    .sb-nav-count {
      margin-left: auto; font-size: 11px; font-weight: 700;
      background: var(--surface-3); color: var(--ink-3);
      padding: 1px 7px; border-radius: var(--r-pill); min-width: 20px; text-align: center;
    }
    .sb-nav-item.active .sb-nav-count { background: var(--blue-soft-2); color: var(--blue-ink); }

    .sb-section-label {
      padding: 16px 4px 7px; font-size: 11px; font-weight: 700;
      color: var(--ink-4); letter-spacing: 0.04em; text-transform: uppercase;
    }
    .sb-saved { flex: 1; overflow-y: auto; padding: 0 0 12px; }
    .sb-saved::-webkit-scrollbar { width: 6px; }
    .sb-saved::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 3px; }

    .sb-recipe {
      display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--r-sm);
      background: none; border: none; width: 100%; text-align: left; transition: background .12s ease;
    }
    .sb-recipe:hover { background: var(--surface-3); }
    .sb-recipe.active { background: var(--blue-soft); }
    .sb-recipe-thumb {
      width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
      display: grid; place-items: center; font-size: 15px;
      background: var(--surface-3); border: 1px solid var(--line);
    }
    .sb-recipe-name { font-size: 13px; font-weight: 600; color: var(--ink);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sb-recipe-meta { font-size: 10.5px; color: var(--ink-3); margin-top: 1px; }
    .sb-status-dot { width: 7px; height: 7px; border-radius: 50%; margin-left: auto; flex-shrink: 0; }
    .dot-cart { background: var(--amber); }
    .dot-done { background: var(--green); }

    .sb-foot { border-top: 1px solid var(--line); padding: 12px 4px; display: flex; align-items: center; gap: 10px; }
    .sb-avatar {
      width: 30px; height: 30px; border-radius: 50%;
      background: var(--blue-soft); color: var(--blue-ink);
      display: grid; place-items: center; font-weight: 800; font-size: 12px;
    }

    /* ============================================================
       TOPBAR
       ============================================================ */
    .topbar {
      border-bottom: 1px solid var(--line); background: rgba(255,255,255,.82); backdrop-filter: blur(8px);
      display: flex; align-items: center; gap: 14px; padding: 14px 4px 16px; margin-bottom: 8px;
    }
    .topbar-title { font-weight: 800; font-size: 16.5px; letter-spacing: -0.02em; color: var(--ink); }
    .topbar-sub { font-size: 12.5px; color: var(--ink-3); font-weight: 500; }
    .topbar-spacer { flex: 1; }
    .topbar-status {
      display: flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 600;
      color: var(--green-ink); background: var(--green-soft); padding: 5px 11px; border-radius: var(--r-pill);
    }
    .live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green);
      box-shadow: 0 0 0 0 rgba(21,168,98,.5); animation: pulse 2.2s infinite; display: inline-block; }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(21,168,98,.45); }
      70% { box-shadow: 0 0 0 6px rgba(21,168,98,0); }
      100% { box-shadow: 0 0 0 0 rgba(21,168,98,0); }
    }

    .scroll { flex: 1; overflow-y: auto; }
    .scroll::-webkit-scrollbar { width: 9px; }
    .scroll::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 5px; border: 2px solid var(--bg); }
    .scroll::-webkit-scrollbar-track { background: transparent; }

    /* ============================================================
       BUTTONS / CHIPS
       ============================================================ */
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 7px;
      border: 1px solid transparent; border-radius: var(--r-md);
      font-weight: 700; font-size: 13.5px; padding: 10px 16px; transition: all .14s ease; white-space: nowrap;
    }
    .btn-primary { background: var(--blue); color: #fff; box-shadow: var(--sh-blue); }
    .btn-primary:hover { background: var(--blue-600); transform: translateY(-1px); }
    .btn-primary:active { transform: translateY(0); }
    .btn-primary:disabled { background: var(--line-strong); color: #fff; box-shadow: none; cursor: not-allowed; transform: none; }
    .btn-ghost { background: var(--surface); color: var(--ink); border-color: var(--line-strong); box-shadow: var(--sh-xs); }
    .btn-ghost:hover { background: var(--surface-3); border-color: var(--ink-4); }
    .btn-soft { background: var(--blue-soft); color: var(--blue-ink); }
    .btn-soft:hover { background: var(--blue-soft-2); }
    .btn-green { background: var(--green); color: #fff; box-shadow: 0 6px 18px rgba(21,168,98,.26); }
    .btn-green:hover { background: var(--green-ink); transform: translateY(-1px); }
    .btn-sm { padding: 7px 13px; font-size: 12.5px; border-radius: var(--r-sm); }
    .btn-lg { padding: 13px 22px; font-size: 14.5px; border-radius: var(--r-md); }

    .chip {
      display: inline-flex; align-items: center; gap: 6px;
      background: var(--surface); border: 1.5px solid var(--blue-soft-2);
      color: var(--blue-ink); font-weight: 600; font-size: 13px;
      padding: 8px 14px; border-radius: var(--r-pill); transition: all .13s ease;
    }
    .chip:hover { border-color: var(--blue); background: var(--blue-soft); transform: translateY(-1px); }
    .chip.selected { background: var(--blue); color: #fff; border-color: var(--blue); }

    /* ============================================================
       CHAT
       ============================================================ */
    .chat-wrap { max-width: 860px; margin: 0 auto; padding: 10px 6px 16px; }
    .day-sep { display: flex; align-items: center; gap: 14px; margin: 6px 0 22px; }
    .day-sep::before, .day-sep::after { content: ""; flex: 1; height: 1px; background: var(--line); }
    .day-sep span { font-size: 11.5px; color: var(--ink-3); font-weight: 600; }

    .msg-ai { display: flex; gap: 12px; margin-bottom: 16px; max-width: 90%; }
    .msg-ai-avatar {
      width: 36px; height: 36px; border-radius: 11px; flex-shrink: 0;
      background: linear-gradient(155deg, var(--blue) 0%, var(--blue-700) 100%);
      display: grid; place-items: center; color: #fff; box-shadow: var(--sh-sm); margin-top: 2px; font-size: 17px;
    }
    .bubble-ai {
      background: var(--surface); border: 1px solid var(--line);
      border-radius: 6px 16px 16px 16px; padding: 13px 16px;
      font-size: 14.5px; line-height: 1.62; color: var(--ink); box-shadow: var(--sh-xs);
    }
    .bubble-ai b { font-weight: 700; }
    .bubble-ai .sub { color: var(--ink-3); font-size: 13px; }

    .msg-user { display: flex; justify-content: flex-end; margin-bottom: 16px; }
    .bubble-user {
      background: var(--blue); color: #fff; border-radius: 16px 6px 16px 16px;
      padding: 12px 16px; font-size: 14.5px; line-height: 1.55; max-width: 75%;
      box-shadow: var(--sh-blue); font-weight: 500;
    }
    .bubble-user.photo { padding: 6px; }
    .bubble-user.photo img, .bubble-user.photo .ph { border-radius: 12px; display: block; }

    .quick-row { display: flex; flex-wrap: wrap; gap: 9px; margin: 0 0 20px 48px; }

    .typing { display: flex; gap: 4px; padding: 4px 2px; }
    .typing i { width: 7px; height: 7px; border-radius: 50%; background: var(--ink-4); animation: bounce 1.3s infinite; }
    .typing i:nth-child(2) { animation-delay: .18s; }
    .typing i:nth-child(3) { animation-delay: .36s; }
    @keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity:.5; } 30% { transform: translateY(-5px); opacity:1; } }

    /* upload zone */
    .upload-zone {
      margin: 4px auto 14px; max-width: 520px;
      border: 2px dashed var(--line-strong); border-radius: var(--r-lg);
      background: var(--surface-2); padding: 26px;
      display: flex; flex-direction: column; align-items: center; gap: 12px;
      text-align: center; transition: all .16s ease;
    }
    .upload-zone:hover { border-color: var(--blue); background: var(--blue-soft); }
    .upload-ic { width: 50px; height: 50px; border-radius: 14px; background: var(--blue-soft);
      color: var(--blue); display: grid; place-items: center; font-size: 24px; }
    .upload-zone h4 { margin: 0; font-size: 14.5px; font-weight: 700; color: var(--ink); }
    .upload-zone p { margin: 0; font-size: 12.5px; color: var(--ink-3); }

    .ph {
      background-image: repeating-linear-gradient(45deg, #EEF1F6 0 11px, #E4E8EF 11px 22px);
      display: grid; place-items: center; color: var(--ink-3);
      font-family: var(--mono); font-size: 12px; position: relative;
    }
    .ph.food { background-image: repeating-linear-gradient(45deg, #F3ECDF 0 11px, #EDE3D0 11px 22px); }

    /* ============================================================
       RECIPE CARD
       ============================================================ */
    .recipe-card {
      background: var(--surface); border: 1px solid var(--line);
      border-radius: var(--r-lg); box-shadow: var(--sh-md); overflow: hidden; margin-bottom: 6px;
    }
    .rc-head { padding: 18px 20px 14px; }
    .rc-eyebrow { font-size: 11.5px; font-weight: 700; color: var(--blue); letter-spacing: 0.03em; text-transform: uppercase; }
    .rc-title { font-size: 21px; font-weight: 800; margin: 5px 0 6px; letter-spacing: -0.025em; color: var(--ink); }
    .rc-intro { font-size: 13.5px; color: var(--ink-2); line-height: 1.6; }

    .rc-meta { display: flex; gap: 10px; padding: 0 20px 16px; flex-wrap: wrap; }
    .rc-meta-item {
      display: flex; align-items: center; gap: 7px;
      background: var(--surface-3); border: 1px solid var(--line-2);
      border-radius: var(--r-sm); padding: 8px 12px; flex: 1; min-width: 92px;
    }
    .rc-meta-ic { color: var(--blue); display: grid; place-items: center; }
    .rc-meta-k { font-size: 10.5px; color: var(--ink-3); font-weight: 600; display: block; }
    .rc-meta-v { font-size: 14px; font-weight: 800; display: block; color: var(--ink); }

    .rc-section { padding: 16px 20px; border-top: 1px solid var(--line-2); }
    .rc-section-title { display: flex; align-items: center; gap: 8px; font-size: 13.5px; font-weight: 800; margin-bottom: 13px; color: var(--ink); }
    .rc-section-title .n { color: var(--ink-4); font-weight: 700; font-size: 12px; margin-left: auto; }

    .ing-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .ing-pill {
      display: flex; align-items: center; gap: 9px;
      background: var(--surface-2); border: 1px solid var(--line-2);
      border-radius: var(--r-sm); padding: 9px 12px;
    }
    .ing-check { width: 17px; height: 17px; border-radius: 5px; border: 1.5px solid var(--line-strong); flex-shrink: 0; display: grid; place-items: center; font-size: 10px; font-weight: 800; transition: all .12s; }
    .ing-pill.have .ing-check { background: var(--green); border-color: var(--green); color: #fff; }
    .ing-pill.missing { background: var(--amber-soft); border-color: #F0DCB0; }
    .ing-pill.missing .ing-check { background: var(--amber-soft); border-color: var(--amber); color: var(--amber-ink); }
    .ing-name { font-size: 13.5px; font-weight: 600; color: var(--ink); }
    .ing-amt { margin-left: auto; font-size: 12.5px; color: var(--ink-2); white-space: nowrap; }
    .ing-pill.missing .ing-amt { color: var(--amber-ink); font-weight: 600; }

    .step { display: flex; gap: 13px; padding: 11px 0; }
    .step:not(:last-child) { border-bottom: 1px solid var(--line-2); }
    .step-n {
      width: 26px; height: 26px; border-radius: 9px; flex-shrink: 0;
      background: var(--blue-soft); color: var(--blue-ink);
      display: grid; place-items: center; font-weight: 800; font-size: 13px; font-family: var(--mono);
    }
    .step-tx { font-size: 13.8px; line-height: 1.6; color: var(--ink); padding-top: 2px; }

    /* legacy step/ing aliases (build_recipe_card_html 호환) */
    .step-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--line-2); font-size: 13.8px; line-height: 1.6; color: var(--ink); }
    .step-item:last-child { border-bottom: none; padding-bottom: 4px; }
    .step-num { min-width: 26px; height: 26px; border-radius: 9px; flex-shrink: 0; background: var(--blue-soft); color: var(--blue-ink); display: flex; align-items: center; justify-content: center; font-size: 12.5px; font-weight: 800; margin-top: 1px; }
    .ing-pill.have { border-color: #B7EACA; background: #F2FBF4; }

    /* ============================================================
       SHOPPING (Naver)
       ============================================================ */
    .shop-block { margin-top: 10px; }
    .shop-ing-label { font-size: 13px; font-weight: 700; margin: 12px 0 7px; display:flex; align-items:center; gap:7px; }
    .shop-item {
      display: flex; align-items: center; gap: 11px;
      background: var(--surface-2); border: 1px solid var(--line);
      border-radius: var(--r-sm); padding: 9px 12px; margin-bottom: 6px;
      text-decoration: none; color: var(--ink); transition: all .12s ease;
    }
    .shop-item:hover { border-color: var(--naver); background: #F2FBF5; }
    .shop-thumb { width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0; }
    .shop-title { font-size: 12.8px; font-weight: 600; line-height: 1.4; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
    .shop-price { margin-left: auto; font-weight: 800; font-size: 13.5px; color: var(--ink); white-space: nowrap; font-family: var(--mono); }
    .shop-mall { font-size: 10.5px; color: var(--naver); font-weight: 700; }

    /* ============================================================
       COMPOSER
       ============================================================ */
    .composer-wrap { border-top: 1px solid var(--line); background: rgba(255,255,255,.9); backdrop-filter: blur(8px); padding: 14px 26px 18px; }
    .composer { max-width: 760px; margin: 0 auto; display: flex; align-items: flex-end; gap: 10px; }
    .composer-box {
      flex: 1; display: flex; align-items: center; gap: 10px;
      background: var(--surface); border: 1.5px solid var(--line-strong);
      border-radius: var(--r-lg); padding: 6px 6px 6px 16px;
      transition: border-color .14s ease, box-shadow .14s ease;
    }
    .composer-box:focus-within { border-color: var(--blue); box-shadow: 0 0 0 4px var(--blue-soft); }
    .composer-input { flex: 1; border: none; outline: none; background: none; font-size: 14.5px; padding: 9px 0; color: var(--ink); }
    .composer-input::placeholder { color: var(--ink-4); }
    .composer-send {
      width: 40px; height: 40px; border-radius: 12px; border: none; flex-shrink: 0;
      background: var(--blue); color: #fff; display: grid; place-items: center;
      transition: all .14s ease; box-shadow: var(--sh-blue);
    }
    .composer-send:hover { background: var(--blue-600); }
    .composer-send:disabled { background: var(--line-strong); box-shadow: none; cursor: default; }
    .composer-icon-btn { width: 40px; height: 40px; border-radius: 12px; border: none; background: none; color: var(--ink-3); display: grid; place-items: center; transition: all .12s; }
    .composer-icon-btn:hover { background: var(--surface-3); color: var(--blue); }

    /* ============================================================
       HOME BOARD
       ============================================================ */
    .board { max-width: 1180px; margin: 0 auto; padding: 6px 0 30px; }
    .board-hero {
      background:
        radial-gradient(120% 140% at 88% -10%, rgba(47,107,255,.14) 0%, rgba(47,107,255,0) 50%),
        linear-gradient(160deg, #1B47B8 0%, #2F6BFF 58%, #4F86FF 100%);
      border-radius: var(--r-xl); padding: 34px 36px; color: #fff;
      position: relative; overflow: hidden; box-shadow: var(--sh-lg);
    }
    .board-hero::after {
      content: ""; position: absolute; right: -40px; bottom: -60px;
      width: 280px; height: 280px; border-radius: 50%;
      background: radial-gradient(circle, rgba(255,255,255,.16) 0%, rgba(255,255,255,0) 70%);
    }
    .bh-eyebrow { font-size: 12.5px; font-weight: 700; opacity: .85; letter-spacing: 0.04em; }
    .bh-title { font-size: 30px; font-weight: 800; margin: 9px 0 8px; letter-spacing: -0.03em; line-height: 1.18; }
    .bh-sub { font-size: 14.5px; opacity: .9; line-height: 1.6; max-width: 460px; }
    .bh-cta { margin-top: 22px; display: flex; gap: 11px; flex-wrap: wrap; position: relative; z-index: 2; }
    .bh-btn {
      display: inline-flex; align-items: center; gap: 8px;
      background: #fff; color: var(--blue-ink); font-weight: 800; font-size: 14px;
      padding: 13px 20px; border: none; border-radius: var(--r-md);
      box-shadow: 0 8px 22px rgba(0,0,0,.18); transition: transform .13s ease;
    }
    .bh-btn:hover { transform: translateY(-2px); }
    .bh-btn.ghost { background: rgba(255,255,255,.16); color: #fff; box-shadow: none; }
    .bh-btn.ghost:hover { background: rgba(255,255,255,.26); }

    .board-row { display: flex; align-items: baseline; justify-content: space-between; margin: 28px 0 4px; }
    .board-row h2 { font-size: 18px; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: var(--ink); }
    .board-row .link { font-size: 13px; font-weight: 700; color: var(--blue); background: none; border: none; display: flex; align-items: center; gap: 4px; }
    .board-row .link:hover { color: var(--blue-700); }

    .stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 20px; }
    .stat-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-md); padding: 16px 18px; box-shadow: var(--sh-xs); }
    .stat-ic { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; margin-bottom: 11px; font-size: 17px; }
    .stat-v { font-size: 23px; font-weight: 800; letter-spacing: -0.02em; font-family: var(--mono); color: var(--ink); }
    .stat-k { font-size: 12.5px; color: var(--ink-3); font-weight: 600; margin-top: 1px; }

    .recipe-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .r-tile {
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg);
      overflow: hidden; box-shadow: var(--sh-xs); transition: all .16s ease; text-align: left;
      cursor: pointer; display: flex; flex-direction: column;
    }
    .r-tile:hover { box-shadow: var(--sh-md); transform: translateY(-3px); border-color: var(--line-strong); }
    .r-tile-hero { height: 116px; position: relative; }
    .r-tile-badge {
      position: absolute; top: 10px; left: 10px;
      display: inline-flex; align-items: center; gap: 5px;
      font-size: 11px; font-weight: 700; padding: 4px 9px; border-radius: var(--r-pill);
      background: rgba(255,255,255,.92); backdrop-filter: blur(4px); box-shadow: var(--sh-xs);
    }
    .badge-cart { color: var(--amber-ink); }
    .badge-done { color: var(--green-ink); }
    .r-tile-body { padding: 13px 15px 15px; flex: 1; display: flex; flex-direction: column; }
    .r-tile-name { font-size: 15px; font-weight: 800; letter-spacing: -0.02em; color: var(--ink); }
    .r-tile-intro { font-size: 12.5px; color: var(--ink-3); margin: 5px 0 11px; line-height: 1.5;
      overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; flex: 1; }
    .r-tile-foot { display: flex; gap: 12px; align-items: center; font-size: 11.5px; color: var(--ink-3); font-weight: 600; }
    .r-tile-foot span { display: flex; align-items: center; gap: 4px; }

    .recipe-list { display: flex; flex-direction: column; gap: 8px; }
    .r-listrow {
      display: flex; align-items: center; gap: 14px;
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-md);
      padding: 12px 16px; box-shadow: var(--sh-xs); transition: all .14s ease; text-align: left;
    }
    .r-listrow:hover { box-shadow: var(--sh-sm); border-color: var(--line-strong); }
    .r-listrow-thumb { width: 46px; height: 46px; border-radius: 11px; flex-shrink: 0; }
    .r-listrow-name { font-size: 14.5px; font-weight: 700; color: var(--ink); }
    .r-listrow-intro { font-size: 12px; color: var(--ink-3); margin-top: 2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width: 420px; }

    /* ============================================================
       KITCHEN
       ============================================================ */
    .kitchen { max-width: 980px; margin: 0 auto; padding: 6px 0 30px; }
    .k-panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); box-shadow: var(--sh-xs); margin-bottom: 18px; overflow: hidden; }
    .k-panel-head { padding: 18px 22px; border-bottom: 1px solid var(--line-2); display: flex; align-items: center; gap: 12px; }
    .k-panel-ic { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; font-size: 18px; }
    .k-panel-title { font-size: 15.5px; font-weight: 800; color: var(--ink); }
    .k-panel-sub { font-size: 12.5px; color: var(--ink-3); margin-top: 1px; }
    .k-panel-body { padding: 18px 22px 22px; }

    .ing-chips { display: flex; flex-wrap: wrap; gap: 9px; }
    .k-ing {
      display: inline-flex; align-items: center; gap: 8px;
      background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--r-pill);
      padding: 8px 14px; font-size: 13.5px; font-weight: 600; color: var(--ink);
    }
    .k-ing .amt { font-family: var(--mono); font-size: 12px; color: var(--ink-2); background: var(--surface-3); padding: 2px 8px; border-radius: var(--r-pill); }
    .k-ing .x { width: 19px; height: 19px; border-radius: 50%; border: none; background: none; color: var(--ink-4); display: grid; place-items: center; }
    .k-ing .x:hover { background: var(--rose-soft); color: var(--rose); }
    .k-add {
      display: inline-flex; align-items: center; gap: 6px;
      background: none; border: 1.5px dashed var(--line-strong); color: var(--ink-3);
      border-radius: var(--r-pill); padding: 8px 15px; font-size: 13px; font-weight: 600;
    }
    .k-add:hover { border-color: var(--blue); color: var(--blue); }

    .pref-list { display: flex; flex-direction: column; gap: 8px; }
    .pref-row {
      display: flex; align-items: center; gap: 11px;
      background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--r-md); padding: 11px 14px;
    }
    .pref-ic { width: 24px; height: 24px; border-radius: 7px; display: grid; place-items: center; flex-shrink: 0; font-size: 14px; }
    .pref-tx { font-size: 13.8px; font-weight: 600; color: var(--ink); }
    .pref-row .x { margin-left: auto; width: 22px; height: 22px; border-radius: 6px; border: none; background: none; color: var(--ink-4); display: grid; place-items: center; }
    .pref-row .x:hover { background: var(--rose-soft); color: var(--rose); }

    .complete-line { display: flex; align-items: center; gap: 10px; padding: 9px 0; font-size: 13.5px; border-bottom: 1px solid var(--line-2); }
    .complete-line .nm { font-weight: 700; }
    .complete-line .chg { margin-left: auto; font-family: var(--mono); font-size: 12.5px; color: var(--ink-2); }
    .complete-line .chg b { color: var(--green-ink); }
    .cl-ic { width: 22px; height: 22px; border-radius: 6px; display: grid; place-items: center; flex-shrink: 0; }

    /* ============================================================
       MISC
       ============================================================ */
    .empty { text-align: center; padding: 50px 20px; color: var(--ink-3); }
    .empty-ic { width: 60px; height: 60px; border-radius: 16px; background: var(--surface-3); display: grid; place-items: center; margin: 0 auto 16px; color: var(--ink-4); font-size: 26px; }
    .fade-up { animation: fadeUp .42s cubic-bezier(.16,1,.3,1) both; }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .spin { animation: spin 0.9s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .divider-soft { height: 1px; background: var(--line-2); margin: 14px 0; }
    .tag { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 700; padding: 3px 9px; border-radius: var(--r-pill); }
    .tag-blue { background: var(--blue-soft); color: var(--blue-ink); }
    .tag-green { background: var(--green-soft); color: var(--green-ink); }
    .tag-amber { background: var(--amber-soft); color: var(--amber-ink); }

    .sb-nav-item, .sb-brand-name, .sb-brand-sub, .topbar-title, .topbar-sub,
    .bh-btn, .chip, .suggest-chip, .r-tile-badge, .tag, .r-tile-foot span,
    .rc-meta-k, .rc-meta-v, .board-row h2, .board-row .link, .k-panel-title,
    .sb-recipe-name, .stat-k, .stat-v, .topbar-status { white-space: nowrap; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────── SESSION STATE ───────────────────────────
SESSION_DEFAULTS = {
    "step": 1,
    "image_bytes": None,
    "mime_type": None,
    "vision_result": None,
    "servings": None,
    "extra_requests": None,
    "recipe_result": None,
    "chat_history": [],  # [{"role": "ai"|"user", "content": str}]
    "recipe_confirmed": False,
    "awaiting_revision": False,
    "reanalyze_pending": False,
    "viewing_recipe": None,
    # 장바구니 완료 처리 (채팅 내 — 하위 호환)
    "cart_selected_path": None,
    "cart_completion_result": None,
    "cart_source_edit_mode": False,
    "cart_source_edit_data": None,
    # 사이드바 저장 레시피 → 채팅 로드 트리거
    "load_recipe_pending": None,
    # ── 3-뷰 구조 (신규) ──
    "view": "home",
    "kitchen_ingredients": None,    # None = 미초기화 (init 시 source.md 로드)
    "kitchen_preferences": None,    # None = 미초기화
    "adding_pref_mode": False,
    "home_layout": "grid",
    "kitchen_complete_target": None,
    "kitchen_complete_result": None,
    "kitchen_source_edit_mode": False,
    "kitchen_source_edit_data": None,
}


def init_session_state():
    for key, val in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = [] if isinstance(val, list) else val
    # kitchen 재료/취향이 미초기화(None)면 source.md에서 로드한다.
    if st.session_state.get("kitchen_ingredients") is None or st.session_state.get("kitchen_preferences") is None:
        _src = parse_source_md_to_data()
        if st.session_state.get("kitchen_ingredients") is None:
            st.session_state["kitchen_ingredients"] = list(_src.get("ingredients", []))
        if st.session_state.get("kitchen_preferences") is None:
            st.session_state["kitchen_preferences"] = list(_src.get("user_preferences", []))


init_session_state()


# ─────────────────────────── 공통 헬퍼 ───────────────────────────
DIFFICULTY_LABELS = {"easy": "쉬움", "medium": "보통", "hard": "어려움"}


def scroll_to_bottom():
    """리렌더링 후 채팅 최하단으로 스크롤한다."""
    components.html(
        "<script>"
        "var m=window.parent.document.querySelector('[data-testid=\"stMain\"]');"
        "if(m)m.scrollTo({top:m.scrollHeight,behavior:'smooth'});"
        "</script>",
        height=0,
        scrolling=False,
    )


def get_ai_client():
    """config.json의 provider에 따라 Groq 또는 Gemini 클라이언트를 반환한다."""
    provider = _get_provider()
    if provider == "gemini":
        try:
            import google.generativeai as genai  # noqa: PLC0415
        except ImportError:
            st.error("Gemini 사용을 위해 'pip install google-generativeai'를 실행하세요.")
            st.stop()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 키를 추가해주세요.")
            st.stop()
        genai.configure(api_key=api_key)
        return None  # Gemini는 전역 설정으로 동작
    else:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY가 설정되지 않았습니다. .env 파일에 키를 추가한 뒤 다시 실행해주세요.")
            st.stop()
        return Groq(api_key=api_key)


def get_groq_client():
    """하위 호환용 alias. get_ai_client()를 사용한다."""
    return get_ai_client()


def handle_api_error(e: Exception):
    """API 호출 예외를 분류해 사용자 메시지를 출력하고 흐름을 중단한다."""
    err_text = str(e).lower()
    is_rate_limited = (
        "429" in err_text
        or "quota" in err_text
        or "resource_exhausted" in err_text
        or "rate limit" in err_text
        or "too many requests" in err_text
    )
    provider = _get_provider()
    if is_rate_limited:
        label = "Gemini" if provider == "gemini" else "Groq"
        st.error(f"현재 {label} API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
    else:
        st.error("요청 처리 중 오류가 발생했습니다.")
        st.exception(e)
    st.stop()


def reset_all():
    """채팅/완료 처리 관련 session_state를 초기화하고 홈으로 되돌린다.

    kitchen_ingredients/preferences는 None으로 두어 다음 init 시 source.md에서 재로드한다.
    """
    for key, default in {
        "step": 1,
        "image_bytes": None,
        "mime_type": None,
        "vision_result": None,
        "servings": None,
        "extra_requests": None,
        "recipe_result": None,
        "chat_history": [],
        "recipe_confirmed": False,
        "awaiting_revision": False,
        "reanalyze_pending": False,
        "viewing_recipe": None,
        "cart_selected_path": None,
        "cart_completion_result": None,
        "cart_source_edit_mode": False,
        "cart_source_edit_data": None,
        "load_recipe_pending": None,
        "view": "home",
        "kitchen_ingredients": None,
        "kitchen_preferences": None,
        "adding_pref_mode": False,
        "home_layout": "grid",
        "kitchen_complete_target": None,
        "kitchen_complete_result": None,
        "kitchen_source_edit_mode": False,
        "kitchen_source_edit_data": None,
    }.items():
        st.session_state[key] = [] if isinstance(default, list) else default


def fmt_ingredient(ing):
    """재료 객체({"name","amount"})를 "재료(단위)" 문자열로 변환한다."""
    if isinstance(ing, dict):
        name = ing.get("name", "")
        amount = ing.get("amount", "")
        return f"{name}({amount})" if amount else name
    return str(ing)


def add_ai_message(content: str):
    """AI 메시지를 chat_history에 추가한다. 직전 AI 메시지와 중복이면 추가하지 않는다."""
    history = st.session_state["chat_history"]
    if history and history[-1]["role"] == "ai" and history[-1]["content"] == content:
        return
    history.append({"role": "ai", "content": content})


def add_user_message(content: str):
    """사용자 메시지를 chat_history에 추가한다."""
    st.session_state["chat_history"].append({"role": "user", "content": content})


def render_chat_history():
    """chat_history 전체를 순서대로 렌더링한다.

    - AI 버블 content는 HTML(레시피 카드 등)을 포함할 수 있다.
    - USER 버블 content는 반드시 html.escape() 처리한다.
    """
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "ai":
            st.markdown(
                f'''
            <div class="msg-ai">
                <div class="msg-ai-avatar">🍽️</div>
                <div class="bubble-ai">{msg["content"]}</div>
            </div>''',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'''
            <div class="msg-user">
                <div class="bubble-user">{html.escape(str(msg["content"]))}</div>
            </div>''',
                unsafe_allow_html=True,
            )


def build_recipe_card_html(recipe: dict) -> str:
    """레시피 dict를 AI 버블 안에 들어갈 레시피 카드 HTML로 변환한다.

    missing_ingredients 기준으로 재료를 have(초록)/missing(앰버)으로 구분한다.
    모든 텍스트 필드는 html.escape() 처리한다.
    """
    dish_name = html.escape(str(recipe.get("dish_name") or "레시피"))
    introduction = html.escape(str(recipe.get("introduction") or ""))
    cooking_time = html.escape(str(recipe.get("cooking_time") or "-"))
    difficulty = recipe.get("difficulty") or ""
    difficulty_kor = html.escape(DIFFICULTY_LABELS.get(difficulty, difficulty or "-"))
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "⚪")
    servings_val = recipe.get("servings")
    servings_label = f"{html.escape(str(servings_val))}인분" if servings_val else "-"

    missing_names: set = set()
    for m in (recipe.get("missing_ingredients") or []):
        missing_names.add(_parse_ingredient_string(str(m))["name"])

    ingredients = recipe.get("ingredients") or []
    if ingredients:
        pills_html = ""
        for ing in ingredients:
            parsed = _parse_ingredient_string(fmt_ingredient(ing))
            name = html.escape(parsed["name"])
            amount = html.escape(parsed["amount"])
            is_missing = parsed["name"] in missing_names
            pill_cls = "ing-pill missing" if is_missing else "ing-pill have"
            check_mark = "✕" if is_missing else "✓"
            pills_html += (
                f'<div class="{pill_cls}">'
                f'<div class="ing-check">{check_mark}</div>'
                f'<span class="ing-name">{name}</span>'
                f'<span class="ing-amt">{amount}</span>'
                f'</div>'
            )
        ingredients_html = f'<div class="ing-grid">{pills_html}</div>'
    else:
        ingredients_html = '<p style="color:var(--ink-3);font-size:0.88rem">재료 정보 없음</p>'

    steps = recipe.get("steps") or []
    if steps:
        steps_html = "".join(
            f'<div class="step-item">'
            f'<div class="step-num">{i}</div>'
            f'<div>{html.escape(str(step_text))}</div>'
            f'</div>'
            for i, step_text in enumerate(steps, start=1)
        )
    else:
        steps_html = '<div class="step-item">조리 단계 정보가 없습니다.</div>'

    intro_html = (
        f'<div class="rc-intro">{introduction}</div>'
        if introduction else ""
    )

    return f"""<div class="recipe-card">
<div class="rc-head">
  <div class="rc-eyebrow">레시피 AI</div>
  <div class="rc-title">{dish_name}</div>
  {intro_html}
</div>
<div class="rc-meta">
  <div class="rc-meta-item">
    <span class="rc-meta-ic">⏱</span>
    <div><span class="rc-meta-k">조리 시간</span><span class="rc-meta-v">{cooking_time}</span></div>
  </div>
  <div class="rc-meta-item">
    <span class="rc-meta-ic">{difficulty_emoji}</span>
    <div><span class="rc-meta-k">난이도</span><span class="rc-meta-v">{difficulty_kor}</span></div>
  </div>
  <div class="rc-meta-item">
    <span class="rc-meta-ic">👥</span>
    <div><span class="rc-meta-k">인분</span><span class="rc-meta-v">{servings_label}</span></div>
  </div>
</div>
<div class="rc-section">
  <div class="rc-section-title">🧺 재료</div>
  {ingredients_html}
</div>
<div class="rc-section">
  <div class="rc-section-title">👩‍🍳 조리법</div>
  {steps_html}
</div>
</div>"""


def _save_kitchen_to_source():
    """현재 session_state의 kitchen 재료/취향을 source.md에 저장한다."""
    save_source_data_to_md({
        "ingredients": st.session_state.get("kitchen_ingredients") or [],
        "user_preferences": st.session_state.get("kitchen_preferences") or [],
    })


# ═══════════════════════════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # 브랜드
        st.markdown(
            """
            <div class="sb-brand">
              <div class="sb-logo">🍽️</div>
              <div>
                <div class="sb-brand-name">레시피 AI</div>
                <div class="sb-brand-sub">음식 AI 비서</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 새 레시피 버튼
        if st.button("📷  새 레시피", key="sb_new_recipe", use_container_width=True, type="primary"):
            st.session_state["view"] = "chat"
            st.session_state["step"] = 1
            st.session_state["chat_history"] = []
            st.session_state["image_bytes"] = None
            st.session_state["mime_type"] = None
            st.session_state["vision_result"] = None
            st.session_state["servings"] = None
            st.session_state["extra_requests"] = None
            st.session_state["recipe_result"] = None
            st.session_state["recipe_confirmed"] = False
            st.session_state["awaiting_revision"] = False
            st.session_state["reanalyze_pending"] = False
            st.session_state["viewing_recipe"] = None
            st.session_state["cart_selected_path"] = None
            st.session_state["cart_completion_result"] = None
            st.rerun()

        # ── 네비게이션 ──
        _src_count = len(st.session_state.get("kitchen_ingredients") or [])
        _chat_count = 1 if st.session_state.get("chat_history") else 0
        _cur_view = st.session_state.get("view", "home")

        nav_items = [
            ("home", "🏠", "홈", None),
            ("chat", "💬", "채팅", _chat_count if _chat_count else None),
            ("kitchen", "🥬", "내 주방", _src_count if _src_count else None),
        ]
        for view_key, icon, label, count in nav_items:
            is_active = _cur_view == view_key
            btn_label = f"{icon} {label}" + (f"  ({count})" if count else "")
            if st.button(
                btn_label,
                key=f"nav_{view_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["view"] = view_key
                st.rerun()

        st.markdown('<div class="sb-section-label">저장된 레시피</div>', unsafe_allow_html=True)

        # ── 저장된 레시피 목록 (장바구니 + 보관함) ──
        _cart_items = list_cart_items()
        _all_items = []
        for ci in _cart_items:
            _all_items.append({"path": ci["path"], "dish_name": ci["dish_name"], "data": ci["data"], "kind": "cart"})
        for rf in sorted(glob.glob(f"{COMPLETED_JSON_DIR}/*.json"), reverse=True):
            try:
                with open(rf, encoding="utf-8") as _f:
                    _rd = json.load(_f)
                _all_items.append({
                    "path": rf,
                    "dish_name": _rd.get("dish_name", os.path.basename(rf)),
                    "data": _rd,
                    "kind": "library",
                })
            except Exception:
                pass

        if not _all_items:
            st.caption("아직 저장된 레시피가 없어요.")
        else:
            for _item in _all_items[:10]:
                _emoji = "🛒" if _item["kind"] == "cart" else "✅"
                _bn = os.path.basename(_item["path"])
                _label = f"{_emoji} {str(_item['dish_name'])[:14]}"
                if st.button(_label, key=f"sb_recipe_{_bn}", use_container_width=True):
                    st.session_state["view"] = "chat"
                    st.session_state["load_recipe_pending"] = _item["data"]
                    st.session_state["viewing_recipe"] = _item["path"]
                    if _item["kind"] == "cart":
                        st.session_state["cart_selected_path"] = _item["path"]
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 홈 보드
# ═══════════════════════════════════════════════════════════════════════════
def _render_recipe_tile(recipe: dict, path: str, kind: str, key_prefix: str = ""):
    """홈 보드용 레시피 타일을 렌더링하고 클릭 시 채팅 뷰로 이동한다."""
    dish_name = html.escape(str(recipe.get("dish_name") or "레시피"))
    intro = html.escape(str(recipe.get("introduction") or ""))[:60]
    cooking_time = html.escape(str(recipe.get("cooking_time") or "-"))
    servings = recipe.get("servings") or "-"
    badge_cls = "badge-cart" if kind == "cart" else "badge-done"
    badge_text = "🛒 장바구니" if kind == "cart" else "✅ 완료"

    st.markdown(
        f"""
    <div class="r-tile fade-up">
      <div class="r-tile-hero ph" style="display:flex;align-items:center;justify-content:center;font-size:42px;">
        🍽️
        <span class="r-tile-badge {badge_cls}">{badge_text}</span>
      </div>
      <div class="r-tile-body">
        <div class="r-tile-name">{dish_name}</div>
        <div class="r-tile-intro">{intro}</div>
        <div class="r-tile-foot">
          <span>⏱ {cooking_time}</span>
          <span>👥 {servings}인분</span>
        </div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _bn = os.path.basename(path)
    if st.button("열기", key=f"tile_open_{key_prefix}{_bn}", use_container_width=True, type="secondary"):
        st.session_state["view"] = "chat"
        st.session_state["load_recipe_pending"] = recipe
        if kind == "cart":
            st.session_state["cart_selected_path"] = path
        st.rerun()


def render_home_view():
    # topbar
    st.markdown(
        """
    <div class="topbar">
      <div class="topbar-title">홈</div>
      <div class="topbar-sub">· 레시피 대시보드</div>
      <div class="topbar-spacer"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 통계 계산
    _cart_items = list_cart_items()
    _library_files = sorted(glob.glob(f"{COMPLETED_JSON_DIR}/*.json"), reverse=True)
    _ing_count = len(st.session_state.get("kitchen_ingredients") or [])
    _cart_count = len(_cart_items)
    _done_count = len(_library_files)
    _total_count = _cart_count + _done_count

    # 히어로 배너
    st.markdown(
        """
    <div class="board fade-up">
      <div class="board-hero">
        <div class="bh-eyebrow">오늘은 어떤 요리를 해볼까요?</div>
        <div class="bh-title">냉장고 속 음식 사진,<br>레시피로 바꿔드릴게요</div>
        <div class="bh-sub">음식 사진을 올리면 AI가 재료를 분석하고, 내 주방에 있는 재료에 맞춰 딱 맞는 한국어 레시피를 만들어 드려요.</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 히어로 CTA 버튼
    _hc1, _hc2, _hsp = st.columns([2, 2, 6])
    with _hc1:
        if st.button("📷 음식 사진으로 시작하기", use_container_width=True, type="primary", key="home_cta_new"):
            st.session_state["view"] = "chat"
            st.session_state["step"] = 1
            st.session_state["chat_history"] = []
            st.session_state["image_bytes"] = None
            st.session_state["mime_type"] = None
            st.session_state["vision_result"] = None
            st.session_state["recipe_result"] = None
            st.session_state["recipe_confirmed"] = False
            st.rerun()
    with _hc2:
        if st.button("🥬 내 주방 관리", use_container_width=True, key="home_cta_kitchen"):
            st.session_state["view"] = "kitchen"
            st.rerun()

    # 통계 카드 (4개)
    st.markdown(
        f"""
    <div class="stat-row">
      <div class="stat-card fade-up">
        <div class="stat-ic" style="background:var(--blue-soft);color:var(--blue)">📚</div>
        <div class="stat-v mono">{_total_count}</div>
        <div class="stat-k">저장된 레시피</div>
      </div>
      <div class="stat-card fade-up" style="animation-delay:.04s">
        <div class="stat-ic" style="background:var(--amber-soft);color:var(--amber-ink)">🛒</div>
        <div class="stat-v mono">{_cart_count}</div>
        <div class="stat-k">장바구니 대기</div>
      </div>
      <div class="stat-card fade-up" style="animation-delay:.08s">
        <div class="stat-ic" style="background:var(--green-soft);color:var(--green-ink)">✅</div>
        <div class="stat-v mono">{_done_count}</div>
        <div class="stat-k">완료한 요리</div>
      </div>
      <div class="stat-card fade-up" style="animation-delay:.12s">
        <div class="stat-ic" style="background:var(--surface-3);color:var(--ink-2)">🌿</div>
        <div class="stat-v mono">{_ing_count}</div>
        <div class="stat-k">보유 재료</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 장바구니 섹션 (있을 때만)
    if _cart_items:
        st.markdown('<div class="board-row"><h2>🛒 이어서 완료하기</h2></div>', unsafe_allow_html=True)
        _cols = st.columns(min(3, len(_cart_items)))
        for i, ci in enumerate(_cart_items[:3]):
            with _cols[i]:
                _render_recipe_tile(ci["data"], ci["path"], "cart", key_prefix="cart_")

    # 전체 레시피 섹션
    _all_recipes = []
    for ci in _cart_items:
        _all_recipes.append({"data": ci["data"], "path": ci["path"], "kind": "cart"})
    for rf in _library_files:
        try:
            with open(rf, encoding="utf-8") as _f:
                _rd = json.load(_f)
            _all_recipes.append({"data": _rd, "path": rf, "kind": "library"})
        except Exception:
            pass

    if _all_recipes:
        st.markdown('<div class="board-row"><h2>최근 레시피 기록</h2></div>', unsafe_allow_html=True)
        _col_n = min(3, len(_all_recipes))
        _cols = st.columns(_col_n)
        for i, r in enumerate(_all_recipes[:6]):
            with _cols[i % _col_n]:
                _render_recipe_tile(r["data"], r["path"], r["kind"])
    else:
        st.markdown(
            """
        <div class="empty">
          <div class="empty-ic">🍳</div>
          <div>아직 레시피가 없어요.<br>음식 사진을 올려서 첫 레시피를 만들어보세요!</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 내 주방
# ═══════════════════════════════════════════════════════════════════════════
def render_kitchen_view():
    from datetime import date

    # topbar
    _updated = date.today().isoformat()
    st.markdown(
        f"""
    <div class="topbar">
      <div class="k-panel-ic" style="width:34px;height:34px;background:var(--blue-soft);color:var(--blue);border-radius:10px;display:grid;place-items:center">🥬</div>
      <div>
        <div class="topbar-title">내 주방</div>
        <div class="topbar-sub">보유 재료와 취향을 관리하면 레시피가 더 정확해져요</div>
      </div>
      <div class="topbar-spacer"></div>
      <div style="font-size:12.5px;color:var(--ink-3);font-weight:600">최종 갱신 <span class="mono">{_updated}</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _cart_items = list_cart_items()

    # ── 완료 처리 대기 패널 ──
    if _cart_items:
        _comp_target = st.session_state.get("kitchen_complete_target")

        st.markdown(
            f"""
        <div class="k-panel fade-up">
          <div class="k-panel-head">
            <div class="k-panel-ic" style="background:var(--amber-soft);color:var(--amber-ink)">🛒</div>
            <div style="flex:1">
              <div class="k-panel-title">완료 처리 대기</div>
              <div class="k-panel-sub">요리를 마친 레시피를 완료하면 사용한 재료가 자동 차감돼요</div>
            </div>
            <span class="tag tag-amber">{len(_cart_items)}개</span>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        for ci in _cart_items:
            _ci_name = html.escape(str(ci.get("dish_name") or "레시피"))
            _ci_ings = len((ci.get("data") or {}).get("ingredients") or [])
            _ci_time = html.escape(str((ci.get("data") or {}).get("cooking_time") or "-"))
            _bn = os.path.basename(ci["path"])
            st.markdown(
                f"""
            <div class="r-listrow" style="margin-bottom:8px">
              <div class="r-listrow-thumb ph" style="display:grid;place-items:center;font-size:22px">🍽️</div>
              <div style="min-width:0;flex:1">
                <div class="r-listrow-name">{_ci_name}</div>
                <div class="r-listrow-intro">재료 {_ci_ings}개 · {_ci_time}</div>
              </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            if st.button("✅ 완료 처리", key=f"kitchen_complete_{_bn}", type="primary"):
                st.session_state["kitchen_complete_target"] = ci["path"]
                _sd = parse_source_md_to_data()
                _res = calculate_source_update(ci["data"], _sd)
                st.session_state["kitchen_complete_result"] = _res
                st.session_state["kitchen_source_edit_data"] = _sd
                st.session_state["kitchen_source_edit_mode"] = False
                st.rerun()

        # ── 완료 처리 결과 표시 ──
        if _comp_target and st.session_state.get("kitchen_complete_result"):
            _comp = st.session_state["kitchen_complete_result"]
            _edit_mode = st.session_state.get("kitchen_source_edit_mode", False)

            with st.container(border=True):
                st.markdown(f"**{os.path.basename(_comp_target)}** — 완료 처리")

                if not _edit_mode:
                    _used = _comp.get("used", [])
                    _blocked = _comp.get("blocked", [])
                    _missing_comp = _comp.get("missing", [])

                    if _used:
                        st.markdown("**자동 차감 가능**")
                        for _it in _used:
                            st.caption(f"- {_it['name']} {_it['amount']}: {_it['before']} → {_it['after']}")
                    if _blocked:
                        st.markdown("**자동 차감 불가**")
                        for _it in _blocked:
                            st.caption(f"- {_it['name']}: {_it['reason']}")
                    if _missing_comp:
                        st.markdown("**추가 준비 필요**")
                        for _it in _missing_comp:
                            _amt = _it.get("amount", "")
                            st.caption(f"- {_it['name']}{f'({_amt})' if _amt else ''}")

                    _kcols = st.columns(3 if (_blocked or _missing_comp) else 2)
                    with _kcols[0]:
                        if st.button("완료 확정", type="primary", use_container_width=True, key="kitchen_confirm_complete"):
                            save_source_data_to_md(_comp["updated_source"])
                            save_to_completed(_comp_target, _comp)
                            st.session_state["kitchen_complete_target"] = None
                            st.session_state["kitchen_complete_result"] = None
                            st.session_state["kitchen_source_edit_mode"] = False
                            st.session_state["kitchen_source_edit_data"] = None
                            _new_src = parse_source_md_to_data()
                            st.session_state["kitchen_ingredients"] = list(_new_src["ingredients"])
                            st.rerun()
                    if _blocked or _missing_comp:
                        with _kcols[1]:
                            if st.button("📝 재료 수정", use_container_width=True, key="kitchen_edit_src"):
                                st.session_state["kitchen_source_edit_mode"] = True
                                st.rerun()
                    with _kcols[-1]:
                        if st.button("취소", use_container_width=True, key="kitchen_cancel_complete"):
                            st.session_state["kitchen_complete_target"] = None
                            st.session_state["kitchen_complete_result"] = None
                            st.session_state["kitchen_source_edit_mode"] = False
                            st.rerun()
                else:
                    # ── 재료 수정 편집 모드 ──
                    _blocked2 = _comp.get("blocked", [])
                    _missing2 = _comp.get("missing", [])
                    _sed = st.session_state.get("kitchen_source_edit_data") or {"ingredients": [], "user_preferences": []}
                    _upd = {_i["name"]: dict(_i) for _i in _sed.get("ingredients", [])}

                    st.markdown("**📝 재료 수정**")
                    for _it in _blocked2:
                        _n = _it["name"]
                        _na = st.text_input(_n, value=_upd.get(_n, {}).get("amount", ""), key=f"k_edit_{_n}", placeholder="예: 500g, 3개")
                        _upd[_n] = {"name": _n, "amount": _na}
                    for _it in _missing2:
                        _n = _it["name"]
                        if _n not in _upd:
                            _na = st.text_input(_n, value="", key=f"k_miss_{_n}", placeholder="수량 입력 (선택)")
                            if _na:
                                _upd[_n] = {"name": _n, "amount": _na}

                    _ke1, _ke2 = st.columns(2)
                    with _ke1:
                        if st.button("저장 후 완료", type="primary", use_container_width=True, key="k_save_complete"):
                            _new_sd = {**_sed, "ingredients": list(_upd.values())}
                            with open(_comp_target, encoding="utf-8") as _f:
                                _target_recipe = json.load(_f)
                            _fr = calculate_source_update(_target_recipe, _new_sd)
                            save_source_data_to_md(_fr["updated_source"])
                            save_to_completed(_comp_target, _fr)
                            st.session_state["kitchen_complete_target"] = None
                            st.session_state["kitchen_complete_result"] = None
                            st.session_state["kitchen_source_edit_mode"] = False
                            st.session_state["kitchen_source_edit_data"] = None
                            _new_src2 = parse_source_md_to_data()
                            st.session_state["kitchen_ingredients"] = list(_new_src2["ingredients"])
                            st.rerun()
                    with _ke2:
                        if st.button("뒤로", use_container_width=True, key="k_back_edit"):
                            st.session_state["kitchen_source_edit_mode"] = False
                            st.rerun()

    # ── 보유 재료 패널 (Bug #26 수정) ──
    _ings = st.session_state.get("kitchen_ingredients") or []
    _ing_count = len(_ings)

    st.markdown(
        f"""
    <div class="k-panel fade-up" style="margin-top:18px">
      <div class="k-panel-head">
        <div class="k-panel-ic" style="background:var(--green-soft);color:var(--green-ink)">🌿</div>
        <div style="flex:1">
          <div class="k-panel-title">보유 재료</div>
          <div class="k-panel-sub">재료명(양) 형식으로 적어주세요 · 양은 g, ml로 통일</div>
        </div>
        <span class="tag tag-green">{_ing_count}개</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 재료 칩 렌더링 (Bug #26: amount 문자열을 그대로 표시. 수량/단위 분해 금지)
    if _ings:
        for i, ing in enumerate(_ings):
            _name = html.escape(str(ing.get("name", "")))
            _amount = html.escape(str(ing.get("amount", "")))
            _amt_badge = f'<span class="amt mono">{_amount}</span>' if _amount else ""
            _chip_col, _del_col = st.columns([8, 1])
            with _chip_col:
                st.markdown(
                    f"""
                <div class="k-ing">
                  <span>{_name}</span>
                  {_amt_badge}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with _del_col:
                if st.button("×", key=f"del_ing_{i}", help=f"{ing.get('name','')} 삭제"):
                    st.session_state["kitchen_ingredients"].pop(i)
                    _save_kitchen_to_source()
                    st.rerun()
    else:
        st.caption("아직 등록된 재료가 없어요.")

    # 재료 추가 입력 (Bug #26: _parse_ingredient_string 으로 단일 dict 생성)
    _ic1, _ic2 = st.columns([5, 1])
    with _ic1:
        _new_ing = st.text_input(
            "새 재료",
            key="new_ing_input",
            placeholder="예: 당근(2개)",
            label_visibility="collapsed",
        )
    with _ic2:
        if st.button("+ 추가", key="add_ing_btn", use_container_width=True):
            if _new_ing.strip():
                # Bug #26 핵심: _parse_ingredient_string() 으로 단일 dict 생성 (단위 분리 금지)
                _parsed = _parse_ingredient_string(_new_ing.strip())
                st.session_state["kitchen_ingredients"].append(_parsed)
                _save_kitchen_to_source()
                st.rerun()

    # ── 사용자 취향 패널 (Bug #27 수정) ──
    _prefs = st.session_state.get("kitchen_preferences") or []
    _pref_count = len(_prefs)
    _adding_pref = st.session_state.get("adding_pref_mode", False)

    st.markdown(
        f"""
    <div class="k-panel fade-up" style="margin-top:18px">
      <div class="k-panel-head">
        <div class="k-panel-ic" style="background:var(--blue-soft);color:var(--blue-ink)">💙</div>
        <div style="flex:1">
          <div class="k-panel-title">사용자 취향</div>
          <div class="k-panel-sub">알러지·식단·선호 맛 — 모든 레시피에 자동 반영돼요</div>
        </div>
        <span class="tag tag-blue">{_pref_count}개</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 취향 목록 렌더링
    if _prefs:
        for i, pref in enumerate(_prefs):
            _ptx = html.escape(str(pref))
            _pref_col, _pdel_col = st.columns([8, 1])
            with _pref_col:
                st.markdown(
                    f"""
                <div class="pref-row">
                  <span class="pref-ic" style="background:var(--green-soft);color:var(--green-ink)">💚</span>
                  <span class="pref-tx">{_ptx}</span>
                  <span class="tag tag-green">선호</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with _pdel_col:
                if st.button("×", key=f"del_pref_{i}", help=f"'{str(pref)[:10]}' 삭제"):
                    st.session_state["kitchen_preferences"].pop(i)
                    _save_kitchen_to_source()
                    st.rerun()
    else:
        st.caption("아직 등록된 취향이 없어요.")

    # Bug #27: 취향 추가 버튼 + 편집 모드 (편집 가능한 text_input 표시)
    if not _adding_pref:
        if st.button("+ 취향 추가", key="add_pref_btn"):
            st.session_state["adding_pref_mode"] = True
            st.rerun()
    else:
        _new_pref = st.text_input(
            "새 취향",
            key="new_pref_input",
            placeholder="예: 매운 음식 선호, 토마토 알러지",
            label_visibility="collapsed",
        )
        _pc1, _pc2 = st.columns(2)
        with _pc1:
            if st.button("추가", type="primary", use_container_width=True, key="confirm_add_pref"):
                if _new_pref.strip():
                    st.session_state["kitchen_preferences"].append(_new_pref.strip())
                    _save_kitchen_to_source()
                st.session_state["adding_pref_mode"] = False
                st.rerun()
        with _pc2:
            if st.button("취소", use_container_width=True, key="cancel_add_pref"):
                st.session_state["adding_pref_mode"] = False
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 채팅 뷰 (기존 Step 1~4 플로우)
# ═══════════════════════════════════════════════════════════════════════════
def render_chat_view():
    # topbar
    st.markdown(
        """
    <div class="topbar">
      <div class="msg-ai-avatar" style="width:34px;height:34px;border-radius:10px">🍽️</div>
      <div>
        <div class="topbar-title">레시피 AI</div>
        <div class="topbar-sub">음식 사진 → 맞춤 레시피</div>
      </div>
      <div class="topbar-spacer"></div>
      <div class="topbar-status">
        <span class="live-dot"></span>항상 활성화
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── 저장 레시피 채팅 로드 처리 ──
    _pending_recipe = st.session_state.get("load_recipe_pending")
    if _pending_recipe is not None:
        st.session_state["load_recipe_pending"] = None
        st.session_state["chat_history"] = []
        st.session_state["step"] = 4
        st.session_state["recipe_result"] = _pending_recipe
        st.session_state["recipe_confirmed"] = True
        st.session_state["awaiting_revision"] = False
        st.session_state["reanalyze_pending"] = False
        st.session_state["image_bytes"] = None
        st.session_state["mime_type"] = None
        st.session_state["vision_result"] = None
        add_ai_message("📂 저장된 레시피를 불러왔어요.")
        add_ai_message(build_recipe_card_html(_pending_recipe))
        _saved_missing = _pending_recipe.get("missing_ingredients", [])
        if _saved_missing:
            _missing_html = (
                "<b>미구매 재료:</b><br>"
                + "<br>".join(f"• {html.escape(str(_m))}" for _m in _saved_missing)
            )
            add_ai_message(_missing_html)
            _load_dish = str(_pending_recipe.get("dish_name") or "")
            with st.spinner("네이버 쇼핑 검색 중..."):
                _shop_html = build_shopping_html(_load_dish, _saved_missing)
            if _shop_html:
                add_ai_message(_shop_html)
        st.rerun()

    # ── 웰컴 메시지 (최초 1회) ──
    if not st.session_state["chat_history"]:
        add_ai_message(
            "안녕하세요! 음식 사진을 올려주시면 재료를 분석해 맞춤 레시피를 만들어 드려요. 📸"
        )

    # ── 재분석 처리 (step 분기보다 먼저) ──
    if st.session_state.get("reanalyze_pending"):
        st.session_state["reanalyze_pending"] = False
        client = get_ai_client()
        with st.spinner("이미지를 다시 분석하고 있어요..."):
            try:
                vision_result, raw = analyze_food_image(
                    client,
                    st.session_state["image_bytes"],
                    st.session_state["mime_type"],
                )
            except Exception as e:
                handle_api_error(e)
        if vision_result is None:
            add_ai_message("분석 결과를 이해하지 못했어요. 다시 시도해 주세요.")
            st.session_state["vision_result"] = vision_result
        else:
            st.session_state["vision_result"] = vision_result
            st.session_state["step"] = 2
            st.rerun()

    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

    # ── STEP 1: 이미지 업로드 ──
    if st.session_state["step"] == 1:
        render_chat_history()
        st.markdown(
            """
        <div class="upload-zone">
          <div class="upload-ic">📷</div>
          <h4>음식 사진 올리기</h4>
          <p>클릭해서 사진을 선택하세요 · JPG·PNG·WEBP · 4MB 이하</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "음식 사진 업로드",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            st.image(uploaded_file, caption="업로드한 이미지", use_container_width=True)
            if st.button("🔍 이 사진으로 분석 시작", type="primary", use_container_width=True):
                image_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0]
                if not is_within_groq_base64_request_limit(image_bytes, mime_type):
                    st.error("이미지가 너무 커요. 4MB 이하 이미지를 사용해주세요.")
                    st.stop()
                st.session_state["image_bytes"] = image_bytes
                st.session_state["mime_type"] = mime_type
                client = get_ai_client()
                with st.spinner("사진을 분석하고 있어요..."):
                    try:
                        vision_result, raw = analyze_food_image(client, image_bytes, mime_type)
                    except Exception as e:
                        handle_api_error(e)
                if vision_result is None:
                    add_ai_message("분석 결과를 이해하지 못했어요. 다시 시도해 주세요.")
                else:
                    st.session_state["vision_result"] = vision_result
                    is_food = vision_result.get("is_food", True)
                    if not is_food:
                        reason = vision_result.get("non_food_reason", "음식이 아닌 것 같아요.")
                        add_ai_message(f"🤔 {reason}")
                        st.session_state["image_bytes"] = None
                        st.session_state["mime_type"] = None
                        st.session_state["vision_result"] = None
                    else:
                        dish = vision_result.get("dish_name", "")
                        ings = vision_result.get("ingredients", [])
                        ing_text = ", ".join(str(i) for i in ings) if ings else "재료 정보 없음"
                        add_user_message("음식 사진을 올렸어요 📷")
                        add_ai_message(
                            f"<b>{html.escape(str(dish))}</b>(으)로 분석했어요! 🎉<br>"
                            f'<span class="sub">보이는 재료 — {html.escape(ing_text)}</span>'
                        )
                        st.session_state["step"] = 2
                st.rerun()

    # ── STEP 2: 인분 입력 ──
    if st.session_state["step"] == 2:
        render_chat_history()
        st.markdown('<div class="quick-row" style="margin-left:0"></div>', unsafe_allow_html=True)
        cols = st.columns(5)
        quick_servings = [("1인분", 1), ("2인분", 2), ("4인분", 4), ("6인분", 6)]
        for i, (label, val) in enumerate(quick_servings):
            with cols[i]:
                if st.button(label, key=f"serv_{val}", use_container_width=True):
                    add_user_message(label)
                    st.session_state["servings"] = val
                    st.session_state["step"] = 3
                    st.rerun()
        with cols[4]:
            if st.button("건너뛰기", key="serv_skip", use_container_width=True):
                add_user_message("인분 수는 상관없어요")
                st.session_state["servings"] = None
                st.session_state["step"] = 3
                st.rerun()
        skip_servings = st.text_input(
            "또는 직접 입력",
            key="servings_text",
            placeholder="예: 3인분",
            label_visibility="collapsed",
        )
        if st.button("입력", key="servings_submit"):
            parsed = parse_servings(skip_servings)
            add_user_message(skip_servings or "인분 수는 상관없어요")
            st.session_state["servings"] = parsed
            st.session_state["step"] = 3
            st.rerun()

    # ── STEP 3: 추가 요청 ──
    if st.session_state["step"] == 3:
        render_chat_history()
        st.markdown('<div class="quick-row" style="margin-left:0"></div>', unsafe_allow_html=True)
        quick_prefs = ["채식으로 바꿔줘", "안 맵게", "10분 이내", "설탕 줄여줘"]
        pcols = st.columns(len(quick_prefs))
        for i, label in enumerate(quick_prefs):
            with pcols[i]:
                if st.button(label, key=f"pref_{i}", use_container_width=True):
                    add_user_message(label)
                    st.session_state["extra_requests"] = label
                    st.session_state["step"] = 4
                    st.rerun()
        extra_text = st.text_input(
            "추가 요청사항",
            key="extra_text",
            placeholder="예: 안 맵게 해주세요 (없으면 건너뛰기)",
            label_visibility="collapsed",
        )
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            if st.button("입력", key="extra_submit", use_container_width=True):
                add_user_message(extra_text or "추가 요청 없음")
                st.session_state["extra_requests"] = extra_text or ""
                st.session_state["step"] = 4
                st.rerun()
        with ecol2:
            if st.button("건너뛰기", key="extra_skip", use_container_width=True):
                add_user_message("추가 요청 없음")
                st.session_state["extra_requests"] = ""
                st.session_state["step"] = 4
                st.rerun()

    # ── STEP 4: 레시피 생성 및 표시 ──
    if st.session_state["step"] == 4:
        render_chat_history()

        # 레시피가 아직 생성되지 않았으면 생성
        if st.session_state["recipe_result"] is None:
            client = get_ai_client()
            with st.spinner("레시피를 만들고 있어요..."):
                try:
                    recipe_result, raw = generate_recipe(
                        client,
                        st.session_state["vision_result"],
                        st.session_state["servings"],
                        st.session_state["extra_requests"],
                    )
                except Exception as e:
                    handle_api_error(e)
            if recipe_result is None:
                add_ai_message("레시피 생성에 실패했어요. 다시 시도해 주세요.")
            else:
                st.session_state["recipe_result"] = recipe_result
                add_ai_message("레시피가 완성됐어요! 아래에서 확인해 보세요 ✨")
                add_ai_message(build_recipe_card_html(recipe_result))
                extra = st.session_state.get("extra_requests")
                if extra:
                    client2 = get_ai_client()
                    extract_and_save_feedback(client2, extra)
                _missing = recipe_result.get("missing_ingredients", [])
                if _missing:
                    _dish = str(recipe_result.get("dish_name") or "")
                    with st.spinner("네이버 쇼핑 검색 중..."):
                        _shop_html = build_shopping_html(_dish, _missing)
                    if _shop_html:
                        add_ai_message(_shop_html)
                st.rerun()

        # 확정/수정/재분석 버튼
        if st.session_state["recipe_result"] is not None and not st.session_state["recipe_confirmed"]:
            if st.session_state.get("awaiting_revision"):
                revision_text = st.text_input(
                    "수정 요청",
                    key="revision_input",
                    placeholder="예: 더 매콤하게, 양 늘려줘",
                )
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("수정 요청 보내기", type="primary", use_container_width=True, key="send_revision"):
                        if revision_text.strip():
                            add_user_message(revision_text)
                            st.session_state["extra_requests"] = revision_text
                            st.session_state["recipe_result"] = None
                            st.session_state["awaiting_revision"] = False
                            st.rerun()
                with rc2:
                    if st.button("취소", use_container_width=True, key="cancel_revision"):
                        st.session_state["awaiting_revision"] = False
                        st.rerun()
            else:
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("✅ 레시피 확정", type="primary", use_container_width=True, key="confirm_recipe"):
                        add_user_message("레시피 확정!")
                        st.session_state["recipe_confirmed"] = True
                        _confirmed = st.session_state["recipe_result"]
                        _cart_path = save_to_cart(_confirmed)
                        st.session_state["cart_selected_path"] = _cart_path
                        add_ai_message(
                            '🛒 레시피가 저장되고 <b>장바구니</b>에 추가됐어요!<br>'
                            '<span class="sub">요리를 마치면 내 주방에서 완료 처리하고 재료를 자동 차감할 수 있어요.</span>'
                        )
                        st.rerun()
                with bc2:
                    if st.button("✏️ 수정 요청", use_container_width=True, key="request_revision"):
                        st.session_state["awaiting_revision"] = True
                        st.rerun()
                with bc3:
                    if st.button("🔄 이미지 재분석", use_container_width=True, key="reanalyze_btn"):
                        add_user_message("이미지 다시 분석해줘")
                        st.session_state["reanalyze_pending"] = True
                        st.rerun()

        # 확정 후 액션
        if st.session_state["recipe_confirmed"]:
            ac1, ac2 = st.columns(2)
            with ac1:
                if st.button("🥬 내 주방에서 완료 처리", use_container_width=True, key="go_kitchen_btn"):
                    st.session_state["view"] = "kitchen"
                    st.rerun()
            with ac2:
                if st.button("🔄 처음부터 다시", use_container_width=True, key="restart_btn"):
                    reset_all()
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # .chat-wrap 닫기
    scroll_to_bottom()


# ═══════════════════════════════════════════════════════════════════════════
# 뷰 라우팅
# ═══════════════════════════════════════════════════════════════════════════
render_sidebar()

_view = st.session_state.get("view", "home")
if _view == "home":
    render_home_view()
elif _view == "kitchen":
    render_kitchen_view()
else:  # "chat"
    render_chat_view()

st.write("")
st.caption("Groq Llama 4 Scout · 음식 사진 레시피 생성기")
