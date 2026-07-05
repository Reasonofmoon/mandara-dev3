---
id: P-AR-01
title: 역할 기반 접근 제어 (RBAC) 패턴
stage: Implement
layer: API
pattern_family: Auth
tech_tags: [NestJS, Guard, Prisma, 권한 검증, 동적 권한]
linked_errors: [E-AR-01, E-AR-02, E-AR-03]
linked_flows: [F-AR-01, F-AR-02]
linked_prompts: [PR-AR-01]
---

# 역할 기반 접근 제어 (RBAC) 패턴

## 목표
사용자의 역할과 권한을 기반으로 리소스에 대한 접근을 제어하고, 데코레이터를 통해 간편하게 관리합니다.

## 언제 사용하는가
- 사용자 역할이 명확하게 정의된 시스템
- 역할 기반 권한 관리가 필요할 때
- 관리자, 사용자 등 역할이 구분될 때

## 언제 사용하지 않는가
- 매우 세분화된 권한 체계 (ABAC 고려)

## 핵심 구조

### Prisma 스키마

```prisma
// schema.prisma
enum UserRole {
  ADMIN
  MODERATOR
  USER
  GUEST
}

model User {
  id            String   @id @default(cuid())
  email         String   @unique
  password      String
  role          UserRole @default(USER)
  permissions   Permission[]
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
}

model Permission {
  id    String @id @default(cuid())
  name  String @unique // 'users.read', 'posts.write', 등
  users User[]
}

model RolePermission {
  id           String   @id @default(cuid())
  role         UserRole
  permissionId String
  permission   Permission @relation(fields: [permissionId], references: [id])

  @@unique([role, permissionId])
}
```

### NestJS Guard 구현

```typescript
// auth/decorators/roles.decorator.ts
import { SetMetadata } from '@nestjs/common';
import { UserRole } from '@prisma/client';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: UserRole[]) =>
  SetMetadata(ROLES_KEY, roles);

// auth/guards/roles.guard.ts
import {
  CanActivate,
  ExecutionContext,
  Injectable,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UserRole } from '@prisma/client';
import { ROLES_KEY } from '../decorators/roles.decorator';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<UserRole[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (!requiredRoles) {
      // 역할 요구사항 없음 - 모든 인증된 사용자 허용
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user; // JWT Guard에서 설정됨

    if (!user) {
      return false;
    }

    return requiredRoles.includes(user.role);
  }
}

// auth/guards/jwt.guard.ts
import {
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }

  handleRequest(err: any, user: any, info: any) {
    if (err || !user) {
      throw err || new UnauthorizedException();
    }
    return user;
  }
}
```

### 컨트롤러에서 사용

```typescript
// users/users.controller.ts
import { Controller, Get, Delete, Param, UseGuards } from '@nestjs/common';
import { UserRole } from '@prisma/client';
import { JwtGuard } from 'auth/guards/jwt.guard';
import { RolesGuard } from 'auth/guards/roles.guard';
import { Roles } from 'auth/decorators/roles.decorator';

@Controller('api/users')
@UseGuards(JwtGuard, RolesGuard)
export class UsersController {
  constructor(private usersService: UsersService) {}

  @Get()
  @Roles(UserRole.ADMIN, UserRole.MODERATOR)
  async listUsers() {
    return this.usersService.findAll();
  }

  @Get(':id')
  async getUser(@Param('id') id: string) {
    return this.usersService.findById(id);
  }

  @Delete(':id')
  @Roles(UserRole.ADMIN)
  async deleteUser(@Param('id') id: string) {
    return this.usersService.delete(id);
  }
}

// posts/posts.controller.ts
@Controller('api/posts')
@UseGuards(JwtGuard)
export class PostsController {
  constructor(private postsService: PostsService) {}

  @Get()
  async listPosts() {
    // 모든 인증된 사용자 허용 (권한 체크 없음)
    return this.postsService.findAll();
  }

  @Post()
  @Roles(UserRole.USER, UserRole.ADMIN)
  async createPost(@Body() createPostDto: CreatePostDto) {
    return this.postsService.create(createPostDto);
  }
}
```

## 최소 예제

```typescript
// 간단한 버전
@Controller('admin')
@UseGuards(JwtGuard, RolesGuard)
export class AdminController {
  @Get('users')
  @Roles(UserRole.ADMIN)
  getUsers() {
    return [];
  }
}
```

## 고급 사용법 - 권한 기반 제어 (Permission-based)

```typescript
// auth/decorators/permissions.decorator.ts
export const PERMISSIONS_KEY = 'permissions';
export const Permissions = (...permissions: string[]) =>
  SetMetadata(PERMISSIONS_KEY, permissions);

// auth/guards/permissions.guard.ts
@Injectable()
export class PermissionsGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    private prisma: PrismaService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const requiredPermissions = this.reflector.getAllAndOverride<string[]>(
      PERMISSIONS_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (!requiredPermissions) {
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user) {
      return false;
    }

    // 역할의 권한 확인
    const rolePermissions = await this.prisma.rolePermission.findMany({
      where: {
        role: user.role,
        permission: {
          name: {
            in: requiredPermissions,
          },
        },
      },
    });

    const grantedPermissions = rolePermissions.map(rp => rp.permission.name);

    return requiredPermissions.every(perm =>
      grantedPermissions.includes(perm)
    );
  }
}

// 사용
@Controller('posts')
@UseGuards(JwtGuard, PermissionsGuard)
export class PostsController {
  @Post()
  @Permissions('posts.create')
  async createPost(@Body() dto: CreatePostDto) {
    return this.postsService.create(dto);
  }

  @Delete(':id')
  @Permissions('posts.delete')
  async deletePost(@Param('id') id: string) {
    return this.postsService.delete(id);
  }
}
```

## 리소스 소유권 검증

```typescript
// auth/decorators/owner-or-admin.decorator.ts
export const OwnerOrAdmin = () => SetMetadata('ownerOrAdmin', true);

// auth/guards/owner-or-admin.guard.ts
@Injectable()
export class OwnerOrAdminGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    const { id } = request.params;

    // 관리자는 항상 허용
    if (user.role === UserRole.ADMIN) {
      return true;
    }

    // 소유자 확인
    const resource = await this.getResource(id);
    return resource.userId === user.id;
  }

  private async getResource(id: string) {
    // 리소스 조회 로직
    return this.prisma.post.findUnique({ where: { id } });
  }
}

// 사용
@Controller('posts')
export class PostsController {
  @Patch(':id')
  @UseGuards(JwtGuard, OwnerOrAdminGuard)
  async updatePost(
    @Param('id') id: string,
    @Body() updateDto: UpdatePostDto,
  ) {
    return this.postsService.update(id, updateDto);
  }
}
```

## 역할 초기화

```typescript
// auth/seeds/roles.seed.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';
import { UserRole } from '@prisma/client';

@Injectable()
export class RolesSeedService {
  constructor(private prisma: PrismaService) {}

  async seed() {
    // 권한 생성
    const permissions = [
      'users.read',
      'users.write',
      'users.delete',
      'posts.create',
      'posts.read',
      'posts.update',
      'posts.delete',
    ];

    for (const permName of permissions) {
      await this.prisma.permission.upsert({
        where: { name: permName },
        update: {},
        create: { name: permName },
      });
    }

    // 역할-권한 매핑
    const permissionMap = {
      [UserRole.ADMIN]: permissions, // 모든 권한
      [UserRole.MODERATOR]: [
        'users.read',
        'posts.read',
        'posts.delete', // 포스트 삭제 권한
      ],
      [UserRole.USER]: [
        'posts.create',
        'posts.read',
        'posts.update', // 자신의 포스트만 수정
      ],
    };

    for (const [role, perms] of Object.entries(permissionMap)) {
      for (const permName of perms) {
        const permission = await this.prisma.permission.findUnique({
          where: { name: permName },
        });

        await this.prisma.rolePermission.upsert({
          where: {
            role_permissionId: {
              role: role as UserRole,
              permissionId: permission!.id,
            },
          },
          update: {},
          create: {
            role: role as UserRole,
            permissionId: permission!.id,
          },
        });
      }
    }
  }
}
```

## 안티패턴

### 1. 권한 검증 누락

```typescript
// ❌ 나쁜 예제
@Delete('users/:id')
deleteUser(@Param('id') id: string) {
  return this.usersService.delete(id); // 누구나 삭제 가능!
}

// ✅ 좋은 예제
@Delete('users/:id')
@UseGuards(JwtGuard, RolesGuard)
@Roles(UserRole.ADMIN)
deleteUser(@Param('id') id: string) {
  return this.usersService.delete(id);
}
```

### 2. 하드코딩된 권한

```typescript
// ❌ 나쁜 예제
if (user.role === 'admin') { // 문자열 비교
  // 권한 부여
}

// ✅ 좋은 예제
if (user.role === UserRole.ADMIN) { // Enum 사용
  // 권한 부여
}
```

## 연결된 오류

- **E-AR-01**: 권한 검증 Guard 누락
- **E-AR-02**: 권한 부여 오류로 인한 접근 거부
- **E-AR-03**: 인증되지 않은 사용자의 리소스 접근

## 연결된 플로우

- **F-AR-01**: 사용자 인증 및 권한 부여
- **F-AR-02**: 관리자 권한 관리

## 참고 자료

- NestJS Guards: https://docs.nestjs.com/guards
- OWASP Authorization: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
