---
title: PostgreSQL과 Prisma 참조 가이드
version: 1.0
---

# PostgreSQL과 Prisma 참조 가이드

Prisma 스키마, 인덱스, EXPLAIN, 격리 수준 참조입니다.

## Prisma 스키마

### Generator와 Datasource

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

### 데이터 타입

| Prisma | PostgreSQL | 설명 |
|--------|-----------|------|
| `Int` | `INTEGER` | 정수 |
| `BigInt` | `BIGINT` | 큰 정수 |
| `Float` | `DOUBLE PRECISION` | 부동소수점 |
| `String` | `VARCHAR` | 문자열 |
| `Boolean` | `BOOLEAN` | 불린 |
| `DateTime` | `TIMESTAMP` | 날짜/시간 |
| `Json` | `JSON` | JSON 객체 |
| `Bytes` | `BYTEA` | 바이너리 |
| `Decimal` | `DECIMAL` | 고정소수점 |

### 모델 정의

```prisma
model User {
  id        Int     @id @default(autoincrement())
  email     String  @unique
  name      String
  role      Role    @default(USER)
  posts     Post[]
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([email])
  @@map("users")
}

enum Role {
  USER
  ADMIN
}

model Post {
  id        Int     @id @default(autoincrement())
  title     String
  content   String?
  published Boolean @default(false)
  author    User    @relation(fields: [authorId], references: [id])
  authorId  Int
  createdAt DateTime @default(now())

  @@index([authorId])
  @@map("posts")
}
```

## 인덱스

### 인덱스 타입

```prisma
// 단일 컬럼 인덱스
model Post {
  id Int @id
  authorId Int
  @@index([authorId])  // 검색 성능 향상
}

// 복합 인덱스
model Order {
  id Int @id
  userId Int
  status String
  @@index([userId, status])  // 두 컬럼 함께 검색
}

// 유니크 인덱스
model User {
  id Int @id
  email String
  @@unique([email])  // 중복 방지
}

// 부분 인덱스
model Post {
  id Int @id
  published Boolean
  @@index([id]) @@where(published == true)
}
```

### SQL 인덱스

```sql
-- 단일 컬럼
CREATE INDEX idx_posts_author_id ON posts(author_id);

-- 복합
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- 유니크
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- 부분
CREATE INDEX idx_posts_published ON posts(id) WHERE published = true;

-- 정렬 지정
CREATE INDEX idx_posts_created_desc ON posts(created_at DESC);

-- 인덱스 확인
SELECT * FROM pg_indexes WHERE tablename = 'posts';

-- 인덱스 삭제
DROP INDEX idx_posts_author_id;
```

## EXPLAIN ANALYZE

### 실행 계획 분석

```sql
-- 기본 실행 계획
EXPLAIN SELECT * FROM posts WHERE author_id = 1;

-- 상세 분석 (실제 실행)
EXPLAIN ANALYZE SELECT * FROM posts WHERE author_id = 1;

-- JSON 포맷
EXPLAIN (FORMAT JSON) SELECT * FROM posts WHERE author_id = 1;

-- 예상 결과
Seq Scan on posts  (cost=0.00..35.50 rows=1 width=100)
Filter: (author_id = 1)
```

### 최적화 팁

- `Seq Scan` → 모든 행 스캔 (느림, 인덱스 필요)
- `Index Scan` → 인덱스 사용 (빠름)
- `Hash Join` → 작은 테이블 조인
- `Nested Loop` → 큰 테이블 조인 (많은 비용)

## 격리 수준

### 격리 수준 설정

```sql
-- 세션 수준
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- 트랜잭션 시작 시
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

### 격리 수준 비교

| 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|------|-----------|-------------------|-------------|
| READ UNCOMMITTED | O | O | O |
| READ COMMITTED | X | O | O |
| REPEATABLE READ | X | X | O |
| SERIALIZABLE | X | X | X |

PostgreSQL: READ UNCOMMITTED = READ COMMITTED

## 트랜잭션

### 기본 트랜잭션

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- 롤백
ROLLBACK;

-- 세이브포인트
SAVEPOINT sp1;
UPDATE accounts SET balance = balance - 50 WHERE id = 1;
ROLLBACK TO sp1;
COMMIT;
```

### Prisma 트랜잭션

```typescript
await prisma.$transaction(async (tx) => {
  await tx.account.update({
    where: { id: 1 },
    data: { balance: { decrement: 100 } }
  });

  await tx.account.update({
    where: { id: 2 },
    data: { balance: { increment: 100 } }
  });
});
```

## 쿼리 최적화

### N+1 쿼리 해결

```prisma
// ❌ N+1
const users = await prisma.user.findMany();
for (const user of users) {
  const posts = await prisma.post.findMany({ where: { authorId: user.id } });
}

// ✅ include 사용
const users = await prisma.user.findMany({
  include: { posts: true }
});

// ✅ 조건부 include
const users = await prisma.user.findMany({
  include: {
    posts: {
      where: { published: true },
      take: 5
    }
  }
});
```

### Select로 필요한 필드만

```prisma
const users = await prisma.user.findMany({
  select: {
    id: true,
    email: true,
    posts: {
      select: {
        title: true
      }
    }
  }
});
```
