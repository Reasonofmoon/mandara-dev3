---
id: P-AC-01
title: 멱등성 명령 패턴
stage: Implement
layer: API
pattern_family: Contract
tech_tags: [멱등성, Idempotency-Key, 중복 방지, 트랜잭션]
linked_errors: [E-AC-01, E-AC-02]
linked_flows: [F-AC-01, F-AC-02]
linked_prompts: [PR-AC-01]
---

# 멱등성 명령 패턴

## 목표
동일한 요청을 여러 번 보내도 동일한 결과를 보장하여, 네트워크 재시도 시 중복 처리를 방지합니다.

## 언제 사용하는가
- 결제, 송금 등 금융 거래
- 계정 생성, 주문 생성 등 중요한 작업
- 재시도 로직이 있는 클라이언트의 요청
- 네트워크 불안정성이 높은 환경

## 언제 사용하지 않는가
- 조회 작업 (GET 요청)
- 상태 조회는 이미 멱등성

## 핵심 구조

### 클라이언트 측

```typescript
import { v4 as uuidv4 } from 'uuid';

export class PaymentClient {
  async createPayment(amount: number, currency: string) {
    const idempotencyKey = uuidv4(); // 또는 요청별 고유 ID

    const response = await fetch('/api/payments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey, // 멱등성 키 전송
      },
      body: JSON.stringify({ amount, currency }),
    });

    if (!response.ok) {
      if (response.status === 409) {
        // 중복 요청 - 이전 결과 사용
        return response.json(); // 이전 결과 반환됨
      }
      throw new Error(`Payment failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// 사용 예제
const client = new PaymentClient();
try {
  const result = await client.createPayment(10000, 'KRW');
  console.log('Payment ID:', result.id);
} catch (error) {
  console.error('Payment error:', error);
  // 재시도 로직
}
```

### 서버 측 - NestJS 구현

```typescript
import {
  Controller,
  Post,
  Body,
  Headers,
  BadRequestException,
  ConflictException,
} from '@nestjs/common';
import { PrismaService } from '@nestjs/prisma';

@Controller('api/payments')
export class PaymentController {
  constructor(
    private prisma: PrismaService,
    private paymentService: PaymentService,
  ) {}

  @Post()
  async createPayment(
    @Body() createPaymentDto: CreatePaymentDto,
    @Headers('idempotency-key') idempotencyKey: string,
  ) {
    // 1. 멱등성 키 검증
    if (!idempotencyKey) {
      throw new BadRequestException('Idempotency-Key header is required');
    }

    // 2. 기존 요청 확인
    const existingPayment = await this.prisma.idempotencyStore.findUnique({
      where: { idempotencyKey },
    });

    if (existingPayment) {
      // 3. 이전에 처리된 요청이면 그 결과 반환
      if (existingPayment.status === 'completed') {
        return existingPayment.response;
      } else if (existingPayment.status === 'failed') {
        throw new ConflictException(existingPayment.error);
      }
      // 진행 중이면 대기
      throw new ConflictException('Payment is already being processed');
    }

    // 4. 멱등성 키 저장 (처리 중 상태)
    await this.prisma.idempotencyStore.create({
      data: {
        idempotencyKey,
        status: 'processing',
      },
    });

    try {
      // 5. 실제 결제 처리
      const payment = await this.paymentService.createPayment(
        createPaymentDto,
      );

      // 6. 성공 결과 저장
      await this.prisma.idempotencyStore.update({
        where: { idempotencyKey },
        data: {
          status: 'completed',
          response: payment,
          completedAt: new Date(),
        },
      });

      return payment;
    } catch (error) {
      // 7. 실패 결과 저장
      await this.prisma.idempotencyStore.update({
        where: { idempotencyKey },
        data: {
          status: 'failed',
          error: error.message,
        },
      });

      throw error;
    }
  }
}
```

### Prisma 스키마

```prisma
model IdempotencyStore {
  id          String    @id @default(cuid())
  idempotencyKey String  @unique
  status      String    // 'processing' | 'completed' | 'failed'
  response    Json?
  error       String?
  createdAt   DateTime  @default(now())
  completedAt DateTime?

  // 24시간 후 자동 삭제를 위한 인덱스
  @@index([createdAt])
}
```

## 최소 예제

```typescript
// 클라이언트
const response = await fetch('/api/transfer', {
  method: 'POST',
  headers: {
    'Idempotency-Key': crypto.randomUUID(),
  },
  body: JSON.stringify({ from: 'acc1', to: 'acc2', amount: 100 }),
});

// 서버
@Post('transfer')
async transfer(
  @Body() dto: TransferDto,
  @Headers('idempotency-key') key: string,
) {
  const existing = await db.idempotency.findUnique({
    where: { key },
  });

  if (existing?.status === 'completed') {
    return existing.response;
  }

  const result = await this.moneyTransfer(dto);
  await db.idempotency.upsert({
    where: { key },
    update: { status: 'completed', response: result },
    create: { key, status: 'completed', response: result },
  });

  return result;
}
```

## 고급 사용법 - Redis 기반 멱등성

대규모 시스템에서는 Redis를 사용하여 성능 향상:

```typescript
import { Redis } from 'ioredis';

export class IdempotentPaymentService {
  constructor(private redis: Redis) {}

  async processPayment(
    idempotencyKey: string,
    paymentData: PaymentData,
  ): Promise<PaymentResult> {
    // 1. Redis에서 기존 결과 확인
    const cachedResult = await this.redis.get(
      `idempotency:${idempotencyKey}`,
    );
    if (cachedResult) {
      return JSON.parse(cachedResult);
    }

    // 2. Lock을 사용하여 동시 처리 방지
    const lockKey = `lock:${idempotencyKey}`;
    const locked = await this.redis.set(
      lockKey,
      '1',
      'EX',
      30, // 30초 제한시간
      'NX', // 이미 존재하면 설정하지 않음
    );

    if (!locked) {
      // 다른 프로세스가 처리 중
      // 대기 후 재시도
      return this.waitForResult(idempotencyKey);
    }

    try {
      // 3. 실제 처리
      const result = await this.executePayment(paymentData);

      // 4. Redis에 결과 캐시 (24시간)
      await this.redis.setex(
        `idempotency:${idempotencyKey}`,
        86400,
        JSON.stringify(result),
      );

      return result;
    } finally {
      // 5. Lock 해제
      await this.redis.del(lockKey);
    }
  }

  private async waitForResult(
    idempotencyKey: string,
    maxWait: number = 30000,
  ): Promise<PaymentResult> {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWait) {
      const result = await this.redis.get(
        `idempotency:${idempotencyKey}`,
      );
      if (result) {
        return JSON.parse(result);
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error('Idempotent request timeout');
  }
}
```

## 안티패턴

### 1. Idempotency-Key 없이 재시도

```typescript
// ❌ 나쁜 예제
async function createOrder(items) {
  return fetch('/api/orders', {
    method: 'POST',
    body: JSON.stringify(items),
  });
  // 재시도 시 중복 주문 생성!
}

// ✅ 좋은 예제
async function createOrder(items) {
  const idempotencyKey = crypto.randomUUID();
  return fetch('/api/orders', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(items),
  });
}
```

### 2. 멱등성 저장소 정리 누락

```typescript
// ❌ 나쁜 예제 - 멱등성 데이터가 계속 증가
await idempotencyStore.create({
  idempotencyKey,
  response: result,
});

// ✅ 좋은 예제 - TTL 설정
await idempotencyStore.create({
  idempotencyKey,
  response: result,
  expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24시간
});

// 또는 정기적인 정리 작업
@Cron('0 0 * * *') // 매일 자정
async cleanupIdempotency() {
  await idempotencyStore.deleteMany({
    where: {
      createdAt: {
        lt: new Date(Date.now() - 24 * 60 * 60 * 1000),
      },
    },
  });
}
```

## 연결된 오류

- **E-AC-01**: Idempotency-Key 없이 요청하여 중복 처리
- **E-AC-02**: 멱등성 저장소 조회 실패로 인한 중복 처리

## 연결된 플로우

- **F-AC-01**: 결제 처리 및 재시도
- **F-AC-02**: 계좌 이체 안전성 보장

## 참고 자료

- Stripe Idempotency: https://stripe.com/docs/api/idempotent_requests
- RFC 7231 Safe and Idempotent Methods: https://tools.ietf.org/html/rfc7231#section-4.2.1
