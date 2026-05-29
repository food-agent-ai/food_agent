# food_agent

음식 사진을 업로드하면 Groq 플랫폼의 Llama 4 Scout 모델이 사진을 분석해 한국어 레시피를 생성하는 Streamlit 앱입니다.

## 사용 모델

- 플랫폼: [Groq](https://console.groq.com/)
- 모델: `meta-llama/llama-4-scout-17b-16e-instruct`
- 입력: 음식 이미지 + 사용자 선호사항 텍스트
- 출력: 앱에서 재사용할 수 있는 JSON 형식의 음식 분석 및 레시피

## 설치

Python 3.10 이상 환경을 권장합니다.

```bash
pip install streamlit python-dotenv groq
```

## Groq API 키 설정

1. [Groq Console](https://console.groq.com/)에 로그인합니다.
2. API Keys 메뉴에서 새 API 키를 생성합니다.
3. 프로젝트 루트에 `.env` 파일을 만들고 아래 값을 추가합니다.

```bash
GROQ_API_KEY=your_groq_api_key_here
```

> 기존 `GEMINI_API_KEY`는 더 이상 사용하지 않습니다.

## 실행

```bash
streamlit run src/main.py
```

실행 후 브라우저에서 음식 사진을 업로드하고, 인분과 추가 선호사항을 입력한 뒤 **레시피 생성하기** 버튼을 누르면 됩니다.

## 이미지 업로드 제한

현재 앱은 업로드한 이미지를 base64 data URL로 Groq Vision API에 전달합니다. Groq의 base64 이미지 요청 제한에 맞춰 4MB 이하 이미지를 업로드해야 합니다.

## 선택 설정: source.md

프로젝트 루트에 `source.md` 파일을 만들면 앱이 해당 내용을 추가 지침으로 읽어 모델 프롬프트에 포함합니다. 예를 들어 선호 조리 방식, 제외 재료, 출력 스타일 등을 저장해둘 수 있습니다.
