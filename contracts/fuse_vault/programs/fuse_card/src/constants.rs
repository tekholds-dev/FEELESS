//! FUSE Card rules — HARD-CODED in the program (mirror backend fuse_hq / runners; change both together).
use anchor_lang::prelude::*;
use anchor_lang::solana_program::pubkey::pubkey;

#[constant]
pub const CONFIG_SEED: &[u8] = b"config";
#[constant]
pub const CARD_SEED: &[u8] = b"card";

/// Cmd Ctr (config admin) cards: up to 12 legs in any mix of pools + runners.
pub const MAX_LEGS: usize = 12;
/// Trader cards: up to 3 pools + 3 runners (fuse_hq.CARD_POOLS / CARD_RUNNERS).
pub const USER_MAX_POOLS: u8 = 3;
pub const USER_MAX_RUNNERS: u8 = 3;
/// Auto-profit levels a card may pick (+25 / +50 / +100 / +200 %), in bps. 0 = off.
pub const PROFIT_LEVELS_BPS: [u32; 4] = [2_500, 5_000, 10_000, 20_000];
/// Per-coin take-profit +5 % … +1000 %, stop-loss −5 % … −95 % (bps). 0 = off.
pub const TP_MIN_BPS: u32 = 500;
pub const TP_MAX_BPS: u32 = 100_000;
pub const SL_MIN_BPS: u16 = 500;
pub const SL_MAX_BPS: u16 = 9_500;

pub const LEG_POOL: u8 = 0;
pub const LEG_RUNNER: u8 = 1;

/// Keeper return reasons (logged on-chain): take-profit, stop-loss, card profit level.
pub const REASON_TP: u8 = 1;
pub const REASON_SL: u8 = 2;
pub const REASON_PROFIT: u8 = 3;
/// Auto-compound: the gain goes back to the owner's wallet too (re-buying is the owner's one-tap, never the keeper's).
pub const REASON_COMPOUND: u8 = 4;

pub const TOKEN_PROGRAM: Pubkey = pubkey!("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
pub const TOKEN_2022_PROGRAM: Pubkey = pubkey!("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb");
