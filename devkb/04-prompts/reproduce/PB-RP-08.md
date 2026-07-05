---
id: PB-RP-08
purpose: Prisma 스키마-DB 드리프트를 격리 환경에서 재현
applies_when: migrate 실패나 드리프트 경고를 안전한 사본 DB에서 재현해야 할 때
version: "1.1"
---

# Prisma 마이그레이션 드리프트 재현 절차 수립

schema.prisma와 실제 DB의 불일치(드리프트)를, 운영 데이터를 건드리지 않는 격리 사본 DB에서 재현하고 어떤 변경이 드리프트를 만드는지 특정하는 프롬프트입니다.

## 용도

"migrate dev가 실패한다" "drift detected가 뜬다"를, 운영 DB가 아닌 사본에서 결정론적으로 재현해 원인 변경(수동 SQL/미적용 스키마/파일 누락)을 좁힙니다.

## 적용 시점

- "The database schema is not in sync with the Prisma schema" 경고 시
- `prisma migrate dev`/`db push`가 실패할 때
- 수동 SQL 변경 후 드리프트가 의심될 때
- dev/prod 마이그레이션 상태가 달라 보일 때

## 필수 입력

- 현재 schema.prisma와 최근 변경 내역
- 드리프트 대상 테이블/컬럼
- prisma/migrations 디렉토리 상태(누락/손상 여부)
- 오류 전문과 실행한 명령

## 프롬프트 템플릿

아래 지시를 AI 도구나 팀원에게 그대로 전달하세요.

```
다음 Prisma 드리프트를 격리 사본 DB에서 재현하고, 원인 변경을 특정해줘.
(운영 DB에는 절대 destructive 명령을 실행하지 말 것)

[증상]
- 오류: (전문 붙여넣기)
- 실행 명령: (예: prisma migrate dev)

[재현 절차 지시]
1. 재현 환경 격리 먼저:
   - DATABASE_URL을 사본 DB(예: repro_db)로 지정한 .env.repro 준비.
   - 운영/개발 DB가 아닌 별도 사본에서만 실행.
2. 드리프트 현황을 증거로 캡처:
   dotenv -e .env.repro -- prisma migrate status
   dotenv -e .env.repro -- prisma migrate diff \
     --from-migrations prisma/migrations \
     --to-schema-datamodel prisma/schema.prisma \
     --script
   → 스키마와 마이그레이션 이력 간 실제 diff SQL을 확보.
3. 원인 변경을 하나씩 재현:
   (a) schema.prisma는 바꿨으나 migrate 미실행 상태 재현
   (b) 사본 DB에 직접 SQL(ALTER TABLE ...) 을 넣고 status 재확인
   (c) prisma/migrations 의 특정 폴더를 제거한 뒤 status 재확인
4. 각 케이스에서 migrate status가 "Drift detected"를 내는지 확인.

[재현 조건 고정]
- 재현에 쓴 사본 DB URL과 시드 상태를 명시.
- 어떤 변경(a~c) 이후 드리프트가 나타나는지 단계별로 기록.
- migrate diff가 출력한 SQL을 그대로 첨부.
```

## 출력 계약

- 사본 DB 기준 `migrate status`/`migrate diff` 출력
- 드리프트를 유발한 변경(a~c 중) 확정
- diff가 보여주는 실제 SQL 차이
- 격리 재현 명령 세트(운영 DB 미접촉 확인 포함)

## 셀프 체크리스트

- [ ] 운영/개발이 아닌 격리 사본 DB에서 재현했는가?
- [ ] destructive 명령을 운영 DB에 실행하지 않았는가?
- [ ] migrate status/diff로 드리프트를 증거화했는가?
- [ ] 원인 변경(미적용/수동SQL/파일누락)을 격리했는가?
- [ ] diff SQL을 그대로 기록했는가?
