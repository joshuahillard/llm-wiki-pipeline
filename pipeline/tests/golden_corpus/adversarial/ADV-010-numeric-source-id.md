---
source_id: 12345
title: Numeric Source ID
---

# Numeric Source ID Test

The source_id is an integer (12345) instead of a string. YAML will parse this as an int. parse_identity.py converts to string via str(), so "12345" matches ^[a-zA-Z0-9-]{1,36}$ and should pass validation. This is an edge case — not an error.
