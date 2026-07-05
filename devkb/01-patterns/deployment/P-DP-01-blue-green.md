---
id: P-DP-01
title: 블루-그린 배포 패턴
stage: Deploy
layer: Infra
pattern_family: Release
tech_tags: [무중단 배포, 트래픽 전환, 롤백, 인프라]
linked_errors: [E-DP-01, E-DP-02]
linked_flows: [F-DP-01]
linked_prompts: [PR-DP-01]
---

# 블루-그린 배포 패턴

## 목표
두 개의 동일한 환경(Blue, Green)을 유지하면서 무중단 배포와 빠른 롤백을 구현합니다.

## 언제 사용하는가
- 무중단 배포가 필수적일 때
- 빠른 롤백이 중요한 경우
- 배포 중 문제 발생 시 즉시 전환 필요

## 핵심 구조

### AWS ECS + ALB 기반 구현

```typescript
// infrastructure/blue-green-deployment.ts
import * as aws from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class BlueGreenDeployment extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    // ALB (Application Load Balancer)
    const alb = new aws.elasticloadbalancingv2.ApplicationLoadBalancer(
      this,
      'ALB',
      {
        vpc: this.vpc,
        internetFacing: true,
      }
    );

    // Blue 타겟 그룹
    const blueTargetGroup =
      new aws.elasticloadbalancingv2.ApplicationTargetGroup(
        this,
        'BlueTargetGroup',
        {
          vpc: this.vpc,
          port: 80,
          protocol: aws.elasticloadbalancingv2.ApplicationProtocol.HTTP,
          targetType:
            aws.elasticloadbalancingv2.TargetType.IP,
        }
      );

    // Green 타겟 그룹
    const greenTargetGroup =
      new aws.elasticloadbalancingv2.ApplicationTargetGroup(
        this,
        'GreenTargetGroup',
        {
          vpc: this.vpc,
          port: 80,
          protocol: aws.elasticloadbalancingv2.ApplicationProtocol.HTTP,
          targetType:
            aws.elasticloadbalancingv2.TargetType.IP,
        }
      );

    // ALB 리스너 (현재 Blue로 트래픽)
    alb.addListener('Listener', {
      port: 80,
      defaultTargetGroups: [blueTargetGroup],
    });

    // ECS 서비스 - Blue
    const blueService = new aws.ecs.FargateService(
      this,
      'BlueService',
      {
        cluster,
        taskDefinition: blueTaskDef,
        desiredCount: 2,
      }
    );
    blueTargetGroup.addTarget(blueService);

    // ECS 서비스 - Green
    const greenService = new aws.ecs.FargateService(
      this,
      'GreenService',
      {
        cluster,
        taskDefinition: greenTaskDef,
        desiredCount: 2,
      }
    );
    greenTargetGroup.addTarget(greenService);

    // 배포 함수
    this.deployNewVersion = async (
      newImageUri: string
    ) => {
      // 현재 상태 확인
      const currentGreen = await this.isGreenActive();

      if (currentGreen) {
        // Green이 현재 활성 - Blue에 배포
        await this.deployToBlue(newImageUri);
        await this.validateBlue();
        await this.switchToBlue(blueTargetGroup, greenTargetGroup);
      } else {
        // Blue가 현재 활성 - Green에 배포
        await this.deployToGreen(newImageUri);
        await this.validateGreen();
        await this.switchToGreen(blueTargetGroup, greenTargetGroup);
      }
    };
  }

  private async deployToBlue(imageUri: string) {
    // Blue 태스크 정의 업데이트
    await this.updateTaskDefinition('blue-task', imageUri);

    // Blue 서비스 업데이트
    await this.updateService('blue-service');
  }

  private async validateBlue() {
    // Blue 환경 헬스 체크
    const response = await fetch('http://blue.internal/health');
    if (!response.ok) {
      throw new Error('Blue health check failed');
    }
  }

  private async switchToBlue(blueTargetGroup: any, greenTargetGroup: any) {
    // ALB 리스너 Blue로 전환
    await this.updateListenerTargetGroup(blueTargetGroup);
    console.log('Traffic switched to Blue');
  }
}
```

### Docker Compose 버전

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Blue 환경
  app-blue:
    image: myapp:current
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - APP_NAME=blue
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Green 환경
  app-green:
    image: myapp:latest
    ports:
      - "3001:3000"
    environment:
      - NODE_ENV=production
      - APP_NAME=green
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # 로드 밸런서 (Nginx)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app-blue
      - app-green
```

### Nginx 설정

```nginx
# nginx.conf
upstream blue {
    server app-blue:3000;
}

upstream green {
    server app-green:3000;
}

server {
    listen 80;

    # Blue로 라우팅 (기본값)
    set $upstream_pool blue;

    # Redis에서 현재 활성 환경 읽기
    access_by_lua_block {
        local redis = require "resty.redis"
        local red = redis:new()
        red:connect("redis", 6379)
        local active = red:get("active_environment")
        if active == "green" then
            ngx.var.upstream_pool = "green"
        end
        red:close()
    }

    location / {
        proxy_pass http://$upstream_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 헬스 체크 엔드포인트
    location /health {
        access_log off;
        default_type application/json;
        return 200 '{"status":"ok"}';
    }
}
```

## 배포 스크립트

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh

set -e

CURRENT_ENV=$(redis-cli get active_environment)
NEW_ENV=$( [ "$CURRENT_ENV" = "blue" ] && echo "green" || echo "blue" )

echo "Current environment: $CURRENT_ENV"
echo "Deploying to: $NEW_ENV"

# 1. 새 환경에 최신 이미지 배포
docker-compose pull app-$NEW_ENV
docker-compose up -d app-$NEW_ENV

# 2. 헬스 체크
echo "Waiting for $NEW_ENV to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost:$([ "$NEW_ENV" = "blue" ] && echo 3000 || echo 3001)/health; then
        echo "$NEW_ENV is healthy"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo "Health check failed for $NEW_ENV"
        docker-compose down app-$NEW_ENV
        exit 1
    fi
done

# 3. 트래픽 전환
echo "Switching traffic to $NEW_ENV"
redis-cli set active_environment $NEW_ENV
sleep 5

# 4. 이전 환경 종료
echo "Shutting down $CURRENT_ENV"
docker-compose down app-$CURRENT_ENV

echo "Deployment completed successfully"
```

## 최소 예제

```bash
# 1. Blue 배포
docker-compose up -d app-blue

# 2. Green에 새 버전 배포
docker-compose up -d app-green

# 3. 헬스 체크
curl http://localhost:3001/health

# 4. 트래픽 전환
nginx -s reload # Green으로 설정된 nginx 재로드

# 5. Blue 종료
docker-compose down app-blue
```

## 롤백

```bash
#!/bin/bash
# scripts/rollback.sh

CURRENT=$(redis-cli get active_environment)
PREVIOUS=$( [ "$CURRENT" = "blue" ] && echo "green" || echo "blue" )

echo "Rolling back from $CURRENT to $PREVIOUS"

# 즉시 이전 환경으로 전환
redis-cli set active_environment $PREVIOUS
nginx -s reload

echo "Rollback completed"
```

## 안티패턴

### 1. 헬스 체크 없이 전환

```bash
# ❌ 나쁜 예제
docker-compose up -d app-green
redis-cli set active_environment green
# 헬스 체크 없음!

# ✅ 좋은 예제
docker-compose up -d app-green
sleep 10
curl -f http://localhost:3001/health || exit 1
redis-cli set active_environment green
```

## 연결된 오류

- **E-DP-01**: 전환 중 트래픽 손실
- **E-DP-02**: 롤백 실패

## 연결된 플로우

- **F-DP-01**: 안전한 배포 프로세스

## 참고 자료

- AWS Blue/Green Deployments: https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/
- Blue-Green Deployment Pattern: https://martinfowler.com/bliki/BlueGreenDeployment.html
