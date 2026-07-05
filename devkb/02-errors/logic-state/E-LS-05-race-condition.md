---
id: E-LS-05
title: 레이스 컨디션
error_class: Logic-State
symptoms:
  - 동시 요청 결과 혼동
  - 예상치 못한 상태
  - 순서 보장 안 됨
exact_messages:
  - "Race condition detected"
  - "Out-of-order response"
  - "Stale response"
tech_tags:
  - Async
  - Concurrency
  - Network
  - State Management
linked_patterns: []
linked_flows: []
---

# 레이스 컨디션

## 증상
여러 비동기 작업이 동시에 실행되어 완료 순서가 예상과 다르면 발생합니다. 이전 요청의 응답이 나중에 도착하여 상태를 덮어쓸 수 있습니다.

## 빠른 해결법

### 1. AbortController로 이전 요청 취소
```typescript
useEffect(() => {
  const controller = new AbortController();

  fetch(`/api/user/${id}`, { signal: controller.signal })
    .then(r => r.json())
    .then(setUser);

  return () => controller.abort();  // 새 id일 때 이전 요청 취소
}, [id]);
```

### 2. 타임스탬프로 이전 응답 무시
```typescript
useEffect(() => {
  const timestamp = Date.now();

  fetch(`/api/search?q=${query}`)
    .then(r => r.json())
    .then(data => {
      if (timestamp === requestTimestamp) {
        setResults(data);  // 최신 요청만 처리
      }
    });

  const requestTimestamp = timestamp;
}, [query]);
```

### 3. SWR/React Query 사용
```typescript
// SWR은 자동으로 race condition 처리
const { data: user } = useSWR(`/api/user/${id}`, fetcher);

// React Query도 동일
const { data: user } = useQuery(['user', id], () => fetchUser(id));
```

## 연결된 패턴
- E-RT-04-unhandled-promise
- E-RT-11-timeout-error

## 재발 방지
1. AbortController 사용
2. 응답 타임스탬프 확인
3. React Query/SWR 라이브러리 활용
