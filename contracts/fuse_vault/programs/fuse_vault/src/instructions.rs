//! FUSE Vault v0.1 instructions. Custody: SOL sits in the `vault_sol` PDA (system account, no private key); only these
//! instructions move it. v0.1 has no pool adapters yet, so NAV = idle SOL (position values stay 0 until the audited
//! Raydium / Orca / Meteora adapters land — there is deliberately no way to "report" a value that wasn't deployed).
use anchor_lang::prelude::*;
use anchor_lang::system_program::{transfer, Transfer};

use crate::{constants::*, error::ErrorCode, math, state::*};

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct VaultConfig {
    pub keeper: Pubkey,
    pub fee_wallet: Pubkey,
    pub pools: Vec<PoolSlot>,
    pub mgmt_bps: u16,
    pub perf_bps: u16,
}

fn apply_config(v: &mut Vault, cfg: &VaultConfig) -> Result<()> {
    require!((1..=MAX_POOLS).contains(&cfg.pools.len()), ErrorCode::BadPoolCount);
    require!(cfg.mgmt_bps <= MAX_MGMT_BPS && cfg.perf_bps <= MAX_PERF_BPS, ErrorCode::FeeTooHigh);
    for p in &cfg.pools {
        require!(p.weight_bps > 0, ErrorCode::BadWeight);
        require!(p.cap_bps <= MAX_CAP_BPS, ErrorCode::CapTooHigh);
    }
    v.keeper = cfg.keeper;
    v.fee_wallet = cfg.fee_wallet;
    v.pools = [PoolSlot::default(); MAX_POOLS];
    for (i, p) in cfg.pools.iter().enumerate() { v.pools[i] = *p; }
    v.pool_count = cfg.pools.len() as u8;
    v.mgmt_bps = cfg.mgmt_bps;
    v.perf_bps = cfg.perf_bps;
    Ok(())
}

/// Idle SOL the vault can pay out: balance minus the rent-exempt floor of the PDA.
pub fn buffer(vault_sol: &AccountInfo) -> Result<u64> {
    let floor = Rent::get()?.minimum_balance(0);
    Ok(vault_sol.lamports().saturating_sub(floor))
}

pub fn nav(v: &Vault, vault_sol: &AccountInfo) -> Result<u64> {
    let deployed: u64 = v.position_values.iter().try_fold(0u64, |a, x| a.checked_add(*x)).ok_or(ErrorCode::Overflow)?;
    buffer(vault_sol)?.checked_add(deployed).ok_or_else(|| error!(ErrorCode::Overflow))
}

fn pay_out<'info>(v: &Account<'info, Vault>, vault_sol: &AccountInfo<'info>, to: &AccountInfo<'info>, sys: &Program<'info, System>, lamports: u64) -> Result<()> {
    let key = v.key();
    let seeds: &[&[u8]] = &[VAULT_SOL_SEED, key.as_ref(), &[v.sol_bump]];
    transfer(CpiContext::new_with_signer(sys.key(), Transfer { from: vault_sol.clone(), to: to.clone() }, &[seeds]), lamports)
}

#[derive(Accounts)]
#[instruction(vault_id: u64)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(init, payer = admin, space = 8 + Vault::INIT_SPACE, seeds = [VAULT_SEED, &vault_id.to_le_bytes()], bump)]
    pub vault: Account<'info, Vault>,
    /// CHECK: system-owned PDA that holds the vault's SOL; funded with the rent-exempt floor here.
    #[account(mut, seeds = [VAULT_SOL_SEED, vault.key().as_ref()], bump)]
    pub vault_sol: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}

pub fn initialize(ctx: Context<Initialize>, vault_id: u64, cfg: VaultConfig) -> Result<()> {
    let v = &mut ctx.accounts.vault;
    v.admin = ctx.accounts.admin.key();
    v.vault_id = vault_id;
    v.bump = ctx.bumps.vault;
    v.sol_bump = ctx.bumps.vault_sol;
    v.last_fee_ts = Clock::get()?.unix_timestamp;
    apply_config(v, &cfg)?;
    let floor = Rent::get()?.minimum_balance(0);
    let have = ctx.accounts.vault_sol.lamports();
    if have < floor {
        transfer(CpiContext::new(ctx.accounts.system_program.key(), Transfer { from: ctx.accounts.admin.to_account_info(), to: ctx.accounts.vault_sol.to_account_info() }), floor - have)?;
    }
    Ok(())
}

#[derive(Accounts)]
pub struct AdminOnly<'info> {
    pub admin: Signer<'info>,
    #[account(mut, has_one = admin @ ErrorCode::Unauthorized)]
    pub vault: Account<'info, Vault>,
}

pub fn configure(ctx: Context<AdminOnly>, cfg: VaultConfig) -> Result<()> {
    apply_config(&mut ctx.accounts.vault, &cfg)
}

pub fn set_paused(ctx: Context<AdminOnly>, paused: bool) -> Result<()> {
    ctx.accounts.vault.paused = paused;
    Ok(())
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub vault: Account<'info, Vault>,
    /// CHECK: the vault's SOL PDA (seeds checked).
    #[account(mut, seeds = [VAULT_SOL_SEED, vault.key().as_ref()], bump = vault.sol_bump)]
    pub vault_sol: UncheckedAccount<'info>,
    #[account(init_if_needed, payer = user, space = 8 + Depositor::INIT_SPACE, seeds = [DEPOSITOR_SEED, vault.key().as_ref(), user.key().as_ref()], bump)]
    pub depositor: Account<'info, Depositor>,
    pub system_program: Program<'info, System>,
}

pub fn deposit(ctx: Context<Deposit>, lamports: u64) -> Result<()> {
    require!(lamports > 0, ErrorCode::ZeroAmount);
    require!(!ctx.accounts.vault.paused, ErrorCode::Paused);
    let nav_before = nav(&ctx.accounts.vault, &ctx.accounts.vault_sol.to_account_info())?;
    let shares = math::shares_for_deposit(lamports, ctx.accounts.vault.total_shares, nav_before).ok_or(ErrorCode::Overflow)?;
    require!(shares > 0, ErrorCode::ZeroAmount);
    transfer(CpiContext::new(ctx.accounts.system_program.key(), Transfer { from: ctx.accounts.user.to_account_info(), to: ctx.accounts.vault_sol.to_account_info() }), lamports)?;
    let d = &mut ctx.accounts.depositor;
    d.owner = ctx.accounts.user.key();
    d.vault = ctx.accounts.vault.key();
    d.bump = ctx.bumps.depositor;
    d.shares = d.shares.checked_add(shares).ok_or(ErrorCode::Overflow)?;
    let v = &mut ctx.accounts.vault;
    v.total_shares = v.total_shares.checked_add(shares).ok_or(ErrorCode::Overflow)?;
    emit!(Deposited { user: d.owner, lamports, shares });
    Ok(())
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut)]
    pub vault: Account<'info, Vault>,
    /// CHECK: the vault's SOL PDA (seeds checked).
    #[account(mut, seeds = [VAULT_SOL_SEED, vault.key().as_ref()], bump = vault.sol_bump)]
    pub vault_sol: UncheckedAccount<'info>,
    #[account(mut, seeds = [DEPOSITOR_SEED, vault.key().as_ref(), user.key().as_ref()], bump = depositor.bump, has_one = owner @ ErrorCode::Unauthorized)]
    pub depositor: Account<'info, Depositor>,
    /// CHECK: must equal the signer (enforced by has_one on depositor).
    pub owner: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}

/// Withdrawals work even while paused (pause only stops new deposits) — users can always leave with idle SOL.
pub fn withdraw(ctx: Context<Withdraw>, shares: u64) -> Result<()> {
    require!(shares > 0, ErrorCode::ZeroAmount);
    require_keys_eq!(ctx.accounts.owner.key(), ctx.accounts.user.key(), ErrorCode::Unauthorized);
    require!(ctx.accounts.depositor.shares >= shares, ErrorCode::InsufficientShares);
    let vault_sol = ctx.accounts.vault_sol.to_account_info();
    let nav_now = nav(&ctx.accounts.vault, &vault_sol)?;
    let out = math::lamports_for_shares(shares, ctx.accounts.vault.total_shares, nav_now).ok_or(ErrorCode::Overflow)?;
    require!(out <= buffer(&vault_sol)?, ErrorCode::InsufficientBuffer);
    pay_out(&ctx.accounts.vault, &vault_sol, &ctx.accounts.user.to_account_info(), &ctx.accounts.system_program, out)?;
    ctx.accounts.depositor.shares -= shares;
    let v = &mut ctx.accounts.vault;
    v.total_shares = v.total_shares.checked_sub(shares).ok_or(ErrorCode::Overflow)?;
    emit!(Withdrawn { user: ctx.accounts.user.key(), lamports: out, shares });
    Ok(())
}

#[derive(Accounts)]
pub struct CollectFees<'info> {
    #[account(mut)]
    pub vault: Account<'info, Vault>,
    /// CHECK: the vault's SOL PDA (seeds checked).
    #[account(mut, seeds = [VAULT_SOL_SEED, vault.key().as_ref()], bump = vault.sol_bump)]
    pub vault_sol: UncheckedAccount<'info>,
    /// CHECK: must be the configured fee wallet (checked below); receives SOL only.
    #[account(mut)]
    pub fee_wallet: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}

/// Permissionless crank: anyone can trigger it, but fees can only ever go to the configured fee wallet.
pub fn collect_fees(ctx: Context<CollectFees>) -> Result<()> {
    require_keys_eq!(ctx.accounts.fee_wallet.key(), ctx.accounts.vault.fee_wallet, ErrorCode::WrongFeeWallet);
    let now = Clock::get()?.unix_timestamp;
    let vault_sol = ctx.accounts.vault_sol.to_account_info();
    let v = &ctx.accounts.vault;
    let secs = u64::try_from(now.saturating_sub(v.last_fee_ts)).unwrap_or(0);
    let (fee, hwm) = math::fees(nav(v, &vault_sol)?, v.total_shares, v.hwm_pps, v.mgmt_bps, v.perf_bps, secs).ok_or(ErrorCode::Overflow)?;
    require!(fee <= buffer(&vault_sol)?, ErrorCode::InsufficientBuffer);
    if fee > 0 {
        pay_out(&ctx.accounts.vault, &vault_sol, &ctx.accounts.fee_wallet.to_account_info(), &ctx.accounts.system_program, fee)?;
    }
    let v = &mut ctx.accounts.vault;
    v.hwm_pps = hwm;
    v.last_fee_ts = now;
    emit!(FeesCollected { lamports: fee, fee_wallet: v.fee_wallet });
    Ok(())
}

#[event]
pub struct Deposited { pub user: Pubkey, pub lamports: u64, pub shares: u64 }
#[event]
pub struct Withdrawn { pub user: Pubkey, pub lamports: u64, pub shares: u64 }
#[event]
pub struct FeesCollected { pub lamports: u64, pub fee_wallet: Pubkey }
