---
id: P-AC-02
title: 요청-응답 계약 패턴
stage: Design
layer: API
pattern_family: Contract
tech_tags: [Zod, DTO, 타입 안전, API 계약]
linked_errors: [E-AC-03, E-AC-04, E-AC-05]
linked_flows: [F-AC-03, F-AC-04]
linked_prompts: [PR-AC-02]
---

# 요청-응답 계약 패턴

## 목표
Zod 스키마를 사용하여 API의 요청과 응답 형식을 명확히 정의하고, 클라이언트와 서버 간 타입 안전성을 보장합니다.

## 언제 사용하는가
- REST API 개발 시
- 클라이언트와 서버를 별도로 개발할 때
- API 문서를 자동으로 생성해야 할 때
- 타입 안전성이 중요한 경우

## 언제 사용하지 않는가
- GraphQL (이미 타입 안전)
- 단순 프로토타입

## 핵심 구조

### 1. 공유 스키마 정의

```typescript
// schemas/user.ts - 클라이언트와 서버에서 공유
import { z } from 'zod';

export const CreateUserRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  age: z.number().int().min(18).optional(),
});

export const UserResponseSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  firstName: z.string(),
  lastName: z.string(),
  createdAt: z.string().datetime(),
});

export const UserListResponseSchema = z.object({
  data: z.array(UserResponseSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
});

export type CreateUserRequest = z.infer<typeof CreateUserRequestSchema>;
export type UserResponse = z.infer<typeof UserResponseSchema>;
export type UserListResponse = z.infer<typeof UserListResponseSchema>;
```

### 2. 서버 구현

```typescript
// controllers/user.controller.ts
import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  Query,
  BadRequestException,
} from '@nestjs/common';
import {
  CreateUserRequestSchema,
  UserResponseSchema,
  UserListResponseSchema,
} from '@shared/schemas/user';

@Controller('api/users')
export class UserController {
  constructor(private userService: UserService) {}

  @Post()
  async createUser(@Body() body: unknown) {
    // 1. 요청 검증
    const validationResult = CreateUserRequestSchema.safeParse(body);

    if (!validationResult.success) {
      throw new BadRequestException({
        message: 'Invalid request',
        errors: validationResult.error.flatten(),
      });
    }

    const createUserRequest = validationResult.data;

    // 2. 비즈니스 로직 처리
    const user = await this.userService.createUser(createUserRequest);

    // 3. 응답 검증 및 반환
    return UserResponseSchema.parse({
      id: user.id,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      createdAt: user.createdAt.toISOString(),
    });
  }

  @Get()
  async listUsers(
    @Query('page') page?: string,
    @Query('pageSize') pageSize?: string,
  ) {
    const p = parseInt(page || '1', 10);
    const ps = parseInt(pageSize || '10', 10);

    const result = await this.userService.listUsers(p, ps);

    // 응답 검증
    return UserListResponseSchema.parse({
      data: result.users.map(u => ({
        id: u.id,
        email: u.email,
        firstName: u.firstName,
        lastName: u.lastName,
        createdAt: u.createdAt.toISOString(),
      })),
      total: result.total,
      page: p,
      pageSize: ps,
    });
  }

  @Get(':id')
  async getUser(@Param('id') id: string) {
    const user = await this.userService.findById(id);

    if (!user) {
      throw new NotFoundException();
    }

    return UserResponseSchema.parse({
      id: user.id,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      createdAt: user.createdAt.toISOString(),
    });
  }
}
```

### 3. 클라이언트 구현

```typescript
// api/user-client.ts
import { CreateUserRequest, UserResponse } from '@shared/schemas/user';

export class UserApiClient {
  private baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:3000';

  async createUser(request: CreateUserRequest): Promise<UserResponse> {
    const response = await fetch(`${this.baseUrl}/api/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to create user: ${response.statusText}`);
    }

    return response.json() as Promise<UserResponse>;
  }

  async getUser(userId: string): Promise<UserResponse> {
    const response = await fetch(`${this.baseUrl}/api/users/${userId}`);

    if (!response.ok) {
      throw new Error(`Failed to get user: ${response.statusText}`);
    }

    return response.json() as Promise<UserResponse>;
  }
}

// React 사용
export function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    const client = new UserApiClient();
    client.getUser(userId).then(setUser);
  }, [userId]);

  if (!user) return <div>로딩 중...</div>;

  return (
    <div>
      <h1>{user.firstName} {user.lastName}</h1>
      <p>{user.email}</p>
      <p>가입: {new Date(user.createdAt).toLocaleDateString()}</p>
    </div>
  );
}
```

## 최소 예제

```typescript
// shared/schemas.ts
export const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
});

export type User = z.infer<typeof UserSchema>;

// server.ts
app.get('/users/:id', (req, res) => {
  const user = getUser(req.params.id);
  res.json(UserSchema.parse(user));
});

// client.ts
const user: User = await fetch('/users/123').then(r => r.json());
```

## 에러 응답 계약

```typescript
export const ErrorResponseSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.any()).optional(),
  timestamp: z.string().datetime(),
});

export const BadRequestErrorSchema = ErrorResponseSchema.extend({
  code: z.literal('BAD_REQUEST'),
  details: z.object({
    field: z.string(),
    message: z.string(),
  }).array(),
});

export const NotFoundErrorSchema = ErrorResponseSchema.extend({
  code: z.literal('NOT_FOUND'),
});

// 서버 에러 핸들러
@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  catch(exception: any, host: ArgumentsHost) {
    const response = host.switchToHttp().getResponse();

    let errorResponse = {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
    };

    if (exception instanceof BadRequestException) {
      errorResponse = {
        code: 'BAD_REQUEST',
        message: exception.message,
        timestamp: new Date().toISOString(),
      };
    }

    // 응답 검증 (개발 환경)
    if (process.env.NODE_ENV === 'development') {
      ErrorResponseSchema.parse(errorResponse);
    }

    response.status(exception.getStatus?.() || 500).json(errorResponse);
  }
}
```

## Pagination 계약

```typescript
export const PaginationParamsSchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(10),
  sortBy: z.string().optional(),
  order: z.enum(['asc', 'desc']).default('asc'),
});

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: z.array(dataSchema),
    pagination: z.object({
      page: z.number(),
      pageSize: z.number(),
      total: z.number(),
      totalPages: z.number(),
    }),
  });

type PaginatedResponse<T> = z.infer<
  ReturnType<typeof PaginatedResponseSchema<z.ZodType<T>>>
>;
```

## 안티패턴

### 1. 스키마 없이 문서만 작성

```typescript
// ❌ 나쁜 예제
// API_DOCS.md: "POST /users - Create a user with email, password, ..."
// 실제 구현과 불일치 가능

// ✅ 좋은 예제
const UserSchema = z.object({ /* ... */ });
// 스키마가 source of truth
```

### 2. 선택적 필드를 제대로 표현하지 않음

```typescript
// ❌ 나쁜 예제
const schema = z.object({
  age: z.number(), // 필수로 보이지만 null일 수 있음
});

// ✅ 좋은 예제
const schema = z.object({
  age: z.number().optional(),
  // 또는
  age: z.number().nullable(),
  // 또는
  age: z.number().or(z.null()).optional(),
});
```

### 3. 응답 검증 생략

```typescript
// ❌ 나쁜 예제
async getUser(id) {
  const user = await db.user.findUnique({ where: { id } });
  return user; // 검증 없음
}

// ✅ 좋은 예제
async getUser(id) {
  const user = await db.user.findUnique({ where: { id } });
  return UserResponseSchema.parse(user);
}
```

## 연결된 오류

- **E-AC-03**: 클라이언트가 예상하지 못한 응답 형식
- **E-AC-04**: 필수 필드가 누락된 응답
- **E-AC-05**: 타입 불일치로 인한 런타임 에러

## 연결된 플로우

- **F-AC-03**: API 개발 및 문서화
- **F-AC-04**: 클라이언트-서버 통신

## 참고 자료

- Zod 공식: https://zod.dev/
- OpenAPI/Swagger: https://swagger.io/
