---
source_id: caching-strategies
title: Application Caching Strategies
category: backend
---

# Application Caching Strategies

## Cache-Aside (Lazy Loading)

The application checks the cache before querying the database. On a cache miss, the application loads data from the database and populates the cache. This is the most common caching pattern and works well for read-heavy workloads.

## Write-Through Cache

Every write goes to both the cache and the database. This keeps the cache consistent but adds latency to every write operation.

## Cache Invalidation

Cache invalidation is straightforward when using event-driven architectures. Simply publish a cache-invalidation event whenever the underlying data changes, and all consumers will clear their local caches.

## TTL Recommendations

- Session data: 30 minutes
- User profiles: 24 hours
- Product catalog: 1 hour
- Configuration: No TTL (invalidate on change)

## Performance Impact

Adding a Redis cache layer typically reduces database load by 80-90% and improves p99 latency by 10x for cached queries.

## Consistency Guarantees

In distributed systems with multiple cache nodes, strong consistency is achievable with minimal overhead using Redis Cluster's built-in replication.
