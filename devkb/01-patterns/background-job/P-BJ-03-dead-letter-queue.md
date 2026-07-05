---
id: P-BJ-03
title: 데드레터 큐 패턴
stage: Implement
layer: API
pattern_family: Concurrency
tech_tags: [DLQ, 메시지 처리, 오류 처리, 모니터링]
linked_errors: [E-BJ-05, E-BJ-06]
linked_flows: [F-BJ-04]
linked_prompts: [PR-BJ-03]
---

# 데드레터 큐 패턴

## 목표
처리할 수 없는 메시지를 별도의 데드레터 큐로 격리하여 시스템 안정성을 보장하고, 나중에 수동으로 처리할 수 있도록 합니다.

## 언제 사용하는가
- 메시지 처리 실패가 발생할 수 있는 경우
- 재시도로도 해결할 수 없는 문제가 있을 때
- 메시지 처리 오류를 추적해야 할 때
- 비즈니스 크리티컬한 작업

## 핵심 구조

### Prisma 스키마

```prisma
// schema.prisma
enum MessageStatus {
  PENDING    // 대기 중
  PROCESSING // 처리 중
  COMPLETED  // 완료
  FAILED     // 실패 (DLQ로 이동)
  DISCARDED  // 폐기됨
}

model Message {
  id              String    @id @default(cuid())
  topic           String    // 'order.created', 'payment.processed' 등
  payload         Json
  status          MessageStatus @default(PENDING)
  attemptCount    Int       @default(0)
  maxAttempts     Int       @default(5)
  error           String?
  errorStacktrace String?
  processedAt     DateTime?
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt
  deadLetterQueue DeadLetterMessage?

  @@index([status, createdAt])
  @@index([topic])
}

model DeadLetterMessage {
  id              String    @id @default(cuid())
  messageId       String    @unique
  message         Message   @relation(fields: [messageId], references: [id], onDelete: Cascade)
  reason          String    // DLQ로 이동한 이유
  lastError       String
  resolution      String?   // 해결 방법
  resolvedAt      DateTime?
  manualAction    Boolean   @default(false)
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt

  @@index([createdAt])
  @@index([manualAction])
}
```

### 메시지 처리 서비스

```typescript
// queue/message-processor.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';
import { Process, Processor } from '@nestjs/bull';
import { Job } from 'bull';

@Processor('messages')
@Injectable()
export class MessageProcessorService {
  private readonly logger = new Logger(MessageProcessorService.name);

  constructor(private prisma: PrismaService) {}

  @Process()
  async processMessage(job: Job<{ messageId: string }>) {
    const { messageId } = job.data;

    // 메시지 조회
    const message = await this.prisma.message.findUnique({
      where: { id: messageId },
    });

    if (!message) {
      this.logger.warn(`Message ${messageId} not found`);
      throw new Error('Message not found');
    }

    try {
      // 처리 중 상태로 업데이트
      await this.prisma.message.update({
        where: { id: messageId },
        data: { status: 'PROCESSING' },
      });

      // 토픽별 핸들러 실행
      await this.handleMessage(message);

      // 완료 상태로 업데이트
      await this.prisma.message.update({
        where: { id: messageId },
        data: {
          status: 'COMPLETED',
          processedAt: new Date(),
        },
      });

      this.logger.log(`Message ${messageId} processed successfully`);
    } catch (error) {
      await this.handleError(message, error as Error);
    }
  }

  private async handleMessage(message: any) {
    switch (message.topic) {
      case 'order.created':
        return this.handleOrderCreated(message.payload);
      case 'payment.processed':
        return this.handlePaymentProcessed(message.payload);
      default:
        throw new Error(`Unknown topic: ${message.topic}`);
    }
  }

  private async handleError(message: any, error: Error) {
    const attemptCount = message.attemptCount + 1;
    const maxAttempts = message.maxAttempts;

    this.logger.error(
      `Message ${message.id} processing failed (attempt ${attemptCount}/${maxAttempts}): ${error.message}`
    );

    // 재시도 여부 결정
    if (attemptCount < maxAttempts) {
      // 재시도 가능 - 다시 큐에 추가
      await this.prisma.message.update({
        where: { id: message.id },
        data: {
          status: 'PENDING',
          attemptCount,
          error: error.message,
          errorStacktrace: error.stack,
          updatedAt: new Date(),
        },
      });

      throw error; // Bull이 재시도 처리
    } else {
      // 재시도 불가 - DLQ로 이동
      await this.moveToDeadLetterQueue(
        message,
        error,
        'Max retry attempts exceeded'
      );
    }
  }

  private async moveToDeadLetterQueue(
    message: any,
    error: Error,
    reason: string,
  ) {
    // 트랜잭션으로 처리
    await this.prisma.$transaction(async (tx) => {
      // 메시지 상태를 FAILED로 업데이트
      await tx.message.update({
        where: { id: message.id },
        data: {
          status: 'FAILED',
          error: error.message,
          errorStacktrace: error.stack,
        },
      });

      // DLQ에 추가
      await tx.deadLetterMessage.create({
        data: {
          messageId: message.id,
          reason,
          lastError: error.message,
        },
      });
    });

    this.logger.error(
      `Message ${message.id} moved to DLQ: ${reason}`
    );

    // 알림 발송
    await this.notifyDLQMessage(message, reason, error);
  }

  private async notifyDLQMessage(
    message: any,
    reason: string,
    error: Error,
  ) {
    // Slack, 이메일 등으로 알림
    console.log(
      `CRITICAL: Message moved to DLQ - ${message.id}`
    );
  }

  private async handleOrderCreated(payload: any) {
    // 주문 처리 로직
    if (!payload.orderId) {
      throw new Error('Invalid order payload');
    }
  }

  private async handlePaymentProcessed(payload: any) {
    // 결제 처리 로직
    if (!payload.transactionId) {
      throw new Error('Invalid payment payload');
    }
  }
}
```

### DLQ 관리 서비스

```typescript
// queue/dlq-manager.service.ts
@Injectable()
export class DLQManagerService {
  constructor(private prisma: PrismaService) {}

  // DLQ 메시지 조회
  async getDeadLetterMessages(
    page: number = 1,
    pageSize: number = 20,
  ) {
    const skip = (page - 1) * pageSize;

    const messages = await this.prisma.deadLetterMessage.findMany({
      include: {
        message: true,
      },
      orderBy: {
        createdAt: 'desc',
      },
      skip,
      take: pageSize,
    });

    const total = await this.prisma.deadLetterMessage.count();

    return {
      messages,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  // DLQ 메시지 수동 재처리
  async retryDeadLetterMessage(dlqMessageId: string) {
    const dlqMessage = await this.prisma.deadLetterMessage.findUnique({
      where: { id: dlqMessageId },
      include: { message: true },
    });

    if (!dlqMessage) {
      throw new Error('DLQ message not found');
    }

    // 메시지를 PENDING으로 복구
    await this.prisma.$transaction(async (tx) => {
      await tx.message.update({
        where: { id: dlqMessage.messageId },
        data: {
          status: 'PENDING',
          attemptCount: 0, // 재시도 횟수 초기화
          error: null,
          errorStacktrace: null,
        },
      });

      // DLQ에서 제거
      await tx.deadLetterMessage.delete({
        where: { id: dlqMessageId },
      });
    });

    return { success: true };
  }

  // DLQ 메시지 폐기
  async discardDeadLetterMessage(
    dlqMessageId: string,
    resolution: string,
  ) {
    await this.prisma.deadLetterMessage.update({
      where: { id: dlqMessageId },
      data: {
        resolution,
        resolvedAt: new Date(),
      },
    });

    await this.prisma.message.update({
      where: { id: (await this.prisma.deadLetterMessage.findUnique({
        where: { id: dlqMessageId },
      }))?.messageId! },
      data: { status: 'DISCARDED' },
    });

    return { success: true };
  }

  // DLQ 통계
  async getDLQStats() {
    const total = await this.prisma.deadLetterMessage.count();
    const unresolved = await this.prisma.deadLetterMessage.count({
      where: { resolvedAt: null },
    });

    const byReason = await this.prisma.deadLetterMessage.groupBy({
      by: ['reason'],
      _count: true,
    });

    return {
      total,
      unresolved,
      byReason,
    };
  }
}

// 컨트롤러
@Controller('api/dlq')
export class DLQController {
  constructor(private dlqManager: DLQManagerService) {}

  @Get()
  async getMessages(
    @Query('page') page?: string,
    @Query('pageSize') pageSize?: string,
  ) {
    return this.dlqManager.getDeadLetterMessages(
      parseInt(page || '1'),
      parseInt(pageSize || '20')
    );
  }

  @Post(':id/retry')
  async retryMessage(@Param('id') id: string) {
    return this.dlqManager.retryDeadLetterMessage(id);
  }

  @Post(':id/discard')
  async discardMessage(
    @Param('id') id: string,
    @Body() { resolution }: { resolution: string },
  ) {
    return this.dlqManager.discardDeadLetterMessage(id, resolution);
  }

  @Get('stats')
  async getStats() {
    return this.dlqManager.getDLQStats();
  }
}
```

## 최소 예제

```typescript
// 처리 실패 시 DLQ로 이동
try {
  await processMessage(msg);
} catch (error) {
  if (retryCount >= maxRetries) {
    await moveToDLQ(msg, error);
  } else {
    throw error; // 재시도
  }
}
```

## 모니터링 대시보드

```typescript
// 주기적으로 DLQ 점검
@Cron('*/5 * * * *') // 5분마다
async monitorDLQ() {
  const stats = await this.dlqManager.getDLQStats();

  if (stats.unresolved > 10) {
    // 알림 발송
    await this.notificationService.send({
      message: `${stats.unresolved} unresolved messages in DLQ`,
      severity: 'warning',
    });
  }
}
```

## 안티패턴

### 1. DLQ 메시지 모니터링 없음

```typescript
// ❌ 나쁜 예제
// DLQ로 이동했지만 아무도 확인하지 않음

// ✅ 좋은 예제
@Cron('0 * * * *') // 매시간
async checkDLQ() {
  const stats = await this.getDLQStats();
  if (stats.total > 0) {
    await this.alertTeam(stats);
  }
}
```

## 연결된 오류

- **E-BJ-05**: 처리 불가능한 메시지로 인한 큐 정체
- **E-BJ-06**: DLQ 메시지 누적으로 인한 데이터 손실

## 연결된 플로우

- **F-BJ-04**: 메시지 처리 실패 및 복구

## 참고 자료

- AWS SQS Dead Letter Queue: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- RabbitMQ Dead Letter Exchange: https://www.rabbitmq.com/dlx.html
