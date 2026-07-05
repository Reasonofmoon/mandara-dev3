---
id: E-BC-09
title: ESLint 설정 충돌
error_class: Build-Config
symptoms:
  - ESLint 실행 실패
  - 규칙 충돌 경고
  - 플러그인 로드 오류
exact_messages:
  - "Error: Failed to load plugin 'react'"
  - "fatal: An error occurred while loading the configuration"
  - "Parsing error: Unexpected token"
tech_tags:
  - ESLint
  - Code Quality
  - Linting
  - Configuration
linked_patterns: []
linked_flows: []
---

# ESLint 설정 충돌

## 증상
ESLint 설정이 잘못되었거나 플러그인이 충돌하면 린팅이 실패합니다. 설정 파일 문법 오류, 플러그인 미설치, 또는 규칙 충돌이 원인입니다.

## 정확한 에러 메시지
```
Error: Failed to load plugin 'react'
fatal: An error occurred while loading the configuration
Parsing error: Unexpected token
Error: Could not find 'eslint-plugin-react'
Cannot find module 'eslint-config-next'
```

## 발생 맥락
```javascript
// .eslintrc.js - 잘못된 예

module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended'  // ❌ 플러그인 미설치
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  rules: {
    'react/react-in-jsx-scope': 0  // ❌ 규칙 오류
  }
};

// 또는 JSON 문법 오류
{
  "extends": ["eslint:recommended"],
  "rules": {
    "indent": ["error", 2]
  }
  // ❌ 누락된 쉼표
}
```

## 필요한 증거
- .eslintrc.js 또는 .eslintrc.json
- ESLint 에러 메시지
- package.json의 플러그인 목록
- 사용 중인 파서/플러그인

## 의심 원인
1. ESLint 플러그인 미설치
2. 설정 파일 문법 오류
3. 호환되지 않는 플러그인 버전
4. extends에서 잘못된 설정 참조
5. parser 설정 오류
6. TypeScript 파서 미설치
7. 규칙 설정 오류

## 빠른 해결법

### 1. React 프로젝트 기본 설정
```javascript
// .eslintrc.js
module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  settings: {
    react: {
      version: 'detect'
    }
  },
  rules: {
    'react/react-in-jsx-scope': 0,  // React 17+
    'no-unused-vars': 'warn'
  }
};
```

```bash
npm install --save-dev \
  eslint \
  eslint-plugin-react \
  eslint-plugin-react-hooks
```

### 2. TypeScript 프로젝트
```javascript
// .eslintrc.js
module.exports = {
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended'
  ],
  rules: {
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    'react/react-in-jsx-scope': 0
  }
};
```

```bash
npm install --save-dev \
  eslint \
  @typescript-eslint/parser \
  @typescript-eslint/eslint-plugin \
  eslint-plugin-react
```

### 3. Next.js 프로젝트
```javascript
// .eslintrc.json
{
  "extends": ["next/core-web-vitals"]
}
```

```bash
npm install --save-dev eslint eslint-config-next
```

### 4. JSON 형식 설정
```json
// .eslintrc.json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "extends": [
    "eslint:recommended"
  ],
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "rules": {
    "indent": ["error", 2],
    "linebreak-style": ["error", "unix"],
    "quotes": ["error", "single"],
    "semi": ["error", "always"]
  }
}
```

### 5. .eslintignore 파일
```
node_modules/
dist/
build/
.next/
coverage/
```

### 6. Prettier와 통합
```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'eslint:recommended',
    'prettier'  // prettier 규칙 추가
  ],
  rules: {
    'prettier/prettier': 'error'
  }
};
```

```bash
npm install --save-dev \
  eslint \
  prettier \
  eslint-config-prettier \
  eslint-plugin-prettier
```

### 7. ESLint 실행
```bash
# 모든 파일 린트
eslint .

# 특정 디렉토리만
eslint src/

# 수정 자동 적용
eslint . --fix

# 특정 포맷으로 출력
eslint . --format json > report.json
```

### 8. 캐시 초기화
```bash
# ESLint 캐시 제거
rm -rf .eslintcache

# 재실행
eslint .
```

## 연결된 패턴
- E-BC-06-tsconfig-mismatch
- E-ST-05-typescript-strict-error

## 연결된 플로우
- 코드 품질 관리 플로우
- 개발 환경 설정 플로우

## 재발 방지
1. 플러그인 설치 전에 문서 확인
2. 호환되는 플러그인 버전 확인
3. package.json에 모든 의존성 명시
4. .eslintignore로 불필요한 파일 제외
5. Prettier와 ESLint 규칙 통합
6. CI/CD에서 ESLint 검사 추가
7. pre-commit 훅으로 자동 수정
