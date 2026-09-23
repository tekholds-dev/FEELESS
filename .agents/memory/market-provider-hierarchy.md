---
name: Market provider hierarchy
description: Durable source-selection rule for Solana launchpad radar and broader market data.
---

Pump.fun is the primary source only for the Pump-scoped Solana radar because it directly establishes launchpad coin coverage and completion status. DexScreener and GeckoTerminal remain the broader discovery/pool/candle fallbacks.

**Why:** Pool indexes can show a market without proving launchpad provenance, while Pump.fun can establish its own coin lifecycle but does not supply every pool, liquidity, or candle field needed by the terminal.

**How to apply:** Keep the actual provider, primary provider, fetched timestamp, stale/error state, and per-stage coverage visible in every market response. Treat all sources as polling snapshots unless a real stream is connected. Never derive USD liquidity or token price from virtual reserves or market cap.

Provider screeners are a ranking layer over reported snapshots, not a safety, profitability, or launchpad-verification layer. Keep the selected mode and its disclosure visible, and treat missing provider fields as unavailable rather than inferred.

**Why:** A useful next-best-coin view needs deterministic ordering from available market observations, but RPC and public indexes cannot establish that a token is safe or will perform well.

**How to apply:** Use observed liquidity, volume, transaction counts, age, and reported price movement only; label the result as a provider score and preserve the source/fallback lineage.

Fallback pool snapshots may expose FDV while leaving market cap null; keep those fields distinct and show market cap as unavailable rather than relabelling FDV.

**Why:** Public provider fallbacks can return usable liquidity and FDV during throttling without establishing a circulating-supply market cap.

**How to apply:** Prefer the explicit marketCap field in radar summaries and cards. Display FDV only with an FDV label in views that include it.