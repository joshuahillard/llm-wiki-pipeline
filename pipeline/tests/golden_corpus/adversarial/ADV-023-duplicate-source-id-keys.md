---
source_id: first-id-value
title: Message Queue Fundamentals
source_id: second-id-value
category: messaging
---

# Message Queue Fundamentals

Message queues decouple producers from consumers by buffering messages in a persistent store. This enables asynchronous processing and graceful handling of traffic bursts.

## Delivery Guarantees

At-most-once delivery avoids duplicates but may lose messages. At-least-once delivery guarantees no loss but requires idempotent consumers. Exactly-once semantics require transactional coordination between the queue and the consumer.
