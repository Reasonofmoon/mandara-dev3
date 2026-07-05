---
id: E-RT-11
title: 타임아웃 오류
error_class: Runtime
symptoms:
  - 요청/작업 미완료
  - 응답 시간 초과
  - 무한 대기
exact_messages:
  - "Request timeout: no response received"
  - "The operation timed out"
  - "Error: timeout of 5000ms exceeded"
tech_tags:
  - Timeout
  - Async Operations
  - Network
  - Performance
linked_patterns: []
linked_flows: []
---

# 타임아웃 오류

## 증상
네트워크 요청, 데이터베이스 쿼리, 또는 기타 비동기 작업이 예상 시간 내에 완료되지 않으면 발생합니다. 느린 서버, 네트워크 문제, 또는 무한 루프가 원인입니다.

## 정확한 에러 메시지
```
Request timeout: no response received
The operation timed out
Error: timeout of 5000ms exceeded
Socket timeout: no activity received in 30000ms
Database query timeout after 10000ms
```

## 발생 맥락
```typescript
// 잘못된 예 1: 타임아웃 없음
const response = await fetch('/api/data');  // ❌ 무한 대기 가능

// 잘못된 예 2: 타임아웃 너무 짧음
const response = await fetch('/api/data', {
  signal: AbortSignal.timeout(100)  // ❌ 100ms는 너무 짧음
});

// 잘못된 예 3: 느린 쿼리
const result = await db.query('SELECT * FROM large_table');  // ❌ 대기

// 잘못된 예 4: 외부 API 연결 지연
const data = await externalAPI.getData();  // ❌ 시간 초과
```

## 필요한 증거
- 타임아웃 에러 메시지
- 요청 시간
- 응답 시간
- 네트워크 상태

## 의심 원인
1. 서버가 느리거나 응답하지 않음
2. 네트워크 연결 문제
3. 데이터베이스 쿼리 성능 저하
4. 외부 API 지연
5. 타임아웃 값 설정 오류
6. 무한 루프 또는 행(hang)

## 빠른 해결법

### 1. Fetch 타임아웃
```typescript
// AbortSignal 사용
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 5000
) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

// 사용
try {
  const response = await fetchWithTimeout('/api/data', {}, 5000);
  const data = await response.json();
} catch (error) {
  if (error.name === 'AbortError') {
    console.error('Request timeout');
  } else {
    console.error('Request failed:', error);
  }
}
```

### 2. Axios 타임아웃
```typescript
import axios from 'axios';

const client = axios.create({
  timeout: 5000,  // 글로벌 타임아웃
  timeoutErrorMessage: 'Request timeout'
});

// 개별 요청
const response = await axios.get('/api/data', {
  timeout: 3000
});

// 타임아웃 처리
try {
  await client.get('/api/data');
} catch (error) {
  if (error.code === 'ECONNABORTED') {
    console.error('Request timeout');
  }
}
```

### 3. 데이터베이스 타임아웃
```typescript
// Prisma
const result = await prisma.$queryRaw`
  SELECT * FROM users
`.timeout(5000);  // 5초 타임아웃

// 또는 Prisma 설정
const prisma = new PrismaClient({
  errorFormat: 'colorless'
});

// PostgreSQL 쿼리 타임아웃
const result = await db.query('SET statement_timeout = 5000; SELECT * FROM users');

// MongoDB
const result = await collection.findOne(
  { name: 'John' },
  { maxTimeMS: 5000 }
);
```

### 4. Promise.race로 타임아웃
```typescript
function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  message = 'Operation timeout'
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(message)), ms)
    )
  ]);
}

// 사용
try {
  const result = await withTimeout(
    fetchData(),
    5000,
    'Fetch timeout'
  );
} catch (error) {
  console.error(error.message);
}
```

### 5. 재시도 로직 with 타임아웃
```typescript
async function fetchWithRetryAndTimeout(
  url: string,
  maxRetries = 3,
  timeoutMs = 5000
) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);

      if (attempt === maxRetries) throw error;

      const backoff = Math.pow(2, attempt - 1) * 1000;  // 지수 백오프
      console.log(`Attempt ${attempt} failed, retrying in ${backoff}ms`);
      await new Promise(r => setTimeout(r, backoff));
    }
  }
}
```

### 6. 네트워크 상태 확인
```typescript
// 온라인 상태 확인
window.addEventListener('online', () => {
  console.log('Back online');
  retryFailedRequests();
});

window.addEventListener('offline', () => {
  console.log('Offline');
  pauseRequests();
});

// 연결 속도 확인
const connection = navigator.connection;
if (connection) {
  const type = connection.effectiveType;  // '4g', '3g', etc
  const downlink = connection.downlink;  // Mbps

  if (type === '4g') {
    TIMEOUT = 3000;
  } else if (type === '3g') {
    TIMEOUT = 5000;
  } else {
    TIMEOUT = 10000;
  }
}
```

### 7. 서버 응답 시간 최적화
```typescript
// Express에서 요청 타임아웃
app.use((req, res, next) => {
  // 30초 타임아웃
  req.setTimeout(30000);
  res.setTimeout(30000);
  next();
});

// 느린 쿼리 감지
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    if (duration > 5000) {
      console.warn(`Slow request: ${req.path} took ${duration}ms`);
    }
  });

  next();
});
```

### 8. 호출자 타임아웃
```typescript
// Node.js child process
const { spawn } = require('child_process');

const child = spawn('node', ['script.js']);
const timeout = setTimeout(() => {
  child.kill();  // 프로세스 강제 종료
  console.error('Process timeout');
}, 5000);

child.on('exit', () => {
  clearTimeout(timeout);
});
```

### 9. 모니터링 및 로깅
```typescript
interface RequestMetrics {
  url: string;
  duration: number;
  status: number;
  timeout: boolean;
}

const metrics: RequestMetrics[] = [];

async function trackRequest(
  url: string,
  fetchFn: () => Promise<Response>,
  timeoutMs = 5000
) {
  const start = Date.now();
  let timeout = false;

  try {
    const response = await withTimeout(fetchFn(), timeoutMs);
    const duration = Date.now() - start;

    metrics.push({
      url,
      duration,
      status: response.status,
      timeout: false
    });

    return response;
  } catch (error) {
    const duration = Date.now() - start;

    if (error.message.includes('timeout')) {
      timeout = true;
    }

    metrics.push({
      url,
      duration,
      status: 0,
      timeout
    });

    throw error;
  }
}

// 분석
function analyzeMetrics() {
  const avgDuration = metrics.reduce((sum, m) => sum + m.duration, 0) / metrics.length;
  const timeouts = metrics.filter(m => m.timeout).length;

  console.log(`Average duration: ${avgDuration.toFixed(2)}ms`);
  console.log(`Timeouts: ${timeouts}/${metrics.length}`);
}
```

## 연결된 패턴
- E-RT-04-unhandled-promise
- E-PF-04-n-plus-one-query

## 연결된 플로우
- 비동기 작업 타임아웃 관리 플로우
- 성능 최적화 플로우

## 재발 방지
1. 모든 비동기 작업에 타임아웃 설정
2. 적절한 타임아웃 값 선택 (5-30초)
3. 재시도 로직으로 일시적 문제 처리
4. 느린 작업은 백그라운드에서 처리
5. 모니터링으로 느린 요청 감지
6. 캐싱으로 반복 요청 최소화
7. CDN, 인덱싱 등으로 성능 최적화
