---
id: PB-DG-09
purpose: Prisma 마이그레이션 드리프트의 근본 원인을 확률·검증 비용 순으로 진단
applies_when: Prisma 스키마와 실제 DB가 어긋나 드리프트가 감지될 때
version: "1.1"
---

# Prisma 마이그레이션 드리프트 원인 진단

드리프트가 감지된 상태에서 마이그레이션 미적용, 수동 SQL 변경, 마이그레이션 파일 손실, 환경 간 불일치 중 어느 것이 원인인지 원인 후보 순으로 정렬하고, 각 가설을 확정 또는 기각할 증거 수집 방법을 지시하는 진단 프롬프트입니다.

## 용도

`prisma migrate status`가 드리프트를 보고할 때, `schema.prisma`와 DB가 갈라진 지점을 `migrate diff`와 `db pull`로 좁혀냅니다. 마이그레이션 히스토리와 실제 DB 스키마 대조로 검증합니다.

## 적용 시점

- "The database schema is not in sync with the Prisma schema" 오류
- "Drift detected" 메시지 출력
- `prisma migrate dev` 또는 `db push`가 실패함
- 증상은 확인됐으나 스키마/DB/히스토리 중 어디가 원인인지 미상

## 필수 입력

- `prisma migrate status` 전체 출력
- `prisma migrate diff --from-empty --to-schema-datamodel` 결과
- `prisma/migrations/` 디렉토리 목록과 `_prisma_migrations` 테이블 상태
- 최근 수동 SQL 변경/백업 복원 이력(있으면)

## 프롬프트 템플릿

```
다음 Prisma 마이그레이션 드리프트의 원인을 진단하라.

[migrate status 출력]
<전체 출력>

[migrate diff 결과]
<schema와 DB의 차이>

[마이그레이션 히스토리]
<prisma/migrations 목록, _prisma_migrations 상태>

[최근 변경 이력]
<수동 SQL, 백업 복원 등>

다음 순서로 진단하라:

1. 원인 후보를 확률·검증비용 순으로 정렬하라:
   - (매우높음/저비용) schema.prisma는 수정됐으나 migrate dev 미실행
   - (높음/고비용) SQL로 DB를 직접 변경해 스키마와 어긋남
   - (높음/고비용) 마이그레이션 파일이 삭제/손상됨
   - (중간/저비용) DATABASE_URL이 잘못된 DB(다른 환경)를 가리킴

2. 각 가설의 확정/기각 증거를 수집하라:
   - 미적용: migrate status에 "pending migration" 또는
     "schema.prisma has changes not yet in a migration"이 보이면 → 미적용
   - 수동 변경: prisma db pull로 DB를 실제로 읽어 schema.prisma와 비교.
     마이그레이션 파일에 없는 컬럼/테이블이 DB에 있으면 → 수동 SQL 변경
   - 파일 손실: _prisma_migrations 테이블의 적용 기록과
     prisma/migrations 디렉토리 목록을 대조.
     테이블엔 있으나 파일이 없으면 → 마이그레이션 파일 손실
   - 환경 불일치: echo $DATABASE_URL로 대상 DB 호스트/DB명 확인.
     의도한 환경이 아니면 → 잘못된 DB를 가리키는 것

3. 가장 확률 높고 검증 비용 낮은 가설부터 확정하고,
   확정된 원인과 증거를 명시하라. 기각된 가설도 근거와 함께 기록하라.
```

## 출력 계약

```
확정 원인: [예: schema.prisma에 email 필드 추가 후 migrate dev 미실행]
증거: [예: migrate status에 "changes not yet in a migration", migrate diff에 email 컬럼]
기각된 후보:
  - 수동 SQL 변경: [기각 근거]
  - 마이그레이션 파일 손실: [기각 근거]
다음 단계: [F-08 6단계 수정안 중 적용할 수정안 번호]
주의: 프로덕션이면 migrate reset/db push 등 파괴적 명령 금지, deploy 경로 사용
```

## 셀프 체크리스트

- [ ] 원인 후보를 확률·검증비용 순으로 정렬했는가?
- [ ] db pull로 실제 DB 스키마를 schema.prisma와 대조했는가?
- [ ] _prisma_migrations 기록과 마이그레이션 파일 목록을 대조했는가?
- [ ] DATABASE_URL이 의도한 환경을 가리키는지 확인했는가?
- [ ] 확정 원인이 F-08의 수정안과 매핑되며, 파괴적 명령의 환경 위험을 표기했는가?
