//! FUSE Card v0.1 instructions. Custody: each leg's coins sit in a token account OWNED BY THE CARD PDA (no private key);
//! only these instructions move them, and every exit path ends in the card OWNER's own token account. v0.1 has no swap
//! adapters (so no on-chain selling yet): the keeper can only hand coins back to the owner when the owner switched
//! automation on. Token CPIs are hand-built (TransferChecked) so the program needs nothing beyond anchor-lang.
use anchor_lang::prelude::*;
use anchor_lang::solana_program::{instruction::{AccountMeta, Instruction}, program::{invoke, invoke_signed}};

use crate::{constants::*, error::ErrorCode, rules, state::*};

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct LegIn {
    pub mint: Pubkey,
    pub kind: u8,
    pub tp_bps: u32,
    pub sl_bps: u16,
}

#[event]
pub struct KeeperReturned {
    pub card: Pubkey,
    pub leg: u8,
    pub amount: u64,
    pub reason: u8,
}

// ---- token helpers (SPL Token / Token-2022 account layout: mint 0..32, owner 32..64, amount 64..72; mint decimals @44) ----
pub(crate) fn token_program_ok(p: &AccountInfo) -> Result<()> {
    require!(p.key() == TOKEN_PROGRAM || p.key() == TOKEN_2022_PROGRAM, ErrorCode::BadTokenProgram);
    Ok(())
}

pub(crate) fn token_account(ai: &AccountInfo, token_program: &AccountInfo) -> Result<(Pubkey, Pubkey)> {
    require!(ai.owner == token_program.key, ErrorCode::BadTokenProgram);
    let d = ai.try_borrow_data()?;
    require!(d.len() >= 72, ErrorCode::BadCardVault);
    Ok((Pubkey::try_from(&d[0..32]).unwrap(), Pubkey::try_from(&d[32..64]).unwrap()))
}

pub(crate) fn decimals(mint: &AccountInfo, token_program: &AccountInfo) -> Result<u8> {
    require!(mint.owner == token_program.key, ErrorCode::BadTokenProgram);
    let d = mint.try_borrow_data()?;
    require!(d.len() > 44, ErrorCode::WrongMint);
    Ok(d[44])
}

pub(crate) fn transfer_checked<'info>(token_program: &AccountInfo<'info>, from: &AccountInfo<'info>, mint: &AccountInfo<'info>, to: &AccountInfo<'info>,
                           authority: &AccountInfo<'info>, amount: u64, seeds: Option<&[&[u8]]>) -> Result<()> {
    let mut data = vec![12u8];
    data.extend_from_slice(&amount.to_le_bytes());
    data.push(decimals(mint, token_program)?);
    let ix = Instruction {
        program_id: token_program.key(),
        accounts: vec![AccountMeta::new(from.key(), false), AccountMeta::new_readonly(mint.key(), false), AccountMeta::new(to.key(), false), AccountMeta::new_readonly(authority.key(), true)],
        data,
    };
    let infos = [from.clone(), mint.clone(), to.clone(), authority.clone(), token_program.clone()];
    match seeds { Some(s) => invoke_signed(&ix, &infos, &[s])?, None => invoke(&ix, &infos)? }
    Ok(())
}

pub(crate) fn leg_of(card: &Card, idx: u8) -> Result<usize> {
    require!((idx as usize) < card.leg_count as usize, ErrorCode::BadLeg);
    Ok(idx as usize)
}

/// The card's own token account for this leg (owned by the card PDA, right mint) and the right mint account.
pub(crate) fn check_vault(card_key: &Pubkey, leg: &Leg, vault: &AccountInfo, mint: &AccountInfo, tp: &AccountInfo) -> Result<()> {
    token_program_ok(tp)?;
    require!(mint.key() == leg.mint, ErrorCode::WrongMint);
    let (m, owner) = token_account(vault, tp)?;
    require!(m == leg.mint && owner == *card_key, ErrorCode::BadCardVault);
    Ok(())
}

/// Every exit goes to the card OWNER's own token account for that coin — nowhere else.
pub(crate) fn check_owner_dest(card: &Card, leg: &Leg, dest: &AccountInfo, tp: &AccountInfo) -> Result<()> {
    let (m, owner) = token_account(dest, tp)?;
    require!(m == leg.mint, ErrorCode::WrongMint);
    require!(owner == card.owner, ErrorCode::NotOwnerAccount);
    Ok(())
}

// ---- config (HQ) ----------------------------------------------------------------------------------------------
#[derive(Accounts)]
pub struct InitConfig<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(init, payer = admin, space = 8 + Config::INIT_SPACE, seeds = [CONFIG_SEED], bump)]
    pub config: Account<'info, Config>,
    pub system_program: Program<'info, System>,
}

pub fn init_config(ctx: Context<InitConfig>, keeper: Pubkey, swap_program: Pubkey, max_slippage_bps: u16) -> Result<()> {
    require!(max_slippage_bps <= MAX_SLIPPAGE_BPS, ErrorCode::BadSlippage);
    let c = &mut ctx.accounts.config;
    c.admin = ctx.accounts.admin.key();
    c.keeper = keeper;
    c.paused = false;
    c.bump = ctx.bumps.config;
    c.swap_program = swap_program;
    c.max_slippage_bps = max_slippage_bps;
    Ok(())
}

#[derive(Accounts)]
pub struct SetConfig<'info> {
    pub admin: Signer<'info>,
    #[account(mut, seeds = [CONFIG_SEED], bump = config.bump, has_one = admin)]
    pub config: Account<'info, Config>,
}

pub fn set_config(ctx: Context<SetConfig>, keeper: Pubkey, paused: bool, swap_program: Pubkey, max_slippage_bps: u16) -> Result<()> {
    require!(max_slippage_bps <= MAX_SLIPPAGE_BPS, ErrorCode::BadSlippage);
    let c = &mut ctx.accounts.config;
    c.keeper = keeper;
    c.paused = paused;
    c.swap_program = swap_program;
    c.max_slippage_bps = max_slippage_bps;
    Ok(())
}

// ---- card lifecycle (owner) ------------------------------------------------------------------------------------------
#[derive(Accounts)]
#[instruction(card_id: u64)]
pub struct OpenCard<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(seeds = [CONFIG_SEED], bump = config.bump)]
    pub config: Account<'info, Config>,
    #[account(init, payer = owner, space = 8 + Card::INIT_SPACE, seeds = [CARD_SEED, owner.key().as_ref(), &card_id.to_le_bytes()], bump)]
    pub card: Account<'info, Card>,
    pub system_program: Program<'info, System>,
}

pub fn open_card(ctx: Context<OpenCard>, card_id: u64, legs: Vec<LegIn>, toggles: Toggles, quote_mint: Pubkey) -> Result<()> {
    let admin = ctx.accounts.owner.key() == ctx.accounts.config.admin;   // HQ cards: up to 12 legs, any mix
    let spec: Vec<rules::LegSpec> = legs.iter().map(|l| rules::LegSpec { mint: l.mint.to_bytes(), kind: l.kind, tp_bps: l.tp_bps, sl_bps: l.sl_bps }).collect();
    rules::check_legs(&spec, admin).map_err(|e| error!(e))?;
    rules::check_toggles(&toggles).map_err(|e| error!(e))?;
    let c = &mut ctx.accounts.card;
    c.owner = ctx.accounts.owner.key();
    c.card_id = card_id;
    c.bump = ctx.bumps.card;
    c.admin_card = admin;
    c.legs = [Leg::default(); MAX_LEGS];
    for (i, l) in legs.iter().enumerate() {
        c.legs[i] = Leg { mint: l.mint, kind: l.kind, tp_bps: l.tp_bps, sl_bps: l.sl_bps, ..Default::default() };
    }
    c.leg_count = legs.len() as u8;
    c.toggles = toggles;
    c.opened_ts = Clock::get()?.unix_timestamp;
    c.quote_mint = quote_mint;
    c.cash = 0;
    Ok(())
}

#[derive(Accounts)]
pub struct OwnerCard<'info> {
    pub owner: Signer<'info>,
    #[account(mut, seeds = [CARD_SEED, owner.key().as_ref(), &card.card_id.to_le_bytes()], bump = card.bump, has_one = owner)]
    pub card: Account<'info, Card>,
}

pub fn set_toggles(ctx: Context<OwnerCard>, toggles: Toggles) -> Result<()> {
    rules::check_toggles(&toggles).map_err(|e| error!(e))?;
    ctx.accounts.card.toggles = toggles;
    Ok(())
}

pub fn set_leg_limits(ctx: Context<OwnerCard>, idx: u8, tp_bps: u32, sl_bps: u16) -> Result<()> {
    rules::check_limits(tp_bps, sl_bps).map_err(|e| error!(e))?;
    let i = leg_of(&ctx.accounts.card, idx)?;
    let leg = &mut ctx.accounts.card.legs[i];
    leg.tp_bps = tp_bps;
    leg.sl_bps = sl_bps;
    Ok(())
}

#[derive(Accounts)]
pub struct MoveLeg<'info> {
    pub owner: Signer<'info>,
    #[account(mut, seeds = [CARD_SEED, owner.key().as_ref(), &card.card_id.to_le_bytes()], bump = card.bump, has_one = owner)]
    pub card: Account<'info, Card>,
    /// CHECK: the owner's token account for this leg's coin (checked: mint, owner).
    #[account(mut)]
    pub owner_token: UncheckedAccount<'info>,
    /// CHECK: the card's token account for this coin (checked: owned by the card PDA, mint).
    #[account(mut)]
    pub card_vault: UncheckedAccount<'info>,
    /// CHECK: the leg's mint (checked against the card).
    pub mint: UncheckedAccount<'info>,
    /// CHECK: SPL Token or Token-2022 (checked).
    pub token_program: UncheckedAccount<'info>,
}

/// Put a leg's coins into the card (after the wallet-signed buy landed in the owner's wallet). `cost_quote` = what the
/// owner paid for them (quote atoms) — the entry every on-chain trigger compares against. Signed by the owner only.
pub fn deposit_leg(ctx: Context<MoveLeg>, idx: u8, amount: u64, cost_quote: u64) -> Result<()> {
    let card_key = ctx.accounts.card.key();
    let i = leg_of(&ctx.accounts.card, idx)?;
    let leg = ctx.accounts.card.legs[i];
    let a = &ctx.accounts;
    check_vault(&card_key, &leg, &a.card_vault, &a.mint, &a.token_program)?;
    check_owner_dest(&a.card, &leg, &a.owner_token, &a.token_program)?;
    transfer_checked(&a.token_program, &a.owner_token, &a.mint, &a.card_vault, &a.owner, amount, None)?;
    let leg = &mut ctx.accounts.card.legs[i];
    leg.held = leg.held.checked_add(amount).ok_or(ErrorCode::Overflow)?;
    leg.entry_coin = leg.entry_coin.checked_add(amount).ok_or(ErrorCode::Overflow)?;
    leg.entry_quote = leg.entry_quote.checked_add(cost_quote).ok_or(ErrorCode::Overflow)?;
    Ok(())
}

/// The owner can ALWAYS take any leg back (even while the keeper is paused).
pub fn withdraw_leg(ctx: Context<MoveLeg>, idx: u8, amount: u64) -> Result<()> {
    let card_key = ctx.accounts.card.key();
    let i = leg_of(&ctx.accounts.card, idx)?;
    let leg = ctx.accounts.card.legs[i];
    require!(amount <= leg.held, ErrorCode::InsufficientHeld);
    let a = &ctx.accounts;
    check_vault(&card_key, &leg, &a.card_vault, &a.mint, &a.token_program)?;
    check_owner_dest(&a.card, &leg, &a.owner_token, &a.token_program)?;
    let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
    let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
    transfer_checked(&a.token_program, &a.card_vault, &a.mint, &a.owner_token, &a.card.to_account_info(), amount, Some(seeds))?;
    ctx.accounts.card.legs[i].held -= amount;
    Ok(())
}

// ---- the fenced keeper -------------------------------------------------------------------------------------------
#[derive(Accounts)]
pub struct KeeperMove<'info> {
    pub keeper: Signer<'info>,
    #[account(seeds = [CONFIG_SEED], bump = config.bump, constraint = config.keeper == keeper.key() @ ErrorCode::AutomationOff)]
    pub config: Account<'info, Config>,
    #[account(mut, seeds = [CARD_SEED, card.owner.as_ref(), &card.card_id.to_le_bytes()], bump = card.bump)]
    pub card: Account<'info, Card>,
    /// CHECK: must be the card OWNER's token account for this coin (checked).
    #[account(mut)]
    pub owner_token: UncheckedAccount<'info>,
    /// CHECK: the card's token account for this coin (checked).
    #[account(mut)]
    pub card_vault: UncheckedAccount<'info>,
    /// CHECK: the leg's mint (checked).
    pub mint: UncheckedAccount<'info>,
    /// CHECK: SPL Token or Token-2022 (checked).
    pub token_program: UncheckedAccount<'info>,
}

/// Keeper hands a leg's coins back to the OWNER (their TP / SL / card profit level hit) — only if the owner switched
/// automation on, only to the owner's own token account, never while paused. v0.1 cannot sell or send elsewhere.
pub fn keeper_return(ctx: Context<KeeperMove>, idx: u8, amount: u64, reason: u8) -> Result<()> {
    require!(!ctx.accounts.config.paused, ErrorCode::Paused);
    let card_key = ctx.accounts.card.key();
    let i = leg_of(&ctx.accounts.card, idx)?;
    let leg = ctx.accounts.card.legs[i];
    rules::keeper_allowed(&ctx.accounts.card.toggles, &leg, reason).map_err(|e| error!(e))?;
    require!(amount <= leg.held, ErrorCode::InsufficientHeld);
    let a = &ctx.accounts;
    check_vault(&card_key, &leg, &a.card_vault, &a.mint, &a.token_program)?;
    check_owner_dest(&a.card, &leg, &a.owner_token, &a.token_program)?;
    let (owner, id, bump) = (a.card.owner, a.card.card_id.to_le_bytes(), a.card.bump);
    let seeds: &[&[u8]] = &[CARD_SEED, owner.as_ref(), &id, &[bump]];
    transfer_checked(&a.token_program, &a.card_vault, &a.mint, &a.owner_token, &a.card.to_account_info(), amount, Some(seeds))?;
    ctx.accounts.card.legs[i].held -= amount;
    emit!(KeeperReturned { card: card_key, leg: idx, amount, reason });
    Ok(())
}

#[derive(Accounts)]
pub struct CloseCard<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    #[account(mut, close = owner, seeds = [CARD_SEED, owner.key().as_ref(), &card.card_id.to_le_bytes()], bump = card.bump, has_one = owner)]
    pub card: Account<'info, Card>,
}

/// Close an EMPTY card (every leg withdrawn); its rent goes back to the owner.
pub fn close_card(ctx: Context<CloseCard>) -> Result<()> {
    let c = &ctx.accounts.card;
    require!(c.legs[..c.leg_count as usize].iter().all(|l| l.held == 0 && l.parked == 0) && c.cash == 0, ErrorCode::NotEmpty);
    Ok(())
}
