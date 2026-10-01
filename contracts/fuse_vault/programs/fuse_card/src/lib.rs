//! FUSE Card — one on-chain account per Fuse card. v0.1 (LOCALNET ONLY, not audited, not deployed):
//! custody of each leg's coins in card-owned token accounts, the card rules HARD-CODED (3 pools + 3 runners for traders,
//! 12 any mix for Cmd Ctr, profit levels, TP / SL ranges), owner-only toggles (auto TP, auto-compound, hold / swap,
//! per-coin TP / SL), owner can always withdraw, and a keeper that can ONLY return coins to the owner when the owner
//! turned automation on. On-chain selling / compounding needs swap adapters + price checks — next, behind an audit.
pub mod constants;
pub mod error;
pub mod instructions;
pub mod rules;
pub mod state;

use anchor_lang::prelude::*;

pub use constants::*;
pub use instructions::*;
pub use state::*;

declare_id!("GKE9e3M8shuD2nwTwchgP4BH22fiN6hyQrp4qwhkurpa");

#[program]
pub mod fuse_card {
    use super::*;

    pub fn init_config(ctx: Context<InitConfig>, keeper: Pubkey) -> Result<()> {
        instructions::init_config(ctx, keeper)
    }

    pub fn set_config(ctx: Context<SetConfig>, keeper: Pubkey, paused: bool) -> Result<()> {
        instructions::set_config(ctx, keeper, paused)
    }

    pub fn open_card(ctx: Context<OpenCard>, card_id: u64, legs: Vec<LegIn>, toggles: Toggles) -> Result<()> {
        instructions::open_card(ctx, card_id, legs, toggles)
    }

    pub fn set_toggles(ctx: Context<OwnerCard>, toggles: Toggles) -> Result<()> {
        instructions::set_toggles(ctx, toggles)
    }

    pub fn set_leg_limits(ctx: Context<OwnerCard>, idx: u8, tp_bps: u32, sl_bps: u16) -> Result<()> {
        instructions::set_leg_limits(ctx, idx, tp_bps, sl_bps)
    }

    pub fn deposit_leg(ctx: Context<MoveLeg>, idx: u8, amount: u64) -> Result<()> {
        instructions::deposit_leg(ctx, idx, amount)
    }

    pub fn withdraw_leg(ctx: Context<MoveLeg>, idx: u8, amount: u64) -> Result<()> {
        instructions::withdraw_leg(ctx, idx, amount)
    }

    pub fn keeper_return(ctx: Context<KeeperMove>, idx: u8, amount: u64, reason: u8) -> Result<()> {
        instructions::keeper_return(ctx, idx, amount, reason)
    }

    pub fn close_card(ctx: Context<CloseCard>) -> Result<()> {
        instructions::close_card(ctx)
    }
}
