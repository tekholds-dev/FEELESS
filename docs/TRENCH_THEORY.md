# 🧪 The Trench Theory — what the desk's own records prove (as of 2026-10-22)

Source: `scripts/edge-audit.py` (4,000 launch coins watched an hour; learn on the oldest 60 %, test on the newest 40 %; 3 % round-trip cost) +
the real card's 943-piece ledger. Code: `backend/trench_theory.py` — `verdict(case)` is sent with EVERY coin case as `theory`, so G4 / OSSY / NEXA
confirm or deny one evidence line instead of reasoning from zero. A law that stops holding on unseen coins is DELETED, never argued with.

| Law | Claim | Evidence |
|---|---|---|
| FRESH | a coin under 15 min old loses | 2,421 coins · typical −68.7 % / hour · 14 % up |
| CURVE | still on the bonding curve = worst bucket | 2,181 coins · typical −65.4 % · 9 % up |
| PROVEN | cap < $30K **and** graduated = the ONLY rule positive on unseen coins | 110 coins · typical +1.0 % · capped avg +10.2 % · 52 % up |
| EXITS | set the exit before entry: +50 / −30 beats holding | −9.9 % vs −42.8 % held an hour |
| HOLD | real card: exits under 15 min lose, 1–3 h holds are the best bucket | 296 closed real lots: < 15 min = 150 lots ~14 % won · 1–3 h = 37 % won, avg +0.8 % |
| BAIL | the agents' own early exits are the costliest habit | 78 agent exits, median hold 13 min: 12 % won, median −6.9 % · stops 3 % won, −15.6 % |
| COST | a setup must expect more than the 3 % round trip | every rule scored after cost |
| THIN | a pool under $5K cannot take a real exit | slippage |

Roles: **G4** = the skeptic (find the law a coin breaks) · **OSSY** = the reader (chart + tape vs the laws) · **NEXA** = the fast confirm
(one line: agree / disagree with `theory`, why) · **agents** = deterministic; the theory is advisory to them until a shadow test proves a law
lifts their real P&L (never a new buy door without guards).
Last 3,000 agent calls: 0 entries, all WAIT (wait → 60 min typical −6.3 %) — waiting was right on this tape.
Re-run: `.venv/bin/python scripts/edge-audit.py` → update `EVIDENCE` in `trench_theory.py` + this table.

## Shadow test on the real card (2026-10-22, 267 closed lots with launch facts)
- The entry laws (FRESH / CURVE) would have blocked only 3 lots — the desk already avoids them; they don't explain the losses.
- The losses come from HOW the card exits: agent bails at ~13 min (12 % won), stops (3 % won). Owner's manual sells: 33 % won, −1.1 %, ~59 min.
- ✅ OWNER DECIDED 2026-10-22 "15 minutes not 30": `arena_prime.AGENT_MIN_HOLD` = 15 — on the real card an agent's / model's own exit of a
  RED coin waits until the buy is 15 min old (stops, rug / drain / dump, the catastrophic line and any green sale never wait); round
  rotations floor at `REAL_MIN_HOLD` = 15 too. The 5-min clock stays. Re-check the BAIL row after a week of lots.
