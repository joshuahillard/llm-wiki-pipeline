---
source_id: database-setup
title: Production Database Setup Guide
category: infrastructure
---

# Production Database Setup Guide

<!-- GOLDEN CORPUS FIXTURE: All credentials below are synthetic test data. -->
<!-- AWS keys use the documented AWS example format (AKIAIOSFODNN7EXAMPLE). -->
<!-- No real secrets are present in this file. -->

## Connection Configuration

Connect to the production PostgreSQL instance using:

```
Host: db-prod-01.internal.company.com
Port: 5432
Database: production_app
Username: admin_user
Password: Sup3r$ecretP@ssw0rd!2026
```

## Backup Configuration

The backup service uses the following AWS credentials:

```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## Maintenance Windows

Production database maintenance occurs every Sunday at 02:00 UTC.
