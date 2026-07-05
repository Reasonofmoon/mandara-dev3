---
id: E-PF-03
title: 과도한 데이터 요청
error_class: Performance
symptoms:
  - API에서 불필요한 데이터 조회
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

# 과도한 데이터 요청

## 증상
API에서 불필요한 데이터 조회로 인해 성능이 저하됩니다.

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
