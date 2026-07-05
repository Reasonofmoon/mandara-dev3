---
id: P-BJ-02
title: 트랜잭션 아웃박스 패턴
stage: Implement
layer: Data
pattern_family: Concurrency
tech_tags: [Outbox, Event Sourcing, 트랜잭션 원자성, 이벤트 발행]
linked_errors: [E-BJ-03, E-BJ-04]
linked_flows: [F-BJ-02, F-BJ-03]
linked_prompts: [PR-BJ-02]
---

# 트랜잭션 아웃박스 패턴

## 목표
데이터베이스 트랜잭션과 이벤트 발행을 원자성 있게 처리하여 데이터 불일치를 방지합니다.

## 언제 사용하는가
- 데이터 변경과 이벤트 발행이 동시에 일어나는 경우
- 메시지 큐와 데이터베이스를 함께 사용할 때
- 분산 시스템에서 일관성이 중요한 경우

## 핵심 구조

### Prisma 스키마

```prisma
// schema.prisma
model Order {
  id        String   @id @default(cuid())
  userId    String
  total     Float
  status    String   @default("PENDING")
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  // 아웃박스 이벤트 관계
  outboxEvents OutboxEvent[]
}

// 아웃박스 테이블
model OutboxEvent {
  id        String   @id @default(cuid())
  aggregateId String  // Order ID
  aggregateType String // "Order"
  eventType String   // "OrderCreated", "OrderPaid" 등
  payload   Json     // 이벤트 데이터
  published Boolean  @default(false)
  publishedAt DateTime?
  createdAt DateTime @default(now())

  @@index([published, createdAt])
  @@index([aggregateId])
}
```

### 주문 생성 시 이벤트 발행

```typescript
// orders/orders.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';

interface CreateOrderDto {
  userId: string;
  items: Array<{ productId: string; quantity: number }>;
  total: number;
}

@Injectable()
export class OrdersService {
  constructor(private prisma: PrismaService) {}

  async createOrder(dto: CreateOrderDto) {
    // 트랜잭션으로 Order 생성과 Outbox 이벤트 발행
    const result = await this.prisma.$transaction(async (tx) => {
      // 1. Order 생성
      const order = await tx.order.create({
        data: {
          userId: dto.userId,
          total: dto.total,
          status: 'PENDING',
        },
      });

      // 2. Outbox 이벤트 추가
      await tx.outboxEvent.create({
        data: {
          aggregateId: order.id,
          aggregateType: 'Order',
          eventType: 'OrderCreated',
          payload: {
            orderId: order.id,
            userId: dto.userId,
            total: dto.total,
            items: dto.items,
            createdAt: order.createdAt,
          },
        },
      });

      return order;
    });

    return result;
  }

  // 결제 완료 시
  async markOrderPaid(orderId: string, paymentId: string) {
    await this.prisma.$transaction(async (tx) => {
      // 1. Order 상태 업데이트
      const order = await tx.order.update({
        where: { id: orderId },
        data: { status: 'PAID' },
      });

      // 2. Outbox 이벤트 추가
      await tx.outboxEvent.create({
        data: {
          aggregateId: orderId,
          aggregateType: 'Order',
          eventType: 'OrderPaid',
          payload: {
            orderId,
            paymentId,
            paidAt: new Date(),
          },
        },
      });
    });
  }
}
```

### 아웃박스 폴러 (이벤트 발행)

```typescript
// outbox/outbox-poller.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from 'prisma/prisma.service';
import { MessageQueue } from 'queue/message-queue';

@Injectable()
export class OutboxPollerService {
  private readonly logger = new Logger(OutboxPollerService.name);

  constructor(
    private prisma: PrismaService,
    private messageQueue: MessageQueue,
  ) {}

  // 매초마다 미발행 이벤트 확인
  @Cron('*/1 * * * * *')
  async pollUnpublishedEvents() {
    try {
      const unpublished = await this.prisma.outboxEvent.findMany({
        where: {
          published: false,
        },
        take: 100, // 배치 처리
        orderBy: {
          createdAt: 'asc',
        },
      });

      for (const event of unpublished) {
        try {
          // 이벤트를 메시지 큐에 발행
          await this.messageQueue.publish(
            `${event.aggregateType}.${event.eventType}`,
            event.payload
          );

          // 발행 완료 표시
          await this.prisma.outboxEvent.update({
            where: { id: event.id },
            data: {
              published: true,
              publishedAt: new Date(),
            },
          });

          this.logger.log(
            `Published event: ${event.eventType} for ${event.aggregateId}`
          );
        } catch (error) {
          this.logger.error(
            `Failed to publish event ${event.id}: ${error.message}`
          );
          // 재시도는 다음 주기에서 수행
        }
      }
    } catch (error) {
      this.logger.error(
        `Outbox polling error: ${error.message}`
      );
    }
  }

  // 오래된 발행 완료 이벤트 정리
  @Cron('0 0 * * *') // 매일 자정
  async cleanupPublishedEvents() {
    const thirtyDaysAgo = new Date(
      Date.now() - 30 * 24 * 60 * 60 * 1000
    );

    const deleted = await this.prisma.outboxEvent.deleteMany({
      where: {
        published: true,
        publishedAt: {
          lt: thirtyDaysAgo,
        },
      },
    });

    this.logger.log(`Cleaned up ${deleted.count} published events`);
  }
}
```

### 메시지 큐 구현

```typescript
// queue/message-queue.ts
import { Injectable } from '@nestjs/common';
import { Queue } from 'bull';
import { InjectQueue } from '@nestjs/bull';

@Injectable()
export class MessageQueue {
  constructor(
    @InjectQueue('events') private eventQueue: Queue,
  ) {}

  async publish(topic: string, payload: any) {
    await this.eventQueue.add(
      {
        topic,
        payload,
      },
      {
        attempts: 5,
        backoff: {
          type: 'exponential',
          delay: 2000,
        },
      }
    );
  }
}

// queue/event-processor.ts
import { Process, Processor } from '@nestjs/bull';
import { Job } from 'bull';

@Processor('events')
export class EventProcessor {
  @Process()
  async handleEvent(job: Job<{ topic: string; payload: any }>) {
    const { topic, payload } = job.data;

    // 이벤트 타입별 처리
    if (topic === 'Order.OrderCreated') {
      await this.handleOrderCreated(payload);
    } else if (topic === 'Order.OrderPaid') {
      await this.handleOrderPaid(payload);
    }
  }

  private async handleOrderCreated(payload: any) {
    // 이메일 발송, 재고 차감, 분석 등
    console.log('Order created:', payload);
  }

  private async handleOrderPaid(payload: any) {
    // 배송 처리, 알림 발송 등
    console.log('Order paid:', payload);
  }
}
```

## 최소 예제

```typescript
// 트랜잭션으로 데이터와 이벤트 함께 저장
await prisma.$transaction(async (tx) => {
  // 1. 데이터 변경
  const order = await tx.order.create({ data: { ...} });

  // 2. 이벤트 저장
  await tx.outboxEvent.create({
    data: {
      aggregateId: order.id,
      eventType: 'OrderCreated',
      payload: { ...order },
    },
  });
});

// 별도 프로세스에서 이벤트 발행
const events = await tx.outboxEvent.findMany({
  where: { published: false },
});

for (const event of events) {
  await messageQueue.publish(event.topic, event.payload);
  await tx.outboxEvent.update({
    where: { id: event.id },
    data: { published: true },
  });
}
```

## 안티패턴

### 1. 트랜잭션 없이 데이터와 이벤트 저장

```typescript
// ❌ 나쁜 예제
const order = await prisma.order.create({ data: {...} });
await messageQueue.publish('OrderCreated', order); // 실패하면 주문만 생성됨!

// ✅ 좋은 예제
await prisma.$transaction(async (tx) => {
  const order = await tx.order.create({ data: {...} });
  await tx.outboxEvent.create({
    data: { aggregateId: order.id, payload: {...} }
  });
});
```

### 2. Outbox 폴러 없이 실시간 발행 시도

```typescript
// ❌ 나쁜 예제
await tx.order.create();
await messageQueue.publish(); // 트랜잭션 중 메시지 전송 - 원자성 깨짐!

// ✅ 좋은 예제
await tx.order.create();
await tx.outboxEvent.create(); // 트랜잭션과 함께
// 별도 폴러가 비동기로 발행
```

## 연결된 오류

- **E-BJ-03**: 트랜잭션 실패로 인한 이벤트 손실
- **E-BJ-04**: 이벤트 발행 실패로 인한 데이터 불일치

## 연결된 플로우

- **F-BJ-02**: 주문 생성 및 이벤트 발행
- **F-BJ-03**: 결제 완료 처리

## 참고 자료

- Transactional Outbox Pattern: https://microservices.io/patterns/data/transactional-outbox.html
- Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
