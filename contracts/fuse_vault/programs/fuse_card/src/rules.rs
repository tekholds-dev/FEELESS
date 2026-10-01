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
    Ok(())
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
        REASON_SL => t.auto_tp && leg.sl_bps != 0,
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
        let cmp = Toggles { auto_compound: true, profit_at_bps: 5_000, ..Default::default() };
        assert!(keeper_allowed(&cmp, &l, REASON_COMPOUND).is_ok());                          // auto-compound runs every time once on
        assert_eq!(keeper_allowed(&on, &l, REASON_COMPOUND), Err(ErrorCode::AutomationOff));
    }
}
