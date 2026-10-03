//! FUSE Card v0.3 — the REAL venue adapter: Raydium CP-Swap (CPMM). LOCALNET / DEVNET until audited.
//! The keeper trades a card's coin ⇄ its quote (wSOL) through Raydium's `swap_base_input`, signed by the card PDA, with every fence
//! from v0.2 plus a MANIPULATION GUARD from Raydium's own on-chain TWAP (the pool's observation account):
//!   • the pool must belong to `config.swap_program` (= Raydium CPMM), hold exactly the leg's coin + the card's quote, be swap-enabled;
//!   • reserves = vault balances − protocol / fund / creator fees (what Raydium itself prices with);
//!   • spot must sit within TWAP_MAX_DEV_BPS of the ≥ TWAP_MIN_SECS time-weighted price → a one-block pool push can't fire a TP / stop;
//!   • the trigger is checked against the TWAP (not spot), min_out ≥ expected − capped slippage (Raydium's real fee tier), balance diff.
//! Token-2022 coins are refused in v0.3 (one SPL Token program for both sides).
use anchor_lang::prelude::*;
use anchor_lang::solana_program::{instruction::{AccountMeta, Instruction}, program::invoke_signed, pubkey::pubkey};

use crate::{constants::*, error::ErrorCode, instructions::{check_owner_dest, check_vault, leg_of, transfer_checked}, keeper::{book_buy, book_sell, KeeperTraded}, rules, state::*};

/// Raydium CPMM program ids (mainnet / devnet) — config.swap_program must be one of these (or the localnet build in tests).
pub const RAYDIUM_CPMM_MAINNET: Pubkey = pubkey!("CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C");
pub const RAYDIUM_CPMM_DEVNET: Pubkey = pubkey!("DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb");
/// sha256("global:swap_base_input")[..8] — pinned by backend/tests/test_contract_pins.py.
pub const SWAP_BASE_INPUT_IX: [u8; 8] = [143, 190, 90, 218, 196, 30, 51, 222];
pub const AUTH_SEED: &[u8] = b"vault_and_lp_mint_auth_seed";
/// TWAP guard: spot within ±10% of the time-weighted price over at least 5 minutes of observations.
pub const TWAP_MAX_DEV_BPS: u128 = 1_000;
#[cfg(not(feature = "fast-twap"))]
pub const TWAP_MIN_SECS: u64 = 300;
#[cfg(feature = "fast-twap")]
pub const TWAP_MIN_SECS: u64 = 90;   // localnet integration test only

/// The fields of Raydium's PoolState the adapter needs (repr(C, packed), after the 8-byte discriminator).
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct CpmmPool {
    pub amm_config: Pubkey,
    pub vault0: Pubkey,
    pub vault1: Pubkey,
    pub mint0: Pubkey,
    pub mint1: Pubkey,
    pub prog0: Pubkey,
    pub prog1: Pubkey,
    pub observation: Pubkey,
    pub status: u8,
    pub fees0: u64,
    pub fees1: u64,
}

fn pk(d: &[u8], o: usize) -> Pubkey { Pubkey::try_from(&d[o..o + 32]).unwrap() }
fn u64_at(d: &[u8], o: usize) -> u64 { u64::from_le_bytes(d[o..o + 8].try_into().unwrap()) }
fn u128_at(d: &[u8], o: usize) -> u128 { u128::from_le_bytes(d[o..o + 16].try_into().unwrap()) }

pub const POOL_LEN: usize = 8 + 10 * 32 + 5 + 8 * 7 + 2 + 6 + 2 * 8 + 8 * 28;

pub fn parse_pool(d: &[u8]) -> Option<CpmmPool> {
    if d.len() < POOL_LEN { return None; }
    // fees owed to protocol / fund / creator sit in the vaults but are NOT liquidity
    let fees = |p: usize, f: usize, c: usize| u64_at(d, p).saturating_add(u64_at(d, f)).saturating_add(u64_at(d, c));
    Some(CpmmPool { amm_config: pk(d, 8), vault0: pk(d, 72), vault1: pk(d, 104), mint0: pk(d, 168), mint1: pk(d, 200), prog0: pk(d, 232), prog1: pk(d, 264),
                    observation: pk(d, 296), status: d[329], fees0: fees(341, 357, 397), fees1: fees(349, 365, 405) })
}

/// bit2 of status = swap disabled.
pub fn swap_enabled(p: &CpmmPool) -> bool { p.status & 0b100 == 0 }

/// Raydium AmmConfig trade_fee_rate (offset 12) + creator_fee_rate (offset 108), 1e6 = 100% → bps, rounded UP so the expected
/// output is never optimistic (a too-tight min_out only makes Raydium refuse — never a bad fill).
pub fn fee_bps(cfg: &[u8]) -> Option<u64> {
    if cfg.len() < 116 { return None; }
    let rate = u64_at(cfg, 12).saturating_add(u64_at(cfg, 108));
    Some((rate + 99) / 100)
}

/// Constant-product output with the pool's REAL fee tier.
pub fn expected_out_fee(amount_in: u64, reserve_in: u64, reserve_out: u64, fee_bps: u64) -> u64 {
    let a = amount_in as u128 * (10_000 - fee_bps.min(10_000)) as u128;
    let d = reserve_in as u128 * 10_000 + a;
    if d == 0 { 0 } else { ((a * reserve_out as u128) / d) as u64 }
}

/// Time-weighted price of token0 in token1 (Q32) from the observation ring: newest cumulative (valid at last_update) vs the newest
/// observation at least `min_secs` older. None = not enough history (the guard then refuses to trade).
pub fn twap0_x32(obs: &[u8], min_secs: u64) -> Option<u128> {
    const BASE: usize = 8 + 1 + 2 + 32;
    const N: usize = 100;
    const W: usize = 40;
    if obs.len() < BASE + N * W + 8 || obs[8] == 0 { return None; }
    let idx = u16::from_le_bytes([obs[9], obs[10]]) as usize % N;
    let ts = |i: usize| u64_at(obs, BASE + i * W);
    let cum = |i: usize| u128_at(obs, BASE + i * W + 8);
    let t_new = u64_at(obs, BASE + N * W);
    let c_new = cum(idx);
    for back in 1..N {
        let i = (idx + N - back) % N;
        // Raydium keeps adding to obs i in place for < 15s after creating it (then opens obs i+1), so its final cumulative is valid at
        // the last update in [ts(i), min(ts(i)+15, ts(i+1))). We take that upper bound: error ≤ 15s / window (≤5% at 300s, inside the band).
        let nxt = (i + 1) % N;
        if ts(i) == 0 || ts(i) > t_new { break; }
        let (t_old, c_old) = ((ts(i) + 15).min(ts(nxt)), cum(i));
        if t_new - t_old >= min_secs {
            return Some(c_new.wrapping_sub(c_old) / (t_new - t_old) as u128);
        }
    }
    None
}

/// Spot (quote per coin) within ±max_dev of the TWAP — prices cross-multiplied in u128, Q32 for the TWAP.
pub fn spot_near_twap(res_coin: u64, res_quote: u64, twap_quote_per_coin_x32: u128, max_dev_bps: u128) -> bool {
    if res_coin == 0 || twap_quote_per_coin_x32 == 0 { return false; }
    let spot_x32 = ((res_quote as u128) << 32) / res_coin as u128;
    let (hi, lo) = (twap_quote_per_coin_x32 * (10_000 + max_dev_bps) / 10_000, twap_quote_per_coin_x32 * (10_000 - max_dev_bps) / 10_000);
    spot_x32 <= hi && spot_x32 >= lo
}

/// TWAP-based reserves for the trigger: same coin reserve, quote reserve implied by the TWAP price (so the trigger can't be pushed).
pub fn twap_reserves(res_coin: u64, twap_quote_per_coin_x32: u128) -> (u64, u64) {
    (res_coin, ((res_coin as u128 * twap_quote_per_coin_x32) >> 32).min(u64::MAX as u128) as u64)
}

#[derive(Accounts)]
pub struct KeeperCpmm<'info> {
    pub keeper: Signer<'info>,
    #[account(seeds = [CONFIG_SEED], bump = config.bump, constraint = config.keeper == keeper.key() @ ErrorCode::AutomationOff)]
    pub config: Account<'info, Config>,
    #[account(mut, seeds = [CARD_SEED, card.owner.as_ref(), &card.card_id.to_le_bytes()], bump = card.bump)]
    pub card: Account<'info, Card>,
    /// CHECK: the leg's coin mint (checked)
    pub coin_mint: UncheckedAccount<'info>,
    /// CHECK: the card's quote mint (checked)
    pub quote_mint: UncheckedAccount<'info>,
    /// CHECK: card-owned coin account (checked)
    #[account(mut)]
    pub card_coin: UncheckedAccount<'info>,
    /// CHECK: card-owned quote account (checked)
    #[account(mut)]
    pub card_quote: UncheckedAccount<'info>,
    /// CHECK: the OWNER's quote account — the only payout destination (checked)
    #[account(mut)]
    pub owner_quote: UncheckedAccount<'info>,
    /// CHECK: Raydium PoolState, owned by config.swap_program (parsed + checked)
    #[account(mut)]
    pub pool_state: UncheckedAccount<'info>,
    /// CHECK: Raydium vault authority PDA (checked by Raydium)
    pub cpmm_authority: UncheckedAccount<'info>,
    /// CHECK: must equal pool.amm_config (fee tier read from it)
    pub amm_config: UncheckedAccount<'info>,
    /// CHECK: the pool's vault for the coin (checked against the pool)
    #[account(mut)]
    pub coin_vault: UncheckedAccount<'info>,
    /// CHECK: the pool's vault for the quote (checked against the pool)
    #[account(mut)]
    pub quote_vault: UncheckedAccount<'info>,
    /// CHECK: must equal pool.observation (TWAP read from it)
    #[account(mut)]
    pub observation: UncheckedAccount<'info>,
    /// CHECK: must equal config.swap_program
    pub swap_program: UncheckedAccount<'info>,
    /// CHECK: SPL Token (both sides in v0.3; checked in the helpers)
    pub token_program: UncheckedAccount<'info>,
}

fn vault_amount(ai: &AccountInfo) -> Result<u64> {
    let d = ai.try_borrow_data()?;
    require!(d.len() >= 72, ErrorCode::BadCardVault);
    Ok(u64_at(&d, 64))
}

/// (coin reserve, quote reserve, fee bps, twap quote-per-coin Q32) — every account checked against the pool.
fn read_pool(a: &KeeperCpmm, coin: &Pubkey) -> Result<(u64, u64, u64, u128)> {
    require!(a.swap_program.key() == a.config.swap_program && a.swap_program.executable, ErrorCode::BadSwapProgram);
    require!(a.pool_state.owner == &a.config.swap_program && a.amm_config.owner == &a.config.swap_program && a.observation.owner == &a.config.swap_program, ErrorCode::BadPool);
    let p = parse_pool(&a.pool_state.try_borrow_data()?).ok_or(ErrorCode::BadPool)?;
    require!(swap_enabled(&p) && p.amm_config == a.amm_config.key() && p.observation == a.observation.key(), ErrorCode::BadPool);
    require!(p.prog0 == TOKEN_PROGRAM && p.prog1 == TOKEN_PROGRAM && a.token_program.key() == TOKEN_PROGRAM, ErrorCode::BadPool);
    let q = a.card.quote_mint;
    let coin_is_0 = if p.mint0 == *coin && p.mint1 == q { true } else if p.mint1 == *coin && p.mint0 == q { false } else { return err!(ErrorCode::BadPool) };
    let (cv, qv, cf, qf) = if coin_is_0 { (p.vault0, p.vault1, p.fees0, p.fees1) } else { (p.vault1, p.vault0, p.fees1, p.fees0) };
    require!(cv == a.coin_vault.key() && qv == a.quote_vault.key(), ErrorCode::BadPool);
    let rc = vault_amount(&a.coin_vault)?.saturating_sub(cf);
    let rq = vault_amount(&a.quote_vault)?.saturating_sub(qf);
    let fee = fee_bps(&a.amm_config.try_borrow_data()?).ok_or(ErrorCode::BadPool)?;
    let t0 = twap0_x32(&a.observation.try_borrow_data()?, TWAP_MIN_SECS).ok_or(ErrorCode::NotTriggered)?;
    // token0 price is quoted in token1: coin = token0 → quote per coin = t0; coin = token1 → invert
    let twap = if coin_is_0 { t0 } else if t0 == 0 { 0 } else { (1u128 << 64) / t0 };
    require!(spot_near_twap(rc, rq, twap, TWAP_MAX_DEV_BPS), ErrorCode::NotTriggered);
    Ok((rc, rq, fee, twap))
}

fn cpmm_cpi<'info>(a: &KeeperCpmm<'info>, amount_in: u64, min_out: u64, sell: bool) -> Result<()> {
    let mut data = SWAP_BASE_INPUT_IX.to_vec();
    data.extend_from_slice(&amount_in.to_le_bytes());
    data.extend_from_slice(&min_out.to_le_bytes());
    let (ui, uo, vi, vo, mi, mo) = if sell { (&a.card_coin, &a.card_quote, &a.coin_vault, &a.quote_vault, &a.coin_mint, &a.quote_mint) }
                                   else { (&a.card_quote, &a.card_coin, &a.quote_vault, &a.coin_vault, &a.quote_mint, &a.coin_mint) };
    let card_ai = a.card.to_account_info();
    let tp = a.token_program.key();
    let ix = Instruction { program_id: a.swap_program.key(), data, accounts: vec![
        AccountMeta::new_readonly(card_ai.key(), true), AccountMeta::new_readonly(a.cpmm_authority.key(), false), AccountMeta::new_readonly(a.amm_config.key(), false),
        AccountMeta::new(a.pool_state.key(), false), AccountMeta::new(ui.key(), false), AccountMeta::new(uo.key(), false), AccountMeta::new(vi.key(), false),
        AccountMeta::new(vo.key(), false), AccountMeta::new_readonly(tp, false), AccountMeta::new_readonly(tp, false), AccountMeta::new_readonly(mi.key(), false),
        AccountMeta::new_readonly(mo.key(), false), AccountMeta::new(a.observation.key(), false)] };
    let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
    let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
    invoke_signed(&ix, &[card_ai, a.cpmm_authority.to_account_info(), a.amm_config.to_account_info(), a.pool_state.to_account_info(), ui.to_account_info(), uo.to_account_info(),
                         vi.to_account_info(), vo.to_account_info(), a.token_program.to_account_info(), mi.to_account_info(), mo.to_account_info(),
                         a.observation.to_account_info(), a.swap_program.to_account_info()], &[seeds])?;
    Ok(())
}

fn check_cards(a: &KeeperCpmm, leg: &Leg) -> Result<()> {
    let card_key = a.card.key();
    check_vault(&card_key, leg, &a.card_coin, &a.coin_mint, &a.token_program)?;
    let q = Leg { mint: a.card.quote_mint, ..Default::default() };
    check_vault(&card_key, &q, &a.card_quote, &a.quote_mint, &a.token_program)?;
    check_owner_dest(&a.card, &q, &a.owner_quote, &a.token_program)
}

pub fn keeper_sell_cpmm<'info>(ctx: Context<'info, KeeperCpmm<'info>>, idx: u8, amount: u64, min_out: u64, reason: u8) -> Result<()> {
    let a = &ctx.accounts;
    require!(!a.config.paused, ErrorCode::Paused);
    require!(matches!(reason, REASON_TP | REASON_SL | REASON_PROFIT | REASON_COMPOUND), ErrorCode::BadReason);
    let i = leg_of(&a.card, idx)?;
    let leg = a.card.legs[i];
    rules::keeper_allowed(&a.card.toggles, &leg, reason).map_err(|e| error!(e))?;
    require!(amount > 0 && amount <= leg.held, ErrorCode::InsufficientHeld);
    check_cards(a, &leg)?;
    let (rc, rq, fee, twap) = read_pool(a, &leg.mint)?;
    let (tc, tq) = twap_reserves(rc, twap);   // the trigger reads the TWAP, never a pushable spot
    let t = a.card.toggles;
    let hit = match reason {
        REASON_TP => rules::hit_up(tc, tq, leg.entry_quote, leg.entry_coin, leg.tp_bps),
        REASON_SL => rules::hit_down(tc, tq, leg.entry_quote, leg.entry_coin, leg.sl_bps),
        _ => rules::hit_up(tc, tq, leg.entry_quote, leg.entry_coin, t.profit_at_bps),
    };
    require!(hit, ErrorCode::NotTriggered);
    require!(rules::min_out_ok(min_out, expected_out_fee(amount, rc, rq, fee), a.config.max_slippage_bps), ErrorCode::SlippageTooLoose);
    let before = vault_amount(&a.card_quote)?;
    cpmm_cpi(a, amount, min_out, true)?;
    let got = vault_amount(&ctx.accounts.card_quote)?.checked_sub(before).ok_or(ErrorCode::ShortFill)?;
    require!(got >= min_out, ErrorCode::ShortFill);
    let pay_out = book_sell(&mut ctx.accounts.card, i, amount, got, reason)?;
    if pay_out {
        let a = &ctx.accounts;
        let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
        let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
        transfer_checked(&a.token_program, &a.card_quote, &a.quote_mint, &a.owner_quote, &a.card.to_account_info(), got, Some(seeds))?;
    }
    emit!(KeeperTraded { card: ctx.accounts.card.key(), leg: idx, sell: true, amount_in: amount, amount_out: got, reason });
    Ok(())
}

pub fn keeper_buy_cpmm<'info>(ctx: Context<'info, KeeperCpmm<'info>>, idx: u8, amount_in: u64, min_out: u64, reason: u8) -> Result<()> {
    let a = &ctx.accounts;
    require!(!a.config.paused, ErrorCode::Paused);
    let i = leg_of(&a.card, idx)?;
    let leg = a.card.legs[i];
    match reason {
        REASON_REBUY => {
            rules::keeper_allowed(&a.card.toggles, &leg, REASON_REBUY).map_err(|e| error!(e))?;
            require!(amount_in > 0 && amount_in <= leg.parked, ErrorCode::InsufficientQuote);
        }
        REASON_COMPOUND => {
            require!(a.card.toggles.auto_compound, ErrorCode::AutomationOff);
            require!(amount_in > 0 && amount_in <= a.card.cash, ErrorCode::InsufficientQuote);
        }
        _ => return err!(ErrorCode::BadReason),
    }
    check_cards(a, &leg)?;
    let (rc, rq, fee, twap) = read_pool(a, &leg.mint)?;
    if reason == REASON_REBUY {
        let (tc, tq) = twap_reserves(rc, twap);
        require!(rules::back_at_entry(tc, tq, leg.entry_quote, leg.entry_coin), ErrorCode::NotTriggered);
    }
    require!(rules::min_out_ok(min_out, expected_out_fee(amount_in, rq, rc, fee), a.config.max_slippage_bps), ErrorCode::SlippageTooLoose);
    let before = vault_amount(&a.card_coin)?;
    cpmm_cpi(a, amount_in, min_out, false)?;
    let got = vault_amount(&ctx.accounts.card_coin)?.checked_sub(before).ok_or(ErrorCode::ShortFill)?;
    require!(got >= min_out, ErrorCode::ShortFill);
    book_buy(&mut ctx.accounts.card, i, amount_in, got, reason)?;
    emit!(KeeperTraded { card: ctx.accounts.card.key(), leg: idx, sell: false, amount_in, amount_out: got, reason });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pool_bytes(m0: Pubkey, m1: Pubkey, status: u8, fees: [u64; 6]) -> Vec<u8> {
        let mut d = vec![0u8; POOL_LEN];
        d[168..200].copy_from_slice(m0.as_ref()); d[200..232].copy_from_slice(m1.as_ref());
        d[72..104].copy_from_slice(Pubkey::new_unique().as_ref());
        d[329] = status;
        for (o, v) in [341usize, 349, 357, 365, 397, 405].iter().zip(fees) { d[*o..o + 8].copy_from_slice(&v.to_le_bytes()); }
        d
    }

    #[test]
    fn pool_parse_reads_mints_status_and_fees_owed() {
        let (a, b) = (Pubkey::new_unique(), Pubkey::new_unique());
        let p = parse_pool(&pool_bytes(a, b, 0, [1, 2, 3, 4, 5, 6])).unwrap();
        assert_eq!((p.mint0, p.mint1), (a, b));
        assert_eq!((p.fees0, p.fees1), (1 + 3 + 5, 2 + 4 + 6));   // protocol + fund + creator fees are NOT liquidity
        assert!(swap_enabled(&p));
        assert!(!swap_enabled(&parse_pool(&pool_bytes(a, b, 4, [0; 6])).unwrap()));
        assert!(parse_pool(&[0u8; 100]).is_none());
    }

    #[test]
    fn fee_tier_rounds_up_and_expected_out_uses_it() {
        let mut cfg = vec![0u8; 236];
        cfg[12..20].copy_from_slice(&2_500u64.to_le_bytes());   // 0.25% trade fee
        assert_eq!(fee_bps(&cfg), Some(25));
        cfg[108..116].copy_from_slice(&1_000u64.to_le_bytes());  // + 0.1% creator fee
        assert_eq!(fee_bps(&cfg), Some(35));
        assert!(expected_out_fee(1_000, 1_000_000, 1_000_000, 25) < 1_000);
        assert!(expected_out_fee(1_000, 1_000_000, 1_000_000, 25) > expected_out_fee(1_000, 1_000_000, 1_000_000, 100));
    }

    fn obs_bytes(points: &[(u64, u128)], last_update: u64) -> Vec<u8> {
        let mut d = vec![0u8; 8 + 1 + 2 + 32 + 100 * 40 + 8 + 24];
        d[8] = 1;
        d[9..11].copy_from_slice(&((points.len() - 1) as u16).to_le_bytes());
        for (i, (t, c)) in points.iter().enumerate() {
            let o = 43 + i * 40;
            d[o..o + 8].copy_from_slice(&t.to_le_bytes()); d[o + 8..o + 24].copy_from_slice(&c.to_le_bytes());
        }
        d[4043..4051].copy_from_slice(&last_update.to_le_bytes());
        d
    }

    /// Replays Raydium's ObservationState::update: a swap every `every` seconds at `price(t)`; in place while < 15s since the
    /// observation opened, else a new observation. Returns the raw account bytes.
    fn raydium_obs(start: u64, secs: u64, every: u64, price: impl Fn(u64) -> u128) -> Vec<u8> {
        let mut d = vec![0u8; 8 + 1 + 2 + 32 + 100 * 40 + 8 + 24];
        let (mut idx, mut last) = (0usize, start);
        let mut ts = vec![0u64; 100]; let mut cum = vec![0u128; 100];
        ts[0] = start;
        let mut t = start + every;
        while t <= start + secs {
            let delta = price(last) * (t - last) as u128;
            if t - ts[idx] < 15 { cum[idx] = cum[idx].wrapping_add(delta); }
            else { let n = (idx + 1) % 100; ts[n] = t; cum[n] = cum[idx].wrapping_add(delta); idx = n; }
            last = t; t += every;
        }
        d[8] = 1; d[9..11].copy_from_slice(&(idx as u16).to_le_bytes());
        for i in 0..100 { let o = 43 + i * 40; d[o..o + 8].copy_from_slice(&ts[i].to_le_bytes()); d[o + 8..o + 24].copy_from_slice(&cum[i].to_le_bytes()); }
        d[4043..4051].copy_from_slice(&last.to_le_bytes());
        d
    }

    #[test]
    fn twap_matches_raydiums_own_accumulation_and_needs_history() {
        let p = 2u128 << 32;
        for every in [1u64, 4, 7, 13] {   // busy pool … sparse pool
            let tw = twap0_x32(&raydium_obs(1_000, 600, every, |_| p), 300).unwrap();
            assert!((tw as i128 - p as i128).abs() <= (p / 20) as i128, "every {every}s: {tw} vs {p}");
        }
        // a pump 60s ago barely moves a 5-minute TWAP; held for 6 minutes, the TWAP is there
        let pumped = |t: u64| if t >= 1_540 { 3u128 << 32 } else { p };
        let tw = twap0_x32(&raydium_obs(1_000, 600, 4, pumped), 300).unwrap();
        assert!(tw < (5u128 << 32) / 2);
        let tw2 = twap0_x32(&raydium_obs(1_000, 1_000, 4, |t| if t >= 1_100 { 3u128 << 32 } else { p }), 300).unwrap();
        assert!((tw2 as i128 - (3i128 << 32)).abs() <= ((3u128 << 32) / 20) as i128);
        assert!(twap0_x32(&raydium_obs(1_000, 60, 4, |_| p), 300).is_none());   // < 5 min of history → refuse
    }

    #[test]
    fn spot_far_from_twap_is_refused_and_trigger_reads_the_twap() {
        let twap = 2u128 << 32;   // 2 quote per coin
        assert!(spot_near_twap(1_000, 2_100, twap, TWAP_MAX_DEV_BPS));    // +5%
        assert!(!spot_near_twap(1_000, 3_000, twap, TWAP_MAX_DEV_BPS));   // pushed +50% in one block → no trade
        let (c, q) = twap_reserves(1_000, twap);
        assert_eq!((c, q), (1_000, 2_000));
        assert!(!rules::hit_up(c, q, 1_000, 1_000, 15_000) && rules::hit_up(c, q, 1_000, 1_000, 10_000));   // TWAP 2× entry: +100% hit, +150% not
    }
}
