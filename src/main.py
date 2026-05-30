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

# === 네이버 쇼핑 API ===
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ─── [OLD UI] ui-developer가 4단계 플로우로 교체 예정 (pipeline 작업 범위 외) ───
# st.set_page_config(page_title="음식 사진 레시피 생성기", page_icon="🍽️", layout="centered")
# st.title("🍽️ 음식 사진 레시피 생성기 (Groq Llama 4 Scout)")
# st.write("음식 사진을 업로드하고 **레시피 생성하기** 버튼을 눌러보세요.")

SOURCE_MD_PATH = "source.md"
FEEDBACK_MD_PATH = "feedback.md"


def load_source_md(path: str = SOURCE_MD_PATH) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


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


def generate_with_retry(client, messages: list, model: str, retries=3, base_delay=3):
    """범용 Groq chat.completions 호출 + 지수 백오프 재시도.

    - messages: Groq API messages 배열을 그대로 받는다.
      (Vision 호출은 text+image_url content, 텍스트 호출은 text content)
    - model: 사용할 모델명 (GROQ_VISION_MODEL 또는 GROQ_TEXT_MODEL)
    - rate limit(429 등) 감지 시 base_delay * 2^(attempt-1)초 대기 후 재시도.
    """
    for attempt in range(1, retries + 1):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=4096,
            )
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


# ═══════════════════════════════════════════════════════════════════════════
# UI — 채팅형 레시피 플로우 (ui-developer / ref3.jpg 완성형 챗봇)
# Step 1: 이미지 업로드 및 분석 (Call 1)
# Step 2: 인분 수 입력
# Step 3: 추가 요청사항
# Step 4: 레시피 생성 + 확정/수정/재분석 (Call 2)
# 모든 단계는 단일 채팅 타임라인(chat_history)에 누적되어 렌더링된다.
# 재분석(reanalyze_pending)은 step 분기보다 먼저 처리된다.
# ═══════════════════════════════════════════════════════════════════════════


# ─────────────────────────── PAGE CONFIG ───────────────────────────
# set_page_config는 스크립트 전체에서 최초 1회만 호출되어야 한다.
st.set_page_config(page_title="레시피 AI", page_icon="🍽️", layout="centered")


# ─────────────────────────── CSS 스타일 (ref3.jpg 기반 챗봇 UI) ───────────────────────────
st.markdown(
    """
    <style>
    /* 전체 배경 */
    .stApp, [data-testid="stAppViewContainer"] {
        background: #FFFFFF !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }

    /* 채팅 헤더 */
    .chat-header {
        display: flex; align-items: center; gap: 12px;
        padding: 14px 20px;
        border-bottom: 1px solid #F0F0F0;
        background: #FFFFFF;
        position: sticky; top: 0; z-index: 100;
    }
    .header-avatar {
        width: 42px; height: 42px;
        background: #EBF3FF;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
    }
    .header-name { font-weight: 700; font-size: 1.05rem; color: #1C1C1E; }
    .header-status { font-size: 0.8rem; color: #22C55E; margin-top: 1px; }

    /* AI 버블 */
    .msg-row-ai {
        display: flex; align-items: flex-start; gap: 10px;
        margin: 8px 0;
    }
    .avatar-ai {
        width: 34px; height: 34px; min-width: 34px;
        background: #EBF3FF; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 17px;
    }
    .bubble-ai {
        background: #F0F0F0;
        color: #1C1C1E;
        border-radius: 4px 18px 18px 18px;
        padding: 11px 15px;
        max-width: 75%;
        font-size: 0.95rem;
        line-height: 1.55;
    }

    /* USER 버블 */
    .msg-row-user {
        display: flex; justify-content: flex-end;
        margin: 8px 0;
    }
    .bubble-user {
        background: #3B82F6;
        color: #FFFFFF;
        border-radius: 18px 4px 18px 18px;
        padding: 11px 15px;
        max-width: 75%;
        font-size: 0.95rem;
        line-height: 1.55;
    }

    /* Quick-reply 버튼 행 */
    .quick-reply-row {
        display: flex; flex-wrap: wrap; gap: 8px;
        margin: 6px 0 12px 44px;
    }

    /* 레시피 카드 */
    .recipe-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 18px 20px;
        max-width: 95%;
        box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    }
    .recipe-card h3 { margin: 0 0 8px; color: #1C1C1E; font-size: 1.1rem; }
    .recipe-meta {
        display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0;
    }
    .recipe-meta-item {
        background: #EBF3FF; border-radius: 8px;
        padding: 4px 10px; font-size: 0.83rem;
        color: #3B82F6; font-weight: 600;
    }
    .ingredient-item {
        display: inline-block;
        background: #F9FAFB; border: 1px solid #E5E7EB;
        border-radius: 6px; padding: 3px 9px;
        margin: 2px; font-size: 0.88rem; color: #374151;
    }
    .step-item {
        display: flex; align-items: flex-start; gap: 10px;
        padding: 7px 0; border-bottom: 1px solid #F3F4F6;
        font-size: 0.92rem; line-height: 1.55;
    }
    .step-num {
        min-width: 22px; height: 22px;
        background: #3B82F6; color: white;
        border-radius: 50%; display: flex;
        align-items: center; justify-content: center;
        font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
        margin-top: 1px;
    }
    .shopping-link {
        display: inline-flex; align-items: center; gap: 5px;
        background: #03C75A; color: white !important;
        padding: 6px 13px; border-radius: 8px;
        text-decoration: none; font-size: 0.88rem;
        margin: 3px; font-weight: 600;
    }
    .divider { border: none; border-top: 1px solid #F0F0F0; margin: 8px 0; }

    /* Streamlit 기본 요소 숨기기/오버라이드 */
    .stFileUploader { margin-top: 8px; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────── 채팅 헤더 ───────────────────────────
st.markdown(
    """
    <div class="chat-header">
      <div class="header-avatar">🍽️</div>
      <div>
        <div class="header-name">레시피 AI</div>
        <div class="header-status">● 항상 활성화</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────── SESSION STATE 초기화 ───────────────────────────
# ─────────────────────────── 사이드바: 레시피 보관함 ───────────────────────────
with st.sidebar:
    st.markdown("### 📚 레시피 보관함")
    recipe_files = sorted(glob.glob("recipes/*.json"), reverse=True)
    if not recipe_files:
        st.caption("아직 저장된 레시피가 없어요.")
    else:
        for rf in recipe_files:
            basename = os.path.basename(rf)
            # 파일명 형식: YYYYMMDD_HHMMSS_dishname.json
            parts = basename.replace(".json", "").split("_", 2)
            if len(parts) >= 3:
                d, t, dish = parts[0], parts[1], parts[2]
                label = f"{dish}  ({d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]})"
            else:
                label = basename
            is_selected = st.session_state.get("viewing_recipe") == rf
            if st.button(
                label,
                key=f"lib_{basename}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    st.session_state["viewing_recipe"] = None
                else:
                    st.session_state["viewing_recipe"] = rf
                st.rerun()

    viewing = st.session_state.get("viewing_recipe")
    if viewing and os.path.exists(viewing):
        st.divider()
        try:
            with open(viewing, "r", encoding="utf-8") as f:
                saved = json.load(f)
            st.markdown(f"#### {saved.get('dish_name', '레시피')}")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("⏱", saved.get("cooking_time", "-"))
            _d = saved.get("difficulty", "")
            col_b.metric("📊", {"easy": "쉬움", "medium": "보통", "hard": "어려움"}.get(_d, _d or "-"))
            col_c.metric("👥", f"{saved.get('servings', '-')}인분")
            if saved.get("introduction"):
                st.caption(saved["introduction"])
            st.markdown("**재료**")
            for ing in saved.get("ingredients") or []:
                if isinstance(ing, dict):
                    st.write(f"- {ing.get('name','')}({ing.get('amount','')})")
                else:
                    st.write(f"- {ing}")
            st.markdown("**조리법**")
            for i, step in enumerate(saved.get("steps") or [], 1):
                st.write(f"{i}. {step}")
        except Exception as e:
            st.error(f"레시피 로드 실패: {e}")


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
    "reanalyze_pending": False,  # 재분석 트리거
    "viewing_recipe": None,      # 보관함에서 선택한 레시피 파일 경로
}


def init_session_state():
    for key, val in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            # 가변 기본값(list)은 매번 새 객체로 할당
            st.session_state[key] = [] if isinstance(val, list) else val


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


def get_groq_client():
    """GROQ_API_KEY로 Groq 클라이언트를 생성한다. 키가 없으면 흐름을 중단한다."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error(
            "GROQ_API_KEY가 설정되지 않았습니다. .env 파일에 키를 추가한 뒤 다시 실행해주세요."
        )
        st.stop()
    return Groq(api_key=api_key)


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
    if is_rate_limited:
        st.error("현재 Groq API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
    else:
        st.error("요청 처리 중 오류가 발생했습니다.")
        st.exception(e)
    st.stop()


def reset_all():
    """모든 session_state를 초기화하고 Step 1로 되돌린다."""
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
            <div class="msg-row-ai">
                <div class="avatar-ai">🍽️</div>
                <div class="bubble-ai">{msg["content"]}</div>
            </div>''',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'''
            <div class="msg-row-user">
                <div class="bubble-user">{html.escape(str(msg["content"]))}</div>
            </div>''',
                unsafe_allow_html=True,
            )


def build_recipe_card_html(recipe: dict) -> str:
    """레시피 dict를 AI 버블 안에 들어갈 레시피 카드 HTML로 변환한다.

    missing_ingredients는 카드에 포함하지 않는다(확정 시 별도 표시).
    모든 텍스트 필드는 html.escape() 처리한다.
    """
    dish_name = html.escape(str(recipe.get("dish_name") or "레시피"))
    introduction = html.escape(str(recipe.get("introduction") or ""))
    cooking_time = html.escape(str(recipe.get("cooking_time") or "-"))
    difficulty = recipe.get("difficulty") or ""
    difficulty_kor = html.escape(DIFFICULTY_LABELS.get(difficulty, difficulty or "-"))
    servings_val = recipe.get("servings")
    servings_label = f"{html.escape(str(servings_val))}인분" if servings_val else "-"

    # 재료 뱃지
    ingredients = recipe.get("ingredients") or []
    if ingredients:
        ingredients_html = "".join(
            f'<span class="ingredient-item">{html.escape(fmt_ingredient(ing))}</span>'
            for ing in ingredients
        )
    else:
        ingredients_html = '<span class="ingredient-item">재료 정보 없음</span>'

    # 조리 단계
    steps = recipe.get("steps") or []
    if steps:
        steps_html = "".join(
            f'<div class="step-item"><div class="step-num">{i}</div>'
            f"<div>{html.escape(str(step_text))}</div></div>"
            for i, step_text in enumerate(steps, start=1)
        )
    else:
        steps_html = '<div class="step-item">조리 단계 정보가 없습니다.</div>'

    intro_html = (
        f"<p style='color:#6B7280;font-size:0.9rem;margin:4px 0 10px'>{introduction}</p>"
        if introduction
        else ""
    )

    return f"""<div class="recipe-card">
<h3>{dish_name}</h3>
{intro_html}
<div class="recipe-meta">
  <span class="recipe-meta-item">⏱ {cooking_time}</span>
  <span class="recipe-meta-item">📊 {difficulty_kor}</span>
  <span class="recipe-meta-item">👥 {servings_label}</span>
</div>
<hr class="divider">
<p style="font-weight:600;margin:8px 0 6px">🧺 재료</p>
{ingredients_html}
<hr class="divider">
<p style="font-weight:600;margin:8px 0 6px">👩‍🍳 조리법</p>
{steps_html}
</div>"""


# ─────────────────────────── 초기 웰컴 메시지 ───────────────────────────
if not st.session_state["chat_history"]:
    add_ai_message(
        "안녕하세요! 🍳 저는 음식 사진으로 레시피를 만들어 드리는 AI예요.<br>"
        "음식 사진을 올려주시면 재료를 분석하고 맞춤 레시피를 생성해 드릴게요!"
    )


# ─────────────────────────── 재분석 처리 (step 분기보다 먼저) ───────────────────────────
if st.session_state.get("reanalyze_pending"):
    client = get_groq_client()
    vision_result = None
    try:
        with st.spinner("이미지를 다시 분석하는 중입니다..."):
            vision_result, raw = analyze_food_image(
                client,
                st.session_state["image_bytes"],
                st.session_state["mime_type"],
            )
    except Exception as e:
        handle_api_error(e)

    if vision_result is None:
        add_ai_message("재분석 중 오류가 발생했어요. 다시 시도해주세요.")
        st.session_state["reanalyze_pending"] = False
        st.rerun()

    st.session_state["vision_result"] = vision_result
    st.session_state["recipe_result"] = None
    st.session_state["recipe_confirmed"] = False
    st.session_state["awaiting_revision"] = False
    st.session_state["reanalyze_pending"] = False

    dish = vision_result.get("dish_name") or "음식"
    ings = ", ".join(str(i) for i in (vision_result.get("ingredients") or [])[:4])
    add_ai_message(
        f"🔍 재분석 완료! <b>{html.escape(str(dish))}</b>으로 확인했어요.<br>"
        f"보이는 재료: {html.escape(ings)}<br>"
        "<small style='color:#9CA3AF'>동일한 인분/요청사항으로 레시피를 다시 생성할게요.</small>"
    )
    st.session_state["step"] = 4
    st.rerun()


step = st.session_state["step"]


# ─────────────────────────── Step 1: 이미지 업로드 및 분석 ───────────────────────────
if step == 1:
    render_chat_history()
    scroll_to_bottom()

    uploaded_file = st.file_uploader(
        "음식 사진을 선택하세요",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=False,
        key="file_uploader_step1",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        st.image(uploaded_file, use_container_width=True)

    if st.button(
        "📷 사진 분석하기", type="primary", disabled=uploaded_file is None
    ):
        client = get_groq_client()
        image_bytes = uploaded_file.getvalue()
        mime_type = (
            uploaded_file.type
            or mimetypes.guess_type(uploaded_file.name)[0]
            or "image/jpeg"
        )

        if not is_within_groq_base64_request_limit(image_bytes, mime_type):
            st.error(
                "이미지가 4MB를 초과합니다. 더 작은 이미지를 사용해주세요."
            )
            st.stop()

        try:
            with st.spinner("사진을 분석하는 중입니다..."):
                vision_result, raw = analyze_food_image(client, image_bytes, mime_type)
        except Exception as e:
            handle_api_error(e)

        if vision_result is None:
            st.error("분석 실패. 모델 원문:")
            st.code(raw or "(빈 응답)", language="text")
            st.stop()

        if not vision_result.get("is_food", False):
            add_ai_message(
                "🤔 음식 사진이 아닌 것 같아요.<br>"
                f"<small style='color:#6B7280'>{html.escape(str(vision_result.get('non_food_reason') or ''))}</small><br>"
                "다른 음식 사진을 올려주세요!"
            )
            render_chat_history()
            scroll_to_bottom()
            st.stop()

        # 채팅 히스토리 업데이트
        add_user_message("(사진 업로드)")
        dish = vision_result.get("dish_name") or "음식"
        ingredients_preview = ", ".join(
            str(i) for i in (vision_result.get("ingredients") or [])[:4]
        )
        add_ai_message(
            f"<b>{html.escape(str(dish))}</b>으로 분석했어요! 🎉<br>"
            f"<small style='color:#6B7280'>보이는 재료: {html.escape(ingredients_preview)}</small>"
        )

        st.session_state["image_bytes"] = image_bytes
        st.session_state["mime_type"] = mime_type
        st.session_state["vision_result"] = vision_result
        st.session_state["step"] = 2
        st.rerun()

    st.stop()


# step >= 2: 업로드 이미지를 접힌 expander로 표시
if step >= 2 and st.session_state.get("image_bytes"):
    with st.expander("📷 업로드한 사진", expanded=False):
        st.image(st.session_state["image_bytes"], use_container_width=True)


# ─────────────────────────── Step 2: 인분 수 입력 ───────────────────────────
if step == 2:
    add_ai_message(
        "몇 인분을 만들건가요? 🍚<br>"
        "<small style='color:#9CA3AF'>예: 2인분, 3명, 4명이서 — 또는 건너뛰기</small>"
    )
    render_chat_history()
    scroll_to_bottom()

    if st.button("건너뛰기 →", key="skip_servings"):
        add_user_message("건너뛰기")
        st.session_state["servings"] = None
        st.session_state["step"] = 3
        st.rerun()

    servings_text = st.chat_input("인분 수 입력 (비워서 전송하면 건너뛰기)")
    if servings_text is not None:
        cleaned = servings_text.strip()
        add_user_message(cleaned if cleaned else "건너뛰기")
        st.session_state["servings"] = parse_servings(cleaned) if cleaned else None
        st.session_state["step"] = 3
        st.rerun()

    st.stop()


# ─────────────────────────── Step 3: 추가 요청사항 ───────────────────────────
if step == 3:
    servings_val = st.session_state.get("servings")
    servings_display = f"{servings_val}인분" if servings_val else "기본(2인분)"
    add_ai_message(
        f"알겠어요! {servings_display}으로 준비할게요 👍<br><br>"
        "추가 요청사항이 있으신가요? ✍️<br>"
        "<small style='color:#9CA3AF'>알러지, 못 먹는 재료, 난이도, 도구 제한 등 — 없으면 건너뛰기</small>"
    )
    render_chat_history()
    scroll_to_bottom()

    if st.button("건너뛰기 →", key="skip_extra"):
        add_user_message("건너뛰기")
        st.session_state["extra_requests"] = None
        st.session_state["recipe_result"] = None
        st.session_state["step"] = 4
        st.rerun()

    extra_text = st.chat_input("요청사항 입력 (비워서 전송하면 건너뛰기)")
    if extra_text is not None:
        cleaned = extra_text.strip()
        add_user_message(cleaned if cleaned else "건너뛰기")
        st.session_state["extra_requests"] = cleaned if cleaned else None
        st.session_state["recipe_result"] = None
        st.session_state["step"] = 4
        st.rerun()

    st.stop()


# ─────────────────────────── Step 4: 레시피 생성 + 확정/수정 ───────────────────────────
if step == 4:
    # recipe_result가 없으면 자동 생성 후 chat_history에 레시피 카드 추가
    if st.session_state.get("recipe_result") is None:
        client = get_groq_client()
        try:
            with st.spinner("레시피를 생성하는 중입니다..."):
                recipe, raw2 = generate_recipe(
                    client,
                    st.session_state["vision_result"],
                    st.session_state["servings"],
                    st.session_state["extra_requests"],
                )
        except Exception as e:
            handle_api_error(e)

        if recipe is None:
            st.error("레시피 생성 실패. 원문:")
            st.code(raw2 or "(빈 응답)", language="text")
            st.stop()

        st.session_state["recipe_result"] = recipe
        add_ai_message(build_recipe_card_html(recipe))
        st.rerun()

    recipe = st.session_state["recipe_result"]

    # 전체 채팅 히스토리 렌더링
    render_chat_history()
    scroll_to_bottom()

    confirmed = st.session_state["recipe_confirmed"]
    awaiting = st.session_state["awaiting_revision"]

    # 1) 확정 완료 → 처음부터 다시 버튼
    if confirmed:
        if st.button("🔄 처음부터 다시 시작", use_container_width=True):
            reset_all()
            st.rerun()

    # 2) 수정 대기 중 → 수정 요청 입력창
    elif awaiting:
        revision = st.chat_input("수정 요청을 입력하세요")
        if revision is not None and revision.strip():
            cleaned = revision.strip()
            add_user_message(cleaned)
            existing = st.session_state.get("extra_requests")
            st.session_state["extra_requests"] = (
                f"{existing} / {cleaned}" if existing else cleaned
            )
            # 레시피 재생성 트리거
            st.session_state["recipe_result"] = None
            st.session_state["awaiting_revision"] = False
            st.rerun()

    # 3) 기본 상태 → 확정/수정/재분석 quick-reply 버튼 3개
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ 레시피 확정", type="primary", use_container_width=True):
                saved_path = save_recipe(recipe)
                add_user_message("레시피 확정!")
                ai_msg = f"레시피가 저장되었어요! 📁<br><code>{html.escape(saved_path)}</code>"

                missing = recipe.get("missing_ingredients") or []
                if missing:
                    dish_name_for_search = str(recipe.get("dish_name") or "")
                    shopping_section = "<br><br><b>🛒 필요한 재료 구매하기</b>"
                    with st.spinner("네이버 쇼핑 검색 중..."):
                        for item in missing:
                            item_str = str(item)
                            products = get_shopping_items(dish_name_for_search, item_str)
                            if products:
                                shopping_section += (
                                    f'<div style="margin-top:10px">'
                                    f'<b style="font-size:0.9rem">{html.escape(item_str)}</b><br>'
                                )
                                for p in products:
                                    raw_price = str(p.get("lprice", ""))
                                    price_str = f"₩{int(raw_price):,}" if raw_price.isdigit() else raw_price
                                    p_link = html.escape(str(p["link"]), quote=True)
                                    p_title = html.escape(str(p["title"]))
                                    shopping_section += (
                                        f'<a href="{p_link}" target="_blank" style="'
                                        f'display:flex;justify-content:space-between;align-items:center;'
                                        f'background:#F8F9FA;border:1px solid #E5E7EB;border-radius:8px;'
                                        f'padding:7px 11px;margin:3px 0;text-decoration:none;color:#1C1C1E;'
                                        f'font-size:0.85rem;">'
                                        f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;'
                                        f'white-space:nowrap;margin-right:8px">{p_title}</span>'
                                        f'<span style="color:#3B82F6;font-weight:600;white-space:nowrap">'
                                        f'{price_str}</span></a>'
                                    )
                                shopping_section += "</div>"
                            else:
                                # API 키 없거나 결과 없을 때 검색 URL fallback
                                fallback_url = build_naver_shopping_url(item_str)
                                shopping_section += (
                                    f'<br><a href="{html.escape(fallback_url, quote=True)}" '
                                    f'target="_blank" class="shopping-link">'
                                    f'🛒 {html.escape(item_str)} 검색하기</a>'
                                )
                    ai_msg += shopping_section

                add_ai_message(ai_msg)
                st.session_state["recipe_confirmed"] = True
                st.rerun()
        with col2:
            if st.button("✏️ 수정 요청", use_container_width=True):
                add_user_message("수정 요청")
                add_ai_message(
                    "어떻게 수정할까요? ✏️<br>"
                    "<small style='color:#9CA3AF'>예: 채식으로 바꿔줘, "
                    "난이도 낮춰줘, 10분 이내로</small>"
                )
                st.session_state["awaiting_revision"] = True
                st.rerun()
        with col3:
            if st.button("🔍 이미지 재분석", use_container_width=True):
                add_user_message("이미지 다시 분석해줘")
                st.session_state["reanalyze_pending"] = True
                st.rerun()


