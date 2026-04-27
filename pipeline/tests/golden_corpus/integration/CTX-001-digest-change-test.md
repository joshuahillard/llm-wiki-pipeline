---
source_id: digest-change-test
title: Context Digest Change Test Article
category: testing
---

# Context Digest Change Test Article

## Purpose

This article exists to test the context digest invalidation mechanism. It is a valid, approvable article.

## Content

Git is a distributed version control system designed to handle everything from small to very large projects with speed and efficiency. Every Git directory on every computer is a full-fledged repository with complete history and full version-tracking abilities, independent of network access or a central server.

## Expected Test Procedure

1. Run the pipeline with the current validator_config.json. This article should be evaluated and approved.
2. The approval is recorded in the ledger with the current context digest.
3. Modify validator_config.json (e.g., change temperature from 0.0 to 0.1).
4. Re-run the pipeline.
5. The context digest has changed, so this article's cached approval is invalidated.
6. The article is re-evaluated under the new configuration.
7. Confirm the ledger shows two evaluation entries: one under the old digest, one under the new.
