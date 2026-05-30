# 요구사항 — UI/UX 완성도 개선 + 비전 재분석 + 플로우 재편

## 요청 요약
ref3.jpg 기반 완성형 챗봇 UX로 교체, 비전 재분석 기능 추가, 포스트-레시피 플로우 확대.

---

## 1. 영향 범위
- [x] 파이프라인: build_vision_prompt() 빵/페이스트리 특화 강화
- [x] UI: 전면 CSS 교체, quick-reply 인라인 버튼, 플로우 재편

---

## 2. 파이프라인 변경 (pipeline-developer)

### 2-A. build_vision_prompt() 강화
음식 오인식 방지를 위한 세부 분석 지시 추가:
- 빵/페이스트리/파이 도우 겉면의 굽기 정도, 색감, 질감 주의
- 속 재료(과일, 크림, 잼 등)의 조리 상태(날것/졸인/구운) 구별
- 빵류 세분화: 파이, 크루아상, 타르트, 갈레트, 브리오슈, 스콘 등 명칭 구분
- 색감/광택/기포/층 구조를 기반으로 정확한 음식 명칭 판별

변경 대상: build_vision_prompt() 반환 문자열 내 응답 규칙 섹션

---

## 3. UI 변경 (ui-developer) — 전면 교체

### 3-A. CSS 디자인 (ref3.jpg 기반)
```
배경: 흰색 #FFFFFF 또는 #FAFAFA
AI 버블: 연회색 #F0F0F0, 텍스트 #1C1C1E, 좌측 정렬, 아바타 있음
USER 버블: 중간 파랑 #3B82F6 또는 #4F8EF7, 텍스트 흰색, 우측 정렬
Quick-reply 버튼: 라이트 블루 테두리 + 파란 텍스트 pill 모양, 좌측 정렬(AI 버블 아래)
채팅 하단 입력창: 둥근 pill 모양, "메시지를 입력하세요...", 전송 버튼
헤더: 봇 이름 + "레시피 AI" + 초록 상태 표시
```

### 3-B. Quick-reply 버튼 시스템
ref3.jpg의 핵심: **AI 메시지 아래에 클릭 가능한 pill 버튼이 채팅 흐름 안에 나타남**

구현 방법:
```python
def render_quick_replies(options: list[tuple[str, str]]):
    """AI 버블 바로 아래 quick-reply pill 버튼들을 렌더링.
    
    options: [(label, key), ...]
    클릭 시 user 메시지로 추가되고 해당 액션 실행.
    """
```

CSS:
```css
.quick-reply-btn {
    display: inline-block;
    border: 1.5px solid #4F8EF7;
    color: #4F8EF7;
    background: white;
    border-radius: 20px;
    padding: 7px 16px;
    margin: 4px;
    font-size: 0.93rem;
    cursor: pointer;
    font-weight: 500;
}
.quick-reply-btn:hover {
    background: #EBF3FF;
}
```

실제로는 st.button에 CSS 클래스를 적용하거나, HTML 렌더링 후 Streamlit 버튼으로 구현.

### 3-C. 헤더 컴포넌트
```python
# 상단 고정 헤더 (Streamlit 컨테이너 또는 HTML)
st.markdown('''
<div class="chat-header">
  <div class="header-avatar">🍽️</div>
  <div>
    <div class="header-name">레시피 AI</div>
    <div class="header-status">● 항상 활성화</div>
  </div>
</div>
''', unsafe_allow_html=True)
```

### 3-D. 플로우 재편

#### Step 1 (이미지 분석) 이후
AI 메시지: "{dish_name}으로 분석했어요! 보이는 재료: ..."
→ 바로 아래 quick-reply 버튼:
```
[🍳 레시피 만들기]  [🔍 다시 분석하기]
```

#### Step 2, 3 (인분/요청사항)
현재 "건너뛰기" 버튼 → quick-reply 스타일로 교체:
```
Step 2: 인분 입력창 + [건너뛰기] quick-reply
Step 3: 요청사항 입력창 + [건너뛰기] quick-reply
```

#### Step 4 (레시피 출력) 이후
AI 레시피 카드 아래 quick-reply 버튼:
```
[✅ 레시피 확정하기]  [✏️ 수정 요청하기]  [🔍 이미지 다시 분석하기]
```

### 3-E. 재분석 플로우
**세션 상태 추가:**
```python
"reanalyze_pending": False   # 재분석 트리거 플래그
```

**재분석 처리 로직:**
```
재분석 버튼 클릭
  → add_user_message("이미지 다시 분석해줘")
  → st.session_state["reanalyze_pending"] = True
  → st.session_state["recipe_result"] = None
  → st.session_state["recipe_confirmed"] = False  
  → st.session_state["awaiting_revision"] = False
  → st.rerun()

reanalyze_pending == True 처리 (렌더링 최상단):
  → st.spinner로 재분석 실행
  → analyze_food_image(client, image_bytes, mime_type) 재호출
  → vision_result 업데이트
  → add_ai_message("재분석 결과: {새 dish_name}으로 확인했어요! ...")
  → reanalyze_pending = False
  → step = 4 (기존 servings/extra_requests 유지, 레시피 재생성)
  → st.rerun()
```

재분석 후: 기존 servings/extra_requests는 유지 → step 4로 바로 이동 → 레시피 자동 재생성

### 3-F. reset_all() 업데이트
reanalyze_pending 키 포함

---

## 4. 편집 경계
- pipeline-developer: build_vision_prompt() 함수 내부만 수정 (line 73-103)
- ui-developer: line 346 이후 UI 섹션 전체 교체 (파이프라인 함수 건드리지 않음)
- 두 변경이 독립적이므로 병렬 진행 가능

---

## 5. 주의사항
- st.button 클릭 시 Streamlit 재실행 → state 변경 후 st.rerun() 필수
- quick-reply 버튼과 st.chat_input은 같은 step에서 동시 렌더 가능 (서로 다른 위젯)
- step 2, 3에서 chat_input이 비어서 전송되면 "건너뛰기"와 동일하게 처리
- 재분석 후 chat_history에 이전 분석 결과도 유지 (누적 타임라인)
