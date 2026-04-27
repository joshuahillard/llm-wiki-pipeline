---
source_id: null
title: Caching Strategies Overview
category: performance
---

# Caching Strategies Overview

Caching stores frequently accessed data in a faster storage layer to reduce latency and backend load. Common strategies include cache-aside (lazy loading), write-through, and write-behind.

## Cache Invalidation

Time-based expiration (TTL) is the simplest invalidation strategy. Event-driven invalidation purges entries when the underlying data changes, offering stronger consistency at the cost of complexity.
