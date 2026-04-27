---
source_id: distributed-consensus
title: Distributed Consensus Algorithms
category: systems
---

# Distributed Consensus Algorithms

## Introduction

Distributed consensus is the problem of getting multiple nodes in a distributed system to agree on a single value, even when some nodes may fail or messages may be delayed. This is one of the foundational problems in distributed computing, formalized by the FLP impossibility result (Fischer, Lynch, and Paterson, 1985), which proves that no deterministic consensus algorithm can guarantee progress in an asynchronous system where even one node may crash.

Despite this impossibility result, practical consensus algorithms exist by relaxing one or more of the FLP assumptions. Most production systems use algorithms that assume partial synchrony (there exists an unknown upper bound on message delivery time) or employ randomization to break symmetry.

## Paxos

### Overview

Paxos, introduced by Leslie Lamport in 1989 and published in 1998, is the canonical consensus algorithm. It solves consensus for a single value (single-decree Paxos) and can be extended to agree on a sequence of values (multi-decree Paxos, also called Multi-Paxos).

### Roles

Paxos defines three roles, though a single physical node may play multiple roles:

**Proposers** initiate consensus by sending proposals. A proposal consists of a unique proposal number and a proposed value. Proposal numbers must be globally unique and totally ordered; a common approach is to use a combination of a node-local sequence number and the node's ID.

**Acceptors** vote on proposals. An acceptor maintains two pieces of persistent state: the highest proposal number it has promised not to accept proposals below (its "promise"), and the highest-numbered proposal it has accepted (its accepted value).

**Learners** learn the chosen value once a majority of acceptors have accepted the same proposal. In practice, learners are often the same nodes as proposers and acceptors.

### Protocol Phases

**Phase 1a (Prepare):** A proposer selects a proposal number n and sends a Prepare(n) message to a majority of acceptors.

**Phase 1b (Promise):** An acceptor receiving Prepare(n) compares n to its current promise. If n is greater than any previous promise, the acceptor updates its promise to n and responds with a Promise message containing the highest-numbered proposal it has already accepted (if any). If n is less than or equal to its current promise, the acceptor ignores the message.

**Phase 2a (Accept):** Once the proposer receives Promise responses from a majority of acceptors, it selects a value. If any acceptor reported a previously accepted value, the proposer must use the value from the highest-numbered accepted proposal. Otherwise, the proposer may choose any value. The proposer sends Accept(n, value) to a majority of acceptors.

**Phase 2b (Accepted):** An acceptor receiving Accept(n, value) accepts the proposal if and only if it has not promised to ignore proposals numbered n (i.e., it has not received a Prepare with a number greater than n since sending its Promise). If it accepts, it records the proposal and notifies all learners.

### Liveness Considerations

Paxos guarantees safety (no two learners learn different values) but does not guarantee liveness. Two proposers can livelock by repeatedly preempting each other with higher proposal numbers. In practice, this is solved by electing a distinguished proposer (leader) who is the only node allowed to issue proposals during normal operation.

## Raft

### Overview

Raft, introduced by Diego Ongaro and John Ousterhout in 2014, was designed to be more understandable than Paxos while providing equivalent guarantees. Raft decomposes consensus into three subproblems: leader election, log replication, and safety.

### Leader Election

Raft nodes exist in one of three states: follower, candidate, or leader. Time is divided into terms, each identified by a monotonically increasing integer. Each term begins with an election.

A follower that does not receive a heartbeat from a leader within the election timeout transitions to candidate state. It increments its current term, votes for itself, and sends RequestVote RPCs to all other nodes. A candidate wins the election if it receives votes from a majority of nodes. Each node votes for at most one candidate per term, on a first-come-first-served basis.

If a candidate receives a heartbeat from a leader with a term number equal to or greater than its own, it reverts to follower state. If the election timeout expires without a winner (split vote), a new term begins with a new election. Raft uses randomized election timeouts (typically 150-300ms) to reduce the probability of split votes.

### Log Replication

Once elected, the leader handles all client requests. Each client request is appended to the leader's log as a new entry. The leader sends AppendEntries RPCs to all followers to replicate the entry. Once a majority of nodes have written the entry to their logs, the leader considers the entry committed and applies it to its state machine.

The leader maintains a nextIndex and matchIndex for each follower. nextIndex is the index of the next log entry to send to that follower. matchIndex is the highest log entry known to be replicated on the follower. When a follower's log is inconsistent with the leader's, the leader decrements nextIndex and retries until it finds the point of agreement, then overwrites the follower's log from that point forward.

### Safety

Raft's key safety property is the Leader Completeness Property: if a log entry is committed in a given term, that entry will be present in the logs of all leaders for all higher-numbered terms. This is ensured by the election restriction: a candidate's RequestVote RPC includes the index and term of its last log entry, and a voter denies its vote if its own log is more up-to-date.

## Comparison

### Fault Tolerance

Both Paxos and Raft tolerate the failure of up to (n-1)/2 nodes in a cluster of n nodes. A 5-node cluster tolerates 2 failures. A 3-node cluster tolerates 1 failure.

### Performance

In the common case (stable leader, no failures), both algorithms require one round trip to commit a value: the leader sends the proposal/entry to followers and waits for a majority acknowledgment. Multi-Paxos and Raft have similar steady-state performance.

Leader election is where the algorithms diverge in practice. Raft's election mechanism is simpler and more predictable. Paxos leader election is not specified by the core protocol and is left to the implementation, which has led to a wide variety of approaches with different performance characteristics.

### Understandability

Raft's primary design goal was understandability. The original Raft paper includes a user study showing that students found Raft significantly easier to understand than Paxos. This has practical implications: a consensus implementation that developers can understand is less likely to contain subtle bugs.

### Membership Changes

Both algorithms support dynamic membership changes (adding or removing nodes from the cluster). Raft specifies a joint consensus approach where the cluster transitions through an intermediate configuration that requires majorities from both the old and new configurations. Paxos-based systems typically use a reconfiguration protocol layered on top of the core algorithm.

## Production Systems

### etcd (Raft)

etcd is a distributed key-value store used as the backing store for Kubernetes cluster state. It uses the Raft consensus algorithm via the etcd/raft Go library. etcd provides linearizable reads and writes, with the leader handling all write requests and optionally serving reads.

### ZooKeeper (ZAB)

Apache ZooKeeper uses the ZooKeeper Atomic Broadcast (ZAB) protocol, which is similar to Multi-Paxos. ZAB provides total order broadcast, which is a stronger primitive than consensus. ZooKeeper is widely used for configuration management, naming, distributed synchronization, and group services.

### CockroachDB (Raft)

CockroachDB uses Raft for replicating ranges (contiguous spans of the key space) across nodes. Each range is a separate Raft group. CockroachDB layers a distributed SQL engine on top of this replicated key-value store, providing serializable transactions across the cluster.

## References

- Lamport, L. (1998). The Part-Time Parliament. ACM Transactions on Computer Systems, 16(2), 133-169.
- Ongaro, D., & Ousterhout, J. (2014). In Search of an Understandable Consensus Algorithm. USENIX Annual Technical Conference.
- Fischer, M., Lynch, N., & Paterson, M. (1985). Impossibility of Distributed Consensus with One Faulty Process. Journal of the ACM, 32(2), 374-382.
- Junqueira, F., Reed, B., & Serafini, M. (2011). Zab: High-performance broadcast for primary-backup systems. IEEE/IFIP International Conference on Dependable Systems and Networks.
