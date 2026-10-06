import pg_sim as ps

NOW = 1_000_000.0


def paths(fn, mints=8, hours=24):
    steps = int(hours * 60 // 5)
    start = NOW - hours * 3600
    return {f'M{i}': [[start + k * 300, fn(i, k)] for k in range(steps + 1)] for i in range(mints)}


def test_flat_market_costs_only_the_swap_fees_and_sims_are_deterministic():
    flat = paths(lambda i, k: 1.0)
    a = ps.run(flat, NOW, n=50, seed=7); b = ps.run(flat, NOW, n=50, seed=7)
    assert len(a) == 50 and a == b
    assert all(r['pct'] <= 0 for r in a)                                           # nothing moved → never a fake gain
    assert all(-ps.SWAP_COST * 100 - 0.01 < r['pct'] for r in a if r['cfg']['minDrop'] > 0)   # rotate-only-losers: just the entry cost
    churn = [r['pct'] for r in a if r['cfg']['minDrop'] == 0 and r['cfg']['clock'] == 5]
    assert not churn or min(churn) < -20                                            # 'rotate anything' every 5 min = fees eat the card


def test_a_runner_that_keeps_going_rewards_the_hold_rule():
    up = paths(lambda i, k: (1 + 0.012 * k) if i == 0 else 1.0)    # M0 climbs ~+300% over the day
    series = ps._series(up, NOW - 24 * 3600, 288)
    hold = ps.simulate(series, ['M0', 'M1', 'M2', 'M3'], {'clock': 60, 'tp': 50, 'sl': 30, 'minDrop': 10, 'hold': True}, 288)
    no_hold = ps.simulate(series, ['M0', 'M1', 'M2', 'M3'], {'clock': 60, 'tp': 50, 'sl': 30, 'minDrop': 10, 'hold': False}, 288)
    assert no_hold > 0 and hold > 0


def test_learn_and_best_rank_trait_values():
    res = [{'cfg': {'clock': 5, 'hold': True}, 'pct': 4.0}] * 12 + [{'cfg': {'clock': 60, 'hold': False}, 'pct': -2.0}] * 12
    b = ps.best(ps.learn(res))
    assert b['clock']['value'] == '5' and b['hold']['value'] == 'True' and b['clock']['upPct'] == 100.0
    assert ps.summary(res)['n'] == 24 and ps.run({}, NOW) == []


def test_brain_ranks_by_the_typical_card_not_one_moonshot():
    res = [{'cfg': {'minDrop': 0}, 'pct': -10.0}] * 11 + [{'cfg': {'minDrop': 0}, 'pct': 2000.0}] + [{'cfg': {'minDrop': 10}, 'pct': 3.0}] * 12
    assert ps.best(ps.learn(res))['minDrop']['value'] == '10'      # the average would have picked 0 because of one +2000%


def test_freeze_then_peak_trail_banks_a_pump_that_would_round_trip():
    # coin pumps +40% over 2h, then gives it all back; a +15% freeze with an 8% peak trail sells near the top
    up = lambda i, k: (1.0 + min(k, 24) * 0.4 / 24 - max(0, k - 24) * 0.4 / 24 if k < 48 else 1.0) if i == 0 else 1.0
    series = ps._series(paths(up), NOW - 24 * 3600, 288)
    base = {'clock': 5, 'tp': 300, 'sl': 30, 'minDrop': 10, 'confirm': 4, 'trail': 8}
    frozen = ps.simulate(series, ['M0', 'M1', 'M2', 'M3'], {**base, 'rideAt': 15}, 288)
    off = ps.simulate(series, ['M0', 'M1', 'M2', 'M3'], {**base, 'rideAt': 0}, 288)
    assert frozen > off + 4                                                         # the pump was banked, not round-tripped


def test_three_different_strategies_per_clock_with_their_own_proof():
    res = ps.run(paths(lambda i, k: 1.0 + 0.002 * k * (1 if i % 2 else -0.5)), NOW, n=300, seed=3)
    bc = ps.by_clock(res)
    assert bc and all(len(v['strategies']) == 3 for v in bc.values())
    for v in bc.values():
        sigs = {tuple(sorted(s['cfg'].items())) for s in v['strategies']}
        assert len(sigs) == 3 and {s['key'] for s in v['strategies']} == {'steady', 'engine', 'hunt'}
        assert all(s['n'] > 0 and 'rideAt' in s['cfg'] and 'trail' in s['cfg'] for s in v['strategies'])


def test_strategies_endpoint_picks_the_card_clock_or_the_nearest(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    S = lambda k: [{'key': k, 'name': k, 'cfg': {'tp': '100'}, 'n': 9, 'medPct': 1.0}]
    rs._json_save(rs.PG_SIM_PATH, {'byClock': {'5': {'n': 70, 'strategies': S('five')}, '60': {'n': 70, 'strategies': S('hour')}}})
    five = asyncio.run(rs.fuse_strategies(hours=0.08))
    assert five['clock'] == 5 and five['strategies'][0]['key'] == 'five' and five['note'] == ''
    day = asyncio.run(rs.fuse_strategies(hours=24))
    assert day['clock'] == 60 and 'nearest' in day['note']


def test_settings_losing_in_both_windows_are_retired_for_a_day_and_a_trait_never_loses_every_value():
    import pg_sim as ps
    s = lambda med, up, n=20: {'n': n, 'medPct': med, 'avgPct': med, 'upPct': up}
    s24 = {'tp': {'50': s(-4, 30), '100': s(2, 60), '200': s(-1, 45)}, 'sl': {'15': s(-3, 20), '20': s(-6, 10)}}
    s6 = {'tp': {'50': s(-2, 40), '100': s(-1, 40), '200': s(3, 70)}, 'sl': {'15': s(-2, 30), '20': s(-9, 5)}}
    r = ps.retire(s24, s6, None, 1000.0)
    assert set(r['tp']) == {'50'} and set(r['sl']) == {'15', '20'}                    # losing in BOTH windows only
    b = ps.best(s24, 10, r)
    assert b['tp']['value'] == '100' and b['sl']['value'] == '15'                     # tp 50 is out; sl lost everything → the least-bad stays
    assert ps.best({'tp': {'50': s(9, 90), '100': s(2, 60)}}, 10, {'tp': {'50': {}}})['tp']['value'] == '100'   # retired = not picked, even on top
    good = {'tp': {'50': s(5, 80)}}
    assert '50' in ps.retire(good, good, r, 1000.0 + 3600)['tp']                      # an hour later, looking fine: still sits out its day
    assert ps.retire(good, good, r, 1000.0 + 90000) == {}                             # a day later and no longer losing: back


def test_the_sim_keeps_the_coins_that_died_and_sells_them_under_their_last_reading():
    # M0 stops trading 2h in (off the feed); the others are flat. The old sim dropped M0 from the replay entirely (survivors only).
    def pts(i):
        last = 24 if i == 0 else 288
        return [[NOW - 24 * 3600 + k * 300, 1.0] for k in range(last)]
    gone = {f'M{i}': pts(i) for i in range(8)}
    series = ps._series(gone, NOW - 24 * 3600, 288)
    assert 'M0' in series and series['M0'][0] == 1.0 and series['M0'][-1] is None
    cfg = {'clock': 60, 'tp': 300, 'sl': 30, 'minDrop': 20, 'confirm': 4}
    with_dead = ps.simulate(series, ['M0', 'M1', 'M2', 'M3'], cfg, 288)
    alive = ps.simulate(series, ['M4', 'M1', 'M2', 'M3'], cfg, 288)
    assert alive == round(-ps.SWAP_COST * 100, 3)                                   # flat coins: just the entry cost
    assert with_dead < alive - 25 * ps.GONE_HAIRCUT                                  # a quarter of the card took the haircut (+ re-entry costs)
    # an impossible UP-tick (bad read) drops the path; a crash of any size is real and stays
    spike = {**gone, 'S': [[NOW - 24 * 3600 + k * 300, 1.0 if k < 50 else 9.0] for k in range(288)], 'R': [[NOW - 24 * 3600 + k * 300, 1.0 if k < 50 else 0.05] for k in range(288)]}
    s2 = ps._series(spike, NOW - 24 * 3600, 288)
    assert 'S' not in s2 and s2['R'][-1] == 0.05


def test_with_the_boards_rounds_a_card_buys_only_what_was_offered_and_its_selection_genes_apply():
    mk = lambda px: [[NOW - 6 * 3600 + k * 300, px(k)] for k in range(72)]
    paths_ = {'OLD': mk(lambda k: 1.0), 'NEW': mk(lambda k: max(0.05, 1.0 - 0.02 * k)), 'X': mk(lambda k: 1.0)}
    snap = lambda m, age, liq: {'mint': m, 'score': 50, 'ageH': age, 'liq': liq}
    rounds = [{'at': NOW - 6 * 3600 - 60 + i * 900, 'picks': [snap('NEW', 0.5, 20000), snap('OLD', 20, 200000)]} for i in range(24)]   # X is never offered
    off = ps.offers(rounds, NOW - 6 * 3600, 72)
    assert [p['mint'] for p in off[0]] == ['NEW', 'OLD'] and ps.offers([], NOW, 3) == [[], [], []]
    series = ps._series(paths_, NOW - 6 * 3600, 72)
    cfg = {'clock': 15, 'tp': 300, 'sl': 20, 'minDrop': 5, 'confirm': 1, 'age': 0, 'pool': 0}
    loose = ps.simulate(series, ['NEW', 'OLD'], cfg, 72, offer=off, seats=2)
    strict = ps.simulate(series, ['OLD'], {**cfg, 'age': 12, 'pool': 100}, 72, offer=off, seats=2)      # only OLD qualifies; the other seat waits in cash
    assert strict > loose and strict > -2 and ps.simulate.trades == 1                                   # never bought NEW, never bought X
    assert ps.fits({'ageH': None, 'liq': 5e5}, {'age': 1}) is False and ps.fits({'ageH': 2, 'liq': 5e5}, {'age': 1, 'pool': 100})
    res = ps.run(paths_, NOW, n=40, hours=6, seed=3, rounds=rounds)
    assert res and all(r['trades'] >= 1 for r in res) and all('age' in r['cfg'] and 'edge' not in r['cfg'] for r in res)   # record too short for an edge table


def _proof_world(hours=34):
    """A board that offers one OLD coin in a DEEP pool (drifts up) and one fresh thin coin (bleeds) at every round."""
    now, paths, rounds = 1_000_000.0, {'OLD': [], 'NEW': []}, []
    for i in range(int(hours * 12) + 1):
        t = now - hours * 3600 + i * 300
        paths['OLD'].append([t, 1.0 * (1.0006 ** i)]); paths['NEW'].append([t, 1.0 * (0.997 ** i)])
        if i % 3 == 0:
            rounds.append({'at': t, 'picks': [{'mint': 'NEW', 'score': 90, 'ageH': 0.5, 'liq': 12000}, {'mint': 'OLD', 'score': 50, 'ageH': 30, 'liq': 120000}]})
    return paths, rounds, now


def test_joint_plays_one_whole_config_and_counts_windows():
    paths, rounds, now = _proof_world()
    deep = ps.joint(ps.prep(paths, rounds, now), {'clock': 15, **ps.SNIPER, 'edge': 0})
    anyc = ps.joint(ps.prep(paths, rounds, now), {'clock': 15, **ps.SNIPER, 'edge': 0, 'age': 0, 'pool': 0})
    assert deep['windows'] == len(ps.TUNE_OFFS) and deep['windowsUp'] == deep['windows'] and deep['medPct'] > 0
    assert anyc['medPct'] < deep['medPct']          # letting the fresh thin coin in costs money
    assert ps.joint([], ps.SNIPER) is None


def test_proven_is_checked_on_other_windows_and_never_claims_a_losing_setup():
    paths, rounds, now = _proof_world()
    p = ps.proven(paths, rounds, now, 15)
    assert p['key'] == 'sniper' and p['profitable'] and p['medPct'] > 0 and (float(p['cfg']['pool']) >= 25 or float(p['cfg']['age']) >= 1)
    assert p['windows'] == len(ps.CHECK_OFFS) and 'clock' not in p['cfg']
    bleed = {m: [[t, 1.0 * (0.997 ** i)] for i, (t, _) in enumerate(pts)] for m, pts in paths.items()}   # every coin loses
    q = ps.proven(bleed, rounds, now, 15)
    assert q is None or q['profitable'] is False
    assert ps.proven({}, [], now, 15) is None
