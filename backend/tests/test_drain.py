"""🩸 Drain vitals: exit liquidity, holders leaving, pool draining, the tape, bots → one read; Reaper sells only on a MOVING drain."""
import drain as dr


def test_exit_liquidity_is_the_top10_bag_over_the_pool():
    assert dr.exit_liq(68, 55_000, 18_800) == 1.99
    assert dr.exit_liq(None, 55_000, 18_800) is None and dr.exit_liq(20, 0, 1) is None   # unknown is never zero


def test_a_heavy_bag_alone_is_a_watch_never_an_exit():
    d = dr.read({'top10': 90, 'mcap': 100_000}, {'liq': 20_000})       # 4.5× the pool, nothing moving
    assert d['state'] == 'WATCH' and dr.exit_why(d) is None


def test_holders_leaving_and_the_pool_draining_under_a_heavy_bag_sell():
    d = dr.read({'top10': 60, 'mcap': 100_000}, {'liq': 20_000, 'holdD': -6, 'liqD': -30}, flow={'state': 'SELLERS'})
    assert d['state'] == 'DRAIN' and d['score'] >= 60
    w = dr.exit_why(d)
    assert w.startswith('drain:') and 'pool' in w


def test_two_moving_parts_sell_even_without_a_known_bag():
    d = dr.read({}, {'holdD': -6, 'liqD': -30})
    assert d['xl'] is None and dr.exit_why(d)
    assert dr.exit_why(dr.read({}, {'holdD': -6})) is None                  # one moving part on its own: not a drain


def test_a_top_holder_dumping_is_a_moving_part():
    d = dr.read({'top10': 40, 'mcap': 80_000}, {'liq': 20_000}, dump='top-10 wallet sold $900')
    assert dr.exit_why(d)


def test_odds_name_the_bucket_that_says_the_most_with_its_n():
    done = [{'at': 1, 'f': ['age:<15m', 'cap:<30K'], 'low': -80, 'end': -70} for _ in range(45)] + \
           [{'at': 1, 'f': ['age:12h+', 'cap:<30K'], 'low': -3, 'end': 1} for _ in range(45)]
    t = dr.odds_table(done)
    assert t['_base'][1] == 50 and t['age:<15m'] == [45, 100, -70.0]
    o = dr.odds(['age:<15m', 'cap:<30K'], t)
    assert o['feature'] == 'age:<15m' and o['rug'] == 100 and '45 coins' in o['why']
    assert dr.odds(['age:12h+'], t)['rug'] == 0
    assert dr.odds(['nothing:here'], t) is None
