use anchor_lang::prelude::*;

use crate::constants::MAX_POOLS;

/// One pool the vault allocates to. kind: 0 = v2 constant product, 1 = v3 concentrated liquidity.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default, InitSpace, PartialEq, Debug)]
pub struct PoolSlot {
    pub pool: Pubkey,
    pub kind: u8,
    pub weight_bps: u16,
    pub cap_bps: u16,
    pub range_bps: u16,
}

#[account]
#[derive(InitSpace)]
pub struct Vault {
    pub admin: Pubkey,
    pub keeper: Pubkey,
    pub fee_wallet: Pubkey,
    pub vault_id: u64,
    pub bump: u8,
    pub sol_bump: u8,
    pub pools: [PoolSlot; MAX_POOLS],
    pub pool_count: u8,
    pub mgmt_bps: u16,
    pub perf_bps: u16,
    pub total_shares: u64,
    /// High-water mark: NAV per share × PPS_SCALE after the last fee collection.
    pub hwm_pps: u128,
    pub last_fee_ts: i64,
    /// Lamport value of each deployed position, reported by the keeper (0 while nothing is deployed).
    pub position_values: [u64; MAX_POOLS],
    pub paused: bool,
}

#[account]
#[derive(InitSpace)]
pub struct Depositor {
    pub owner: Pubkey,
    pub vault: Pubkey,
    pub shares: u64,
    pub bump: u8,
}
