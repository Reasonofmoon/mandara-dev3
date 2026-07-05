---
id: P-AC-03
title: API 버전 관리 패턴
stage: Design
layer: API
pattern_family: Contract
tech_tags: [버전 관리, 하위 호환성, API 진화]
linked_errors: [E-AC-06, E-AC-07]
linked_flows: [F-AC-05]
linked_prompts: [PR-AC-03]
---

# API 버전 관리 패턴

## 목표
API의 하위 호환성을 유지하면서 새로운 기능을 추가하고, 구 버전을 단계적으로 폐기합니다.

## 언제 사용하는가
- 기존 클라이언트를 깨뜨리지 않고 API를 개선할 때
- 다양한 버전의 클라이언트를 지원해야 할 때
- API 진화 전략이 필요한 경우

## 언제 사용하지 않는가
- 단일 클라이언트만 지원하는 경우 (내부 API)

## 핵심 구조

### 1. URL 경로 버전 (가장 일반적)

```typescript
import { Module } from '@nestjs/common';
import { Controller, Get, Post, Body, Param } from '@nestjs/common';

// API v1 컨트롤러
@Controller('api/v1/users')
export class UserControllerV1 {
  @Get(':id')
  async getUser(@Param('id') id: string) {
    const user = await this.userService.findById(id);
    // v1 응답 형식
    return {
      id: user.id,
      name: user.name,
      email: user.email,
    };
  }

  @Post()
  async createUser(@Body() body: any) {
    const user = await this.userService.create(body);
    return {
      id: user.id,
      name: user.name,
      email: user.email,
    };
  }
}

// API v2 컨트롤러 - 개선된 형식
@Controller('api/v2/users')
export class UserControllerV2 {
  @Get(':id')
  async getUser(@Param('id') id: string) {
    const user = await this.userService.findById(id);
    // v2 응답 형식 - 더 상세한 정보
    return {
      id: user.id,
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
      createdAt: user.createdAt,
      profile: {
        bio: user.bio,
        avatar: user.avatar,
      },
    };
  }

  @Post()
  async createUser(@Body() body: CreateUserV2Dto) {
    const user = await this.userService.create({
      firstName: body.firstName,
      lastName: body.lastName,
      email: body.email,
      bio: body.profile?.bio,
      avatar: body.profile?.avatar,
    });
    return {
      id: user.id,
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
      createdAt: user.createdAt,
      profile: {
        bio: user.bio,
        avatar: user.avatar,
      },
    };
  }
}

@Module({
  controllers: [UserControllerV1, UserControllerV2],
})
export class UserModule {}
```

### 2. 헤더 기반 버전

```typescript
@Controller('api/users')
export class UserController {
  @Get(':id')
  async getUser(
    @Param('id') id: string,
    @Headers('API-Version') apiVersion: string = '1',
  ) {
    const user = await this.userService.findById(id);

    if (apiVersion === '2') {
      return {
        id: user.id,
        firstName: user.firstName,
        lastName: user.lastName,
        email: user.email,
        createdAt: user.createdAt,
        profile: {
          bio: user.bio,
          avatar: user.avatar,
        },
      };
    }

    // v1 (기본값)
    return {
      id: user.id,
      name: user.name,
      email: user.email,
    };
  }
}

// 클라이언트
fetch('/api/users/123', {
  headers: {
    'API-Version': '2',
  },
});
```

### 3. Query Parameter 버전

```typescript
@Controller('api/users')
export class UserController {
  @Get(':id')
  async getUser(
    @Param('id') id: string,
    @Query('api_version') apiVersion: string = '1',
  ) {
    // 버전별 처리
    const user = await this.userService.findById(id);
    return this.formatUserResponse(user, apiVersion);
  }

  private formatUserResponse(user: User, version: string) {
    if (version === '2') {
      return {
        id: user.id,
        firstName: user.firstName,
        lastName: user.lastName,
        email: user.email,
        createdAt: user.createdAt,
        profile: {
          bio: user.bio,
          avatar: user.avatar,
        },
      };
    }
    return {
      id: user.id,
      name: user.name,
      email: user.email,
    };
  }
}

// 클라이언트
fetch('/api/users/123?api_version=2');
```

## 최소 예제

```typescript
// 간단한 버전 관리
@Controller('api')
export class ApiController {
  @Get('v1/data')
  getV1() {
    return { status: 'v1' };
  }

  @Get('v2/data')
  getV2() {
    return { status: 'v2', extra: 'info' };
  }
}
```

## 고급 사용법 - 호환성 레이어

```typescript
// 버전 호환성을 자동으로 처리
class ApiVersionAdapter {
  static adaptResponse(data: any, version: string): any {
    if (version === '1') {
      // v2 형식을 v1 형식으로 변환
      return {
        id: data.id,
        name: `${data.firstName} ${data.lastName}`,
        email: data.email,
      };
    }
    return data;
  }

  static adaptRequest(data: any, fromVersion: string): any {
    if (fromVersion === '1') {
      // v1 요청을 v2 형식으로 변환
      const [firstName, lastName] = (data.name || '').split(' ');
      return {
        firstName,
        lastName,
        email: data.email,
      };
    }
    return data;
  }
}

@Controller('api')
export class VersionedController {
  @Get('users/:id')
  async getUser(
    @Param('id') id: string,
    @Headers('api-version') version: string = '2',
  ) {
    const user = await this.userService.findById(id);
    const v2Response = {
      id: user.id,
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
    };

    return ApiVersionAdapter.adaptResponse(v2Response, version);
  }

  @Post('users')
  async createUser(
    @Body() body: any,
    @Headers('api-version') version: string = '2',
  ) {
    const v2Data = ApiVersionAdapter.adaptRequest(body, version);
    const user = await this.userService.create(v2Data);

    const v2Response = {
      id: user.id,
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
    };

    return ApiVersionAdapter.adaptResponse(v2Response, version);
  }
}
```

## 버전 수명 주기 관리

```typescript
import { Deprecated, Header } from '@nestjs/common';

interface ApiVersionInfo {
  version: string;
  releaseDate: Date;
  deprecationDate?: Date;
  sunsetDate: Date; // API 종료 날짜
}

const VERSION_MANIFEST: Record<string, ApiVersionInfo> = {
  v1: {
    version: 'v1',
    releaseDate: new Date('2023-01-01'),
    deprecationDate: new Date('2024-01-01'),
    sunsetDate: new Date('2024-12-31'),
  },
  v2: {
    version: 'v2',
    releaseDate: new Date('2024-01-01'),
    sunsetDate: new Date('2025-12-31'),
  },
  v3: {
    version: 'v3',
    releaseDate: new Date('2025-01-01'),
    sunsetDate: new Date('2026-12-31'),
  },
};

@Controller('api')
export class VersionCheckMiddleware {
  private checkVersionStatus(version: string) {
    const info = VERSION_MANIFEST[version];
    if (!info) throw new BadRequestException(`API version ${version} not found`);

    const now = new Date();
    if (now > info.sunsetDate) {
      throw new GoneException(
        `API version ${version} has been discontinued`
      );
    }

    if (info.deprecationDate && now > info.deprecationDate) {
      console.warn(
        `API version ${version} is deprecated. Sunset date: ${info.sunsetDate}`
      );
    }
  }
}
```

## 마이그레이션 가이드 제공

```typescript
@Get('migration-guide/:from/:to')
getMigrationGuide(
  @Param('from') from: string,
  @Param('to') to: string,
) {
  return {
    from,
    to,
    changes: [
      {
        field: 'name',
        oldPath: 'user.name',
        newPath: 'user.firstName + user.lastName',
        description: '이름 필드가 firstName, lastName으로 분리됨',
      },
      {
        field: 'createdAt',
        oldPath: '없음',
        newPath: 'user.createdAt',
        description: '생성 날짜 필드 추가',
      },
    ],
    examples: {
      v1Response: {
        id: '123',
        name: 'John Doe',
        email: 'john@example.com',
      },
      v2Response: {
        id: '123',
        firstName: 'John',
        lastName: 'Doe',
        email: 'john@example.com',
        createdAt: '2024-01-01T00:00:00Z',
      },
    },
  };
}
```

## 안티패턴

### 1. 버전을 명시하지 않으면 최신 버전 제공

```typescript
// ❌ 나쁜 예제 - 기존 클라이언트가 깨짐
@Get('api/users')
getUsers() {
  return latestVersionFormat();
}

// ✅ 좋은 예제 - 명시적 버전 기본값
@Get('api/v1/users')
getUsersV1() {
  return v1Format();
}

@Get('api/v2/users')
getUsersV2() {
  return v2Format();
}
```

### 2. 버전 정보 누락

```typescript
// ❌ 나쁜 예제 - 어떤 버전이 폐기되는지 모름
@Get('api/v1/data')
getDataV1() { /* ... */ }

// ✅ 좋은 예제 - 명확한 수명 주기
@Get('api/v1/data')
@Deprecated('This version will be sunset on 2024-12-31')
getDataV1() { /* ... */ }
```

## 연결된 오류

- **E-AC-06**: 버전을 명시하지 않아 예상치 못한 응답 형식 수신
- **E-AC-07**: 폐기된 API 버전 사용

## 연결된 플로우

- **F-AC-05**: API 버전 업그레이드 계획

## 참고 자료

- Semantic Versioning: https://semver.org/
- API Versioning Best Practices: https://swagger.io/blog/api-strategy/versioning-a-rest-api/
