---
id: P-QP-02
title: 복합 인덱스 패턴
stage: Design
layer: Data
pattern_family: Persistence
tech_tags: [복합 인덱스, 쿼리 최적화, 커버링 인덱스, 컬럼 순서]
linked_errors: [E-QP-03, E-QP-04]
linked_flows: [F-QP-02]
linked_prompts: [PR-QP-02]
---

# 복합 인덱스 패턴

## 목표
여러 컬럼을 조합한 인덱스로 쿼리 성능을 최적화하고, 커버링 인덱스로 디스크 I/O를 줄입니다.

## 언제 사용하는가
- 여러 컬럼으로 필터링하는 쿼리
- 필터링과 정렬이 함께 필요한 경우
- 커버링 인덱스로 전체 테이블 스캔 회피
- 쿼리 성능이 중요한 경우

## 핵심 구조

### 기본 복합 인덱스

```prisma
// schema.prisma
model Order {
  id        String   @id @default(cuid())
  userId    String
  status    String   // 'pending', 'completed', 'cancelled'
  totalAmount Float
  createdAt DateTime @default(now())

  // WHERE userId = ? AND status = ? ORDER BY createdAt DESC
  @@index([userId, status, createdAt])
}

model Post {
  id        String   @id @default(cuid())
  authorId  String
  published Boolean
  viewCount Int
  createdAt DateTime @default(now())

  // WHERE authorId = ? AND published = true ORDER BY viewCount DESC
  @@index([authorId, published, viewCount(sort: Desc)])
}
```

### 인덱스 순서 원칙

```prisma
// ESR 규칙: Equality, Sort, Range
// WHERE userId = ? ORDER BY createdAt ASC LIMIT 10
@@index([userId, createdAt])

// WHERE status IN (...) AND createdAt >= ? ORDER BY createdAt DESC
@@index([status, createdAt(sort: Desc)])

// WHERE userId = ? AND status IN (...) AND createdAt >= ?
// ORDER BY viewCount DESC
@@index([userId, status, createdAt, viewCount(sort: Desc)])
```

## 최소 예제

```prisma
// 나쁜 인덱스 설계
model User {
  id    String @id
  name  String
  email String

  @@index([name])      // 개별 인덱스
  @@index([email])     // 개별 인덱스
}

// 좋은 인덱스 설계
model User {
  id    String @id
  name  String
  email String

  @@index([email, name]) // 복합 인덱스
}
```

## 커버링 인덱스

```prisma
// 모든 필요한 컬럼을 인덱스에 포함
model Product {
  id       String  @id
  name     String
  price    Float
  quantity Int
  categoryId String

  // 이 인덱스만으로 쿼리 완료 가능 (테이블 접근 불필요)
  @@index([categoryId, name, price, quantity])
}

// 쿼리
// SELECT name, price FROM products WHERE categoryId = 123
// 이 쿼리는 인덱스만으로 처리됨 (인덱스 전용 스캔)
```

## 실전 예제

```typescript
// orders/orders.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';

@Injectable()
export class OrdersService {
  constructor(private prisma: PrismaService) {}

  // 사용자의 완료된 주문 조회 (가장 최신순)
  async getUserCompletedOrders(
    userId: string,
    limit: number = 20,
  ) {
    // @@index([userId, status, createdAt(sort: Desc)])
    // 이 인덱스가 이 쿼리 최적화
    return this.prisma.order.findMany({
      where: {
        userId,
        status: 'completed',
      },
      orderBy: {
        createdAt: 'desc',
      },
      take: limit,
      select: {
        id: true,
        totalAmount: true,
        createdAt: true,
      },
    });
  }

  // 특정 기간의 상태별 주문 통계
  async getOrderStats(
    startDate: Date,
    endDate: Date,
    status: string,
  ) {
    // @@index([status, createdAt])
    return this.prisma.order.groupBy({
      by: ['status'],
      where: {
        createdAt: {
          gte: startDate,
          lte: endDate,
        },
        status,
      },
      _sum: {
        totalAmount: true,
      },
      _count: true,
    });
  }

  // 고가주문 검색
  async searchHighValueOrders(
    minAmount: number,
    limit: number = 50,
  ) {
    // @@index([totalAmount(sort: Desc), createdAt])
    return this.prisma.order.findMany({
      where: {
        totalAmount: {
          gte: minAmount,
        },
      },
      orderBy: {
        totalAmount: 'desc',
      },
      take: limit,
    });
  }
}
```

### Prisma 마이그레이션

```prisma
// schema.prisma - 최적화된 인덱스 설계
model Order {
  id           String   @id @default(cuid())
  userId       String
  status       String
  totalAmount  Float
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  user User @relation(fields: [userId], references: [id])

  // 주요 쿼리 패턴별 인덱스
  // 패턴 1: WHERE userId AND status ORDER BY createdAt
  @@index([userId, status, createdAt(sort: Desc)])

  // 패턴 2: WHERE status AND createdAt >= ORDER BY createdAt
  @@index([status, createdAt(sort: Desc)])

  // 패턴 3: 고가 주문 정렬
  @@index([totalAmount(sort: Desc), createdAt])

  // 패턴 4: WHERE userId AND createdAt >=
  @@index([userId, createdAt(sort: Desc)])
}
```

## 인덱스 분석 및 최적화

```typescript
// 인덱스 성능 확인 (PostgreSQL)
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

// 사용되지 않는 인덱스 찾기
SELECT
  i.schemaname,
  i.tablename,
  i.indexname,
  i.idx_scan
FROM pg_stat_user_indexes i
WHERE i.idx_scan = 0
  AND i.indexname NOT LIKE 'pg_toast%'
ORDER BY i.tablename, i.indexname;
```

## 쿼리 계획 분석

```typescript
// EXPLAIN을 사용한 쿼리 분석
// 좋은 쿼리 (인덱스 사용)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE userId = '123' AND status = 'completed'
ORDER BY createdAt DESC
LIMIT 20;

// 결과: Index Scan using idx_userid_status_createdat ...

// 나쁜 쿼리 (풀 테이블 스캔)
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE totalAmount > 1000
ORDER BY createdAt DESC;

// 결과: Seq Scan on orders ...
```

## 안티패턴

### 1. 필터 컬럼 순서 무시

```prisma
// ❌ 나쁜 예제
// WHERE userId = 123 AND status = 'pending'인데
@@index([status, userId]) // 순서 잘못됨!

// ✅ 좋은 예제
@@index([userId, status]) // Equality 순서 맞춤
```

### 2. 불필요한 인덱스 과다

```prisma
// ❌ 나쁜 예제
model Post {
  id String @id
  authorId String
  title String
  content String

  @@index([authorId])
  @@index([title])
  @@index([content]) // 너무 많은 인덱스!
  @@index([authorId, title])
  @@index([authorId, content])
}

// ✅ 좋은 예제
model Post {
  id String @id
  authorId String
  title String
  content String

  @@index([authorId, title]) // 선택적인 핵심 인덱스
}
```

### 3. 높은 카디널리티 컬럼을 먼저

```prisma
// ❌ 나쁜 예제
// status는 4개 값만 가능 (낮은 카디널리티)
// userId는 백만 개 (높은 카디널리티)
@@index([status, userId])

// ✅ 좋은 예제
@@index([userId, status]) // 높은 카디널리티가 먼저
```

## 연결된 오류

- **E-QP-03**: 쿼리 성능 저하로 인한 타임아웃
- **E-QP-04**: 인덱스 메모리 오버헤드

## 연결된 플로우

- **F-QP-02**: 쿼리 성능 최적화

## 참고 자료

- Use The Index, Luke!: https://use-the-index-luke.com/
- PostgreSQL Index Types: https://www.postgresql.org/docs/current/indexes-types.html
- Prisma Indexes: https://www.prisma.io/docs/reference/api-reference/prisma-schema-reference#index
