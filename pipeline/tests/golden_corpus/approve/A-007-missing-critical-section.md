---
source_id: webhook-api-reference
title: Webhook API Reference
category: api
---

# Webhook API Reference

## Overview

The Webhook API allows services to subscribe to event delivery over HTTPS. Each delivery contains an event type, a timestamp, and a signed payload.

## Authentication

Clients authenticate using a bearer token and should verify the request signature before processing a payload. Signature verification prevents spoofed event submissions.

## Endpoints

`POST /v1/webhooks/test` triggers a synthetic delivery for configuration checks.

`GET /v1/webhooks/events` returns recent delivery metadata for debugging.

## Error Handling

Return a `2xx` status code after successful processing. Non-`2xx` responses cause the sender to retry with exponential backoff.

## References

- [Webhook Security Best Practices](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
