---
source_id: adv-019-empty-resp
title: Container Networking Basics
category: infrastructure
---

# Container Networking Basics

Containers communicate via virtual network interfaces bridged to the host. Docker creates a default bridge network where containers can reach each other by IP address. User-defined bridge networks additionally support DNS-based service discovery by container name.

## Port Mapping

The `-p` flag maps a host port to a container port, enabling external access to containerized services. Multiple containers can expose the same internal port as long as the host ports differ.
