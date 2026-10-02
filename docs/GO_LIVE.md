# FUSE — go live with real money

There are two tracks. **A** puts FEELESS's own tier cards on real money from your **Fuse Circle wallet**; the code is built and
runs on the local server. **B** makes *users'* cards hands-free on-chain (the FUSE Card contract). No Squads: the Fuse Circle
account is the one key for both.

## A · Tier cards on real money (Fuse Circle wallet) — local server

| # | Step | Where | Status |
|---|------|-------|--------|
| 1 | **Circle keys**: `CIRCLE_API_KEY` + `ENTITY_SECRET` in `backend/.env`, then `cd circle && npm install && node setup.mjs`. | terminal | done if HQ › Money › Circle lists wallets |
| 2 | **Turn on signing**: the keeper builds each swap from a Jupiter quote, checks your limits, and Circle signs it (Circle's sign-transaction API for SOL). **Not enabled in this release**: it needs your go-ahead before FEELESS can sign anything with your wallet. | you approve → dev adds it | 🔒 waiting on you |
| 3 | **Create the Fuse wallet**: HQ › Money › Circle → new **SOL** wallet named "Fuse" → send it SOL (cards + about 0.03 SOL kept back for network fees). | HQ | you |
| 4 | **Jupiter + RPC**: `JUPITER_API_KEY` (Swap API; falls back to lite-api) and a dedicated `HELIUS_RPC_URL` / `SOLANA_RPC_URL`. | `backend/.env` | check |
| 5 | **Pick + limit**: HQ › Fuse › 👛 Fuse wallet → pick the wallet, set max per card / per swap / daily, slippage, max impact. Then 🔍 **Dry run** a tier: real quotes, nothing signed. | HQ | ready now |
| 6 | **Arm + fund one tier small** ($20): the card RESETS as a new real run, the keeper buys its coins, and every swap shows on the card with its tx. | HQ | after step 2 |
| 7 | **Watch the audit trail**: every order (quote, fill, impact, network fee, tx). After 3 real fills, paper calibrates its impact + fees to match. | HQ › 👛 | automatic |
| 8 | **Scale**: raise the per-card cap, fund more tiers. ⏸ halts a card, ↩ sells it back to SOL (back to paper), the kill switch pauses everything. | HQ › 👛 | you |

Docs: Circle wallets https://developers.circle.com · Jupiter Swap API https://dev.jup.ag/docs · Solana fees https://solana.com/docs/core/fees

## B · Users' cards hands-free (FUSE Card contract)

Users still approve every card action with one tap. To make it truly sign-once (the card runs TP / SL / compound / payout to the
owner's wallet on its own, and FEELESS never holds their keys):

| # | Step | Who | Link |
|---|------|-----|------|
| 1 | **Swap adapter**: Raydium CPMM call inside `keeper_sell` / `keeper_buy` (reserve check, 3% slippage cap and balance diff are already there). | dev | https://github.com/raydium-io/raydium-cp-swap |
| 2 | **Price bound**: Pyth / Switchboard oracle on `minOut`, so nobody can push the pool to trigger a sell. | dev | https://docs.pyth.network/price-feeds/use-real-time-data/solana · https://docs.switchboard.xyz |
| 3 | **Devnet run**: deploy, run the 14 localnet tests against real pools, and let one card run for a week. | you + dev | https://solana.com/docs/core/clusters · https://faucet.solana.com |
| 4 | **External audit** of `fuse_card`. | auditor | https://osec.io · https://neodyme.io · https://www.sec3.dev · https://www.halborn.com |
| 5 | **Upgrade authority = a Fuse Circle wallet** (instead of Squads): `solana program set-upgrade-authority <PROGRAM_ID> --new-upgrade-authority <CIRCLE_ADDR>`. Use a **separate** Circle wallet from the trading one, and keep its API key off the server. | you | https://solana.com/docs/programs/deploying |
| 6 | **Mainnet with small caps** ($100 per card), raised as it proves out. | you | https://www.anchor-lang.com/docs |
| 7 | **Keeper host**: an always-on host for the engine loops + keeper. | you | https://railway.app |
| 8 | **Launch hygiene**: `ALLOWED_ORIGINS` = the real domain, re-check fees (HQ › Fuse › 💲 Fees), unpause the season. | you | HQ › Security |

HQ › Fuse › ⛓ Contract tracks B 1–5 (owner only, proof required). A user card goes hands-free only when every step is ✅.
