import base64
import json
import mimetypes
import os
import time

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE64_REQUEST_LIMIT_BYTES = 4 * 1024 * 1024

st.set_page_config(page_title="음식 사진 레시피 생성기", page_icon="🍽️", layout="centered")
st.title("🍽️ 음식 사진 레시피 생성기 (Groq Llama 4 Scout)")
st.write("음식 사진을 업로드하고 **레시피 생성하기** 버튼을 눌러보세요.")

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


uploaded_file = st.file_uploader(
    "음식 사진 업로드",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    st.image(uploaded_file, caption="업로드한 이미지", use_container_width=True)

st.subheader("사용자 설정")
servings = st.number_input("몇 인분으로 만들까요?", min_value=1, max_value=20, value=1, step=1)
user_preference_text = st.text_area(
    "추가 선호사항 (선택)",
    placeholder="예: 빨간 소스는 달지 않은 케첩 베이스, 사진에 없는 재료는 최대한 제외, 10분 내 조리 희망",
    help="첨부 파일 외에 매번 텍스트 선호사항을 함께 전달할 수 있습니다.",
)

source_md_content = load_source_md()
if source_md_content:
    st.caption(f"source.md 로드 완료 ({len(source_md_content)}자)")
else:
    st.caption("source.md가 없어 기본 설정만 사용합니다.")

feedback_md_content = load_feedback_md()
if feedback_md_content:
    st.caption(f"feedback.md 기억 로드 완료 ({len(feedback_md_content)}자)")

prompt = f"""
너는 음식 사진을 분석하는 요리 보조 AI다.
아래 지침, 사용자 기억 파일, 현재 요청을 반영하여 반드시 한국어로 응답하라.

━━━ 사용자 기억 파일 ━━━

[source.md] 우선순위 높음 — 사용자가 직접 관리하는 취향과 보유 재료 목록
{source_md_content if source_md_content else '(비어 있음)'}

[feedback.md] 자동 학습된 장기 취향 기억 — source.md와 충돌 시 source.md 우선 적용
{feedback_md_content if feedback_md_content else '(비어 있음)'}

━━━ 현재 요청 ━━━

- 목표 인분: {servings}인분
- 추가 요청사항: {user_preference_text.strip() if user_preference_text.strip() else '(없음)'}

━━━ 응답 규칙 ━━━

[기본]
- 반드시 한국어로만 응답한다.
- 순수 JSON 문자열만 반환한다. 마크다운 코드블록(```)이나 설명 문장 절대 포함 금지.

[음식 판별]
- 사진이 음식이 아니면 is_food를 false로 설정하고 non_food_reason에 이유를 작성한다.
- 음식이 아닌 경우 다른 필드는 모두 기본값(빈 문자열/빈 배열/false)으로 반환한다.

[취향 반영 우선순위]
- source.md > feedback.md > 추가 요청사항 순으로 적용한다.
- source.md 내용과 추가 요청사항이 충돌하면 source.md를 따른다.
- feedback.md는 source.md가 다루지 않는 영역에서만 보완적으로 반영한다.
- 각각 어디서 무엇을 반영했는지 preference_applied에 명시한다.

[재료 분석]
- 레시피 필요 재료와 source.md 보유 재료를 대조한다.
  · 레시피에 필요하고 source.md에 있는 재료 → ingredient_status.available
  · 레시피에 필요하지만 source.md에 없는 재료 → ingredient_status.missing  ← 네이버 쇼핑 검색에 사용됨
  · 대체 가능하거나 없어도 되는 재료 → ingredient_status.optional
- 사진에서 확실히 보이는 재료 → visible_ingredients
- 사진만으로 추정한 재료 → guessed_ingredients
- 사진에서 보이지 않는 양념·소스·알레르기 성분은 단정하지 않는다.

[장기 기억 후보 추출]
- 추가 요청사항에서 feedback.md에 저장할 만한 취향·패턴을 추출한다.
- 다음은 추출 대상에서 제외한다:
  · 이미 source.md 또는 feedback.md에 있는 내용
  · "이번에만", "오늘은" 같은 일회성 요청
  · 이번 레시피에만 해당하는 구체적 수치(인분, 시간 등)
- 긍정적 취향 → memory_candidates.preferences (간결한 문장)
- 회피 사항 → memory_candidates.avoidances (간결한 문장)
- 추출할 내용이 없으면 두 필드 모두 빈 배열로 반환한다.

[레시피 작성]
- 모든 재료 양은 목표 인분({servings}인분) 기준으로 계산한다.
- 조리도구(cooking_tools)와 조리기기(cooking_equipment)를 반드시 포함한다.
- 확신이 낮으면 confidence를 low로 설정하고 warnings에 불확실성을 명시한다.

━━━ JSON 스키마 ━━━

{{
  "is_food": true,
  "non_food_reason": "음식이 아닐 때만 작성, 음식이면 빈 문자열",
  "dish_guess": "음식명 후보",
  "confidence": "high | medium | low",
  "summary": "사진 기반 분석 요약 (2~3문장)",

  "visible_ingredients": ["사진에서 확실히 보이는 재료"],
  "guessed_ingredients": ["사진만으로 추정한 재료"],

  "preference_applied": {{
    "from_source_md": ["source.md에서 반영한 취향/제약 항목"],
    "from_feedback_md": ["feedback.md에서 반영한 취향 항목"],
    "from_user_request": ["이번 추가 요청사항에서 반영한 항목"]
  }},

  "recipe": {{
    "servings": {servings},
    "cooking_time": "예: 20분",
    "difficulty": "easy | medium | hard",
    "ingredients": ["재료명 + 양 (예: 닭가슴살 200g)"],
    "cooking_tools": ["예: 칼, 도마, 볼"],
    "cooking_equipment": ["예: 가스레인지, 오븐, 에어프라이어"],
    "steps": ["조리 단계 (번호 없이 문장으로)"]
  }},

  "ingredient_status": {{
    "available": ["source.md 보유 재료 중 이 레시피에 필요한 것"],
    "missing": ["이 레시피에 필요하지만 source.md에 없어 구매해야 할 재료"],
    "optional": ["대체 가능하거나 없어도 되는 선택 재료"]
  }},

  "memory_candidates": {{
    "preferences": ["feedback.md에 저장할 만한 새로운 긍정적 취향"],
    "avoidances": ["feedback.md에 저장할 만한 새로운 회피 사항"],
    "reason": "이 항목들을 후보로 선정한 이유 (없으면 빈 문자열)"
  }},

  "warnings": ["주의사항, 불확실한 재료, 알레르기 가능성 등"]
}}
""".strip()


def build_image_data_url(image_bytes, mime_type):
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_image}"


def is_within_groq_base64_request_limit(image_bytes, mime_type):
    encoded_request_size = len(build_image_data_url(image_bytes, mime_type).encode("utf-8"))
    return encoded_request_size <= GROQ_BASE64_REQUEST_LIMIT_BYTES


def generate_with_retry(client, image_bytes, mime_type, retries=3, base_delay=3):
    image_data_url = build_image_data_url(image_bytes, mime_type)

    for attempt in range(1, retries + 1):
        try:
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data_url},
                            },
                        ],
                    }
                ],
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


if st.button("레시피 생성하기", type="primary"):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        st.error(
            "GROQ_API_KEY가 설정되지 않았습니다. .env 파일에 키를 추가한 뒤 다시 실행해주세요."
        )
        st.stop()

    if uploaded_file is None:
        st.warning("먼저 음식 사진을 업로드해주세요.")
        st.stop()

    try:
        image_bytes = uploaded_file.getvalue()
        mime_type = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"

        if not is_within_groq_base64_request_limit(image_bytes, mime_type):
            st.error(
                "Groq API의 base64 이미지 요청 제한은 4MB입니다. 더 작은 이미지로 다시 업로드해주세요."
            )
            st.stop()

        client = Groq(api_key=api_key)

        with st.spinner("Groq Llama 4 Scout가 사진을 분석하고 레시피를 생성하는 중입니다..."):
            response = generate_with_retry(client, image_bytes, mime_type)

        raw_text = (response.choices[0].message.content or "").strip()

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            st.error("JSON 파싱에 실패했습니다. 모델 원문 응답을 확인해주세요.")
            st.code(raw_text or "(빈 응답)", language="text")
            st.stop()

        if not result.get("is_food", False):
            st.warning("업로드한 이미지는 음식 사진이 아닌 것으로 판단되었습니다.")
            st.write(f"**판별 사유:** {result.get('non_food_reason', '사유 없음')}")
            st.stop()

        st.success("레시피 생성이 완료되었습니다!")

        st.subheader("음식 분석 결과")
        st.write(f"**음식명 후보:** {result.get('dish_guess', '-')}")
        st.write(f"**신뢰도:** {result.get('confidence', '-')}")
        st.write(f"**요약:** {result.get('summary', '-')}")

        st.markdown("**보이는 재료**")
        for item in result.get("visible_ingredients", []):
            st.write(f"- {item}")

        st.markdown("**추정 재료**")
        for item in result.get("guessed_ingredients", []):
            st.write(f"- {item}")

        pref = result.get("preference_applied", {})
        if pref.get("from_source_md") or pref.get("from_feedback_md") or pref.get("from_user_request"):
            st.markdown("**반영된 취향/설정**")
            for item in pref.get("from_source_md", []):
                st.write(f"- [source.md] {item}")
            for item in pref.get("from_feedback_md", []):
                st.write(f"- [feedback.md] {item}")
            for item in pref.get("from_user_request", []):
                st.write(f"- [요청사항] {item}")

        recipe = result.get("recipe", {})
        st.subheader("레시피")
        st.write(f"**인분:** {recipe.get('servings', servings)}")
        st.write(f"**조리 시간:** {recipe.get('cooking_time', '-')}")
        st.write(f"**난이도:** {recipe.get('difficulty', '-')}")

        st.markdown("**필요한 재료**")
        for item in recipe.get("ingredients", []):
            st.write(f"- {item}")

        st.markdown("**필요한 조리도구**")
        for item in recipe.get("cooking_tools", []):
            st.write(f"- {item}")

        st.markdown("**필요한 조리기기**")
        for item in recipe.get("cooking_equipment", []):
            st.write(f"- {item}")

        st.markdown("**조리 단계**")
        for idx, step in enumerate(recipe.get("steps", []), start=1):
            st.write(f"{idx}. {step}")

        status = result.get("ingredient_status", {})
        st.subheader("재료 현황")

        if status.get("available"):
            st.markdown("**보유 중인 재료** ✓")
            for item in status.get("available", []):
                st.write(f"- {item}")

        if status.get("missing"):
            st.markdown("**구매 필요 재료**")
            for item in status.get("missing", []):
                st.write(f"- {item}")

        if status.get("optional"):
            st.markdown("**선택 재료**")
            for item in status.get("optional", []):
                st.write(f"- {item}")

        candidates = result.get("memory_candidates", {})
        if candidates.get("preferences") or candidates.get("avoidances"):
            st.subheader("장기 기억 후보")
            st.caption("다음 항목이 feedback.md 저장 후보로 추출되었습니다.")
            for item in candidates.get("preferences", []):
                st.write(f"- 👍 {item}")
            for item in candidates.get("avoidances", []):
                st.write(f"- 👎 {item}")

        if result.get("warnings"):
            st.subheader("주의사항")
            for item in result.get("warnings", []):
                st.write(f"- {item}")

    except Exception as e:
        err_text = str(e).lower()
        if (
            "429" in err_text
            or "quota" in err_text
            or "resource_exhausted" in err_text
            or "rate limit" in err_text
            or "too many requests" in err_text
        ):
            st.error(
                "현재 Groq API 요청 한도를 초과했습니다. 잠시 후 다시 시도하거나, 요청 간격을 늘려주세요."
            )
        else:
            st.error("요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            st.exception(e)
