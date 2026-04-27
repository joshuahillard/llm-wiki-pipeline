---
source_id: structured-logging-practices
title: Structured Logging Best Practices
category: observability
last_reviewed: 2026-01-25
---

# Structured Logging Best Practices

## Overview

Structured logging emits log entries as key-value pairs (typically JSON) rather than free-form text strings. This makes logs machine-parseable, queryable, and compatible with log aggregation systems without fragile regex-based extraction.

## Why Structured Logging

Unstructured logs like `"User 42 logged in from 10.0.0.1"` require pattern matching to extract the user ID and IP address. A structured equivalent — `{"event": "user_login", "user_id": 42, "ip": "10.0.0.1"}` — makes every field directly queryable.

Benefits include:

- Consistent field names across services enable cross-service correlation.
- Log aggregation tools (Elasticsearch, Loki, Datadog) index structured fields natively.
- Alerting rules can reference specific fields without parsing ambiguity.

## Key Fields

Every log entry should include at minimum:

- **timestamp** — ISO 8601 with timezone, preferably UTC.
- **level** — severity (debug, info, warn, error, fatal).
- **message** — human-readable description of the event.
- **service** — the name of the emitting service or component.
- **trace_id** — distributed tracing correlation identifier, if available.

Additional context fields depend on the event type: `user_id`, `request_id`, `duration_ms`, `status_code`, `error_type`, and so on.

## Avoiding Common Mistakes

- **Logging sensitive data** — PII, credentials, and tokens must never appear in logs. Use allowlists rather than blocklists to control which fields are logged.
- **Inconsistent field naming** — `userId`, `user_id`, and `uid` in different services defeat cross-service queries. Establish a naming convention and enforce it via shared logging libraries.
- **Excessive verbosity at INFO level** — high-volume debug-grade entries at INFO level increase storage costs and noise. Reserve INFO for operationally meaningful events.

## Log Levels in Practice

| Level | Use For | Example |
|-------|---------|---------|
| DEBUG | Internal state useful during development | Cache hit ratio per request |
| INFO | Normal operational events | Service started, request completed |
| WARN | Recoverable anomalies | Retry succeeded after transient failure |
| ERROR | Failures requiring attention | Database connection failed, timeout exceeded |
| FATAL | Unrecoverable failures | Configuration missing, process exiting |

## References

- [The Twelve-Factor App — Logs](https://12factor.net/logs)
- [OpenTelemetry Logging Specification](https://opentelemetry.io/docs/specs/otel/logs/)
