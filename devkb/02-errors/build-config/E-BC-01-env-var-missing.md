---
id: E-BC-01
title: 환경 변수 누락
error_class: Build-Config
symptoms:
  - 설정 값이 undefined
  - 런타임 에러
  - 기능이 작동하지 않음
exact_messages:
  - "Cannot read property of undefined"
  - "DATABASE_URL is not defined"
  - "Configuration error: missing NEXT_PUBLIC_API_URL"
tech_tags:
  - Environment
  - Configuration
  - Build
  - Deployment
linked_patterns: []
linked_flows: []
---

# 환경 변수 누락

## 증상
애플리케이션에 필요한 환경 변수가 정의되지 않으면 설정 값이 undefined가 되어 오류가 발생합니다. 로컬에서는 작동하지만 배포 환경에서 실패할 수 있습니다.

## 정확한 에러 메시지
```
Cannot read property 'DATABASE_URL' of undefined
process.env.API_URL is undefined
Error: Missing required environment variable: GITHUB_TOKEN
Configuration error: DATABASE_URL not found in environment
```

## 발생 맥락
```typescript
// 잘못된 예 1: 환경 변수 직접 사용
const databaseUrl = process.env.DATABASE_URL;
const connection = createConnection(databaseUrl);  // ❌ undefined일 수 있음

// 잘못된 예 2: 선택적 체크 없이 접근
const apiKey = process.env.API_KEY;
const response = await fetch(`${apiKey}/endpoint`);  // ❌ 에러

// 잘못된 예 3: 빌드 시간에 필요한 변수 누락
// .env 파일 없음
// NEXT_PUBLIC_API_URL 정의 안됨
const API_URL = process.env.NEXT_PUBLIC_API_URL;
```

## 필요한 증거
- 에러 메시지
- 필요한 환경 변수 목록
- .env 파일 상태
- 배포 환경 설정

## 의심 원인
1. .env 파일이 없음
2. .env 파일에 변수 정의 안 됨
3. 배포 플랫폼에 환경 변수 설정 안 됨
4. 변수명 오타
5. 로컬/개발/프로덕션 환경 설정 불일치
6. .gitignore에 의해 .env 파일 제외됨

## 빠른 해결법

### 1. .env 파일 생성 및 설정
```bash
# .env.local (로컬 개발)
DATABASE_URL="postgresql://user:pass@localhost:5432/db"
API_KEY="your-api-key"
NEXT_PUBLIC_API_URL="http://localhost:3000"

# .env.production (프로덕션)
DATABASE_URL="postgresql://prod-user:prod-pass@prod-host:5432/prod-db"
API_KEY="prod-api-key"
NEXT_PUBLIC_API_URL="https://api.example.com"
```

### 2. 환경 변수 검증 함수 작성
```typescript
// lib/env.ts
function getEnvVar(name: string, defaultValue?: string): string {
  const value = process.env[name];

  if (!value && !defaultValue) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value || defaultValue || '';
}

// 사용
const DATABASE_URL = getEnvVar('DATABASE_URL');
const API_KEY = getEnvVar('API_KEY', 'default-key');

export { DATABASE_URL, API_KEY };
```

### 3. Zod로 환경 변수 검증
```typescript
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  API_KEY: z.string().min(1),
  NEXT_PUBLIC_API_URL: z.string().url(),
  NODE_ENV: z.enum(['development', 'production']).default('development')
});

const env = envSchema.parse(process.env);

export { env };
```

### 4. 빌드 시간 검증
```typescript
// next.config.js
module.exports = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
  },
  webpack: (config, { isServer }) => {
    if (isServer) {
      const required = ['DATABASE_URL', 'API_KEY'];
      const missing = required.filter(name => !process.env[name]);

      if (missing.length > 0) {
        throw new Error(`Missing environment variables: ${missing.join(', ')}`);
      }
    }
    return config;
  }
};
```

### 5. Docker 환경 변수 설정
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY . .

# 빌드 시간에 필요한 변수
ARG NEXT_PUBLIC_API_URL
ARG DATABASE_URL
ARG API_KEY

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV DATABASE_URL=$DATABASE_URL
ENV API_KEY=$API_KEY

RUN npm install && npm run build

CMD ["npm", "start"]
```

```bash
# docker-compose.yml
services:
  app:
    build:
      context: .
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
        DATABASE_URL: ${DATABASE_URL}
        API_KEY: ${API_KEY}
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
      DATABASE_URL: ${DATABASE_URL}
      API_KEY: ${API_KEY}
```

### 6. 안전한 환경 변수 접근
```typescript
// 옵셔널 체이닝과 널 병합
const databaseUrl = process.env.DATABASE_URL ?? 'sqlite://:memory:';
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3000';

// 또는 타입 안전
const config = {
  database: process.env.DATABASE_URL,
  apiKey: process.env.API_KEY,
  apiUrl: process.env.NEXT_PUBLIC_API_URL
} as const;

if (!config.database) {
  throw new Error('DATABASE_URL must be defined');
}
```

## 연결된 패턴
- E-BC-06-tsconfig-mismatch
- E-DO-06-secret-rotation-failure

## 연결된 플로우
- 배포 환경 설정 플로우
- CI/CD 파이프라인 구성 플로우

## 재발 방지
1. 프로젝트 시작할 때 .env.example 생성
2. 필수 환경 변수를 문서화
3. 빌드 시간에 검증 함수 실행
4. 배포 체크리스트에 환경 변수 확인 항목 추가
5. 각 환경(로컬/dev/prod)별 .env 파일 관리
6. CI/CD에서 자동으로 환경 변수 검증
