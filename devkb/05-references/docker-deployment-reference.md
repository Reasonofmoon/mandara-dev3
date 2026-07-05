---
title: Docker와 Kubernetes 참조 가이드
version: 1.0
---

# Docker와 Kubernetes 참조 가이드

Dockerfile 최적화, K8s 리소스 설정 참조입니다.

## Dockerfile 최적화

### 멀티 스테이지 빌드

```dockerfile
# Stage 1: builder
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: runtime
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./
USER node
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### 계층 캐싱

```dockerfile
FROM node:18-alpine
WORKDIR /app

# 의존성 레이어 (변경 적음 = 캐시 유지)
COPY package*.json ./
RUN npm ci

# 소스 코드 레이어 (변경 빈번 = 캐시 재생성)
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["node", "dist/index.js"]
```

## Kubernetes 리소스

### Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  containers:
  - name: app
    image: myapp:latest
    ports:
    - containerPort: 3000
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 3000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  type: ClusterIP  # or LoadBalancer, NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "info"
  API_URL: "https://api.example.com"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@db:5432/mydb"
  API_KEY: "secret-key-123"
```

### HorizontalPodAutoscaler

```yaml
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
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

## 리소스 요청/제한

### CPU/Memory 단위

- CPU: `100m` (0.1 core), `1`, `1500m`
- Memory: `128Mi`, `256Mi`, `1Gi`, `2Gi`

### 권장사항

| 유형 | CPU | Memory |
|------|-----|--------|
| 소규모 | 100m-250m | 128Mi-256Mi |
| 중규모 | 250m-500m | 256Mi-512Mi |
| 대규모 | 500m-1000m | 512Mi-1Gi |

