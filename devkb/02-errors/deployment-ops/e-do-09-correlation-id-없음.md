---
id: E-DO-09
title: Correlation ID 없음
error_class: Deployment-Ops
symptoms:
  - 요청 추적 불가
  - 서비스 장애
exact_messages:
  - "Deployment failed"
  - "Service unavailable"
tech_tags:
  - DevOps
  - Deployment
  - Monitoring
linked_patterns: []
linked_flows: []
---

# Correlation ID 없음

## 증상
요청 추적 불가로 인해 배포 또는 운영 문제가 발생합니다.

## 빠른 해결법

### 1. 자동화
- 배포 파이프라인 자동화
- 헬스체크 자동화
- 모니터링 자동화

### 2. 모니터링
- 주요 메트릭 추적
- 알림 설정
- 로그 집계

### 3. 복구
- 롤백 계획 수립
- 재해 복구 계획 (DR)
- 백업 검증

## 재발 방지
1. 배포 전 검증 자동화
2. 헬스체크 지속적 모니터링
3. 정기적 재해 복구 훈련
