# HANDOFF — OPEN CARDS ONLY (reorganized 2026-11-12). The only to-do list.

> Work top down. **Claim** a card (`claimed: <account> <time>`) before you start so no two Claudes build the same thing.
> Done = the "Done when" is proven → push → delete the card here → one line in `docs/history/<this month>.md`.
> Rules: `docs/RULINGS.md` · old detail for any ID: grep `docs/archive/HANDOFF_before_2026-11-12.md` (full old page, word for word).
> Every report says the % left. **Now: ≈19% left**, then only the owner's money tests.

## COLLECTIVE

**COL-6 · PoStatic pilot on OSSY + G4** · OPEN · claimed: —
Owner: run it end to end. Done when: plan → build → review → real-browser test → file → stash → grade → stamp → events → vitals row, all
kept on one real proof. G4 runs from the owner's Terminal (Claude has no LAN route) → Claude preps one command for him. No money.

**COL-11 · Evolution Lab** · OPEN (after COL-6) · claimed: —
Done when: frozen baseline vs challenger on held-out data, promotion gate, rollback, generation history, shadow trades — shown on a real
agent. Never call one winning trade learning. Source: `docs/specs/agents.md` (SUPREME_INTELLIGENCE_REQUEST).

**COL-16 · Graded proof with funds** · OPEN · claimed: —
Owner: the user sends a proof WITH an amount of funds to be graded; on AUTO the agent sends the % from its own wallet with the proof.
Done when: amount + % shown before send, wallet signs, receipt filed on the proof, tested with fakes; owner does the first real send.

**COL-18 · Pool ledger → database** · OPEN (hold lifted by owner) · claimed: —
Done when: ledger + HMAC trail in the DB, `audit()` still closes, old file kept read-only as backup, test proves totals equal before/after.

**COL-8 · Collective audit (fast)** · OPEN · claimed: —
Done when: every Collective folder checked for bugs, text matches the data, designs aligned; fixes pushed. No deep dig.

**COL-9 · Agents work from the shared brain** · OPEN · claimed: —
Done when: one live run where an agent reuses another agent's fresh read (shown in its folder). Real research (cited reads) where needed, never faked.

**COL-10 · Method kits (ongoing)** · OPEN · claimed: —
First: check whether the owner's Claude accounts have been adding to the stash. If not, build the smart fix: every Claude session/agent
auto-files its methods + builds into the stash. Done when: new entries from more than one account visible in the stash.

**COL-19 · Proving ground** · OPEN · claimed: —
Done when: an arena with faked volume, delays and failures gates live permission; many runs with FREE models filed on the Test bench;
handed to the owner clean → he funds the FeeCat wallet (HQ › Circle wallets).

## SITE

**SITE-4 · Command centers** · OPEN · claimed: —
Done when: Familia's own + Sicario's, Fee, FeeCat rebuilt with real telemetry only, alive, dense, phone-ready. Familia amounts: owner sets, no caps.

**SITE-5 · Split the big backend file** · OPEN · claimed: —
Done when: money 52, writes 50, admin 48 and the 11 overlapping routes moved; route table identical; safety cases tested (auth, signed = quoted,
no resubmit, staff checks).

**SITE-2 · Hardening (users + attacks)** · OPEN · claimed: —
Done when: rate limits on every public write, request size caps, slow-client timeouts, one bad endpoint can't starve the rest; abuse load test
(`scripts/load-test.py`) passes.

**SITE-8 · Database + workers** · OPEN · claimed: —
Done when: hot stores in a real DB, multiple workers, no lost writes, load test proves it. (FPS + first load test done.)

**SITE-17 · Familia lending readers — real work** · OPEN · claimed: —
Done when: marginfi, Save, PumpSwap LP, Phoenix, Meteora wired into family blocks, each shown on screen from a real account read; Helius 429
handled (rotate / fall back). No claim without a live read.

## OWNER ONLY
**Owner only (Claude never moves funds) — 👑 owner 2026-11-12 (said twice, final): HE does ALL real-money testing himself. Claude's whole job is: finish every build row, prove it, push, tick this page, then TELL HIM it is ready to test. Claude never asks him anything mid-list; it builds, proves and pushes straight through.**
- 💵 **T1 READY (checked 2026-11-12 16:55):** cash-check covered (30 swaps match, gas reserve short 0.005982 SOL) · edge gate TRADE (1/994 rules pass unseen, n 35, thin) · live quotes with his admin wallet: 0.0123 SOL → $1.0008 USDC and $1 → 0.01229 SOL, engine Swap API, 0 FEELESS fee (non-staff wallets pay 1425 bps = Q29). His wallet: 0.1378 SOL + 1.03 USDC.
- 💵 Real-money agent tests, in order: cash audit (`scripts/edge-audit.py`; Fuse gas reserve short 0.006 SOL) → T1 $1 SOL→USDC→SOL · T3 $1 into
  Happy's wallet and back → AGT-25 OSSY/G4 PoWs through the Fuse card (DEGEN_PLAYBOOK, guards, he confirms the first buy) → T2 Fuse withdraw $1 →
  Circle → Phantom → AGT-26, AGT-24.
- Decisions/keys: $FEE / FEECAT / rFEE have no pool · Q29 15% swap fee intended? · KEYS, LAWYER, HOUSE, LOOKS rows below · $ limit on the OpenRouter key.
