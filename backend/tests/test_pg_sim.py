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
