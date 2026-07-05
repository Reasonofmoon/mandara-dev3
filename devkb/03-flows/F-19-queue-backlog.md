---
id: F-19
title: 큐 적체 해결
pattern_id: P-19
error_ids: [E-55, E-56, E-57]
tech_scope: 메시지 큐, 비동기 처리, 작업 스케줄링
---

# 큐 적체 해결

메시지 큐 및 작업 큐 적체로 인한 지연 문제를 해결합니다.

## 1단계: 증상 고정

- 메시지 처리 지연 증가
- 큐 크기 계속 증가
- 작업 완료 시간 초과
- "Queue full" 오류
- 메모리 부족

## 2단계: 재현

```javascript
// Redis 큐 상태 확인
const queue = new Queue('myQueue', {
  redis: { host: 'localhost', port: 6379 }
});

queue.getCount().then(count => {
  console.log(`Queue size: ${count}`);
});

// 또는 CLI
redis-cli LLEN myQueue:jobs
```

## 3단계: 범위 축소

큐 적체 원인:

1. **처리 속도 느림**: 워커가 느리게 처리
2. **워커 부족**: 병렬 처리 수 부족
3. **메모리 누수**: 처리 완료 안 된 작업
4. **에러 루프**: 계속 실패하는 작업
5. **트래픽 급증**: 예상보다 많은 요청

## 6단계: 수정안 선택

### 수정안 1: 워커 동적 스케일링

```javascript
const Queue = require('bull');
const redis = require('redis');

const queue = new Queue('emails', {
  redis: { host: 'localhost', port: 6379 }
});

// 워커 수 동적 조정
const processingQueue = [];
let activeWorkers = 2;

async function adjustWorkers() {
  const count = await queue.getCount();
  const targetWorkers = Math.min(
    Math.ceil(count / 100),
    10 // 최대 10개
  );

  if (targetWorkers > activeWorkers) {
    console.log(`Scaling up workers: ${activeWorkers} → ${targetWorkers}`);
    for (let i = activeWorkers; i < targetWorkers; i++) {
      addWorker();
    }
    activeWorkers = targetWorkers;
  }
}

function addWorker() {
  queue.process('*', 5, async (job) => {
    // 작업 처리
    await processJob(job);
  });
}

// 1분마다 워커 수 조정
setInterval(adjustWorkers, 60000);
```

### 수정안 2: 우선순위 큐

```javascript
const Queue = require('bull');

const priorityQueue = new Queue('tasks', {
  redis: { host: 'localhost', port: 6379 }
});

// 우선순위별 작업 추가
priorityQueue.add(
  { type: 'email', to: 'user@example.com' },
  { priority: 10 } // 높은 우선순위
);

priorityQueue.add(
  { type: 'analytics', data: {} },
  { priority: 1 } // 낮은 우선순위
);

// 워커: 우선순위 순서로 처리
priorityQueue.process(async (job) => {
  console.log(`Processing job priority ${job._priority}`);
  // 처리 로직
});
```

### 수정안 3: 배치 처리

```javascript
const Queue = require('bull');

const batchQueue = new Queue('batch', {
  redis: { host: 'localhost', port: 6379 }
});

// 배치로 작업 추가
async function addBatchJobs(items) {
  const jobs = items.map(item => ({
    data: item,
    opts: { attempts: 3, backoff: 'fixed', backoffDelay: 5000 }
  }));

  await batchQueue.addBulk(jobs);
}

// 워커: 배치 처리
batchQueue.process(100, async (job) => {
  // 배치 크기: 100개 동시 처리
  await processJob(job.data);
});
```

### 수정안 4: 재시도 로직 및 데드 레터 큐

```javascript
const Queue = require('bull');

const mainQueue = new Queue('main', {
  redis: { host: 'localhost', port: 6379 }
});

const deadLetterQueue = new Queue('deadLetter', {
  redis: { host: 'localhost', port: 6379 }
});

mainQueue.process(async (job) => {
  try {
    await processJob(job.data);
  } catch (error) {
    // 재시도 횟수 초과시
    if (job.attemptsMade >= job.opts.attempts) {
      await deadLetterQueue.add(
        {
          originalJob: job.data,
          error: error.message,
          attempts: job.attemptsMade
        },
        { removeOnFail: false }
      );
      throw error;
    }
    throw error;
  }
});

// 데드 레터 큐 모니터링
deadLetterQueue.on('failed', async (job) => {
  console.error('Job failed permanently:', job.data);
  // 알럿 발송
  await sendAlert({
    type: 'QUEUE_FAILURE',
    job: job.data
  });
});
```

### 수정안 5: 큐 모니터링 및 알럿

```javascript
const Queue = require('bull');

const queue = new Queue('myQueue', {
  redis: { host: 'localhost', port: 6379 }
});

// 큐 상태 모니터링
setInterval(async () => {
  const [waiting, active, completed, failed] = await Promise.all([
    queue.getWaitingCount(),
    queue.getActiveCount(),
    queue.getCompletedCount(),
    queue.getFailedCount()
  ]);

  const metrics = { waiting, active, completed, failed };
  console.log('Queue metrics:', metrics);

  // 알럿 조건
  if (waiting > 1000) {
    sendAlert({
      type: 'QUEUE_BACKLOG_HIGH',
      waiting,
      threshold: 1000
    });
  }

  if (failed > 100) {
    sendAlert({
      type: 'QUEUE_HIGH_FAILURES',
      failed
    });
  }
}, 60000);
```

### 수정안 6: 큐 정리 및 유지보수

```javascript
const Queue = require('bull');

const queue = new Queue('myQueue', {
  redis: { host: 'localhost', port: 6379 }
});

// 완료된 작업 정리 (1주일 이상 된 것)
queue.clean(7 * 24 * 60 * 60 * 1000, 'completed');

// 실패한 작업 정리
queue.clean(24 * 60 * 60 * 1000, 'failed', 0, 100);

// 또는 주기적으로
setInterval(async () => {
  const cleaned = await queue.clean(0, 'completed', 0, 100);
  console.log(`Cleaned ${cleaned.length} completed jobs`);
}, 12 * 60 * 60 * 1000); // 12시간마다
```

## 연결된 프롬프트 블록

- **PB-CL-20-queues**: 큐 개념
- **PB-RP-19-queue-test**: 큐 부하 테스트
- **PB-DG-20-queue-monitor**: 큐 모니터링
- **PB-PA-20-queue-scaling**: 큐 스케일링
- **PB-VF-19-queue-verify**: 큐 성능 검증
