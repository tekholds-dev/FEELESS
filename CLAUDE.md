# FEELESS — the ONE rulebook for every Claude account (cleaned 2026-11-14: nothing here blocks a direct ask). Degen trading terminal + agents, Solana-first.

Every account, every machine, cloud or local, reads THIS file. It is in git, so it is the same everywhere.
`~/.claude/CLAUDE.md`, the claude.ai profile and memory notes only point here; they never hold a rule of their own.
Order of authority: **1 Hard limits** (never bend) → **the owner's newest chat message** → this file → `docs/RULINGS.md` → `docs/specs/` → memory.
Anything below §1 that gets in the way of what the owner just asked loses to his ask — do the ask.

## 1 · Hard limits (never bend, not even for a newer message — the owner changes these only by editing this section)
- **Money:** Claude never moves funds, never hits mainnet in tests, never changes a trading rule or the owner's real config unless he names the value. The owner does ALL real-money tests. OSSY + G4 tests run on their own LM Studio only, never a fallback model.
- **Keys + privacy:** never print, commit or send keys, the owner's email or wallet secrets. Tests never touch real data (`tests/conftest.py` sandbox).
- **Signing:** the wallet signs everything; the server verifies signed = quoted; no resubmits; only show or sign an order matching the coins, side and amount on screen.
- **P&L never includes fees** (cost = money that reached the pool; fees live on the receipt). Any new real-money auto-buy ships with age / pool / already-ran guards.
- **NO GeckoTerminal, ever** (a test enforces). Market data = DexScreener + our own indexes.
- **Legal:** nothing that makes FEELESS a custodian, broker or betting house without the owner's dated ruling (see `docs/legal/`).

## 2 · How we work
- **The owner's ask is the task.** No card, claim or plan step is needed first. `docs/HANDOFF.md` only carries open work between sessions.
- **Answer first**, short and plain, then do it.
- **Scope:** build exactly what was asked, fully. Ideas past the ask go in the report under **"Proposed"** (one line each). A bug or security hole found on the way is fixed and named.
- **Keep going:** work every item in order without stopping to ask. If something is unclear, take the safest reading, build it, and list it under **"Judgment calls"** so the owner can flip it. Only §1 stops work.
- **Big work ships in slices** (never stuck on one thing for more than ~30 min); each slice is finished and says what is left.
- **Done means:**
  - UI: `docs/specs/style.md` tokens, real data, every tab of the surface checked in the browser, a screenshot shown to the owner.
  - Backend: a test for the new mechanic (network faked), pyflakes clean, the live service checked after reload.
  - Money code: a second review pass (`/code-review` or `/security-review`) before push; the owner tests it with real money.
  - Then: gate green on real exit codes → pushed to `main` → a history line if a HANDOFF card closed → the report says what is live, faked-only and untested.
- **Reports:** sections only when they have content: Done · Not verified · Judgment calls · Proposed · % left.
- **A new rule from the owner** → one dated line in `docs/RULINGS.md`, and remove whatever it contradicts the same turn. No rule lives in two places.

## 3 · Machine facts (learned the hard way — apply on every account)
- Saved backend `.py` files go live in ~15 s (keep-alive reload): grep names + run guard tests right after each backend edit.
- A backend push makes the owner's `scripts/auto-pull.sh` restart every service: never push backend code while a build/proof is running.
- Claude's shell has no LAN route: G4 / LM Studio restarts and pilots run from the **owner's Terminal** — give him the one command.
- The owner only looks at `localhost:51367` from the main folder: never hand over work from another port/worktree. (The private gate snapshot below is fine — it is not handed over.)
- Push gate flakes under load: commit in the main tree, then gate + push from `.claude/worktrees/gate` (`git checkout --detach <sha>`; `git push origin HEAD:main`); run nothing beside it. Never gate on `| tail`/`| grep`.
- Make one real call to an outside service before building on it. Research free/open libraries first (shadcn/ui, Motion, Recharts, Lightweight Charts) — never hand-draw a chart.
- Every desk test → `test_bench.file_run` (Proofs › Test bench). Every safe build/data piece → the stash (Fee's stash/Git folder).
- Never commit `.emergent/recordings/` or `scripts/trim-mongo-caches.py`. Commits end with `Co-Authored-By: <your model> <noreply@anthropic.com>`.
- Phone / LAN wallet tests need https (wallets ignore plain-http LAN pages): owner runs `cloudflared tunnel --config /dev/null --url http://127.0.0.1:51367 --http-host-header localhost:51367` (his old `~/.cloudflared/config.yml` 404s a bare quick tunnel; `localhost` dials ::1 and fails). keep-alive restarts only the backend: if 51367 is down, start `feeless-frontend` (launch.json).
- Ship steps for every account: the `feeless-ship` skill (`.claude/skills/feeless-ship/SKILL.md`).

## 4 · Where everything lives (read ONLY what your task needs)
| File | When |
|---|---|
| `docs/HANDOFF.md` | Open work carried between sessions (no claiming). A finished card becomes one line in `docs/history/<month>.md`. |
| `docs/RULINGS.md` | Live owner decisions (dated, newest wins) + Open questions. Old decisions below it are history. |
| `docs/specs/style.md` | **Before ANY UI work.** |
| `docs/specs/money.md` · `agents.md` · `site.md` · `familia.md` | Money/perps/brokers · agent brain + Collective · architecture, mobile, staff · Familia (older — check code first). |
| `docs/legal/` | Terms, risk, privacy drafts + the lawyer checklist. |
| `docs/history/`, `docs/archive/` | GREP only, never load whole. |

## 5 · Gate (all must pass on real exit codes before every push)
1. `cd frontend && CI=true yarn test --watchAll=false` 2. `cd frontend && CI=false npx craco build`
3. `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` (plain `python` isn't on the owner's Mac)

## 6 · Code map + money engine
- Palette FEELESS green on Obsidian (`#19e68c`, day `#08995a`) via meta.css tokens; 6 font tokens; m-* presets first. (WebGL shader colours in JS are the one place a hex is allowed.)
- `_is_staff(address)` is THE admin rule. Speed: no request waterfalls, shared pollers, transform/opacity animation only, heavy FX die under `body.fx-lite`.
- Engine: Jupiter Swap API primary (FEELESS fee into our SOL/USDC accounts, capped priority, our broadcast); Ultra only as engine or opt-in fallback; fallback off + Swap API down ⇒ trading pauses. Fee-free only when **buying** $FEE / FEECAT / rFEE. Coin→coin with no SOL/USDC side is refused.
- Services (restart: `bash scripts/start-backend.sh`, from the owner's Terminal): `server` 5001, `reputation_service` 5077, `feecat_service` 5088, `candles_service` 5099. Frontend CRA + craco on 51367. Helius: `HELIUS_API_KEY` or `HELIUS_RPC_URL`.
- HQ settings that matter at scale (keys, engine, fees) live in its **Core** group.
- Names: the judges (OSSY + G4) are **The Collective** to users; Fee's public trade brain is **FeeCat AI** to visitors; funds = **The Pool**. Code names `honey` / `colony` are legacy ids only.
