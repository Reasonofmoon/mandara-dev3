---
id: F-16
title: Docker 빌드 실패 해결
pattern_id: P-16
error_ids: [E-46, E-47, E-48]
tech_scope: Docker, 컨테이너화, 빌드 최적화
---

# Docker 빌드 실패 해결

Docker 이미지 빌드 실패 문제를 진단하고 해결합니다.

## 1단계: 증상 고정

오류 메시지:
- "COPY failed: stat /app/build: no such file or directory"
- "RUN npm install failed"
- "base image not found"
- "disk space full"
- "build timed out"

## 2단계: 재현

```bash
docker build -t myapp .

# 실패 출력 예:
# Step 5/10 : COPY build/ /app/build/
# COPY failed: stat ./build: no such file or directory
```

## 3단계: 범위 축소

Docker 빌드 실패 유형:

1. **파일 누락**: COPY 대상 파일 없음
2. **의존성 설치 실패**: npm/pip install 오류
3. **베이스 이미지 문제**: 잘못된 이미지 또는 네트워크 오류
4. **빌드 컨텍스트**: .dockerignore 오류
5. **디스크 공간**: 이미지 크기 초과

## 4단계: 증거 수집

```bash
# 빌드 로그 확인
docker build -t myapp . 2>&1 | tee build.log

# Dockerfile 검증
docker run --rm -i hadolint/hadolint < Dockerfile

# 빌드 컨텍스트 확인
ls -la
cat .dockerignore
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 파일 경로 오류 | 매우높음 | 낮음 |
| 의존성 버전 문제 | 높음 | 중간 |
| 네트워크 오류 | 높음 | 중간 |
| 권한 문제 | 중간 | 낮음 |
| 디스크 공간 | 낮음 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 최적화된 Dockerfile

```dockerfile
# ❌ 비효율적 Dockerfile
FROM node:18
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]

# ✅ 최적화된 Dockerfile (멀티 스테이지)
FROM node:18-alpine AS builder

WORKDIR /app

# 의존성 파일 먼저 복사 (캐싱 활용)
COPY package*.json ./
RUN npm ci --only=production

# 빌드 단계
COPY . .
RUN npm ci --include=dev
RUN npm run build

# 최종 이미지 (불필요한 파일 제외)
FROM node:18-alpine

WORKDIR /app

# builder에서만 필요한 파일 복사
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

EXPOSE 3000

# 보안: non-root 사용자
USER node

CMD ["node", "dist/index.js"]
```

### 수정안 2: .dockerignore 설정

```dockerignore
# .dockerignore
node_modules
npm-debug.log
.git
.gitignore
.env
.env.local
.DS_Store
.vscode
.idea
dist
build
coverage
*.log
.npm
.eslintcache
```

### 수정안 3: 환경별 Dockerfile

```dockerfile
# Dockerfile.dev (개발 환경)
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

```dockerfile
# Dockerfile.prod (프로덕션)
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY . .
RUN npm ci --include=dev
RUN npm run build

FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

USER node

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### 수정안 4: 빌드 인자 및 ARG

```dockerfile
ARG NODE_VERSION=18
ARG ENVIRONMENT=production

FROM node:${NODE_VERSION}-alpine AS builder

ARG ENVIRONMENT

WORKDIR /app

COPY package*.json ./

RUN if [ "$ENVIRONMENT" = "production" ]; then \
      npm ci --only=production; \
    else \
      npm ci; \
    fi

COPY . .

RUN if [ "$ENVIRONMENT" = "production" ]; then \
      npm run build; \
    fi

EXPOSE 3000

CMD ["npm", "start"]
```

```bash
# 빌드 시 인자 전달
docker build \
  --build-arg NODE_VERSION=20 \
  --build-arg ENVIRONMENT=production \
  -t myapp .
```

### 수정안 5: 빌드 캐시 활용

```dockerfile
# 캐시 활용을 위해 의존성 먼저 설치
FROM node:18-alpine

WORKDIR /app

# 이 단계는 package.json이 변경되지 않으면 캐시됨
COPY package*.json ./
RUN npm ci

# 이 단계는 파일이 변경될 때마다 실행
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

```bash
# 캐시 무시하고 빌드
docker build --no-cache -t myapp .
```

### 수정안 6: 헬스체크 추가

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node healthcheck.js || exit 1

CMD ["npm", "start"]
```

```javascript
// healthcheck.js
const http = require('http');

http.get('http://localhost:3000/health', (res) => {
  if (res.statusCode === 200) {
    process.exit(0);
  }
  process.exit(1);
}).on('error', () => {
  process.exit(1);
});

setTimeout(() => {
  process.exit(1);
}, 3000);
```

## 7단계: 검증

```bash
# 빌드 성공 확인
docker build -t myapp . && echo "Build successful"

# 이미지 크기 확인
docker images myapp

# 컨테이너 실행 테스트
docker run --rm myapp npm --version

# 헬스체크 테스트
docker run -d myapp
docker ps # STATUS 컬럼에서 "healthy" 확인
```

## 8단계: 재발 방지

1. **CI/CD 통합**

```yaml
# .github/workflows/docker.yml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Build Docker image
        run: docker build -t myapp .

      - name: Test Docker image
        run: docker run --rm myapp npm test
```

2. **이미지 스캔**

```bash
# 보안 취약점 스캔
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image myapp
```

## 연결된 프롬프트 블록

- **PB-CL-17-dockerfile**: Dockerfile 작성법
- **PB-RP-16-docker-test**: Docker 테스트
- **PB-DG-17-build-logs**: 빌드 로그 분석
- **PB-PA-17-optimization**: 이미지 최적화
- **PB-VF-16-image-verify**: 이미지 검증
