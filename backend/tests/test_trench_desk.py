"""⏱ THE TRENCH DESK (owner's one-and-done spec, 2026-10-12): ≤ 6h · < $200K universe, 5-minute rounds with a three-round decision,
event wakeups, fresh-first priority, cost-aware sizing, real-money desk records, one execution path."""
from pathlib import Path

import agents as ag
import judge_review as jr
import market_wake as mw
import office as of
import office_edge as oe
import opportunity as opp
import real_memory as rm
import trench_rounds as tr

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()
FRONT = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'components' / 'command'


def row(m='M', age=1.0, mc=80_000, d5=2.0, buy=60, liq=30_000, px=1.0, safe=True, **k):
    return {'mint': m, 'symbol': m, 'px': px, 'nums': {'v5': 5_000, 'pace': 1.5, 'liq': liq, 'd5': d5, 'buy': buy},
            'vitals': {'safe': safe, 'mcap': mc, 'liq': liq, 'ageH': age, 'rug': 5}, **k}


# ── the universe ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_over_6h_cannot_get_a_new_entry_and_under_6h_can():
    assert opp.hard_fail(row(age=5.9)) is None
    assert 'no new entry past 6h' in opp.hard_fail(row(age=6.5))
    assert ag.in_lane({'mcap': 80_000, 'ageH': 5.0, 'vol1h': 5_000}) and not ag.in_lane({'mcap': 80_000, 'ageH': 7.0, 'vol1h': 5_000})


def test_unknown_age_or_cap_never_masquerades_as_valid_and_the_cap_is_under_200k():
    assert opp.hard_fail(row(age=None)) == 'launch age unknown'
    assert opp.hard_fail(row(mc=None)) == 'market cap unknown'
    assert '≥ $200K' in opp.hard_fail(row(mc=200_000)) and opp.hard_fail(row(mc=199_000)) is None
    assert not ag.in_lane({'mcap': 80_000, 'vol1h': 5_000})            # no age → not in the lane


def test_a_0_to_5_minute_launch_gets_the_top_priority():
    assert opp.fresh_bucket(row(age=3 / 60))[0].startswith('EXTREME 0–5m')
    assert opp.fresh_bucket(row(age=3 / 60))[1] > opp.fresh_bucket(row(age=0.2))[1] > opp.fresh_bucket(row(age=2))[1] > opp.fresh_bucket(row(age=5))[1]
    assert oe.fresh_key({'ageH': 3 / 60}) < oe.fresh_key({'ageH': 0.2}) < oe.fresh_key({'ageH': 2})
    assert list(oe.candle_order([{'mint': 'OLDISH', 'pairAddress': 'P1', 'ageH': 4, 'vol5m': 50_000}, {'mint': 'NEWB', 'pairAddress': 'P2', 'ageH': 0.03, 'vol5m': 900}], {}, {'H': 'Ph'}))[:2] == ['NEWB', 'OLDISH']   # a new Pump coin gets real candles first, held last


def test_a_limited_history_early_coin_still_qualifies_and_an_old_coin_cannot_outrank_it_on_history():
    young = row(age=4 / 60, chart={'state': 'EARLY', 'src': 'candles', 'n': 4, 'q': {'state': 'LIMITED_HISTORY'}})
    assert opp.hard_fail(young) is None and opp.tier_of(opp.score(young)[0]) is not None
    assert opp.hard_fail(row(age=300, liq=500_000)) is not None        # history alone never wins a seat: it is not in the universe


def test_volume_velocity_not_lifetime_volume():
    a = {**row('NEW', age=3 / 60), 'vitals': {**row()['vitals'], 'ageH': 3 / 60, 'vol1h': 20_000}}
    b = {**row('OLD', age=5.5), 'vitals': {**row()['vitals'], 'ageH': 5.5, 'vol1h': 60_000}}
    assert opp.velocity(a)[0] > opp.velocity(b)[0]


# ── safety vs warnings ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_hard_safety_blocks_and_a_soft_warning_only_lowers_the_score():
    assert opp.hard_fail(row(safe=False)) == 'failed the holder safety scan'
    assert opp.hard_fail({**row(), 'mp': 'COLLAPSE'}).startswith('chart phase')
    plain, warned = opp.score(row())[0], opp.score({**row(), 'warns': [['ran']]})[0]
    assert warned < plain and opp.hard_fail({**row(), 'warns': [['ran']]}) is None
    late = opp.score({**row(), 'mp': 'LATE FOMO'})[0]
    assert late < plain and opp.hard_fail({**row(), 'mp': 'LATE FOMO'}) is None   # LATE FOMO is avoided by score, not a veto


def test_trench_phases_prefer_the_early_ones():
    assert mw.market_phase({'state': 'EARLY'}) == 'EARLY ACCELERATION' and mw.market_phase({'state': 'PARABOLIC'}) == 'LATE FOMO'
    assert mw.market_phase({'state': 'PULLBACK IN UPTREND', 'f': {'recovery': 0.7, 'pullback': 4}}) == 'RECLAIM'
    assert mw.market_phase({'state': 'PULLBACK IN UPTREND', 'f': {'recovery': 0.2, 'pullback': 4}}) == 'FIRST PULLBACK'
    assert set(mw.PHASE_OF.values()) <= set(mw.PHASES)


# ── the three rounds ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def _run(rows_by_t, hard=None, tiers=None, phases=None):
    s = {}
    for t, rows in rows_by_t:
        s = tr.step(s, rows, t, hard or {}, tiers or {}, phases or {})
    return s


def test_a_candidate_expires_into_enter_reject_or_cooldown_by_round_3_never_an_endless_wait():
    r = row('B')
    s = _run([(0, [r]), (310, [{**r, 'px': 1.02}]), (620, [{**r, 'px': 1.04}])], tiers={'B': ('B', 58)})
    assert s['c']['B']['decision'] == 'ENTER' and 'B' in tr.entered(s, 630)
    s = _run([(0, [r]), (310, [{**r, 'px': 0.95}]), (620, [{**r, 'px': 0.9}])], tiers={'B': ('B', 58)})
    assert s['c']['B']['decision'] == 'COOLDOWN' and 'momentum did not hold' in s['c']['B']['why']
    s = _run([(0, [r]), (310, [r]), (620, [r])], tiers={})
    assert s['c']['B']['decision'] == 'REJECT'
    s = _run([(0, [r]), (310, [r]), (620, [r])], tiers={'B': ('C', 45)})
    assert s['c']['B']['decision'] == 'COOLDOWN'                              # a C tier that did not improve
    s = _run([(t, [r]) for t in range(0, 4000, 18)], tiers={'B': ('C', 45)})
    assert all(e.get('decision') for e in s['c'].values()) and tr.summary(s, 4000)['waitingLongest'] < tr.ROUND_SEC * 3


def test_a_hard_failure_rejects_at_once_and_a_full_go_enters_before_round_3():
    r = row('X')
    s = _run([(0, [r])], hard={'X': 'failed the holder safety scan'})
    assert s['c']['X']['decision'] == 'REJECT' and s['hist'][-1]['rounds'] == 0
    s = _run([(0, [{**r, 'go': True}])], tiers={'X': ('A', 80)})
    assert s['c']['X']['decision'] == 'ENTER' and 'GO' in s['c']['X']['why']


def test_an_unseated_enter_lapses_and_a_material_change_wakes_a_cooled_coin():
    r = row('Y')
    s = _run([(0, [r]), (310, [r]), (620, [r])], tiers={'Y': ('A', 75)})
    s = tr.step(s, [r], 620 + tr.ENTER_TTL + 1, {}, {'Y': ('A', 75)})
    assert s['c']['Y']['decision'] == 'COOLDOWN' and 'not seated' in s['c']['Y']['why']
    s = tr.step(s, [{**r, 'px': 1.2}], 620 + tr.ENTER_TTL + 30, {}, {'Y': ('A', 75)})
    assert not s['c']['Y'].get('decision') and 'price' in s['c']['Y']['woke'] and s['c']['Y']['round'] == 1


def test_a_c_tier_enters_only_when_it_improved_every_round():
    r = row('C')
    s = {}
    for t, px, sc in ((0, 1.0, 41), (310, 1.03, 46), (620, 1.06, 52)):
        s = tr.step(s, [{**r, 'px': px}], t, {}, {'C': ('C', sc)})
    assert s['c']['C']['decision'] == 'ENTER' and 'small size' in s['c']['C']['why']


def test_round_enters_fill_through_the_one_execution_path():
    assert "near0_.append({**x_, 'pair': x_.get('pair') or x_.get('pairAddress'), 'tier': tr_, 'opp': s_, 'roundEnter': why_," in SRC
    assert "wait_ = wait_ + [t_ for t_ in rnd_ok_" in SRC                     # → fill_plan → Warden → agent_seat → keeper
    assert SRC.count('_prime.agent_seat(') == 1                              # one seat-fill call; no second engine
    assert 'class FuseWallet' not in SRC and SRC.count('def _fw_execute(') == 1


# ── seats + positions ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_four_independent_candidates_can_target_four_seats():
    four = [{'mint': m} for m in 'ABCD']
    ctx = {'control': True, 'pol': oe.policy({}), 'live': True, 'courier': 'OK', 'used': 0, 'gos': [], 'wait': four, 'empty': 4,
           'emptySince': 900, 'lastFill': 0, 'now': 1000.0, 'cap': ag.FILL_MOVES_HR}
    assert [r['mint'] for r in oe.fill_plan(ctx)][:4] == ['A', 'B', 'C', 'D']


def test_a_runner_keeps_running_and_a_loser_leaves_before_the_round_ends():
    assert mw.run_state(12.0, 12.5, 'ACCELERATING') == 'ACCELERATING'      # a green accelerating coin is a runner: no time exit sells it
    legs = [{'mint': 'L', 'pairAddress': 'PL', 'units': 10, 'entry': 1.0, 'real': True, 'at': 0, 'bought': {'tag': '🤖 agents'}}]
    assert of.fast_reap(legs, {'L': 0.8}, {'L': {'stopNow': 15}}, 120.0)   # −20% vs a 15% stop: out on the 6-second guard
    assert tr.position_round(0, 610) == {'round': 3, 'left': 290.0} and tr.action_word('EXIT INVALIDATED') == 'EXIT'


def test_a_material_breakout_wakes_trigger_and_a_breakdown_wakes_reaper_between_rounds():
    assert mw.candidate_wake({'px': 1.0, 'high': 1.0}, 1.01) == ['live breakout above its local high']
    assert any('reversal' in w for w in mw.position_wake({'entry': 1.0, 'peak': 10.0, 'decPx': 1.1}, 1.04))


# ── cost, learning, display ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_seat_too_small_for_its_fees_is_not_bought():
    base = {'liq': 500_000, 'ageH': 2, 'courier': 'OK', 'rtPct': 2.4, 'feeUsd': 0.001}
    assert not of.warden(0.13, base)['veto']                                # ~3.9% round trip: fine
    w = of.warden(0.05, base, floor=0.05)
    assert w['veto'] and any(r['id'] == 'W22 cost' for r in w['rules'])    # ~6.4%: the fees eat the trade


def test_the_judge_records_wins_and_losses_and_no_rule_moves_from_one_outcome():
    rv = [{'kind': 'win', 'pct': 12.0, 'exit': 'R7 trailing protection', 'resp': {}}, {'kind': 'loss', 'pct': -20.0, 'resp': {'devil': 1}}]
    d = jr.desk_stats(rv)
    assert d['devil'] == {'decisions': 2, 'winResp': 1, 'lossResp': 1, 'accuracy': 50, 'medNet': -4.0} and d['reaper']['winResp'] == 1
    assert jr.penalties([{'penalty': 'thin pool', 'points': -8}]) == {}       # the Judge proposes; nothing changes live
    one = [{'confirmed': True, 'realPct': -30, 'closedAt': 1, 'thesis': {'structure': 'UPTREND'}}]
    assert not rm.build(one)['proof']['ok'] and rm.judge(rm.build(one), rm.feats('UPTREND')) is None


def test_every_agents_tab_chart_is_the_live_feeless_chart():
    room = (FRONT / 'OfficeRoom.jsx').read_text()
    assert '<PriceChartLazy' in room and 'useLiveCandles(model0?.wall?.pair' in room   # panel / seats / candidates = PriceChart · wall = the war room's own 1m candles
    assert 'export function RoundBar' in (FRONT / 'SeatOps.jsx').read_text()


def test_an_unread_holder_scan_is_pending_not_a_rejection():
    """Live, 2026-10-12: 'holders not read yet' was REJECTED for 30 min — every newborn starts unscanned."""
    r = row('P')
    s = tr.step({}, [r], 0, {'P': 'holders not read yet'}, {})
    assert not s['c']['P'].get('decision') and s['c']['P']['reads'][0]['pending'] == 'holders not read yet'
    s = tr.step(s, [r], 310, {}, {'P': ('B', 60)})                            # the scan landed: it keeps its rounds
    s = tr.step(s, [{**r, 'px': 1.02}], 620, {}, {'P': ('B', 62)})
    assert s['c']['P']['decision'] == 'ENTER'
    s = _run([(0, [r]), (310, [r]), (620, [r])], hard={'P': 'holders not read yet'})
    assert s['c']['P']['decision'] == 'COOLDOWN' and 'pending' in s['c']['P']['why']


def test_a_coin_flickering_off_the_list_for_one_pass_keeps_its_rounds():
    r = row('F')
    s = tr.step({}, [r], 0, {}, {'F': ('B', 60)})
    s = tr.step(s, [], 40, {}, {})                                            # one pass off the list (volume / cap wobble)
    assert not s['c']['F'].get('decision')
    s = tr.step(s, [], 40 + tr.ROUND_SEC + 1, {}, {})                        # gone a whole round: closed
    assert s['c']['F']['decision'] == 'COOLDOWN' and 'whole round' in s['c']['F']['why']


def test_an_office_desk_that_keeps_losing_real_money_starts_its_next_generation_with_the_lesson():
    """Owner, 2026-10-12: "ok to lose but not learning and still in the gen is crazy" — Warden had 16 real losses pinned and was gen 1."""
    rv = [{'kind': 'loss', 'at': 10 + i, 'resp': {'warden': 1}, 'cause': 'thin_pool'} for i in range(6)]
    o = of.demote({}, {}, 100.0, rv)
    assert o['gen']['warden'] == 2 and o['born']['warden'] == 100.0 and o['lineage'][-1]['lesson'] == 'thin_pool'
    assert of.demote(o, {}, 200.0, rv)['gen']['warden'] == 2                     # its new life starts clean: old losses don't count twice
    few = [{'kind': 'loss', 'at': 1, 'resp': {'reaper': 1}}] * 3 + [{'kind': 'win', 'at': 2, 'exit': 'R7 trail'}]
    assert of.demote({}, {}, 100.0, few).get('gen', {}).get('reaper') is None      # 3 losses − 1 win: still ACTIVE (replaced at 3 net)
