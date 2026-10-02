# FEELESS: what it needs and how we keep it clean

## Priority #1: low usage, clean build, no lag, no bugs
Every change has to meet all of these before it ships:

1. **Gates must pass before a push.** Run these in order:
   - Frontend tests: `cd frontend && CI=true yarn test --watchAll=false`
   - Build: `CI=false npx craco build`
   - Backend tests: `PYTHONPATH=backend:. python -m pytest backend/tests -q`
   - Page scan: every page renders, with no panel or page crashes.
2. **Speed budget.** A page should stay at 55fps or better on a mid laptop, and no API route should have a p95 above 1.2s. **HQ › Lag catcher** reports both from real browsers. Anything on its fix list gets fixed before new features.
3. **Animation rules.**
   - Animate only `transform` and `opacity`.
   - Never animate a CSS custom property such as `--ang`, because it repaints every frame.
   - Never use `backdrop-filter` over an animated background.
   - Don't put `filter: blur()` on moving layers.
   - Respect `prefers-reduced-motion`.
   - Heavy effects switch off under `body.fx-lite`.
4. **Network rules.**
   - No request waterfalls: use `asyncio.gather` or parallel fetches.
   - Use one shared poller per data type (`pumpPulse`, `snipersOut`, `RepMark` batch).
   - Load hot JSON through `_cached_json` / `_json_load`.
   - Debounce typing to 300ms or less.
5. **Crash-proofing.**
   - Every page and panel sits inside a `PanelBoundary`, so one bad API shape costs one card, not the page.
   - Crashes auto-report to Bugs.
   - `test_routes_unique.py` blocks duplicate API paths.
6. **Usage (saving credits).** Grep before reading, read only what's needed, batch commands, and keep reports short. Add new mechanics to pure, tested modules such as `investigate.py`, `reserve_pool.py` and `perf.py`, so fixes are small.

## To go live: what the owner must do
| Step | Where | Status check |
|---|---|---|
| Helius RPC key → `SOLANA_RPC_URL` | `backend/.env` | HQ › Launch & setup › Hook-up steps |
| `JUPITER_API_KEY` | `backend/.env` | same |
| `PUBLIC_SITE_URL` (coin metadata host) | `backend/.env` | same |
| `FEELESS_ADMIN_WALLETS` (hardware or multisig) | `backend/.env` | same |
| Fee accounts (SOL + USDC) for the trade fee | HQ › Trading & fees | Self-test goes green |
| Treasury route / fee claimer (Squads multisig) | HQ › Treasury | Hook-up steps |
| **Launch config**: pick a preset, check the readiness box, sign once (about 0.01 SOL) | HQ › Launch & setup | Box reads "✓ Valid on Meteora" with no ⚠ warnings |
| `ALLOWED_ORIGINS=https://your-domain` | `backend/.env` | Hook-up steps |
| Restart the backend after `.env` edits | `bash scripts/start-backend.sh` | |

### Launch presets (Meteora DBC)
All presets use:
- a 99% launch fee that decays exponentially (block-0 snipers lose money);
- dynamic (volatility) fees;
- a fixed supply, with mint and freeze authority revoked;
- 100% of graduated LP locked forever.

| Preset | Open → graduate | Snipe tax | Normal fee | Use for |
|---|---|---|---|---|
| 🛡 Anti-snipe max | 30 → 500 SOL | 99% → 1% over 3 min | 1% | Default |
| 🚀 Pump classic | 28 → 420 SOL | 90% over 1 min | 1% | Fast pump.fun-style runs |
| 🏦 Deep reserve | 100 → 1500 SOL | 99% over 5 min | 0.5% | Slower candles, deep pool |
| 💵 Stable (USDC) | $5K → $69K | 99% over 3 min | 1% | No SOL price swings |
| 🔥 Buy & burn | 30 → 500 SOL | 99% over 3 min | 1.5% | FEELESS share goes to a buy-back wallet |

Meteora's own validator checks the curve before you can sign. The warnings flag weak anti-snipe settings, a normal fee above 2%, and any withdrawable LP.

## Engines and how they link
- **Trading.** The Jupiter Swap API is primary; the FEELESS fee is its own transfer in the transaction. Ultra is only used when opted in. The wallet signs, the server verifies the signed message and broadcasts. A confirmed trade then earns **season points**: fees paid weigh most, capped at 50 per trade, counted once per signature.
- **Reputation.**
  - `investigate.py` produces cited evidence and a verdict.
  - The **same verdict** appears on case files, profile rails, chat rep marks (a red ⚠ when suspect or high, opening the case file on click), and in the rug shield / trade tickets ("Creator case file: …").
  - FEELESS wallets are never suspects.
- **Wallet watch.** One tap from any case file or profile. Alerts arrive on the wallet's next buys and sells, and dumps by suspect wallets are called out. The limit is 25 per user.
- **After the sell.** Your recent sells compared with the price now ("sold a runner" / "good exit"). This is FeeCat's learning loop applied to you.
- **Badges → money.**
  - Season tiers earn a share of the season **reserve wallet**.
  - **Badge pools**: a pool is any wallet you choose plus the % of it that forms the pot. In the badge × pool matrix, each badge gets its own **% of each pool's pot**, split equally between that badge's holders. A pool's shares can't pass 100%, and unassigned % stays in the wallet.
  - The pool wallet always signs its own payout. The server records only SOL transfers verified on-chain, and never the same transaction twice.
- **Networks.**
  - DexScreener boosts are the first source.
  - Small chains (Cronos, zkSync, Zora…) are topped up from GeckoTerminal trending/new pools, so no network loads empty.
  - Chain logos come from DexScreener, which carries the current CRO mark.
- **Treasury.** HQ › Treasury shows every wallet holding FEELESS money: the fee accounts (wSOL / USDC), the admin wallet, season reserves and badge pools.
  - **Split now** sends fees to the split-plan destinations. You sign from the wallet that owns the fee account.
  - The server re-reads each transaction on-chain and records only what actually moved.
  - Nothing splits automatically, because that would need a server-held key.
- **What's launchable** (HQ › Launch & setup):
  - **Launch config:** a one-time on-chain template.
  - **FEELESS coins:** launched on the Launch page. The config's terms apply and the page's planning fields lock.
  - **Pump.fun coins:** launched from the same page.
  - **Pools for existing tokens:** created in the Pools tab.
  - Airdrops and badge payouts.
- **Coin verification.** A coin earns a green ✓ on its logo, site-wide, by passing all 5 safety gates and scoring 75+ out of 100 on 10 cited checks:
  - **Gates:** mint and freeze authority revoked, creator not flagged, 24h+ of trading, $25K+ liquidity.
  - **Checks:** locked LP, holder spread, insider share, dev bag, socials, real volume, two-sided flow, 72h+ age.
  - Official or reviewed coins get a gold ✦ granted in HQ › Verify coins. A revoke always wins.
  - Checks re-run every 6h. Case files and the coin passport show the same report.
- **Fee's setup memory.** Fee files every closed trade under its setup buckets (1h move, flow, depth, age, 5m heat, market-cap band, lane, fair value gap).
  - Setups with a proven edge size her up, to at most 1.5×. Setups that keep losing size her down, or veto the entry outright after 6+ trades at ≤20% wins and −8% or worse on average.
  - HQ › Fee 🐱 shows her playbook, her vetoes and her exit tuning.
- **Lag catcher.** Browsers report API latency, long tasks and FPS once a minute. A device that lags switches itself to lite effects. The owner can force lite effects site-wide.

## Open items (not built yet)
- Circle house-wallet trading: needs the owner's per-trade and daily caps.
- Buy & burn executor: claimed fees are currently bought and burned by hand from Treasury.
- Moving to a database plus multiple workers, for scale beyond one box.
