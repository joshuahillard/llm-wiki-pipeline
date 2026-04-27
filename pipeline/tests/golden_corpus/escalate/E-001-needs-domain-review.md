---
source_id: disaster-recovery-rpo
title: Disaster Recovery RPO and RTO Planning
category: operations
---

# Disaster Recovery RPO and RTO Planning

## Definitions

- **RPO (Recovery Point Objective):** The maximum acceptable amount of data loss measured in time. An RPO of 1 hour means you can tolerate losing up to 1 hour of data.
- **RTO (Recovery Time Objective):** The maximum acceptable downtime before services must be restored.

## Our Current Configuration

Our PostgreSQL streaming replication has an RPO of approximately 5 seconds under normal conditions. During network partitions, the RPO may increase to the duration of the partition.

Our Kubernetes deployment achieves an RTO of approximately 15 minutes for stateless services (pod rescheduling) and 45 minutes for stateful services (volume reattachment + data verification).

## Recommendation

Based on the current SLA (99.9% availability, 8.7 hours annual downtime budget), these values are adequate for Tier 2 services. However, Tier 1 services (payment processing, authentication) may require synchronous replication and hot standby to achieve sub-second RPO.

## Open Question

The cost of synchronous replication (estimated 30-40% write latency increase) has not been validated against the payment processing SLA. This trade-off requires engineering and product alignment before implementation.
