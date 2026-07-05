---
id: F-22
title: OOMKilled 해결
pattern_id: P-22
error_ids: [E-64, E-65, E-66]
tech_scope: 메모리 관리, Kubernetes, 리소스 제한
---

# OOMKilled 해결

메모리 부족으로 인해 Pod이 강제 종료되는 문제를 해결합니다.

## 1단계: 증상 고정

- Pod 상태: "OOMKilled"
- 오류 메시지: "out of memory"
- Pod이 갑자기 재시작
- 메모리 사용량이 할당량 초과
- 일정 시간 후 항상 실패

## 2단계: 재현

```bash
# OOMKilled 상태 확인
kubectl get pods myapp

# Pod 정보 확인 (Reason: OOMKilled)
kubectl describe pod myapp

# 메모리 사용량 확인
kubectl top pod myapp
```

## 6단계: 수정안 선택

### 수정안 1: 리소스 요청/제한 설정

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
        resources:
          requests:  # 최소 보장 메모리
            memory: "256Mi"
            cpu: "250m"
          limits:    # 최대 허용 메모리
            memory: "512Mi"
            cpu: "500m"
```

### 수정안 2: 메모리 누수 수정

```javascript
// memory-leak-fix.js
// ❌ 무한정 증가하는 캐시
const cache = {};

function addToCache(key, value) {
  cache[key] = value;
}

// ✅ 크기 제한
class BoundedCache {
  constructor(maxSize = 100) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }

  set(key, value) {
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  get(key) {
    return this.cache.get(key);
  }
}

const cache = new BoundedCache(100);
```

### 수정안 3: 메모리 프로파일링

```javascript
// server.js
if (process.env.ENABLE_MEMORY_PROFILING) {
  const heapdump = require('heapdump');

  // 1시간마다 힙 스냅샷 저장
  setInterval(() => {
    const filename = `/tmp/heap-${Date.now()}.heapsnapshot`;
    heapdump.writeSnapshot(filename);
    console.log(`Heap snapshot saved to ${filename}`);
  }, 60 * 60 * 1000);
}

// 메모리 사용량 모니터링
setInterval(() => {
  const usage = process.memoryUsage();
  console.log({
    rss: Math.round(usage.rss / 1024 / 1024) + 'MB',  // 프로세스 메모리
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024) + 'MB',
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024) + 'MB',
    external: Math.round(usage.external / 1024 / 1024) + 'MB'
  });

  // 메모리 사용량이 50% 초과하면 경고
  const limit = 512 * 1024 * 1024; // 512MB
  if (usage.heapUsed > limit * 0.5) {
    console.warn('High memory usage');
    // 가비지 컬렉션 강제
    if (global.gc) {
      global.gc();
    }
  }
}, 60000);
```

### 수정안 4: 배치 처리로 메모리 효율화

```javascript
// ❌ 메모리 낭비
async function processLargeFile() {
  const data = await fs.readFile('large-file.txt'); // 전체 파일 메모리에 로드
  const lines = data.toString().split('\n');

  for (const line of lines) {
    await procesLine(line);
  }
}

// ✅ 스트리밍
import fs from 'fs';
import readline from 'readline';

async function processLargeFile() {
  const stream = fs.createReadStream('large-file.txt');
  const rl = readline.createInterface({
    input: stream,
    crlfDelay: Infinity
  });

  for await (const line of rl) {
    await processLine(line);
  }
}
```

### 수정안 5: 수평 스케일링

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70  # 70% 이상시 스케일 아웃
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

### 수정안 6: 메모리 재시작 정책

```yaml
# 일정 시간마다 Pod 재시작 (메모리 재설정)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      restartPolicy: Always
      containers:
      - name: app
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 30"]  # Graceful shutdown

# CronJob으로 주기적 재시작
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pod-restart
spec:
  schedule: "0 2 * * *"  # 매일 오전 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kubectl
            image: bitnami/kubectl
            command:
            - /bin/sh
            - -c
            - kubectl rollout restart deployment/myapp
          restartPolicy: OnFailure
```

## 연결된 프롬프트 블록

- **PB-CL-23-resources**: 리소스 개념
- **PB-RP-22-memory-stress**: 메모리 스트레스 테스트
- **PB-DG-23-memory-profile**: 메모리 프로파일링
- **PB-PA-23-resource-tuning**: 리소스 튜닝
- **PB-VF-22-memory-verify**: 메모리 검증
