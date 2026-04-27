---
source_id: sql-indexing-basics
title: SQL Indexing Basics
category: databases
---

# SQL Indexing Basics

## Overview

Indexes speed up reads by giving the database an alternate structure for locating rows. They improve query performance for selective predicates, but they also increase write cost and storage usage.

## Example Query

```sql
SELECT id, email
FROM users
WHERE email = 'user@example.com';

## Tradeoffs

Indexes are most effective when queries are selective and well aligned with the indexed columns. Over-indexing can slow inserts and updates, so teams should review unused indexes periodically.

## References

- [PostgreSQL Indexes](https://www.postgresql.org/docs/current/indexes.html)
