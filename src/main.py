import os
import json
# 앞서 작성한 두 파일에서 필요한 함수들을 가져옵니다.
from visual_decision import analyze_food_image
from naver_api import search_ingredients_shopping


def run_food_agent_pipeline(image_path):
    print("🚀 [Food Agent Pipeline] 작업을 시작합니다.")
    print("-" * 60)
    
    # 1단계: visual_decision.py를 통해 이미지 분석 및 재료 추출
    print(f"📷 1단계: 이미지 분석 중... ({os.path.basename(image_path)})")
    analysis_result = analyze_food_image(image_path)
    
    # 예외 처리: 음식이 아닌 경우 프로세스 중단
    if not analysis_result.get("is_food"):
        print("\n❌ 분석 실패: 음식 사진이 아닙니다. 다시 촬영해주세요.")
        return {
            "status": "fail",
            "message": "음식 사진이 아닙니다."
        }
    
    food_name = analysis_result.get("food_name")
    ingredients = analysis_result.get("ingredients", [])
    
    print(f"✅ 분석 완료! 음식 이름: [{food_name}]")
    print(f"🥕 추출된 재료 리스트: {ingredients}")
    print("-" * 60)
    
    # 2단계: naver_api.py를 통해 추출된 재료별 쇼핑 링크 검색 (6개씩)
    print("🛒 2단계: 네이버 쇼핑 API 연동 및 링크 추출 시작")
    shopping_result = search_ingredients_shopping(ingredients)
    print("-" * 60)
    
    # 3단계: 최종 결과 데이터 구조화
    final_pipeline_output = {
        "status": "success",
        "food_name": food_name,
        "ingredients": ingredients,
        "shopping_links": shopping_result
    }
    
    return final_pipeline_output


if __name__ == "__main__":
    # 테스트에 사용할 실제 햄버거 이미지 경로를 절대 경로로 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    HAMBURGER_IMAGE = os.path.abspath(os.path.join(current_dir, "..", "image", "hambuger.png"))
    # HAMBURGER_IMAGE = os.path.abspath(os.path.join(current_dir, "..", "image", "amusement.png"))
    
    if not os.path.exists(HAMBURGER_IMAGE):
        print(f"❌ 에러: 테스트 이미지 파일이 없습니다. 경로를 확인해주세요: {HAMBURGER_IMAGE}")
    else:
        # 파이프라인 전체 실행
        final_result = run_food_agent_pipeline(HAMBURGER_IMAGE)
        
        # 최종 완성된 통합 데이터 출력
        if final_result["status"] == "success":
            print("\n======================= 🎉 최종 통합 결과 화면 =======================")
            print(f"🍔 분석된 음식: {final_result['food_name']}")
            print(f"📝 전체 재료 목록: {', '.join(final_result['ingredients'])}")
            print("-" * 70)
            
            for ingredient, links_data in final_result["shopping_links"].items():
                print(f"\n🟩 [{ingredient}] 구매 링크 목록")
                
                print("  🔥 인기순 상위 3개:")
                for idx, item in enumerate(links_data["popular"], 1):
                    price = f"{int(item['lprice']):,}원" if item['lprice'] else "가격 정보 없음"
                    print(f"    {idx}. {item['title']} ({price})")
                    print(f"       🔗 {item['link']}")
                    
                print("  💸 최저가순 상위 3개:")
                for idx, item in enumerate(links_data["cheapest"], 1):
                    price = f"{int(item['lprice']):,}원" if item['lprice'] else "가격 정보 없음"
                    print(f"    {idx}. {item['title']} ({price})")
                    print(f"       🔗 {item['link']}")
            print("=======================================================================\n")
