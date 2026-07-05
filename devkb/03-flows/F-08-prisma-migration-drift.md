---
id: F-08
title: Prisma 마이그레이션 드리프트 해결
pattern_id: P-08
error_ids: [E-22, E-23, E-24]
tech_scope: Prisma, 데이터베이스 마이그레이션, 스키마 동기화
---

# Prisma 마이그레이션 드리프트 해결

Prisma 스키마와 데이터베이스 간 불일치(드리프트)로 인한 문제를 해결합니다.

## 1단계: 증상 고정

오류 메시지:
- "The database schema is not in sync with the Prisma schema"
- "Drift detected"
- "Database migration failed"
- `prisma migrate dev` 실패
- `prisma db push` 오류

## 2단계: 재현

```bash
# 드리프트 감지
prisma migrate status

# 출력 예:
# ✔ Drift detected

# 또는 강제로 실패 상황 만들기
# 1. schema.prisma 수정
# 2. 직접 SQL로 데이터베이스 변경
# 3. migrate dev 실행
```

## 3단계: 범위 축소

마이그레이션 드리프트 유형:

1. **스키마 변경 미적용**: schema.prisma는 수정했으나 DB는 미적용
2. **수동 DB 변경**: SQL로 직접 DB 변경해서 스키마와 불일치
3. **마이그레이션 파일 손상**: .prisma 마이그레이션 파일 손상 또는 삭제
4. **마이그레이션 실패**: 이전 마이그레이션이 실패했으나 미처리
5. **환경 간 불일치**: dev/prod 데이터베이스 마이그레이션 상태 다름

## 4단계: 증거 수집

```bash
# 마이그레이션 상태 확인
prisma migrate status

# 드리프트 자세히 보기
prisma migrate diff --from-empty --to-schema-datamodel

# 현재 데이터베이스 스키마 확인
prisma db pull

# 마이그레이션 히스토리 확인
ls -la prisma/migrations/
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| migrate dev 누락 | 매우높음 | 낮음 |
| 수동 SQL 변경 | 높음 | 높음 |
| 마이그레이션 파일 누락 | 높음 | 높음 |
| DB 백업 복원 | 중간 | 높음 |
| 환경 변수 오류 | 중간 | 낮음 |

## 6단계: 수정안 선택

### 수정안 1: 스키마 변경 후 마이그레이션

```bash
# 1. schema.prisma 파일 수정
# 예: User 모델에 새로운 필드 추가

# 2. 마이그레이션 생성
prisma migrate dev --name add_email_to_user

# 출력:
# ✔ Created migration: 20240315_add_email_to_user

# 3. 마이그레이션 자동 적용됨
# ✔ Database synced, migrations table created, wrote migration file

# 4. Prisma 클라이언트 재생성됨
# ✔ Generated Prisma Client
```

### 수정안 2: 드리프트 복구 (프로토타입 모드)

```bash
# 프로토타입 모드: db push 사용 (개발 환경만)
# ⚠️ 데이터 손실 가능, dev 환경에서만 사용

# 1. schema.prisma 수정
# 2. 변경사항 데이터베이스에 즉시 적용
prisma db push

# 또는 드리프트 검토 후 적용
prisma db push --skip-generate --print
```

### 수정안 3: 수동 DB 변경 시 복구

```bash
# 상황: SQL로 직접 변경하거나 백업 복원 후 드리프트 발생

# 옵션 1: 현재 DB 스키마를 schema.prisma로 가져오기
prisma db pull

# 옵션 2: schema.prisma를 DB에 적용 (⚠️ 데이터 손실 가능)
# a) 모든 마이그레이션 리셋 (destructive)
prisma migrate reset

# b) 특정 지점으로 되돌리기
# prisma/migrations 디렉토리에서 이후 마이그레이션 삭제
rm -rf prisma/migrations/[timestamp]_*

# c) 드리프트 복구
prisma migrate resolve --rolled-back [migration_name]
```

### 수정안 4: 마이그레이션 리셋 (개발 환경)

```bash
# ⚠️ 모든 데이터 삭제됨 - 개발 환경에서만 사용

# 1. 현재 스키마와 일치하도록 리셋
prisma migrate reset

# 프롬프트:
# Are you sure? All data will be lost.
# → y

# 결과:
# ✔ Successfully reset your database
# ✔ Ran all pending migrations
# ✔ Seeded the database with seed.js data (if exists)
```

### 수정안 5: 프로덕션 환경 마이그레이션

```bash
# 프로덕션: migrate deploy 사용 (데이터 손실 없음)

# 1. 개발 환경에서 마이그레이션 파일 생성
# 로컬 schema.prisma 수정
prisma migrate dev --name your_migration_name

# 2. 마이그레이션 파일 커밋
git add prisma/migrations/
git commit -m "Add migration: your_migration_name"

# 3. CI/CD 파이프라인에서 적용
prisma migrate deploy

# 또는 수동으로
npx prisma migrate deploy
```

### 수정안 6: schema.prisma 예제

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String
  posts Post[]

  @@map("users")
}

model Post {
  id    Int     @id @default(autoincrement())
  title String
  content String?
  published Boolean @default(false)
  author    User    @relation(fields: [authorId], references: [id], onDelete: Cascade)
  authorId  Int
  comments  Comment[]

  @@map("posts")
}

model Comment {
  id    Int     @id @default(autoincrement())
  text  String
  post  Post    @relation(fields: [postId], references: [id], onDelete: Cascade)
  postId Int
  author User?   @relation(fields: [authorId], references: [id])
  authorId Int?

  @@map("comments")
}
```

### 수정안 7: 마이그레이션 파일 정리

```bash
# 빈 또는 불필요한 마이그레이션 제거
# prisma/migrations/[timestamp]_empty/migration.sql 삭제

# 마이그레이션 이력 정리 (선택)
prisma migrate resolve --rolled-back [migration_name]

# 마이그레이션 이름 확인
prisma migrate resolve --list
```

## 7단계: 검증

```bash
# 마이그레이션 상태 확인
prisma migrate status

# 출력:
# Database schema is up to date. All migrations have been applied.

# 마이그레이션 적용 확인
prisma db pull

# 현재 스키마와 일치하는지 검증
prisma validate
```

```javascript
// 애플리케이션 시작 시 검증
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function validateDatabase() {
  try {
    await prisma.$queryRaw`SELECT 1`;
    console.log('✔ Database connection successful');
  } catch (error) {
    console.error('✗ Database connection failed:', error);
    process.exit(1);
  }
}

validateDatabase();
```

## 8단계: 재발 방지

1. **마이그레이션 워크플로우**

```bash
# 1. schema.prisma 수정
# 2. 마이그레이션 생성
prisma migrate dev --name describe_change

# 3. 검토 및 테스트
npm test

# 4. 커밋
git add prisma/migrations/
git commit -m "Add migration: describe_change"

# 5. 배포
# CI/CD에서 prisma migrate deploy 실행
```

2. **.gitignore 확인**

```gitignore
# .gitignore
.env
.env.local

# ✔ 마이그레이션 파일은 커밋해야 함
# prisma/migrations/ 제외하면 안 됨!
```

3. **환경별 설정**

```bash
# .env.development
DATABASE_URL="postgresql://user:pass@localhost:5432/dev_db"

# .env.production
DATABASE_URL="postgresql://user:pass@prod-server:5432/prod_db"

# .env.test
DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
```

4. **자동 마이그레이션 체크**

```javascript
// src/lib/prisma.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log: ['query', 'error', 'warn'],
  });

if (process.env.NODE_ENV !== 'production')
  globalForPrisma.prisma = prisma;

// 애플리케이션 시작 시 자동 마이그레이션
if (process.env.AUTO_MIGRATE === 'true') {
  import('./migrate').then(({ migrate }) => {
    migrate();
  });
}
```

## 연결된 프롬프트 블록

- **PB-CL-09-schema-design**: Prisma 스키마 설계
- **PB-RP-08-migration-test**: 마이그레이션 테스트
- **PB-DG-09-schema-drift**: 스키마 드리프트 진단
- **PB-PA-09-migration-creation**: 마이그레이션 파일 생성
- **PB-VF-08-migration-verify**: 마이그레이션 검증
