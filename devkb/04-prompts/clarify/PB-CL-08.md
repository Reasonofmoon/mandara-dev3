---
id: PB-CL-08
purpose: JWT 토큰 문제 파악
applies_when: JWT 서명 검증 실패·만료·저장·갱신 관련 문제가 발생할 때
version: "1.1"
---

# JWT 토큰 문제 파악

JWT 관련 문제가 발생할 때, 생성·검증·저장·갱신 중 어느 단계에서 무엇이 어긋났는지 짚어내도록 유도하는 질문 세트입니다.

## 용도

"토큰이 안 먹혀요"를 넘어, 시크릿 불일치·만료 검증 누락·저장 위치·리프레시 로직 중 무엇이 문제인지 좁힙니다.

## 적용 시점

- "Invalid signature" 오류
- 토큰이 만료됐는데도 계속 유효하거나, 반대로 너무 빨리 만료됨
- 토큰 갱신(refresh)이 실패함
- 토큰 저장 위치(localStorage/쿠키)가 불명확하거나 보안이 걱정됨

## 필수 입력

- 오류 메시지(name과 message, 예: TokenExpiredError)
- 토큰 생성 옵션(expiresIn, algorithm, issuer/audience)과 검증 코드
- 토큰 저장·전송 방식(localStorage / sessionStorage / HttpOnly 쿠키)

## 프롬프트 템플릿

아래 질문에 답해 JWT 문제 단계를 좁혀주세요.

1. **오류 확인**
   - `jwt.verify` 실패 시 error.name이 무엇인가요? (`JsonWebTokenError` / `TokenExpiredError` 등)
   - 토큰을 `jwt.decode`로 풀었을 때 payload(exp, iss, aud 등)가 예상과 같나요?

2. **서명·시크릿**
   - 토큰 생성과 검증에 같은 시크릿 키를 쓰나요? 액세스/리프레시 토큰의 시크릿이 분리돼 있나요?
   - `issuer`/`audience` 옵션을 생성 시엔 넣고 검증 시엔 안 넣거나 값이 다르진 않나요?

3. **만료 처리**
   - `expiresIn`이 설정돼 있나요? 액세스 토큰(짧게)과 리프레시 토큰(길게)의 수명이 어떻게 되나요?
   - 검증 시 만료를 확인하나요, 아니면 서명만 보고 통과시키나요?

4. **저장·전송**
   - 토큰을 어디에 저장하나요? localStorage(XSS 위험) / sessionStorage / HttpOnly 쿠키 중 무엇인가요?
   - 요청 시 헤더(`Authorization: Bearer`)로 보내나요, 쿠키로 자동 전송하나요(`credentials: 'include'`)?

5. **갱신 로직**
   - 401 발생 시 리프레시 토큰으로 갱신을 시도하나요? 리프레시 토큰을 서버가 검증·확인하나요?
   - 갱신 엔드포인트가 보호돼 있나요? 로그아웃 시 토큰을 무효화(블랙리스트)하나요?

## 출력 계약

JWT 문제 정의:
- 증상: [error.name과 message]
- 서명/시크릿: [생성·검증 시크릿 일치 여부, iss/aud 일관성]
- 만료: [expiresIn 설정, 만료 검증 여부]
- 저장 위치: [localStorage / sessionStorage / HttpOnly 쿠키]
- 전송: [Authorization 헤더 / 쿠키 자동]
- 갱신: [리프레시 토큰 검증·갱신 로직 유무]

## 셀프 체크리스트

- [ ] error.name으로 실패 유형(서명 vs 만료)을 구분했는가?
- [ ] 생성·검증 시크릿 및 iss/aud 일관성을 확인했는가?
- [ ] expiresIn 설정과 만료 검증 여부를 확인했는가?
- [ ] 토큰 저장 위치의 보안 특성을 파악했는가?
- [ ] 리프레시 토큰 검증·갱신 로직 유무를 확인했는가?
