---
id: F-05
title: API 멱등성 문제 해결
pattern_id: P-05
error_ids: [E-13, E-14, E-15]
tech_scope: API 설계, 분산 시스템, 재시도 로직
---

# API 멱등성 문제 해결

동일한 요청을 여러 번 실행했을 때 부작용이 발생하는 멱등성 문제를 해결합니다.

## 1단계: 증상 고정

문제 증상:
- 같은 요청을 여러 번 보내면 다른 결과가 나옴
- 결제가 여러 번 처리됨
- 주문이 중복으로 생성됨
- 재시도 로직이 부작용 발생
- 네트워크 오류로 재시도 시 중복 처리

## 2단계: 재현

```javascript
// ❌ 비멱등 엔드포인트
// POST /api/orders - 매번 새 주문 생성
app.post('/api/orders', async (req, res) => {
  const order = await Order.create(req.body);
  res.json(order);
});

// 클라이언트: 네트워크 오류로 재시도
fetch('/api/orders', {
  method: 'POST',
  body: JSON.stringify({ items: [1, 2, 3], amount: 100 })
})
  .catch(() => {
    // 재시도 - 또 다른 주문 생성!
    fetch('/api/orders', {
      method: 'POST',
      body: JSON.stringify({ items: [1, 2, 3], amount: 100 })
    });
  });
```

## 3단계: 범위 축소

멱등성 문제의 유형:

1. **비멱등 엔드포인트**: POST로 실행할 때마다 새로운 리소스 생성
2. **중복 검사 부재**: 동일 요청의 중복 실행 여부 확인 안 함
3. **재시도 메커니즘 부재**: 실패 시 안전한 재시도 불가
4. **분산 트랜잭션**: 여러 서비스 간 부분 실패
5. **캐시 일관성**: 멱등 요청 캐싱 미흡

## 4단계: 증거 수집

```bash
# 같은 요청 여러 번 보내기
for i in {1..3}; do
  curl -X POST http://localhost:3001/api/orders \
    -H "Content-Type: application/json" \
    -d '{"items": [1,2,3], "amount": 100}' \
    -H "Idempotency-Key: req-123"
done

# 결과 확인: 모두 같은 주문 ID여야 함
```

```javascript
// 재시도 시 중복 생성 여부 확인
const orders = [];

async function createOrder(data) {
  const response = await fetch('/api/orders', {
    method: 'POST',
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error('Failed to create order');
  }

  return response.json();
}

// 3번 시도
for (let i = 0; i < 3; i++) {
  try {
    const order = await createOrder({ amount: 100 });
    orders.push(order);
  } catch (err) {
    console.log(`Attempt ${i + 1} failed:`, err);
  }
}

console.log(`Created ${orders.length} orders`);
// ❌ 예상: 1개, 실제: 3개 (멱등성 없음)
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 해결 난도 |
|------|------|---------|
| Idempotency-Key 미구현 | 매우높음 | 중간 |
| 중복 검사 로직 부재 | 높음 | 중간 |
| 재시도 로직 부재 | 높음 | 낮음 |
| 데이터베이스 제약 부족 | 중간 | 중간 |
| 분산 트랜잭션 미처리 | 중간 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: Idempotency-Key 구현 (권장)

```javascript
// server.js
const express = require('express');
const Redis = require('ioredis');

const app = express();
const redis = new Redis();

// 1. Idempotency-Key 검증 미들웨어
app.use(express.json());

const idempotencyMiddleware = async (req, res, next) => {
  if (!['POST', 'PUT', 'DELETE'].includes(req.method)) {
    return next();
  }

  const key = req.headers['idempotency-key'];

  if (!key) {
    return res.status(400).json({
      error: 'Idempotency-Key header required'
    });
  }

  // Redis에서 이전 응답 확인
  const cachedResponse = await redis.get(`idempotency:${key}`);

  if (cachedResponse) {
    return res
      .status(200)
      .set('Idempotency-Replay', 'true')
      .json(JSON.parse(cachedResponse));
  }

  // 요청 처리를 위해 original json 저장
  req.idempotencyKey = key;
  next();
};

app.use(idempotencyMiddleware);

// 2. 응답 저장 미들웨어
const saveIdempotencyResponse = async (key, data) => {
  // 24시간 TTL로 저장
  await redis.setex(
    `idempotency:${key}`,
    86400,
    JSON.stringify(data)
  );
};

// 3. 주문 생성 엔드포인트
app.post('/api/orders', async (req, res) => {
  const { items, amount } = req.body;
  const idempotencyKey = req.idempotencyKey;

  try {
    // 데이터베이스에서 중복 확인
    const existing = await Order.findOne({
      idempotencyKey
    });

    if (existing) {
      const response = existing.toJSON();
      await saveIdempotencyResponse(idempotencyKey, response);
      return res.json(response);
    }

    // 새 주문 생성
    const order = await Order.create({
      items,
      amount,
      idempotencyKey
    });

    const response = order.toJSON();
    await saveIdempotencyResponse(idempotencyKey, response);

    res.status(201).json(response);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### 수정안 2: 데이터베이스 유니크 제약

```sql
-- 데이터베이스 스키마
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key VARCHAR(255) UNIQUE NOT NULL,
  items JSONB NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_idempotency_key ON orders(idempotency_key);
```

```javascript
// Prisma 스키마
model Order {
  id String @id @default(cuid())
  idempotencyKey String @unique @map("idempotency_key")
  items Json
  amount Decimal
  status String @default("pending")
  createdAt DateTime @default(now()) @map("created_at")
}
```

### 수정안 3: 클라이언트 재시도 로직

```javascript
// client.js
import { v4 as uuidv4 } from 'uuid';

async function createOrderWithRetry(orderData, maxRetries = 3) {
  const idempotencyKey = uuidv4();
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey
        },
        body: JSON.stringify(orderData)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      lastError = error;
      console.warn(`Attempt ${attempt} failed:`, error);

      if (attempt < maxRetries) {
        // 지수 백오프
        const delay = Math.pow(2, attempt - 1) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

// 사용
try {
  const order = await createOrderWithRetry({
    items: [1, 2, 3],
    amount: 100
  });
  console.log('Order created:', order);
} catch (error) {
  console.error('Failed to create order:', error);
}
```

### 수정안 4: NestJS에서 구현

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Redis } from 'ioredis';

@Injectable()
export class IdempotencyMiddleware implements NestMiddleware {
  constructor(private redis: Redis) {}

  async use(req: any, res: any, next: () => void) {
    if (!['POST', 'PUT', 'DELETE'].includes(req.method)) {
      return next();
    }

    const key = req.headers['idempotency-key'];

    if (!key) {
      return res.status(400).json({
        error: 'Idempotency-Key header required'
      });
    }

    const cached = await this.redis.get(`idempotency:${key}`);

    if (cached) {
      return res
        .set('Idempotency-Replay', 'true')
        .json(JSON.parse(cached));
    }

    req.idempotencyKey = key;

    // 응답 저장을 위해 원본 json 메서드 덮어쓰기
    const originalJson = res.json.bind(res);
    res.json = (data: any) => {
      this.redis.setex(
        `idempotency:${key}`,
        86400,
        JSON.stringify(data)
      );
      return originalJson(data);
    };

    next();
  }
}
```

## 7단계: 검증

```javascript
describe('API Idempotency', () => {
  it('should return same result for identical requests', async () => {
    const idempotencyKey = 'test-key-123';
    const orderData = { items: [1, 2, 3], amount: 100 };

    const response1 = await fetch('/api/orders', {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(orderData)
    });

    const order1 = await response1.json();

    // 동일한 요청 다시 보내기
    const response2 = await fetch('/api/orders', {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(orderData)
    });

    const order2 = await response2.json();

    // 같은 주문ID여야 함
    expect(order1.id).toBe(order2.id);
    expect(response2.headers.get('Idempotency-Replay')).toBe('true');
  });
});
```

## 8단계: 재발 방지

1. **API 설계 원칙**
   - POST: 새 리소스 생성 (멱등성 권장)
   - PUT: 리소스 전체 교체 (멱등)
   - PATCH: 리소스 부분 수정 (멱등 권장)
   - DELETE: 리소스 삭제 (멱등)

2. **모니터링**

```javascript
// 중복 요청 감지
app.use((req, res, next) => {
  if (res.headers['Idempotency-Replay'] === 'true') {
    console.log('Idempotent replay:', req.idempotencyKey);
  }
  next();
});
```

## 연결된 프롬프트 블록

- **PB-CL-06-api-design**: API 설계 원칙
- **PB-RP-05-idempotency-test**: 멱등성 테스트
- **PB-DG-06-duplicate-check**: 중복 검사 로직
- **PB-PA-06-retry-logic**: 재시도 로직 구현
- **PB-VF-05-idempotency**: 멱등성 검증
