"""💀 Dead coins never take a seat and a held one gives its seat away; majors / xStocks are never a trench seat; the brain reads the bad guys' footprint."""
import agents
import fuse
import office
import opportunity as opp
import trench_brain as tb


def _row(v5, pace=1.0, **kw):
    return {'mint': 'M', 'px': 1.0, 'nums': {'v5': v5, 'pace': pace, 'liq': 50_000, 'd5': 0}, 'vitals': {'safe': True, 'mcap': 100_000, 'liq': 50_000, 'ageH': 1.0}, **kw}


def test_dead_now_reads_the_last_5_minutes():
    assert opp.dead_now(_row(50)) .startswith('dead')
    assert opp.dead_now(_row(1000, pace=0.1)).startswith('dead')        # the hour's volume is gone
    assert opp.dead_now(_row(1000, pace=0.8)) is None
    assert opp.dead_now(_row(5000, pace=0.1)) is None                   # still real money moving
    assert opp.dead_now({'nums': {}}) is None                           # no reading = not judged


def test_a_dead_coin_is_a_hard_no():
    assert opp.hard_fail(_row(10)).startswith('dead')
    assert opp.hard_fail(_row(5000)) is None


def test_majors_and_stocks_are_never_in_the_agents_lane():
    stock = next(iter(fuse.STOCKS))
    r = {'mint': stock, 'mcap': 100_000, 'vol1h': 50_000, 'ageH': 1.0}
    assert agents.in_lane(r) is False
    assert agents.in_lane({**r, 'mint': 'NEW'}) is True


def test_tally_keeps_5_min_dollars_and_none_when_missing():
    _s, nums = agents.tally({}, [{'mint': 'A', 'price': 1, 'vol5m': 120, 'vol1h': 6000}, {'mint': 'B', 'price': 1, 'vol1h': 6000}], 100.0)
    assert nums['A']['v5'] == 120 and nums['B']['v5'] is None


def test_dead_exit_only_swaps_and_skips_the_flat_churn_rule():
    rep = [{'mint': 'M', 'pair': 'P', 'symbol': 'X', 'action': 'pull', 'rule': 'R11 dead coin', 'evidence': 'dead', 'pct': -0.5}]
    out = office.merge_reaper([], [dict(r) for r in rep], buys_left=1)
    assert out and out[0]['reaper'] == 'R11 dead coin'                  # flat, but dead: it goes
    r2 = [dict(r) for r in rep]
    assert office.merge_reaper([], r2, buys_left=0) == [] and r2[0].get('deferred')   # nothing ready: the seat stays full
    flat = [{**rep[0], 'rule': 'R9 windows used'}]
    assert office.merge_reaper([], flat, buys_left=1) == []             # a merely flat coin still keeps its seat


def test_brain_learns_the_footprint():
    f = tb.feats({'bundledN': 4, 'snipersN': 0, 'insiders': 10, 'dev': 0.1, 'vol5m': 100})
    assert {'bund:3+', 'snipe:0', 'ins:8+', 'dev:out', 'live:dead'} <= set(f)


def test_a_quiet_coin_on_a_base_is_not_dead():
    import office as of
    assert of.base_of({'f': {'germ': {'dist': 9, 'lost': False}}}).startswith('on its 1m germ floor')
    assert of.base_of({'f': {'germ5': {'dist': 4}}}).startswith('on its 5m germ floor')
    assert of.base_of({'f': {'hl': 2, 'll': 0}}) == '2 higher lows, no lower low'
    assert of.base_of({'f': {'germ': {'dist': 9, 'lost': True}}}) is None
    assert of.base_of({'f': {'germ': {'dist': 40}, 'hl': 1}}) is None


def test_breakout_window_never_holds_back_a_stop_or_a_rug_exit():
    import office as of
    for hard in ('R1', 'R2', 'R3', 'R4', 'R4r', 'R4d', 'R5', 'R5x', 'R5c', 'R9c', 'R6', 'R7'):
        assert hard not in of.BREAKOUT_RULES
    assert of.BREAKOUT_SEC == 900 and 'R11' in of.BREAKOUT_RULES


def test_a_coin_left_at_a_loss_sits_out_an_hour():
    import arena_prime as ap
    c = {'agentOut': {'M': {'at': 0, 'loss': True}, 'N': {'at': 0}}}
    out = ap.agent_out(c, 1200)
    assert 'M' in out and 'N' not in out
    assert 'M' not in ap.agent_out(c, 3700)


def test_time_rules_never_sell_a_base():
    import office as of
    assert set(of.BASE_TIME_RULES) <= set(of.BREAKOUT_RULES) and 'R9' in of.BASE_TIME_RULES and 'R5' not in of.BASE_TIME_RULES


def test_your_hold_hint_never_blocks_a_stop_or_a_rug():
    import office as of
    for hard in ('R1', 'R4r', 'R5', 'R5x', 'R6', 'R5m', 'R6m'):
        assert hard in of.HINT_HARD
    assert 'R9' not in of.HINT_HARD and of.HINT_SEC == 1800
