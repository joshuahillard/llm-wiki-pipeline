---
source_id: api-error-codes
title: API Error Code Reference
category: backend
---

# API Error Code Reference

## Standard HTTP Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 400  | Bad Request | The request body is malformed or missing required fields. |
| 401  | Unauthorized | Authentication credentials are missing or invalid. |
| 403  | Forbidden | The authenticated user lacks permission for this resource. |
| 404  | Not Found | The requested resource does not exist. |
| 429  | Too Many Requests | Rate limit exceeded — retry after the `Retry-After` header value. |
| 500  | Internal Server Error | An unexpected server-side error occurred. |

## Custom Error Codes

Our API returns structured error responses with a `code` field:

- `ERR_VALIDATION_FAILED` — Input validation failed. Check the `details` array.
- `ERR_DUPLICATE_ENTRY` — A resource with the same unique key already exists.
- `ERR_STALE_VERSION` — The `If-Match` ETag does not match the current version (optimistic concurrency conflict).

## Retry Strategy

For 429 and 5xx errors, implement exponential backoff with jitter:

```
delay = min(base_delay × 2^attempt + random_jitter, max_delay)
```

Maximum retry attempts: 3. Circuit breaker opens after 5 consecutive failures.
