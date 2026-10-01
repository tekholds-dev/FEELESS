//! TEST ONLY — a tiny constant-product AMM (x·y = k, 0.3% fee) so the FUSE Card keeper can be tested end to end on a local
//! validator. It mirrors what a real adapter must provide (two vaults owned by the pool PDA, swap with min_out). Never
//! deployed anywhere. Layout of `Pool` is read by fuse_card for its on-chain price check — keep them in sync.
use anchor_lang::prelude::*;
use anchor_lang::solana_program::{instruction::{AccountMeta, Instruction}, program::{invoke, invoke_signed}};

declare_id!("HvN8e8WZQ3vsLfAcqn83zvhRRnYdf2bHiyRcFDwtq7Wp");

pub const FEE_BPS: u64 = 30;

#[account]
#[derive(InitSpace)]
pub struct Pool {
    pub mint_a: Pubkey,   // the coin
    pub mint_b: Pubkey,   // the quote (wSOL on mainnet)
    pub vault_a: Pubkey,
    pub vault_b: Pubkey,
    pub bump: u8,
}

#[error_code]
pub enum AmmError {
    #[msg("Slippage: output below min_out")]
    Slippage,
    #[msg("Wrong vault")]
    BadVault,
    #[msg("Math overflow")]
    Overflow,
}

fn amount_of(ai: &AccountInfo) -> u64 {
    let d = ai.try_borrow_data().unwrap();
    u64::from_le_bytes(d[64..72].try_into().unwrap())
}

/// Plain SPL Token Transfer (ix 3) — the test mints are classic SPL.
fn transfer<'info>(tp: &AccountInfo<'info>, from: &AccountInfo<'info>, to: &AccountInfo<'info>, auth: &AccountInfo<'info>, amount: u64, seeds: Option<&[&[u8]]>) -> Result<()> {
    let mut data = vec![3u8];
    data.extend_from_slice(&amount.to_le_bytes());
    let ix = Instruction { program_id: tp.key(), accounts: vec![AccountMeta::new(from.key(), false), AccountMeta::new(to.key(), false), AccountMeta::new_readonly(auth.key(), true)], data };
    let infos = [from.clone(), to.clone(), auth.clone(), tp.clone()];
    match seeds { Some(s) => invoke_signed(&ix, &infos, &[s])?, None => invoke(&ix, &infos)? }
    Ok(())
}

/// Constant-product output after the fee (same formula fuse_card uses for its expected-out check).
pub fn quote_out(amount_in: u64, reserve_in: u64, reserve_out: u64) -> u64 {
    let a = amount_in as u128 * (10_000 - FEE_BPS) as u128;
    ((a * reserve_out as u128) / (reserve_in as u128 * 10_000 + a)) as u64
}

#[program]
pub mod mock_amm {
    use super::*;

    pub fn init_pool(ctx: Context<InitPool>, vault_a: Pubkey, vault_b: Pubkey) -> Result<()> {
        let p = &mut ctx.accounts.pool;
        p.mint_a = ctx.accounts.mint_a.key();
        p.mint_b = ctx.accounts.mint_b.key();
        p.vault_a = vault_a;
        p.vault_b = vault_b;
        p.bump = ctx.bumps.pool;
        Ok(())
    }

    /// a_to_b = sell the coin for quote. The trader (any signer, e.g. a card PDA via CPI) pays `amount_in` from `user_in`.
    pub fn swap(ctx: Context<Swap>, amount_in: u64, min_out: u64, a_to_b: bool) -> Result<()> {
        let a = &ctx.accounts;
        require!(a.vault_a.key() == a.pool.vault_a && a.vault_b.key() == a.pool.vault_b, AmmError::BadVault);
        let (vin, vout) = if a_to_b { (&a.vault_a, &a.vault_b) } else { (&a.vault_b, &a.vault_a) };
        let out = quote_out(amount_in, amount_of(vin), amount_of(vout));
        require!(out >= min_out && out > 0, AmmError::Slippage);
        transfer(&a.token_program, &a.user_in, vin, &a.user, amount_in, None)?;
        let (ma, mb, bump) = (a.pool.mint_a, a.pool.mint_b, a.pool.bump);
        let seeds: &[&[u8]] = &[b"pool", ma.as_ref(), mb.as_ref(), &[bump]];
        transfer(&a.token_program, vout, &a.user_out, &a.pool.to_account_info(), out, Some(seeds))?;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitPool<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    /// CHECK: coin mint
    pub mint_a: UncheckedAccount<'info>,
    /// CHECK: quote mint
    pub mint_b: UncheckedAccount<'info>,
    #[account(init, payer = payer, space = 8 + Pool::INIT_SPACE, seeds = [b"pool", mint_a.key().as_ref(), mint_b.key().as_ref()], bump)]
    pub pool: Account<'info, Pool>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Swap<'info> {
    pub user: Signer<'info>,
    pub pool: Account<'info, Pool>,
    /// CHECK: checked against the pool
    #[account(mut)]
    pub vault_a: UncheckedAccount<'info>,
    /// CHECK: checked against the pool
    #[account(mut)]
    pub vault_b: UncheckedAccount<'info>,
    /// CHECK: the trader's source token account (the token program enforces the authority)
    #[account(mut)]
    pub user_in: UncheckedAccount<'info>,
    /// CHECK: the trader's destination token account
    #[account(mut)]
    pub user_out: UncheckedAccount<'info>,
    /// CHECK: SPL Token
    pub token_program: UncheckedAccount<'info>,
}
