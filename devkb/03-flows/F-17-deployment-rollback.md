---
id: F-17
title: 배포 실패 및 롤백
pattern_id: P-17
error_ids: [E-49, E-50, E-51]
tech_scope: CI/CD, Kubernetes, 배포 자동화
---

# 배포 실패 및 롤백

배포 중 발생하는 오류를 처리하고 이전 버전으로 롤백합니다.

## 1단계: 증상 고정

- "Deployment failed"
- 새 버전의 pod이 실패
- 헬스체크 실패로 pod 재시작
- 데이터베이스 마이그레이션 오류
- 서비스 다운타임 발생

## 2단계: 재현

```bash
# 배포 시뮬레이션
kubectl apply -f deployment.yaml

# 배포 상태 확인
kubectl rollout status deployment/myapp

# 이벤트 확인
kubectl describe deployment myapp
```

## 3단계: 범위 축소

배포 실패 유형:

1. **애플리케이션 오류**: 코드 버그
2. **마이그레이션 오류**: DB 스키마 변경 실패
3. **리소스 부족**: CPU/메모리 부족
4. **헬스체크 실패**: pod이 ready 상태 도달 못함
5. **이미지 오류**: 컨테이너 이미지 없음/손상

## 4단계: 증거 수집

```bash
# 배포 히스토리 확인
kubectl rollout history deployment/myapp

# 현재 pod 상태
kubectl get pods -l app=myapp
kubectl describe pod <pod-name>
kubectl logs <pod-name>

# 배포 이벤트
kubectl get events --sort-by='.lastTimestamp'
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| 코드 버그 | 매우높음 | 높음 |
| 환경 변수 미설정 | 높음 | 낮음 |
| 마이그레이션 오류 | 높음 | 높음 |
| 리소스 부족 | 중간 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 점진적 배포 (Rolling Update)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 추가 pod 1개 허용
      maxUnavailable: 0  # 기존 pod 다운타임 없음
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v2
        ports:
        - containerPort: 3000

        # 헬스체크
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
```

```bash
# 배포
kubectl apply -f deployment.yaml

# 배포 진행 상황 확인
kubectl rollout status deployment/myapp
```

### 수정안 2: 신속한 롤백

```bash
# 배포 히스토리 확인
kubectl rollout history deployment/myapp

# 이전 버전으로 롤백
kubectl rollout undo deployment/myapp

# 특정 리비전으로 롤백
kubectl rollout undo deployment/myapp --to-revision=2

# 롤백 진행 상황 확인
kubectl rollout status deployment/myapp
```

### 수정안 3: Blue-Green 배포

```yaml
# blue-deployment.yaml (현재 버전)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: app
        image: myapp:v1

---

# green-deployment.yaml (새 버전)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: green
  template:
    metadata:
      labels:
        app: myapp
        version: green
    spec:
      containers:
      - name: app
        image: myapp:v2

---

# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # blue로 트래픽 라우팅
  ports:
  - port: 80
    targetPort: 3000
```

```bash
# green 배포
kubectl apply -f green-deployment.yaml
kubectl wait --for=condition=available --timeout=300s \
  deployment/myapp-green

# 헬스체크 및 테스트
kubectl run test-pod --rm -it --image=busybox -- \
  wget -q -O- http://myapp-green:3000/health

# green이 정상이면 서비스 스위칭
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

# 롤백 필요시
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'

# blue 제거
kubectl delete deployment myapp-blue
```

### 수정안 4: 캐나리 배포

```yaml
# 초기: 90% 기존 버전, 10% 새 버전
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - match:
    - headers:
        user-type:
          exact: canary
    route:
    - destination:
        host: myapp
        subset: v2
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 90
    - destination:
        host: myapp
        subset: v2
      weight: 10
```

### 수정안 5: 배포 전 검증

```bash
#!/bin/bash
# deploy.sh

set -e

IMAGE=$1
VERSION=$2

# 1. 이미지 스캔
docker scan $IMAGE

# 2. 단위 테스트
docker run --rm $IMAGE npm test

# 3. 통합 테스트
docker run -d --name test-app $IMAGE
sleep 5
curl http://localhost:3000/health || exit 1
docker stop test-app

# 4. 배포 준비
kubectl set image deployment/myapp \
  app=$IMAGE:$VERSION \
  --record

# 5. 배포 진행 상황 확인
kubectl rollout status deployment/myapp

echo "Deployment successful!"
```

### 수정안 6: 자동 롤백

```yaml
# deployment with automatic rollback
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  progressDeadlineSeconds: 600  # 10분 내에 배포 완료
  revisionHistoryLimit: 10      # 최근 10개 리비전만 유지
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v2
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          failureThreshold: 2
          periodSeconds: 5
```

```bash
# 배포 실패 시 자동 롤백 스크립트
#!/bin/bash

DEPLOYMENT="myapp"
MAX_WAIT=600

kubectl rollout status deployment/$DEPLOYMENT \
  --timeout=${MAX_WAIT}s

if [ $? -ne 0 ]; then
  echo "Deployment failed, rolling back..."
  kubectl rollout undo deployment/$DEPLOYMENT
  kubectl rollout status deployment/$DEPLOYMENT
fi
```

## 7단계: 검증

```bash
# 배포 검증
kubectl get deployment myapp -o wide

# pod 상태 확인
kubectl get pods -l app=myapp

# 헬스체크
kubectl exec -it <pod-name> -- curl localhost:3000/health

# 로그 확인
kubectl logs -f deployment/myapp
```

## 8단계: 재발 방지

1. **CI/CD 파이프라인**

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy
  - verify

test:
  stage: test
  script:
    - npm test

build:
  stage: build
  script:
    - docker build -t myapp:$CI_COMMIT_SHA .
    - docker push myapp:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/myapp app=myapp:$CI_COMMIT_SHA
    - kubectl rollout status deployment/myapp --timeout=10m

verify:
  stage: verify
  script:
    - kubectl run test-pod --rm -it --image=busybox -- wget -q -O- http://myapp/health
```

2. **모니터링**

```bash
# 배포 후 모니터링
kubectl rollout status deployment/myapp
kubectl top pods -l app=myapp
```

## 연결된 프롬프트 블록

- **PB-CL-18-deployment**: 배포 전략
- **PB-RP-17-rollback**: 롤백 시뮬레이션
- **PB-DG-18-deploy-logs**: 배포 로그 분석
- **PB-PA-18-deployment-strategy**: 배포 전략 구현
- **PB-VF-17-deploy-verify**: 배포 검증
