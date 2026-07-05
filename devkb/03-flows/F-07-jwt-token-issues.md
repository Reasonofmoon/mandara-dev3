---
id: F-07
title: JWT 토큰 문제 해결
pattern_id: P-07
error_ids: [E-19, E-20, E-21]
tech_scope: JWT, 토큰 관리, 보안
---

# JWT 토큰 문제 해결

JWT 토큰 생성, 검증, 갱신 과정에서 발생하는 문제를 해결합니다.

## 1단계: 증상 고정

- "Invalid signature" 오류
- "Token not found" 또는 토큰 누락
- 토큰이 시간이 지나도 유효함 (만료 체크 안 함)
- 토큰이 너무 빨리 만료됨
- 토큰 갱신 실패
- 클라이언트에서 토큰 저장 위치 불명확

## 2단계: 재현

```javascript
// ❌ 토큰 검증 미흡
const token = req.headers['authorization']?.split(' ')[1];

if (!token) {
  return res.status(401).json({ error: 'Token required' });
}

// 서명만 검증, 만료 시간은 검증 안 함
jwt.verify(token, process.env.SECRET); // 이미 jwt.verify가 만료를 확인함

// ❌ 토큰 저장 위치 불안전
localStorage.setItem('token', token); // XSS 공격에 취약

// ❌ 토큰 갱신 미흡
app.post('/api/auth/refresh', (req, res) => {
  const { refreshToken } = req.body;
  // 리프레시 토큰 검증 없음
  const newToken = jwt.sign({ userId: 1 }, SECRET, { expiresIn: '1h' });
  res.json({ token: newToken });
});
```

## 3단계: 범위 축소

JWT 문제의 유형:

1. **토큰 생성 오류**: 시크릿 키 오류, 옵션 설정 미흡
2. **토큰 검증 실패**: 서명 검증, 만료 확인 불충분
3. **토큰 저장 위치**: localStorage, sessionStorage, 쿠키 선택
4. **토큰 갱신**: 리프레시 토큰 없음, 갱신 로직 오류
5. **보안 문제**: XSS, CSRF, 토큰 노출

## 4단계: 증거 수집

```bash
# JWT 디코드 (서명 검증 없음)
npm install -g jwt-cli
jwt decode "eyJhbGc..."

# 토큰 내용 확인
echo "eyJhbGc..." | base64 -D | jq
```

```javascript
// JWT 검증 단계별 테스트
const jwt = require('jsonwebtoken');

const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
const secret = process.env.JWT_SECRET;

try {
  const decoded = jwt.verify(token, secret);
  console.log('Token valid:', decoded);
} catch (error) {
  console.log('Token invalid:');
  console.log('- Name:', error.name);
  console.log('- Message:', error.message);

  if (error.name === 'TokenExpiredError') {
    console.log('- Expired at:', error.expiredAt);
  }
}

// 서명 검증만 (만료 무시)
const decoded = jwt.decode(token);
console.log('Decoded (unverified):', decoded);
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 난도 |
|------|------|------|
| 잘못된 시크릿 키 | 매우높음 | 낮음 |
| 만료 시간 검증 누락 | 높음 | 낮음 |
| 토큰 저장 위치 부적절 | 높음 | 중간 |
| 리프레시 토큰 미구현 | 높음 | 중간 |
| 환경 변수 설정 오류 | 중간 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: JWT 생성 (권장)

```javascript
// authService.js
const jwt = require('jsonwebtoken');

class AuthService {
  // 액세스 토큰 생성 (수명 짧음)
  generateAccessToken(userId, email) {
    return jwt.sign(
      {
        userId,
        email,
        type: 'access'
      },
      process.env.JWT_SECRET,
      {
        expiresIn: '15m', // 15분
        algorithm: 'HS256',
        issuer: 'my-app',
        audience: 'my-app-users'
      }
    );
  }

  // 리프레시 토큰 생성 (수명 김)
  generateRefreshToken(userId) {
    return jwt.sign(
      {
        userId,
        type: 'refresh'
      },
      process.env.REFRESH_SECRET, // 다른 시크릿 키 사용
      {
        expiresIn: '7d', // 7일
        algorithm: 'HS256'
      }
    );
  }

  // 토큰 쌍 생성
  generateTokenPair(userId, email) {
    return {
      accessToken: this.generateAccessToken(userId, email),
      refreshToken: this.generateRefreshToken(userId),
      expiresIn: 15 * 60 // 초 단위
    };
  }

  // 토큰 검증
  verifyAccessToken(token) {
    try {
      return jwt.verify(token, process.env.JWT_SECRET, {
        issuer: 'my-app',
        audience: 'my-app-users'
      });
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        throw new Error('Token expired');
      }
      throw new Error('Invalid token');
    }
  }

  // 리프레시 토큰 검증
  verifyRefreshToken(token) {
    try {
      return jwt.verify(token, process.env.REFRESH_SECRET);
    } catch (error) {
      throw new Error('Invalid refresh token');
    }
  }
}

module.exports = new AuthService();
```

### 수정안 2: 토큰 저장 및 전송 (보안)

```javascript
// 옵션 1: HttpOnly 쿠키 (권장)
app.post('/api/auth/login', async (req, res) => {
  const user = await authenticate(req.body);
  const { accessToken, refreshToken } = generateTokenPair(user.id);

  // HttpOnly 쿠키에 저장 (자동 전송, XSS 보호)
  res.cookie('accessToken', accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 15 * 60 * 1000 // 15분
  });

  res.cookie('refreshToken', refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000 // 7일
  });

  res.json({ success: true });
});

// 클라이언트: fetch할 때 credentials 포함
fetch('/api/protected', {
  credentials: 'include' // 쿠키 자동 전송
});

// 옵션 2: Memory + SessionStorage (XSS 위험)
// 액세스 토큰은 메모리 변수에, 리프레시는 sessionStorage에
let accessToken = null;

async function login(credentials) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials)
  });

  const { accessToken: token, refreshToken } = await res.json();

  accessToken = token; // 메모리에 저장
  sessionStorage.setItem('refreshToken', refreshToken);
}

// 옵션 3: LocalStorage (최악의 선택, XSS 노출)
// ⚠️ 피해야 할 방식
localStorage.setItem('accessToken', token);
```

### 수정안 3: 서버 미들웨어

```javascript
// authMiddleware.js
const authService = require('./authService');

const authenticateToken = (req, res, next) => {
  // 1. 쿠키 또는 Authorization 헤더에서 토큰 추출
  const token = req.cookies.accessToken ||
                req.headers['authorization']?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Token required' });
  }

  // 2. 토큰 검증
  try {
    const payload = authService.verifyAccessToken(token);
    req.user = payload;
    next();
  } catch (error) {
    if (error.message === 'Token expired') {
      // 토큰 갱신 자동 시도 (선택사항)
      return res.status(401).json({
        error: 'Token expired',
        code: 'TOKEN_EXPIRED'
      });
    }

    return res.status(401).json({ error: 'Invalid token' });
  }
};

module.exports = authenticateToken;
```

### 수정안 4: 토큰 갱신

```javascript
// authRouter.js
const express = require('express');
const authService = require('./authService');

const router = express.Router();

router.post('/refresh', (req, res) => {
  // 1. 리프레시 토큰 추출
  const refreshToken = req.cookies.refreshToken || req.body.refreshToken;

  if (!refreshToken) {
    return res.status(401).json({ error: 'Refresh token required' });
  }

  // 2. 리프레시 토큰 검증
  try {
    const payload = authService.verifyRefreshToken(refreshToken);

    // 3. 데이터베이스에서 리프레시 토큰 확인 (옵션)
    // - 로그아웃 토큰 블랙리스트 확인
    // - 토큰 재사용 여부 확인

    // 4. 새 토큰 생성
    const user = await User.findById(payload.userId);
    const { accessToken, refreshToken: newRefreshToken } =
      authService.generateTokenPair(user.id, user.email);

    // 5. 새 쿠키 설정
    res.cookie('accessToken', accessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 15 * 60 * 1000
    });

    res.cookie('refreshToken', newRefreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000
    });

    res.json({ accessToken, expiresIn: 15 * 60 });
  } catch (error) {
    return res.status(401).json({ error: 'Invalid refresh token' });
  }
});

router.post('/logout', (req, res) => {
  res.clearCookie('accessToken');
  res.clearCookie('refreshToken');

  // (선택사항) 리프레시 토큰 블랙리스트 추가
  // tokenBlacklist.add(req.body.refreshToken);

  res.json({ success: true });
});

module.exports = router;
```

### 수정안 5: 클라이언트 토큰 갱신

```javascript
// authClient.js
class AuthClient {
  constructor() {
    this.accessToken = null;
  }

  async fetchWithRefresh(url, options = {}) {
    let response = await fetch(url, {
      ...options,
      credentials: 'include' // 쿠키 전송
    });

    // 토큰 만료 시 갱신 시도
    if (response.status === 401) {
      const refreshed = await this.refreshToken();

      if (!refreshed) {
        // 갱신 실패 - 로그인 페이지로
        window.location.href = '/login';
        return;
      }

      // 원래 요청 재시도
      response = await fetch(url, {
        ...options,
        credentials: 'include'
      });
    }

    return response;
  }

  async refreshToken() {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        return false;
      }

      const { accessToken } = await response.json();
      this.accessToken = accessToken;
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }

  async login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const { accessToken } = await response.json();
    this.accessToken = accessToken;
  }

  async logout() {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include'
    });

    this.accessToken = null;
    window.location.href = '/login';
  }
}

const authClient = new AuthClient();
```

## 7단계: 검증

```javascript
describe('JWT Token', () => {
  it('should create valid token', () => {
    const token = authService.generateAccessToken(1, 'user@test.com');
    expect(token).toBeDefined();

    const decoded = jwt.decode(token);
    expect(decoded.userId).toBe(1);
    expect(decoded.email).toBe('user@test.com');
  });

  it('should verify token with correct secret', () => {
    const token = authService.generateAccessToken(1, 'user@test.com');
    const decoded = authService.verifyAccessToken(token);

    expect(decoded.userId).toBe(1);
  });

  it('should reject token with wrong secret', () => {
    const token = jwt.sign({ userId: 1 }, 'wrong-secret');

    expect(() => {
      authService.verifyAccessToken(token);
    }).toThrow();
  });

  it('should reject expired token', (done) => {
    const token = jwt.sign({ userId: 1 }, process.env.JWT_SECRET, {
      expiresIn: '1ms'
    });

    setTimeout(() => {
      expect(() => {
        authService.verifyAccessToken(token);
      }).toThrow('Token expired');
      done();
    }, 10);
  });
});
```

## 8단계: 재발 방지

1. **환경 변수 설정**

```bash
# .env
JWT_SECRET=your-super-secret-key-min-32-chars
REFRESH_SECRET=your-refresh-secret-key-min-32-chars
```

2. **보안 체크리스트**
   - [ ] JWT_SECRET이 32자 이상인가?
   - [ ] 프로덕션에서 환경 변수로 관리하는가?
   - [ ] HttpOnly 쿠키 사용하는가?
   - [ ] 리프레시 토큰 만료 시간이 더 길다?
   - [ ] 토큰 갱신 끝점이 보호되어 있는가?

## 연결된 프롬프트 블록

- **PB-CL-08-jwt-structure**: JWT 구조 이해
- **PB-RP-07-token-generation**: 토큰 생성 테스트
- **PB-DG-08-token-decode**: 토큰 디코드 및 검증
- **PB-PA-08-token-refresh**: 토큰 갱신 로직
- **PB-VF-07-token-security**: 토큰 보안 검증
