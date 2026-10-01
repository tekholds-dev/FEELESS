use anchor_lang::prelude::*;

use crate::constants::MAX_LEGS;

/// Program-wide config: who the admin (Cmd Ctr) and the keeper are, and the keeper pause switch.
#[account]
#[derive(InitSpace)]
pub struct Config {
    pub admin: Pubkey,
    pub keeper: Pubkey,
    pub paused: bool,
    pub bump: u8,
}

/// One coin / pool on a card. `held` = tokens the card account holds for it right now.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default, InitSpace, PartialEq, Debug)]
pub struct Leg {
    pub mint: Pubkey,
    pub kind: u8,
    pub tp_bps: u32,
    pub sl_bps: u16,
    pub held: u64,
}

/// The owner's switches — only the owner can change them.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default, InitSpace, PartialEq, Debug)]
pub struct Toggles {
    pub auto_tp: bool,
    pub auto_compound: bool,
    pub swap_mode: bool,
    pub profit_at_bps: u32,
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
}
