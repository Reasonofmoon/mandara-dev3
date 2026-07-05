---
id: E-RT-06
title: 연결 거부됨
error_class: Runtime
symptoms:
  - 데이터베이스 연결 실패
  - 서버 연결 불가
  - ECONNREFUSED 에러
exact_messages:
  - "Error: connect ECONNREFUSED 127.0.0.1:5432"
  - "getaddrinfo ENOTFOUND database.example.com"
  - "Connection refused at 127.0.0.1:27017"
tech_tags:
  - Networking
  - Database
  - Connection
  - Troubleshooting
linked_patterns: []
linked_flows: []
---

# 연결 거부됨

## 증상
데이터베이스, 캐시 서버, 또는 외부 API 서버에 연결할 수 없습니다. 포트가 닫혀있거나 서비스가 실행되지 않으면 발생합니다.

## 정확한 에러 메시지
```
Error: connect ECONNREFUSED 127.0.0.1:5432
getaddrinfo ENOTFOUND database.example.com
Connection refused at 127.0.0.1:27017
Error: getaddrinfo EAGAIN database.local
```

## 발생 맥락
```typescript
// 잘못된 예 1: 서비스 미실행
const client = new MongoClient('mongodb://localhost:27017');
await client.connect();  // ❌ MongoDB가 실행 안 됨

// 잘못된 예 2: 잘못된 호스트
const connection = createConnection({
  host: 'database.example.com',  // ❌ 호스트명 오타
  port: 5432
});

// 잘못된 예 3: 방화벽 차단
const db = new DatabaseClient({
  url: 'postgres://user:pass@prod-db.example.com:5432/mydb'
  // ❌ 방화벽이 외부 연결 차단
});
```

## 필요한 증거
- 에러 메시지 (호스트, 포트)
- 네트워크 연결 확인 결과
- 서비스 상태
- 방화벽/보안 그룹 설정

## 의심 원인
1. 데이터베이스 또는 서비스가 실행되지 않음
2. 잘못된 호스트명 또는 IP
3. 잘못된 포트
4. 방화벽이 연결 차단
5. 네트워크 연결 불가
6. DNS 해석 실패
7. 클라우드 보안 그룹 설정 오류

## 빠른 해결법

### 1. 서비스 상태 확인
```bash
# PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# MongoDB
sudo systemctl status mongod
sudo systemctl start mongod

# Redis
sudo systemctl status redis-server
sudo systemctl start redis-server

# MySQL
sudo systemctl status mysql
sudo systemctl start mysql

# Docker에서 실행 중인 경우
docker ps  # 실행 중인 컨테이너 확인
docker start container_name
```

### 2. 포트 연결 테스트
```bash
# Linux/Mac: nc (netcat)
nc -zv localhost 5432
nc -zv database.example.com 5432

# 또는 telnet
telnet localhost 5432

# 또는 curl (HTTP 포트)
curl -v http://localhost:3000

# Windows: Test-NetConnection
Test-NetConnection -ComputerName localhost -Port 5432
```

### 3. 호스트명 해석 확인
```bash
# DNS 해석
nslookup database.example.com
dig database.example.com

# 또는
host database.example.com

# ping 테스트
ping database.example.com
```

### 4. 방화벽 확인
```bash
# Linux: iptables
sudo iptables -L -n | grep 5432

# UFW (Ubuntu)
sudo ufw status
sudo ufw allow 5432/tcp

# macOS: pf
sudo pfctl -s nat

# Windows: Windows Defender Firewall
netsh advfirewall show allprofiles
```

### 5. Docker로 서비스 실행
```bash
# PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15

# MongoDB
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  mongo:latest

# Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:latest
```

### 6. 연결 문자열 확인
```typescript
// ❌ 잘못된 예
const DATABASE_URL = 'postgresql://user:pass@localhost:5432/db';

// ✅ 올바른 예
const DATABASE_URL = 'postgresql://user:password@localhost:5432/mydb';

// 환경 변수 확인
console.log(process.env.DATABASE_URL);

// URL 파싱
const url = new URL(process.env.DATABASE_URL);
console.log({
  host: url.hostname,
  port: url.port,
  database: url.pathname.slice(1)
});
```

### 7. 재시도 로직 추가
```typescript
async function connectWithRetry(
  connect: () => Promise<any>,
  maxAttempts = 5,
  delayMs = 2000
) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      console.log(`Connection attempt ${attempt}/${maxAttempts}...`);
      return await connect();
    } catch (error) {
      if (attempt === maxAttempts) {
        throw error;
      }
      console.log(`Failed, retrying in ${delayMs}ms...`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

const db = await connectWithRetry(() =>
  createConnection(process.env.DATABASE_URL)
);
```

### 8. 클라우드 환경 (AWS/GCP/Azure)
```bash
# AWS RDS 보안 그룹 확인
aws ec2 describe-security-groups --group-ids sg-xxxxx

# 인바운드 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0

# 또는 Google Cloud SQL
gcloud sql instances describe my-instance --format='get(ipAddresses[0].ipAddress)'
```

### 9. 로컬 개발 VS 프로덕션
```typescript
// 환경별 다른 host 사용
const DB_HOST = process.env.NODE_ENV === 'production'
  ? process.env.PROD_DB_HOST
  : 'localhost';

const DB_PORT = process.env.NODE_ENV === 'production'
  ? 5432
  : 5433;  // 로컬에서는 다른 포트

const CONNECTION_STRING =
  `postgresql://user:pass@${DB_HOST}:${DB_PORT}/db`;
```

### 10. 디버깅
```bash
# 연결 시도 로그 확인
DEBUG=* npm start

# 또는 특정 모듈
DEBUG=postgres npm start

# 네트워크 추적
tcpdump -i any -n host database.example.com

# strace로 시스템 콜 모니터링
strace -e openat,connect node app.js
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-RT-01-cannot-read-undefined

## 연결된 플로우
- 데이터베이스 연결 플로우
- 네트워크 문제 해결 플로우

## 재발 방지
1. 개발 환경에 필요한 모든 서비스 문서화
2. docker-compose.yml로 의존성 서비스 관리
3. 연결 문자열 검증 로직 추가
4. 연결 실패 시 재시도 로직 구현
5. 헬스 체크 엔드포인트 추가
6. 환경별 호스트/포트 명확히 분리
7. 모니터링으로 연결 문제 조기 감지
