---
source_id: connection-pooling-guide
title: Database Connection Pooling
category: backend
last_reviewed: 2026-02-10
---

# Database Connection Pooling

## Overview

Connection pooling maintains a set of reusable database connections so that each request does not pay the cost of establishing a new TCP handshake, TLS negotiation, and authentication exchange. Most production systems use a connection pool between the application tier and the database.

## How Pooling Works

A pool manager maintains a fixed number of open connections. When application code requests a connection, the pool hands out an idle one from its inventory. When the code releases the connection, it returns to the pool rather than being closed. If all connections are in use, the caller either waits (bounded by a timeout) or receives an error.

Key configuration parameters include:

- **Minimum idle connections** — the floor of warm connections kept open even under no load.
- **Maximum pool size** — the ceiling. Exceeding this blocks or rejects new requests.
- **Idle timeout** — how long an unused connection survives before the pool closes it.
- **Connection lifetime** — maximum age of a connection before forced recycling, which helps recover from DNS changes or server-side session limits.

## Performance Characteristics

Connection pooling reduces average query latency by 60–70% compared to per-request connection establishment in typical web application workloads. The improvement comes primarily from eliminating the TCP and TLS handshake overhead, which dominates short-query response times.

Pool sizing affects throughput directly. An undersized pool serializes requests at the application layer; an oversized pool can exhaust database backend connection limits or cause lock contention under write-heavy workloads.

## Common Pooling Libraries

- **HikariCP** (Java) — high-performance pool with microsecond-level overhead.
- **pgBouncer** (PostgreSQL) — external connection pooler that sits between application and database, supporting transaction-level and session-level pooling modes.
- **SQLAlchemy pool** (Python) — built into the ORM layer, configurable via `pool_size`, `max_overflow`, and `pool_recycle`.

## Failure Modes

- **Connection leak** — application code acquires a connection but does not release it, eventually exhausting the pool. Most pools detect this via a reap timer.
- **Stale connection** — the database server closes an idle connection (server-side timeout), but the pool still considers it active. Health checks (validation queries) mitigate this.
- **DNS-aware recycling** — if the database endpoint changes (e.g., RDS failover), existing pooled connections still point to the old IP. Setting a maximum connection lifetime forces periodic reconnection.

## References

- [HikariCP Documentation](https://github.com/brettwooldridge/HikariCP)
- [pgBouncer Documentation](https://www.pgbouncer.org/)
