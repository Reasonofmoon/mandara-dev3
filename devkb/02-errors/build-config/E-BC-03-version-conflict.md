---
id: E-BC-03
title: 의존성 버전 충돌
error_class: Build-Config
symptoms:
  - 빌드 실패
  - 호환성 오류
  - peer dependency 경고
exact_messages:
  - "peer dep missing: react@* should be 17 or 18, got 16"
  - "Could not resolve dependency: react-dom@18.0.0"
  - "npm ERR! peer dep missing: react-router-dom@6.0.0"
tech_tags:
  - Dependencies
  - Version Management
  - npm
  - Package Resolution
linked_patterns: []
linked_flows: []
---

# 의존성 버전 충돌

## 증상
패키지의 peer dependency, semver 범위 또는 호환성 요구사항이 충족되지 않을 때 발생합니다. 서로 다른 버전의 같은 패키지가 필요할 때 나타납니다.

## 정확한 에러 메시지
```
peer dep missing: react@* should be ^17.0.0, got ^16.0.0
Could not resolve dependency: react-dom@18.0.0 requires react@18
npm ERR! peer dep missing: react-router-dom@6.0.0
npm WARN peer dep missing: typescript@5 (peer required by some package)
```

## 발생 맥락
```json
{
  "dependencies": {
    "react": "^16.8.0",
    "react-dom": "^16.8.0",
    "my-ui-library": "^2.0.0"
  }
}
```

```typescript
// my-ui-library@2.0.0의 package.json
// peerDependencies: { react: "^18.0.0" }
// react 16과 react 18은 호환되지 않음 ❌
```

## 필요한 증거
- npm install 또는 빌드 에러 메시지
- package.json 의존성 목록
- lock 파일 (package-lock.json, yarn.lock)
- 패키지의 peerDependencies 요구사항

## 의심 원인
1. 패키지가 요구하는 peer dependency 버전 불일치
2. 여러 패키지가 같은 라이브러리의 다른 버전 필요
3. 새 메이저 버전으로 업그레이드 시 호환성 미확인
4. lock 파일 손상 또는 stale
5. 패키지 간 불명확한 버전 범위

## 빠른 해결법

### 1. 버전 확인 및 호환성 맞추기
```bash
# 현재 설치된 버전 확인
npm list react react-dom

# 특정 패키지의 요구사항 확인
npm info my-ui-library peerDependencies
```

```json
{
  "dependencies": {
    "react": "^18.2.0",      // ^18.0.0 요구
    "react-dom": "^18.2.0",  // ^18.0.0 요구
    "my-ui-library": "^2.0.0"
  }
}
```

### 2. Lock 파일 업데이트
```bash
# npm
rm package-lock.json
npm install

# yarn
rm yarn.lock
yarn install

# pnpm
rm pnpm-lock.yaml
pnpm install
```

### 3. 특정 버전으로 업그레이드
```bash
# React 16에서 18로 업그레이드
npm install react@^18.2.0 react-dom@^18.2.0

# 관련 타입 패키지도 함께 업그레이드
npm install @types/react@^18.0.0 @types/react-dom@^18.0.0
```

### 4. 호환 가능한 패키지 찾기
```bash
# 호환 가능한 버전 목록 확인
npm view react-query versions

# 특정 호환성 조건으로 설치
npm install react-query@^3.0.0  # React 16 호환
# 또는
npm install react-query@^4.0.0  # React 18 호환
```

### 5. npm 8+ (peer deps 자동 설치)
```bash
# npm 8 이상에서는 peer deps를 자동으로 설치하려고 시도
npm install

# 여전히 충돌이 있으면 강제 설치
npm install --legacy-peer-deps
```

### 6. 여러 버전 필요 시 (monorepo)
```json
{
  "workspaces": [
    "packages/app",
    "packages/lib-v1",
    "packages/lib-v2"
  ]
}
```

```bash
# 각 워크스페이스에서 다른 버전 관리 가능
cd packages/lib-v1
npm install react@^16.0.0

cd packages/lib-v2
npm install react@^18.0.0
```

### 7. 조건부 peer dependencies
```json
{
  "peerDependenciesMeta": {
    "react": {
      "optional": true
    },
    "react-dom": {
      "optional": true
    }
  }
}
```

### 8. 버전 범위 조정
```json
{
  "dependencies": {
    "react": ">=16.8.0 <19.0.0",     // 더 넓은 범위
    "react-dom": ">=16.8.0 <19.0.0",
    "utility-lib": "^1.0.0"
  }
}
```

## 연결된 패턴
- E-BC-02-module-not-found
- E-BC-06-tsconfig-mismatch

## 연결된 플로우
- 의존성 관리 플로우
- 패키지 업그레이드 플로우

## 재발 방지
1. 주요 라이브러리 업그레이드 전에 호환성 문서 확인
2. 호환 가능한 버전 범위 명시
3. lock 파일을 git에 커밋하여 일관성 유지
4. 정기적으로 npm audit로 의존성 검사
5. CI/CD에서 npm ci 사용
6. 새 패키지 추가 시 peer dependencies 확인
7. monorepo에서는 각 패키지의 의존성 명확히 정의
