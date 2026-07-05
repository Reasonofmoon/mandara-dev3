---
id: F-14
title: 중복 사이드 이펙트 해결
pattern_id: P-14
error_ids: [E-40, E-41, E-42]
tech_scope: 비동기 처리, useEffect, 사이드 이펙트
---

# 중복 사이드 이펙트 해결

React 컴포넌트에서 useEffect가 중복 실행되거나 이벤트 핸들러가 중복 트리거되는 문제를 해결합니다.

## 1단계: 증상 고정

증상:
- API 요청이 두 번 실행됨
- 이메일이 중복 발송됨
- 결제가 중복 처리됨
- 로그에 중복 메시지 출현
- 데이터 중복 생성

## 2단계: 재현

```javascript
// ❌ useEffect 중복 실행 (Strict Mode)
function Component() {
  useEffect(() => {
    console.log('Effect executed');
    fetchData(); // 개발 환경에서 2회 실행
  }, []);

  return <div>Content</div>;
}

// ❌ 이벤트 핸들러 중복 등록
function Button() {
  useEffect(() => {
    const handleClick = () => {
      console.log('Clicked');
      submitForm(); // 2회 실행
    };

    window.addEventListener('click', handleClick);
    // cleanup 함수 없음
  }, []); // 의존성 배열 없음

  return <button>Click me</button>;
}

// ❌ 콜백 함수 실행 위험
button.addEventListener('click', () => {
  processPayment(); // 버튼 클릭 시 2회 실행
});
```

## 3단계: 범위 축소

중복 사이드 이펙트 유형:

1. **useEffect 중복**: Strict Mode 또는 의존성 오류
2. **이벤트 리스너 중복**: cleanup 함수 미사용
3. **콜백 함수 중복 호출**: 버튼 중복 클릭 방지 미흡
4. **동기화 미흡**: 여러 효과가 같은 작업 수행
5. **초기화 중복**: 리소스 중복 초기화

## 4단계: 증거 수집

```javascript
// 로깅으로 실행 횟수 추적
useEffect(() => {
  console.log('Effect executed at', new Date().toISOString());
  fetchData();
}, []);

// 또는 카운터로 추적
let count = 0;
useEffect(() => {
  count++;
  console.log(`Execution #${count}`);
}, []);
```

```bash
# 콘솔 로그 확인
# "Effect executed at 2024-01-15T10:00:00.000Z" (1차)
# "Effect executed at 2024-01-15T10:00:00.001Z" (2차)
# → 동시에 2회 실행
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| React Strict Mode | 매우높음 | 낮음 |
| cleanup 함수 미사용 | 높음 | 낮음 |
| 의존성 배열 오류 | 높음 | 낮음 |
| 이벤트 리스너 미제거 | 높음 | 낮음 |
| 메모리 누수 | 중간 | 중간 |

## 6단계: 수정안 선택

### 수정안 1: React Strict Mode 이해

```javascript
// Strict Mode는 개발 환경에서 문제를 감지하기 위해 2회 실행
// 프로덕션에서는 1회만 실행

// ✅ Strict Mode에서도 안전하게 작동
function Component() {
  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        const response = await fetch('/api/data');
        if (isMounted) {
          setData(await response.json());
        }
      } catch (error) {
        if (isMounted) {
          setError(error);
        }
      }
    };

    fetchData();

    // cleanup 함수: 언마운트 또는 의존성 변경 시 실행
    return () => {
      isMounted = false; // 언마운트 상태 표시
    };
  }, []);

  return <div>{/* content */}</div>;
}
```

### 수정안 2: useEffect cleanup 함수

```javascript
// ❌ cleanup 함수 없음
useEffect(() => {
  const handleResize = () => console.log('Resized');
  window.addEventListener('resize', handleResize);
  // 언마운트 시 리스너 제거 안 함
}, []);

// ✅ cleanup 함수로 리스너 제거
useEffect(() => {
  const handleResize = () => console.log('Resized');

  window.addEventListener('resize', handleResize);

  return () => {
    window.removeEventListener('resize', handleResize); // cleanup
  };
}, []);

// 다양한 cleanup 시나리오
useEffect(() => {
  // 타이머
  const timerId = setInterval(() => {
    console.log('Interval');
  }, 1000);

  return () => clearInterval(timerId); // cleanup
}, []);

useEffect(() => {
  // Subscription
  const subscription = observable.subscribe(value => {
    console.log(value);
  });

  return () => subscription.unsubscribe(); // cleanup
}, []);

useEffect(() => {
  // API 요청 취소
  const controller = new AbortController();

  fetch('/api/data', { signal: controller.signal });

  return () => controller.abort(); // cleanup
}, []);
```

### 수정안 3: 의존성 배열 올바르게 설정

```javascript
// ❌ 의존성 배열 없음 → 매번 실행
useEffect(() => {
  fetchData();
  // → 매 렌더링마다 실행
});

// ✅ 빈 배열 → 마운트 시 1회만 실행
useEffect(() => {
  fetchData();
}, []);

// ✅ 의존성 포함 → 의존성 변경 시에만 실행
useEffect(() => {
  fetchData(userId);
}, [userId]);

// ❌ 함수를 의존성에 추가 하면 매번 실행
const handleClick = () => {
  console.log('Clicked');
};

useEffect(() => {
  button.addEventListener('click', handleClick);
  return () => button.removeEventListener('click', handleClick);
}, [handleClick]); // handleClick이 매번 새로 생성되면 2회 실행

// ✅ useCallback으로 함수 메모이제이션
const handleClick = useCallback(() => {
  console.log('Clicked');
}, []);

useEffect(() => {
  button.addEventListener('click', handleClick);
  return () => button.removeEventListener('click', handleClick);
}, [handleClick]); // 안정적인 참조
```

### 수정안 4: 버튼 중복 클릭 방지

```javascript
// ❌ 중복 클릭 가능
function Button() {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await submitForm();
    } finally {
      setLoading(false);
    }
  };

  return <button onClick={handleClick}>Submit</button>; // 클릭 중 다시 클릭 가능
}

// ✅ 중복 클릭 방지
function Button() {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return; // 이미 로딩 중이면 반환

    setLoading(true);
    try {
      await submitForm();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleClick} disabled={loading}>
      {loading ? 'Loading...' : 'Submit'}
    </button>
  );
}

// 또는 useRef로 더 견고하게
function Button() {
  const [loading, setLoading] = useState(false);
  const isProcessing = useRef(false);

  const handleClick = async () => {
    if (isProcessing.current) return;

    isProcessing.current = true;
    setLoading(true);

    try {
      await submitForm();
    } finally {
      setLoading(false);
      isProcessing.current = false;
    }
  };

  return <button onClick={handleClick}>{loading ? 'Loading...' : 'Submit'}</button>;
}
```

### 수정안 5: 사이드 이펙트 통합

```javascript
// ❌ 여러 effect가 같은 작업
useEffect(() => {
  loadData();
}, []);

useEffect(() => {
  loadData(); // 중복
}, [userId]);

// ✅ 하나의 effect에 통합
useEffect(() => {
  loadData();
}, [userId]); // userId 변경 시에만 로드
```

### 수정안 6: custom hook으로 분리

```javascript
// 재사용 가능한 hook
function useAsync(asyncFunction, immediate = true) {
  const [status, setStatus] = useState('idle');
  const [value, setValue] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!immediate) return;

    let isMounted = true;

    const execute = async () => {
      setStatus('pending');
      try {
        const response = await asyncFunction();
        if (isMounted) {
          setValue(response);
          setStatus('success');
        }
      } catch (error) {
        if (isMounted) {
          setError(error);
          setStatus('error');
        }
      }
    };

    execute();

    return () => {
      isMounted = false; // cleanup
    };
  }, [asyncFunction, immediate]);

  return { status, value, error };
}

// 사용
function MyComponent() {
  const { status, value, error } = useAsync(() => fetchData(), true);

  if (status === 'pending') return <div>Loading...</div>;
  if (status === 'error') return <div>Error: {error.message}</div>;
  return <div>{value}</div>;
}
```

## 7단계: 검증

```javascript
describe('No Duplicate Side Effects', () => {
  it('should execute effect only once on mount', () => {
    const effectFn = jest.fn();

    const { rerender } = render(
      <Component onMount={effectFn} />
    );

    // 마운트 시 1회만 호출
    expect(effectFn).toHaveBeenCalledTimes(1);

    rerender(<Component onMount={effectFn} />);

    // 리렌더링 후에도 여전히 1회
    expect(effectFn).toHaveBeenCalledTimes(1);
  });

  it('should clean up event listeners', () => {
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

    const { unmount } = render(<Component />);

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalled();
  });

  it('should handle rapid clicks correctly', async () => {
    const submitFn = jest.fn();
    const { getByRole } = render(
      <Button onClick={submitFn} />
    );

    const button = getByRole('button');

    // 빠른 클릭 3회
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => {
      // 실제로는 1회만 실행
      expect(submitFn).toHaveBeenCalledTimes(1);
    });
  });
});
```

## 8단계: 재발 방지

1. **ESLint 규칙**

```json
{
  "extends": ["plugin:react-hooks/recommended"]
}
```

2. **코드 리뷰 체크리스트**
   - [ ] 모든 useEffect에 cleanup 함수 있는가?
   - [ ] 의존성 배열이 올바른가?
   - [ ] 이벤트 리스너가 제거되는가?
   - [ ] 버튼 중복 클릭 방지 있는가?

## 연결된 프롬프트 블록

- **PB-CL-15-hooks-usage**: React Hooks 사용법
- **PB-RP-14-effect-test**: useEffect 테스트
- **PB-DG-15-effect-trace**: 사이드 이펙트 추적
- **PB-PA-15-effect-cleanup**: cleanup 함수 구현
- **PB-VF-14-duplicate-test**: 중복 실행 검증
