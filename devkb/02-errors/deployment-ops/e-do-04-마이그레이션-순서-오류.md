---
id: E-DO-04
title: 마이그레이션 순서 오류
error_class: Deployment-Ops
symptoms:
  - 데이터베이스 마이그레이션 순서 문제
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

# 마이그레이션 순서 오류

## 증상
데이터베이스 마이그레이션 순서 문제로 인해 배포 또는 운영 문제가 발생합니다.

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
