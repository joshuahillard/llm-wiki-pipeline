---
source_id: monitoring-alerting
title: Monitoring and Alerting Best Practices
category: operations
---

# Monitoring and Alerting Best Practices

## The Four Golden Signals

Monitor these signals for every service:

1. **Latency** — Time to service a request. Distinguish between successful and failed request latency.
2. **Traffic** — Request rate (HTTP requests per second, transactions per minute).
3. **Errors** — Rate of failed requests (5xx responses, exceptions).
4. **Saturation** — How full the most constrained resource is (CPU, memory, disk I/O, network).

## Alert Fatigue

The biggest risk in monitoring is alert fatigue. If your team receives more than 10 non-actionable alerts per on-call shift, your alerting is too noisy. Every alert should have a clear runbook and require human action.

## Recommended Stack

Use Prometheus for metrics collection, Grafana for visualization, and PagerDuty for alert routing. This stack handles most use cases up to moderate scale.

## SLO-Based Alerting

Define error budgets based on your SLO. Alert when the burn rate exceeds your budget:

- 1-hour burn rate > 14.4x budget → Page immediately
- 6-hour burn rate > 6x budget → Page during business hours
- 3-day burn rate > 1x budget → Ticket

This approach dramatically reduces alert noise.
