---
id: E-LS-03
title: 제어/비제어 컴포넌트 전환
error_class: Logic-State
symptoms:
  - 입력값 변경 안 됨
  - 경고: controlled to uncontrolled
  - 폼 입력 동기화 실패
exact_messages:
  - "You provided a 'value' prop to a form field without 'onChange'"
  - "A component is changing a controlled input to be uncontrolled"
  - "onChange handler is missing"
tech_tags:
  - React
  - Forms
  - Controlled Components
  - State Management
linked_patterns: []
linked_flows: []
---

# 제어/비제어 컴포넌트 전환

## 증상
폼 입력 요소가 제어/비제어 상태를 전환하면 React 경고가 발생하고 입력이 작동하지 않습니다.

## 빠른 해결법

### 1. 제어 컴포넌트 (권장)
```typescript
const [email, setEmail] = useState('');

return (
  <input
    value={email}
    onChange={e => setEmail(e.target.value)}
  />
);
```

### 2. 비제어 컴포넌트
```typescript
const emailRef = useRef<HTMLInputElement>(null);

const handleSubmit = () => {
  console.log(emailRef.current?.value);
};

return (
  <>
    <input ref={emailRef} defaultValue="" />
    <button onClick={handleSubmit}>Submit</button>
  </>
);
```

### 3. 항상 일관성 유지
```typescript
// ❌ 잘못된 코드
const [value, setValue] = useState<string | undefined>();
<input value={value} onChange={e => setValue(e.target.value)} />

// ✅ 올바른 코드
const [value, setValue] = useState('');
<input value={value} onChange={e => setValue(e.target.value)} />
```

## 연결된 패턴
- E-LS-01-infinite-rerender

## 재발 방지
1. 항상 초기값 설정
2. value와 onChange 함께 사용
3. undefined/null은 빈 문자열로 변환
