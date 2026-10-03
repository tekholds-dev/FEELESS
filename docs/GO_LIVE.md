# FUSE — go live with real money

There are two tracks. **A** puts FEELESS's own tier cards on real money from your **Fuse Circle wallet**; the code is built and
runs on the local server. **B** makes *users'* cards hands-free on-chain (the FUSE Card contract). No Squads: the Fuse Circle
account is the one key for both.

## A · Tier cards on real money (Fuse Circle wallet) — local server

| # | Step | Where | Status |
|---|------|-------|--------|
| 1 | **Circle keys**: `CIRCLE_API_KEY` + `ENTITY_SECRET` in `backend/.env`, then `cd circle && npm install && node setup.mjs`. | terminal | done if HQ › Money › Circle lists wallets |
| 2 | **Signing**: the keeper builds each swap from a Jupiter quote, checks your limits, Circle signs it (sign only), FEELESS broadcasts and books the confirmed fill. | built | ✅ on (you approved) |
| 3 | **Create the Fuse wallet**: HQ › Money › Circle → new **SOL** wallet named "Fuse" → send it SOL (cards + about 0.03 SOL kept back for network fees). | HQ | you |
| 4 | **Jupiter + RPC**: `JUPITER_API_KEY` (Swap API; falls back to lite-api) and a dedicated `HELIUS_RPC_URL` / `SOLANA_RPC_URL`. | `backend/.env` | check |
| 5 | **Pick + limit**: HQ › Fuse › 👛 Fuse wallet → pick the wallet, set max per card / per swap / daily, slippage, max impact. Then 🔍 **Dry run** a tier: real quotes, nothing signed. | HQ | ready now |
| 6 | **Arm + fund one tier small** ($20): the SAME card goes real — same coins, phase, clock and config, time + P&L start over; the keeper buys its coins and every swap shows on the card with its tx + an inbox notice. | HQ | you |
| 7 | **Watch the audit trail**: every order (quote, fill, impact, network fee, tx). After 3 real fills, paper calibrates its impact + fees to match. | HQ › 👛 | automatic |
| 8 | **Scale**: raise the per-card cap, fund more tiers. ⏸ halts a card, ↩ sells it back to SOL (back to paper), the kill switch pauses everything. | HQ › 👛 | you |

Docs: Circle wallets https://developers.circle.com · Jupiter Swap API https://dev.jup.ag/docs · Solana fees https://solana.com/docs/core/fees

## B · Users' cards hands-free (FUSE Card contract)

Users still approve every card action with one tap. To make it truly sign-once (the card runs TP / SL / compound / payout to the
owner's wallet on its own, and FEELESS never holds their keys):

| # | Step | Who | Link |
|---|------|-----|------|
| 1 | **Swap adapter**: Raydium CP-Swap `keeper_sell_cpmm` / `keeper_buy_cpmm` — ✅ built + tested against the REAL Raydium program on localnet (contracts README v0.3). | dev ✅ | https://github.com/raydium-io/raydium-cp-swap |
| 2 | **Price bound**: ✅ Raydium's own on-chain TWAP (≥5 min, spot within ±10%, triggers read the TWAP) — a one-block push can't fire a sell (tested). Pyth / Switchboard optional on top. | dev ✅ | https://docs.pyth.network |
| 3 | **Devnet run**: ✅ deployed `GKE9e3M8shuD2nwTwchgP4BH22fiN6hyQrp4qwhkurpa` (plain build) + config → Raydium devnet `DRaycpLY…` (config `36k9tXVE…`, `migrations/devnet-init.ts`). Next: one card on a devnet Raydium pool for a week (needs the keeper host, B·7). Devnet SOL: Alchemy devnet `requestAirdrop` works (no GitHub needed). | dev ✅ / you | https://solana.com/docs/core/clusters · https://faucet.solana.com |
| 4 | **External audit** of `fuse_card`. | auditor | https://osec.io · https://neodyme.io · https://www.sec3.dev · https://www.halborn.com |
| 5 | **Upgrade authority = a Fuse Circle wallet** (instead of Squads): `solana program set-upgrade-authority <PROGRAM_ID> --new-upgrade-authority <CIRCLE_ADDR>`. Use a **separate** Circle wallet from the trading one, and keep its API key off the server. | you | https://solana.com/docs/programs/deploying |
| 6 | **Mainnet with small caps** ($100 per card), raised as it proves out. | you | https://www.anchor-lang.com/docs |
| 7 | **Keeper host**: an always-on host for the engine loops + keeper. | you | https://railway.app |
| 8 | **Launch hygiene**: `ALLOWED_ORIGINS` = the real domain, re-check fees (HQ › Fuse › 💲 Fees), unpause the season. | you | HQ › Security |

HQ › Fuse › ⛓ Contract tracks B 1–5 (owner only, proof required). A user card goes hands-free only when every step is ✅.

### Is it a real contract or a wallet full of coins?
- **Track A (now):** the tier cards are coins in your Fuse Circle wallet, traded by the FEELESS keeper under server-enforced limits. Every
  trade is on-chain and audited in HQ, but the RULES live on the server.
- **Track B (the FUSE Card program):** the rules are in the contract — the card account holds the coins, only the owner withdraws, the keeper
  can only sell on an on-chain trigger (Raydium TWAP), only through Raydium, with capped slippage, paying only the owner. HQ tier cards can
  move into it (HQ cards = up to 12 legs) once B·3–B·5 are done. Until the audit, it is localnet / devnet only.
