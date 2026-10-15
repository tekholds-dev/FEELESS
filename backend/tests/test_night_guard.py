import night_guard as ng


def test_a_drawdown_pauses_new_buys_then_the_window_restarts():
    st, v = ng.step({}, 10.0, [], 0)
    assert v['paused'] is False
    st, v = ng.step(st, 8.7, [], 600)                      # −13% under the 6h high
    assert v['paused'] and v['kind'] == 'draw' and v.get('new')
    st, v = ng.step(st, 8.0, [], 1200)
    assert v['paused'] and not v.get('new')                # still paused, not tripped again
    st, v = ng.step(st, 8.0, [], 600 + ng.DRAW_PAUSE + 1)  # pause over: the high restarts from here
    assert v['paused'] is False and v['drawPct'] == 0


def test_a_losing_streak_and_a_rug_burst_pause_too():
    ex = [{'at': i, 'pct': -5} for i in range(1, 5)]
    st, v = ng.step({}, 10, ex, 10)
    assert v['kind'] == 'streak'
    st, v = ng.step({}, 10, [{'at': 1, 'pct': -5}, {'at': 2, 'pct': 9}, {'at': 3, 'pct': -2}], 10)
    assert v['paused'] is False                             # a win in the run: no streak
    st, v = ng.step({}, 10, [{'at': 100, 'pct': -60}, {'at': 200, 'pct': 4}, {'at': 300, 'pct': -70}], 400)
    assert v['kind'] == 'rug'
    assert ng.view(st, v, 400)['paused'] is True
