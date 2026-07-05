---
id: F-10
title: 느린 쿼리 진단 및 해결
pattern_id: P-10
error_ids: [E-28, E-29, E-30]
tech_scope: 데이터베이스 성능, EXPLAIN, 인덱스
---

# 느린 쿼리 진단 및 해결

데이터베이스 쿼리 성능을 진단하고 최적화합니다.

## 1단계: 증상 고정

증상:
- "Database query timeout" 오류
- 쿼리 실행 시간이 5초 이상
- 데이터베이스 CPU 사용률 높음
- 동시 접속 사용자 증가 시 응답 느림
- 특정 페이지나 기능이 느림

## 2단계: 재현

```sql
-- 느린 쿼리 확인
SHOW VARIABLES LIKE 'slow_query_log';

-- slow query log 활성화
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- 또는 직접 쿼리 실행 시간 측정
\timing ON -- psql
EXPLAIN ANALYZE SELECT * FROM posts WHERE author_id = 1;
```

## 3단계: 범위 축소

느린 쿼리의 원인:

1. **인덱스 부재**: WHERE 절의 컬럼에 인덱스 없음
2. **부적절한 조인**: 큰 테이블 끼리 조인
3. **전체 테이블 스캔**: 필터링 없는 조회
4. **서브쿼리 오버헤드**: 비효율적인 서브쿼리
5. **통계 오래됨**: 쿼리 계획 최적화 안 됨

## 4단계: 증거 수집

```sql
-- PostgreSQL에서 쿼리 실행 계획 분석
EXPLAIN ANALYZE SELECT * FROM posts WHERE author_id = 1;

-- 예상되는 출력:
-- Seq Scan on posts  (cost=0.00..35.50 rows=1 width=100)
-- Filter: (author_id = 1)
-- Planning Time: 0.089 ms
-- Execution Time: 0.234 ms

-- 만약 Seq Scan이면 인덱스가 필요
```

```sql
-- MySQL에서 쿼리 실행 계획
EXPLAIN SELECT * FROM posts WHERE author_id = 1;

-- ANALYZE로 더 자세한 정보
EXPLAIN FORMAT=JSON SELECT * FROM posts WHERE author_id = 1;
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 해결 난도 |
|------|------|---------|
| 인덱스 부재 | 매우높음 | 낮음 |
| 부적절한 WHERE 절 | 높음 | 중간 |
| N+1 쿼리 | 높음 | 중간 |
| 데이터 양 증가 | 중간 | 낮음 |
| 통계 오래됨 | 낮음 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 인덱스 추가 (가장 일반적)

```sql
-- 단일 컬럼 인덱스
CREATE INDEX idx_posts_author_id ON posts(author_id);

-- 복합 인덱스 (자주 함께 검색되는 컬럼)
CREATE INDEX idx_posts_author_published ON posts(author_id, published);

-- 정렬 포함 인덱스
CREATE INDEX idx_posts_created_desc ON posts(created_at DESC);

-- 부분 인덱스 (특정 조건만)
CREATE INDEX idx_posts_published ON posts(id)
WHERE published = true;

-- 인덱스 확인
SELECT * FROM pg_indexes WHERE tablename = 'posts';
```

```prisma
// Prisma 스키마에 인덱스 정의
model Post {
  id Int @id @default(autoincrement())
  title String
  content String?
  authorId Int
  published Boolean @default(false)
  createdAt DateTime @default(now())

  author User @relation(fields: [authorId], references: [id])

  // 인덱스 정의
  @@index([authorId])
  @@index([authorId, published])
  @@index([createdAt(sort: Desc)])
}
```

### 수정안 2: 쿼리 최적화

```sql
-- ❌ 느린 쿼리: 전체 스캔
SELECT * FROM posts WHERE author_id = 1;

-- ✅ 개선: 필요한 컬럼만 선택
SELECT id, title, created_at FROM posts WHERE author_id = 1;

-- ❌ 느린 쿼리: 부적절한 조인
SELECT * FROM posts
WHERE user_id IN (SELECT id FROM users WHERE status = 'active');

-- ✅ 개선: INNER JOIN
SELECT p.* FROM posts p
INNER JOIN users u ON p.user_id = u.id
WHERE u.status = 'active';

-- ❌ 느린 쿼리: OR 조건 많음
SELECT * FROM posts
WHERE author_id = 1 OR author_id = 2 OR author_id = 3;

-- ✅ 개선: IN 절
SELECT * FROM posts WHERE author_id IN (1, 2, 3);
```

### 수정안 3: EXPLAIN 분석 및 개선

```sql
-- 1단계: 쿼리 실행 계획 확인
EXPLAIN ANALYZE
SELECT p.*, u.name FROM posts p
JOIN users u ON p.author_id = u.id
WHERE p.created_at > '2024-01-01';

-- 결과 분석
-- → Seq Scan on posts (느림)
-- → Hash Join on users (비효율적)

-- 2단계: 인덱스 추가
CREATE INDEX idx_posts_created_at ON posts(created_at);

-- 3단계: 다시 실행 계획 확인
EXPLAIN ANALYZE
SELECT p.*, u.name FROM posts p
JOIN users u ON p.author_id = u.id
WHERE p.created_at > '2024-01-01';

-- 결과
-- → Index Scan on posts (빠름)
-- → Nested Loop (효율적)
```

### 수정안 4: 쿼리 캐싱

```javascript
// Prisma에서 쿼리 캐싱
const redis = require('redis').createClient();

async function getPostsByAuthor(authorId, useCache = true) {
  const cacheKey = `posts:author:${authorId}`;

  if (useCache) {
    const cached = await redis.get(cacheKey);
    if (cached) {
      return JSON.parse(cached);
    }
  }

  const posts = await prisma.post.findMany({
    where: { authorId },
    orderBy: { createdAt: 'desc' }
  });

  await redis.setex(cacheKey, 3600, JSON.stringify(posts));

  return posts;
}
```

### 수정안 5: 페이지네이션

```javascript
// ❌ 느린 쿼리: 모든 데이터 로드
const allPosts = await prisma.post.findMany({
  where: { published: true }
});

// ✅ 페이지네이션
async function getPaginatedPosts(page = 1, pageSize = 20) {
  const skip = (page - 1) * pageSize;

  const [posts, total] = await Promise.all([
    prisma.post.findMany({
      where: { published: true },
      orderBy: { createdAt: 'desc' },
      skip,
      take: pageSize
    }),
    prisma.post.count({
      where: { published: true }
    })
  ]);

  return {
    posts,
    pagination: {
      page,
      pageSize,
      total,
      pages: Math.ceil(total / pageSize)
    }
  };
}
```

### 수정안 6: 집계 함수 활용

```sql
-- ❌ 느린 쿼리: 클라이언트에서 집계
SELECT * FROM comments WHERE post_id = 1;
-- 클라이언트에서 COUNT, SUM, AVG 계산

-- ✅ 데이터베이스에서 집계
SELECT
  COUNT(*) as total_comments,
  AVG(rating) as avg_rating,
  MAX(created_at) as latest_comment
FROM comments
WHERE post_id = 1;
```

### 수정안 7: 배치 작업 분산

```javascript
// ❌ 느린: 모든 데이터 한 번에 처리
const allPosts = await prisma.post.findMany();
for (const post of allPosts) {
  await processPost(post);
}

// ✅ 배치: 작은 단위로 처리
async function processBatch(batchSize = 100) {
  let skip = 0;

  while (true) {
    const posts = await prisma.post.findMany({
      skip,
      take: batchSize
    });

    if (posts.length === 0) break;

    await Promise.all(posts.map(post => processPost(post)));

    skip += batchSize;
  }
}
```

## 7단계: 검증

```javascript
// 쿼리 성능 측정
async function measureQueryPerformance() {
  const startTime = Date.now();

  const posts = await prisma.post.findMany({
    where: { published: true },
    take: 20
  });

  const executionTime = Date.now() - startTime;

  console.log(`Query executed in ${executionTime}ms`);
  console.log(`Retrieved ${posts.length} posts`);

  // 목표: < 100ms
  expect(executionTime).toBeLessThan(100);
}
```

## 8단계: 재발 방지

1. **쿼리 모니터링**

```javascript
prisma.$on('query', (e) => {
  if (e.duration > 1000) {
    console.warn(`Slow query (${e.duration}ms): ${e.query}`);

    // 모니터링 서비스로 전송
    sendAlert({
      type: 'SLOW_QUERY',
      duration: e.duration,
      query: e.query
    });
  }
});
```

2. **정기 인덱스 검토**

```sql
-- 사용되지 않는 인덱스 찾기
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename, indexname;
```

3. **통계 업데이트**

```sql
-- PostgreSQL
ANALYZE;

-- MySQL
ANALYZE TABLE posts;
```

## 연결된 프롬프트 블록

- **PB-CL-11-index-design**: 인덱스 설계
- **PB-RP-10-query-profiling**: 쿼리 프로파일링
- **PB-DG-11-execution-plan**: 실행 계획 분석
- **PB-PA-11-query-tuning**: 쿼리 튜닝
- **PB-VF-10-perf-monitoring**: 성능 모니터링
