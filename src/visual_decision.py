import os
import base64
import json
from groq import Groq
from dotenv import load_dotenv

# 환경 변수에 등록한 GROQ_API_KEY를 자동으로 가져옵니다.
# 코드를 테스트할 때는 직접 "gsk_..." 형태의 문자열을 넣으셔도 됩니다.
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_food_image(image_path):
    # 1. 이미지를 Base64로 인코딩
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    # 2. 무료 오픈소스 Vision 모델(Llama 3.2 11b Vision) 호출
    # Groq에서 JSON 출력을 보장하기 위해 response_format 설정을 추가합니다.
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        response_format={ "type": "json_object" },
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": (
                            "이 사진이 음식 사진인지 판별해줘. 만약 음식이 아니라면 is_food를 false로 응답해줘. "
                            "음식이 맞다면 is_food를 true로 주고, 음식 이름(food_name)과 "
                            "이 음식을 만들기 위해 '네이버 쇼핑에서 검색하기 좋은 구체적인 재료 키워드 리스트(ingredients)'를 추출해줘. "
                            "반드시 아래의 JSON 형식만 반환하고 다른 텍스트는 절대 포함하지 마:\n"
                            "{\n"
                            "  \"is_food\": true,\n"
                            "  \"food_name\": \"음식명\",\n"
                            "  \"ingredients\": [\"재료1\", \"재료2\"]\n"
                            "}"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                    }
                ]
            }
        ]
    )
    
    # 3. 결과 JSON 파싱
    result = json.loads(response.choices[0].message.content)
    return result

if __name__ == "__main__":
    # 1. 현재 파일이 있는 src 폴더의 절대 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. os.path.abspath()로 감싸서 '..' 기호를 없애고 깨끗한 절대 경로로 만듭니다.
    AMUSEMENT_IMAGE = os.path.abspath(os.path.join(current_dir, "..", "image", "amusement.png"))
    HAMBURGER_IMAGE = os.path.abspath(os.path.join(current_dir, "..", "image", "hambuger.png"))

    # --- 테스트 1: 음식이 아닌 사진 (놀이공원) ---
    print("🔄 [테스트 1] 놀이공원 사진 분석을 시작합니다...")
    if os.path.exists(AMUSEMENT_IMAGE):
        result_1 = analyze_food_image(AMUSEMENT_IMAGE)
        print("\n================ [테스트 1] 결과 ================")
        print(json.dumps(result_1, indent=2, ensure_ascii=False))
        print("==================================================\n")
    else:
        print(f"❌ 파일을 찾을 수 없습니다: {AMUSEMENT_IMAGE}")


    # --- 테스트 2: 음식 사진 (햄버거) ---
    print("🔄 [테스트 2] 햄버거 사진 분석을 시작합니다...")
    if os.path.exists(HAMBURGER_IMAGE):
        result_2 = analyze_food_image(HAMBURGER_IMAGE)
        print("\n================ [테스트 2] 결과 ================")
        print(json.dumps(result_2, indent=2, ensure_ascii=False))
        print("==================================================\n")
    else:
        print(f"❌ 파일을 찾을 수 없습니다: {HAMBURGER_IMAGE}")