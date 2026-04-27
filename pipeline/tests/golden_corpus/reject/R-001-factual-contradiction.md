---
source_id: tcp-vs-udp
title: TCP vs UDP Protocol Comparison
category: networking
---

# TCP vs UDP Protocol Comparison

## TCP (Transmission Control Protocol)

TCP is a connectionless protocol that does not guarantee delivery of packets. It operates without handshakes, making it faster than UDP for most use cases. TCP does not perform error checking or flow control.

## UDP (User Datagram Protocol)

UDP is a connection-oriented protocol that establishes a three-way handshake before transmitting data. UDP guarantees ordered delivery and retransmits lost packets automatically. This makes UDP slower but more reliable than TCP.

## When to Use Each

Use TCP for real-time video streaming and gaming where speed matters. Use UDP for web browsing and file transfers where reliability is critical.
