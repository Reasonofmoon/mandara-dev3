---
id: E-BC-10
title: 포트 충돌
error_class: Build-Config
symptoms:
  - 개발 서버 시작 실패
  - 포트가 이미 사용 중
  - 프로세스 충돌
exact_messages:
  - "Error: listen EADDRINUSE: address already in use :::3000"
  - "Port 3000 is already in use"
  - "Error: bind: address already in use"
tech_tags:
  - Networking
  - Development Server
  - Port Management
  - Process Management
linked_patterns: []
linked_flows: []
---

# 포트 충돌

## 증상
개발 서버를 시작할 때 요청한 포트가 이미 사용 중이어서 서버를 시작할 수 없습니다. 포트 3000, 8080, 5432 등이 자주 충돌합니다.

## 정확한 에러 메시지
```
Error: listen EADDRINUSE: address already in use :::3000
Port 3000 is already in use. Try:
  lsof -ti :3000 | xargs kill -9
Error: bind: address already in use
Address already in use (OS error 48)
```

## 발생 맥락
```bash
# 포트 3000 사용 중인 상태에서
npm run dev
# ❌ Error: listen EADDRINUSE: address already in use :::3000

# 이전 프로세스가 종료되지 않음
npm start  # 첫 번째 실행
npm start  # 두 번째 시도 - 포트 이미 사용 중
```

## 필요한 증거
- 에러 메시지와 포트 번호
- 현재 포트 사용 상황
- 실행 중인 프로세스 목록

## 의심 원인
1. 같은 포트로 실행 중인 다른 프로세스
2. 이전 개발 서버 프로세스가 여전히 실행 중
3. 다른 애플리케이션이 포트 사용
4. 포트가 TIME_WAIT 상태
5. 권한 부족 (1024 이하 포트)

## 빠른 해결법

### 1. 포트 사용 확인 및 프로세스 종료 (Linux/Mac)
```bash
# 포트 사용 프로세스 확인
lsof -i :3000

# 프로세스 강제 종료
lsof -ti :3000 | xargs kill -9

# 또는 직접 PID로 종료
kill -9 12345
```

### 2. 포트 사용 확인 (Windows)
```bash
# 포트 사용 프로세스 확인
netstat -ano | findstr :3000

# 또는
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess

# 프로세스 종료
taskkill /PID 12345 /F
```

### 3. 다른 포트 사용
```bash
# 명령줄에서 포트 지정
npm run dev -- --port 3001

# 또는 PORT 환경 변수
PORT=3001 npm run dev
```

### 4. package.json에서 포트 설정
```json
{
  "scripts": {
    "dev": "next dev -p 3001",
    "dev-alt": "PORT=3001 next dev"
  }
}
```

### 5. Next.js에서 포트 동적 할당
```javascript
// next.config.js
module.exports = {
  serverRuntimeConfig: {
    port: process.env.PORT || 3000
  }
};
```

```javascript
// server.js
const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');

const port = parseInt(process.env.PORT || '3000', 10);
const hostname = 'localhost';
const app = next({ dev: true });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  }).listen(port, (err) => {
    if (err) throw err;
    console.log(`Ready on http://${hostname}:${port}`);
  });
});
```

### 6. 모든 Node 프로세스 확인
```bash
# 모든 Node 프로세스 확인
ps aux | grep node

# 모든 Node 프로세스 종료 (위험!)
pkill -f node
```

### 7. 포트 여러 개 시도
```bash
# Bash 스크립트
#!/bin/bash
PORT=3000
while netstat -an | grep -q ":$PORT "; do
  PORT=$((PORT + 1))
done
echo "Using port $PORT"
PORT=$PORT npm run dev
```

### 8. 개발 서버 설정 (Vite)
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: false,  // 포트 충돌 시 다른 포트 자동 사용
    host: 'localhost'
  }
});
```

### 9. Docker 포트 매핑
```bash
# 호스트 포트 3001을 컨테이너 포트 3000으로 매핑
docker run -p 3001:3000 my-app
```

```yaml
# docker-compose.yml
services:
  app:
    ports:
      - "3001:3000"
    environment:
      PORT: 3000
```

### 10. 시스템 포트 범위 확인
```bash
# Mac/Linux: 사용 가능한 포트 확인
netstat -tuln | grep LISTEN

# 일반적인 포트 범위
# 0-1023: 시스템 포트 (권한 필요)
# 1024-49151: 사용자 포트
# 49152-65535: 동적 포트
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-DO-13-oom-killed

## 연결된 플로우
- 개발 환경 설정 플로우
- 프로세스 관리 플로우

## 재발 방지
1. Vite에서 strictPort: false 설정
2. 개발 스크립트에 동적 포트 할당
3. Ctrl+C로 정상 종료 습관화
4. 정기적으로 불필요한 프로세스 확인
5. 서로 다른 프로젝트에 다른 포트 할당
6. PM2 등 프로세스 관리자 사용
7. CI/CD에서 포트 충돌 방지 로직 추가
