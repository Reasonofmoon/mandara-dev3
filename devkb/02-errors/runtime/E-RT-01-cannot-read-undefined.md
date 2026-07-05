---
id: E-RT-01
title: Cannot read properties of undefined
error_class: Runtime
symptoms:
  - 애플리케이션 크래시
  - 콘솔 에러
  - 기능이 작동하지 않음
exact_messages:
  - "Cannot read properties of undefined (reading 'name')"
  - "TypeError: Cannot read property 'map' of undefined"
  - "Cannot read properties of null (reading 'innerHTML')"
tech_tags:
  - JavaScript
  - Error Handling
  - Null Safety
  - Debugging
linked_patterns: []
linked_flows: []
---

# Cannot read properties of undefined

## 증상
변수나 객체가 undefined 또는 null이 아닌 것으로 예상되지만 실제로는 undefined/null일 때 발생합니다. 이는 가장 일반적인 런타임 에러입니다.

## 정확한 에러 메시지
```
Cannot read properties of undefined (reading 'name')
TypeError: Cannot read property 'map' of undefined
Cannot read properties of null (reading 'innerHTML')
Cannot set properties of undefined (setting 'value')
```

## 발생 맥락
```javascript
// 잘못된 예 1: 객체 체크 없이 접근
const user = null;
console.log(user.name);  // ❌ Cannot read properties of null

// 잘못된 예 2: 배열이 undefined
const items = undefined;
items.forEach(item => console.log(item));  // ❌ Cannot read properties of undefined

// 잘못된 예 3: API 응답이 예상과 다름
async function fetchUser() {
  const response = await fetch('/api/user');
  const data = await response.json();
  return data.user;  // ❌ data.user가 undefined일 수 있음
}

const user = fetchUser();
console.log(user.name);  // ❌ user는 Promise

// 잘못된 예 4: React에서의 타입 불일치
function UserCard({ user }) {
  return <div>{user.profile.avatar}</div>;  // ❌ user.profile이 undefined일 수 있음
}
```

## 필요한 증거
- 에러 메시지와 라인 번호
- 변수의 값과 타입
- 콜 스택 추적
- 최근 변경사항

## 의심 원인
1. 변수 초기화 누락
2. 조건부 체크 누락
3. API 응답이 예상과 다름
4. 비동기 작업 처리 오류
5. 객체 구조 변경
6. null 체크 누락
7. 인덱스 범위 오류

## 빠른 해결법

### 1. 옵셔널 체이닝 사용
```javascript
// ❌ 위험
const name = user.profile.name;

// ✅ 안전
const name = user?.profile?.name;

// 함수 호출도 가능
const result = user?.getProfile?.();
```

### 2. 널 병합 연산자 with 기본값
```javascript
// ❌ ||는 falsy 값도 교체
const count = user.count || 0;  // 0도 false이므로 기본값 사용

// ✅ ?? 는 null/undefined만 확인
const count = user?.count ?? 0;
```

### 3. 타입 가드
```javascript
// 조건부 체크
if (user && user.profile && user.profile.name) {
  console.log(user.profile.name);
}

// 또는 더 간단하게
if (user?.profile?.name) {
  console.log(user.profile.name);
}
```

### 4. 기본값 설정
```javascript
function UserCard({ user = {} }) {
  return <div>{user?.name || 'Anonymous'}</div>;
}

// 또는 객체 기본값
const userProfile = {
  name: 'Unknown',
  email: '',
  ...fetchedUser
};
```

### 5. 배열 처리
```javascript
// ❌ undefined일 수 있음
items.forEach(item => console.log(item));

// ✅ 안전
(items || []).forEach(item => console.log(item));

// 또는
items?.forEach(item => console.log(item));

// 또는 Array.isArray 확인
if (Array.isArray(items)) {
  items.forEach(item => console.log(item));
}
```

### 6. 비동기 처리
```javascript
// ❌ 잘못된 코드
const user = fetchUser();
console.log(user.name);  // user는 Promise!

// ✅ 올바른 코드
const user = await fetchUser();
console.log(user?.name);

// 또는 .then() 사용
fetchUser().then(user => {
  console.log(user?.name);
});
```

### 7. React에서의 안전한 접근
```typescript
interface User {
  id: number;
  name?: string;
  profile?: {
    avatar?: string;
  };
}

function UserCard({ user }: { user?: User }) {
  return (
    <div>
      <h1>{user?.name ?? 'Anonymous'}</h1>
      <img src={user?.profile?.avatar} alt={user?.name} />
    </div>
  );
}
```

### 8. 타입 검사 함수
```javascript
function isDefined<T>(value: T | undefined): value is T {
  return value !== undefined;
}

const users = [user1, null, user2, undefined];
const validUsers = users.filter(isDefined);
```

### 9. 객체 검증
```javascript
// 객체 존재 확인
if (typeof user === 'object' && user !== null) {
  console.log(user.name);
}

// 또는 in 연산자
if ('name' in user) {
  console.log(user.name);
}
```

### 10. 디버깅
```javascript
// 값 확인
console.log(typeof user, user);

// 조건부 중단점 설정
debugger;

// 또는 console.assert
console.assert(user !== undefined, 'user is undefined');
```

## 연결된 패턴
- E-ST-05-typescript-strict-error
- E-RT-03-hydration-mismatch

## 연결된 플로우
- 에러 처리 및 방어 플로우
- 비동기 프로그래밍 플로우

## 재발 방지
1. TypeScript strict 모드 활성화
2. 옵셔널 체이닝(?.) 및 널 병합(??) 활용
3. 객체/배열 접근 전 존재 확인
4. API 응답 검증 로직 추가
5. 기본값 명시적으로 제공
6. 콘솔 에러 정기적으로 모니터링
7. 타입 가드 함수 작성 및 활용
