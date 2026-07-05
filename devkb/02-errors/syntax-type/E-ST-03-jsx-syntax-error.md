---
id: E-ST-03
title: JSX 문법 오류
error_class: Syntax-Type
symptoms:
  - 파일 파싱 에러
  - 컴파일 실패
  - 태그 닫기 오류
exact_messages:
  - "Unexpected token '<'"
  - "Expected closing tag 'div'"
  - "Adjacent JSX elements must be wrapped in an enclosing tag"
  - "JSX expressions must have one parent element"
tech_tags:
  - React
  - JSX
  - Syntax
  - Compilation
linked_patterns: []
linked_flows: []
---

# JSX 문법 오류

## 증상
JSX 문법이 올바르지 않으면 파일이 파싱되지 않아 컴파일 단계에서 실패합니다. 태그 닫기, 속성 문법, 또는 표현식 문법이 잘못되었을 때 발생합니다.

## 정확한 에러 메시지
```
Unexpected token '<'
Expected closing tag 'div'
Adjacent JSX elements must be wrapped in an enclosing tag
JSX expressions must have one parent element
Unterminated JSX expression
```

## 발생 맥락
```typescript
// 잘못된 예 1: 태그 닫기 오류
function Component() {
  return (
    <div>
      <h1>Title</h1>
      <p>Content
    </div>
  );
}

// 잘못된 예 2: 여러 최상위 요소
function Component() {
  return (
    <div>Title</div>
    <p>Content</p>
  );
}

// 잘못된 예 3: 속성 문법 오류
function Component() {
  return <div class="container">Content</div>;  // ❌ HTML: class, JSX: className
}

// 잘못된 예 4: 표현식 문법 오류
function Component() {
  const items = [1, 2, 3];
  return (
    <div>
      {items.map(item => <span>{item}</span>)}  // ❌ key 속성 누락
    </div>
  );
}
```

## 필요한 증거
- 컴파일 에러 메시지 및 라인 번호
- JSX 코드 스니펫
- 오류 발생 시점의 파일 내용

## 의심 원인
1. 태그 닫기 누락 또는 잘못된 순서
2. 여러 최상위 요소 반환
3. HTML 속성을 JSX에서 사용 (예: class 대신 className)
4. 표현식 문법 오류 (중괄호, 따옴표)
5. 조건부 렌더링 문법 오류

## 빠른 해결법

### 1. 태그 닫기 확인 및 수정
```typescript
// ❌ 잘못된 코드
function Component() {
  return (
    <div>
      <h1>Title</h1>
      <p>Content
    </div>
  );
}

// ✅ 올바른 코드
function Component() {
  return (
    <div>
      <h1>Title</h1>
      <p>Content</p>
    </div>
  );
}
```

### 2. 여러 요소는 Fragment로 감싸기
```typescript
// ❌ 잘못된 코드
function Component() {
  return (
    <h1>Title</h1>
    <p>Content</p>
  );
}

// ✅ 올바른 코드
function Component() {
  return (
    <>
      <h1>Title</h1>
      <p>Content</p>
    </>
  );
}

// 또는
import React from 'react';
function Component() {
  return (
    <React.Fragment>
      <h1>Title</h1>
      <p>Content</p>
    </React.Fragment>
  );
}
```

### 3. HTML 속성을 JSX 속성으로 수정
```typescript
// ❌ 잘못된 코드
function Component() {
  return (
    <div class="container" for="input">
      <input id="input" />
    </div>
  );
}

// ✅ 올바른 코드
function Component() {
  return (
    <div className="container" htmlFor="input">
      <input id="input" />
    </div>
  );
}
```

### 4. 리스트 렌더링 시 key 속성 추가
```typescript
// ❌ 잘못된 코드
function Component() {
  const items = [1, 2, 3];
  return (
    <ul>
      {items.map(item => <li>{item}</li>)}
    </ul>
  );
}

// ✅ 올바른 코드
function Component() {
  const items = [1, 2, 3];
  return (
    <ul>
      {items.map(item => <li key={item}>{item}</li>)}
    </ul>
  );
}
```

### 5. 조건부 렌더링 문법
```typescript
// ❌ 잘못된 코드
function Component({ isVisible }) {
  return (
    <div>
      {isVisible && <p>Visible</p> || <p>Hidden</p>}
    </div>
  );
}

// ✅ 올바른 코드
function Component({ isVisible }) {
  return (
    <div>
      {isVisible ? <p>Visible</p> : <p>Hidden</p>}
      {isVisible && <p>Visible</p>}
    </div>
  );
}
```

## 연결된 패턴
- E-ST-01-prop-type-mismatch
- E-RT-08-serialization-error

## 연결된 플로우
- React 컴포넌트 개발 플로우
- JSX 작성 및 검증 플로우

## 재발 방지
1. IDE에서 ESLint 및 Prettier 설정
2. JSX 문법 하이라이팅 활성화
3. 자동 포맷팅으로 일관성 유지
4. 열고 닫는 태그 개수 확인 습관
5. TypeScript 사용으로 추가 타입 체크
