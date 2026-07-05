---
id: PB-CL-05
purpose: CORS 오류 증상 파악
applies_when: 브라우저 콘솔에 "blocked by CORS policy" 오류가 발생할 때
version: "1.1"
---

# CORS 오류 문제 파악

교차 출처 요청이 차단될 때, 어떤 출처에서 어디로 가는 요청이 어떤 CORS 규칙에 걸렸는지 정확히 기술하도록 유도하는 질문 세트입니다.

## 용도

"API가 안 돼요"를 넘어, Origin·메서드·헤더·자격증명·Preflight 중 무엇이 문제인지 요청 단위로 좁힙니다.

## 적용 시점

- "Access to XMLHttpRequest at 'X' from origin 'Y' has been blocked by CORS policy"
- "Preflight request failed" 또는 OPTIONS 요청 실패
- 응답에 Access-Control-* 헤더가 없음
- 자격증명(쿠키) 포함 요청만 실패함

## 필수 입력

- 요청을 보내는 출처(Origin, 예: http://localhost:3000)
- 요청 대상 URL과 HTTP 메서드
- 콘솔 CORS 오류 메시지 전문
- Network 탭의 OPTIONS 요청/응답 헤더

## 프롬프트 템플릿

아래 질문에 답해 CORS 차단 지점을 좁혀주세요.

1. **오류 메시지 확인**
   - 콘솔 CORS 오류 전문을 붙여주세요. Origin과 대상 URL이 각각 무엇인가요?
   - 메시지가 "Allow-Origin", "Allow-Methods", "Allow-Headers", "Allow-Credentials" 중 무엇을 지목하나요?

2. **요청 특성 점검**
   - 메서드가 GET/HEAD/POST(Simple Request)인가요, 아니면 PUT/DELETE/PATCH인가요?
   - `Content-Type: application/json`이나 `Authorization` 같은 커스텀 헤더를 붙이나요? (Preflight 유발)
   - Network 탭에 OPTIONS 요청이 먼저 나가고 실패하나요?

3. **자격증명 여부**
   - `credentials: 'include'` 또는 `withCredentials: true`로 쿠키를 함께 보내나요?
   - 서버 응답에 `Access-Control-Allow-Credentials: true`가 있나요? Allow-Origin이 `*`로 되어 있진 않나요?

4. **서버 응답 헤더**
   - 대상 응답에 `Access-Control-Allow-Origin`이 있나요? 값이 내 Origin과 정확히 일치하나요?
   - 서버가 내 통제 하에 있나요(직접 헤더 수정 가능), 아니면 외부 제3자 API인가요?

5. **환경 확인**
   - 로컬 개발에서만 발생하나요, 배포 환경에서도 발생하나요?
   - 프록시(Next.js rewrites, 백엔드 프록시)를 거치나요, 브라우저에서 직접 호출하나요?

## 출력 계약

CORS 문제 정의:
- 증상: [오류 전문 / 지목된 헤더]
- 요청: [Origin → 대상 URL, 메서드]
- Preflight: [OPTIONS 발생·실패 여부]
- 자격증명: [쿠키 포함 여부와 Allow-Credentials 상태]
- 서버 통제권: [직접 수정 가능 / 외부 API]
- 재현 환경: [로컬 / 배포 / 프록시 경유]

## 셀프 체크리스트

- [ ] Origin과 대상 URL을 명확히 확보했는가?
- [ ] Simple Request인지 Preflight 유발 요청인지 구분했는가?
- [ ] 자격증명 포함 여부와 Allow-Credentials 상태를 확인했는가?
- [ ] 서버 응답의 Access-Control-* 헤더 유무를 확인했는가?
- [ ] 서버가 직접 수정 가능한지(프록시 필요 여부) 파악했는가?
