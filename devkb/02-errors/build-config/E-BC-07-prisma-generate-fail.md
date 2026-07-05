---
id: E-BC-07
title: Prisma 생성 실패
error_class: Build-Config
symptoms:
  - Prisma Client 생성 안 됨
  - 스키마 파싱 실패
  - 데이터베이스 연결 오류
exact_messages:
  - "Error parsing Prisma schema"
  - "Prisma schema validation error"
  - "Failed to fetch necessary information from the database"
tech_tags:
  - Prisma
  - ORM
  - Database
  - Schema
linked_patterns: []
linked_flows: []
---

# Prisma 생성 실패

## 증상
`prisma generate` 명령이 실패하면 Prisma Client를 사용할 수 없습니다. 스키마 오류, 데이터베이스 연결 실패, 또는 설정 문제가 원인입니다.

## 정확한 에러 메시지
```
Error parsing Prisma schema
Prisma schema validation error: field 'id' is missing from model 'User'
Failed to fetch necessary information from the database
error: Introspection failed
datasource db: Could not connect to database
```

## 발생 맥락
```prisma
// schema.prisma - 잘못된 예

// 예 1: 문법 오류
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String
  posts Post[]  // ❌ 관계 정의 미완료

model Post {
  id    Int     @id @default(autoincrement())
  title String
  // ❌ userId 필드 또는 @relation 누락
}

// 예 2: 잘못된 데이터소스
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")  // ❌ 환경 변수 미설정
}

// 예 3: 유효하지 않은 속성
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique @validate(email)  // ❌ @validate는 없음
  role  String  @default("user") @invalid  // ❌ @invalid는 없음
}
```

## 필요한 증거
- schema.prisma 파일
- .env 파일의 DATABASE_URL
- Prisma 에러 메시지
- 데이터베이스 연결 상태

## 의심 원인
1. Prisma 스키마 문법 오류
2. DATABASE_URL 환경 변수 누락
3. 데이터베이스 연결 실패
4. 데이터베이스가 실행 중이 아님
5. 관계 정의 오류
6. 유효하지 않은 Prisma 속성
7. Prisma CLI 버전 오류

## 빠른 해결법

### 1. 기본 스키마 구조
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"  // sqlite, mysql, etc.
  url      = env("DATABASE_URL")
}

model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String?
  role  String  @default("user")
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  posts Post[]
}

model Post {
  id    Int     @id @default(autoincrement())
  title String
  content String?
  published Boolean @default(false)
  authorId Int
  author User @relation(fields: [authorId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([authorId])
}
```

### 2. 환경 변수 설정
```bash
# .env
DATABASE_URL="postgresql://user:password@localhost:5432/mydatabase"

# SQLite
DATABASE_URL="file:./dev.db"

# MySQL
DATABASE_URL="mysql://user:password@localhost:3306/mydatabase"
```

### 3. Prisma 생성 및 마이그레이션
```bash
# 1. 스키마 검증
npx prisma validate

# 2. 클라이언트 생성
npx prisma generate

# 3. 데이터베이스 마이그레이션
npx prisma migrate dev --name init

# 4. 데이터베이스 푸시 (개발 환경)
npx prisma db push
```

### 4. 관계 정의 올바르게
```prisma
// 1:N 관계
model User {
  id    Int     @id @default(autoincrement())
  name  String
  posts Post[]  // 역방향 관계
}

model Post {
  id      Int     @id @default(autoincrement())
  title   String
  userId  Int
  user    User    @relation(fields: [userId], references: [id])

  @@index([userId])
}

// N:N 관계 (암시적)
model Student {
  id       Int        @id @default(autoincrement())
  name     String
  courses  Course[]
}

model Course {
  id       Int       @id @default(autoincrement())
  name     String
  students Student[]
}

// N:N 관계 (명시적 - 조인 테이블)
model StudentCourse {
  id        Int     @id @default(autoincrement())
  studentId Int
  courseId  Int
  student   Student @relation(fields: [studentId], references: [id], onDelete: Cascade)
  course    Course  @relation(fields: [courseId], references: [id], onDelete: Cascade)

  @@unique([studentId, courseId])
  @@index([courseId])
}
```

### 5. 데이터베이스 연결 확인
```bash
# PostgreSQL 연결 테스트
psql -U user -d mydatabase -h localhost

# MySQL 연결 테스트
mysql -u user -p -h localhost mydatabase

# 또는 Prisma Studio로 확인
npx prisma studio
```

### 6. 스키마 검증
```bash
# 스키마 유효성 확인
npx prisma validate

# 상세한 오류 정보
npx prisma validate --verbose
```

### 7. Introspection (기존 DB에서 스키마 생성)
```bash
# 기존 데이터베이스에서 스키마 자동 생성
npx prisma db pull

# 그 후 generate
npx prisma generate
```

### 8. 마이그레이션 초기화
```bash
# 마이그레이션 히스토리 초기화 (개발 환경만!)
npx prisma migrate reset

# 스키마 푸시 (마이그레이션 없이)
npx prisma db push --skip-generate
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-ST-06-prisma-type-error
- E-RT-05-prisma-migration-drift

## 연결된 플로우
- Prisma 초기화 플로우
- 데이터베이스 마이그레이션 플로우

## 재발 방지
1. schema.prisma 작성 후 `prisma validate` 실행
2. DATABASE_URL 환경 변수 설정 확인
3. 빌드 전에 `npx prisma generate` 실행
4. CI/CD에 스키마 검증 단계 추가
5. 마이그레이션 파일을 버전 관리에 포함
6. 정기적으로 `prisma studio`로 데이터 확인
