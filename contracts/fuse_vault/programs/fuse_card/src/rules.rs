//! Pure rule checks (unit-tested with `cargo test -p fuse_card --lib`). Every number lives in constants.rs.
use crate::constants::*;
use crate::error::ErrorCode;
use crate::state::{Leg, Toggles};

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct LegSpec {
    pub mint: [u8; 32],
    pub kind: u8,
    pub tp_bps: u32,
    pub sl_bps: u16,
}

pub fn check_limits(tp_bps: u32, sl_bps: u16) -> Result<(), ErrorCode> {
    if tp_bps != 0 && !(TP_MIN_BPS..=TP_MAX_BPS).contains(&tp_bps) {
        return Err(ErrorCode::BadTakeProfit);
    }
    if sl_bps != 0 && !(SL_MIN_BPS..=SL_MAX_BPS).contains(&sl_bps) {
        return Err(ErrorCode::BadStopLoss);
    }
    Ok(())
}

pub fn check_toggles(t: &Toggles) -> Result<(), ErrorCode> {
    if t.profit_at_bps != 0 && !PROFIT_LEVELS_BPS.contains(&t.profit_at_bps) {
        return Err(ErrorCode::BadProfitLevel);
    }
    if t.sl_mode > SL_HOLD {
        return Err(ErrorCode::BadSlMode);
    }
    Ok(())
}

/// Constant-product output after the fee — the pool's own expected price for this trade.
pub fn expected_out(amount_in: u64, reserve_in: u64, reserve_out: u64) -> u64 {
    let a = amount_in as u128 * (10_000 - AMM_FEE_BPS) as u128;
    let d = reserve_in as u128 * 10_000 + a;
    if d == 0 { 0 } else { ((a * reserve_out as u128) / d) as u64 }
}

/// The keeper's min_out may not be looser than the pool's expected output minus the capped slippage.
pub fn min_out_ok(min_out: u64, expected: u64, max_slippage_bps: u16) -> bool {
    let floor = expected as u128 * (10_000 - max_slippage_bps.min(MAX_SLIPPAGE_BPS) as u128) / 10_000;
    min_out as u128 >= floor && min_out > 0
}

/// Price trigger, checked ON-CHAIN from pool reserves (spot = res_quote / res_coin) vs the owner's entry
/// (entry_quote / entry_coin). Cross-multiplied in u128 — no floats, no keeper-supplied price.
///   up_bps:   spot ≥ entry × (1 + up)      (take-profit / profit level / compound)
///   down_bps: spot ≤ entry × (1 − down)    (stop-loss)
///   back:     spot ≥ entry                 (park → buy back)
pub fn spot_vs_entry(res_coin: u64, res_quote: u64, entry_quote: u64, entry_coin: u64) -> (u128, u128) {
    (res_quote as u128 * entry_coin as u128, entry_quote as u128 * res_coin as u128)   // (spot·k, entry·k)
}
pub fn hit_up(res_coin: u64, res_quote: u64, entry_quote: u64, entry_coin: u64, up_bps: u32) -> bool {
    let (s, e) = spot_vs_entry(res_coin, res_quote, entry_quote, entry_coin);
    entry_coin > 0 && up_bps > 0 && s * 10_000 >= e * (10_000 + up_bps as u128)
}
pub fn hit_down(res_coin: u64, res_quote: u64, entry_quote: u64, entry_coin: u64, down_bps: u16) -> bool {
    let (s, e) = spot_vs_entry(res_coin, res_quote, entry_quote, entry_coin);
    entry_coin > 0 && down_bps > 0 && s * 10_000 <= e * (10_000 - down_bps as u128)
}
pub fn back_at_entry(res_coin: u64, res_quote: u64, entry_quote: u64, entry_coin: u64) -> bool {
    let (s, e) = spot_vs_entry(res_coin, res_quote, entry_quote, entry_coin);
    entry_coin > 0 && s >= e
}

/// Leg mix: traders 3 pools + 3 runners; Cmd Ctr (admin) up to 12 in any mix; never the same coin twice.
pub fn check_legs(legs: &[LegSpec], admin: bool) -> Result<(), ErrorCode> {
    if legs.is_empty() || legs.len() > MAX_LEGS {
        return Err(ErrorCode::BadLegCount);
    }
    let (mut pools, mut runners) = (0u8, 0u8);
    for (i, l) in legs.iter().enumerate() {
        match l.kind {
            LEG_POOL => pools += 1,
            LEG_RUNNER => runners += 1,
            _ => return Err(ErrorCode::BadLegKind),
        }
        check_limits(l.tp_bps, l.sl_bps)?;
        if legs[..i].iter().any(|x| x.mint == l.mint) {
            return Err(ErrorCode::DuplicateLeg);
        }
    }
    if !admin && (pools > USER_MAX_POOLS || runners > USER_MAX_RUNNERS) {
        return Err(ErrorCode::TooManyLegs);
    }
    Ok(())
}

/// The keeper may only act when the owner switched automation on: card auto-TP / auto-profit for reason PROFIT,
/// or that leg's own TP / SL for reasons TP / SL.
pub fn keeper_allowed(t: &Toggles, leg: &Leg, reason: u8) -> Result<(), ErrorCode> {
    let ok = match reason {
        REASON_TP => t.auto_tp && leg.tp_bps != 0,
        REASON_SL => t.auto_tp && leg.sl_bps != 0 && t.sl_mode != SL_HOLD,   // hold = never sold on a stop
        REASON_REBUY => t.auto_tp && t.sl_mode == SL_PARK && leg.parked > 0,
        REASON_PROFIT => t.auto_tp && t.profit_at_bps != 0,
        REASON_COMPOUND => t.auto_compound && t.profit_at_bps != 0,   // standing order: no click each time
        _ => return Err(ErrorCode::BadReason),
    };
    if ok { Ok(()) } else { Err(ErrorCode::AutomationOff) }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn leg(m: u8, kind: u8) -> LegSpec { LegSpec { mint: [m; 32], kind, tp_bps: 0, sl_bps: 0 } }

    #[test]
    fn trader_cards_cap_at_3_pools_plus_3_runners_admin_at_12_any_mix() {
        let mut v: Vec<LegSpec> = (0..3).map(|i| leg(i, LEG_POOL)).chain((3..6).map(|i| leg(i, LEG_RUNNER))).collect();
        assert!(check_legs(&v, false).is_ok());
        v.push(leg(9, LEG_RUNNER));
        assert_eq!(check_legs(&v, false), Err(ErrorCode::TooManyLegs));
        let twelve: Vec<LegSpec> = (0..12).map(|i| leg(i, LEG_RUNNER)).collect();
        assert!(check_legs(&twelve, true).is_ok());
        let thirteen: Vec<LegSpec> = (0..13).map(|i| leg(i, LEG_POOL)).collect();
        assert_eq!(check_legs(&thirteen, true), Err(ErrorCode::BadLegCount));
        assert_eq!(check_legs(&[], true), Err(ErrorCode::BadLegCount));
    }

    #[test]
    fn duplicate_coins_bad_kinds_and_limits_are_refused() {
        assert_eq!(check_legs(&[leg(1, LEG_POOL), leg(1, LEG_RUNNER)], true), Err(ErrorCode::DuplicateLeg));
        assert_eq!(check_legs(&[leg(1, 7)], true), Err(ErrorCode::BadLegKind));
        assert_eq!(check_limits(400, 0), Err(ErrorCode::BadTakeProfit));
        assert_eq!(check_limits(0, 9_600), Err(ErrorCode::BadStopLoss));
        assert!(check_limits(5_000, 2_500).is_ok() && check_limits(0, 0).is_ok());
    }

    #[test]
    fn profit_levels_are_the_hard_coded_ones() {
        assert!(check_toggles(&Toggles { profit_at_bps: 5_000, ..Default::default() }).is_ok());
        assert_eq!(check_toggles(&Toggles { profit_at_bps: 7_500, ..Default::default() }), Err(ErrorCode::BadProfitLevel));
        assert_eq!(check_toggles(&Toggles { sl_mode: 3, ..Default::default() }), Err(ErrorCode::BadSlMode));
    }

    #[test]
    fn price_triggers_come_from_pool_reserves_not_the_keeper() {
        // entry: 1,000 quote for 1,000,000 coin (price 0.001). Pool now 2,000,000 coin : 3,000 quote = 0.0015 (+50%)
        assert!(hit_up(2_000_000, 3_000, 1_000, 1_000_000, 5_000));          // +50% TP hit
        assert!(!hit_up(2_000_000, 3_000, 1_000, 1_000_000, 10_000));        // +100% not yet
        assert!(hit_down(2_000_000, 1_400, 1_000, 1_000_000, 2_500));        // 0.0007 = −30% ≤ −25% stop
        assert!(!hit_down(2_000_000, 1_600, 1_000, 1_000_000, 2_500));       // −20%: no stop
        assert!(back_at_entry(1_000_000, 1_000, 1_000, 1_000_000) && !back_at_entry(1_000_000, 999, 1_000, 1_000_000));
        assert!(!hit_up(1, 1, 0, 0, 5_000) && !hit_down(1, 1, 0, 0, 2_500));  // no entry = never triggers
    }

    #[test]
    fn keeper_min_out_cannot_be_looser_than_the_pool_price_minus_capped_slippage() {
        let exp = expected_out(1_000, 1_000_000, 1_000_000);                  // ≈ 996 after 0.3% fee
        assert!((995..=997).contains(&exp));
        assert!(min_out_ok(exp * 99 / 100, exp, 100));                        // 1% under, cap 1% → ok
        assert!(!min_out_ok(exp * 95 / 100, exp, 100));                       // 5% under → refused
        assert!(!min_out_ok(exp * 90 / 100, exp, 5_000));                     // config can't loosen past the 3% hard cap
        assert!(!min_out_ok(0, 0, 100));
    }

    #[test]
    fn keeper_only_acts_when_the_owner_switched_it_on() {
        let l = Leg { tp_bps: 5_000, ..Default::default() };
        let off = Toggles::default();
        let on = Toggles { auto_tp: true, ..Default::default() };
        assert_eq!(keeper_allowed(&off, &l, REASON_TP), Err(ErrorCode::AutomationOff));
        assert!(keeper_allowed(&on, &l, REASON_TP).is_ok());
        assert_eq!(keeper_allowed(&on, &l, REASON_SL), Err(ErrorCode::AutomationOff));       // no SL set on this leg
        assert_eq!(keeper_allowed(&on, &l, REASON_PROFIT), Err(ErrorCode::AutomationOff));   // no profit level set
        assert_eq!(keeper_allowed(&on, &l, 9), Err(ErrorCode::BadReason));
        let hold = Toggles { auto_tp: true, sl_mode: SL_HOLD, ..Default::default() };
        let sl = Leg { sl_bps: 2_500, ..Default::default() };
        assert_eq!(keeper_allowed(&hold, &sl, REASON_SL), Err(ErrorCode::AutomationOff));     // hold: never sold on a stop
        assert!(keeper_allowed(&on, &sl, REASON_SL).is_ok());
        let park = Toggles { auto_tp: true, sl_mode: SL_PARK, ..Default::default() };
        assert_eq!(keeper_allowed(&park, &sl, REASON_REBUY), Err(ErrorCode::AutomationOff));  // nothing parked yet
        assert!(keeper_allowed(&park, &Leg { parked: 5, ..sl }, REASON_REBUY).is_ok());
        assert_eq!(keeper_allowed(&on, &Leg { parked: 5, ..sl }, REASON_REBUY), Err(ErrorCode::AutomationOff)); // not park mode
        let cmp = Toggles { auto_compound: true, profit_at_bps: 5_000, ..Default::default() };
        assert!(keeper_allowed(&cmp, &l, REASON_COMPOUND).is_ok());                          // auto-compound runs every time once on
        assert_eq!(keeper_allowed(&on, &l, REASON_COMPOUND), Err(ErrorCode::AutomationOff));
    }
}
