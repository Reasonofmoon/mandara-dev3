---
id: E-LS-09
title: 만료된 세션 참조
error_class: Logic-State
symptoms:
  - 로그아웃 후에도 접근 가능
  - 세션 데이터 일관성 없음
  - 다중 탭 동기화 실패
exact_messages:
  - "Session expired"
  - "Invalid session"
  - "User not found in session"
tech_tags:
  - Session Management
  - Authentication
  - State
linked_patterns: []
linked_flows: []
---

# 만료된 세션 참조

## 증상
세션이 만료되었거나 로그아웃했는데 여전히 이전 세션 데이터를 사용합니다.

## 빠른 해결법

### 1. 세션 검증
```typescript
async function getSession(req) {
  const sessionId = req.cookies.sessionId;

  if (!sessionId) {
    return null;
  }

  const session = await db.session.findUnique({
    where: { id: sessionId }
  });

  if (!session || new Date() > session.expiresAt) {
    return null;  // 세션 만료
  }

  return session;
}
```

### 2. 다중 탭 동기화
```typescript
useEffect(() => {
  // 다른 탭에서 logout 감지
  window.addEventListener('storage', (e) => {
    if (e.key === 'auth' && !e.newValue) {
      logout();
    }
  });
}, []);
```

### 3. 세션 갱신
```typescript
async function refreshSession() {
  const response = await fetch('/api/refresh', {
    method: 'POST',
    credentials: 'include'
  });

  if (response.ok) {
    const { token } = await response.json();
    localStorage.setItem('token', token);
  } else {
    logout();
  }
}
```

## 연결된 패턴
- E-LS-08-auth-401-403-confusion
- E-RT-07-token-parse-failure

## 재발 방지
1. 세션 만료 시간 설정
2. 매 요청 시 세션 검증
3. 다중 탭 동기화
