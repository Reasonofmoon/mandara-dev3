---
id: E-ST-04
title: import 경로 오류
error_class: Syntax-Type
symptoms:
  - 모듈을 찾을 수 없음
  - 파일이 없다고 표시됨
  - 런타임에 undefined
exact_messages:
  - "Cannot find module '../components/Button'"
  - "Cannot find module 'axios' in '/project/src'"
  - "Module not found: Error: Can't resolve './utils'"
tech_tags:
  - JavaScript
  - Modules
  - Import/Export
  - File System
linked_patterns: []
linked_flows: []
---

# import 경로 오류

## 증상
모듈을 import할 때 경로가 잘못되어 파일을 찾을 수 없습니다. 상대 경로, 절대 경로, 또는 패키지명이 잘못될 때 발생합니다.

## 정확한 에러 메시지
```
Cannot find module '../components/Button'
Cannot find module 'axios' in '/project/src'
Module not found: Error: Can't resolve './utils'
You may need to install package 'lodash'
Invalid file path: src/pages/index.ts is not under /project/src
```

## 발생 맥락
```typescript
// 잘못된 예 1: 경로 오류
// 파일 구조:
// src/
//   pages/
//     index.tsx
//   components/
//     Button.tsx

import Button from '../Button';  // ❌ 상대 경로 오류
import Button from './Button';   // ❌ 현재 디렉토리에 없음

// 잘못된 예 2: 파일 확장자 누락
import { utils } from './utils';  // ❌ utils.ts 파일이 있지만 확장자 생략

// 잘못된 예 3: 잘못된 패키지명
import axios from 'axios';  // 설치되지 않은 패키지

// 잘못된 예 4: 존재하지 않는 인덱스 파일
import config from './config';  // ❌ config.ts, config/index.ts 모두 없음
```

## 필요한 증거
- 에러 메시지 및 파일 경로
- 현재 파일의 위치
- 대상 파일의 위치
- 프로젝트 디렉토리 구조

## 의심 원인
1. 상대 경로 계산 오류
2. 파일이 존재하지 않음
3. 파일 이름 대소문자 불일치 (특히 Linux/Mac)
4. 설치되지 않은 패키지
5. TypeScript 설정에서 baseUrl 미설정
6. 파일 확장자 누락 (Node.js에서 필요할 수 있음)

## 빠른 해결법

### 1. 상대 경로 수정
```typescript
// 파일 구조:
// src/pages/index.tsx
// src/components/Button.tsx

// ❌ 잘못된 경로
import Button from '../Button';

// ✅ 올바른 경로
import Button from '../components/Button';
```

### 2. 절대 경로 사용 (tsconfig 설정)
```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"],
      "@pages/*": ["src/pages/*"],
      "@utils/*": ["src/utils/*"]
    }
  }
}
```

```typescript
// 이제 절대 경로 사용 가능
import Button from '@components/Button';
import { getUserData } from '@utils/api';
```

### 3. 패키지 설치
```bash
npm install axios
# 또는
yarn add lodash
# 또는
pnpm add express
```

```typescript
// 설치 후 import
import axios from 'axios';
import { debounce } from 'lodash';
```

### 4. 인덱스 파일 생성
```typescript
// 파일 구조:
// src/utils/
//   index.ts
//   helpers.ts
//   validators.ts

// utils/index.ts
export * from './helpers';
export * from './validators';

// 다른 파일에서
import { validate, help } from '@utils';  // ✅ 인덱스 파일 자동 로드
```

### 5. 파일 확장자 명시
```typescript
// ❌ Node.js에서 실패할 수 있음
import { utils } from './utils';

// ✅ 확장자 명시
import { utils } from './utils.js';  // ES modules
import { utils } from './utils.ts';  // TypeScript
```

### 6. 대소문자 확인 (특히 Linux/Mac)
```typescript
// 파일: src/components/Button.tsx
// ❌ 잘못된 import (Linux에서 실패)
import Button from './button';

// ✅ 올바른 import
import Button from './Button';
```

## 연결된 패턴
- E-BC-02-module-not-found
- E-BC-03-version-conflict

## 연결된 플로우
- 프로젝트 설정 플로우
- 모듈 시스템 구성 플로우

## 재발 방지
1. TypeScript baseUrl과 paths 설정
2. 절대 경로 사용으로 일관성 유지
3. 파일 구조 명확하게 정의
4. IDE의 경로 자동완성 활용
5. 설치된 패키지 목록 정기 확인
6. 모노레포에서는 workspaces 설정
