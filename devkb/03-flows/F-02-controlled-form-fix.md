---
id: F-02
title: 폼 상태 오류 해결
pattern_id: P-02
error_ids: [E-04, E-05, E-06]
tech_scope: React, 폼 상태 관리, 유효성 검사
---

# 폼 상태 오류 해결

제어된(controlled) 또는 비제어(uncontrolled) 폼 입력 상태 불일치로 인한 경고 및 버그를 해결합니다.

## 1단계: 증상 고정

콘솔 경고 확인:
- "You provided a `value` prop to a form field without an `onChange` handler"
- "A component is changing an uncontrolled input to be controlled"
- 입력 필드에 값을 입력할 수 없음
- 폼 값이 업데이트되지 않음

## 2단계: 재현

```javascript
// ❌ 문제: value는 있지만 onChange 없음
function Form() {
  const [name, setName] = useState('');

  return (
    <input
      type="text"
      value={name}
      // onChange 핸들러 누락
    />
  );
}

// ❌ 문제: 제어/비제어 혼합
function Form() {
  const inputRef = useRef();

  return (
    <input
      ref={inputRef}
      defaultValue="initial"
      value={inputRef.current?.value} // 위험한 패턴
    />
  );
}
```

## 3단계: 범위 축소

폼 상태 문제의 유형:

1. **제어 input 누락**: value는 있지만 onChange 없음
2. **제어/비제어 혼합**: defaultValue와 value를 동시에 사용
3. **상태 초기화 오류**: 초기값 설정 문제
4. **다중 입력 동기화**: 여러 입력 필드 상태 비동기화

## 4단계: 증거 수집

```javascript
// DevTools Console
document.querySelectorAll('input').forEach(input => {
  console.log({
    type: input.type,
    hasValue: 'value' in input.attributes,
    hasDefaultValue: 'defaultValue' in input.attributes,
    value: input.value,
    defaultValue: input.defaultValue
  });
});
```

React DevTools에서:
- 컴포넌트 state 값 확인
- 부모 컴포넌트에서 전달하는 prop 확인
- 리렌더링 트리거 원인 파악

## 5단계: 원인 후보 정렬

| 원인 | 확률 | 영향도 |
|------|------|--------|
| onChange 핸들러 누락 | 매우높음 | 높음 |
| defaultValue/value 혼합 | 높음 | 높음 |
| 상태 초기화 로직 오류 | 중간 | 중간 |
| 부모 컴포넌트 state | 중간 | 높음 |

## 6단계: 수정안 선택

### 수정안 1: 제어 폼 입력 (권장)

```javascript
// ✅ 올바른 제어 입력
function Form() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <form>
      <input
        name="name"
        value={formData.name}
        onChange={handleChange}
        placeholder="이름"
      />
      <input
        name="email"
        type="email"
        value={formData.email}
        onChange={handleChange}
        placeholder="이메일"
      />
      <textarea
        name="message"
        value={formData.message}
        onChange={handleChange}
        placeholder="메시지"
      />
    </form>
  );
}
```

### 수정안 2: 체크박스 및 라디오 버튼

```javascript
function FormWithCheckbox() {
  const [formData, setFormData] = useState({
    agree: false,
    role: 'user'
  });

  const handleCheckboxChange = (e) => {
    const { name, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  const handleRadioChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <>
      <label>
        <input
          type="checkbox"
          name="agree"
          checked={formData.agree}
          onChange={handleCheckboxChange}
        />
        약관 동의
      </label>

      <fieldset>
        <legend>역할 선택</legend>
        <label>
          <input
            type="radio"
            name="role"
            value="user"
            checked={formData.role === 'user'}
            onChange={handleRadioChange}
          />
          사용자
        </label>
        <label>
          <input
            type="radio"
            name="role"
            value="admin"
            checked={formData.role === 'admin'}
            onChange={handleRadioChange}
          />
          관리자
        </label>
      </fieldset>
    </>
  );
}
```

### 수정안 3: Select 및 Multiple Select

```javascript
function FormWithSelect() {
  const [formData, setFormData] = useState({
    country: 'kr',
    tags: ['javascript']
  });

  const handleSelectChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleMultiSelectChange = (e) => {
    const selectedOptions = Array.from(e.target.selectedOptions, opt => opt.value);
    setFormData(prev => ({
      ...prev,
      tags: selectedOptions
    }));
  };

  return (
    <>
      <select
        name="country"
        value={formData.country}
        onChange={handleSelectChange}
      >
        <option value="kr">한국</option>
        <option value="us">미국</option>
        <option value="jp">일본</option>
      </select>

      <select
        name="tags"
        value={formData.tags}
        onChange={handleMultiSelectChange}
        multiple
      >
        <option value="javascript">JavaScript</option>
        <option value="python">Python</option>
        <option value="rust">Rust</option>
      </select>
    </>
  );
}
```

### 수정안 4: 폼 라이브러리 사용

```javascript
import { useForm } from 'react-hook-form';

function FormWithLibrary() {
  const { register, handleSubmit, watch } = useForm({
    defaultValues: {
      name: '',
      email: '',
      message: ''
    }
  });

  const onSubmit = (data) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} placeholder="이름" />
      <input {...register('email')} type="email" placeholder="이메일" />
      <textarea {...register('message')} placeholder="메시지" />
      <button type="submit">제출</button>
    </form>
  );
}
```

## 7단계: 검증

```javascript
// 폼 동작 테스트
function FormTest() {
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({ name: '' });

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        name="name"
        value={formData.name}
        onChange={handleChange}
      />
      <button type="submit">제출</button>
      {submitted && <p>이름: {formData.name}</p>}
    </form>
  );
}
```

## 8단계: 재발 방지

1. **TypeScript로 안정성 확보**

```typescript
interface FormData {
  name: string;
  email: string;
  message: string;
}

function Form() {
  const [data, setData] = useState<FormData>({
    name: '',
    email: '',
    message: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.currentTarget;
    setData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // ...
}
```

2. **유효성 검사 추가**

```javascript
const validateEmail = (email) => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
};

const handleChange = (e) => {
  const { name, value } = e.target;

  if (name === 'email' && !validateEmail(value)) {
    console.warn('Invalid email format');
  }

  setFormData(prev => ({
    ...prev,
    [name]: value
  }));
};
```

## 연결된 프롬프트 블록

- **PB-CL-03-form-structure**: 폼 구조 설계
- **PB-RP-02-form-testing**: 폼 동작 재현
- **PB-DG-03-state-inspection**: 상태 값 검사
- **PB-PA-03-form-validation**: 폼 유효성 검사 구현
- **PB-VF-02-form-tests**: 폼 기능 검증
