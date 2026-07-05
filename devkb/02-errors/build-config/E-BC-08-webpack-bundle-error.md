---
id: E-BC-08
title: Webpack 번들 오류
error_class: Build-Config
symptoms:
  - 번들 생성 실패
  - 로더 오류
  - 플러그인 로드 실패
exact_messages:
  - "Cannot find module or its corresponding type declarations"
  - "This relative module was not found"
  - "Error: Child compilation failed"
tech_tags:
  - Webpack
  - Bundling
  - Build Tools
  - Module Resolution
linked_patterns: []
linked_flows: []
---

# Webpack 번들 오류

## 증상
Webpack 번들링 중에 로더 설정 오류, 플러그인 오류, 또는 모듈 해석 실패가 발생합니다. 번들이 생성되지 않거나 크기가 예상과 다를 수 있습니다.

## 정확한 에러 메시지
```
Cannot find module or its corresponding type declarations
This relative module was not found
ERROR in ./src/index.js
Module parse failed: You may need an appropriate loader
Error: Child compilation failed
```

## 발생 맥락
```javascript
// webpack.config.js - 잘못된 예

module.exports = {
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      // 예 1: 로더 설정 오류
      {
        test: /\.css$/,
        // ❌ use 없음
        loader: 'style-loader'
      },
      // 예 2: 로더 순서 오류
      {
        test: /\.scss$/,
        use: [
          'style-loader',
          'css-loader',
          'sass-loader'  // ❌ 순서 잘못됨 (sass-loader 먼저 와야 함)
        ]
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html'
      // ❌ 파일 경로 오류
    })
  ]
};
```

## 필요한 증거
- webpack.config.js 파일
- 번들 에러 메시지
- 로더 및 플러그인 설정
- package.json의 의존성

## 의심 원인
1. 로더 설정 오류 (use 배열 미설정)
2. 로더 순서 오류
3. 플러그인 누락 또는 오류
4. 스타일 로더, 바벨 설정 오류
5. entry/output 경로 오류
6. 모듈 해석 설정 오류

## 빠른 해결법

### 1. 기본 webpack.config.js
```javascript
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
    clean: true
  },
  devServer: {
    static: './dist',
    port: 8080,
    hot: true
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader'
        }
      },
      {
        test: /\.css$/,
        use: [
          'style-loader',
          'css-loader'
        ]
      },
      {
        test: /\.scss$/,
        use: [
          'style-loader',
          'css-loader',
          'sass-loader'
        ]
      },
      {
        test: /\.(png|svg|jpg|jpeg|gif)$/,
        type: 'asset/resource'
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html',
      filename: 'index.html'
    })
  ]
};
```

### 2. Babel 설정
```javascript
// .babelrc
{
  "presets": [
    ["@babel/preset-env", {
      "targets": {
        "browsers": ["last 2 versions"]
      }
    }],
    "@babel/preset-react"
  ],
  "plugins": []
}
```

### 3. 로더 순서 (중요)
```javascript
// CSS: style-loader → css-loader 순서
{
  test: /\.css$/,
  use: ['style-loader', 'css-loader']  // 우에서 좌로 실행
}

// SCSS: sass-loader → css-loader → style-loader
{
  test: /\.scss$/,
  use: ['style-loader', 'css-loader', 'sass-loader']
}

// JavaScript: source-map-loader → babel-loader
{
  test: /\.jsx?$/,
  use: ['source-map-loader', 'babel-loader']
}
```

### 4. TypeScript 지원
```javascript
{
  test: /\.tsx?$/,
  use: 'ts-loader',
  exclude: /node_modules/
}
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM"]
  }
}
```

### 5. 플러그인 설정
```javascript
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');

module.exports = {
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html'
    }),
    new MiniCssExtractPlugin({
      filename: 'styles/[name].[contenthash].css'
    }),
    // 개발 환경에서만
    ...(process.env.NODE_ENV === 'development' ? [
      new BundleAnalyzerPlugin()
    ] : [])
  ]
};
```

### 6. 번들 최적화
```javascript
module.exports = {
  mode: 'production',
  optimization: {
    minimize: true,
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        },
        common: {
          minChunks: 2,
          priority: 5,
          reuseExistingChunk: true
        }
      }
    }
  }
};
```

### 7. 환경 변수
```javascript
const webpack = require('webpack');

module.exports = {
  plugins: [
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
      'process.env.API_URL': JSON.stringify(process.env.API_URL)
    })
  ]
};
```

### 8. 번들 분석
```bash
# 번들 크기 확인
webpack-bundle-analyzer

# 상세 로그
webpack --stats=verbose

# 빌드 시간 측정
speed-measure-webpack-plugin
```

## 연결된 패턴
- E-BC-04-nextjs-config-error
- E-PF-12-bundle-size

## 연결된 플로우
- Webpack 설정 최적화 플로우
- 번들 크기 최적화 플로우

## 재발 방지
1. 공식 문서 예제 참고하여 로더 설정
2. 로더 순서 이해 (우에서 좌로 실행)
3. 번들 분석 도구로 정기적 검사
4. 필요한 플러그인만 사용
5. 캐시 설정으로 빌드 속도 향상
6. 소스맵을 dev에만 포함
