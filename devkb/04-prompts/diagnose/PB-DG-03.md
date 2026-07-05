---
id: PB-DG-03
purpose: 제어/비제어 폼 입력 상태 불일치의 원인을 확률·검증 비용 순으로 진단
applies_when: 폼 입력이 갱신되지 않거나 제어/비제어 전환 경고가 발생할 때
version: "1.1"
---

# React 폼 상태 불일치 원인 진단

폼 입력 경고나 값 미갱신 증상이 재현된 상태에서 원인 후보를 정렬하고, 각 가설을 확정 또는 기각할 증거 수집 방법을 지시하는 진단 프롬프트입니다.

## 용도

`onChange` 핸들러 누락, `defaultValue`/`value` 혼합, 상태 초기화 오류, 부모 state 비동기화 중 어느 것이 원인인지 좁혀냅니다. DOM 속성과 React state를 대조해 검증합니다.

## 적용 시점

- "provided a `value` prop without an `onChange` handler" 경고 발생
- "changing an uncontrolled input to be controlled" 경고 발생
- 입력 필드에 타이핑해도 값이 반영되지 않음
- 여러 입력 필드 중 일부만 갱신됨

## 필수 입력

- 문제 폼 컴포넌트의 소스 코드 (input/textarea/select와 핸들러)
- 각 입력의 `value`, `defaultValue`, `checked`, `onChange` prop 유무
- 폼 state의 초기값 정의
- 콘솔 경고 전문

## 프롬프트 템플릿

```
다음 React 폼 상태 문제의 원인을 진단하라.

[폼 컴포넌트 코드]
<input/textarea/select와 핸들러 전체 소스>

[state 초기값]
<useState 초기화 코드>

[콘솔 경고]
<경고 전문>

다음 순서로 진단하라:

1. 원인 후보를 확률·검증비용 순으로 정렬하라:
   - (매우높음/저비용) value는 있으나 onChange 핸들러 누락
   - (높음/저비용) defaultValue와 value(또는 defaultChecked와 checked) 동시 사용
   - (중간/중간) state 초기값이 undefined → 나중에 문자열로 바뀌며 비제어→제어 전환
   - (중간/중간) 부모가 전달하는 state가 갱신되지 않아 입력이 고정됨

2. 각 가설의 확정/기각 증거를 수집하라:
   - onChange 누락: 각 입력의 onChange 존재 여부를 코드로 스캔.
     DevTools Console에서 아래로 속성 대조:
     document.querySelectorAll('input').forEach(i =>
       console.log(i.name, {value: i.value, hasOnChange: !!i.onchange}));
   - 혼합 사용: 동일 요소에 defaultValue와 value가 함께 있는지 검사
   - 비제어→제어 전환: 초기값이 undefined/null인지 확인.
     useState('')처럼 항상 정의된 초기값으로 바꿨을 때 경고가 사라지면 → 전환이 원인
   - 부모 state: React DevTools에서 부모 state 값이 타이핑 시 실제로
     바뀌는지 관찰. 변하지 않으면 → 부모 핸들러/전달 경로가 원인

3. 가장 확률 높고 검증 비용 낮은 가설부터 확정하고,
   확정된 원인과 증거를 명시하라. 기각된 가설도 근거와 함께 기록하라.
```

## 출력 계약

```
확정 원인: [예: email 입력에 value만 있고 onChange 누락]
증거: [예: DevTools 스캔에서 email의 hasOnChange가 false]
기각된 후보:
  - defaultValue/value 혼합: [기각 근거]
  - 비제어→제어 전환: [기각 근거]
다음 단계: [F-02 6단계 수정안 중 적용할 수정안 번호]
```

## 셀프 체크리스트

- [ ] 원인 후보를 확률·검증비용 순으로 정렬했는가?
- [ ] 각 입력의 onChange 존재 여부를 코드로 스캔했는가?
- [ ] DOM 속성과 React state를 대조했는가?
- [ ] state 초기값이 항상 정의되어 있는지 확인했는가?
- [ ] 확정 원인이 F-02의 수정안과 매핑되는가?
