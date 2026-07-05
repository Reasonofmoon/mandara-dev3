---
id: F-23
title: 권한 문제 해결
pattern_id: P-23
error_ids: [E-67, E-68, E-69]
tech_scope: 파일 권한, 접근 제어, Linux 권한
---

# 권한 문제 해결

파일 권한, 디렉토리 접근, 프로세스 권한 문제를 해결합니다.

## 1단계: 증상 고정

- "Permission denied" 오류
- "EACCES" 오류
- 파일을 읽을 수 없음
- 디렉토리를 생성할 수 없음
- Docker 컨테이너가 파일에 접근 불가

## 6단계: 수정안 선택

### 수정안 1: 파일 권한 설정

```bash
# 파일 권한 확인
ls -la myfile.txt
# -rw-r--r-- 1 user group 1024 Jan 15 10:00 myfile.txt

# 소유자만 읽기
chmod 400 myfile.txt

# 소유자는 읽기/쓰기, 그룹과 타인은 읽기
chmod 644 myfile.txt

# 소유자는 모든 권한, 그룹과 타인은 읽기/실행
chmod 755 myfile.txt

# 특정 권한 추가
chmod +x myfile.sh  # 실행 권한 추가
chmod u+w myfile    # 소유자에게 쓰기 권한 추가
```

### 수정안 2: 소유권 변경

```bash
# 소유자 변경
chown user:group myfile.txt

# 재귀적 변경
chown -R user:group /app/

# 현재 사용자로 변경
chown $(whoami) myfile.txt
```

### 수정안 3: Docker 컨테이너 권한

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

# 작업 수행
COPY . .
RUN npm ci

# 보안: non-root 사용자 생성 및 전환
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# 파일 소유권 변경
RUN chown -R appuser:appgroup /app

# non-root 사용자로 전환
USER appuser

EXPOSE 3000
CMD ["node", "index.js"]
```

### 수정안 4: Volume 권한 (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      securityContext:
        fsGroup: 1000  # Volume의 모든 파일을 이 그룹으로 설정
      containers:
      - name: app
        image: myapp:latest
        securityContext:
          runAsUser: 1000      # 이 UID로 실행
          runAsNonRoot: true   # non-root 강제
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: app-data
          mountPath: /app/data
      volumes:
      - name: app-data
        emptyDir: {}
```

### 수정안 5: 임시 파일 권한

```bash
# /tmp 디렉토리 권한
chmod 1777 /tmp  # sticky bit 포함

# 애플리케이션 임시 디렉토리
mkdir -p /app/tmp
chmod 777 /app/tmp  # 모두 읽기/쓰기/실행
```

### 수정안 6: 권한 감사

```bash
# 위험한 권한 파일 찾기
find /app -perm 777  # 모두에게 모든 권한

# 소유자 확인
ls -l /app/config.json

# 권한 설정
chmod 600 /app/config.json  # 소유자만 읽기/쓰기
```

## 연결된 프롬프트 블록

- **PB-CL-24-permissions**: 권한 개념
- **PB-RP-23-permission-test**: 권한 테스트
- **PB-DG-24-permission-audit**: 권한 감사
- **PB-PA-24-permission-fix**: 권한 설정
- **PB-VF-23-permission-verify**: 권한 검증
