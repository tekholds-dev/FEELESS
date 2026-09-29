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

## Pump Pulse (pink bolt)
- Pump Pulse = the pink bolt beside a coin on Pump Radar and Trenches cards, plus a banner in that coin's chat, shown while the coin has hot 5-minute flow.
- Rule (`backend/market.py` `pulse_stats`): 20+ trades, $5K+ volume, price up 2%+ in 5m, 55–97% buys, average trade $20+ (filters micro-buy volume bots). Levels 1/2/3 at $5K/$20K/$50K 5m volume. Creators marked flagged/risky never get a bolt.
- Data: `GET /api/market/pulse?mints=…` batches DexScreener's 5m stats (up to 60 mints, cached 20s). The browser shares one poller for every card on screen (`frontend/src/lib/pumpPulse.js`), refreshed every 15s, so bolts and banners appear and disappear live.
- Pump.fun callouts are shelved; the offline notice is hidden.

## PumpPortal (background only)
- `backend/pump_network.py` keeps a free PumpPortal launch/migration stream so brand-new bonding-curve coins open before DexScreener indexes them (`/api/market/pair` fallback). The earlier Pump Pulse / Pump Flow panels were removed.
- The paid trade stream is off: `PUMPPORTAL_API_KEY` is commented out in `backend/.env`. Uncomment it and fund the PumpPortal wallet with at least 0.02 SOL to re-enable it.
