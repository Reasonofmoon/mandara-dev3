---
id: PB-VF-02
purpose: 제어/비제어 폼 상태 수정이 경고를 없애고 입력 동작을 정상화했는지 검증
applies_when: 폼 상태 오류(F-02) 수정을 적용한 뒤 입력·제출 동작과 회귀를 확인할 때
version: "1.1"
---

# 제어 폼 상태 수정 검증

value/onChange 정합성, 제어·비제어 혼합 제거 등의 폼 수정을 적용한 뒤, 콘솔 경고가 사라지고 모든 입력 유형(텍스트·체크박스·라디오·셀렉트)이 정상 동작하며 제출 값이 기대대로 수집되는지 확인하는 검증 프롬프트입니다.

## 용도

F-02 플로우의 6단계(수정) 이후, 제어 입력 경고 소멸과 폼 상호작용의 정확성을 회귀 테스트로 보증합니다.

## 적용 시점

- "changing an uncontrolled input to be controlled" 경고를 수정한 직후
- onChange 핸들러를 추가/보완한 직후
- 다중 입력 필드 동기화 로직을 변경했을 때

## 필수 입력

- 수정한 폼 컴포넌트 경로
- 폼 필드 목록과 각 필드의 입력 유형
- 제출 시 기대되는 payload 형태

## 프롬프트 템플릿

아래 폼 수정에 대해 제어 상태 정합성과 입력 동작을 검증하고 회귀 여부를 확인해줘.

**폼:** [컴포넌트/파일]
**필드:** [name, email, agree(checkbox), role(radio), tags(multi-select)]

1. **성공 기준 정의**
   - 콘솔에 제어/비제어 관련 경고 0건
   - 모든 필드가 타이핑/토글/선택에 즉시 반응
   - 제출 payload가 기대 스키마와 일치

2. **입력 유형별 회귀 테스트 매트릭스**
   | 필드 유형 | 조작 | 기대 state | 결과 |
   |----------|------|-----------|------|
   | text | 문자 입력 | 입력값 반영 | |
   | text | 전체 삭제 | `''` (undefined 아님) | |
   | checkbox | 토글 | boolean 반전 | |
   | radio | 다른 값 선택 | 선택값으로 교체 | |
   | select | 옵션 변경 | 선택값 반영 | |
   | multi-select | 다중 선택 | 배열로 수집 | |

3. **Testing Library 기반 자동화**
   ```javascript
   it('입력이 state에 반영되고 제출값이 정확하다', async () => {
     render(<Form />);
     await userEvent.type(screen.getByPlaceholderText('이름'), '홍길동');
     await userEvent.click(screen.getByText('제출'));
     expect(screen.getByText('이름: 홍길동')).toBeInTheDocument();
   });
   ```

4. **경계 케이스 확인**
   - 초기값이 `undefined`가 아닌 명시적 초기값인지
   - 빈 문자열 입력 시 uncontrolled로 전환되지 않는지
   - 유효성 검사(예: 이메일 정규식) 경고가 의도대로 뜨는지

## 출력 계약

```
검증 결과: [통과 / 실패]
- 제어 경고: [0건 / N건]
- 입력 매트릭스: [모두 통과 / 실패 필드]
- 제출 payload: [스키마 일치 / 불일치]
- 경계 케이스: [통과 / 문제]
```

## 셀프 체크리스트

- [ ] 모든 value에 대응하는 onChange가 있는가?
- [ ] defaultValue와 value를 동시에 쓰는 필드가 남아있지 않은가?
- [ ] 빈 값 입력 시 uncontrolled 전환 경고가 없는가?
- [ ] 제출 payload를 실제로 검증했는가?
- [ ] 입력 유형별 자동화 테스트를 추가했는가?
