---
id: E-LS-10
title: 멱등성 누락
error_class: Logic-State
symptoms:
  - 중복 요청 시 여러 번 처리
  - 데이터 중복 생성
  - 부작용 반복
exact_messages:
  - "Duplicate transaction"
  - "Record already exists"
  - "Idempotency key mismatch"
tech_tags:
  - API Design
  - Idempotency
  - Database
  - Transactions
linked_patterns: []
linked_flows: []
---

# 멱등성 누락

## 증상
같은 요청을 여러 번 실행하면 매번 다른 결과가 나옵니다. 중복 결제, 데이터 중복 생성 등이 발생합니다.

## 빠른 해결법

### 1. Idempotency Key
```typescript
app.post('/api/payment', async (req, res) => {
  const idempotencyKey = req.headers['idempotency-key'];

  if (!idempotencyKey) {
    return res.status(400).json({ error: 'Idempotency-Key required' });
  }

  // 캐시 확인
  const cached = await redis.get(`idempotency:${idempotencyKey}`);
  if (cached) {
    return res.json(JSON.parse(cached));
  }

  // 결제 처리
  const result = await processPayment(req.body);

  // 결과 캐시 (1시간)
  await redis.setex(`idempotency:${idempotencyKey}`, 3600, JSON.stringify(result));

  res.json(result);
});
```

### 2. 데이터베이스 unique 제약
```prisma
model Payment {
  id            Int     @id
  transactionId String  @unique  // 멱등성 키
  amount        Float
  status        String
}
```

```typescript
try {
  const payment = await prisma.payment.create({
    data: {
      transactionId: req.body.transactionId,
      amount: req.body.amount,
      status: 'completed'
    }
  });
} catch (error) {
  if (error.code === 'P2002') {
    // 이미 존재 - 기존 결과 반환
    const existing = await prisma.payment.findUnique({
      where: { transactionId: req.body.transactionId }
    });
    res.json(existing);
  }
}
```

### 3. 클라이언트에서 Idempotency Key 생성
```typescript
const idempotencyKey = crypto.randomUUID();

async function makePayment() {
  const response = await fetch('/api/payment', {
    method: 'POST',
    headers: {
      'Idempotency-Key': idempotencyKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ amount: 100 })
  });

  return response.json();
}
```

## 연결된 패턴
- E-LS-06-transaction-boundary
- E-PF-09-retry-storm

## 재발 방지
1. PUT/POST에 Idempotency-Key 사용
2. 결과 캐싱 (Redis)
3. 데이터베이스 unique 제약
4. 결과 반환 전 캐시 저장
