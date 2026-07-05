---
id: P-MG-01
title: 무중단 마이그레이션 패턴
stage: Design
layer: Data
pattern_family: Persistence
tech_tags: [Zero-Downtime, Expand/Contract, 스키마 변경]
linked_errors: [E-MG-01, E-MG-02]
linked_flows: [F-MG-01, F-MG-02]
linked_prompts: [PR-MG-01]
---

# 무중단 마이그레이션 패턴

## 목표
서비스를 중단하지 않고 데이터베이스 스키마를 안전하게 변경합니다.

## 언제 사용하는가
- 프로덕션 환경에서 스키마 변경
- 테이블 구조 변경
- 컬럼 이름 변경
- 데이터 타입 변경

## Expand/Contract 패턴

### Step 1: Expand (확장)

```prisma
// schema.prisma - 변경 전
model User {
  id    String @id @default(cuid())
  email String @unique
}

// Step 1: 새 컬럼 추가
model User {
  id       String @id @default(cuid())
  email    String @unique
  username String? // 새 컬럼 (nullable)
}
```

마이그레이션:
```sql
-- Step 1: Expand
ALTER TABLE "User" ADD COLUMN username VARCHAR(255);
```

### Step 2: 이중 쓰기 (Dual Write)

```typescript
// users/users.service.ts
@Injectable()
export class UsersService {
  async createUser(email: string, username: string) {
    // 기존 필드와 새 필드 모두에 쓰기
    return this.prisma.user.create({
      data: {
        email,
        username, // 새 필드도 함께 저장
      },
    });
  }

  async updateUser(id: string, email: string, username: string) {
    return this.prisma.user.update({
      where: { id },
      data: {
        email,
        username, // 새 필드도 업데이트
      },
    });
  }
}
```

### Step 3: 데이터 마이그레이션

```typescript
// migrations/migrate-username.ts
import { PrismaClient } from '@prisma/client';

async function main() {
  const prisma = new PrismaClient();

  // 기존 데이터에서 새 필드 채우기
  const users = await prisma.user.findMany();

  for (const user of users) {
    // 이메일에서 username 도출
    const username = user.email.split('@')[0];

    await prisma.user.update({
      where: { id: user.id },
      data: { username },
    });
  }

  console.log(`Migrated ${users.length} users`);
}

main();
```

### Step 4: Contract (축소)

```prisma
// schema.prisma - 변경 후
model User {
  id       String @id @default(cuid())
  username String @unique // 새 필드가 주요 필드로
  // email 필드 제거
}
```

마이그레이션:
```sql
-- Step 4: Contract
ALTER TABLE "User" DROP COLUMN email;
```

## 실전 예제 - 테이블 분할

### Before
```prisma
model Order {
  id          String @id
  userId      String
  items       String // JSON
  total       Float
  status      String
  createdAt   DateTime
  updatedAt   DateTime
}
```

### Step 1: Expand - 새 테이블 추가

```prisma
model Order {
  id          String @id
  userId      String
  items       String? // 기존 필드는 nullable로
  total       Float
  status      String
  createdAt   DateTime
  updatedAt   DateTime
}

model OrderItem {
  id        String @id @default(cuid())
  orderId   String
  productId String
  quantity  Int
  price     Float
}
```

### Step 2: 이중 쓰기

```typescript
@Injectable()
export class OrdersService {
  async createOrder(userId: string, items: OrderItemInput[]) {
    // 트랜잭션으로 원자성 보장
    return this.prisma.$transaction(async (tx) => {
      // 기존 방식: items를 JSON으로 저장
      const order = await tx.order.create({
        data: {
          userId,
          items: JSON.stringify(items),
          total: items.reduce((sum, i) => sum + i.price, 0),
          status: 'PENDING',
        },
      });

      // 새로운 방식: OrderItem 생성
      await Promise.all(
        items.map(item =>
          tx.orderItem.create({
            data: {
              orderId: order.id,
              productId: item.productId,
              quantity: item.quantity,
              price: item.price,
            },
          })
        )
      );

      return order;
    });
  }
}
```

### Step 3: 데이터 마이그레이션

```typescript
async function migrateOrderItems(
  prisma: PrismaClient
) {
  const orders = await prisma.order.findMany({
    where: {
      items: { not: null },
    },
  });

  for (const order of orders) {
    const items = JSON.parse(order.items || '[]');

    for (const item of items) {
      await prisma.orderItem.upsert({
        where: {
          id: `${order.id}-${item.productId}`,
        },
        create: {
          id: `${order.id}-${item.productId}`,
          orderId: order.id,
          productId: item.productId,
          quantity: item.quantity,
          price: item.price,
        },
        update: {},
      });
    }
  }
}
```

### Step 4: Contract

```typescript
// 모든 read를 새 테이블에서 수행하는지 확인
async getOrder(id: string) {
  return this.prisma.order.findUnique({
    where: { id },
    include: {
      items: true, // OrderItem에서 읽음
    },
  });
}

// 기존 items 필드 제거 가능
```

## 최소 예제

```prisma
// Step 1: Expand
model User {
  id       String @id
  name     String
  newName  String? // 새 필드
}

// Step 2: 데이터 마이그레이션
// UPDATE User SET newName = name

// Step 3: 애플리케이션 업데이트
// newName 사용

// Step 4: Contract
// ALTER TABLE User DROP COLUMN name
```

## 롤백 전략

```typescript
// 문제 발생 시 이전 상태로 복구
async function rollbackMigration(prisma: PrismaClient) {
  // 신규 필드를 사용하는 쿼리 실패 시
  // 기존 필드로 복구
  const users = await prisma.user.findMany({
    where: { username: { not: null } },
  });

  for (const user of users) {
    // username이 있으면 새 버전 사용
    // 없으면 기존 email 사용
  }
}
```

## 안티패턴

### 1. 한 번에 모든 것 변경

```typescript
// ❌ 나쁜 예제
// 오래된 필드 즉시 삭제
ALTER TABLE User DROP COLUMN email;
// 새 애플리케이션 배포

// ✅ 좋은 예제
// Step 1: 새 필드 추가
// Step 2: 이중 쓰기
// Step 3: 데이터 마이그레이션
// Step 4: 기존 필드 삭제
```

## 연결된 오류

- **E-MG-01**: 마이그레이션 중 서비스 중단
- **E-MG-02**: 데이터 불일치로 인한 무결성 문제

## 연결된 플로우

- **F-MG-01**: 테이블 구조 변경
- **F-MG-02**: 필드 이름 변경

## 참고 자료

- Zero-Downtime Deployment: https://wiki.postgresql.org/wiki/SlowlyChangingDimension
- Expand-Contract Pattern: https://martinfowler.com/bliki/ParallelChange.html
