---
name: New coin source policy
description: Broad new-coin discovery uses a multi-network pool index first and requires provider image metadata.
---

Broad new-coin views should prefer the provider with the widest supported-network pool discovery, retain a clearly labeled fallback when it is unavailable, and omit entries with no provider image metadata.

**Why:** Boost-only discovery is incomplete for new coins, while image-less entries create inconsistent cards and neutral placeholders across the site.

**How to apply:** Keep the primary/fallback source visible in feed metadata, apply the image requirement before ranking or rendering new coins, and preserve launchpad-specific provenance rules for scoped feeds.