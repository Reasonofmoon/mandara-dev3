---
id: E-RT-04
title: 처리되지 않은 Promise 거부
error_class: Runtime
symptoms:
  - 콘솔 경고 메시지
  - 애플리케이션 불안정
  - 에러 처리 누락
exact_messages:
  - "UnhandledPromiseRejectionWarning: Error: something went wrong"
  - "Unhandled promise rejection"
  - "PromiseRejectionHandledWarning"
tech_tags:
  - JavaScript
  - Promise
  - Async/Await
  - Error Handling
linked_patterns: []
linked_flows: []
---

# 처리되지 않은 Promise 거부

## 증상
Promise가 거부(reject)되었지만 .catch()나 try/catch로 처리되지 않으면 경고가 발생합니다. 이는 예측 불가능한 동작으로 이어질 수 있습니다.

## 정확한 에러 메시지
```
UnhandledPromiseRejectionWarning: Error: something went wrong
Unhandled promise rejection: TypeError: Cannot read property
PromiseRejectionHandledWarning: Promise rejection was handled asynchronously
```

## 발생 맥락
```javascript
// 잘못된 예 1: .catch() 없음
fetchUser(id)
  .then(user => console.log(user))
  // ❌ reject되면 처리되지 않음

// 잘못된 예 2: async/await에서 try/catch 없음
async function loadData() {
  const data = await fetchData();  // ❌ 에러가 발생하면 처리 안 됨
  return data;
}

// 잘못된 예 3: 비동기 작업 미완료
useEffect(() => {
  fetchUser(id)
    .then(setUser)
    .catch(error => console.error(error));
  // ❌ cleanup function 없음 - 컴포넌트 언마운트 후 setState
}, [id]);

// 잘못된 예 4: Promise 연쇄에서 중간에 누락
Promise.resolve()
  .then(() => fetchData())
  .then(data => console.log(data))
  .then(() => fetchMore())  // ❌ 이 단계에서 에러 처리 안 됨
```

## 필요한 증거
- 콘솔 경고 메시지
- Promise 거부 관련 에러
- 콜 스택 추적
- 비동기 코드

## 의심 원인
1. .catch() 핸들러 누락
2. async/await에서 try/catch 누락
3. 컴포넌트 언마운트 후 setState 시도
4. Promise 체인의 중간 단계에서 에러 처리 누락
5. 타임아웃 또는 비동기 작업 취소 미구현
6. 에러 콜백이 너무 늦게 등록됨

## 빠른 해결법

### 1. .catch() 로 처리
```javascript
// ❌ 잘못된 코드
fetchUser(id)
  .then(user => console.log(user));

// ✅ 올바른 코드
fetchUser(id)
  .then(user => console.log(user))
  .catch(error => console.error('Failed to fetch user:', error));
```

### 2. async/await에서 try/catch
```javascript
// ❌ 잘못된 코드
async function loadUser() {
  const user = await fetchUser(id);
  return user;
}

// ✅ 올바른 코드
async function loadUser() {
  try {
    const user = await fetchUser(id);
    return user;
  } catch (error) {
    console.error('Failed to fetch user:', error);
    throw error;  // 또는 기본값 반환
  }
}
```

### 3. React에서 비동기 작업
```typescript
// ❌ 잘못된 코드
useEffect(() => {
  fetchUser(id).then(setUser);
}, [id]);

// ✅ 올바른 코드
useEffect(() => {
  let isMounted = true;

  fetchUser(id)
    .then(user => {
      if (isMounted) {
        setUser(user);
      }
    })
    .catch(error => {
      if (isMounted) {
        console.error('Failed to fetch user:', error);
      }
    });

  return () => {
    isMounted = false;  // cleanup
  };
}, [id]);
```

### 4. AbortController로 취소
```typescript
useEffect(() => {
  const controller = new AbortController();

  fetchUser(id, { signal: controller.signal })
    .then(setUser)
    .catch(error => {
      if (error.name !== 'AbortError') {
        console.error('Failed to fetch user:', error);
      }
    });

  return () => {
    controller.abort();  // cleanup에서 요청 취소
  };
}, [id]);
```

### 5. Promise.allSettled 로 에러 처리
```javascript
// ❌ 하나 실패하면 전체 실패
Promise.all([
  fetchUser(1),
  fetchUser(2),
  fetchUser(3)
]).catch(error => console.error(error));

// ✅ 모든 Promise 처리 결과 수집
Promise.allSettled([
  fetchUser(1),
  fetchUser(2),
  fetchUser(3)
]).then(results => {
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      console.log(`User ${index + 1}:`, result.value);
    } else {
      console.error(`User ${index + 1} failed:`, result.reason);
    }
  });
});
```

### 6. 전역 에러 핸들러
```javascript
// 처리되지 않은 Promise 거부 감지
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // 에러 로깅, 사용자 알림 등
});

// 또는 브라우저에서
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled rejection:', event.reason);
  event.preventDefault();  // 기본 동작 방지
});
```

### 7. 재시도 로직
```typescript
async function fetchWithRetry(
  fn: () => Promise<any>,
  maxRetries = 3,
  delayMs = 1000
) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;  // 마지막 시도 실패
      }
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

// 사용
fetchWithRetry(() => fetchUser(id))
  .then(setUser)
  .catch(error => console.error('Failed after retries:', error));
```

### 8. Promise 체인 에러 처리
```javascript
fetchUser(id)
  .then(user => fetchPosts(user.id))
  .then(posts => console.log(posts))
  .catch(error => {
    // 어느 단계에서 실패했든 여기서 처리
    console.error('Failed in chain:', error);
  });
```

## 연결된 패턴
- E-RT-01-cannot-read-undefined
- E-LS-05-race-condition

## 연결된 플로우
- 에러 처리 및 복구 플로우
- 비동기 프로그래밍 플로우

## 재발 방지
1. 모든 Promise에 .catch() 또는 try/catch 추가
2. React useEffect에서 cleanup 함수로 isMounted 확인
3. AbortController로 비동기 작업 취소 가능하게
4. 전역 에러 핸들러로 미처리 에러 감지
5. Promise.allSettled로 모든 결과 수집
6. TypeScript로 Promise 반환 타입 명시
7. ESLint의 no-floating-promises 규칙 활성화
