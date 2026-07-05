---
id: P-AC-04
title: 클라이언트 레이트 제한 처리 패턴
stage: Implement
layer: API
pattern_family: Contract
tech_tags: [429 응답, 지수 백오프, Retry-After, 네트워크 복원력]
linked_errors: [E-AC-08, E-AC-09]
linked_flows: [F-AC-06]
linked_prompts: [PR-AC-04]
---

# 클라이언트 레이트 제한 처리 패턴

## 목표
서버의 레이트 제한(429 응답)을 우아하게 처리하고, 지수 백오프로 재시도하여 요청 성공률을 높입니다.

## 언제 사용하는가
- 외부 API를 호출할 때
- 요청 속도 제한이 있는 서비스와 통신할 때
- 네트워크 안정성이 중요한 경우
- 데이터 수집 및 배치 작업

## 언제 사용하지 않는가
- 실시간 상호작용이 필요한 경우
- 레이트 제한이 없는 내부 API

## 핵심 구조

### 기본 Retry 로직

```typescript
// api/client.ts
interface RetryConfig {
  maxRetries: number;
  baseDelay: number; // 밀리초
  maxDelay: number;
  backoffMultiplier: number;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000, // 1초
  maxDelay: 32000, // 32초
  backoffMultiplier: 2,
};

export async function fetchWithRetry(
  url: string,
  options?: RequestInit,
  config: Partial<RetryConfig> = {},
): Promise<Response> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);

      // 429 Too Many Requests
      if (response.status === 429) {
        if (attempt < finalConfig.maxRetries) {
          // Retry-After 헤더 확인
          const retryAfter = response.headers.get('Retry-After');
          const delay = getRetryDelay(
            attempt,
            retryAfter,
            finalConfig
          );

          console.log(
            `Rate limited. Retrying after ${delay}ms (attempt ${attempt + 1}/${finalConfig.maxRetries})`
          );

          await sleep(delay);
          continue;
        }
      }

      // 5xx 에러 - 재시도 가능
      if (response.status >= 500 && attempt < finalConfig.maxRetries) {
        const delay = calculateBackoffDelay(attempt, finalConfig);
        console.log(
          `Server error ${response.status}. Retrying after ${delay}ms`
        );
        await sleep(delay);
        continue;
      }

      return response;
    } catch (error) {
      lastError = error as Error;

      // 네트워크 에러 - 재시도
      if (attempt < finalConfig.maxRetries) {
        const delay = calculateBackoffDelay(attempt, finalConfig);
        console.log(
          `Network error. Retrying after ${delay}ms: ${lastError.message}`
        );
        await sleep(delay);
        continue;
      }
    }
  }

  throw lastError || new Error('Failed after max retries');
}

function getRetryDelay(
  attempt: number,
  retryAfter: string | null,
  config: RetryConfig,
): number {
  if (retryAfter) {
    // Retry-After는 초 단위
    if (!isNaN(Number(retryAfter))) {
      return parseInt(retryAfter, 10) * 1000;
    }
    // HTTP 날짜 형식
    const retryDate = new Date(retryAfter);
    if (!isNaN(retryDate.getTime())) {
      return Math.max(0, retryDate.getTime() - Date.now());
    }
  }

  return calculateBackoffDelay(attempt, config);
}

function calculateBackoffDelay(attempt: number, config: RetryConfig): number {
  const delay = config.baseDelay * Math.pow(config.backoffMultiplier, attempt);
  // jitter 추가 (동시 재시도 방지)
  const jitter = Math.random() * delay * 0.1;
  return Math.min(delay + jitter, config.maxDelay);
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

## 최소 예제

```typescript
async function getUser(id: string) {
  const response = await fetchWithRetry(`/api/users/${id}`);
  return response.json();
}

// 사용
try {
  const user = await getUser('123');
  console.log(user);
} catch (error) {
  console.error('Failed to get user:', error);
}
```

## 고급 사용법 - Circuit Breaker 패턴

```typescript
enum CircuitState {
  CLOSED = 'CLOSED', // 정상 작동
  OPEN = 'OPEN', // 요청 차단
  HALF_OPEN = 'HALF_OPEN', // 복구 시도
}

interface CircuitBreakerConfig {
  failureThreshold: number; // 실패 횟수 임계값
  successThreshold: number; // HALF_OPEN에서 성공 필요 횟수
  timeout: number; // OPEN에서 HALF_OPEN으로 전환 시간 (ms)
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime = 0;

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(
    fn: () => Promise<T>,
  ): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await fn();

      if (this.state === CircuitState.HALF_OPEN) {
        this.successCount++;
        if (this.successCount >= this.config.successThreshold) {
          this.reset();
        }
      } else {
        this.failureCount = 0; // CLOSED 상태에서 성공
      }

      return result;
    } catch (error) {
      this.failureCount++;
      this.lastFailureTime = Date.now();

      if (this.state === CircuitState.HALF_OPEN) {
        this.state = CircuitState.OPEN;
        throw error;
      }

      if (this.failureCount >= this.config.failureThreshold) {
        this.state = CircuitState.OPEN;
      }

      throw error;
    }
  }

  private shouldAttemptReset(): boolean {
    return (
      Date.now() - this.lastFailureTime >= this.config.timeout
    );
  }

  private reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
  }

  getState(): CircuitState {
    return this.state;
  }
}

// 사용
const breaker = new CircuitBreaker({
  failureThreshold: 5,
  successThreshold: 2,
  timeout: 60000, // 1분
});

async function callExternalApi() {
  return breaker.execute(() =>
    fetchWithRetry('https://api.example.com/data')
  );
}
```

## React Hook for Rate Limit Handling

```typescript
interface UseApiOptions {
  maxRetries?: number;
  baseDelay?: number;
  onRetry?: (attempt: number, delay: number) => void;
}

export function useApi<T>(
  url: string,
  options?: UseApiOptions,
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [retryInfo, setRetryInfo] = useState({
    attempt: 0,
    nextRetryAt: null as Date | null,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetchWithRetry(
          url,
          undefined,
          {
            maxRetries: options?.maxRetries,
            baseDelay: options?.baseDelay,
          }
        );

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [url]);

  return { data, loading, error, retryInfo };
}

// 사용
export function UserList() {
  const { data: users, loading, error } = useApi<User[]>('/api/users');

  if (loading) return <div>로딩 중...</div>;
  if (error) return <div>오류: {error.message}</div>;

  return (
    <ul>
      {users?.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

## 사용자 피드백 표시

```typescript
export function ApiCallWithUserFeedback() {
  const [status, setStatus] = useState<
    'idle' | 'loading' | 'rate_limited' | 'error' | 'success'
  >('idle');
  const [retryCountdown, setRetryCountdown] = useState(0);

  const fetchData = async () => {
    setStatus('loading');
    let attempt = 0;

    while (attempt < 3) {
      try {
        const response = await fetch('/api/data');

        if (response.status === 429) {
          const retryAfter = parseInt(
            response.headers.get('Retry-After') || '5',
            10
          );
          setStatus('rate_limited');
          setRetryCountdown(retryAfter);

          // 카운트다운
          for (let i = retryAfter; i > 0; i--) {
            await sleep(1000);
            setRetryCountdown(i - 1);
          }

          attempt++;
          continue;
        }

        const data = await response.json();
        setStatus('success');
        return data;
      } catch (error) {
        if (attempt < 2) {
          attempt++;
          await sleep(1000 * Math.pow(2, attempt));
        } else {
          setStatus('error');
          throw error;
        }
      }
    }
  };

  return (
    <div>
      {status === 'loading' && <p>요청 중...</p>}
      {status === 'rate_limited' && (
        <p>요청이 많습니다. {retryCountdown}초 후 재시도됩니다.</p>
      )}
      {status === 'error' && <p>요청이 실패했습니다.</p>}
      {status === 'success' && <p>성공!</p>}
      <button onClick={fetchData}>데이터 불러오기</button>
    </div>
  );
}
```

## 안티패턴

### 1. 무한 재시도

```typescript
// ❌ 나쁜 예제
async function retryForever(url: string) {
  while (true) {
    try {
      return await fetch(url);
    } catch {
      // 무한 재시도!
    }
  }
}

// ✅ 좋은 예제
async function retryWithLimit(url: string, maxRetries: number = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(url);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(1000 * Math.pow(2, i));
    }
  }
}
```

### 2. Retry-After 헤더 무시

```typescript
// ❌ 나쁜 예제
if (response.status === 429) {
  await sleep(1000); // 고정 지연
  retry();
}

// ✅ 좋은 예제
if (response.status === 429) {
  const retryAfter = response.headers.get('Retry-After');
  const delay = retryAfter ? parseInt(retryAfter) * 1000 : 1000;
  await sleep(delay);
  retry();
}
```

## 연결된 오류

- **E-AC-08**: 429 응답을 처리하지 못해 요청 계속 실패
- **E-AC-09**: 너무 빠른 재시도로 인한 추가 제한

## 연결된 플로우

- **F-AC-06**: 외부 API 안정적 호출 패턴

## 참고 자료

- MDN Rate Limiting: https://developer.mozilla.org/en-US/docs/Glossary/rate_limit
- RFC 6585 HTTP 429: https://tools.ietf.org/html/rfc6585
