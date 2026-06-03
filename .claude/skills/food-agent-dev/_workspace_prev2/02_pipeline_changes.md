# 02 Pipeline Changes — build_vision_prompt() 강화

## 요청 요약
음식 오인식 방지를 위해 `build_vision_prompt()`의 응답 규칙에 정밀 시각 분석 지침 추가.

## 변경 파일
- `C:\research\food_agent\src\main.py` — `build_vision_prompt()` 함수 (line 73~)

## 변경 내용
기존 `━━━ 응답 규칙 ━━━` 블록 뒤, `━━━ JSON 스키마 ━━━` 블록 앞에 신규 섹션 `━━━ 정밀 시각 분석 지침 ━━━` 삽입. 3개 하위 블록 구성:

- `[빵·베이커리·페이스트리류 정밀 판별]` — 굽기 정도·윤기·층 구조·충전물 조리상태·겉면 질감 판별
- `[일반 음식 정밀 판별]` — 색감 그러데이션·조리법 시각 단서·국적 추론·저확신 시 "○○ 추정" 표기
- `[characteristics 필드 작성 기준]` — 색감/조리형태/플레이팅/추정 조리법 포함 3문장 이상, 베이커리류 겉면·굽기·충전물 명시

## 스키마 변경
**없음 (Breaking change 없음).** `━━━ JSON 스키마 ━━━` 블록(`is_food`, `non_food_reason`, `dish_name`, `ingredients`, `characteristics`)은 그대로 유지. 함수 시그니처 `build_vision_prompt() -> str` 불변.
→ ui-developer, `ingredient_extraction`, `md_export` 다운스트림 영향 없음. UI 협의 불필요.

## 호환성 검증
- `python -c "ast.parse(...)"` 통과 (syntax OK).
- 반환값은 여전히 순수 JSON 강제 지침(`마크다운 코드블록 절대 포함 금지`)을 유지 → `response_format={"type": "json_object"}` 호환 유지. 추가 텍스트는 모두 분석 지침이며 출력 형식을 바꾸지 않음.
- `반드시 한국어로 응답` 지침 유지.

## 주의점 / QA 참고
- **기존 규칙과의 문장 수 불일치**: 기존 응답 규칙은 characteristics를 "2~3문장"으로, 신규 정밀 분석 지침은 "3문장 이상"으로 안내. 의도적으로 정밀 섹션이 상향 기준을 제시하나, 동일 필드에 대해 두 기준이 공존. 향후 통일 검토 권장(이번 작업 범위는 신규 섹션 추가로 한정되어 기존 텍스트 미수정).
- 프롬프트 길이 증가로 토큰 사용량 소폭 상승. rate-limit/429 재시도 로직에는 영향 없음.

## Mock 테스트 절차 (qa-reviewer용)
1. 과일 타르트/파이 사진 업로드 → `dish_name`이 타르트·파이·갈레트 등으로 세분화되는지, characteristics에 겉면 질감·충전물 상태가 포함되는지 확인.
2. 저확신 케이스(모호한 음식) → `dish_name`에 "○○ 추정" 또는 "○○ 또는 ○○" 표기 + characteristics에 불확실 사유 명시 확인.
3. 반환 응답이 마크다운 코드블록 없는 순수 JSON인지(파싱 성공) 확인.
