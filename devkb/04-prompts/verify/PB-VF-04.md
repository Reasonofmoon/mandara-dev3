---
id: PB-VF-04
purpose: CORS 설정 수정이 허용 출처는 통과·비허용 출처는 차단하는지 검증
applies_when: CORS 오류(F-04) 수정을 적용한 뒤 출처·메서드·자격증명 정책을 확인할 때
version: "1.1"
---

# CORS 설정 해결 검증

서버 CORS 헤더, 화이트리스트, preflight 처리, credentials 설정을 수정한 뒤, 허용된 출처의 요청은 성공하고 비허용 출처는 차단되며 프로덕션에서 와일드카드(`*`)가 노출되지 않는지 확인하는 검증 프롬프트입니다.

## 용도

F-04 플로우의 6단계(수정) 이후, preflight(OPTIONS)와 실제 요청 양쪽에서 CORS 헤더가 올바르게 내려오는지, 보안 회귀(과도한 허용)가 없는지 curl·자동화 테스트로 검증합니다.

## 적용 시점

- 서버 cors 미들웨어 / enableCors 설정을 변경한 직후
- credentials: true / allowedHeaders를 조정한 직후
- 프로덕션 배포 전 출처 화이트리스트를 최종 확인할 때

## 필수 입력

- API 서버 URL과 수정한 CORS 설정
- 허용해야 할 출처 목록과 차단해야 할 출처 예시
- 사용하는 메서드/커스텀 헤더/credentials 여부

## 프롬프트 템플릿

아래 CORS 수정에 대해 허용/차단 동작과 preflight를 검증하고 보안 회귀가 없는지 확인해줘.

**API:** [URL]
**허용 출처:** [http://localhost:3000, https://myapp.com]
**차단 기대:** [http://evil.com]

1. **성공 기준 정의**
   - 허용 출처: `Access-Control-Allow-Origin`에 해당 출처 반영
   - 비허용 출처: 해당 헤더 미반영 → 브라우저가 차단
   - preflight(OPTIONS) 200 응답 + 허용 메서드/헤더 명시
   - 프로덕션 응답에 `Access-Control-Allow-Origin: *` 없음

2. **preflight 검증 (curl)**
   ```bash
   curl -X OPTIONS https://api.example.com/data -v \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type, Authorization"
   # 기대: 200, Allow-Origin/Methods/Headers 헤더 존재
   ```

3. **출처별 회귀 매트릭스**
   | Origin | 메서드 | 기대 Allow-Origin | 기대 결과 |
   |--------|--------|------------------|----------|
   | 허용 출처 | GET | 해당 출처 | 성공 |
   | 허용 출처 | POST(+credentials) | 해당 출처 + Allow-Credentials:true | 성공 |
   | 비허용 출처 | GET | (없음) | 차단 |
   | 허용 출처 | DELETE/PATCH | 허용 메서드 포함 | 성공 |

4. **자동화 테스트**
   ```javascript
   it('허용 출처는 통과, 비허용은 차단한다', async () => {
     const ok = await fetch(API, { headers: { Origin: 'http://localhost:3000' } });
     expect(ok.headers.get('Access-Control-Allow-Origin')).toBe('http://localhost:3000');
     const blocked = await fetch(API, { headers: { Origin: 'http://evil.com' } });
     expect(blocked.headers.get('Access-Control-Allow-Origin')).toBeFalsy();
   });
   ```

5. **모니터링/보안 지표**
   - 차단된 출처 요청이 서버 로그에 경고로 남는지
   - credentials 사용 시 Allow-Origin이 `*`가 아닌 명시 출처인지

## 출력 계약

```
검증 결과: [통과 / 실패]
- preflight(OPTIONS): [200 + 헤더 정상 / 문제]
- 허용 출처: [통과]
- 비허용 출처: [차단]
- credentials 정책: [명시 출처 / 위험]
- 프로덕션 와일드카드: [없음 / 노출]
```

## 셀프 체크리스트

- [ ] preflight와 실제 요청 헤더를 모두 확인했는가?
- [ ] 비허용 출처가 실제로 차단되는지 검증했는가?
- [ ] credentials 사용 시 Allow-Origin이 와일드카드가 아닌가?
- [ ] 허용 메서드를 필요한 것으로 최소화했는가?
- [ ] 차단 요청에 대한 로그/모니터링이 있는가?
