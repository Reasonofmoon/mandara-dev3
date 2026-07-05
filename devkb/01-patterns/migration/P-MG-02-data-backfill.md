---
id: P-MG-02
title: 대규모 데이터 백필 패턴
stage: Implement
layer: Data
pattern_family: Persistence
tech_tags: [배치 처리, 진행률 추적, 대규모 데이터, 롤백]
linked_errors: [E-MG-03, E-MG-04]
linked_flows: [F-MG-03]
linked_prompts: [PR-MG-02]
---

# 대규모 데이터 백필 패턴

## 목표
대규모 데이터셋을 효율적으로 처리하고 진행률을 추적하며, 실패 시 롤백할 수 있도록 구현합니다.

## 핵심 구조

### 배치 처리 기본

```typescript
// migrations/backfill-username.ts
import { PrismaClient } from '@prisma/client';

async function backfillUsername() {
  const prisma = new PrismaClient();
  const BATCH_SIZE = 1000;

  let offset = 0;
  let processed = 0;

  while (true) {
    // 배치 단위로 조회
    const users = await prisma.user.findMany({
      skip: offset,
      take: BATCH_SIZE,
      select: { id: true, email: true },
    });

    if (users.length === 0) break;

    // 배치 처리
    await Promise.all(
      users.map(user =>
        prisma.user.update({
          where: { id: user.id },
          data: {
            username: user.email.split('@')[0],
          },
        })
      )
    );

    processed += users.length;
    offset += BATCH_SIZE;

    console.log(`Processed: ${processed} users`);
  }

  await prisma.$disconnect();
  console.log(`Backfill completed: ${processed} users`);
}

backfillUsername().catch(console.error);
```

### 진행률 추적

```typescript
// migrations/backfill-with-progress.ts
import { PrismaClient } from '@prisma/client';

interface BackfillProgress {
  id: string;
  name: string;
  totalRecords: number;
  processedRecords: number;
  failedRecords: number;
  status: 'running' | 'completed' | 'failed';
  startedAt: Date;
  completedAt?: Date;
  errorMessage?: string;
}

async function backfillWithProgress(
  prisma: PrismaClient,
  backfillName: string
) {
  const BATCH_SIZE = 500;

  // 진행 상황 저장 테이블
  let progress = await prisma.backfillProgress.create({
    data: {
      name: backfillName,
      totalRecords: 0,
      processedRecords: 0,
      failedRecords: 0,
      status: 'running',
      startedAt: new Date(),
    },
  });

  try {
    // 총 레코드 수 계산
    const total = await prisma.user.count();
    progress = await prisma.backfillProgress.update({
      where: { id: progress.id },
      data: { totalRecords: total },
    });

    let offset = 0;
    let failedCount = 0;

    while (offset < total) {
      try {
        const users = await prisma.user.findMany({
          skip: offset,
          take: BATCH_SIZE,
          select: { id: true, email: true },
        });

        if (users.length === 0) break;

        // 트랜잭션으로 배치 처리
        await prisma.$transaction(
          users.map(user =>
            prisma.user.update({
              where: { id: user.id },
              data: {
                username: user.email.split('@')[0],
              },
            })
          )
        );

        offset += BATCH_SIZE;

        // 진행률 업데이트
        progress = await prisma.backfillProgress.update({
          where: { id: progress.id },
          data: {
            processedRecords: Math.min(offset, total),
          },
        });

        const percentage =
          ((progress.processedRecords / total) * 100).toFixed(2);
        console.log(
          `Progress: ${progress.processedRecords}/${total} (${percentage}%)`
        );
      } catch (batchError) {
        failedCount++;
        console.error(
          `Batch failed at offset ${offset}:`,
          batchError
        );

        // 실패 횟수 업데이트
        await prisma.backfillProgress.update({
          where: { id: progress.id },
          data: {
            failedRecords: failedCount,
          },
        });

        // 재시도 또는 계속
        if (failedCount > 3) {
          throw new Error('Too many failures');
        }

        // 잠시 대기 후 재시도
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    // 완료
    progress = await prisma.backfillProgress.update({
      where: { id: progress.id },
      data: {
        status: 'completed',
        completedAt: new Date(),
      },
    });

    console.log(
      `Backfill completed: ${progress.processedRecords}/${progress.totalRecords}`
    );
  } catch (error) {
    // 실패
    await prisma.backfillProgress.update({
      where: { id: progress.id },
      data: {
        status: 'failed',
        errorMessage: (error as Error).message,
      },
    });

    throw error;
  }
}
```

## 대규모 데이터 최적화

```typescript
// 메모리 효율적인 처리
async function efficientBackfill(prisma: PrismaClient) {
  const BATCH_SIZE = 100;

  // 커서 기반으로 데이터 처리 (메모리 효율)
  let cursor: string | null = null;

  while (true) {
    const users = await prisma.user.findMany({
      ...(cursor && { skip: 1, cursor: { id: cursor } }),
      take: BATCH_SIZE,
      select: { id: true, email: true },
      orderBy: { id: 'asc' },
    });

    if (users.length === 0) break;

    // 처리
    for (const user of users) {
      await updateUser(user);
    }

    cursor = users[users.length - 1].id;
  }
}

// 병렬 처리
async function parallelBackfill(prisma: PrismaClient) {
  const BATCH_SIZE = 500;
  const PARALLEL_COUNT = 4;

  const total = await prisma.user.count();
  const batchCount = Math.ceil(total / BATCH_SIZE);

  // PARALLEL_COUNT개의 배치를 동시에 처리
  for (let i = 0; i < batchCount; i += PARALLEL_COUNT) {
    const promises = [];

    for (let j = 0; j < PARALLEL_COUNT && i + j < batchCount; j++) {
      const offset = (i + j) * BATCH_SIZE;
      promises.push(
        processBatch(prisma, offset, BATCH_SIZE)
      );
    }

    await Promise.all(promises);
  }
}

async function processBatch(
  prisma: PrismaClient,
  offset: number,
  batchSize: number
) {
  const users = await prisma.user.findMany({
    skip: offset,
    take: batchSize,
  });

  return Promise.all(
    users.map(user =>
      prisma.user.update({
        where: { id: user.id },
        data: { username: user.email.split('@')[0] },
      })
    )
  );
}
```

### Prisma 스키마

```prisma
// schema.prisma
model BackfillProgress {
  id              String   @id @default(cuid())
  name            String   @unique
  totalRecords    Int
  processedRecords Int     @default(0)
  failedRecords   Int      @default(0)
  status          String   @default("running")
  startedAt       DateTime
  completedAt     DateTime?
  errorMessage    String?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt

  @@index([status])
}
```

## 롤백 전략

```typescript
// 롤백 함수
async function rollbackBackfill(
  prisma: PrismaClient,
  backfillId: string
) {
  const progress = await prisma.backfillProgress.findUnique({
    where: { id: backfillId },
  });

  if (!progress) {
    throw new Error('Backfill not found');
  }

  // 데이터 롤백
  if (progress.status === 'completed') {
    // 수정된 데이터 되돌리기
    const users = await prisma.user.findMany({
      where: {
        username: { not: null },
      },
    });

    for (const user of users) {
      await prisma.user.update({
        where: { id: user.id },
        data: { username: null },
      });
    }
  }

  // 진행 상황 삭제
  await prisma.backfillProgress.delete({
    where: { id: backfillId },
  });
}
```

## 최소 예제

```typescript
// 간단한 배치 처리
async function simpleBackfill(prisma: PrismaClient) {
  const users = await prisma.user.findMany();

  for (const user of users) {
    await prisma.user.update({
      where: { id: user.id },
      data: { processed: true },
    });
  }
}
```

## 안티패턴

### 1. 메모리에 모든 데이터 로드

```typescript
// ❌ 나쁜 예제
const allUsers = await prisma.user.findMany(); // 메모리 부족!
for (const user of allUsers) {
  await updateUser(user);
}

// ✅ 좋은 예제
const BATCH_SIZE = 1000;
let offset = 0;
while (true) {
  const users = await prisma.user.findMany({
    skip: offset,
    take: BATCH_SIZE,
  });
  // 배치 처리
  offset += BATCH_SIZE;
}
```

## 연결된 오류

- **E-MG-03**: 백필 중 메모리 부족
- **E-MG-04**: 배치 처리 실패로 인한 데이터 손실

## 연결된 플로우

- **F-MG-03**: 필드 추가 및 데이터 백필

## 참고 자료

- Batch Processing Patterns: https://databases.zeef.com/
- Prisma Pagination: https://www.prisma.io/docs/orm/prisma-client/queries/pagination
