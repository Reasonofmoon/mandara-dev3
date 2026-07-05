---
id: E-ST-06
title: Prisma 타입 오류
error_class: Syntax-Type
symptoms:
  - Prisma Client 타입 불일치
  - 모델 필드 타입 오류
  - 쿼리 결과 타입 오류
exact_messages:
  - "Type 'string' is not assignable to type 'UserCreateInput'"
  - "Property 'age' does not exist on type 'User'"
  - "Argument of type 'object' is not assignable to parameter of type 'UserWhereInput'"
tech_tags:
  - Prisma
  - ORM
  - TypeScript
  - Database
linked_patterns: []
linked_flows: []
---

# Prisma 타입 오류

## 증상
Prisma 스키마와 TypeScript 타입이 맞지 않으면 발생합니다. 모델 필드 타입, 쿼리 입력, 또는 결과 타입이 불일치할 때 나타납니다.

## 정확한 에러 메시지
```
Type 'string' is not assignable to type 'UserCreateInput'
Property 'age' does not exist on type 'User'
Argument of type 'object' is not assignable to parameter of type 'UserWhereInput'
The property 'posts' does not exist on the model 'User', but you tried to select it
```

## 발생 맥락
```prisma
// schema.prisma
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String?
  posts Post[]
}

model Post {
  id      Int     @id @default(autoincrement())
  title   String
  userId  Int
  user    User    @relation(fields: [userId], references: [id])
}
```

```typescript
// 잘못된 예 1: 타입 불일치
const user = await prisma.user.create({
  data: {
    email: "user@example.com",
    name: "John",
    age: 30  // ❌ User 모델에 age 필드 없음
  }
});

// 잘못된 예 2: 선택 필드 오류
const user = await prisma.user.findUnique({
  where: { id: 1 },
  select: {
    id: true,
    email: true,
    profile: true  // ❌ profile 필드 없음
  }
});

// 잘못된 예 3: 쿼리 결과 타입 오류
const users = await prisma.user.findMany({
  select: { id: true, email: true }
});
const name = users[0].name;  // ❌ select에 name 없음
```

## 필요한 증거
- Prisma 스키마 정의
- TypeScript 에러 메시지
- Prisma Client 쿼리 코드
- @prisma/client 타입 정의

## 의심 원인
1. 스키마 모델과 쿼리 필드 불일치
2. select/include로 가져오지 않은 필드 접근
3. 선택적 필드를 필수로 취급
4. 마이그레이션 후 타입 생성 미실행
5. 모델 필드 타입 변경 후 타입 동기화 미실행

## 빠른 해결법

### 1. Prisma 타입 재생성
```bash
npx prisma generate
npx prisma db push
```

```typescript
// 타입 재생성 후 import
import { User, Prisma } from '@prisma/client';
```

### 2. 정확한 필드 타입 사용
```typescript
// ✅ 올바른 코드
const user = await prisma.user.create({
  data: {
    email: "user@example.com",
    name: "John"
  }
});
```

### 3. select/include로 명시적 필드 선택
```typescript
// ❌ 잘못된 코드
const user = await prisma.user.findUnique({
  where: { id: 1 }
});
const name = user.name;  // undefined일 수 있음

// ✅ 올바른 코드
const user = await prisma.user.findUnique({
  where: { id: 1 },
  select: {
    id: true,
    email: true,
    name: true
  }
});
const name = user.name;  // 안전함
```

### 4. 관계 데이터 로드
```typescript
// ✅ include로 관계 필드 로드
const user = await prisma.user.findUnique({
  where: { id: 1 },
  include: {
    posts: true
  }
});
const postCount = user.posts.length;
```

### 5. 타입 추론 활용
```typescript
// ✅ Prisma 생성 타입으로 파라미터 정의
type UserCreateData = Prisma.UserCreateInput;

function createUser(data: UserCreateData) {
  return prisma.user.create({ data });
}

// 또는
const data: Prisma.UserCreateInput = {
  email: "user@example.com",
  name: "John"
};
```

### 6. 선택적 필드 처리
```typescript
// schema.prisma에서 name이 String?라면

// ✅ null 허용
const user = await prisma.user.create({
  data: {
    email: "user@example.com",
    name: null
  }
});

// ✅ 또는
const user = await prisma.user.create({
  data: {
    email: "user@example.com"
  }
});
```

## 연결된 패턴
- E-ST-05-typescript-strict-error
- E-ST-07-zod-schema-mismatch
- E-BC-07-prisma-generate-fail

## 연결된 플로우
- Prisma 스키마 관리 플로우
- 데이터베이스 타입 안전성 플로우

## 재발 방지
1. 스키마 변경 후 항상 `prisma generate` 실행
2. select/include로 필드를 명시적으로 선택
3. Prisma 생성 타입 활용 (UserCreateInput 등)
4. 타입 검사 도구로 쿼리 검증
5. 마이그레이션 전후 타입 일관성 확인
6. CI/CD에 `prisma generate` 추가
