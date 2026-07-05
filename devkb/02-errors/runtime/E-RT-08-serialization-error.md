---
id: E-RT-08
title: 직렬화 오류
error_class: Runtime
symptoms:
  - JSON 변환 실패
  - 순환 참조 감지
  - 직렬화 불가능한 값
exact_messages:
  - "JSON.stringify circular object"
  - "Object has a circular reference and cannot be serialized"
  - "Cannot serialize value: [object Object]"
tech_tags:
  - Serialization
  - JSON
  - Data Structure
  - Debugging
linked_patterns: []
linked_flows: []
---

# 직렬화 오류

## 증상
객체가 JSON으로 변환될 수 없거나 순환 참조로 인해 스택 오버플로우가 발생합니다. 네트워크 전송 또는 저장소 저장 시 실패합니다.

## 정확한 에러 메시지
```
JSON.stringify circular object
Object has a circular reference and cannot be serialized
Cannot serialize value: [object Object]
RangeError: Maximum call stack size exceeded (순환 참조)
```

## 발생 맥락
```typescript
// 잘못된 예 1: 순환 참조
const user = { id: 1, name: 'John' };
user.self = user;  // 순환 참조
JSON.stringify(user);  // ❌ 에러

// 잘못된 예 2: DOM 요소
const obj = { element: document.getElementById('root') };
JSON.stringify(obj);  // ❌ DOM은 직렬화 불가

// 잘못된 예 3: 함수
const obj = {
  value: 42,
  handler: () => console.log('test')
};
JSON.stringify(obj);  // ❌ 함수는 무시됨

// 잘못된 예 4: undefined 값
const obj = { a: 1, b: undefined };
JSON.stringify(obj);  // { "a": 1 } - b는 생략됨
```

## 필요한 증거
- 직렬화 에러 메시지
- 객체 구조
- 순환 참조 위치
- 변환하려는 데이터

## 의심 원인
1. 객체에 순환 참조 있음
2. DOM 요소, 함수 등 직렬화 불가능한 타입
3. Symbol, Map, Set 등 특수 타입
4. undefined, Infinity 등의 값
5. 깊게 중첩된 객체 구조

## 빠른 해결법

### 1. 순환 참조 제거
```typescript
// ❌ 잘못된 코드
const user = { id: 1 };
user.self = user;

// ✅ 올바른 코드
const user = { id: 1, name: 'John' };
delete user.self;

// 또는 replacer 함수 사용
function stringifyWithoutCircular(obj: any) {
  const seen = new WeakSet();

  return JSON.stringify(obj, (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (seen.has(value)) {
        return '[Circular Reference]';
      }
      seen.add(value);
    }
    return value;
  });
}

const json = stringifyWithoutCircular(user);
```

### 2. Replacer 함수 사용
```typescript
function customStringify(obj: any) {
  return JSON.stringify(obj, (key, value) => {
    // 함수 제외
    if (typeof value === 'function') {
      return '[Function]';
    }

    // DOM 요소 제외
    if (value instanceof HTMLElement) {
      return '[DOM Element]';
    }

    // undefined 대신 null
    if (value === undefined) {
      return null;
    }

    // Infinity, -Infinity 처리
    if (!Number.isFinite(value)) {
      return null;
    }

    return value;
  });
}

const obj = {
  name: 'John',
  handler: () => {},
  element: document.body,
  value: Infinity
};

console.log(customStringify(obj));
// {"name":"John","handler":"[Function]","element":"[DOM Element]","value":null}
```

### 3. 직렬화 가능한 객체로 변환
```typescript
// ❌ 직렬화 불가능
const data = {
  id: 1,
  created: new Date(),
  active: new Set([1, 2, 3]),
  metadata: new Map([['key', 'value']])
};

// ✅ 직렬화 가능
const serializable = {
  id: data.id,
  created: data.created.toISOString(),
  active: Array.from(data.active),
  metadata: Object.fromEntries(data.metadata)
};

JSON.stringify(serializable);
```

### 4. toJSON 메서드
```typescript
class User {
  id: number;
  name: string;
  password: string;  // 민감한 정보

  constructor(id: number, name: string, password: string) {
    this.id = id;
    this.name = name;
    this.password = password;
  }

  // JSON 직렬화 시 호출
  toJSON() {
    return {
      id: this.id,
      name: this.name
      // password는 제외
    };
  }
}

const user = new User(1, 'John', 'secret');
console.log(JSON.stringify(user));
// {"id":1,"name":"John"}
```

### 5. 깊은 복사로 순환 참조 제거
```typescript
function deepCloneWithoutCircular(obj: any) {
  const seen = new WeakMap();

  function clone(value: any): any {
    if (value === null || typeof value !== 'object') {
      return value;
    }

    if (seen.has(value)) {
      return null;  // 순환 참조 제거
    }

    if (value instanceof Date) {
      return new Date(value.getTime());
    }

    if (Array.isArray(value)) {
      seen.set(value, true);
      return value.map(item => clone(item));
    }

    const cloned: any = {};
    seen.set(value, true);

    for (const key in value) {
      if (value.hasOwnProperty(key)) {
        cloned[key] = clone(value[key]);
      }
    }

    return cloned;
  }

  return clone(obj);
}
```

### 6. 특수 타입 처리
```typescript
class CustomSerializer {
  static stringify(obj: any, pretty = false) {
    const json = JSON.stringify(obj, (key, value) => {
      // Date
      if (value instanceof Date) {
        return value.toISOString();
      }

      // Set
      if (value instanceof Set) {
        return Array.from(value);
      }

      // Map
      if (value instanceof Map) {
        return Object.fromEntries(value);
      }

      // BigInt
      if (typeof value === 'bigint') {
        return value.toString();
      }

      // Symbol
      if (typeof value === 'symbol') {
        return value.toString();
      }

      // 함수
      if (typeof value === 'function') {
        return undefined;
      }

      return value;
    }, pretty ? 2 : 0);

    return json;
  }

  static parse(json: string) {
    return JSON.parse(json, (key, value) => {
      // ISO String을 Date로 변환
      if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
        return new Date(value);
      }
      return value;
    });
  }
}

const obj = {
  date: new Date(),
  bigint: BigInt(999),
  nested: { set: new Set([1, 2, 3]) }
};

const json = CustomSerializer.stringify(obj, true);
console.log(json);
```

### 7. 라이브러리 사용
```typescript
// flatted: 순환 참조 처리
import { stringify, parse } from 'flatted';

const circular = { a: 1 };
circular.self = circular;

const json = stringify(circular);
const obj = parse(json);

// superjson: 특수 타입 지원
import superjson from 'superjson';

const data = {
  date: new Date(),
  map: new Map([['key', 'value']]),
  bigint: BigInt(999)
};

const json = superjson.stringify(data);
const parsed = superjson.parse(json);
```

## 연결된 패턴
- E-RT-01-cannot-read-undefined
- E-BC-04-nextjs-config-error

## 연결된 플로우
- 데이터 직렬화 플로우
- API 통신 플로우

## 재발 방지
1. 직렬화 전에 객체 구조 검증
2. toJSON 메서드로 직렬화 제어
3. replacer 함수로 필터링
4. 순환 참조 감지 로직 추가
5. TypeScript로 타입 안전성 강화
6. 직렬화 라이브러리 활용 (flatted, superjson)
7. 테스트에서 직렬화 테스트 포함
