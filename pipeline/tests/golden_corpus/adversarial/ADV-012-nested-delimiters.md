---
source_id: nested-delimiter-test
title: Article With YAML Delimiters in Body
---

# Nested Delimiters

This article is valid. The frontmatter is correct and complete.

## Example Code

Here is an example of a YAML file:

---
apiVersion: v1
kind: ConfigMap
---

The `---` characters above should NOT be interpreted as frontmatter delimiters. parse_identity.py only reads the FIRST `---` block (lines 1 through the first closing `---`). Everything after is body content.
