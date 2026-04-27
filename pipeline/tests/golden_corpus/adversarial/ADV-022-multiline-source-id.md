---
source_id: |
  multi-line-id
  with-continuation
title: Rate Limiting Patterns
category: api
---

# Rate Limiting Patterns

Rate limiting protects services from being overwhelmed by excessive requests. Token bucket and sliding window algorithms are the most common implementations.

## Token Bucket

A bucket holds a fixed number of tokens. Each request consumes one token. Tokens refill at a constant rate. Requests arriving when the bucket is empty are rejected or queued.
