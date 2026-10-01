//! Share + fee math. Mirrors backend/fuse_vault.py (shares_for_deposit, withdraw, fees) — change both together.
use crate::constants::{PPS_SCALE, YEAR_SECONDS};

/// Shares minted for a deposit: 1:1 on the first deposit, else at NAV (no dilution of existing holders).
pub fn shares_for_deposit(lamports: u64, total_shares: u64, nav: u64) -> Option<u64> {
    if lamports == 0 { return Some(0); }
    if total_shares == 0 || nav == 0 { return Some(lamports); }
    u64::try_from((lamports as u128).checked_mul(total_shares as u128)?.checked_div(nav as u128)?).ok()
}

/// Lamports owed for `shares` at NAV.
pub fn lamports_for_shares(shares: u64, total_shares: u64, nav: u64) -> Option<u64> {
    if total_shares == 0 { return Some(0); }
    u64::try_from((shares as u128).checked_mul(nav as u128)?.checked_div(total_shares as u128)?).ok()
}

/// (fee lamports, new high-water mark pps). Management accrues by time on NAV; performance is charged only on gains
/// above the high-water mark. The first collection just sets the mark.
pub fn fees(nav: u64, total_shares: u64, hwm_pps: u128, mgmt_bps: u16, perf_bps: u16, seconds: u64) -> Option<(u64, u128)> {
    if total_shares == 0 || nav == 0 { return Some((0, hwm_pps)); }
    let nav = nav as u128; let ts = total_shares as u128;
    let mgmt = nav.checked_mul(mgmt_bps as u128)?.checked_mul(seconds as u128)? / 10_000 / YEAR_SECONDS;
    let after_mgmt = nav.checked_sub(mgmt)?;
    let pps = after_mgmt.checked_mul(PPS_SCALE)? / ts;
    if hwm_pps == 0 { return Some((u64::try_from(mgmt).ok()?, pps)); }
    let perf = if pps > hwm_pps { (pps - hwm_pps).checked_mul(ts)? / PPS_SCALE * perf_bps as u128 / 10_000 } else { 0 };
    let new_pps = after_mgmt.checked_sub(perf)?.checked_mul(PPS_SCALE)? / ts;
    Some((u64::try_from(mgmt + perf).ok()?, new_pps.max(hwm_pps)))
}

#[cfg(test)]
mod tests {
    use super::*;
    const YEAR: u64 = 365 * 86_400;

    #[test]
    fn deposits_mint_at_nav() {
        assert_eq!(shares_for_deposit(10, 0, 0), Some(10));
        assert_eq!(shares_for_deposit(10, 10, 20), Some(5));
        assert_eq!(lamports_for_shares(5, 10, 16), Some(8));
    }

    #[test]
    fn fees_match_the_python_engine() {
        // flat year, 2% management: 2 of 100
        let (fee, hwm) = fees(100_000_000, 100_000_000, PPS_SCALE, 200, 1000, YEAR).unwrap();
        assert_eq!(fee, 2_000_000); assert_eq!(hwm, PPS_SCALE);
        // +20%, 10% performance, no management: 2 of 120
        let (fee, hwm) = fees(120_000_000, 100_000_000, PPS_SCALE, 0, 1000, 0).unwrap();
        assert_eq!(fee, 2_000_000); assert_eq!(hwm, PPS_SCALE * 118 / 100);
        // below the high-water mark: nothing
        assert_eq!(fees(110_000_000, 100_000_000, PPS_SCALE * 118 / 100, 0, 1000, 0).unwrap().0, 0);
        // first collection only sets the mark
        assert_eq!(fees(100, 100, 0, 0, 1000, 0).unwrap(), (0, PPS_SCALE));
    }
}
