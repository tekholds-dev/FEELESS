# 💵 Real-money cats — the full user process (design, NOT built)

> Planning status and remaining requests: [WORK_QUEUE.md](WORK_QUEUE.md). This file retains the technical specification/history; do not maintain a second active backlog here.

Owner ask (2026-10-21): "Build a Cat needs to show the models, the whole shabang — no paper, real money, and creator-wallet access in HQ
for how much I charge per …". Every step below must exist before any of it ships (one and done). Today every cat is PAPER.

## The decision that blocks everything (owner)
Who holds a real cat's money?
- **A. The user's own wallet signs each trade** — non-custodial, legal-light, but the cat is not autonomous: every buy / sell is a wallet
  prompt (FEELESS can pre-build and alert, like Fuse one-tap cards).
- **B. A per-user wallet FEELESS controls (Circle / keeper)** — autonomous, but FEELESS holds user funds = custody (licensing, security,
  audits). Breaks the standing rule "never hold user keys".
- **C. An on-chain cat program (like the FUSE Card program)** — the cat's funds sit in a program account only the user can withdraw; a keeper
  may only trade inside the user's signed limits. Autonomous AND non-custodial, but needs the program, an audit and a devnet run first.

## The process (whichever option)
1. **Pick brains** — the whole OpenRouter list (`/api/cats/models`): price per decision, memory, intelligence, categories; up to 2 brains + how
   they work together (turns · discuss · together · battle).
2. **Identity** — name, handle, coat, look (same fields as Create a Cat — `CatFields`).
3. **Risk** — balance, max position, daily buy limit, daily loss limit, the one-time brief.
4. **Pricing shown before funding** — the creator's fee (HQ › Fees › Cats: $ per decision markup, % of profit, flat launch fee), the model
   cost per decision, network fees. Example $ for this setup.
5. **Fund** — the user's signed SOL transfer (A: none, B: to their cat wallet, C: into the program account).
6. **Live** — decisions on the wall, every trade with its tx, P&L price-only, fees apart, the brain's words.
7. **Controls** — pause, chime in (advice), pull all funds (sell everything → back to the user's wallet), top up, change limits.
8. **Billing** — model + creator fees settled from profit or pay-as-you-go, every charge on a receipt; nothing charged on a losing day
   beyond the model's real cost (owner decides).
9. **Exit** — withdraw anytime to the user's own wallet; receipts + record stay on the profile.
10. **HQ** — creator sees every live cat, revenue per cat, fee settings, kill switch per cat, the audit trail.

## What must be proven first
Edge: no cat strategy has a positive record on unseen coins yet (`scripts/edge-audit.py`). Real money for users needs a record, an audit
(C) or a legal read (B), and the owner's go.
