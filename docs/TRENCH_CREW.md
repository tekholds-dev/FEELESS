# 🪖 The Trench Crew — trenching only

The agents are a **trench crew**, not a compliance committee. They keep digging until they understand what is happening, then
**Warden** and **Courier** enforce only the few things that can actually blow up execution.

> **Tally discovers. Sherlock investigates. Weather contextualizes. Trigger times. Devil challenges.
> Warden sizes. Courier executes. Reaper manages. Archivist remembers. Judge improves.**

Code: `backend/trench_crew.py` (roles, the hard wall, Devil's weights, Warden's shrink rule) · ranking `opportunity.open_score` ·
the wall `opportunity.open_ok` · live narrative `opportunity.narrative` · switch: real card `agentOpen` (HQ › Agents › ⚙ Control).
Change this file and `trench_crew.py` together — `tests/test_trench_crew.py` checks they agree.

## The crew

| Agent | Role | What it does | What it never does |
|---|---|---|---|
| 📊 Tally | MARKET TRUTH / DISCOVERY | Sees every fresh coin first (Pump, Pulse, Radar, RPC, migrations, volume leaders, movers, new pools) and measures it: newness, cap, price, liquidity, volume velocity, buyer velocity, trades, acceleration, candle / tape freshness, source. | Decide good or bad. A weird coin stays visible unless its data is unusable. |
| 🔍 Sherlock | DEEP INVESTIGATOR | The most curious bot in the office. Chases public clues: deployer / funders, first buyers, wallet clusters, bundles, early-wallet behaviour, site / X, narrative, copycats, prior launches of related wallets, whales accumulating or distributing — does the story match the chain? | Say "no verification = reject". Missing proof is **UNKNOWN / UNPROVEN** — a research state. |
| 🌦 Weather | MARKET CONTEXT | Reads the whole trench: is Pump hot or dead, do launches follow through, are buyers chasing everything, do rugs dominate, do leaders hold gains? | Shut the office. It changes how aggressively the desk sizes (never below ×0.5 in trench mode). |
| ⏱ Trigger | ENTRY TIMING | Decides **when**, from the live FEELESS chart / tape: early acceleration, first pullback, reclaim, breakout, momentum resumption. Reads a newborn chart as a newborn. | Demand a textbook setup or a long history. |
| ⚖ Devil | ADVERSARIAL THINKER | Asks "what could make us wrong?" and weighs each objection by severity. | Kill the trade. Objections are confidence deductions (strong ×0.85, others ×0.95, never below ×0.6). Only the hard wall is a no. |
| 🛡 Warden | RISK TRANSLATOR | Answers "how much can we risk here?" — strong but uncertain = smaller; excellent = the creator's cap. | Invent reasons to say no. Uncertainty rules only **shrink** (≥ ×0.5); only execution health and a seat too small for its own costs stop a buy. |
| 📮 Courier | EXECUTION TRUTH | Mechanically strict: route, price, slippage, fill, signature, duplicate-order protection, can it be bought **and** sold — through the one existing keeper path. | Have an opinion on narrative. |
| ☠ Reaper | POSITION MANAGER | Watches the **live** chart every 6 seconds: P/L velocity, peak, support, structure, liquidity, early-wallet exits, challengers. Lets accelerating runners run, protects when momentum stalls, exits when the thesis breaks. | Dump a winner because a clock expired, or babysit a dead loser. |
| 🗄 Archivist | MEMORY / EVIDENCE | Remembers what really happened: every round, source, entry reason, clue, P/L path, MFE / MAE, exit, outcome — wins and losses. | Turn a pattern into an instant hard restriction. |
| 👨‍⚖️ Judge | ACCOUNTABILITY / EVOLUTION | After a loss: bad selection, timing, size, hold, exit, execution, or normal variance? After a win: what worked? Adjusts **weights** through repeated evidence; a desk that keeps losing real money starts its next generation. | Add a hard veto after a bad trade. |

## The ranking

`open_score` = **newness × volume velocity × buyer velocity × live momentum × early wallets × the Judge's evidence weight × Devil's confidence**.
No holder, rug, creator, coin or source reputation part. No advantage for old history.

Newness: 0–5m ×1.5 · 5–15m ×1.35 · 15–60m ×1.2 · 1–3h ×1.0 · 3–6h ×0.8 · older = outside the universe.

## The live narrative

Built from THIS pass only: **HOT EARLY MOVE · BUILDING · BREAKOUT · RUNNING · STALLING · DISTRIBUTING · COLLAPSING**.
DISTRIBUTING and COLLAPSING are skipped at once; the desk moves to the next coin.

## The HARD WALL (the money boundary — the only things that can stop a trench buy)

- no live price · no trades in the last 5 minutes
- outside the universe: live cap inside the owner's MC band (default $12K–$300K, HQ › Agents › controls) and ≤ 6h old
- a pool the keeper cannot buy into
- market data invalid / malformed / a bot ladder
- the live chart collapsing or distributing · the dev dumping now
- no route back to SOL / a sell-back tax · a price far from market (the keeper's own checks)
- keeper halted · Courier reads BAD · office not live
- a seat too small for its own round-trip cost → reported as **SIZE TOO SMALL FOR COSTS**, not as a strategy failure

Everything else is curious, adaptive and evidence-weighted.
