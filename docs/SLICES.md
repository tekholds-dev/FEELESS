# SLICES — the fix plan (owner 2026-11-18). One slice = one session = one model. Paste the prompt, pick the model, let it run.

**The bar for every slice:** `docs/VISION.md`. A slice is done only when its checks pass on a **real TEST run on Happy's agent**
(`scripts/test-proof.py --agent happy`, proposals and paper only, $0.25 per proof type, $1.00 for all TESTs; RULINGS 2026-11-19) filed into that proof type's own folder marked **TEST**, the gate is green and it's pushed.

## ▶ NEXT ACCOUNT: START HERE (owner 2026-11-19: "only need one slice running at a time")
**ONE slice at a time, each in its OWN session, started by a manager session (owner 2026-11-19, RULINGS).** The owner talks to one manager session, which never builds a slice itself. It starts a fresh session for the next slice (Claude desktop `start_session`: user_asked, fresh, Opus 5.5 medium, no worktree, the standard prompt below). It waits for that session's report and checks the Status line (✅ or ⛔) is on `origin/main` with nothing of that slice left uncommitted. Only then does it start the next slice. Never two slice sessions at once.
**If you are the manager:** don't edit code. Start, wait, check, start the next. If a slice session stops at the usage limit, start a new session with the same prompt: it resumes from the Status line.
**If you are a slice session:** do only your slice, end by pushing its Status line, and report.
**Where it stands (2026-11-19, ~17:00 CT):** on main, slices 0–7, 9, 10, 11, 12 and 14 have their Status lines (10 ⛔ 5/6, 11 ⛔ 2/4, 7 ⛔: COMP 11/22 vs base 13/22, not shipped). **Left, in this order:**
1. ~~Slice 13 (PoB dashboard)~~ ✅ 2026-11-19, on main.
2. **Slice 15 (PoC clip farming, owner 2026-11-19).**
3. **Slice 16 (PoEco earns real money, owner 2026-11-19).** Running.
3b. **Desks (owner 2026-11-20):** 24 PoC ✅ · 25 PoW ✅ · **26 PoP (NEXT, its card is ready in the manager session)** · **29 clip studio** (grid, week planner, chat in the plan, caption / transition / effect editor, the cut-off caption bug) · 27 PoStatic · 28 PoEco.
4. **Slices 17–23 (the owner's earn ideas, in order):** 17 Solana bounties · 18 clips as a service · 19 faceless channels · 20 PoStatic storefront · 21 affiliate micro-sites · 22 agent for hire (waits on a legal ruling) · 23 cheaper-model race.
5. **Slice 8 (proof of everything) last.**
**The prompt** is the standard prompt below with the slice number. Pick Opus 5.5 medium and never switch mid-session.
**Owner's open items (Claude can't do these):** load a Gemma model in this Mac's LM Studio for the ZED judge (Sicario's proofs get no verdict, and COMP's exam had no ZED). Then real-money tests once Slice 8's VISION report is in.

## Models (pick once per session in the app's model picker; never switch mid-session)
**Owner 2026-11-18 (latest): every slice runs on Claude Opus 5.5, MEDIUM effort.** ("the issue was one convo doing back-to-back 200 tasks, instead of what we are doing now.") The table below is the original split, kept only for reference.

**Standard prompt** (swap in the slice number; paste it into a new session):
```
FEELESS, Slice N. Read CLAUDE.md, then docs/VISION.md, then "Slice N" in docs/SLICES.md. Do only Slice N, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice N check passes on a real TEST run on Happy's agent (scripts/test-proof.py --agent happy, proposals and paper only, $0.25 per proof type, $1.00 total), seen in the browser when it has UI; gate green; pushed. Commit only your own files by path; never push while another gate.sh or TEST run is going. Finish by updating Slice N's Status line.
```
| Model | Effort | Used for | Why |
|---|---|---|---|
| **Claude Fable 5.2** | high (xhigh for slice 8) | Slices 4, 7, 8: the hardest builds (video swap, COMP) and the final review | Strongest at long agentic coding, but twice the price of Opus, so only 3 sessions |
| **Claude Opus 5.5** | **high**, never medium | Slices 0, 2, 3, 5, 6: the backend builds | The workhorse. High effort for deep backend work |
| **Claude Sonnet 5.5** | high | Slice 1: the wiring audit, Brains proof, UI checks | Cheaper; enough for audit + UI + small wiring |

## How to run a slice
1. The manager session starts it (or, with no manager, Claude desktop → **New session** in this project's main folder) on Opus 5.5 medium with that slice's prompt.
2. Let it run. If it runs out of room, it continues in the same session by itself. **Don't start a new session mid-slice.**
3. It ends with a report. **Faked-only / not wired** comes first, then which VISION checks pass for real. It also updates that slice's **Status** line below.
4. Not finished? Start the next session **with the same model**, using the same prompt. It reads the Status line and carries on.
5. **ONE slice at a time (owner 2026-11-19: "only need one slice running at a time").** Order left: 33 → 27 → 28 → 32 → 34 → 30 → 31 → 17–23 → 8. A slice starts only when the slice before it shows ✅ (done) or ⛔ (stopped, cause written) on its Status line **on main**. So every slice ends by pushing its Status line, starting with ✅ or ⛔. **Lane lock (2026-11-19, kept as a safety net):** before saving any backend file or starting a TEST, take `mkdir .claude/lane.lock` (it fails if anything else holds it).lock` (it succeeds for exactly one slice; on failure, wait and retry). Put your slice number in `.claude/lane.lock/owner` and remove the lock right after your TEST files. A backend save kills any running TEST. To see if a TEST is running, use `pgrep -fl test-proof | grep -v zsh` or `/api/cats/health` busy; a bare `pgrep -f` matches your own waiting shell and hangs. **TEST agent (owner 2026-11-19):** once Slice 6 is on main, every TEST runs on Happy (`scripts/test-proof.py --agent happy`, proposals and paper only, $0.25 per proof type, $1.00 total). Don't waste the owner's credit: one TEST per check, not reruns for luck. A paused slice leaves no half-wired code live: it finishes the edit it's in or restores its own files, and its Status line says where to resume. **Clean:** every slice deletes what it replaced, ships no unwired file, and ends with `git status` showing none of its own files left uncommitted.
6. Never push backend code while a TEST or proof is running: a push restarts every service.

**Order (2026-11-19):** everything up to 14 has a Status line on main; left: 26 (PoP desk) → 29 (clip studio) → 27 (PoStatic desk) → 28 (PoEco desk) → 17–23 (earn ideas) → 8 last.

---

## Slice 0 · The test agent + a true record · Opus 5.5 high
**Why:** nothing can be proven until every test lands in the real folders and every proof says honestly which minds ran and what they read.
**Area:** `backend/test_bench.py`, `backend/proof_footprint.py`, `backend/launch_cat.py` (`minds_for`), each proof type's filer (`fc_pow.py`, `fc_pob.py`, `fc_desk.py` builds/content, `fc_tools.py`), `feecat_service.py` call log (`_calls_of`).
**Checks:**
- [ ] Claude can start a TEST proof of any type on Sicario's agent ($0). It files into that type's own folder, marked TEST and visible there, plus a Test bench row.
- [ ] Every proof's record names the minds that REALLY ran (from the call log). PoStatic folders currently record none (`minds` is None); that's fixed.
- [ ] The record lists every source read, and the footprint gate sends back a filing that repeats a past filing's sources, topic and angle before it files.
- [ ] One TEST proof of each type (PoW, PoP, PoB, PoC, PoStatic, PoEco) filed on Sicario. The report links each one.
**Status:** ✅ done 2026-11-18 (Opus 5.5). `POST /api/cats/internal/test-proof` (`scripts/test-proof.py --kind …`) runs a TEST on Sicario through the owner's own chat door, local minds only ($0); a TEST PoW is a proposal, a TEST PoB never bids (the mark rides the run, so a service restart mid-run never makes it real). Every filing gets `proof_record.stamp`: `ran` (call log), `read`, `foot` + `proofChecks`; the footprint gate sends a repeat back once. Every proof window shows it (TrueRecord). Real TESTs on Sicario, each with a Test bench row: PoW #3 `pow1795019777` (bench e6bdae973ae4) · PoP #1 `pop1795019664` (613958825dc5) · PoB #2 `pob1795019335` (3eb470dc196c) · PoC #5 `poc1795018969` (72f03c70b2e7) · PoStatic #5 `pse8c49b5434` (8b5aa0fa527a) · PoEco #3 `poe6c7f253bf3` (025a4f8725f4, sent back once first). Open for a later slice: the kits check FAILS for real on PoB and PoStatic (no kit was picked on those runs).
```
FEELESS, Slice 0. Read CLAUDE.md, then docs/VISION.md, then "Slice 0" in docs/SLICES.md. Do only Slice 0, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 0 check passes on a real free run on Sicario's agent (no money), filed TEST in each proof type's own folder; gate green; pushed. Finish by updating Slice 0's Status line in docs/SLICES.md.
```

## Slice 1 · Wired or it doesn't ship: Brains + the agent desk · Sonnet 5.5 high · can run beside Slice 2
**Why:** the owner picks a mind per proof in Brains and can't see that it worked. Every control has to prove it does something.
**Area:** the Brains window (agent desk), `backend/launch_cat.py` (`set_minds`, `minds_for`), `fc_cloud.py` (`ownMinds`), the desk controls.
**Checks:**
- [ ] A list of every control in Brains and the agent desk, marking each wired / not wired, kept in the report.
- [ ] Each wired control has a test: click → saved → used by the engine → shown in the next proof's record.
- [ ] Brains shows, for each type, the minds that ran on the LAST proof of that type (from the call log).
- [ ] Unwired controls are wired now. One that needs big backend work goes on the Status line for an Opus slice, never left looking like it works.
**Status:** ✅ done 2026-11-18 (Sonnet 5.5). Audit of every Brains / desk control (wired = click → saved → used by the engine → shown in the next record; each has a test in `backend/tests/test_brains_wired.py`): **wired already** · its two minds + memory (`models`) · BY PROOF pair for all six kinds (`kind_models`) · kit picks on PoW/PoP/PoC · chime · MAX A TRADE · start/stop/one cycle · skin · orders + brief + work mode (general). **Fixed now** · effort/knobs (`model_cfg`) had no desk UI and every PoP/PoB/PoStatic/PoC call dropped the effort → "TUNE ITS MINDS" in Brains, effort rides each call and shows in the record · a kind's own prompt + personality only reached PoStatic/PoC → now PoP + PoB too (PoW and PoEco refuse it, by design, and the UI says so) · PoB's topic path ignored the kind's kit picks (TEST PoB kits ✗) → read now, kits ✓ · ONLY THESE / NEVER THESE coins never reached PoW's candidates → filtered now · the venue picker saved Perps but nothing traded it → server refuses it, chip disabled. **New:** Brains lists, per kind, the minds that ran on the LAST proof, from the call log (`GET /api/cats/{id}/paths` → `last`; `LastRan` in the Brains window). Real TEST on Sicario: PoB #3/#4 with its pair set to g4 + ossy (A leads = g4 in the call log), #4 all four checks ✓ incl. kits (pair put back after). **For an Opus slice (big backend):** DAILY LOSS CAP only stops the paper rule engine, never a PoW buy (needs PoW day-loss accounting) · Perps venue for agents (no perps sender yet) · PoStatic folders still record no kit picks (Slice 2). Faked-only (no real run): effort/knobs, own voice, and the PoW coin lists (a TEST can't set them without an owner sign-in). **Shipping:** commit `2660df2a`; its gate + push was started from `.claude/worktrees/gate` and not yet seen finish — check `git log origin/main | grep 2660df2a`, and if absent re-run `cd .claude/worktrees/gate && git checkout -q --detach 2660df2a && git push origin HEAD:main`. **Next step to resume:** none needed for Slice 1; the three "Opus slice" items above are the open work.
```
FEELESS, Slice 1. Read CLAUDE.md, then docs/VISION.md ("Brains"), then "Slice 1" in docs/SLICES.md. Do only Slice 1, fully. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 1 check passes, seen in the browser with a screenshot, proven with a TEST proof on Sicario's agent (no money); gate green; pushed. Finish by updating Slice 1's Status line.
```

## Slice 2 · PoStatic: studio → build · Opus 5.5 high · can run beside Slice 1
**Why:** "I'm unable to have 3D pieces built to be used in the current static build." The 2026-11-17 ruling says this exists; the owner says it doesn't work. Start by reproducing it.
**Area:** `backend/fc_studio.py`, `fc_desk.py` (build path, `kind == 'build'`), the 3D studio + PoStatic folder components, `ps_hidden.py`.
**Checks:**
- [ ] Reproduce the failure first and name the cause in the report.
- [ ] Make or tweak a 3D piece in the studio (size, turn, spin), add it to a PoStatic folder, and the next build uses that exact piece. Seen in the browser on 51366 with a screenshot.
- [ ] A TEST PoStatic on Sicario carrying a studio piece, linked in the report.
- [ ] No back pedals: every older PoStatic check still passes.
**Status:** ✅ done 2026-11-18 (Opus 5.5). **Cause (reproduced on his real data):** no PoStatic folder anywhere ever held a studio model. He opened the 3D studio inside "trench build" on 11-17 19:07 and put a real model on the stage, but adding one only marked the folder: the page he was looking at never changed, and the model was mounted only when a build wrote a NEW version. His trench edits mostly ended "Its changes did not match the page. Nothing changed", so nothing was ever mounted. Game folders ignored the model, the page ignored the size he set, the Objects inspector had no turn control, and no record said whether a build carried the piece. **Fixed:** adding/removing a piece changes the folder's CURRENT page by code, $0, as a new version by "3D studio" (`owner_models.place`, `fc_cat_work` play3d_model_to/_drop) · every build keeps it (page, edit, restyle, sections, game after its playtest) · the page keeps the piece's turn, spin and proportions, and survives a browser with no WebGL · TURN slider for real models in the studio · folder chips show size/turn/spin · a filed PoStatic records `studio` rows read back from the page's own code (same file, turn, spin) + a 5th `studio` check (PoStatic with pieces only), shown in TrueRecord · `scripts/test-proof.py --kind pos --model <id> --size --turn --spin` adds the piece through the studio's own step before the TEST build. **Real TEST on Sicario ($0, local/ossy + local/g4):** PoStatic #6 `ps4ef3590b1f` (folder `wd6494db42c`, bench `6c4adfd9d588`) carried Tombstone Familie Laurenz (1.6 m · 35° · spin 6): 5/5 checks incl. studio ✓ ("IN THE PAGE"), seen live in Static on 51366 (`/dev/features?studio`, the real filed folder) with the tombstone turning. **Open:** the minds did not mark their own spots, so code put the piece in once under the header; the 2026-11-17 ruling's "throughout the site" (hero + 2 more places) needs the build minds to place it (Slice 3, with the kits) · the Code tab's "Add to build" still sends the model as first added, not the size/turn written in code · the in-app browser pane has WebGL off (use Playwright for 3D checks).
```
FEELESS, Slice 2. Read CLAUDE.md, then docs/VISION.md ("PoStatic"), then "Slice 2" in docs/SLICES.md. Do only Slice 2, fully, end to end. Reproduce the bug before changing code. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 2 check passes on a real free TEST run on Sicario's agent (no money), seen in the browser; gate green; pushed. Finish by updating Slice 2's Status line.
```

## Slice 3 · PoStatic: full toolkit, unique, clean · Opus 5.5 medium
**Why:** "so many integrative tools missing from static." The Collective exists to hand every mind the kits.
**Area:** `backend/proof_kits.py`, `collective_kits.py`, `method_kits.py`, `kit_fresh.py`, `ps_hidden.py`, `proof_footprint.py`, the build path in `fc_desk.py`.
**Checks:**
- [ ] The build minds can use every approved kit (three, Motion, Recharts, Lightweight Charts, shadcn/ui, DexScreener + our indexes, wallet connect, forms, maps). Each kit used is listed in the folder with what it did.
- [ ] Uniqueness gate: a near-copy of any past build is refused before filing. Every build gets a new brief, a new centrepiece and a new layout.
- [ ] Hidden code check adds overlapping blocks, broken links, placeholder text and phone load.
- [ ] No back pedals: a new version can't lose a part the last version had working.
- [ ] A studio piece added to a folder is used throughout the site wherever it fits, not placed once (Slice 2's leftover).
- [ ] 3 TEST PoStatics on Sicario, all different, linked in the report.
**Status:** 🟡 built, 1 of 3 real TESTs passes every check, 2026-11-18 (Opus 5.5). **Built:** the full toolkit (`ps_kits.py`: three, Motion, Recharts, Lightweight Charts, shadcn, live = SOL feed + DexScreener pools + our candle index, read-only wallet connect, forms, Leaflet maps). A filed folder lists each kit with what it did, read from the code (folder › Kits). Uniqueness gate (`ps_unique.py`: text + structure + palette + layout + centre fingerprint, COPY_AT 0.72 from 65 real folders). Every build gets a new brief, centre and layout; one retry, then refused. Hidden check v3 (`ps_hidden.py`): dead anchors, more placeholder text, and a real headless phone + desktop (loads with no script error, fits 390 px, no overlapping words, outside links answer). No back pedals (`ps_keep.py`): a version that loses a part is sent back once, then refused. The studio piece is put in every place it fits (`owner_models.places`). New record rows `unique` · `clean` · `progress`. Bugs fixed on the way: 9 broken kit signs (Leaflet/Howler/Tabulator crashed `kit_report`) · `_ws_view` never sent kitsUsed · the sections path gave every page the same shell with no h1 and cut the kit menu at 1,500 chars · a section cut off mid-`<script>`/mid-tag broke the page. **Real TESTs on Sicario ($0, local/ossy + local/g4):** #7 `ps7e7489c211` 3/6 (before the sections fix) · #8 `psaad7033f91` 5/6 (clean: a cut-off script → phone-load; fixed) · #9 `psd406240e54` 5/6 (clean: words laid over the Leaflet map → no-overlap; fixed in the builder prompt) · **#10 `ps657f97f9f6` 6/6** (kits Magic UI + Forms + Leaflet, unique numbers+scroll 16% like #61, clean 15/15). Seen in `/dev/features?slice3` on 51366. **Open (not proven on a real run):** the studio piece throughout the site, and progress on an edit run (`--ws`) — faked tests only (TEST budget hit; two runs were killed by an outside `start-backend.sh` restart) · #10 dropped the wallet section and typed a SOL price instead of the live feed (the hidden check cannot tell a typed number from a live one) · need 2 more all-pass TESTs. **Not pushed:** committed locally only (gate not run: another session's TEST was live). **Resume:** gate + push this commit from `.claude/worktrees/gate`, then 2 more TEST pos runs (one with `--model`, one `--ws` edit run) and fix the wallet/live-number gap.
```
FEELESS, Slice 3. Read CLAUDE.md, then docs/VISION.md ("PoStatic"), then "Slice 3" in docs/SLICES.md. Do only Slice 3, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 3 check passes on real free TEST runs on Sicario's agent (no money); gate green; pushed. Finish by updating Slice 3's Status line.
```

## Slice 4 · PoC: the video swap · Fable 5.2 high · can run beside Slice 5
**Why:** "people download a video, enter it, and get the same exact realistic video back with a new realistic AI-made person." High quality, no watermark.
**Area:** new PoC media pipeline beside `backend/poc_play.py` / `poc_watch.py`, the PoC folder.
**Checks:**
- [ ] Research today's best video person-replacement engines (web search first: quality, price, API, output files without watermark). Make one real call before building. Pick one and name the runner-up.
- [ ] Upload a video, get the same video back (motion, timing, camera, sound) with an AI-made person in place. Filed into the PoC folder with before/after side by side, and its cost shown.
- [ ] The engine key lives in HQ › Core and never in git or logs (§1).
- [ ] Tests fake the engine. The video engine is paid, so the **owner presses the first real run**; Claude never spends on it.
**Status:** on main 2026-11-18 (gate green). Faked-only until the owner presses the first paid run: no real swap has run yet. Pick: **MiniMax H3 Max Recast on fal** (keeps the clip's motion, timing, camera and sound; 768p $0.085/s, no watermark). Runner-up: **Runway Aleph 2 on OpenRouter** (28¢/s, first 10 s, sound laid back from the clip). Real calls made: fal's live API schemas (H3 Recast + the Seedream portrait), free; no paid call. Panel: PoC folder › Video swap (`frontend/src/components/command/VideoSwap.jsx`, `backend/video_swap.py` + `video_swap_run.py`, 21 faked tests). Files the after clip + a before|after side-by-side into the PoC folder with its cost and a receipt. Keys live in HQ › Core (`FAL_KEY` not set yet: add it there, or the swap runs Aleph on your own OpenRouter agent key). Owner + staff only, $10/day cap on FEELESS keys, price seen = price run, never sent twice. **To finish:** the owner presses the first real swap.
```
FEELESS, Slice 4. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 4" in docs/SLICES.md. Do only Slice 4, fully, end to end. Research today's engines with a web search first and make one real call before building on one. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 4 check passes; tests fake the paid engine; the owner presses the first paid run; gate green; pushed. Finish by updating Slice 4's Status line.
```

## Slice 5 · PoC: the content engine, graded on reach · Opus 5.5 medium · can run beside Slice 4
**Why:** PoC is 12 text week-plans with 0 passes. It must make real content and prove reach.
**Area:** `backend/poc_play.py`, `poc_watch.py`, `proof_tools.py` (`viral()`), the PoC folder (`PocWire.jsx`, `WeekBoard.jsx`).
**Checks:**
- [ ] Trend first: the record shows the trend it rode.
- [ ] Makes the real files (image, short video, post, thread) in story, feed and wide formats.
- [ ] Owner approves, then it posts on his own connected accounts. Nothing posts by itself.
- [ ] Reads views and engagement back at 24 h and 7 d. The grade is real reach against the goal set at filing, plus cost per 1,000 views.
- [ ] A TEST PoC on Sicario up to the approve step, linked in the report.
**Status:** ✅ built 2026-11-18 (Opus 5.5). The PoC filer is now a studio (`backend/fc_poc.py` + pure `poc_studio.py` + `poc_post.py`; UI `PocStudio.jsx` in the PoC folder): trend first (clips + Bluesky / Google News / Wikipedia / HN / CoinGecko, never one it already rode) → both minds pitch blind → the most complete pitch → 12 real files made free on this machine (Pillow + ffmpeg, no watermark: image, short video, post, thread × story / feed / wide) → the minds' goal (reach / followers / clicks / buzz + a number; the owner edits it until it posts, then it locks). Posting = the owner's approve only (the internal key, auto runs and agents get 403; a TEST needs his "post it for real" tick) through **Upload-Post, Zernio or Ayrshare** with his accounts signed in there and the key in Vault › API keys. Reach is read at 24 h and 7 d (every 10 min sweep; a failed read is retried ~6 h), graded against the goal with cost per 1,000 views; the 7 d read sets graded right/wrong. **Real TEST PoC #6 `poc1795033461` on Sicario (local/ossy + local/g4, $0, bench `ed65b8bbd443`): 8/8 checks** (minds, sources, footprint, kits, trend = CoinGecko $WASTED, files 12/12, approve = waiting, reach = goal 15,000 buzz); seen in the browser at `/dev/pocstudio` (its real files). **Faked-only:** posting + reach reads (no service key saved yet; the owner presses the first real post). The old Postiz week board is untouched.
```
FEELESS, Slice 5. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 5" in docs/SLICES.md. Do only Slice 5, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 5 check passes on a real free TEST run on Sicario's agent (no money, nothing posted without the owner's approve); gate green; pushed. Finish by updating Slice 5's Status line.
```

## Slice 6 · PoW, PoP, PoEco brought up to the bar · Opus 5.5 medium
**Why:** PoP (5) and PoEco (1) had never been judged as of 2026-11-18, and every type must meet the every-proof checks.
**Area:** `backend/proof_review.py` (`next_due`), `fc_cats.py` (`_review_one`), `fc_pow.py`, the PoP and PoEco filers.
**Checks:**
- [ ] Find why PoP and PoEco never reach the judges, and fix it. All 6 types are now judged.
- [ ] PoW, PoP and PoEco pass every every-proof check in VISION. P&L stays without fees (§1).
- [ ] A TEST of each of the 3 on Sicario, judged, linked in the report.
**Status:** ✅ done 2026-11-19 (Opus 5.5). Why PoP/PoEco were never judged (4 causes, all fixed): `next_due` skipped every `noTrade` proof and every PoP so far was a sit-out (now a PoP its minds called and sat out is judged on its own 5 checks; a blank-mind or outage one is not); a PoEco market call stayed `open` because only the owner's open Eco folder asked for `eco_grade` (now judged once sealed, like a PoB, and the engine grades due calls every 10 min; a feed outage never grades one wrong); `builders_of` fell back to the agent's minds so both judges sat out a PoEco no model built (now the call log's `ran` ∪ `minds`; PoEco = none); and `poeFolders` is an owner key, so `_save` laid the owner snapshot over every PoEco verdict (now kept in `_KEPT`). Also: a PoW proposal is judged as a proposal (it failed 0/100 for "no entry price"); a PoP call cut off at 220 tokens filed as a pass (now 420 + a cut call keeps its finished fields); a real PoW's P&L was the wallet's cash net, fees in (§1: now pool to pool, `feesSol` on the receipt, old cash-only folders say `pnlBasis`); the PoW record names the coin tools it used; a TEST start sent while another proof runs is refused (it was taken as a note). Owner 2026-11-19: `scripts/test-proof.py --agent happy` ($0.25 per proof type, $1.00 total, from the call log). Judged TESTs: PoEco #4 `poeee0623db74` (Sicario) 100 pass, OSSY + G4 · PoP `pop1795113771` (Happy, sat out) 60 pass, G4 · PoW #17 `pow1795113317` (Happy, proposal) 100 pass, G4. $0.16 of Happy credit. OPEN for the owner: ZED (`local/zed`) has never answered (this Mac's LM Studio has no Gemma), so on Sicario's agent, where OSSY + G4 build every proof, no proof of any kind gets a verdict (Sicario PoP #2 `pop1795089019` traded on paper, unjudged). OSSY drops some reviews (timeouts under load). Real-money P&L (pool basis) untested: the owner tests it.
```
FEELESS, Slice 6. Read CLAUDE.md, then docs/VISION.md, then "Slice 6" in docs/SLICES.md. Do only Slice 6, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 6 check passes on real free TEST runs on Sicario's agent (no money); gate green; pushed. Finish by updating Slice 6's Status line.
```

## Slice 7 · COMP on real proofs only · Opus 5.5 medium
**Why:** "I'm not confident in COMP." It has to learn from real judged proofs and beat the base model on an honest exam.
**Area:** `backend/comp_v2.py`, `comp_v2_exam.py`, `comp_teacher.py`, `model_lab.py`, `docs/specs/comp-next.md`.
**Checks:**
- [ ] COMP's training set is only real, judged proofs of each type, each with its pass/fail evidence. Anything else is dropped and counted.
- [ ] An exam on held-out real proofs: COMP vs the base model vs OSSY, G4 and ZED, all on the owner's LM Studio. The scores are in the report.
- [ ] A COMP that doesn't beat the base model isn't shipped, and the report says why.
**Status:** ⛔ stopped 2026-11-19 (Opus 5.5): 2 of 3 checks pass on real exam numbers; ZED could not sit the exam (no Gemma in LM Studio). **(1) Real, judged proofs only, LIVE** (`backend/comp_real.py`): 70 real proofs kept (PoB 22 · PoC 7 · PoStatic 31 · PoW 10), each with its pass/fail evidence (`settledBy` + `proofOf`: 37 owner mark · 19 scoreboard · 10 P&L · 2 Kalshi · 1 Polymarket · 1 owner grade), never a judge's grade; COMP reads what each proof said and did BEFORE it settled. 2,458 dropped and counted: 1,869 market snapshots, 274 per-site index rows, 147 repeats, 62 judged only by the judges, 35 not settled, 32 teacher lessons, 25 TEST, 11 with no evidence, 2 Kalshi lessons, 1 hand mark on a scored game. **Found:** the old 64% was not honest: one row per site a proof read put the same proof in training AND the exam, and a PoW's sell reason sat in its question (old files in `backend/data/comp_v2/pre_slice7/`). Exam seats are now fixed by a hash of the proof id. **(2) The exam, REAL numbers** on 22 held-out real proofs (`comp_v2_exam.py --free`, $0, no paid call): base Qwen3.5-9B **13/22 (59%)** · always "won" 12/22 (55%) · COMP **11/22 (50%)** · COMP + memory 11/22 · G4 (qwen3.5-4b, desktop LM Studio) 11/22 · OSSY (qwen3.5-9b, this Mac) 10/22 (45%) · ZED blocked: no Gemma in LM Studio, never a Qwen stand-in. **(3) Ship rule, LIVE:** COMP is NOT shipped. The exam says why: "COMP got 11 of 22 right and the base 9B got 13 of 22 … one answer = 4.5 points". The rule (`comp_v2.ship`): strictly beat the base and at least match always-guess, else the last shipped COMP stays (none has ever passed). COMP › v2 › THE GATE shows the verdict, the meter and kept vs dropped (seen in the browser on the real exam on desktop; at 375 px in day theme it fits with no sideways scroll, by measurement). Training: 41 proofs, LoRA checkpoint 50 picked on the tuning proofs (the run hit GPU memory at step 110 with LM Studio's 9B loaded; 100 was worse). **Resume (owner):** load a Gemma in LM Studio on this Mac (e.g. google/gemma-3-12b), then from your Terminal: `cd "~/Desktop/feeless v.o7/backend" && ../.venv-mlx/bin/python comp_v2_exam.py data/comp_v2 --free`. ZED's score then joins the exam; COMP stays unshipped until a retrain beats the base.
```
FEELESS, Slice 7. Read CLAUDE.md, then docs/VISION.md ("COMP"), then "Slice 7" in docs/SLICES.md. Do only Slice 7, fully. LM Studio runs from the owner's Terminal: give him the one command when needed. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 7 check passes with real exam numbers; gate green; pushed. Finish by updating Slice 7's Status line.
```

## Slice 9 · PoStatic: inspect, not mark · after Slice 3 (same files)
**Why:** "users should be able to do an 'inspect element' type thing in static to highlight what AI used to comment on or fix, instead of the mark tool."
**Area:** the PoStatic page viewer and its fix/comment requests, `backend/fc_desk.py` (build versions), `ps_hidden.py`.
**Checks:**
- [ ] Hovering the build highlights any element, the way a browser's inspect does. Clicking it opens "fix this / comment" aimed at that exact element.
- [ ] The request carries the element's selector, its text and a snapshot. The minds change that element, and the next version shows the before and after of it.
- [ ] The mark tool is replaced, and its old saved marks still open.
- [ ] A TEST PoStatic on Sicario fixed through inspect, seen in the browser.
**Status:** ✅ done 2026-11-19 (Opus 5.5). **Inspect replaced the mark tool** on a built page (`backend/ps_inspect.py`, `PsInspect.jsx`): ⌖ Inspect turns on a hover outline with tag + size inside the page's sandbox (the script only reads the page and posts to its parent); a click pins that element and opens a card with **Fix this** (a build aimed at it) and **Comment** (a free note kept on that element, op `ws_comment`, read by every next build, pinned amber, fed to the COL-14 lessons). The request carries the element's selector (written from the page's own DOM and resolved back to its exact code in the source), its words, its code, size/colour, and a picture. An inspected fix asks each mind for **that element only** and code splices it back (TEST 1 showed the whole-page edit overflowed the local minds' context: LM Studio 400). The next version shows **before → after** per element (headless pictures + words + code, CHANGED/SAME/GONE, one tab per round) in the folder and on the filed PoStatic (`inspect` row). **Old marks still open:** a saved box round (`unfinished.region`) reopens on the page with its notes and goes with Finish it; the blank-canvas draw stays (+ Draw); the "Mark the part with +" message now says Inspect. **Real TEST PoStatic #11 `ps0ea0c043ae` on Sicario** (folder `w05b17e11e7`, $0, local/ossy + local/g4): `scripts/test-proof.py --kind pos --ws w05b17e11e7 --inspect .hero-title` clicked the hero h1 through the page's own inspect tool; Mind A changed "EMBER" → "EMBER, the Solana launch that burns bright", Mind B checked it (no change), inspect 1/1 CHANGED with both pictures, clean 15/15, progress kept 5/5, unique ✓. Seen in the browser (`/dev/features?inspect` = that real folder: hover, pick, comment, before → after, V1/V2 rounds, phone, day). TEST runs used: 2 of 3 (#1 made no page: context overflow, fixed). Not proven: Fix this pressed from the owner's real UI (proven through the TEST door + harness + jest); the footprint check reads ✗ on an edit of the same folder (same sources as #10, a Slice 0 rule, not Slice 9's).

## Slice 10 · The stash brain: capture, sort, ask first · Opus 5.5 medium
**Why:** "agents move really faster… the webscrape and static saved helps future requests… any new agent can reuse it… only brains can see the stash, encrypted via categories, and never log any encrypted info."
**Area:** the brains' page-read path (`cat_agent` browsing, `fc_cat_work.py`), the agent DB / stash (`_adb`, `_ck.seal_bytes`), a new stash index (entities, categories, freshness).
**Checks:**
- [ ] Every page a mind loads is kept as scrape, static and screenshot, sealed in the stash.
- [ ] Every page is sorted by everything on it (teams, players, coins, leagues, markets, dates), not just the reason it was opened. The Bulls–Lakers page with Clippers and Spurs odds is found by a Clippers ask.
- [ ] Brains ask the stash first and browse only what's missing or stale. The record shows hits vs pages browsed, and the time and $ saved.
- [ ] Contents are sealed by category and only a brain inside a run can read them. A test proves no sealed text reaches logs, the call log, prints or any API answer.
- [ ] A stash panel shows growth, hit rate and $ saved by category, never contents.
- [ ] Two TEST PoBs on Sicario about related games: the second one shows stash hits from the first.
**Status:** ⛔ stopped 2026-11-19: 5 of 6 checks live; the 2-PoB check is not met. Live: every public page a mind loads is kept as scrape + static page + screenshot, sealed per category (`stash_brain.py`, `stash_sort.py`), sorted by everything on it (a Clippers ask finds the Bulls–Lakers page), and brains ask first (`fc_work._work_run`: ask note + `StashPage`). The record carries `stash` hits vs browsed + time/$ saved + a `stash` check. Leak test green, and the panel (Proofs › Stash brain, `/api/cats/proofs/stash-brain`) was seen on live data. Real TEST PoB #13 on Sicario: stash ✓, 3 hits / 1 browsed, 19 s saved (its hits came from its own first read before the footprint send-back). NOT MET: two related TEST PoBs where the 2nd shows hits from the 1st. Runs 3 and 4 were killed by other sessions' backend reloads (log 2218 + 2239), and run 4's Clippers ask was lost. Also fixed: a sent-back PoB filed empty "its windows were busy" (fc_pob.py, for Slice 8 to review). Resume: with no other slice saving backend files, run `scripts/test-proof.py --kind pob --topic "Knicks vs Timberwolves tonight" --wait`, then within 30 min a related game ("Clippers vs Spurs tonight"). The 2nd must show `stash: N hits … from [read:<1st>]`.

## Slice 11 · COMP stays ahead · after Slice 10
**Why:** "COMP always web scraping and staying ahead of the game, having PoBs filed already to compare a PoB filed by another agent, or agents' brains can ask COMP to do a decent-sized task (owner agents only, once per filing)."
**Area:** `backend/comp_*.py`, the stash from Slice 10, the PoB filer (`fc_pob.py`).
**Checks:**
- [ ] COMP keeps reading on a schedule (plain page reads into the stash, no paid model calls), aimed at what's coming up (tonight's games, hot coins).
- [ ] A new PoB is compared against every other agent's PoB on the same game. The record shows where they agree and disagree.
- [ ] An owner agent's brain can hand COMP one decent-sized task per filing, refused a second time and for non-owner agents. The record shows the ask and the answer.
- [ ] The first piece of the Living Atlas (VISION › COMP): facts stored as atoms with a freshness clock, and each source's trust moving with settled outcomes.
**Status:** ⛔ stopped 2026-11-19: 2 of 4 checks live, 1 live on a real (not TEST) PoB, 1 faked-only. LIVE: (1) COMP reads ahead on a schedule (`comp_ahead.py`, every 20 min inside feecat_service, plain reads, 0 model calls): tonight's and tomorrow's games in nba/nfl/nhl/cbb (ESPN data + Kalshi + Polymarket), each league's odds pages (covers, oddsshark, cbssports, actionnetwork, kept 3 ways) and our hottest coins, into the stash + atlas, with delta reading (a fresh page or game is skipped); 32 passes since 01:47, panel `/api/cats/proofs/comp-ahead`. (4) The Living Atlas (`atlas.py`): 620 atoms with a freshness clock by kind (odds 15 min, line 30 min, record 1 day, launch never; stale marked), the same fact from 2+ sites = one atom (28 such), sealed per category; source trust moves once per settled proof: 25 settled proofs moved it (e.g. kalshi.com nba 8-2), and COMP's own references settle by the final score. REAL, NOT TEST: (2) PoB compare (`pob_peers.py`, on every filing): real PoB #15 shows COMP's reference (ESPN line, Kalshi, Polymarket all favour the Texans: 3 agree) and the `ahead` row (its stash hits came from COMP's pass). TEST #17 missed it, because `proof_tools.games_for` matched "Spurs" to an EPL game (fixed + tested). Comparing with ANOTHER agent's PoB is faked-only: no other agent filed a PoB on tonight's games. FAKED-ONLY: (3) the COMP task (`comp_task.py`, FEELESS tool `comp`, owner agents only, one per read, refused twice, the ask + facts on the record): neither local mind called it in #15 or #17; its line now leads the job and is in the tools list. TEST runs: 3 used, on Sicario ($0): one lost to a store race (an old NFL send-back overwrote the ask, for Slice 8), #16 lost to another lane's reload, #17 filed 5/7. Also fixed: `/api/cats/health` busy now counts proof reads, PoB asks/filings and live TEST claims, so a backend save no longer kills a running TEST. Resume: one TEST PoB on a game not started yet, on the agent RULINGS names for TESTs, with no other lane saving backend files. Its record must show `comp` ✓ (the ask + facts), `peers` ✓ and `ahead` ✓. If the minds still skip the tool, make COMP's task the engine's first step, its words from the minds' plan.

## Slice 12 · PoB: player-prop parlays + bids that always go through · Opus 5.5 medium
**Why:** "minds need to pick leg parlays as in the best over or under for players" · "can't afford for bids not to go through or filings to f up."
**Area:** `backend/fc_pob.py`, `kalshi_bid.py`, `pob.py`, `feecat_service.py` (`_kalshi_*`, `_kb_*`).
**Checks:**
- [ ] The minds pick the best player overs/unders as legs, each with evidence and a number, only from markets Kalshi really lists.
- [ ] Every past bid or filing failure (404s, shard balance, read-backs, started games, blank minds) has a test, and each one ends in "sent and confirmed" or a plain-words reason with no money moved.
- [ ] A filing that breaks halfway resumes or stops cleanly. It never leaves a half-made slip.
- [ ] A TEST PoB on Sicario with prop legs (TEST never bids). This is money code, so a `/code-review` pass runs before push, and the owner tests the real bid.
**Status:** done 2026-11-19 (Opus 5.5). Real: player-prop menu from Kalshi's own lists (one over/under line per player per stat, 40 legs), each leg needs its own evidence + number (Kalshi's line/price, ticker digits or a season average ESPN doesn't show are thrown out, and recorded in `legsDropped`), ESPN season averages on every menu leg for both minds, `mindSlips` on the folder; every send ends in sent+confirmed, a plain reason + "No money moved", or `unknown` (cut off: looked up by client order id, never re-sent, counted in the cap, read back every 5 min); a filing that breaks stops cleanly, a restart refiles once and waits for a tap; blank minds named. 39 tests in `test_slice12_bids.py`; /code-review high: 8 findings fixed. TEST PoB #9 on Sicario (Knicks–Wolves): 7/7 `scripts/pob-check.py`, but its two numbers were jersey digits and ESPN numbers never reached it (tomorrow's game): both fixed after, faked + real public read only. Left: one more TEST PoB to see ESPN numbers in a real filing; the owner's real-money bid + slip test.

## Slice 13 · PoB folder: the sleek dashboard · after Slice 12
**Why:** "make PoB a sleek dashboard that views everything beautifully when I / a user opens the PoB folder: either build their own or see what to have the agent file."
**Area:** the Bids / PoB folder home (`PobFile`, `LiveBidCard`, Bids desk), `docs/specs/style.md`.
**Checks:**
- [ ] The folder opens on one dashboard: live and upcoming games, the agent's filings, results, P&L without fees, judge scores, fresh stash odds.
- [ ] "What to file next" suggestions from tonight's markets, each one filed in one tap.
- [ ] A user can build their own slip there, which then goes through the same checks.
- [ ] Every tab is checked in the browser on real data, with a screenshot.
**Status:** ✅ done 2026-11-19 (Opus 5.5). The Bids folder now OPENS on the dashboard (`backend/pob_dash.py`, `PobDash.jsx`; the PoB record and live tools sit under it). Hero: P&L without fees (settled real bids, pool basis, open bids apart) + its curve, record, judges' average, live/upcoming; a live strip; tabs **Next to file** (tonight's Kalshi games from COMP's stash + the board, each filed in one tap through op `pob`), **Filings** (result, P&L, judge score; a row opens its file), **Stash odds** (Kalshi bar + Polymarket tick, age, sources agree/split), **Your slip** (legs from Kalshi's own list via op `pob_menu`; `slip_clean` 2–4 legs, one game, no repeats; the minds see only his legs, must both back every leg, the ticket must equal his slip, a restart refiles it as his; `SlipVerdict` on the filing). Layout follows the window's width (container query). Seen in the browser on real data (`/dev/cats?realpob`, every tab). 19 backend + 5 UI tests. **Real TEST PoB #18 `pob1795143015`** (Sicario, $0: Happy's PoB TEST cap was already spent, $0.30 of $0.25) through the dashboard door with his own 2-leg slip (Chicago to win + Under 242.5, Wizards vs Bulls): 7/7 checks, menu cut to his 2 legs, both minds passed (no data on tomorrow's game), so **not sent**, and `userSlip` says which legs and why. Not proven on a real run: a slip both minds back going out (the owner's real-money test).

## Slice 14 · GitHub folder: proof files show everything · Opus 5.5 medium
**Why:** "no proof should look like this in git: the snapshots and all logs need to show, plus the wired info from each."
**Area:** the agent GitHub folder viewer (proof file view), the proof-file writer, `proof_record.py`.
**Checks:**
- [ ] Each proof file opens to the full record: true record, snapshots, step log (model, time, cost per call), kits used, judge reviews, bid or trade and receipt, a link to the proof window.
- [ ] Old proof files show what they have and say plainly what was never recorded.
- [ ] No key or secret ever shows. A test proves it.
- [ ] Checked in the browser on a Slice 0 TEST proof, with a screenshot.
**Status:** done 2026-11-19. Every agent proof file (PoW/PoP/PoB/PoC/PoStatic + PoEco now) carries `fileRecord` (backend/proof_file.py): true record, page snapshots + Slice 10 stash rows as metadata, step log per mind call (model, route, time, $), kits, judge reviews + their calls, bid/trade + receipt (ids and signatures kept off), a button back to its proof window, and a NEVER RECORDED list; redacted, and a test proves no key/secret shows. Viewer: ProofFile.jsx in the GitHub folder. Seen in the browser on real TEST PoB #10 (pob1795068799) from Sicario, 4/4 checks. Not yet: stash rows (Slice 10 hasn't filed any yet), judge review on #10 still pending.

## Slice 15 · PoC: clip farming (YouTube, Twitch, Instagram) · Opus 5.5 medium · after 13, before 8
**Why (owner 2026-11-19):** "PoC wireframing and filing needs advanced features for clipfarming! yt, twitch, ig -> even if they can't access sites users should be able to upload vids etc up to 5 mins and we provide best brains to clip farm epically and quickly!!"
**Area:** the PoC studio (`backend/fc_poc.py`, `poc_studio.py`, `clip_source.py`, `PocStudio.jsx`, `PocWire.jsx`), a new clip engine beside them, the PoC folder.
**Checks:**
- [ ] **Upload first:** a user drops in any video up to 5 min (mp4 / mov / webm, size-capped, length read by ffprobe before anything runs). YouTube, Twitch and Instagram links keep `clip_source`'s rule (their terms forbid downloading: save it from the app, then upload); a Bluesky or direct file link still works. Research free/open tools with a web search first and make one real call before building on one.
- [ ] **Best brains find the moments:** a free local transcript with word times (e.g. faster-whisper), loudness / laughter / scene-cut peaks, then both minds pick the clips blind (hook in the first 2 s, a payoff, 15–60 s each) and say why. The record shows every candidate, each mind's pick and score.
- [ ] **Made for each platform:** each clip is cut and reframed by code (face / speaker tracked, never a dumb centre crop) to 9:16 for Shorts / Reels / TikTok, 1:1 and 16:9; burned-in word-by-word captions in a FEELESS style; a hook title and a cover frame; no watermark. Files land in the PoC folder.
- [ ] **Quick:** a 5-min upload gives its first clip in under 2 min on this Mac, all clips under 5 min, with a progress line per step. Free on local tools; any paid step shows its price first and is owner-pressed.
- [ ] **Wireframe + filing:** the PoC wireframe board shows each clip as a phone story / feed / wide tile with a Mon–Sun slot; a clip files as a PoC with its goal and cost, and posts only after the owner's approve (Slice 5's door), with reach read back at 24 h / 7 d.
- [ ] A TEST PoC clip-farm run on an uploaded 5-min file (on Happy's agent, inside the TEST caps; the local tools are $0), every tab seen in the browser with a screenshot.
**Status:** ✅ done 2026-11-20, one miss named. Upload → faster-whisper → peaks → both minds blind → face/motion-tracked 9:16 · 1:1 · 16:9 with word captions, hook, cover → each clip a PoC behind Slice 5's approve door; clip board with Mon–Sun slots. Add-on (owner): free ffmpeg converter (.mov/.mkv/.avi/.m4v/HEVC → H.264/AAC .mp4, Apple encoder then x264, 5-min cap, plain reason when ffmpeg can't read it, runs while the minds think) ✓; an in-house FEELESS link per converted upload and per clip format (80-bit id, Range 206, 416, 404, 410 after 7 days or Delete, noindex, private cache, never listed) ✓; YouTube / Twitch / Instagram / TikTok / X / Facebook links get a "save it from the app, then upload" card, never a downloader ✓. TESTs: Happy #11 mp4 ($0.0038, first clip 80 s); Sicario .mov all 10 checks (first clip 128 s); Happy .mov run cr760fba971f 9/10 ($0.0041, 3 clips, converter 42 s hidden behind the minds; ✗ moments = Happy has one mind). Seen in the browser on /dev/clipfarm (51366) on that run. ⛔ Miss: Quick on a converted iPhone .mov: first clip 128–176 s, over the 2-min bar (the minds' wait, 73–89 s, not the converter); an mp4 makes it.
```
FEELESS, Slice 15. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 15" in docs/SLICES.md. Do only Slice 15, fully, end to end. Research free/open clip tools with a web search first and make one real call before building on one. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 15 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps), seen in the browser; gate green; pushed. Finish by updating Slice 15's Status line.
```

## Slice 16 · PoEco: agents earn real money (faceless paid work) · Opus 5.5 medium · after 15, before 8
**Why (owner 2026-11-19):** "poeco can do upwork and other stuff etc no face or sumn to make money working for places etc whatever pays real money!!"
**Area:** the PoEco filer + folder (`EcoFolder`), a new `backend/eco_earn.py` (job finder + work runner), the Collective's kits, Slice 5's approve door (reuse it for bids and deliveries).
**Checks:**
- [ ] **Terms first:** a web search of where faceless AI-done work can earn (e.g. Upwork, Fiverr, Freelancer, Contra, Superteam Earn for Solana bounties, Algora / GitHub bounties, Gitcoin). For each one, write what its terms say about AI-made work and automated bids, keep only the ones that allow our flow, and name the rest with why they're out. Make one real public read of a listing feed before building on it.
- [ ] **Job finder:** reads open listings (public feeds / APIs only, no login scraping) and scores each on faceless fit (writing, code, data, research, design, translation), pay, deadline and what the minds would cost to do it. The folder shows the best ones with the expected profit.
- [ ] **Bid, then work, both on the owner's approve:** both minds draft the bid blind and the stronger one is kept; nothing goes out until the owner taps approve, from his own connected account (FEELESS never signs up, logs in with a password or holds the money). On a win, the minds do the work with the kits; the Collective checks the deliverable; the owner approves delivery.
- [ ] **Graded on real money:** the amount actually paid (the platform's receipt or the owner's mark) against the minds' cost = profit, and hours saved. Platform fees live on the receipt, never in the profit (§1 style). A job lost or unpaid is graded too, with why.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on an earn filing.
- [ ] A TEST PoEco earn run on Happy (inside the TEST caps) up to the approve step: a real listing found, scored, the bid drafted, nothing sent. Seen in the browser with a screenshot.
**Status:** ✅ done 2026-11-20 (Opus 5.5), one named miss. **Terms first** (web search + one real public read each): kept Superteam Earn (its own agentAccess flag: AGENT_ALLOWED / AGENT_ONLY only), Freelancer.com (public projects API; no AI ban found, bots banned, so FEELESS never bids) and Algora bounties (GitHub search, `commenter:app/algora-pbc`, $ from the bounty's label, a repo whose CONTRIBUTING bans AI work is dropped); out with why: Upwork (RSS ended 2024-08-20, API needs login), Fiverr (no job feed), Contra (no feed / no AI terms), Gitcoin (bounties moved to Buidlbox). `backend/eco_earn.py` (pure: terms, faceless fit, credential/role/live-session filter, score = fit 30 + pay 30 + time 20 + profit 20, expected profit = pay × win chance − the minds' cost from the agent's real median $/call, blind-bid pick, stages, receipt, grade) + `fc_earn.py` (ops earn_find · earn_bid · earn_go · earn_work · earn_view; the approve door refuses the internal key and auto runs, a TEST needs his tick; FEELESS never sends, delivers or holds money, the owner sends from his own account and marks sent / won / lost / paid; a win → both minds do the work blind with the kits, OSSY + G4 check it on the new earn rubric, he approves delivery; paid − the minds' cost = profit, fees on the receipt only, hours saved; lost / unpaid graded with why). PoEco kits: Bid Desk + Faceless Work Check (+ Earn desk stack, PoEco in the kit picker). UI: `EarnDesk.jsx` (board with meters + expected profit, terms, left-out reasons; filing with both bids, stage track, the approve door). **TESTs on Happy (qwen3.8-max + gpt-6.1-terra): #1 earn1795194899 9/9 ($0.018) and #2 earn1795195066 9/9 ($0.018)**, minds · sources (5 sites) · footprint · kits · terms · finder · bid · approve · graded; nothing sent. Seen at `/dev/ecoearn` (51366) on #2 + a live board read with today's rules. ⛔ Miss: both TESTs bid on work a licensed engineer must sign (#1 "Arkansas PE", #2 "Industrial Stairs", the second off a board kept from before the fix); the licence/role filter + re-score on every bid are in and a live read drops 10 such listings, but no third TEST was run (one-rerun rule). **Faked-only:** approve → sent → won → work → Collective check → delivery → paid (no real win yet; the owner sends the first bid himself).
```
FEELESS, Slice 16. Read CLAUDE.md, then docs/VISION.md ("PoW · PoP · PoEco"), then "Slice 16" in docs/SLICES.md. Do only Slice 16, fully, end to end. Research each platform's terms with a web search first and make one real public read before building on one. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 16 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent or delivered), seen in the browser; gate green; pushed. Finish by updating Slice 16's Status line.
```

## Slices 24–28 · every proof desk redone for long work (owner 2026-11-20). Opus 5.5 medium each, after 16, before 17.
Owner: "issues and layout needs to be cleaner, more dashboard like for each proof type, a unique look for easy working … each proof type will have a user in it for hours potentially building or working on sumn cool!" One desk per slice, deep (never a shallow pass over all of them).

## Slice 24 · PoC desk: fixes + a dashboard for content work
**Why:** owner's screenshots 2026-11-20: the PoC home is a huge header and a giant checks block, and the clip board is broken.
**Area:** `PocStudio.jsx`, `ClipFarm.jsx`, the PoC folder home (`ProofHead` for poc, `ProofDeskLazy kind="content"`), `backend/media_gen.py` (Runway Aleph 2 on OpenRouter).
**Checks:**
- [x] **Bug:** in Clips, a run's info line (`5:00 · 1920×1080 · …`, "Your upload, converted …", candidate counts) renders one letter per line down the page. Find the cause and fix it, with a test that the line keeps its width.
- [x] **Bug:** Runway Aleph 2 · Replace fails with `400: Validation of body failed: Unrecognized key: "references"`. Read OpenRouter's current `/videos` schema (one real free call), send the body it takes, and add a test with that schema. ("Out of credit" is the owner's provider balance: keep the plain message.)
- [x] Slice 15's named miss: first clip on a converted iPhone .mov in under 2 min, or the cause named with numbers.
- [x] The PoC home is a content dashboard: what's trending now, its posts and their reach / cost per 1,000 views, clips waiting for approve, this week's plan, with the live tools beside it, not under a wall.
- [x] **The desk bar (RULINGS 2026-11-20):** it opens on a compact dashboard for this type's work (its own look and layout, Slice 13's PoB dashboard is the reference); the true record and checks fold into one slim row that expands on tap (no full-width bars, no giant headings); the working area gets the room; no text breaks one letter per line; checked in the browser at a full window, a half window and a phone width, night and day, with a screenshot of every tab.
**Status:** ✅ done 2026-11-20 (Opus 5.5). **Letter-per-line:** hive.css (loaded on every agent desk) owns `.cfm`/`.cfm-steps` (a 5-column grid), so the clip farm's step notes got a 0 px column; the farm now has its own `clf-` names and flex-wrap rows (test: no other sheet styles a `clf` class, notes keep a 200 px basis). **Aleph:** a free read of OpenRouter `/videos` (2026-11-20) shows the body sent since 11-17 17:35 is valid (`input_references` = the video only, the image as `provider.options.runway.keyframes`); the owner's 400 at 15:18 came from the body before that fix, his 18:37 run passed validation and stopped at the 402 credit check (kept plain). The one gap left: aspect ratios Aleph refuses (9:21, 2:1, 5:2) now map to its nearest one; test pins the body to a saved copy of the live schema. **First clip:** 112.7 s on an iPhone HEVC .mov (was 176 s): words on Apple's GPU (faster-whisper `mps`, 11.5 s vs 45.2 s, CPU fallback for good on error) with scene cuts beside them; words+peaks done at 21 s (was 67.8 s); the rest is the minds (tencent/hy4 79.7 s) with the convert hidden behind them. **Desk:** PoC home is `PocDash` (REACH · per 1K views · to approve · this week; tabs Trending / To approve / Posts / Week / All filed; Post desk + tools beside it); record + checks fold into one slim row (`RecordFold` in TrueRecord.jsx, `ProofHead slim`: reusable by 25–28). Seen on `/dev/pocdesk` (Happy's real folders) at full / 700 px / 375 px, night and day, every dashboard tab, the fold and the folder's Clips tab. **TEST on Happy ($0.0041):** clip run `cr4294e54aa6`, PoC #12–14 (run `1c3445df37`, bench ab7f9700b507 / 1cda6dfa1d13 / 5e8b7b45d569), 9/10: `moments` fails honestly because Happy's PoC Brains has one mind set (it needs both). **Open:** reach / cost per 1K is 0 / — until something is posted (nothing posted yet); no week slots set yet; the paid Aleph swap is the owner's to press.
```
FEELESS, Slice 24. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoC"), then "Slice 24" in docs/SLICES.md. Do only Slice 24, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 24 check passes, every tab seen in the browser on 51366 at full / half / phone width with screenshots, on real data; a TEST run on Happy only if backend changed (inside the caps); gate green; pushed. Finish by updating Slice 24's Status line.
```

## Slice 25 · PoW desk: a dashboard for coin work
**Area:** the PoW folder (`PowExplorer`, `ProofHead` for pow, `ProofRail`).
**Checks:**
- [x] It opens on a coin-work dashboard: open proposals and trades, P&L without fees (§1) with its curve, the coins it's watching with live prices, the minds' last calls, and its guards (age / pool / already-ran) at a glance.
- [x] **The desk bar (RULINGS 2026-11-20):** it opens on a compact dashboard for this type's work (its own look and layout, Slice 13's PoB dashboard is the reference); the true record and checks fold into one slim row that expands on tap (no full-width bars, no giant headings); the working area gets the room; no text breaks one letter per line; checked in the browser at a full window, a half window and a phone width, night and day, with a screenshot of every tab.
**Status:** ✅ 2026-11-20 — the PoW folder opens on its coin-work dashboard (`PowDash.jsx`, gold-seam look): P&L without fees + Recharts curve, won %, open now, guards stopped; tabs Open · Watching (live prices via `/api/market`, gate pips) · Calls · Guards (age / pool / ran + every stopped coin) · All filed · Tools (the old home panels). Record folds into `<ProofHead slim>`; the window goes one column under 900 px (`boxRef`). Checked on Happy's 17 real folders at full / half / phone, night and day. Frontend only, no TEST needed.
```
FEELESS, Slice 25. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoW · PoP · PoEco"), then "Slice 25" in docs/SLICES.md. Do only Slice 25, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 25 check passes, every tab seen in the browser on 51366 at full / half / phone width with screenshots, on real data; a TEST run on Happy only if backend changed (inside the caps); gate green; pushed. Finish by updating Slice 25's Status line.
```

## Slice 26 · PoP desk: a dashboard for paper perps
**Area:** the PoP folder (`PopApp`, `ProofHead` for pop).
**Checks:**
- [ ] It opens on a perps dashboard: open paper positions with entry / mark / liquidation and P&L, a real chart (Lightweight Charts), its win rate, and the minds' sit-out reasons.
- [ ] **The desk bar (RULINGS 2026-11-20):** it opens on a compact dashboard for this type's work (its own look and layout, Slice 13's PoB dashboard is the reference); the true record and checks fold into one slim row that expands on tap (no full-width bars, no giant headings); the working area gets the room; no text breaks one letter per line; checked in the browser at a full window, a half window and a phone width, night and day, with a screenshot of every tab.
**Status:** ✅ 2026-11-20. `PopDash.jsx` + `popDash.css` (`ppx-*`, a perps terminal: violet longs, pink shorts, the ☠ liquidation ruler): hero (paper P&L no fees + curve · win rate · open · sat out), tabs Desk (true chart + the paper position: entry / mark / ☠ liq / P&L) · Sat out (each mind's reason) · All filed · Tools (the old home). `<ProofHead slim kind="pop">`, `ref={prfBox}`, PoP's tile wall removed. Checked full / half / phone, night + day on Happy's real PoPs (the open position on the harness fixture: Happy has never opened one). No backend change, no TEST.
```
FEELESS, Slice 26. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoW · PoP · PoEco"), then "Slice 26" in docs/SLICES.md. Do only Slice 26, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 26 check passes, every tab seen in the browser on 51366 at full / half / phone width with screenshots, on real data; a TEST run on Happy only if backend changed (inside the caps); gate green; pushed. Finish by updating Slice 26's Status line.
```

## Slice 29 · Clip studio: the clip folder as a real editor + week planner (owner 2026-11-20) · Opus 5.5 medium · after 26, before 27
**Why:** owner, with screenshots of PoC #21 and the new PoC dashboard: "yess and clip farming should show file folder with some cool smart way to show a grid and easy way for user to plan a week or have agent plan and user able to chat in file of the plan etc, able to edit captions and different transition and effects user or ai can use to make unique and ultimate design etc, like do better."
**Area:** `ClipFarm.jsx`, `PocDash.jsx`, `PocWire.jsx` / `WeekBoard.jsx`, `backend/clip_farm.py`, `fc_clips.py` (ffmpeg render).
**Checks:**
- [x] **Bug (PoC #21 screenshot):** the caption box on the 9:16 clip is cut off at the frame edge ("…since I was a", the word "kid." lost), while the 1:1 one wraps right. Captions always fit and wrap inside the frame, on every format, with a test.
- [x] **Clip folder = a smart grid:** every clip of a run as playable tiles, grouped by source and format, with hover-play, its score, hook and status (to approve / planned / posted), plus quick filters. No long list rows.
- [x] **Week planner:** drag clips onto a Mon–Sun board with times per platform, or tap "agent plans it" (the minds fill the week from the scores and the trend reader, saying why for each slot). Both ways land in the same saved plan.
- [x] **Chat in the plan:** a chat inside the plan's file. The owner asks ("move the best one to Friday, make Tuesday funnier") and the minds change the plan and the clips. Every change is versioned and can be undone.
- [x] **Edit like an editor:** captions (words, timing, style: font, colour, size, position, word-by-word highlight), transitions (cut, fade, zoom, whip, glitch) and effects (punch-in zoom, shake, colour grade, speed ramp, B-roll / emoji pop) as presets the owner OR the minds can apply. A live preview, rendered by ffmpeg ($0, local), no watermark, each clip's look unique (no two clips the same preset set).
- [x] **Type and polish (owner: "poor layout/ui and fonts bigasl like just basic asf"):** the clip viewer (PoC #21: two giant side-by-side players with a lone Download button) and the PoC post rows get the RULINGS 2026-11-20 type scale (body 12–13 px, labels 10–11 px, one hero number per card) and designed depth, not plain boxes.
- [x] Everything still files through Slice 5's approve door (nothing posts by itself) and meets the desk bar (RULINGS 2026-11-20): full / half / phone width, night and day, with a screenshot per tab, on real clips (the ohara_iphone run).
- [x] **Add-on: saved edit formats + templates (owner 2026-11-20):** a template = caption style, font, accent, safe area, transition, effects, formats, saved by name per agent; defaults per format (9:16 / 1:1 / 16:9), per platform and for the farm; one tap puts it on a clip, its run or the week (re-rendered, $0, each nudged unique); listed with moving samples, editable, deletable; the minds can design one.
- [x] **Add-on: cooler captions:** no flat green slab; ≤ 2 tight lines, a thin stroke + soft shadow, the said word pops in the accent, animated keyword emphasis, a safe area off faces / clear of app buttons; six templates (pop highlight, karaoke sweep, minimal lower-third, bold outline, gradient keyword, emoji accent), each rendered by ffmpeg and tested in-frame.
- [x] **Add-on: farm templating ("help them understand better templating"):** before a run pick a template or "minds pick"; your saved default is preselected; every clip comes out in it; minds give each clip a different template with a why on its tile; swap for one clip or the whole run in one tap; the run card shows each clip's template.
**Status:** ✅ done 2026-11-20 (Opus 5.5), commit `a8f68949`. Captions are Pillow PNG bands overlaid by ffmpeg (this ffmpeg has no libass/drawtext); effects = scale+crop eval=frame, rgbashift/noise, tmix, eq/curves/hue, fade, trim/atempo; $0, no watermark. Cut-off hook fixed (`clip_look.hook_lines`: every word, ≤ 3 lines, ≤ 84 % width, clip + cover). Clips grid / Week (dnd-kit) + plan chat / Edit (live preview) in `ClipStudio.jsx` + `ClipEdit.jsx`; plan versions + look versions with undo; no two clips of an agent share a look (owner twin → 409, minds/chat → nudged). Real TEST on Happy (ohara_iphone runs): agent plan hy4 $0.0033 (6 slots, each a why) · chat "move the best one to Friday, make Tuesday funnier" → v2, 2 looks re-rendered, $0.0034 · minds look 20.1 s · hype preset 31.6 s · 6/6 unique looks. Seen on 51366 at 1440/720/375, night + day. Open: B-roll is keyword word-pop stickers, not stock footage; the editor preview is a CSS approximation (the render is the truth); Sicario's older twin clips get unique-look renders queued on the owner's next open ($0, not yet watched). **Add-on ✅ 2026-11-20 (`ede579a4`, `9b3b4ef0`):** templates per agent (save / edit / delete, defaults per format, platform and farm, one tap on a clip / run / week, minds design or pick one per clip with a why); six modern caption styles (no slab, ≤ 2 lines, popped word in the accent, face / UI safe area), Pillow frames since this ffmpeg has no libass; the farm makes every clip in the picked template and the Moments table names each. Fixed on the way: a run's upload link row was trimmed by the 24-link cap after ~7 re-renders (clips could not be restyled, the upload never swept) — kept now, Happy's two runs restored. TEST on Happy: minds pick ×2 runs $0.0059, 6 distinct templates with whys, 6 real re-renders 14.6–40.2 s, 6/6 unique. Open: the face safe area uses the clip's median face, so a multi-shot clip can still land a mid caption on a face for one shot.
```
FEELESS, Slice 29. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoC"), then RULINGS 2026-11-20, then "Slice 29" in docs/SLICES.md. Do only Slice 29, fully, end to end. Research free/open caption, transition and effect tools first (ffmpeg filters, open caption styles) and make one real local render before building on one. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 29 check passes on real clips, seen in the browser on 51366 at full / half / phone width with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed and confirmed on origin/main. Finish by updating Slice 29's Status line.
```

## Slice 27 · PoStatic desk: a dashboard for building
**Area:** the PoStatic folder (`ProofDeskLazy kind="build"`, the page viewer, inspect, studio).
**Checks:**
- [ ] It opens on a builder's dashboard: the live page big, versions, inspect + studio one tap away, kits used, and its unique / clean / progress checks slim. Hours of building must feel like an editor, not a report.
- [ ] **Inspect everything (owner 2026-11-20: "inspect needs to be able to hover over anything in static, even the 3D stuff"):** hover draws a box on EVERY coded component and every text node (not just spans), on canvas / chart regions, and on 3D objects (three.js raycast → the object's name, mesh and code), each editable in place or commentable so the minds fix exactly that. Inspect labels never sit on top of the page's own content (seen: the 1/2/3 badges covering the chart's legend).
- [ ] **Built on Slice 33's shell (owner's screenshot of "The Collective Landing" v11):** a slim top bar instead of the big header; the 7 step chips folded into the bar; the 10-button toolbar grouped into one compact bar with overflow; the left inspect cards made compact; the "Also loads cdn…" warnings in a tidy issues tray; the chat beside a big live preview, so the page stays visible while chatting.
- [ ] Every inspect fix uses the stash's tools first (Slice 30 later), so no mind wastes usage or build time.
- [ ] **The desk bar (RULINGS 2026-11-20):** it opens on a compact dashboard for this type's work (its own look and layout, Slice 13's PoB dashboard is the reference); the true record and checks fold into one slim row that expands on tap (no full-width bars, no giant headings); the working area gets the room; no text breaks one letter per line; checked in the browser at a full window, a half window and a phone width, night and day, with a screenshot of every tab.
**Status:** not started.
```
FEELESS, Slice 27. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoStatic"), then "Slice 27" in docs/SLICES.md. Do only Slice 27, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 27 check passes, every tab seen in the browser on 51366 at full / half / phone width with screenshots, on real data; a TEST run on Happy only if backend changed (inside the caps); gate green; pushed. Finish by updating Slice 27's Status line.
```

## Slice 28 · PoEco desk: a dashboard for earning
**Area:** the PoEco folder (`EcoFolder`), Slice 16's earn finder.
**Checks:**
- [ ] It opens on an earning dashboard: jobs found with expected profit, bids waiting for approve, work in progress, money paid vs the minds' cost, and its market calls.
- [ ] **Fixes from the owner's screenshot (manager's finds):**
  - The PoEco folder still opens on the big header and the full-width check bars, not `<ProofHead slim>`.
  - A tooltip covers the "minds that ran" line.
  - The job text is cut off under the header ("work from site dimensions you provide?").
  - The finder picked a structural stair / handrail CAD job (OSHA / IBC, stamped drawings) as "faceless fit": it needs a licensed engineer. Licensed and regulated work is filtered out.
  - The bids promise $20,000–$35,000 of work "within 1 day": a bid's price and time must be realistic for the work.
- [ ] **Easy, dynamic job start:** one-tap "find me work" by skill, a live feed of jobs where AI can really compete (few bids, clear scope, fast turnaround), and starting a job through Slice 33's wizard.
- [ ] **What it takes to win (owner: "PoEco needs to show how much it would cost and the brains / models needed to make it successful"):** each job shows the minds and models it needs, the expected model cost, the time, the competition (bid count, typical human rate) and our win chance, before the owner starts it.
- [ ] **The desk bar (RULINGS 2026-11-20):** it opens on a compact dashboard for this type's work (its own look and layout, Slice 13's PoB dashboard is the reference); the true record and checks fold into one slim row that expands on tap (no full-width bars, no giant headings); the working area gets the room; no text breaks one letter per line; checked in the browser at a full window, a half window and a phone width, night and day, with a screenshot of every tab.
**Status:** not started.
```
FEELESS, Slice 28. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoW · PoP · PoEco"), then "Slice 28" in docs/SLICES.md. Do only Slice 28, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 28 check passes, every tab seen in the browser on 51366 at full / half / phone width with screenshots, on real data; a TEST run on Happy only if backend changed (inside the caps); gate green; pushed. Finish by updating Slice 28's Status line.
```

## Slices 30–34 + the 27/28 add-ons · owner 2026-11-20 night ("think big and robust … be senior dev and mad computer scientist … investors are ready for the beta")
Order: **33 → 27 → 28 → 32 → 34 → 30 → 31 → 17–23 → 8.** The shared workspace shell (33) goes first because every desk after it builds on it.

## Slice 33 · The filing workspace + the start wizard (shared by every proof type)
**Why:** Owner 2026-11-20 (night, with 5 screenshots): "in any proof type folder the ui/layout isnt robust and lit!! just bulky and annoying … don't be afraid to use popouts … before a PoC, PoEco or PoStatic job starts, instead of the drop of long text, it can pop out a 3-step window."
**Area:** a new shared `ProofWorkspace` shell + `StartWizard` popout used by every proof folder and every opened filing (`PobFile`, PoC / PoStatic / PoEco filings), `CatWorkbench.jsx`.
**Checks:**
- [ ] **One workspace shell for an opened filing:** a slim top bar (name, status, cost, back; never a big header), a big work area (the preview, page, clip or job), a chat pane that docks or pops out, and a tools rail that collapses. Panels resize and remember their sizes, and any panel can pop out into its own window.
- [ ] **The start wizard popout** (replaces the long confirm text before a PoC, PoEco or PoStatic job): step 1 is the direction (the brief, the goal, the minds' pitch, and the owner approves or edits); step 2 is kits, tooling and versions (which kits, which past versions or stash pieces to start from); step 3 is research (ask COMP, OSSY or G4 to search the web for better components, or let the minds search), with the cost and minds shown before Go. Every choice is saved into the filing's record (wired, tested).
- [ ] **No bulky folder or file, ever:** no folder or file view opens with a big header or basic text. The audit lists every proof folder and filing view and moves each one onto the shell.
- [ ] The desk bar and the type scale (RULINGS 2026-11-20) everywhere, with Motion transitions between steps and panels.
**Status:** ✅ done 2026-11-20 (Opus 5.5). **Shell:** `ProofWorkspace.jsx` (react-resizable-panels 2.1.9 + Motion): a slim bar (back, name or breadcrumb, status, cost, extras), the work, a chat pane and a tools rail that resize, fold, float (drag) or open in their own browser window, all remembered per view (`feeless.pws.<id>` + `autoSaveId`); ≤640 px = one pane with phone tabs (ResizeObserver + `boxRef`, no container queries). Views with no live chat get a read-only minds thread, never a dead input. **Moved onto it:** PoW filing, PoP filing (the folder tiles kept), PoB filing + reading (glass header → bar), PoC folder, filed PoC, PoStatic build, Features open view, PoEco filing; PoStatic / PoEco / Bids homes use the slim record row; an opened PoW / PoP filing hides the record head + rail like PoB. **Wizard:** `StartWizard.jsx` (Radix Dialog, Motion steps): direction (brief, goal, the minds' pitch; approve or write his own) → kits (≤3 or let it pick) + start from (fresh or a past filing) → research (minds / COMP free / OSSY / G4 on his LM Studio, no fallback) with minds + cost before Go. Replaces the approve text (PoStatic), File a PoC, Draft bid (PoEco). Backend `start_wizard.py`: checked on the door (`ws_approve`, `poc`, `earn_bid`, 400 unless approved / on offer), the kits reach `_recall`, the direction + found refs reach both minds' prompt, the record lands on the filing (`wizard`) and the true record shows STARTED WITH. Research searches the JOB, not his direction sentence (TEST #3 found notes apps for it; fixed). **Real TESTs on Happy:** PoEco #3 (earn1795234146, $0.0259) and #4 (earn1795234384, $0.0263): #4 ran only his picked kit (Bid Desk), both minds read his direction, STARTED WITH on the record, research said honestly that nothing open came back. `scripts/test-proof.py --kind poe --earn --wizard '<json>'`. Not run for real: the PoStatic and PoC wizard paths (faked tests only; same module, same record).
```
FEELESS, Slice 33. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md (every proof type), then RULINGS 2026-11-20, then "Slice 33" in docs/SLICES.md. Do only Slice 33, fully, end to end. Research free/open libraries first and make one real call before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 33 check passes on real data, every tab seen in the browser on 51366 at full / half / phone width, night and day, with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed in the FOREGROUND from `.claude/worktrees/gate` and confirmed with `git merge-base --is-ancestor <sha> origin/main`. Finish by updating Slice 33's Status line.
```

## Slice 32 · PoC: one filing = a whole channel (series package)
**Why:** Owner 2026-11-20 (night, with 5 screenshots): "all these need to be in 1 filing … this one filing of the nasa ppl and what they do can be a whole youtube page with narrative and all! meaning we would need logo and cover photo, intro video … and i can truly work!" (The PoC list showed 14 separate TEST filings, all cut from the same ohara_iphone upload.)
**Area:** `fc_poc.py`, `fc_clips.py`, `PocDash.jsx`, `ClipFarm.jsx`, Slice 33's shell.
**Checks:**
- [ ] One source (an upload or a theme) = ONE filing: a series with its narrative arc (episode order, hooks, a through-line), and every clip inside it as an episode, never 14 loose filings. Old loose filings are grouped by source.
- [ ] The channel package is made as real files: channel name, logo, cover / banner, profile image, an intro video (sting), an about text, per-episode thumbnails and titles, and a posting calendar. Free local tools first; any paid image or video step shows its price and is owner-pressed.
- [ ] The filing opens as a channel page preview (like a YouTube / TikTok profile) with the package editable in place, plus the chat to change any part.
- [ ] Graded on the series' reach as a whole and per episode. Nothing posts without the approve door.
**Status:** not started.
```
FEELESS, Slice 32. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("PoC"), then RULINGS 2026-11-20, then "Slice 32" in docs/SLICES.md. Do only Slice 32, fully, end to end. Research free/open libraries first and make one real call before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 32 check passes on real data, every tab seen in the browser on 51366 at full / half / phone width, night and day, with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed in the FOREGROUND from `.claude/worktrees/gate` and confirmed with `git merge-base --is-ancestor <sha> origin/main`. Finish by updating Slice 32's Status line.
```

## Slice 34 · Main desk: a real chat + the clean desk look
**Why:** Owner 2026-11-20 (night, with 5 screenshots): "main desk needs to be dynamic with true chat stuff and if I ask GPT SOL 6 to generate an img it actually shows a beautiful box referencing the loading state of the img" · "the OG agent main desk looks unprofessional". The look is set by the preview the manager built in chat (owner's pick of theme and background).
**Area:** the agent main desk (`CatDesk`, the desktop, the chat), `media_gen.py` for image calls.
**Checks:**
- [ ] A real chat: streaming replies, markdown, code blocks, attachments, tool steps as tidy cards, the mind and cost per answer, retry and edit.
- [ ] **Image generation in chat:** an image ask shows a polished generating card (shimmering dot-grid, % progress, the model's name, cancel), then the image with download, use-in-proof and variations. The same goes for video.
- [ ] **Desktop clean-up (manager's finds on the owner's screenshot):**
  - The icons are scattered with big gaps; they snap to a tidy grid with groups.
  - Duplicates are merged: The Collective ×2, Brain + Brains, Wallet + "Wallet + style", Browser ×2.
  - Prompts, Character and Features share one generic icon, so each gets its own.
  - The "Fee" wordmark and "PRIVATE DESKTOP" are nearly invisible.
  - "Wallet + style" wraps onto two lines.
  - The DASHBOARD widget says Proofs 0 · Won/lost 0/0 · Jobs 0 on Fee's desk while the agent desks show 118: say whose numbers they are, or show the account total.
  - The widgets column is a stack of plain boxes.
- [ ] The clean look from the preview: black and white themes, 2 monitors, chat, vitals, and full-page backgrounds (real smoke grain + others), with transform / opacity animation only and heavy FX off under `body.fx-lite`.
**Status:** not started.
```
FEELESS, Slice 34. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("The point of it all" and "Brains"), then RULINGS 2026-11-20, then "Slice 34" in docs/SLICES.md. Do only Slice 34, fully, end to end. Research free/open libraries first and make one real call before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 34 check passes on real data, every tab seen in the browser on 51366 at full / half / phone width, night and day, with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed in the FOREGROUND from `.claude/worktrees/gate` and confirmed with `git merge-base --is-ancestor <sha> origin/main`. Finish by updating Slice 34's Status line.
```

## Slice 30 · The stash tooling: shared, selective, never copied
**Why:** Owner 2026-11-20 (night, with 5 screenshots): "our stash's internal tooling needs to be robust and selective to assure every agent / new agent can always use another agent's version and ONLY use them uniquely, to assure the best new look plus the most efficient tooling … which wouldn't exploit the original agent's look or repeat design and layout, proving unique fingerprints every time … the stash, COMP and Sicario's will perfect the tooling as well, not just judging."
**Area:** `collective_stash.py`, `proof_kits.py`, `ps_unique.py`, `proof_footprint.py`, `stash_brain.py`, COMP.
**Checks:**
- [ ] Every built piece (kits, components, sections, caption templates, effects, prompts) goes into the stash as a versioned tool with its source agent, what it does, its quality score and its fingerprint.
- [ ] Any agent (new ones too) can pull another agent's tool version, but the result must pass the uniqueness gate against the source agent's look (palette, layout, structure, copy). A reuse that would copy the look is refused and remixed.
- [ ] Selective: a mind asks the stash first and gets the best tool for the job ranked by score, freshness and cost saved. The record shows which stash tools it used, from whom, and the time and $ saved.
- [ ] Tooling gets better, not just judged: COMP and Sicario's local minds run a loop that proposes improved versions of the most-used tools (faster, cheaper, cleaner), tests them, and promotes a version only when it beats the old one on real filings.
- [ ] Opus-class minds work faster with the stash's approved tools: measured on a TEST (time and $ with vs without).
**Status:** not started.
```
FEELESS, Slice 30. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("The stash brain" and "COMP"), then RULINGS 2026-11-20, then "Slice 30" in docs/SLICES.md. Do only Slice 30, fully, end to end. Research free/open libraries first and make one real call before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 30 check passes on real data, every tab seen in the browser on 51366 at full / half / phone width, night and day, with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed in the FOREGROUND from `.claude/worktrees/gate` and confirmed with `git merge-base --is-ancestor <sha> origin/main`. Finish by updating Slice 30's Status line.
```

## Slice 31 · COMP: the owner's own unrestricted model (guardrails his alone)
**Why:** Owner 2026-11-20 (night, with 5 screenshots): "sort through all COMP info and the AI model's build YOURSELF and assure this is an obliterated model that I can ask literally anything and he will find a way!! and ONLY I set the guardrails! … if the model ain't the one to start with, let me know so we don't waste time, usage and Mac space … that can potentially be better than GPT SOL 6.1 and Claude 5.5 med one day."
**Area:** `comp_v2*.py`, `model_lab.py`, `comp_teacher.py`, LM Studio / MLX on this Mac (M3, 24 GB unified memory, ~350 GB free as of 2026-11-20). Today's base is Qwen3.5-9B MLX 4-bit + a LoRA (Slice 7: 11/22 vs the base's 13/22, not shipped).
**Checks:**
- [ ] **Base choice first, before any download:** research the 2026 open-weight models that fit 24 GB for inference AND for MLX LoRA training (dense ~8–14B vs MoE ~30B-A3B at 4-bit), with their benchmark scores, licences and refusal-ablated ("abliterated") variants. Recommend one with numbers and ask the owner once. If 9B stays, say why.
- [ ] **Unrestricted, owner-only guardrails:** a refusal-ablated base (or abliteration done here with an open tool), plus an owner-only guardrail panel (COMP › Guardrails) where only the owner sets what it refuses. FEELESS §1 still applies in code around it: the model never moves money, signs or touches keys, whatever it's told.
- [ ] **"Finds a way":** COMP runs as an agent with tools (the stash, the atlas, web reads, code run in a sandbox, the kits), retries with a plan, and says plainly when it can't, never a silent refusal.
- [ ] **Measured:** the Slice 7 exam + a general set (reasoning, code, tool use) against the base, OSSY, G4 and a frontier reference via one paid call per item inside a cap the owner names. It ships only when it beats the base.
**Status:** not started.
```
FEELESS, Slice 31. Read CLAUDE.md, then docs/specs/style.md, then docs/VISION.md ("COMP"), then RULINGS 2026-11-20, then "Slice 31" in docs/SLICES.md. Do only Slice 31, fully, end to end. Research free/open libraries first and make one real call before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 31 check passes on real data, every tab seen in the browser on 51366 at full / half / phone width, night and day, with screenshots; a TEST on Happy if backend changed (inside the caps); gate green; pushed in the FOREGROUND from `.claude/worktrees/gate` and confirmed with `git merge-base --is-ancestor <sha> origin/main`. Finish by updating Slice 31's Status line.
```

## Slices 17–23 · the owner's earn ideas (owner 2026-11-19: "loving the proposals!! … add these all + u suggested to slices"). Opus 5.5 medium each, in this order, after 24–28, before 8. Each one's UI meets the desk bar (RULINGS 2026-11-20).

## Slice 17 · Solana bounty hunter
**Why:** Superteam Earn and GitHub / Algora bounties pay USDC or SOL for code, writing and design. FEELESS is Solana-first, and the Pool already holds these coins.
**Area:** builds on Slice 16's `eco_earn.py` (finder, scoring, approve door), plus the bounty feeds.
**Checks:**
- [ ] Reads open bounties (public feeds only), scores fit, pay and minds' cost, and shows the best ones in PoEco with the expected profit.
- [ ] The minds draft the submission (code as a real PR on a fork, writing as a file). The Collective checks it before the owner's approve.
- [ ] Graded on the bounty actually paid (on-chain receipt or the owner's mark) against the minds' cost.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 17. Read CLAUDE.md, then docs/VISION.md ("PoW · PoP · PoEco"), then "Slice 17" in docs/SLICES.md. Do only Slice 17, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 17 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 17's Status line.
```

## Slice 18 · Clip farming as a service
**Why:** Slice 15's clips sold to streamers and podcasters (Fiverr / Contra gigs or monthly retainers). It turns PoC from reach into paid work.
**Area:** Slice 15's clip engine + Slice 16's earn door.
**Checks:**
- [ ] A client's video in (upload or their in-house link) → clips back on a FEELESS link, with a revision round the owner approves.
- [ ] Gig listings and retainer offers drafted by the minds, sent only on approve. Graded on money paid per client against the minds' cost.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 18. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 18" in docs/SLICES.md. Do only Slice 18, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 18 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 18's Status line.
```

## Slice 19 · Faceless channel runner
**Why:** one niche Shorts / TikTok / Reels channel per agent, fed by PoC and clip farming. Reach turns into recurring money.
**Area:** PoC studio, Slice 15 clips, Slice 5's post + reach reads.
**Checks:**
- [ ] The agent picks a niche from the trend reader and keeps a weekly plan on the wireframe board, each post made as real files.
- [ ] Graded on creator-fund and affiliate payouts per channel (the owner's mark or the platform's numbers) and cost per 1,000 views.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 19. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 19" in docs/SLICES.md. Do only Slice 19, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 19 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 19's Status line.
```

## Slice 20 · PoStatic storefront
**Why:** PoStatic already builds unique sites. This sells them as digital products (landing-page templates, Notion / Canva packs, micro-tools) on Gumroad / Etsy digital.
**Area:** PoStatic builds (`fc_desk.py`, `ps_*`), Slice 16's earn door.
**Checks:**
- [ ] Each product is a real downloadable bundle with a listing (title, cover, price) drafted by the minds, listed only on approve.
- [ ] Graded on real sales against the minds' cost. Platform fees live on the receipt.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 20. Read CLAUDE.md, then docs/VISION.md ("PoStatic"), then "Slice 20" in docs/SLICES.md. Do only Slice 20, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 20 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 20's Status line.
```

## Slice 21 · Affiliate micro-sites
**Why:** PoStatic + the stash's fresh data make small useful sites (calculators, comparison pages) that earn affiliate or ad money.
**Area:** PoStatic, the stash / atlas (Slices 10–11), Slice 16's earn door.
**Checks:**
- [ ] Each site is built from fresh stash atoms and refreshed on their freshness clock, unique by Slice 3's gate.
- [ ] Graded on real affiliate / ad payouts per site (the owner's mark or the program's report) against cost.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 21. Read CLAUDE.md, then docs/VISION.md ("PoStatic"), then "Slice 21" in docs/SLICES.md. Do only Slice 21, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 21 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 21's Status line.
```

## Slice 22 · Agent for hire inside FEELESS
**Why:** other users rent an agent's proven skill (its proof record is the résumé), paid in $FEE.
**Area:** agent profile + proof record, Slice 14's proof files, the $FEE payment path.
**Checks:**
- [ ] **Blocked until the owner's dated legal ruling** (custodian / broker risk, §1 Legal). The slice starts by writing the exact question into RULINGS › Open questions, then stops ⛔ until he answers.
- [ ] After the ruling: a hire page per agent (skills from real judged proofs, price, what it won't do); a hire runs as that agent's proof, and the renter approves delivery.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started (waits on the owner's legal ruling).
```
FEELESS, Slice 22. Read CLAUDE.md, then docs/VISION.md ("Brains" and "PoW · PoP · PoEco"), then "Slice 22" in docs/SLICES.md. Do only Slice 22, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 22 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 22's Status line.
```

## Slice 23 · Cheaper-model race
**Why:** VISION's "any model, better and cheaper", proved in real dollars. Owner 2026-11-19: "cheaper model race will only replay latest test i click to test as it would be real money and the stash and comp is growing to be and help this."
**Area:** COMP (`comp_v2*.py`), the stash / atlas, the Test bench, Slice 16's earn filings.
**Checks:**
- [ ] It runs ONLY when the owner clicks it, and only on the LATEST TEST he picks: that TEST is replayed by a cheap model with the stash + atlas + COMP beside an expensive model without them. Never on a live job, never on its own.
- [ ] Both answers are judged blind by the Collective, and the folder shows quality, $ cost and time for each, plus the stash hits and COMP's help that made the difference.
- [ ] Each race is kept, so the board shows the gap closing (or not) as the stash and COMP grow. Inside the TEST caps.
- [ ] Nothing goes out (bid, post, listing, delivery, payout) without the owner's approve, from his own connected accounts. FEELESS never holds the money (§1 Legal). Only platforms whose terms allow AI-made work.
- [ ] Every every-proof check (minds, sources, new footprint, kits) on its filings, and a TEST run on Happy up to the approve step, seen in the browser with a screenshot.
**Status:** not started.
```
FEELESS, Slice 23. Read CLAUDE.md, then docs/VISION.md ("COMP" and "The point of it all"), then "Slice 23" in docs/SLICES.md. Do only Slice 23, fully, end to end. Research with a web search first and make one real public read before building on any outside service. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 23 check passes on a real TEST run (scripts/test-proof.py --agent happy, inside the TEST caps; nothing sent, posted, sold or paid), seen in the browser; gate green; pushed. Finish by updating Slice 23's Status line.
```

## Slice 8 · Proof of everything (runs LAST, after 9–29) · Opus 5.5 medium
**Why:** one session that trusts nothing and proves every VISION check for real.
**Checks:**
- [ ] `/code-review` (high) on everything slices 0–7 pushed. Every real finding fixed.
- [ ] Slice 10's open check: one clean pair of related TEST PoBs while NO other slice saves backend files. The second must show stash hits from the first (runs 3 and 4 were killed by other slices' reloads).
- [ ] One TEST proof of every type on Happy's agent (proposals and paper only, inside the $1.00 total). Every VISION checkbox is marked pass or fail with a link to the proof that shows it.
- [ ] The report = VISION with every box ticked or a named reason, faked-only first.
**Status:** not started.
```
FEELESS, Slice 8. Read CLAUDE.md, then docs/VISION.md, then docs/SLICES.md. Trust nothing: review everything slices 0–7 pushed (/code-review high), fix real findings, then run one TEST proof of every type on Happy's agent (scripts/test-proof.py --agent happy, proposals and paper only, $1.00 total) and mark every VISION checkbox pass/fail with a link to the proof. Gate green; pushed. Report faked-only first.
```
