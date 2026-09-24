---
name: New coin source policy
description: Broad new-coin discovery uses a multi-network pool index first and requires provider image metadata.
---

Broad new-coin views should prefer the provider with the widest supported-network pool discovery, retain a clearly labeled fallback when it is unavailable, and omit entries with no provider image metadata.

**Why:** Boost-only discovery is incomplete for new coins, while image-less entries create inconsistent cards and neutral placeholders across the site.

**How to apply:** Keep the primary/fallback source visible in feed metadata, apply the image requirement before ranking or rendering new coins, and preserve launchpad-specific provenance rules for scoped feeds.

Primary-provider 429 responses should use a short URL-scoped cooldown before retrying, while fallback rows for an all-network request must be limited to the chain IDs supported by the selector.

**Why:** Repeating throttled requests reduces coverage and can return networks that the UI cannot open in its current market context.

**How to apply:** Preserve stale successful snapshots when available, otherwise use the labeled fallback during cooldown, and retry the primary provider after the cooldown expires.