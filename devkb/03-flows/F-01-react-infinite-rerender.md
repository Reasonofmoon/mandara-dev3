---
id: F-01
title: React 무한 리렌더링 해결
pattern_id: P-01
error_ids: [E-01, E-02, E-03]
tech_scope: React, Next.js, 성능 최적화
---

# React 무한 리렌더링 해결

무한 리렌더링은 컴포넌트가 계속해서 자기 자신을 업데이트 하여 성능 저하와 불안정성을 초래합니다.

## 1단계: 증상 고정

- 브라우저 DevTools의 Performance 탭 또는 콘솔에서 경고 메시지 확인
- CPU 사용률이 비정상적으로 높은지 확인
- 네트워크 탭에서 반복적인 API 요청 여부 확인
- React DevTools Profiler로 렌더링 횟수 측정

## 2단계: 재현

```javascript
// 테스트 환경에서 재현
import { useEffect, useState } from 'react';

function Problem() {
  const [count, setCount] = useState(0);

  // 무한 루프: useEffect 의존성이 없음
  useEffect(() => {
    setCount(count + 1);
  });

  return <div>{count}</div>;
}
```

브라우저 콘솔에서 경고 메시지 확인:
"Warning: Maximum update depth exceeded"

## 3단계: 범위 축소

문제의 출처를 파악합니다:

1. **State 업데이트 루프**: setState가 렌더링을 트리거하고 다시 setState 호출
2. **useEffect 의존성 오류**: 의존성 배열이 없거나 잘못됨
3. **객체 참조 불변성**: 매번 새로운 객체/배열을 생성해서 의존성 변경
4. **상위 컴포넌트 프롭**: 상위 컴포넌트에서 매번 새로운 함수/객체 전달

## 4단계: 증거 수집

React DevTools 활용:

```javascript
// DevTools Console에서 실행
React.Profiler.onCommitFiberRoot = (...args) => {
  console.log('Render', new Date().toISOString());
};
```

렌더링 스택 추적:
- 어떤 state가 변경되었는지 확인
- 변경 전후의 props 비교
- useEffect 의존성 배열 검토

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 수정 난도 |
|------|------|---------|
| useEffect 의존성 누락 | 높음 | 낮음 |
| 상위 컴포넌트 객체 참조 | 높음 | 중간 |
| 상태 관리 로직 오류 | 중간 | 중간 |
| 외부 라이브러리 문제 | 낮음 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: useEffect 의존성 배열 추가 (가장 일반적)

```javascript
// ❌ 잘못된 코드
useEffect(() => {
  setCount(count + 1);
});

// ✅ 올바른 코드
useEffect(() => {
  setCount(count + 1);
}, [count]); // 의존성 추가
```

### 수정안 2: 의존성에서 객체 제거

```javascript
// ❌ 렌더링마다 새로운 객체 생성
useEffect(() => {
  fetch('/api/data');
}, [{ id: 1 }]); // 매번 새로운 객체

// ✅ useMemo로 메모이제이션
const config = useMemo(() => ({ id: 1 }), []);
useEffect(() => {
  fetch('/api/data');
}, [config]);
```

### 수정안 3: useCallback으로 함수 안정화

```javascript
// ❌ 렌더링마다 새로운 함수
function Parent() {
  const handleClick = () => console.log('clicked');
  return <Child onClick={handleClick} />;
}

// ✅ useCallback 사용
function Parent() {
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);
  return <Child onClick={handleClick} />;
}
```

### 수정안 4: 상태 업데이트 함수형으로 변경

```javascript
// ❌ 이전 상태에 의존
useEffect(() => {
  setCount(count + 1);
}, []);

// ✅ 함수형 업데이트
useEffect(() => {
  setCount(prev => prev + 1);
}, []);
```

## 7단계: 검증

수정 후 확인 사항:

```javascript
// 렌더링 횟수 추적
function Component() {
  const renderCount = useRef(0);

  useEffect(() => {
    renderCount.current++;
    console.log('Render count:', renderCount.current);
  });

  return <div>Renders: {renderCount.current}</div>;
}
```

테스트:
- 콘솔에서 경고 메시지 사라짐 확인
- DevTools Profiler에서 렌더링 횟수 정상 확인
- 성능 메트릭 개선 확인

## 8단계: 재발 방지

1. **ESLint 플러그인 설정**

```json
{
  "extends": ["plugin:react-hooks/recommended"]
}
```

2. **코드 리뷰 체크리스트**
   - 모든 useEffect에 의존성 배열 있는가?
   - 상위 컴포넌트에서 객체/함수를 memoize했는가?
   - setState로 인한 무한 루프는 없는가?

3. **자동화 테스트**

```javascript
describe('Infinite render prevention', () => {
  it('should not cause infinite renders', () => {
    const renderCount = jest.fn();
    render(<Component onRender={renderCount} />);

    expect(renderCount.mock.calls.length).toBeLessThan(5);
  });
});
```

## 연결된 프롬프트 블록

- **PB-CL-02-state-management**: 상태 관리 구조 검토
- **PB-RP-01-general**: 무한 리렌더링 재현 방법
- **PB-DG-02-react-profiling**: React Profiler로 분석
- **PB-PA-02-react-hooks**: React Hooks 최적화 패턴
- **PB-VF-01-general**: 성능 개선 검증
