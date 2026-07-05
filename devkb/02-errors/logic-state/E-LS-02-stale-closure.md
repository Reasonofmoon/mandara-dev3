---
id: E-LS-02
title: 오래된 클로저 참조
error_class: Logic-State
symptoms:
  - 이전 값 사용
  - 콜백이 예상과 다름
  - 상태 업데이트 누락
exact_messages:
  - "Stale closure detected"
  - "Reference to outdated state"
  - "Handler using old values"
tech_tags:
  - React
  - Closure
  - State
  - Hooks
linked_patterns: []
linked_flows: []
---

# 오래된 클로저 참조

## 증상
콜백이나 이벤트 핸들러가 이전 상태값을 참조합니다. 상태가 업데이트되어도 핸들러는 여전히 이전 값을 사용합니다.

## 빠른 해결법

### 1. 함수형 업데이트 사용
```typescript
// ❌ 이전 count 참조
const increment = () => setCount(count + 1);

// ✅ 현재 값 사용
const increment = () => setCount(c => c + 1);
```

### 2. useCallback 의존성
```typescript
// ❌ stale closure
const handleClick = useCallback(() => {
  console.log(count);
}, []);

// ✅ 의존성 추가
const handleClick = useCallback(() => {
  console.log(count);
}, [count]);
```

### 3. useRef로 최신 값 유지
```typescript
const countRef = useRef(count);

useEffect(() => {
  countRef.current = count;
}, [count]);

const handleClick = useCallback(() => {
  console.log(countRef.current);  // 항상 최신
}, []);
```

## 연결된 패턴
- E-LS-01-infinite-rerender

## 재발 방지
1. 함수형 업데이트 사용
2. useCallback 의존성 명시
3. 불필요한 메모이제이션 피하기
