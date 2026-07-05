---
id: E-RT-12
title: 파일을 찾을 수 없음
error_class: Runtime
symptoms:
  - 파일 로드 실패
  - ENOENT 에러
  - 리소스 누락
exact_messages:
  - "ENOENT: no such file or directory"
  - "Error: ENOENT: open '/path/to/file'"
  - "Cannot find module './file.js'"
tech_tags:
  - File System
  - Path Resolution
  - Error Handling
  - File I/O
linked_patterns: []
linked_flows: []
---

# 파일을 찾을 수 없음

## 증상
애플리케이션이 필요한 파일을 찾을 수 없으면 발생합니다. 절대/상대 경로 오류, 파일 이동, 또는 배포 구조 차이가 원인입니다.

## 정확한 에러 메시지
```
ENOENT: no such file or directory, open '/path/to/file.json'
Error: ENOENT: open './config.json'
Cannot find module './config'
ENOENT: no such file or directory, stat '/uploads/file.jpg'
```

## 발생 맥락
```typescript
// 잘못된 예 1: 상대 경로 오류
const config = fs.readFileSync('./config.json');  // ❌ 실행 위치에 따라 다름

// 잘못된 예 2: 파일이 존재하지 않음
const content = fs.readFileSync('/tmp/data.csv');  // ❌ 파일 없음

// 잘못된 예 3: 배포 후 경로 오류
const publicFile = fs.readFileSync('../public/style.css');  // ❌ 배포 구조 다름

// 잘못된 예 4: 확장자 오류
import config from './config';  // ❌ config.json이 있어도 .js 찾음
```

## 필요한 증거
- ENOENT 에러 메시지와 경로
- 실제 파일 위치
- 실행 디렉토리
- 배포 구조

## 의심 원인
1. 파일이 실제로 존재하지 않음
2. 상대 경로가 잘못됨
3. 현재 작업 디렉토리(cwd) 다름
4. 배포 시 파일 복사 누락
5. 파일 권한 문제
6. 심볼릭 링크 끊김
7. 대소문자 불일치 (Linux)

## 빠른 해결법

### 1. 절대 경로 사용
```typescript
import path from 'path';
import { fileURLToPath } from 'url';

// CommonJS
const __filename = __filename;
const __dirname = __dirname;

const configPath = path.join(__dirname, 'config.json');
const config = fs.readFileSync(configPath, 'utf-8');

// ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const configPath = path.join(__dirname, 'config.json');
```

### 2. 파일 존재 여부 확인
```typescript
import fs from 'fs';
import path from 'path';

// 파일 존재 확인
if (fs.existsSync(filePath)) {
  const content = fs.readFileSync(filePath);
} else {
  console.error(`File not found: ${filePath}`);
}

// 또는 stat 사용
fs.stat(filePath, (error, stats) => {
  if (error) {
    console.error('File not found:', error.message);
  } else {
    console.log('File found');
  }
});

// Promise 기반
async function readFile(filePath: string) {
  try {
    const stats = await fs.promises.stat(filePath);
    if (stats.isFile()) {
      return fs.promises.readFile(filePath, 'utf-8');
    }
  } catch (error) {
    console.error(`File not found: ${filePath}`);
    throw error;
  }
}
```

### 3. 기본값 제공
```typescript
function loadConfig(configPath: string) {
  const defaultConfig = {
    port: 3000,
    host: 'localhost'
  };

  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.warn(`Config not found, using defaults: ${configPath}`);
      return defaultConfig;
    }
    throw error;
  }
}
```

### 4. 환경별 경로 설정
```typescript
// config.ts
function getConfigPath() {
  const env = process.env.NODE_ENV || 'development';

  const paths = {
    development: './config/dev.json',
    production: '/etc/app/config/prod.json',
    test: './config/test.json'
  };

  return paths[env] || paths.development;
}

const configPath = path.resolve(getConfigPath());
const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
```

### 5. 여러 경로 시도
```typescript
function findFile(filename: string, searchPaths: string[]) {
  for (const searchPath of searchPaths) {
    const filePath = path.join(searchPath, filename);
    if (fs.existsSync(filePath)) {
      return filePath;
    }
  }
  throw new Error(`File not found: ${filename}`);
}

const searchPaths = [
  process.cwd(),
  path.join(process.cwd(), 'config'),
  '/etc/app',
  path.dirname(process.execPath)
];

const configPath = findFile('config.json', searchPaths);
```

### 6. Glob으로 파일 찾기
```typescript
import glob from 'glob';

// 패턴으로 파일 찾기
glob('src/**/*.json', (err, files) => {
  if (err) throw err;
  console.log('Found files:', files);
});

// Promise 기반
import { glob } from 'glob';

const files = await glob('src/**/*.json');
console.log('Found files:', files);
```

### 7. Express에서 정적 파일
```typescript
import express from 'express';
import path from 'path';

const app = express();

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));

// 또는 명시적 경로
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// 404 처리
app.use((req, res) => {
  res.status(404).json({ error: 'File not found' });
});
```

### 8. Next.js 정적 파일
```typescript
// public 디렉토리에 파일 배치
// 예: public/images/logo.png

// JSX에서 사용
<Image src="/images/logo.png" alt="Logo" />

// API에서 사용
import path from 'path';

export default function handler(req, res) {
  const filePath = path.join(process.cwd(), 'public', 'data.json');

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const data = fs.readFileSync(filePath, 'utf-8');
  res.json(JSON.parse(data));
}
```

### 9. Docker에서 파일 경로
```dockerfile
FROM node:18-alpine

WORKDIR /app

# 모든 파일 복사
COPY . .

# 특정 파일만 복사
COPY config/ ./config/
COPY package*.json ./

RUN npm install

CMD ["node", "dist/index.js"]
```

```typescript
// 컨테이너 내 경로 (생성 후)
const configPath = '/app/config/app.json';
const config = fs.readFileSync(configPath, 'utf-8');
```

### 10. 파일 감시 및 재로드
```typescript
import fs from 'fs';

let config = loadConfig('./config.json');

// 파일 변경 감시
fs.watch('./config.json', (eventType, filename) => {
  console.log(`Config changed: ${filename}`);
  try {
    config = loadConfig('./config.json');
    console.log('Config reloaded');
  } catch (error) {
    console.error('Failed to reload config:', error);
  }
});

function getConfig() {
  return config;
}
```

## 연결된 패턴
- E-ST-04-import-path-error
- E-BC-02-module-not-found

## 연결된 플로우
- 파일 시스템 관리 플로우
- 배포 구조 설정 플로우

## 재발 방지
1. 항상 절대 경로 사용 (path.join + __dirname)
2. 파일 존재 여부 확인 후 읽기
3. 기본값 제공으로 우아한 실패
4. 배포 시 필요한 모든 파일 포함
5. 파일 경로 문서화
6. 환경별 경로 분리
7. CI/CD에서 파일 존재 확인
