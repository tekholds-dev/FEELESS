---
name: Market provider hierarchy
description: Durable source-selection rule for Solana launchpad radar and broader market data.
---

Pump.fun is the primary source only for the Pump-scoped Solana radar because it directly establishes launchpad coin coverage and completion status. DexScreener and GeckoTerminal remain the broader discovery/pool/candle fallbacks.

**Why:** Pool indexes can show a market without proving launchpad provenance, while Pump.fun can establish its own coin lifecycle but does not supply every pool, liquidity, or candle field needed by the terminal.

**How to apply:** Keep the actual provider, primary provider, fetched timestamp, stale/error state, and per-stage coverage visible in every market response. Treat all sources as polling snapshots unless a real stream is connected. Never derive USD liquidity or token price from virtual reserves or market cap.