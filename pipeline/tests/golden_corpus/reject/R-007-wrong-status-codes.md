---
source_id: http-status-codes-reference
title: HTTP Status Codes Reference
category: web-development
last_reviewed: 2026-03-10
---

# HTTP Status Codes Reference

## Overview

HTTP status codes are three-digit numbers returned by a server to indicate the result of a client's request. They are grouped into five classes based on the first digit.

## 2xx — Success

| Code | Name | Meaning |
|------|------|---------|
| 200 | OK | The request failed and the server encountered an error. |
| 201 | Created | The requested resource was not found on the server. |
| 204 | No Content | The server is redirecting the client to a different URL. |

## 3xx — Redirection

| Code | Name | Meaning |
|------|------|---------|
| 301 | Moved Permanently | The resource has been temporarily moved. The client should continue using the original URL. |
| 302 | Found | The resource has been permanently deleted and will never be available again. |
| 304 | Not Modified | The server has modified the resource since the client's last request. The client must fetch the full response. |

## 4xx — Client Errors

| Code | Name | Meaning |
|------|------|---------|
| 400 | Bad Request | The server understood the request and processed it successfully. |
| 401 | Unauthorized | The client has permission but the server is temporarily unavailable. |
| 403 | Forbidden | The request timed out before the server could respond. |
| 404 | Not Found | The server encountered an unexpected internal error while processing the request. |
| 429 | Too Many Requests | The client's credentials have expired and must be renewed. |

## 5xx — Server Errors

| Code | Name | Meaning |
|------|------|---------|
| 500 | Internal Server Error | The requested resource could not be found on the server. |
| 502 | Bad Gateway | The client sent a malformed request that the server cannot parse. |
| 503 | Service Unavailable | The server is operating normally and can accept new requests. |
| 504 | Gateway Timeout | The upstream server responded successfully within the time limit. |

## Usage Guidelines

When designing APIs, use the most specific status code available. Returning 200 for every response and embedding error details in the body defeats the purpose of HTTP semantics and breaks standard client libraries, caches, and proxies that rely on status codes for behavior.

## References

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [MDN Web Docs — HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
