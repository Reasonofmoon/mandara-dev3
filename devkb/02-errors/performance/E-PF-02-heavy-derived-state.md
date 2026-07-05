---
id: E-PF-02
title: 무거운 파생 상태 계산
error_class: Performance
symptoms:
  - 느린 렌더링
  - CPU 사용률 높음
  - 애니메이션 버벅거림
exact_messages:
  - "Slow computation during render"
  - "Expensive calculation"
tech_tags:
  - React
  - Performance
  - Optimization
linked_patterns: []
linked_flows: []
---

# 무거운 파생 상태 계산

## 빠른 해결법

### 1. useMemo로 메모이제이션
```typescript
const filteredList = useMemo(() => {
  return items.filter(item => item.category === category);
}, [items, category]);
```

### 2. 계산을 바깥으로
```typescript
// ❌ 렌더링 시마다 계산
const largeList = items.map(transform);

// ✅ useMemo 사용
const largeList = useMemo(
  () => items.map(transform),
  [items]
);
```

### 3. 선택적 메모이제이션
```typescript
const MemoizedChild = React.memo(Child);
```

## 재발 방지
1. 계산 비용 측정
2. useMemo 적절히 사용
3. 계산 로직 최적화
