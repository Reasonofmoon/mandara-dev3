---
id: P-BJ-01
title: 지수 백오프 재시도 패턴
stage: Implement
layer: API
pattern_family: Concurrency
tech_tags: [Bull Queue, 재시도, 지수 백오프, Circuit Breaker]
linked_errors: [E-BJ-01, E-BJ-02]
linked_flows: [F-BJ-01]
linked_prompts: [PR-BJ-01]
---

# 지수 백오프 재시도 패턴

## 목표
작업 실패 시 지수 백오프로 재시도하여 일시적 오류를 자동으로 복구하고 circuit breaker로 연쇄 실패를 방지합니다.

## 언제 사용하는가
- 외부 API 호출이 포함된 작업
- 데이터베이스 쿼리가 실패할 가능성 있는 경우
- 네트워크가 불안정한 환경
- 일시적 오류가 자동으로 해결될 수 있는 경우

## 핵심 구조

### Bull Queue 설정

```typescript
// jobs/email.queue.ts
import { Injectable } from '@nestjs/common';
import { Queue, Job } from 'bull';
import { InjectQueue } from '@nestjs/bull';

export interface SendEmailJob {
  to: string;
  subject: string;
  html: string;
}

@Injectable()
export class EmailQueue {
  constructor(
    @InjectQueue('email') private emailQueue: Queue<SendEmailJob>,
  ) {}

  async addEmailJob(data: SendEmailJob) {
    return this.emailQueue.add(data, {
      // 재시도 설정
      attempts: 5, // 최대 5회 시도
      backoff: {
        type: 'exponential',
        delay: 2000, // 초기 딜레이: 2초
      },
      removeOnComplete: true, // 성공 시 작업 제거
      removeOnFail: false, // 실패 시 기록 유지
    });
  }
}

// jobs/email.processor.ts
import { Process, Processor } from '@nestjs/bull';
import { Job } from 'bull';
import { Logger } from '@nestjs/common';

@Processor('email')
export class EmailProcessor {
  private readonly logger = new Logger(EmailProcessor.name);

  @Process()
  async handleSendEmail(job: Job<SendEmailJob>) {
    const { to, subject, html } = job.data;
    const attempt = job.attemptsMade + 1;

    try {
      this.logger.log(
        `Sending email to ${to} (attempt ${attempt}/${job.opts.attempts})`
      );

      // 이메일 전송
      await this.sendEmailViaProvider(to, subject, html);

      this.logger.log(`Email sent successfully to ${to}`);
    } catch (error) {
      this.logger.error(
        `Failed to send email to ${to}: ${error.message}`
      );

      // 재시도 가능한 오류인지 판단
      if (this.isRetryableError(error)) {
        // 재시도 큐 시스템이 자동으로 처리
        throw error;
      } else {
        // 재시도 불가능한 오류 (유효하지 않은 이메일 등)
        this.logger.error(`Non-retryable error: ${error.message}`);
        throw new Error(`Permanent failure: ${error.message}`);
      }
    }
  }

  private isRetryableError(error: any): boolean {
    const retryableErrors = [
      'ECONNREFUSED', // 연결 거부
      'ETIMEDOUT', // 타임아웃
      'EHOSTUNREACH', // 호스트 도달 불가
      'ERR_TLS_CERT_ALTNAME_INVALID', // 일시적 SSL 오류
    ];

    return retryableErrors.some(code =>
      error.message?.includes(code)
    );
  }

  private async sendEmailViaProvider(
    to: string,
    subject: string,
    html: string,
  ) {
    // 실제 이메일 전송 로직
    return fetch('https://api.mailprovider.com/send', {
      method: 'POST',
      body: JSON.stringify({ to, subject, html }),
    });
  }
}
```

### 모듈 설정

```typescript
// jobs/jobs.module.ts
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { EmailProcessor } from './email.processor';
import { EmailQueue } from './email.queue';

@Module({
  imports: [
    BullModule.forRoot({
      redis: {
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
      },
    }),
    BullModule.registerQueue({
      name: 'email',
    }),
  ],
  providers: [EmailProcessor, EmailQueue],
  exports: [EmailQueue],
})
export class JobsModule {}
```

### Circuit Breaker 통합

```typescript
// jobs/circuit-breaker.ts
export enum CircuitState {
  CLOSED = 'CLOSED', // 정상
  OPEN = 'OPEN', // 차단
  HALF_OPEN = 'HALF_OPEN', // 복구 중
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime = 0;

  constructor(
    private readonly failureThreshold = 5,
    private readonly successThreshold = 2,
    private readonly timeout = 60000, // 1분
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
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
        if (this.successCount >= this.successThreshold) {
          this.reset();
        }
      } else {
        this.failureCount = 0;
      }

      return result;
    } catch (error) {
      this.failureCount++;
      this.lastFailureTime = Date.now();

      if (this.state === CircuitState.HALF_OPEN) {
        this.state = CircuitState.OPEN;
      }

      if (this.failureCount >= this.failureThreshold) {
        this.state = CircuitState.OPEN;
      }

      throw error;
    }
  }

  private shouldAttemptReset(): boolean {
    return Date.now() - this.lastFailureTime >= this.timeout;
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
@Processor('email')
export class EmailProcessor {
  private readonly breaker = new CircuitBreaker(5, 2, 60000);

  @Process()
  async handleSendEmail(job: Job<SendEmailJob>) {
    const { to, subject, html } = job.data;

    try {
      await this.breaker.execute(() =>
        this.sendEmailViaProvider(to, subject, html)
      );
    } catch (error) {
      if (this.breaker.getState() === CircuitState.OPEN) {
        throw new Error(
          'Email service is temporarily unavailable. Retrying later.'
        );
      }
      throw error;
    }
  }
}
```

### 작업 모니터링

```typescript
// jobs/job-monitor.service.ts
@Injectable()
export class JobMonitorService {
  constructor(
    @InjectQueue('email') private emailQueue: Queue<SendEmailJob>,
  ) {}

  async getJobStats() {
    const counts = await this.emailQueue.getJobCounts();
    const failedJobs = await this.emailQueue.getFailed(0, 10);

    return {
      stats: {
        waiting: counts.waiting,
        active: counts.active,
        completed: counts.completed,
        failed: counts.failed,
        delayed: counts.delayed,
      },
      recentFailures: failedJobs.map(job => ({
        id: job.id,
        data: job.data,
        attemptsMade: job.attemptsMade,
        failedReason: job.failedReason,
        stackTrace: job.stacktrace,
      })),
    };
  }

  async retryFailedJob(jobId: string | number) {
    const job = await this.emailQueue.getJob(jobId);
    if (!job) throw new Error('Job not found');

    await job.retry();
  }
}

// 컨트롤러
@Controller('api/jobs')
export class JobsController {
  constructor(private jobMonitor: JobMonitorService) {}

  @Get('stats')
  async getStats() {
    return this.jobMonitor.getJobStats();
  }

  @Post('retry/:jobId')
  async retryJob(@Param('jobId') jobId: string) {
    await this.jobMonitor.retryFailedJob(jobId);
    return { success: true };
  }
}
```

## 최소 예제

```typescript
const queue = new Queue('jobs');

await queue.add(
  { url: 'https://api.example.com/data' },
  {
    attempts: 5,
    backoff: { type: 'exponential', delay: 2000 },
  }
);

queue.process(async (job) => {
  try {
    return await fetch(job.data.url);
  } catch (error) {
    throw error; // 재시도됨
  }
});
```

## 안티패턴

### 1. 모든 오류를 재시도

```typescript
// ❌ 나쁜 예제
@Process()
async handle(job: Job) {
  await this.sendEmail(); // 검증 오류도 재시도!
}

// ✅ 좋은 예제
@Process()
async handle(job: Job) {
  try {
    await this.sendEmail();
  } catch (error) {
    if (!this.isRetryable(error)) {
      throw new Error(`Permanent failure: ${error.message}`);
    }
    throw error;
  }
}
```

## 연결된 오류

- **E-BJ-01**: 재시도 실패로 인한 작업 손실
- **E-BJ-02**: Circuit breaker 오픈으로 인한 작업 대기

## 연결된 플로우

- **F-BJ-01**: 이메일 발송 재시도 로직

## 참고 자료

- Bull Queue: https://github.com/OptimalBits/bull
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
