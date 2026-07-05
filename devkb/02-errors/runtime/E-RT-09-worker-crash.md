---
id: E-RT-09
title: 워커 프로세스 충돌
error_class: Runtime
symptoms:
  - 워커 종료됨
  - 작업 미완료
  - 메모리 누수
exact_messages:
  - "Worker process exited with code 1"
  - "Unexpected exit code: 1"
  - "Worker has died"
tech_tags:
  - Worker Threads
  - Child Process
  - Multi-threading
  - Process Management
linked_patterns: []
linked_flows: []
---

# 워커 프로세스 충돌

## 증상
워커 스레드 또는 자식 프로세스가 예기치 않게 종료됩니다. 작업이 완료되지 않거나 리소스 누수가 발생할 수 있습니다.

## 정확한 에러 메시지
```
Worker process exited with code 1
Unexpected exit code: 1
Worker has died: undefined
Error: Worker terminated due to memory limit
```

## 발생 맥락
```typescript
// 잘못된 예 1: 처리되지 않은 에러
const worker = new Worker('./worker.js');
worker.on('error', (error) => {
  console.error('Worker error:', error);
  // ❌ 복구 로직 없음
});

// 잘못된 예 2: 메모리 누수
for (let i = 0; i < 1000; i++) {
  const worker = new Worker('./worker.js');
  worker.postMessage({ data: largeArray });
  // ❌ 워커 종료 안 함
}

// 잘못된 예 3: 타임아웃
const worker = new Worker('./worker.js');
worker.postMessage({ task: 'longRunning' });
// ❌ 진행 상황 확인 없이 무한 대기
```

## 필요한 증거
- 워커 종료 코드
- 에러 메시지
- 워커 코드
- 리소스 사용량

## 의심 원인
1. 워커에서 처리되지 않은 에러
2. 메모리 부족으로 인한 강제 종료
3. 무한 루프 또는 행(hang)
4. 리소스 누수
5. 부모-자식 프로세스 통신 오류
6. 워커 파일 누락 또는 로드 실패

## 빠른 해결법

### 1. Worker 기본 설정
```typescript
import { Worker } from 'worker_threads';

const worker = new Worker('./worker.js');

// 메시지 수신
worker.on('message', (message) => {
  console.log('Message from worker:', message);
});

// 에러 처리
worker.on('error', (error) => {
  console.error('Worker error:', error);
  worker.terminate();  // 워커 종료
});

// 종료 처리
worker.on('exit', (code) => {
  if (code !== 0) {
    console.error(`Worker exit with code ${code}`);
  }
});

// 작업 전송
worker.postMessage({ task: 'calculate', data: [1, 2, 3] });

// 명시적 종료
setTimeout(() => {
  worker.terminate();
}, 5000);
```

### 2. Worker 파일
```typescript
// worker.js
import { parentPort } from 'worker_threads';

parentPort.on('message', async (message) => {
  try {
    const result = await processTask(message);
    parentPort.postMessage({ success: true, result });
  } catch (error) {
    parentPort.postMessage({ success: false, error: error.message });
  }
});

async function processTask(message) {
  if (message.task === 'calculate') {
    return message.data.reduce((a, b) => a + b, 0);
  }
  throw new Error('Unknown task');
}
```

### 3. 워커 풀 (여러 워커 관리)
```typescript
class WorkerPool {
  private workers: Worker[] = [];
  private queue: any[] = [];
  private active: Set<Worker> = new Set();

  constructor(poolSize = 4) {
    for (let i = 0; i < poolSize; i++) {
      const worker = new Worker('./worker.js');
      worker.on('error', (error) => console.error('Worker error:', error));
      this.workers.push(worker);
    }
  }

  async run(task: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const availableWorker = this.workers.find(w => !this.active.has(w));

      if (availableWorker) {
        this.executeTask(availableWorker, task, resolve, reject);
      } else {
        this.queue.push({ task, resolve, reject });
      }
    });
  }

  private executeTask(worker: Worker, task: any, resolve: any, reject: any) {
    this.active.add(worker);

    const messageHandler = (message: any) => {
      this.active.delete(worker);
      worker.removeListener('message', messageHandler);
      worker.removeListener('error', errorHandler);

      if (message.success) {
        resolve(message.result);
      } else {
        reject(new Error(message.error));
      }

      // 대기 중인 작업 처리
      const nextTask = this.queue.shift();
      if (nextTask) {
        this.executeTask(worker, nextTask.task, nextTask.resolve, nextTask.reject);
      }
    };

    const errorHandler = (error: any) => {
      this.active.delete(worker);
      worker.removeListener('message', messageHandler);
      worker.removeListener('error', errorHandler);
      reject(error);
    };

    worker.on('message', messageHandler);
    worker.on('error', errorHandler);
    worker.postMessage(task);
  }

  terminate() {
    this.workers.forEach(w => w.terminate());
  }
}

// 사용
const pool = new WorkerPool(4);
const result = await pool.run({ task: 'calculate', data: [1, 2, 3] });
pool.terminate();
```

### 4. 타임아웃 처리
```typescript
function runWithTimeout<T>(
  fn: () => Promise<T>,
  timeoutMs = 5000
): Promise<T> {
  return Promise.race([
    fn(),
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error('Operation timeout')), timeoutMs)
    )
  ]);
}

// 사용
try {
  const result = await runWithTimeout(
    () => worker.postMessage({ task: 'longRunning' }),
    10000  // 10초 타임아웃
  );
} catch (error) {
  console.error('Task timed out:', error);
  worker.terminate();
}
```

### 5. 메모리 모니터링
```typescript
import { Worker, resourceLimits } from 'worker_threads';

const worker = new Worker('./worker.js', {
  resourceLimits: {
    maxOldGenerationSizeMb: 512,  // 최대 메모리 512MB
    maxYoungGenerationSizeMb: 128  // Young generation 최대 128MB
  }
});

worker.on('exit', (code) => {
  if (code === 1) {
    console.error('Worker exceeded memory limit');
  }
});
```

### 6. Child Process
```typescript
import { fork, spawn } from 'child_process';

// fork: Node.js 프로세스
const child = fork('./child.js');
child.on('error', (error) => console.error('Child error:', error));
child.on('exit', (code) => console.log('Child exit:', code));

// spawn: 일반 프로세스
const proc = spawn('node', ['script.js']);
proc.on('error', (error) => console.error('Spawn error:', error));
proc.on('exit', (code) => console.log('Exit:', code));

// 데이터 처리
proc.stdout.on('data', (data) => {
  console.log(`stdout: ${data}`);
});

proc.stderr.on('data', (data) => {
  console.error(`stderr: ${data}`);
});
```

### 7. 재시작 로직
```typescript
class ResilientWorker {
  private worker: Worker;
  private maxRetries = 3;
  private retries = 0;

  constructor(scriptPath: string) {
    this.worker = this.createWorker(scriptPath);
  }

  private createWorker(scriptPath: string) {
    const worker = new Worker(scriptPath);

    worker.on('exit', (code) => {
      if (code !== 0 && this.retries < this.maxRetries) {
        console.log(`Worker crashed, restarting... (attempt ${this.retries + 1})`);
        this.retries++;
        this.worker = this.createWorker(scriptPath);
      } else if (code !== 0) {
        console.error('Worker failed permanently');
      }
    });

    return worker;
  }

  postMessage(message: any) {
    if (this.worker) {
      this.worker.postMessage(message);
    }
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate();
    }
  }
}
```

## 연결된 패턴
- E-RT-01-cannot-read-undefined
- E-PF-09-retry-storm

## 연결된 플로우
- 멀티스레딩 및 병렬 처리 플로우
- 프로세스 관리 플로우

## 재발 방지
1. 워커의 모든 에러 처리
2. 명시적으로 워커 종료
3. 메모리 제한 설정
4. 타임아웃 로직 추가
5. 워커 풀로 리소스 관리
6. 재시도 로직으로 일시적 오류 처리
7. 정기적으로 메모리 사용량 모니터링
