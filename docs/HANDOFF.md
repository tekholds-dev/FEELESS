# HANDOFF — OPEN CARDS ONLY (reorganized 2026-11-12). The only to-do list.

> Work top down. **Claim** a card (`claimed: <account> <time>`) before you start so no two Claudes build the same thing.
> Done = the "Done when" is proven → push → delete the card here → one line in `docs/history/<this month>.md`.
> Rules: `docs/RULINGS.md` · old detail for any ID: grep `docs/archive/HANDOFF_before_2026-11-12.md` (full old page, word for word).
> Every report says the % left. **Now (2026-11-13, owner flagged): build order = ~~LOOK-1~~ ✅ → ~~COMP-1~~ ✅ → ~~AGENT-AUTO~~ ✅ → SEC-1 (+ SITE-8) → STYLE-1 → LEGAL-1 → JUDGE (COL-20, LAST). Owner is NOT testing real money until all of this works and OSSY+G4 can file easy live proofs with working realtime chat.**
> How to work: `CLAUDE.md` (the one rulebook) · ship with the `feeless-ship` skill. These cards came straight from the owner on 2026-11-13 with screenshots — build the full ask, don't re-litigate.

> ## ▶ START HERE (next account — the owner does NOT want to paste instructions)
> 1. Read `CLAUDE.md` then this file. Work the build order above, **one card at a time, full build, shown LIVE to the owner before moving to the next** (this is the fix for the surfaces he re-asked 20× that only got half-done).
> 2. Before building a card, give the owner the shortlist of the best free tools/services for it, then build.
> 3. **SEC-1's full brief is already written in its card below** — build to that spec exactly; the owner should not have to paste a prompt. Push the defensive edge as far as the law allows; the "OFF THE TABLE" line in that card is the one boundary.
> 4. Never move real funds / hit mainnet; the owner does all real-money tests.

## COLLECTIVE

**COL-6 · PoStatic pilot on OSSY + G4** · WAITING ON THE 24h STAMP · claimed: fable 2026-11-13
2026-11-13: Sicario's real proof ps0801357a62 keeps plan, build, OSSY + G4 reviews, file, grade, stash, events, vitals. Only the stamp is left
(lands 2026-11-14 05:43 UTC). Check: `bash scripts/postatic-pilot.sh --check` → all ✅ = close this card.
Owner: run it end to end. Done when: plan → build → review → real-browser test → file → stash → grade → stamp → events → vitals row, all
kept on one real proof. G4 runs from the owner's Terminal (Claude has no LAN route) → Claude preps one command for him. No money.

**COL-20 · Proof integrity (P0 + P1 done 2026-11-13, P2/P3 open)** · claimed: — · see RULINGS 2026-11-13
Done + live: results beat grades (false PoB pob1793907481 corrected to NOT PROVED by rows 526-527), builders sit out, clean judge brief, review provenance, ps_hidden code checks (59 real pages: 88% avg; misses = sample numbers + our own hidden WebGL text, both fixed at the source).
Owner 2026-11-13: OSSY + G4 review ALL agents (`FEELESS_REVIEW_SCOPE=all`), he reviews what they built + spot-checks. Judge scorecard live in the proofs brief: G4 44% right vs 44% fail-everything (9 settled), OSSY 50% vs 40% (10). Goal: both clearly past the line.
Left (Claude): JUDGE SKILL — feed each judge its own misses vs the stamp, a non-Qwen third judge, fix one-issue-fails-all-five checks · P2 regression checks on reused kits + "existing tools checked" note on PoStatic reviews · P3 verified missions per dollar on Fee's stash dashboard + daily chain-tip commitment.

**COL-10 · Method kits (ongoing)** · BACKFILLED 2026-11-13 · claimed: fable
Checked: no Claude session had ever filed to the stash. Built `scripts/stash-builds.py` (+ `backend/claude_builds.py`): every Claude-made
commit → stash 'Builds', tagged by model (git can't tell accounts apart). 1,195 filed (opus-5.5, fable-5, fable-5.2), live in /api/cats/stash/web.
Left: run it on every commit. Claude was blocked from adding a git hook (persistence rule) → owner adds `.githooks/post-commit` calling
`.venv/bin/python scripts/stash-builds.py --rev HEAD`, or runs `.venv/bin/python scripts/stash-builds.py` any time (never files twice).

## SITE

**SITE-5 · Split the big backend file** · OPEN · claimed: — · money/write/admin routes move only with the owner watching the live machine · 2026-11-13: `scripts/route-table.py` (--save before a move, --check after = same 618 routes in the same order with the same params, --left = what is still inside by kind: money 26 · write 101 · admin 164 · read 131). The old AST mover was a one-off; the 131 reads left are the long / comprehension-shadow ones. 2026-11-13 slice 8: `scripts/move-routes.py` moved 45 more plain reads → `rep_more_reads.py` (route-table --check now says EQUIVALENT when only non-overlapping order changed; it refuses a move a wildcard path would catch). Left: money 26 · write 101 · admin 164 · read 86 (59 reuse a module name as a local → hand-move).
Done when: money 52, writes 50, admin 48 and the 11 overlapping routes moved; route table identical; safety cases tested (auth, signed = quoted,
no resubmit, staff checks).

**SITE-8 · Database + workers** · OPEN · claimed: — · 2026-11-13: `backend/sql_store.Docs` (one row per key, `update()` = one BEGIN IMMEDIATE txn across processes) + quest state moved onto it (real 13 wallets equal, old file 0400); `scripts/load-workers.py`: uvicorn 4 workers × 3,000 concurrent writes → 0 lost, 1.9K rps, p95 45 ms. Slice 2 done: wallet profiles → profiles.db (4 write sites are per-wallet transactions, real 3 rows equal, old file 0400; 4-process test 160/160). Next slices: fuse_hq.json (117 save sites, money → watched), feecats.json (_KEPT overlay), crews/runners; then in-memory limits/caches → shared; then `--workers` on the live services (owner watching).
Done when: hot stores in a real DB, multiple workers, no lost writes, load test proves it. (FPS + first load test done.)

**STYLE-1 · Colour token sweep** · OPEN · claimed: — · 2026-11-13: ~20.9K hand-written hex values in `frontend/src/styles` + ~1.1K in components break the tokens-only rule (CLAUDE.md §6). Sweep one sheet per slice into meta.css tokens (screenshot before/after; the look must not change). Shader colours in JS are exempt. Done when: `grep -c '#[0-9a-f]{6}'` on styles is near zero outside meta.css.

**LEGAL-1 · Terms, risk, privacy — self-serve, NO lawyer (owner 2026-11-13: "nothing truly needs a lawyer frfr, research how these sites do it")** · OPEN · claimed: —
Drafts in `docs/legal/`. Owner's call: perps / Jupiter / wiring keys are the USER's own legal discretion (Q3 closed), and FEELESS is non-custodial, so no lawyer read is booked. Instead: research how real peer sites (Jupiter, Phantom, pump.fun, Drift, GMX-style UIs) word their terms / risk / disclaimers and age+region gates, and match that. Then: Terms + Risk + Privacy pages live on the site, versioned terms acceptance on first wallet connect (stored per wallet), a per-feature geo/age gate switch in HQ › Core, data export/delete per wallet. Fill [ENTITY]/[STATE]/[SUPPORT ADDRESS] with the owner. Still LAST.

**SEC-1 · WAR ROOM — one live security dashboard in the owner cmd-center (owner 2026-11-13: "all of it in one spot, a huge live dash")** · OPEN · claimed: opus-5.5 2026-11-13 14:40
Everything below lives in ONE owner-only tab, as a big always-live dashboard (game-window density, library charts, transform/opacity only, tokens). All of it stays on FEELESS's own property — that is what keeps it legal.
1. **Live attempts feed:** every probe/attack on FEELESS streaming in — source IP/ASN, wallet if any, what was tried, what was blocked, a running map/timeline. This is the owner's "live moves" view.
2. **Honeypots + tarpits:** fake admin panels, fake wallet/API endpoints, fake "vulnerable" routes served to attackers; connections that hang forever to burn their tooling. Capture the full payload + method for study. (Our server → legal.)
3. **Canary / beacon tokens:** plant unique tracking tokens (canarytokens-style URLs/docs/pixels) in the fake data they exfiltrate; when they open it THEY call us → log real IP, UA, rough location. Poison the stolen dump with junk + beacons. Edge rule: the beacon only phones home — it NEVER runs code on their machine.
4. **On-chain tracing:** follow any stolen/suspect wallet (it's traceable forever); auto-build an evidence pack (IPs, wallets, tooling fingerprints, timing) ready to send to exchanges (freeze on cash-out) + IC3/law enforcement. This is how real crews recover funds — tracing + freezes, not counter-hacks.
5. **Auto-harden / auto-ban loop (live):** on a detected pattern — block IP/ASN, rotate the targeted secret, tighten the rule — each move animating on the dash in real time.
6. **Breach-attempt rewards = an opt-in bounty:** publish scope + rules; pay responsible disclosure (HackerOne / Immunefi-style, crypto-native). Turns attackers into paid testers.
7. **Exploit research → hardening writeup:** deep web research of the biggest + most recent crypto attacks/scams/exploits (how the white/black hats did it, incl. the ~15%-kept-BTC crews), each turned into a concrete FEELESS hardening item, tracked on the dash.
⚠ OFF THE TABLE (illegal — CFAA etc., do NOT build): sending any attack/code to run on the attacker's machine, flooding/damaging their systems, "the same attack back stronger", or a downloadable offensive kit to use on others. The defensive stack above is the legal maximum — build that, and tell the owner plainly if anyone asks for the hack-back part again.
Pairs with SITE-8 (many users + attacks never stop the operation). Done when: the War Room tab is live with real tracked attempts, honeypots capture + the auto-harden/ban loop works on real probes, canary beacons log openers, on-chain tracing + evidence pack generate, the bounty page is up, the exploit→hardening list is written, and `/security-review` passes clean.

**MODEL-CFG · Per-model effort + tooling controls when a user picks a model (owner 2026-11-13)** · OPEN · claimed: —
After a user chooses a model (OpenRouter-backed) for an agent brain / chat, surface whatever that model + provider actually exposes — reasoning **effort** (e.g. low/medium/high), max-tokens, temperature, and any provider-specific toggles — read live from OpenRouter's model metadata, not hard-coded, so each model only shows the knobs it really supports (a model with one effort shows none; a reasoning model shows its efforts). If a control is Anthropic-only or provider-only, that's fine — show it only for those models. Keep it one compact control cluster by the model chip (game-window density, tokens). Note: "ultracode"/`/code-review ultra` is a Claude Code harness feature, not an API model param — not exposed to FEELESS users; don't fake it. Done when: picking a model shows exactly the controls that model supports (verified against a live OpenRouter metadata call), the settings ride with the agent's requests, and a model with no extra knobs shows a clean default.

## OWNER ONLY
- 🔧 **One-time setup (2 min):** post-commit stash hook (hooks already live in `.githooks`) — `printf '#!/bin/sh\n.venv/bin/python scripts/stash-builds.py --rev HEAD >/dev/null 2>&1 &\n' > .githooks/post-commit && chmod +x .githooks/post-commit`. Paste the 4-line block from `docs/CLAUDE_ACCOUNT_PROMPT.md` into every Claude account's profile. Authorize GitHub in `/mcp`.
**Owner only (Claude never moves funds) — 👑 owner 2026-11-12 (said twice, final): HE does ALL real-money testing himself. Claude's whole job is: finish every build row, prove it, push, tick this page, then TELL HIM it is ready to test. Claude never asks him anything mid-list; it builds, proves and pushes straight through.**
- 💵 **T1 READY (checked 2026-11-12 16:55):** cash-check covered (30 swaps match, gas reserve short 0.005982 SOL) · edge gate TRADE (1/994 rules pass unseen, n 35, thin) · live quotes with his admin wallet: 0.0123 SOL → $1.0008 USDC and $1 → 0.01229 SOL, engine Swap API, 0 FEELESS fee (non-staff wallets pay 10% = 950 bps at tier 0). His wallet: 0.1378 SOL + 1.03 USDC.
- 💸 COL-16 first real send (yours): open a filed proof → 🪙 Send to the Collective → SEND IT WITH YOUR FUNDS → Quote it → Sign and send.
- 💵 Real-money agent tests, in order: cash audit (`scripts/edge-audit.py`; Fuse gas reserve short 0.006 SOL) → T1 $1 SOL→USDC→SOL · T3 $1 into
  Happy's wallet and back → AGT-25 OSSY/G4 PoWs through the Fuse card (DEGEN_PLAYBOOK, guards, he confirms the first buy) → T2 Fuse withdraw $1 →
  Circle → Phantom → AGT-26, AGT-24.
- Decisions/keys: KEYS, LAWYER, HOUSE, LOOKS rows below · $ limit on the OpenRouter key.
