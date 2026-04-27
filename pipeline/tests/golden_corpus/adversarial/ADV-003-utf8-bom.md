---
source_id: bom-test-article
title: Article With UTF-8 BOM
---

# Article With UTF-8 BOM

This file starts with a UTF-8 Byte Order Mark (EF BB BF). The parser must handle this transparently via utf-8-sig encoding. The BOM should not interfere with frontmatter delimiter detection.

## Content

This is standard article content after the BOM-prefixed frontmatter.
