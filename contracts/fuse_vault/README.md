# FUSE Vault (Solana program)

One contract, up to **3 yield pools** (v2 constant-product and/or v3 concentrated liquidity). Users deposit SOL and get
vault shares; the vault spreads SOL across the pools by auto-scaled weights with per-pool caps; management +
performance fees are paid **in SOL to the FEELESS vault fee wallet** (Command Center › Trading & fees).

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
3. Deploy with the owner's keys; set the upgrade authority to a multisig; set the vault fee wallet in Command Center.
