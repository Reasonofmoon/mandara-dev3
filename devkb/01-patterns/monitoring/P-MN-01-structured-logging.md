---
id: P-MN-01
title: 구조화된 로깅 패턴
stage: Operate
layer: Observability
pattern_family: Monitoring
tech_tags: [JSON 로깅, Correlation ID, Winston, Pino, ELK]
linked_errors: [E-MN-01, E-MN-02]
linked_flows: [F-MN-01]
linked_prompts: [PR-MN-01]
---

# 구조화된 로깅 패턴

## 목표
로그를 기계가 읽을 수 있는 구조화된 형식으로 기록하여 검색과 분석을 용이하게 합니다.

## 핵심 구조

### Winston 설정

```typescript
// logger/logger.module.ts
import { Module } from '@nestjs/common';
import * as winston from 'winston';
import { WinstonModule } from 'nest-winston';

@Module({
  providers: [
    {
      provide: 'WINSTON_MODULE_PROVIDER',
      useValue: WinstonModule.createLogger({
        transports: [
          // 콘솔 출력 (개발 환경)
          new winston.transports.Console({
            format: winston.format.combine(
              winston.format.timestamp(),
              winston.format.ms(),
              winston.format.errors({ stack: true }),
              winston.format.colorize(),
              winston.format.printf(
                ({ level, message, timestamp, ...meta }) => {
                  return `${timestamp} [${level}] ${message} ${
                    Object.keys(meta).length ? JSON.stringify(meta) : ''
                  }`;
                }
              )
            ),
          }),

          // JSON 파일 (프로덕션)
          new winston.transports.File({
            filename: 'logs/error.log',
            level: 'error',
            format: winston.format.combine(
              winston.format.timestamp(),
              winston.format.errors({ stack: true }),
              winston.format.json()
            ),
          }),

          new winston.transports.File({
            filename: 'logs/combined.log',
            format: winston.format.combine(
              winston.format.timestamp(),
              winston.format.json()
            ),
          }),
        ],
      }),
    },
  ],
  exports: ['WINSTON_MODULE_PROVIDER'],
})
export class LoggerModule {}
```

### 구조화된 로깅 인터셉터

```typescript
// logger/logging.interceptor.ts
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  Logger,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('HTTP');

  intercept(
    context: ExecutionContext,
    next
  ): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const response = context.switchToHttp().getResponse();

    // Correlation ID 생성 (또는 기존값 사용)
    const correlationId =
      request.headers['x-correlation-id'] || uuidv4();
    request.correlationId = correlationId;
    response.setHeader('X-Correlation-ID', correlationId);

    const startTime = Date.now();
    const { method, url, ip, headers } = request;

    // 요청 로깅
    this.logger.log(
      JSON.stringify({
        event: 'request_start',
        correlationId,
        method,
        url,
        ip,
        userAgent: headers['user-agent'],
        timestamp: new Date().toISOString(),
      })
    );

    return next.handle().pipe(
      tap(() => {
        const duration = Date.now() - startTime;

        // 성공 응답 로깅
        this.logger.log(
          JSON.stringify({
            event: 'request_complete',
            correlationId,
            method,
            url,
            statusCode: response.statusCode,
            duration,
            timestamp: new Date().toISOString(),
          })
        );
      }),
      catchError(error => {
        const duration = Date.now() - startTime;

        // 오류 로깅
        this.logger.error(
          JSON.stringify({
            event: 'request_error',
            correlationId,
            method,
            url,
            statusCode: error.status || 500,
            duration,
            error: {
              message: error.message,
              stack: error.stack,
              code: error.code,
            },
            timestamp: new Date().toISOString(),
          })
        );

        throw error;
      })
    );
  }
}
```

### 애플리케이션 레벨 로깅

```typescript
// services/users.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';
import { REQUEST } from '@nestjs/core';
import { Inject } from '@nestjs/common';

@Injectable()
export class UsersService {
  private readonly logger = new Logger(UsersService.name);

  constructor(
    private prisma: PrismaService,
    @Inject(REQUEST) private request: any,
  ) {}

  async createUser(email: string, password: string) {
    const correlationId = this.request.correlationId;

    this.logger.log(
      JSON.stringify({
        event: 'user_creation_started',
        correlationId,
        email,
        timestamp: new Date().toISOString(),
      })
    );

    try {
      const user = await this.prisma.user.create({
        data: { email, password: this.hashPassword(password) },
      });

      this.logger.log(
        JSON.stringify({
          event: 'user_created',
          correlationId,
          userId: user.id,
          email,
          timestamp: new Date().toISOString(),
        })
      );

      return user;
    } catch (error) {
      this.logger.error(
        JSON.stringify({
          event: 'user_creation_failed',
          correlationId,
          email,
          error: {
            message: (error as Error).message,
            code: (error as any).code,
          },
          timestamp: new Date().toISOString(),
        })
      );

      throw error;
    }
  }

  private hashPassword(password: string): string {
    // 구현
    return password;
  }
}
```

## 로그 포맷 예제

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "event": "user_login",
  "userId": "user-123",
  "email": "user@example.com",
  "ipAddress": "192.168.1.1",
  "userAgent": "Mozilla/5.0...",
  "duration": 125,
  "statusCode": 200
}

{
  "timestamp": "2024-01-15T10:31:15.456Z",
  "level": "error",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "event": "database_error",
  "error": {
    "message": "Connection timeout",
    "code": "ECONNREFUSED",
    "stack": "Error: Connection timeout..."
  }
}
```

## 로그 수집 및 분석

### ELK Stack 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_URL=http://elasticsearch:9200

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.0.0
    volumes:
      - ./logs:/var/log/app:ro
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    depends_on:
      - elasticsearch
```

### 로그 검색 쿼리

```json
// Elasticsearch 쿼리
{
  "query": {
    "bool": {
      "must": [
        { "match": { "event": "user_login" } },
        { "range": { "timestamp": { "gte": "2024-01-15T00:00:00Z" } } }
      ]
    }
  },
  "aggs": {
    "by_status": {
      "terms": { "field": "statusCode" }
    }
  }
}
```

## 최소 예제

```typescript
import * as winston from 'winston';

const logger = winston.createLogger({
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'app.log' }),
  ],
});

logger.info({
  event: 'user_login',
  userId: 'user-123',
  timestamp: new Date(),
});
```

## Context 기반 로깅

```typescript
// logger/logger.context.ts
import { Injectable } from '@nestjs/common';
import { AsyncLocalStorage } from 'async_hooks';

interface LogContext {
  correlationId: string;
  userId?: string;
  requestId?: string;
}

@Injectable()
export class LoggerContext {
  private context = new AsyncLocalStorage<LogContext>();

  setContext(ctx: LogContext) {
    this.context.getStore = () => ctx;
  }

  getContext(): LogContext | undefined {
    return this.context.getStore();
  }

  log(message: string, meta?: any) {
    const ctx = this.getContext();
    console.log(
      JSON.stringify({
        message,
        ...ctx,
        ...meta,
        timestamp: new Date().toISOString(),
      })
    );
  }
}
```

## 안티패턴

### 1. 민감한 정보 로깅

```typescript
// ❌ 나쁜 예제
logger.info({
  event: 'user_created',
  email: user.email,
  password: user.password, // 민감한 정보!
  creditCard: user.creditCard, // 민감한 정보!
});

// ✅ 좋은 예제
logger.info({
  event: 'user_created',
  userId: user.id,
  // 민감한 정보는 제외
});
```

### 2. 로깅 오버헤드

```typescript
// ❌ 나쁜 예제
for (const item of items) {
  logger.info('Processing item'); // 너무 많은 로그
}

// ✅ 좋은 예제
logger.info(`Processing ${items.length} items`);
for (const item of items) {
  // 로깅 없음
}
logger.info(`Completed ${items.length} items`);
```

## 연결된 오류

- **E-MN-01**: 추적 불가능한 오류
- **E-MN-02**: 로그 오버플로우

## 연결된 플로우

- **F-MN-01**: 요청 추적 및 디버깅

## 참고 자료

- Winston Logger: https://github.com/winstonjs/winston
- ELK Stack: https://www.elastic.co/what-is/elk-stack
- Structured Logging: https://www.kartar.net/2015/12/structured-logging/
