# 📲 FEELESS × Telegram — Strike Zone (the Familia shooter) + an automated group

Owner 2026-10-27: "family be a telegram game" → then "a cool third-person shooter instead of the raceway". What is built:

| Piece | Where |
| --- | --- |
| 🎯 STRIKE ZONE — a full-screen third-person shooter on three.js's own open-source FPS physics (Octree + Capsule) and its rigged Soldier model: a container yard with warehouses + ramps, bots (easy / normal / hard) or ONLINE rooms, over-the-shoulder aim, ADS, recoil, headshots | `components/StrikeGame.jsx`, `StrikeZone.jsx`, `lib/strikeGame.js` |
| Levelling + the GUNSMITH — 4 guns × barrel · optic · magazine · stock · skin, each part unlocking at a level; XP for kills, headshots, wins (server-checked on its own clock) | `backend/arena.py`, `/api/reputation/arena*` |
| Telegram Mini App — opens full screen inside Telegram, plays under the player's Telegram name (no wallet needed); a wallet in a family also feeds the family bank (+5 MP a kill, 150 a day) | `lib/telegram.js`, `backend/tg_auth.py` |
| Online rooms — a WebSocket per room (≤ 8 players), positions + shots relayed | `/api/reputation/arena/ws` |
| Automated group posts — every level-up (with what it unlocked) and a 🎯 PLAY button | `_tg_group`, `arena.level_post` |

## A. Set it up (≈10 minutes, only you can do this)
1. **Make the bot.** In Telegram open **@BotFather** → `/newbot` → name `FEELESS Familia` → username e.g. `FeelessFamiliaBot`. Copy the token.
2. **Put the token in** `backend/.env`: `TELEGRAM_BOT_TOKEN=<the token>` (never paste it anywhere else).
3. **A public https address.** Telegram only opens https pages. Production: your `PUBLIC_SITE_URL`. To test from this Mac today:
   `cloudflared tunnel --url http://localhost:51367` → it prints `https://<random>.trycloudflare.com` (keep that terminal open).
4. **Make the Mini App.** @BotFather → `/newapp` → pick your bot → title `Fee City Race` → description → a 640×360 picture (a screenshot of the
   Raceway works) → skip the GIF → **Web App URL** `https://<your https address>/familia?tg=1&place=strike` → short name `strike`.
   BotFather answers with the app link `https://t.me/FeelessFamiliaBot/strike` → put it in `backend/.env` as `TELEGRAM_APP_URL=`.
5. **The menu button** (so the bot's chat opens the game in one tap): @BotFather → `/setmenubutton` → your bot → the same Web App URL → label `🎯 Play`.
6. **The group.** Create a group `FEELESS Familia` (or use yours) → add your bot → make it **admin** (Post messages · Pin messages).
   Get the group's id: post any message in the group, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   `"chat":{"id":-100…}` → `backend/.env`: `TELEGRAM_GROUP_ID=-100…`.
7. **Restart the backend** (push to `main` restarts it through auto-pull, or the watcher — see `docs/HANDOFF.md`). HQ › Launch › Ready board
   and HQ › Setup show the three Telegram keys as set (never their values).
8. **Pin the game in the group:** post `https://t.me/FeelessFamiliaBot/strike` in the group and pin it. Done — the group now gets `🎯 STRIKE ZONE · <name> hit LEVEL n — unlocked …` on every level-up, with a 🎯 PLAY button.

## B. Test the shooter (no setup needed)
1. Open **`http://localhost:51367/familia?place=strike`** (or Familia → the city → Directory → 🌹 THE FAMILY → **STRIKE ZONE**, also a room of Family HQ).
2. The lobby: your level + XP, the GUNSMITH (pick a gun, then barrel · optic · magazine · stock · skin — locked parts say the level they open at),
   VS BOTS (easy / normal / hard) or ONLINE (type a room name, share it with your family).
3. **🎯 PLAY** opens full screen. Desktop: click to capture the mouse → **WASD** move · **Shift** sprint · **Space** jump · **left-click** fire ·
   **right-click** aim down sights · **R** reload · **Esc** frees the mouse. Phone: left stick moves, drag the right side to look, **FIRE · AIM · JUMP · R**.
4. First to 25 kills (bots) / 30 (online) or the clock ends the match → the result card: kills, deaths, headshots, accuracy, the XP saved (a guest
   sees it but keeps nothing — sign in with a wallet or open it from Telegram).
5. The server refuses results that beat its own clock (`backend/tests/test_arena*.py`). Dev preview without the lobby: `/dev/towers?strike=hard`.
6. Online: open the same room on two devices — you see each other's soldiers (blue), shots and kills. (A dev server restart is needed once so the
   WebSocket proxy in `setupProxy.js` is live.)
