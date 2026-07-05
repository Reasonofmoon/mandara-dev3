---
id: E-ST-08
title: 제네릭 제약 조건 오류
error_class: Syntax-Type
symptoms:
  - 제네릭 타입 인수 오류
  - 제약 조건 위반
  - 타입 추론 실패
exact_messages:
  - "Type 'string' does not satisfy the constraint 'number'"
  - "Type 'MyClass' does not satisfy the constraint 'extends { id: number }'"
  - "Generic type 'T' could not be inferred from usage"
tech_tags:
  - TypeScript
  - Generics
  - Type Constraints
  - Type Safety
linked_patterns: []
linked_flows: []
---

# 제네릭 제약 조건 오류

## 증상
제네릭 타입에 정의된 제약 조건을 만족하지 않는 타입을 전달하면 에러가 발생합니다. 제약 조건이 너무 좁거나 타입 추론이 실패할 때 발생합니다.

## 정확한 에러 메시지
```
Type 'string' does not satisfy the constraint 'number'
Type 'MyClass' does not satisfy the constraint 'extends { id: number }'
Generic type 'T' could not be inferred from usage
Type parameter 'T' has no matching type argument
Argument of type 'unknown' is not assignable to parameter of type 'T extends string'
```

## 발생 맥락
```typescript
// 잘못된 예 1: 제약 조건 위반
function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}

getLength("hello");  // ✅ 문자열은 length 속성 있음
getLength(123);      // ❌ 숫자는 length 속성 없음
getLength({ value: 10 });  // ❌ { value } 객체는 length 없음

// 잘못된 예 2: 제약 조건 부족
function findById<T>(items: T[], id: number): T | undefined {
  return items.find(item => item.id === id);  // ❌ T가 id 속성을 갖는다는 보장 없음
}

// 잘못된 예 3: 타입 추론 실패
function create<T>(constructor: new () => T): T {
  return new constructor();
}

const instance = create();  // ❌ T를 추론할 수 없음

// 잘못된 예 4: extends 체이닝 오류
function process<T extends string | number>(value: T): void {
  const result = value.toFixed(2);  // ❌ string에는 toFixed 없음
}
```

## 필요한 증거
- 제네릭 함수/클래스 정의
- 타입 제약 조건
- 실제 전달된 타입
- TypeScript 에러 메시지

## 의심 원인
1. 제약 조건이 전달된 타입을 충족하지 않음
2. 제약 조건이 너무 좁게 정의됨
3. 타입 추론에 필요한 정보 부족
4. extends 키워드 사용 오류
5. 제약 조건에서 다른 제네릭 참조 오류

## 빠른 해결법

### 1. 제약 조건을 명확히 정의
```typescript
// ❌ 잘못된 코드
function getLength<T>(item: T): number {
  return item.length;  // T에 length 없을 수 있음
}

// ✅ 올바른 코드
function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}
```

### 2. keyof를 사용한 제약 조건
```typescript
// ❌ 잘못된 코드
function getValue<T, K>(obj: T, key: K): any {
  return obj[key];  // obj에 key가 없을 수 있음
}

// ✅ 올바른 코드
function getValue<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const user = { name: 'John', age: 30 };
const name = getValue(user, 'name');  // ✅ 타입: string
const age = getValue(user, 'age');    // ✅ 타입: number
```

### 3. 조건부 타입으로 복합 제약 조건
```typescript
// ✅ 복합 제약 조건
function process<T extends string | number>(value: T): string {
  if (typeof value === 'string') {
    return value.toUpperCase();
  } else {
    return value.toFixed(2);
  }
}
```

### 4. 기본 제약 조건 제공
```typescript
// ❌ 타입 추론 실패
function create<T>(constructor: new () => T): T {
  return new constructor();
}

// ✅ 명시적 타입 인수 필요
const instance = create(MyClass);

// 또는 기본값 제공
function create<T = MyClass>(constructor?: new () => T): T {
  return new (constructor || MyClass)() as T;
}
```

### 5. 제네릭 제약 조건의 교집합
```typescript
// ✅ 여러 제약 조건 조합
function merge<T extends object, U extends object>(obj1: T, obj2: U): T & U {
  return { ...obj1, ...obj2 } as T & U;
}

const result = merge({ id: 1 }, { name: 'John' });
// result 타입: { id: number } & { name: string }
```

### 6. 제약 조건과 기본값
```typescript
// ✅ 제약 조건과 함께 기본값
function createArray<T extends string | number = string>(
  defaultValue: T,
  length: number
): T[] {
  return Array(length).fill(defaultValue);
}

createArray('hello', 3);  // 타입: string[]
createArray(42, 3);       // 타입: number[]
```

### 7. 재귀 제약 조건
```typescript
// ✅ 재귀 구조 처리
type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

function stringify<T extends JsonValue>(value: T): string {
  return JSON.stringify(value);
}

stringify({ name: 'John', age: 30, hobbies: ['reading', 'gaming'] });
// ✅ 유효함
```

## 연결된 패턴
- E-ST-05-typescript-strict-error
- E-ST-06-prisma-type-error

## 연결된 플로우
- TypeScript 고급 타입 설계 플로우
- 제네릭 라이브러리 개발 플로우

## 재발 방지
1. 제약 조건을 처음부터 명확히 정의
2. keyof와 extends를 활용한 정확한 제약 조건
3. 타입 추론이 필요한 경우 명시적 타입 인수 제공
4. 제약 조건이 너무 좁으면 Union 타입 고려
5. 복합 제약 조건은 조건부 타입 활용
6. 테스트 케이스로 제네릭 제약 조건 검증
