# 요구사항 분석 — 채팅 UI 전환 + 레시피 확정/수정 플로우

## 1. 요청 요약
ref2.png 기반 양방향 채팅 UI로 전면 교체하고, 레시피 출력 후 확정(저장+쇼핑링크)·수정(재생성) 플로우를 추가한다.

## 2. 영향 범위
- [x] 파이프라인 변경 — save_recipe(), build_naver_shopping_url() 함수 추가
- [x] UI 변경 — 채팅 UI 전면 교체, 확정/수정 플로우 추가
- [x] 양쪽 모두 (독립적이므로 병렬 진행 가능)

## 3. 파이프라인 작업 (pipeline-developer)
파일의 `# ───── 파이프라인 오케스트레이션 ─────` 섹션 하단에 두 함수 추가.

### 3-A. save_recipe(recipe: dict) -> str
- `recipes/` 폴더 없으면 자동 생성
- 파일명: `YYYYMMDD_HHMMSS_{dish_name}.json`
  - dish_name에 파일명 불가 문자(`/\:*?"<>|`) 제거
- recipe dict를 JSON으로 저장 (indent=2, ensure_ascii=False)
- 저장된 전체 경로(str) 반환

### 3-B. build_naver_shopping_url(ingredient: str) -> str
- URL: `https://search.shopping.naver.com/search/all?query={ingredient}`
- ingredient는 urllib.parse.quote로 인코딩
- 반환: 완성된 URL 문자열

## 4. UI 작업 (ui-developer)
`src/main.py`의 UI 섹션(`# ═══ UI — 4단계 채팅형 플로우 ═══` 이하) 전면 교체.

### 4-A. 채팅 UI 구조
#### CSS 설계 (ref2.png 기반)
```css
/* 전체 배경 */
body: 흰색 또는 매우 연한 회색 (#f8f9fa)

/* AI 버블 — 좌측 */
.bubble-ai:
  배경: 흰색 (#ffffff)
  그림자: 0 2px 8px rgba(0,0,0,0.08)
  border-radius: 4px 18px 18px 18px
  최대 너비: 75%
  정렬: flex-start

/* 사용자 버블 — 우측 */  
.bubble-user:
  배경: #5B4DDB (보라/파랑)
  색상: 흰색
  border-radius: 18px 4px 18px 18px
  최대 너비: 75%
  정렬: flex-end

/* 채팅 컨테이너 */
.chat-container:
  overflow-y: auto
  padding: 16px
  display: flex
  flex-direction: column
  gap: 8px

/* 입력창 고정 */
- Streamlit의 sticky/fixed는 제한적이므로 st.container + key 패턴 사용
```

#### session_state 추가 키
```python
"chat_history": []    # list of {"role": "ai"|"user", "content": str, "type": "text"|"image"|"recipe"}
"recipe_confirmed": False   # 레시피 확정 여부
"awaiting_revision": False  # 수정 대기 중 여부
```

#### 채팅 히스토리 관리
- 각 단계 진행 시 chat_history에 메시지 추가
- 화면에는 chat_history 전체를 역할에 따라 좌/우로 렌더링
- 예시 흐름:
  ```
  [AI] 안녕하세요! 음식 사진을 올려주세요 📷
  [USER] (업로드한 이미지 썸네일)
  [AI] 김치찌개로 분석했어요! 몇 인분을 만들건가요?
  [USER] 3인분
  [AI] 추가 요청사항이 있으신가요?
  [USER] (건너뜀)
  [AI] (레시피 카드)
  ```

### 4-B. Step 1 — 이미지 업로드
- chat_history에 AI 웰컴 메시지 초기 추가
- file_uploader는 채팅 입력 위에 표시
- 분석 완료 후 chat_history에 추가:
  - USER: 업로드 이미지 썸네일
  - AI: "{{dish_name}}으로 분석했어요! 재료: {{ingredients}}"

### 4-C. Step 2 — 인분 입력
- AI 버블: "몇 인분을 만들건가요?"
- 입력창(텍스트) + "다음" 버튼 + "건너뛰기"
- 입력 후 USER 버블 추가: "{{servings}}인분" 또는 "건너뜀"

### 4-D. Step 3 — 추가 요청사항
- AI 버블: "추가 요청사항이 있으신가요?"
- 입력창 + "생성하기" + "건너뛰기"
- 입력 후 USER 버블 추가

### 4-E. Step 4 — 레시피 + 확정/수정
레시피 카드를 채팅 영역에 AI 버블로 표시 후 아래 버튼:

```
[ ✅ 레시피 확정하기 ]  [ ✏️ 수정 요청하기 ]
```

**확정 플로우 (recipe_confirmed = True)**:
1. USER 버블: "레시피 확정!"
2. recipes/ 폴더에 JSON 저장 → AI 버블: "레시피가 저장되었습니다: {경로}"
3. missing_ingredients가 있으면 AI 버블: "필요한 재료를 네이버 쇼핑에서 찾아봤어요!" + 각 재료 링크
4. "처음부터 다시" 버튼

**수정 플로우 (awaiting_revision = True)**:
1. USER 버블: "수정 요청"
2. AI 버블: "어떻게 수정할까요? 예: 채식으로, 난이도 낮춰서 등"
3. 채팅 입력창에서 수정 내용 입력 → 전송
4. USER 버블: 수정 내용
5. extra_requests 누적(기존 + " / " + 새 요청)
6. recipe_result = None, awaiting_revision = False → step 유지 → 레시피 재생성

## 5. 스키마 변경 없음 (pipeline ↔ ui 협의 불필요)
파이프라인 API는 그대로. UI에서 save_recipe()와 build_naver_shopping_url()만 호출하면 됨.

## 6. 병렬 실행 계획
- pipeline-developer: 파이프라인 섹션 하단에 함수 2개 추가 (UI 코드 건드리지 않음)
- ui-developer: UI 섹션 전면 교체 (파이프라인 함수 건드리지 않음)
- 편집 영역이 겹치지 않으므로 병렬 진행 가능

## 7. 주의사항
- Streamlit 고정 하단 입력창: native sticky 미지원 → `st.chat_input` 사용 (Streamlit 1.23+ 기본 하단 고정) 또는 JS hack
- `st.chat_input`은 항상 페이지 하단에 고정되므로 이를 활용
- st.chat_message 컴포넌트 활용 가능 (with st.chat_message("assistant"):)
- session_state["chat_history"]는 step 전환 간 보존
- recipe_confirmed = True 이후에는 확정/수정 버튼 숨김
