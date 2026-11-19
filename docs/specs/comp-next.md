# COMP — how to teach it next (notes, owner 2026-11-14: "put those new ways in new notes")

Ideas, not cards: nothing here is built until the owner picks one. Best first.

## Where COMP stands (2026-11-14 exam race, 28 held-out proofs)
COMP + memory 68% · COMP 64% · base 9B 54% · always-guess 54% · OSSY 50% · G4 43%.
COMP was trained ONCE (2026-11-12, 99 rows, 200 iters); every race since used that same adapter, so it has not improved since. With 28 questions, one answer = ~4 points: small moves are noise.

## Slice 7 rules (2026-11-19): real, judged proofs only; ships only if it beats the base
- **What COMP learns from** (`backend/comp_real.py`): one row per real proof an agent filed, with its pass / fail from what really happened:
  PoW/PoP P&L, PoB scoreboard / Polymarket / Kalshi (or the owner's mark on a topic-only ask), PoC reach at 7 d or the owner's mark, PoStatic
  the owner's mark, plus the owner's Model Lab grades. Each row keeps `settledBy` + `proofOf` (the facts that settled it). The judges' grades
  are NEVER a label (they sit the exam). TEST proofs, open / flat ones, per-site index rows, repeats, market snapshots, teacher lessons and
  Kalshi lessons are dropped and counted by reason (`dataset.json › dropped`, shown in COMP › THE GATE).
- **What COMP reads:** what the proof said and DID before it settled (calls + reasons, bid + legs, the coin at entry, the build plan).
  Never the exit, P&L, final score, a PoW's `why` (the watcher's sell reason), reviews or owner notes.
- **The old 64% was not honest:** the old export kept one row per site a proof read (`…:src:<site>` index rows), so the same proof sat in
  training AND the exam, and a PoW's sell reason was in its question. The pre-Slice-7 files are kept in `backend/data/comp_v2/pre_slice7/`.
- **Exam seats are fixed by a hash of the proof id** (25% exam, 10% tune): an examined proof never trains a later COMP.
- **Ship rule** (`comp_v2.ship`): COMP (no memory) must get strictly more held-out proofs right than the base 9B, and no fewer than
  always-guess. Else it is NOT shipped, the exam says why, and the last shipped COMP (`shipped/`) stays. The exam runs `--free` from Claude.

## The ways (best first)
1. **Retrain on the internet learner's rows** — 546 settled DexScreener market rows (live snapshot → real result an hour later) that COMP never trained on, vs the 99 it learned from. Free, on this Mac, same MLX LoRA recipe (COMP v2 tab › Train). Biggest win for the least work.
2. **Reward training (GRPO, verifiable rewards)** — COMP answers, the settled result scores it (right = reward), it learns from the score. Fits FEELESS because proofs settle themselves. Tools: `mlx-lm-lora` (Mac), TRL / Unsloth (rented GPU, owner approves spend).
3. **Preference training (DPO / ORPO)** — on the right-vs-wrong pairs (48 today) and the owner's 👍/👎 duel picks. Wants ~200 pairs per proof type before it pays.
4. **Teacher lessons (distillation)** — a top model (Claude) writes the reasoning for proofs that already settled; COMP learns the reasoning, not just the answer. The "Teacher lessons" source in Build your model is 0 today. Needs a key + a small spend the owner approves.
5. **A bigger exam** — grow past 28 held-out questions (add market rows + new PoB/PoC results) so a score change is real, not noise.

## Already in place (don't rebuild)
Memory/recall over the stash (the "+ memory" line), the race history (`exam_history.jsonl`), OSSY + G4 in the race with thinking off, the dataset export (Data & grades › Export), the tooling shortlist (Data & grades).

## Owner's proof tests that feed COMP (2026-11-14) — every settled one is a new training + exam row
- **PoB · real Kalshi bid** (Bids app › Real money · USA → the Kalshi door, `kalshi_bid.py`): key saved in the agent's Keys, door ON, mode **Approve each**, $1 a bid, $3 a day, floor $2, min confidence 65. Ask a topic PoB ("NBA games tonight"); a ticket appears only when BOTH minds pick the same market + side → check the limit price vs Kalshi → tap. Settles on Kalshi's result; the proof's stamp follows it.
- **PoB · free chips first** (same ask, door OFF): the bid goes on the FEELESS board with free chips; compare its stamp with the real one.
- **PoC · content** (desk ask: "write the launch post for X"; or a PoC watch on up to 8 sites): no money. Proves itself by your mark (right / wrong) + the 24 h stamp; check the references it cites are real.
