---
id: E-BC-02
title: 모듈을 찾을 수 없음
error_class: Build-Config
symptoms:
  - 빌드 실패
  - 패키지 오류
  - 의존성 누락
exact_messages:
  - "Cannot find module 'lodash'"
  - "Module not found: Error: Can't resolve 'react-router-dom'"
  - "ERR! 404 Not Found - GET https://registry.npmjs.org/non-existent-package"
tech_tags:
  - Dependencies
  - npm
  - yarn
  - pnpm
  - Package Management
linked_patterns: []
linked_flows: []
---

# 모듈을 찾을 수 없음

## 증상
필요한 npm 패키지가 설치되지 않았거나 package.json에 정의되지 않으면 발생합니다. 빌드 또는 런타임에 모듈을 찾을 수 없다는 에러가 나타납니다.

## 정확한 에러 메시지
```
Cannot find module 'lodash'
Module not found: Error: Can't resolve 'react-router-dom'
ERR! 404 Not Found - GET https://registry.npmjs.org/non-existent-package
Could not find "react" in dependencies of "my-package"
```

## 발생 맥락
```typescript
// 잘못된 예 1: 설치하지 않은 패키지 import
import _ from 'lodash';  // ❌ package.json에 없음

// 잘못된 예 2: 잘못된 패키지명
import Router from 'react-router';  // ❌ react-router-dom 필요

// 잘못된 예 3: node_modules 없음
// package.json 있지만 npm install 미실행
import axios from 'axios';  // ❌ node_modules 없음

// 잘못된 예 4: 삭제된 패키지
import oldPackage from 'deprecated-lib';  // ❌ 더 이상 유지되지 않음
```

## 필요한 증거
- 에러 메시지 및 모듈명
- package.json 내용
- node_modules 상태
- 빌드 로그

## 의심 원인
1. 패키지가 npm install로 설치되지 않음
2. package.json에 패키지 추가 후 npm install 미실행
3. 패키지명 오타
4. 잘못된 패키지 버전
5. peerDependencies 미설치
6. monorepo에서 올바른 패키지 참조 안 함

## 빠른 해결법

### 1. 패키지 설치
```bash
# npm
npm install lodash
npm install react-router-dom

# yarn
yarn add lodash
yarn add react-router-dom

# pnpm
pnpm add lodash
pnpm add react-router-dom

# 개발 의존성
npm install --save-dev @types/lodash
```

### 2. package.json 확인 및 설치
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "lodash": "^4.17.21",
    "axios": "^1.4.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/lodash": "^4.14.0"
  }
}
```

```bash
# 모든 의존성 설치
npm install
# 또는
npm ci  # 정확한 버전 설치 (CI 환경 권장)
```

### 3. node_modules 초기화
```bash
# 캐시 제거 및 재설치
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# 또는 yarn 사용
rm -rf node_modules yarn.lock
yarn install
```

### 4. Lock 파일 업데이트
```bash
# package-lock.json 재생성
npm install --package-lock-only

# 또는 yarn.lock 재생성
yarn install --frozen-lockfile
```

### 5. Peer Dependencies 해결
```bash
# peer dependencies 설치
npm install react react-dom

# 또는 자동 설치 (npm 7+)
npm install
```

### 6. 패키지 버전 확인
```bash
# 설치된 패키지 확인
npm list lodash

# 특정 패키지 최신 버전 확인
npm view lodash version

# 모든 의존성 확인
npm list
npm list --depth=0
```

### 7. 패키지명 오타 확인
```bash
# npm 레지스트리에서 검색
npm search lodash

# 올바른 패키지명으로 설치
npm install lodash-es  # lodash 대신 lodash-es인 경우
npm install react-router-dom  # react-router가 아님
```

### 8. GitHub에서 직접 설치
```json
{
  "dependencies": {
    "my-lib": "github:username/repo#branch"
  }
}
```

```bash
npm install github:username/repo#main
```

## 연결된 패턴
- E-BC-03-version-conflict
- E-ST-04-import-path-error

## 연결된 플로우
- 의존성 관리 플로우
- CI/CD 빌드 플로우

## 재발 방지
1. package.json에만 의존성 정의, node_modules는 git 제외
2. package-lock.json (npm) 또는 yarn.lock을 버전 관리
3. CI/CD에서 npm ci 사용 (npm install 대신)
4. 정기적으로 npm audit로 보안 검사
5. 패키지 설치 후 항상 lock 파일 커밋
6. 로컬 개발 환경을 CI 환경과 동일하게 유지
