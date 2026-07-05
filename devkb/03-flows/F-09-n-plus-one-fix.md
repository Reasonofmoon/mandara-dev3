---
id: F-09
title: N+1 쿼리 해결
pattern_id: P-09
error_ids: [E-25, E-26, E-27]
tech_scope: 데이터베이스 최적화, Prisma, SQL
---

# N+1 쿼리 해결

N+1 쿼리 문제로 인한 데이터베이스 성능 저하를 진단하고 해결합니다.

## 1단계: 증상 고정

증상:
- 데이터베이스 쿼리 수가 비정상적으로 많음
- 작은 데이터 조회에도 수백 개의 쿼리 발생
- 페이지 로드 시간이 오래 걸림
- 데이터베이스 CPU 사용률 높음
- 데이터 양이 늘어날수록 성능 급속 악화

## 2단계: 재현

```javascript
// ❌ N+1 쿼리 예제
const users = await prisma.user.findMany();

// 각 user마다 1번씩 쿼리 실행 = N개
for (const user of users) {
  const posts = await prisma.post.findMany({
    where: { authorId: user.id }
  });
  console.log(user.name, posts.length);
}

// 총 쿼리: 1 (users) + N (각 user의 posts) = N+1

// 또는 더 심한 경우
// ❌ 루프 내 루프
const users = await prisma.user.findMany();

for (const user of users) {
  const posts = await prisma.post.findMany({
    where: { authorId: user.id }
  });

  for (const post of posts) {
    const comments = await prisma.comment.findMany({
      where: { postId: post.id }
    });
    // 총 쿼리: 1 + N + (N * M)
  }
}
```

## 3단계: 범위 축소

N+1 문제의 유형:

1. **루프 내 쿼리**: 반복문에서 매번 쿼리 실행
2. **관계 데이터 로딩**: 1:N 또는 M:N 관계에서 개별 조회
3. **중첩 관계**: 여러 수준의 관계 데이터 조회
4. **이터레이터 메서드**: map, forEach 등에서 비동기 쿼리
5. **GraphQL Resolver**: 각 필드마다 개별 쿼리

## 4단계: 증거 수집

```bash
# Prisma 쿼리 로깅 활성화
export DATABASE_URL="postgresql://...?logging=true"

# 또는 코드에서
const prisma = new PrismaClient({
  log: ['query', 'error', 'warn']
});
```

```javascript
// 쿼리 실행 로깅
prisma.$on('query', (e) => {
  console.log('Query:', e.query);
  console.log('Duration:', e.duration, 'ms');
});

// 또는 더 상세하게
const startTime = Date.now();
await queryFunction();
console.log(`Execution time: ${Date.now() - startTime}ms`);
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 루프 내 쿼리 | 매우높음 | 낮음 |
| 관계 미선택 로딩 | 높음 | 중간 |
| include 누락 | 높음 | 낮음 |
| 깊은 중첩 | 중간 | 높음 |
| GraphQL 문제 | 낮음 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: Prisma include (권장)

```javascript
// ❌ N+1 쿼리
const users = await prisma.user.findMany();
for (const user of users) {
  user.posts = await prisma.post.findMany({
    where: { authorId: user.id }
  });
}

// ✅ include로 한 번에 로드
const users = await prisma.user.findMany({
  include: {
    posts: true
  }
});

// 각 user에는 posts 배열이 이미 포함됨
console.log(users[0].posts); // 추가 쿼리 없음

// ✅ 중첩 include
const users = await prisma.user.findMany({
  include: {
    posts: {
      include: {
        comments: true
      }
    }
  }
});

// ✅ 조건부 include
const users = await prisma.user.findMany({
  include: {
    posts: {
      where: { published: true },
      orderBy: { createdAt: 'desc' },
      take: 5
    }
  }
});
```

### 수정안 2: select로 필요한 필드만 로드

```javascript
// ✅ 필요한 필드만 선택
const users = await prisma.user.findMany({
  select: {
    id: true,
    name: true,
    email: true,
    posts: {
      select: {
        id: true,
        title: true
      }
    }
  }
});

// 또는 exclude 사용
const users = await prisma.user.findMany({
  select: {
    id: true,
    name: true,
    email: true,
    password: false // 제외
  }
});
```

### 수정안 3: 배치 로딩

```javascript
// ❌ 배치 로딩 없음
async function getUsersWithPostCounts() {
  const users = await prisma.user.findMany();

  for (const user of users) {
    user.postCount = await prisma.post.count({
      where: { authorId: user.id }
    });
  }

  return users;
}

// ✅ 배치 로딩 (한 번에)
async function getUsersWithPostCounts() {
  const users = await prisma.user.findMany();

  const postCounts = await prisma.post.groupBy({
    by: ['authorId'],
    _count: {
      id: true
    }
  });

  const countMap = Object.fromEntries(
    postCounts.map(c => [c.authorId, c._count.id])
  );

  return users.map(user => ({
    ...user,
    postCount: countMap[user.id] || 0
  }));
}
```

### 수정안 4: raw SQL 쿼리

```javascript
// 매우 복잡한 조회는 SQL이 더 효율적
const result = await prisma.$queryRaw`
  SELECT
    u.id,
    u.name,
    COUNT(p.id) as post_count,
    JSON_AGG(JSON_BUILD_OBJECT(
      'id', p.id,
      'title', p.title
    )) as posts
  FROM users u
  LEFT JOIN posts p ON p.author_id = u.id
  GROUP BY u.id
`;

// 또는 parameterized query
const result = await prisma.$queryRaw`
  SELECT u.*, COUNT(p.id) as post_count
  FROM users u
  LEFT JOIN posts p ON p.author_id = u.id
  WHERE u.id = ${userId}
  GROUP BY u.id
`;
```

### 수정안 5: DataLoader (GraphQL)

```javascript
// DataLoader로 배치 처리
const DataLoader = require('dataloader');

const postLoader = new DataLoader(async (userIds) => {
  const posts = await prisma.post.findMany({
    where: {
      authorId: { in: userIds }
    }
  });

  // userIds 순서대로 결과 반환
  return userIds.map(userId =>
    posts.filter(p => p.authorId === userId)
  );
});

// GraphQL Resolver에서 사용
const User = {
  posts(user, args, context) {
    return postLoader.load(user.id); // 배치 처리됨
  }
};

// 클라이언트 요청 내에서 여러 번 호출해도 한 번의 쿼리로 처리
```

### 수정안 6: Redis 캐싱

```javascript
const redis = require('redis').createClient();

async function getUsersWithPosts(userId) {
  // 캐시 확인
  const cached = await redis.get(`user:${userId}:posts`);
  if (cached) {
    return JSON.parse(cached);
  }

  // 데이터베이스에서 로드
  const user = await prisma.user.findUnique({
    where: { id: userId },
    include: { posts: true }
  });

  // 캐시 저장 (1시간)
  await redis.setex(
    `user:${userId}:posts`,
    3600,
    JSON.stringify(user)
  );

  return user;
}
```

## 7단계: 검증

```javascript
describe('N+1 Query Prevention', () => {
  it('should load users with posts in minimum queries', async () => {
    let queryCount = 0;

    prisma.$on('query', () => {
      queryCount++;
    });

    // 10명의 사용자와 그들의 게시글 조회
    const users = await prisma.user.findMany({
      take: 10,
      include: { posts: true }
    });

    // 예상: 1개 쿼리 (또는 매우 적은 수)
    expect(queryCount).toBeLessThan(5);
    expect(users).toHaveLength(10);
    expect(users[0].posts).toBeDefined();
  });

  it('should not query in loop', async () => {
    // ❌ 안 좋은 패턴
    const users = await prisma.user.findMany();
    for (const user of users) {
      const posts = await prisma.post.findMany({
        where: { authorId: user.id }
      });
      // N+1 쿼리 발생
    }

    // ✅ 좋은 패턴
    const usersWithPosts = await prisma.user.findMany({
      include: { posts: true }
    });
  });
});
```

## 8단계: 재발 방지

1. **쿼리 로깅**

```javascript
// development에서 항상 로깅
const prisma = new PrismaClient({
  log: process.env.NODE_ENV === 'development'
    ? ['query', 'error', 'warn']
    : ['error']
});
```

2. **성능 모니터링**

```javascript
import * as Sentry from "@sentry/node";

prisma.$on('query', (e) => {
  if (e.duration > 1000) {
    Sentry.captureMessage(
      `Slow query: ${e.query}`,
      'warning'
    );
  }
});
```

3. **코드 리뷰 체크리스트**
   - [ ] 루프에서 쿼리 실행하지 않는가?
   - [ ] include/select 사용하는가?
   - [ ] 필요한 필드만 로드하는가?
   - [ ] 중복 쿼리는 없는가?

## 연결된 프롬프트 블록

- **PB-CL-10-query-optimization**: 쿼리 최적화
- **PB-RP-09-query-profiling**: 쿼리 프로파일링
- **PB-DG-10-slow-queries**: 느린 쿼리 진단
- **PB-PA-10-query-batching**: 쿼리 배치 처리
- **PB-VF-09-performance-test**: 성능 테스트
