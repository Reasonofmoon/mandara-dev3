---
id: PB-RP-07
purpose: JWT 생성·검증·갱신 실패를 단계별로 재현
applies_when: 서명/만료/갱신 중 어느 단계에서 토큰이 깨지는지 특정해 재현해야 할 때
version: "1.1"
---

# JWT 토큰 문제 재현 절차 수립

Invalid signature·조기 만료·갱신 실패가 섞인 JWT 문제를, 디코드→검증→갱신을 단계별로 격리해 어느 단계에서 깨지는지 재현하는 프롬프트입니다.

## 용도

"토큰이 안 먹힘"이 시크릿 불일치인지, 만료 검증 문제인지, 리프레시 로직 오류인지를 단계별로 고정 재현해 원인 단계를 특정합니다.

## 적용 시점

- "invalid signature" 오류가 날 때
- 토큰이 예상보다 빨리 또는 늦게 만료될 때
- 리프레시 요청이 실패하거나 무한 갱신될 때
- 액세스/리프레시 시크릿이 뒤바뀐 것을 의심할 때

## 필수 입력

- 문제 토큰 샘플(액세스/리프레시)
- 서명 알고리즘과 issuer/audience 설정값
- 만료 옵션(expiresIn)과 서버 시각
- 오류 전문(error.name, expiredAt 포함)

## 프롬프트 템플릿

아래 지시를 AI 도구나 팀원에게 그대로 전달하세요.

```
다음 JWT 문제를 디코드→검증→갱신 단계로 격리 재현하고, 깨지는 단계를 특정해줘.

[증상]
- 오류: (예: invalid signature / Token expired)
- 토큰: (샘플, 민감정보 마스킹)

[재현 절차 지시]
1. 서명 없이 디코드해 페이로드부터 확인(만료·issuer·audience):
   node -e "console.log(require('jsonwebtoken').decode('<token>'))"
   → exp, iat, iss, aud 값을 서버 설정과 대조.
2. 서명 검증 단독 재현(시크릿 불일치 격리):
   node -e "try{require('jsonwebtoken').verify('<token>', process.env.JWT_SECRET,
     {issuer:'<iss>',audience:'<aud>'})}catch(e){console.log(e.name,e.message)}"
   → invalid signature면 시크릿/알고리즘 불일치.
3. 만료 재현: expiresIn:'1ms' 로 토큰을 만들고 즉시 verify 해
   TokenExpiredError와 expiredAt이 정확히 나오는지 확인.
4. 갱신 재현: 리프레시 토큰으로 /api/auth/refresh 를 호출하고,
   - 리프레시 시크릿이 액세스 시크릿과 다른지
   - 만료된 리프레시 토큰이 거부되는지 확인.
5. 단계 분류: (a) 디코드 단계 값 오류 (b) 서명 불일치
   (c) 만료 검증 오류 (d) 갱신 로직 오류.

[재현 조건 고정]
- 각 단계에 쓴 토큰/시크릿 출처를 명시(민감정보는 마스킹).
- error.name과 메시지를 단계별로 그대로 캡처.
- 서버 시각과 토큰 exp의 차이를 기록(시계 오차 배제).
```

## 출력 계약

- 디코드된 페이로드(exp/iat/iss/aud)와 설정값 대조표
- 서명 검증/만료/갱신 각 단계의 오류 캡처
- 깨지는 단계(a~d 중) 확정
- 결정론적 재현 스니펫(복붙용)

## 셀프 체크리스트

- [ ] 서명 없이 디코드해 페이로드부터 확인했는가?
- [ ] 서명 검증을 단독으로 재현했는가?
- [ ] 만료를 짧은 expiresIn으로 강제 재현했는가?
- [ ] 갱신 실패를 리프레시 시크릿/만료 기준으로 격리했는가?
- [ ] 서버 시각과 exp 차이를 기록했는가?
