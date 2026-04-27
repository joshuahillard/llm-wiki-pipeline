---
source_id: this-source-id-is-way-too-long-and-exceeds-the-thirty-six-character-limit
title: Oversized Source ID Test
---

# Oversized Source ID

The source_id in this file's frontmatter is 73 characters, far exceeding the ^[a-zA-Z0-9-]{1,36}$ restricted identifier format. parse_identity.py should reject this with a structured error before the file reaches the LLM.
