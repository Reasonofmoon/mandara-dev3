---
id: F-03
title: Hydration 불일치 해결
pattern_id: P-03
error_ids: [E-07, E-08, E-09]
tech_scope: Next.js, SSR, 클라이언트 렌더링
---

# Hydration 불일치 해결

서버에서 렌더링된 HTML과 클라이언트에서 렌더링된 결과가 일치하지 않아 발생하는 문제를 해결합니다.

## 1단계: 증상 고정

콘솔 경고:
- "Hydration failed because the initial UI does not match what was rendered on the server"
- "Did not expect server HTML to contain a \<div\>"
- "Text content does not match server-rendered HTML"
- 페이지가 깜박거리거나 콘텐츠가 변함

## 2단계: 재현

```javascript
// ❌ 서버/클라이언트 불일치 예제
import { useEffect, useState } from 'react';

export default function Component() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // 서버에서는 null 렌더링, 클라이언트에서는 내용 렌더링
  if (!isClient) {
    return null;
  }

  return <div>Client-only content</div>;
}

// ❌ 시간/날짜 기반 렌더링
export default function Timestamp() {
  return <div>{new Date().toLocaleString()}</div>;
}

// ❌ 랜덤 데이터
export default function Random() {
  return <div>{Math.random()}</div>;
}
```

## 3단계: 범위 축소

Hydration 불일치의 원인:

1. **조건부 렌더링**: 서버/클라이언트에서 다른 조건
2. **동적 데이터**: 시간, 날짜, 랜덤값
3. **브라우저 API**: localStorage, sessionStorage, window 객체
4. **클라이언트 전용 라이브러리**: 서버에서 실행 불가능한 코드
5. **CSS-in-JS**: 서버/클라이언트 스타일 불일치

## 4단계: 증거 수집

```bash
# Next.js 개발 모드에서 Hydration 오류 확인
npm run dev

# 빌드 후 검증
npm run build && npm run start

# Chrome DevTools에서 Console 탭 확인
# Network 탭에서 SSR HTML 확인
# Application 탭에서 localStorage/sessionStorage 확인
```

```javascript
// 서버 렌더링 HTML 확인
async function compareHTML() {
  const res = await fetch('http://localhost:3000');
  const html = await res.text();
  console.log(html); // 서버 렌더링 결과
}
```

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 복잡도 |
|------|------|--------|
| useEffect 내 상태 변경 | 매우높음 | 낮음 |
| 시간/날짜 직접 사용 | 높음 | 낮음 |
| localStorage 접근 | 높음 | 중간 |
| 조건부 렌더링 | 높음 | 중간 |
| 서드파티 라이브러리 | 중간 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: useEffect로 지연 렌더링 (권장)

```javascript
import { useEffect, useState } from 'react';

export default function Component() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 클라이언트 마운트 후에만 렌더링
  if (!isMounted) {
    return null; // 또는 로딩 상태 표시
  }

  return <div>This renders only on the client</div>;
}
```

### 수정안 2: 동적 임포트 (Dynamic Import)

```javascript
import dynamic from 'next/dynamic';

// ClientComponent는 SSR을 건너뛰고 클라이언트에서만 렌더링
const ClientComponent = dynamic(
  () => import('../components/ClientOnly'),
  { ssr: false }
);

export default function Page() {
  return (
    <div>
      <h1>Server-rendered content</h1>
      <ClientComponent /> {/* 클라이언트에서만 렌더링 */}
    </div>
  );
}
```

### 수정안 3: 시간/날짜 처리

```javascript
import { useEffect, useState } from 'react';

export default function Timestamp() {
  const [time, setTime] = useState(null);

  useEffect(() => {
    // 클라이언트에서만 시간 설정
    setTime(new Date().toLocaleString());
  }, []);

  // 서버/클라이언트 모두에서 같은 내용 표시
  if (time === null) {
    return <div>-</div>;
  }

  return <div>{time}</div>;
}

// 또는 고정값 사용
export default function ISO8601Time() {
  const fixedTime = new Date('2024-01-01T12:00:00Z').toISOString();
  return <div>{fixedTime}</div>;
}
```

### 수정안 4: localStorage 안전하게 접근

```javascript
import { useEffect, useState } from 'react';

export default function WithLocalStorage() {
  const [theme, setTheme] = useState('light');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // 클라이언트에서만 localStorage 접근
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    setIsMounted(true);
  }, []);

  // Hydration이 완료될 때까지 대기
  if (!isMounted) {
    return <div>Loading...</div>;
  }

  return <div className={`theme-${theme}`}>Content</div>;
}
```

### 수정안 5: Suppressible Warning (주의)

```javascript
import { useEffect } from 'react';

// 알려진 불일치를 무시하려는 경우
export default function Component() {
  useEffect(() => {
    // 컴포넌트를 강제 업데이트하여 Hydration 완료
    // ⚠️ 부득이한 경우만 사용
  }, []);

  return <div suppressHydrationWarning>{Math.random()}</div>;
}
```

### 수정안 6: 서드파티 라이브러리 처리

```javascript
import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

// 라이브러리가 window 객체에 의존하는 경우
const DynamicChart = dynamic(
  () => import('chart-library'),
  { ssr: false }
);

export default function ChartComponent() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return <div>Loading chart...</div>;
  }

  return <DynamicChart />;
}
```

## 7단계: 검증

```javascript
// Hydration 검증 테스트
import { render, waitFor } from '@testing-library/react';

describe('Hydration', () => {
  it('should hydrate without warnings', async () => {
    const consoleSpy = jest.spyOn(console, 'error');

    render(<Component />);

    await waitFor(() => {
      // "Hydration" 관련 경고 없음 확인
      const hydrationErrors = consoleSpy.mock.calls.filter(
        call => call[0]?.includes('Hydration')
      );
      expect(hydrationErrors).toHaveLength(0);
    });

    consoleSpy.mockRestore();
  });
});
```

## 8단계: 재발 방지

1. **개발 체크리스트**
   - [ ] 모든 state 초기값이 서버/클라이언트에서 동일한가?
   - [ ] useEffect 외부에서 브라우저 API를 사용하지 않는가?
   - [ ] 시간/날짜를 직접 렌더링하지 않는가?
   - [ ] localStorage를 useEffect 내부에서만 접근하는가?

2. **자동화 검사**

```javascript
// next.config.js에 strict mode 추가
module.exports = {
  reactStrictMode: true,
  // Hydration 문제 감지
};
```

3. **모니터링**

```javascript
// Sentry 또는 유사 도구로 Hydration 오류 추적
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    if (event.message.includes('Hydration')) {
      console.error('Hydration mismatch detected', event);
    }
  });
}
```

## 연결된 프롬프트 블록

- **PB-CL-04-ssr-csr-diff**: SSR/CSR 차이점 분석
- **PB-RP-03-ssr-debugging**: SSR 환경에서 디버깅
- **PB-DG-04-hydration-trace**: Hydration 추적
- **PB-PA-04-ssr-fix**: SSR 호환 코드 작성
- **PB-VF-03-hydration-check**: Hydration 검증
