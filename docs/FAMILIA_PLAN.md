# La Familia v2 — build plan (owner's ask, 2026-10-21, not built yet)

The owner wants a big, addictive city game in the spirit of Godfather PSP and Jailblock. It must make money with **no pay-to-win**. Build it in this order. Each step ships with tests and a browser check.

## 1. Economy (`backend/family_city.py`)
MP must grow fast, and every store must do a real job.
- Production: mp/h ×5, costs ×1.5, `MAX_LEVEL` 10.
- What each store does (`FUNC`):
  - Pizza: trains recruits +2 XP an hour per level.
  - Gas: moves cost 5% less per level (up to 40% off).
  - Laundry: 4% per level of new production goes straight to the bank, where it can't be robbed.
  - Pharma: hurt recruits heal 15% per level faster.
  - Mart: building, upgrades and hires cost 3% less per level (up to 30% off).
  - Lounge: trains recruits +4 XP an hour per level.
  - Docks: every 3 levels, raids reach one more bridge.
  - Lab: lets the family hire spies, which reveal rival guards.
  - Casino: dice, earned MP only, up to 5% of the bank, pays 1.9×.
  - Bank: the stash holds +2 hours per level.
  - Tower: every 3 levels, raids get +1 round.
  - Park: +3% to every store.
- Recruits are units with levels 1–10: guard, hitter, earner and spy. They train every hour and earn XP on raids. Levels can never be bought. Hurt recruits sit out until healed.
- Collect streak: +5% per day, up to +50%. Members' verified FEELESS trades boost production up to ×3, so trading on FEELESS is what grows a city.
- Two wallets:
  - **BANK** = earned MP. It pays for everything.
  - **GOLD** = MP bought with SOL. It pays for cosmetics and moves. At most `GOLD_WEEK_CAP` (owner-set) of gold can go into the bank each week.
- House tax: 5% of every collect (owner-set) goes to the FEELESS house pool, which pays season prizes.
- A half-written v2 of family_city.py was drafted in the session that wrote this file, but it was never saved.

## 2. The world (new `backend/family_world.py`, pure + tested)
- 5 boroughs × 12 blocks (Pump Harbor, Raydium Heights, Jupiter Hills, Meteora Market, Bonk Bay), plus a 4-block Tower Island. Bridges link the boroughs in a ring, and the island links to all of them.
- Every family gets a free HOME block. Families can **buy turf** with MP: price = 800 × borough tier × (1 + 0.6 × blocks owned). Each turf block adds +4% production and +1 recruit seat. Turf can be sold back at 50%. Buying near a rival puts them in raid reach.
- **Relocate** home: costs MP (cheaper with gas) plus the owner's `moveUsd` in SOL, when the owner sets one.
- **Season** follows the calendar (October = 🎃 Haunted Trenches) and sets the weather and look of the city.
- **Today's boom**: the top live narrative from `meme_terms.wave_leaders` maps to one borough, which gets ×1.25 production. This is real data.

## 3. Raids = chess moves (`family_world.raid_*`)
- The attacker sends one member. That member's rank sets the move power: Associate / Soldier 1 · Capo / Consigliere 2 · Underboss / Don 3.
- The raid alternates: attacker move, then defender response. It lasts 2 rounds, +1 per 3 tower levels.
- Attacker moves:
  - HIT a lot: steals that store's share of the stash.
  - SABOTAGE: that store makes nothing for 2h.
  - SCOUT: reveals the guards on a lot.
  - RETREAT: ends the raid and keeps the loot.
- Defender moves:
  - GUARD a lot: +3 defence there.
  - COUNTER: chance to hurt a hitter and halve the loot.
  - LOCKDOWN: once per raid, moves 50% of the stash into the bank.
- If the defender doesn't answer within 5 min, the CPU answers for them. The defender gets an inbox notice and the move board.
- Rules: dice rolls are seeded by raid id + move number, so they can be tested. Loot is capped at 35% of the stash and never touches the bank. Each pair of families has a 2h cooldown. Only rivals in reach can be raided.

## 4. Shop + owner pricing (HQ › Fees › 🌹 La Familia)
- Gold packs: the owner sets the prices (default 1,000 / 6,000 / 15,000 gold for $1 / $5 / $10). Payment is a SOL transfer the user signs, checked with `_verify_sol_payment`; the full payment goes to FEELESS.
- Owner-set knobs: `houseTaxPct`, `goldWeekCap`, `moveMp`, `moveUsd`, and the redeem line.
- **Redeem**: earned MP → a 24h FEELESS swap-fee discount for that member, at most once a week. Defaults: 30,000 MP for 15% off. This hooks into `effective_fee` after the promo block, read from an in-memory pass dict.

## 5. Frontend
- **Landing**: a cinematic full-screen noir page, unique to Familia (not a copy of the Fuse landing). Skyline searchlights, rain, live numbers (families · blocks owned · MP made today · raids live), the season banner and today's boom.
- **Backdrop**: add a `PageBackdrop` kind `familia` for leaderboard `?lens=crews`. Full bleed, with **no FEELESS green**.
- **Big city map**: CSS 3D. The borough islands sit on water, joined by bridge strips. Each block is an extruded box whose height is its owner's power, in the owner's badge colour. Show a beacon on your blocks, a glow on the boom borough, and weather from the season or the family's own look. Drag or orbit to rotate, plus zoom. Tapping a block opens a side card: owner, price, Buy / Raid / Visit / Relocate here.
- **Raid board**: a modal with the rival's 5×5 lots, whose turn it is with a countdown, the move buttons and the move log. Show an incoming-raid banner to the defender.
- **Family room customization**: weather, time of day, neon colour and skyline style. The basic set is free; premium looks cost MP or gold.
- **Tabs**: give every Familia tab its own look.

## Not yet done from the same request
- Launch page + FeeCat pages: finish the glass / backdrop restyle. The owner's screenshots show flat panels still there.
