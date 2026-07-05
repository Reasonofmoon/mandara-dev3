---
id: F-21
title: 번들 크기 최적화
pattern_id: P-21
error_ids: [E-61, E-62, E-63]
tech_scope: 빌드 최적화, 성능, 웹팩
---

# 번들 크기 최적화

JavaScript 번들 크기를 줄여 페이지 로딩 속도를 개선합니다.

## 1단계: 증상 고정

- 페이지 로딩 시간이 오래 걸림
- JavaScript 번들이 5MB 이상
- 모바일에서 매우 느림
- "JavaScript time exceeded"
- Lighthouse 점수 저하

## 6단계: 수정안 선택

### 수정안 1: 번들 분석

```bash
npm install --save-dev webpack-bundle-analyzer

# webpack.config.js에 추가
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [
    new BundleAnalyzerPlugin()
  ]
};

# 빌드 및 분석
npm run build
# http://localhost:8888에서 시각화된 번들 확인
```

### 수정안 2: Code Splitting

```javascript
// ❌ 모든 모듈을 하나의 번들로
import Button from './Button';
import Modal from './Modal';
import HeavyChart from './HeavyChart';

export default App() {
  return <div><Button /><Modal /><HeavyChart /></div>;
}

// ✅ Code Splitting으로 분리
import { lazy, Suspense } from 'react';

const Button = lazy(() => import('./Button'));
const Modal = lazy(() => import('./Modal'));
const HeavyChart = lazy(() => import('./HeavyChart'));

export default function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Button />
      <Modal />
      <HeavyChart />
    </Suspense>
  );
}

// 또는 라우트 기반
import { lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const Admin = lazy(() => import('./pages/Admin'));

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### 수정안 3: Tree Shaking

```javascript
// ❌ 전체 라이브러리 import
import _ from 'lodash';

const unique = _.uniq([1, 2, 2, 3]);

// ✅ 필요한 함수만 import
import { uniq } from 'lodash-es';

const unique = uniq([1, 2, 2, 3]);
```

### 수정안 4: 라이브러리 최적화

```javascript
// ❌ 큰 라이브러리
import moment from 'moment'; // 67KB

// ✅ 가벼운 대안
import dayjs from 'dayjs'; // 2KB
const date = dayjs().format('YYYY-MM-DD');

// 또는
import { format } from 'date-fns';
const date = format(new Date(), 'yyyy-MM-dd');
```

```bash
# 사용 가능한 라이브러리 크기 확인
npm install --save-dev bundle-phobia-cli
phobia dayjs moment date-fns
```

### 수정안 5: 동적 import

```javascript
// ❌ 초기 로딩 시 모두 로드
import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import Editor from './Editor';
import Viewer from './Viewer';

// ✅ 필요할 때만 로드
async function loadEditor() {
  const Editor = await import('./Editor');
  return Editor.default;
}

button.addEventListener('click', async () => {
  const Editor = await loadEditor();
  const editor = new Editor();
});
```

### 수정안 6: 압축 및 최소화

```javascript
// webpack.config.js
const TerserPlugin = require('terser-webpack-plugin');

module.exports = {
  mode: 'production',
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          parse: {
            ecma: 2020
          },
          compress: {
            ecma: 2020,
            drop_console: true // console 제거
          },
          mangle: {
            safari10: true
          }
        }
      })
    ],
    runtimeChunk: 'single',
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        }
      }
    }
  }
};
```

## 연결된 프롬프트 블록

- **PB-CL-22-bundle**: 번들 개념
- **PB-RP-21-bundle-analyze**: 번들 분석
- **PB-DG-22-size-trace**: 크기 추적
- **PB-PA-22-optimization**: 최적화 구현
- **PB-VF-21-perf-test**: 성능 테스트
