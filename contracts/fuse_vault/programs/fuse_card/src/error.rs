use anchor_lang::prelude::*;

#[error_code]
#[derive(PartialEq)]
pub enum ErrorCode {
    #[msg("A card needs 1 to 12 legs")]
    BadLegCount,
    #[msg("Trader cards hold at most 3 pools + 3 runners")]
    TooManyLegs,
    #[msg("A coin can only be in a card once")]
    DuplicateLeg,
    #[msg("Leg kind must be pool (0) or runner (1)")]
    BadLegKind,
    #[msg("Take-profit must be off or +5% to +1000%")]
    BadTakeProfit,
    #[msg("Stop-loss must be off or -5% to -95%")]
    BadStopLoss,
    #[msg("Auto-profit must be off or one of +25/+50/+100/+200%")]
    BadProfitLevel,
    #[msg("No such leg on this card")]
    BadLeg,
    #[msg("That token account is not the card's account for this coin")]
    BadCardVault,
    #[msg("Coins can only go back to the card owner's own token account")]
    NotOwnerAccount,
    #[msg("Wrong token mint for this leg")]
    WrongMint,
    #[msg("Unsupported token program")]
    BadTokenProgram,
    #[msg("More than the card holds for this leg")]
    InsufficientHeld,
    #[msg("Automation is off on this card (the owner didn't enable it)")]
    AutomationOff,
    #[msg("Keeper actions are paused")]
    Paused,
    #[msg("Empty every leg before closing the card")]
    NotEmpty,
    #[msg("Bad reason code")]
    BadReason,
    #[msg("Math overflow")]
    Overflow,
    #[msg("Stop mode must be payout (0), park (1) or hold (2)")]
    BadSlMode,
    #[msg("Only the configured swap program may be used")]
    BadSwapProgram,
    #[msg("Pool does not match this leg / quote coin")]
    BadPool,
    #[msg("The price trigger is not hit on-chain")]
    NotTriggered,
    #[msg("min_out is looser than the pool price minus the allowed slippage")]
    SlippageTooLoose,
    #[msg("The swap paid less than min_out")]
    ShortFill,
    #[msg("Not enough parked / cash quote")]
    InsufficientQuote,
    #[msg("Slippage cap is at most 3%")]
    BadSlippage,
}
