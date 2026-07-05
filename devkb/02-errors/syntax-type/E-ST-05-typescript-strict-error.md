---
id: E-ST-05
title: TypeScript 엄격 모드 오류
error_class: Syntax-Type
symptoms:
  - strict 모드에서 컴파일 실패
  - null/undefined 관련 에러
  - any 타입 사용 불가
exact_messages:
  - "Object is possibly 'null' or 'undefined'"
  - "Argument of type 'undefined' is not assignable to parameter of type 'string'"
  - "Type 'any' is not allowed"
tech_tags:
  - TypeScript
  - Type Safety
  - Strict Mode
  - Null Safety
linked_patterns: []
linked_flows: []
---

# TypeScript 엄격 모드 오류

## 증상
TypeScript strict 모드에서는 null/undefined, any 타입, implicit any 등을 허용하지 않습니다. 이로 인해 타입 체크가 더 엄격해집니다.

## 정확한 에러 메시지
```
Object is possibly 'null' or 'undefined'
Property 'name' does not exist on type 'null | undefined'
Argument of type 'undefined' is not assignable to parameter of type 'string'
Variable 'x' implicitly has an 'any' type
Type 'any' is not allowed in strict mode
```

## 발생 맥락
```typescript
// 잘못된 예 1: null/undefined 체크 누락
function getUser(id: string) {
  const user = users.find(u => u.id === id);
  console.log(user.name);  // ❌ user는 User | undefined일 수 있음
}

// 잘못된 예 2: any 타입 사용
function process(data: any) {  // ❌ strict 모드에서 불가
  return data.value;
}

// 잘못된 예 3: implicit any
function add(a, b) {  // ❌ 파라미터 타입이 any
  return a + b;
}

// 잘못된 예 4: null 체크 누락
const name: string | null = getName();
const upper = name.toUpperCase();  // ❌ name이 null일 수 있음
```

## 필요한 증거
- TypeScript 에러 메시지
- tsconfig.json의 strict 설정
- 타입이 정의되지 않은 코드

## 의심 원인
1. null/undefined 가능성을 고려하지 않음
2. any 타입 사용
3. 함수 파라미터 타입 미정의
4. 옵셔널 체이닝/널 병합 연산자 미사용
5. 타입 가드 함수 미구현

## 빠른 해결법

### 1. null/undefined 체크 추가
```typescript
// ❌ 잘못된 코드
function getUser(id: string) {
  const user = users.find(u => u.id === id);
  console.log(user.name);
}

// ✅ 올바른 코드
function getUser(id: string) {
  const user = users.find(u => u.id === id);
  if (user) {
    console.log(user.name);
  } else {
    console.log('User not found');
  }
}
```

### 2. 옵셔널 체이닝 사용
```typescript
// ✅ 더 간결한 코드
const name = user?.name;
const email = user?.contact?.email;
const phone = user?.getPhone?.();
```

### 3. 널 병합 연산자
```typescript
// ❌ 잘못된 코드
const displayName = user.name || 'Anonymous';  // name이 undefined일 수 있음

// ✅ 올바른 코드
const displayName = user?.name ?? 'Anonymous';
```

### 4. 함수 파라미터에 타입 추가
```typescript
// ❌ 잘못된 코드
function add(a, b) {
  return a + b;
}

// ✅ 올바른 코드
function add(a: number, b: number): number {
  return a + b;
}
```

### 5. 타입 가드 함수
```typescript
// ✅ 타입 가드로 null 체크
function isUser(value: any): value is User {
  return value && typeof value === 'object' && 'id' in value && 'name' in value;
}

if (isUser(data)) {
  console.log(data.name);
}
```

### 6. Strict 모드 설정
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitAny": true,
    "noImplicitThis": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## 연결된 패턴
- E-ST-01-prop-type-mismatch
- E-ST-06-prisma-type-error

## 연결된 플로우
- TypeScript 프로젝트 설정 플로우
- 타입 안전성 강화 플로우

## 재발 방지
1. 프로젝트 초기에 strict mode 활성화
2. 모든 함수에 반환 타입 명시
3. 옵셔널 체이닝(?.) 및 널 병합(??) 활용
4. 타입 가드 함수 작성
5. TypeScript 버전 최신 유지
6. ESLint의 @typescript-eslint/recommended 사용
