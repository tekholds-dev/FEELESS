---
name: Fee asset provider fallback
description: Exact fee coin metadata can come from GeckoTerminal when DexScreener has no token-pair result.
---

Fee asset resolution should match the owner-provided CA first, use DexScreener when available, and fall back to GeckoTerminal token metadata plus its top-pool address for price and logo data. Never fabricate an unavailable asset price.

**Why:** DexScreener may return no exact pair or rate-limit while GeckoTerminal still exposes the CA's current price, logo, and top pool.

**How to apply:** Keep the fallback provider-labeled, attach its image URL to both the asset and pair, and leave the asset in an explicit awaiting-market state when no provider supplies a price.