---
id: E-LS-01
title: 무한 리렌더링
error_class: Logic-State
symptoms:
  - CPU 사용량 높음
  - 브라우저 응답 없음
  - 콘솔 경고 반복
exact_messages:
  - "Maximum update depth exceeded"
  - "Too many re-renders. React limits the number of renders"
  - "Components can only have one instance"
tech_tags:
  - React
  - Rendering
  - State Management
  - Performance
linked_patterns: []
linked_flows: []
---

# 무한 리렌더링

## 증상
컴포넌트가 계속 리렌더링되어 애플리케이션이 느려지고 브라우저가 응답하지 않습니다. useEffect 의존성, setState 호출, 또는 객체 비교 오류가 원인입니다.

## 정확한 에러 메시지
```
Too many re-renders. React limits the number of renders to prevent an infinite loop
Maximum update depth exceeded
State update during render
```

## 발생 맥락
```typescript
// 잘못된 예 1: setState in render
function Component() {
  const [count, setCount] = useState(0);
  setCount(count + 1);  // ❌ 매번 리렌더링 시 호출
  return <div>{count}</div>;
}

// 잘못된 예 2: useEffect 의존성 누락
function Component() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetchData().then(setData);
    // ❌ 의존성 배열 없음
  });

  return <div>{data.length}</div>;
}

// 잘못된 예 3: 객체를 의존성으로
function Component({ config }) {
  useEffect(() => {
    // config 설정
  }, [config]);  // ❌ config가 매번 새로 생성되면 무한 루프
}

// 잘못된 예 4: setState in useEffect without deps
function Component() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    setItems([...items, newItem]);  // ❌ items 변경 → effect 실행 → items 변경
  }, [items]);
}
```

## 빠른 해결법

### 1. setState를 효과에 넣기
```typescript
// ❌ 잘못된 코드
function Component() {
  const [count, setCount] = useState(0);
  setCount(count + 1);
  return <div>{count}</div>;
}

// ✅ 올바른 코드
function Component() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(count + 1);
  }, []);  // 한 번만 실행

  return <div>{count}</div>;
}
```

### 2. 의존성 배열 올바르게 사용
```typescript
// ✅ 의존성 명시
useEffect(() => {
  fetchData(id).then(setData);
}, [id]);  // id가 변경될 때만 실행

// ❌ 의존성 무시
useEffect(() => {
  const timer = setInterval(() => setCount(c => c + 1), 1000);
  return () => clearInterval(timer);
}, []);  // 의존성 배열 필요
```

### 3. 함수형 업데이트
```typescript
// ❌ 잘못된 코드
setItems([...items, newItem]);

// ✅ 함수형 업데이트
setItems(prevItems => [...prevItems, newItem]);

// useEffect에서도
useEffect(() => {
  setCount(prevCount => prevCount + 1);
}, []);  // count가 의존성에 없어도 안전
```

### 4. 객체/배열 메모이제이션
```typescript
// ❌ 매번 새로 생성
const config = { debug: true };

useEffect(() => {
  console.log(config);
}, [config]);  // 무한 루프

// ✅ useMemo 사용
const config = useMemo(() => ({ debug: true }), []);

useEffect(() => {
  console.log(config);
}, [config]);  // 안전
```

### 5. ESLint 규칙 활성화
```json
{
  "extends": "plugin:react-hooks/recommended",
  "rules": {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn"
  }
}
```

## 연결된 패턴
- E-LS-02-stale-closure
- E-LS-04-duplicate-side-effect

## 재발 방지
1. 렌더링 중에 setState 호출 금지
2. 항상 의존성 배열 명시
3. useMemo/useCallback으로 메모이제이션
4. ESLint 규칙 활성화
5. React Profiler로 성능 모니터링
