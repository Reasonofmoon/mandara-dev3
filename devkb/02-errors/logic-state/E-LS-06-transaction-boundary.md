---
id: E-LS-06
title: 트랜잭션 경계 오류
error_class: Logic-State
symptoms:
  - 부분적 업데이트
  - 데이터 불일치
  - 롤백 실패
exact_messages:
  - "Transaction not started"
  - "Cannot commit without transaction"
  - "Database constraint violation"
tech_tags:
  - Database
  - Transactions
  - Data Consistency
  - Prisma
linked_patterns: []
linked_flows: []
---

# 트랜잭션 경계 오류

## 증상
데이터베이스 작업이 부분적으로 완료되거나 일관성이 깨집니다. 트랜잭션 시작/종료가 올바르지 않을 때 발생합니다.

## 빠른 해결법

### 1. Prisma Transaction
```typescript
const result = await prisma.$transaction(async (tx) => {
  const user = await tx.user.create({
    data: { email: 'user@example.com' }
  });

  const post = await tx.post.create({
    data: { title: 'Hello', authorId: user.id }
  });

  return { user, post };
});
```

### 2. PostgreSQL Transaction
```typescript
const client = await pool.connect();

try {
  await client.query('BEGIN');
  await client.query('INSERT INTO users VALUES ($1)', [userId]);
  await client.query('INSERT INTO posts VALUES ($1, $2)', [postId, userId]);
  await client.query('COMMIT');
} catch (error) {
  await client.query('ROLLBACK');
  throw error;
} finally {
  client.release();
}
```

### 3. 오류 처리
```typescript
try {
  await prisma.$transaction(async (tx) => {
    // 작업
  });
} catch (error) {
  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    console.error('Database error:', error.code);
  }
  throw error;
}
```

## 연결된 패턴
- E-RT-05-prisma-migration-drift
- E-DO-04-migration-order-error

## 재발 방지
1. 모든 관련 작업을 하나의 트랜잭션에 포함
2. 에러 처리로 롤백 보장
3. 데이터 일관성 검증 테스트
