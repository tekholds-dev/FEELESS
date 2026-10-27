# 📲 FEELESS × Telegram — the Familia race game + an automated group

Owner 2026-10-27: "family be a telegram game where people can drive vehicles / race this city". What is built:

| Piece | Where |
| --- | --- |
| 🏁 The Raceway — drive Fee City at night (the families' blocks are the buildings), 3 vehicles, the server's checkpoints, server-checked times | `components/StreetRace.jsx`, `lib/raceEngine.js`, `backend/raceway.py` |
| Telegram Mini App — opens full screen inside Telegram, the player races under their Telegram name (no wallet needed) | `lib/telegram.js`, `backend/tg_auth.py`, `/api/reputation/familia-race*` |
| MP — a wallet in a family earns the day's first finish (120 MP) + under par (280 MP) into the family bank; a driven errand pays that errand's MP ×1.25 under par | `raceway.race_mp`, the Job Board's 🚚 Drive it |
| Automated group posts — every new #1 of the day + yesterday's podium (with a 🏁 RACE NOW button) | `_tg_group`, `raceway.record_post` / `recap_post` |

## A. Set it up (≈10 minutes, only you can do this)
1. **Make the bot.** In Telegram open **@BotFather** → `/newbot` → name `FEELESS Familia` → username e.g. `FeelessFamiliaBot`. Copy the token.
2. **Put the token in** `backend/.env`: `TELEGRAM_BOT_TOKEN=<the token>` (never paste it anywhere else).
3. **A public https address.** Telegram only opens https pages. Production: your `PUBLIC_SITE_URL`. To test from this Mac today:
   `cloudflared tunnel --url http://localhost:51367` → it prints `https://<random>.trycloudflare.com` (keep that terminal open).
4. **Make the Mini App.** @BotFather → `/newapp` → pick your bot → title `Fee City Race` → description → a 640×360 picture (a screenshot of the
   Raceway works) → skip the GIF → **Web App URL** `https://<your https address>/familia?tg=1&place=race` → short name `race`.
   BotFather answers with the app link `https://t.me/FeelessFamiliaBot/race` → put it in `backend/.env` as `TELEGRAM_APP_URL=`.
5. **The menu button** (so the bot's chat opens the game in one tap): @BotFather → `/setmenubutton` → your bot → the same Web App URL → label `🏁 Race`.
6. **The group.** Create a group `FEELESS Familia` (or use yours) → add your bot → make it **admin** (Post messages · Pin messages).
   Get the group's id: post any message in the group, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   `"chat":{"id":-100…}` → `backend/.env`: `TELEGRAM_GROUP_ID=-100…`.
7. **Restart the backend** (push to `main` restarts it through auto-pull, or the watcher — see `docs/HANDOFF.md`). HQ › Launch › Ready board
   and HQ › Setup show the three Telegram keys as set (never their values).
8. **Pin the game in the group:** post `https://t.me/FeelessFamiliaBot/race` in the group and pin it. Done — the group now gets:
   - `🏁 NEW #1 IN FEE CITY …` the moment someone takes today's top spot (with the gap they beat it by),
   - `🏆 FEE CITY RACE · <day>` yesterday's podium on the first finish of a new UTC day, with the MP the new track pays.

## B. Test the racing (no setup needed)
1. Open **`http://localhost:51367/familia?place=race`** (or Familia → the city → Directory → 🌹 THE FAMILY → **THE RACEWAY**, also a room of
   Family HQ).
2. Pick **MUSCLE CAR · STREET BIKE · BOX TRUCK** → **🏁 START** → 3-2-1.
3. Drive: **arrows / WASD**, **space** brakes · on a phone the **◀ ▶** and **BRAKE / GAS** pedals. Follow the green ring (the arrow + the mini-map
   point to it); hit every ring in order.
4. Results: not signed in = *practice* (times not posted). Signed in with your wallet and in a family = your time posts to today's board + MP
   to the family bank (once a day + under par). Opened from Telegram = your Telegram name on the board.
5. Errands: Family HQ → **JOB BOARD** → a delivery store (pizza · gas · laundry · pharma · mart · docks) → **🚚 Drive it** → pickup → drop.
6. Cheats are refused by the server: faster than the straight line at top speed, rings out of order, or a run shorter on the server's clock
   than the time it claims (`backend/tests/test_raceway*.py`).
7. Telegram test: open `https://t.me/FeelessFamiliaBot/race` on your phone (after A.1–A.7) → it opens full screen → race → your name is on
   the board → the group gets the #1 post.
