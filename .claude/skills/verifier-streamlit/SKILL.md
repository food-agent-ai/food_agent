---
name: verifier-streamlit
description: >
  food-agent Streamlit 앱의 변경사항을 실제 브라우저에서 검증하는 스킬.
  Python = /c/Users/jinpa/anaconda3/python.exe
  Streamlit = /c/Users/jinpa/anaconda3/Scripts/streamlit
  앱 실행 후 Chrome MCP로 브라우저를 조작해 스크린샷으로 동작을 확인한다.
---

# Streamlit 앱 Verifier

## 환경

- **Python**: `/c/Users/jinpa/anaconda3/python.exe`
- **Streamlit**: `/c/Users/jinpa/anaconda3/Scripts/streamlit`
- **앱 진입점**: `src/main.py`
- **기본 포트**: `8501` (충돌 시 `8502` 사용)
- **앱 URL**: `http://localhost:8501`

## 앱 실행 방법

```bash
# 기존 프로세스 종료
taskkill /F /IM streamlit.exe 2>nul; true

# 백그라운드로 실행
/c/Users/jinpa/anaconda3/Scripts/streamlit run src/main.py \
  --server.headless true \
  --server.port 8501 &

# 기동 대기 (5초)
sleep 5

# 정상 기동 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/
```

## Chrome MCP로 브라우저 조작

1. `tabs_context_mcp` → 탭 확인
2. `tabs_create_mcp` → 새 탭 생성
3. `navigate` → `http://localhost:8501` 이동
4. `preview_screenshot` 또는 `computer` → 스크린샷
5. 필요 시 `preview_click`, `preview_fill` 등으로 인터랙션

## 검증 체크리스트 (food-agent 공통)

- [ ] 앱이 에러 없이 뜨는가 (500 / traceback 없음)
- [ ] 사이드바가 정상 렌더링되는가
- [ ] 홈 뷰 히어로 배너가 보이는가
- [ ] "새 레시피 만들기" → 채팅 뷰 전환되는가
- [ ] 채팅 뷰에서 업로드 존이 보이는가

## 변경사항별 추가 체크 (최근 변경)

- [ ] 파일 업로드 시 "사진 분석하기" 버튼 없이 자동 분석 시작
- [ ] 분석 중 채팅 버블 안 타이핑 인디케이터(`...`) 표시
- [ ] 인분 선택 후 "N인분으로 준비할게요 👍" AI 메시지
- [ ] 퀵리플라이 칩이 pill 스타일·좌측 정렬
- [ ] 헤더 gap 없음 (topbar가 상단에 바로 붙음)
- [ ] 채팅 영역 좌우 여백 존재
- [ ] 사이드바 레시피 아이템: "열기" 버튼 없이 아이템 자체가 클릭됨
