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
    assert all(-1.5 < r['pct'] for r in a if r['cfg']['minDrop'] > 0)              # rotate-only-losers: just the entry cost
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
