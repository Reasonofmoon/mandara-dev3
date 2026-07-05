---
id: E-PF-01
title: 불필요한 리렌더링
error_class: Performance
symptoms:
  - CPU 사용률 높음
  - 버벅거리는 UI
  - 성능 저하
exact_messages:
  - "Component re-renders too often"
  - "Expensive render"
tech_tags:
  - React
  - Performance
  - Optimization
linked_patterns: []
linked_flows: []
---

# 불필요한 리렌더링

## 빠른 해결법

### 1. React.memo
```typescript
const Item = React.memo(({ item }) => (
  <div>{item.name}</div>
));
```

### 2. useMemo
```typescript
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(a, b);
}, [a, b]);
```

### 3. useCallback
```typescript
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

## 재발 방지
1. React Profiler로 성능 측정
2. 불필요한 리렌더링 감지
3. 메모이제이션 적용
