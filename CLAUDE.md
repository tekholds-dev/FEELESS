# FEELESS — working rules (slim, 2026-11-12). Degen trading terminal + agents, Solana-first.

> 👑 The owner's newest chat message wins. A changed rule goes into **docs/RULINGS.md** (the one place), the same turn.
> ✨ First try = finished: styled, real data, tested, seen in the browser, pushed, HANDOFF card closed. Never stop to ask mid-list.
> 🧰 Stash every safe, clean piece of data/build (stash + Fee's stash/Git folder). Think past the ask; never fake a feature.

## Where everything lives (read ONLY what your task needs)
| File | When |
|---|---|
| `docs/HANDOFF.md` | Every session: open task cards only. **Claim a card** (`claimed: <you> <time>`) before starting; close it when proven. |
| `docs/RULINGS.md` | Any rule question. Dated owner decisions; newest wins. |
| `docs/specs/style.md` | **Before ANY UI work**: mandatory styling + animation, meta styling, CSS map, one component per job, speed, data sources, chat meta. |
| `docs/specs/money.md` | Fuse / real card / perps / brokers / go-live (DEGEN_PLAYBOOK is its first section). |
| `docs/specs/agents.md` | Agent brain, kernel, real cats, trench crew, Supreme Intelligence. |
| `docs/specs/site.md` | Architecture, always-on, speed list, **mobile layout (before any phone/Duo change)**, Telegram, LM Studio, staff + safety nets. |
| `docs/specs/familia.md` | Familia (older spec — check the code first). |
| `docs/FEELESS_HISTORY.md`, `docs/archive/` | GREP only, never load whole. Done cards become one line in HISTORY. |

## Before every push (all must pass, gate on real exit codes — never `| tail`)
1. `cd frontend && CI=true yarn test --watchAll=false`
2. `cd frontend && CI=false npx craco build`
3. `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` (plain `python` isn't on the owner's Mac)
4. New mechanic ⇒ new test (fake the network; never hit mainnet or move funds). 5. UI change ⇒ open it in the browser, screenshot, or say you didn't.
Push finished work to `main` (the owner's `scripts/auto-pull.sh` updates his machine). Never commit unrelated edits.

## Hard rules (always)
- Palette FEELESS green on Obsidian (`#19e68c`, day `#08995a`) via meta.css tokens, never a hand-written hex; 6 font tokens only; m-* presets first.
- **NO GeckoTerminal, ever** (test enforces). Market data = DexScreener + our own indexes.
- Tests never touch real data (`tests/conftest.py` sandbox). `_is_staff(address)` is THE admin rule. Pyflakes guard: no undefined names.
- Speed: no request waterfalls, shared pollers, transform/opacity animation only, heavy FX die under `body.fx-lite`.

## Money rules (trading)
- 🔒 P&L NEVER includes fees, anywhere (live trades, Fuse cards, Arena/Prime, FeeCat): cost = money that REACHED THE POOL
  (`trade_fills.position` → `investedPoolUsd` / `realizedPoolUsd`; client `pnlSummary` uses them), fees live on the receipt
  (`feesUsd`, FeeCat `feesSol`). Value = on-chain balance × Jupiter live price. Phantom's chart price can lag ~0.5%.
- Engine: Jupiter Swap API primary (FEELESS fee into our SOL/USDC token accounts, capped priority,
  our broadcast). Ultra only as engine or opt-in fallback. Fallback off + Swap API down ⇒ trading pauses.
- Nothing trades fee-free except **buying** $FEE / FEECAT / rFEE. Coin→coin with no SOL/USDC side is refused.
- The wallet signs everything; the server verifies the signed message equals the quoted one; no resubmits.
- Only show or sign an order that matches the coins, side and amount on screen.

## Layout
- Helius key: `HELIUS_API_KEY` or `HELIUS_RPC_URL` (SOLANA_RPC_URL may point at another RPC).
- Backend services (restart all after backend changes: `bash scripts/start-backend.sh`):
  `server` 5001 (market + trading), `reputation_service` 5077 (social, fees, admin), `feecat_service` 5088, `candles_service` 5099.
- Frontend: CRA + craco on 51367. Styles mostly in `frontend/src/styles/terminal.css` (append scoped blocks).
- HQ settings that matter at scale (keys, engine, fees) must be visible in its **Core** group.


