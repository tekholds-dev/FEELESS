# FUSE Vault (Solana program)

One contract, up to **3 yield pools** (v2 constant-product and/or v3 concentrated liquidity). Users deposit SOL and get
vault shares; the vault spreads SOL across the pools by auto-scaled weights with per-pool caps; management +
performance fees are paid **in SOL to the FEELESS vault fee wallet** (HQ › Trading & fees).

The math is specified and tested first in `backend/fuse_vault.py` (Python) and mirrored in `programs/fuse_vault/src/math.rs`.
Change both together.

## Status — v0.1 (localnet only, NOT deployed, NOT audited)

| Piece | State |
|---|---|
| Custody: SOL in the `vault_sol` PDA (no private key; only program rules move it) | ✅ |
| Deposit → shares at NAV (no dilution), withdraw at NAV (from the idle buffer) | ✅ |
| Fees: management by time + performance above a high-water mark, only to the configured fee wallet | ✅ |
| Admin-only config (≤3 pools, fee caps 3%/yr + 30% enforced on-chain), pause (stops deposits, never exits) | ✅ |
| Pool adapters: add/remove liquidity in Raydium CPMM/CLMM, Orca Whirlpool, Meteora DLMM | ⏳ next |
| Position valuation tied to what was actually deployed (no free-form "report a value") | ⏳ with adapters |
| Rebalance / v3 recenter crank (rules already in `fuse_vault.py`) | ⏳ with adapters |
| Independent security audit | ⏳ before mainnet |

v0.1 deliberately has **no** instruction to set position values: until adapters exist, NAV is exactly the SOL held,
so a compromised keeper key cannot inflate NAV and drain withdrawals.

## Test (local validator only — never mainnet)

```bash
. "$HOME/.cargo/env"; export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"
cargo test -p fuse_vault --lib                     # math mirrors the Python engine
solana-test-validator --reset --quiet &            # Anchor 1.2 defaults to surfpool; we use the stock validator
anchor test --skip-local-validator --provider.cluster localnet
```

## Before mainnet (owner decisions)

1. Pool adapters + valuation, then a devnet run with real pool programs.
2. External audit.
3. Deploy with the owner's keys; set the upgrade authority to a multisig; set the vault fee wallet in HQ.


# FUSE Card (`programs/fuse_card`) — v0.1, localnet only

One on-chain account per Fuse card (PDA `["card", owner, card_id]`). Each leg's coins sit in a token account owned by the
card PDA. Rules are hard-coded in `constants.rs` (mirror `backend/fuse_hq.py` / `runners.py`):

| Rule | Value |
|---|---|
| Trader card | ≤ 3 pools + ≤ 3 runners |
| HQ card (config admin) | ≤ 12 legs, any mix |
| Auto-profit levels | +25 / +50 / +100 / +200 % (or off) |
| Per-coin TP / SL | +5…+1000 % / −5…−95 % (or off) |

| Who | Can |
|---|---|
| Owner | open, set toggles (auto TP, auto-compound, hold/swap, profit level) and per-coin TP/SL, deposit, **withdraw any time**, close when empty |
| Keeper | `keeper_return` ONLY: send a leg's coins back to the **owner's own token account**, only when the owner switched automation on (TP / SL / profit / compound), never while paused |
| Admin | set keeper, pause the keeper (owners can still withdraw) |

v0.1 can't sell on-chain: auto TP and auto-compound return the coins to the owner's wallet as a standing order (no click each time).
Selling / re-buying in-program needs swap adapters + price checks — next, then an audit, then the owner's keys.

```bash
cargo test -p fuse_card --lib            # hard-coded rules + keeper fence
anchor build -p fuse_card                # target/deploy/fuse_card.so + IDL
solana-test-validator --reset --quiet &  # then:
anchor test --skip-local-validator --provider.cluster localnet   # tests/fuse_card.ts (5) + tests/fuse_vault.ts (5)
```

`tests/fuse_card.ts` (hand-built SPL Token instructions, no extra deps) proves: config admin-only; trader caps 3+3, no duplicate
coins, bad profit level refused, HQ 12 legs (13 refused); deposit/withdraw only through the card PDA's own token account and
only back to the owner's account (wrong mint / someone else's account / over-withdraw refused); keeper refused when auto is off,
when it isn't the configured keeper, when sending anywhere but the owner, with a bad reason, and while paused — while the owner
can still withdraw; auto-compound works as a standing order; only an empty card closes and every token comes home.

## Next: on-chain selling (DESIGN — not built, audit before any deploy)

Goal: auto TP / SL / profit / compound **sell inside the program** instead of only returning coins.

1. **Card cash vaults.** Each card gets a wSOL (and optional USDC) token account owned by the card PDA. Sells land there; the
   owner withdraws them like any leg (same owner-only destination rule).
2. **One whitelisted router.** `keeper_sell(idx, amount, min_out, route_ix_data)` CPIs **only** into Jupiter v6
   (hard-coded program id) with the card PDA as the swap authority. Input = the leg's card vault (mint = leg.mint),
   output = the card's wSOL vault. Any other program id, input or output account → reject.
3. **Price checks (memecoins have no oracle).** Before the CPI the program reads the leg's pool state directly
   (PumpSwap / Raydium CPMM reserves; Pump.fun curve state for pre-bond) and computes the expected out for `amount`;
   require `min_out ≥ expected × (1 − 1%)`. After the CPI, require the wSOL vault grew by **≥ min_out** (balance diff, not the
   route's word). Majors (SOL/USDC legs) may use a Pyth price as a second check.
4. **Triggers on-chain.** `deposit_leg` stores the entry price (pool price at deposit). `keeper_sell` re-derives the
   current pool price and only proceeds if the owner's rule holds: TP (`price ≥ entry × (1 + tp_bps)`), SL, card profit level,
   or compound — and only with the owner's toggle on. Amount ≤ held; a TP ladder sells only its slice.
5. **Compound** = sell the gain to wSOL, then `keeper_buy` the other legs by the card's stored weights through the same
   router + checks (min_out from pool reserves). Still owner-toggled; still owner-withdrawable at any time.
6. Then: devnet run against real PumpSwap / Raydium pools → external audit → deploy with the owner's keys + multisig upgrade
   authority. Until then the website keeps one-tap alerts (FEELESS never signs for users).


## FUSE Card v0.2 — keeper trades (LOCALNET ONLY · not audited · not deployed)
What a card owner signs once (open_card + toggles): per-coin TP / SL, auto on/off, auto-compound, and the stop mode
(`sl_mode`: 0 pay out · 1 park & rebuy at entry · 2 hold). After that the keeper runs it — no click per trade — inside these fences:
1. Only the configured keeper key, never while paused, only automations the owner switched on (`rules::keeper_allowed`).
2. Only through `config.swap_program` (one whitelisted program) and only the pool whose mints = the leg's coin + the card's quote.
3. The TRIGGER is checked on-chain from that pool's reserves vs the owner's own entry (`hit_up` / `hit_down` / `back_at_entry`).
4. `min_out` ≥ pool's expected output − slippage (config ≤ 3% hard cap) and the card's balance must really grow by ≥ min_out.
5. Proceeds go to the owner's own wallet (TP / profit / payout stops), stay parked on the leg (park mode) or stay as card cash
   that may only be bought back into coins ALREADY on the card (compound). The owner can always withdraw coins, parked SOL, cash.

Tests: `cargo test -p fuse_card --lib` (6) · `solana-test-validator --reset` then `anchor test --skip-local-validator
--provider.cluster localnet` (14: card 5 + keeper trading 4 against `programs/mock_amm` + vault 5).

### Before any real money (owner + auditor)
- **Adapter**: replace `mock_amm` with an audited adapter per venue (Raydium CPMM first: same constant-product math). Pin its
  program id in config; each adapter must expose the same pool layout (mints + vaults) the price check reads.
- **Price manipulation**: spot reserves can be pushed inside one transaction. Mainnet needs a TWAP / oracle bound (e.g. the pool's
  observation account or Pyth for majors) next to the spot check, and the keeper key in an HSM.
- Devnet run with real pools → external audit → owner deploys with a multisig upgrade authority and small per-card caps.

## v0.3 — real venue: Raydium CP-Swap adapter (LOCALNET-TESTED, not audited, not deployed)

`programs/fuse_card/src/raydium.rs` + instructions `keeper_sell_cpmm` / `keeper_buy_cpmm`:
- swaps through Raydium CP-Swap `swap_base_input` signed by the card PDA; `config.swap_program` = the Raydium CPMM id
  (mainnet `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`, devnet `DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb`);
- pool, AMM config and observation accounts must be owned by Raydium and match the pool; reserves = vault − protocol/fund/creator fees;
- **price bound = Raydium's own on-chain TWAP** (observation ring, ≥300s): spot must be within ±10% of it and the TP / SL / re-buy
  trigger reads the TWAP, so a one-block pool push can't fire anything. TWAP error ≤ 15s / window (Raydium accumulates in place < 15s);
- min_out ≥ expected output with the pool's REAL fee tier (trade + creator fee, rounded up) − the capped slippage; balance-diff check;
- Token-2022 coins are refused in v0.3.

Rust unit tests (10): `cargo test -p fuse_card --lib` (incl. a replay of Raydium's observation updates for busy and sparse pools).

### Raydium integration test (real Raydium program on a local validator)
```
git clone --depth 1 https://github.com/raydium-io/raydium-cp-swap /tmp/raydium-cp-swap
cd /tmp/raydium-cp-swap && CPSWAP_LOCALNET_ADMIN=$(solana-keygen pubkey ~/.config/solana/id.json) cargo build-sbf --manifest-path programs/cp-swap/Cargo.toml --features localnet
cd <repo>/contracts/fuse_vault && anchor build -p fuse_card -- --features fast-twap      # 90s TWAP window, TEST BUILD ONLY
solana-test-validator --reset --bpf-program CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C /tmp/raydium-cp-swap/target/deploy/raydium_cp_swap.so \
  --clone DNXgeM9EiiaAbaWvwjHj9fQQLAX5ZsfHyvmYUNRAdNC8 --url https://api.mainnet-beta.solana.com
anchor test --skip-local-validator --skip-build --provider.cluster localnet
```
`tests/fuse_card_raydium.ts` (4): no TWAP history → refused · a one-block +55% pump → refused · after the price held, the TP sells
through Raydium and pays the owner ≥ min_out · wrong program / vault / oracle / payout account → refused.
**Never deploy a `fast-twap` build.** A deploy build is plain `anchor build -p fuse_card`.
