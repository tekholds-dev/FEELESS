---
name: Collection count contract
description: Mobile collection checks must track the catalog contract when new Cat variants are added.
---

The Feeless Cat collection is an expanding catalog, so browser checks must use the current documented filter counts or derive them from the rendered filter state rather than assuming the original collection size.

**Why:** A valid Spots-variant expansion caused the post-merge mobile gate to fail because it still expected the former 25-card catalog.

**How to apply:** When adding or removing collection variants, update the collection tests and the real-browser mobile check in the same change, then rerun post-merge setup.