---
title: React와 Next.js 참조 가이드
version: 1.0
last_updated: 2024-01-15
---

# React와 Next.js 참조 가이드

React Hook API, Next.js App Router, 설정 옵션을 빠르게 찾을 수 있는 참조 가이드입니다.

## React Hooks API

### 상태 관리 Hooks

| Hook | 용도 | 예제 |
|------|------|------|
| `useState` | 상태 관리 | `const [count, setCount] = useState(0)` |
| `useReducer` | 복잡한 상태 | `const [state, dispatch] = useReducer(reducer, init)` |
| `useContext` | 컨텍스트 소비 | `const value = useContext(ThemeContext)` |

### 사이드 이펙트 Hooks

| Hook | 용도 | 의존성 |
|------|------|--------|
| `useEffect` | 사이드 이펙트 | `[]` 마운트시만, `[dep]` 의존시 |
| `useLayoutEffect` | DOM 업데이트 전 | useEffect와 동일하지만 동기 실행 |
| `useInsertionEffect` | CSS-in-JS | 레이아웃 이펙트 전 실행 |

### 성능 최적화 Hooks

| Hook | 용도 |
|------|------|
| `useMemo` | 계산 결과 메모이제이션 |
| `useCallback` | 함수 참조 안정화 |
| `useTransition` | UI 업데이트 우선순위 |
| `useDeferredValue` | 값 업데이트 지연 |

### Ref Hooks

| Hook | 용도 |
|------|------|
| `useRef` | DOM 직접 접근 |
| `useImperativeHandle` | ref 커스터마이제이션 |
| `forwardRef` | 자식 ref 전달 |

## Next.js App Router

### 파일 구조

```
app/
├── page.js          # /
├── layout.js        # 레이아웃
├── not-found.js     # 404
├── error.js         # 에러 바운더리
├── loading.js       # 로딩 상태
├── posts/
│   ├── page.js      # /posts
│   ├── [id]/
│   │   └── page.js  # /posts/[id]
│   └── [...slug]/
│       └── page.js  # /posts/[...slug]
└── api/
    └── route.js     # API 엔드포인트
```

### 핵심 파일 설명

| 파일 | 설명 |
|------|------|
| `layout.js` | 레이아웃 및 공통 UI |
| `page.js` | 라우트별 페이지 |
| `loading.js` | Suspense 폴백 |
| `error.js` | 에러 처리 |
| `not-found.js` | 404 페이지 |
| `route.js` | API 엔드포인트 (GET, POST, etc) |

### 동적 라우팅

```javascript
// [id] - 단일 세그먼트
app/posts/[id]/page.js
// /posts/123

// [...slug] - 다중 세그먼트
app/docs/[...slug]/page.js
// /docs/a/b/c

// [[...slug]] - 선택적
app/blog/[[...slug]]/page.js
// /blog
// /blog/post
// /blog/post/nested
```

## Next.js 설정

### next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 이미지 최적화
  images: {
    domains: ['example.com'],
    unoptimized: false
  },

  // 환경 변수
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
  },

  // 리다이렉트
  redirects: async () => [{
    source: '/old-page',
    destination: '/new-page',
    permanent: true
  }],

  // 재작성
  rewrites: async () => ({
    beforeFiles: [{
      source: '/api/:path*',
      destination: 'http://backend:3000/:path*'
    }]
  }),

  // 헤더
  headers: async () => [{
    source: '/api/:path*',
    headers: [
      { key: 'Cache-Control', value: 'max-age=3600' }
    ]
  }],

  // 성능
  swcMinify: true,
  compress: true,

  // 빌드
  productionBrowserSourceMaps: false
};

module.exports = nextConfig;
```

### .env.local

```bash
# 공개 변수 (NEXT_PUBLIC_ 접두사)
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_APP_ENV=production

# 비공개 변수
DATABASE_URL=postgresql://user:pass@localhost/db
API_KEY=secret-key
JWT_SECRET=jwt-secret-key
```

## React 성능 최적화

### 메모이제이션

```javascript
// useMemo
const memoizedValue = useMemo(() => {
  return expensiveCalculation(a, b);
}, [a, b]);

// useCallback
const memoizedCallback = useCallback(
  (item) => doSomething(item, a),
  [a]
);

// memo
const MyComponent = memo(function Component(props) {
  return <div>{props.name}</div>;
});
```

### 코드 분할

```javascript
// 동적 import
const DynamicComponent = dynamic(
  () => import('../components/DynamicComponent'),
  { loading: () => <p>로딩 중...</p> }
);

// 라우트 기반 코드 분할
const Dashboard = lazy(() => import('./Dashboard'));
const Settings = lazy(() => import('./Settings'));
```

## 일반적인 패턴

### 폼 처리

```javascript
function Form() {
  const [formData, setFormData] = useState({ name: '', email: '' });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const response = await fetch('/api/submit', {
      method: 'POST',
      body: JSON.stringify(formData)
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" value={formData.name} onChange={handleChange} />
      <button type="submit">제출</button>
    </form>
  );
}
```

### 데이터 페칭

```javascript
// useEffect로 데이터 페칭
function DataComponent() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/data')
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>로딩 중...</p>;
  return <div>{JSON.stringify(data)}</div>;
}

// Next.js 서버 컴포넌트
async function ServerComponent() {
  const data = await fetch('http://localhost:3000/api/data');
  const result = await data.json();
  return <div>{JSON.stringify(result)}</div>;
}
```

## 유용한 라이브러리

| 라이브러리 | 용도 |
|----------|------|
| `react-hook-form` | 폼 관리 |
| `zod` / `yup` | 데이터 검증 |
| `zustand` / `recoil` | 상태 관리 |
| `swr` / `react-query` | 데이터 페칭 |
| `framer-motion` | 애니메이션 |
