---
id: F-12
title: 락/데드락 해결
pattern_id: P-12
error_ids: [E-34, E-35, E-36]
tech_scope: 트랜잭션, 동시성, 데이터베이스 락
---

# 락/데드락 해결

데이터베이스 락으로 인한 성능 저하와 데드락 문제를 해결합니다.

## 1단계: 증상 고정

- "Deadlock detected" 오류
- "Lock timeout exceeded"
- 특정 쿼리가 무한 대기
- "waiting for ..." 상태
- 임의로 트랜잭션 실패

## 2단계: 재현

```javascript
// ❌ 데드락 시나리오
// Transaction 1: UPDATE user SET balance = 100 WHERE id = 1; UPDATE user SET balance = 200 WHERE id = 2;
// Transaction 2: UPDATE user SET balance = 300 WHERE id = 2; UPDATE user SET balance = 400 WHERE id = 1;
// → 두 트랜잭션이 서로 다른 행에 락을 잡고 대기 = 데드락

await prisma.$transaction(async (tx) => {
  await tx.user.update({
    where: { id: 1 },
    data: { balance: 100 }
  });

  // 다른 트랜잭션이 동시에 같은 행 수정 시도
  // → 락 대기 → 데드락 가능성
  await tx.user.update({
    where: { id: 2 },
    data: { balance: 200 }
  });
});
```

## 3단계: 범위 축소

락/데드락 유형:

1. **쓰기 락(Write Lock)**: UPDATE/DELETE 시 발생
2. **읽기 락(Read Lock)**: FOR UPDATE로 명시적 락
3. **행 수준 락**: 특정 행 락
4. **테이블 수준 락**: 전체 테이블 락
5. **시퀀셜 락**: 순서 의존성으로 인한 락

## 4단계: 증거 수집

```sql
-- PostgreSQL: 현재 락 상태 확인
SELECT pid, usename, query, wait_event_type, wait_event
FROM pg_stat_activity WHERE wait_event_type IS NOT NULL;

-- 데드락 로그 확인
SELECT * FROM pg_stat_statements WHERE query LIKE '%deadlock%';

-- 블로킹 쿼리 찾기
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 트랜잭션 순서 불일치 | 매우높음 | 중간 |
| 긴 트랜잭션 | 높음 | 중간 |
| 암시적 락 | 높음 | 낮음 |
| 부적절한 격리 수준 | 중간 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: 트랜잭션 순서 정렬

```javascript
// ❌ 데드락 위험
async function transfer(fromId, toId, amount) {
  await prisma.$transaction(async (tx) => {
    if (fromId < toId) {
      // 트랜잭션 1
      await tx.account.update({ where: { id: fromId }, data: { balance: { decrement: amount } } });
      await tx.account.update({ where: { id: toId }, data: { balance: { increment: amount } } });
    } else {
      // 트랜잭션 2 (순서 반대)
      await tx.account.update({ where: { id: toId }, data: { balance: { increment: amount } } });
      await tx.account.update({ where: { id: fromId }, data: { balance: { decrement: amount } } });
    }
  });
}

// ✅ 데드락 방지: 항상 작은 ID부터 접근
async function transfer(fromId, toId, amount) {
  const [id1, id2] = fromId < toId ? [fromId, toId] : [toId, fromId];

  await prisma.$transaction(async (tx) => {
    const account1 = await tx.account.findUnique({ where: { id: id1 } });
    const account2 = await tx.account.findUnique({ where: { id: id2 } });

    if (id1 === fromId) {
      // fromId가 작은 ID
      await tx.account.update({ where: { id: fromId }, data: { balance: { decrement: amount } } });
      await tx.account.update({ where: { id: toId }, data: { balance: { increment: amount } } });
    } else {
      // toId가 작은 ID
      await tx.account.update({ where: { id: toId }, data: { balance: { increment: amount } } });
      await tx.account.update({ where: { id: fromId }, data: { balance: { decrement: amount } } });
    }
  });
}
```

### 수정안 2: 격리 수준 조정

```javascript
// 트랜잭션 격리 수준 설정
await prisma.$transaction(
  async (tx) => {
    // 쿼리 실행
    return await tx.user.findMany();
  },
  {
    isolationLevel: 'ReadCommitted' // 기본값
    // 옵션: Serializable, RepeatableRead, ReadCommitted, ReadUncommitted
  }
);
```

```sql
-- PostgreSQL: 세션 격리 수준 설정
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED; -- 기본값
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED; -- PostgreSQL에서는 READ COMMITTED와 동일
```

### 수정안 3: FOR UPDATE로 명시적 락

```javascript
// ✅ 명시적 락으로 순서 보장
async function transfer(fromId, toId, amount) {
  await prisma.$transaction(async (tx) => {
    // 두 계정을 명시적으로 락 (작은 ID부터)
    const [id1, id2] = fromId < toId ? [fromId, toId] : [toId, fromId];

    const account1 = await tx.$queryRaw`
      SELECT * FROM accounts WHERE id = ${id1} FOR UPDATE
    `;

    const account2 = await tx.$queryRaw`
      SELECT * FROM accounts WHERE id = ${id2} FOR UPDATE
    `;

    // 잔액 확인 및 업데이트
    if (account1.balance >= amount) {
      await tx.account.update({
        where: { id: fromId },
        data: { balance: { decrement: amount } }
      });

      await tx.account.update({
        where: { id: toId },
        data: { balance: { increment: amount } }
      });
    } else {
      throw new Error('Insufficient balance');
    }
  });
}
```

### 수정안 4: 타임아웃 설정

```javascript
// 트랜잭션 타임아웃
await prisma.$transaction(
  async (tx) => {
    return await tx.user.findMany();
  },
  {
    timeout: 5000 // 5초 타임아웃
  }
);

// 또는 쿼리 수준 타임아웃
await prisma.$queryRaw`
  SET statement_timeout = 5000;
  SELECT * FROM users;
`;
```

### 수정안 5: 재시도 로직

```javascript
import pRetry from 'p-retry';

async function executeWithRetry(transaction) {
  return pRetry(
    () => transaction(),
    {
      retries: 3,
      minTimeout: 100,
      maxTimeout: 1000,
      onFailedAttempt: error => {
        if (error.message.includes('Deadlock')) {
          console.warn('Deadlock detected, retrying...');
        }
      }
    }
  );
}

// 사용
await executeWithRetry(async () => {
  return await prisma.$transaction(async (tx) => {
    // 트랜잭션 로직
  });
});
```

### 수정안 6: 낙관적 락(Optimistic Locking)

```javascript
// Prisma 스키마에 version 필드 추가
model Account {
  id Int @id
  balance Decimal
  version Int @default(0)
}

// 낙관적 락으로 충돌 감지
async function updateBalance(id, newBalance) {
  const account = await prisma.account.findUnique({ where: { id } });

  try {
    const updated = await prisma.account.update({
      where: { id },
      data: {
        balance: newBalance,
        version: { increment: 1 }
      }
    });

    return updated;
  } catch (error) {
    if (error.code === 'P2025') {
      // 충돌 발생: version이 변경됨
      throw new Error('Version mismatch - concurrent update detected');
    }
    throw error;
  }
}
```

## 7단계: 검증

```javascript
// 동시성 테스트
describe('Deadlock Prevention', () => {
  it('should not deadlock on concurrent transfers', async () => {
    const [account1, account2] = [1, 2];
    const amount = 10;

    const results = await Promise.all([
      transfer(account1, account2, amount),
      transfer(account2, account1, amount)
    ]);

    expect(results).toHaveLength(2);
    expect(results[0]).toBeDefined();
    expect(results[1]).toBeDefined();
  });

  it('should handle concurrent updates', async () => {
    const updates = Array(50).fill(null).map((_, i) =>
      prisma.account.update({
        where: { id: 1 },
        data: { balance: { increment: 1 } }
      })
    );

    const results = await Promise.allSettled(updates);

    const successful = results.filter(r => r.status === 'fulfilled');
    expect(successful.length).toBeGreaterThan(0);
  });
});
```

## 8단계: 재발 방지

1. **코드 리뷰 체크리스트**
   - [ ] 여러 행/테이블을 수정하는 트랜잭션인가?
   - [ ] 액세스 순서가 일관적인가?
   - [ ] 트랜잭션 범위가 최소인가?

2. **모니터링**

```javascript
// 데드락 감시
prisma.$on('query', (event) => {
  if (event.query.includes('ROLLBACK') && event.query.includes('deadlock')) {
    console.error('Deadlock occurred:', event.query);
    sendAlert({ type: 'DEADLOCK' });
  }
});
```

## 연결된 프롬프트 블록

- **PB-CL-13-transactions**: 트랜잭션 이해
- **PB-RP-12-concurrency**: 동시성 테스트
- **PB-DG-13-lock-trace**: 락 추적
- **PB-PA-13-transaction-opt**: 트랜잭션 최적화
- **PB-VF-12-deadlock-test**: 데드락 테스트
