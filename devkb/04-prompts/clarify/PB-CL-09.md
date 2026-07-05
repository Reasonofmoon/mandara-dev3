---
id: PB-CL-09
purpose: Prisma 마이그레이션 드리프트 파악
applies_when: 스키마와 DB가 어긋나 "Drift detected" 또는 migrate 실패가 발생할 때
version: "1.1"
---

# Prisma 마이그레이션 드리프트 문제 파악

schema.prisma와 실제 DB가 어긋날 때, 어디서 불일치가 생겼고 데이터 손실 없이 복구 가능한 상황인지 짚어내도록 유도하는 질문 세트입니다.

## 용도

"마이그레이션이 안 돼요"를 넘어, 스키마 미적용·수동 SQL 변경·마이그레이션 파일 손상·환경 간 불일치 중 무엇인지 좁힙니다. 특히 대상 DB가 개발용인지 프로덕션인지(데이터 보존 필요 여부)를 먼저 가립니다.

## 적용 시점

- "The database schema is not in sync with the Prisma schema"
- "Drift detected"
- `prisma migrate dev` 또는 `prisma db push` 실패
- 환경(dev/prod)마다 마이그레이션 상태가 다름

## 필수 입력

- `prisma migrate status` 출력
- 대상 데이터베이스 환경(개발/스테이징/프로덕션)과 데이터 보존 필요 여부
- 최근에 한 작업(스키마 수정 / 수동 SQL / 백업 복원 / 파일 삭제)

## 프롬프트 템플릿

아래 질문에 답해 드리프트 원인과 안전한 복구 경로를 좁혀주세요.

1. **상태 확인**
   - `prisma migrate status`의 전체 출력을 붙여주세요. "Drift detected"가 나오나요?
   - `prisma migrate diff`로 스키마와 DB의 차이를 확인하면 무엇이 다른가요?

2. **원인 추적**
   - schema.prisma를 수정하고 `migrate dev`를 안 돌린 상태인가요?
   - SQL로 DB를 직접 변경했거나 백업을 복원했나요?
   - prisma/migrations 폴더의 파일을 지우거나 수정했나요? 이전 마이그레이션이 실패한 채 남아있나요?

3. **환경·데이터 보존 (매우 중요)**
   - 대상 DB가 개발용인가요, 프로덕션인가요?
   - 데이터를 잃으면 안 되나요? (이 답에 따라 `migrate reset`/`db push` 사용 가능 여부가 갈립니다)

4. **마이그레이션 이력**
   - prisma/migrations 폴더가 git에 커밋돼 있나요? 팀원과 파일 목록이 일치하나요?
   - `migrate status`가 "pending" 또는 "failed" 마이그레이션을 보고하나요?

5. **환경 변수**
   - `DATABASE_URL`이 의도한 DB(dev/test/prod)를 가리키나요? 잘못된 DB에 붙어 드리프트로 보이는 건 아닌가요?

## 출력 계약

마이그레이션 드리프트 문제 정의:
- 증상: [migrate status 출력 / diff 결과]
- 원인: [스키마 미적용 / 수동 SQL / 파일 손상 / 실패한 마이그레이션]
- 환경: [개발 / 프로덕션]
- 데이터 보존 필요: [예 / 아니오] ← 복구 방법 결정의 핵심
- 마이그레이션 이력: [커밋 여부, pending/failed 상태]
- DATABASE_URL: [올바른 DB 지정 여부]

## 셀프 체크리스트

- [ ] migrate status 출력을 확보했는가?
- [ ] 드리프트를 만든 최근 작업을 특정했는가?
- [ ] 대상 DB가 개발/프로덕션인지, 데이터 보존이 필요한지 확인했는가?
- [ ] 마이그레이션 파일의 커밋·pending/failed 상태를 확인했는가?
- [ ] DATABASE_URL이 올바른 DB를 가리키는지 확인했는가?
