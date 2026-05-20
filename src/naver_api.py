import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# ⚠️ 발급받으신 네이버 API 키를 그대로 유지합니다.
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

def get_shopping_links_by_sort(keyword, sort_type):
    """
    네이버 쇼핑 검색 공식 API를 사용하여 정렬 기준별로 상위 3개 상품을 가져옵니다.
    """
    # 🛠️ 공식 문서에 명시된 올바른 URL로 수정 (shopping.json -> shop.json)
    url = "https://openapi.naver.com/v1/search/shop.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    params = {
        "query": keyword,      # 검색어 (UTF-8 자동 인코딩)
        "display": 3,          # 한 번에 표시할 검색 결과 개수 (3개)
        "sort": sort_type      # sim: 정확도순(인기순) / asc: 가격 오름차순(최저가순)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            products = []
            
            # 응답 결과에서 items 배열을 순회합니다.
            for item in data.get("items", []):
                clean_title = item["title"].replace("<b>", "").replace("</b>", "")
                products.append({
                    "title": clean_title,
                    "lprice": item["lprice"],  # 최저가
                    "link": item["link"]        # 상품 정보 URL
                })
            return products
        else:
            # 에러 발생 시 디버깅을 위해 공식 문서의 오류 코드 정보를 함께 출력하도록 개선
            print(f"❌ 네이버 API 호출 실패 (정렬: {sort_type}, HTTP 상태 코드: {response.status_code})")
            try:
                err_data = response.json()
                print(f"   ℹ️ 상세 에러 내용: {err_data}")
            except:
                pass
            return []
            
    except Exception as e:
        print(f"❌ API 요청 중 오류 발생: {e}")
        return []

def search_ingredients_shopping(ingredients_list):
    """
    재료 리스트를 받아서 각 재료별로 정확도순(sim) 3개 + 최저가순(asc) 3개 = 총 6개의 링크를 반환합니다.
    """
    shopping_results = {}
    
    print(f"\n🛒 [네이버 쇼핑] 총 {len(ingredients_list)}개의 재료 검색을 시작합니다. (재료당 6개 링크)")
    
    for ingredient in ingredients_list:
        print(f"🔍 '{ingredient}' 검색 중...")
        
        # 1. 정확도/인기순(sim) 3개 가져오기
        popular_links = get_shopping_links_by_sort(ingredient, "sim")
        
        # 2. 가격 오름차순/최저가순(asc) 3개 가져오기 (공식 문서 기준 asc로 롤백)
        cheapest_links = get_shopping_links_by_sort(ingredient, "asc")
        
        # 3. 데이터 구조화
        shopping_results[ingredient] = {
            "popular": popular_links,
            "cheapest": cheapest_links
        }
        
    return shopping_results


# 독립 테스트용 코드
if __name__ == "__main__":
    test_ingredients = ["햄버거 패티", "체다 치즈"]
    results = search_ingredients_shopping(test_ingredients)
    print(json.dumps(results, indent=2, ensure_ascii=False))