//! FUSE Card — one on-chain account per Fuse card. v0.1 (LOCALNET ONLY, not audited, not deployed):
//! custody of each leg's coins in card-owned token accounts, the card rules HARD-CODED (3 pools + 3 runners for traders,
//! 12 any mix for Cmd Ctr, profit levels, TP / SL ranges), owner-only toggles (auto TP, auto-compound, hold / swap,
//! per-coin TP / SL), owner can always withdraw, and a keeper that can ONLY return coins to the owner when the owner
//! turned automation on. v0.2: the keeper SELLS / BUYS through ONE whitelisted swap program, only when the owner's trigger
//! is hit on-chain (pool reserves vs the owner's entry), with min_out bounded by the pool price − capped slippage and a
//! balance-diff check; stop modes pay out / park / hold. Mainnet needs an audited adapter + a manipulation-resistant
//! price (TWAP / oracle) — see the README.
pub mod constants;
pub mod error;
pub mod instructions;
pub mod keeper;
pub mod rules;
pub mod state;

use anchor_lang::prelude::*;

pub use constants::*;
pub use instructions::*;
pub use keeper::*;
pub use state::*;

declare_id!("GKE9e3M8shuD2nwTwchgP4BH22fiN6hyQrp4qwhkurpa");

#[program]
pub mod fuse_card {
    use super::*;

    pub fn init_config(ctx: Context<InitConfig>, keeper: Pubkey, swap_program: Pubkey, max_slippage_bps: u16) -> Result<()> {
        instructions::init_config(ctx, keeper, swap_program, max_slippage_bps)
    }

    pub fn set_config(ctx: Context<SetConfig>, keeper: Pubkey, paused: bool, swap_program: Pubkey, max_slippage_bps: u16) -> Result<()> {
        instructions::set_config(ctx, keeper, paused, swap_program, max_slippage_bps)
    }

    pub fn open_card(ctx: Context<OpenCard>, card_id: u64, legs: Vec<LegIn>, toggles: Toggles, quote_mint: Pubkey) -> Result<()> {
        instructions::open_card(ctx, card_id, legs, toggles, quote_mint)
    }

    pub fn set_toggles(ctx: Context<OwnerCard>, toggles: Toggles) -> Result<()> {
        instructions::set_toggles(ctx, toggles)
    }

    pub fn set_leg_limits(ctx: Context<OwnerCard>, idx: u8, tp_bps: u32, sl_bps: u16) -> Result<()> {
        instructions::set_leg_limits(ctx, idx, tp_bps, sl_bps)
    }

    pub fn deposit_leg(ctx: Context<MoveLeg>, idx: u8, amount: u64, cost_quote: u64) -> Result<()> {
        instructions::deposit_leg(ctx, idx, amount, cost_quote)
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

    /// v0.2 keeper: SELL a leg through the whitelisted swap program — only when the owner's trigger is hit ON-CHAIN.
    pub fn keeper_sell<'info>(ctx: Context<'info, KeeperSwap<'info>>, idx: u8, amount: u64, min_out: u64, reason: u8) -> Result<()> {
        keeper::keeper_sell(ctx, idx, amount, min_out, reason)
    }

    /// v0.2 keeper: BUY back a parked leg (price back at entry) or compound card cash into a leg already on the card.
    pub fn keeper_buy<'info>(ctx: Context<'info, KeeperSwap<'info>>, idx: u8, amount_in: u64, min_out: u64, reason: u8) -> Result<()> {
        keeper::keeper_buy(ctx, idx, amount_in, min_out, reason)
    }

    /// The owner can always take parked SOL (idx) or compound cash (idx 255) back to their wallet.
    pub fn withdraw_quote(ctx: Context<OwnerQuote>, idx: u8, amount: u64) -> Result<()> {
        keeper::withdraw_quote(ctx, idx, amount)
    }
}
