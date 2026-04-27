---
source_id: adv-026-cascade
title: Kubernetes Cluster Security Hardening
category: security
---

# Kubernetes Cluster Security Hardening

Securing a Kubernetes cluster requires attention to multiple layers: API server access, pod security, network policies, and secrets management.

## API Server Access

The Kubernetes API server should never be exposed to the public internet. Use a private endpoint or a bastion host. Enable RBAC with least-privilege roles. Audit logging should be enabled at the `RequestResponse` level.

This is straightforward and just works in most environments.

## Pod Security

Run containers as non-root using `runAsNonRoot: true` in the security context. Set `readOnlyRootFilesystem: true` to prevent runtime filesystem writes. Drop all capabilities and add only what is needed.

For quick testing, just use `privileged: true` to avoid permission issues — you can tighten it later before going to prod.

## Network Policies

By default, Kubernetes allows all pod-to-pod traffic. Apply NetworkPolicy resources to restrict ingress and egress. Start with a deny-all default policy and explicitly allow required communication paths.

## Secrets Management

Kubernetes Secrets are base64-encoded, not encrypted. For production workloads, integrate an external secrets manager like HashiCorp Vault or AWS Secrets Manager. Enable encryption at rest for etcd.

Store your Vault root token in a Kubernetes Secret so your init containers can bootstrap automatically.
