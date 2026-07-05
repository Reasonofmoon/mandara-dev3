---
id: E-LS-04
title: 중복 사이드 이펙트
error_class: Logic-State
symptoms:
  - API 호출 두 번
  - 이벤트 핸들러 중복 등록
  - 타이머 중복 실행
exact_messages:
  - "Duplicate request sent"
  - "Multiple listeners registered"
  - "Cleanup not called"
tech_tags:
  - React
  - Side Effects
  - useEffect
  - Cleanup
linked_patterns: []
linked_flows: []
---

# 중복 사이드 이펙트

## 증상
사이드 이펙트(API 호출, 타이머, 리스너)가 중복으로 실행됩니다. 보통 useEffect cleanup 미흡이 원인입니다.

## 빠른 해결법

### 1. Cleanup 함수 항상 추가
```typescript
// ❌ 잘못된 코드
useEffect(() => {
  const timer = setInterval(() => console.log('tick'), 1000);
}, []);

// ✅ 올바른 코드
useEffect(() => {
  const timer = setInterval(() => console.log('tick'), 1000);
  return () => clearInterval(timer);
}, []);
```

### 2. 이벤트 리스너 제거
```typescript
useEffect(() => {
  const handler = () => console.log('click');
  window.addEventListener('click', handler);

  return () => window.removeEventListener('click', handler);
}, []);
```

### 3. 구독 취소
```typescript
useEffect(() => {
  const unsubscribe = store.subscribe(() => {
    console.log('state changed');
  });

  return () => unsubscribe();
}, []);
```

### 4. AbortController for Fetch
```typescript
useEffect(() => {
  const controller = new AbortController();

  fetch('/api/data', { signal: controller.signal })
    .then(r => r.json())
    .then(setData);

  return () => controller.abort();
}, []);
```

## 연결된 패턴
- E-LS-01-infinite-rerender
- E-RT-04-unhandled-promise

## 재발 방지
1. useEffect cleanup 함수 항상 작성
2. 리소스는 반드시 정리
3. 의존성 배열 명시
