---
id: E-SP-05
title: 권한 상승
error_class: Security-Permission
symptoms:
  - 낮은 권한이 높은 권한 획득
  - 보안 취약점
exact_messages:
  - "Security vulnerability detected"
  - "Unauthorized access"
tech_tags:
  - Security
  - Authorization
linked_patterns: []
linked_flows: []
---

# 권한 상승

## 증상
낮은 권한이 높은 권한 획득로 인해 보안 위험이 발생합니다.

## 빠른 해결법

### 1. 서버 검증
- 모든 권한 확인을 서버에서 수행
- 클라이언트는 신뢰하지 않기

### 2. 접근 제어
- 역할 기반 접근 제어 (RBAC) 구현
- 행 수준 보안 (RLS) 적용

### 3. 입력 검증
- 모든 입력 검증
- 매개변수화된 쿼리 사용

### 4. 출력 이스케이프
- 출력 데이터 이스케이프
- CSP(Content Security Policy) 설정

## 재발 방지
1. 보안 감사 정기 실시
2. 권한 검사 자동화 테스트
3. 의존성 보안 검사
