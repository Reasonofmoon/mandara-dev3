---
id: PB-PA-09
purpose: Prisma 마이그레이션 드리프트의 진단된 원인에 대해 안전한 복구 수정안을 적용
applies_when: 스키마-DB 불일치 원인이 특정되어 마이그레이션을 반영해야 할 때
version: "1.1"
---

# Prisma 마이그레이션 드리프트 복구 적용

진단된 드리프트 원인(migrate 누락, 수동 SQL 변경, 마이그레이션 파일 손상, 환경 간 불일치)에 대해 복구 수정안을 트레이드오프와 함께 제시하고, 데이터 손실 없이 안전하게 적용하도록 지시하는 프롬프트입니다.

## 용도

F-08 플로우의 "6단계: 수정안 선택"을 근거로, schema.prisma와 데이터베이스를 동기화합니다. migrate dev, db push, db pull, migrate resolve, migrate reset 등 후보를 환경(dev/prod)·데이터 손실 트레이드오프와 함께 비교합니다.

## 적용 시점

- "Drift detected"/"schema is not in sync" 원인이 특정됐을 때
- 수동 SQL 또는 백업 복원으로 스키마가 어긋났을 때
- 프로덕션에 마이그레이션을 안전하게 배포해야 할 때

## 필수 입력

- 진단된 원인 (예: 수동 SQL 변경으로 드리프트 / migrate dev 누락)
- 대상 환경 (dev/staging/prod)과 데이터 보존 필요 여부
- prisma migrate status 및 migrate diff 출력

## 프롬프트 템플릿

```
다음 Prisma 마이그레이션 드리프트 원인에 대한 복구 수정안을 적용하라.

[진단된 원인]
- 환경: {dev/staging/prod}
- 근본 원인: {예: 수동 SQL 변경 / 마이그레이션 파일 삭제}
- 데이터 보존 필요: {예/아니오}
- migrate status 출력: {붙여넣기}

[요구사항]
1. 아래 복구 옵션을 트레이드오프와 함께 비교하라 (⚠️ 데이터 손실 위험 명시):
   - 옵션 A: migrate dev --name <설명> (정상 워크플로우, dev 전용)
   - 옵션 B: db push (프로토타입, dev 전용, 데이터 손실 가능)
   - 옵션 C: db pull로 현재 DB를 스키마에 역반영 (수동 변경 보존, 마이그레이션 이력 공백)
   - 옵션 D: migrate resolve --rolled-back/--applied (이력만 정정, 무손실)
   - 옵션 E: migrate reset (전체 재생성, ⚠️ 전 데이터 삭제, dev 전용)
   - 프로덕션: migrate deploy만 사용 (무손실, dev에서 생성한 파일 필요)
2. 최소 침습 원칙: 프로덕션에서는 reset/db push를 절대 사용하지 말고, 커밋된 마이그레이션 파일로 deploy하라.
3. 사이드 이펙트를 점검하라:
   - 파괴적 마이그레이션(컬럼/테이블 삭제) 포함 여부와 백업 선행
   - 마이그레이션 이력(_prisma_migrations)과 실제 스키마 정합성
   - Prisma Client 재생성 필요 여부
4. 롤백 가능성 확보: 적용 전 DB 백업을 확보하고, 마이그레이션 파일을 커밋 단위로 관리하라.

[출력]
- 선택한 복구 옵션과 근거 (환경·데이터 손실 명시)
- 실행할 명령 시퀀스와 schema.prisma diff
- 사이드 이펙트 점검 결과
- 롤백 절차 (백업 복원 포함)
```

## 출력 계약

- 선택한 복구 옵션과 근거 (환경/데이터 손실 명시)
- 실행 명령 시퀀스와 schema.prisma/마이그레이션 diff
- 사이드 이펙트 점검표: 파괴적 변경, 백업, 이력 정합성, Client 재생성
- 롤백 절차: DB 백업 복원 및 마이그레이션 되돌리기 방법

## 셀프 체크리스트

- [ ] 대상 환경(dev/prod)에 맞는 명령을 선택했는가? (prod는 deploy만)
- [ ] 파괴적 마이그레이션 전에 DB 백업을 확보했는가?
- [ ] 프로덕션에서 reset/db push를 사용하지 않았는가?
- [ ] 적용 후 migrate status가 "up to date"로 나오는가?
- [ ] 마이그레이션 파일을 커밋해 환경 간 재현 가능한가?
- [ ] 실패 시 백업 복원 절차가 준비되어 있는가?
