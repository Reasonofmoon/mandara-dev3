---
id: F-11
title: 커넥션 풀 고갈 해결
pattern_id: P-11
error_ids: [E-31, E-32, E-33]
tech_scope: 데이터베이스 연결, 커넥션 풀, Prisma
---

# 커넥션 풀 고갈 해결

데이터베이스 커넥션 풀이 고갈되어 새로운 연결을 받을 수 없는 문제를 해결합니다.

## 1단계: 증상 고정

오류 메시지:
- "ConnectionError: connect ECONNREFUSED"
- "KnexTimeoutError: Knex: Timeout acquiring a connection. The pool is probably full"
- "FATAL: too many connections"
- "could not connect to server"
- 비정상적으로 느린 데이터베이스 응답

## 2단계: 재현

```javascript
// ❌ 커넥션 누수 예제
// Prisma 클라이언트를 여러 번 인스턴스화
for (let i = 0; i < 100; i++) {
  const prisma = new PrismaClient();
  // 연결하지만 해제하지 않음 → 풀 고갈
}

// ❌ 연결 미해제
const connection = await db.getConnection();
// disconnect() 호출 안 함

// ❌ 오류 시 연결 미해제
try {
  const data = await query();
} catch (error) {
  // 오류 발생 시에도 연결 반환해야 함
}
```

## 3단계: 범위 축소

커넥션 풀 문제의 유형:

1. **커넥션 누수**: 사용 후 반환하지 않음
2. **과다 생성**: 풀 크기보다 많은 요청
3. **타임아웃 짧음**: 연결 타임아웃 설정이 너무 짧음
4. **데드락**: 연결이 블로킹됨
5. **재연결 실패**: 연결 끊김 후 재연결 실패

## 4단계: 증거 수집

```sql
-- PostgreSQL: 현재 연결 수 확인
SELECT count(*) FROM pg_stat_activity;

-- 상세 정보
SELECT usename, application_name, state, query_start FROM pg_stat_activity;

-- 유휴 연결 찾기
SELECT * FROM pg_stat_activity WHERE state = 'idle';

-- MySQL: 현재 연결 수
SHOW PROCESSLIST;

-- 최대 연결 수
SHOW VARIABLES LIKE 'max_connections';
```

```javascript
// Prisma에서 커넥션 풀 상태 확인
const prisma = new PrismaClient({
  log: ['query', 'warn', 'error']
});

// 메트릭 수집
setInterval(async () => {
  const result = await prisma.$queryRaw`
    SELECT count(*) FROM pg_stat_activity
  `;
  console.log('Active connections:', result);
}, 10000);
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 연결 미해제 | 매우높음 | 중간 |
| 풀 크기 너무 작음 | 높음 | 낮음 |
| 동시 요청 많음 | 높음 | 중간 |
| 쿼리 타임아웃 | 중간 | 낮음 |
| 데드락 | 중간 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: Prisma 클라이언트 싱글톤

```javascript
// ❌ 잘못된 사용: 매번 새 인스턴스 생성
app.get('/api/users', async (req, res) => {
  const prisma = new PrismaClient(); // 매번 새 인스턴스!
  const users = await prisma.user.findMany();
  await prisma.$disconnect();
  res.json(users);
});

// ✅ 올바른 사용: 싱글톤 인스턴스
// lib/prisma.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log: process.env.NODE_ENV === 'development'
      ? ['query', 'error', 'warn']
      : ['error']
  });

if (process.env.NODE_ENV !== 'production')
  globalForPrisma.prisma = prisma;

// app.ts
import { prisma } from './lib/prisma';

app.get('/api/users', async (req, res) => {
  const users = await prisma.user.findMany();
  res.json(users);
});

// 애플리케이션 종료 시 정리
process.on('SIGINT', async () => {
  await prisma.$disconnect();
  process.exit(0);
});
```

### 수정안 2: 커넥션 풀 크기 조정

```javascript
// .env
DATABASE_URL="postgresql://user:pass@localhost:5432/db?schema=public"

// 풀 크기 설정 (기본: 2, 최대: 10)
DATABASE_URL="postgresql://user:pass@localhost:5432/db?schema=public&connection_limit=5&pool_timeout=5"
```

```javascript
// 프로그래밍으로 설정
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL + '?connection_limit=5'
    }
  }
});
```

### 수정안 3: 연결 타임아웃 및 재시도

```javascript
// PgBouncer 또는 데이터베이스 풀러 사용 (권장)
// pgbouncer.ini
[databases]
mydb = host=localhost port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 3
```

### 수정안 4: 오류 처리 및 재시도 로직

```javascript
// retry 라이브러리 사용
import pRetry from 'p-retry';

async function queryWithRetry() {
  return pRetry(
    async () => {
      return await prisma.user.findMany();
    },
    {
      retries: 3,
      minTimeout: 100,
      maxTimeout: 1000,
      onFailedAttempt: error => {
        console.warn(
          `Attempt ${error.attemptNumber} failed. ` +
          `${error.retriesLeft} retries left. ` +
          `Error: ${error.message}`
        );
      }
    }
  );
}
```

### 수정안 5: 요청 큐 및 속도 제한

```javascript
// 동시 요청 수 제한
import PQueue from 'p-queue';

const queue = new PQueue({
  concurrency: 5, // 동시에 5개 요청만 처리
  interval: 1000,
  intervalCap: 20 // 초당 최대 20개 요청
});

app.get('/api/users', async (req, res) => {
  try {
    const users = await queue.add(() =>
      prisma.user.findMany()
    );
    res.json(users);
  } catch (error) {
    res.status(503).json({ error: 'Service unavailable' });
  }
});
```

### 수정안 6: 커넥션 모니터링

```javascript
// 주기적으로 커넥션 상태 확인
async function monitorConnections() {
  setInterval(async () => {
    try {
      const result = await prisma.$queryRaw`
        SELECT count(*) as active_connections FROM pg_stat_activity
      `;

      const count = result[0].active_connections;
      const limit = 100; // 최대 커넥션

      if (count > limit * 0.8) {
        console.warn(`Connection pool near capacity: ${count}/${limit}`);
        // 알럿 발송
        sendAlert({
          type: 'CONNECTION_POOL_NEAR_CAPACITY',
          current: count,
          limit: limit
        });
      }
    } catch (error) {
      console.error('Failed to monitor connections:', error);
    }
  }, 30000); // 30초마다 확인
}

monitorConnections();
```

### 수정안 7: 유휴 연결 정리

```javascript
// 유휴 연결 강제 종료 (PostgreSQL)
// pgbouncer 설정
[pgbouncer]
server_lifetime = 3600
server_idle_timeout = 600 # 10분 유휴 후 정리
idle_in_transaction_session_timeout = 300 # 5분 유휴 트랜잭션 정리
```

## 7단계: 검증

```javascript
describe('Connection Pool', () => {
  it('should reuse connections', async () => {
    const results = await Promise.all([
      prisma.user.findFirst(),
      prisma.user.findFirst(),
      prisma.user.findFirst()
    ]);

    // 3개 요청이지만 1-2개 커넥션만 사용됨
    expect(results).toHaveLength(3);
  });

  it('should handle concurrent requests', async () => {
    const requests = Array(100).fill(null).map(() =>
      prisma.user.findMany({ take: 1 })
    );

    const results = await Promise.all(requests);

    expect(results).toHaveLength(100);
  });

  it('should disconnect properly on process termination', async () => {
    await prisma.$disconnect();

    // 재연결 확인
    const user = await prisma.user.findFirst();
    expect(user).toBeDefined();
  });
});
```

## 8단계: 재발 방지

1. **체크리스트**
   - [ ] PrismaClient는 싱글톤 인스턴스인가?
   - [ ] 모든 연결이 올바르게 해제되는가?
   - [ ] 커넥션 풀 크기가 적절한가?
   - [ ] 비정상 종료 시 정리 코드 있는가?

2. **모니터링**

```javascript
// Prometheus 메트릭으로 수집
import prometheus from 'prom-client';

const activeConnections = new prometheus.Gauge({
  name: 'database_active_connections',
  help: 'Number of active database connections'
});

setInterval(async () => {
  const result = await prisma.$queryRaw`
    SELECT count(*) FROM pg_stat_activity
  `;
  activeConnections.set(result[0].count);
}, 10000);
```

## 연결된 프롬프트 블록

- **PB-CL-12-connection-pool**: 커넥션 풀 개념
- **PB-RP-11-pool-stress**: 풀 스트레스 테스트
- **PB-DG-12-connection-trace**: 연결 추적
- **PB-PA-12-pool-config**: 풀 설정 최적화
- **PB-VF-11-pool-monitor**: 풀 모니터링
