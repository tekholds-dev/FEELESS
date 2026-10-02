use anchor_lang::prelude::*;

use crate::constants::MAX_LEGS;

/// Program-wide config: who the admin (HQ) and the keeper are, and the keeper pause switch.
#[account]
#[derive(InitSpace)]
pub struct Config {
    pub admin: Pubkey,
    pub keeper: Pubkey,
    pub paused: bool,
    pub bump: u8,
    /// v0.2: the ONLY swap program the keeper may route through (an audited adapter on mainnet; the mock AMM on localnet).
    pub swap_program: Pubkey,
    /// Max slippage vs the pool's own expected output (≤ MAX_SLIPPAGE_BPS).
    pub max_slippage_bps: u16,
}

/// One coin / pool on a card. `held` = tokens the card account holds for it right now.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default, InitSpace, PartialEq, Debug)]
pub struct Leg {
    pub mint: Pubkey,
    pub kind: u8,
    pub tp_bps: u32,
    pub sl_bps: u16,
    pub held: u64,
    /// Entry price as a ratio: quote atoms paid (entry_quote) for coin atoms (entry_coin). Set by the OWNER on deposit.
    pub entry_quote: u64,
    pub entry_coin: u64,
    /// Quote atoms parked after a stop in park mode (bought back at entry, or withdrawn by the owner any time).
    pub parked: u64,
}

/// The owner's switches — only the owner can change them.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default, InitSpace, PartialEq, Debug)]
pub struct Toggles {
    pub auto_tp: bool,
    pub auto_compound: bool,
    pub swap_mode: bool,
    pub profit_at_bps: u32,
    /// SL_PAYOUT / SL_PARK / SL_HOLD.
    pub sl_mode: u8,
}

#[account]
#[derive(InitSpace)]
pub struct Card {
    pub owner: Pubkey,
    pub card_id: u64,
    pub bump: u8,
    pub admin_card: bool,
    pub legs: [Leg; MAX_LEGS],
    pub leg_count: u8,
    pub toggles: Toggles,
    pub opened_ts: i64,
    /// v0.2: the quote coin (wSOL) every sell pays into; `cash` = quote atoms held for compounding.
    pub quote_mint: Pubkey,
    pub cash: u64,
}
