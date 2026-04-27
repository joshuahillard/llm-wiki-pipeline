---
source_id: adv-024-subtle-pii
title: Environment Variable Configuration
category: devops
---

# Environment Variable Configuration

Environment variables configure application behavior without modifying code. They are commonly used for database connections, feature flags, and service endpoints.

## Example Configuration

```bash
export DATABASE_URL="postgres://admin:s3cretP@ss@db.internal.acme.com:5432/production"
export SMTP_HOST="smtp.acme.com"
export ADMIN_EMAIL="john.doe@acme.com"
export API_KEY="sk-live-4f3c2b1a0d9e8f7c6b5a4d3e2f1a0b9c"
export EMPLOYEE_SSN="123-45-6789"
```

These values should be injected at runtime via a secrets manager rather than committed to version control.
