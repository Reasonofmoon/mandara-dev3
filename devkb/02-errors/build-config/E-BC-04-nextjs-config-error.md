---
id: E-BC-04
title: Next.js 설정 오류
error_class: Build-Config
symptoms:
  - 빌드 실패
  - next.config.js 파싱 실패
  - 플러그인 로드 오류
exact_messages:
  - "Error: Could not find a valid build in the '.next' directory"
  - "error: Your page ~/pages/api/route.js does not have a method export"
  - "error: next/image: Invalid src prop"
tech_tags:
  - Next.js
  - Configuration
  - Build System
  - Webpack
linked_patterns: []
linked_flows: []
---

# Next.js 설정 오류

## 증상
next.config.js 설정이 잘못되었거나 페이지 구조가 Next.js 규칙을 따르지 않으면 발생합니다. 빌드 시간 또는 런타임에 에러가 나타날 수 있습니다.

## 정확한 에러 메시지
```
Error: Could not find a valid build in the '.next' directory
error: Your page ~/pages/api/route.js does not have a method export
error: next/image: Invalid src prop
Config error: invalid option provided to Image Optimization
```

## 발생 맥락
```javascript
// 잘못된 예 1: next.config.js 문법 오류
module.exports = {
  webpack: (config, { isServer }) => {
    config.module.rules.push({
      test: /\.custom$/,
      loader: 'custom-loader'
    })
    return config;
  }
  // ❌ 누락된 쉼표
};

// 잘못된 예 2: 유효하지 않은 설정 옵션
module.exports = {
  swcMinify: true,
  experimental: {
    appDir: true,
    invalidOption: true  // ❌ 지원하지 않는 옵션
  }
};

// 잘못된 예 3: API 라우트 작성 오류
// pages/api/users.js
export default function handler(req, res) {  // ❌ default export만 지원
  res.status(200).json({ name: 'John' });
}

// 잘못된 예 4: Image 컴포넌트 오류
<Image src="image.jpg" />  // ❌ width, height 필요

// 잘못된 예 5: 동적 라우트 오류
// pages/users/[id]/edit/[tab].js
// getStaticPaths에서 필수 경로 미정의
export async function getStaticPaths() {
  return { paths: [], fallback: false };  // ❌ 모든 경로에서 404
}
```

## 필요한 증거
- next.config.js 파일
- 빌드 에러 메시지
- pages/app 디렉토리 구조
- 빌드 로그

## 의심 원인
1. next.config.js 문법 오류 또는 누락된 쉼표
2. 지원하지 않는 설정 옵션
3. API 라우트에서 named export 사용
4. Image 컴포넌트에서 width/height 누락
5. 동적 라우트 fallback 설정 오류
6. webpack 설정 오류
7. next.config.js 로드 실패

## 빠른 해결법

### 1. next.config.js 기본 구조
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.example.com'
      }
    ]
  },
  experimental: {
    appDir: true
  }
};

module.exports = nextConfig;
```

### 2. API 라우트 올바른 작성
```typescript
// pages/api/users.ts
import type { NextApiRequest, NextApiResponse } from 'next';

type ResponseData = {
  name: string;
};

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  if (req.method === 'GET') {
    res.status(200).json({ name: 'John Doe' });
  } else if (req.method === 'POST') {
    // 처리
  } else {
    res.status(405).end();  // Method Not Allowed
  }
}
```

### 3. Image 컴포넌트 올바른 사용
```typescript
import Image from 'next/image';

// ❌ 잘못된 코드
<Image src="image.jpg" alt="description" />

// ✅ 올바른 코드
<Image
  src="/image.jpg"
  alt="description"
  width={400}
  height={300}
/>

// 또는 fill 사용
<Image
  src="/image.jpg"
  alt="description"
  fill
  style={{ objectFit: 'cover' }}
/>
```

### 4. 동적 라우트 getStaticPaths
```typescript
// pages/posts/[id].tsx
export async function getStaticPaths() {
  const posts = await fetchPosts();

  return {
    paths: posts.map(post => ({
      params: { id: post.id.toString() }
    })),
    fallback: 'blocking'  // 또는 true
  };
}

export async function getStaticProps({ params }: { params: { id: string } }) {
  const post = await fetchPost(params.id);

  return {
    props: { post },
    revalidate: 3600  // ISR: 1시간마다 재검증
  };
}
```

### 5. Webpack 설정 올바른 작성
```javascript
// next.config.js
module.exports = {
  webpack: (config, { isServer }) => {
    config.module.rules.push({
      test: /\.custom$/,
      loader: 'custom-loader'
    });

    // 조건부 설정
    if (isServer) {
      config.externals.push({
        'fs': 'fs'
      });
    }

    return config;
  }
};
```

### 6. App Router (Next.js 13+)
```typescript
// app/page.tsx
export default function Home() {
  return <div>Welcome</div>;
}

// app/api/users/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ users: [] });
}

export async function POST(request: Request) {
  const data = await request.json();
  return NextResponse.json({ success: true });
}
```

### 7. 설정 검증
```bash
# next.config.js 검증
node -e "const config = require('./next.config.js'); console.log('Config valid:', config);"

# 빌드 테스트
npm run build

# lint 실행
npm run lint
```

### 8. 캐시 초기화
```bash
# .next 디렉토리 삭제
rm -rf .next

# 빌드 다시 실행
npm run build
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-BC-06-tsconfig-mismatch

## 연결된 플로우
- Next.js 프로젝트 설정 플로우
- 빌드 최적화 플로우

## 재발 방지
1. next.config.js 변경 후 빌드 테스트
2. TypeScript 사용으로 설정 타입 검증
3. 공식 문서 예제 참고하기
4. ESLint로 설정 파일 검사
5. CI/CD에서 빌드 검증
6. 정기적으로 Next.js 버전 업그레이드하고 마이그레이션 가이드 확인
