---
source_id: my_article.v2
title: Source ID with Underscores and Dots
---

# Special Character Source ID

The source_id "my_article.v2" contains underscores and dots, which are NOT in the allowed character set ^[a-zA-Z0-9-]{1,36}$. This should be rejected by parse_identity.py even though underscores and dots are common in filenames.
