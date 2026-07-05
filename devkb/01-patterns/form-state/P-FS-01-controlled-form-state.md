---
id: P-FS-01
title: 제어 폼 상태 패턴
stage: Implement
layer: UI
pattern_family: State
tech_tags: [React, useState, 폼 상태, 단방향 데이터 흐름]
linked_errors: [E-FS-01, E-FS-02, E-FS-03]
linked_flows: [F-FS-01, F-FS-02]
linked_prompts: [PR-FS-01]
---

# 제어 폼 상태 패턴

## 목표
React의 상태를 단일 source of truth로 하여 폼 필드를 관리하고, 예측 가능하고 테스트 가능한 폼 동작을 보장합니다.

## 언제 사용하는가
- 폼 입력값을 실시간으로 검증해야 할 때
- 조건부 필드 표시가 필요할 때
- 폼 상태를 부모 컴포넌트와 동기화해야 할 때
- 초기값 설정 후 동적으로 변경해야 할 때

## 언제 사용하지 않는가
- 매우 복잡한 다단계 폼 (useReducer 또는 폼 라이브러리 사용)
- 대규모 동적 필드 (배열 필드가 많은 경우)

## 핵심 구조

제어 컴포넌트는 React 상태값을 value로 가지며, onChange 핸들러로 업데이트합니다:

```typescript
// form-state를 상위 컴포넌트에서 관리
interface SignUpForm {
  email: string;
  password: string;
  confirmPassword: string;
  agree: boolean;
}

export function SignUpComponent() {
  const [form, setForm] = useState<SignUpForm>({
    email: '',
    password: '',
    confirmPassword: '',
    agree: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.currentTarget;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // 폼 상태는 항상 동기화되어 있음
    console.log('제출할 데이터:', form);

    // 검증 후 API 호출
    if (validateForm(form)) {
      await signUp(form);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        name="email"
        value={form.email}
        onChange={handleChange}
        placeholder="이메일을 입력하세요"
      />
      <input
        type="password"
        name="password"
        value={form.password}
        onChange={handleChange}
        placeholder="비밀번호를 입력하세요"
      />
      <input
        type="password"
        name="confirmPassword"
        value={form.confirmPassword}
        onChange={handleChange}
        placeholder="비밀번호 확인"
      />
      <label>
        <input
          type="checkbox"
          name="agree"
          checked={form.agree}
          onChange={handleChange}
        />
        약관에 동의합니다
      </label>
      <button type="submit">회원가입</button>
    </form>
  );
}
```

## 최소 예제

```typescript
import { useState } from 'react';

export function SimpleForm() {
  const [formData, setFormData] = useState({ name: '', email: '' });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      console.log(formData);
    }}>
      <input name="name" value={formData.name} onChange={handleChange} />
      <input name="email" value={formData.email} onChange={handleChange} />
      <button type="submit">제출</button>
    </form>
  );
}
```

## 고급 사용법 - 초기값 동적 설정

```typescript
interface UserEditFormProps {
  userId: string;
}

export function UserEditForm({ userId }: UserEditFormProps) {
  const [form, setForm] = useState<SignUpForm | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 초기값을 서버에서 로드
    const loadUser = async () => {
      const user = await fetchUser(userId);
      setForm({
        email: user.email,
        password: '',
        confirmPassword: '',
        agree: true,
      });
      setLoading(false);
    };

    loadUser();
  }, [userId]);

  if (loading) return <div>로딩 중...</div>;
  if (!form) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.currentTarget;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      updateUser(userId, form);
    }}>
      <input
        type="email"
        name="email"
        value={form.email}
        onChange={handleChange}
      />
      {/* ... */}
    </form>
  );
}
```

## 안티패턴

### 1. Uncontrolled → Controlled 전환 (경고 발생)

```typescript
// ❌ 나쁜 예제
const [form, setForm] = useState<SignUpForm | undefined>();

return (
  <input
    value={form?.email || ''} // undefined에서 문자열로 변함 - 경고!
    onChange={handleChange}
  />
);

// ✅ 좋은 예제
const [form, setForm] = useState<SignUpForm>({
  email: '', // 항상 문자열로 초기화
});
```

### 2. 과도한 re-render

```typescript
// ❌ 나쁜 예제 - 부모 폼 상태를 개별 state로 분산
const [email, setEmail] = useState('');
const [password, setPassword] = useState('');
const [name, setName] = useState('');
// ... 많은 state가 각각 re-render 유발

// ✅ 좋은 예제 - 단일 form 객체로 관리
const [form, setForm] = useState({ email: '', password: '', name: '' });
```

### 3. onChange에서 직접 state 수정

```typescript
// ❌ 나쁜 예제
const form = { email: '', password: '' };
const handleChange = (e) => {
  form[e.target.name] = e.target.value; // 직접 변경 - 반응성 없음!
  setForm(form);
};

// ✅ 좋은 예제
const handleChange = (e) => {
  setForm(prev => ({
    ...prev,
    [e.target.name]: e.target.value,
  }));
};
```

## 연결된 오류

- **E-FS-01**: Warning: You provided a `checked` prop to a form field without an `onChange`
- **E-FS-02**: Warning: A component is changing a controlled input of type text to be uncontrolled
- **E-FS-03**: Input value prop is undefined, leading to uncontrolled component warning

## 연결된 플로우

- **F-FS-01**: 폼 제출 및 검증 플로우
- **F-FS-02**: 조건부 필드 표시 플로우

## 참고 자료

- React 공식 문서: https://react.dev/reference/react-dom/components/input#controlling-an-input-with-a-state-variable
- React Hook Form과의 비교: https://react-hook-form.com/
