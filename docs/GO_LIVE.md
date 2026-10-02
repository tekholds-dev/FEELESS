# FUSE cards — go live with real money (auto swap · compound · payout to your wallet)

Today every card action is a one-tap alert the holder approves. Each card's 🤖 Auto spec (its DNA: cycle, compound, payout %,
clock, stop) is exactly what the **FUSE Card program** (`contracts/fuse_vault/programs/fuse_card`) will run on its own once the
holder signs. Payouts go straight to the holder's wallet with no click, and FEELESS never holds anyone's keys. To get there:

| # | Step | Who | Link |
|---|------|-----|------|
| 1 | **Swap adapter**: add the Raydium CPMM swap call to `keeper_sell` / `keeper_buy`. The program already checks pool reserves, a 3% max slippage and the balance difference. | dev | Raydium CP-Swap program: https://github.com/raydium-io/raydium-cp-swap |
| 2 | **Price check (TWAP / oracle)**: bound `minOut` by an oracle price so nobody can move the pool and trigger a sell. | dev | Pyth on Solana: https://docs.pyth.network/price-feeds/use-real-time-data/solana · Switchboard: https://docs.switchboard.xyz |
| 3 | **Devnet run**: deploy to devnet, run the 14 localnet tests against real pools, and let one card run TP / SL / compound / payout for a week. | you + dev | Devnet guide: https://solana.com/docs/core/clusters · faucet: https://faucet.solana.com |
| 4 | **External audit** of `fuse_card` (math, keeper limits, owner-only withdraw). | auditor | OtterSec https://osec.io · Neodyme https://neodyme.io · Sec3 https://www.sec3.dev · Halborn https://www.halborn.com |
| 5 | **Multisig upgrade authority**, so no single key can change the program. | you | Squads: https://squads.so |
| 6 | **Mainnet with small caps**: set a per-card cap (e.g. $100), then raise it as it proves out. | you | Anchor deploy: https://www.anchor-lang.com/docs |
| 7 | **Keeper host**: the always-on job that sends `keeper_sell` / `keeper_buy` / payout when a card's rule hits. | you | Railway: https://railway.app (the engines already run as loops; move them there) |
| 8 | **Launch hygiene**: set `ALLOWED_ORIGINS` to the real domain, re-check the swap fee, unpause the season. | you | HQ › Security · HQ › Fees |

HQ › Fuse › ⛓ Contract tracks steps 1–5 (the go-live checklist; owner only, proof required). A card only goes hands-free
when every step shows ✅. Until then, alerts stay one tap.
