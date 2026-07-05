---
id: PB-PA-05
purpose: CORS 오류의 진단된 원인에 대해 서버측 Origin 정책 수정안을 안전하게 적용
applies_when: 교차 출처 요청 차단 원인이 특정되어 CORS 설정을 반영해야 할 때
version: "1.1"
---

# CORS Origin 정책 수정 적용

진단된 CORS 원인(허용 헤더 누락, Origin 화이트리스트 오류, Preflight 거부, 자격증명 설정)에 대해 서버측 Origin 화이트리스트 구성 옵션을 트레이드오프와 함께 제시하고, 보안을 유지하며 안전하게 구현하도록 지시하는 프롬프트입니다.

## 용도

F-04 플로우의 "6단계: 수정안 선택"을 근거로, 교차 출처 요청을 안전하게 허용합니다. 서버 CORS 설정, 프록시, 수동 헤더 등 후보를 보안·유지보수 트레이드오프와 함께 비교합니다.

## 적용 시점

- "blocked by CORS policy" 원인이 서버 헤더 누락/Origin 불일치로 특정됐을 때
- Preflight OPTIONS 요청이 거부되는 원인이 확인됐을 때
- credentials 포함 요청의 Origin/자격증명 설정을 결정할 때

## 필수 입력

- 진단된 원인 (예: Access-Control-Allow-Origin 미설정 / credentials 불일치)
- 요청 Origin 목록과 허용해야 할 도메인
- 서버 프레임워크 (Express/NestJS 등)와 credentials 필요 여부

## 프롬프트 템플릿

```
다음 CORS 차단 원인에 대한 수정안을 적용하라.

[진단된 원인]
- 요청 Origin: {예: http://localhost:3000}
- 근본 원인: {예: 서버 CORS 헤더 누락 / 화이트리스트에 Origin 없음}
- 서버: {Express/NestJS} / credentials 필요: {예/아니오}

[요구사항]
1. 아래 서버측 Origin 화이트리스트 구성 옵션을 트레이드오프와 함께 비교하라:
   - 옵션 A: 정적 배열 화이트리스트 (명시적, 도메인 추가 시 재배포 필요)
   - 옵션 B: 환경변수 기반 origin 콜백 (환경별 유연, 설정 실수 위험)
   - 옵션 C: 리버스 프록시/next.config rewrites로 same-origin화 (CORS 자체 회피, 인프라 의존)
   - 옵션 D: 수동 미들웨어로 헤더 세밀 제어 (완전 제어, 유지보수 부담)
2. 최소 침습 원칙: 프로덕션에서 origin: '*' 를 쓰지 말고, 필요한 도메인만 허용하라.
3. 사이드 이펙트를 점검하라:
   - credentials:true 와 origin:'*' 병용 금지 위반 여부
   - allowedHeaders/methods 최소화 여부, Preflight 캐시(maxAge) 영향
4. 롤백 가능성 확보: CORS 설정을 환경변수/단일 미들웨어로 격리해 되돌릴 수 있게 하라.

[출력]
- 선택한 옵션과 근거
- 서버 설정 수정 전/후 코드 diff
- 보안 사이드 이펙트 점검 결과
- 롤백 절차
```

## 출력 계약

- 선택한 화이트리스트 구성 옵션과 근거
- 서버 CORS 설정 수정 전/후 코드 diff (Origin/methods/headers/credentials)
- 보안 점검표: 와일드카드 사용 여부, credentials 병용, 허용 메서드 최소화
- 롤백 절차: 환경변수/미들웨어 단위 복귀 방법

## 셀프 체크리스트

- [ ] 프로덕션에서 origin: '*' 를 사용하지 않는가?
- [ ] credentials:true 와 와일드카드 Origin을 병용하지 않았는가?
- [ ] 허용 메서드/헤더를 실제 필요한 범위로 최소화했는가?
- [ ] Preflight(OPTIONS) 요청이 200으로 정상 응답되는가?
- [ ] 허용되지 않은 Origin이 차단되는지 검증했는가?
- [ ] CORS 설정이 환경변수/단일 지점으로 격리되어 롤백 가능한가?
