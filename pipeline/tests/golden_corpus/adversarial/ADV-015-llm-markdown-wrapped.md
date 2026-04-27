---
source_id: adv-015-markdown-wrap
title: Basic Load Balancing Concepts
category: infrastructure
---

# Basic Load Balancing Concepts

A load balancer distributes incoming network traffic across multiple backend servers to improve availability and responsiveness.

## Common Algorithms

Round-robin assigns requests sequentially. Least-connections routes to the server with the fewest active connections. IP-hash pins a client to a consistent backend based on source address.

## Health Checks

Load balancers periodically probe backend servers. If a server fails a health check, it is temporarily removed from the pool until it recovers.
