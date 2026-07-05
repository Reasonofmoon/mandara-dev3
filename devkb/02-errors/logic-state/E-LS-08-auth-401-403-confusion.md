---
id: E-LS-08
title: 401/403 혼동
error_class: Logic-State
symptoms:
  - 인증 과 권한 혼동
  - 잘못된 에러 응답
  - 토큰 재생성 오류
exact_messages:
  - "401 Unauthorized"
  - "403 Forbidden"
  - "Authentication required vs Insufficient permissions"
tech_tags:
  - Authentication
  - Authorization
  - HTTP
  - Security
linked_patterns: []
linked_flows: []
---

# 401/403 혼동

## 증상
401(인증)과 403(권한)을 혼동하여 잘못된 처리를 합니다. 401은 로그인 필요, 403은 권한 부족을 의미합니다.

## 빠른 해결법

### 1. 올바른 상태코드
```typescript
// 401: 인증 필요 (토큰 없음 또는 만료)
if (!token || isExpired(token)) {
  return res.status(401).json({ error: 'Unauthorized' });
}

// 403: 권한 부족 (인증되었지만 권한 없음)
if (user.role !== 'admin') {
  return res.status(403).json({ error: 'Forbidden' });
}
```

### 2. 클라이언트 처리
```typescript
async function fetchData() {
  try {
    const response = await fetch('/api/data');

    if (response.status === 401) {
      // 토큰 갱신 시도
      const newToken = await refreshToken();
      return fetch('/api/data', {
        headers: { 'Authorization': `Bearer ${newToken}` }
      });
    }

    if (response.status === 403) {
      // 권한 부족 - 사용자에게 알림
      showError('You do not have permission');
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('Request failed:', error);
  }
}
```

### 3. 미들웨어
```typescript
function requireAuth(req, res, next) {
  const token = req.headers.authorization?.slice(7);

  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const decoded = jwt.verify(token, SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

function requireRole(role) {
  return (req, res, next) => {
    if (req.user.role !== role) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    next();
  };
}

app.get('/api/admin', requireAuth, requireRole('admin'), handler);
```

## 연결된 패턴
- E-RT-07-token-parse-failure
- E-SP-03-role-filtering-missing

## 재발 방지
1. 401 = 인증, 403 = 권한 구분
2. 클라이언트에서 각각 다르게 처리
3. 미들웨어로 검증 분리
