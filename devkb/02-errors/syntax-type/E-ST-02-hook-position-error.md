---
id: E-ST-02
title: Hook 호출 위치 오류
error_class: Syntax-Type
symptoms:
  - 런타임 에러 발생
  - Hook 상태가 동기화되지 않음
  - 조건부로 Hook이 호출됨
exact_messages:
  - "React Hook \"useState\" is called conditionally"
  - "Hooks can only be called inside the body of a function component"
  - "React Hooks must be called in the exact same order"
tech_tags:
  - React
  - Hooks
  - useState
  - useEffect
linked_patterns: []
linked_flows: []
---

# Hook 호출 위치 오류

## 증상
React Hook을 조건부로 호출하거나 반복문 내에서 호출하면 Hook의 상태 관리가 깨집니다. 렌더링마다 다른 수의 Hook이 호출되어 상태가 뒤바뀝니다.

## 정확한 에러 메시지
```
React Hook "useState" is called conditionally. React Hooks must be called in the exact same order in every render of the component
React Hook "useEffect" is called in function "customFunction" which is neither a React function component nor a custom React Hook function
Hooks can only be called inside the body of a function component or a custom React Hook
```

## 발생 맥락
```typescript
// 잘못된 예 1: 조건부 Hook 호출
function Component({ isEnabled }: { isEnabled: boolean }) {
  if (isEnabled) {
    const [count, setCount] = useState(0);  // ❌ 조건부 호출
  }
  return <div>Count</div>;
}

// 잘못된 예 2: 반복문 내 Hook 호출
function Component() {
  for (let i = 0; i < 3; i++) {
    const [value, setValue] = useState(0);  // ❌ 반복문 내 호출
  }
  return <div>Values</div>;
}

// 잘못된 예 3: 일반 함수에서 Hook 호출
function handleClick() {
  const [state, setState] = useState(0);  // ❌ 일반 함수 내
}

function Component() {
  return <button onClick={handleClick}>Click</button>;
}
```

## 필요한 증거
- Hook 호출 위치의 조건부/반복문 코드
- 런타임 에러 메시지
- 컴포넌트 렌더링 로직

## 의심 원인
1. 조건부로 Hook 호출
2. 반복문 또는 중첩 함수 내에서 Hook 호출
3. Hook을 일반 JavaScript 함수에서 호출
4. Hook이 들어갈 위치가 변함

## 빠른 해결법

### 1. Hook을 최상위 레벨로 이동
```typescript
function Component({ isEnabled }: { isEnabled: boolean }) {
  const [count, setCount] = useState(0);  // ✅ 항상 호출됨

  useEffect(() => {
    if (isEnabled) {
      // 로직 실행
    }
  }, [isEnabled]);

  return <div>Count: {count}</div>;
}
```

### 2. 조건부 로직은 Hook 내부에서 구현
```typescript
function Component({ userId }: { userId: string | null }) {
  const [userData, setUserData] = useState(null);

  useEffect(() => {
    // Hook 내부에서 조건 체크
    if (userId) {
      fetchUser(userId).then(setUserData);
    }
  }, [userId]);

  return <div>{userData?.name}</div>;
}
```

### 3. 커스텀 Hook으로 래핑
```typescript
function useConditionalValue(isEnabled: boolean) {
  const [value, setValue] = useState(0);  // ✅ Hook은 항상 호출됨

  useEffect(() => {
    if (!isEnabled) return;
    // 로직 실행
  }, [isEnabled]);

  return value;
}

function Component({ isEnabled }: { isEnabled: boolean }) {
  const value = useConditionalValue(isEnabled);
  return <div>{value}</div>;
}
```

### 4. 동적 Hook 호출 (커스텀 Hook 배열)
```typescript
function useMultipleValues(count: number) {
  const [values, setValues] = useState<number[]>([]);

  // Hook은 고정적으로 호출되고 내부에서 개수 관리
  useEffect(() => {
    setValues(Array(count).fill(0));
  }, [count]);

  return values;
}
```

## 연결된 패턴
- E-LS-01-infinite-rerender
- E-LS-04-duplicate-side-effect

## 연결된 플로우
- React 컴포넌트 개발 플로우
- Hook 설계 및 구현 플로우

## 재발 방지
1. Hook 호출을 컴포넌트 최상위 레벨에 배치
2. ESLint의 `rules-of-hooks` 규칙 활성화
3. 조건부 로직은 Hook 내부 useEffect에서 처리
4. 복잡한 로직은 커스텀 Hook으로 추상화
5. 반복적인 Hook이 필요하면 배열이나 객체 상태 사용
