---
id: P-QP-04
title: 커넥션 풀 튜닝 패턴
stage: Design
layer: Infra
pattern_family: Persistence
tech_tags: [커넥션 풀, PgBouncer, 서버리스, Prisma]
linked_errors: [E-QP-07, E-QP-08]
linked_flows: [F-QP-04]
linked_prompts: [PR-QP-04]
---

# 커넥션 풀 튜닝 패턴

## 목표
데이터베이스 커넥션 풀을 최적화하여 커넥션 고갈을 방지하고 성능을 극대화합니다.

## 언제 사용하는가
- 데이터베이스 연결이 많이 필요한 경우
- 서버리스 환경에서의 콜드 스타트
- 높은 동시성 요구사항
- 데이터베이스 성능 최적화

## 핵심 구조

### Prisma 커넥션 풀 설정

```typescript
// .env
DATABASE_URL="postgresql://user:password@localhost:5432/dbname?schema=public"
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30
```

### PrismaClient 설정

```typescript
// prisma/prisma.service.ts
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor() {
    super({
      datasources: {
        db: {
          url: process.env.DATABASE_URL,
        },
      },
      log: [
        {
          emit: 'event',
          level: 'query',
        },
        {
          emit: 'event',
          level: 'error',
        },
        {
          emit: 'stdout',
          level: 'warn',
        },
      ],
    });
  }

  async onModuleInit() {
    // 커넥션 풀 초기화
    await this.$connect();

    // 쿼리 로깅
    this.$on('query', (e) => {
      console.log('Query: ' + e.query);
      console.log('Params: ' + JSON.stringify(e.params));
      console.log('Duration: ' + e.duration + 'ms');
    });
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
```

## PgBouncer 설정 (프로덕션)

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
mydb = host=db.example.com port=5432 dbname=mydb

[pgbouncer]
# 풀 모드 설정
pool_mode = transaction  # 트랜잭션 단위로 풀 재사용

# 커넥션 풀 크기
max_client_conn = 1000   # 최대 클라이언트 연결 수
default_pool_size = 20   # 데이터베이스당 기본 풀 크기
min_pool_size = 10       # 최소 유지 풀 크기
reserve_pool_size = 5    # 예약 풀
reserve_pool_timeout = 3 # 예약 풀 타임아웃

# 타임아웃
server_lifetime = 3600   # 커넥션 최대 수명
server_idle_timeout = 600 # 유휴 타임아웃
server_connect_timeout = 15 # 연결 시간 제한

# 성능 튜닝
tcp_keepalives = 1
tcp_keepalives_idle = 150
tcp_keepalives_interval = 10
tcp_keepalives_count = 5
```

### 서버리스 환경 (AWS Lambda + RDS Proxy)

```typescript
// AWS Lambda 최적화 설정
export const handler = async (event) => {
  // RDS Proxy는 커넥션 풀을 관리
  const result = await prisma.user.findMany();
  return result;
};

// serverless.yml
service: myapp

provider:
  name: aws
  runtime: nodejs18.x
  environment:
    # RDS Proxy 엔드포인트 사용
    DATABASE_URL: ${ssm:/myapp/db-proxy-url}
    # 서버리스 환경에서 풀 크기 축소
    DATABASE_POOL_SIZE: 1
    DATABASE_CONNECTION_LIMIT: 1
```

## 커넥션 풀 모니터링

```typescript
// monitoring/connection-monitor.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from 'prisma/prisma.service';

@Injectable()
export class ConnectionMonitorService {
  private readonly logger = new Logger(ConnectionMonitorService.name);

  constructor(private prisma: PrismaService) {}

  @Cron('*/30 * * * * *') // 30초마다
  async monitorConnections() {
    try {
      // PostgreSQL에서 활성 커넥션 조회
      const result = await this.prisma.$queryRaw`
        SELECT
          pid,
          usename,
          state,
          query,
          state_change,
          wait_event
        FROM pg_stat_activity
        WHERE datname = current_database()
      `;

      const activeConnections = (result as any[]).filter(
        (row) => row.state === 'active'
      );

      this.logger.log(
        `Active connections: ${activeConnections.length}`
      );

      // 경고: 커넥션 많이 사용 중
      if (activeConnections.length > 15) {
        this.logger.warn(
          `High connection usage: ${activeConnections.length}/20`
        );
      }

      // 롱-러닝 쿼리 감지
      const longRunningQueries = activeConnections.filter(
        (row) =>
          row.state === 'active' &&
          new Date(row.state_change).getTime() <
            Date.now() - 5 * 60 * 1000 // 5분 이상
      );

      if (longRunningQueries.length > 0) {
        this.logger.warn(
          `Long-running queries detected: ${longRunningQueries.length}`
        );
        longRunningQueries.forEach((query) => {
          this.logger.debug(`Query: ${query.query}`);
        });
      }
    } catch (error) {
      this.logger.error('Failed to monitor connections:', error);
    }
  }
}
```

## 최소 예제

```typescript
// 기본 설정
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL,
    },
  },
});

// 사용
await prisma.user.findMany();
```

## 고급 최적화

### 커넥션 재사용 패턴

```typescript
// 싱글톤으로 PrismaClient 관리
let prisma: PrismaClient;

export function getPrismaClient(): PrismaClient {
  if (!prisma) {
    prisma = new PrismaClient();
  }
  return prisma;
}

// API 핸들러
export async function handleRequest(req) {
  const db = getPrismaClient();
  return db.user.findMany();
}
```

### 배치 작업 최적화

```typescript
// 많은 쿼리를 배치로 처리
async function batchInsertUsers(users: User[]) {
  // 대량 삽입 시 한 번의 쿼리 사용
  return prisma.user.createMany({
    data: users,
    skipDuplicates: true,
  });
}

// 트랜잭션으로 여러 작업을 그룹화
async function transferMoney(
  fromUserId: string,
  toUserId: string,
  amount: number
) {
  return prisma.$transaction(async (tx) => {
    const fromUser = await tx.user.update({
      where: { id: fromUserId },
      data: { balance: { decrement: amount } },
    });

    const toUser = await tx.user.update({
      where: { id: toUserId },
      data: { balance: { increment: amount } },
    });

    return { fromUser, toUser };
  });
}
```

## 문제 해결

### 커넥션 풀 부족

```typescript
// 증상: "too many connections" 에러
// 해결책 1: PgBouncer 사용
// 해결책 2: 풀 크기 증가
DATABASE_POOL_SIZE=50

// 해결책 3: 커넥션 수명 조정
server_lifetime = 1800 // 30분

// 해결책 4: 유휴 타임아웃 감소
server_idle_timeout = 300 // 5분
```

### 슬로우 커넥션

```typescript
// 증상: 쿼리가 지연됨
// 해결책 1: 커넥션 타임아웃 확인
server_connect_timeout = 5 // 5초

// 해결책 2: 네트워크 성능 확인
// ping db-server

// 해결책 3: 쿼리 최적화
// EXPLAIN ANALYZE 사용
```

## 안티패턴

### 1. 풀 크기 무한정 증가

```typescript
// ❌ 나쁜 예제
DATABASE_POOL_SIZE=1000 // 너무 많음!

// ✅ 좋은 예제
DATABASE_POOL_SIZE=20 // 적절한 크기
```

### 2. 풀 모드 오류

```ini
# ❌ 나쁜 예제
pool_mode = session # 세션 모드 - 오버헤드 많음

# ✅ 좋은 예제
pool_mode = transaction # 트랜잭션 모드 - 효율적
```

## 연결된 오류

- **E-QP-07**: 커넥션 풀 고갈
- **E-QP-08**: 데이터베이스 연결 거부

## 연결된 플로우

- **F-QP-04**: 데이터베이스 성능 모니터링

## 참고 자료

- PgBouncer: https://www.pgbouncer.org/
- Prisma Connection Management: https://www.prisma.io/docs/orm/overview/databases/connection-management
- AWS RDS Proxy: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html
