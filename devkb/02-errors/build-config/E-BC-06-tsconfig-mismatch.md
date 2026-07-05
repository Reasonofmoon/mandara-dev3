---
id: E-BC-06
title: tsconfig 불일치
error_class: Build-Config
symptoms:
  - TypeScript 컴파일 오류
  - 빌드 경로 오류
  - 모듈 해석 실패
exact_messages:
  - "Output file would overwrite input file"
  - "Cannot write file because it would overwrite input file"
  - "Cannot find module at path"
  - "error TS6059: File ... is not under 'rootDir'"
tech_tags:
  - TypeScript
  - Configuration
  - Build System
  - Compilation
linked_patterns: []
linked_flows: []
---

# tsconfig 불일치

## 증상
tsconfig.json 설정이 프로젝트 구조와 맞지 않으면 TypeScript 컴파일 오류가 발생합니다. 경로, 모듈 해석, 또는 출력 디렉토리 설정 오류가 원인입니다.

## 정확한 에러 메시지
```
Output file would overwrite input file
Cannot write file because it would overwrite input file
error TS6059: File '/path/file.ts' is not under 'rootDir'
Cannot find module path resolution
Invalid compilerOptions configuration
```

## 발생 맥락
```json
{
  "compilerOptions": {
    "outDir": "./src",        // ❌ 입력과 동일한 디렉토리
    "rootDir": "./dist",      // ❌ 소스가 rootDir 밖에 있음
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"]
    },
    "moduleResolution": "node",
    "target": "es2020",
    "module": "esnext"
  },
  "include": ["src"],
  "exclude": ["node_modules"]
}
```

## 필요한 증거
- tsconfig.json 파일
- 프로젝트 디렉토리 구조
- TypeScript 컴파일 에러 메시지
- 다른 설정 파일 (next.config.js 등)

## 의심 원인
1. outDir과 rootDir 설정 오류
2. include/exclude 경로 불일치
3. baseUrl과 paths 설정 오류
4. module과 moduleResolution 불일치
5. 다중 tsconfig.json 설정 충돌
6. Next.js, Vite 등과 호환성 문제

## 빠른 해결법

### 1. 기본 tsconfig.json 템플릿
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@utils/*": ["src/utils/*"]
    }
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist", "build"]
}
```

### 2. Next.js 프로젝트
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "preserve",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "incremental": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
```

### 3. React + Vite 프로젝트
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vite/client"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 4. 경로 설정 확인
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"],
      "@pages/*": ["src/pages/*"],
      "@utils/*": ["src/utils/*"],
      "@types/*": ["src/types/*"]
    }
  }
}
```

```typescript
// 이제 절대 경로 사용 가능
import Button from '@components/Button';
import { HomePage } from '@pages/home';
import { helper } from '@utils/helpers';
import type { User } from '@types/user';
```

### 5. 다중 tsconfig 설정 (monorepo)
```json
// tsconfig.json (루트)
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@lib/*": ["packages/lib/*"],
      "@cli/*": ["packages/cli/*"]
    }
  }
}
```

```json
// packages/lib/tsconfig.json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "."
  },
  "include": ["src"],
  "exclude": ["node_modules"]
}
```

### 6. 조건부 컴파일
```json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "strict": true
  }
}
```

### 7. 빌드 확인
```bash
# TypeScript 컴파일 확인
tsc --noEmit

# 특정 파일 확인
tsc --noEmit src/index.ts

# 생성된 파일 확인
tsc --listFiles

# 설정 확인
tsc --showConfig
```

## 연결된 패턴
- E-BC-01-env-var-missing
- E-ST-05-typescript-strict-error

## 연결된 플로우
- TypeScript 프로젝트 설정 플로우
- 빌드 시스템 설정 플로우

## 재발 방지
1. 프로젝트 생성 시 정확한 tsconfig 설정
2. outDir은 항상 src 밖에 위치 (dist, build 등)
3. baseUrl과 paths를 명확히 정의
4. 프레임워크별 권장 설정 참고
5. tsconfig.json 변경 후 IDE 재시작
6. 정기적으로 `tsc --noEmit`으로 타입 확인
