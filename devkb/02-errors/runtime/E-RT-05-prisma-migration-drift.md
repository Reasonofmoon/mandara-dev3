---
id: E-RT-05
title: Prisma 마이그레이션 드리프트
error_class: Runtime
symptoms:
  - 마이그레이션 적용 불가
  - 스키마와 DB 불일치
  - 프로덕션 배포 실패
exact_messages:
  - "The database schema is not in sync with the Prisma schema"
  - "Drift detected: the database schema does not match the Prisma schema"
  - "Migration cannot be applied"
tech_tags:
  - Prisma
  - Database
  - Migration
  - Schema Management
linked_patterns: []
linked_flows: []
---

# Prisma 마이그레이션 드리프트

## 증상
Prisma 스키마와 실제 데이터베이스 스키마가 동기화되지 않으면 드리프트가 발생합니다. 마이그레이션을 적용할 수 없거나 배포가 실패합니다.

## 정확한 에러 메시지
```
The database schema is not in sync with the Prisma schema
Drift detected: the database schema does not match the Prisma schema
Migration cannot be applied: the database is not empty
Your database is not in sync with your schema
```

## 발생 맥락
```
시나리오 1: 수동 DB 수정
- DBeaver, pgAdmin 등에서 직접 테이블 수정
- Prisma schema는 업데이트 안 함
- npx prisma migrate dev → 드리프트 감지

시나리오 2: 마이그레이션 스킵
- git에서 마이그레이션 파일 충돌
- 일부 마이그레이션만 적용
- DB 상태가 예상과 다름

시나리오 3: 프로덕션 DB 직접 수정
- 긴급 상황에서 직접 수정
- Prisma schema 미업데이트
- 다음 배포 시 마이그레이션 실패
```

## 필요한 증거
- Prisma migration 에러 메시지
- 현재 Prisma schema
- 데이터베이스 실제 스키마
- migration 히스토리

## 의심 원인
1. 수동으로 데이터베이스 스키마 수정
2. 마이그레이션 파일 손실 또는 누락
3. 마이그레이션이 부분적으로만 적용됨
4. Prisma schema 변경 후 마이그레이션 미생성
5. 협력자 간 schema 버전 불일치
6. 데이터베이스 복제 또는 복원 후 부분적 동기화

## 빠운 해결법

### 1. 드리프트 상태 확인
```bash
# 현재 상태 확인
npx prisma migrate status

# 상세 드리프트 정보
npx prisma schema diagnose
```

### 2. 드리프트 복구 (개발 환경)
```bash
# 마이그레이션 히스토리 초기화 (모든 데이터 삭제!)
npx prisma migrate reset

# 또는 단계별
# 1. 모든 마이그레이션 롤백
npx prisma migrate resolve --rolled-back 20240101120000_init

# 2. 마이그레이션 재적용
npx prisma migrate dev
```

### 3. 수동으로 DB 스키마 수정
```bash
# DB 푸시 (마이그레이션 없이 직접 적용)
npx prisma db push

# 위험: 기존 데이터 손실 가능
npx prisma db push --force-reset
```

### 4. 프로덕션 복구
```bash
# 1단계: 현재 상태 파악
npx prisma migrate status --environment-name production

# 2단계: 마이그레이션 적용할 수 없으면 수동으로 해결
# - 데이터베이스 백업
# - SQL로 스키마 수정
# - 마이그레이션 재생성

# 3단계: 마이그레이션 히스토리 재설정 (신중하게!)
npx prisma migrate resolve --rolled-back <migration_name>
```

### 5. 스키마 재생성 (introspection)
```bash
# 현재 DB에서 Prisma schema 생성
npx prisma db pull

# 생성된 schema.prisma 검토 및 수정
# 그 후 마이그레이션 생성
npx prisma migrate dev --name sync_schema
```

### 6. 마이그레이션 충돌 해결
```bash
# 충돌하는 마이그레이션 수동 해결
# prisma/migrations/ 디렉토리에서 conflict markers 확인

# 해결 후 마이그레이션 적용
npx prisma migrate deploy

# 또는 해당 마이그레이션 강제 마킹
npx prisma migrate resolve --applied <migration_name>
```

### 7. CI/CD에서 안전한 마이그레이션
```bash
# 배포 전 마이그레이션 검증
npx prisma migrate status

# 상태에 따라 처리
if [ $? -eq 0 ]; then
  echo "Database is in sync"
else
  echo "Migration required"
  npx prisma migrate deploy
fi
```

### 8. 마이그레이션 파일 생성 팁
```bash
# schema 변경 후 항상 마이그레이션 생성
npx prisma migrate dev --name add_user_email_field

# 마이그레이션만 생성 (자동 적용 안 함)
npx prisma migrate dev --name add_user_email_field --create-only
```

### 9. 데이터 보존하며 드리프트 수정
```bash
# 1. 현재 데이터 내보내기
pg_dump database > backup.sql

# 2. 스키마만 추출
pg_dump --schema-only database > schema.sql

# 3. DB 초기화
dropdb database
createdb database

# 4. Prisma 마이그레이션 재적용
npx prisma migrate deploy

# 5. 데이터 복원
psql database < backup.sql
```

### 10. 베스트 프랙티스
```typescript
// schema.prisma
// 주석으로 의도 명시
model User {
  id    Int     @id @default(autoincrement())
  /// 사용자의 이메일 - 변경하면 마이그레이션 필요
  email String  @unique
  name  String?
  createdAt DateTime @default(now())
}
```

```bash
# 마이그레이션 생성 전 항상 테스트
npx prisma migrate dev --name test_migration

# 스키마 검증
npx prisma validate

# 데이터베이스 연결 확인
npx prisma db execute --stdin < /dev/null
```

## 연결된 패턴
- E-BC-07-prisma-generate-fail
- E-DO-04-migration-order-error

## 연결된 플로우
- 데이터베이스 마이그레이션 플로우
- 배포 안전성 플로우

## 재발 방지
1. 데이터베이스는 항상 Prisma로만 수정
2. schema.prisma 변경 후 즉시 마이그레이션 생성
3. 모든 마이그레이션을 git에 커밋
4. 프로덕션 배포 전 마이그레이션 검증
5. 긴급 수정 필요 시 수정 후 즉시 schema 동기화
6. 정기적으로 `prisma migrate status` 확인
7. DB 백업 후 마이그레이션 실행
