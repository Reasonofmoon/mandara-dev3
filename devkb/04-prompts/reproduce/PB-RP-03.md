---
id: PB-RP-03
purpose: Hydration 불일치를 SSR/CSR 대조로 반복 재현
applies_when: Next.js hydration 경고를 안정적으로 재현하고 원인 노드를 특정해야 할 때
version: "1.1"
---

# Hydration 불일치 재현 절차 수립

서버 렌더 HTML과 클라이언트 렌더 결과의 차이로 발생하는 hydration 경고를, 서버 응답과 클라이언트 출력을 직접 대조하는 방식으로 반복 재현하는 프롬프트입니다.

## 용도

깜박임/경고가 산발적으로 나타나는 상황에서 어떤 노드가 서버/클라이언트에서 달라지는지를 고정하고, 프로덕션 빌드에서도 재현되는지를 확인합니다.

## 적용 시점

- "Hydration failed because the initial UI does not match" 경고가 뜰 때
- "Text content does not match server-rendered HTML"이 특정 페이지에서만 발생할 때
- 시간/랜덤/localStorage 등 동적 소스가 의심될 때
- dev에서만 보이는지 build에서도 보이는지 구분해야 할 때

## 필수 입력

- 경고가 뜨는 페이지 경로(route)
- 의심 컴포넌트와 동적 소스(Date, Math.random, window, localStorage 등)
- Next.js 버전 및 렌더 모드(App/Pages Router)
- 경고 전문과 지목된 DOM 태그

## 프롬프트 템플릿

아래 지시를 AI 도구나 팀원에게 그대로 전달하세요.

```
다음 hydration 불일치를 서버/클라이언트 출력 대조로 재현하고, 어긋나는 노드를 특정해줘.

[증상]
- route: (경로)
- 경고 전문: (붙여넣기)

[재현 절차 지시]
1. dev와 prod를 분리해 재현 조건부터 고정:
   - npm run dev 에서 경고 재현 확인
   - npm run build && npm run start 에서도 재현되는지 확인 (dev 전용인지 구분)
2. 서버 HTML을 직접 캡처해 클라이언트와 대조:
   curl -s http://localhost:3000<route> | grep -n "<의심 텍스트/태그>"
   → 서버가 실제로 어떤 값을 내려보내는지 확인
3. 브라우저 콘솔에서 클라이언트 첫 렌더 값을 캡처해 서버 값과 문자 단위로 비교.
4. 동적 소스를 하나씩 제거하며 격리:
   (a) new Date()/toLocaleString 직접 렌더 제거
   (b) Math.random 제거
   (c) localStorage/window 접근을 useEffect 밖에서 사용하는지 확인
   (d) 조건부 렌더(isClient 패턴)로 서버가 null을 내리는지 확인
5. 원인 후보 컴포넌트를 최소 페이지로 축소해 단독 재현.

[재현 조건 고정]
- 재현되는 route와 새로고침/네비게이션 조건을 명시.
- dev/prod 각각에서 5회 새로고침 중 몇 회 경고가 뜨는지 재현율 기록.
- 서버 문자열 vs 클라이언트 문자열의 차이를 그대로 첨부.
```

## 출력 계약

- 서버 HTML 발췌 vs 클라이언트 렌더 값의 차이(diff)
- 원인 동적 소스(a~d 중) 확정 및 해당 컴포넌트
- dev/prod 각각의 재현 여부와 재현율
- 최소 재현 페이지(단독 라우트) 코드

## 셀프 체크리스트

- [ ] dev와 prod 빌드 양쪽에서 재현 여부를 확인했는가?
- [ ] curl로 서버 HTML을 캡처해 클라이언트와 대조했는가?
- [ ] 동적 소스를 하나씩 격리했는가?
- [ ] 어긋나는 노드/문자열을 특정했는가?
- [ ] 재현율(N회 중 M회)을 기록했는가?
