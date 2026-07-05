---
id: F-13
title: 레이스 컨디션 해결
pattern_id: P-13
error_ids: [E-37, E-38, E-39]
tech_scope: 동시성, 원자성, 상태 관리
---

# 레이스 컨디션 해결

동시 요청으로 인한 레이스 컨디션 문제를 진단하고 해결합니다.

## 1단계: 증상 고정

- 재고가 음수가 됨
- 쿠폰이 중복 사용됨
- 계좌 잔액이 불일치
- 데이터 일관성 오류
- 특정 조건에서만 버그 발생

## 2단계: 재현

```javascript
// ❌ 레이스 컨디션 예제
// 재고 감소 (비원자적 연산)
async function decreaseStock(itemId, quantity) {
  const item = await db.query('SELECT stock FROM items WHERE id = ?', [itemId]);

  if (item.stock >= quantity) {
    // 두 요청이 동시에 여기 도달 가능
    const newStock = item.stock - quantity;
    await db.query('UPDATE items SET stock = ? WHERE id = ?', [newStock, itemId]);
  }
}

// 요청 1: stock = 10, quantity = 5 → newStock = 5
// 요청 2: stock = 10 (캐시됨), quantity = 6 → newStock = 4
// 결과: stock = 4 (예상: 음수 또는 정상 처리)
```

## 3단계: 범위 축소

레이스 컨디션 유형:

1. **Check-Then-Act**: 조건 확인 후 액션 실행 시 사이에 변경
2. **Read-Modify-Write**: 읽기-수정-쓰기 사이에 변경
3. **카운터 증감**: 여러 스레드에서 동시 증감
4. **캐시 무효화**: 캐시와 DB 불일치
5. **초기화 레이스**: 객체/리소스 초기화 중복

## 4단계: 증거 수집

```bash
# 데이터 불일치 확인
SELECT id, stock FROM items WHERE stock < 0;

# 중복 처리 확인
SELECT coupon_code, COUNT(*) FROM coupon_usage
GROUP BY coupon_code HAVING COUNT(*) > 1;
```

```javascript
// 부하 테스트로 재현
async function stressTest() {
  const requests = Array(1000).fill(null).map(() =>
    decreaseStock(1, 1)
  );

  await Promise.all(requests);

  const stock = await getStock(1);
  console.log('Final stock:', stock); // 음수일 가능성
}
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 원자적 연산 부재 | 매우높음 | 중간 |
| 트랜잭션 미사용 | 높음 | 낮음 |
| 캐시 불일치 | 높음 | 중간 |
| 잠금 메커니즘 부재 | 높음 | 중간 |

## 6단계: 수정안 선택

### 수정안 1: 데이터베이스 원자적 연산

```sql
-- ✅ 원자적 UPDATE 사용
UPDATE items SET stock = stock - 5 WHERE id = 1 AND stock >= 5;

-- 결과 확인
SELECT changes() > 0; -- 성공 여부 확인
```

```javascript
// Prisma로 원자적 연산
async function decreaseStock(itemId, quantity) {
  const result = await prisma.item.updateMany({
    where: {
      id: itemId,
      stock: { gte: quantity }
    },
    data: {
      stock: { decrement: quantity }
    }
  });

  return result.count > 0; // 성공 여부
}
```

### 수정안 2: 트랜잭션 사용

```javascript
// ✅ 트랜잭션으로 원자성 보장
async function purchaseItem(itemId, quantity) {
  return await prisma.$transaction(async (tx) => {
    // 1단계: 읽기 (락 포함)
    const item = await tx.item.findUnique({
      where: { id: itemId }
    });

    if (!item || item.stock < quantity) {
      throw new Error('Insufficient stock');
    }

    // 2단계: 쓰기
    const updated = await tx.item.update({
      where: { id: itemId },
      data: { stock: { decrement: quantity } }
    });

    // 3단계: 판매 기록
    await tx.sale.create({
      data: {
        itemId,
        quantity,
        date: new Date()
      }
    });

    return updated;
  });
}
```

### 수정안 3: 분산 락(Distributed Lock)

```javascript
// Redis로 분산 락 구현
const redis = require('redis').createClient();

async function withLock(key, fn, ttl = 5000) {
  const lockId = Math.random().toString();

  try {
    // 락 획득 (NX = 없을 때만 설정)
    const acquired = await redis.set(
      `lock:${key}`,
      lockId,
      'PX', ttl,
      'NX'
    );

    if (!acquired) {
      throw new Error('Could not acquire lock');
    }

    // 함수 실행
    return await fn();
  } finally {
    // 락 해제 (자신의 락만 해제)
    const storedId = await redis.get(`lock:${key}`);
    if (storedId === lockId) {
      await redis.del(`lock:${key}`);
    }
  }
}

// 사용
async function decreaseStock(itemId, quantity) {
  return withLock(`stock:${itemId}`, async () => {
    const item = await db.query('SELECT stock FROM items WHERE id = ?', [itemId]);

    if (item.stock >= quantity) {
      await db.query('UPDATE items SET stock = stock - ? WHERE id = ?', [quantity, itemId]);
      return true;
    }
    return false;
  });
}
```

### 수정안 4: 낙관적 락

```javascript
// 버전 기반 낙관적 락
model Item {
  id Int @id
  stock Int
  version Int @default(0)
}

async function decreaseStock(itemId, quantity) {
  const item = await prisma.item.findUnique({
    where: { id: itemId }
  });

  let retries = 3;
  while (retries > 0) {
    try {
      const updated = await prisma.item.updateMany({
        where: {
          id: itemId,
          version: item.version, // 버전 확인
          stock: { gte: quantity }
        },
        data: {
          stock: { decrement: quantity },
          version: { increment: 1 } // 버전 증가
        }
      });

      if (updated.count > 0) {
        return true;
      }

      // 버전 충돌 - 재시도
      const newItem = await prisma.item.findUnique({
        where: { id: itemId }
      });
      item.version = newItem.version;
      retries--;
    } catch (error) {
      retries--;
    }
  }

  throw new Error('Failed to decrease stock after retries');
}
```

### 수정안 5: 경합 해소(Contention Reduction)

```javascript
// 샤딩으로 경합 감소
// 각 재고를 여러 행으로 분산
model StockShard {
  id Int @id @default(autoincrement())
  itemId Int
  shardId Int
  quantity Int

  @@unique([itemId, shardId])
}

async function decreaseStockSharded(itemId, quantity) {
  // 무작위 샤드에서 감소
  const shardId = Math.floor(Math.random() * 10);

  const result = await prisma.stockShard.updateMany({
    where: {
      itemId,
      shardId,
      quantity: { gte: quantity }
    },
    data: {
      quantity: { decrement: quantity }
    }
  });

  return result.count > 0;
}

// 전체 재고 조회
async function getTotalStock(itemId) {
  const result = await prisma.stockShard.aggregate({
    where: { itemId },
    _sum: { quantity: true }
  });

  return result._sum.quantity || 0;
}
```

### 수정안 6: 메시지 큐 사용

```javascript
// 메시지 큐로 순차 처리
import amqp from 'amqplib';

const connection = await amqp.connect('amqp://localhost');
const channel = await connection.createChannel();

// 구독자: 순차적으로 처리
channel.consume('stock-updates', async (msg) => {
  const { itemId, quantity } = JSON.parse(msg.content.toString());

  await prisma.item.update({
    where: { id: itemId },
    data: { stock: { decrement: quantity } }
  });

  channel.ack(msg);
});

// 발행자: 비동기로 발행
async function publishStockUpdate(itemId, quantity) {
  await channel.assertQueue('stock-updates');
  await channel.sendToQueue(
    'stock-updates',
    Buffer.from(JSON.stringify({ itemId, quantity }))
  );
}
```

## 7단계: 검증

```javascript
describe('Race Condition Prevention', () => {
  it('should handle concurrent decrements correctly', async () => {
    const initialStock = 100;
    let remainingStock = initialStock;

    const requests = Array(100).fill(null).map(() =>
      decreaseStock(1, 1)
    );

    const results = await Promise.allSettled(requests);
    const successful = results.filter(r => r.status === 'fulfilled' && r.value).length;

    const currentStock = await getStock(1);

    expect(currentStock).toBe(initialStock - successful);
    expect(currentStock).toBeGreaterThanOrEqual(0);
  });
});
```

## 8단계: 재발 방지

1. **코드 리뷰**
   - [ ] Read-Modify-Write 구간에 락이 있는가?
   - [ ] 데이터베이스 원자적 연산 사용하는가?
   - [ ] 트랜잭션 범위가 최소인가?

2. **테스트**

```javascript
// 동시성 테스트 추가
it('should pass concurrent stress test', async () => {
  const concurrentRequests = 1000;
  const requests = Array(concurrentRequests).fill(null).map(() =>
    decreaseStock(1, 1)
  );

  const results = await Promise.allSettled(requests);
  const finalStock = await getStock(1);

  expect(finalStock).toBeGreaterThanOrEqual(0);
});
```

## 연결된 프롬프트 블록

- **PB-CL-14-concurrency**: 동시성 제어
- **PB-RP-13-race-test**: 레이스 컨디션 재현
- **PB-DG-14-race-trace**: 레이스 컨디션 추적
- **PB-PA-14-atomicity**: 원자성 보장
- **PB-VF-13-concurrency-test**: 동시성 검증
