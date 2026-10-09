# FEELESS degen playbook — the model and mindset

For the next Claude working on Fuse. Read this before you touch the engine, the real card or any list.
CLAUDE.md has the rules. This file covers how to think about them.

## The owner, in one paragraph
The owner runs a real-money Fuse card (Prime Blaze, tpl `degen`) on 5-minute rounds and trenches by hand. They talk in
degen shorthand ("send it", "trench cat", "seats not filling", "do all") and want things shipped, not debated. They love
visual meters, one-tap actions, live numbers and the evidence behind a call. They hate dead UI, extra clicks, emoji
stand-ins where a real icon belongs, and lectures. They make the trading decisions. Your job is to make the tools honest,
fast and readable, and to say plainly what the records show.

## Where the money is (2026-10-08, re-check before you quote it)
- Put in: **$22.50**. Card: **~$2.25**. Owner's next milestone: **$2.40**. They'll add $2.50 if the card gets there. The 🎯 goal
  bar on the real card tracks it.
- 24h you vs engine (`realBook.versus`): **hand picks −8.4% on $85 (35% won), engine −0.5% on $33**. Realized all-time
  −$12.38 (276 wins / 377 losses).
- Owner-move record (`humanStyle.moves`, judged 30 min later): picks 200 · 39 good / 88 bad · −6.7% typical. Profit takes
  46 · 20 good / 10 bad. 🏠 initial-out 2 · +182% typical (tiny sample, and the best thing on the board).
- Ledger autopsy (943 pieces, memory `real-card-what-pays`): **held 30+ min wins, exits inside 15 min lose, trims of
  winners make the money.** The leak is turnover × entry cost, not fees.

## What the records say works and what doesn't (1-hour medians, `/fuses/list-proof` + `/fuses/call-proof`)
| Least bad | Losing hard (scrapped from engine buys, shown ☠ BUSTED) |
|---|---|
| 🧲 Fed runners −0.2% | 🆕 New launches −81% |
| 🔥 Pump trending −2.4% | 🗑 Trench list −79% (small ticket only, never paused) |
| 🟢 Dips & bottoms −4.7% | 🔥🔥 Double signal −83% |
| calls WATCH +0.9%, WASH +0.5%, COOLING +0.2% | 🚀 Movers −65% · 📣 Pump callouts −54% |
| combo "in 2 lists, flat pace" +5.0% (n 9) | calls BOND RUN −83% · EARLY RUSH −64% · DUMPING −55% · BREAKOUT −25% |

No list or call is positive "95–100% of the time". Nothing on this site is. **The honest edge is not losing**: be in
fewer coins for longer, take profit from winners, and keep the seat count small while the card is small. A record
that reads −80% is mostly coins that vanished (no price = −100%). That is the point: those coins rug.

## The mindset
1. **Evidence first, every time.** Every list, call, exit and wallet signal keeps its OWN settled record (noted once,
   judged 1h later, no price = −100%). A new signal ships as a READ, and it moves money only once its own record is
   positive (`PROVE_FIRST`, `CALL_AUTO_MIN`, `smart` key ≥ 5). A busted record turns a feature into a warning
   (`busted()` in CoinVital: ≥ 30 settled, median ≤ −20%).
2. **Warn, never block the owner.** Their picks go through the 409 → "I understand — pick it anyway" path. Engine
   rules limit the ENGINE. Sizing (tickets) is fine, refusals are not.
3. **Never promise.** No "100%", no "guaranteed", no profit forecasts. Say the median and the sample size.
4. **Read the money before the code.** Start every task with a cash check (`realBook.reconciliation`, `versus`,
   `realized`). When the owner says "why did it buy X", read the card event before the buy and the leg's `bought` tag.
   When they say "button doesn't work", compare stored `realCfg` with `cfgEff` (ladder / real_guard / seat fit sit on top).
5. **Small card = few seats, small tickets, long holds.** 5-min rounds are the owner's choice. Don't lobby for a slower
   clock. Lobby for min hold, locks and trims.
6. **Degen UI = 5-second read.** Verdict word + meter + ≤ 3 facts + one tap. Buys/sells bar on every coin. Real icons
   (SVG globe / X / Telegram), socials first, record badge on every call (`+0.9%/1h`).
7. **Ship one and done.** Test (fake network), gate (`bash scripts/gate.sh`), fetch + rebase, push to main, restart the
   backend only when no order is pending, check one keeper (`pgrep -f "uvicorn reputation_service" | wc -l` = 1).

## The engine's shape (where to plug things in)
- Per-coin data → the coin-edge record (`/api/reputation/edge`, `lib/coinEdge.js`). Never a new poller.
- Ranking → `confluence.edge` (lists × call × learned combo × your real trades × capped hand tilts).
- Learning → `real_learn` (every coin leaving the real card is a lesson), `degen` (smart wallets, bursts, callout spikes),
  `flow` (90s tape: flow exit, rug radar, flow entry), `owner_moves` (owner actions judged 30 min later).
- Records → `trench.meta_track` / `meta_proof` keyed files in `backend/data/*_proof.json`.
- Real-card actions → `POST /admin/arena/prime {leg | skim | manualSell | pickSwap | fillSeat | realCfg …}`; the keeper
  (`_fw_tick`) does the chain work. Never sign or move Fuse-wallet money yourself. Never press money buttons in a browser.

## Next degen moves worth building (owner hasn't approved yet; offer them, don't assume)
- **🎟 Picks ride as tickets while your record is red.** A hand pick goes in at a ticket size (e.g. 25% of a seat)
  while `versus.you` is negative over 24h, and gets a full seat once it turns green. Sizing only, never a refusal.
- **🏠 Auto initial-out on every winner.** The only owner move with a positive record. Turn `trenchHouseAt` into a
  card-wide "pull the stake at +X%" for every coin, so winners ride on house money.
- **⏳ 30-minute pick lock.** The ledger says exits inside 15 min lose. A hand pick can't be hand-swapped for 30 min
  (warn + acknowledge, like picks).
- **🧲 Fed + 🔥 trending overlap lane.** The two least-bad lists. Coins in both get their own record, and the engine
  takes them once that record is ≥ 0.
- **🐳 Smart-wallet auto-follow.** Smart wallets started settling 2026-10-08. Once the `smart` key is proven (≥ 5
  settled, median > 0), a smart buy may jump a coin to the front of Coming up.
- **Scrap candidates:** the 📣 Pump signals tab (calls −54%, double −83%; fed is the only part worth keeping) and the
  🆕 New launches tab (−81%). Ask before removing tabs the owner uses daily.
