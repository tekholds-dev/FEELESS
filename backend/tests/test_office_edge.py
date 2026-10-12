"""⚡ The office's edge pass (`backend/office_edge.py`) and where it plugs into the desks: the creator's limits (AGENTS CHOOSE vs CREATOR
OVERRIDE, manual authority), restart readiness (no off-radar / time exit from a restart gap), the empty-seat state and fill timing, the
superiority switch test, launch context, the missed-winner study, the non-blocking review queue and the speed counters.
Pure functions first, then `agents.manage` / `office.reap` / `office.warden` / `agents.desk`, then the service's one payload and the
creator's POST. No network, no wallet, no order: nothing here can place a trade."""
import asyncio
import json

import pytest

import agents as ag
import arena_prime as ap
import chart_intel as ci
import office as of
import office_edge as oe


# ── helpers (same shapes as tests/test_office.py) ─────────────────────────────────────────────────────────────────────────────────
def leg(m, entry=1.0, units=1.0, at=1, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'entry': entry, 'units': units, 'at': at, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}, **k}


def trow(m, lean=2.0, call='enter', d5=1.0, buy=60, **v):
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'why': {'lean': lean, 'drivers': []}, 'trigger': [call, ''], 'devil': ['agree', ''], 'case': ['agree', ''],
            'nums': {'d5': d5, 'buy': buy, 'liq': 60_000, 'pts': 5}, 'vitals': {'safe': True, 'ageH': 8, 'liq': 60_000, 'top10': 15, 'rug': 10, **v}, 'go': call == 'enter'}


def case(m, lean=2.0, cleared=True, checks=None):
    return {'mint': m, 'symbol': m, 'lean': lean, 'cleared': cleared, 'checks': checks if checks is not None else [['scan', True, ''], ['devil', cleared, '']], 'row': trow(m, lean)}


# ── 🎛 THE CREATOR'S LIMITS ───────────────────────────────────────────────────────────────────────────────────────────────────────
def test_unknown_or_wild_policy_values_fall_back_to_agents_choose_or_are_clamped_never_silently_wild():
    assert oe.clean_policy({}) == {'agentAuthority': 'agents', 'agentTp': 0.0, 'agentSl': 0.0, 'agentTrail': 'auto', 'agentTrailArm': 0.0, 'agentTrailPct': 0.0, 'agentMaxHold': 0.0,
                                   'agentSizePct': 0.0, 'agentSeatTarget': 0, 'agentSwitch': 'agents', 'agentEntry': 'agents', 'agentMinAgeH': 0.0}
    wild = oe.clean_policy({'agentAuthority': 'god', 'agentTp': 9999, 'agentSl': 0.5, 'agentMaxHold': -3, 'agentSizePct': 99, 'agentSeatTarget': 7, 'agentSwitch': 'yolo', 'agentEntry': 'x', 'agentTrail': 'z'})
    assert wild['agentAuthority'] == 'agents' and wild['agentTp'] == oe.BOUNDS['agentTp'][1] and wild['agentSl'] == oe.BOUNDS['agentSl'][0]   # clamped into the bounds
    assert wild['agentMaxHold'] == 0.0 and wild['agentSizePct'] == oe.BOUNDS['agentSizePct'][1] and wild['agentSeatTarget'] == 0 and (wild['agentSwitch'], wild['agentEntry'], wild['agentTrail']) == ('agents', 'agents', 'auto')
    assert ap.clean_cfg({'agentTp': 20, 'agentSl': 12, 'agentSwitch': 'conservative', 'agentAuthority': 'manual'})['agentTp'] == 20.0   # the card's own validator keeps them
    c = ap.clean_cfg({'agentTp': 20, 'agentSl': 12, 'agentSwitch': 'conservative', 'agentAuthority': 'manual', 'agentSeatTarget': 60})
    assert (c['agentSl'], c['agentSwitch'], c['agentAuthority'], c['agentSeatTarget']) == (12.0, 'conservative', 'manual', 60)
    assert all(k in ap.clean_cfg({}) for k in oe.POLICY_KEYS)                                                     # every key exists on every cleaned card config


def test_policy_says_per_control_who_decides_and_never_goes_under_the_hard_floors():
    p = oe.policy({'agentSeats': 4, 'coins': 4})
    assert set(p['who'].values()) == {'AGENTS CHOOSE', 'CREATOR OVERRIDE'} and p['who']['seatCount'] == 'CREATOR OVERRIDE'
    assert all(p['who'][k] == 'AGENTS CHOOSE' for k in ('takeProfit', 'stopLoss', 'trailing', 'maxHold', 'positionSize', 'switching', 'emptySeat', 'entryStyle', 'exitStyle'))
    assert (p['tp'], p['sl'], p['maxHold'], p['sizePct'], p['manual'], p['seats'], p['seatTarget']) == (None, None, None, None, False, 4, oe.SEAT_TARGET_AUTO)
    assert p['hard'] == {'catastrophicStop': ci.CATASTROPHIC_STOP, 'movesPerHour': ag.CONTROL_MOVES_HR, 'minPool': ag.CONTROL_MIN_LIQ}
    o = oe.policy({'agentTp': 15, 'agentSl': 10, 'agentMaxHold': 60, 'agentSizePct': 25, 'agentSwitch': 'aggressive', 'agentSeats': 4, 'coins': 2})
    assert (o['tp'], o['sl'], o['maxHold'], o['sizePct'], o['seats']) == (15.0, 10.0, 60.0, 25.0, 2) and o['who']['takeProfit'] == 'CREATOR OVERRIDE'
    assert o['switch']['edge'] >= oe.SWITCH_FLOOR[0] and o['switch']['holdMin'] >= oe.SWITCH_FLOOR[1] and o['switch']['holdMin'] >= ag.CONTROL_HOLD_MIN   # aggressive never under the floors
    assert oe.policy({'agentSwitch': 'off'})['switch'] == {'mode': 'off', 'on': False, 'edge': None, 'holdMin': None}
    assert oe.policy({'agentTrail': 'custom'})['trail']['mode'] == 'auto'                                         # a custom trail with no numbers is not a trail: back to theirs
    assert oe.policy({'agentTrail': 'custom', 'agentTrailArm': 10, 'agentTrailPct': 5})['trail'] == {'mode': 'custom', 'arm': 10.0, 'pct': 5.0}
    assert oe.policy({'agentAuthority': 'manual'})['manual'] is True


def test_the_controls_panel_lists_every_control_with_its_options_and_what_the_agents_use_now():
    rows = oe.controls({'agentTp': 20}, oe.agents_now({'source': 'base', 'base': 20, 'active': 20}, {'stopPct': 30, 'protectAt': 6, 'giveBackPct': 50, 'maxSeatPct': 40},
                                                       {'stopPct': 12, 'sym': 'AAA'}))
    by = {r['key']: r for r in rows}
    assert set(by) == {k for k, *_ in oe.CONTROLS} and all(r['options'] and r['means'] for r in rows)
    assert by['agentTp']['who'] == 'CREATOR OVERRIDE' and by['agentTp']['value'] == 20.0 and by['agentTp']['options'][0] == 0   # 0 = AGENTS CHOOSE is always an option
    assert by['agentSl']['who'] == 'AGENTS CHOOSE' and '12% on $AAA' in by['agentSl']['agentsNow'] and 'never past 30%' in by['agentSl']['agentsNow']
    assert 'they read it' in by['agentTp']['agentsNow'] and 'learned' in oe.agents_now({'source': 'learned', 'active': 8, 'evidenceN': 24}, {})['agentTp']
    assert oe.controls({})[0]['agentsNow'] is None                                                               # nothing handed in = nothing claimed
    for r in rows:                                                                                               # every option of every control survives the card's validator
        for v in r['options']:
            assert ap.clean_cfg({r['key']: v})[r['key']] == (float(v) if isinstance(v, (int, float)) and r['key'] not in ('agentSeatTarget',) else v)


# ── 🔌 RESTART READINESS ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_office_is_live_only_after_positions_are_read_back_and_the_market_has_refilled():
    s = lambda **b: oe.ready({'at': 100, **b}, 400)
    assert s()['state'] == 'OFFICE WARMING UP' and not s()['live'] and s()['sinceSec'] == 300
    assert s(reconciled=True)['state'] == 'POSITIONS RECONCILED' and not s(reconciled=True)['live']
    assert s(passes=2, coins=40)['state'] == 'MARKET REFILLED' and 'positions not read back' in s(passes=2, coins=40)['why']
    assert s(passes=1, coins=40, reconciled=True)['state'] == 'POSITIONS RECONCILED' and '1 of 2 agent passes' in s(passes=1, coins=40, reconciled=True)['why']
    assert s(passes=5, coins=4, reconciled=True)['live'] is False and 'needs 10' in s(passes=5, coins=4, reconciled=True)['why']   # passes on a thin board do not count as refilled
    on = s(passes=2, coins=10, reconciled=True)
    assert on['state'] == 'LIVE' and on['live'] and on['why'] == 'live' and [x[1] for x in on['steps']] == [True, True, True, True]
    assert oe.radar_gone(100, 100 + oe.RADAR_GRACE_SEC, True) and not oe.radar_gone(100, 100 + oe.RADAR_GRACE_SEC - 1, True)
    assert not oe.radar_gone(100, 10_000, False) and not oe.radar_gone(None, 10_000, True)                        # never while warming up · never without a stamp


def test_a_restart_gap_never_exits_a_position_but_price_pool_and_safety_exits_never_wait():
    cfg = {'agentTakePct': 10, 'agentScalp': False}
    run = lambda l, px, table, pos=None, now=3 * 3600, live=True, **k: of.reap([l], table, {'P' + l['mint']: px}, cfg, pos, now, live=live, **k)
    pos, rep, _ = run(leg('A'), 0.97, [], now=3 * 3600 - 400, live=False)                                         # warming up and the coin is not on the (refilling) table
    assert rep[0]['rule'] == 'R10 hold' and 'offSince' not in pos['A'] and 'OFFICE WARMING UP' in rep[0]['evidence'] and rep[0]['live'] is False
    stale = {'A': {**pos['A'], 'offSince': 1}}                                                                    # a stamp left on disk from before the restart …
    pos, rep, _ = run(leg('A'), 0.97, [], pos=stale, now=3 * 3600 - 300, live=False)
    assert rep[0]['action'] is None and 'offSince' not in pos['A']                                                # … is dropped while warming up
    pos, rep, _ = run(leg('A'), 0.97, [], pos=pos, now=3 * 3600 - 290)                                           # LIVE again: the grace starts NOW
    assert rep[0]['action'] is None and pos['A']['offSince'] == 3 * 3600 - 290 and 'under the 180s grace' in rep[0]['evidence']
    assert run(leg('A'), 0.97, [], pos=pos, now=3 * 3600 - 290 + oe.RADAR_GRACE_SEC)[1][0]['rule'] == 'R11 dead coin'  # (an off-radar seat is now a swap-only R11 exit) missing for the full grace while LIVE → it may rule
    for px, rule in ((0.5, 'R5x catastrophic stop'), (0.69, 'R5 stop')):                                          # price exits act while warming up
        assert run(leg('A'), px, [trow('A')], live=False)[1][0]['rule'] == rule
    assert run(leg('A', liqNow=10_000), 1.0, [trow('A')], live=False)[1][0]['rule'] == 'R1 liquidity collapse'  # … the pool rule
    assert run(leg('A'), 1.0, [trow('A', safe=False)], live=False)[1][0]['rule'] == 'R2 hard invalidation'      # … the scan / rug rule
    tl = run(leg('A'), 1.03, [trow('A', lean=-1.0)], live=False)[1][0]
    assert tl['action'] is None and tl['state'] != 'TAKE'                                                         # a read / time exit waits for LIVE (flagged, never sold)
    mx = lambda live: of.reap([leg('A', at=1)], [trow('A')], {'PA': 1.02}, {**cfg, 'agentMaxHold': 30}, None, 3600, live=live)[1][0]
    assert mx(True)['rule'] == 'R9c creator max hold' and mx(True)['action'] == 'pull' and mx(False)['action'] is None   # even your max hold waits for LIVE after a restart


def test_while_warming_up_the_desk_makes_no_read_or_switch_move_and_banks_a_take_on_price_alone():
    cfg = {'agentTakePct': 10, 'agentMode': 'auto', 'trenchMinAgeH': 1}
    picks = [trow('NEW', lean=5)]
    broke = [trow('A', lean=-1.0)]
    assert ag.manage([leg('A')], broke, {'PA': 0.97}, cfg, control=True, now=7200, moves_left=1, picks=picks)[0]['action'] == 'swap'   # LIVE: a broken read is switched
    w = ag.manage([leg('A')], broke, {'PA': 0.97}, cfg, control=True, now=7200, moves_left=1, picks=picks, live=False)[0]
    assert w['action'] == 'hold' and 'warming up' in w['why']
    assert all(x['action'] == 'hold' for x in ag.manage([leg('A')], [trow('A', lean=0.1)], {'PA': 0.95}, cfg, control=True, now=7200, moves_left=1, picks=picks, rotate=True, live=False))
    t = ag.manage([leg('A')], [trow('A')], {'PA': 1.12}, cfg, control=True, now=7200, moves_left=1, picks=picks, live=False)[0]
    assert t['action'] == 'pull' and 'warming up' in t['why']                                                     # at the take line with no live read: banked to cash, never swapped
    d = ag.manage([leg('A', liqNow=20_000)], [trow('A')], {'PA': 1.0}, cfg, control=True, now=7200, live=False)[0]
    assert d['action'] == 'pull' and 'pool fell' in d['why']                                                      # a draining pool never waits


# ── 🎛 AGENTS CHOOSE vs CREATOR OVERRIDE, in the desks that act ─────────────────────────────────────────────────────────────────────
def test_agents_choose_really_lets_the_agents_decide_the_take_inside_your_limits():
    cfg = {'agentTakePct': 10, 'agentMode': 'auto'}
    clean, broken, weakthesis = [trow('A', lean=0.5)], [trow('A', lean=0.5, d5=-4.0)], [trow('A', lean=0.5)]
    m = lambda table, c=cfg, scalp=None, reviews=None, **k: ag.manage([leg('A')], table, {'PA': 1.14}, c, scalp, control=True, now=7200, moves_left=0, reviews=reviews, **k)[0]
    assert m(clean)['action'] == 'hold' and 'let it run' in m(clean)['why']                                       # at the base line a clean read runs …
    assert m(broken)['action'] == 'pull' and '5 min' in m(broken)['why']                                          # … a broken read is banked
    assert m(weakthesis, reviews={'A': 'weak'})['action'] == 'pull' and 'thesis reads weak' in m(weakthesis, reviews={'A': 'weak'})['why']   # … and so is a weak thesis
    assert m(clean, scalp={'tp': 12, 'sl': 6})['action'] == 'pull'                                                 # their LEARNED line is their choice: banked at it
    over = m(clean, c={**cfg, 'agentTp': 12})
    assert over['action'] == 'pull' and 'your take' in over['why']                                                # YOUR override: banked at your line, whatever their read
    assert m(clean, c={**cfg, 'agentTp': 20})['action'] == 'hold'                                                  # under your line nothing is banked
    assert of.take_line({**cfg, 'agentTp': 12}, {'tp': 30}) == 12.0 and of.take_info({**cfg, 'agentTp': 12}, {'tp': 30})['who'] == 'CREATOR OVERRIDE'
    _, rep, _ = of.reap([leg('A')], clean, {'PA': 1.14}, cfg, None, 3600)
    assert rep[0]['state'] == 'PROTECT' and rep[0]['decision'] == 'PROTECT' and rep[0]['action'] is None          # Reaper keeps the trail on a coin the agents let run …
    pos, _, _ = of.reap([leg('A')], clean, {'PA': 1.40}, cfg, None, 3600)
    _, rep, _ = of.reap([leg('A')], clean, {'PA': 1.15}, cfg, pos, 3700)
    assert (rep[0]['rule'], rep[0]['action']) == ('R7 trailing protection', 'pull')                                # … and banks it when it gives back half the peak (+40 → +15)


def test_your_stop_is_a_ceiling_the_agents_may_only_tighten_and_the_catastrophic_stop_never_moves():
    cfg = {'agentTakePct': 10}
    r = lambda px, c, th=None: of.reap([leg('A')], [trow('A')], {'PA': px}, c, {'A': {'entry': 1.0, 'since': 1, 'peak': 0, 'low': 0, 'path': [], 'thesis': th}} if th else None, 3600)[1][0]
    assert r(0.88, {**cfg, 'agentSl': 10})['rule'] == 'R5c creator stop' and r(0.88, cfg)['state'] == 'HOLD'        # your −10% fires where the agents' −30% would not
    assert r(0.90, {**cfg, 'agentSl': 20}, {'stopPct': 9, 'structure': 'UPTREND'})['rule'] == 'R5 stop'              # their tighter structure stop (−9%) still acts under your −20%
    assert r(0.75, {**cfg, 'agentSl': 40}, {'stopPct': 9})['rule'] in ('R5 stop', 'R5c creator stop')               # a wide creator stop never loosens theirs
    assert r(0.54, {**cfg, 'agentSl': 40})['rule'] == 'R5x catastrophic stop' and ci.CATASTROPHIC_STOP == 45.0      # the hard-coded line stands above everything
    assert 'agentSl' in oe.POLICY_KEYS and 'CATASTROPHIC_STOP' not in json.dumps(of.TUNABLE, default=str)          # not a tunable: nothing can promote it away


def test_max_hold_caps_the_thesis_windows_and_custom_or_off_trails_are_obeyed():
    cfg = {'agentTakePct': 30, 'agentScalp': False}
    th = {'stopPct': 20, 'structure': 'UPTREND', 'maxHoldWindows': 12, 'expectedHoldWindows': 6}
    rep = of.reap([leg('A', at=3000)], [trow('A')], {'PA': 1.02}, {**cfg, 'agentMaxHold': 15}, {'A': {'entry': 1.0, 'since': 3000, 'peak': 0, 'low': 0, 'path': [], 'thesis': th}}, 3600)[1][0]
    assert rep['granted'] == 3 and rep['limits']['maxHold'] == 15.0                                               # 15 min = 3 windows, whatever the thesis earned
    pos, _, _ = of.reap([leg('A')], [trow('A')], {'PA': 1.12}, {**cfg, 'agentTrail': 'custom', 'agentTrailArm': 10, 'agentTrailPct': 5}, None, 3600)
    t = of.reap([leg('A')], [trow('A')], {'PA': 1.065}, {**cfg, 'agentTrail': 'custom', 'agentTrailArm': 10, 'agentTrailPct': 5}, pos, 3700)[1][0]
    assert t['rule'] == 'R7 trailing protection' and 'your trail' in t['evidence'] and t['action'] == 'pull'      # +12 peak → 5 points off = +7 → banked at +6.5
    pos, _, _ = of.reap([leg('A')], [trow('A')], {'PA': 1.12}, {**cfg, 'agentTrail': 'off'}, None, 3600)
    assert of.reap([leg('A')], [trow('A')], {'PA': 1.03}, {**cfg, 'agentTrail': 'off'}, pos, 3700)[1][0]['action'] is None   # trailing OFF: no give-back exit


def test_creator_manual_means_the_agents_make_no_discretionary_move_but_your_own_limits_still_act():
    man = {'agentTakePct': 10, 'agentAuthority': 'manual'}
    m = lambda px, table, c=man: ag.manage([leg('A')], table, {'PA': px}, c, control=True, now=7200, moves_left=2, picks=[trow('NEW', lean=9)], rotate=True)[0]
    assert m(0.9, [trow('A', lean=-2)])['action'] == 'hold' and m(1.3, [trow('A')])['action'] == 'hold'             # no switch, no bank on a read
    assert ag.manage([leg('A', liqNow=10_000)], [trow('A')], {'PA': 1.0}, man, control=True, now=7200)[0]['action'] == 'pull'   # the pool rule acts in every mode
    r = lambda px, c=man: of.reap([leg('A')], [trow('A', lean=-2)], {'PA': px}, c, None, 3600, control=True)[1][0]
    assert r(0.75)['rule'] == 'R10 creator manual' and r(0.75)['action'] is None                                    # their own −30% stop is theirs: not acting in manual
    assert r(0.88, {**man, 'agentSl': 10})['rule'] == 'R5c creator stop'                                          # YOUR stop acts
    assert r(1.25, {**man, 'agentTp': 20})['action'] == 'pull' and r(1.25, {**man, 'agentTp': 20})['rule'] == 'R6 take line'   # YOUR take acts
    assert r(0.5)['rule'] == 'R5x catastrophic stop'                                                              # the hard stop always acts
    assert oe.seat_state({'want': 4, 'held': 2, 'manual': True})['state'] == 'CREATOR MANUAL'


def test_the_wardens_creator_cap_and_launch_risk_can_only_shrink_a_seat():
    ctx = {'value': 10.0, 'putIn': 10.0, 'cash': 5.0, 'seats': 2, 'liq': 80_000, 'ageH': 8, 'lives': 9, 'courier': 'HEALTHY'}
    base = of.warden(4.0, ctx)
    capped = of.warden(4.0, {**ctx, 'policy': {'sizePct': 25}})
    assert capped['allowed'] <= base['allowed'] and capped['allowed'] <= 2.5 + 1e-9 and any(x['id'] == 'W14 creator size cap' for x in capped['rules'])
    curve = of.warden(1.0, {**ctx, 'launch': oe.launch_context({'mint': 'AAApump', 'curve': True, 'ageH': 2})})
    assert any(x['id'] == 'W15 launch context' for x in curve['rules']) and curve['allowed'] <= 0.5 + 1e-9
    plain = of.warden(1.0, {**ctx, 'launch': oe.launch_context({'mint': 'AAApump', 'curve': False, 'ageH': 2})})
    assert not any(x['id'] == 'W15 launch context' for x in plain['rules'])                                     # a migrated Pump coin: no launch haircut
    big = of.warden(1.0, {**ctx, 'policy': {'sizePct': 50}})
    assert big['allowed'] <= 1.0 and not any(x['id'] == 'W14 creator size cap' for x in big['rules'])           # a cap above the ask never grows it


# ── 🪑 EMPTY SEATS ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_empty_seat_always_says_why_it_is_empty_and_cash_is_a_valid_position():
    base = {'want': 4, 'held': 3, 'movesLeft': 3, 'freeUsd': 1.0, 'minUsd': 0.1, 'now': 1000, 'emptySince': 950, 'target': 30, 'live': True}
    assert oe.seat_state({**base, 'held': 4})['state'] == 'FULL'
    assert oe.seat_state({**base, 'live': False, 'readyWhy': '1 of 2 agent passes'})['state'] == 'OFFICE WARMING UP'
    assert 'EXECUTION BLOCK' in oe.seat_state({**base, 'courier': 'BAD'})['reason']
    assert 'hourly budget' in oe.seat_state({**base, 'movesLeft': 0})['reason']
    assert oe.seat_state({**base, 'freeUsd': 0.02})['reason'].startswith('NO CASH')
    f = oe.seat_state({**base, 'valid': [{'symbol': 'GO1'}], 'nextTickIn': 12.4})
    assert f['state'] == 'FILLING' and f['nextIn'] == 12 and f['late'] is True and f['emptyFor'] == 50 and f['validSyms'] == ['GO1']   # empty 50s > the 30s target
    cases = [case('X', cleared=False, checks=[['scan', True, ''], ['age', False, ''], ['devil', False, '']]), case('Y', cleared=False, checks=[['age', False, '']]),
             case('Z', cleared=False, checks=[['pool', False, '']]), case('OK')]
    n = oe.seat_state({**base, 'cases': cases})
    assert n['state'] == 'NO VALID ENTRY' and n['blockers'][0] == ['age', 'too young', 2] and '0 of 4 case files clear' in n['reason'] and 'too young (2)' in n['reason']
    assert oe.blockers(cases) == [['age', 'too young', 2], ['pool', 'pool under $20K', 1]]
    assert 'no coin has a positive read' in oe.seat_state(base)['reason']


def test_a_cleared_case_fills_on_the_seat_target_and_a_full_go_never_waits():
    pol = oe.policy({})
    assert oe.may_fill({'go': True}, pol, None, 0)                                                                # a full GO fills at once
    assert not oe.may_fill({'go': False}, pol, None, 1000)                                                        # no empty seat recorded → no duty fill
    assert oe.may_fill({'go': False}, pol, 900, 1000, last_fill_at=900) and not oe.may_fill({'go': False}, pol, 995, 1000, last_fill_at=995)   # one cleared fill per 10s (auto)
    assert not oe.may_fill({'go': False}, oe.policy({'agentEntry': 'go'}), 900, 1000)                              # entry = GO only: a cleared case never fills
    assert not oe.may_fill({'go': False}, oe.policy({'agentSeatTarget': 60}), 900, 1000, last_fill_at=950) and oe.may_fill({'go': False}, oe.policy({'agentSeatTarget': 60}), 900, 1000, last_fill_at=900)


# ── ⇄ SWITCHING ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_switch_must_pass_every_line_of_the_superiority_test_and_a_winner_is_never_surrendered():
    pol = oe.policy({})
    weak = {'symbol': 'OLD', 'pnl': -4.0, 'heldMin': 40, 'lean': 0.2, 'verdict': 'weak'}
    ok = oe.switch_test(weak, case('NEW', lean=2.5), pol)
    assert ok['switch'] and 'cleared every desk' in ok['why'] and ok['edge'] == 2.3 and all(l[1] for l in ok['lines']) and len(ok['lines']) == 7
    fail = lambda cur, new, p=pol: oe.switch_test({**weak, **cur}, new, p)
    assert 'OFF' in fail({}, case('NEW', 3), oe.policy({'agentSwitch': 'off'}))['why']
    assert fail({}, None)['why'] == 'no challenger this pass' and not fail({}, None)['switch']
    assert 'too young' in fail({}, case('NEW', 3, cleared=False, checks=[['age', False, '']]))['why']
    assert 'frozen' in fail({'frozen': True}, case('NEW', 3))['why'] and 'riding' in fail({'riding': True}, case('NEW', 3))['why']
    for v in ('weak', 'invalid', None):                                                                           # green is never surrendered — even on a broken thesis (Reaper banks it)
        assert 'winner is not surrendered' in fail({'pnl': 0.5, 'verdict': v}, case('NEW', 9))['why']
    assert 'needs 30' in fail({'heldMin': 20}, case('NEW', 3))['why'] and 'needs 45' in fail({'heldMin': 40}, case('NEW', 3), oe.policy({'agentSwitch': 'conservative'}))['why']
    assert 'read margin' in fail({}, case('NEW', 0.9))['why']
    assert 'thesis still stands' in fail({'verdict': 'valid', 'lean': 1.0, 'heldMin': 40}, case('NEW', 3))['why']    # opportunity cost alone is not a reason …
    assert fail({'verdict': 'valid', 'lean': 1.0, 'heldMin': 61}, case('NEW', 3))['switch']                         # … until twice the hold with nothing to show
    lines = {l[0]: l[1] for l in fail({'pnl': 2.0, 'heldMin': 5}, case('NEW', 0.5))['lines']}
    assert lines['position not a winner'] is False and lines['held long enough'] is False and lines['read margin'] is False and lines['challenger cleared every desk'] is True


def test_the_desk_switches_only_through_the_test_and_your_switching_mode_binds_a_broken_read_too():
    cfg = {'agentTakePct': 10, 'agentMode': 'auto', 'trenchMinAgeH': 1}
    picks = [trow('NEW', lean=5)]
    ex = lambda c, held_min, table=None: ag.manage([leg('A', at=7200 - held_min * 60)], table or [trow('A', lean=-1.0)], {'PA': 0.97}, c, control=True, now=7200, moves_left=1, picks=picks)[0]['action']
    assert ex(cfg, 16) == 'swap' and ex(cfg, 14) == 'hold'                                                         # AGENTS CHOOSE: a broken read after 15 min
    assert ex({**cfg, 'agentSwitch': 'conservative'}, 30) == 'hold' and ex({**cfg, 'agentSwitch': 'conservative'}, 46) == 'swap'   # your mode's 45 min binds it
    assert ex({**cfg, 'agentSwitch': 'off'}, 120) == 'hold'                                                        # switching OFF: never
    legs = [leg('W', at=1), leg('L', at=1)]
    d = {x['symbol']: x for x in ag.manage(legs, [trow('W', lean=0.1), trow('L', lean=0.1), *picks], {'PW': 1.05, 'PL': 0.9}, cfg, control=True, now=7200, moves_left=1, picks=picks, rotate=True)}
    assert d['W']['action'] == 'hold' and d['L']['action'] == 'swap' and d['L']['test'] == {'edge': 4.9, 'need': 1.0, 'mode': 'agents'}   # the winner keeps its seat
    gap = ag.manage([leg('L', at=1)], [*picks], {'PL': 0.9}, cfg, control=True, now=7200, moves_left=1, picks=picks, rotate=True, radar=set())
    assert gap[0]['action'] == 'hold'                                                                             # missing from the table inside the grace: not compared, not switched


# ── 🚀 LAUNCH CONTEXT ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_launch_context_claims_only_what_is_measured_and_unknown_stays_unknown():
    lc = oe.launch_context
    assert (lc({'mint': 'AbCpump', 'curve': True, 'curvePct': 61})['type'], lc({'mint': 'AbCpump', 'curve': True})['pad']) == ('bonding curve', 'Pump.fun')
    assert lc({'mint': 'AbCpump', 'curve': True, 'curvePct': 61})['curvePct'] == 61 and lc({'mint': 'AbCbonk', 'curve': False, 'ageH': 3})['type'] == 'migrated'
    m = lc({'mint': 'AbCbonk', 'curve': False, 'ageH': 3})
    assert m['pad'] == 'LetsBONK' and m['graduated'] is True and m['poolAgeH'] == 3 and m['key'] == 'bonk:migrated'
    o = lc({'mint': 'Raydium111', 'curve': False, 'vitals': {'ageH': 400}})
    assert (o['pad'], o['type'], o['graduated']) == ('UNKNOWN', 'established pool', None)                          # an old pool of unknown origin: never given a pad
    u = lc({'mint': 'Meteora111', 'curve': False, 'ageH': 5})
    assert (u['pad'], u['type'], u['measured']) == ('UNKNOWN', 'unknown', True)
    nm = lc({'mint': 'AbCpump'})
    assert (nm['type'], nm['measured'], nm['graduated'], nm['curvePct']) == ('unknown', False, None, None)         # no curve flag: nothing about it is claimed
    assert set(nm['notMeasured']) >= {'initial liquidity', 'migration time'}


def test_trigger_needs_more_confidence_on_an_unknown_launch_and_devil_objects_only_on_our_own_record():
    u = oe.launch_context({'mint': 'Meteora111', 'curve': False, 'ageH': 5})
    assert oe.launch_gate(u, 1.6, 1.5) and 'unknown launch context' in oe.launch_gate(u, 1.6, 1.5) and oe.launch_gate(u, 1.8, 1.5) is None
    assert oe.launch_gate(oe.launch_context({'mint': 'Pump111pump', 'curve': True}), 0.1, 1.5) is None              # a known mechanism is not penalised here (the Warden sizes it)
    assert oe.launch_gate(oe.launch_context({'mint': 'Meteora111'}), 0.1, 1.5) is None                              # an unmeasured row is never judged on its launch
    row = {'mint': 'X', 'safe': True, 'launch': {'key': 'unknown:unknown'}}
    bad = {'unknown:unknown': {'enterN': ag.PAD_MIN_N, 'enterMed5': -4.0}}
    assert ('pad_losing' in [a for a, _ in ag.devil_args('enter', {}, {'drivers': [], 'lean': 2}, row, {'pads': bad})]) is True
    thin = {'unknown:unknown': {'enterN': ag.PAD_MIN_N - 1, 'enterMed5': -9.0}}
    assert 'pad_losing' not in [a for a, _ in ag.devil_args('enter', {}, {'drivers': [], 'lean': 2}, row, {'pads': thin})]                  # under 15 of OUR entries: no claim
    assert ag.DEVIL_RULES['pad_losing'][0] is False                                                              # a soft objection, never a hard one
    rec = oe.pad_record([{'pad': 'pump:migrated', 'p5': x, 'p15': x * 2, 'kind': 'enter' if i % 2 else 'wait'} for i, x in enumerate([1, -2, 3, 4, -5, 6])] + [{'pad': 'bonk:migrated', 'p5': 1}])
    assert rec['pump:migrated']['n'] == 6 and rec['pump:migrated']['known'] and rec['pump:migrated']['won'] == 67 and rec['bonk:migrated']['known'] is False
    assert rec['pump:migrated']['enterN'] == 3 and rec['pump:migrated']['med5'] == 2.0
    assert ag.word('pad:pump:migrated').startswith('🚀') and 'pad:pump:migrated' in ag.drivers({}, {'launch': {'key': 'pump:migrated'}})


# ── 🔎 MISSED WINNERS ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _arch_case(m, at, **d):
    return {'at': at, 'd': {'mint': m, 'sym': m, 'px': 1.0, **d}, 'out': d.pop('out', {})}


def test_a_missed_winner_is_classified_from_what_was_known_then_and_safe_blocks_stay_right():
    cm = oe.classify_miss
    assert cm(None, [], None)[0] == 'NEVER DISCOVERED' and cm(None, [], None, held=True)[0] == 'HELD'
    assert cm(None, [], {'call': 'skip', 'why': 'failed holder scan'})[:4] == ('CORRECT SKIP — UNTRADEABLE / UNSAFE', 'trigger', 'failed holder scan', True)
    assert cm(None, [], {'call': 'skip', 'why': 'pool $8K'})[0] == 'LIQUIDITY RULE' and cm(None, [], {'call': 'wait', 'lean': -0.4})[0] == 'NO POSITIVE READ'
    assert cm(None, [], {'call': 'wait', 'lean': 1.0, 'why': 'under the bar'})[0] == 'WAITED TOO LONG'
    one = lambda **d: cm(_arch_case('A', 1, **d), [], None)
    assert one(data={'state': 'MALFORMED'})[0] == 'BAD DATA' and one(data={'state': 'MALFORMED'})[3] is True
    assert one(blocked=['devil'], devil=['object', ['rug_meter']]) == ('CORRECT SKIP — UNTRADEABLE / UNSAFE', 'devil', 'rug_meter', True)   # it pumped — the block was still right
    assert one(blocked=['pool'], launch={'type': 'bonding curve'})[0] == 'LAUNCHPAD RULE' and one(blocked=['pool'])[0] == 'LIQUIDITY RULE'
    assert one(blocked=['age'], ageH=0.4)[:3] == ('AGE RULE', 'devil', '0.4h old') and one(blocked=['scan'])[0] == 'HOLDER RULE'
    assert one(blocked=[], tally={'c1': 140})[0] == 'DISCOVERED TOO LATE' and one(blocked=['burn'])[0] == 'CREATOR POLICY'
    soft = one(blocked=['devil'], devil=['object', ['botted']])
    assert soft[0] == 'DEVIL OBJECTION' and soft[2] == 'botted' and soft[3] is False                              # a soft objection that blocked a winner: to re-examine on its record
    assert one(blocked=['chart'], chart={'entry': ['WAIT FOR PULLBACK', 'E5', 'extended']})[0] == 'WAITED TOO LONG'
    assert one(cleared=True, courier='BAD')[0] == 'EXECUTION BLOCK' and one(cleared=True, warden={'allowed': 0, 'rule': 'W9'})[0] == 'WARDEN ZEROED IT'
    assert one(cleared=True, noFill='NO CASH — $0.01')[0] == 'NO CASH' and one(cleared=True, noFill='FULL')[0] == 'NO SEAT'


def test_the_missed_winner_study_files_each_winner_once_with_paper_counterfactuals_and_stays_bounded():
    now = 50_000
    done = [{'mint': 'RUN', 'sym': 'RUN', 'at': now - 600, 'peak': 120.0, 'end': 80.0, 'x': {'50': now - 1800, '100': now - 1500}, 'f': ['age:1-3h']},
            {'mint': 'MEH', 'sym': 'MEH', 'at': now - 600, 'peak': 20.0, 'end': 5.0, 'x': {}},
            {'mint': 'HELD', 'sym': 'HELD', 'at': now - 600, 'peak': 90.0, 'end': 50.0, 'x': {'50': now - 1700}},
            {'mint': 'OLD', 'sym': 'OLD', 'at': now - 9 * 3600, 'peak': 300.0, 'end': 1.0, 'x': {}}]
    arch = {'cases': [_arch_case('RUN', now - 3000, cleared=True, noFill='FULL', out={'p5': 4.0, 'p15': 22.0, 'p60': 80.0}),
                      _arch_case('RUN', now - 2400, chart={'state': 'PULLBACK IN UPTREND', 'entry': ['ENTER NOW', 'E7', 'ok']}, out={'p5': 9.0})]}
    a, new = oe.missed_winners(arch, done, {}, now, held={'HELD'})
    assert [m['mint'] for m in new] == ['RUN'] and new[0]['reason'] == 'NO SEAT' and new[0]['leadMin'] == 20.0     # seen 20 min before it crossed +50%
    assert new[0]['counter']['firstCleared'] == {'at': now - 3000, 'p5': 4.0, 'p15': 22.0, 'p60': 80.0} and new[0]['counter']['firstPullback']['p5'] == 9.0
    assert new[0]['counter']['confirmedBreakout'] is None                                                         # no such moment on file → nothing invented
    a2, again = oe.missed_winners(a, done, {}, now, held={'HELD'})
    assert again == [] and len(a2['missed']) == 1                                                                 # filed once
    s = oe.missed_summary(a2, now)
    assert s['n'] == 1 and s['seen'] == 1 and s['byReason'][0]['key'] == 'NO SEAT' and s['counter']['firstCleared']['p15'] == 22.0 and 'Nothing here loosens a rule' in s['note']
    many = [{'mint': f'M{i}', 'sym': f'M{i}', 'at': now - 60 - i, 'peak': 60.0, 'end': 10.0, 'x': {}} for i in range(oe.MISSED_KEEP + 40)]
    big, _ = oe.missed_winners({}, many, {}, now)
    assert len(big['missed']) == oe.MISSED_KEEP                                                                   # bounded
    never = [{'mint': 'NX', 'sym': 'NX', 'at': now - 60, 'peak': 70.0, 'end': 9.0, 'x': {'50': now - 1200, '100': None}}]
    _, nx = oe.missed_winners({'cases': [_arch_case('NX', now - 2400, cleared=True, noFill='FULL')]}, never, {}, now)
    assert nx[0]['hitAt'] == now - 1200 and nx[0]['leadMin'] == 20.0                                              # a level never crossed (None) is not a time


# ── 📝 THE CREATOR'S REVIEW QUEUE ─────────────────────────────────────────────────────────────────────────────────────────────────
def _judged_state(now):
    mk = lambda i, kind, p5, **k: {'mint': f'C{i}', 'sym': f'C{i}', 'at': now - 600 - i, 'kind': kind, 'p5': p5, 'p15': p5, 'p60': p5, 'lean': 2.0, 'drivers': ['src:movers'], **k}
    return {'done': [mk(1, 'enter', -14.0, cs='PARABOLIC', ce='ENTER NOW', pad='pump:migrated'), mk(2, 'enter', 18.0, devil='object', devilRule='botted', pad='pump:migrated'),
                     mk(3, 'wait', 2.0, dq='MALFORMED'), *[mk(10 + i, 'enter', 1.0, pad='pump:migrated') for i in range(5)]]}


def test_the_review_queue_is_built_from_records_with_every_category_and_never_blocks_anything():
    now = 90_000
    r = oe.review(_judged_state(now), {'positions': [{'mint': 'P', 'sym': 'P', 'closedAt': now - 100, 'confirmed': True, 'realPct': 3.0, 'peak': 15.0, 'rule': 'R7 trailing protection'}]},
                  {'wardenLog': [{'sym': 'W', 'at': now - 50, 'move': 'fill', 'req': 1.0, 'allowed': 0.5, 'rule': 'W13', 'why': 'data'}]}, now)
    assert r['blocking'] is False and r['order'] == list(oe.REVIEW) and set(r['items']) == set(oe.REVIEW)
    assert r['items']['entry'][0]['sym'] == 'C1' and 'already ending' in r['items']['entry'][0]['lesson']
    assert r['items']['vetoes'][0]['rule'] == 'botted' and r['items']['data'][0]['rule'] == 'MALFORMED' and r['items']['exit'][0]['sym'] == 'P'
    assert r['items']['risk'][0]['agent'] == 'warden' and r['items']['launchpad'][0]['launch'] == 'pump:migrated'
    assert all(it['key'] and it['mark'] is None for its in r['items'].values() for it in its) and r['open'] == r['counts']
    k = r['items']['entry'][0]['key']
    marks = oe.mark_review({}, k, 'disagree', 'too early', now)
    r2 = oe.review(_judged_state(now), {}, {}, now, marks=marks)
    assert r2['items']['entry'][0]['mark']['mark'] == 'disagree' and r2['open']['entry'] == r2['counts']['entry'] - 1
    assert oe.item_key('entry', r2['items']['entry'][0]) == k                                                      # the same item keeps its key pass after pass
    with pytest.raises(ValueError):
        oe.mark_review({}, k, 'approve-trade', '', now)                                                           # a review mark is never an order
    assert oe.mark_review(marks, k, 'clear', '', now) == {}
    lots = {}
    for i in range(oe.MARKS_KEEP + 25):
        lots = oe.mark_review(lots, f'k{i}', 'seen', '', i)
    assert len(lots) == oe.MARKS_KEEP and 'k0' not in lots


def test_a_review_mark_changes_nothing_the_desks_decide():
    now = 7200
    cfg = {'agentTakePct': 10, 'agentMode': 'auto'}
    picks = [trow('NEW', lean=5)]
    st0 = _judged_state(now)
    before = (ag.manage([leg('A')], [trow('A', lean=-1)], {'PA': 0.97}, cfg, control=True, now=now, moves_left=1, picks=picks),
              of.reap([leg('A')], [trow('A')], {'PA': 1.14}, cfg, None, 3600)[1])
    marks = oe.mark_review({}, 'entry:C1:1', 'disagree', 'x', now)
    st1 = {**st0, 'reviewMarks': marks}
    after = (ag.manage([leg('A')], [trow('A', lean=-1)], {'PA': 0.97}, {**cfg, 'reviewMarks': marks}, control=True, now=now, moves_left=1, picks=picks),
             of.reap([leg('A')], [trow('A')], {'PA': 1.14}, cfg, None, 3600, office={'reviewMarks': marks})[1])
    assert json.dumps(before, sort_keys=True, default=str) == json.dumps(after, sort_keys=True, default=str)
    assert ag.learn(st0, 5) == ag.learn(st1, 5)                                                                   # the learning never reads a mark


# ── ⏱ SPEED ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_speed_counters_are_measured_bounded_and_none_when_nothing_was_measured():
    assert oe.speed_view({}) == {k: {'n': 0, 'med': None, 'avg': None, 'max': None} for k in ('seatEmpty', 'validToFill', 'exitToFill')}
    sp = {}
    for x in (10, 40, 20):
        sp = oe.speed_note(sp, 'seatEmpty', x)
    assert oe.speed_view(sp)['seatEmpty'] == {'n': 3, 'med': 20, 'avg': 23.3, 'max': 40}
    for x in range(oe.SPEED_KEEP + 10):
        sp = oe.speed_note(sp, 'exitToFill', x)
    assert len(sp['exitToFill']) == oe.SPEED_KEEP


# ── 🎓 THE STAGE: 5 minutes through breakeven, until real equity is 2× the put-in ───────────────────────────────────────────────────
def test_the_stage_stays_at_five_minutes_through_breakeven_until_real_equity_is_two_times_the_put_in():
    run = {'done': [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2, 'p5': 50.0} for i in range(30)]}
    for v in (1.0, 29.5, 45.0, 58.99):
        assert ag.stage({**run, 'money': {'value': v, 'putIn': 29.5}})['h'] == 5
    assert ag.stage({**run, 'money': {'value': 59.0, 'putIn': 29.5}})['h'] == 15
    m = of.mission({'value': 31.0, 'putIn': 29.5}, 9, ag.stage({**run, 'money': {'value': 31.0, 'putIn': 29.5}}), 0, 100)
    assert m['phase'] == 'GROWTH' and m['stage'] == 5 and m['locked'] is True                                     # past breakeven: still the 5-minute stage


# ── 🏢 THE SERVICE: one payload, the creator's POST ────────────────────────────────────────────────────────────────────────────────
class Req:
    def __init__(self, body=None): self._b = body or {}
    async def json(self): return self._b


def test_the_one_office_payload_carries_the_edge_pass_and_the_creators_post_saves_limits_and_review_marks(monkeypatch):
    import reputation_service as rs
    from test_office import _fresh, _one_pass
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    _fresh(rs)
    rs._office['boot'] = {'at': 4000, 'passes': 0, 'coins': 0, 'reconciled': False}
    _one_pass(rs, {}, 0)
    p = rs._office['payload']
    assert {'policy', 'ready', 'seat', 'switchEval', 'review', 'launch', 'ops'} <= set(p) and p['review']['blocking'] is False
    assert p['ops']['office'] == 'WARMING' and p['ops']['keeper'] == '1 active' and 'cycle' in p and isinstance(p['seatActions'], list)
    assert {c['key'] for c in p['policy']['controls']} == {k for k, *_ in oe.CONTROLS} and all(c['agentsNow'] for c in p['policy']['controls'])
    assert p['ready']['state'] == 'OFFICE WARMING UP' and set(p['performance']['speed']) >= {'seatEmpty', 'validToFill', 'exitToFill', 'seatWakes'}
    assert p['launch']['pads'] == oe.PADS and 'UNKNOWN' in p['launch']['source']
    monkeypatch.setattr(rs, '_require_owner', lambda r: None)

    async def no_ctl(on, now):
        return None
    monkeypatch.setattr(rs, '_agent_control_set', no_ctl)
    out = asyncio.run(rs.admin_agents_set(Req({'cfg': {'agentTp': 15, 'agentSl': 999, 'agentSwitch': 'conservative', 'agentAuthority': 'manual'}})))
    rc = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {})
    assert out['ok'] and rc['realCfg']['agentTp'] == 15.0 and rc['realCfg']['agentSl'] == oe.BOUNDS['agentSl'][1] and rc['realCfg']['agentAuthority'] == 'manual'
    assert {'agentTp', 'agentSl', 'agentSwitch', 'agentAuthority'} <= set(rc['realOwnerSet']) and {'agentTp'} <= set(rc['ladderKeep'])
    key = 'entry:X:1'
    p['review']['items']['entry'] = [{'key': key, 'mark': None, 'sym': 'X'}]
    r = asyncio.run(rs.admin_agents_set(Req({'review': {'key': key, 'mark': 'agree', 'note': 'right call'}})))
    assert r['review']['mark'] == 'agree' and p['review']['items']['entry'][0]['mark']['note'] == 'right call' and p['review']['open']['entry'] == 0   # the open page sees it at once
    assert rs._json_load(rs.OFFICE_PATH, {})['reviewMarks'][key]['mark'] == 'agree'
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_agents_set(Req({'review': {'key': key, 'mark': 'buy'}})))
    monkeypatch.setattr(rs, '_require_admin', lambda r: None)
    assert asyncio.run(rs.admin_agents_office(None))['review']['items']['entry'][0]['mark']['mark'] == 'agree'


# ── 🪑 FAST SEAT FILL + EVERY EMPTY SEAT HAS ONE PRIMARY REASON ────────────────────────────────────────────────────────────────────
def _fctx(**k):
    return {'control': True, 'pol': oe.policy({}), 'live': True, 'halt': None, 'courier': 'HEALTHY', 'used': 0, 'gos': [], 'wait': [{'mint': 'CLR', 'symbol': 'CLR'}],
            'empty': 2, 'emptySince': 900, 'lastFill': 0, 'now': 1000, **k}


def test_a_cleared_candidate_with_an_open_seat_cash_and_a_live_office_is_tried_without_the_ten_minute_duty():
    assert oe.fill_plan(_fctx()) == [{'mint': 'CLR', 'symbol': 'CLR'}]                                          # duty clock never asked
    assert oe.fill_plan(_fctx(lastFill=995)) == []                                                               # only the creator's seat target (auto 10s) may hold it
    assert oe.fill_plan(_fctx(lastFill=995, gos=[{'mint': 'GO'}])) == [{'mint': 'GO'}]                          # a full GO never waits
    assert oe.fill_plan(_fctx(wait=[])) == []                                                                    # no valid candidate → the seat stays cash


def test_nothing_is_tried_when_control_is_off_manual_warming_halted_courier_bad_or_the_budget_is_used():
    assert oe.fill_plan(_fctx(control=False)) == []
    assert oe.fill_plan(_fctx(pol=oe.policy({'agentAuthority': 'manual'}))) == []
    assert oe.fill_plan(_fctx(live=False)) == []
    assert oe.fill_plan(_fctx(halt='token balance below card books')) == []
    assert oe.fill_plan(_fctx(courier='BAD')) == []
    assert oe.fill_plan(_fctx(used=ag.CONTROL_MOVES_HR)) == []
    assert oe.fill_plan(_fctx(empty=0, gos=[{'mint': 'GO'}])) == []
    assert oe.fill_plan(_fctx(pol=oe.policy({'agentEntry': 'go'}))) == []                                        # entry style "GO only": a cleared case never fills
    assert oe.fill_plan(_fctx(courier='DEGRADED')) == [{'mint': 'CLR', 'symbol': 'CLR'}]                          # degraded = the Warden sizes it down, not a block


def test_every_empty_seat_carries_exactly_one_primary_reason_code():
    base = {'want': 4, 'held': 1, 'movesLeft': 3, 'freeUsd': 1.0, 'minUsd': 0.1, 'now': 1000, 'emptySince': 950, 'target': 30, 'live': True, 'control': True}
    code = lambda **k: oe.seat_state({**base, **k})
    for k, want in (({'control': False}, 'CREATOR POLICY'), ({'manual': True}, 'CREATOR POLICY'), ({'live': False}, 'OFFICE NOT LIVE'), ({'halt': 'halted'}, 'EXECUTION BLOCK'),
                    ({'courier': 'BAD'}, 'COURIER BLOCK'), ({'movesLeft': 0}, 'BUY BUDGET'), ({'freeUsd': 0.01}, 'NO CASH'), ({}, 'NO VALID ENTRY'),
                    ({'cases': [case('A', cleared=False, checks=[['scan', True, ''], ['chart', False, '']])]}, 'WAITING FOR CONFIRMATION'),
                    ({'cases': [case('A', cleared=False, checks=[['data', False, '']])]}, 'DATA DEGRADED'),
                    ({'cases': [case('A', cleared=False, checks=[['devil', False, '']])]}, 'NO CLEARED CANDIDATE'),
                    ({'cooled': ['OLD']}, 'REBUY COOLDOWN'),
                    ({'valid': [{'symbol': 'V'}], 'vetoed': 1}, 'WARDEN VETO'),
                    ({'valid': [{'symbol': 'V'}], 'timerIn': 12}, 'WAITING FOR SEAT TIMER')):
        s = code(**k)
        assert s['code'] == want and len(s['seats']) == 3 and all(x['code'] in oe.SEAT_CODES and x['reason'] for x in s['seats']), (k, s['code'])
        assert s['code'] in oe.SEAT_CODES
    one = code(valid=[{'symbol': 'V'}], cases=[case('A', cleared=False, checks=[['devil', False, '']])])
    assert [x['code'] for x in one['seats']] == ['FILLING', 'NO CLEARED CANDIDATE', 'NO CLEARED CANDIDATE']     # one valid coin fills one seat; the rest say why
    assert code(valid=[{'symbol': 'G', 'go': True}], timerIn=12)['code'] == 'FILLING'                           # a GO is never on the timer
    assert code(held=4)['seats'] == [] and code(held=4)['code'] == 'FULL'


def test_the_ops_line_reads_only_state_the_office_holds():
    s = oe.seat_state({'want': 4, 'held': 2, 'movesLeft': 5, 'freeUsd': 1.29, 'minUsd': 0.1, 'now': 1000, 'live': True, 'control': True,
                       'cases': [case('A', cleared=False, checks=[['devil', False, '']])]})
    o = oe.ops({'live': True}, {**s, 'movesLeft': 5, 'freeUsd': 1.29}, {'health': 'HEALTHY'}, True)
    assert o == {'office': 'LIVE', 'keeper': '1 active', 'openSeats': 2, 'valid': 0, 'cleared': 0, 'nextIn': None, 'block': s['reason'], 'code': 'NO CLEARED CANDIDATE',
                 'execution': 'HEALTHY', 'budget': {'left': 5, 'of': ag.CONTROL_MOVES_HR}, 'cash': 1.29}
    assert oe.ops({'live': False}, {'code': 'EXECUTION BLOCK', 'empty': 1}, {'health': 'HEALTHY'}, False)['execution'] == 'BLOCKED'
    assert oe.ops({}, {}, {'health': 'BAD'}, True)['execution'] == 'BLOCKED' and oe.ops({}, {}, {'health': 'DEGRADED'}, True)['execution'] == 'DEGRADED'


def test_a_coin_read_hours_ago_is_never_called_never_discovered_after_the_tape_evicted_it():
    now = 50_000
    st = {'first': {'OLD': {'t': now - 30 * 3600, 'c': 'w'}, 'KEEP': {'t': now - 600, 'c': 'w', 'r': 'RANGE', 'l': 1.2}}}
    fs = ag.first_seen(st, now)
    assert 'OLD' not in fs and 'KEEP' in fs                                                                      # bounded to 24h
    done = [{'mint': 'KEEP', 'sym': 'KEEP', 'at': now - 60, 'peak': 80.0, 'end': 20.0, 'x': {'50': now - 300}}]
    _, gone = oe.missed_winners({}, done, {}, now)                                                               # the tape lost it: nothing on file
    assert gone[0]['reason'] == 'NEVER DISCOVERED'
    _, kept = oe.missed_winners({}, done, {}, now, first_seen=fs)
    assert kept[0]['reason'] == 'WAITED TOO LONG' and kept[0]['seen'] is True and kept[0]['seenAt'] == now - 600
    big = ag.first_seen({'first': {f'M{i}': {'t': now - i} for i in range(ag.FIRST_KEEP + 50)}}, now)
    assert len(big) == ag.FIRST_KEEP and 'M0' in big                                                             # newest kept


def test_the_desk_stamps_each_coins_first_call_once():
    rows = [{'mint': 'A', 'symbol': 'A', 'price': 1.0, 'vol5m': 100, 'vol1h': 1000, 'buyShare': 55, 'liq': 60_000, 'ageH': 5, 'safe': True}]
    st, _ = ag.desk({}, rows, 1000)
    first = dict(st['first'])
    assert 'A' in first and first['A']['t'] == 1000
    st2, _ = ag.desk(st, [{**rows[0], 'price': 1.1}], 1060)
    assert st2['first']['A']['t'] == 1000                                                                        # the first stamp never moves


def test_a_coin_scanned_on_request_off_the_runner_board_is_judged_by_the_same_safety_gates(monkeypatch):
    import time as _t
    import reputation_service as rs
    pair = {'baseToken': {'address': 'OFFBOARDmint', 'symbol': 'OFF'}, 'pairAddress': 'POFF', 'priceUsd': '1', 'liquidity': {'usd': 80_000}, 'volume': {'h1': 60_000, 'm5': 5_000},
            'txns': {'h1': {'buys': 300, 'sells': 200}}, 'pairCreatedAt': (_t.time() - 100 * 3600) * 1000, 'marketCap': 2_000_000}
    monkeypatch.setattr(rs, '_runner_cands', [])
    monkeypatch.setattr(rs, '_open_pairs', [pair])
    rs._open_scan_memo.clear()
    assert next(r for r in rs._open_board() if r['mint'] == 'OFFBOARDmint')['safe'] is None                     # never scanned: says so
    rs._intel_cache['OFFBOARDmint'] = (_t.time(), {'mint': 'OFFBOARDmint', 'checkedAt': _t.time(), 'top10Pct': 18.0, 'devHoldingPct': 1.0, 'insiderPct': 1.0, 'bundledWallets': 0,
                                                    'sniperCount': 0, 'creator': None, 'topHolders': [{'pct': 5}], 'supply': 1e9})
    try:
        row = next(r for r in rs._open_board() if r['mint'] == 'OFFBOARDmint')
        c = rs._rn.candidate(pair, rs._intel_cache['OFFBOARDmint'][1], False, False, _t.time() * 1000)
        assert row['safe'] is (not rs._rn.safety_fails(c, rs._runner_cfg())) and row['safe'] is not None        # the scan now reaches the agents' row, judged the same way
    finally:
        rs._intel_cache.pop('OFFBOARDmint', None)


# ── 🔁 THE LIVE TRENCH: 60s cycle · full intake · stage-aware evidence · warnings vs vetoes ────────────────────────────────────────
def _brow(m, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'price': 1.0, 'ageH': 50, 'vol1h': 50_000, 'vol5m': 3000, 'chg5m': 1.0, 'curve': False, 'front': 40, **k}


def test_a_new_board_launch_reaches_the_intake_on_the_next_pass_however_busy_the_board_is():
    board = [_brow(f'OLD{i}', front=90 - i * 0.1, vol1h=900_000) for i in range(400)] + [_brow('BABY', ageH=0.01, vol1h=800, vol5m=800, front=3, curve=True)]
    got = oe.intake(board, recheck=['HELD'], listed={})
    tags = {x['mint']: x['intake'] for x in got}
    assert 'BABY' in tags and 'new' in tags['BABY'] and len(got) <= oe.INTAKE_MAX                                # seconds old, quiet, deep in the board: still read this pass
    held = oe.intake(board + [_brow('HELD', front=0)], recheck=['HELD'])
    assert held[0]['mint'] == 'HELD' and held[0]['intake'][0] == 'recheck'                                         # what the card holds is always re-read
    big = oe.intake(board + [_brow('WHALE', mcap=40_000_000, front=0.1)], listed={'WHALE': ['movers', 'volume']})
    assert any(x['mint'] == 'WHALE' and 'listed' in x['intake'] for x in big)                                     # a $1M+ coin stays eligible
    assert len({x['mint'] for x in got}) == len(got)                                                               # deduped


def test_market_cap_bands_classify_never_exclude_and_are_learned_from_the_record_only():
    assert [ag.mc_band(v) for v in (5_000, 60_000, 150_000, 300_000, 700_000, 5_000_000, None, 0)] == ['micro', 'early', 'building', 'momentum', 'established', '1m+', None, None]
    d = ag.drivers({'buy': 55, 'pts': 4}, {'mcap': 5_000_000})
    assert 'band:1m+' in d and ag.PRIOR.get('band:1m+') is None and ag.word('band:micro').startswith('💰 MICRO')   # no belief: only its own record weighs
    st, table = ag.desk({}, [{'mint': 'BIG', 'symbol': 'BIG', 'price': 1, 'mcap': 3_000_000, 'vol5m': 1, 'vol1h': 10, 'liq': 90_000, 'ageH': 300, 'safe': True}], 100)
    assert table and table[0]['band'] == '1m+'                                                                    # read, not dropped


def test_a_very_young_launch_is_not_rejected_for_its_age_and_uses_stage_aware_evidence():
    w = []
    assert ag.devil_args('enter', {'age': 0.05}, {'drivers': [], 'lean': 3}, {'safe': True, 'tv': {'rug': 5}}, {'busted': set()}, warns=w) == []
    assert w[0][0] == 'young' and ag.DEVIL_RULES['young'][0] is False                                              # age is a WARNING, never a veto
    rows = [[60 * i, 1.0 + 0.02 * i, 1.03 + 0.02 * i, 0.99 + 0.02 * i, 1.02 + 0.02 * i, 500] for i in range(4)]
    early = ci.read(rows, 240, True, 'candles', {'ageMin': 4, 'provider': 'jupiter', 'vol5m': 5000, 'vol1h': 20_000, 'liqAge': 0}, liq=40_000)
    assert early['state'] == 'EARLY' and early['q']['state'] == 'LIMITED_HISTORY' and early['q']['enterOk'] and early['entry'][0] == 'ENTER NOW'
    assert 'EARLY DATA' in early['q']['why'] and early['risk'][0] == 0.5                                          # labelled early, half size — never "bad data"
    old = ci.read(rows, 240, True, 'candles', {'ageMin': 600, 'provider': 'jupiter', 'vol5m': 5000, 'vol1h': 20_000, 'liqAge': 0}, liq=40_000)
    assert old['q']['state'] == 'SPARSE' and old['entry'][0] == 'WAIT FOR DATA'                                    # a 10h coin with 4 candles IS thin data
    spike = [[60 * i, 1.0, 1.0, 1.0, 1.0, 500] for i in range(3)] + [[180, 1.0, 1.3, 1.0, 1.25, 900]]
    assert ci.read(spike, 240, True, 'candles', {'ageMin': 4, 'provider': 'jupiter'})['entry'][0] == 'WAIT FOR PULLBACK'   # a +25% newborn candle is still never chased
    dump = [[60 * i, 1.0 - 0.03 * i, 1.0 - 0.03 * i, 0.97 - 0.03 * i, 0.98 - 0.03 * i, 500] for i in range(4)]
    assert ci.read(dump, 240, True, 'candles', {'ageMin': 4, 'provider': 'jupiter'})['entry'][0] == 'SKIP'
    tr = ag.trigger({'pts': 1, 'buy': 60, 'd5': 1}, {'lean': 5, 'drivers': []}, {'safe': True, 'chart': {'src': 'candles', 'f': {'n': 4}, 'q': {'enterOk': True}}}, {'bar': 1.5})
    assert tr[0] == 'enter'                                                                                       # its real candles count as readings
    assert ag.trigger({'pts': 1, 'buy': 60, 'd5': 1}, {'lean': 5, 'drivers': []}, {'safe': True}, {'bar': 1.5})[0] == 'wait'
    young = trow('YNG', ageH=0.2)
    assert ag.investigate([young], set(), 0)[0]['cleared'] and not ag.investigate([young], set(), 1)[0]['cleared']   # only the CREATOR's min-age setting can hold it


def test_devil_warnings_are_not_vetoes_but_hard_safety_still_is():
    why = {'lean': 3, 'drivers': [('src:volume', -0.4, 'found on volume leaders')]}
    w = []
    assert ag.devil_args('enter', {'age': 5}, why, {'safe': True, 'tv': {'rug': 5}}, {'busted': set()}, warns=w) == [] and w[0][0] == 'against'   # already in the lean: noted only
    strong = {'busted': set(), 'drivers': {'src:volume': {'n': 40, 'med': -6.0}}}
    pos = {'lean': 3, 'drivers': [('src:volume', 0.4, 'found on volume leaders')]}
    assert ag.devil_args('enter', {'age': 5}, pos, {'safe': True, 'tv': {'rug': 5}}, strong)[0][0] == 'driver_losing'   # a STRONG record is a veto
    mild = {'busted': set(), 'drivers': {'src:volume': {'n': 40, 'med': -1.0}}}
    assert ag.devil_args('enter', {'age': 5}, pos, {'safe': True, 'tv': {'rug': 5}}, mild) == []                          # a mild one only warns
    for row, n in (({'safe': None, 'tv': {'rug': 5}}, {}), ({'safe': True, 'tv': {'rug': 70}}, {}), ({'safe': True, 'tv': {'rug': 5}}, {'c1': 400})):
        assert ag.devil('enter', {'age': 5, **n}, why, row, {'busted': set()})[0] == 'object'                  # unscanned · rug meter · ran: never softened


def test_every_cycle_re_evaluates_held_seats_against_challengers_but_a_timer_never_forces_a_trade():
    pol = oe.policy({'agentSeatTarget': 60})
    assert oe.cycle_due(pol, 0, 61) and not oe.cycle_due(pol, 1000, 1030) and oe.cycle_due(oe.policy({'agentSeatTarget': 30}), 1000, 1031)
    assert oe.cycle_due(oe.policy({}), 1000, 1030) and not oe.cycle_due(oe.policy({}), 1000, 1020)               # never under 30s
    cfg = {'agentTakePct': 10, 'agentMode': 'auto', 'trenchMinAgeH': 1}
    legs = [leg('W', at=1), leg('L', at=1)]
    table = [trow('W', lean=0.1), trow('L', lean=0.1)]
    none = ag.manage(legs, table, {'PW': 1.05, 'PL': 0.9}, cfg, control=True, now=7200, moves_left=1, picks=[], rotate=True)
    assert all(x['action'] == 'hold' for x in none)                                                               # cycle due, no challenger: keep — nothing manufactured
    assert oe.fill_plan(_fctx(wait=[], gos=[])) == []
    new = [trow('NEW', lean=5)]
    d = {x['symbol']: x for x in ag.manage(legs, table + new, {'PW': 1.05, 'PL': 0.9}, cfg, control=True, now=7200, moves_left=1, picks=new, rotate=True)}
    assert d['W']['action'] == 'hold' and d['L']['action'] == 'swap'                                              # the winner is protected, the loser is challenged
    agg = oe.policy({'agentSwitch': 'aggressive'})
    weak = {'symbol': 'L', 'pnl': -5, 'heldMin': 40, 'lean': 0.2, 'verdict': 'weak'}
    assert not oe.switch_test(weak, {'symbol': 'N', 'lean': 0.6, 'cleared': True}, agg)['switch']               # aggressive: margin 0.4 < 0.5 — still superiority
    assert oe.switch_test(weak, {'symbol': 'N', 'lean': 0.8, 'cleared': True}, agg)['switch']
    assert not oe.switch_test({**weak, 'pnl': 3}, {'symbol': 'N', 'lean': 9, 'cleared': True}, agg)['switch']    # a winner is never surrendered for a new coin


def test_holder_scans_go_to_the_strongest_unscanned_reads_first():
    mk = lambda m, lean, safe=None, pace=0.0: {'mint': m, 'symbol': m, 'lean': lean, 'row': {'vitals': {'safe': safe}, 'nums': {'pace': pace}}}
    cases = [mk('weak', 0.3), mk('done', 9, safe=True), mk('strong', 4), mk('neg', -1), mk('mid', 2, pace=3), mk('mid2', 2, pace=1)]
    assert [c['mint'] for c in oe.scan_order(cases, 3)] == ['strong', 'mid', 'mid2']


def test_each_seat_says_what_it_is_doing_this_cycle_and_the_cycle_line_counts_the_funnel():
    seats = [{'kind': 'agent', 'symbol': 'A', 'pair': 'PA', 'pct': 3.0}, {'kind': 'agent', 'symbol': 'B', 'pair': 'PB', 'pct': -4.0},
             {'kind': 'yours', 'symbol': 'C', 'pair': 'PC', 'pct': -2.0}, {'kind': 'open', 'symbol': None}]
    dec = [{'pair': 'PA', 'action': 'hold', 'why': 'ok'}, {'pair': 'PB', 'action': 'swap', 'toSym': 'N'}, {'pair': 'PC', 'action': 'hold'}]
    sw = {'current': {'symbol': 'C'}, 'challenger': {'symbol': 'Z', 'cleared': True}, 'switch': False, 'why': 'held 10 min — needs 30'}
    seat = {'code': 'NO CLEARED CANDIDATE', 'reason': 'r', 'seats': [{'seat': 4, 'code': 'NO CLEARED CANDIDATE', 'reason': 'nothing cleared'}]}
    a = oe.seat_actions(seats, dec, sw, seat)
    assert [x['action'] for x in a] == ['HOLD', 'SWITCHING', 'CHALLENGER FOUND', 'CASH — NO VALID ENTRY'] and a[2]['to'] == 'Z' and a[3]['code'] == 'NO CLEARED CANDIDATE'
    assert all(x['action'] in oe.SEAT_ACTIONS for x in a)
    cy = oe.cycle_view({'board': 900, 'screened': 240, 'newLaunches': 120, 'by': {'new': 50}}, [{'band': 'micro'}, {'band': 'micro'}, {'band': '1m+'}],
                       [case('X'), case('Y', cleared=False)], {'X': {'src': 'candles'}, 'Y': {'src': 'tape'}}, {'X': {'t': 1000}, 'Y': {'t': 10}}, 1000, 940, 60, 7)
    assert cy['board'] == 900 and cy['screened'] == 240 and cy['reviewed'] == 1 and cy['cleared'] == 1 and cy['best']['symbol'] == 'X' and cy['newToDesk'] == 1
    assert cy['bands'] == {'micro': 2, '1m+': 1} and cy['nextIn'] == 0 and cy['n'] == 7


def test_the_decision_module_has_no_wallet_network_or_execution_path_of_its_own():
    import inspect
    src = inspect.getsource(oe)
    for bad in ('httpx', 'fuse_wallet', 'signTransaction', 'sendTransaction', 'import requests', '_fw_', 'asyncio'):
        assert bad not in src, bad                                                                                # fill_plan / intake / cycle only DECIDE; the existing keeper path executes


# ── ⚡ REALTIME: a case file never freezes the market state ─────────────────────────────────────────────────────────────────────────
def test_a_case_read_at_price_a_sees_price_b_and_a_new_candle_without_being_rediscovered(monkeypatch):
    import reputation_service as rs
    row = {**trow('LIVE'), 'px': 1.00}
    monkeypatch.setitem(rs._jup_px_cache, 'LIVE', (1000.0, 1.25))                                               # the shared price moved A → B
    v = rs._mkt_view('LIVE', 'PLIVE', 1005.0)
    assert v['px'] == 1.25 and v['pxSrc'] == 'jupiter' and v['pxAt'] == 1000.0
    chk = oe.live_check(row, v, None, 1005.0)
    assert chk['px'] == 1.25 and chk['move'] == 25.0 and not chk['ok'] and 'not chased' in chk['why']           # Trigger's line on the NEWEST price
    monkeypatch.setitem(rs._jup_px_cache, 'LIVE', (1001.0, 1.03))
    assert oe.live_check(row, rs._mkt_view('LIVE', 'PLIVE', 1005.0), None, 1005.0)['ok']                         # a small move: the read stands
    up = [[60 * i, 1.0 + 0.01 * i, 1.012 + 0.01 * i, 0.995 + 0.01 * i, 1.008 + 0.01 * i, 900] for i in range(20)]
    meta = {'provider': 'jupiter', 'vol5m': 9000, 'vol1h': 90_000, 'liqAge': 0, 'ageMin': 500}
    before = ci.read(up, 1200, True, 'candles', meta, liq=80_000)
    dump = up + [[1200, 1.2, 1.2, 0.9, 0.92, 4000]]                                                               # a new completed 1-minute candle lands
    after = ci.read(dump, 1260, True, 'candles', meta, liq=80_000)
    monkeypatch.setitem(rs._office['charts'], 'LIVE', after)
    assert before['entry'][0] != after['entry'][0] or after['entry'][0] != 'ENTER NOW'
    got = oe.live_check(row, rs._mkt_view('LIVE', 'PLIVE', 1265.0), rs._mkt_view('LIVE', 'PLIVE', 1265.0)['chart'], 1265.0)
    assert not got['ok'] and 'newest chart' in got['why']                                                         # the SAME case now reads the new candle


def test_freshness_reports_each_input_separately_and_says_none_when_nothing_was_measured():
    f = oe.freshness(1000, [990, None, 995], [970], [940], 980, 950, 998)
    assert f == {'price': 5.0, 'tape': 30.0, 'candle': 60.0, 'liquidity': 20.0, 'agentInput': 50.0, 'decision': 2.0}
    assert oe.freshness(1000) == {'price': None, 'tape': None, 'candle': None, 'liquidity': None, 'agentInput': None, 'decision': None}


def test_a_thirty_second_old_launch_enters_the_intake_and_graduation_is_only_context():
    board = [_brow(f'B{i}', front=80) for i in range(300)] + [_brow('NOW', ageH=30 / 3600, curve=True, mcap=6_000), _brow('GRAD', ageH=2, curve=False, vol1h=40_000)]
    tags = {x['mint']: x['intake'] for x in oe.intake(board)}
    assert 'new' in tags['NOW'] and 'grad' in tags['GRAD']
    assert ag.stage_of(30 / 3600) == 'NEWBORN' and ag.stage_of(0.5) == 'EARLY' and ag.stage_of(5) == 'DEVELOPING' and ag.stage_of(48) == 'MATURE' and ag.stage_of(None) is None
    two = trow('TWO', ageH=2 / 60)
    c = ag.investigate([two], set(), ag.min_age_of({}))[0]
    assert c['cleared'] and 'NEWBORN' in dict((k[0], k[2]) for k in c['checks'])['age']                         # evaluated, labelled — not rejected
    assert ag.min_age_of({}) == 0 and ag.min_age_of({'agentMinAgeH': 1}) == 1 and ag.min_age_of({'agentMinAgeH': 7}) == 0 and ag.min_age_of({'trenchMinAgeH': 1}) == 0
    assert oe.clean_policy({'agentMinAgeH': 0.25})['agentMinAgeH'] == 0.25 and any(x['key'] == 'agentMinAgeH' for x in oe.controls({}))
    rows = [[60 * i, 1.0 + 0.01 * i, 1.015 + 0.01 * i, 0.995 + 0.01 * i, 1.008 + 0.01 * i, 100 + i] for i in range(3)]
    q = ci.read(rows, 180, True, 'candles', {'ageMin': 3, 'provider': 'jupiter'})['q']
    assert q['state'] == 'LIMITED_HISTORY' and q['state'] not in ('MALFORMED', 'INCONSISTENT', 'STALE', 'UNTRUSTED')   # few candles ≠ DATA INVALID


# ── ♻ SAME COIN AGAIN ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_rejected_coin_waits_until_something_material_changes():
    rej = case('R', cleared=False, checks=[['scan', True, ''], ['chart', False, 'RANGE → WAIT FOR BREAKOUT']])
    row = {**trow('R'), 'px': 1.0}
    m = oe.note_seen({}, [row], [rej], {'R'}, 1000)
    e = m['R']
    assert e['first'] == 1000 and e['review'] == 1000 and 'WAIT FOR BREAKOUT' in e['reject']
    assert not oe.review_due(e, 1060)[0]                                                                          # rejected 60s ago, nothing new
    assert oe.review_due(e, 1000 + oe.REVIEW_COOL_SEC)[0]                                                         # bounded: the cooldown ends
    m2 = oe.note_seen(m, [{**row, 'px': 1.08}], [rej], set(), 1060)
    due, why = oe.review_due(m2['R'], 1060)
    assert due and 'price' in why                                                                                  # a material move wakes it at once
    m3 = oe.note_seen(m, [{**row, 'vitals': {**row['vitals'], 'safe': None}}], [rej], set(), 1030)
    m3 = oe.note_seen(m3, [row], [rej], set(), 1050)
    assert oe.review_due(m3['R'], 1050)[0] and 'scan' in oe.review_due(m3['R'], 1050)[1]                         # a holder scan landing wakes it
    m4 = oe.note_seen(m, [{**row, 'chart': {'state': 'CONFIRMED BREAKOUT'}}], [rej], set(), 1040)
    assert oe.review_due(m4['R'], 1040)[0]                                                                        # a breakout wakes it
    board = [_brow('R', front=99, ageH=8)] + [_brow(f'X{i}', front=50, ageH=8) for i in range(300)]
    assert 'busy' in {x['mint']: x['intake'] for x in oe.intake(board)}['R']                                       # without news it would take a busy seat first …
    stale = [_brow('S', front=99, ageH=500, vol5m=500)] + [_brow(f'X{i}', front=50) for i in range(300)]
    assert 'S' not in {x['mint'] for x in oe.intake(stale)}                                                         # 🆕 12h+ and not waking up: no seat at the table
    assert 'R' not in {x['mint'] for x in oe.intake(board, cool={'R'})}                                            # … cooled, the seat goes to a coin with news


def test_holder_scans_follow_the_priority_tiers():
    mk = lambda m, lean, checks, ageH=8, pace=0.0, liq=60_000: {'mint': m, 'symbol': m, 'lean': lean, 'checks': checks,
                                                                 'row': {'vitals': {'safe': None, 'ageH': ageH, 'liq': liq}, 'nums': {'pace': pace, 'liq': liq}}}
    only = [['scan', False, ''], ['age', True, ''], ['devil', True, '']]
    more = [['scan', False, ''], ['devil', False, '']]
    cases = [mk('plain', 3.0, more), mk('chal', 0.5, more), mk('fresh', 0.4, more, ageH=0.1, pace=3), mk('blockonly', 0.6, only), mk('near', 2.0, only)]
    got = oe.scan_order(cases, 5, challengers={'chal'})
    assert [c['mint'] for c in got] == ['near', 'blockonly', 'fresh', 'chal', 'plain'] and got[0]['scanTier'] == oe.SCAN_TIERS[0]


# ── 🔎 SOCIAL RESEARCH (fixtures only — the suite never opens a live site) ─────────────────────────────────────────────────────────
def _fx(name):
    import pathlib
    return (pathlib.Path(__file__).parent / 'fixtures' / 'social' / name).read_text()


def test_website_and_x_research_cross_check_the_mint_and_classify_the_narrative():
    import social_research as sr
    MINT = 'FroGGyMint1111111111111111111111111111pump'
    site = sr.site_read(_fx('site_match.html'), 'https://froggy.fun', MINT)
    assert site['mintMatch'] == 'yes' and site['x'] == ['froggy_sol'] and site['tg'] == ['froggyportal'] and site['title'].startswith('FROGGY')
    x = sr.x_read(_fx('x_profile.html'), 'https://x.com/froggy_sol', MINT, now=1791700000)
    assert x['available'] and x['followers'] == 12500 and x['following'] == 1204 and x['mintMentioned'] and x['website'] == 'https://froggy.fun'
    assert x['posts'][0]['text'].startswith('frog szn') and x['lastPostAt']
    row = {'mint': MINT, 'symbol': 'FROGGY', 'name': 'Froggy', 'x': 'https://x.com/froggy_sol', 'site': 'https://froggy.fun'}
    p = sr.packet(row, site, x, now=x['lastPostAt'] + 3600)
    assert p['cross']['mintMatch'] == 'yes' and p['cross']['siteLinksX'] is True and p['cross']['xLinksSite'] is True and not p['cross']['conflict']
    assert p['cross']['confidence'] >= 80 and p['narrative']['class'] == 'ANIMAL' and p['social'] == 'ACTIVE' and p['narrative']['class'] in sr.NARRATIVES
    bad = sr.site_read(_fx('site_other_mint.html'), 'https://froggy-official.xyz', MINT)
    pb = sr.packet(row, bad, None, now=1)
    assert bad['mintMatch'] == 'no' and pb['cross']['conflict'] and pb['cross']['confidence'] < 40 and pb['warnings'] and pb['cross']['siteLinksX'] is False


def test_unavailable_social_is_unknown_never_a_veto_and_identity_only_shrinks_a_seat():
    import social_research as sr
    wall = sr.x_read(_fx('x_wall.html'), 'https://x.com/whoever', 'M')
    assert wall['available'] is False and sr.freshness(wall, 0) == 'UNAVAILABLE' and sr.freshness(None, 0) == 'UNKNOWN'
    p = sr.packet({'mint': 'M', 'symbol': 'NEW'}, None, None, now=1)
    assert p['cross']['confidence'] is None and p['social'] == 'UNKNOWN' and p['warnings'] == []                  # nothing to judge: unknown, not low
    row = {'safe': True, 'tv': {'rug': 5}, 'social': p}
    assert ag.devil('enter', {'age': 0.1}, {'lean': 3, 'drivers': []}, row, {'busted': set()})[0] == 'agree'
    conflict = sr.packet({'mint': 'M', 'symbol': 'X'}, sr.site_read(_fx('site_other_mint.html'), 'https://a.xyz', 'M'), None, now=1)
    w = []
    assert ag.devil_args('enter', {'age': 5}, {'lean': 3, 'drivers': []}, {'safe': True, 'tv': {'rug': 5}, 'social': conflict}, {'busted': set()}, warns=w) == []
    assert any(x[0] == 'identity' for x in w)                                                                      # a WARNING …
    ctx = {'value': 4.0, 'putIn': 4.0, 'cash': 4.0, 'seats': 1, 'liq': 90_000, 'ageH': 10, 'd5': 1, 'top10': 10, 'courier': 'HEALTHY', 'social': conflict}
    wd = of.warden(1.0, ctx, {})
    assert wd['allowed'] <= 0.25 + 1e-9 and any(r['id'] == 'W16 identity' for r in wd['rules'])                    # … and a smaller seat, never a bigger one
    hype = {**ctx, 'social': sr.packet({'mint': 'M', 'symbol': 'MOON'}, None, {'available': True, 'posts': [{'text': 'moon lfg send it', 'at': 1}], 'lastPostAt': 1, 'url': 'u'}, now=2)}
    assert of.warden(1.0, hype, {})['allowed'] <= 1.0


def test_research_reuses_its_cache_picks_only_the_strongest_and_fetches_each_page_once():
    import social_research as sr
    calls = []

    async def fake(url):
        calls.append(url)
        return _fx('site_match.html') if 'froggy.fun' in url else _fx('x_profile.html')
    row = {'mint': 'FroGGyMint1111111111111111111111111111pump', 'symbol': 'FROGGY', 'site': 'https://froggy.fun', 'x': 'https://x.com/froggy_sol'}
    p, n = asyncio.run(sr.research(row, fetch=fake, now=1000))
    assert n == 2 and calls == ['https://froggy.fun', 'https://x.com/froggy_sol'] and p['cross']['mintMatch'] == 'yes'   # one fetch per page
    cache = {row['mint']: p}
    assert not sr.due(cache, row['mint'], 1000 + 60) and sr.due(cache, row['mint'], 1000 + sr.TTL['social'])
    cases = [{'mint': row['mint'], 'lean': 3, 'cleared': True}, {'mint': 'B', 'lean': 2}, {'mint': 'C', 'lean': 1}, {'mint': 'D', 'lean': 0.5}, {'mint': 'E', 'lean': -1}]
    assert [c['mint'] for c in sr.pick(cases, cache, 1100)] == ['B', 'C', 'D']                                   # cached one skipped, a negative read never opened
    calls.clear()
    nolink = {'mint': 'ZZ', 'symbol': 'ZZ'}

    async def search(url):
        calls.append(url)
        return '<a class="result__a" href="https://zz.fun">ZZ</a>' if 'duckduckgo' in url else _fx('site_match.html')
    _, n2 = asyncio.run(sr.research(nolink, fetch=search, now=1000))
    assert n2 == 2 and 'duckduckgo' in calls[0]                                                                    # one bounded search only when it carries no link
    _, n3 = asyncio.run(sr.research(nolink, fetch=search, now=1000, cache_search={'ZZ': 999}))
    assert n3 == 0                                                                                                 # searched recently: not again


def test_build_hashes_and_hex_ids_are_never_read_as_another_contract():
    import social_research as sr
    html = ('<html><head><script src="/_next/static/chunks/ec3933a1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9.js"></script></head>'
            '<body class="Xk9qPz3LmN2vB7rT5yW1aE4sD6fG8hJ"><p>Welcome to the frog pond</p></body></html>')
    s = sr.site_read(html, 'https://frog.fun', 'FroGGyMint1111111111111111111111111111pump')
    assert s['mints'] == [] and s['mintMatch'] == 'unknown' and not sr.crosscheck('FroGGyMint1111111111111111111111111111pump', None, s, None)['conflict']
    assert sr.mints_in('CA: 9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin') == ['9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin']


def test_a_website_without_any_x_link_is_not_called_a_different_x():
    import social_research as sr
    s = sr.site_read('<html><title>Human</title><body>gm</body></html>', 'https://human.ai', 'M')
    cc = sr.crosscheck('M', 'https://x.com/human_ai', s, None)
    assert cc['siteLinksX'] is None and cc['flags'] == []


def test_a_research_browser_left_running_is_found_and_only_ours_are_touched():
    import social_research as sr
    lines = ['66983 19:48 /x/chrome-headless-shell --headless --user-data-dir=/tmp/feeless-research-ab12 --dump-dom https://a.fun',
             '70001 00:05 /x/chrome-headless-shell --user-data-dir=/tmp/feeless-research-cd34 --dump-dom https://b.fun',
             '70002 1-02:00:00 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
             '70003 45:00 /x/chrome-headless-shell --user-data-dir=/Users/me/profile']
    assert sr.orphans(lines) == [66983]                                                                         # ours and old: killed; a fresh fetch / the user's own Chrome: never
    assert sr._etime_sec('1-02:03:04') == 93784 and sr._etime_sec('05') == 5 and sr._etime_sec('19:48') == 1188


# ── 🧾 PROOF: every social / identity claim carries its evidence ────────────────────────────────────────────────────────────────────
NO_WORDS = ('legit', 'verified', 'backed', 'real project', 'official', 'active community', 'safe token')


def _strings(x):
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in _strings(v)]
    return [x.lower()] if isinstance(x, str) else []


def test_every_research_claim_carries_its_source_url_time_title_and_exact_mint_match():
    import social_research as sr
    MINT = 'AcmeAgentMint11111111111111111111111111pump'
    calls = []

    async def fake(url):
        calls.append(url)
        return _fx('terms.html') if url.endswith('/terms') else _fx('site_legal.html') if 'acme.ai' in url else _fx('x_wall.html')
    row = {'mint': MINT, 'symbol': 'ACME', 'name': 'Acme', 'site': 'https://acme.ai', 'x': 'https://x.com/acme_ai'}
    p, n = asyncio.run(sr.research(row, fetch=fake, now=5000))
    assert n == 3 and calls == ['https://acme.ai', 'https://x.com/acme_ai', 'https://acme.ai/terms']                  # ONE bounded legal read, from a link the project gave
    ev = {e['kind']: e for e in p['evidence']}
    assert set(ev) == {k for k, _ in sr.EVIDENCE_KINDS}
    w = ev['website']
    assert w['status'] == 'FOUND' and w['url'] == 'https://acme.ai' and w['fetchedAt'] == 5000 and w['title'].startswith('ACME') and w['mintMatch'] == 'YES'
    assert w['launchMint'] == MINT and w['sourceMint'] == MINT and MINT in w['excerpt']
    assert ev['x']['status'] == 'UNKNOWN' and 'login wall' in ev['x']['note']                                          # signed-out wall: unknown, never "inactive"
    assert ev['launch']['status'] == 'FOUND' and ev['launch']['url'] == f'https://pump.fun/coin/{MINT}' and 'not opened' in ev['launch']['note']
    assert ev['telegram']['url'] == 'https://t.me/acmeportal' and ev['github']['url'] == 'https://github.com/acme-labs/agent'
    assert ev['audit']['status'] == 'FOUND' and 'certik' in ev['audit']['url'] and 'never guarantees' in ev['audit']['note']
    assert ev['terms']['url'] == 'https://acme.ai/terms' and ev['terms']['fetchedAt'] == 5000 and ev['terms']['note'] == 'opened and read'
    lg = p['legal']
    assert lg['level'] == 'PARTIAL' and lg['entity'] == 'Acme Labs Ltd' and lg['jurisdiction'] == 'England and Wales' and lg['regRef'] == '12345678'
    assert {'ENTITY FOUND', 'ENTITY NOT VERIFIED', 'TERMS FOUND', 'REGISTRATION NUMBER SHOWN', 'AUDIT DOCUMENT FOUND'} <= set(lg['labels'])
    assert 'no public registry was checked' in lg['note'] and lg['level'] != 'STRONG'                                 # STRONG needs a registry: never claimed
    assert ev['legal']['status'] == 'FOUND' and ev['legal']['url'] == 'https://acme.ai/terms' and 'PARTIAL' in ev['legal']['note']
    assert p['narrative']['class'] == 'AI / TECH' and p['narrative']['sources'] and all(s_['keywords'] for s_ in p['narrative']['sources'])
    for s_ in _strings({'ev': p['evidence'], 'legal': p['legal']}):
        assert not any(wd in s_.replace('not verified', '') for wd in NO_WORDS), s_                                      # no blanket "legit / verified / official" label ("ENTITY NOT VERIFIED" is the fact)


def test_missing_evidence_is_unknown_and_a_mint_mismatch_keeps_its_proof_through_devil_warden_and_the_archive():
    import social_research as sr
    p0 = sr.packet({'mint': 'Zz9noLinksMint1111111111111111111111111', 'symbol': 'ZZ'}, None, None, now=1)
    st0 = {e['kind']: e['status'] for e in p0['evidence']}
    assert st0 == {'website': 'UNKNOWN', 'x': 'UNKNOWN', 'launch': 'UNKNOWN', 'telegram': 'UNKNOWN', 'github': 'UNKNOWN', 'legal': 'UNKNOWN', 'terms': 'UNKNOWN', 'audit': 'UNKNOWN'}
    assert p0['legal']['level'] == 'NONE' and p0['cross']['confidence'] is None
    MINT = 'FroGGyMint1111111111111111111111111111pump'
    bad = sr.site_read(_fx('site_other_mint.html'), 'https://froggy-official.xyz', MINT)
    pk = sr.packet({'mint': MINT, 'symbol': 'FROGGY', 'x': 'https://x.com/froggy_sol'}, bad, None, now=777)
    w = next(e for e in pk['evidence'] if e['kind'] == 'website')
    other = bad['mints'][0]
    assert w['mintMatch'] == 'NO' and w['launchMint'] == MINT and w['sourceMint'] == other != MINT and w['url'] == 'https://froggy-official.xyz'
    assert pk['cross']['sourceUrl'] == 'https://froggy-official.xyz' and pk['cross']['sourceMint'] == other
    row = {**trow('FROGGY'), 'mint': MINT, 'social': pk}
    warns = []
    ag.devil_args('enter', row['nums'], row['why'], row, {}, warns=warns)
    idw = ' '.join(w_[1] for w_ in warns if w_[0] == 'identity')
    assert 'froggy-official.xyz' in idw and other[:8] in idw and MINT[:8] in idw                                    # Devil's warning names launch mint, source URL, source mint
    wd = of.warden(1.0, {'value': 4.0, 'liq': 500_000, 'ageH': 20, 'courier': 'HEALTHY', 'social': pk})
    w16 = next(r_ for r_ in wd['rules'] if r_['id'] == 'W16 identity')
    assert w16['mult'] == 0.25 and w16['evidence']['sourceUrl'] == 'https://froggy-official.xyz' and w16['evidence']['launchMint'] == MINT
    c = {'mint': MINT, 'symbol': 'FROGGY', 'px': 1.0, 'cleared': False, 'checks': [], 'row': row}
    rec = of.lineage_of(c, {'warden': {**wd, 'decided': 'W16 identity'}})
    assert rec['evidence']['sourceMint'] == other and rec['evidence']['sourceUrl'] == 'https://froggy-official.xyz' and rec['evidence']['launchMint'] == MINT
    assert rec['warden']['evidence']['sourceUrl'] == 'https://froggy-official.xyz' and ['website', 'FOUND', 'https://froggy-official.xyz'] in rec['evidence']['items']
