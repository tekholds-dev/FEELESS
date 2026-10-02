//! FUSE Card v0.2 — the keeper can TRADE, but only inside hard fences (LOCALNET ONLY, not audited, not deployed):
//!   1. only the configured keeper, never while paused, only automations the OWNER switched on (rules::keeper_allowed);
//!   2. only through `config.swap_program` (one whitelisted program), only on the pool whose mints match the leg + card quote;
//!   3. the trigger is checked ON-CHAIN from that pool's reserves vs the owner's own entry (TP / SL / profit / back-at-entry);
//!   4. min_out ≥ the pool's expected output − capped slippage, and the card's balance must actually grow by ≥ min_out;
//!   5. every coin / SOL ends in the card's own accounts or the OWNER's wallet — nowhere else.
//! Stop modes (owner's `sl_mode`): PAYOUT = sell + SOL to the owner's wallet · PARK = sell, SOL stays parked on the leg,
//! bought back when price returns to entry · HOLD = never sold on a stop. Compound: profit sells keep SOL as card cash and
//! may only be bought back into coins ALREADY on the card.
use anchor_lang::prelude::*;
use anchor_lang::solana_program::{instruction::{AccountMeta, Instruction}, program::invoke_signed};

use crate::{constants::*, error::ErrorCode, instructions::{check_owner_dest, check_vault, leg_of, transfer_checked}, rules, state::*};

#[event]
pub struct KeeperTraded {
    pub card: Pubkey,
    pub leg: u8,
    pub sell: bool,
    pub amount_in: u64,
    pub amount_out: u64,
    pub reason: u8,
}

#[derive(Accounts)]
pub struct KeeperSwap<'info> {
    pub keeper: Signer<'info>,
    #[account(seeds = [CONFIG_SEED], bump = config.bump, constraint = config.keeper == keeper.key() @ ErrorCode::AutomationOff)]
    pub config: Account<'info, Config>,
    #[account(mut, seeds = [CARD_SEED, card.owner.as_ref(), &card.card_id.to_le_bytes()], bump = card.bump)]
    pub card: Account<'info, Card>,
    /// CHECK: the leg's coin mint (checked)
    pub coin_mint: UncheckedAccount<'info>,
    /// CHECK: the card's quote mint (checked)
    pub quote_mint: UncheckedAccount<'info>,
    /// CHECK: the card's coin account (owned by the card PDA — checked)
    #[account(mut)]
    pub card_coin: UncheckedAccount<'info>,
    /// CHECK: the card's quote account (owned by the card PDA — checked)
    #[account(mut)]
    pub card_quote: UncheckedAccount<'info>,
    /// CHECK: the OWNER's quote account — the only place a payout may go (checked)
    #[account(mut)]
    pub owner_quote: UncheckedAccount<'info>,
    /// CHECK: pool account owned by the whitelisted swap program; mints + vaults parsed and checked
    pub pool: UncheckedAccount<'info>,
    /// CHECK: checked against the pool
    #[account(mut)]
    pub pool_coin_vault: UncheckedAccount<'info>,
    /// CHECK: checked against the pool
    #[account(mut)]
    pub pool_quote_vault: UncheckedAccount<'info>,
    /// CHECK: must equal config.swap_program
    pub swap_program: UncheckedAccount<'info>,
    /// CHECK: SPL Token (checked in the helpers)
    pub token_program: UncheckedAccount<'info>,
}

/// Anchor discriminator of the adapter's `swap` = sha256("global:swap")[..8] (test-pinned).
pub const SWAP_IX: [u8; 8] = [248, 198, 158, 145, 225, 117, 135, 200];

fn amount_of(ai: &AccountInfo) -> Result<u64> {
    let d = ai.try_borrow_data()?;
    require!(d.len() >= 72, ErrorCode::BadCardVault);
    Ok(u64::from_le_bytes(d[64..72].try_into().unwrap()))
}

/// Pool layout (mock AMM / adapter): 8 disc · mint_a · mint_b · vault_a · vault_b. Returns (coin reserve, quote reserve).
fn pool_reserves(a: &KeeperSwap, leg_mint: &Pubkey) -> Result<(u64, u64)> {
    require!(a.swap_program.key() == a.config.swap_program && a.swap_program.executable, ErrorCode::BadSwapProgram);
    require!(a.pool.owner == &a.config.swap_program, ErrorCode::BadPool);
    let d = a.pool.try_borrow_data()?;
    require!(d.len() >= 8 + 32 * 4, ErrorCode::BadPool);
    let k = |o: usize| Pubkey::try_from(&d[o..o + 32]).unwrap();
    require!(k(8) == *leg_mint && k(40) == a.card.quote_mint, ErrorCode::BadPool);
    require!(k(72) == a.pool_coin_vault.key() && k(104) == a.pool_quote_vault.key(), ErrorCode::BadPool);
    Ok((amount_of(&a.pool_coin_vault)?, amount_of(&a.pool_quote_vault)?))
}

/// CPI the whitelisted swap program as the card PDA: swap(amount_in, min_out, a_to_b).
fn swap_cpi<'info>(a: &KeeperSwap<'info>, amount_in: u64, min_out: u64, sell: bool) -> Result<()> {
    let mut data = SWAP_IX.to_vec();
    data.extend_from_slice(&amount_in.to_le_bytes());
    data.extend_from_slice(&min_out.to_le_bytes());
    data.push(sell as u8);
    let (user_in, user_out) = if sell { (&a.card_coin, &a.card_quote) } else { (&a.card_quote, &a.card_coin) };
    let card_ai = a.card.to_account_info();
    let ix = Instruction {
        program_id: a.swap_program.key(),
        accounts: vec![AccountMeta::new_readonly(card_ai.key(), true), AccountMeta::new_readonly(a.pool.key(), false),
                       AccountMeta::new(a.pool_coin_vault.key(), false), AccountMeta::new(a.pool_quote_vault.key(), false),
                       AccountMeta::new(user_in.key(), false), AccountMeta::new(user_out.key(), false), AccountMeta::new_readonly(a.token_program.key(), false)],
        data,
    };
    let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
    let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
    invoke_signed(&ix, &[card_ai, a.pool.to_account_info(), a.pool_coin_vault.to_account_info(), a.pool_quote_vault.to_account_info(),
                         user_in.to_account_info(), user_out.to_account_info(), a.token_program.to_account_info(), a.swap_program.to_account_info()], &[seeds])?;
    Ok(())
}

fn check_accounts(a: &KeeperSwap, leg: &Leg) -> Result<()> {
    let card_key = a.card.key();
    check_vault(&card_key, leg, &a.card_coin, &a.coin_mint, &a.token_program)?;
    let q = Leg { mint: a.card.quote_mint, ..Default::default() };
    check_vault(&card_key, &q, &a.card_quote, &a.quote_mint, &a.token_program)?;
    check_owner_dest(&a.card, &q, &a.owner_quote, &a.token_program)?;
    Ok(())
}

pub fn keeper_sell<'info>(ctx: Context<'info, KeeperSwap<'info>>, idx: u8, amount: u64, min_out: u64, reason: u8) -> Result<()> {
    let a = &ctx.accounts;
    require!(!a.config.paused, ErrorCode::Paused);
    require!(matches!(reason, REASON_TP | REASON_SL | REASON_PROFIT | REASON_COMPOUND), ErrorCode::BadReason);
    let i = leg_of(&a.card, idx)?;
    let leg = a.card.legs[i];
    rules::keeper_allowed(&a.card.toggles, &leg, reason).map_err(|e| error!(e))?;
    require!(amount > 0 && amount <= leg.held, ErrorCode::InsufficientHeld);
    check_accounts(a, &leg)?;
    let (rc, rq) = pool_reserves(a, &leg.mint)?;
    // the trigger, from the pool's reserves vs the owner's entry — the keeper can't claim a price
    let t = a.card.toggles;
    let hit = match reason {
        REASON_TP => rules::hit_up(rc, rq, leg.entry_quote, leg.entry_coin, leg.tp_bps),
        REASON_SL => rules::hit_down(rc, rq, leg.entry_quote, leg.entry_coin, leg.sl_bps),
        _ => rules::hit_up(rc, rq, leg.entry_quote, leg.entry_coin, t.profit_at_bps),
    };
    require!(hit, ErrorCode::NotTriggered);
    require!(rules::min_out_ok(min_out, rules::expected_out(amount, rc, rq), a.config.max_slippage_bps), ErrorCode::SlippageTooLoose);
    let before = amount_of(&a.card_quote)?;
    swap_cpi(a, amount, min_out, true)?;
    let got = amount_of(&ctx.accounts.card_quote)?.checked_sub(before).ok_or(ErrorCode::ShortFill)?;
    require!(got >= min_out, ErrorCode::ShortFill);
    let pay_out = book_sell(&mut ctx.accounts.card, i, amount, got, reason)?;
    if pay_out {   // TP / profit / stop (payout mode): the SOL goes to the OWNER's wallet
        let a = &ctx.accounts;
        let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
        let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
        transfer_checked(&a.token_program, &a.card_quote, &a.quote_mint, &a.owner_quote, &a.card.to_account_info(), got, Some(seeds))?;
    }
    emit!(KeeperTraded { card: ctx.accounts.card.key(), leg: idx, sell: true, amount_in: amount, amount_out: got, reason });
    Ok(())
}

pub fn keeper_buy<'info>(ctx: Context<'info, KeeperSwap<'info>>, idx: u8, amount_in: u64, min_out: u64, reason: u8) -> Result<()> {
    let a = &ctx.accounts;
    require!(!a.config.paused, ErrorCode::Paused);
    let i = leg_of(&a.card, idx)?;
    let leg = a.card.legs[i];
    match reason {
        REASON_REBUY => {
            rules::keeper_allowed(&a.card.toggles, &leg, REASON_REBUY).map_err(|e| error!(e))?;
            require!(amount_in > 0 && amount_in <= leg.parked, ErrorCode::InsufficientQuote);
        }
        REASON_COMPOUND => {   // card cash may only go into a coin ALREADY on this card
            require!(a.card.toggles.auto_compound, ErrorCode::AutomationOff);
            require!(amount_in > 0 && amount_in <= a.card.cash, ErrorCode::InsufficientQuote);
        }
        _ => return err!(ErrorCode::BadReason),
    }
    check_accounts(a, &leg)?;
    let (rc, rq) = pool_reserves(a, &leg.mint)?;
    if reason == REASON_REBUY {
        require!(rules::back_at_entry(rc, rq, leg.entry_quote, leg.entry_coin), ErrorCode::NotTriggered);
    }
    require!(rules::min_out_ok(min_out, rules::expected_out(amount_in, rq, rc), a.config.max_slippage_bps), ErrorCode::SlippageTooLoose);
    let before = amount_of(&a.card_coin)?;
    swap_cpi(a, amount_in, min_out, false)?;
    let got = amount_of(&ctx.accounts.card_coin)?.checked_sub(before).ok_or(ErrorCode::ShortFill)?;
    require!(got >= min_out, ErrorCode::ShortFill);
    book_buy(&mut ctx.accounts.card, i, amount_in, got, reason)?;
    let c = &ctx.accounts.card;
    emit!(KeeperTraded { card: c.key(), leg: idx, sell: false, amount_in, amount_out: got, reason });
    Ok(())
}

/// Sell bookkeeping shared by every venue: the leg shrinks with its entry pro-rata; a park-mode stop parks the SOL on the leg (keeps
/// the stop-out entry), a compound sell keeps it as card cash. Returns true when the SOL must be paid to the OWNER's wallet.
pub fn book_sell(c: &mut Account<Card>, i: usize, amount: u64, got: u64, reason: u8) -> Result<bool> {
    let t = c.toggles;
    let l = &mut c.legs[i];
    let cut = (l.entry_quote as u128 * amount as u128 / l.held.max(1) as u128) as u64;
    l.held -= amount;
    l.entry_quote = l.entry_quote.saturating_sub(cut);
    l.entry_coin = l.entry_coin.saturating_sub(amount);
    let park = reason == REASON_SL && t.sl_mode == SL_PARK;
    if park {
        l.parked = l.parked.checked_add(got).ok_or(ErrorCode::Overflow)?;
        l.entry_quote = l.entry_quote.saturating_add(cut);     // keep the stop-out entry: buy back only at this price
        l.entry_coin = l.entry_coin.saturating_add(amount);
    } else if reason == REASON_COMPOUND {
        c.cash = c.cash.checked_add(got).ok_or(ErrorCode::Overflow)?;
    }
    Ok(!park && reason != REASON_COMPOUND)
}

/// Buy bookkeeping shared by every venue: a re-buy spends the leg's parked SOL (entry already = the stop-out price); a compound
/// buy spends card cash and raises the leg's entry by what it paid.
pub fn book_buy(c: &mut Account<Card>, i: usize, amount_in: u64, got: u64, reason: u8) -> Result<()> {
    if reason == REASON_REBUY {
        let l = &mut c.legs[i];
        l.parked -= amount_in;
        l.held = l.held.checked_add(got).ok_or(ErrorCode::Overflow)?;
    } else {
        c.cash -= amount_in;
        let l = &mut c.legs[i];
        l.held = l.held.checked_add(got).ok_or(ErrorCode::Overflow)?;
        l.entry_coin = l.entry_coin.checked_add(got).ok_or(ErrorCode::Overflow)?;
        l.entry_quote = l.entry_quote.checked_add(amount_in).ok_or(ErrorCode::Overflow)?;
    }
    Ok(())
}

#[derive(Accounts)]
pub struct OwnerQuote<'info> {
    pub owner: Signer<'info>,
    #[account(mut, seeds = [CARD_SEED, owner.key().as_ref(), &card.card_id.to_le_bytes()], bump = card.bump, has_one = owner)]
    pub card: Account<'info, Card>,
    /// CHECK: the card's quote account (checked)
    #[account(mut)]
    pub card_quote: UncheckedAccount<'info>,
    /// CHECK: the owner's quote account (checked)
    #[account(mut)]
    pub owner_quote: UncheckedAccount<'info>,
    /// CHECK: quote mint (checked)
    pub quote_mint: UncheckedAccount<'info>,
    /// CHECK: SPL Token (checked)
    pub token_program: UncheckedAccount<'info>,
}

/// The owner can ALWAYS pull parked SOL (idx = leg) or compound cash (idx = CASH_IDX) to their own wallet — even paused.
pub fn withdraw_quote(ctx: Context<OwnerQuote>, idx: u8, amount: u64) -> Result<()> {
    let a = &ctx.accounts;
    let q = Leg { mint: a.card.quote_mint, ..Default::default() };
    check_vault(&a.card.key(), &q, &a.card_quote, &a.quote_mint, &a.token_program)?;
    check_owner_dest(&a.card, &q, &a.owner_quote, &a.token_program)?;
    if idx == CASH_IDX {
        require!(amount <= a.card.cash, ErrorCode::InsufficientQuote);
    } else {
        let i = leg_of(&a.card, idx)?;
        require!(amount <= a.card.legs[i].parked, ErrorCode::InsufficientQuote);
    }
    let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
    let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
    transfer_checked(&a.token_program, &a.card_quote, &a.quote_mint, &a.owner_quote, &a.card.to_account_info(), amount, Some(seeds))?;
    let c = &mut ctx.accounts.card;
    if idx == CASH_IDX { c.cash -= amount } else { c.legs[idx as usize].parked -= amount }
    Ok(())
}
