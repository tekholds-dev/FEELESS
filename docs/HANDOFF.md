# HANDOFF — THE ONE PAGE (owner 2026-11-09: every request in three blocks: AGENTS · COLLECTIVE · SITE)

> ⚡ EVERY SESSION (owner, repeat in anything you hand off): **1. Conserve usage** (grep first, read only what you need, batch, no essays).
> **2. Finish everything in priority order** (never leave a surface half done; one task at a time, proof, then stop).
> **3. Never dead-style** (prove no component renders a class before deleting it; every new box gets real styling and a live visual).

**How this page works.** One page, three blocks, one task list. Each block has: how it works now (from the code), its open rows in order,
its built-needs-a-check rows, and what the owner decided. A row finished AND proven leaves this page as one line in
`docs/FEELESS_HISTORY.md` (grep it, never load it whole). Never start a second list in another file.
**Merged 2026-11-09** from 54 MD files (this page, REQUIREMENTS, SUPREME_INTELLIGENCE_REQUEST, DECISIONS, FAMILIA_PLAN, REAL_CATS, PERPS,
BROKERS, TELEGRAM, GO_LIVE, ALWAYS_ON, ARCHITECTURE, AGENT_KERNEL, TRENCH_CREW, the guides, the leftovers and the history's open rows).
The full old text, word for word, is in `docs/FEELESS_HISTORY.md` under "ARCHIVED HANDOFF 2026-11-09". Old IDs stay in brackets so a grep
finds both. Nothing was dropped: a row is kept, merged with its repeat, or marked as replaced by the owner's later word.

**Status words:** OPEN = asked, not built · VERIFY = built, needs one real run or the owner's look · OWNER = needs his key, account,
signature, money or decision · LAWYER = waits on counsel · DECIDED = a rule, do not undo. Nothing here authorizes a trade or a payment.

**Rules for every row:** inspect the code first, never guess what exists · build locally, test, report, push to `main` only on the owner's go
(he tests on 51367; no dev-branch workflow; the main folder runs the live keeper) · never touch a money path without his explicit OK ·
never invent a test, outcome, cost or proof · no duplicate systems · leave every running service alone (51367, 5001, 5077, 5088, 5099,
5111, 5112, 8765, 27017, and nCheck on 3000).

## TASKS

---

# 0 · BLOCKERS ONLY THE OWNER CAN CLEAR (say these first in any report that hits them)

| ID | Blocks | What he does |
|---|---|---|
| W05 | Every paid model call, the cost side of model ranking | OpenRouter account credits are **$0** (live read 2026-11-09: credits 0, used $0.20; the key's $20 cap is not money). Add credit at openrouter.ai/settings/credits. Design gap: FEELESS model credit is a ledger number and nothing moves it to OpenRouter. |
| AG11 | Image output | OpenRouter needs at least $1.00 for images. |
| CASH | Any real-card or Sicario seat buy | Fuse card held 0.002565 SOL at last read. Fund it, then Auto-collect on Sicario's. |
| SEND1 | Every send, boost and payout path (all fakes today) | One real small proof send ($1+) by the owner. The Pool ledger has 0 real sends. |
| SI31 | Proves SI01-21, 25, 29, 30, 34, 36, 37, 40-42, 44-46, 48, PF01, B02, FC12 at once | One paid PoW + one paid PoP, owner OK'd. |
| LAWYER | Withdrawals (FC14), rewards by amount sent, profit share from a pool, earning from debate on top of a stake, team logos, tokenized stocks for pooled money, card fees on third-party cards, custody (W02, C13), perps partner APIs, geo/KYC (Q06), Terms text | `docs/COUNSEL_BRIEF.md`. Withdrawals and any cap on them stay OFF until counsel answers. |
| KEYS | FC03 (Birdeye, X, Telegram reads), CH04 (stream key with quota), DFlow (Kalshi), SnapTrade commercial, The Odds API, FC13 Dropbox app, SR01 (AgentMail, Postiz/Blotato/Zernio/Ayrshare, MoonPay Agents, Onramper), SR02 (Crossmint Agentic Cards / Alchemy AgentCard), ST02 (stash cloud mirror: R2/B2/Storj), C13 (Circle wallet for Fee), D01 (hosting, domain, HTTPS, production keys), T01 (Telegram bot token, group id, Mini App URL), X client id/secret, PUBLIC_SITE_URL, launch-rule signature, Crypto.com Exchange keys, RPC quota, second Jupiter read key | Each needs his account. |
| HOUSE | Machine and accounts | Back up `~/.circle-agent/`; find the FEELESS Circle recovery file (`~/.circle` is empty); rotate `CIRCLE_AGENT_API_KEY` if he chooses (it once printed in a log); Spotlight privacy for the project (MAC01); close extra apps or move OSSY to the LAN box when swapping (P11); clear the system prompt set inside G4's LM Studio; Gemma 4 12B (9.8 GB) can be deleted; purge the ~221 older plain files in the Collective GitHub repo (pushes never delete); contact Poly Haven as an integrator; confirm the Wireface licence with sales@compsmart.co.uk (CH03); save Mixkit forest/peaks/aurora by hand (V01); sign out and back in once (old session tokens sat in a local log). |
| LOOKS | Rows he must see | M01 real Safari + Duo, H01 HQ screenshots of what bothers him, Q25 which profile shows FeeCat, Q29 is the 1500 bps (15%) swap fee intended, the boost display (18.7 points vs his "187"). |

---

# 1 · AGENTS — the helpers: two minds, a desktop, a wallet, proofs

## How it works now (read from the code 2026-11-09)
- **Where:** `feecat_service.py` (:5088, 10K lines) runs every agent ("cat") and every proof. One store, `backend/data/feecats.json`: 5 agents,
  4 with two minds. Real folders: PoW 18 · PoP 5 · PoB 13 · PoC 7 · PoStatic 61 · PoEco 1, the "Example books" a Claude test filed on
  2026-11-05, not a real filing (`powFolders popFolders pobFolders pocFolders psFolders poeFolders`). Work runs as in-process tick loops (`run_engine`), no queue. A restart of 5088 kills running builds and proofs.
- **Agents that matter:** Fee (leader, creator wallet, opens as everyone sees her) · Happy Assistant (owner's real-money test agent) ·
  Sicario's (OSSY + G4, one private paper agent, no wallet, lives on HQ's Sicario tab).
- **Two minds:** per AGENT, `brainsCfg.brains[:2]` (feecat_service reads it in 70 places). Mind A leads / builds, mind B reviews; on 3D both
  take turns leading. Budgets stay per agent (daily $, credit, stops at $0.10 of its own credit, `launch_cat.CREDIT_RESERVE`).
- **Who answers a call (`_think`, owner rule 2026-10-31):** Fee / staff: SingIt from its own wallet → OpenRouter → SingIt free → Groq free.
  A user's agent: its own key / OpenRouter → its wallet on SingIt → the free routes. Never charges FEELESS's OpenRouter while the owner switch
  is off. **The configured model is not always the one that answered:** folders keep cost per mind (`folder.spend[i]`, `folder.cost`) but not
  the route. OpenRouter receipts go to `data/model_receipts.jsonl`.
- **Local minds:** OSSY = LM Studio on this Mac (:1234, qwen3.5-9b), G4 = LM Studio on the LAN desktop (qwen3.5-4b); both answered 2026-11-09.
  One call per machine (`_LM_GATE`), a call stops at 480 s, 4,000 tokens on the Mac, `_mac_cool` waits past load 12, a local page stops at
  10 min. `LM_ASKED_ONLY=true`: background router calls skip them; asked work on any proof is allowed (owner 2026-11-07).
- **The proofs it runs:** PoW (`_pow2_*`: 4 coins, minds blind, buys on FEELESS through the agent wallet with every guard) · PoP (`_pop_*`:
  each mind reads 2 free sources, calls blind, practice trade) · PoB (`_pob_*`: sites, picks blind, nothing staked, graded from finals) · PoC
  (`_poc_file`: trend sources, pitches, nothing posted) · PoStatic (`_ws_run`: plan → owner approves → build in sections → second mind
  reviews → real-browser look) · PoEco (`agent_eco.py`: sealed books, Python sums, a hash, no model unless he presses send).
  One loop for all (`proof_plan.LOOP`): Clarify → Research → Compare → Decide → File → Grade.
- **What a proof reads before it works:** `proof_book` (its site book per kind) · `agent_refs` (86 sites, opens the best 3 first, learns new
  ones) · `proof_kits` (10 FEELESS live-data kits) · `collective_kits` picks (auto by real record) · stash recall (`best_for`, `related`) ·
  `proof_footprint` (6 angles a kind, last footprints, fallbacks) · `proof_loop` (no repeat of a losing coin, best mind per topic) ·
  `prompt_studio` (GENERAL mind + PERSONAS) · `agent_knows` (product brief, no invented facts).
- **Desktop:** CatDesk / CatWorkbench, folders per proof, Git (Vault is a tab inside), Browser (cloud windows, manual bot-check hand-off,
  never a solver), Wallet (`WalletApp`, Circle agent tenant :5112), Features, Brains, Manual, Ideas, Debate, Watch, Py agents; the owner's
  AGENTS desktop folds by job (Money, Collective, Proofs, Setup, Performance).
- **MCP (:8765):** `feeless_mcp.py`, read-only, for LM Studio; the agents desk reads its tools list.
- **The real card's desk agents** (ten-agent kernel, `agents.py`, `trench_kernel/`) are trading, not proofs: see block 3.

## Open, in order (top first)
| ID | Status | What · done when |
|---|---|---|
| AGT-1 | OPEN | **Show the real payer.** Agents that pay through SingIt still show MODEL CREDIT (`CatDesk.jsx:173`, spend header :65). (desktop audit 2026-11-07) |
| AGT-2 | BUILT 2026-11-10 | Sicario's chats name both minds: the owner's own `GET /api/cats/{id}` was scrubbed like a visitor's (`_pub` turns OSSY / G4 into "FeeCat AI"). The owner (and FEELESS's own services) now read the real names; visitors still read FeeCat AI. Test: `test_owner_sees_minds.py`. |
| AGT-3 | OPEN | **New prompts by use case, or one overall** (asked 2026-11-06 and twice on 11-07). GENERAL mind exists; per-use-case prompts do not. |
| AGT-4 | OPEN | **Personalities per use case** (today one setting per agent, `prompt_studio.PERSONAS`). |
| AGT-5 | OPEN | **PoC and PoStatic: the user takes steps and asks**, with a quick preview and the tools used shown; PoC must be great. **PoC watch:** he picks the watch and its steps, it checks a few times an hour while doing other work, and a SHORT report lands after X hours (Live desk covers part). |
| AGT-6 | OPEN | **PoC and PoEco conversationalist:** mic voice-to-text, natural voices, fast replies; browsing quicker. |
| AGT-7 | OPEN | **Live code:** a real VS Code look with packages, a whole project, marked areas, fast answers, short prompts unless he asks for long. True token streaming changes the paid routes (`_wallet_call`, `_or_call`): his call. |
| AGT-8 | BUILT 2026-11-10 | Cost in PoW, PoP and PoB folder talk: `FolderCost` (CatWorkbench) above both discussion views: Mind A $, Mind B $, folder $ (PoStatic and PoC keep `ChatCost`). Test in `CatWorkbench.test.jsx`. |
| AGT-9 | OPEN | **Jobs from proofs and chat are missing from folders.** "Live price in every agent chat": his request text was not found; ask him. |
| AGT-10 | OPEN | **Visitor view of an agent:** no scroll, strong vitals. (next list 2026-11-06 #2) |
| AGT-11 | OPEN | **Each agent: an encrypted, growing private database with select access**, and a clean desktop: no big buttons, nothing clipped or hidden, every mechanic wired. (next list #3) |
| AGT-12 | OPEN | **Engine folder** on Fee's and the AGENTS desktops: live data showing what each engine does for agents and the Collective. (next list #4) |
| AGT-13 | OPEN | **Sicario's HQ page redo** (was A3 + 2026-11-07 list #2): new look, keep what is needed. Files: `AgentCockpit.jsx`, `DeskAgents.jsx`, `styles/sicario.css`, `collectiveSetup.css`. |
| AGT-14 | OPEN | **A settings view that explains proof paths simply** (angles, fallbacks, site order), so users understand their settings. |
| AGT-15 | OPEN | **Fix agent (A01):** pipeline and guards work, but no real model has produced a right fix (free G4 failed every try); no before/after picture; a paid cloud mind not run. |
| AGT-16 | BUILT 2026-11-10 (first slice) | Images and video in one place: PoC's 🎬 Image / video on the user's own fal.ai or Replicate (Wan 2.2 / 2.5, Kling 2.5, Seedance, FLUX), see the media line under AGENTS Decided. "Pick the best result across several APIs" and a local GPU are not built. |
| AGT-17 | OPEN | **3D:** NOVA not solved (OSSY 22 min, opened black; G4 and paid not run on it); PoC and PoEco as bigger worlds; real GPU frame rate not measured. |
| AGT-18 | OPEN | **Browser proofs on OSSY and G4 under load:** a read died when the keep-alive restarted 5088 at Mac load 41. Try windows and models from the LAN box, a more patient health check, one window at a time. |
| AGT-19 | OPEN | **Snapshot mouse gestures and clicks:** suspected buggy, never reproduced. Reproduce first. |
| AGT-20 | DONE 2026-11-10 | Redundant code audit: an AST scan of every backend module found 3 top-level functions nothing names (8 lines: `pow.engine_pick`, `proof_tools.free_image`, `poc_watch.hash_of`), and a scan of every frontend export found one unused component (`MoneyCharts.BackLines`); all removed, suites green. 24 unused `lucide3d` icon exports stay (tree-shaken from the build). Rerun the same scan after big features. |
| AGT-21 | OPEN | **Agents beyond pages in a user's repo:** edit files, and chat requests that read the project. Send-a-page works. |
| AGT-22 | OPEN | **Watch room (was A4):** more free legal options and tools on one monitor (his words were unclear: ask). Official players only (`WatchWall` built). |
| AGT-23 | OPEN | **Agent go-mode** (history 2026-10-29 Q1): keep going task after task until a human is truly needed, inside its $ cap, never typing a password or card. Check what exists before building. |
| AGT-24 | OPEN · OWNER · REAL MONEY | **W02 user-held signer**: a key the USER holds for his agent (passkey / delegated signer, or an embedded wallet with export), export screen, withdraw signed by it. Avoid FEELESS generating raw keys (custody, DECISIONS #2, LAWYER). |
| AGT-25 | OPEN · OWNER · REAL MONEY | **A2: OSSY and G4 PoWs through the Fuse card** when Auto-collect is on. New buy door: read `DEGEN_PLAYBOOK.md`, age/pool/already-ran guards, cash audit first, reconcile with `deskBuysOff`, owner only, confirm before the first buy. |
| AGT-26 | OPEN · OWNER · REAL MONEY | **Send from an agent wallet to its card** (`CardSites`, `card_link` save the address only). Needs guards and one real provider address. |
| AGT-27 | OWNER | **Wallet auto-pay when low** (`_wallet_think` shows cost a day and days left): he says how before anything moves. |
| AGT-28 | OWNER | **PoEco money:** pay bills and order a card (a bill is only marked paid today), reminders outside the desk. His path first. |
| AGT-29 | OWNER | **FC03:** wire the drawer keys into the brain (Birdeye holders, Helius RPC, X chatter, Telegram calls, signal webhook), each read guarded and faked in tests. Only Happy has a key (Helius). |
| AGT-30 | OWNER | **FC06 early calls:** call a coin falling toward the germ floor or breaking out; add a rendered 1m chart picture to G4's ask (owner said yes to the picture 2026-10-30). A buy-rule change: edge-audit first. |
| AGT-31 | OWNER | **OSSY01:** the seat prompt is ~1,900 tokens of real-money trading rules; any trim rewrites them. His word first. |
| AGT-32 | OWNER | **FC11 Hive crawl** (GO 2026-10-31): he saves X once in an agent's signed-in sites so traders can read X searches. |
| AGT-33 | OWNER | **PoW #14 findings (his trading calls):** a pick with 0 verified facts probably should not buy; chat says 0.01 SOL while the cap sends 0.008; a dropped buy closes the folder and never re-buys; a stale `BUY $FLOAT · 1 to sign` row. |
| AGT-34 | OPEN | **Supreme Intelligence leftovers on the agent side:** persistent shadow proposals beyond closed trades; real browser baselines (research duration per 4-coin PoW, facts per page, repeat visits, challenge recovery, frame rate); authorized cross-worker session reuse; unified kernel resource limits. Measure before changing (`SUPREME_INTELLIGENCE_REQUEST.md`). |
| AGT-35 | BUILT 2026-11-10 · HIS PLAY | **Games are not what he wanted** (owner 2026-11-10: "these games aren't what I wanted"). Cause: `play_games.py` has two fixed three.js templates (`runner`, `arena`), so every ask becomes one of them. **No Unity / Unreal key is needed and neither fits:** Unity and Unreal build with a desktop editor (an agent can't produce a WebGL build through an API), and Unreal's browser path is pixel streaming (a paid GPU server per player). **Next level, all free, no key:** a real game kit the minds write against instead of templates: **Babylon.js + Havok physics** (Apache-2.0 / free) or **three.js + Rapier** (MIT / Apache-2.0) for 3D, **Phaser 3** (MIT) for 2D, **PlayCanvas engine** (MIT); art and motion from **Kenney / Quaternius / ambientCG** (CC0), **Poly Haven** (already in), **Mixamo** animations (free with an Adobe account, the owner links it once). Flow: a game design step first (genre, core loop, controls on keys + touch, win / lose, progression, juice), then the build, then a headless playtest before filing (the canvas draws, input moves the player, no console errors, frame time) — a game that fails it is not filed. **Where his asks are basic and the next-level version is** (owner: "you must recommend where I'm lacking"): a game ask → a design doc + playtest gate (above); a page ask → a real component kit + a live-data section (COL-26 parts); a video ask → a character bible kept across clips (same face, voice, lore) so an influencer stays one person (media); a trading ask → verified P&L only (COL-25) before any grade. **Built:** `game_forge.py` + `_build_game` (a game ask in PoStatic): design JSON → the build on Phaser / Babylon / three+Rapier (pinned CDN, the `window.__game` hook) → `playtest` in headless Chromium (draws, input moves pixels, reaches play, 20+ fps, no page errors) → the other mind fixes with the failures and the failing file, ≤ 2 rounds → filed only if it passes (else says why). Proven: a hand-written Phaser game passes (3,343 px moved), frozen and broken ones fail. **Found with it:** OpenRouter reasoning models spent the whole page budget thinking and billed for nothing (Hy4 $0.0075 a call); long writes now go with reasoning off (+ a capped retry for GLM). Not built: Mixamo / Kenney asset fetching, Havok physics. |

## Built, needs one real run or his look (VERIFY)
| ID | What is built · what is missing |
|---|---|
| A1 | `.env` matches the loaded models (G4 qwen3.5-4b, OSSY qwen3.5-9b). Sicario's runs tests on `local/ossy`, `local/g4`, free. |
| A5 | PoW research reads empty: 0 of 41 scout rounds hold an empty read; not reproduced. |
| A8 | His real tests: `propose a PoW`, `propose a perp`, `file a pob best NBA picks tonight`, a Bids slip, `file a poc`. Read what each filed. |
| AG20 | Sicario's = OSSY + G4 (`_sicario_merge`), private. Filed PoW #1 $LEEROY −11.3%. Assigning minds to users' agents not built. |
| OR01 | Folder ⚙ Shorten long chats + Repair broken plans (OpenRouter only, off by default). Paid model cost not proven (W05). |
| AG06 · PP01 · PB01 · PB02 · PB03 | PoP reads in each mind's own window; `file a bid` / `file a pob` with picks blind; `file a perp` with 2 of 8 sources a mind; PoB board (12 leagues, 60 Polymarket markets, free-licence photos). Fakes, or one real proposal; no live trade card or real filed bid yet. |
| A7 | Every proof opens its best listed sites first (`read_first`, `_site_reads`, `sitesRead` chips): real reads over all 86, a real G4 call named the site that helped. A full proof with these chips not seen on screen. |
| AG08 | `watch a wallet` folder with a chain check. Fakes. |
| AG10 | `build a project …` writes static files into Creations with a .zip. One real free Groq call; a real dev server needs a sandbox host (E2B). |
| SD01 · BC01 · TY01 | Site door (Open, sign in by hand, Scan, a manual with every line tied to the site's sentence); bot-check window kept warm 14 min; type-and-paste bar. Polymarket read live; pump.fun stayed behind Cloudflare. Needs his real sign-in + save. |
| TU01 · ST01 | `top up pump` (one SOL transfer from its own wallet, $0.50 to $25) and trades on its own site account (owner's words only, guards). Fakes only; ST01 not wired into the PoW loop until a first real $1 works. |
| OD01 · DK01 · DK02 · DS01 · FD01 · LP01 · PF01G · PF02 · CH03 · CH05X · MN01 · TM01 · PS01 · MM01 · FP01 · BA01 · AG12 · IC01 | Desktop pieces: owner monitors, wallet + limits + tour + lamp, opens nothing by itself, settings, measured folders, performance glass, Proofs folder, Character (Wireface), chat looks, Manual, one explainer, Priority Setup, memory controls, fingerprint, Build an agent, command lists, 3dicons. Mostly seen on fixtures; not signed in, phone or day. |
| LV01 · LV02 | Go live: the canvas reached a local RTMP receiver; a real Twitch / Kick / TikTok key not run. |
| VV01 · NM01 · RK01 | Visitors see safe copies; names change once per 7 days; recovery key + 12 words. Tests only. |
| TL01 · FE01 · FE02 | Proof dashes from real free sources; Features demos and real working pages in the sandbox. No real model build from Features. |
| PS02 · PC02 · PC03 · EV01 | PoStatic proves first (reads best builds, plan, approval, build, review); PoC creator desk and snapshots; evidence marks. Not run in a real proof. |
| FC09 · FC15 | Agents' go-to list and a mail.tm mailbox. No real sign-up (his click). |
| CH02 | Your question shows the moment you send it. Send one real ask. |
| NIGHT-11-06 | Py agents folder; Prompt Studio GENERAL mind; kits allowed on real pages (`open_for_kits`, proven); page stitching (`cut_hint`, `add_css`); `BuildBar`; `proof_commands` from the desk; Git folder (`project_read`, uploads); `model_limits` Test limits (one real G4 run; PoStatic exam at 1,800 tokens not re-run); `agent_knows` + visitor floor `visit.feeless` (no real agent walked it); marks stick on scroll; login wait + `TypeBar`. Mostly fakes or harness; signed-in not seen. |
| NIGHT-11-07 | Features tiles each build something different; showcase mix; page links navigate; Code tree + zip; live data in builds (`_live_feed`); 3D playground (`Code3D`); PoC voice + Send to PoStatic; Git back with Vault inside; Remove from view; PoStatic built in sections (real LIVE VAULT run on OSSY + G4, 492 s, $0); 6 angles a kind; 3D engine from a brief; listening fixes (`keep_page`, go back); Ideas folder; personalities; proof alerts; Watch wall; Live desk; desk apps; WalletApp. Seen in Chromium on harness pages, not signed in. |
| LOCAL | Check folder `wfdde5bb856` ("SICARIO TESTS"); local page quality not run; G4's LM Studio system prompt makes it answer in trading JSON. |

## Decided (do not undo)
- **OpenRouter first for the owner's and admins' agents and Fee** (owner 2026-11-10, replaces the 2026-11-09 SingIt-only rule): calls go FEELESS's OpenRouter → SingIt paid from the agent's wallet → the free stand-ins, even with the users' switch (`LAUNCH_CAT_LIVE`) off. Why: SingIt's paid window cancels long page writes (Happy's live PoStatic: 4 of 14 calls fell to the 400-token free tier and wrote the weak design). Needs OpenRouter credit (it was $0). Users' agents unchanged; users bring their own OpenRouter.
- **PoC images and video on the user's own fal.ai / Replicate** (owner 2026-11-10): 🎬 Image / video beside File a PoC. Not linked → 3 steps (account, key, paste; sealed in `cat_keys` as `fal` / `replicate`). Linked → pick (Wan 2.2 5B $0.15 cheap default, Wan 2.2 A14B, Wan 2.5, Kling 2.5, FLUX schnell; Replicate Wan 2.2 fast, Wan 2.5, Seedance, FLUX), prompt (prefilled from the newest mind answer), make. `media_gen.py` + ops `media_models` / `media_make`: submit on the owner's key, poll the real state into the folder message, keep the file under `data/media/<cat>/` (served at `/api/cats/media/…`, random id), resume after a restart, max 3 at once. The key never reaches the page or the file link. Verified: both APIs answer 401 without a key, model pages exist; a real render needs the owner's fal/Replicate key (not run). Next: the agent keeps an influencer's posts coming (approved by the user), once a real render works.
- **Connect OpenRouter, one click** (owner 2026-11-10): in an agent's API keys drawer. OpenRouter's own sign-in (PKCE, `lib/openrouterConnect.js`): the tab keeps a one-time verifier, the user approves FEELESS on openrouter.ai, and action `openrouter_connect` swaps the code at `/api/v1/auth/keys` and seals the key on the agent (`cat_keys`). The key never reaches the page and bills the user's OpenRouter; they revoke it on OpenRouter. Pasting a key still works. The launch wizard still pastes (no agent yet). Verified: endpoints live (a dummy code → 400), the button reaches openrouter.ai; a real approval needs a signed-in OpenRouter account (not run).
- OSSY and G4 are ONE agent, Sicario's, private to the owner; minds stay qwen3.5-9b + qwen3.5-4b (beat Gemma 4 12B on a decoy fact test).
- Proofs propose until they can run the whole loop like PoW. Each proof has its own steps, colour, site list, layout and fingerprint.
- Trader-only Edge desk; the server refuses it for a general agent (the answer to "why two kinds of agent").
- Unlicensed sports streams and a VPN to hide them were refused on purpose: do not build. YouTube in a frame only through its /embed/ player.
- Bot checks stay a manual hand-off: never a solver, never stealth.
- Never hand-build charts: libraries (shadcn, Motion, Recharts, Lightweight Charts, sigma, React Flow, HeroUI). Less scroll, no nested scroll.
- No paid stand-in for local minds (`WS_CODE_MODEL` gone). No paper for users anywhere except the Fuse Arena.
- Proof of Range measured, not built: median −0.72% on 30 real pools; no new proof kind until a real effect exists.
- A02 removed 2026-11-06 (he did not want Fuse › Agents). A04 closed: the failed "graduated under $30K" rule left the theory and the DEGEN mindset.

---

# 2 · COLLECTIVE — proofs, grading, stash, kits, the Pool: the intelligence layer

## How it works now (read from the code 2026-11-09)
- **Where:** `reputation_service.py` (:5077, 35K lines) holds the Collective, stash, sorter, grading passes, sends and admin.
- **Quality:** `proof_weights.RUBRIC`, per-kind parts read by code (result, depth, evidence, evolve, unique, look …), ceilings (simple 30% +
  depth, failed 40%, unproven 60%, broken page 50%), ranks S–D (S needs every part known), top 300 growing with the pot. OSSY / G4 scores
  blend in, capped at +8% of top; two rejections stand; the owner's word is last. Weights re-fit after 12 samples of a kind (proposes, owner
  applies). PoStatic adds a real-browser look (`page_look`, 15 of 100).
- **Outcome:** `proof_stamp` marks PROVED / NOT PROVED 24 h after close. Strength differs by kind: **PoW** chain tx + live price (strong) ·
  **PoB** final scores from ESPN (`_pob_grade_pass`, outside) · **PoP** practice trade against true prices (paper) · **PoStatic** owner's
  mark + browser measure (not independent) · **PoC** owner's mark + owner-entered earnings (self-reported) · **PoEco** a deterministic hash
  of his own books (integrity only, no outcome; not in any rubric, stamp, validator, stash or loop).
- **Sends:** `ProofSubmit` / `pot_send`: $1+, the agent's own wallet signs, read back on-chain, five code-only validators
  (`proof_validators`: Tally, Sherlock, Devil, Archivist, Judge); PoW keeps its +50% rule; Auto-collect (`_collect_pass`) for PoW wins.
  `$Proof/` shelf: OSSY and G4 deep-read a sent proof, the average sets the score (`set_score`).
- **Money:** THE DEAL (below) in `collective_stake.py` (`deal='stake'`) on the Pool ledger `collective_pool.py` (sealed file, HMAC hash
  chain keyed by the server's master key, audited every 5 min). Collective wallet on Circle. Withdrawals OFF. The old `deal='bank'` is still
  in code. Real ledger: 0 sends, 0 agents. `collective_auditor.py`: 7 hard cases at 1,000 agents on fakes.
- **Stash:** `collective_stash.py`, SQLite index (`data/stash/index.db`, a sha per item) + sealed blobs, visitor-safe copies only.
  Real (2026-11-09): 244 items from 2 agents, 2026-11-01 → 11-08: Trades 59 (9 won / 29 lost / 21 open) · Picks 70 (none with an outcome:
  check) · Code 60 (16 / 13 / 31) · Content 9 · Perps 5 · Snapshots 41. Trash: 7 days then gone for good. Hourly sealed push (hashed names) to
  the private repo `tekholds-dev/feeless-collective`; a vault per agent. Losing the server's seal key loses that backup.
- **Sorting:** `collective_sort` (OSSY + G4 read one file per 45 s when idle, both must agree, trash waits for him).
- **Kits:** `collective_kits.py` (34 kits: version, quality earned from real proofs Untested / Working / Proven / Losing, auto-picks per kind by
  record, daily scout + owner approve, skill switches, `kit_report` = what a page really used; kits are text and page libraries with no
  wallet or file access) · `proof_kits.py` (10 FEELESS live-data kits).
- **Credit and learning:** `proof_loop.mind_board` (each mind per topic), `agent_refs` source trust from real wins, kit record, debate points,
  source print (`SourceWins`), `ai_learn` on the real card.
- **Public:** Collective landing (`CollectiveLanding`, atoms = real proofs, no ids), stash no longer public.

## The target (agreed with GPT, 2026-11-09): a thin layer over the code above, not new systems
Mission envelope (one read-only schema) · per-kind minds + the route that really answered · a proof event history separate from money ·
three evaluations kept apart (quality = rubric; outcome = stamp + evidence + who verified it; improvement = **unverified** until a matched
baseline) · model × proof vitals · tools and an evolution gate later, once real data exists. Contribution intelligence stays an observation:
**the grade-to-boost deal does not change.** Measured with real results, never internal grades, agent agreement or simulated success.
First milestone: **one real, traceable, independently tested PoStatic**, not a dashboard of unverified scores.
**Principle (owner 2026-11-09):** agents get stronger by working, like muscles: every proven mission may leave a reusable part (COL-26), and what is not used goes stale. Our own code is the proofs, record and parts; open libraries are raw material, adapted with their licenses kept.
**Evidence levels (never the same thing as pass / fail):** L0 claimed · L1 filed with its artifacts + sha · L2 an outside fact recorded,
authority named · L3 re-checked independently (a second reader or a replay reached the same fact) · L4 beat a frozen baseline on held-out data.

## Open, in order (top first)
| ID | Status | What · done when |
|---|---|---|
| COL-1 | BUILT 2026-11-09 · HIS CHECK | **Mission envelope** `backend/mission.py` (pure, read-only): `envelope(kind, folder, now, cat, quality)` and `all_of(cat, now, quality_of)` for all six kinds. Fields: id, kind, agent, minds (configured now; who answered = not recorded until COL-2), cost per mind, sources, kits, artifacts, `recordSha`, quality (the service's own `_proof_view` passed in, else "not computed"; PoEco none), outcome + authority + strength, improvement `unverified`, evidence L0-L4, mark, sent. A day with no result reads `unsettled`, not a loss. **Tests:** `test_mission.py`, 15, on cleaned copies of real folders (`tests/fixtures/mission_folders.json`); three planted bugs were caught. **Real read:** all 105 real folders, nothing changed: 8 at L2 (PoBs settled by the scoreboard), 97 at L1, 0 PoW checked against the chain. Imported by nothing yet: no live effect. |
| COL-2 | BUILT 2026-11-09 · HIS CHECK | **Two models per proof type + who really answered.** `launch_cat.minds_for` / `set_minds` (`brainsCfg.byKind`, falls back to `brains`); every proof path reads its kind's pair (PoW, PoP, PoB, PoC, PoStatic, PoEco); chat, budgets, credit and memory stay per agent. Brains window › Its models › **BY PROOF** (`KindMinds` in `CatDesk.jsx`, action `kind_models`, 24 h lock, the server checks each model against the list or the agent's own minds). Every proof call writes one line to `data/mind_calls.jsonl` (`mission.call_row`): asked, route, model that answered, $, tokens, ms; the envelope reads it (`calls=`). No routing changed, no new paid fallback. **Fixed with it:** a model switch dropped every setting `clean()` did not own, today's spend (`daySpend`) included, so a switch reset the daily budget; kits per proof, persona and Sicario's switches were lost too. **Real calls through the new code:** asked OSSY → answered by local qwen/qwen3.5-9b; asked G4 → **answered by SingIt free deepseek-v4.1-flash standing in** (this shell's Python has no LAN route to G4, so G4 failed silently, which the old label hid). Whether the live service reaches G4 shows in the log once COL-2 is live. Tests: `test_kind_minds.py` (6), CatDesk picker test; seen on `/dev/cats` desktop › Brains at 800 and 375 wide. Day theme not looked at. |
| COL-3 | BUILT 2026-11-09 · HIS CHECK | **Proof event history** `backend/proof_events.py`: one SQLite file `data/proof_events.db`, append-only, every row HMAC-chained to the one before with its own key (`proof-events:` + master, never the Pool's chain or key), writers under `BEGIN IMMEDIATE`. Events: plan, build, review, file, grade, stamp, send, score, correction. Each row's id is made from the fact, so a replay, a restart or two saves of the same state file it once. A wrong row is never edited: a `correction` row points at it (`history()` shows `correctedBy`). `verify()` walks the chain; deleting the newest rows still verifies unless a head kept elsewhere is passed (`verify(expect=head())`): **where that head is anchored (repo or chain memo) is his call.** **Fed by** a watcher at the service's two save points (`_save` = every folder of all six kinds plus the open PoW run; `_ws_save` = PoStatic / PoC plan, review, each page), log only, wrapped so a broken event file never stops a save (tested). 5077 writes no proof events yet; the file takes a second writer when it does (tested with 4 at once). **Tests:** `test_proof_events.py` (15): tampering ×4, forged row, cut-back, replays, corrections, two writers, the watcher, the service save. **Real dry run** on a copy of the real store (scratch file): 105 proofs → 318 rows (105 file, 50 grade, 59 score, 104 stamp), chain verifies; an unchanged save adds 0 rows in 0.3 ms, a restart 0 rows in 3 ms. The dry run caught one bug the first tests missed (61 PoStatic pages share 20 workspaces, so keyed by workspace they overwrote each other): each filing is now its own row, naming its workspace. Live once pushed: the first save backfills, `at` = when the record saw it, `filedAt` = the folder's own time. |
| COL-4 | BUILT 2026-11-10 | **Three evaluations, served:** `GET /api/cats/{id}/missions` (owner only) returns every proof's envelope with quality (the service's own `_proof_view`, untouched), outcome (stamp + authority + strength) and improvement (`unverified`, no matched baseline) kept apart, plus who really answered (COL-2 call log) and its tamper-proof record (COL-3: events, steps, last step, chain intact; a page's workspace rows join its folder's). Real read: Happy's 99 proofs in ~200 ms, chain intact (327 rows). Tests: `test_missions_endpoint.py`, envelope record, `counts`. |
| COL-5 | BUILT 2026-11-10 · HIS LOOK | **Model × proof vitals** (`mission.vitals`, in `/missions`; `ModelVitals` in the desk's models panel and the Brains window): per model per kind, proofs, calls, failed %, API $ per proof with local calls apart, average quality, outcomes settled from outside (owner marks do not count) and the win rate. A pick only with ≥ 5 settled proofs per model: the cheapest within 10 points of the best verified win rate; otherwise it says not enough. Real: only Happy's newest PoStatic has full call rows so far (Hy4 5 calls $0.0175, GLM 3 $0.0061, deepseek fallback 2, SingIt free 4 at $0). Seen at /dev/cats (fixture rows). |
| COL-6 | OPEN · MILESTONE | **Real PoStatic pilot on OSSY + G4** (free, local): plan → he approves → build → review → independent real-browser test of the page → file → stash → grade → stamp → event history verifies → vitals row. Artifacts, results, costs and events kept. No send, no boost, no money. |
| COL-26 | BUILT 2026-11-10 · HIS LOOK | **Parts record, the capability foundry** (`collective_parts.py`, `data/parts.db`): every PROVED PoStatic page (marked right + its 24 h stamp) gives its blocks once (header / nav / section / aside / footer / form; a page-wide main or article is split into its sections). Kept only with every license carried (any GPL family blocks it) and a code check (no eval, no outside script beyond the kit CDNs, no inline handler reaching cookies / storage / network). **Recombine:** each build is offered up to 3 fresh parts matched to the ask (`offer_line` in the build prompt); a reuse is seen by its `data-part` mark, logged once per proof and filed as a COL-3 `reuse` event. **Muscle rule:** a part nobody reused in 30 days is stale and no longer offered. Reuse is never paid. Surface: `GET /api/cats/{id}/parts` (owner) and the 🧩 PROVEN PARTS strip on the PoStatic desk. **Real dry harvest** (scratch file): 33 parts from 13 proved pages in ~50 ms (17 sections, 7 headers, …; MIT / Apache / GSAP / FEELESS licenses). **Done when** (unchanged): one part reused in two other kinds beats a matched run without it; until then improvement reads unverified. Today parts are offered to PoStatic builds only. |
| COL-7 | BUILT 2026-11-10 | **Stash Picks with no outcome — cause found and fixed:** `collective_stash.put` wrote each proof once, at filing; a PoB is graded later (the game's final score), so 9 of the 10 real PoBs (70 rows with their sources) kept 'none' forever. Now a row still at 'none' takes its result once when the proof settles; a settled result never flips and the kept copy never changes (append-only holds). The stash's own pass fills them once live. Test: `test_stash_outcome.py`. |
| COL-25 | BUILT 2026-11-10 · OWNER OK (money record) | **Real PoWs read back from the chain — cause found and fixed:** `pow.folder_public` (what a filed folder keeps) dropped `pid`, `sellPid`, both signatures and `settlementVerified`, so no filed real PoW ever showed a chain check. Kept now. **Backfill** (`_pow2_relink`, once at start, chain reads on a copy, only the fixed folders' fields written onto a fresh store): each real PoW is matched to its own buy and sell in the agent's transactions (same coin, inside the folder's time) and read back with the existing `_pow2_reconcile`. **Dry run on Happy's real folders (nothing saved):** 7 of 11 verified; the server's own P&L was off: niketyson −19.8% → −37.0%, GATO +0.7% → −0.6%, ANSEM +0.2% → +9.3%, SIS −16.1% → −16.3%, FLOAT −6.4% → −10.0%; Donkey and Diamond already matched. 3 never traded on chain (BLUE, Dacity, HELL), 1 failed buy (ANONVOYAGE). No payout is triggered; COL-3 files each change as a correction. Test: `test_pow_relink.py`. |
| COL-8 | OPEN | **Finish the Collective audit** (was A6): every mechanic and folder full, with vitals; signed-in folders unread. **Proof data true and complete** for OSSY and G4 (they flagged rich rugcheck snapshots as bad and called a future-dated game "hallucinated"); total score on each file; scoring really good. (next list #6) **Audit 2026-11-10 (every real folder, read only):** PoW 18 (8 never bought: proposals / paper, so no buy time, P&L or source; 7 at L2 after COL-25), PoP 5 (all no-trade), PoB 13 (8 at L2), PoC 7 (6 recorded no source: their reads really failed), PoStatic 62 (37 recorded no source), PoEco 1. **Fixed:** a filed PoStatic dropped what its build read; `file_static` now keeps `sitesRead` and the kits used, so COL-13 and COL-12 count them. Still open: the OSSY / G4 flags (rich rugcheck snapshots called bad, a future-dated game called hallucinated) need a live run on Sicario's. |
| COL-9 | OPEN | **Agents autonomous on the stash brain** (next list #1): file any proof, first read what any agent already filed, never research the same thing twice, no made-up predictions or content; the fingerprint sharpens with every proof. Recall exists (`_recall`, `best_for`); not proven in a live proof. **Built 2026-11-10 (never twice):** `_site_reads` now shares one read of a kind's best sites with every agent's next proof of that kind while it is fresh (PoW / PoP 5 min, PoB 30, PoC 1 h, PoStatic 6 h); reuses are counted, a read where nothing opened is never reused. `_recall` (the stash's best past proof + kits) already reaches every proof. Test: `test_shared_reads.py`. Still open: a topic PoB's own browser research is not shared yet. |
| COL-10 | OPEN | **Method kits + Tool Forge** (owner 2026-11-07 #12, GPT kit composer 2026-11-06, GPT 2026-11-09 E): every working method (planning, checking its own work, finding real components and packs, reading docs first, testing before done, picking sources) becomes a kit per proof type; a kit scout per proof; minds propose kits themselves; combine kits beyond ready sets; per kit a manifest (version, dependencies, permissions, tests), measured reliability, approval, regression check, quarantine, rollback. Goal: cheap and local models work like the newest because the stash gives them the method. Kits must never gain wallet or file access. |
| COL-11 | OPEN · AFTER COL-6 | **Evolution Lab** (Supreme Intelligence PoI, GPT 2026-11-06 + 11-09 F): frozen baselines, point-in-time data, held-out comparison, promotion gate, rollback, generation history; shadow trades and counterfactuals; model-independent memory (keep, start fresh, model-assisted migration, compare before adoption). Never infer learning from one winning trade. |
| COL-12 | BUILT 2026-11-10 · HIS LOOK | **Contribution view** (`mission.contribution`, in `/missions`; WHAT EARNED IT in the Model × proof card): per source (host), the proofs that read it and its outside-settled wins / losses (owner marks count as read, never as a win); per model, calls, API $ (local free), proofs, outside-settled wins; per kind, how often the two minds split. Nothing is ranked under 5 settled; activity alone earns nothing; payouts untouched. Happy's real record: rugcheck.xyz 16 proofs 5–6, jup.ag 14 proofs 3–6, birdeye.so 8 proofs 2–4, coingecko.com 6 proofs 1–4; PoP minds split 2 of 2. Not built: confidence calibration (needs a stated confidence per call). |
| COL-13 | BUILT 2026-11-10 | **Compare before settling, enforced** (`compare_gate.py`): from the folder's own record, never a mind's word: ≥ 4 distinct sources really read (a site that would not open or a repeat host does not count), ≥ 2 options weighed, a reason written. **Enforced on PoB bids and PoP trades** (no money): a thin pick is filed as no bid / no trade with the exact gap, and the next round reads more. **Real-money PoW: recorded, never blocked** (owner 2026-11-10: "always do what's best"; the buy path is unchanged). Every envelope carries `compare` (so COL-5 vitals and grades can see it); folder discussions show ⚖ compared N of 4. Real record at build time: PoB 10 / 13 pass, PoP 2 / 5, PoW 8 / 18 (8 real PoWs recorded no source at all). Tests: `test_compare_gate.py` (a thin PoB is not bid; 4 sources bids). |
| COL-14 | BUILT 2026-11-10 | **Mark notes teach the record:** the owner's notes on marked parts of a page stay with the build (`markNotes`) and reach its filed PoStatic; notes on pages he then marked **working**, across every agent, become LESSONS FROM THE OWNER in every next page build (deduped, newest 8, data only). Test: `test_mark_lessons.py`. |
| COL-15 | BUILT 2026-11-10 (claim slice) | **＋ I traded it** on a PoW proposal folder (`ProposalClaim` in the PoW explorer, op `pow_claim`): where (e.g. Crypto.com), the result in $, an https receipt link, a note. Kept as `manual` on the folder; the record reads it as **owner claim, strength self**, never a settled result. Not built (real money, his test): the send from the agent wallet to the Collective that would confirm a claim; the py agents scanning marked areas. Tests: `test_pow_claim.py`, `CatWorkbench.test.jsx`. |
| COL-16 | OPEN | **BD02:** bids and browser wins sending to the Pool. Needs the agent's Polymarket or site address on file and one real read of its public record. Perps stay paper. |
| COL-17 | BUILT 2026-11-10 | **Math auditor on real data:** `collective_auditor.laws` (nothing negative, books add up, nobody paid past its points) now runs on the REAL Pool ledger every 5-minute pool pass beside the chain audit (`auditNow.laws`, a breach prints `[pool] MATH AUDIT`). Today's real ledger: 0 members, 0 sends, chain intact, laws clean. The stress suite (zero profit, losses, rounding, stale prices) keeps running on fakes. |
| COL-18 | OPEN | **LG01:** move the Pool ledger from one sealed file to a database before ~10,000 members (each fee rewrites a 46 MB file at 100,000). |
| COL-19 | OPEN | **Proving ground** (GPT 2026-11-06): a permanent arena with manipulated volume, latency and failures that gates live permission. Paper desk, arena and `theory-shadow.py` exist. |
| COL-20 | BUILT 2026-11-10 (first slice) | **Data contracts** (`contracts.py`): one versioned shape, one owner and a check for each shared record: the mission envelope, a model call row, a proof event, a part; tests run every contract on records made by their real code (and on the cleaned real folders). Not yet: schemas for PoW research, trade fills, Colony contributions, memory versions; the legacy agent store migration. |
| COL-21 | OWNER | **Pool rules he must decide:** a higher grade paying back faster (today the seat and the limit both scale with boost, so payback days are equal); a 3-boost-point effort floor for low scores; rewards speed by profit growth, not only pot size; what debate points and convo boosts buy (CC01); the boost display. |
| COL-22 | OWNER · REAL MONEY | **Collective money moves:** AutoRange on the Collective wallet (ranged by hand today); profit read from pools (paste a tx today); a card-seat win closing its PoW with real P&L and paying the Pool (Sicario's has no wallet); the Collective earning per top-up and per card transaction (third-party card fees need provider terms + LAWYER). |
| COL-23 | OWNER · LAWYER | **FC14 withdrawals** from the Pool ledger: counsel, then a payout wallet with a daily limit. LP deposits and on-chain staking not built. |
| COL-24 | OPEN | **New proof types that are missing** (owner 2026-11-07 #12): he names them, or the Collective proposes from real gaps; each needs a real effect first (Proof of Range had none). |

## Built, needs one real run or his look (VERIFY)
| ID | What is built · what is missing |
|---|---|
| DEAL | THE DEAL on the real server; 0 real sends, so nothing moved. `test_the_owner_endpoint_runs_the_whole_deal` on fakes. |
| VD01 · PR01 · AC01 · CX01 | Five validators; PROVED / NOT PROVED stamps; Auto-collect (re-sign needed, old signature does not carry); a Collective folder per paid proof with the chain receipt. Tests only, no real send. |
| CP01 · CP02 · CP03 · CP04 · CP05 · CP06 · CP07 · CP08 · BU02 | Pool ledger, fees to the Collective wallet, boosts, Collective HQ, plan picker, boost coin, faster earning, outside money, live boost dollars. Several describe the replaced `bank` deal: re-check each against THE DEAL. Tests and fixtures only. |
| PL01 · PL90 · LS01 | Proof Loop, one loop for every proof, colony loss shapes + best mind per topic. Only Happy has closed proofs, so they rarely fire on real data. |
| ST01X · PP03 · CL01 · CT01 · CC01 | Stash, Proofprint, The Collective naming, Collective top, collective convos. Fixtures or one live pass. |
| GRADE | `proof_weights` real rescoring (no S page left), `page_look` (24 real pages), grade preview (real: Happy PoStatic #46 = 129/300 C). No paid send deep-scored for real, so learning sits at 0. |
| DEBATE | Debate rooms + linked boost ceiling (1 point = $0.05, max 25% of what sends allow: his numbers to change). Never played by two real owners. |
| SORT · TRASH · GIT | Sorter marks on 3 real snapshots; Trash desk; sealed repo pushes (171 real files → 227 blobs, 12 of 12 opened back). Sorter not re-run to prove marks land; signed-in not seen. |
| KITS | Kit picker, proposals, skills switches, Discover gallery with real previews. No real proof has read a picked kit end to end. |
| MONEY-DASH | Money folder (`GrowFolder`, `MoneyDash`): real KPIs, best by risk in four lanes, ranked never picked. Seen on a real snapshot, not signed in; AutoRange bands not backtested. |
| ATOMS · MODELS | Collective landing with 66 real proofs at 60 fps; model discovery from OpenRouter's published scores (`place_proofs`). |

## THE DEAL (owner 2026-11-06, his words after a long debate; ledger `collective_stake.py`, cfg `deal='stake'`). DECIDED.
- **The Collective earns from the jump:** every agent wallet fee, top-up and site fee is its own (`keep`). A send is NOT income.
- **A proof send is a stake** in the owner's own unlocked, auto-ranged pools on different platforms. Rewards come from pool PROFIT, never from what anyone staked.
- **Grade makes boost:** grade 0-100 (`grade_of`: 5 validators up to 60, print strength up to 40); boost = 1 + grade/100. $10 at grade 87 = 1.87x, at most $18.70 back. Code uses 18.7 points (1 point = $1 it may still earn); he wrote 187: OWNER confirms the display. A held proof has no points until cleared.
- **Score rule (2026-11-06, replaces 300x):** base top 300, flawless only; boost = score/100 ($5 at 300 = 3x, $15 at most). The top grows with the pot: 500 / 750 / 1000 at `tier500Usd` / `tier750Usd` / `tier1000Usd` (defaults $10K / $100K / $1M, Claude's guess, his dial). Bigger pot pays faster (7, 3.5, 1.75 days, at once), still only from real profit.
- **Seat = boost × dollars** (`size_of`: $10 1x, $100 2x, $1,000 3x, then half a step per 10x). One wallet's agents share `walletCapPct` (10). Boost cash releases over `dripDays` (7). Burning points speeds up and takes a bigger seat.
- **The boost is also the cut:** 1.87x = 1.87% of every profit from all pools (`cutPerX` = 1) until points run out.
- **A profit splits three ways:** agents' cuts, the Collective's piece (`collectivePoolPct` 20), the rest compounds. Cuts scale down evenly; agents never take the Collective's piece.
- **Fast compound:** burn points (`fastPtsPerDay` 5) for time at the highest cut held; only from room nobody holds (test proves no cut shrinks).
- **Claude's numbers he can change:** `capPct` 3%, `minStakeUsd` $1 (tiny sends earn no points).
- **Not a Ponzi by construction:** `pay_early` and `bonus` refuse a stake; sends never reach a reward. Screens say a stake can lose money and nothing is promised; never "invest" or "staking" on screens.
- **The pool test stands:** high fee-APR pools did not prove growth after price moves (SOL-USDC net ≈ −2.6% over 30 days). Money screens show numbers and risks, never advice.

## Decided (do not undo)
- Collective = The Collective, its funds = The Pool (honey design is gone). Visitors never see private stash rows, site names or ids.
- Grading is by code from the record; minds may lift at most 8%; the owner's word is last; kits never get wallet or file access.
- Debate points are a record; paying them needs his decision. Others' proofs only through Debate; Real proofs tab shows this owner's own agents only.
- Stash is append-only except the owner's Trash; agents' own proof folders and the money ledger are never touched by Trash.

---

# 3 · SITE — trading, the real card, perps, launch, pools, Familia, FeeCat pages, chats, infrastructure

## How it works now
- **Services** (restart all after backend changes: `bash scripts/start-backend.sh`): `server` 5001 (market feeds, quotes/swaps on Jupiter, chat
  on Mongo) · `reputation_service` 5077 (reputation, fees + fee ledger, quests, Fuse, seasons, profiles, notifications, admin, Collective) ·
  `feecat_service` 5088 (agents) · `candles_service` 5099 (true candles, trade tape Helius → Solana RPC) · Circle sidecars 5111 (FEELESS
  account, never for users) and 5112 (family + agent wallets, `CIRCLE_TENANT=agent`) · MCP 8765 · Mongo 27017 (market caches) · frontend 51367
  (the owner's own dev server: attach, never start a second).
- **Money path:** quote → simulate → wallet signs → server checks the signed message equals the quote → broadcast → confirm → fee ledger
  (`fee_ledger.json`, the source of truth). Anything that counts a trade must find its signature in the wallet's confirmed FEELESS trades.
- **The real card (Fuse):** the ten-agent kernel (`agents.py`, `trench_kernel/`, `opportunity.py`; docs `AGENT_KERNEL.md`, `TRENCH_CREW.md`),
  one keeper (`fuse_wallet.py`), Circle signs. `deskBuysOff` = the desk's agents make no new real buys. Before advising on real-money buying run
  `scripts/edge-audit.py`: 31 of 1,066 rules positive on unseen coins, agents entered 0 of 3,000 calls.
- **Perps:** Jupiter Perps live (wallet signs, TP/SL, partial close; owner lifted the US rule for Jupiter only); Kalshi via DFlow built, off
  until the key; paper desk; agents only propose perps (no agent perps sender). Full page: `docs/PERPS.md`.
- **Familia:** city (`family_city.py`, `family_world.py`, `FeeCity3D`), Strike Zone shooter (`docs/TELEGRAM.md`), brokers (`docs/BROKERS.md`).

## Open, in order (top first)
| ID | Status | What · done when |
|---|---|---|
| SITE-1 | TRIAGED 2026-11-10 | **Support queue, triaged (data/bugs.json, 282 open, Oct 20 to Nov 6, all auto-reported):** 232 are **dead clicks** (a layer covers a button), 40 **crashes**, 10 **dev-build errors** logged while code was mid-edit (noise). Dead clicks by what gets covered: `season-banner` 19 (under `ack-panel` and others), the HQ button `hq-pop-open` 15 (under `hq-shell` / `agent-desk`), `ftd-veil` 10, `city-fee` 5, `workspace-ecosystem` 5, the terminal menu toggle 4; by what covers: `canvas` 14, `hq-shell` 13, `agent-desk` 10. Crashes are from code states that no longer build (e.g. `txt is not defined` in CrewHQ, `useNavigate()` outside a Router in Chat, a lazy chunk `reading 'call'`): today's build fails on an undefined name, so these cannot recur as written. **Next:** reproduce the top 4 dead clicks at 1280 and 390 wide and give each covering layer `pointer-events:none` or a lower z-index; then mark the dev-build and stale-crash rows fixed in one pass. |
| SITE-2 | OPEN | **Lag:** scrolling 35-48 fps (Bids 35); Proofprint and Features open in 220-240 ms (dev build); the ResizeObserver overlay fix is unproven on his screen; LAG01 chart overlays; agents-tab fps recheck with the pane in view (was 41). Production not measured. |
| SITE-3 | OPEN | **HeroUI across the site, the rest:** FeeCat tabs and the Brain's own settings panels; trim HeroUI to the parts used (main CSS +36 KB gzipped). |
| SITE-4 | OPEN · LAST | **Command center rebuild** for Sicario's, Fee and Familia (and the FEE CAT Command Center from Supreme Intelligence §7): real telemetry only, alive, dense, responsive. Data first, this last. |
| SITE-5 | OPEN | **Q02:** split the 35K-line `reputation_service.py`, one small slice per change (`rep_tools.py` is the pattern): read-only and admin tool routes next, money and trading routes last. Never unwatched on the live machine. |
| SITE-6 | OPEN | **Q03:** FeeCat stage, tabs and perf; lore and launch flows; 3D roadmap; faster model reads; Launch and FeeCat pages' glass restyle (flat panels remain, FAMILIA_PLAN leftover); Fee's public desk is still 3,600 px tall. HQ and Familia need a signed-in measure. |
| SITE-7 | OPEN | **Tutorials styling.** |
| SITE-8 | OPEN | **Q01:** signed-in city FPS (his throttled window voided the last read), load tests, a database and multiple workers for scale beyond one box. |
| SITE-9 | OPEN · AFTER HIS FIRST GENERAL AGENT | **SEC01 security hardening** front to back: no secrets reachable from the bundle, every write endpoint signed + owner-checked, CORS/CSP/headers, rate limits, SSRF + path guards, dependency audit, encryption at rest and in transit, three free defensive layers (Cloudflare WAF + bot fight + rate limiting, Turnstile on sign-ups, Dependabot/CodeQL). Defensive only. An outside pen test is still not done. |
| SITE-10 | BUILT 2026-11-10 | `/terminal/hq` was a 404: HQ is the creator's pop-up, not a page. LaunchLab's "House config (HQ)" door now opens it (`feeless:hq-open`, HqPop listens). Test: `LaunchLabDoor.test.jsx`. |
| SITE-11 | OPEN | **Q23 Price-gap engine:** a live drawn view before buying, then the buyer's own running engine. Ships with buy guards. |
| SITE-12 | OPEN · OWNER · REAL MONEY | **L01 AutoRange:** Orca as a third venue (US allowed? not checked), DLMM wider than 69 bins, compound LP fees; reconcile older tight-range requests with shipped Meteora / Raydium. |
| SITE-13 | OPEN · OWNER | **P01 Perps:** limit orders, the owner's fee on every open (`increase-position-with-fee`), Coinbase Advanced door; more venues only through an approved eligibility flow (gTrade, Aster, Hyperliquid bar US users; add the US-regulated HIP-3 market the day it launches). DFlow key → first real $1 Kalshi order; first real Jupiter open + 50% close + TP move. |
| SITE-14 | OPEN · OWNER | **B01 Brokers:** Kraken / Coinbase own-key doors, YOUR MONEY totals, options, broker perps where supported; his ask for an easier OAuth sign-up than SnapTrade / Alpaca keys; first real link + $5 SPY buy. |
| SITE-15 | OPEN · OWNER | **R01** RepMarket user sign-in / key and deposit flow (verify the permitted product first) · **LA01** Launch: selected-venue configuration and any supported quote pair · **C05** leverage position rows and one-transaction loops · **C06** provider fee configuration for perps / LP / run / leverage / launch (no invented referral fields; Zora needs a supported venue) · **Q04** Fee-Back eligibility, valuation, settlement, rounding, audited payouts, and the buy-and-burn executor (done by hand today) · **Q06** feature-level geo/KYC switches (LAWYER). |
| SITE-16 | OPEN · OWNER | **Leverage beyond Jupiter:** his note on DECISIONS #7, find US-legal ecosystems with less entry than Jupiter Lend. Research, real call, then his choice. Circle house-wallet trading needs his per-trade and daily caps. |
| SITE-17 | OPEN | **Familia (after agents, his order):** **C02** live building P&L, real-money / MP errands, rank and badge pools, custom backdrops, drag in the 3D block, new islands / bridges / lots / kiosks, saved layout · **C03** block readers (Meteora DLMM, marginfi, Save, PumpSwap LP, Phoenix), each checked against a real account first · **C04** Night Vault (DCA / limit orders, compound LP fees, retire old MP errands, outer-city markets, coin buildings, in-city raids, MP ladders, MOBhouse, for-sale island) · family wallets + a payout engine that cannot hit one family more than 3 times in 12 h (his DECISIONS #4 note; no pooled family wallet held by FEELESS). FAMILIA_PLAN is an older spec: verify gaps against the code before building. |
| SITE-18 | OPEN · OWNER | **T01 HQ Telegram center:** bot rooms, alerts / trading / community / security, Mini App setup, FeeCat-art idle RPG and slot hub. Bot setup steps are in `docs/TELEGRAM.md`. |
| SITE-19 | OWNER | **CH05:** move agents and the real card onto true candles after a shadow test (they still read filled bars). **CH04:** per-trade ticks need a stream key with quota. |
| SITE-20 | OWNER · LATER | **Contract path (GO_LIVE B):** a week-long devnet soak with a keeper host, external audit of `fuse_card`, upgrade authority on a separate Circle wallet, mainnet with small caps; `contracts/fuse_vault` not run or audited here. **Always-on host** (`docs/ALWAYS_ON.md`, Railway): only one place may run the backend against the Fuse wallet. |
| SITE-21 | OWNER | **Real-money checks on Happy, one at a time:** "2 + 2" paid from the wallet; `buy 0.01 SOL of $JUP` and `sell all $JUP`; withdraw to his wallet; first non-staff agent's fees land in the Collective wallet; Venice fallback (W06, needs the $5 top-up flow, not built); the model share of a split arriving as USDC (not built). AutoRange $25 open / re-center / close; $5 bridge round trip and $2 gas fill; leverage open/close; first $5 Run deposit; FeeCat signed proposal. |
| SITE-22 | OWNER | **Leftover files from the Emergent tool (2026-09):** `test_result.md`, `backend_test.py`, `memory/PRD.md`; also the stub `README.md` and CRA's `frontend/README.md`. Delete on his OK. Q05 (below) checks the PRD's claims first. |

## Built, needs one real run or his look (VERIFY)
| ID | What is built · what is missing |
|---|---|
| MB01 · MB02 · M02 | Phone shell (the page never scrolls, only the tab), fold split at the crease, every page fits. Emulated only, not physical Safari or Duo (M01). |
| LAG01 | reputation_service idles at 5.8% CPU; 9 pages at 60 fps signed out. Signed-in desks and a real window not measured. |
| F01 | FEEd v5. Coin chips and receipts seen only via the composer. |
| IC01 · RW01 | 3dicons swap; Rewards page. Signed-in pages and phone not swept. |
| C12 · G01 · C01 · K01 | Alliances; real CC0 guns; all 28 Familia buildings; one key vault in Family HQ. Signed create / real use not clicked. |
| DB01 | Desk buys off at all 4 doors; not watched through a real tick. |
| SC01 | Security audit 2026-11-04: no plaintext secrets in the store, sealed sign-ins, https only. Legacy store and old archive rows still plaintext; Terms text is a draft for a lawyer. |
| A03 | Same-coin shadow ledger and edge audit: repeat after ~50 newer model trades; diagnose G4 uptime. No claim of profitable unseen performance. |
| Q05 | Old PRD claims (chain coverage, risk signals, moderation, identity): validate against the code before any rebuild. |
| Q07 | Final site-wide click-through after the builds: day / night, 360 px, lite / reduced motion, every step and empty state. |
| AUDIT-11-07 | Signed-out audit of every page at 1280 and 360: 0 crashes, 0 sideways scroll. Signed-in pages, Duo sizes and real funds not covered. |

## Decided (do not undo) — money, custody, legal (details: `docs/DECISIONS.md`, read it before any money or custody work)
- The user's wallet signs real money; FEELESS holds no user keys. Agent wallets are Circle (agent tenant); Crossmint is unused.
- Every new buy door ships with age / pool / already-ran guards. Coin → coin with no SOL/USDC side is refused. P&L never includes fees.
- Nothing trades fee-free except buying $FEE / FEECAT / rFEE. Swaps never auto-quote.
- No GeckoTerminal, ever. Candles: the source's own bars, unedited (CH01).
- Perps: paper in FEELESS except Jupiter Perps (his call, his legal risk); no agent perps sender (FC04 closed).
- One points system; the rep market stays free weekly chips (no real-USD prediction markets).
- Money surfaces lead with the aggressive play and name the risk (SAFE · DEGEN · MOON). Never advice; Claude is not a licensed advisor.

---

# CONFLICTS RESOLVED (the owner's latest explicit word wins)
- **One MD vs three new documents (2026-11-09):** GPT proposed three files; his 2026-11-04 rule "always one MD" and his 11-09 "three blocks" win: this page, three blocks.
- **Dev branch (Supreme Intelligence, GPT 11-09) vs main:** tested pushes to main on his go; he tests on 51367 only.
- **Contribution vs rewards:** THE DEAL keeps grade → boost; contribution intelligence only observes.
- **Old deal `bank` vs THE DEAL `stake`:** stake is live; bank stays in code until he says remove it. VERIFY rows CP01-CP08 were written for bank.
- **Sicario's paused (11-05) vs allowed on any proof (11-07):** allowed when asked; Endless, Auto-collect and desk seats stay off.
- **"OSSY and G4 do not code" (11-05) vs they build their own pages (11-07):** they build; no paid stand-in.
- **Older "everything is built" claims** conflict with their own open lists: not a completion certificate.
- **Circle / house-wallet notes differ across REQUIREMENTS, GO_LIVE and DECISIONS:** reconcile owner-only operation vs user custody before building; a cap alone does not settle it.
- **FAMILIA_PLAN and memory/PRD are older specs:** keep their requirements, verify gaps against the code first.
- **Perps:** owner 2026-11-04: no cheap venue with our keys, so agents only propose perps; he tests by hand on Crypto.com.

# IDEAS (not approved)
- Ticket-sized manual picks while the record is red; automatic initial-out on winners; 30-minute hand-pick acknowledgement; fed/trending
  overlap; proven smart-wallet follow; FeeCat + agent pair conversations; a better-coin track. Never remove Pump / New-launch tabs from these
  old suggestions without a fresh request. (Stronger-agents ideas from 2026-11-04 shipped as `mind_board`, colony loss shapes and the loop.)

# DOC MAP (what each MD is for)
- **This page:** every open request. **`CLAUDE.md`:** working rules. **`FEELESS_HISTORY.md`:** the log (grep, never load whole).
- **Guides kept (read when the task touches them):** `DECISIONS.md` (money, custody), `COUNSEL_BRIEF.md` (lawyer), `DEGEN_PLAYBOOK.md` (Fuse, real card),
  `MOBILE_LAYOUT.md` (phone, Duo), `PERPS.md`, `BROKERS.md`, `TELEGRAM.md`, `GO_LIVE.md`, `ALWAYS_ON.md`, `ARCHITECTURE.md`, `AGENT_KERNEL.md`,
  `TRENCH_CREW.md`, `TRENCH_THEORY.md`, `REQUIREMENTS.md` (gates, speed budget, launch presets), `LM_STUDIO_MCP.md`, `FEE_BRAIN.md`,
  `CLAUDE_ACCOUNT_PROMPT.md`, `market-graduation-source.md`, `backend/ai_brain.md` (read by `ai_router.py`), `contracts/fuse_vault/README.md`.
- **The owner's original requests kept word for word:** `SUPREME_INTELLIGENCE_REQUEST.md`, `FAMILIA_PLAN.md`, `REAL_CATS.md`.
- **Leftovers:** SITE-22. `.agents/memory/*` is another tool's memory; Wireface licences are legal files.

# RUN / CHECK
| What | Command |
|---|---|
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` (plain `python` is not on his Mac) |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest`) |
| build | `cd frontend && CI=false npx craco build` |
| push | `git push origin main`: the pre-push hook runs `scripts/gate.sh` once, path-aware. Never `--no-verify`, never edit during a gate. |
| restart a service | Check nothing is building first (`workspaces[].busy`, `powRun`, `popRead`, `pobRead`, `_POC_BUSY`). `kill $(lsof -ti tcp:<port> -sTCP:LISTEN)`; the keep-alive relaunches in 10-25 s. After a `reputation_service.py` change kill 5077 too and check `ps -o etime`; `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1. Watcher: `bash scripts/background.sh status`. |
| real card cash | `backend/.venv/bin/python scripts/cash-check.py degen 30` (every task that touches it) |
| real card money trail | `.venv/bin/python scripts/fuse-report.py 6` |
| is there an edge? | `.venv/bin/python scripts/edge-audit.py` (before any real-money buying advice) |
| test pages | `/dev/cats?general&wallet`, `/dev/colony?owner`, `/dev/features`, `/dev/chats?git`, `/dev/hq?deck=<tab>`; a hidden pane reads 1 fps, never trust it |
| never | move real funds yourself · run a paid call without him · kill his processes · overlap gates · print `.env` lines (mask by NAME) |

**Traps that already bit:** a push that touches `backend/` restarts ALL four services within 30 s (`scripts/auto-pull.sh`), killing any running build or proof: check builds are idle before pushing backend code (COL-1's push restarted them 2026-11-09) · a 5088 restart killed his Monitor build · `_no_keys` drops any key named `setup` from answers · `.dsk-body` is a
stretched grid (`overflow: hidden` items collapse; proof windows use `.prf` with `align-self: start`) · editing a lazy component while the
page is open shows "This tab couldn't render" (reload) · Chrome will not shrink below his screen: test phones in Playwright · shell heredocs
are sometimes blocked: put a script in the scratchpad and run `python3 -I` · Endless shares OSSY and G4 with the real card · Jest stubs
HeroUI, React Flow and echarts, so only a browser proves them · `package.json` pins d3-selection 3.0.0 (a nested copy killed React Flow zoom).

**Where things live:** agents (real card) `agents.py` · `office.py` · `office_edge.py` · `trench_kernel/` · `opportunity.py` · `capital.py` ·
keeper `fuse_wallet.py` · `arena_prime.py` · AI `ai_router.py` · `prompt_studio.py` · `model_desk.py` · `ai_rig.py` · `ai_chat.py` ·
FeeCat `feecat_service.py` · `feecat_brain.py` · `cat_real.py` → `components/feecat/`, `command/CatDesk.jsx`, `CatReal.jsx`,
`CatWorkbench.jsx`, `FeeCatDesk.jsx` · Familia `family_city.py` · `family_world.py` · `block_markets.py` → `FeeCity3D` · HQ
`frontend/src/components/command/` · styles map in `CLAUDE.md › CSS map`.
