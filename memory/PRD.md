# FEELESS — product and implementation record

## Original product goal
Upgrade the FEELESS landing page into an advanced ecosystem experience with a 3D WebGL globe. Nodes open an ecosystem panel with persistent polling chat, CA token previews, live coins and platform links. `/terminal` is a complete black/charcoal + neon-mint degen dashboard. Wallet-ready architecture initially requested.

## Current user request
“now connect and trace all coins new coins etc all buttons working, bring the terminal to life, white paper and the coins all coins … logo suppose to be this”. Work was paused at user's request over budget, then explicitly resumed after credits recharged. Latest direction: “globe looks good but needs pump and other popular launch pads clean up and advance this then make terminal look like this but meta for degens”. Use supplied F logo and dashboard reference. Do not promise exhaustive coin coverage. Signing and in-app trading out of scope.

## Architecture
- React 19, react-router, Tailwind, Outfit/JetBrains Mono, custom terminal CSS, existing shadcn Dialog/Toaster.
- Globe: react-globe.gl / Three.js, responsive ResizeObserver and launchpad labels/nodes.
- Charts: lightweight-charts v5, real GeckoTerminal OHLCV; no simulated candles.
- FastAPI, Motor/MongoDB via original MONGO_URL and DB_NAME; `/api` prefix for all backend endpoints.
- Backend `/app/backend/market.py` uses Mongo-persisted provider cache, TTL, per-provider request limits, per-key collapse, stale fallbacks, timestamps and explicit errors.
- Provider URL configuration in `/app/backend/market.env`; original backend .env untouched. Frontend API origin remains REACT_APP_BACKEND_URL; public chart/trade URLs in frontend .env.
- DexScreener: search and pair snapshots via backend. GeckoTerminal: trending/new pools and OHLCV via backend. Public/keyless.
- WalletProvider: real injected Phantom Solana / EIP-1193 account connection only; never signs or sends transactions; wallet state not used as chat auth.

## Current implementation — 2026-09-19
- Replaced fake ticker, random candles, invented feed, fake online counts, fake FEE price/verified claims and dead controls.
- Terminal routes: home, trade (research + outbound trade links), pump radar, discover, new pools, launchpads, watchlist, chat, top movers, browser alerts, learn, roadmap, draft whitepaper, settings.
- Live discovery: provider-limited feeds, chain/DEX-venue/liquidity filters, search incl. contracts, ranking modes, pagination, selectable pools, source/stale metadata.
- Selected token chart: real candlesticks/volume, interval controls, fresh pair quote, copy contract, saved watchlist, relevant external links.
- Watchlist and alerts persist locally. Maximum five active price alerts checked every 60s while terminal is mounted, triggered on fresh quotes only. No email/push background delivery.
- Four public chat channels persisted server-side; bounded latest history and send/poll error states, CA preview cards.
- Launchpads: Pump.fun, LetsBONK, Raydium LaunchLab, Meteora, Moonit, Four.meme. Globe positions are visual layout coordinates, not physical headquarters.
- Supplied logo downloaded, transparent whitespace cropped (art unchanged) to `/frontend/public/assets/feeless-logo.png`.
- Whitepaper is a clearly marked draft, markdown download, no invented tokenomics or zero-network-fee promises.

## Key files
- `frontend/src/pages/Terminal.jsx`, `Landing.jsx`
- `frontend/src/components/terminal/*` modular terminal widgets and document pages
- `frontend/src/styles/terminal.css`
- `frontend/src/hooks/useMarket.js`, `useWallet.jsx`
- `frontend/src/lib/dexscreener.js`, `launchpads.js`, `ecosystems.js`
- `backend/server.py`, `backend/market.py`, `backend/market.env`

## API
- GET /api/market/feed?kind=trending|new&chain=solana|all|…&page=1..10
- GET /api/market/search?q=…
- GET /api/market/pair/{chain}/{pair}
- GET /api/market/candles/{chain}/{pool}?interval=5m|15m|1h|4h|1d
- GET/POST /api/chat/{room}, GET /api/chat/{room}/online (recent unique posters, not real online presence)

## 2026-09-19 — Degen Command Terminal expansion
User explicitly approved continuing and supplied FEE, RFEE, FEECAT Solana contracts, requested all-in-app execution and enhanced restrained mint motion, floating/glowing logo, mouse glow. Current exact supplied mints: FEE `49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump`; RFEE `2vZjg2w58k4urtdNWPnNHizuSxesLCozQ5Pq9xxqNray`; FEECAT `AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump`.

- Default center asset is now exclusively FEE unless the user selects a pool. NO random trending default. Exact-contract DexScreener asset resolver returns awaiting-market for all three supplied contracts at validation time; no candles/prices fabricated. FEE mint verified through Solana RPC: decimals6, raw supply1000000000000000 (1B tokens), mint and freeze authorities null. No audit or on-chain allocation claim.
- Approved policy: 70% Liquidity & Ecosystem; 15% Marketing & Growth; 10% Team & Development; 5% Community & Airdrops. No private sale / fair launch. Interactive tokenomics with explicit policy vs actual allocation distinction.
- WorkspaceProvider persists ecosystem context globally; globe node/launchpad/terminal controls feed same scope. Six chat rooms per ecosystem. API-backed rich CA cards resolve on SERVER (client data not trusted), link charts/watch/alerts/trade. Exact SPL addresses are case-sensitive.
- `backend/intelligence.py`: actual provider observations, same-source deltas, price observation history, new pair observations, contract scans and chat CA mentions stored in Mongo. Alpha Tape, radar, velocity/acceleration/expansion ranks, live local watchlist histories, real participation rankings. No made-up whales, holders, ATH, migrations or liquidity transactions.
- `backend/trading.py`: official Jupiter Swap V2 order/execute, real key in backend `.env`, public mainnet Solana RPC configured. Amount precision validation, token metadata via RPC, expiry, simulation, Phantom approval, unchanged-message/signature validation, single-submit lock and RPC confirmation. Supports Solana only; other networks intelligence-only. No agent-run real swap.
- Verified actual SOL→USDC read-only Jupiter order returns metis route/output. FEE route currently returns provider error. Supply RPC works. RFEE utility deliberately not invented.
- FeeBackCenter/FeeCatCenter: real policy example calculator (60 USD illustration), separate USD-equivalent vs token quantity, planned architecture explorer, no imaginary payouts. 100% eligible tracked USD fees intended to return in FEECAT. Actual eligibility valuation/distribution infrastructure NOT activated. Network/DEX fees still apply.
- Conditional browser alerts: price, percent, liquidity, rolling24h volume, market cap and supported ecosystem tape events. Unsupported ATH/wallet/listing controls explicitly unavailable. Evaluate only while terminal is open.
- `backend/whitepaper.py`: single shared source with25 chapters, registry, 70/15/10/5 model, fee return example, risk disclosures, Q2 2027 public platform launch target. Actual PDF generated by ReportLab; backend serves view and attachment variants. Download validated as PDF-1.4,732KB; source webJSON25 chapters. Saved sample `/app/test_reports/FEELESS-Whitepaper-v1.0.pdf`.
- Added command screens and CSS in `frontend/src/components/command/*`, `styles/command.css`. New fee/feeback/feecat/movers/leaderboard routes, context transition, hover-floating logo, mouse glow, subtle orbit/radar effects with reduced-motion support.

## Validation status — complete for implemented scope
- `/app/test_reports/iteration_2.json`: testing agent validated core routes, FEE default, persistent context, globe transfer, two-session chat/CA cards, watchlists/alerts, responsive core layouts at320/768/1024/1440/1920. Test-generated chat artifacts removed.
- Final backend regression: **26 passed,0 failed,0 skipped**, report `/app/test_reports/pytest/final_results.xml`.
- All reported frontend findings resolved and self-tested: native alert option labels remove invalid DOM nesting; conditional alert creation/deletion verified. PDF popup uncertainty eliminated with in-app PDF.js reader (`components/command/PdfReader.jsx`), locally hosted worker/fonts, actual canvas page rendering, pagination, zoom and real download. Browser pixel check confirmed nonblank1013x1432 PDF page; next/previous/110%zoom/download/close passed.
- `pypdf` verifies actual PDF content; normalized PDF line wrapping so semantic text assertions work. Same25-chapter source used for web and ReportLab PDF. PDF.js5.4.624 chosen for compatible Node20 runtime.
- Landing and terminal are lazy route chunks. Final production build passes, with only existing third-party missing-source-map warnings.
- Prior chart duplicate-timestamp and invalid browser-locale regressions fixed by dedupe, explicit en-US locale and chart error boundary.
- Final handoff report: `/app/test_reports/final_verification.json`. Real mainnet wallet signature/broadcast intentionally NOT performed; user-wallet verification remains pending.

## Remaining priorities
- P0: No unresolved bugs from executed tests. Preserve no-fabricated-data rule and no agent-submitted mainnet transactions.
- P1: User verification of command experience and installed Phantom signing on a supported, funded route. Publish Fee-Back eligibility, valuation timestamp/reference-price, settlement, rounding and distribution rules before implementing payouts. Supplied assets await indexed provider markets; do not substitute another token.
- P2: Publish Fee-Back eligibility/source/valuation/distribution rules and implement audited settlement; broader on-chain/indexer coverage, independently sourced risk data, authenticated moderation, additional-chain execution. User-wallet/mainnet signing requires explicit user verification, not agent use of funds.

## Known limits
Provider rate limits and incomplete token coverage; new pools are not every launch. LetsBONK origin cannot be inferred from Raydium LaunchLab pools; no venue match is fabricated. Watchlists/settings/alerts are browser-local. Chat identities unauthenticated. Supplied assets currently lack indexed DexScreener markets. In-app Solana execution integration implemented but actual wallet signature/broadcast NOT tested with real funds. Fee-Back payouts and eligibility remain PLANNED, not MOCKED. Unsupported market event types explicitly unavailable. Whitepaper is authored from current implemented architecture and user-approved policy, not externally audited.

## Recommended enhancement
Independently sourced contract-risk signals displayed alongside simulation before wallet approval. Requires a verified risk-data integration rather than inferred safety badges.