---
id: PB-VF-07
purpose: JWT 생성·검증·갱신·폐기 수정이 보안 요건을 충족하는지 검증
applies_when: JWT 토큰 문제(F-07) 수정을 적용한 뒤 만료·갱신·폐기·저장 보안을 확인할 때
version: "1.1"
---

# JWT 토큰 보안 해결 검증

액세스/리프레시 토큰 분리, 만료·서명 검증, HttpOnly 쿠키 저장, 토큰 갱신·폐기 로직을 수정한 뒤, 만료·갱신·폐기 시나리오가 모두 안전하게 동작하고 XSS/CSRF 노출이 없는지 확인하는 검증 프롬프트입니다.

## 용도

F-07 플로우의 6단계(수정) 이후, 토큰 생명주기 전체(발급→검증→만료→갱신→폐기)를 시나리오 매트릭스로 검증하고 저장 위치의 보안 회귀를 점검합니다.

## 적용 시점

- 토큰 발급/검증 로직(시크릿, 만료, issuer/audience)을 수정한 직후
- 리프레시 토큰·갱신 엔드포인트를 도입한 직후
- 토큰 저장 방식을 HttpOnly 쿠키로 전환한 뒤

## 필수 입력

- 액세스/리프레시 토큰의 만료 시간과 시크릿 분리 여부
- 토큰 저장 위치(HttpOnly 쿠키 / 메모리 / localStorage)
- 갱신·로그아웃(폐기) 엔드포인트 명세

## 프롬프트 템플릿

아래 JWT 수정에 대해 토큰 생명주기와 보안을 검증하고 회귀가 없는지 확인해줘.

**토큰:** [access 15m, refresh 7d, 시크릿 분리]
**저장:** [HttpOnly + Secure + SameSite 쿠키]

1. **성공 기준 정의**
   - 유효 토큰 검증 통과, 잘못된 시크릿/변조 토큰 거부
   - 만료 토큰은 검증 실패(TokenExpiredError)
   - 리프레시로 새 액세스 발급, 로그아웃 후 재사용 불가
   - 토큰이 localStorage에 노출되지 않음

2. **토큰 생명주기 시나리오 매트릭스**
   | 시나리오 | 입력 | 기대 결과 | 결과 |
   |---------|------|----------|------|
   | 정상 검증 | 유효 토큰 | 통과, payload 정확 | |
   | 서명 위조 | 잘못된 시크릿 서명 | 거부 | |
   | 만료 | expiresIn 지난 토큰 | TokenExpiredError | |
   | issuer/audience 불일치 | 다른 iss/aud | 거부 | |
   | 갱신 | 유효 refresh | 새 access 발급 | |
   | 폐기 후 재사용 | 로그아웃한 refresh | 거부 | |

3. **자동화 테스트 (만료·서명·갱신·폐기)**
   ```javascript
   it('잘못된 시크릿 토큰을 거부한다', () => {
     const t = jwt.sign({ userId: 1 }, 'wrong-secret');
     expect(() => authService.verifyAccessToken(t)).toThrow();
   });
   it('만료 토큰을 거부한다', (done) => {
     const t = jwt.sign({ userId: 1 }, process.env.JWT_SECRET, { expiresIn: '1ms' });
     setTimeout(() => {
       expect(() => authService.verifyAccessToken(t)).toThrow('Token expired');
       done();
     }, 10);
   });
   ```

4. **저장·전송 보안 확인**
   - `document.cookie`에서 토큰이 읽히지 않는지 (HttpOnly)
   - Secure/SameSite 속성이 설정됐는지
   - localStorage/sessionStorage에 액세스 토큰이 없는지
   - 갱신 요청이 credentials: 'include'로만 동작하는지

5. **모니터링 지표**
   - 토큰 검증 실패율(만료/위조 구분)
   - 리프레시 남용/재사용 탐지(폐기 목록 조회)
   - 시크릿 길이(32자 이상)·환경변수 관리 확인

## 출력 계약

```
검증 결과: [통과 / 실패]
- 서명 검증: [정상 거부/통과]
- 만료 처리: [TokenExpiredError]
- 갱신: [새 토큰 발급]
- 폐기 후 재사용: [차단]
- 저장 보안(HttpOnly/localStorage 미노출): [안전 / 취약]
```

## 셀프 체크리스트

- [ ] 만료·위조·갱신·폐기 시나리오를 모두 테스트했는가?
- [ ] 액세스/리프레시 시크릿이 분리되어 있는가?
- [ ] 토큰이 localStorage에 저장되지 않는가?
- [ ] HttpOnly/Secure/SameSite 속성이 설정됐는가?
- [ ] 로그아웃한 리프레시 토큰이 재사용 불가한가?
