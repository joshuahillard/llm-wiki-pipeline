---
source_id: git-branching-strategies
title: Git Branching Strategies
category: development-workflow
last_reviewed: 2026-03-01
---

# Git Branching Strategies

## Overview

A branching strategy defines how a team organizes concurrent work, integrates changes, and ships releases using Git. The choice of strategy affects merge frequency, conflict rate, CI pipeline design, and release cadence.

## Feature Branch Workflow

Each unit of work gets its own branch created from `main`. The developer works on the feature branch, pushes to the remote, and opens a pull request for review. After approval, the branch is merged (usually with a squash or merge commit) and deleted.

Advantages: isolation between features, clear review boundary, easy to revert a single feature by reverting its merge commit.

Disadvantages: long-lived feature branches diverge from `main` and accumulate merge conflicts. Teams mitigate this by keeping branches short-lived (1–3 days) and rebasing frequently.

## Trunk-Based Development

All developers commit directly to `main` (or to very short-lived branches that merge within hours). Feature flags gate incomplete work so that `main` is always deployable.

Advantages: continuous integration in the literal sense — integration happens constantly, not in batches. Merge conflicts are small and frequent rather than large and painful.

Disadvantages: requires strong CI discipline (fast tests, reliable builds) and feature flag infrastructure. Without these, broken commits on `main` block the entire team.

## Release Branch Workflow

When a release is ready, a branch is cut from `main` (e.g., `release/2.3`). Only bug fixes are cherry-picked into the release branch. New feature work continues on `main`.

This model is common in projects that maintain multiple supported versions simultaneously, such as open-source libraries or enterprise software with contractual support windows.

## Choosing a Strategy

The right strategy depends on team size, release cadence, and CI maturity. Small teams with continuous deployment often favor trunk-based development. Larger teams with scheduled releases often use feature branches with a release branch cut at the end of each cycle.

## References

- [Git Documentation — Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell)
- [Trunk Based Development](https://trunkbaseddevelopment.com/)
