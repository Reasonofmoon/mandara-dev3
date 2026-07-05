---
id: PB-CL-04
purpose: SSR/CSR Hydration 불일치 증상 파악
applies_when: "Hydration failed" 경고가 뜨거나 페이지가 깜박이며 콘텐츠가 바뀔 때
version: "1.1"
---

# Next.js Hydration 불일치 문제 파악

서버 렌더 HTML과 클라이언트 렌더 결과가 달라 발생하는 hydration 오류를, 어떤 값이 서버/클라이언트에서 달라지는지 짚어내도록 유도하는 질문 세트입니다.

## 용도

"화면이 깜박여요"를 넘어, 불일치를 만드는 동적 값(시간·랜덤·브라우저 API·조건부 렌더)을 특정하도록 좁힙니다.

## 적용 시점

- "Hydration failed because the initial UI does not match what was rendered on the server"
- "Text content does not match server-rendered HTML"
- "Did not expect server HTML to contain a ..."
- 첫 로드 시 콘텐츠가 잠깐 보였다가 바뀌거나 깜박임

## 필수 입력

- 경고가 가리키는 컴포넌트 코드
- 콘솔 경고 전문 (서버/클라이언트 diff 부분 포함)
- 해당 컴포넌트가 렌더링하는 동적 값의 출처

## 프롬프트 템플릿

아래 질문에 답해 불일치의 출처를 좁혀주세요.

1. **경고 내용 확인**
   - 콘솔 경고 전문을 붙여주세요. 서버 값과 클라이언트 값의 diff가 표시되나요?
   - 경고가 특정 컴포넌트/텍스트를 지목하나요?

2. **동적 값 점검**
   - 렌더 본문에서 `new Date()`, `Date.now()`, `Math.random()` 같은 값을 직접 출력하나요?
   - 로케일·타임존에 따라 달라지는 포맷(`toLocaleString` 등)을 쓰나요?

3. **브라우저 API 접근**
   - 렌더 중(useEffect 밖에서) `window`, `localStorage`, `sessionStorage`, `navigator`에 접근하나요?
   - `typeof window !== 'undefined'` 같은 분기로 서버/클라이언트 렌더 결과가 달라지나요?

4. **조건부 렌더링**
   - `isClient`/`isMounted` 같은 상태로 서버에서는 null, 클라이언트에서는 다른 걸 렌더하나요?
   - 서드파티 라이브러리가 window에 의존해 SSR에서 다른 마크업을 내나요?

5. **범위·재현**
   - `npm run dev`와 `npm run build && npm run start` 모두에서 재현되나요?
   - 특정 컴포넌트를 dynamic import(`ssr: false`)로 빼면 사라지나요?

## 출력 계약

Hydration 불일치 문제 정의:
- 증상: [경고 전문 / 깜박임 여부]
- 불일치 값: [시간/랜덤/로케일/브라우저 API 중 무엇]
- 접근 위치: [렌더 본문 / useEffect 내부]
- 조건부 렌더: [isClient 등 분기 유무]
- 재현 환경: [dev / prod 빌드]

## 셀프 체크리스트

- [ ] 서버/클라이언트 diff가 담긴 경고 전문을 확보했는가?
- [ ] 렌더 본문의 동적 값(시간·랜덤)을 확인했는가?
- [ ] useEffect 밖 브라우저 API 접근 여부를 확인했는가?
- [ ] 조건부 렌더링 분기를 파악했는가?
- [ ] dev/prod 양쪽 재현 여부를 확인했는가?
