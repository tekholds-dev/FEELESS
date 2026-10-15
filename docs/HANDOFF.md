# HANDOFF — start here (any Claude account, any new session)

Read this first (2 min), then only the parts of `CLAUDE.md` your task touches (`grep -n "<topic>" CLAUDE.md`). CLAUDE.md is the
full rulebook (~2K lines of "why"); this page is the map.

## 1 · What this is
FEELESS = a Solana degen trading terminal. One owner, one REAL money card run by ten agents, plus a big site (trade, Fuse, Arena,
chats, FeeCat). Money rules are strict and tested — read `CLAUDE.md › Money rules` before touching anything that buys or sells.

## 2 · Run / check
| What | Command |
| --- | --- |
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest` — it lacks the babel config) |
| build | `cd frontend && CI=false npx craco build` |
| all gates (pre-push hook) | `bash scripts/gate.sh` |
| restart backend | `bash scripts/start-backend.sh`, then `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1 |
| real card money trail | `.venv/bin/python scripts/fuse-report.py 6` |
| is there an edge? | `.venv/bin/python scripts/edge-audit.py` (run BEFORE advising on real-money buying) |

Services: `server` 5001 · `reputation_service` 5077 · `feecat_service` 5088 · `candles_service` 5099 · frontend 51367 (the owner's own dev
server — attach, never start a second). Push to `main`; the owner's Mac auto-pulls. After a backend push, restart the backend yourself.

## 3 · Where things live (the 20 files that matter most)
| Area | Files |
| --- | --- |
| agents (the real card) | `backend/agents.py` · `office.py` · `office_edge.py` · `trench_kernel/` · `opportunity.py` · `capital.py` |
| keeper (signs, sells, books) | `backend/fuse_wallet.py` · `arena_prime.py` (tier engine) |
| AI | `backend/ai_router.py` (providers) · `ai_duet.py` (Gemma + Qwen) · `ai_learn.py` (grading) · `ai_chat.py` (Brain) · `ai_brain.md` |
| owner's LM Studio | `backend/feeless_mcp.py` (read-only MCP) · `docs/lm_fee_prompt.txt` · `docs/LM_STUDIO_MCP.md` · `docs/FEE_BRAIN.md` |
| big service | `backend/reputation_service.py` (16K+ lines — grep, never read whole) |
| UI | `frontend/src/components/command/` (HQ, Agents cockpit) · `components/HomeEngine.jsx` · `styles/` |

## 4 · Current state (2026-10-14)
- AI: 🖥 Gemma on the desktop Mac (`lan`, primary) + 💻 Qwen on this Mac (`local`, secondary) as a DUET; cloud = Groq / OpenRouter.
  Reads are advisory and graded; no model ever buys, sizes or sells.
- Real card ≈ $2.80 of $39.24 put in (`fuse-report.py`). Edge audit: no rule positive on unseen coins yet — losses = cost × swaps + rugs.
- Open asks: see `backend/data/build_queue.json` (approved build ideas) and `CLAUDE.md › NEXT SESSION`.

## 5 · How to work here (the owner's rules, short)
- Brief with the owner. Verdict, what changed, what was tested, what wasn't.
- Every money change ships with a test that fakes the network. Never hit mainnet or move funds.
- UI = m-* presets, transform / opacity only, day theme + fx-lite + reduced motion + 640px blocks.
- When you ship something, add ONE line to the right section of `CLAUDE.md` and, if it changes the map, this page.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
