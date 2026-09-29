# Checkpoint — 2026-09-29

Codex's `recovery/codex-sept28` work (41ecf2a…f7a4271) is merged into `main`, plus the cleanup pass below.

Done:
- Pump user callouts live inside the FEELESS coin chat (Bulls / Trenches / Bears) with a pink PUMP pill: the 3 callouts made just before you open the coin, then every 3rd new Pump callout. FEELESS posts stay first-class; Pump rows follow the chat's "All" and "Calls only" filters. Entry time is per coin, so switching tabs keeps the cadence.
- Shared reputation lookups: bolt, badge and card on the same coin share one in-flight request (fixes bolts silently missing).
- Swap page crash fixed (`useMemo` was not imported in SwapWorkspace).
- Liquidity depth: liquidity at or above market cap now floors at 15 (dead-pool tell).
- Tests updated for the MC-first chart default. 148/148 frontend tests pass; preview API 22/22; production build clean.
- FeeCat engine verified cycling after restarting the 5088 service on current code. Presets fill the rule fields and apply when "Save brain" is pressed.

External blocker (unchanged):
- Pump's `GET /coin-activity/{mint}?includeCallouts=true` needs authorization. Set `PUMP_CALLOUT_TOKEN` server-side with legitimately issued access. Until then, coin chats show "Pump callouts are offline for this coin right now." Never present FEELESS calls as Pump users' calls.

Local dev note: the backend runs as four processes — `server` (5001), `reputation_service` (5077), `feecat_service` (5088), `candles_service` (5099). Restart all of them after pulling backend changes, or the preview runs stale code.

## FEELESS Pump network (PumpPortal)
- `backend/pump_network.py`: one shared PumpPortal websocket for the whole app, started with the main server (5001). Free stream: every pump.fun launch + migration. Paid stream (`PUMPPORTAL_API_KEY`): live trades only for coins someone is viewing (max 12, dropped 90s after the last viewer), capped per day by `PUMPPORTAL_DAILY_MESSAGE_CAP` (default 20,000 ≈ 0.02 SOL). The key never reaches the browser.
- API: `GET /api/pump/pulse` (launches, migrations, launches/min, SOL price) and `GET /api/pump/coin/{mint}/flow` (trade tape, 5m pressure, traders, whales, curve progress).
- Fresh launches open even before DexScreener indexes them: `/api/market/pair/solana/{curve}` falls back to the streamed launch (price = MC / fixed 1B supply).
- UI: Pump Pulse on Pump Radar (live launches with "Serious only" filter for dust/copycat launches, migrations, launches-per-minute sparkline); Pump Flow at the top of the trench tools column (buy pressure, net SOL, traders, whales, bonding curve, live tape).
- Status 2026-09-29: key accepted, but the PumpPortal wallet needs ≥ 0.02 SOL before trade data flows. The server re-checks every 2 minutes, so no restart is needed after funding.
