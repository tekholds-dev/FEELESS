//! FUSE Vault — one contract, up to 3 yield pools (v2 constant-product / v3 concentrated), SOL in → shares out,
//! management + performance fees in SOL to the FEELESS fee wallet. v0.1: custody, shares, fees, admin controls.
//! Pool adapters (Raydium CPMM/CLMM, Orca Whirlpool, Meteora DLMM) come next, behind an audit.
pub mod constants;
pub mod error;
pub mod instructions;
pub mod math;
pub mod state;

use anchor_lang::prelude::*;

pub use constants::*;
pub use instructions::*;
pub use state::*;

declare_id!("yFFn2Z5Rc1vRYQWNQabtc3qLgnKwscx7rzPv4EL4rzb");

#[program]
pub mod fuse_vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, vault_id: u64, cfg: VaultConfig) -> Result<()> {
        instructions::initialize(ctx, vault_id, cfg)
    }

    pub fn configure(ctx: Context<AdminOnly>, cfg: VaultConfig) -> Result<()> {
        instructions::configure(ctx, cfg)
    }

    pub fn set_paused(ctx: Context<AdminOnly>, paused: bool) -> Result<()> {
        instructions::set_paused(ctx, paused)
    }

    pub fn deposit(ctx: Context<Deposit>, lamports: u64) -> Result<()> {
        instructions::deposit(ctx, lamports)
    }

    pub fn withdraw(ctx: Context<Withdraw>, shares: u64) -> Result<()> {
        instructions::withdraw(ctx, shares)
    }

    pub fn collect_fees(ctx: Context<CollectFees>) -> Result<()> {
        instructions::collect_fees(ctx)
    }
}
