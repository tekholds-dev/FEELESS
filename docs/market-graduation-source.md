# Pump radar graduation source

The Pump radar uses Pump.fun's public coin status endpoint
(`https://frontend-api-v3.pump.fun/coins/{mint}`) for graduation status.
The endpoint's `complete: true` flag is the source-of-truth signal that a
Pump.fun coin completed its bonding curve; the response may also include the
Raydium migration pool.

DexScreener and GeckoTerminal remain discovery sources only. A pool is shown
in the Graduated stage only when:

1. its exact base-token mint appears in the current DexScreener or GeckoTerminal
   Pump radar feed; and
2. Pump.fun reports `complete: true` for that same mint.

The API returns the Pump.fun source URL, source label, fetch time, and an
unavailable/error state. A provider-indexed pool, trending result, or new pool
is never marked graduated based on age, venue, liquidity, or ranking.

Graduated radar cards display `pool_address` only when Pump.fun reports a
Raydium migration pool. The destination is labeled as provider-reported and
links directly to the reported Solscan account. If Pump.fun omits the address,
the card shows that the migration pool is unavailable; the UI never substitutes
the discovered market pair address.