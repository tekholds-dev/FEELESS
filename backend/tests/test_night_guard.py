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


def test_the_morning_report_is_plain_numbers_from_real_exits():
    ex = [{'at': 10, 'pct': 12, 'sym': 'A'}, {'at': 20, 'pct': -30, 'sym': 'B', 'rule': 'R5'}, {'at': 30, 'pct': -5, 'sym': 'C', 'rule': 'R5'}]
    t = ng.morning(ex, {'tripAts': [50], 'why': '🧊 streak'}, 0, 100)
    assert '3 real exits, 1 won (33%)' in t and 'worst $B -30%' in t and 'R5 (2×)' in t and 'Night guard paused buying 1×' in t
    assert ng.morning([], {}, 0, 100) is None


def test_night_shift_tightens_only_between_midnight_and_nine():
    day = {'agentSizePct': 0, 'agentMinAgeH': 0.25, 'chartWait': False, 'agentValve': True}
    assert ng.night_cfg(day, 14) == day                                         # regular programming by day
    n = ng.night_cfg(day, 3)
    assert n['agentSizePct'] == 15 and n['agentMinAgeH'] == 0.5 and n['chartWait'] is True and n['agentValve'] is False and n['nightShift']
    assert ng.night_cfg({**day, 'agentSizePct': 10}, 3)['agentSizePct'] == 10    # a smaller owner ceiling stays
    assert ng.night_cfg(day, 3, on=False) == day and ng.is_night(0) and not ng.is_night(9)
    st, v = ng.step({}, 10.0, [], 0, night=True)
    st, v = ng.step(st, 9.1, [], 60, night=True)                                # −9%: trips at night (8%), not by day (12%)
    assert v['paused'] and v['kind'] == 'draw'
    assert ng.step({}, 10, [{'at': 1, 'pct': -50}], 10, night=True)[1]['kind'] == 'rug'   # one rug-level exit at night
