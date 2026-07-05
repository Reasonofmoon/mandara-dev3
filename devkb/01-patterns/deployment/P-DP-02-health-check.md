---
id: P-DP-02
title: 헬스체크 패턴
stage: Deploy
layer: Infra
pattern_family: Release
tech_tags: [liveness probe, readiness probe, graceful shutdown, Kubernetes]
linked_errors: [E-DP-03, E-DP-04]
linked_flows: [F-DP-02]
linked_prompts: [PR-DP-02]
---

# 헬스체크 패턴

## 목표
애플리케이션의 건강 상태를 정확하게 모니터링하고, 장애 서비스를 자동으로 격리합니다.

## 핵심 구조

### Liveness & Readiness Probes

```typescript
// health/health.controller.ts
import { Controller, Get, Inject } from '@nestjs/common';
import { PrismaService } from 'prisma/prisma.service';
import { RedisService } from 'redis/redis.service';

@Controller('health')
export class HealthController {
  constructor(
    private prisma: PrismaService,
    private redis: RedisService,
  ) {}

  // Liveness Probe: 애플리케이션이 실행 중인가?
  @Get('live')
  async getLiveness() {
    return {
      status: 'UP',
      timestamp: new Date(),
    };
  }

  // Readiness Probe: 요청을 받을 준비가 되었는가?
  @Get('ready')
  async getReadiness() {
    const checks = {
      database: await this.checkDatabase(),
      redis: await this.checkRedis(),
      diskSpace: await this.checkDiskSpace(),
    };

    const allHealthy = Object.values(checks).every(
      check => check.status === 'UP'
    );

    return {
      status: allHealthy ? 'UP' : 'DOWN',
      checks,
      timestamp: new Date(),
    };
  }

  // Detailed Health Check
  @Get('detailed')
  async getDetailedHealth() {
    return {
      status: 'UP',
      components: {
        database: await this.checkDatabase(),
        redis: await this.checkRedis(),
        disk: await this.checkDiskSpace(),
        memory: this.checkMemory(),
        uptime: process.uptime(),
      },
    };
  }

  private async checkDatabase() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return { status: 'UP', responseTime: 'fast' };
    } catch (error) {
      return { status: 'DOWN', error: (error as Error).message };
    }
  }

  private async checkRedis() {
    try {
      const pong = await this.redis.ping();
      return { status: pong === 'PONG' ? 'UP' : 'DOWN' };
    } catch (error) {
      return { status: 'DOWN', error: (error as Error).message };
    }
  }

  private async checkDiskSpace() {
    try {
      const diskSpace = await this.getDiskUsage();
      const usage = (diskSpace.used / diskSpace.total) * 100;

      return {
        status: usage < 90 ? 'UP' : 'DOWN',
        used: diskSpace.used,
        total: diskSpace.total,
        percentage: usage.toFixed(2),
      };
    } catch (error) {
      return { status: 'DOWN', error: (error as Error).message };
    }
  }

  private checkMemory() {
    const usage = process.memoryUsage();
    const percentage = (usage.heapUsed / usage.heapTotal) * 100;

    return {
      status: percentage < 90 ? 'UP' : 'DEGRADED',
      used: Math.round(usage.heapUsed / 1024 / 1024),
      total: Math.round(usage.heapTotal / 1024 / 1024),
      percentage: percentage.toFixed(2),
    };
  }

  private async getDiskUsage() {
    // 구현 (예: df 명령)
    return { used: 0, total: 0 };
  }
}
```

### Kubernetes 설정

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 3000

        # Liveness Probe: Pod이 살아있는가?
        # 실패 시 Pod 재시작
        livenessProbe:
          httpGet:
            path: /health/live
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness Probe: 트래픽을 받을 준비가 되었는가?
        # 실패 시 Pod에서 트래픽 차단
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2

        # Startup Probe: 애플리케이션이 시작되었는가?
        # 이것이 완료되어야 다른 probe 실행
        startupProbe:
          httpGet:
            path: /health/ready
            port: 3000
          failureThreshold: 30
          periodSeconds: 10

        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        # Graceful Shutdown
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
```

### Graceful Shutdown

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Graceful shutdown 처리
  let isShuttingDown = false;

  const gracefulShutdown = async (signal: string) => {
    console.log(`${signal} received, starting graceful shutdown`);

    if (isShuttingDown) return;
    isShuttingDown = true;

    // 1. 새로운 요청 차단
    app.get(HealthController).setReady(false);

    // 2. 기존 요청 완료 대기 (최대 30초)
    await new Promise(resolve => setTimeout(resolve, 30000));

    // 3. 데이터베이스 연결 종료
    const prisma = app.get(PrismaService);
    await prisma.$disconnect();

    // 4. 애플리케이션 종료
    await app.close();
    process.exit(0);
  };

  // 신호 처리
  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  await app.listen(3000);
}

bootstrap();
```

### Health Service

```typescript
// health/health.service.ts
@Injectable()
export class HealthService {
  private isReady = true;
  private startTime = Date.now();

  setReady(ready: boolean) {
    this.isReady = ready;
  }

  isHealthy(): boolean {
    return this.isReady;
  }

  getUptime(): number {
    return (Date.now() - this.startTime) / 1000;
  }

  async performChecks() {
    const checks = {
      database: await this.checkDatabaseHealth(),
      redis: await this.checkRedisHealth(),
      memory: this.checkMemoryHealth(),
    };

    const allHealthy = Object.values(checks).every(
      check => check.status === 'healthy'
    );

    if (!allHealthy) {
      this.setReady(false);
    }

    return checks;
  }
}
```

## 최소 예제

```typescript
@Get('health')
async health() {
  try {
    await this.prisma.$queryRaw`SELECT 1`;
    return { status: 'ok' };
  } catch (error) {
    return { status: 'error' };
  }
}
```

## Docker Compose 헬스체크

```yaml
services:
  app:
    image: myapp:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s # 컨테이너 시작 후 40초 동안 체크 안 함
```

## 모니터링

```typescript
@Injectable()
export class HealthMonitorService {
  @Cron('*/1 * * * *') // 매분
  async checkHealth() {
    const response = await fetch('/health/detailed');
    const health = await response.json();

    if (health.status !== 'UP') {
      await this.alertOps(health);
    }

    // 메트릭 저장
    await this.prometheus.gauge('health_status', health);
  }
}
```

## 안티패턴

### 1. 헬스체크가 너무 복잡

```typescript
// ❌ 나쁜 예제
@Get('health')
async health() {
  // 복잡한 계산과 쿼리
  const analysis = await complexAnalysis();
  return analysis; // 시간 오래 걸림!
}

// ✅ 좋은 예제
@Get('health/live')
live() {
  return { status: 'ok' }; // 빠른 응답
}

@Get('health/ready')
async ready() {
  // 필수 체크만 수행
  return await this.prisma.$queryRaw`SELECT 1`;
}
```

## 연결된 오류

- **E-DP-03**: 장애 서비스 미탐지
- **E-DP-04**: 거짓 양성으로 인한 불필요한 재시작

## 연결된 플로우

- **F-DP-02**: 자동 복구 및 모니터링

## 참고 자료

- Kubernetes Probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Spring Boot Health: https://docs.spring.io/spring-boot/docs/current/reference/html/actuator.html
