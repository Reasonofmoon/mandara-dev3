---
id: P-MG-03
title: 스키마 버전 관리 패턴
stage: Design
layer: Data
pattern_family: Persistence
tech_tags: [마이그레이션, 버전 관리, 충돌 해결, 롤백]
linked_errors: [E-MG-05, E-MG-06]
linked_flows: [F-MG-04]
linked_prompts: [PR-MG-03]
---

# 스키마 버전 관리 패턴

## 목표
데이터베이스 스키마 변경을 체계적으로 버전 관리하여 협력 개발과 롤백을 쉽게 합니다.

## 핵심 구조

### Prisma 마이그레이션

```bash
# 마이그레이션 생성
npx prisma migrate dev --name add_username

# 마이그레이션 상태 확인
npx prisma migrate status

# 본 환경에 마이그레이션 적용
npx prisma migrate deploy

# 마이그레이션 목록
npx prisma migrate history
```

### 마이그레이션 파일 구조

```
prisma/migrations/
├── 20240101120000_initial_schema/
│   └── migration.sql
├── 20240102150000_add_username/
│   └── migration.sql
├── 20240103100000_create_order_items/
│   └── migration.sql
└── migration_lock.toml
```

### 마이그레이션 파일 예제

```sql
-- 20240102150000_add_username/migration.sql
-- AddColumn
ALTER TABLE "User" ADD COLUMN "username" VARCHAR(255);

-- CreateIndex
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");
```

## 충돌 해결

### 병렬 마이그레이션 충돌

```bash
# 문제 상황
# main 브랜치: 20240102_add_username
# feature 브랜치: 20240102_add_bio

# 해결 방법 1: 마이그레이션 파일 이름 변경
npx prisma migrate resolve --rolled-back

# feature 브랜치에서
npx prisma migrate dev --name add_bio

# 해결 방법 2: 수동 충돌 해결
# 두 마이그레이션을 합치기
```

### 머지 전략

```typescript
// prisma/migrations 충돌 시
// 수동으로 마이그레이션 파일 합치기
// 또는 새 마이그레이션으로 통합

// 충돌 해결 후
npx prisma migrate status
npx prisma migrate deploy
```

## 버전 관리 전략

### Semantic Versioning

```
0.1.0 (초기)
├─ 0.1.1: 버그 수정 (롤백 가능)
├─ 0.2.0: 새 기능 (호환성 유지)
└─ 1.0.0: 구조 변경 (호환성 깨짐)
```

### 마이그레이션 네이밍

```bash
# 좋은 예제
20240101120000_initial_schema
20240102_add_user_username
20240103_create_order_items
20240104_add_order_items_relation

# 나쁜 예제
migration1
update
fix
```

## 개발/프로덕션 분리

```bash
# 개발 환경
npx prisma migrate dev --name feature

# 스테이징 환경
npx prisma migrate deploy --preview-feature

# 프로덕션 환경
npx prisma migrate deploy # CI/CD 파이프라인에서 자동 실행
```

### GitHub Actions CI/CD

```yaml
name: Database Migration

on: [push]

jobs:
  migrate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Check for migration status
        run: npx prisma migrate status

      - name: Deploy migrations (only on main)
        if: github.ref == 'refs/heads/main'
        env:
          DATABASE_URL: ${{ secrets.PROD_DATABASE_URL }}
        run: npx prisma migrate deploy
```

## 롤백 전략

```bash
# Prisma는 자동 롤백을 지원하지 않음
# 수동 롤백 필요

# 1. 롤백할 마이그레이션 확인
npx prisma migrate status

# 2. 이전 상태로 돌아가기 (수동)
# 데이터베이스 백업 후 이전 마이그레이션 상태로 복구

# 3. _prisma_migrations 테이블에서 마지막 항목 삭제
# (권장하지 않음)
```

### 안전한 롤백 전략

```typescript
// 마이그레이션 작성 시 UP/DOWN 모두 포함
-- 20240102_add_username/migration.sql

-- UP
ALTER TABLE "User" ADD COLUMN "username" VARCHAR(255);

-- DOWN (롤백 시)
-- ALTER TABLE "User" DROP COLUMN "username";

-- 이를 위해 호환성 있는 스크립트 작성
```

## 마이그레이션 테스트

```typescript
// tests/migrations.test.ts
import { execSync } from 'child_process';
import { PrismaClient } from '@prisma/client';

describe('Database Migrations', () => {
  let prisma: PrismaClient;

  beforeAll(async () => {
    // 테스트용 DB에 마이그레이션 적용
    execSync('npx prisma migrate deploy', {
      env: {
        ...process.env,
        DATABASE_URL: process.env.TEST_DATABASE_URL,
      },
    });

    prisma = new PrismaClient();
  });

  afterAll(async () => {
    await prisma.$disconnect();
  });

  it('should have username column', async () => {
    const result = await prisma.$queryRaw`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_name = 'User'
    `;

    const columnNames = result.map((row: any) => row.column_name);
    expect(columnNames).toContain('username');
  });

  it('should have unique constraint on username', async () => {
    await expect(
      prisma.user.create({
        data: {
          email: 'user1@test.com',
          username: 'john',
        },
      })
    ).resolves.toBeDefined();

    await expect(
      prisma.user.create({
        data: {
          email: 'user2@test.com',
          username: 'john',
        },
      })
    ).rejects.toThrow();
  });
});
```

## 최소 예제

```bash
# 1. 스키마 수정
# schema.prisma에 새 필드 추가

# 2. 마이그레이션 생성
npx prisma migrate dev --name field_name

# 3. 확인
npx prisma migrate status

# 4. 배포
npx prisma migrate deploy
```

## 모니터링

```typescript
// 마이그레이션 상태 체크
import { execSync } from 'child_process';

function checkMigrationStatus(): boolean {
  try {
    const status = execSync('npx prisma migrate status', {
      encoding: 'utf-8',
    });

    if (status.includes('Following migrations have been applied')) {
      return true;
    }

    return false;
  } catch (error) {
    console.error('Migration check failed:', error);
    return false;
  }
}

// 헬스 체크에 포함
app.get('/health', async (req, res) => {
  const migrationOk = checkMigrationStatus();

  if (!migrationOk) {
    return res.status(503).json({ status: 'unhealthy' });
  }

  res.json({ status: 'healthy' });
});
```

## 안티패턴

### 1. 수동 SQL 직접 실행

```bash
# ❌ 나쁜 예제
psql -U user -d mydb -c "ALTER TABLE User ADD COLUMN username VARCHAR(255);"
# Prisma 마이그레이션과 동기화 안 됨!

# ✅ 좋은 예제
# schema.prisma 수정 후
npx prisma migrate dev
```

### 2. 마이그레이션 파일 수정

```bash
# ❌ 나쁜 예제
# 이미 배포된 마이그레이션 파일 수정

# ✅ 좋은 예제
# 새로운 마이그레이션 생성
npx prisma migrate dev --name fix_previous_migration
```

## 연결된 오류

- **E-MG-05**: 마이그레이션 충돌
- **E-MG-06**: 롤백 불가능한 마이그레이션

## 연결된 플로우

- **F-MG-04**: 마이그레이션 배포 파이프라인

## 참고 자료

- Prisma Migrate: https://www.prisma.io/docs/orm/prisma-migrate/understanding-prisma-migrate
- Database Versioning: https://www.liquibase.org/get-started/best-practices
