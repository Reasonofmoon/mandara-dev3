---
id: P-AR-03
title: 서버 세션 관리 패턴
stage: Implement
layer: API
pattern_family: Auth
tech_tags: [Redis, 세션, 동시 로그인 제한, 세션 만료]
linked_errors: [E-AR-07, E-AR-08]
linked_flows: [F-AR-05]
linked_prompts: [PR-AR-03]
---

# 서버 세션 관리 패턴

## 목표
Redis를 사용한 서버 세션 저장소로 세션 정보를 관리하고, 동시 로그인 제한과 세션 만료를 구현합니다.

## 언제 사용하는가
- JWT보다 더 강한 제어가 필요한 경우
- 사용자를 실시간으로 강제 로그아웃해야 할 때
- 동시 로그인 제한이 필요한 경우
- 세션별 추가 정보 관리가 필요한 경우

## 핵심 구조

### Redis 세션 저장소

```typescript
// session/session.service.ts
import { Injectable } from '@nestjs/common';
import { Redis } from 'ioredis';

interface SessionData {
  userId: string;
  email: string;
  role: string;
  loginAt: number;
  lastActivityAt: number;
  userAgent: string;
  ipAddress: string;
  deviceId?: string;
}

@Injectable()
export class SessionService {
  private redis: Redis;
  private readonly SESSION_TTL = 30 * 24 * 60 * 60; // 30일

  constructor() {
    this.redis = new Redis({
      host: process.env.REDIS_HOST,
      port: parseInt(process.env.REDIS_PORT || '6379'),
    });
  }

  // 세션 생성
  async createSession(
    sessionId: string,
    data: SessionData,
  ): Promise<void> {
    const key = `session:${sessionId}`;
    await this.redis.setex(
      key,
      this.SESSION_TTL,
      JSON.stringify(data),
    );

    // 사용자별 세션 목록 유지
    await this.redis.sadd(
      `user:${data.userId}:sessions`,
      sessionId,
    );
  }

  // 세션 조회
  async getSession(sessionId: string): Promise<SessionData | null> {
    const data = await this.redis.get(`session:${sessionId}`);
    return data ? JSON.parse(data) : null;
  }

  // 세션 활동 시간 갱신
  async updateActivity(sessionId: string): Promise<void> {
    const session = await this.getSession(sessionId);
    if (session) {
      session.lastActivityAt = Date.now();
      const key = `session:${sessionId}`;
      await this.redis.setex(
        key,
        this.SESSION_TTL,
        JSON.stringify(session),
      );
    }
  }

  // 세션 삭제
  async destroySession(sessionId: string): Promise<void> {
    const session = await this.getSession(sessionId);
    if (session) {
      await this.redis.del(`session:${sessionId}`);
      await this.redis.srem(
        `user:${session.userId}:sessions`,
        sessionId,
      );
    }
  }

  // 사용자의 모든 세션 조회
  async getUserSessions(userId: string): Promise<SessionData[]> {
    const sessionIds = await this.redis.smembers(
      `user:${userId}:sessions`,
    );

    const sessions: SessionData[] = [];
    for (const sessionId of sessionIds) {
      const session = await this.getSession(sessionId);
      if (session) {
        sessions.push(session);
      }
    }

    return sessions;
  }

  // 사용자의 모든 세션 종료
  async destroyAllSessions(userId: string): Promise<void> {
    const sessionIds = await this.redis.smembers(
      `user:${userId}:sessions`,
    );

    for (const sessionId of sessionIds) {
      await this.destroySession(sessionId);
    }
  }

  // 동시 세션 제한
  async enforceSessionLimit(
    userId: string,
    maxSessions: number = 1,
  ): Promise<void> {
    const sessions = await this.getUserSessions(userId);

    if (sessions.length > maxSessions) {
      // 가장 오래된 세션부터 제거
      const sorted = sessions.sort(
        (a, b) => a.lastActivityAt - b.lastActivityAt,
      );

      for (let i = 0; i < sorted.length - maxSessions; i++) {
        const sessionIds = await this.redis.smembers(
          `user:${userId}:sessions`,
        );
        const oldestSessionId = sessionIds[i];
        if (oldestSessionId) {
          await this.destroySession(oldestSessionId);
        }
      }
    }
  }
}
```

### 인증 컨트롤러

```typescript
// auth/auth.controller.ts
import { Controller, Post, Body, Req, Res } from '@nestjs/common';
import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

@Controller('auth')
export class AuthController {
  constructor(
    private sessionService: SessionService,
    private authService: AuthService,
  ) {}

  @Post('login')
  async login(
    @Body() loginDto: LoginDto,
    @Req() request: Request,
    @Res({ passthrough: true }) response: Response,
  ) {
    // 사용자 인증
    const user = await this.authService.validateUser(
      loginDto.email,
      loginDto.password,
    );

    // 세션 ID 생성
    const sessionId = uuidv4();

    // 세션 생성
    await this.sessionService.createSession(sessionId, {
      userId: user.id,
      email: user.email,
      role: user.role,
      loginAt: Date.now(),
      lastActivityAt: Date.now(),
      userAgent: request.get('user-agent') || '',
      ipAddress: request.ip || '',
      deviceId: loginDto.deviceId,
    });

    // 동시 로그인 제한 (1개만 허용)
    await this.sessionService.enforceSessionLimit(user.id, 1);

    // 쿠키에 세션 ID 저장
    response.cookie('sessionId', sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 30 * 24 * 60 * 60 * 1000, // 30일
    });

    return {
      user: { id: user.id, email: user.email, role: user.role },
    };
  }

  @Post('logout')
  async logout(
    @Req() request: Request,
    @Res({ passthrough: true }) response: Response,
  ) {
    const sessionId = request.cookies.sessionId;

    if (sessionId) {
      await this.sessionService.destroySession(sessionId);
    }

    response.clearCookie('sessionId');
    return { message: 'Logged out successfully' };
  }

  @Get('sessions')
  @UseGuards(SessionGuard)
  async listSessions(@Req() request: any) {
    const userId = request.session.userId;
    const sessions = await this.sessionService.getUserSessions(userId);

    return sessions.map(session => ({
      ...session,
      isCurrent: session.sessionId === request.cookies.sessionId,
      loginTime: new Date(session.loginAt).toISOString(),
      lastActivity: new Date(session.lastActivityAt).toISOString(),
    }));
  }

  @Post('sessions/:sessionId/revoke')
  @UseGuards(SessionGuard)
  async revokeSession(
    @Param('sessionId') sessionId: string,
    @Req() request: any,
  ) {
    const session = await this.sessionService.getSession(sessionId);
    if (!session || session.userId !== request.session.userId) {
      throw new ForbiddenException('Cannot revoke other users sessions');
    }

    await this.sessionService.destroySession(sessionId);
    return { message: 'Session revoked' };
  }
}
```

### Session Guard

```typescript
// session/session.guard.ts
import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';

@Injectable()
export class SessionGuard implements CanActivate {
  constructor(private sessionService: SessionService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const sessionId = request.cookies.sessionId;

    if (!sessionId) {
      throw new UnauthorizedException('No session');
    }

    const session = await this.sessionService.getSession(sessionId);

    if (!session) {
      throw new UnauthorizedException('Invalid or expired session');
    }

    // 활동 시간 갱신
    await this.sessionService.updateActivity(sessionId);

    // 요청에 세션 정보 추가
    request.session = session;
    request.sessionId = sessionId;

    return true;
  }
}
```

## 최소 예제

```typescript
// 간단한 세션
const sessionId = crypto.randomUUID();
redis.setex(`session:${sessionId}`, 86400, JSON.stringify({
  userId: user.id,
  email: user.email,
}));

response.cookie('sessionId', sessionId, { httpOnly: true });
```

## 다중 기기 관리

```typescript
// 여러 기기에서 로그인 허용
@Post('login')
async login(
  @Body() loginDto: LoginDto & { deviceName?: string },
  @Req() request: Request,
  @Res({ passthrough: true }) response: Response,
) {
  const user = await this.authService.validateUser(
    loginDto.email,
    loginDto.password,
  );

  const sessionId = uuidv4();

  await this.sessionService.createSession(sessionId, {
    userId: user.id,
    email: user.email,
    role: user.role,
    loginAt: Date.now(),
    lastActivityAt: Date.now(),
    userAgent: request.get('user-agent') || '',
    ipAddress: request.ip || '',
    deviceId: loginDto.deviceName,
  });

  // 최대 3개 동시 세션 허용
  await this.sessionService.enforceSessionLimit(user.id, 3);

  response.cookie('sessionId', sessionId, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
  });

  return { user };
}
```

## 세션 모니터링

```typescript
@Get('active-sessions')
@UseGuards(SessionGuard)
async getActiveSessions(@Req() request: any) {
  const sessions = await this.sessionService.getUserSessions(
    request.session.userId,
  );

  return {
    total: sessions.length,
    current: sessions.find(s =>
      s.sessionId === request.sessionId
    ),
    others: sessions.filter(s =>
      s.sessionId !== request.sessionId
    ),
  };
}
```

## 안티패턴

### 1. 세션 활동 시간 갱신 안 함

```typescript
// ❌ 나쁜 예제 - 세션 만료 시간이 고정됨
async executeRequest() {
  // 활동 시간 갱신 안 함
}

// ✅ 좋은 예제
async executeRequest() {
  await this.sessionService.updateActivity(sessionId);
}
```

### 2. 세션 저장소 정리 누락

```typescript
// ❌ 나쁜 예제 - 만료된 세션 계속 증가
// 정리 없음

// ✅ 좋은 예제
@Cron('0 */6 * * *') // 6시간마다
async cleanupExpiredSessions() {
  // Redis TTL이 자동으로 처리하므로 추가 정리 불필요
  // 필요 시 orphaned session 정리
}
```

## 연결된 오류

- **E-AR-07**: 동시 로그인 제한 초과
- **E-AR-08**: 세션 만료로 인한 재인증 필요

## 연결된 플로우

- **F-AR-05**: 멀티 기기 세션 관리

## 참고 자료

- Redis Sessions: https://redis.io/docs/
- Session Security: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
