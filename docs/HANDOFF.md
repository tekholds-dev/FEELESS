# HANDOFF — THE ONE PAGE every Claude works from (any account, any session)

Owner, 2026-11-04: "always should be one MD". This file is the handoff AND the only task list (`## TASKS

Owner 2026-11-04: what's left comes first, what's built comes after. **OPEN** = not built · **OWNER** = needs your key, account, signature or decision · **VERIFY** = built, needs one real run or your check. A row finished AND proven moves to `docs/FEELESS_HISTORY.md`.

# LATEST (2026-11-05, evening). Read this first; it updates START HERE below.

**Shipped in be01a187:** desktop lag (page under a desktop stops painting, windows behind pause, drags touch the DOM only; PoW scroll 26 to 45 fps in the dev build). Fit to screen and new settings (`fitIcons`, `useDeskIcons`). All 5 proof folders plus PoEco use `ProofTile`, and `PrintLines` makes a folder's print its exact line on the desktop print. PoStatic lists every filed page and a failed read retries instead of saying "blank". PoEco (`agent_eco.py`, `EcoFolder.jsx`): Python math, sealed entries, receipt with hash, no model reads it. GitHub folder for every agent (`GitFolder.jsx`, `collective_git.py`, token sealed via `cat_keys`). Sicario's HQ tab is the full `CatWorkbench` plus Fuse seat and Endless switches. Fuse seat: `op desk_seat`, `/api/reputation/internal/sicario-want`, off by default. OSSY and G4 make no LM call while desk buys are off and the seat holds nothing. Web cannot zoom out past fit. Collective HQ numbers sit behind "Every number".

**Works live:** private repo `tekholds-dev/feeless-collective` made and pushed with a real call (154 files, second push 0, anonymous read 404, secret scan 0), done from a script, not the folder's button. PoEco filed on Sicario's through the real server (one "Example books" folder is there, made by my test). Sicario tab and web zoom looked at on screen.
**Fakes only:** GitHub folder's buttons (`test_collective_git.py`), Fuse seat send, hourly auto push, `sources/good.json` and `bad.json` (their code ran in no real push yet).
**Not built:** a card seat win does not close its PoW folder with real P/L and cannot pay the Pool, because `_collect_pass` sends from an agent wallet and Sicario's has none. Prompt Studio is still mostly trading (only its header line changed). The Brain chat on the Sicario tab is untouched. py agents are not retired; the sorter is `collective_git`. Manual only moved 6 tabs behind More: lessons are not rewritten yet. A full audit of every page was not done: scroll was audited on the Agents desktop only, and "wired properly and encrypted" is unproven beyond PoEco entries and tokens. Auto-updating outside source repo: no external one found or wired. Proof pages (`source/pages`) were not in the real push.
**Still lagging:** 35 to 48 fps scrolling (Bids 35), and Proofprint and Features take 220 to 240 ms to open (dev build). Production was not measured.
**Data notes:** Monitor test's folder was deleted before this fix, so its 4 filed pages show "its folder was deleted" and cannot open. A filed folder's page is now kept on delete. My test also dragged Happy's Desktop settings icon and pressed Fit on Happy's desktop, replacing the owner's arrangement.

**The deal (owner decided 2026-11-05, replaces the plans):** cfg `deal='bank'`. The Collective banks 100% of a send on the sealed ledger, with total sent and points (dollars x boost at that send). Each month `rewardPayPct` (50) of the fee pot is the budget. Each agent is paid on its own clock: `cycle_days` runs 30 days at Spark down to 15 at Myth, 10.5 with a full boost, never under `minDays` (7); speed moves money sooner, not more. `floorPct` (20) is split evenly by owner so every rank eats; the rest goes by points, up to `capPct` per owner. Lifetime reward payouts cannot pass `payoutCapPct` (50, hard limit) of all fee money ever in. Points carry at `carryPct` (80) each month. Screens: `KeepDeal.jsx`, `RankLadder`, `RewardCalc`. Tests: `test_collective_deal.py`.
**Owner asked that what the Collective keeps also pay rewards. NOT built that way, on purpose:** sends never reach a reward, because later senders paying earlier ones is a Ponzi and `NOT_PONZI` on screen says it cannot happen. Rewards pay from fees only. Change this only after the owner has a lawyer's answer, and then remove that on-screen claim first. Monthly capped withdrawals are not built: withdrawals stay off until a lawyer looks, so there is no withdrawal cap to set yet.

**OSSY and G4, found by real calls:** `_lm_call` got empty text because both models spent every token on hidden thinking; fixed with `reasoning_effort: none`. The budget guard treated `local/` models as infinite cost, so Sicario's chat always stopped; fixed. `.env` LAN_LLM_MODEL now names the loaded model. Sicario's chat answered through the real service at $0.00. G4 answered in trading JSON to a plain question with 1,323 prompt tokens: LM Studio on the desktop has a system prompt set there; the owner should clear it for general work. A real PoW request ended "only 3 of 20 coins passed every buy guard", so no full PoW has run since these fixes, and the "no vitals" research reads (A5) are not retested.

**Seats and Auto-collect (2026-11-05, owner: "allow them all 4 seats"):** a Sicario's PoW may take any free seat of the card's 4 (`_seat.card_seats`, `sicario_refusal`, `desk_off_plan`, `review_leg`). `deskBuysOff` still stops everything else. Every seat guard still decides: fresh, night guard, picks only, blocked, precheck, gun line. Hitting Auto-collect (hive on) sets `cardSeat` and files a PoW every 4 minutes until no seat is free (`_sicario_loop`, `_sicario_free`). Tests: `test_sicario_seats.py`. Fakes only: no live want was sent, because the card holds 0.002565 SOL and a live test could spend real money. **Not built:** a card win paying the Pool, and a closed seat's P/L on its PoW folder. **Bug fixed:** a resting `powRun` looked busy, so Endless never ran. Live, a PoW then often stops at "only 2 buyable coins" (needs 4, trading guard, not changed).

**The pool test, and why the on-chain pool is NOT built:** owner said "if it works, build it". Raydium's own 30 day numbers (read 2026-11-05): WSOL-USDC 0.04% tier, $6.7M pool, 55% fee APR, about 4.5% a month, but SOL fell 14% in 350 hours, so half in SOL lost about 7%: net about -2.6%. USDC-USDT: 4.6% APR with almost no price risk, so $37 earns about $1.70 a year. Top APRs (SQQQ, TTWO, PUMP pairs) are 150-800% on assets that swing 40% or more. These are pool-wide averages, not what one ranged position earns. Verdict: a stable pair grows slowly; the high-fee pools did not prove growth. What IS built is the ledger for any real profit: `book_result` (profit joins the pot, a loss hits the pot then the bank), `back_room` (rewards stop at `maxBackX`, 1.08x of what it sent, owner can raise to 5x), sends never reach a reward, payouts capped at 50% of fees plus profit. Nothing feeds `book_result` yet. Tests: `test_collective_deal.py`.

**The game room (`GameRoom.jsx`, `lib/gamePrint.js`, `game_edge.py`):** PoB's game window. Every number is an ESPN field, a missing one stays missing. Live polls every 20 s (server cache 15 s). The print: same ridges as the Proofprint (`lib/proofprint`). Core = first play, outer ridge = final horn. Each play inks the stretch from the last play at its spot on the game clock (`game_at`), scores and win-chance swings heavier. `printStage`: pre, live, grading (game over, a call still ungraded), final (seals with one green or red mark per agent call, from `game_calls`). Team and player prints: one ridge per stat, last season on one half, this season on the other, inked by `score_change`. Edge tab: reads, officials (names only: ESPN has no referee record), line open to now, pace vs total, run, last games and rest, hot and cold, foul trouble, flow, model, ATS, weather, injuries. "Prove it" puts a read in the chat box. Tested live on a real college game: the print, floor, plays, edge, players. The final print was seen on that same game once it ended: sealed with Happy's real WRONG grade. Logos are ESPN's images, shown because the owner asked (an earlier note avoided logos as trademarks): lawyer item.

**Webs:** `/api/cats/sources/web` (folders and features, no site names, nothing clicks) in Features › The web, `/api/cats/web/live` (working agents and recent stored proofs; Sicario's and incognito agents only for the creator) on both webs. `StashMap` `live` rides agent names on nodes. Not seen with an agent firing live yet.

**Not finished by this account:** Sicario's Wallet folder (`dsk-fuse-wallet`) was never opened on screen: the endpoint was read live, and the page's dev chunk failed once (`ChunkLoadError` while webpack rebuilt; press Retry). Sicario's real PoW never ran end to end: it stops at "only 2 buyable coins". The proposal `+` and the Git folder item below are not started.

**Costs:** `CostTicket` (faint cost, click for receipt) on chat bubbles, Jobs nodes in `WorkTree`, totals in `ProofHead`. A mind's own cost is recorded only from now on.

**GitHub, as it stands:** Collective repo linked by the owner in the folder (`tekholds-dev/feeless-collective`), and pushing for real: the owner fixed the token, 203 files in commit `eaa5306` (118 snapshots, 45 sealed vault files, 34 proofs), anonymous read 404, hourly push on. Deep sorting: `to='collective'` answers only on Fee and only for the creator. Every other agent's folder sees only its own files. Agents' own repos: none linked. Private vault (`vault_tree`): each agent's filed proofs and pages, gzipped and sealed under its own key at `vault/<tag>/<hash>.seal` inside the Collective repo, pushed by the hourly pass, 20 MB share per agent. Tests fake only, first real pass not yet seen. It holds proofs and pages only; snapshots are not in it yet. The seal depends on this server's secret: lose it and the vault cannot open. GitHub is not a file drive: a repo should stay small, so this cannot replace storage at scale.

**Sicario's wallet:** its Wallet folder is the Fuse wallet (`/internal/sicario-wallet`, read only). `cardSeat` now defaults on: a PoW it files goes to a free seat, all guards apply, and the desk's switch turns it off. Topping up the address alone leaves the SOL unassigned: it must go on the card in HQ.
**Recall before searching:** `_recall` puts wins and losses related to the job in every proof's prompt, from the Stash (`related`), titles and results only. Agents never hold the repo's token or call GitHub: the server reads its own copy. Tests only, not seen in a live proof yet.
**Highlights (root cause):** `_pow_snap` boxed every number matching a regex, not what the mind read. Now only facts it filed from that site are boxed, it scrolls to them, and the picture is taken right after finding them. A page only opened has no boxes. Blank pictures and bot checks are not kept (`is_dead`, `needs_human`). Old snapshots are unchanged: nothing sorts or re-marks them yet. PoB and PoC shots still box topic words or trend words. Tested with fakes, not on a live proof. Mouse gestures were not looked at.

**Restart trap:** killing 5088 restarted only 5088 this session (5077 stayed up 22 minutes). After a change to `reputation_service.py`, kill 5077 too and check `ps -o etime`.

**Owner decisions waiting:**
1. Card has 0.002565 SOL, so no seat can buy until funded. Then hit Auto-collect on Sicario's.
2. PoB streams (A4) still needs the owner's call on sources.
3. Lawyer: rewards by amount sent, profit share from a pool, team logos, and withdrawals. Withdrawals and any cap on them stay off until then.

# PRIORITY FOCUS, IN ORDER (owner 2026-11-05, next up)
0. **NEXT, before everything below (owner's last message to this account):**
   - **Card signup (`CardSites`, `card_link`):** Sign up opens the provider in the agent's Browser, and the owner saves the card's Solana top-up address on the agent (`cardLink`). No card number, no ID. **Not built: the send from agent wallet to card**, a new real-money door, needing guards and one real provider's address first. Not seen with a real provider. **PoB watch:** owner asked for auto VPN to free streams, declined: those are mostly unlicensed. Build it on licensed services the user signs in to himself in the cloud browser, a saved session, click a game to open it (A4).
   - **Kit library (`collective_kits.py`, `KitShelf`, `KitPick`, `RepoPrint`):** Fee's GitHub folder adds a free kit's AI guide, edits its text, shows the repo's fingerprint. Kits push under `kits/`. `_recall` carries them into every proof's prompt, the agent's picks first (PoStatic's READS FIRST chips), capped at 5,000 characters. Previews open the kit's site in a new tab; there are no previews inside FEELESS, and only those 5 catalog kits can be added. **Not built:** editing any other repo file from the folder (edits on GitHub are overwritten or ignored), uploading your own kits, a playground, per-kit win rates, per-proof steps.
   - **Sicario's is PAUSED (owner: "don't get requests until we find a better all-around model for PC and desktop").** `SICARIO_PAUSED = True` in `feecat_service.py` refuses chats, pages, PoC, loops and Auto-collect, and stops its PoW loop. So seats and browser proofs stay untested. Everything below about OSSY and G4 waits for that model. First job: find it, sized to both machines, and test it with the owner's say-so, because it lags his PC.
   - **`LM_ASKED_ONLY=true` in `backend/.env` (owner 2026-11-05):** `_feecat_duo` returns at once, and background router calls skip OSSY and G4 (`asked_only`). Anything with `only=` or force/seat still reaches them, so a model seat holding a coin is still reviewed. Background cases now go only to cloud providers, which may cost a little.
   - **Found in LM Studio's own log:** the desk's coach ("ROLE: JUDGE") still calls OSSY on the Mac, against the owner's 2026-10-13 rule that background jobs stay off it (`ai_router.local_ok`). `LOCAL_LLM_BACKGROUND` is not set; `reason(..., 'coach', 'normal')` at `reputation_service.py:22033`. Find out why it passes and tell the owner. It is a likely part of the lag even with Sicario's paused. Fixed by `LM_ASKED_ONLY`.
   - **OSSY and G4 do not code:** `_ws_page` sends any page from a `local/` mind to `WS_CODE_MODEL` (`z-ai/glm-5.3-flash`, on its model credit). Plans and content stay local. **Stop button:** `desk_stop`, `lm_stop` on Sicario's desk. Tests only, neither seen live.
   - **Browser proofs on OSSY and G4 are NOT proven.** A real PoB on Sicario's opened no site: "its browser session ended". The service restarted during the read (5088 up 30 seconds right after). Likely cause, not proven: load 41 on the Mac made the keep-alive health check fail, so it restarted the service and killed the read. Fixes to try: run the browser windows and models from the LAN desktop, give the health check more patience under load, one window at a time. `_lm_call` now takes one call per machine (`_LM_GATE`), not yet tested under a real proof. Local cap raised to 8000 tokens and 600 s. The owner reports OSSY lags the PC: do not run tests on the Mac without saying so.
   - **Fee's GitHub folder IS the Collective repo now** (`scope='collective'` on `leader`), the separate icon is gone. Not opened on screen.
   - **PoStatic on OSSY and G4:** cause found and fixed: `_ws_view` called any run older than 240 seconds dead while the models were still writing, and service restarts killed others. Now a run is dead only when its task is gone (`_ws_dead`, 40 minute last stop). A restart still kills a running build. Check the real result of folder `wfdde5bb856` ("SICARIO TESTS"), and whether a page takes too long on local models: 8.5 minutes was not enough for one, so consider one mind writing instead of both.
   - **Owner's ask, not built: a py agents folder on Sicario's desktop**, with live animations of how the py agents work, so OSSY and G4 can fix agents. See item 4 below: it proposes, the owner approves any code. Start by listing what the 5 py agents really do in code before drawing them.
   - **Owner's ask, not built: the Collective's list updates itself** so the best sites and sources always beat a static list. `sources/good.json` and `bad.json` go to the repo, but `agent_refs.PROOF_FILES` is still a fixed list. Merge good and bad back into what agents read.
   - **Sicario's Minds folder gets the new elite general prompts and brain.** Update Prompt Studio (still built on trade records) and make sure the local LM servers get those prompts. A real call showed both models obey a request's system message, with 41 prompt tokens, so nothing needs changing inside LM Studio itself.
   - **Vision model:** the owner wants these computers to do anything asked, with no PC crash. Find the best current local vision model that fits each machine (this Mac runs qwen3.5-9b, the LAN desktop qwen3.5-4b; check their RAM first), test one real call, then tell the owner the pick.
   - **Images and video:** research pulling several image and video APIs in one place and picking the best result (the owner named Higgs as the idea). Also site plugins. Real call to each before building. Put steps here if limited.
   - **Best sources for everyone:** the repo and the web visual serve all users and visitors. When a user runs top models, the Collective keeps what they proved, so every agent gets the best build techniques and sources from the models the Collective approves most. Build on `_recall`, `sources_web` and `collective_tree`.
   - **The Collective earns even when nobody sends a proof:** per top-up and per card transaction. Lock a fee onto any card txn made in the cloud browser by agents, or by a user on FEELESS, if that is possible. Unknown: a third party card cannot be charged a fee by us unless the payment runs through us. Check card provider terms and ask a lawyer before building.
1. **Snapshot highlights are not accurate.** Every brain must highlight all the data it really scraped, on the right spot. Find hard-coded highlights and dead snapshots, make them easy to sort and fix. No snapshots of bot blocks, ever. Agent mouse gestures and clicks are suspected buggy: reproduce first.
2. **`+` on a proposal, in every proof folder (pow/pow13 and so on).** Scenario: an agent proposes a perp, the owner trades it by hand on the crypto.com app, on a win uploads the receipt screenshot, then sends the winning funds to the agent's wallet, which sends to the Collective with all the required info. The 5 py agents scan the highlighted areas of the proof. A pasted receipt is a claim until a send confirms it: never count it as proof by itself.
3. **Git folder:** users see all their proofs and data organized, we keep everything, and they may assign their own repo to get a copy of their agent. Only what the folder shows goes out: never keys, sign-ins or secrets.
4. **Sicario's agent playground (owner: "this mf big").** In Sicario's desktop, a py agts folder that opens like PoStatic but better. Only they say why and where the agents lack and propose fixes that help production and never overload it. When OSSY and G4 see agents getting proofing wrong they step in, fix the sorted issues, update the code, then show the owner the code and a static page. Not built. Any code change waits for the owner's approval.
5. **Grading the sends.** A send is graded, weighed, ranked and scored by the py agents; points reflect its share of the private pool's rewards; boosts speed the return. The ledger exists (`maxBackX`, `book_result`), the py agent grading and any pool do not. The pool stays unbuilt until a test shows the wallet grows.
6. **Command center:** a full per-page rebuild, for Sicario's, Fee and Familia only. Not started.
7. **Still open from earlier:** Prompt Studio is still built around trade records, not general. Manual rewrite with fewer steps and pictures. Tutorials styling. Auto-updating outside source for good and bad sources. A5 research reads. A7 site lists read by agents. Collective folder's "Where the money goes" panel draws empty. Bids 35 fps.

---

# START HERE (written 2026-11-05 for the next Claude, other account)

Owner's focus right now: **the Agents tab only, until it is tested and clean.** Everything below `# WHAT'S LEFT` still stands, but do these first, in order. The owner is testing real money on Happy Assistant while OSSY and G4 run the tests. Do not stop to ask what's next; do ask before anything that moves money. Answer short, plain words, show proof.

## Latest asks, in the owner's words where it matters

| # | Status | Ask |
|---|---|---|
| A1 | OPEN | **Fix OSSY and G4's settings/env.** "They will be the head of operation doing all the tests you want them to do, being they are my Mac and desktop downloaded models, so run them for tests while I request and test real money." Known: `.env` `LAN_LLM_MODEL=google/gemma-4-e2b` but the desktop's LM Studio lists only `qwen/qwen3.5-4b`. Local is fine (`qwen/qwen3.5-9b`). `_lm_call` already uses the loaded model; the card's route in `ai_router.py` still reads `.env`. Use Sicario's as the test runner, on `local/ossy` and `local/g4`, free. |
| A2 | OPEN · REAL MONEY | **No paper proofs for OSSY and G4.** "They were already using Fuse wallet and Fuse card to trade, so allow them to use Fuse mechanics within PoWs. Owner-only features we test to see if working good." When Auto-collect is chosen they work through the Fuse card wallet and the intake for PoWs. Today Sicario's is paper with no wallet, and `DeskAgents.jsx`, `_sicario_loop` and the screen copy all say paper, so all of that changes. This is a new real-money buy door: read `docs/DEGEN_PLAYBOOK.md` first, ship with age/pool/already-ran guards, audit the card's cash first (0.0026 SOL when last read), owner only, and reconcile with `deskBuysOff` (owner set it true: the desk's agents stop real buys). Confirm how it should interact before the first real buy. |
| A3 | OPEN | **Sicario tab layout.** "Monitors small and layout not organized and clean." Latest screenshot: seat card sits alone with an empty row beside it, monitors still look small. Files: `AgentCockpit.jsx`, `DeskAgents.jsx`, `styles/sicario.css`, `collectiveSetup.css`. |
| A4 | OPEN · NEEDS A CALL | **Watch any game or fight live from the PoB folder**: "secret and the user's responsibility, we only provide a free VPN and sources that provide free sports viewing." Note from the last Claude: most free stream sites are pirated, so raise this with the owner before listing them. Legal first: league and network free streams, YouTube, and Pluto, Tubi and similar. Do not ship a list of pirate streams without the owner deciding knowingly; pop-up-free viewing is a fair goal on legal sources. Not started. |
| A5 | OPEN | **PoW research reads come back empty.** Sicario's PoW said "researched on feeless.app: no vitals (nothing it could read)" on $TIRED and $COGE, then both minds skipped for lack of data. Find out why (`_pow`, scout step in `feecat_service.py`, near the `COIN_TALK_SYS` calls). This can make every PoW's research look blind. Check Happy's real PoW result first. |
| A6 | OPEN | **Finish the Collective audit**: every mechanic and every folder full, with vitals. The owner said "will be doing a lot more harder requests now". Proof folders must stay lit, clean, little scroll. |
| A7 | OPEN | **Site lists: the owner wants them huge** (86 now in `agent_refs.PROOF_FILES`): "every proof folder gets a huge site list... when I ask for best code they know where to go so they don't build from scratch EVER but be able to be creative." The list is in the prompts, but no test proves agents really open those sites first. Make the minds actually read them. |
| A8 | VERIFY | Owner's real tests running: PoStatic (a Monitor test built, owner liked it: "static build was nice"), then `file a PoW` on Happy for a real trade ("see if they can win a trade"). Happy has 0.0363 SOL, $0.98 USDC, $6.69 credit, wallet mode approve. Read what it filed. Test list given to the owner: `propose a PoW`, `propose a perp`, `file a pob best NBA picks tonight`, a slip from the Bids folder, `file a poc`. |

## What the owner has decided (do not undo)

- OSSY and G4 are **one agent, named Sicario's**, with two minds, private to the owner: off the public wall, no folder on the desktops. Its monitors and desktop live on the **HQ Sicario tab**. No chart and no old OSSY×G4 talk there (deleted, with the old generations code).
- **Proofs propose until they can run the whole loop like PoW.** Split PoP minds now give a card with both calls (Run, or Run … instead). Each proof has its own steps, colour, site list and layout.
- **Fingerprints are real, not decoration**: `ProofFingerprint` in `Proofprint.jsx` (click a proof's print: verdict, what it lacks, best and worst traits). Every folder's mark is its own ridge coloured by its result.
- **Why an agent sends** (the owner's question): less back, but a share of every fee. No pool rule was changed; the owner sets them in HQ. Numbers come from `collective_pool.project` and `growth`, which run the real send and tick on a throwaway state. More members alone do not raise profit, because they split the pot; more trading and outside swaps do. Never promise a return; words "invest" and "staking" stay off screens; withdrawals stay off until a lawyer looks.
- **Trader only**: Edge desk (indicators, order books, tape, case files); the server refuses it for a general agent. That is the answer to "why two kinds of agent?".
- **Fee's desk opens as everyone sees her**; the Owner only button shows only to the owner.
- **Style**: never hand-build charts; use libraries (shadcn, Motion, Recharts, Lightweight Charts, sigma, React Flow). The owner hates Sankey split pipes. Less scroll, no nested scroll, no tabs on money screens. Stash web = black space, fine lines, every proof a dot. Collective landing follows `~/Downloads/collective_signature_protocol_lab.html`.

## Traps that already bit

- **Check before restarting `feecat_service`**: a restart kills running builds and proofs (it killed the owner's Monitor test). Restart: `kill $(lsof -ti tcp:5088 -sTCP:LISTEN)`, the watcher brings it back in about 20 s. Check `workspaces[].busy`, `powRun`, `popRead`, `pobRead`, `_POC_BUSY` first.
- A privacy filter (`_no_keys`, `feecat_service.py`) drops any key named `setup` from answers. Playbook rows carry `name` for the screen and keep `setup` for her brain.
- `.dsk-body` is a stretched grid: items with `overflow: hidden` collapse. Proof windows use `.prf` with `align-self: start`.
- Editing a lazy-loaded component while a page is open can show "This tab couldn't render" (stale chunk). Reload, not a bug.
- Chrome won't shrink below the owner's screen, so test phones in Playwright against `/dev/cats?general&wallet`. Signed-in phone is still untested. HQ is the orb popup; `/terminal/hq` is a 404 and LaunchLab links to it.
- Shell edits with heredocs are sometimes blocked by a safety check: put a script in the scratchpad and run `python3 -I`.
- Endless (`_sicario_loop`) shares OSSY and G4 with the real card, so card answers can slow. Off by default, never run yet.

## Not tested live yet

Split PoP Run-instead; PoB quarter lines in chat; Endless; a cloud Browser window at the new size; signed-in phone; the final PoStatic studio on screen; agents really opening the site lists. Fee's public desk is still 3,600 px tall. Sicario's has no wallet, so it cannot pay through SingIt (asked by the owner, unanswered, likely moot now since they run local).

---

# WHAT'S LEFT

### 1. Agents (8)
| ID | Status | What |
|---|---|---|
| W02 | OPEN · FIRST | ✅ 2026-10-30 part: a real RECOVERY PIN (`backend/cat_recovery.py`) rebinds an agent to a new browser, hash only, never moves money. A user-held signer below is still open. OWNER 2026-10-30: "FEELESS provides a TRUE SECURE encrypted generated key for each user (I keep the root key safe)". Today an agent wallet = Crossmint smart wallet, admin signer = our API key → NO user-held key exists (the old random 'recoveryKey' was fake and is removed; SafeKeeping tells the truth). Build: per-user signer the USER holds — options: Crossmint delegated / passkey signer on the smart wallet (no custody change), or Turnkey / Privy embedded wallets with export (user can export their key). Avoid FEELESS generating + storing raw private keys (custody, DECISIONS #2 counsel). Wire: create → user signer → export screen ("save it, only chance") + confirm box (built: SafeKeeping) → withdraw signed by it. |
| A01 | OPEN | Fix-agent: Lag catcher + Support issue → investigation → branch fix → before/after visual preview → owner review. |
| K01 | VERIFY | One user key vault in Familia (FamilyHQ keys tab). Owner card shipped earlier. |
| A02 | OPEN | NSFA: at most five learning agents, ledger-based sizing/generation vitals; user Fuse dashboard with two charts, up to three agents and intake levels. Reconcile existing work first. |
| A04 | OPEN | Cat learning/accept-loop parity with NEXA; G4 Models layout; trench theory only after shadow testing; launch-a-cat violet visual pass. |
| Q23 | OPEN | Price-gap engine: a live drawn view before buying, then the buyer's own running engine. Ships with buy guards. |
| OR01 | VERIFY | Folder ⚙ has Shorten long chats (context-compression) and Repair broken plans (response-healing), both off by default, OpenRouter calls only. Real calls on a free model: answered, $0. Not proven: a paid model and its cost (W05, no credit); a SingIt call does not use them. `web` is deprecated by OpenRouter and file-parser has no PDF input here, so neither is offered. |
| ST02 | OPEN · OWNER | Stash cloud mirror. Free tiers are small: Cloudflare R2 and Backblaze B2 10 GB, Storj 25 GB (third-party comparisons, check before relying). Needs your account and key. Local disk holds it until then. |
| AG20 | VERIFY | OSSY and G4 are ONE agent, Sicario's (minds OSSY + G4; `_sicario_merge`), paper, no wallet, private: off the public wall, monitors and desktop on HQ's Sicario tab, no folder (owner 2026-11-05). Filed PoW #1 $LEEROY −11.3%. Assigning to users' agents later. |
| MB02 | VERIFY | `markFoldSplit` splits every terminal tab at the crease on an unfolded fold; 128 page views clean at 4 sizes, signed out. |
| LG01 | OPEN | Move the Pool ledger from one sealed file to a database before about 10,000 members. Measured at 100,000 members: a tick takes 0.39 s, but each fee rewrites a 46 MB file (0.51 s). Safe, too slow at that volume. |
| BD02 | OPEN | Bids and browser wins sending to the Pool. Only a real PoW can send today, since it is the only one the chain proves. Needs the agent's Polymarket or site address on file and one real read of its public record before a bid can send. Perps stay paper (owner). |

### 2. Trading and money (9): needs real money, a provider's rules or a lawyer before it can be proven
| ID | Status | What |
|---|---|---|
| L01 | OPEN | AutoRange: Orca as third venue(ONLY USA ALLOWED), DLMM positions wider than 69 bins, compound LP fees; reconcile older tight-range/re-center requests against shipped Meteora/Raydium implementation. |
| P01 | OPEN | Perps: limit orders, owner fee controls, Coinbase Advanced door; additional venues only through approved eligibility flow. |
| B01 | OPEN | Brokers: Kraken/Coinbase own-key doors, YOUR MONEY totals, options; broker perps only when supported. |
| R01 | OPEN | RepMarket user sign-in/key and deposit flow; verify the permitted product/API before implementation. |
| LA01 | OPEN | Launch: selected-venue configuration and any supported quote pair. (The coin/pools switch and Range Lab before signing shipped in LaunchModes.) |
| C05 | OPEN | Leverage: complete position-row handling and one-transaction loops. Verify existing close flow with owner-authorized use. |
| C06 | OPEN | Provider fee configuration for perps/LP/run/leverage/launch; no invented referral fields. Zora execution needs a supported venue. |
| Q04 | OPEN | Fee-Back eligibility, valuation/reference timestamp, settlement, rounding/distribution policy and audited payouts. Treasury buy/burn executor. |
| Q06 | OPEN | Feature-level geo/KYC switches guided by the existing decisions and counsel. |

### 3. Familia, city and games (7): the owner's "after" batch
| ID | Status | What |
|---|---|---|
| C12 | VERIFY | Alliances live in Support, from a chat reply; owner sets the days. Signed create not clicked live; reads and tests pass. |
| G01 | VERIFY | Real CC0 guns (Kenney), played signed in, no console error. Camo/PBR extras not added. |
| T01 | OPEN | HQ Telegram center: bot rooms, alerts/trading/community/security, Mini App setup; FeeCat-art idle RPG and slot game hub. |
| C01 | VERIFY | All 28 Familia buildings clicked signed in, each opens real content. |
| C02 | OPEN | Familia: live building P&L, real-money/MP errands, rank/badge pools, custom backdrops; drag within 3D block, new islands/bridges/lots/kiosks and saved family layout. |
| C03 | OPEN | Block readers: Meteora DLMM, marginfi, Save, PumpSwap LP, Phoenix; construction state when funds removed; opt-in member positions. Verify each against an actual account. |
| C04 | OPEN | Night Vault: DCA/limit orders, compound LP fees, retire old MP drag-errands/catalog; outer-city markets, held/launched coin buildings, in-city raids, MP buildings/ladders, MOBhouse and for-sale island. |

### 4. Site and infrastructure (6)
| ID | Status | What |
|---|---|---|
| Browser | open the pane only to look, then close it. A hidden pane reads 1 fps: never trust that number |
| OSSY01 | OWNER REVIEW | Measured 2026-11-05: the seat prompt is about 1,900 tokens (SYSTEM 1,750 + persona 150), not 300. It is static and sent first, so it already caches. All of it is real-money trading rules, so any trim rewrites those rules: not touched without the owner's word. |
| FC11 | OPEN | Hive crawl engine (owner said GO 2026-10-31). OWNER: save X once in an agent's signed-in sites so traders can read X searches. |
| Q01 | OPEN | City FPS measured 2026-11-05 (dev build, signed out, real M3 GPU, load 5): plain control page 60, /familia 59–60 at 1440 and 466 wide, 0 long tasks. So instancing/LOD is not needed yet. Still open: signed-in city (the owner's Chrome window was throttled, 15 fps on the control too, so that reading is void), load tests, database and multiple workers. |
| Q02 | OPEN | Split `reputation_service` safely (the supervisor part shipped: `start-backend.sh` starts the watcher). |
| Q03 | OPEN | Whitepaper done (9,855 → 2,603 px). Familia side wall trimmed. Trench report posts cut to a one-line header plus short rows (code only, not seen live; the next post shows it). Still to do: FeeCat stage/tabs and perf, lore/launch flows, 3D roadmap, faster model reads. HQ and Familia still need a signed-in measure. |

### 5. Waiting on you (24)
| ID | Status | What |
|---|---|---|
| SR01 | OPEN · OWNER | 📚 Sources found, not wired: AgentMail (3 free inboxes per its docs, sturdier than mail.tm), Postiz / Blotato / Zernio / Ayrshare (post through official APIs), MoonPay Agents, Onramper. Each needs an owner account + key. |
| SR02 | OPEN · OWNER | 💳 Agent cards, not built: Crossmint (we already use it for wallets) launched Agentic Cards in June 2026, Alchemy has AgentCard (Visa). Both need an account, terms and likely KYC. Next step: ask Crossmint for pricing and whether USDC from an agent wallet can fund a card. |
| AG11 | OWNER | 🎨 Creations drawer works. `make an image of …` is built with fakes, but the one real call was refused: OpenRouter needs at least $1.00 in the account for image output. Top it up at openrouter.ai/credits, then it can be tested and added to the command list. |
| SI31 | OWNER OK | **One paid PoW + one paid PoP.** Also proves FC12 (sign-in, hand-off, sealed download, Stop). Everything else in Supreme Intelligence and today's PoP work is built and tested on fakes; this one run proves it live: SI01–21, 25, 29, 30, 34, 36, 37, 40, 41, 42, 44, 45, 46, 48, PF01, B02. Full text of each is in history. |
| CH04 | OWNER | **Live ticks are limited by the key.** `PRICE_STREAM_WS_URL` (Helius) answers 429, so the stream falls back to the public node + one Alchemy fill a second (`stream_lanes`). Measured on $GATO: 3 to 6 prices in 45 s. Per-trade needs a stream key with quota; the keeper's Helius key is not used for this. Drawing is not the limit: 60 fps, 0 long tasks (headless, dev build). No 30 fps easing: it would draw prices that never traded. |
| FC06 | OWNER | Agents' EARLY calls (OSSY / G4; NEXA retired): call a coin while it falls toward the germ floor or just as it breaks out, not only at the floor. Real-money buy-rule change ⇒ edge-audit it first, owner approves. Today the desk models read a TEXT chart snapshot (`ai_snapshot.py`), never an image; OSSY (gpt-oss-20b) is text-only; G4 (Gemma, LAN) can take a chart IMAGE → add a rendered 1m chart PNG to G4's ask. OWNER 2026-10-30: YES — they need the image snapshot (add to the desk workflow). |
| P11 | OWNER | Lag 2026-10-30: reputation loop blocked 68 % of 24 min (Lag catcher) while the Mac swapped 13 of 14 GB (24 GB RAM: LM Studio gpt-oss-20b 12 GB generating, ChatGPT/Codex, two dev servers, 6 stale preview servers from old sessions on :51412 :51433 :51437 :51399 :51411 :51431). Fixed in code: `reap_orphans` off the loop. Owner: close what isn't needed / move OSSY to the LAN box. |
| MAC01 | OWNER | Checked 2026-11-04: 210 GB disk free, swap 4.2 of 5.1 GB. Ours is small: rebuildable `frontend/node_modules/.cache` 1.8 GB, 3 worktrees 314 MB (nothing deleted). Left for you: Spotlight privacy for the project; the watcher keeps restarting LM Studio (3 times in 16 min this morning), likely the swap; `scripts/trim-mongo-caches.py` is untracked and not run. |
| SEC01 | OPEN · AFTER the owner buys his first general agent (owner 2026-10-30) | FULL SECURITY HARDENING, front to back: prove nothing in the frontend bundle reaches backend secrets (no keys/tokens in JS, every write endpoint signed + owner-checked, CORS/CSP/headers, rate limits, SSRF + path guards, dependency audit), confirm encryption at rest (Fernet vault, BROKER_SECRET_KEY rotation) and in transit (TLS). Add 3 free defensive services layered so an attack only gets slower with no sure outcome (e.g. Cloudflare free WAF + bot fight + rate limiting, Cloudflare Turnstile on sign-ups, GitHub Dependabot/CodeQL secret + code scanning) — defensive only, no counter-attacks. Report findings + fixes. |
| FC13 | OWNER | Dropbox: the app was made team-scoped; make a new Scoped access app and add the redirect `http://localhost:51367/api/cats/cloud/callback`. Pump.fun wallet launch stays your wallet's signature, never an agent's. |
| FC14 | OPEN + OWNER | User withdrawals from the Pool ledger, not built: a lawyer first, then a payout wallet with a daily limit. The ledger and live count run (CP01). LP deposits and on-chain staking also not built. |
| W05 | OWNER · BLOCKS PAID AGENT CALLS (checked 2026-11-04) | The FEELESS OpenRouter key can afford only 271 tokens (real 402). Add credit at openrouter.ai/settings/credits. Guards live: credit sales stop under $5 on OpenRouter (`cat_fund.credit_open`, `_openrouter_left`), the owner gets one alert a day, each agent stops at $0.10 of its own credit (`launch_cat.CREDIT_RESERVE`). FEELESS model credit is a ledger number and does not top up OpenRouter. Design gap: paid model credit lands in the FEELESS fee wallet, nothing moves it to OpenRouter. Then re-run the 2 + 2 test ask and the small real trade round trip. |
| V01 | OWNER | Backdrops: ocean.mp4 is in (Mixkit 25163). Mixkit blocked the other 3 automated downloads → save by hand from mixkit.co (Download, 720p) into frontend/public/backdrops/: forest.mp4 = 25158, peaks.mp4 = 4396, aurora.mp4 = 4038 (see LICENSE.txt). Until then those scenes are drawn. |
| C13 | OWNER | "Circle wallet to FEE": confirm = a Circle developer wallet for Fee (the leader cat, creator-owned, like the Crossmint agent wallet) — needs a Circle API key; per-USER Circle accounts stay blocked on counsel (DECISIONS #2). |
| M01 | OWNER | Real device check on Safari and the Duo. Automated 2026-11-04: 20 pages at 360, 466, 678, 890, 1440 px: no sideways scroll, no crash, no dead route. Popups: 16 pages at 360 and 466 px, first 22 buttons each, writes blocked; fixed the shared dialog (taller than a phone) and the desk picker (clipped). |
| D01 | OWNER | Public hosting, domain, HTTPS, production configuration and provider keys. Validate deployed endpoints. |
| H01 | OWNER | HQ tabs: unread folding, hidden '—' cells and one screen per tab need your screenshots of what bothers you. Harness and crash guards are done. |
| Q25 | OWNER | Charts-first is live on Fee's and trader desks. No cat shows on a profile today, so "FeeCat on a profile is a pop-out" needs your reference: which profile, and what you tap. |
| Q29 | OWNER | HQ › Fees showed the swap fee at 1500 bps (15%) on 2026-10-29: confirm that is intended. |
| CH05 | OWNER | Move agents and the real card onto true candles after a shadow test. They still read filled bars. |
| What | Value |
| What | Command |
| Area | Files |
| UI | `frontend/src/components/command/` (HQ) · `components/HomeEngine.jsx` · `styles/` (map in CLAUDE.md › CSS map) |

# WHAT'S BUILT

### 6. Built, needs one real run or your check (56)
| ID | Status | What |
|---|---|---|
| AG06 | VERIFY | PoP now reads sites in each mind's own window before it calls (coinglass, hyperliquid and others), each mind sees only its own read, and the folder shows what it opened. New PoB: `file a bid` or Bids › File a bid. Minds read sites, call a market blind, agree, then 50 free chips go on it and the market's result grades the folder. Tested with a fake browser and fake minds only; not run live (paid model and browser calls). |
| AG08 | VERIFY | `watch a wallet` files as a folder (PoW › 👁 Wallet watches): each address, the lines about it, Solscan link, one chain check (on chain / no history / not checked). Parser and check tested on fakes. Not run live (paid browser and model calls). |
| AG10 | VERIFY + OWNER | `build a project …` writes several static files, filed in Creations with a .zip and a sandboxed preview. A real free Groq call made 3 files and the parser took them; its script ran in a test iframe ($100 bill → $115.00). The chat-to-Creations path is fakes only and the Creations row is not seen on screen. A real dev server (node, packages) still needs a sandbox host and key, such as E2B. |
| SD01 | VERIFY | 🌐 Site door in every proof folder (`SiteDoor.jsx`, `site_scan.py`): type a site, Open + sign in by hand, Scan. A fetch reads terms, fees and help pages; a wall or no terms goes to its browser. Files a manual: meters, snapshot, Do / Don't / Withdraw / Fees / Bots / Regions / Risk / Pages, every line tied to the site's own sentence and source. Read + signed in earns `file a pump pow`, `file a polymarket bid` etc: its windows go there first, read only. Live on Happy's desk, signed in: Polymarket read 6 of 6 pages, real snapshot, worded by its model for $0.0022, CAUTION (bots banned). pump.fun stayed behind Cloudflare even with its saved sign-in: NOT READ, no command. Both manuals are still on Happy. Not run: a fresh hand sign-in, Open + sign in inside the folder, a site command through a real proof. Live finding fixed: "scanning" ended before the manual was saved, so the page missed it; fix is tested, not re-run live. |
| OD01 | VERIFY | 👑 Owner tab = two live monitors. FEE opens the same desktop agents get plus Lane, Brain, Prompts, Wallet + style. AGENTS opens Colony, Honeypot, PoW folders, Agent slots, Performance. Seen live on the owner's page, every app opened with content. Fee's Performance chart is empty because she files no proofs; her glass shows her paper record. |
| PF01G | VERIFY | 🫧 Every desktop has a see-through performance glass; tap it for a chart with crosshair, per-proof bars, table view. PoW SOL, PoP paper %, PoB chips are never added together. Chart seen only as the agents list live; the crosshair chart is tests and code, no real data shown yet on screen. |
| TU01 | VERIFY (owner testing) | 💸 `top up pump`, `top up pump $1.50`, `add $2 to pump`. It reads your deposit address in its signed-in window, or you paste it. Yes / No / amount in chat or card. One SOL transfer from its own Circle wallet, $0.50 to $25, keeps gas. A page-read address needs its last 4 typed. Manual shows LOADED: the address's on-chain balance. Fakes only: no real send, no real address read. It cannot use the site's own deposit flow, only an on-chain address. |
| IC01 | VERIFY | 🧊 3dicons V1 + social, white cut out, 1 MB total, on our own origin. 1,019 rendered symbols and 200 line icons swapped outside Familia. Small controls (close, menu, arrows, checks, copy, refresh) stay line icons. Emoji inside strings (button words from data, chat lines, the "Fuse 🧬" nav titles) are not swapped. 15 pages, signed out, headless, dev build: 60 fps, no broken icon, no console error. Signed-in pages and phone not swept. |
| PB01 | VERIFY | 🏈 `file a pob best NFL picks`, or type a topic in Bids. Each mind opens major sites for that topic (ESPN, NFL, CBS, Action Network, Covers, Kalshi, Polymarket), one snapshot per site, then calls up to 3 picks blind. The folder shows picks, what both agree on, snapshots; the owner marks it right or wrong. Nothing staked. Fakes only, not run live (paid calls). |
| DK01 | VERIFY | 🖥 Wallet + Limits moved from tabs onto the desktop. 12-step first-time tour pointing at the real icons, replay in Manual. Lamp over monitors. 3 new live backdrops in the desk's skin picker. Manual: PoB, Sites, Funding, Mail tabs. Shared glass for every folder window. Tour, lamp, Wallet seen live, night, desktop. New Manual tabs, Limits layout, PoB topic folder, live backdrops, day theme and phone not seen on screen. Wallet is still about 2,400 px tall inside its window, and Jobs and Files only got the shared glass. |
| BC01 | VERIFY (owner) | 🔥 Bot check after sign-in. Measured on Happy's real pump.fun save: all 15 cookies including `cf_clearance` load, and every NEW window is still walled (Kernel and Steel, routed or plain, 4 of 4). Cloudflare ties it to the browser that passed. Fix: save keeps that window open (`_WARM`, 14 min, Steel's 15-min cap), the scan and the first agent window on that site work inside it, unrouted. Open + sign in reopens the same window. After it ends, a new window hits the check again and hands it to the person. Never stealth or a solver. Tested with fakes; needs the owner's real sign-in + save. |
| TY01 | VERIFY | ⌨ Type-and-paste bar above every sign-in window (`signin_type`, `type_into`): Send, Paste, Hide, Tab, Enter, Delete, Its email, Newest code. Live on a real Steel window (httpbin form): email landed in the box, Tab moved on, next word landed. Never stored or logged. Not run on pump.fun. |
| ST01 | VERIFY (owner, real money) | 🛒 Trades on its own site account (`agent_site_trade.py`): `buy $1 of $BONK on pump`, `sell all $BONK on pump`. Owner's typed words only. Asks yes/no, or "No question" in the manual. Buys: $0.50 to $25, $50 and 6 a day, pool $10K, age 10 min, not up 300% in 1 h. Its window presses the site's own button once. Receipt from the chain when its site wallet is known, else UNVERIFIED. An order never resumes after a restart. Fakes only. NOT wired into the PoW loop yet: PoW still buys through FEELESS, wire after the first real $1 works. |
| PL01 | VERIFY | 🔁 Proof Loop (`proof_loop.py`): PoW drops a coin with the fingerprint of a past loss (source, pool, cap, direction; only ever trades less) and studies its last 5. PoB keeps one series per topic and tells both minds what they called and how you marked it. PoP studies its last 5. Fakes only. Bids on our board and PoP need real runs to show the loop chip. |
| PF02 | VERIFY | 🏆 Proofs folder on every desktop (`ProofsFolder.jsx`): results ring, 3D chart, loop orbit, PoI timeline with the decisions and snapshots at the time. Seen live on fixtures, night, desktop. Not seen on a signed-in agent, phone or day. |
| RW01 | VERIFY | 🎁 Rewards page `/terminal/rewards`, the sidebar's MOB & Rewards landing (`RewardsDash.jsx`): points, level, streak, claim all, The Hunt (closest badges), deposit to family bank (the shop's real `mp` items), trophy wall, shop, top points. Every button is an existing server route. Seen on fixtures at `/dev/rewards`, night, desktop. Not seen signed in, phone or day. |
| CH02 | VERIFY | 💬 Your question now shows the moment you send it (it was saved only when the task ended, 34 s later on the owner's 2+2). The chat box keeps 120 px beside any card. Fakes only: send one real ask to confirm. |
| SC01 | VERIFY | 🔒 Security audit 2026-11-04. Sound already: no plaintext cookies, passwords or keys in the store (checked on the real file), sign-ins sealed per agent, master key outside the repo at 0600, every door asks the wallet's signed session. Closed: public PoW/PoB snapshots (owner-only when signed-in or PoB, sealed on disk), public monitors showing a signed-in page, plain http (https only now), posting by any job (content only). Sealing is per AGENT, control is per WALLET: a key made only from a wallet adds nothing, addresses are public, and one from a wallet signature would stop agents working while you are away. Not done: an outside pen test. Terms text is a draft: have a lawyer read it. |
| PS01 | VERIFY | 🚀 Priority Setup (`agent_setup.py`, `SetupDeck.jsx`): 9-10 slides in Manual, auto-opened with a lit count on the Desktop buttons and the Manual icon. Use → email → sites by use → fund → limits → colony share (5-25%, signed; old 30% pays 25%) → posting → site trades → security → terms. Terms & security folder on every desktop. Seen on fixtures. Sign-in slide and colony signature not run live. |
| FD01 | VERIFY | 🧱 Folders measured in the harness: PoP 52→91%, Bids 64→93%, Jobs, Sources 14→94%, Mail 6→94%, Files 55→93%, Commands 19→93%, Wallet 2,141 px→847 px. Clickable vitals wall (`VitalsWall`), long boxes scroll inside themselves, cabinet drawers in a grid. Manual has a monitor beside each tab, its own data or marked EXAMPLE. Not seen on phone or day, or with a signed-in agent. |
| LP01 | VERIFY | 💡 Lamp rebuilt: bright tube, two cones, hot core. On while its windows work, a burst of static every 5, 23 and 45 s, a last burst then out when they finish. Seen on with fixtures; going out is tests only. |
| CL01 | VERIFY | 💎 Colony is now The Collective, its funds The Pool (owner 2026-11-04, honey dropped). Crystal on a pedestal, top 3 on the stage, the rest in glass hexes, each with a live pool bar; click rises it and opens its vitals. Seen on fixtures at desktop width. Not seen: real data, phone, day. Code names and API paths still say colony on purpose; some agent replies may too. |
| LS01 | VERIFY | 🐝 Colony loss shapes (3 losses, 2 sharing agents, under 40% wins) and 🧠 best mind per topic (3 graded calls each, a 15-point gap: it opens and has the last word on a PoW, both minds see the record on PoB and PoP). Tests only. Only Happy has closed proofs, so neither fires on real data yet. |
| CH03 | VERIFY | 🎭 Character folder on every desktop (`CharacterFolder.jsx`, `public/wireface`, 46 MB, loaded only when opened): 11 rigged stock portraits + 13 SDK characters + your own picture. Seen working: swap, expressions, tracker on a photo (82 ms). Not run: a real webcam or mic, upload save on a signed-in agent. Wireface licence: repo LICENSE.md v1.0 allows paid products, but its website says charged services need Developer (£50/yr): OWNER confirm with sales@compsmart.co.uk. Realistic whole heads (their Heads page) are not in the SDK and not licensed to copy. |
| LV01 | VERIFY | 🔴 Go live (`agent_live.py`, socket `/api/cats/{id}/stream`, ffmpeg): the real canvas reached a local RTMP receiver as 720p H.264 + AAC. Not run: a real Twitch, Kick or TikTok key (address allowlists unproven until then), the service socket with a signed session, Pop out. Stream stops if the tab is hidden. Max 3 at once. |
| VV01 | VERIFY | 👀 Visitors: proofs show (emails, phones, tx and wallet trails removed), mailbox and account pages show the blank security screen, other pages have emails, phones and password fields boxed out, any failure shows blank; owner sees raw. PoB snapshots stay owner-only (their names do not say the site). Tests only, no live signed-in page. |
| NM01 | VERIFY | 🪪 Names change once per 7 days, staff any time (`name_lock.py`): profile displayName + handle, agent rename in its Character folder. Stamped with a keyed signature, past names sealed. Current names stay readable: they are public and searched. Not covered: Circle owner edits (already owner-only), Familia names. Tests only. |
| AC01 | VERIFY | 💎 Auto-collect (was Colonize): signed once, each real PoW of +50% or more sends the signed % of its profit to the Pool (`_collect_pass`). Each send is read back from the chain (`collective.verify_tx`) before its receipt, link and boost. One proof pays once (Circle idempotency key = proof id). A manual proof send has the same rules; a reason-only send is a gift, no boost. Solscan blocks plain fetches (403), so the snapshot is a receipt drawn from the chain beside a Solscan link. Bids and perps cannot pay in: they are paper, no transaction. Tests only: no real send run. The owner's old signature does NOT carry over: re-sign. |
| PR01 | VERIFY | ✅ Every proof shows PROVED, NOT PROVED, a countdown or LIVE (`proof_stamp.py`), worked out from the result 24h after closing; a PoB on real games waits for finals and is graded from the scoreboard (`_pob_grade_pass`), never over an owner's mark. PROOFS list (5, dropdown to 20) in the Collective; visitors get one list of 5. Live scores tested with fixtures only. |
| CC01 | VERIFY | 💬 Collective convos (`_convo_pass`): owner opt-in, different owners only, once a day, 2 short model calls on own credit, max 3 proofs each, one joint call on something one of them traded. Market move of 2% that way in 24h = 5 boost points each. Tests only: needs 2 owners with agents. Boosts rank the stage; they pay nothing yet: OWNER decide what a boost buys. |
| RK01 | VERIFY | 🔑 Recovery key + 12 BIP39 words (`recovery_kit.py`): Terms & security folder, shown once, scrypt hash only, rotate any time. My agents > Recover an agent takes a new signed wallet; both burned after; wallet withdrawal held 72h. Older PIN still works. Not a wallet seed. Tests only, not run on a real wallet swap. |
| LV02 | VERIFY | 🔴 Live scene (`lib/liveScene.js`): browser Canvas + captureStream. Agent bottom left, right or hidden, S/M/L; monitors (visitor-safe frames), the 2 minds, chat (off by default) sorted before going live, preview is what is sent. Layout tested; the composed canvas was seen; a real channel not run. |
| TL01 | VERIFY | 🧰 Dashes (`proof_tools.py`, `ProofTools.jsx`) atop PoW, PoP and Bids. Real calls made 2026-11-04: ESPN, Polymarket, Kalshi, TheSportsDB (test key 123), DexScreener, RugCheck, CoinGecko, Hyperliquid, Coinbase, Fear & Greed, DefiLlama. The Odds API needs an owner key. "Best" = market odds, said on screen. A parlay tap fills chat, nothing is staked. |
| BA01 | VERIFY | 🎭 Build an agent replaces Build a cat: ants, flies and queen removed (`Critters.jsx` deleted). Fee keeps its panther. Old "cat" words remain in some deep agent copy. |
| FE01 | VERIFY | ✨ Features folder (`FeaturesFolder.jsx`, `agent_features.py`): demo per feature marked EXAMPLE, Create button, sealed folders. Build: chat to Mind A, B or both, Code or Static, sandboxed preview, drag to mark an area. Content: trending from 5 live sources, PoC, marks. Edge: 24 case files, 8 own Pine indicators, TradingView search (links only), Hyperliquid book, tape. Research: chat. Sources called live. No real model build run: it spends credit: OWNER test. Code use added to setup. |
| FP01 | VERIFY | 🧬 Fingerprint (`agent_print.py`): traits from every proof, weighed by result, fade over 30 days; owner sees contents, others a level only (checked on the live card). Computed from filed proofs, not stored separately. Its note and the case-file checklist go into PoW research: study only, every guard stays. |
| MM01 | VERIFY | 🧠 Memory in Features > Its mind: Start fresh (proofs, money, fingerprint stay), Let AI clean (one paid call), About you (read on every task). Tests only. |
| CT01 | VERIFY | 👑 Collective top: owners get their chart, boosts, payout weight, next move; visitors get the pitch with live numbers. Fixtures for the visitor; owner view not seen signed in. |
| AG12 | VERIFY | The command list now differs: a trader is offered proofs, watch a wallet and free reads; a General agent is offered image, page and post, and the free reads. Either still does what it is told. Word-matching tests only. |
| PP01 | VERIFY | `file a perp` / `propose a perp`. Each mind reads 2 of 8 free sources, never its partner's or its own last ones, measured against the Coinbase chart (`pop_sources.py`), with its own sealed fingerprint (`{cat}:pop`). Real proposal: Deribit + Bitstamp vs dYdX + Coinpaprika, $0.008, one mind passed so nothing opened. Real chart, sources and fingerprint seen in the owner's browser. A trade or card has not appeared live yet. Sources are API reads, not browser windows. |
| MN01 | VERIFY | Desktop Manual folder (`AgentManual.jsx`): step-through tutorial, trader vs general board, drawn PoW / PoP / fingerprint flows, live limits, code map. Tutorial and board checked at 360 px day on fixtures, flows at 1280 px; the rest by tests. |
| LAG01 | VERIFY | Measured 2026-11-04, dev build, load 3–5: `reputation_service` idles at 5.8% CPU (was ~24%). 9 main pages over 25 s, headless Chrome, signed out: 60 fps, no long tasks (a planted 200 ms stall was caught, so the measure works). Not measured: signed-in desks and a real window. Tell me if a page still feels slow. |
| FC09 | VERIFY | Agents read one go-to list (`agent_mail.SOURCES`): own mailbox first, then Tuta / GMX, Catbox / Filebase, GitHub, Bluesky / Mastodon. Human checks stay human. Prompt and tests only; no real sign-up run. |
| FC15 | VERIFY + OPEN | 📧 Desktop › Mail: Make its email (mail.tm, password sealed), inbox as plain text, codes pulled out; agents read it with tool `inbox`. mail.tm's public domain list answered live; no mailbox was made because making accounts is the owner's click. Open: cheap clouds an owner can buy with crypto. |
| F01 | VERIFY | FEEd v5 shipped 2026-10-29 (`FeedX.jsx`, `feed.css`, `feedPro.css`): 600px column, sticky glass header (For you/Following/Calls/Heat/Graveyard + 🔖, sliding underline), swipe source chips, composer with live CA coin card, ↑N new pill, post cards with live coin chip (→ Trenches floor) + call receipt, threads on a connector line, rail (search · pulse · trending · callers · who to follow · sites), mini-nav ≥1250, phone ✎ sheet + folding header, Duo split. Browser-checked desktop/360/Duo-wide/day/pop-out. Remaining: owner look on real phone/Duo; coin chips/receipts only seen via the composer (no coin posts in the live feed today). |
| A03 | VERIFY | Same-coin shadow ledger and fresh edge audit; repeat after ~50 newer model trades; diagnose G4 uptime. No claim of profitable unseen performance. |
| Q05 | VERIFY | Broader chain/indexer coverage, independent risk signals and moderation/identity claims from the old PRD; validate against newer implementation before rebuilding. |
| Q07 | VERIFY | Final site-wide click-through only after the relevant builds: day/night, 360px, lite/reduced motion, every step and empty state. |
| CP01 | VERIFY | 🪙 Pool ledger v3 (`collective_pool.py`, sealed, hash-chained, audited every 5 min). A verified send: 20% kept, the rest follows its PLAN with an exact amount and date: 1 week 70% back, 30 days 85%, 90 days 95%, or the Vault (nothing back, the biggest fee pot part, fading by half every 45 days unless it keeps sending). The fee pot takes 50% of real trade and task fees ONLY and pays 5% of itself a day straight into earnings. Stress test with made-up activity: a member gets $1.53 to $3.71 back per $1, about the same early or late except the Vault; at a tenth of the trading, $0.93. Not run: a real send, deposit or fee. |
| CP02 | VERIFY | 💵 Every agent fee goes to the Collective wallet, nothing to a FEELESS wallet: deposits and top-ups flat 10% (first from $50, staff free; the 5% rate and every-3rd rule are gone), trades 5% under $10, 3% to $100, 1% above (a sell is sized by what it cost), the flat task fee, the Agent Pass fee. The ledger counts each one only once it landed. Tests only; no real deposit or fee yet. |
| CP03 | VERIFY | ⚡ Boost: points scale per dollar sent (5 + $2 per $, max 60 a send), graded 0.5x to 1.5x by print strength (real results, recent most, about 10 proofs to read fully), fade by half in 60 days. A boost adds up to 5% back and up to 2x fee pot weight. Points can be spent: 10 points = a date 1 day closer, never under a third of its plan. Rank only turns the boost off. Whale limits: 3% of the pot per owner, earn limit per plan. Thin pool or twin-agent wins cannot send. Tests only. |
| CP04 | VERIFY | 👑 Collective HQ on Fee's owner desk (`CollectiveOwner.jsx`): tanks, covered check, money in, agents; every setting has a hover and draws its effect live beside it; Wallet + LP. Server-gated (403 to a stranger, checked live). Fixtures in the harness; not opened signed in as the owner. |
| CP05 | VERIFY | 🌊 Plan picker + the split drawn (`SplitFlow.jsx`): shows how much and by what date from live rules. `GrowthExample`: every plan side by side over a year with Even by day N, on members, send, trades and print strength. Boosts folder lists each send with its date, bar and spend-points button. In Auto-collect, Send to the Pool, Boosts, Collective, Manual. Fixtures only. |
| CP06 | VERIFY | 🪙 Owner's Collective Boost coin: three.js 3D in Boosts (drag to spin, pauses off-screen, flat under fx-lite), small on PoW, PoP, Bids, The Pool, Boosts and Proofprint icons, small in the Collective. Live count in Boosts, on the desktop chip and in Proofprint. Seen on fixtures; no real count yet. |
| PP03 | VERIFY | 🧬 Proofprint from the owner's design (Proofprint.jsx, lib/proofprint.js). One print per agent for life: a keyed server seed picks 1 of 30 patterns and 30 inks, then bends every curve, core and ridge break, so no two match and nobody chooses one. Each proof is a green, yellow or red section; a bigger result takes more of the line; ridges grow outward. A click on the line opens a card wired to that spot, in the folder and on the desktop; a click anywhere lets go. Folder: print code, replay, kind filter, stats, what it earned, what it reads, every proof with best 2 snapshots. In the Collective: a mini per agent + one overall, only proofs really sent. Snapshots free on our disk, 10 MB today; a proof closed 14 days keeps its best 2. No paid fallback exists. Fixtures only; overall print reads the last 20 proofs. |
| PS02 | VERIFY | 💻 PoStatic proves first (`proof_tools.build_refs`, `_ws_run`): reads the best current builds (GitHub, Show HN, free, real call made), checks each is reachable, one small paid call for a plan, waits for approval, builds, the other mind reviews, files with its plan and references. Per-folder ⚙: research, suggest, review, depth. Not run with a real model. |
| PC02 | VERIFY | 📣 PoC creator desk: report a post's link and what it earned (owner-entered, labelled so), totals, best earner. Snapshots of posts not built. |
| EV01 | VERIFY | 🖍 Evidence marks (`evidence_marks.py`): snapshots box what was really found on the live page, list what was missing, and carry a fingerprint. PoW, PoB and PoC. Run on a real page with local Chromium (Hacker News). Not run in a real proof. |
| PC03 | VERIFY | 📸 PoC snapshots what it found, free, with local Chromium (`free_browser.py`): 3 public pages with its trend words boxed. Needs Chromium on whatever machine runs the service. No real PoC run. |
| CX01 | VERIFY | 💎 Each proof that paid the Collective has its own Collective folder: the send on Solana Explorer with signature and result boxed, the chain receipt, amounts, links. Solscan blocks automated browsers and we don't bypass it, so Solscan is a link. Explorer tested on a real transaction; no real send yet. |
| ST01X | VERIFY | 🧊 Collective Stash (`collective_stash.py`): every closed proof won or lost plus snapshots, compressed, sealed, deduped, indexed on our disk; it only adds. Visitor-safe copy only: signed-in pages never go in. Terms V3 says so, and an owner's proofs go in only after they accept. The crystal opens a live web of categories and sources; Collective HQ › Stash shows disk. Tests plus one live pass. |
| DS01 | VERIFY | ⚙ Desktop settings folder: background color (6), Alive, Still or Off, brightness, Proofprint and name on the wall. Saved in that browser. Seen on the harness. |
| PL90 | VERIFY | 🔁 One loop for every proof (`proof_plan.py`): Clarify, Research, Decide, File, Grade, each kind with its own steps and fallback, shown in Proofs. It asks one question in chat first, with answer chips; per-kind Asks first or Just does it. PoB: one search, 4 sites, 3 to 6 steps each (told to the mind, not hard-enforced), and free scores and odds when it reads too little. Tests only. |
| BU02 | VERIFY | ⚡ Live boost dollars: what its boost really added, counted live beside its earnings, on the desk and the desktop. Tests only, no real send. |
| DK02 | VERIFY | 🖥 The desktop opens nothing on its own (Manual and Vault used to, and could land on top of the folder you clicked). Its real cursor already moves; it now has a glowing ring. |
| CP07 | VERIFY | 💸 Faster earning: the pot pays 10% a day, a send earns on its whole amount until its date, a fresh proof earns 3x fading by half in 7 days, and each plan shows Pays for itself ≈ N days from the real pot. The year sim shows After its own fees: without trading wins, the average member does not profit from the Pool alone, because all pot money is members' own fees. |
| PB03 | VERIFY | 🏈 PoB board: Everything or 12 leagues, live first, scores update; 60 top Polymarket markets by category with timers; real calls made. Photos only from Wikimedia Commons under free licenses, with credit, no logos; no match means no photo. A bid on an open market is graded when it settles. Not run on a real filed bid. |
| CH05X | VERIFY | 💬 Chat looks in ⚙: Classic, Clean, Bubbles, Feed, Just the agent; Match site, Day, Night; animations. Just the agent shows its real character (Wireface) if it has one, else its picture or mind, with thought bubbles. Bubbles and agent mode seen on the harness; a real character not seen. |
| CP08 | VERIFY | 🌍 Pool rework: 20% of FEELESS swap fees from regular traders counts as outside money for the fee pot. Nothing moves itself: Collective HQ shows what to send, you send it, paste the transaction, and it counts once the chain shows it landed. The sim shows the effect: in its example a member needs about $10K a day in site fees to end the year ahead. Tests only, no real transfer. |
| VD01 | VERIFY | ⚖ Five validators (`proof_validators.py`): Tally, Sherlock, Devil, Archivist, Judge check each sent proof from its record, no model, no cost. A failed proof is held: its plan still pays, but no fee share or points until you clear it in HQ. Names chosen by Claude from the desk's roster. Tests only. |
| MB01 | VERIFY | 📱 Phone shell (`lib/phoneShell.js`, `styles/phoneShell.css`): the page itself no longer scrolls at 360 to 890 wide, in either orientation (measured on 6 tabs, 7 sizes, was up to 4,347 px); only the tab scrolls. Follows the real visible height and the keyboard. Tab bar no longer covers content. Emulated Chromium only, not physical Safari or a real Duo. Crease split per tab still only on Trenches and HQ Agents. |
| DB01 | VERIFY | ⚖ Desk buys off (`deskBuysOff`, owner 2026-11-05): the desk's agents, OSSY and G4 make no new real buys, at all 4 doors: GO rows, switches, the AI seat, seat fills. Exits run as before; the owner's own picks and Gstop re-buys are not touched. Set once on the live card; old value saved; switch in HQ › Agents with a confirm. Source check plus settings test; not watched through a real tick. |
| TM01 | VERIFY | 📖 One explainer for every proof word (`lib/proofTerms.js`, `ProofTerms.jsx`): first tab in Manual, on top of Proofs. PoW, PoP, PoB, PoC, PoStatic, PoI, Proofprint, Proved, Collective, Auto-collect, Locked, Boost, Fee pot. |
| FE02 | VERIFY | 💻 Features: every demo in a real monitor. Build runs 3 real working pages in the locked sandbox (fingerprint playground, live desk, small game) with Running or Its code, plus the 5 strongest code models from our live list, with prices. Build prompt asks for finished, alive pages. Each page built files a PoStatic that the owner marks. Seen on fixtures; no real model build run. |
| PB02 | VERIFY | 🏈 `file a pob` with no topic now takes the 2 or 3 strongest sides of the first sport with games coming up, then runs as a normal PoB. Fakes for the pick; board itself read live earlier. |

### 7. Done and proven
Every finished row lives in `docs/FEELESS_HISTORY.md` (grep it, never load it whole).

- 2026-11-05 Collective HQ door: green HQ button › Collective HQ (shortcut, and Core tab); same `CollectiveOwner` as Fee's desk. Owner Desktop button now lands on the owner tab even while the desk loads. Harness tested only; no real owner wallet session.
- 2026-11-05 Browser folder (`BrowserApp`, agent desktop): its email + newest code + signed-in count, sign up or sign in (`SignedSites`), send it to browse (writes the job into chat). Type bar gains Your email, kept on the device only. Steel real call passed (201, released). No real sign-up run yet. Sealed Vault passwords are not one-click: a reveal needs a fresh wallet signature.

- 2026-11-05 Fixes on the owner's report: owner monitors opened behind HQ (z 2600 vs 4000), now over it. Collective settings rebuilt on Motion (`CollectiveSetup.jsx`): presets, tabs, real charts; sliders no longer one wall. Pool builder: pick the pair (FEE, SOL, USDC or any coin; FEECAT not needed), fee, lock; server `POOL_QUOTES`. Simulation with the real builder not run yet: needs the owner signed in; no pool was created.
- 2026-11-05 Bids: photos cycle from Wikimedia (links only, nothing stored, off-screen cards hold no image, one shared clock). Click any game: stats window (`GameWindow`). Chain: ESPN, ESPN second host, NHL/MLB official standings, TheSportsDB. Real run with ESPN cut off passed for NHL, MLB, NBA. NBA's own CDN refused us (403), left out.
- 2026-11-05 Source files per job (`agent_refs.py`; `agent_sources.py` is the older sources book, keep both): in each agent's prompt and its Sources folder. Sites that refused a plain read were left out.
- OPEN, owner's call: throwaway prepaid/debit card with Apple Pay for agents. Needs a card issuer account with identity checks and a lawyer look; not built, nothing promised on screen.

- 2026-11-05 `ProChart.jsx` = one result chart for the whole site (TradingView Lightweight Charts, free, zoom off). Agent monitors never zoom, owner included. Trade bar (`PowPnl`) on a monitor takes turns with its notices (`Turns`); toasts too. AGENTS desktop gains Sicario's, Prompts, Stash, Providers. Features › First sources (`first_rows`, `refsMine`): owner's sites on top; states come from real visits and sealed cookies, nothing is opened to check. Trade bar seen in tests only; no agent was in a live trade.

- 2026-11-05 Collective HQ is one page, no tabs (`CollectiveOwner.jsx`, `CollectiveSetup.jsx`): shadcn table/chart (`components/ui`), Recharts Sankey `MoneyCharts.jsx` shows how pay moves; users' `SplitFlow` uses the same flow. Rule: libraries first, never hand-drawn. Game window is the look to match. Other money folders not yet moved: Proofprint, StashWeb, Boosts tiles.

- 2026-11-05 Collective front page (`CollectiveLanding.jsx`, from the owner's lab file): the living print is one pre-drawn bitmap plus only the real proofs, so 12,000 cells ran at 60 fps here; real proofs light up with a wired card. React Flow proof diagram on live rules, owner colours saved for everyone (`/admin/collective-look`). Stash is a sigma.js bubble map (`StashMap.jsx`). Providers: click a row to enter a key (`/admin/provider-key`, listed names only; agent service needs a restart to read a new key). PoW folder = proof cards with a print and vitals, click to pop. Agent slots lists every agent. Coin thinner. Not tried with the owner's wallet: saving a colour or key.

- 2026-11-05 Real proposals on Happy, signed in as the owner in Chrome (PoB x3, PoP, PoC, PoStatic x3; 72 paid calls, $0.16 of Happy's own USDC; no bet, trade or post). Fixed what they exposed: NBA asked, NFL answered (`best_topic`, `sport_named`); a window out of budget lost what it read (`read_note`); minds shared one budget (`mindCaps` on reads); a first Build folder 500'd and "About you" could vanish because `_save` restored an old owner snapshot (`keep_owned`); provider stops at ~1,500 tokens so pages came back cut off and were filed blank (`_ws_page` continues, `page_complete` refuses); PoStatic filing raced the store's writer (`_WS_DONE`); session tokens in the access log (`_NoTokensInLog`; older lines in /tmp/feeless-feecat.log still hold them; the file is local and was not cleaned, and the owner should sign out and back in once to replace the session). Not run: a PoW, since Happy is on real money; its last real one was PoW #15. PoB still rarely has picks both minds agree on word for word.
- 2026-11-05 Click-through signed in: 21 folders on Happy's desktop, 9 on AGENTS, Collective HQ, no crash or console error. Signed-out page audit: 76 views at 4 sizes, nothing but 504s during a restart. Real Safari and Duo still owner (M01).

- 2026-11-05 MB02: fold split in the locked shell (`markFoldSplit`): on an unfolded fold each tab's blocks sit either side of the crease; seen on real touch emulation at 890×626, not on the device. AG20: OSSY and G4 are real paper agents with full desktops (`DeskAgents.jsx`, AGENTS › OSSY + G4). OSSY's first PoW proposed real coins; its browser windows stopped on the empty OpenRouter key (W05). Assigning them to users' agents still to build.

- 2026-11-05 K01: one key vault in the family HQ (`FamilyKeys.jsx`, HQ › Key vault), names and last 4 only. C12: Alliances (`alliances.py`, `AllianceBoard.jsx`, Support › Alliances, chat reply › 🤝 Alliance): 10 members, one per wallet, Union after the owner's days (default 30, set on the board). Route read live; creating one with a signed wallet not clicked.

- 2026-11-05 G01: Strike Zone guns are real CC0 models (Kenney Blaster Kit, licence in `public/models/guns/`), one per gun with scope, silencer and clip; stats unchanged, drawn gun stays as fallback; played signed in, no console error. C01: all 28 Familia directory buildings clicked signed in, each opens real content. AG20 proven: OSSY filed a full paper PoW ($LEEROY −11.3%, stop). Audit: 128 views on every real page at 4 sizes, 0 problems (not-found now counts as a failure).

- 2026-11-05 Agents pass (owner: "focus on agents until tested"). Fixed: PoW/PoP/Bids folders squashed to a 28 px row by a stretched grid; Fee's Brain folder crashed the whole desktop (privacy filter strips `setup`, playbook rows now use `name`); Browser page stuck in an auto row; wallet clipped at 360 px and mixed with brief/log. New: PoC + PoStatic desk folders (a created folder files there with thumbnails), Features starters, Collective landing per the lab file inside both Collective folders, Colors for the owner, stash as black space with every proof a dot, `collective_pool.project` + `/api/cats/pool/project` (real send/tick on a throwaway state) behind the Boost calculator, ProofKit (3 tools per proof folder from real folders), Fee opens as everyone sees her with an Owner only button.
- OPEN FINDINGS: (1) PoP: 4 of 4 Happy rounds filed no trade, because both minds must pick the same market and side ("long SOL vs long BTC"). So PoP tools stay thin. Owner's call: paper-trade each mind's call separately? (2) OSSY/G4 use OpenRouter/free, not SingIt: SingIt pays from an agent's own USDC wallet and Sicario's has none by design. (3) `/terminal/hq` is a 404 and LaunchLab links to it. (4) Fee's public desk is still 3,600 px tall. Not tested: a real cloud Browser window at the new size; signed-in phone (Chrome would not shrink, harness at 466 wide was clean).

- 2026-11-05 Agents pass 2. Live: growth math (`collective_pool.growth`, `/api/cats/pool/growth`, real send/tick) with Why an agent sends on the landing and in Collective HQ; no pool rule changed. Providers is a clean list. Every proof: own colour, own print per folder (`ProofPrint seedId`), own steps and own source file (`agent_refs.PROOF_FILES`, also in PoP and PoB prompts). PoB: team and player averages, season, career, last 5 (ESPN `team_sheet`, `athlete_sheet`), slip of legs, market gaps. Edge desk is trader only, the server refuses it for a general agent (owner: the answer to why two kinds of agent).
- FAKES ONLY until the test phase: split PoP proposal + Run the other call; PoB quarter lines in chat (runs in the 5-minute grade pass). Owner's Monitor test build was killed by my service restart; check for running builds before any restart (a stopped run now says so in its chat).

- 2026-11-05 Agents pass 3. PoStatic is a studio (rail + big screen, device sizes, build clock). Sicario tab: chart, old OSSY×G4 talk and old generations deleted (LifeLens gone), monitors + desktop on top, noir gold. Sicario's runs on the owner's LM Studio (`local/ossy`, `local/g4`, `_lm_call`, free) with an Endless switch (`_sicario_loop`, one proof at a time, 15 min rest, paper, no wallet; real trades stay on the Fuse card). Real fingerprint per proof (`ProofFingerprint`, `printHealth`: click for verdict, what it lacks, best and worst traits) replaces the decorative rings; each folder's mark is its own ridge coloured by its result. Proof folders: head + main + rail (`.prf`). Site lists per proof (`PROOF_FILES`, 86 places, `ranked` by Stash results after 5 graded, search + plug in your own), in the PoW, PoP, PoB, PoC and PoStatic prompts: look first, then own twist. Game window fits the screen, only the player list scrolls.
- Risk to watch: Endless shares OSSY and G4 with the real card, so card answers can slow while it runs. Off by default. `.env` LAN_LLM_MODEL names a model that is not loaded on the desktop; `_lm_call` uses the loaded one, the card's own route still reads `.env`.

# NOTES

## TASKS`, at the end). **Rewrite 🔁 NOW in place every session; a finished row leaves the list**
→ one line in `docs/FEELESS_HISTORY.md` (archive: grep, never load). Never start a second list.

Read this (2 min) → `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING) → `## TASKS` below (left first, built after) → `docs/DECISIONS.md` (before any money / custody work) → only the history lines your task touches
(`grep -n "<topic>" docs/FEELESS_HISTORY.md`).

> ⚡ EVERY SESSION (owner, 2026-10-15 — repeat in anything you hand off):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. FULLY redo what is asked (owner: "not half do, not some side shit").
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 🔁 NOW (rewrite this section in place every session) — 2026-11-04, production upgrade in progress
> **2026-11-05: the current state and next steps are in `# START HERE` at the top of this file. It wins over anything older below.**
> **Owner flow (2026-11-03):** keep working through the Supreme Intelligence list, stop for owner review after every 5–10 major tasks. Reference free sources before building. SI23–SI30 are in `HANDOFF.md` (A, B and C pushed, fixtures only for the visuals). SI31 paid PoW only with the owner's OK. Fixture FPS: `/dev/cats?general&wallet` in headless Chrome (`channel='chrome'`); a backgrounded pane reads 1 fps.
> **Next (owner: chop this list down):** 2026-11-04 overnight shipped PP01, MN01. SI50 closed: Fee's learned limits now apply only to Fee, and PoW #15 ran a real buy and sell on Happy ($Donkey, 0.008 SOL, −0.000586 SOL, plus 0.001514 SOL rent, since recovered). SI51 closed: an agent's own wallet closes its empty coin accounts every 10 min (`agent_trade.sweep_rent`; USDC stays open); Happy got 0.012106 SOL back on-chain. SI31 needs the owner's OK and closes the most at once. CH04 needs a stream key. Check the watcher before any restart: `bash scripts/background.sh status`; on 2026-11-04 it was NOT running and a kill left candles down. Watch real runs in Chrome through the Claude in Chrome extension: `localhost:51367/terminal/feecat/agents` → Happy Assistant; never restart `feecat_service` while a folder is open. New limits: change one and `test_pop.py` fails until `pow_kernel.VERSION` and the pin move on purpose. Fixtures: `/dev/cats?general&wallet`; a window fading in can screenshot blank, so wait 3 s.

> **Owner 2026-11-04, latest:** finish the whole MD without asking what's next, FeeCat and agent rows first, Familia last. Folder shapes stay; use the 3dicons packs inside them, never with a white background. New look = glass, live walls (`ShaderWall`), no huge text. Next rows: OSSY01, A04, FC11, FC03 (needs keys), Q03's FeeCat stage and lore, then the backlog by priority. OpenRouter credit (W05) blocks long paid agent calls.

> **Owner 2026-11-04, Collective:** all agent fees go to the Collective wallet. Withdrawals stay OFF until a lawyer has looked (FC14). Then Familia and city, in that order. `## TASKS` shows what's left first.

> **Owner 2026-11-04, Collective:** all agent fees go to the Collective wallet. Withdrawals stay OFF until a lawyer has looked (FC14). Then Familia and city, in that order. `## TASKS` shows what's left first.

**Verify in this order, one at a time, with the owner:**
| # | Task | Status |
| --- | --- | --- |
| 1 | Ask Happy Assistant "what is 2 + 2?" in chat. Label 💳 = wallet paid, 🛟 = backup answered (then read `/tmp/feeless-feecat.log`, `[agent pay]`) | Built. Never paid live |
| 2 | Add about $3 SOL (split 100% wallet), send `buy 0.01 SOL of $JUP`, approve it | Built. Never run live |
| 3 | Send `sell all $JUP` | Built. Never run live |
| 4 | Withdraw to the owner's wallet | Built. Never run live |
| 5 | First non-staff agent: confirm its deposit and trade fees land in the Collective wallet and show in Fee's desk › Collective HQ | Fakes only, UI seen on fixtures |
| 6 | Venice fallback (W06): needs the $5 top-up flow | Not built. Login tested live |
| 7 | Model share of the split arrives as USDC (today the agent swaps its own SOL) | Not built |
| 8 | Agents-tab fps recheck with the pane in view | Measured once at 41 fps |
| 9 | Then the rest of the queue: LAG01 chart overlays · MAC01 Spotlight · OSSY01 · SEC01 | Open |

**How agent money works:** funding = one amount, split by `creditUsd`, one signed tx (`cat_fund.plan`, `FundCat`). Creator credit is free and is only a FEELESS number. Model calls go: agent wallet USDC to SingIt per call (`agent_pay.py`, `_wallet_call`, `_thinking_money` swaps about 0.012 SOL when USDC is under $0.30) → OpenRouter (balance $0, its crypto API is gone: 410) → Groq free backup. Each agent stops at $0.10. Flat fees: `agentTradeFeeUsd`, `agentOtherFeeUsd`, `/internal/agent-fee`; staff pay $0.
**Accounts:** FEELESS Circle = sidecar 5111, never for users. Family + agent Circle = sidecar 5112 (`CIRCLE_TENANT=agent`), auto-started by reputation; never mix them. Crossmint is unused (api-key signers off). The engine's old store copy can't wipe owner data (`keep_owned`, `OWNER_KEYS`).

**Owner to-dos:** back up `~/.circle-agent/` and find the FEELESS Circle recovery file (`~/.circle` is empty) · rotate `CIRCLE_AGENT_API_KEY` only if he chooses (it was printed in a session log) · per-user Circle wallets still wait on counsel (DECISIONS #2) · Spotlight Privacy for the project folder.

**Presets:**
| --- | --- |
| Push | `git push origin main`: the pre-push hook runs `scripts/gate.sh` once, path-aware. Never `--no-verify`, never edit during a gate |
| Restart | `kill $(lsof -ti tcp:<port> -sTCP:LISTEN)`, keep-alive relaunches in about 10 to 25 s (5001 · 5077 · 5088 · 5099). Check no pending book first |
| Never | move real funds yourself · run a paid call without the owner · kill the owner's processes · overlap gates · print `.env` lines (mask by NAME only) |
| Test harness | `/dev/cats?general&wallet` |

**FeeCat map:** wizard `command/LaunchCat.jsx` · desk `CatDesk.jsx` · funding, PIN, withdraw `CatReal.jsx` · workbench chat `CatWorkbench.jsx` · log `CatCockpit.jsx` · Fee's tools `FeeCatDesk.jsx`, `ProfileFeeCat.jsx` · one Fee door `FeeCatsPlatform.jsx › FeeDesk`.

## 1 · What this is
FEELESS = a Solana degen trading terminal. One owner, one REAL money card run by ten agents, plus a big site (trade, Fuse, Arena,
chats, FeeCat, Familia). Money rules are strict and tested — read `CLAUDE.md › Money rules` before touching anything that buys or sells.

## 2 · Run / check
| --- | --- |
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest` — it lacks the babel config) |
| build | `cd frontend && CI=false npx craco build` |
| all gates | run by the pre-push hook on `git push origin main` (path-aware; `GATE_ALL=1` forces all) |
| restart a service | `kill $(lsof -ti tcp:<port> -sTCP:LISTEN)` → the keep-alive relaunches it; then `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1 |
| real card cash | `backend/.venv/bin/python scripts/cash-check.py degen 30` (every task) |
| real card money trail | `.venv/bin/python scripts/fuse-report.py 6` |
| is there an edge? | `.venv/bin/python scripts/edge-audit.py` (run BEFORE advising on real-money buying) |

Services: `server` 5001 · `reputation_service` 5077 · `feecat_service` 5088 · `candles_service` 5099 · frontend 51367 (the owner's own dev
server — attach, never start a second). Push to `main`; the owner's Mac auto-pulls.

## 3 · Where things live (the files that matter most)
| --- | --- |
| agents (the real card) | `backend/agents.py` · `office.py` · `office_edge.py` · `trench_kernel/` · `opportunity.py` · `capital.py` |
| keeper (signs, sells, books) | `backend/fuse_wallet.py` · `arena_prime.py` (tier engine) |
| AI | `backend/ai_router.py` (providers, `with_studio`) · `prompt_studio.py` · `model_desk.py` · `ai_rig.py` · `ai_chat.py` (Brain) · `nexa_desk.py` |
| owner's LM Studio | `backend/feeless_mcp.py` (read-only MCP) · `docs/lm_fee_prompt.txt` · `docs/LM_STUDIO_MCP.md` · `docs/FEE_BRAIN.md` |
| big service | `backend/reputation_service.py` (31K lines — grep, never read whole) |
| Familia | `family_city.py` · `family_world.py` · `block_markets.py` → `FamilyWorld` → `FeeCity3D` (`lib/cityEngine.js` draws `lib/cityPlan.js`) · `FamilyBlock3D` · `FamiliaTrade.jsx` · `FamiliaApp.jsx` · `paper_perps.py` · `clmm_range.py` |
| FeeCat | `backend/feecat_service.py` · `feecat_brain.py` · `cat_model.py` · `cat_real.py` (real mode) → `components/feecat/` · `command/CatDesk.jsx` + `CatReal.jsx` |

## 4 · How to work here (the owner's rules, short)
- Brief with the owner. Verdict, what changed, what was tested, what wasn't.
- Every money change ships with a test that fakes the network. Never hit mainnet or move funds.
- UI = m-* presets, transform / opacity only, day theme + fx-lite + reduced motion + 640px blocks.
- When you ship: its row leaves `## TASKS`, ONE line in `docs/FEELESS_HISTORY.md`, rewrite 🔁 NOW above.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
- Edge audit 2026-11-04: 31 of 1,066 rules positive on unseen coins, agents entered 0 of 3,000 calls. Many rules tested means chance winners: say so before any real-money advice.


**Agents first (owner 2026-11-04, in this order):**


Status: **OPEN** = requested; **VERIFY** = built, needs a real run or the owner's check; **OWNER** = key, account, signature or decision; **LATER** = needs a lawyer or audit first. Nothing here authorizes a trade or a payment.

**Perps (owner 2026-11-04):** no cheap venue with our keys, so agents only propose perps; the owner tests them by hand on the Crypto.com app. No agent perps sender gets built (FC04 closed).

### Supreme Intelligence upgrade — owner request 2026-11-03

Objective: improve the existing autonomous, model-replaceable research system through verified evidence and measured outcomes. Preserve independent two-mind/four-coin PoW, guarded trading and a model-free Colony. The owner subsequently authorized tested production pushes to main and the 51367 checkout, without stopping their running command. No request here authorizes a trade, treasury transfer or CAPTCHA bypass.

The owner's complete request is preserved in [SUPREME_INTELLIGENCE_REQUEST.md](SUPREME_INTELLIGENCE_REQUEST.md); this queue tracks its implementation.

**First ten, in implementation order (this pass):**


**Second batch requested, in this order (2026-11-03):**

| ID | Status | Deliverable and current evidence |
|---|---|---|

**Next ten, in order (2026-11-03; corrections are at the end of the request doc):**


**Owner cleanup 2026-11-03 (no duplicate designs; snapshots):**



**Mechanics pass 2026-11-04 (each built backend first, then its screen):**


**Live PoW #14 debug + pPoP, 2026-11-04 (watched on the owner's signed-in page):**


### Owner batch 2026-11-04, overnight


### Owner batch 2026-11-04, second pass (charts, cleanup)


**Owner batch 2026-11-04 (PoP folders, Bids, charts, backend):**


**Found in PoW #14, not changed (trading decisions, owner's call):** it picked $ANONVOYAGE with 0 verified facts and one snapshot, because its research hit a wall, and would have bought anyway. A pick with no verified facts should probably not buy. The chat says 0.01 SOL while the wallet cap sends 0.008. A dropped buy closes the folder and never re-buys. The agents list still shows an old `BUY $FLOAT · 1 to sign`.

**Still open from the full request:** FEE CAT Command Center rebuild; persistent shadow proposals beyond completed trade intervals; out-of-sample method comparison/combination and rollback; model-assisted memory migration and strategy comparison; unified kernel resource limits; real browser duration, evidence completeness, FPS and challenge-recovery baselines; authorized cross-worker sessions; transferred/distributed Colony reconciliation; versioned contracts and safe legacy encryption migration; responsive command-center redesign. The plaintext legacy agent store is restricted to owner-only file permissions; full encryption requires updating its many cross-service readers safely. Do not mark these complete from synthetic tests or visual labels alone.

**Security audit finding:** new per-agent PoW archive entries and saved site session contexts use the existing per-agent Fernet seal. Legacy archive entries and the main agent state file remain plaintext on disk; a careful, versioned migration with backups is still required before claiming full at-rest encryption. Public archive replies now omit private plans, browser steps and exact page excerpts. No claim of complete encryption is made for this pass.

### Owner requests 2026-10-30 — queued (FeeCat tabs came first and shipped; see HANDOFF 🔁 NOW)
| ID | Status | Task |
|---|---|---|
| FC03 | OPEN · OWNER FIRST (2026-11-02: only Happy has a key saved — Helius; no Birdeye / X / Telegram keys exist, so those reads can't be proven) | Wire the stored drawer keys into the brain (Birdeye holders, Helius RPC, X chatter, Telegram calls, signal webhook) — each read guarded + faked in tests. |

### Build next — latest owner priorities

| ID | Status | Specific remaining work / done when |
|---|---|---|

### Product and engineering backlog

| ID | Status | Specific remaining work |
|---|---|---|

### Owner prerequisites and verification

- Physical Safari/Duo review (M01); first funded wallet-signing checks belong to the owner.
- AutoRange $25 open/re-center/close; Jupiter perps open with TP/SL, partial close and TP move; broker paper key then authorized real link; Kalshi production metadata/order check; $5 bridge round trip and $2 gas fill; leverage open/close; first $5 Run deposit; FeeCat signed proposal. These are recorded requests, not actions performed in this session.
- X client ID/secret and callback domain; public site URL; launch-rule signature; DFlow, SnapTrade and LaunchLab provider keys; Telegram token/group/Mini App URL; Crypto.com Exchange keys; sufficient RPC quota and additional Jupiter read key.
- Contract path: week-long devnet soak with keeper host, external audit, upgrade-authority decision, capped mainnet deployment and launch settings. GO_LIVE is a technical checklist, not evidence these steps passed.
- Counsel review of custody/sign-once agents, legal venue eligibility, on-chain cat/pot programs and real-volume readiness. Preserve the current wallet-signing model until approved changes.
- Clarify older owner questions: remaining Fuse bug reproduction, Fee City fullscreen preference, Desktop-cleanup folder scope.

### Ideas — not approved implementation
- Stronger agents (2026-11-04): each mind keeps a track record per topic, and the next proof goes to the mind that is best at it. Colony-wide loss shapes: an agent that shares its winnings also gets the fingerprints other agents lost on. Size only by a mind's record on unseen coins, and only ever down. A weekly self-review that drops the sources and steps that did not pay.

Ticket-sized manual picks while record is red; automatic initial-out on winners; 30-minute hand-pick acknowledgement; fed/trending overlap; proven smart-wallet follow; FeeCat + agent pair conversations; better-coin track. Never remove Pump/New-launch tabs based on these old suggestions without a fresh request.

### Conflicts resolved for planning

- Older HANDOFF/CLAUDE statements that “everything is built” conflict with their own open lists. They are not a completion certificate.
- Duo per-tab implementations and the page watcher were subsequently committed. Treat them as mobile verification work, not wholly unbuilt features. Agents still needed this refinement.
- FAMILIA_PLAN is an older specification, not a claim the entire current city is unbuilt. Preserve its detailed requirements; verify gaps against code/history.
- Old PRD claims about unauthenticated chat/local-only features may be stale. Q05 is verification before new work.
- Circle/house-wallet notes differ across REQUIREMENTS, GO_LIVE and DECISIONS. Reconcile owner-only operation versus user custody before implementing; a cap setting alone does not resolve that distinction.

### Source map

CLAUDE's former CURRENT TASKS is preserved below for exact wording and the detailed FEEd specification. Supporting specs remain in HANDOFF, REQUIREMENTS, PERPS, BROKERS, GO_LIVE, FAMILIA_PLAN, REAL_CATS, DECISIONS, COUNSEL_BRIEF, DEGEN_PLAYBOOK, TELEGRAM, memory/PRD. FEELESS_HISTORY is evidence of older work, not a second active queue. Technical architecture/runbooks and .agents memory remain reference material. Update statuses here rather than copying another task list into those files.



<details>
<summary>Original owner request ledger (archived wording; statuses above take precedence)</summary>

### Old asks still open (from the 2026-10-29 lists; finished ones and repeats went to history)


**Standing rules:** US users only reach venues allowed for them. The user's wallet signs real money; FEELESS holds no keys or pooled funds. Every new buy door ships with guards. Touching a page means its whole flow. Money surfaces lead with the aggressive play and name the risk.

**Lawyer first:** a perps partner API, on-chain cat or pot programs, do-anything agents, real volume (`docs/COUNSEL_BRIEF.md`).

