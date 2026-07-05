---
id: P-AR-04
title: 권한 가드 패턴
stage: Implement
layer: UI
pattern_family: Auth
tech_tags: [React, 라우트 가드, 조건부 렌더링, SSR]
linked_errors: [E-AR-09, E-AR-10]
linked_flows: [F-AR-06]
linked_prompts: [PR-AR-04]
---

# 권한 가드 패턴

## 목표
React에서 사용자의 권한에 따라 라우트와 컴포넌트 렌더링을 제어하여 보안을 강화합니다.

## 언제 사용하는가
- 관리자 페이지 등 권한이 필요한 경로
- 특정 권한을 가진 사용자만 볼 수 있는 컴포넌트
- SSR 환경에서의 권한 검증

## 핵심 구조

### Context 기반 권한 관리

```typescript
// auth/auth.context.tsx
import React, { createContext, useState, useEffect } from 'react';

export enum UserRole {
  ADMIN = 'ADMIN',
  MODERATOR = 'MODERATOR',
  USER = 'USER',
  GUEST = 'GUEST',
}

interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  hasRole: (role: UserRole | UserRole[]) => boolean;
  hasPermission: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // 초기 로드
  useEffect(() => {
    const initAuth = async () => {
      try {
        const response = await fetch('/auth/me', {
          credentials: 'include',
        });

        if (response.ok) {
          const data = await response.json();
          setUser(data.user);
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const hasRole = (role: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const roles = Array.isArray(role) ? role : [role];
    return roles.includes(user.role);
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;

    // 역할별 권한 맵
    const permissionMap: Record<UserRole, string[]> = {
      [UserRole.ADMIN]: ['users.read', 'users.write', 'users.delete', 'posts.delete'],
      [UserRole.MODERATOR]: ['users.read', 'posts.delete'],
      [UserRole.USER]: ['posts.create', 'posts.update'],
      [UserRole.GUEST]: [],
    };

    return permissionMap[user.role]?.includes(permission) ?? false;
  };

  const login = async (email: string, password: string) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include',
    });

    if (!response.ok) throw new Error('Login failed');

    const data = await response.json();
    setUser(data.user);
  };

  const logout = async () => {
    await fetch('/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        hasRole,
        hasPermission,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### 라우트 가드

```typescript
// routing/protected-route.tsx
import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, UserRole } from 'auth/auth.context';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: UserRole[];
  requiredPermissions?: string[];
  fallback?: ReactNode;
}

export function ProtectedRoute({
  children,
  requiredRoles,
  requiredPermissions,
  fallback,
}: ProtectedRouteProps) {
  const { user, loading, hasRole, hasPermission } = useAuth();
  const location = useLocation();

  if (loading) {
    return fallback || <div>로딩 중...</div>;
  }

  // 인증 확인
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 역할 확인
  if (requiredRoles && !hasRole(requiredRoles)) {
    return fallback || <Navigate to="/unauthorized" replace />;
  }

  // 권한 확인
  if (requiredPermissions) {
    const hasAllPermissions = requiredPermissions.every(perm =>
      hasPermission(perm)
    );

    if (!hasAllPermissions) {
      return fallback || <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
}
```

### 라우팅 설정

```typescript
// routing/routes.tsx
import { Routes, Route } from 'react-router-dom';
import { UserRole } from 'auth/auth.context';
import { ProtectedRoute } from './protected-route';
import { AdminDashboard } from 'pages/admin-dashboard';
import { Dashboard } from 'pages/dashboard';
import { Login } from 'pages/login';
import { Unauthorized } from 'pages/unauthorized';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* 모든 인증된 사용자 접근 가능 */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* 관리자만 접근 가능 */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRoles={[UserRole.ADMIN]}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      {/* 특정 권한 필요 */}
      <Route
        path="/user-management"
        element={
          <ProtectedRoute
            requiredRoles={[UserRole.ADMIN, UserRole.MODERATOR]}
            requiredPermissions={['users.read']}
          >
            <UserManagement />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

## 컴포넌트 레벨 권한

```typescript
// components/admin-section.tsx
import { useAuth, UserRole } from 'auth/auth.context';

export function AdminSection() {
  const { hasRole, hasPermission } = useAuth();

  if (!hasRole(UserRole.ADMIN)) {
    return null;
  }

  return (
    <div className="admin-section">
      <h2>관리자 섹션</h2>

      {hasPermission('users.write') && (
        <button>사용자 추가</button>
      )}

      {hasPermission('users.delete') && (
        <button>사용자 삭제</button>
      )}
    </div>
  );
}

// 조건부 렌더링
export function Dashboard() {
  const { user, hasRole } = useAuth();

  return (
    <div>
      <h1>대시보드</h1>

      {/* 모든 사용자 볼 수 있음 */}
      <StatsSection />

      {/* 관리자만 볼 수 있음 */}
      {hasRole(UserRole.ADMIN) && <AdminPanel />}

      {/* 중재자 이상 */}
      {hasRole([UserRole.ADMIN, UserRole.MODERATOR]) && (
        <ModerationTools />
      )}
    </div>
  );
}
```

## SSR 환경 (Next.js)

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

const secret = new TextEncoder().encode(
  process.env.JWT_ACCESS_SECRET || ''
);

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('accessToken')?.value;

  // 보호된 라우트
  if (request.nextUrl.pathname.startsWith('/admin')) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    try {
      const verified = await jwtVerify(token, secret);
      const user = verified.payload as any;

      if (user.role !== 'ADMIN') {
        return NextResponse.redirect(new URL('/unauthorized', request.url));
      }
    } catch (error) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/dashboard/:path*'],
};

// app/admin/page.tsx
import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';
import { redirect } from 'next/navigation';

export default async function AdminPage() {
  const cookieStore = cookies();
  const token = cookieStore.get('accessToken')?.value;

  if (!token) {
    redirect('/login');
  }

  try {
    const secret = new TextEncoder().encode(
      process.env.JWT_ACCESS_SECRET || ''
    );
    const verified = await jwtVerify(token, secret);
    const user = verified.payload as any;

    if (user.role !== 'ADMIN') {
      redirect('/unauthorized');
    }

    return <div>관리자 페이지</div>;
  } catch (error) {
    redirect('/login');
  }
}
```

## 최소 예제

```typescript
function AdminRoute({ children }) {
  const { user } = useAuth();

  if (user?.role !== 'ADMIN') {
    return <Navigate to="/login" />;
  }

  return children;
}
```

## 동적 권한 기반 UI

```typescript
export function FeatureGate({
  requiredPermission,
  fallback,
  children,
}: {
  requiredPermission: string;
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const { hasPermission } = useAuth();

  if (!hasPermission(requiredPermission)) {
    return fallback || null;
  }

  return <>{children}</>;
}

// 사용
<FeatureGate
  requiredPermission="advanced.analytics"
  fallback={<p>이 기능은 프리미엄 플랜에서 사용 가능합니다.</p>}
>
  <AdvancedAnalytics />
</FeatureGate>
```

## 안티패턴

### 1. 클라이언트 검증만 수행

```typescript
// ❌ 나쁜 예제
if (user?.role === 'ADMIN') {
  // UI 숨김만 함
}
// 하지만 사용자가 개발자 도구로 API 직접 호출 가능!

// ✅ 좋은 예제
// 1. 클라이언트에서 UI 제어
if (!hasRole(UserRole.ADMIN)) {
  return null;
}

// 2. 서버에서도 권한 검증
@UseGuards(JwtGuard, RolesGuard)
@Roles(UserRole.ADMIN)
deleteUser() { }
```

### 2. 권한 정보를 localStorage에 저장

```typescript
// ❌ 나쁜 예제
localStorage.setItem('userRole', user.role);
// XSS로 조작 가능!

// ✅ 좋은 예제
// Context/State에서만 관리하고, 서버에서 검증
const { user } = useAuth();
```

## 연결된 오류

- **E-AR-09**: 미인증 사용자가 보호된 라우트 접근
- **E-AR-10**: 권한 없는 사용자가 기능 사용

## 연결된 플로우

- **F-AR-06**: 권한별 UI 구성

## 참고 자료

- React Router Protected Routes: https://reactrouter.com/
- Next.js Middleware: https://nextjs.org/docs/app/building-your-application/routing/middleware
