# 레시피 AI

음식 사진을 채팅창에 업로드하면 Groq Llama 4 Scout이 재료를 분석하고 맞춤 레시피를 생성하는 Streamlit 앱.

## 주요 기능

- **채팅형 레시피 생성**: 사진 업로드 → AI 분석 → 인분 설정 → 추가 요청 → 레시피 확정까지 4단계 채팅 플로우
- **장바구니 & 보관함**: 확정된 레시피를 장바구니(`cart/`)에 저장, 요리 완료 후 보관함(`completed/`)으로 이동
- **재료 자동 차감**: 완료 처리 시 source.md 보유 재료에서 사용한 재료를 자동 계산
- **네이버 쇼핑 연동**: 미구매 재료를 네이버 쇼핑에서 실시간 검색해 가격 비교 링크 제공
- **내 주방 설정 (source.md)**: 보유 재료와 식단 취향을 저장, 레시피 생성 시 자동 반영
- **장기 취향 학습 (feedback.md)**: 추가 요청에서 LLM이 장기 취향을 추출해 자동 누적
- **멀티 AI 지원**: Groq(기본) 또는 Gemini를 config.json으로 전환 가능
- **사이드바 GUI 편집기**: source.md / feedback.md를 앱 내에서 직접 확인·수정 가능

## 설치

Python 3.10 이상 환경 권장.

```bash
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일 생성:

```env
# 필수
GROQ_API_KEY=your_groq_api_key_here

# 선택: 네이버 쇼핑 API (없으면 쇼핑 검색 비활성화)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret

# 선택: Gemini 전환 시 필요
GEMINI_API_KEY=your_gemini_api_key
```

### API 키 발급

| 키 | 발급 URL |
|---|---|
| `GROQ_API_KEY` | https://console.groq.com/ → API Keys |
| `NAVER_CLIENT_ID/SECRET` | https://developers.naver.com → 애플리케이션 등록 → 검색 API |
| `GEMINI_API_KEY` | https://aistudio.google.com/ → Get API key |

## 실행

```bash
streamlit run src/main.py
```

## AI Provider 전환

기본값은 Groq. Gemini로 전환하려면 프로젝트 루트에 `config.json` 생성:

```json
{ "provider": "gemini" }
```

Groq으로 되돌리려면 `{ "provider": "groq" }` 또는 파일 삭제.

## 파일 구조

```
food_agent/
├── src/
│   └── main.py          # Streamlit 앱 진입점 (파이프라인 + UI)
├── source.md            # 보유 재료 & 취향 설정 (사이드바에서 GUI 편집 가능)
├── feedback.md          # LLM이 자동 누적하는 장기 취향 기억
├── config.json          # AI provider 설정 (groq | gemini)
├── cart/
│   └── json/            # 확정 대기 레시피 (🛒 장바구니)
├── completed/
│   └── json/            # 완료된 레시피 보관함 (✅)
└── requirements.txt
```

## 사용 흐름

1. **사진 업로드** — 음식 사진(JPG/PNG/WEBP, 4MB 이하) 선택 후 "사진 분석하기"
2. **인분 설정** — 숫자 입력 또는 건너뛰기 (기본 2인분)
3. **추가 요청** — 알러지, 난이도, 재료 제외 등 자유 입력 또는 건너뛰기
4. **레시피 확인** — 재료(보유/미구매 구분), 조리 단계, 네이버 쇼핑 링크 표시
5. **확정 or 수정** — ✅ 확정하면 장바구니 저장, ✏️ 수정 요청으로 재생성
6. **완료 처리** — 사이드바에서 장바구니 레시피 선택 → 채팅에서 완료 처리 → 재료 자동 차감

## source.md 설정

앱 사이드바의 **⚙️ 내 설정 > 🥬 보유 재료** 에서 직접 편집하거나, 파일을 직접 수정:

```markdown
## 1. 재료
입력:
- 양파(5개)
- 간장(500ml)
- 계란(10알)

## 2. 사용자 특성
입력:
- 매운 음식을 좋아해요
- 토마토 알러지가 있어요
```

재료에 양이 있으면 완료 처리 시 자동 차감됩니다.

## 이미지 제한

Groq Vision API 특성상 base64 인코딩 후 **4MB 이하** 이미지만 처리됩니다.
