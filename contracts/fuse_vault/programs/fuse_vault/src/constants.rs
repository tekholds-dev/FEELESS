use anchor_lang::prelude::*;

#[constant]
pub const VAULT_SEED: &[u8] = b"vault";
#[constant]
pub const VAULT_SOL_SEED: &[u8] = b"vault_sol";
#[constant]
pub const DEPOSITOR_SEED: &[u8] = b"depositor";

pub const MAX_POOLS: usize = 3;
/// Hard caps enforced on-chain (mirrors backend VAULT_MAX_*_BPS): ≤3%/yr management, ≤30% performance.
pub const MAX_MGMT_BPS: u16 = 300;
pub const MAX_PERF_BPS: u16 = 3000;
/// Per-pool cap of that pool's TVL, in bps (≤10%).
pub const MAX_CAP_BPS: u16 = 1000;
pub const PPS_SCALE: u128 = 1_000_000_000_000;
pub const YEAR_SECONDS: u128 = 365 * 86_400;
