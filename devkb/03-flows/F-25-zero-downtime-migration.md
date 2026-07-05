---
id: F-25
title: 무중단 마이그레이션 실행
pattern_id: P-25
error_ids: [E-73, E-74, E-75]
tech_scope: 데이터베이스 마이그레이션, 배포 전략, 무중단 업데이트
---

# 무중단 마이그레이션 실행

데이터베이스 스키마 변경 중 서비스 다운타임 없이 마이그레이션을 수행합니다.

## 1단계: 증상 고정

- 마이그레이션 중 서비스 다운타임 발생
- "Relation does not exist" 오류
- 새 컬럼이 없어 애플리케이션 오류
- 데이터 손실 위험
- 롤백 불가능

## 2단계: 재현

```bash
# ❌ 위험한 마이그레이션
ALTER TABLE users ADD COLUMN email VARCHAR(255) NOT NULL;
# → 기존 행은 email 값이 없어 오류 발생

# ❌ 다운타임 발생
ALTER TABLE posts RENAME COLUMN content TO body;
# → 시간이 오래 걸리고 테이블 락 발생
```

## 6단계: 수정안 선택

### 수정안 1: 무중단 마이그레이션 패턴

```sql
-- 1단계: 새 컬럼 추가 (기본값 포함)
ALTER TABLE users ADD COLUMN email VARCHAR(255);
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false;

-- 2단계: 애플리케이션 배포 (구 컬럼과 신 컬럼 모두 사용)
-- 애플리케이션 코드:
-- INSERT INTO users (name, email) VALUES (?, ?)
-- UPDATE users SET email = ? WHERE id = ?

-- 3단계: 데이터 마이그레이션 (백그라운드)
UPDATE users SET email = 'migrated@example.com'
WHERE email IS NULL;

-- 4단계: 제약 조건 추가
ALTER TABLE users ALTER COLUMN email SET NOT NULL;

-- 5단계: 애플리케이션 배포 (신 컬럼만 사용)

-- 6단계: 구 컬럼 제거
-- 필요시 나중에 제거
ALTER TABLE users DROP COLUMN old_email;
```

### 수정안 2: Prisma 무중단 마이그레이션

```prisma
// schema.prisma

// 1단계: 새 필드 추가 (선택사항)
model User {
  id Int @id @default(autoincrement())
  name String
  email String?  // nullable로 추가
}

// 마이그레이션 생성
// prisma migrate dev --name add_email_field
```

```javascript
// 2단계: 애플리케이션 업데이트
app.post('/users', async (req, res) => {
  const user = await prisma.user.create({
    data: {
      name: req.body.name,
      email: req.body.email  // 새 필드에 저장
    }
  });
  res.json(user);
});

// 3단계: 데이터 마이그레이션 (별도 스크립트)
async function migrateEmails() {
  const usersWithoutEmail = await prisma.user.findMany({
    where: { email: null }
  });

  for (const user of usersWithoutEmail) {
    await prisma.user.update({
      where: { id: user.id },
      data: { email: generateDefaultEmail(user.id) }
    });
  }

  console.log('Email migration completed');
}

// 4단계: 제약 조건 추가
// schema.prisma: email String (NOT NULL로 변경)
// prisma migrate dev --name make_email_required
```

### 수정안 3: 테이블 전환 (Big Alter)

```sql
-- 대용량 테이블에서 컬럼 추가/제거 시 사용

-- 1단계: 새 테이블 생성
CREATE TABLE users_new (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  email VARCHAR(255)
);

-- 2단계: 데이터 복사 (배경)
INSERT INTO users_new SELECT id, name, email FROM users;

-- 3단계: 인덱스 추가
CREATE INDEX idx_users_new_email ON users_new(email);

-- 4단계: 구 테이블에 트리거 설정 (새 데이터 동기화)
CREATE TRIGGER users_insert AFTER INSERT ON users
FOR EACH ROW
BEGIN
  INSERT INTO users_new VALUES (NEW.id, NEW.name, NEW.email);
END;

-- 5단계: 애플리케이션 배포 (두 테이블 모두 쓰기)

-- 6단계: 구 테이블 제거, 신 테이블 이름 변경
ALTER TABLE users RENAME TO users_old;
ALTER TABLE users_new RENAME TO users;

-- 7단계: 구 테이블 삭제 (필요시)
DROP TABLE users_old;
```

### 수정안 4: 카나리 배포 + 점진적 마이그레이션

```yaml
# 1단계: 신 버전 배포 (10%)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-v2
spec:
  replicas: 1  # 전체 중 10%
  template:
    spec:
      containers:
      - name: app
        image: myapp:v2
        env:
        - name: DATABASE_VERSION
          value: "v2"  # 신 스키마 사용

---

# 트래픽 분배 (90% v1, 10% v2)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - route:
    - destination:
        host: myapp-v1
      weight: 90
    - destination:
        host: myapp-v2
      weight: 10
```

```javascript
// v2 애플리케이션: 신 스키마 호환
async function createUser(name, email) {
  return await prisma.user.create({
    data: {
      name,
      email  // 새 필드
    }
  });
}
```

### 수정안 5: 마이그레이션 검증

```bash
#!/bin/bash
# migrate.sh

set -e

echo "Starting zero-downtime migration..."

# 1단계: 백업
pg_dump mydb > backup_$(date +%s).sql

# 2단계: 마이그레이션 (배경)
psql mydb < migration.sql &
MIGRATION_PID=$!

# 3단계: 애플리케이션 배포
kubectl apply -f deployment-v2.yaml
kubectl rollout status deployment/myapp-v2

# 4단계: 마이그레이션 완료 대기
wait $MIGRATION_PID
if [ $? -ne 0 ]; then
  echo "Migration failed, rolling back..."
  psql mydb < rollback.sql
  exit 1
fi

# 5단계: 트래픽 전환
kubectl patch service myapp -p '{"spec":{"selector":{"version":"v2"}}}'

# 6단계: v1 제거
kubectl delete deployment myapp-v1

echo "Migration completed successfully"
```

### 수정안 6: 롤백 계획

```javascript
// 마이그레이션 롤백 스크립트
async function rollbackMigration() {
  // 1. 구 버전 배포
  await deploVersion('v1');

  // 2. 애플리케이션 재시작
  await restartServers();

  // 3. 데이터베이스 롤백 (필요시)
  if (requiresDbRollback) {
    await execSQL('ROLLBACK TO migration_v1');
  }

  // 4. 확인
  await healthCheck();
}
```

## 연결된 프롬프트 블록

- **PB-CL-26-migration**: 마이그레이션 전략
- **PB-RP-25-migration-test**: 마이그레이션 테스트
- **PB-DG-26-migration-plan**: 마이그레이션 계획
- **PB-PA-26-zero-downtime**: 무중단 구현
- **PB-VF-25-migration-verify**: 마이그레이션 검증
