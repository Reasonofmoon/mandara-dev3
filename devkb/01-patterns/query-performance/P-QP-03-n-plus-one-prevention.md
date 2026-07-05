---
id: P-QP-03
title: N+1 문제 방지 패턴
stage: Implement
layer: Data
pattern_family: Persistence
tech_tags: [N+1, include, DataLoader, eager loading]
linked_errors: [E-QP-05, E-QP-06]
linked_flows: [F-QP-03]
linked_prompts: [PR-QP-03]
---

# N+1 문제 방지 패턴

## 목표
관계형 데이터를 효율적으로 로드하여 불필요한 데이터베이스 쿼리를 줄입니다.

## 언제 사용하는가
- 관계 있는 데이터를 함께 조회할 때
- 루프에서 관계 데이터를 반복 조회할 때
- 성능이 중요한 리스트 페이지

## 핵심 구조 - Prisma include

```typescript
// ❌ 나쁜 예제: N+1 문제
async getPostsWithAuthor() {
  const posts = await prisma.post.findMany(); // 쿼리 1: 10개 포스트

  const postsWithAuthor = await Promise.all(
    posts.map(post =>
      prisma.user.findUnique({
        where: { id: post.authorId }, // 쿼리 11: 각 포스트마다 작가 조회!
      })
    )
  );

  return postsWithAuthor;
  // 총 11개 쿼리!
}

// ✅ 좋은 예제: include 사용
async getPostsWithAuthor() {
  return prisma.post.findMany({
    include: {
      author: true, // 조인으로 한 번에 조회
    },
  });
  // 총 1개 쿼리 (또는 2개 - DB 최적화에 따라)
}
```

## 다양한 시나리오

### 1단계 관계

```typescript
// 포스트와 작가
async getPosts() {
  return prisma.post.findMany({
    include: {
      author: true,
    },
  });
}
```

### 다단계 관계

```typescript
// 주석과 댓글 작가
async getPosts() {
  return prisma.post.findMany({
    include: {
      author: true,
      comments: {
        include: {
          author: true, // 중첩된 관계
        },
      },
    },
  });
}
```

### 선택적 필드 포함

```typescript
// 필요한 필드만 선택
async getPosts() {
  return prisma.post.findMany({
    include: {
      author: {
        select: {
          id: true,
          name: true,
          email: true,
          // password는 제외
        },
      },
    },
    select: {
      id: true,
      title: true,
      content: true,
      author: true,
      // comments는 제외
    },
  });
}
```

## 고급 사용법 - DataLoader

대규모 배치 작업에서는 DataLoader를 사용하여 더 효율적으로 처리:

```typescript
// loaders/author.loader.ts
import DataLoader from 'dataloader';
import { PrismaService } from 'prisma/prisma.service';

export class AuthorLoader {
  private loader: DataLoader<string, User>;

  constructor(private prisma: PrismaService) {
    this.loader = new DataLoader(async (userIds: readonly string[]) => {
      // 여러 개의 ID를 한 번에 조회
      const users = await this.prisma.user.findMany({
        where: {
          id: { in: [...userIds] },
        },
      });

      // userIds 순서대로 정렬하여 반환
      return userIds.map(
        id => users.find(user => user.id === id) || null
      );
    });
  }

  async load(userId: string): Promise<User | null> {
    return this.loader.load(userId);
  }

  async loadMany(userIds: string[]): Promise<(User | null)[]> {
    return this.loader.loadMany(userIds);
  }

  clearCache(userId: string): void {
    this.loader.clear(userId);
  }
}

// graphql/resolvers/post.resolver.ts
@Resolver(Post)
export class PostResolver {
  constructor(private authorLoader: AuthorLoader) {}

  @ResolveField(() => User)
  async author(@Parent() post: Post) {
    // 여러 포스트를 로드할 때도 배치 처리됨
    return this.authorLoader.load(post.authorId);
  }
}
```

## React Query와 함께 사용

```typescript
// hooks/usePosts.ts
import { useQuery } from '@tanstack/react-query';

async function fetchPosts() {
  const response = await fetch('/api/posts?include=author,comments');
  return response.json();
}

export function usePosts() {
  return useQuery({
    queryKey: ['posts'],
    queryFn: fetchPosts,
  });
}

// API 엔드포인트
@Controller('api/posts')
export class PostsController {
  @Get()
  async getPosts(
    @Query('include') include?: string, // 'author,comments'
  ) {
    const includeMap = (include || '').split(',').reduce(
      (acc, key) => {
        acc[key.trim()] = true;
        return acc;
      },
      {} as Record<string, boolean>
    );

    return this.prisma.post.findMany({
      include: includeMap,
      take: 20,
    });
  }
}
```

## 연관관계별 쿼리 최적화

```typescript
// 댓글이 많은 포스트
async getPostsWithCommentCount() {
  return prisma.post.findMany({
    include: {
      _count: {
        select: {
          comments: true, // 댓글 개수만 조회
        },
      },
    },
    select: {
      id: true,
      title: true,
      _count: true,
    },
  });
}

// 최근 댓글만 포함
async getPostsWithRecentComments() {
  return prisma.post.findMany({
    include: {
      comments: {
        take: 5, // 최신 5개만
        orderBy: {
          createdAt: 'desc',
        },
      },
    },
  });
}
```

## 최소 예제

```typescript
// ❌ 나쁜 예제
const posts = await db.post.findMany();
for (const post of posts) {
  const author = await db.user.findUnique({
    where: { id: post.authorId },
  }); // N번 반복!
}

// ✅ 좋은 예제
const posts = await db.post.findMany({
  include: { author: true },
});
```

## 성능 모니터링

```typescript
// 쿼리 개수 모니터링
if (process.env.NODE_ENV === 'development') {
  prisma.$on('query', (e) => {
    console.log(`Query: ${e.query}`);
    console.log(`Duration: ${e.duration}ms`);
  });
}
```

## 안티패턴

### 1. 조건부 include

```typescript
// ❌ 나쁜 예제
async getPosts(includeComments: boolean) {
  if (includeComments) {
    return prisma.post.findMany({
      include: { comments: true },
    });
  } else {
    return prisma.post.findMany(); // N+1 발생 가능
  }
}

// ✅ 좋은 예제
async getPosts(includeComments: boolean) {
  return prisma.post.findMany({
    include: {
      comments: includeComments,
    },
  });
}
```

### 2. 모든 관계 포함

```typescript
// ❌ 나쁜 예제
async getPost(id: string) {
  return prisma.post.findUnique({
    where: { id },
    include: {
      author: true,
      comments: true,
      likes: true,
      tags: true,
      // 모든 관계를 포함 - 오버페칭
    },
  });
}

// ✅ 좋은 예제
async getPost(id: string) {
  return prisma.post.findUnique({
    where: { id },
    include: {
      author: true,
      comments: {
        take: 10,
        include: { author: true },
      },
      // 필요한 관계만 포함
    },
  });
}
```

## 연결된 오류

- **E-QP-05**: N+1 쿼리로 인한 성능 저하
- **E-QP-06**: 메모리 오버헤드로 인한 서버 부하

## 연결된 플로우

- **F-QP-03**: 포스트 목록 조회 최적화

## 참고 자료

- Prisma Eager Loading: https://www.prisma.io/docs/orm/prisma-client/queries/relations/eager-loading-relations
- DataLoader: https://github.com/graphql/dataloader
- N+1 Problem: https://stackoverflow.com/questions/97197/what-is-the-n1-problem-in-orm-object-relational-mapping
