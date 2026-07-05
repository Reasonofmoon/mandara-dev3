---
id: P-FS-04
title: 폼 검증 파이프라인 패턴
stage: Implement
layer: UI
pattern_family: Validation
tech_tags: [Zod, React Hook Form, 클라이언트 검증, 서버 검증]
linked_errors: [E-FS-09, E-FS-10, E-FS-11]
linked_flows: [F-FS-06, F-FS-07]
linked_prompts: [PR-FS-04]
---

# 폼 검증 파이프라인 패턴

## 목표
Zod 스키마로 클라이언트와 서버 검증을 통합하고, React Hook Form으로 효율적인 폼 관리를 구현합니다.

## 언제 사용하는가
- 복잡한 폼 검증 규칙이 필요할 때
- 클라이언트와 서버 검증을 동기화해야 할 때
- 비동기 검증 (중복 확인 등)이 필요할 때
- 타입 안전한 폼 처리가 필요할 때

## 언제 사용하지 않는가
- 매우 간단한 폼 (필수 입력만)
- Zod 의존성을 추가할 수 없는 경우

## 핵심 구조

Zod 스키마 정의 및 React Hook Form 통합:

```typescript
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

// 클라이언트와 서버에서 공유할 Zod 스키마
const SignUpSchema = z.object({
  email: z
    .string()
    .email('유효한 이메일을 입력하세요')
    .refine(
      async email => !(await checkEmailExists(email)),
      '이미 등록된 이메일입니다'
    ),
  password: z
    .string()
    .min(8, '비밀번호는 8자 이상이어야 합니다')
    .regex(/[A-Z]/, '대문자를 포함해야 합니다')
    .regex(/[0-9]/, '숫자를 포함해야 합니다'),
  confirmPassword: z.string(),
  agreeTerms: z.boolean().refine(v => v === true, '약관에 동의해야 합니다'),
}).refine(
  data => data.password === data.confirmPassword,
  {
    message: '비밀번호가 일치하지 않습니다',
    path: ['confirmPassword'],
  }
);

type SignUpFormData = z.infer<typeof SignUpSchema>;

export function SignUpForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignUpFormData>({
    resolver: zodResolver(SignUpSchema),
    mode: 'onBlur', // blur 시점에 검증
  });

  const onSubmit = async (data: SignUpFormData) => {
    try {
      // 서버도 같은 스키마로 검증
      const response = await signUp(data);
      // 성공 처리
    } catch (error) {
      // 오류 처리
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label>이메일</label>
        <input
          {...register('email')}
          type="email"
          placeholder="your@email.com"
        />
        {errors.email && (
          <span className="error">{errors.email.message}</span>
        )}
      </div>

      <div>
        <label>비밀번호</label>
        <input
          {...register('password')}
          type="password"
          placeholder="8자 이상"
        />
        {errors.password && (
          <span className="error">{errors.password.message}</span>
        )}
      </div>

      <div>
        <label>비밀번호 확인</label>
        <input
          {...register('confirmPassword')}
          type="password"
        />
        {errors.confirmPassword && (
          <span className="error">{errors.confirmPassword.message}</span>
        )}
      </div>

      <div>
        <label>
          <input {...register('agreeTerms')} type="checkbox" />
          약관에 동의합니다
        </label>
        {errors.agreeTerms && (
          <span className="error">{errors.agreeTerms.message}</span>
        )}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? '처리 중...' : '회원가입'}
      </button>
    </form>
  );
}
```

## 최소 예제

```typescript
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormData = z.infer<typeof schema>;

export function SimpleForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(data => console.log(data))}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}

      <input {...register('password')} type="password" />
      {errors.password && <span>{errors.password.message}</span>}

      <button type="submit">제출</button>
    </form>
  );
}
```

## 고급 사용법 - 비동기 검증

```typescript
// 서버에서 중복 확인
async function checkEmailExists(email: string): Promise<boolean> {
  const response = await fetch(`/api/check-email?email=${email}`);
  const data = await response.json();
  return data.exists;
}

const UserSchema = z.object({
  email: z
    .string()
    .email()
    .refine(
      async email => {
        const exists = await checkEmailExists(email);
        return !exists;
      },
      '이미 등록된 이메일입니다'
    ),
  username: z
    .string()
    .min(3)
    .refine(
      async username => {
        const exists = await checkUsernameExists(username);
        return !exists;
      },
      '이미 사용 중인 사용자명입니다'
    ),
});

export function UserForm() {
  const form = useForm<z.infer<typeof UserSchema>>({
    resolver: zodResolver(UserSchema),
    mode: 'onBlur', // 비동기 검증은 blur 시점에 수행
  });

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* ... */}
    </form>
  );
}
```

## 서버 측 검증 통합

```typescript
// NestJS 컨트롤러
import { Body, Post, Controller } from '@nestjs/common';
import { SignUpSchema } from '@shared/schemas';

@Controller('auth')
export class AuthController {
  @Post('signup')
  async signup(@Body() data: unknown) {
    // 클라이언트와 동일한 스키마로 검증
    const validatedData = SignUpSchema.parse(data);

    // 추가 서버 검증 (DB 쿼리 등)
    const existingUser = await this.userService.findByEmail(
      validatedData.email
    );
    if (existingUser) {
      throw new BadRequestException('이미 등록된 이메일입니다');
    }

    return this.authService.signup(validatedData);
  }
}
```

## 동적 필드 검증

```typescript
const AddressSchema = z.object({
  country: z.enum(['US', 'CA', 'KR']),
  zipCode: z.string(),
}).refine(
  data => {
    // 국가별 우편번호 형식 검증
    if (data.country === 'US') {
      return /^\d{5}(-\d{4})?$/.test(data.zipCode);
    }
    if (data.country === 'KR') {
      return /^\d{5}$/.test(data.zipCode);
    }
    return true;
  },
  {
    message: '유효하지 않은 우편번호입니다',
    path: ['zipCode'],
  }
);
```

## 안티패턴

### 1. 검증 로직을 폼에만 구현

```typescript
// ❌ 나쁜 예제 - 서버에서 검증하지 않음
export function Form() {
  const { register, handleSubmit } = useForm();

  const onSubmit = async (data) => {
    // 클라이언트 검증만 통과하면 바로 제출
    await submitForm(data); // 서버에서 검증 없음!
  };
}

// ✅ 좋은 예제 - 서버에서도 동일하게 검증
const schema = z.object({
  email: z.string().email(),
});

export function Form() {
  const { register, handleSubmit } = useForm({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data) => {
    const response = await submitForm(data);
    // 서버에서도 schema.parse(data) 실행
  };
}
```

### 2. 비동기 검증 성능 문제

```typescript
// ❌ 나쁜 예제 - 매 입력마다 API 호출
const schema = z.object({
  email: z.string().email().refine(
    async email => !(await checkEmailExists(email)), // 매 onChange마다 호출!
  ),
});

export function Form() {
  const form = useForm({ resolver: zodResolver(schema) }); // mode: 'onChange'
}

// ✅ 좋은 예제 - blur 시점에만 검증
export function Form() {
  const form = useForm({
    resolver: zodResolver(schema),
    mode: 'onBlur', // blur 시점에만 실행
  });
}
```

### 3. 중첩 객체 검증 누락

```typescript
// ❌ 나쁜 예제
const schema = z.object({
  email: z.string().email(),
  profile: z.object({}), // 검증 규칙 없음!
});

// ✅ 좋은 예제
const schema = z.object({
  email: z.string().email(),
  profile: z.object({
    firstName: z.string().min(1),
    lastName: z.string().min(1),
    bio: z.string().max(500).optional(),
  }),
});
```

## 연결된 오류

- **E-FS-09**: 클라이언트 검증은 통과했으나 서버 검증 실패
- **E-FS-10**: Zod 스키마와 React Hook Form 타입 불일치
- **E-FS-11**: 비동기 검증 완료 전 폼 제출

## 연결된 플로우

- **F-FS-06**: 이메일 중복 확인 및 등록 플로우
- **F-FS-07**: 주소 유효성 검증 플로우

## 참고 자료

- Zod 공식 문서: https://zod.dev/
- React Hook Form + Zod: https://react-hook-form.com/form-builder
