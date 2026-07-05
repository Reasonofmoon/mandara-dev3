---
id: E-RT-07
title: 토큰 파싱 실패
error_class: Runtime
symptoms:
  - JWT 검증 실패
  - 인증 토큰 거부
  - 사용자 로그인 실패
exact_messages:
  - "Invalid token"
  - "JsonWebTokenError: invalid token"
  - "TokenExpiredError: jwt expired"
  - "JwtClaimsSetRejected"
tech_tags:
  - JWT
  - Authentication
  - Security
  - Token Management
linked_patterns: []
linked_flows: []
---

# 토큰 파싱 실패

## 증상
JWT 토큰이 손상, 만료, 또는 잘못된 서명으로 인해 검증에 실패합니다. 사용자 인증이 실패하거나 API 요청이 거부됩니다.

## 정확한 에러 메시지
```
Invalid token
JsonWebTokenError: invalid token
TokenExpiredError: jwt expired
JwtClaimsSetRejected: Token too old
NotBeforeError: token used before valid
```

## 발생 맥락
```typescript
// 잘못된 예 1: 토큰 서명 검증 실패
const secret = process.env.JWT_SECRET || 'default-secret';
const decoded = jwt.verify(token, secret);  // ❌ secret이 다르면 실패

// 잘못된 예 2: 만료된 토큰
const token = jwt.sign({ userId: 1 }, secret, { expiresIn: '1h' });
// 1시간 후
const decoded = jwt.verify(token, secret);  // ❌ TokenExpiredError

// 잘못된 예 3: 토큰이 손상됨
const token = 'eyJhbGc...truncated';
jwt.verify(token, secret);  // ❌ Invalid token

// 잘못된 예 4: Bearer 헤더 형식 오류
const authHeader = 'Token eyJhbGc...';  // ❌ 'Bearer' 아님
const token = authHeader.split(' ')[1];
```

## 필요한 증거
- JWT 토큰
- 에러 메시지
- 서명 키 설정
- 토큰 생성/검증 코드

## 의심 원인
1. JWT 서명 키가 일치하지 않음
2. 토큰이 만료됨
3. 토큰이 손상되거나 잘못된 형식
4. 토큰 생성과 검증의 알고리즘 불일치
5. 클라이언트와 서버의 시간 불일치
6. 토큰이 서버에서 撤回/블랙리스트됨

## 빠른 해결법

### 1. JWT 토큰 생성 및 검증
```typescript
import jwt from 'jsonwebtoken';

const SECRET = process.env.JWT_SECRET || 'your-secret-key';

// 토큰 생성
function generateToken(payload: any, expiresIn = '7d') {
  return jwt.sign(payload, SECRET, { expiresIn });
}

// 토큰 검증
function verifyToken(token: string) {
  try {
    return jwt.verify(token, SECRET);
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      console.error('Token expired');
    } else if (error.name === 'JsonWebTokenError') {
      console.error('Invalid token');
    }
    throw error;
  }
}
```

### 2. Express 미들웨어
```typescript
function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }

  const token = authHeader.slice(7);  // 'Bearer ' 제거

  try {
    const decoded = jwt.verify(token, SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      return res.status(401).json({ error: 'Token expired' });
    } else if (error instanceof jwt.JsonWebTokenError) {
      return res.status(401).json({ error: 'Invalid token' });
    }
    res.status(500).json({ error: 'Token verification failed' });
  }
}

app.get('/api/protected', authMiddleware, (req, res) => {
  res.json({ user: req.user });
});
```

### 3. 토큰 갱신 로직
```typescript
function generateTokens(payload: any) {
  const accessToken = jwt.sign(payload, SECRET, { expiresIn: '15m' });
  const refreshToken = jwt.sign(payload, REFRESH_SECRET, { expiresIn: '7d' });

  return { accessToken, refreshToken };
}

// 토큰 갱신 엔드포인트
app.post('/api/refresh', (req, res) => {
  const { refreshToken } = req.body;

  try {
    const decoded = jwt.verify(refreshToken, REFRESH_SECRET);
    const newTokens = generateTokens({ userId: decoded.userId });
    res.json(newTokens);
  } catch (error) {
    res.status(401).json({ error: 'Invalid refresh token' });
  }
});
```

### 4. 토큰 블랙리스트 (로그아웃)
```typescript
const tokenBlacklist = new Set<string>();

function logout(token: string) {
  tokenBlacklist.add(token);
}

function verifyTokenNotBlacklisted(token: string) {
  if (tokenBlacklist.has(token)) {
    throw new Error('Token has been revoked');
  }
  return jwt.verify(token, SECRET);
}

// 미들웨어
app.use((req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.slice(7);

  if (token && tokenBlacklist.has(token)) {
    return res.status(401).json({ error: 'Token has been revoked' });
  }

  next();
});
```

### 5. 환경 변수 설정
```bash
# .env
JWT_SECRET="your-super-secret-key-min-32-chars"
JWT_EXPIRY="7d"
REFRESH_SECRET="your-refresh-secret-key"
REFRESH_EXPIRY="30d"
```

### 6. 클라이언트에서 토큰 처리
```typescript
interface TokenResponse {
  accessToken: string;
  refreshToken?: string;
}

async function login(credentials: any): Promise<TokenResponse> {
  const response = await fetch('/api/login', {
    method: 'POST',
    body: JSON.stringify(credentials)
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const { accessToken, refreshToken } = await response.json();

  localStorage.setItem('accessToken', accessToken);
  if (refreshToken) {
    localStorage.setItem('refreshToken', refreshToken);
  }

  return { accessToken, refreshToken };
}

async function fetchWithAuth(url: string, options: any = {}) {
  let token = localStorage.getItem('accessToken');

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });

  // 토큰 만료 시 갱신 시도
  if (response.status === 401) {
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) {
      const newTokens = await refreshAccessToken(refreshToken);
      localStorage.setItem('accessToken', newTokens.accessToken);

      // 요청 재시도
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${newTokens.accessToken}`
        }
      });
    }
  }

  return response;
}
```

### 7. 토큰 검증 라이브러리
```typescript
import { jwtVerify } from 'jose';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

async function verifyAuth(token: string) {
  try {
    const verified = await jwtVerify(token, secret);
    return verified.payload;
  } catch (error) {
    throw new Error('Invalid token');
  }
}
```

### 8. 디버깅
```typescript
// 토큰 디코딩 (검증 없이)
const decoded = jwt.decode(token);
console.log('Token payload:', decoded);

// 토큰 정보 확인
const parts = token.split('.');
if (parts.length !== 3) {
  console.error('Invalid JWT format');
}

// Base64 디코딩
const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
console.log('Decoded payload:', payload);
```

## 연결된 패턴
- E-SP-02-auth-header-missing
- E-LS-08-auth-401-403-confusion

## 연결된 플로우
- 인증 및 권한 부여 플로우
- 토큰 생명주기 관리 플로우

## 재발 방지
1. JWT_SECRET을 안전하게 관리 (.env 파일)
2. 토큰 만료 시간을 적절히 설정
3. 액세스 토큰 (짧음) + 리프레시 토큰 (길음) 사용
4. 토큰 검증 시 명확한 에러 메시지 제공
5. 로그아웃 시 토큰 블랙리스트 처리
6. 정기적으로 SECRET 키 로테이션
7. HTTPS 전송으로 토큰 노출 방지
