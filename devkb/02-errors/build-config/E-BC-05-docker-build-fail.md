---
id: E-BC-05
title: Docker 빌드 실패
error_class: Build-Config
symptoms:
  - 도커 이미지 빌드 실패
  - 빌드 시간 오래 걸림
  - 레이어 캐시 미스
exact_messages:
  - "failed to build: executor failed running [RUN npm install]"
  - "no space left on device"
  - "COPY failed: file not found"
tech_tags:
  - Docker
  - Containerization
  - Build Process
  - DevOps
linked_patterns: []
linked_flows: []
---

# Docker 빌드 실패

## 증상
Docker 이미지 빌드 중에 명령 실행 실패, 파일 찾기 실패, 또는 공간 부족 등의 문제가 발생합니다. 베이스 이미지, 의존성, 또는 Dockerfile 작성 오류가 원인입니다.

## 정확한 에러 메시지
```
failed to build: executor failed running [RUN npm install]: exit code 1
COPY failed: file not found in build context
no space left on device
The command 'RUN npm install' returned a non-zero code: 127
```

## 발생 맥락
```dockerfile
# 잘못된 예 1: npm install 실패
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install  # ❌ 캐시 누락으로 느림

COPY . .

RUN npm run build
RUN npm prune --production

CMD ["npm", "start"]

# 잘못된 예 2: 파일 복사 오류
COPY ./src ./src  # ❌ src 디렉토리가 없을 수 있음

# 잘못된 예 3: 베이스 이미지 문제
FROM node:18  # ❌ 크기가 큼 (900MB)

# 잘못된 예 4: .dockerignore 누락
# node_modules, .git 등이 포함되어 빌드 느림
```

## 필요한 증거
- Dockerfile 내용
- 빌드 에러 메시지 및 라인 번호
- .dockerignore 파일
- 도커 버전

## 의심 원인
1. Dockerfile 문법 오류
2. COPY 또는 ADD 명령에서 파일 찾기 실패
3. RUN 명령 실패 (npm install 등)
4. 베이스 이미지 부적절
5. .dockerignore 미설정
6. 디스크 공간 부족
7. 레이어 캐시 미스로 인한 느린 빌드

## 빠른 해결법

### 1. 최적화된 Dockerfile (다단계 빌드)
```dockerfile
# 빌드 단계
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci --only=production && npm cache clean --force

COPY . .

RUN npm run build

# 런타임 단계
FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "start"]
```

### 2. .dockerignore 파일
```
node_modules
npm-debug.log
.git
.gitignore
.env.local
.next
.DS_Store
dist
build
```

### 3. 캐시 최적화
```dockerfile
FROM node:18-alpine

WORKDIR /app

# 의존성을 별도 레이어로 (캐시 활용)
COPY package*.json ./
RUN npm ci --only=production

# 소스 코드 복사 (변경 빈번)
COPY . .

RUN npm run build

CMD ["npm", "start"]
```

### 4. 빌드 argument와 환경 변수
```dockerfile
FROM node:18-alpine

ARG NODE_ENV=production
ENV NODE_ENV=$NODE_ENV

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

CMD ["npm", "start"]
```

```bash
docker build \
  --build-arg NODE_ENV=production \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com \
  -t my-app:latest .
```

### 5. 작은 베이스 이미지 사용
```dockerfile
# ❌ 900MB
FROM node:18

# ✅ 150MB (Alpine)
FROM node:18-alpine

# ✅ 170MB (Debian slim)
FROM node:18-slim

# ✅ 최소 크기 (프로덕션만 배포)
FROM alpine:3.18
RUN apk add --no-cache nodejs npm
```

### 6. 권장 사항
```dockerfile
FROM node:18-alpine

WORKDIR /app

# 사용자 추가 (보안)
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# 의존성 설치
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# 소스 복사
COPY --chown=nextjs:nodejs . .

# 빌드
RUN npm run build

USER nextjs

EXPOSE 3000

CMD ["npm", "start"]
```

### 7. 빌드 최적화 옵션
```bash
# 캐시 무시
docker build --no-cache -t my-app:latest .

# 빌드 컨텍스트 축소
docker build --exclude=node_modules --exclude=.git -t my-app:latest .

# 빌드 진행 상황 확인
docker build --progress=plain -t my-app:latest .

# 빌드 시간 측정
time docker build -t my-app:latest .
```

### 8. Docker Compose로 빌드
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        NODE_ENV: production
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
    restart: unless-stopped
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-PF-11-image-bloat

## 연결된 플로우
- 도커 이미지 빌드 최적화 플로우
- CI/CD 배포 플로우

## 재발 방지
1. 다단계 빌드로 최종 이미지 크기 축소
2. .dockerignore로 불필요한 파일 제외
3. Alpine 베이스 이미지 사용
4. 레이어 캐시 활용으로 빌드 속도 향상
5. 정기적으로 npm audit 실행
6. 프로덕션 의존성만 설치 (--only=production)
7. 비루트 사용자로 실행
