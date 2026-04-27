---
source_id: kubernetes-networking-101
title: Kubernetes Networking Fundamentals
category: infrastructure
last_reviewed: 2026-03-15
---

# Kubernetes Networking Fundamentals

## Overview

Kubernetes networking enables communication between pods, services, and external clients. Every pod in a Kubernetes cluster receives its own IP address, eliminating the need for explicit links between pods and removing the need to map container ports to host ports.

## Pod-to-Pod Communication

All pods can communicate with all other pods without NAT. This is a fundamental invariant of the Kubernetes networking model. The Container Network Interface (CNI) plugin is responsible for implementing this behavior. Common CNI plugins include Calico, Flannel, and Cilium.

### How It Works

1. Each node is assigned a subnet from the cluster CIDR range.
2. Pods on the same node communicate via the local bridge.
3. Pods on different nodes communicate via the overlay network or direct routing, depending on the CNI plugin.

## Service Discovery

Kubernetes Services provide stable virtual IPs (ClusterIPs) that load-balance traffic across pod replicas. DNS is the primary service discovery mechanism — every Service gets a DNS entry in the format `<service-name>.<namespace>.svc.cluster.local`.

## Network Policies

NetworkPolicy resources control traffic flow at the IP address or port level. By default, pods are non-isolated and accept traffic from any source. Once a NetworkPolicy selects a pod, that pod rejects any connections not explicitly allowed.

## References

- [Kubernetes Networking Documentation](https://kubernetes.io/docs/concepts/services-networking/)
- [CNI Specification](https://github.com/containernetworking/cni)
