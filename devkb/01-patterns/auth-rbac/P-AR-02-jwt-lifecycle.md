---
id: P-AR-02
title: JWT 생명주기 패턴
stage: Implement
layer: API
pattern_family: Auth
tech_tags: [JWT, Access Token, Refresh Token, 토큰 갱신, 보안]
linked_errors: [E-AR-04, E-AR-05, E-AR-06]
linked_flows: [F-AR-03, F-AR-04]
linked_prompts: [PR-AR-02]
---

# JWT 생명주기 패턴

## 목표
Access Token과 Refresh Token의 생명주기를 관리하여 보안과 사용성을 동시에 달성합니다.

## 언제 사용하는가
- 토큰 기반 인증 시스템
- 장기간 로그인 상태 유지가 필요한 경우
- 토큰 갱신이 필요한 경우

## 핵심 구조

### 토큰 생성 및 관리

```typescript
// auth/jwt.service.ts
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from 'prisma/prisma.service';

interface TokenPayload {
  sub: string; // user ID
  email: string;
  role: string;
}

@Injectable()
export class TokenService {
  constructor(
    private jwtService: JwtService,
    private prisma: PrismaService,
  ) {}

  // Access Token 생성 (단기)
  generateAccessToken(user: TokenPayload): string {
    return this.jwtService.sign(user, {
      secret: process.env.JWT_ACCESS_SECRET,
      expiresIn: '15m', // 15분
    });
  }

  // Refresh Token 생성 (장기)
  generateRefreshToken(user: TokenPayload): string {
    const token = this.jwtService.sign(user, {
      secret: process.env.JWT_REFRESH_SECRET,
      expiresIn: '7d', // 7일
    });

    // Refresh Token을 DB에 저장 (나중에 폐기 가능)
    this.prisma.refreshToken.create({
      data: {
        token,
        userId: user.sub,
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
      },
    });

    return token;
  }

  // 토큰 페어 생성
  generateTokenPair(user: TokenPayload) {
    return {
      accessToken: this.generateAccessToken(user),
      refreshToken: this.generateRefreshToken(user),
    };
  }

  // Refresh Token 검증 및 새 토큰 발급
  async refreshAccessToken(refreshToken: string) {
    try {
      // Refresh Token 검증
      const payload = this.jwtService.verify(refreshToken, {
        secret: process.env.JWT_REFRESH_SECRET,
      });

      // DB에서 토큰 확인 (폐기 여부)
      const storedToken = await this.prisma.refreshToken.findUnique({
        where: { token: refreshToken },
      });

      if (!storedToken || storedToken.revokedAt) {
        throw new Error('Refresh token has been revoked');
      }

      if (storedToken.expiresAt < new Date()) {
        throw new Error('Refresh token has expired');
      }

      // 새 Access Token 생성
      const newAccessToken = this.generateAccessToken({
        sub: payload.sub,
        email: payload.email,
        role: payload.role,
      });

      return {
        accessToken: newAccessToken,
        refreshToken: refreshToken, // 기존 refresh token 재사용
      };
    } catch (error) {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }

  // Refresh Token 폐기 (로그아웃)
  async revokeRefreshToken(refreshToken: string) {
    await this.prisma.refreshToken.update({
      where: { token: refreshToken },
      data: { revokedAt: new Date() },
    });
  }

  // 사용자의 모든 토큰 폐기 (강제 로그아웃)
  async revokeAllTokens(userId: string) {
    await this.prisma.refreshToken.updateMany({
      where: { userId },
      data: { revokedAt: new Date() },
    });
  }
}
```

### Prisma 스키마

```prisma
// schema.prisma
model RefreshToken {
  id        String   @id @default(cuid())
  token     String   @unique
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  expiresAt DateTime
  revokedAt DateTime?
  createdAt DateTime @default(now())

  @@index([userId])
  @@index([expiresAt])
}
```

### 컨트롤러

```typescript
// auth/auth.controller.ts
import { Controller, Post, Body, UseGuards, Req, Res } from '@nestjs/common';
import { Response } from 'express';

@Controller('auth')
export class AuthController {
  constructor(private tokenService: TokenService) {}

  @Post('login')
  async login(
    @Body() loginDto: LoginDto,
    @Res({ passthrough: true }) response: Response,
  ) {
    // 사용자 인증 (생략)
    const user = await this.authService.validateUser(
      loginDto.email,
      loginDto.password,
    );

    const { accessToken, refreshToken } = this.tokenService.generateTokenPair({
      sub: user.id,
      email: user.email,
      role: user.role,
    });

    // Refresh Token을 httpOnly 쿠키에 저장
    response.cookie('refreshToken', refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7일
    });

    return {
      accessToken,
      user: { id: user.id, email: user.email, role: user.role },
    };
  }

  @Post('refresh')
  async refresh(@Req() request: Request) {
    const refreshToken = request.cookies.refreshToken;

    if (!refreshToken) {
      throw new UnauthorizedException('Refresh token not found');
    }

    const tokens = await this.tokenService.refreshAccessToken(
      refreshToken,
    );

    return {
      accessToken: tokens.accessToken,
    };
  }

  @Post('logout')
  @UseGuards(JwtGuard)
  async logout(
    @Req() request: Request,
    @Res({ passthrough: true }) response: Response,
  ) {
    const refreshToken = request.cookies.refreshToken;

    if (refreshToken) {
      await this.tokenService.revokeRefreshToken(refreshToken);
    }

    // 쿠키 삭제
    response.clearCookie('refreshToken');

    return { message: 'Logged out successfully' };
  }

  @Post('logout-all')
  @UseGuards(JwtGuard)
  async logoutAll(
    @Req() request: any,
    @Res({ passthrough: true }) response: Response,
  ) {
    const userId = request.user.sub;
    await this.tokenService.revokeAllTokens(userId);
    response.clearCookie('refreshToken');

    return { message: 'Logged out from all devices' };
  }
}
```

### JWT Strategy (Passport)

```typescript
// auth/strategies/jwt.strategy.ts
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: process.env.JWT_ACCESS_SECRET,
    });
  }

  validate(payload: any) {
    return {
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
    };
  }
}
```

## 최소 예제

```typescript
// 간단한 토큰 관리
const accessToken = jwt.sign(
  { userId: user.id },
  process.env.JWT_SECRET,
  { expiresIn: '15m' }
);

const refreshToken = jwt.sign(
  { userId: user.id },
  process.env.JWT_REFRESH_SECRET,
  { expiresIn: '7d' }
);

return { accessToken, refreshToken };
```

## 클라이언트 구현

```typescript
// api/auth-client.ts
export class AuthClient {
  private accessToken: string | null = null;

  async login(email: string, password: string) {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include', // 쿠키 전송
    });

    const data = await response.json();
    this.accessToken = data.accessToken;
    return data;
  }

  async request(url: string, options?: RequestInit) {
    let response = await fetch(url, {
      ...options,
      headers: {
        ...options?.headers,
        Authorization: `Bearer ${this.accessToken}`,
      },
    });

    // Access Token 만료 시 갱신
    if (response.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        response = await fetch(url, {
          ...options,
          headers: {
            ...options?.headers,
            Authorization: `Bearer ${this.accessToken}`,
          },
        });
      }
    }

    return response;
  }

  async refreshAccessToken() {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    });

    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.accessToken;
      return true;
    }

    return false;
  }

  async logout() {
    await fetch('/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    this.accessToken = null;
  }
}
```

### React Hook

```typescript
// hooks/useAuth.ts
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const authClient = useRef(new AuthClient());

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const data = await authClient.current.login(email, password);
      setUser(data.user);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await authClient.current.logout();
    setUser(null);
  };

  return { user, loading, login, logout };
}
```

## 보안 고려사항

```typescript
// 만료된 토큰 정리 - 정기 작업
@Injectable()
export class TokenCleanupService {
  constructor(private prisma: PrismaService) {}

  @Cron('0 0 * * *') // 매일 자정
  async cleanupExpiredTokens() {
    await this.prisma.refreshToken.deleteMany({
      where: {
        expiresAt: {
          lt: new Date(),
        },
      },
    });
  }
}
```

## 안티패턴

### 1. Refresh Token을 localStorage에 저장

```typescript
// ❌ 나쁜 예제
localStorage.setItem('refreshToken', refreshToken); // XSS 취약점!

// ✅ 좋은 예제
// httpOnly 쿠키에 저장 (JavaScript에서 접근 불가)
response.cookie('refreshToken', refreshToken, { httpOnly: true });
```

### 2. 토큰 폐기 없이 로그아웃

```typescript
// ❌ 나쁜 예제
logout() {
  localStorage.removeItem('accessToken');
  // 서버의 토큰은 여전히 유효!
}

// ✅ 좋은 예제
async logout() {
  await fetch('/auth/logout', { method: 'POST' });
  // 서버가 토큰을 폐기함
  localStorage.removeItem('accessToken');
}
```

## 연결된 오류

- **E-AR-04**: 만료된 Access Token 사용
- **E-AR-05**: 무효한 Refresh Token
- **E-AR-06**: 토큰 갱신 실패로 인한 재인증 필요

## 연결된 플로우

- **F-AR-03**: 자동 토큰 갱신
- **F-AR-04**: 안전한 로그아웃

## 참고 자료

- JWT Best Practices: https://tools.ietf.org/html/rfc8725
- OWASP JWT Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
