---
source_id: dns-resolution-internals
title: DNS Resolution Internals
category: networking
last_reviewed: 2026-03-20
---

DNS resolution is the process of converting a human-readable domain name into an IP address. It is a foundational operation in networked systems and affects the latency, reliability, and security of virtually every outbound connection.

## Recursive vs. Iterative Resolution

When a client issues a DNS query, it typically contacts a recursive resolver (often operated by the ISP or a service like 1.1.1.1 or 8.8.8.8). The recursive resolver walks the DNS hierarchy on the client's behalf:

1. Query the root nameserver for the TLD (e.g., `.com`).
2. Query the TLD nameserver for the authoritative server of the target domain.
3. Query the authoritative server for the final A or AAAA record.

Iterative resolution shifts this work to the client, which receives referrals at each step and must follow them independently. Most end-user systems rely on recursive resolution.

## Caching and TTL

Every DNS record carries a time-to-live (TTL) value that tells resolvers how long to cache the response. Short TTLs (30–60 seconds) allow rapid failover but increase query volume. Long TTLs (3600+ seconds) reduce load but delay propagation of changes.

Negative caching — caching the absence of a record (NXDOMAIN) — is governed by the SOA record's minimum TTL field. Misconfigured negative caching can cause stale NXDOMAIN responses to persist after a new record is created.

## Common Failure Modes

- **Stale cache entries** after a DNS migration when TTLs were not lowered in advance.
- **SERVFAIL loops** when a recursive resolver cannot reach the authoritative server due to network partitioning or firewall rules.
- **DNSSEC validation failures** when signature records expire or the chain of trust is broken by a key rollover.

## Security Considerations

DNS traffic is unencrypted by default (port 53, UDP/TCP). DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT) encrypt queries between the client and recursive resolver but do not protect the resolver-to-authoritative leg. DNSSEC provides authenticity and integrity for DNS responses but does not provide confidentiality.

## References

- [RFC 1034 — Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034)
- [RFC 1035 — Domain Names: Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035)
