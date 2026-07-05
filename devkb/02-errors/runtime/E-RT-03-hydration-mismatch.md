---
id: E-RT-03
title: Hydration 불일치
error_class: Runtime
symptoms:
  - 콘솔 경고 (hydration mismatch)
  - 스타일 또는 콘텐츠 깜빡임
  - 클라이언트와 서버 렌더링 다름
exact_messages:
  - "Hydration failed because the initial UI does not match what was rendered on the server"
  - "Text content does not match server-rendered HTML"
  - "Extra attributes from the server"
tech_tags:
  - React
  - Next.js
  - SSR
  - Hydration
linked_patterns: []
linked_flows: []
---

# Hydration 불일치

## 증상
서버에서 렌더링한 HTML과 클라이언트에서 렌더링한 React 트리가 다르면 hydration이 실패합니다. 경고가 나타나거나 UI가 깜빡일 수 있습니다.

## 정확한 에러 메시지
```
Hydration failed because the initial UI does not match what was rendered on the server
Text content does not match server-rendered HTML
Expected server HTML to contain a matching div
Mismatch between server-rendered and client-rendered React component
```

## 발생 맥락
```typescript
// 잘못된 예 1: 시간 기반 렌더링
function Component() {
  const [date, setDate] = useState(new Date());

  return <div>{date.toLocaleString()}</div>;  // ❌ 서버/클라이언트 다를 수 있음
}

// 잘못된 예 2: 클라이언트만의 조건부 렌더링
function Component() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient ? <ClientComponent /> : null;  // ❌ 처음엔 null, 그 후 다른 콘텐츠
}

// 잘못된 예 3: 난수 생성
function Component() {
  const id = Math.random().toString();
  return <div id={id}>Content</div>;  // ❌ 서버/클라이언트 다른 난수
}

// 잘못된 예 4: localStorage 사용
function Component() {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    setTheme(localStorage.getItem('theme') || 'light');
  }, []);

  return <div className={theme}>Content</div>;  // ❌ 초기값과 다를 수 있음
}
```

## 필요한 증거
- hydration mismatch 경고 메시지
- 서버/클라이언트 렌더링 비교
- 콘텐츠 또는 속성 차이
- useEffect 또는 상태 변경 코드

## 의심 원인
1. useEffect에서만 상태 변경
2. 시간/날짜 기반 렌더링
3. 난수 또는 고유 ID 생성
4. localStorage/sessionStorage 접근
5. 브라우저 API (window, document) 직접 사용
6. 조건부 클라이언트만 렌더링
7. 서버/클라이언트 타임존 차이

## 빠른 해결법

### 1. useEffect로 클라이언트만 업데이트
```typescript
// ❌ 잘못된 코드
function Component() {
  const [date, setDate] = useState(new Date());
  return <div>{date.toLocaleString()}</div>;
}

// ✅ 올바른 코드
function Component() {
  const [date, setDate] = useState<Date | null>(null);

  useEffect(() => {
    setDate(new Date());
  }, []);

  return <div>{date?.toLocaleString() ?? 'Loading...'}</div>;
}
```

### 2. 클라이언트만 렌더링하는 컴포넌트
```typescript
'use client';  // Next.js 13+ App Router

import { useEffect, useState } from 'react';

function ClientOnlyComponent() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  return <div>{new Date().toLocaleString()}</div>;
}

export default ClientOnlyComponent;
```

### 3. 동적 import (Next.js)
```typescript
import dynamic from 'next/dynamic';

// 클라이언트 전용 컴포넌트
const DynamicComponent = dynamic(() => import('./ClientComponent'), {
  ssr: false,
  loading: () => <div>Loading...</div>
});

export default function Page() {
  return <DynamicComponent />;
}
```

### 4. 일관된 ID 생성
```typescript
// ❌ 잘못된 코드
const id = Math.random().toString();

// ✅ 올바른 코드 - 서버에서 미리 생성
const id = useId();  // React 18+

// 또는
const id = `item-${props.itemId}`;
```

### 5. 시간 포맷팅 일관성
```typescript
// ❌ 잘못된 코드 - 브라우저 시간존
function Component() {
  const [date, setDate] = useState(() => new Date());
  return <div>{date.toLocaleString()}</div>;
}

// ✅ 올바른 코드 - ISO 형식 (시간존 무시)
function Component() {
  const [date, setDate] = useState<string>('');

  useEffect(() => {
    setDate(new Date().toISOString());
  }, []);

  return <div>{date}</div>;
}

// 또는 서버에서 생성
function Component({ date }: { date: string }) {
  return <div>{date}</div>;
}

// pages/index.tsx
export async function getStaticProps() {
  return {
    props: {
      date: new Date().toISOString()
    }
  };
}
```

### 6. localStorage 안전한 사용
```typescript
function Component() {
  const [theme, setTheme] = useState('light');
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setTheme(savedTheme);
    }
  }, []);

  if (!isMounted) {
    return null;
  }

  return <div className={theme}>Content</div>;
}
```

### 7. 사용자 정의 Hook
```typescript
function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState(initialValue);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    try {
      const item = window.localStorage.getItem(key);
      if (item) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.error(error);
    }
  }, [key]);

  if (!isMounted) {
    return initialValue;
  }

  return storedValue;
}

function Component() {
  const theme = useLocalStorage('theme', 'light');
  return <div className={theme}>Content</div>;
}
```

### 8. suppressHydrationWarning (임시 해결)
```typescript
// ❌ 권장하지 않음
function Component() {
  return (
    <div suppressHydrationWarning>
      {new Date().toLocaleString()}
    </div>
  );
}
```

## 연결된 패턴
- E-RT-01-cannot-read-undefined
- E-LS-02-stale-closure

## 연결된 플로우
- Next.js SSR/Hydration 플로우
- React 상태 관리 플로우

## 재발 방지
1. 서버/클라이언트에서 동일한 초기값 제공
2. useEffect에서만 클라이언트 로직 처리
3. dynamic import로 클라이언트 전용 컴포넌트 분리
4. useId() 사용으로 안전한 ID 생성
5. 시간/난수 관련 렌더링은 useEffect 후 업데이트
6. localStorage 접근 전 isMounted 확인
7. console 경고 정기적으로 확인
