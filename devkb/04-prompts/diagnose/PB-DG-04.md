---
id: PB-DG-04
purpose: Hydration 불일치의 근본 원인을 확률·검증 비용 순으로 진단
applies_when: Next.js SSR에서 서버/클라이언트 렌더링 결과가 어긋날 때
version: "1.1"
---

# Next.js Hydration 불일치 원인 진단

Hydration 실패 경고가 재현된 상태에서 서버/클라이언트 출력이 갈라지는 지점을 원인 후보 순으로 정렬하고, 각 가설을 확정 또는 기각할 증거 수집 방법을 지시하는 진단 프롬프트입니다.

## 용도

`useEffect` 내 상태 변경, 시간/날짜/랜덤값 직접 사용, `localStorage`/`window` 접근, 조건부 렌더링, 서드파티 라이브러리 중 어느 것이 서버/클라이언트 출력을 갈라놓는지 좁혀냅니다. 서버 HTML과 클라이언트 DOM을 대조해 검증합니다.

## 적용 시점

- "Hydration failed because the initial UI does not match" 경고 발생
- "Text content does not match server-rendered HTML" 경고 발생
- 페이지가 첫 로드 직후 깜박이며 콘텐츠가 바뀜
- 증상은 확인됐으나 어느 컴포넌트가 원인인지 특정되지 않음

## 필수 입력

- 경고에 언급된 컴포넌트 트리 위치와 소스 코드
- 서버 렌더링 HTML (curl 또는 View Source)과 클라이언트 렌더링 결과
- 브라우저 API(`window`, `localStorage`, `Date`, `Math.random`) 사용 위치
- 콘솔 경고 전문

## 프롬프트 템플릿

```
다음 Next.js Hydration 불일치의 원인을 진단하라.

[문제 컴포넌트 코드]
<경고에 언급된 컴포넌트 전체 소스>

[서버 HTML vs 클라이언트 DOM]
<불일치하는 노드/텍스트 diff>

[콘솔 경고]
<경고 전문>

다음 순서로 진단하라:

1. 원인 후보를 확률·검증비용 순으로 정렬하라:
   - (매우높음/저비용) 렌더 본문에서 new Date() / Math.random() 직접 출력
   - (높음/저비용) 렌더 중 localStorage / window / navigator 접근
   - (높음/중간) typeof window 등 서버/클라이언트 분기로 다른 트리 렌더
   - (중간/고비용) 서드파티 라이브러리가 브라우저 전용 값을 렌더에 주입

2. 각 가설의 확정/기각 증거를 수집하라:
   - 동적 값: 서버 HTML(curl http://localhost:3000)과 클라이언트 DOM에서
     해당 텍스트 노드를 대조. 두 값이 다르면 → 동적 값이 원인
   - 브라우저 API: 렌더 경로에서 window/localStorage 접근을 grep.
     해당 값을 useEffect로 옮기고 초기 렌더를 고정값으로 바꿨을 때
     경고가 사라지면 → 브라우저 API가 원인
   - 조건부 렌더링: typeof window 분기를 임시로 서버 기준으로 고정해
     경고가 사라지는지 확인
   - 서드파티: 의심 컴포넌트를 dynamic(() => import, { ssr:false })로
     감쌌을 때 경고가 사라지면 → 해당 라이브러리가 원인

3. 가장 확률 높고 검증 비용 낮은 가설부터 확정하고,
   확정된 원인과 증거를 명시하라. 기각된 가설도 근거와 함께 기록하라.
```

## 출력 계약

```
확정 원인: [예: Timestamp 컴포넌트가 렌더 본문에서 new Date() 출력]
증거: [예: 서버 HTML은 12:00, 클라이언트 DOM은 12:03으로 텍스트 노드 불일치]
기각된 후보:
  - localStorage 접근: [기각 근거]
  - 서드파티 라이브러리: [기각 근거]
다음 단계: [F-03 6단계 수정안 중 적용할 수정안 번호]
```

## 셀프 체크리스트

- [ ] 원인 후보를 확률·검증비용 순으로 정렬했는가?
- [ ] 서버 HTML과 클라이언트 DOM을 실제로 대조했는가?
- [ ] 렌더 경로의 브라우저 API 접근을 grep으로 확인했는가?
- [ ] dynamic ssr:false로 서드파티 원인 여부를 격리했는가?
- [ ] 확정 원인이 F-03의 수정안과 매핑되는가?
