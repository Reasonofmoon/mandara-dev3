---
id: PB-VF-03
purpose: Hydration 불일치 수정이 SSR/CSR 출력을 일치시켰고 회귀가 없는지 검증
applies_when: Hydration 불일치(F-03) 수정을 적용한 뒤 서버/클라이언트 렌더 정합성을 확인할 때
version: "1.1"
---

# Next.js Hydration 불일치 해결 검증

지연 렌더링, dynamic import(ssr:false), 시간·localStorage 안전 접근 등의 수정을 적용한 뒤, 서버 HTML과 클라이언트 렌더 결과가 일치하고 Hydration 경고가 사라졌으며 프로덕션 빌드에서도 재현되지 않는지 확인하는 검증 프롬프트입니다.

## 용도

F-03 플로우의 6단계(수정) 이후, dev와 prod(build+start) 양쪽에서 Hydration 오류 소멸을 확인하고 콘텐츠 깜박임·레이아웃 시프트 회귀를 점검합니다.

## 적용 시점

- "Hydration failed" / "Text content does not match" 경고를 수정한 직후
- 브라우저 API(window, localStorage) 접근을 useEffect로 옮긴 뒤
- 배포 전 SSR 페이지의 안정성을 최종 확인할 때

## 필수 입력

- 수정한 페이지/컴포넌트 경로
- 문제가 났던 동적 값의 출처 (시간, 랜덤, localStorage 등)
- 재현 URL

## 프롬프트 템플릿

아래 Hydration 수정에 대해 서버/클라이언트 정합성을 검증하고 회귀가 없는지 확인해줘.

**대상:** [페이지/컴포넌트]
**원인이었던 동적 값:** [예: new Date(), localStorage.theme]

1. **성공 기준 정의**
   - dev, prod 콘솔 모두 "Hydration" 관련 경고 0건
   - 최초 페인트와 hydration 후 DOM이 동일 (깜박임 없음)
   - 서버 HTML과 클라이언트 마운트 결과 문자열 일치

2. **dev/prod 이중 검증**
   ```bash
   npm run dev        # 개발 모드 경고 확인
   npm run build && npm run start   # 프로덕션 모드 재확인
   ```
   - 두 모드 모두에서 경고 없음을 확인 (dev에서만 잡히는 케이스 주의)

3. **회귀 매트릭스**
   | 상황 | 기대 | 결과 |
   |------|------|------|
   | 첫 로드(캐시 없음) | 경고 0, 깜박임 없음 | |
   | 새로고침 | 서버/클라 동일 | |
   | localStorage 값 있음/없음 | 양쪽 모두 안정 | |
   | 시간 표시 컴포넌트 | 서버=placeholder, 이후 갱신 | |

4. **자동화 테스트** — 콘솔 error 감시
   ```javascript
   it('Hydration 경고 없이 렌더된다', async () => {
     const spy = jest.spyOn(console, 'error');
     render(<Component />);
     await waitFor(() => {
       const hy = spy.mock.calls.filter(c => c[0]?.includes?.('Hydration'));
       expect(hy).toHaveLength(0);
     });
     spy.mockRestore();
   });
   ```

5. **모니터링 지표**
   - 프로덕션에서 Hydration 오류를 Sentry 등으로 추적 중인지
   - CLS(Cumulative Layout Shift)가 임계값 이하인지

## 출력 계약

```
검증 결과: [통과 / 실패]
- dev 경고: [0건 / N건]
- prod 경고: [0건 / N건]
- 회귀 매트릭스: [모두 통과 / 실패]
- CLS/깜박임: [정상 / 이상]
- 모니터링 연결: [있음 / 없음]
```

## 셀프 체크리스트

- [ ] dev와 prod 빌드 양쪽에서 확인했는가?
- [ ] 브라우저 API를 useEffect 밖에서 호출하는 코드가 남았는가?
- [ ] suppressHydrationWarning을 남용하지 않았는가?
- [ ] 콘솔 error 감시 자동화 테스트를 추가했는가?
- [ ] 프로덕션 Hydration 오류 모니터링이 연결되어 있는가?
