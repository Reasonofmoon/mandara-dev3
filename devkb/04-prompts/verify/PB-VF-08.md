---
id: PB-VF-08
purpose: Prisma 마이그레이션 드리프트 해소가 스키마·DB 동기화를 회복했는지 검증
applies_when: 마이그레이션 드리프트(F-08) 수정을 적용한 뒤 스키마 동기화와 환경 일관성을 확인할 때
version: "1.1"
---

# Prisma 마이그레이션 드리프트 해결 검증

migrate dev/deploy, db pull, resolve 등으로 드리프트를 해소한 뒤, Prisma 스키마와 데이터베이스가 완전히 동기화되었고 마이그레이션 이력이 정상이며 dev/prod 환경 간 불일치가 없는지 확인하는 검증 프롬프트입니다.

## 용도

F-08 플로우의 6단계(수정) 이후, `migrate status`와 `validate`로 동기화를 확인하고 마이그레이션 파일 커밋·환경 일관성·애플리케이션 연결까지 회귀 없이 회복됐는지 검증합니다.

## 적용 시점

- 드리프트를 감지해 migrate dev / db pull / resolve로 처리한 직후
- 프로덕션에 migrate deploy를 적용하기 직전/직후
- 수동 SQL 변경이나 백업 복원 후 스키마를 재정렬한 뒤

## 필수 입력

- 대상 환경(dev/staging/prod)과 각 DATABASE_URL
- 드리프트 원인 (스키마 미적용 / 수동 SQL / 파일 손상 등)
- 적용한 복구 방법과 마이그레이션 파일 목록

## 프롬프트 템플릿

아래 마이그레이션 드리프트 복구에 대해 스키마 동기화와 환경 일관성을 검증하고 회귀가 없는지 확인해줘.

**환경:** [dev / prod]
**복구 방법:** [예: prisma migrate deploy]

1. **성공 기준 정의**
   - `migrate status` → "Database schema is up to date"
   - `prisma validate` 통과
   - `migrate diff`로 스키마↔DB 차이 0
   - 마이그레이션 파일이 커밋되어 팀/환경 간 공유됨

2. **동기화 검증 명령**
   ```bash
   prisma migrate status     # 미적용 마이그레이션/드리프트 없음
   prisma validate           # 스키마 유효성
   prisma migrate diff \
     --from-schema-datamodel prisma/schema.prisma \
     --to-schema-datasource prisma/schema.prisma   # 차이 없음 기대
   ```

3. **환경 일관성 매트릭스**
   | 환경 | migrate status | diff | 결과 |
   |------|---------------|------|------|
   | dev | up to date | 0 | |
   | staging | up to date | 0 | |
   | prod (deploy 후) | up to date | 0 | |

   - 각 환경이 동일한 마이그레이션 히스토리(applied 목록)를 갖는지 대조

4. **애플리케이션 연결·회귀 검증**
   ```javascript
   // 시작 시 연결 및 신규 컬럼 접근 확인
   await prisma.$queryRaw`SELECT 1`;              // 연결
   await prisma.user.findFirst({ select: { email: true } }); // 신규 필드 반영
   ```
   - 새로 추가/변경한 컬럼에 CRUD가 정상 동작하는지
   - 기존 쿼리가 깨지지 않았는지(회귀)

5. **재발 방지·모니터링**
   - `prisma/migrations/`가 .gitignore에서 제외되어 커밋되는지
   - CI/CD에 `migrate deploy` 및 배포 전 `migrate status` 게이트가 있는지
   - 프로덕션에서 수동 SQL 변경을 금지하는 정책 확인

## 출력 계약

```
검증 결과: [통과 / 실패]
- migrate status: [up to date / 드리프트]
- validate: [통과 / 실패]
- 환경 일관성: [dev/staging/prod 동일 / 불일치]
- 신규 스키마 CRUD: [정상 / 회귀]
- 마이그레이션 파일 커밋: [됨 / 안 됨]
```

## 셀프 체크리스트

- [ ] migrate status가 "up to date"인가?
- [ ] validate와 diff로 스키마↔DB 일치를 확인했는가?
- [ ] dev/staging/prod 마이그레이션 이력이 동일한가?
- [ ] 마이그레이션 파일을 커밋했는가?
- [ ] 신규 컬럼 CRUD와 기존 쿼리 회귀를 확인했는가?
- [ ] CI/CD에 migrate deploy 게이트가 있는가?
