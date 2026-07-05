---
id: PB-CL-03
purpose: 제어/비제어 폼 상태 오류 파악
applies_when: 폼 입력이 갱신되지 않거나 controlled/uncontrolled 경고가 발생할 때
version: "1.1"
---

# React 폼 상태 오류 문제 파악

입력 필드가 먹통이거나 controlled/uncontrolled 경고가 뜰 때, 각 입력의 value·onChange·초기값 상태를 정확히 기술하도록 유도하는 질문 세트입니다.

## 용도

"입력이 안 돼요" 수준의 설명을 넘어, 어떤 필드가 제어/비제어 중 어느 쪽이며 무엇이 누락됐는지 필드 단위로 좁힙니다.

## 적용 시점

- "You provided a `value` prop to a form field without an `onChange` handler" 경고
- "A component is changing an uncontrolled input to be controlled" 경고
- 입력 필드에 타이핑해도 값이 바뀌지 않음
- 폼 상태가 화면에 반영되지 않음

## 필수 입력

- 문제 입력 필드의 JSX (value / defaultValue / onChange 속성)
- 폼 상태를 관리하는 useState 또는 useRef 선언
- 콘솔 경고 메시지 전문

## 프롬프트 템플릿

아래 질문에 필드별로 답해주세요.

1. **경고 메시지 확인**
   - 콘솔에 어떤 경고가 뜨나요? "without an `onChange` handler"인가요, "uncontrolled to controlled"인가요?
   - 경고가 특정 입력 필드를 지목하나요?

2. **입력 속성 점검**
   - 문제 필드에 `value` prop이 있나요? `defaultValue`도 함께 있나요? (둘 다 있으면 위험)
   - `onChange` 핸들러가 연결되어 있나요? 핸들러가 실제로 setState를 호출하나요?
   - 초기 상태값이 `undefined`나 `null`로 시작하나요? (uncontrolled→controlled 원인)

3. **상태 관리 방식**
   - 이 필드는 useState로 관리하나요, useRef로 관리하나요, 아니면 섞여 있나요?
   - 여러 입력을 하나의 state 객체로 묶어 관리하나요? 그렇다면 `name` 속성으로 구분하나요?

4. **입력 타입 특성**
   - 문제 필드가 text/textarea인가요, checkbox/radio인가요, select(multiple 포함)인가요?
   - checkbox라면 `checked`를, select multiple이라면 배열 상태를 쓰고 있나요?

5. **재현 조건**
   - 처음부터 안 됐나요, 아니면 특정 조작(초기화·리셋·비동기 로드) 이후부터인가요?
   - 부모 컴포넌트가 값을 다시 주입하면서 상태를 덮어쓰나요?

## 출력 계약

폼 상태 문제 정의:
- 증상: [경고 메시지 / 입력 불가 / 미반영]
- 대상 필드: [필드명과 입력 타입]
- 제어 여부: [value/onChange/defaultValue 조합 상태]
- 초기값: [undefined/null 여부]
- 상태 관리: [useState / useRef / 혼합]
- 재현 조건: [최초 / 특정 조작 이후]

## 셀프 체크리스트

- [ ] 경고 메시지 유형(누락 vs 혼합)을 구분했는가?
- [ ] 각 필드의 value·onChange·defaultValue 조합을 확인했는가?
- [ ] 초기 상태값이 undefined/null인지 확인했는가?
- [ ] 입력 타입(checkbox/radio/select)별 특성을 반영했는가?
- [ ] 부모의 상태 덮어쓰기 여부를 확인했는가?
