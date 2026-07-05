---
id: E-RT-02
title: CORS 프리플라이트 실패
error_class: Runtime
symptoms:
  - 브라우저 요청 실패
  - OPTIONS 요청 거부
  - Access-Control 헤더 누락
exact_messages:
  - "Access to XMLHttpRequest has been blocked by CORS policy"
  - "Response to preflight request doesn't pass access control check"
  - "The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard"
tech_tags:
  - CORS
  - HTTP
  - Security
  - API
linked_patterns: []
linked_flows: []
---

# CORS 프리플라이트 실패

## 증상
브라우저가 cross-origin 요청 전에 OPTIONS preflight 요청을 보내는데 실패합니다. 서버가 CORS 헤더를 올바르게 반환하지 않으면 실제 요청이 차단됩니다.

## 정확한 에러 메시지
```
Access to XMLHttpRequest at 'http://api.example.com/data' from origin 'http://localhost:3000' has been blocked by CORS policy
Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource
The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'
```

## 발생 맥락
```typescript
// 클라이언트 코드
// http://localhost:3000에서 http://api.example.com 요청
const response = await fetch('http://api.example.com/api/data', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ data: 'test' })
});

// 브라우저가 자동으로 OPTIONS 요청 전송
// OPTIONS http://api.example.com/api/data

// 서버가 CORS 헤더 없이 응답
// ❌ Access-Control-Allow-Origin 헤더 없음
```

## 필요한 증거
- 브라우저 네트워크 탭 (OPTIONS 요청 확인)
- CORS 에러 메시지
- 서버의 Access-Control 헤더
- 요청 헤더 (Origin, Content-Type 등)

## 의심 원인
1. 서버에서 CORS 헤더 미설정
2. Access-Control-Allow-Origin이 요청 origin과 일치하지 않음
3. Access-Control-Allow-Methods가 요청 메서드를 허용하지 않음
4. Access-Control-Allow-Headers가 요청 헤더를 허용하지 않음
5. credentials: 'include'일 때 wildcard '*' 사용
6. 프리플라이트 요청이 401/403으로 응답

## 빠른 해결법

### 1. Express에서 CORS 설정
```typescript
import cors from 'cors';
import express from 'express';

const app = express();

// 기본 CORS 활성화
app.use(cors());

// 또는 세부 설정
app.use(cors({
  origin: 'http://localhost:3000',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  maxAge: 3600  // preflight 캐시 1시간
}));

// 또는 특정 경로만
app.get('/api/data', cors(), (req, res) => {
  res.json({ data: 'test' });
});
```

### 2. 수동으로 CORS 헤더 설정
```typescript
app.use((req, res, next) => {
  const origin = req.headers.origin;
  const allowedOrigins = ['http://localhost:3000', 'https://example.com'];

  if (allowedOrigins.includes(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
  }

  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.header('Access-Control-Allow-Credentials', 'true');
  res.header('Access-Control-Max-Age', '3600');

  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }

  next();
});
```

### 3. Next.js API Routes
```typescript
// pages/api/data.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  // CORS 헤더 설정
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // OPTIONS 요청 처리
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  res.status(200).json({ data: 'test' });
}
```

### 4. 클라이언트에서 credentials 사용
```typescript
// credentials: 'include'일 때는 origin이 '*'이면 안됨
const response = await fetch('http://api.example.com/api/data', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include',  // 쿠키 포함
  body: JSON.stringify({ data: 'test' })
});
```

### 5. Proxy 사용 (개발 환경)
```json
// next.config.js
module.exports = {
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: 'http://api.example.com/api/:path*'
        }
      ]
    };
  }
};
```

### 6. Node.js/Express CORS 미들웨어
```typescript
const cors = require('cors');

const whitelist = ['http://localhost:3000', 'https://example.com'];

const corsOptions = {
  origin: function (origin, callback) {
    if (whitelist.indexOf(origin) !== -1 || !origin) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true
};

app.use(cors(corsOptions));
```

### 7. Nginx에서 CORS 설정
```nginx
server {
  listen 80;
  server_name api.example.com;

  location /api {
    # 요청 origin 확인
    if ($http_origin ~ ^(http://localhost:3000|https://example.com)$) {
      add_header 'Access-Control-Allow-Origin' $http_origin always;
    }

    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
    add_header 'Access-Control-Max-Age' '3600' always;

    if ($request_method = 'OPTIONS') {
      return 204;
    }

    proxy_pass http://backend;
  }
}
```

### 8. 클라이언트에서 에러 처리
```typescript
fetch('http://api.example.com/data')
  .catch(error => {
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      console.error('CORS 에러 또는 네트워크 에러');
    }
  });

// 또는
try {
  const response = await fetch('http://api.example.com/data');
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
} catch (error) {
  console.error('요청 실패:', error);
}
```

## 연결된 패턴
- E-SP-02-auth-header-missing
- E-DO-10-missing-instrumentation

## 연결된 플로우
- API 통신 플로우
- 보안 설정 플로우

## 재발 방지
1. 개발 초기에 CORS 정책 명확히 정의
2. 프로덕션에서는 구체적인 origin 명시 (wildcard 지양)
3. credentials 사용 시 명확한 origin 목록 유지
4. 모든 OPTIONS 요청 처리 로직 추가
5. CORS 설정 문서화
6. 테스트 시 모든 HTTP 메서드 확인
