---
id: F-04
title: CORS 오류 해결
pattern_id: P-04
error_ids: [E-10, E-11, E-12]
tech_scope: API, HTTP, 브라우저 보안
---

# CORS 오류 해결

교차 출처 요청이 거부되어 발생하는 CORS(Cross-Origin Resource Sharing) 오류를 해결합니다.

## 1단계: 증상 고정

브라우저 콘솔 오류:
- "Access to XMLHttpRequest at 'X' from origin 'Y' has been blocked by CORS policy"
- "The value of the 'Access-Control-Allow-Credentials' header in the response is ''"
- "Method not allowed by Access-Control-Allow-Methods"
- "Preflight request failed"

네트워크 탭:
- OPTIONS 요청이 실패함
- 응답 헤더에 Access-Control-* 헤더 누락

## 2단계: 재현

```javascript
// ❌ CORS 오류 발생
fetch('https://api.example.com/data')
  .then(res => res.json())
  .catch(err => console.error(err));

// 브라우저 콘솔 결과:
// Access to XMLHttpRequest at 'https://api.example.com/data'
// from origin 'http://localhost:3000' has been blocked by CORS policy
```

## 3단계: 범위 축소

CORS 오류의 유형:

1. **Simple Request 실패**: GET, HEAD, POST 중 하나인데도 실패
2. **Preflight 실패**: OPTIONS 요청이 거부됨
3. **자격증명 문제**: credentials이 포함되어 있음
4. **헤더 문제**: Custom 헤더 사용
5. **메서드 문제**: PUT, DELETE, PATCH 사용

## 4단계: 증거 수집

```bash
# 1. 요청이 어디에서 오는지 확인
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://api.example.com/data \
     -v

# 2. 응답 헤더 확인
curl https://api.example.com/data -v

# 3. 브라우저 DevTools Network 탭 확인
# - Request Headers: Origin, Access-Control-Request-Method 등
# - Response Headers: Access-Control-Allow-Origin 등
```

```javascript
// 요청 세부정보 로깅
fetch('https://api.example.com/data')
  .then(res => {
    console.log('Response headers:');
    console.log('Access-Control-Allow-Origin:', res.headers.get('Access-Control-Allow-Origin'));
    console.log('Access-Control-Allow-Credentials:', res.headers.get('Access-Control-Allow-Credentials'));
    return res.json();
  })
  .catch(err => {
    console.error('CORS Error:', err);
  });
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 해결 난도 |
|------|------|---------|
| 서버 CORS 헤더 누락 | 매우높음 | 높음 |
| 도메인 화이트리스트 오류 | 높음 | 중간 |
| Preflight OPTIONS 거부 | 높음 | 중간 |
| 자격증명 설정 오류 | 중간 | 낮음 |
| 요청 헤더 문제 | 중간 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 서버 CORS 설정 (Express)

```javascript
// server.js
const cors = require('cors');
const express = require('express');

const app = express();

// 1. 모든 출처 허용 (개발 환경용, 프로덕션에서는 사용 금지)
app.use(cors());

// 2. 특정 출처만 허용 (권장)
const corsOptions = {
  origin: [
    'http://localhost:3000',
    'https://myapp.com'
  ],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  credentials: true,
  allowedHeaders: ['Content-Type', 'Authorization'],
  maxAge: 86400 // preflight 캐시 시간 (초)
};

app.use(cors(corsOptions));

// 3. 특정 경로에만 CORS 적용
app.get('/api/public', cors(), (req, res) => {
  res.json({ message: 'public' });
});

// 4. 환경변수로 출처 관리
const allowedOrigins = process.env.ALLOWED_ORIGINS.split(',');

const corsOptions = {
  origin: (origin, callback) => {
    if (allowedOrigins.includes(origin) || !origin) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true
};

app.use(cors(corsOptions));
```

### 수정안 2: 서버 CORS 설정 (NestJS)

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // CORS 설정
  app.enableCors({
    origin: [
      'http://localhost:3000',
      'https://myapp.com'
    ],
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    credentials: true,
    allowedHeaders: ['Content-Type', 'Authorization'],
    maxAge: 86400
  });

  await app.listen(3001);
}

bootstrap();

// 또는 환경변수 사용
app.enableCors({
  origin: process.env.CORS_ORIGIN?.split(','),
  credentials: true
});
```

### 수정안 3: 클라이언트 요청 설정

```javascript
// ✅ 자격증명이 필요한 경우
fetch('https://api.example.com/data', {
  method: 'GET',
  credentials: 'include', // 쿠키 포함
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer token'
  }
})
  .then(res => res.json())
  .catch(err => console.error('CORS Error:', err));

// axios 사용
import axios from 'axios';

axios.get('https://api.example.com/data', {
  withCredentials: true, // 쿠키 포함
  headers: {
    'Authorization': 'Bearer token'
  }
});
```

### 수정안 4: Next.js 환경에서 프록시 사용

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: 'https://external-api.com/:path*'
        }
      ]
    };
  }
};

// 클라이언트 코드
fetch('/api/data') // 로컬 /api로 요청 -> 프록시가 외부 API로 전달
  .then(res => res.json());
```

### 수정안 5: 백엔드 프록시 (권장)

```javascript
// server/routes/api.js
const express = require('express');
const axios = require('axios');
const router = express.Router();

// 클라이언트 -> 우리 서버 -> 외부 API
router.get('/data', async (req, res) => {
  try {
    const response = await axios.get('https://external-api.com/data', {
      headers: {
        'Authorization': 'Bearer ' + process.env.EXTERNAL_API_KEY
      }
    });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;

// app.js
app.use('/api', require('./routes/api'));
```

### 수정안 6: 수동 CORS 헤더 설정

```javascript
// Express 미들웨어
app.use((req, res, next) => {
  const origin = req.get('origin');
  const allowedOrigins = ['http://localhost:3000', 'https://myapp.com'];

  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader(
      'Access-Control-Allow-Methods',
      'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    );
    res.setHeader(
      'Access-Control-Allow-Headers',
      'Content-Type, Authorization'
    );
    res.setHeader('Access-Control-Max-Age', '86400');
  }

  // Preflight OPTIONS 요청 처리
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});
```

## 7단계: 검증

```javascript
// CORS 검증 테스트
describe('CORS', () => {
  it('should allow requests from allowed origins', async () => {
    const response = await fetch('http://localhost:3001/api/data', {
      headers: {
        'Origin': 'http://localhost:3000'
      }
    });

    expect(response.headers.get('Access-Control-Allow-Origin')).toBe(
      'http://localhost:3000'
    );
  });

  it('should block requests from unauthorized origins', async () => {
    const response = await fetch('http://localhost:3001/api/data', {
      headers: {
        'Origin': 'http://evil.com'
      }
    });

    expect(response.headers.get('Access-Control-Allow-Origin')).toBeFalsy();
  });
});
```

## 8단계: 재발 방지

1. **환경별 설정**

```javascript
// .env.local
NEXT_PUBLIC_API_URL=http://localhost:3001
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

// .env.production
NEXT_PUBLIC_API_URL=https://api.myapp.com
CORS_ALLOWED_ORIGINS=https://myapp.com
```

2. **보안 체크리스트**
   - [ ] 프로덕션에서 `*` 출처 허용하지 않음
   - [ ] 신뢰할 수 있는 도메인만 화이트리스트 추가
   - [ ] 자격증명 옵션 명확히 설정
   - [ ] 허용 메서드 최소화

3. **모니터링**

```javascript
// 경고 로그
if (origin && !allowedOrigins.includes(origin)) {
  console.warn(`CORS blocked: ${origin}`);
}
```

## 연결된 프롬프트 블록

- **PB-CL-05-http-headers**: HTTP 헤더 이해
- **PB-RP-04-cors-requests**: CORS 요청 재현
- **PB-DG-05-network-trace**: 네트워크 추적
- **PB-PA-05-cors-config**: CORS 설정 구현
- **PB-VF-04-cors-test**: CORS 검증
