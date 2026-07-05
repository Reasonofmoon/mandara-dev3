---
id: P-QP-01
title: 키셋 페이지네이션 패턴
stage: Implement
layer: Data
pattern_family: Persistence
tech_tags: [Cursor-based Pagination, 성능, 대규모 데이터셋]
linked_errors: [E-QP-01, E-QP-02]
linked_flows: [F-QP-01]
linked_prompts: [PR-QP-01]
---

# 키셋 페이지네이션 패턴

## 목표
OFFSET 대신 WHERE 조건을 사용하여 대규모 데이터셋에서 효율적인 페이지네이션을 구현합니다.

## 언제 사용하는가
- 대규모 데이터셋의 목록 조회
- 무한 스크롤 구현
- 데이터가 자주 변하는 경우
- 성능이 중요한 경우

## 언제 사용하지 않는가
- 소규모 데이터셋 (OFFSET으로도 충분)
- "5번째 페이지로 이동" 같은 임의 접근이 필요한 경우

## 핵심 구조

### 서버 구현

```typescript
// posts/posts.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';

interface KeysetPaginationParams {
  limit: number;
  cursor?: string; // 마지막 항목의 ID 또는 정렬 키
  sortBy?: 'createdAt' | 'updatedAt' | 'popularity';
  order?: 'asc' | 'desc';
}

interface PaginatedResult<T> {
  items: T[];
  nextCursor?: string;
  hasMore: boolean;
  limit: number;
}

@Injectable()
export class PostsService {
  constructor(private prisma: PrismaService) {}

  async getPosts(
    params: KeysetPaginationParams,
  ): Promise<PaginatedResult<Post>> {
    const {
      limit = 20,
      cursor,
      sortBy = 'createdAt',
      order = 'desc',
    } = params;

    // limit + 1을 조회하여 hasMore 판단
    const take = limit + 1;

    // 커서 기반 조건 구성
    let where: any = {};
    let orderBy: any = { [sortBy]: order };

    if (cursor) {
      // 커서(마지막 항목의 정렬 키)를 기준으로 조회
      const lastPost = await this.prisma.post.findUnique({
        where: { id: cursor },
        select: { [sortBy]: true },
      });

      if (!lastPost) {
        throw new Error('Invalid cursor');
      }

      // 정렬 방향에 따른 조건
      const cursorValue = lastPost[sortBy];
      if (order === 'desc') {
        where = {
          OR: [
            {
              [sortBy]: {
                lt: cursorValue, // 마지막 항목보다 작음
              },
            },
            {
              AND: [
                { [sortBy]: cursorValue },
                { id: { not: cursor } },
              ],
            },
          ],
        };
      } else {
        where = {
          OR: [
            {
              [sortBy]: {
                gt: cursorValue, // 마지막 항목보다 큼
              },
            },
            {
              AND: [
                { [sortBy]: cursorValue },
                { id: { not: cursor } },
              ],
            },
          ],
        };
      }
    }

    const posts = await this.prisma.post.findMany({
      where,
      orderBy,
      take,
      select: {
        id: true,
        title: true,
        content: true,
        [sortBy]: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    // hasMore 판단 (실제 조회된 항목이 limit보다 많으면 다음 페이지 있음)
    const hasMore = posts.length > limit;
    const items = posts.slice(0, limit);

    // 다음 커서 계산
    const nextCursor = hasMore ? items[items.length - 1]?.id : undefined;

    return {
      items,
      nextCursor,
      hasMore,
      limit,
    };
  }
}

// posts/posts.controller.ts
@Controller('api/posts')
export class PostsController {
  constructor(private postsService: PostsService) {}

  @Get()
  async getPosts(
    @Query('cursor') cursor?: string,
    @Query('limit') limit?: string,
    @Query('sortBy') sortBy?: 'createdAt' | 'updatedAt' | 'popularity',
    @Query('order') order?: 'asc' | 'desc',
  ) {
    return this.postsService.getPosts({
      cursor,
      limit: Math.min(parseInt(limit || '20'), 100), // 최대 100
      sortBy,
      order,
    });
  }
}
```

## 최소 예제

```typescript
// 첫 페이지
GET /api/posts?limit=20

// 다음 페이지 (cursor는 이전 응답의 nextCursor)
GET /api/posts?limit=20&cursor=post-123
```

### 응답 형식

```json
{
  "items": [
    {
      "id": "post-123",
      "title": "First post",
      "createdAt": "2024-01-01T00:00:00Z"
    },
    {
      "id": "post-122",
      "title": "Second post",
      "createdAt": "2024-01-02T00:00:00Z"
    }
  ],
  "nextCursor": "post-122",
  "hasMore": true,
  "limit": 20
}
```

## 고급 사용법 - 복합 정렬

```typescript
async getPosts(
  params: KeysetPaginationParams,
): Promise<PaginatedResult<Post>> {
  const { limit = 20, cursor } = params;

  // 복합 정렬 (createdAt desc, id asc)
  let where: any = {};
  const orderBy = [
    { createdAt: 'desc' as const },
    { id: 'asc' as const },
  ];

  if (cursor) {
    const [createdAtValue, idValue] = cursor.split(':');
    const lastCreatedAt = new Date(createdAtValue);

    where = {
      OR: [
        { createdAt: { lt: lastCreatedAt } },
        {
          AND: [
            { createdAt: lastCreatedAt },
            { id: { gt: idValue } },
          ],
        },
      ],
    };
  }

  const posts = await this.prisma.post.findMany({
    where,
    orderBy,
    take: limit + 1,
  });

  const hasMore = posts.length > limit;
  const items = posts.slice(0, limit);

  const nextCursor = hasMore
    ? `${items[items.length - 1].createdAt.toISOString()}:${items[items.length - 1].id}`
    : undefined;

  return { items, nextCursor, hasMore, limit };
}
```

## 클라이언트 React Hook

```typescript
// hooks/useKeysetPagination.ts
import { useState, useCallback } from 'react';

export function useKeysetPagination<T>(
  fetchFn: (cursor?: string, limit?: number) => Promise<PaginationResult<T>>,
  limit: number = 20,
) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [cursor, setCursor] = useState<string | undefined>();

  const loadMore = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFn(cursor, limit);
      setItems(prev =>
        cursor ? [...prev, ...result.items] : result.items
      );
      setCursor(result.nextCursor);
      setHasMore(result.hasMore);
    } finally {
      setLoading(false);
    }
  }, [cursor, limit, fetchFn]);

  return {
    items,
    loading,
    hasMore,
    loadMore,
  };
}

// 사용
export function InfinitePostsList() {
  const { items, loading, hasMore, loadMore } = useKeysetPagination(
    async (cursor, limit) => {
      const response = await fetch(
        `/api/posts?${cursor ? `cursor=${cursor}&` : ''}limit=${limit}`
      );
      return response.json();
    }
  );

  return (
    <div>
      {items.map(post => (
        <article key={post.id}>{post.title}</article>
      ))}

      {hasMore && (
        <button onClick={loadMore} disabled={loading}>
          {loading ? '로딩...' : '더 불러오기'}
        </button>
      )}
    </div>
  );
}
```

## 인덱스 최적화

```prisma
// schema.prisma
model Post {
  id        String   @id @default(cuid())
  title     String
  content   String
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  // 정렬에 사용되는 필드의 인덱스
  @@index([createdAt, id])
  @@index([updatedAt])
}
```

## 안티패턴

### 1. OFFSET 기반 페이지네이션

```typescript
// ❌ 나쁜 예제 (큰 OFFSET은 성능 문제)
async getPosts(page: number, limit: number) {
  return this.prisma.post.findMany({
    skip: (page - 1) * limit,
    take: limit,
  });
  // page 1000이면 999000개 행을 스킵해야 함!
}

// ✅ 좋은 예제
async getPosts(cursor?: string, limit?: number) {
  // WHERE 조건으로 효율적 조회
}
```

### 2. 인덱스 없는 정렬

```typescript
// ❌ 나쁜 예제
model Post {
  createdAt DateTime @default(now())
  // 인덱스 없음 - 풀 테이블 스캔!
}

// ✅ 좋은 예제
model Post {
  createdAt DateTime @default(now())
  @@index([createdAt, id]) // 정렬과 커서용 복합 인덱스
}
```

## 연결된 오류

- **E-QP-01**: 커서 기반 페이지네이션 오류
- **E-QP-02**: 데이터 누락 또는 중복

## 연결된 플로우

- **F-QP-01**: 무한 스크롤 구현

## 참고 자료

- Keyset Pagination: https://use-the-index-luke.com/no-offset
- Cursor-based Pagination: https://www.apollographql.com/docs/apollo-server/features/pagination/
