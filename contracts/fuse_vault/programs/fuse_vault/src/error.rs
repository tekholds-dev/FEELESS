use anchor_lang::prelude::*;

#[error_code]
pub enum ErrorCode {
    #[msg("Only the vault admin can do that.")]
    Unauthorized,
    #[msg("A vault holds 1 to 3 pools.")]
    BadPoolCount,
    #[msg("Fee above the on-chain cap.")]
    FeeTooHigh,
    #[msg("Pool cap above 10% of the pool.")]
    CapTooHigh,
    #[msg("Pool weights must be positive.")]
    BadWeight,
    #[msg("Amount must be greater than zero.")]
    ZeroAmount,
    #[msg("Vault is paused.")]
    Paused,
    #[msg("Not enough shares.")]
    InsufficientShares,
    #[msg("Not enough idle SOL in the vault buffer; the keeper must unwind a position first.")]
    InsufficientBuffer,
    #[msg("Fee wallet does not match the vault config.")]
    WrongFeeWallet,
    #[msg("Math overflow.")]
    Overflow,
}
