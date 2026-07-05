---
id: F-18
title: 헬스체크 실패 해결
pattern_id: P-18
error_ids: [E-52, E-53, E-54]
tech_scope: 헬스체크, 모니터링, 가용성
---

# 헬스체크 실패 해결

Kubernetes 헬스체크 및 애플리케이션 가용성 문제를 해결합니다.

## 1단계: 증상 고정

- Pod이 CrashLoopBackOff 상태
- "Liveness probe failed"
- "Readiness probe failed"
- Pod이 계속 재시작됨
- 헬스체크 엔드포인트가 응답 안 함

## 2단계: 재현

```bash
# Pod 상태 확인
kubectl get pods myapp-xyz

# 상세 정보
kubectl describe pod myapp-xyz
```

## 3단계: 범위 축소

헬스체크 실패 유형:

1. **리디니스 프로브**: 스타트업 시간 부족
2. **라이브니스 프로브**: 앱이 멈춤 또는 교착
3. **네트워크 문제**: 연결 거부
4. **포트 오류**: 잘못된 포트 설정
5. **헬스 엔드포인트 버그**: 로직 오류

## 6단계: 수정안 선택

### 수정안 1: 올바른 헬스체크 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: app
    image: myapp:latest
    ports:
    - containerPort: 3000

    # 스타트업 프로브: 초기 시작 시간 확보
    startupProbe:
      httpGet:
        path: /health
        port: 3000
      failureThreshold: 30  # 최대 30회 시도
      periodSeconds: 10    # 10초마다 시도
      # 최대 300초(5분) 동안 시작 대기

    # 라이브니스 프로브: 앱이 살아있는지 확인
    livenessProbe:
      httpGet:
        path: /health
        port: 3000
      initialDelaySeconds: 30  # 30초 후 시작
      periodSeconds: 10        # 10초마다 확인
      timeoutSeconds: 5        # 5초 타임아웃
      failureThreshold: 3      # 3회 실패 시 재시작

    # 레디니스 프로브: 트래픽 받을 준비 확인
    readinessProbe:
      httpGet:
        path: /ready
        port: 3000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 2
```

### 수정안 2: 헬스 엔드포인트 구현

```javascript
// server.js (Node.js)
const express = require('express');
const app = express();

let isReady = false;
let lastHealthCheck = Date.now();

// 앱 초기화 (DB 연결 등)
async function initialize() {
  try {
    // DB 연결, 캐시 초기화 등
    await connectDB();
    isReady = true;
  } catch (error) {
    console.error('Initialization failed:', error);
    process.exit(1);
  }
}

// 헬스체크 엔드포인트
app.get('/health', (req, res) => {
  lastHealthCheck = Date.now();

  // 기본 헬스: 프로세스가 살아있는지만 확인
  res.status(200).json({
    status: 'ok',
    timestamp: new Date(),
    uptime: process.uptime()
  });
});

// 레디니스 엔드포인트
app.get('/ready', (req, res) => {
  if (!isReady) {
    res.status(503).json({
      status: 'not_ready',
      reason: 'Still initializing'
    });
    return;
  }

  // 의존성 확인
  try {
    // DB 연결 확인
    if (!db.isConnected()) {
      throw new Error('Database not connected');
    }

    res.status(200).json({
      status: 'ready',
      timestamp: new Date()
    });
  } catch (error) {
    res.status(503).json({
      status: 'not_ready',
      reason: error.message
    });
  }
});

// 시작
initialize().then(() => {
  app.listen(3000, () => {
    console.log('Server listening on port 3000');
  });
});
```

### 수정안 3: TCP 또는 명령 프로브

```yaml
# TCP 프로브
readinessProbe:
  tcpSocket:
    port: 3000
  initialDelaySeconds: 10
  periodSeconds: 5

# 명령 프로브
livenessProbe:
  exec:
    command:
    - /bin/sh
    - -c
    - curl -f http://localhost:3000/health || exit 1
  initialDelaySeconds: 30
  periodSeconds: 10
```

### 수정안 4: 점진적 헬스체크 설정

```yaml
# 초기: 느슨한 조건
spec:
  containers:
  - name: app
    startupProbe:
      httpGet:
        path: /health
        port: 3000
      failureThreshold: 40    # 느슨함
      periodSeconds: 10

    readinessProbe:
      httpGet:
        path: /ready
        port: 3000
      initialDelaySeconds: 5  # 빠르게 준비 확인
      periodSeconds: 3        # 자주 확인
      failureThreshold: 2

    livenessProbe:
      httpGet:
        path: /health
        port: 3000
      initialDelaySeconds: 60 # 충분한 시간 확보
      periodSeconds: 30
      failureThreshold: 3
```

## 연결된 프롬프트 블록

- **PB-CL-19-probes**: 프로브 개념
- **PB-RP-18-probe-test**: 프로브 테스트
- **PB-DG-19-probe-logs**: 프로브 로그
- **PB-PA-19-health-endpoint**: 헬스 엔드포인트
- **PB-VF-18-health-verify**: 헬스체크 검증
