---
id: P-FS-05
title: 다단계 폼 위저드 패턴
stage: Implement
layer: UI
pattern_family: State
tech_tags: [React, 단계별 관리, 폼 상태, 진행 추적]
linked_errors: [E-FS-12, E-FS-13]
linked_flows: [F-FS-08, F-FS-09]
linked_prompts: [PR-FS-05]
---

# 다단계 폼 위저드 패턴

## 목표
여러 단계의 폼을 관리하면서 각 단계의 검증을 수행하고, 사용자가 이전/다음으로 쉽게 네비게이션할 수 있도록 합니다.

## 언제 사용하는가
- 긴 폼을 여러 단계로 나누어야 할 때 (회원가입, 결제 프로세스)
- 단계 간 의존성이 있을 때
- 각 단계별로 다른 검증 규칙이 필요할 때
- 사용자가 이전 단계로 돌아갈 수 있어야 할 때

## 언제 사용하지 않는가
- 단순한 선형 프로세스
- 단계 간 데이터 공유가 없는 경우

## 핵심 구조

```typescript
import { useState } from 'react';
import { z } from 'zod';

// 각 단계의 스키마 정의
const step1Schema = z.object({
  firstName: z.string().min(1, '이름은 필수입니다'),
  lastName: z.string().min(1, '성은 필수입니다'),
  email: z.string().email('유효한 이메일을 입력하세요'),
});

const step2Schema = z.object({
  phone: z.string().regex(/^\d{10,}$/, '유효한 전화번호를 입력하세요'),
  country: z.string().min(1, '국가를 선택하세요'),
  address: z.string().min(5, '주소를 입력하세요'),
});

const step3Schema = z.object({
  cardNumber: z.string().regex(/^\d{16}$/, '유효한 카드 번호를 입력하세요'),
  expiryDate: z.string().regex(/^\d{2}\/\d{2}$/, 'MM/YY 형식으로 입력하세요'),
  cvv: z.string().regex(/^\d{3}$/, '유효한 CVV를 입력하세요'),
});

type Step1Data = z.infer<typeof step1Schema>;
type Step2Data = z.infer<typeof step2Schema>;
type Step3Data = z.infer<typeof step3Schema>;

interface WizardState {
  step1: Partial<Step1Data>;
  step2: Partial<Step2Data>;
  step3: Partial<Step3Data>;
}

export function RegistrationWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<WizardState>({
    step1: {},
    step2: {},
    step3: {},
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const updateStep = (step: keyof WizardState, data: any) => {
    setFormData(prev => ({
      ...prev,
      [step]: { ...prev[step], ...data },
    }));
  };

  const validateStep = (step: number): boolean => {
    try {
      if (step === 1) {
        step1Schema.parse(formData.step1);
      } else if (step === 2) {
        step2Schema.parse(formData.step2);
      } else if (step === 3) {
        step3Schema.parse(formData.step3);
      }
      setErrors({});
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: Record<string, string> = {};
        error.errors.forEach(err => {
          newErrors[err.path.join('.')] = err.message;
        });
        setErrors(newErrors);
      }
      return false;
    }
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 3));
    }
  };

  const handlePrev = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (validateStep(currentStep)) {
      const allData = {
        ...formData.step1,
        ...formData.step2,
        ...formData.step3,
      };
      await submitRegistration(allData);
    }
  };

  return (
    <div className="wizard">
      <div className="progress-bar">
        <div className={`step ${currentStep >= 1 ? 'active' : ''}`}>1. 기본 정보</div>
        <div className={`step ${currentStep >= 2 ? 'active' : ''}`}>2. 주소</div>
        <div className={`step ${currentStep >= 3 ? 'active' : ''}`}>3. 결제</div>
      </div>

      <div className="step-content">
        {currentStep === 1 && (
          <Step1
            data={formData.step1}
            onChange={data => updateStep('step1', data)}
            errors={errors}
          />
        )}
        {currentStep === 2 && (
          <Step2
            data={formData.step2}
            onChange={data => updateStep('step2', data)}
            errors={errors}
          />
        )}
        {currentStep === 3 && (
          <Step3
            data={formData.step3}
            onChange={data => updateStep('step3', data)}
            errors={errors}
          />
        )}
      </div>

      <div className="navigation">
        <button
          onClick={handlePrev}
          disabled={currentStep === 1}
        >
          이전
        </button>
        {currentStep < 3 ? (
          <button onClick={handleNext}>다음</button>
        ) : (
          <button onClick={handleSubmit}>완료</button>
        )}
      </div>
    </div>
  );
}

interface Step1Props {
  data: Partial<Step1Data>;
  onChange: (data: any) => void;
  errors: Record<string, string>;
}

function Step1({ data, onChange, errors }: Step1Props) {
  return (
    <div>
      <h2>기본 정보</h2>
      <div>
        <input
          type="text"
          value={data.firstName || ''}
          onChange={e => onChange({ firstName: e.target.value })}
          placeholder="이름"
        />
        {errors.firstName && <span className="error">{errors.firstName}</span>}
      </div>
      <div>
        <input
          type="text"
          value={data.lastName || ''}
          onChange={e => onChange({ lastName: e.target.value })}
          placeholder="성"
        />
        {errors.lastName && <span className="error">{errors.lastName}</span>}
      </div>
      <div>
        <input
          type="email"
          value={data.email || ''}
          onChange={e => onChange({ email: e.target.value })}
          placeholder="이메일"
        />
        {errors.email && <span className="error">{errors.email}</span>}
      </div>
    </div>
  );
}

function Step2({ data, onChange, errors }: any) {
  return (
    <div>
      <h2>주소</h2>
      <input
        type="tel"
        value={data.phone || ''}
        onChange={e => onChange({ phone: e.target.value })}
        placeholder="전화번호"
      />
      {errors.phone && <span className="error">{errors.phone}</span>}
      {/* ... */}
    </div>
  );
}

function Step3({ data, onChange, errors }: any) {
  return (
    <div>
      <h2>결제 정보</h2>
      <input
        type="text"
        value={data.cardNumber || ''}
        onChange={e => onChange({ cardNumber: e.target.value })}
        placeholder="카드 번호"
      />
      {errors.cardNumber && <span className="error">{errors.cardNumber}</span>}
      {/* ... */}
    </div>
  );
}
```

## 최소 예제

```typescript
export function SimpleWizard() {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({ name: '', email: '', phone: '' });

  return (
    <div>
      <div>Step {step} of 3</div>

      {step === 1 && (
        <input
          value={data.name}
          onChange={e => setData({ ...data, name: e.target.value })}
          placeholder="이름"
        />
      )}
      {step === 2 && (
        <input
          value={data.email}
          onChange={e => setData({ ...data, email: e.target.value })}
          placeholder="이메일"
        />
      )}
      {step === 3 && (
        <input
          value={data.phone}
          onChange={e => setData({ ...data, phone: e.target.value })}
          placeholder="전화번호"
        />
      )}

      <button onClick={() => setStep(s => Math.max(s - 1, 1))}>이전</button>
      <button onClick={() => setStep(s => Math.min(s + 1, 3))}>다음</button>
    </div>
  );
}
```

## 고급 사용법 - 단계별 자동 저장

```typescript
export function AutoSaveWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<WizardState>(() => {
    // 로컬 스토리지에서 이전 데이터 복구
    return JSON.parse(localStorage.getItem('wizardData') || '{}');
  });

  // 폼 데이터가 변경될 때마다 저장
  useEffect(() => {
    localStorage.setItem('wizardData', JSON.stringify(formData));
  }, [formData]);

  // ... 나머지 로직
}
```

## 조건부 단계 표시

```typescript
export function ConditionalWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<WizardState>({...});

  // Step 2에서 "개인사업자" 선택 시에만 Step 3 표시
  const hasCompany = formData.step2.accountType === 'business';

  const nextStep = () => {
    if (currentStep === 2 && !hasCompany) {
      setCurrentStep(4); // Step 3 건너뛰기
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  return (
    <div>
      {currentStep === 1 && <Step1 {...props} />}
      {currentStep === 2 && <Step2 {...props} />}
      {currentStep === 3 && hasCompany && <Step3 {...props} />}
      {currentStep === 4 && <Step4 {...props} />}
    </div>
  );
}
```

## 안티패턴

### 1. 단계별 컴포넌트에서 전역 상태 관리

```typescript
// ❌ 나쁜 예제
function Step1() {
  const [step1Data, setStep1Data] = useState({});
  const [step2Data, setStep2Data] = useState({}); // 다른 단계 데이터를 여기서 관리
}

// ✅ 좋은 예제
function Step1({ data, onChange }) {
  // 부모에서 관리하는 데이터만 사용
}

export function Wizard() {
  const [formData, setFormData] = useState({
    step1: {}, step2: {}, step3: {}
  });
}
```

### 2. 이전 단계 데이터 검증 누락

```typescript
// ❌ 나쁜 예제 - 다음 버튼만 클릭 가능
const handleNext = () => {
  setCurrentStep(prev => prev + 1); // 검증 없음!
};

// ✅ 좋은 예제 - 현재 단계 검증
const handleNext = () => {
  if (validateStep(currentStep)) {
    setCurrentStep(prev => prev + 1);
  }
};
```

## 연결된 오류

- **E-FS-12**: 이전 단계 데이터 손실
- **E-FS-13**: 검증 없이 단계 진행

## 연결된 플로우

- **F-FS-08**: 온보딩 프로세스
- **F-FS-09**: 체크아웃 플로우

## 참고 자료

- React Context: https://react.dev/reference/react/useContext
- Form Stepper patterns: https://www.smashingmagazine.com/2021/10/form-design-patterns-release-checklist/
