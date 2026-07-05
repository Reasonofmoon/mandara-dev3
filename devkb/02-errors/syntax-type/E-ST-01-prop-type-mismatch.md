---
id: E-ST-01
title: Props 타입 불일치
error_class: Syntax-Type
symptoms:
  - TypeScript 컴파일 에러
  - 런타임에 예상 값이 없음
  - 컴포넌트가 예상대로 작동하지 않음
exact_messages:
  - "Type 'string' is not assignable to type 'number'"
  - "Property 'onClick' does not exist on type"
  - "Expected 1 argument, but got 2"
tech_tags:
  - React
  - TypeScript
  - Props
  - Type Safety
linked_patterns: []
linked_flows: []
---

# Props 타입 불일치

## 증상
Props를 컴포넌트에 전달할 때 정의된 타입과 다른 타입의 값을 전달하면 발생합니다. TypeScript 컴파일 단계에서 감지되거나 런타임에 오류가 나타납니다.

## 정확한 에러 메시지
```
Type 'string' is not assignable to type 'number'
Type 'boolean' is not assignable to type 'string | undefined'
Property 'color' does not exist on type 'ButtonProps'
```

## 발생 맥락
```typescript
interface ButtonProps {
  label: string;
  count: number;
  disabled?: boolean;
}

function Button({ label, count, disabled }: ButtonProps) {
  return <button>{label} ({count})</button>;
}

// 잘못된 사용
<Button label="Click" count="5" disabled={0} />
// count는 number가 필요하지만 string "5" 전달
// disabled는 boolean인데 0(number) 전달
```

## 필요한 증거
- TypeScript 에러 메시지
- 컴포넌트의 Props 인터페이스 정의
- Props를 전달하는 호출 코드

## 의심 원인
1. Props 타입 정의와 전달 값의 타입 불일치
2. Props 인터페이스 변경 후 호출 코드 미업데이트
3. 외부 라이브러리 타입과의 불일치
4. optional 필드를 필수로 취급하거나 그 반대

## 빠른 해결법

### 1. Props 타입 확인 및 수정
```typescript
interface ButtonProps {
  label: string;
  count: number;
  disabled?: boolean;
}

function Button({ label, count, disabled }: ButtonProps) {
  return <button>{label} ({count})</button>;
}

// 올바른 사용
<Button label="Click" count={5} disabled={false} />
```

### 2. 타입 변환이 필요한 경우
```typescript
// 문자열을 숫자로 변환
const count = parseInt(countString);
<Button label="Click" count={count} />

// 또는 호출 시 직접 변환
<Button label="Click" count={Number(countString)} />
```

### 3. Union 타입 사용
```typescript
interface ButtonProps {
  label: string;
  count: number | string;  // 둘 다 허용
}

function Button({ label, count }: ButtonProps) {
  const numCount = typeof count === 'string' ? parseInt(count) : count;
  return <button>{label} ({numCount})</button>;
}
```

### 4. 제네릭 Props 사용
```typescript
interface BaseProps<T> {
  value: T;
  onChange: (value: T) => void;
}

function Input<T extends string | number>({ value, onChange }: BaseProps<T>) {
  return <input value={value} onChange={(e) => onChange(e.target.value as T)} />;
}
```

## 연결된 패턴
- E-ST-05-typescript-strict-error
- E-ST-06-prisma-type-error

## 연결된 플로우
- 컴포넌트 개발 플로우
- Props 설계 및 검증 플로우

## 재발 방지
1. TypeScript strict mode 활성화
2. 컴포넌트 Props 인터페이스를 먼저 정의 후 사용
3. IDE의 타입 체크 기능 활용
4. Props 변경 시 모든 호출 코드 검증
5. 유닛 테스트에서 Props 타입 검증 추가
