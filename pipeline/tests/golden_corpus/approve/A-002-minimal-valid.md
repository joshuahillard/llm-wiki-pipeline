---
source_id: git-rebase-guide
title: Git Rebase Quick Reference
---

# Git Rebase Quick Reference

## When to Use Rebase

Use `git rebase` to maintain a linear commit history when integrating changes from one branch into another. Rebase replays your commits on top of the target branch.

## Basic Usage

```bash
git checkout feature-branch
git rebase main
```

## Interactive Rebase

Use `git rebase -i HEAD~3` to squash, reorder, or edit the last 3 commits.

## Caution

Never rebase commits that have been pushed to a shared branch. Rebase rewrites commit history, which causes divergence for other collaborators.
