---
id: P-AC-05
title: 표준 오류 응답 패턴
stage: Design
layer: API
pattern_family: Contract
tech_tags: [RFC 7807, Problem Details, 오류 처리, API 표준]
linked_errors: [E-AC-10, E-AC-11, E-AC-12]
linked_flows: [F-AC-07]
linked_prompts: [PR-AC-05]
---

# 표준 오류 응답 패턴

## 목표
RFC 7807 Problem Details를 따르는 표준화된 오류 응답 형식으로 클라이언트가 오류를 명확하게 처리할 수 있도록 합니다.

## 언제 사용하는가
- 모든 API 개발
- 클라이언트가 오류 종류별로 다르게 처리해야 할 때
- 상세한 오류 정보가 필요한 경우

## 핵심 구조

### RFC 7807 Problem Details 형식

```typescript
// shared/schemas/errors.ts
import { z } from 'zod';

export const ProblemDetailsSchema = z.object({
  type: z.string().url().describe('오류 종류 URI'),
  title: z.string().describe('오류 제목'),
  status: z.number().describe('HTTP 상태 코드'),
  detail: z.string().optional().describe('오류 상세 설명'),
  instance: z.string().optional().describe('오류 발생 인스턴스'),
  timestamp: z.string().datetime().describe('오류 발생 시간'),
  traceId: z.string().optional().describe('추적 ID'),
});

export type ProblemDetails = z.infer<typeof ProblemDetailsSchema>;

// 구체적인 오류 타입들
export const ValidationErrorDetailsSchema = ProblemDetailsSchema.extend({
  type: z.literal('https://api.example.com/errors/validation-error'),
  errors: z.array(z.object({
    field: z.string(),
    message: z.string(),
    value: z.any().optional(),
  })),
});

export const NotFoundErrorDetailsSchema = ProblemDetailsSchema.extend({
  type: z.literal('https://api.example.com/errors/not-found'),
});

export const ConflictErrorDetailsSchema = ProblemDetailsSchema.extend({
  type: z.literal('https://api.example.com/errors/conflict'),
  conflictingField: z.string().optional(),
  conflictingValue: z.any().optional(),
});

export type ValidationErrorDetails = z.infer<typeof ValidationErrorDetailsSchema>;
export type NotFoundErrorDetails = z.infer<typeof NotFoundErrorDetailsSchema>;
export type ConflictErrorDetails = z.infer<typeof ConflictErrorDetailsSchema>;
```

### NestJS 구현

```typescript
// common/exceptions/problem-details.exception.ts
import { HttpException, HttpStatus } from '@nestjs/common';
import { ProblemDetails } from '@shared/schemas/errors';

export class ProblemDetailsException extends HttpException {
  constructor(
    problemDetails: ProblemDetails,
    status: HttpStatus = HttpStatus.INTERNAL_SERVER_ERROR,
  ) {
    super(problemDetails, status);
  }
}

// 구체적인 예외 클래스들
export class ValidationErrorException extends ProblemDetailsException {
  constructor(errors: Array<{ field: string; message: string }>) {
    const problemDetails: ValidationErrorDetails = {
      type: 'https://api.example.com/errors/validation-error',
      title: 'Validation Error',
      status: 400,
      detail: 'The request body contains invalid data',
      timestamp: new Date().toISOString(),
      errors,
    };

    super(problemDetails, HttpStatus.BAD_REQUEST);
  }
}

export class ResourceNotFoundException extends ProblemDetailsException {
  constructor(resource: string, id: string) {
    const problemDetails: NotFoundErrorDetails = {
      type: 'https://api.example.com/errors/not-found',
      title: 'Not Found',
      status: 404,
      detail: `${resource} with id ${id} not found`,
      instance: `/api/${resource}/${id}`,
      timestamp: new Date().toISOString(),
    };

    super(problemDetails, HttpStatus.NOT_FOUND);
  }
}

export class ResourceConflictException extends ProblemDetailsException {
  constructor(
    resource: string,
    field: string,
    value: any,
  ) {
    const problemDetails: ConflictErrorDetails = {
      type: 'https://api.example.com/errors/conflict',
      title: 'Conflict',
      status: 409,
      detail: `${resource} with ${field} '${value}' already exists`,
      timestamp: new Date().toISOString(),
      conflictingField: field,
      conflictingValue: value,
    };

    super(problemDetails, HttpStatus.CONFLICT);
  }
}

// Global Exception Filter
import { ExceptionFilter, Catch, ArgumentsHost, HttpException } from '@nestjs/common';

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const request = ctx.getRequest();

    let statusCode = 500;
    let problemDetails: ProblemDetails;

    if (exception instanceof HttpException) {
      statusCode = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (
        typeof exceptionResponse === 'object' &&
        'type' in exceptionResponse
      ) {
        // 이미 Problem Details 형식
        problemDetails = exceptionResponse as ProblemDetails;
      } else {
        // 표준 HttpException을 Problem Details로 변환
        problemDetails = {
          type: 'https://api.example.com/errors/http-error',
          title: exception.name,
          status: statusCode,
          detail:
            typeof exceptionResponse === 'object' &&
            'message' in exceptionResponse
              ? (exceptionResponse as any).message
              : String(exceptionResponse),
          instance: request.url,
          timestamp: new Date().toISOString(),
          traceId: request.id, // 요청 ID
        };
      }
    } else {
      // 예상 밖의 오류
      problemDetails = {
        type: 'https://api.example.com/errors/internal-server-error',
        title: 'Internal Server Error',
        status: 500,
        detail:
          process.env.NODE_ENV === 'development'
            ? (exception as Error).message
            : 'An unexpected error occurred',
        instance: request.url,
        timestamp: new Date().toISOString(),
        traceId: request.id,
      };
    }

    response
      .status(statusCode)
      .header('Content-Type', 'application/problem+json')
      .json(problemDetails);
  }
}
```

### 컨트롤러에서 사용

```typescript
@Controller('api/users')
export class UserController {
  constructor(private userService: UserService) {}

  @Post()
  async createUser(@Body() body: unknown) {
    // 요청 검증
    try {
      const validationResult = CreateUserSchema.safeParse(body);
      if (!validationResult.success) {
        throw new ValidationErrorException(
          validationResult.error.issues.map(issue => ({
            field: String(issue.path[0]),
            message: issue.message,
          }))
        );
      }
    } catch (error) {
      // 검증 실패
    }

    const { email } = validationResult.data;

    // 이메일 중복 확인
    const existing = await this.userService.findByEmail(email);
    if (existing) {
      throw new ResourceConflictException('User', 'email', email);
    }

    // 사용자 생성
    const user = await this.userService.create(validationResult.data);
    return user;
  }

  @Get(':id')
  async getUser(@Param('id') id: string) {
    const user = await this.userService.findById(id);

    if (!user) {
      throw new ResourceNotFoundException('User', id);
    }

    return user;
  }
}
```

## 최소 예제

```typescript
// 간단한 오류 응답
const errorResponse = {
  type: 'https://api.example.com/errors/not-found',
  title: 'Not Found',
  status: 404,
  detail: 'User with id 123 not found',
  timestamp: new Date().toISOString(),
};

res.status(404).json(errorResponse);
```

## 클라이언트 오류 처리

```typescript
export class ApiClient {
  async fetch(url: string, options?: RequestInit) {
    const response = await fetch(url, options);

    if (!response.ok) {
      const problemDetails = await response.json() as ProblemDetails;
      throw new ApiError(problemDetails);
    }

    return response.json();
  }
}

export class ApiError extends Error {
  constructor(public problemDetails: ProblemDetails) {
    super(problemDetails.detail || problemDetails.title);
    this.name = 'ApiError';
  }

  isValidationError(): boolean {
    return this.problemDetails.type.includes('validation-error');
  }

  isNotFound(): boolean {
    return this.problemDetails.status === 404;
  }

  isConflict(): boolean {
    return this.problemDetails.status === 409;
  }
}

// React에서 사용
export function UserForm() {
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (formData: CreateUserRequest) => {
    try {
      const user = await apiClient.createUser(formData);
      // 성공
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.isValidationError()) {
          // 검증 오류 처리
          const validationError = error.problemDetails as ValidationErrorDetails;
          const fieldErrors: Record<string, string> = {};
          validationError.errors.forEach(err => {
            fieldErrors[err.field] = err.message;
          });
          setErrors(fieldErrors);
        } else if (error.isConflict()) {
          // 충돌 오류 처리
          alert('이미 등록된 이메일입니다');
        } else {
          alert(error.message);
        }
      }
    }
  };

  return (
    <form onSubmit={e => {
      e.preventDefault();
      handleSubmit(/* ... */);
    }}>
      {/* 폼 필드 */}
    </form>
  );
}
```

## 오류 카탈로그

```typescript
// 오류 정의 중앙화
export const ErrorCatalog = {
  VALIDATION_ERROR: {
    type: 'https://api.example.com/errors/validation-error',
    title: 'Validation Error',
    status: 400,
  },
  NOT_FOUND: {
    type: 'https://api.example.com/errors/not-found',
    title: 'Not Found',
    status: 404,
  },
  UNAUTHORIZED: {
    type: 'https://api.example.com/errors/unauthorized',
    title: 'Unauthorized',
    status: 401,
  },
  FORBIDDEN: {
    type: 'https://api.example.com/errors/forbidden',
    title: 'Forbidden',
    status: 403,
  },
  CONFLICT: {
    type: 'https://api.example.com/errors/conflict',
    title: 'Conflict',
    status: 409,
  },
  RATE_LIMIT: {
    type: 'https://api.example.com/errors/rate-limit',
    title: 'Too Many Requests',
    status: 429,
  },
  INTERNAL_SERVER_ERROR: {
    type: 'https://api.example.com/errors/internal-server-error',
    title: 'Internal Server Error',
    status: 500,
  },
} as const;

function createProblemDetails(
  catalogEntry: (typeof ErrorCatalog)[keyof typeof ErrorCatalog],
  detail: string,
  extra?: Record<string, any>,
): ProblemDetails {
  return {
    type: catalogEntry.type,
    title: catalogEntry.title,
    status: catalogEntry.status,
    detail,
    timestamp: new Date().toISOString(),
    ...extra,
  };
}
```

## 안티패턴

### 1. 불일치한 오류 형식

```typescript
// ❌ 나쁜 예제
return res.status(400).json({ error: 'Invalid email' });
// 또는
return res.status(404).json({ message: 'Not found' });
// 형식이 일관성이 없음

// ✅ 좋은 예제
return res.status(400).json({
  type: 'https://api.example.com/errors/validation-error',
  title: 'Validation Error',
  status: 400,
  detail: 'Invalid email format',
  timestamp: new Date().toISOString(),
});
```

### 2. 민감한 정보 노출

```typescript
// ❌ 나쁜 예제
catch (error) {
  res.status(500).json({
    detail: error.message, // SQL 오류 등 노출!
    stack: error.stack,
  });
}

// ✅ 좋은 예제
catch (error) {
  logger.error(error);
  res.status(500).json({
    type: 'https://api.example.com/errors/internal-server-error',
    title: 'Internal Server Error',
    status: 500,
    detail: 'An unexpected error occurred',
    timestamp: new Date().toISOString(),
    traceId: request.id, // 로그 추적용
  });
}
```

## 연결된 오류

- **E-AC-10**: 불일치한 오류 응답 형식으로 인한 클라이언트 파싱 실패
- **E-AC-11**: 오류 응답에 필수 정보 누락
- **E-AC-12**: 민감한 정보가 포함된 오류 응답

## 연결된 플로우

- **F-AC-07**: 오류 처리 및 사용자 알림

## 참고 자료

- RFC 7807 Problem Details: https://tools.ietf.org/html/rfc7807
- JSON API Error Objects: https://jsonapi.org/format/#errors
