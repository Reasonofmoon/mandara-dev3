---
id: P-MN-02
title: SLO 기반 알림 패턴
stage: Operate
layer: Observability
pattern_family: Monitoring
tech_tags: [SLO, Burn Rate, Prometheus, Grafana, 에러 버짓]
linked_errors: [E-MN-03, E-MN-04]
linked_flows: [F-MN-02, F-MN-03]
linked_prompts: [PR-MN-02]
---

# SLO 기반 알림 패턴

## 목표
Service Level Objective(SLO)를 기반으로 알림을 설정하여 서비스 신뢰성을 보장합니다.

## 핵심 개념

### SLO 정의

```typescript
// monitoring/slo.config.ts
export const SLOs = {
  // 99.9% 가용성 (월간 약 43분 다운타임 허용)
  availability: {
    target: 0.999,
    window: '30d',
    description: 'Service availability SLO',
  },

  // API 응답 시간 (p99)
  latency: {
    target: 0.99,
    threshold: 100, // ms
    window: '30d',
    description: 'API latency p99 SLO',
  },

  // 에러율
  errorRate: {
    target: 0.999, // 0.1% 이하
    window: '30d',
    description: 'Error rate SLO',
  },
};

// 에러 버짓 계산
export function calculateErrorBudget(slo: SLO, window: string) {
  const dailyBudget = (1 - slo.target) / 30;
  return dailyBudget * 100; // 퍼센트
}
```

## Prometheus 설정

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'myapp'
    static_configs:
      - targets: ['localhost:3000']

# 알림 규칙
rule_files:
  - 'alert_rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'localhost:9093'
```

### 알림 규칙

```yaml
# alert_rules.yml
groups:
  - name: slo_alerts
    interval: 1m

    rules:
      # 1시간 에러 버짓 소진 속도 (빠름)
      - alert: HighErrorRateFastBurn
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          slo: error_rate
        annotations:
          summary: "High error rate (fast burn)"
          description: "Error rate is {{ $value | humanizePercentage }} (target: 0.1%)"

      # 6시간 에러 버짓 소진 속도 (느림)
      - alert: HighErrorRateSlowBurn
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[30m]))
            /
            sum(rate(http_requests_total[30m]))
          ) > 0.01
        for: 30m
        labels:
          severity: warning
          slo: error_rate
        annotations:
          summary: "Sustained elevated error rate"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # API 응답 시간
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
          > 0.1
        for: 10m
        labels:
          severity: warning
          slo: latency
        annotations:
          summary: "High API latency"
          description: "p99 latency is {{ $value }}s (target: 0.1s)"

      # 가용성
      - alert: LowAvailability
        expr: |
          (
            sum(rate(http_requests_total{status!~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) < 0.999
        for: 5m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Low service availability"
          description: "Availability is {{ $value | humanizePercentage }} (target: 99.9%)"
```

## Grafana 대시보드

```typescript
// grafana/dashboards/slo.ts
export const sloDashboard = {
  dashboard: {
    title: 'SLO Monitoring',
    panels: [
      {
        title: 'Error Rate vs SLO',
        targets: [
          {
            expr: 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))',
            legendFormat: 'Actual Error Rate',
          },
          {
            expr: '0.001', // SLO 목표 (0.1%)
            legendFormat: 'SLO Target',
          },
        ],
        alert: {
          conditions: [
            {
              evaluator: { params: [0.001], type: 'gt' },
            },
          ],
        },
      },

      {
        title: 'Error Budget Remaining',
        targets: [
          {
            expr: |
              (1 - sum(rate(http_requests_total{status=~"5.."}[30d])) / sum(rate(http_requests_total[30d]))) * 100
            ,
            legendFormat: 'Remaining Budget %',
          },
        ],
      },

      {
        title: 'Burn Rate (1h window)',
        targets: [
          {
            expr: |
              (
                sum(rate(http_requests_total{status=~"5.."}[1h]))
                /
                (sum(rate(http_requests_total[1h])) * 0.001)
              )
            ,
            legendFormat: 'Burn Rate',
          },
        ],
      },

      {
        title: 'API Latency p99',
        targets: [
          {
            expr: 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))',
            legendFormat: 'p99 Latency',
          },
          {
            expr: '0.1', // SLO 목표 (100ms)
            legendFormat: 'SLO Target',
          },
        ],
      },
    ],
  },
};
```

## 알림 매니저 설정

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # 중대한 SLO 위반
    - match:
        severity: critical
        slo: error_rate
      receiver: 'slo-critical'
      repeat_interval: 5m

    # 경고 수준 SLO
    - match:
        severity: warning
        slo: error_rate
      receiver: 'slo-warning'
      repeat_interval: 1h

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'slo-critical'
    slack_configs:
      - channel: '#slo-critical'
        title: '🚨 SLO VIOLATION: {{ .GroupLabels.slo }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
    pagerduty_configs:
      - routing_key: 'YOUR_ROUTING_KEY'

  - name: 'slo-warning'
    slack_configs:
      - channel: '#slo-warning'
        title: '⚠️ SLO Warning: {{ .GroupLabels.slo }}'
```

## Burn Rate 기반 알림

```typescript
// monitoring/burn-rate.service.ts
@Injectable()
export class BurnRateService {
  async checkBurnRate(slo: SLO): Promise<Severity> {
    const errors1h = await this.getErrorRate('1h');
    const errors6h = await this.getErrorRate('6h');

    // 에러 버짓 소진율
    const burnRate1h = errors1h / (1 - slo.target);
    const burnRate6h = errors6h / (1 - slo.target);

    // 다양한 severity 결정
    if (burnRate1h > 10) {
      // 1시간에 한 달 에러 버짓의 10배 소진
      return 'CRITICAL';
    }

    if (burnRate1h > 3 && burnRate6h > 1) {
      // 1시간에 3배 이상, 6시간에 1배 이상
      return 'WARNING';
    }

    if (burnRate6h > 1.5) {
      // 지속적인 초과
      return 'INFO';
    }

    return 'OK';
  }

  private async getErrorRate(window: string): Promise<number> {
    // Prometheus 쿼리
    return 0.001; // 실제로는 동적 계산
  }
}
```

## 최소 예제

```yaml
# 간단한 SLO 알림
- alert: ErrorRateHigh
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
    ) > 0.001
  for: 5m
  annotations:
    summary: "Error rate exceeded SLO"
```

## 안티패턴

### 1. SLO 목표 설정 오류

```typescript
// ❌ 나쁜 예제
// 99.99% 가용성은 현실적이지 않은 목표
const unrealistic = { availability: 0.9999 };

// ✅ 좋은 예제
// 실제 역사 데이터 기반
const realistic = { availability: 0.999 }; // 43분/월
```

### 2. 알림 피로

```typescript
// ❌ 나쁜 예제
// 모든 임계값에 대해 알림
- alert: AnyError
  expr: up == 0

// ✅ 좋은 예제
// SLO 위반만 알림
- alert: SLOViolation
  expr: burn_rate > 1
```

## 연결된 오류

- **E-MN-03**: SLO 위반 미탐지
- **E-MN-04**: 불필요한 알림 (알림 피로)

## 연결된 플로우

- **F-MN-02**: SLO 위반 대응
- **F-MN-03**: 에러 버짓 관리

## 참고 자료

- Google SRE Book: https://sre.google/sre-book/service-level-objectives/
- Prometheus Alerting: https://prometheus.io/docs/alerting/latest/overview/
- Burn Rate Alerting: https://www.gremlin.com/blog/understanding-slos-and-burn-rate/
