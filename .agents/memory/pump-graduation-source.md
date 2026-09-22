---
name: Pump graduation source
description: The authoritative source and matching rule for Pump radar graduation status
---

Pump radar graduation is established only by Pump.fun's public coin status
response reporting `complete: true` for the exact base-token mint. DexScreener
and GeckoTerminal provide the candidate pool universe, not graduation proof.

**Why:** Market indexes expose pool observations but do not establish that a
Pump.fun bonding curve completed. Treating their ranking, age, venue, or
liquidity as graduation would mislabel ordinary discovery results.

**How to apply:** Keep the Pump.fun status source separate from discovery
feeds, preserve source/fetch-time/error states in the UI, and limit request
concurrency because the public endpoint can return HTTP 429 under bursts.