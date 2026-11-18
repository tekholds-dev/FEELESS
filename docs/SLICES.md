# SLICES — the fix plan (owner 2026-11-18). One slice = one session = one model. Paste the prompt, pick the model, let it run.

**The bar for every slice:** `docs/VISION.md`. A slice is done only when its checks pass on a **real free run on Sicario's agent**
(`local/ossy` + `local/g4`, $0, no money) filed into that proof type's own folder marked **TEST**, the gate is green and it's pushed.

## The 3 models (pick once per session in the app's model picker; never switch mid-session)
| Model | Effort | Used for | Why |
|---|---|---|---|
| **Claude Fable 5.2** | high (xhigh for slice 8) | Slices 4, 7, 8: the hardest builds (video swap, COMP) and the final review | Strongest at long agentic coding, but twice the price of Opus, so only 3 sessions |
| **Claude Opus 5.5** | **high**, never medium | Slices 0, 2, 3, 5, 6: the backend builds | The workhorse. High effort for deep backend work |
| **Claude Sonnet 5.5** | high | Slice 1: the wiring audit, Brains proof, UI checks | Cheaper; enough for audit + UI + small wiring |

## How to run a slice
1. Claude desktop → **New session** in this project (main folder) → set the model + effort from the table → paste that slice's prompt.
2. Let it run. If it runs out of room, it continues in the same session by itself. **Don't start a new session mid-slice.**
3. It ends with a report. **Faked-only / not wired** comes first, then which VISION checks pass for real. It also updates that slice's **Status** line below.
4. Not finished? Start the next session **with the same model**, using the same prompt. It reads the Status line and carries on.
5. **At most 2 slices at once**, only the pairs marked "can run beside" (they touch different files). Never 2 backend pushes at the same moment: a push restarts every service.

**Order:** 0 → (1 beside 2) → 3 → (4 beside 5) → 6 → 7 → 8.  Slice 0 is first because every later slice needs TEST filings and a true record.

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

## Slice 3 · PoStatic: full toolkit, unique, clean · Opus 5.5 high
**Why:** "so many integrative tools missing from static." The Collective exists to hand every mind the kits.
**Area:** `backend/proof_kits.py`, `collective_kits.py`, `method_kits.py`, `kit_fresh.py`, `ps_hidden.py`, `proof_footprint.py`, the build path in `fc_desk.py`.
**Checks:**
- [ ] The build minds can use every approved kit (three, Motion, Recharts, Lightweight Charts, shadcn/ui, DexScreener + our indexes, wallet connect, forms, maps). Each kit used is listed in the folder with what it did.
- [ ] Uniqueness gate: a near-copy of any past build is refused before filing. Every build gets a new brief, a new centrepiece and a new layout.
- [ ] Hidden code check adds overlapping blocks, broken links, placeholder text and phone load.
- [ ] No back pedals: a new version can't lose a part the last version had working.
- [ ] 3 TEST PoStatics on Sicario, all different, linked in the report.
**Status:** not started.
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
**Status:** not started.
```
FEELESS, Slice 4. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 4" in docs/SLICES.md. Do only Slice 4, fully, end to end. Research today's engines with a web search first and make one real call before building on one. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 4 check passes; tests fake the paid engine; the owner presses the first paid run; gate green; pushed. Finish by updating Slice 4's Status line.
```

## Slice 5 · PoC: the content engine, graded on reach · Opus 5.5 high · can run beside Slice 4
**Why:** PoC is 12 text week-plans with 0 passes. It must make real content and prove reach.
**Area:** `backend/poc_play.py`, `poc_watch.py`, `proof_tools.py` (`viral()`), the PoC folder (`PocWire.jsx`, `WeekBoard.jsx`).
**Checks:**
- [ ] Trend first: the record shows the trend it rode.
- [ ] Makes the real files (image, short video, post, thread) in story, feed and wide formats.
- [ ] Owner approves, then it posts on his own connected accounts. Nothing posts by itself.
- [ ] Reads views and engagement back at 24 h and 7 d. The grade is real reach against the goal set at filing, plus cost per 1,000 views.
- [ ] A TEST PoC on Sicario up to the approve step, linked in the report.
**Status:** not started.
```
FEELESS, Slice 5. Read CLAUDE.md, then docs/VISION.md ("PoC"), then "Slice 5" in docs/SLICES.md. Do only Slice 5, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 5 check passes on a real free TEST run on Sicario's agent (no money, nothing posted without the owner's approve); gate green; pushed. Finish by updating Slice 5's Status line.
```

## Slice 6 · PoW, PoP, PoEco brought up to the bar · Opus 5.5 high
**Why:** PoP (5) and PoEco (1) had never been judged as of 2026-11-18, and every type must meet the every-proof checks.
**Area:** `backend/proof_review.py` (`next_due`), `fc_cats.py` (`_review_one`), `fc_pow.py`, the PoP and PoEco filers.
**Checks:**
- [ ] Find why PoP and PoEco never reach the judges, and fix it. All 6 types are now judged.
- [ ] PoW, PoP and PoEco pass every every-proof check in VISION. P&L stays without fees (§1).
- [ ] A TEST of each of the 3 on Sicario, judged, linked in the report.
**Status:** not started.
```
FEELESS, Slice 6. Read CLAUDE.md, then docs/VISION.md, then "Slice 6" in docs/SLICES.md. Do only Slice 6, fully, end to end. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 6 check passes on real free TEST runs on Sicario's agent (no money); gate green; pushed. Finish by updating Slice 6's Status line.
```

## Slice 7 · COMP on real proofs only · Fable 5.2 high
**Why:** "I'm not confident in COMP." It has to learn from real judged proofs and beat the base model on an honest exam.
**Area:** `backend/comp_v2.py`, `comp_v2_exam.py`, `comp_teacher.py`, `model_lab.py`, `docs/specs/comp-next.md`.
**Checks:**
- [ ] COMP's training set is only real, judged proofs of each type, each with its pass/fail evidence. Anything else is dropped and counted.
- [ ] An exam on held-out real proofs: COMP vs the base model vs OSSY, G4 and ZED, all on the owner's LM Studio. The scores are in the report.
- [ ] A COMP that doesn't beat the base model isn't shipped, and the report says why.
**Status:** not started.
```
FEELESS, Slice 7. Read CLAUDE.md, then docs/VISION.md ("COMP"), then "Slice 7" in docs/SLICES.md. Do only Slice 7, fully. LM Studio runs from the owner's Terminal: give him the one command when needed. Ask any vision questions in ONE batch first, then don't stop. Done = every Slice 7 check passes with real exam numbers; gate green; pushed. Finish by updating Slice 7's Status line.
```

## Slice 8 · Proof of everything · Fable 5.2 xhigh
**Why:** one session that trusts nothing and proves every VISION check for real.
**Checks:**
- [ ] `/code-review` (high) on everything slices 0–7 pushed. Every real finding fixed.
- [ ] One TEST proof of every type on Sicario. Every VISION checkbox is marked pass or fail with a link to the proof that shows it.
- [ ] The report = VISION with every box ticked or a named reason, faked-only first.
**Status:** not started.
```
FEELESS, Slice 8. Read CLAUDE.md, then docs/VISION.md, then docs/SLICES.md. Trust nothing: review everything slices 0–7 pushed (/code-review high), fix real findings, then run one TEST proof of every type on Sicario's agent (no money) and mark every VISION checkbox pass/fail with a link to the proof. Gate green; pushed. Report faked-only first.
```
