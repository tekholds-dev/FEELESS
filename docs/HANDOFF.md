# HANDOFF — OPEN CARDS ONLY (reorganized 2026-11-12). The only to-do list.

> Work top down. **Claim** a card (`claimed: <account> <time>`) before you start so no two Claudes build the same thing.
> Done = the "Done when" is proven → push → delete the card here → one line in `docs/history/<this month>.md`.
> Rules: `docs/RULINGS.md` · old detail for any ID: grep `docs/archive/HANDOFF_before_2026-11-12.md` (full old page, word for word).
> Every report says the % left. **Now: ≈5% left** (COL-20 P2/P3, SITE-5 hand-moves, SITE-8 money stores + live workers, COL-6's stamp), then only the owner's money tests.

## COLLECTIVE

**COL-6 · PoStatic pilot on OSSY + G4** · WAITING ON THE 24h STAMP · claimed: fable 2026-11-13
2026-11-13: Sicario's real proof ps0801357a62 keeps plan, build, OSSY + G4 reviews, file, grade, stash, events, vitals. Only the stamp is left
(lands 2026-11-14 05:43 UTC). Check: `bash scripts/postatic-pilot.sh --check` → all ✅ = close this card.
Owner: run it end to end. Done when: plan → build → review → real-browser test → file → stash → grade → stamp → events → vitals row, all
kept on one real proof. G4 runs from the owner's Terminal (Claude has no LAN route) → Claude preps one command for him. No money.

**COL-20 · Proof integrity (P0 + P1 done 2026-11-13, P2/P3 open)** · claimed: — · see RULINGS 2026-11-13
Done + live: results beat grades (false PoB pob1793907481 corrected to NOT PROVED by rows 526-527), builders sit out, clean judge brief, review provenance, ps_hidden code checks (59 real pages: 88% avg; misses = sample numbers + our own hidden WebGL text, both fixed at the source).
Owner 2026-11-13: HE reviews Sicario's proofs (his marks); OSSY + G4 sit out what they built; scope stays Sicario's only. Both judges are Qwen: a non-Qwen local judge would make them independent.
Left (Claude): P2 regression checks on reused kits + "existing tools checked" note on PoStatic reviews · P3 verified missions per dollar on Fee's stash dashboard + daily chain-tip commitment.

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

## OWNER ONLY
**Owner only (Claude never moves funds) — 👑 owner 2026-11-12 (said twice, final): HE does ALL real-money testing himself. Claude's whole job is: finish every build row, prove it, push, tick this page, then TELL HIM it is ready to test. Claude never asks him anything mid-list; it builds, proves and pushes straight through.**
- 💵 **T1 READY (checked 2026-11-12 16:55):** cash-check covered (30 swaps match, gas reserve short 0.005982 SOL) · edge gate TRADE (1/994 rules pass unseen, n 35, thin) · live quotes with his admin wallet: 0.0123 SOL → $1.0008 USDC and $1 → 0.01229 SOL, engine Swap API, 0 FEELESS fee (non-staff wallets pay 10% = 950 bps at tier 0). His wallet: 0.1378 SOL + 1.03 USDC.
- 💸 COL-16 first real send (yours): open a filed proof → 🪙 Send to the Collective → SEND IT WITH YOUR FUNDS → Quote it → Sign and send.
- 💵 Real-money agent tests, in order: cash audit (`scripts/edge-audit.py`; Fuse gas reserve short 0.006 SOL) → T1 $1 SOL→USDC→SOL · T3 $1 into
  Happy's wallet and back → AGT-25 OSSY/G4 PoWs through the Fuse card (DEGEN_PLAYBOOK, guards, he confirms the first buy) → T2 Fuse withdraw $1 →
  Circle → Phantom → AGT-26, AGT-24.
- Decisions/keys: KEYS, LAWYER, HOUSE, LOOKS rows below · $ limit on the OpenRouter key.
