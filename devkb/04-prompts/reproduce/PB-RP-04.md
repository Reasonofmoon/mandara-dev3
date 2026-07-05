---
id: PB-RP-04
purpose: CORS 차단을 preflight 요청 단위로 반복 재현
applies_when: CORS 오류를 브라우저 밖 curl로 격리해 preflight/실요청 실패 지점을 특정해야 할 때
version: "1.1"
---

# CORS 차단 재현 절차 수립

교차 출처 요청이 차단되는 CORS 오류를, 브라우저의 노이즈를 걷어내고 curl로 preflight(OPTIONS)와 실제 요청을 분리 재현하는 프롬프트입니다.

## 용도

"CORS policy에 의해 차단됨" 경고가 preflight 단계 실패인지, 실요청 응답 헤더 누락인지, 자격증명 설정 충돌인지를 요청 단위로 좁혀 결정론적으로 재현합니다.

## 적용 시점

- "has been blocked by CORS policy"가 콘솔에 뜰 때
- Network 탭에서 OPTIONS 요청만 실패할 때
- credentials 포함 요청에서 Allow-Credentials 헤더 오류가 날 때
- 커스텀 헤더/비단순 메서드(PUT/DELETE/PATCH) 사용 시 실패할 때

## 필수 입력

- 요청 출처(Origin)와 대상 API URL
- 요청 메서드와 커스텀 헤더(Content-Type, Authorization 등)
- credentials 포함 여부(include/omit)
- 브라우저 콘솔 오류 전문

## 프롬프트 템플릿

아래 지시를 AI 도구나 팀원에게 그대로 전달하세요.

```
다음 CORS 차단을 curl로 preflight와 실요청을 분리해 재현하고, 실패 지점을 특정해줘.

[증상]
- Origin: (예: http://localhost:3000)
- 대상: (API URL)
- 콘솔 오류: (전문 붙여넣기)

[재현 절차 지시]
1. Preflight(OPTIONS)를 단독 재현해 응답 헤더를 확인:
   curl -i -X OPTIONS '<API URL>' \
     -H 'Origin: <Origin>' \
     -H 'Access-Control-Request-Method: <메서드>' \
     -H 'Access-Control-Request-Headers: content-type,authorization'
   → 응답에 Access-Control-Allow-Origin / -Methods / -Headers 가 있는지 대조.
2. 실제 요청을 재현해 응답 헤더 누락 여부 확인:
   curl -i -X <메서드> '<API URL>' -H 'Origin: <Origin>'
   → Access-Control-Allow-Origin 값이 Origin과 일치하는지 확인.
3. 자격증명 시나리오 격리:
   - credentials: 'include' 인 경우 Allow-Credentials: true 와
     Allow-Origin이 * 가 아닌 정확한 Origin인지 확인.
4. 실패 유형을 아래로 분류:
   (a) preflight OPTIONS 자체가 거부/누락
   (b) 실요청 Allow-Origin 헤더 누락
   (c) Allow-Origin이 * 인데 credentials 사용(충돌)
   (d) 커스텀 헤더가 Allow-Headers에 없음

[재현 조건 고정]
- 재현에 쓴 정확한 curl 명령을 그대로 첨부.
- 동일 명령 반복 시 항상 재현되는지(결정론) 확인해 재현율 기록.
- 서버가 내려준 실제 응답 헤더 전체를 붙여넣기.
```

## 출력 계약

- preflight/실요청 각각의 curl 명령과 응답 헤더 전문
- 실패 유형(a~d 중) 확정 및 근거 헤더
- 브라우저 재현과 curl 재현이 일치하는지 여부
- 결정론적 재현 명령 1줄(복붙용)

## 셀프 체크리스트

- [ ] preflight(OPTIONS)와 실요청을 분리 재현했는가?
- [ ] 응답의 Access-Control-* 헤더를 실제로 확인했는가?
- [ ] credentials/Origin 충돌 케이스를 격리했는가?
- [ ] 재현에 쓴 curl 명령을 그대로 기록했는가?
- [ ] 매 실행마다 동일 재현(결정론)인지 확인했는가?
