---
id: F-20
title: 시크릿 교체 문제 해결
pattern_id: P-20
error_ids: [E-58, E-59, E-60]
tech_scope: 보안, 시크릿 관리, Kubernetes
---

# 시크릿 교체 문제 해결

API 키, 데이터베이스 비밀번호 등의 시크릿 교체 중 발생하는 문제를 해결합니다.

## 1단계: 증상 고정

- "Unauthorized" 오류 증가
- 시크릿 교체 후 애플리케이션 오류
- "Invalid credentials"
- 서비스 간 통신 실패
- 특정 시간대 요청 실패

## 2단계: 재현

```bash
# 시크릿 확인
kubectl get secret myapp-secret -o yaml

# 시크릿 업데이트
kubectl create secret generic myapp-secret \
  --from-literal=DB_PASSWORD=newpassword \
  --dry-run=client -o yaml | kubectl apply -f -

# Pod이 자동으로 다시 시작되지 않음 → 구 시크릿 사용 지속
```

## 3단계: 범위 축소

시크릿 교체 문제:

1. **Pod 재시작 미흡**: Pod이 구 시크릿 계속 사용
2. **무중단 교체 부재**: 다운타임 발생
3. **백업 시크릿 부재**: 교체 실패 시 복구 불가
4. **암호화 미흡**: 시크릿이 평문으로 저장
5. **감사 로그 부재**: 교체 기록 없음

## 6단계: 수정안 선택

### 수정안 1: 시크릿 무중단 교체 (Rolling Update)

```bash
# 1단계: 새 시크릿 생성 (다른 이름)
kubectl create secret generic myapp-secret-v2 \
  --from-literal=DB_PASSWORD=newpassword \
  --from-literal=API_KEY=newkey

# 2단계: Pod 이미지 동시에 업데이트하여 새 시크릿 참조
kubectl patch deployment myapp --patch '
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: SECRET_VERSION
          value: "v2"
        volumeMounts:
        - name: secret
          mountPath: /etc/secret
      volumes:
      - name: secret
        secret:
          secretName: myapp-secret-v2
'

# 3단계: 배포 진행 상황 확인
kubectl rollout status deployment/myapp

# 4단계: 구 시크릿 제거
kubectl delete secret myapp-secret-v1
```

### 수정안 2: Blue-Green 시크릿 교체

```yaml
# deployment-blue.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
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
        image: myapp:latest
        envFrom:
        - secretRef:
            name: myapp-secret-blue

---

# deployment-green.yaml (새 시크릿 사용)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
spec:
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
        image: myapp:latest
        envFrom:
        - secretRef:
            name: myapp-secret-green
```

```bash
# green 배포 및 테스트
kubectl apply -f deployment-green.yaml
sleep 30
kubectl run test-pod --rm -it --image=busybox -- \
  wget -q -O- http://myapp-green/health

# 트래픽 전환
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'

# 롤백 필요시
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
```

### 수정안 3: External Secrets Operator 사용

```yaml
# ExternalSecrets로 외부 시크릿 자동 동기화
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "myapp-role"

---

apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secret
spec:
  refreshInterval: 1h  # 1시간마다 갱신
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: myapp-secret-synced
    creationPolicy: Owner
  data:
  - secretKey: db-password
    remoteRef:
      key: myapp/db-password
  - secretKey: api-key
    remoteRef:
      key: myapp/api-key

---

# 배포에서 사용
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        envFrom:
        - secretRef:
            name: myapp-secret-synced  # 자동으로 갱신됨
```

### 수정안 4: 시크릿 버전 관리

```yaml
# Sealed Secrets로 git에 암호화된 시크릿 저장
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: myapp-secret
spec:
  encryptedData:
    db-password: AgBx1q2... # 암호화된 값
    api-key: AgC2m3z...
  template:
    metadata:
      name: myapp-secret
    type: Opaque
```

```bash
# 시크릿 암호화
echo -n 'newpassword' | \
  kubeseal -f - -s > secret.yaml

# 배포
kubectl apply -f secret.yaml

# 이전 버전으로 롤백 가능
git revert commits...
kubectl apply -f secret.yaml
```

### 수정안 5: 감사 로그 및 모니터링

```bash
# kubectl audit log로 시크릿 접근 추적
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  resources:
  - group: ""
    resources: ["secrets"]
  omitStages:
  - RequestReceived
```

```javascript
// 시크릿 접근 로깅
async function accessSecret(name) {
  console.log(`[AUDIT] Secret accessed: ${name} at ${new Date()}`);
  // 로그 서버로 전송
  await sendAuditLog({
    action: 'secret_access',
    secret: name,
    user: process.env.USER,
    timestamp: new Date()
  });

  return await getSecret(name);
}
```

### 수정안 6: 자동 시크릿 교체 스크립트

```bash
#!/bin/bash
# rotate-secrets.sh

set -e

DEPLOYMENT="myapp"
SECRETS_VERSION=$(date +%s)

# 1. 새 시크릿 생성
kubectl create secret generic myapp-secret-${SECRETS_VERSION} \
  --from-literal=DB_PASSWORD=$(openssl rand -base64 32) \
  --from-literal=API_KEY=$(openssl rand -base64 32)

# 2. 배포 업데이트
kubectl set env deployment/${DEPLOYMENT} \
  SECRETS_VERSION=${SECRETS_VERSION}

# 3. 롤링 업데이트 모니터링
kubectl rollout status deployment/${DEPLOYMENT} --timeout=5m

# 4. 헬스 확인
sleep 10
for i in {1..5}; do
  if kubectl run test-pod --rm -it --image=busybox -- \
    wget -q -O- http://${DEPLOYMENT}:3000/health; then
    echo "Health check passed"
    break
  fi
  sleep 2
done

# 5. 이전 시크릿 정리
OLD_SECRETS=$(kubectl get secret -o name | grep myapp-secret | sort -r | tail -n +2)
for secret in $OLD_SECRETS; do
  kubectl delete $secret
done

echo "Secret rotation completed successfully"
```

## 연결된 프롬프트 블록

- **PB-CL-21-secrets**: 시크릿 관리
- **PB-RP-20-secret-test**: 시크릿 테스트
- **PB-DG-21-secret-audit**: 시크릿 감사
- **PB-PA-21-rotation**: 시크릿 교체 구현
- **PB-VF-20-secret-verify**: 시크릿 검증
