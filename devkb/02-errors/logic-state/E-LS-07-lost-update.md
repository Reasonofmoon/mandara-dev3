---
id: E-LS-07
title: 유실된 업데이트
error_class: Logic-State
symptoms:
  - 변경사항 손실
  - 마지막 업데이트만 저장
  - 동시 수정 충돌
exact_messages:
  - "Update lost due to concurrent modification"
  - "Conflict: resource has been modified"
  - "Optimistic lock violation"
tech_tags:
  - Concurrency
  - Database
  - State Management
linked_patterns: []
linked_flows: []
---

# 유실된 업데이트

## 증상
여러 사용자가 동시에 같은 데이터를 수정할 때 이전 수정사항이 손실됩니다.

## 빠른 해결법

### 1. Optimistic Lock (버전 번호)
```typescript
// schema.prisma
model Post {
  id    Int     @id
  title String
  version Int   @default(0)
}

// 업데이트
const updated = await prisma.post.updateMany({
  where: { id: 1, version: currentVersion },
  data: { title: 'New Title', version: { increment: 1 } }
});

if (updated.count === 0) {
  throw new Error('Conflict: post was modified');
}
```

### 2. Pessimistic Lock (FOR UPDATE)
```typescript
await prisma.$transaction(async (tx) => {
  const post = await tx.$queryRaw`
    SELECT * FROM "Post" WHERE id = 1 FOR UPDATE
  `;

  await tx.post.update({
    where: { id: 1 },
    data: { title: 'Updated' }
  });
});
```

### 3. Last-Write-Wins (타임스탬프)
```typescript
const updated = await prisma.post.updateMany({
  where: { id: 1, updatedAt: lastKnownTime },
  data: { title: 'New', updatedAt: new Date() }
});
```

## 연결된 패턴
- E-LS-06-transaction-boundary
- E-LS-05-race-condition

## 재발 방지
1. 동시성 제어 메커니즘 구현
2. 충돌 감지 및 해결 로직
3. 버전 관리
