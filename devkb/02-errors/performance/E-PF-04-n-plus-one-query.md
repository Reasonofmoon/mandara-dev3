---
id: E-PF-04
title: N+1 쿼리
error_class: Performance
symptoms:
  - 반복문에서 데이터베이스 쿼리 반복
  - 성능 저하
exact_messages:
  - "Performance issue detected"
  - "Slow operation"
tech_tags:
  - Performance
  - Optimization
linked_patterns: []
linked_flows: []
---

# N+1 쿼리

## 증상
반복문에서 데이터베이스 쿼리 반복로 인해 성능이 저하됩니다.

## 빠른 해결법

### 1. 분석 및 측정
- Chrome DevTools Profiler로 성능 측정
- 병목 지점 식별

### 2. 최적화
- 캐싱 도입
- 데이터 구조 최적화
- 알고리즘 개선

### 3. 모니터링
- 성능 메트릭 수집
- 정기적인 성능 검사

## 재발 방지
1. 성능 테스트 자동화
2. 성능 예산 설정
3. 정기적인 성능 감시
