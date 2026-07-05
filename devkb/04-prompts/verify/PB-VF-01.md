---
id: PB-VF-01
purpose: React 무한 리렌더링 수정이 실제로 해결되었고 회귀가 없는지 검증
applies_when: 무한 리렌더링(F-01) 수정을 적용한 직후 효과와 안정성 확인이 필요할 때
version: "1.1"
---

# React 무한 리렌더링 해결 검증

무한 리렌더링 수정(useEffect 의존성, memoization 등)을 적용한 뒤, 렌더링 횟수가 정상화되었고 성능이 회복되었으며 다른 컴포넌트에 회귀가 없는지 확인하는 검증 프롬프트입니다.

## 용도

F-01 플로우의 6단계(수정)를 마친 후, 콘솔 경고 소멸·렌더링 횟수·성능 메트릭을 기준으로 수정 효과를 정량 검증하고 재발 방지 장치가 작동하는지 확인합니다.

## 적용 시점

- useEffect 의존성 배열 추가 / useMemo / useCallback 수정 직후
- "Maximum update depth exceeded" 경고가 사라졌다고 판단되는 시점
- 성능 회귀 여부를 배포 전 확인해야 할 때

## 필수 입력

- 수정한 컴포넌트 파일 경로와 diff
- 수정 전 렌더링 횟수 / CPU 사용률 (베이스라인)
- 재현 시나리오 (F-01 2단계에서 확보한 재현 절차)

## 프롬프트 템플릿

아래 수정에 대해 무한 리렌더링이 실제로 해결되었는지 검증하고, 회귀가 없는지 확인해줘.

**수정 대상:** [컴포넌트/파일]
**수정 내용:** [예: useEffect에 [count] 의존성 추가]

다음 순서로 검증 절차와 결과를 정리해줘.

1. **성공 기준 정의**
   - 콘솔에 "Maximum update depth exceeded" 경고 0건
   - 마운트 후 안정화까지 렌더링 횟수 < 5회
   - Profiler commit 시간 및 CPU 사용률이 베이스라인 이하

2. **렌더링 횟수 계측** (수정 컴포넌트에 임시 삽입)
   ```javascript
   const renderCount = useRef(0);
   useEffect(() => { renderCount.current++; console.log('renders:', renderCount.current); });
   ```
   - 초기 렌더 후 추가 렌더가 멈추는지 확인

3. **회귀 테스트 매트릭스**
   | 시나리오 | 기대 렌더 횟수 | 결과 |
   |---------|---------------|------|
   | 최초 마운트 | 1~2 | |
   | props 변경 1회 | +1 | |
   | 부모 리렌더(동일 props) | 0 (memo 시) | |
   | 언마운트/재마운트 | 초기값 리셋 | |

4. **자동화 테스트 추가** — 무한 렌더 재발을 CI에서 잡도록
   ```javascript
   it('무한 렌더가 발생하지 않는다', () => {
     const onRender = jest.fn();
     render(<Component onRender={onRender} />);
     expect(onRender.mock.calls.length).toBeLessThan(5);
   });
   ```

5. **재발 방지 확인**
   - `eslint-plugin-react-hooks`의 exhaustive-deps 경고 0건인지
   - 동일 패턴이 다른 컴포넌트에 남아있지 않은지 grep

## 출력 계약

```
검증 결과: [통과 / 실패]
- 콘솔 경고: [0건 / N건]
- 안정화 렌더 횟수: [N회] (기준 < 5)
- 회귀 매트릭스: [모두 통과 / 실패 항목]
- ESLint exhaustive-deps: [clean / 경고 N건]
- 남은 위험: [없음 / 설명]
```

## 셀프 체크리스트

- [ ] 수정 전/후 렌더링 횟수를 정량 비교했는가?
- [ ] 콘솔 경고가 완전히 사라졌는가?
- [ ] 부모 리렌더 시 불필요한 자식 렌더가 없는지 확인했는가?
- [ ] 회귀를 잡는 자동화 테스트를 추가했는가?
- [ ] exhaustive-deps 린트 규칙이 활성화·통과되는가?
