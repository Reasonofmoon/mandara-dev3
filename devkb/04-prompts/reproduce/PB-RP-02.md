---
id: PB-RP-02
purpose: 폼 상태 오류를 최소 조건으로 반복 재현
applies_when: 제어/비제어 폼 입력 경고나 값 갱신 버그를 안정적으로 재현해야 할 때
version: "1.1"
---

# 폼 상태 오류 재현 절차 수립

제어(controlled)/비제어(uncontrolled) 입력 불일치로 발생하는 콘솔 경고와 값 갱신 버그를 최소 컴포넌트로 격리해 반복 재현하는 프롬프트입니다.

## 용도

"입력이 안 됨" "값이 안 바뀜" 같은 산발적 증상을 특정 입력 필드와 특정 상태 전이로 좁혀, 수정 전후를 비교할 수 있는 결정론적 재현 케이스를 만듭니다.

## 적용 시점

- "changing an uncontrolled input to be controlled" 경고가 뜰 때
- value는 있는데 onChange가 없어 입력이 막힐 때
- defaultValue와 value가 혼용된 컴포넌트를 의심할 때
- 특정 입력만 갱신되지 않아 원인을 좁혀야 할 때

## 필수 입력

- 문제 입력 필드의 JSX (value/defaultValue/onChange 유무)
- 초기 state 값과 초기화 시점
- 재현되는 조작 순서 (첫 렌더 직후인지, 초기화 후인지)
- 콘솔 경고 전문

## 프롬프트 템플릿

아래 지시를 AI 도구나 팀원에게 그대로 전달하세요.

```
다음 폼 상태 문제를 최소 재현 케이스로 축소하고, 재현율을 기록해줘.

[증상]
- 콘솔 경고: (전문 붙여넣기)
- 실제 동작: (예: 특정 input에 타이핑 불가 / 값 미갱신)

[재현 케이스 구성 지시]
1. 문제 입력 하나만 남긴 단일 컴포넌트로 축소해줘. 다른 필드/스타일/라이브러리는 제거.
2. 다음 네 가지 조합 중 어느 것이 경고를 유발하는지 하나씩 격리해:
   (a) value만 있고 onChange 없음
   (b) defaultValue와 value 동시 사용
   (c) 초기 state가 undefined였다가 값이 채워짐
   (d) 부모 리렌더가 value를 undefined로 되돌림
3. 각 조합에 대해 아래 DevTools 스니펫으로 input의 현재 상태를 캡처해:
   document.querySelectorAll('input').forEach(i => console.log({
     value: i.value, hasValueAttr: i.hasAttribute('value'),
     hasDefault: i.hasAttribute('defaultValue')
   }));
4. React DevTools에서 해당 컴포넌트 state와 부모가 넘기는 prop을 대조해 첫 값이 undefined인지 확인.

[재현 조건 고정]
- 재현되는 정확한 조작 순서를 1..N 단계로 적어줘.
- 첫 렌더에서만인지, 초기화 버튼 이후인지 조건을 명시.
- 10회 반복 중 경고가 몇 회 뜨는지 재현율을 기록.
```

## 출력 계약

- 단일 파일로 실행 가능한 최소 재현 컴포넌트
- 경고를 유발한 조합 (a~d 중 하나) 확정
- 재현 조작 순서(단계별) + 재현율(예: 10/10)
- 수정 검증에 쓸 "정상 기대 동작" 한 줄 정의

## 셀프 체크리스트

- [ ] 문제 입력 하나만 남긴 최소 컴포넌트인가?
- [ ] value/defaultValue/onChange 조합을 하나씩 격리했는가?
- [ ] 재현 조작 순서가 결정론적으로 기술됐는가?
- [ ] 재현율(N회 중 M회)을 기록했는가?
- [ ] 수정 후 비교할 기대 동작을 정의했는가?
