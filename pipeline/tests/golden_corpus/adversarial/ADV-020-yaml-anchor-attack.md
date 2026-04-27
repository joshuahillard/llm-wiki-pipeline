---
source_id: &anchor adv-020-anchor
title: *anchor
category: security
extra_a: &bomb "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
extra_b: [*bomb, *bomb, *bomb, *bomb, *bomb, *bomb, *bomb, *bomb]
extra_c: [*bomb, *bomb, *bomb, *bomb, *bomb, *bomb, *bomb, *bomb]
---

# YAML Anchor Attack Test

This article tests whether the parser safely handles YAML anchors and aliases. The frontmatter uses anchors to alias the source_id value into the title field, and includes repeated references to a large string value.

Safe YAML loaders accept anchors but should not allow exponential expansion attacks.
