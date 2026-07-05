---
id: E-ST-07
title: Zod 스키마 불일치
error_class: Syntax-Type
symptoms:
  - 검증 실패
  - 파싱 에러
  - 타입 추론 오류
exact_messages:
  - "Validation error: Expected number, received string"
  - "Invalid enum value. Expected 'admin' | 'user' | 'guest'"
  - "Required"
  - "String must contain at least 5 characters"
tech_tags:
  - Zod
  - Validation
  - TypeScript
  - Schema
linked_patterns: []
linked_flows: []
---

# Zod 스키마 불일치

## 증상
Zod 스키마로 정의한 데이터 구조와 실제 데이터가 맞지 않으면 검증에 실패합니다. 필드 타입, 형식, 또는 값 범위가 불일치할 때 발생합니다.

## 정확한 에러 메시지
```
Validation error: Expected number, received string
Invalid enum value. Expected 'admin' | 'user'
String must contain at least 5 characters
Number must be greater than 0
Required
Path: ["email"]
```

## 발생 맥락
```typescript
import { z } from 'zod';

// Zod 스키마 정의
const userSchema = z.object({
  id: z.number(),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'guest']),
  age: z.number().min(0).max(150),
  name: z.string().min(1)
});

// 잘못된 예 1: 필드 타입 오류
const data1 = {
  id: "123",  // ❌ string이 아닌 number 필요
  email: "user@example.com",
  role: "moderator",  // ❌ 정의된 enum 값이 아님
  age: 25,
  name: "John"
};

// 잘못된 예 2: 검증 규칙 미충족
const data2 = {
  id: 1,
  email: "invalid-email",  // ❌ 유효한 이메일이 아님
  role: "user",
  age: 200,  // ❌ max(150) 초과
  name: ""  // ❌ min(1) 미충족
};

// 잘못된 예 3: 필드 누락
const data3 = {
  id: 1,
  email: "user@example.com"
  // ❌ role, age, name 필드 누락
};
```

## 필요한 증거
- Zod 스키마 정의
- 검증 에러 메시지
- 입력 데이터
- parse/validate 호출 코드

## 의심 원인
1. 입력 데이터 타입이 스키마와 다름
2. enum 값이 정의되지 않음
3. 검증 규칙(min, max, pattern 등) 미충족
4. 필수 필드 누락
5. 스키마와 실제 데이터 구조 불일치

## 빠른 해결법

### 1. 스키마에 맞게 데이터 변환
```typescript
// ❌ 잘못된 코드
const data = {
  id: "123",
  email: "user@example.com",
  role: "admin",
  age: 30,
  name: "John"
};
const result = userSchema.parse(data);  // 타입 에러

// ✅ 올바른 코드
const data = {
  id: 123,  // string 대신 number
  email: "user@example.com",
  role: "admin",
  age: 30,
  name: "John"
};
const result = userSchema.parse(data);
```

### 2. 타입 강제 변환
```typescript
const data = {
  id: parseInt("123"),  // string을 number로 변환
  email: "user@example.com",
  role: "admin" as const,
  age: 30,
  name: "John"
};
const result = userSchema.parse(data);
```

### 3. safeParse로 에러 처리
```typescript
// ✅ 더 안전한 방법
const result = userSchema.safeParse(data);

if (!result.success) {
  console.error('Validation errors:', result.error.errors);
  // [
  //   {
  //     code: 'invalid_enum_value',
  //     expected: ['admin', 'user', 'guest'],
  //     received: 'moderator',
  //     path: ['role'],
  //     message: "Invalid enum value..."
  //   }
  // ]
} else {
  console.log('Valid data:', result.data);
}
```

### 4. 스키마 오류 메시지 맞춤화
```typescript
const userSchema = z.object({
  id: z.number({ message: "ID는 숫자여야 합니다" }),
  email: z.string().email("유효한 이메일을 입력하세요"),
  role: z.enum(['admin', 'user', 'guest'], {
    errorMap: () => ({ message: "역할은 admin, user, guest 중 하나여야 합니다" })
  }),
  age: z.number()
    .min(0, "나이는 0 이상이어야 합니다")
    .max(150, "나이는 150 이하여야 합니다"),
  name: z.string().min(1, "이름은 필수입니다")
});
```

### 5. 선택적 필드와 기본값
```typescript
const userSchema = z.object({
  id: z.number(),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'guest']).default('user'),
  age: z.number().optional(),  // 선택적
  name: z.string().default('Anonymous')
});

const data = { id: 1, email: "user@example.com" };
const result = userSchema.parse(data);
// { id: 1, email: 'user@example.com', role: 'user', name: 'Anonymous' }
```

### 6. 타입 추론
```typescript
// Zod 스키마에서 TypeScript 타입 자동 추론
type User = z.infer<typeof userSchema>;

// User 타입은 자동으로 생성됨:
// {
//   id: number;
//   email: string;
//   role: 'admin' | 'user' | 'guest';
//   age: number;
//   name: string;
// }
```

## 연결된 패턴
- E-ST-05-typescript-strict-error
- E-ST-06-prisma-type-error
- E-RT-02-cors-preflight-fail

## 연결된 플로우
- 데이터 검증 플로우
- API 입력 검증 플로우

## 재발 방지
1. 스키마 정의 시 모든 검증 규칙 명시
2. safeParse로 안전하게 검증
3. z.infer로 타입 일관성 유지
4. 오류 메시지 맞춤화
5. 런타임에 스키마 동적 생성 피하기
6. 스키마 변경 시 모든 사용처 검토
