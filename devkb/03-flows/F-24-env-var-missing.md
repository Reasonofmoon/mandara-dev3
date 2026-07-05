---
id: F-24
title: 환경 변수 문제 해결
pattern_id: P-24
error_ids: [E-70, E-71, E-72]
tech_scope: 환경 설정, .env, 배포 구성
---

# 환경 변수 문제 해결

환경 변수 누락, 오류로 인한 애플리케이션 문제를 해결합니다.

## 1단계: 증상 고정

- "Cannot find module or its corresponding type declarations"
- 설정값이 undefined
- 프로덕션에서만 실패
- "DATABASE_URL is not defined"
- 포트 번호 오류

## 6단계: 수정안 선택

### 수정안 1: 환경 변수 검증

```javascript
// config.js
function getEnvVar(name, defaultValue = null) {
  const value = process.env[name];

  if (!value && defaultValue === null) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value || defaultValue;
}

// 필수 환경 변수 검증
const config = {
  port: getEnvVar('PORT', 3000),
  databaseUrl: getEnvVar('DATABASE_URL'),
  nodeEnv: getEnvVar('NODE_ENV', 'development'),
  apiKey: getEnvVar('API_KEY'),
  logLevel: getEnvVar('LOG_LEVEL', 'info')
};

export default config;
```

### 수정안 2: .env 파일 관리

```bash
# .env (로컬 개발)
PORT=3000
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
NODE_ENV=development
API_KEY=dev-key-123

# .env.production (프로덕션)
PORT=3000
DATABASE_URL=postgresql://user:pass@prod-db:5432/mydb
NODE_ENV=production
API_KEY=prod-key-456

# .env.test (테스트)
PORT=3001
DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
NODE_ENV=test
API_KEY=test-key-789
```

```javascript
// .env 파일 로드
import dotenv from 'dotenv';

dotenv.config({
  path: `.env.${process.env.NODE_ENV || 'development'}`
});

// 또는 환경별 로드
const envFile = process.env.NODE_ENV === 'production'
  ? '.env.production'
  : '.env.development';

dotenv.config({ path: envFile });
```

### 수정안 3: TypeScript로 환경 변수 타입 안정성

```typescript
// env.ts
import { z } from 'zod';

const envSchema = z.object({
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  API_KEY: z.string(),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info')
});

type Environment = z.infer<typeof envSchema>;

export const env: Environment = envSchema.parse(process.env);

// 사용
console.log(env.PORT); // 타입 안전
console.log(env.DATABASE_URL);
```

### 수정안 4: Docker 환경 변수

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# 기본값 설정
ENV PORT=3000
ENV NODE_ENV=production
ENV LOG_LEVEL=info

EXPOSE ${PORT}

CMD ["node", "index.js"]
```

```bash
# docker run 시 환경 변수 전달
docker run -e DATABASE_URL="postgresql://..." \
           -e API_KEY="key" \
           myapp:latest

# 또는 env 파일 사용
docker run --env-file .env.production myapp:latest
```

### 수정안 5: Kubernetes 환경 변수

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest

        # 환경 변수 직접 설정
        env:
        - name: PORT
          value: "3000"
        - name: NODE_ENV
          value: "production"

        # ConfigMap에서 로드
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log-level

        # Secret에서 로드 (민감한 정보)
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: database-url
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: api-key

        # Pod 이름을 환경 변수로
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name

        # Namespace를 환경 변수로
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace

---

# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  log-level: "info"
  feature-flag: "enabled"

---

# Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  database-url: "postgresql://user:pass@db:5432/mydb"
  api-key: "secret-key-123"
```

### 수정안 6: 환경 변수 검증 스크립트

```bash
#!/bin/bash
# validate-env.sh

REQUIRED_VARS=(
  "DATABASE_URL"
  "API_KEY"
  "JWT_SECRET"
  "PORT"
)

echo "Validating environment variables..."

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing required variable: $var"
    exit 1
  fi
  echo "✓ $var is set"
done

# 검증 로직
if [ ${#API_KEY} -lt 32 ]; then
  echo "❌ API_KEY is too short (minimum 32 characters)"
  exit 1
fi

echo "✓ All validations passed"
```

```json
// package.json
{
  "scripts": {
    "validate-env": "bash validate-env.sh",
    "start": "npm run validate-env && node index.js"
  }
}
```

## 연결된 프롬프트 블록

- **PB-CL-25-env-config**: 환경 변수 설정
- **PB-RP-24-env-test**: 환경 변수 테스트
- **PB-DG-25-env-audit**: 환경 변수 감사
- **PB-PA-25-env-setup**: 환경 변수 구성
- **PB-VF-24-env-verify**: 환경 변수 검증
