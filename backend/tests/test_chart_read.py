import chart_read as cr
import pick_edge as pe


def _pts(prices, t0=0.0, step=300.0):
    return [(t0 + i * step, p) for i, p in enumerate(prices)]


def test_too_short_a_chart_is_not_read_and_candles_only_use_readings_before_t():
    assert cr.read(_pts([1, 1.1, 1.2]), 900.0) is None and cr.keys(_pts([1, 1.1]), 600.0) == {'cBars': 0}
    pts = _pts([1.0] * 30 + [50.0] * 5)                       # the spike is AFTER t → it must not be seen
    r = cr.read(pts, 29 * 300.0)
    assert r and r['pull'] == 0.0 and r['structure'] == 'range'


def test_structure_range_place_and_pullback():
    up = cr.read(_pts([1 + 0.02 * i for i in range(36)]), 35 * 300.0)
    assert up['structure'] == 'up' and up['pos'] > 0.95 and up['pull'] < 1 and up['bars'] >= 10
    down = cr.read(_pts([2 - 0.02 * i for i in range(36)]), 35 * 300.0)
    assert down['structure'] == 'down' and down['pos'] < 0.05
    pulled = cr.read(_pts([1 + 0.03 * i for i in range(30)] + [1.87 * 0.9] * 6), 35 * 300.0)
    assert 8 < pulled['pull'] < 12


def test_fair_value_gap_states_and_a_reclaimed_sweep():
    base = [1.0] * 9 + [1.0, 1.0, 1.0] + [1.3, 1.3, 1.3] + [1.6, 1.6, 1.6]          # candle highs 1.0 → lows 1.6: an open gap between
    assert cr.read(_pts(base + [1.65, 1.7, 1.75, 1.8, 1.85, 1.9]), (len(base) + 5) * 300.0)['fvg'] == 'above'
    assert cr.read(_pts(base + [1.5] * 3), (len(base) + 2) * 300.0)['fvg'] == 'in'
    assert cr.read(_pts(base + [0.8] * 3 + [0.9] * 3), (len(base) + 5) * 300.0)['fvg'] == 'lost'
    sw = [1.0, 1.02, 1.0] * 5 + [0.9, 0.95, 1.05]                                    # took the lows, closed back above
    assert cr.read(_pts(sw), (len(sw) - 1) * 300.0)['sweep'] is True


def test_the_pick_record_learns_the_chart_fields():
    assert {'cread', 'cstruct', 'cpos', 'cpull'} <= set(pe.FEATURES)
    f = {k: v[2] for k, v in pe.FEATURES.items()}
    assert f['cread']({'cBars': 0}) == 0 and f['cread']({'cBars': 14}) == 1 and f['cread']({}) is None
    assert f['cstruct']({'cStruct': 'up'}) == 2 and f['cstruct']({}) is None
    assert f['cpos']({'cPos': 0.9}) == 2 and f['cpull']({'cPull': 10}) == 1 and f['cpull']({}) is None


def test_market_candles_read_like_the_boards_own_record():
    t0 = 1_000_000.0
    rows = [[t0 + i * 900, 1 + i * 0.1, 1.15 + i * 0.1, 0.98 + i * 0.1, 1.1 + i * 0.1, 5000] for i in range(8)]   # 8 rising 15-min candles
    pts = cr.points_from_candles(rows + [['bad'], [t0, 0, 0, 0, 0]])
    assert len(pts) == 32
    k = cr.keys(pts, t0 + 8 * 900)
    assert k['cBars'] >= 5 and k['cStruct'] == 'up'
    bars = cr.candles(pts, t0 + 8 * 900)
    assert abs(bars[-1][0] - 1.7) < 1e-9 and abs(bars[-1][1] - 1.85) < 1e-9 and abs(bars[-1][3] - 1.8) < 1e-9   # open · high · close survive
    assert cr.why_not({'cBars': 0}) == 'chart too short to read' and cr.why_not({'cBars': 9, 'cStruct': 'down'}) == 'trending down'
    assert cr.why_not({}) == 'chart not read yet' and cr.why_not(k) == ''


def test_a_one_candle_crash_in_the_last_hour_is_read_as_wild():
    t0 = 1_000_000.0
    calm = [[t0 + i * 900, 1.0, 1.05, 0.97, 1.02, 1] for i in range(8)]
    crash = calm[:6] + [[t0 + 6 * 900, 1.0, 1.1, 0.5, 0.8, 1], [t0 + 7 * 900, 0.8, 0.9, 0.78, 0.88, 1]]
    assert cr.keys(cr.points_from_candles(calm), t0 + 8 * 900)['cWild'] < 10
    assert cr.keys(cr.points_from_candles(crash), t0 + 8 * 900)['cWild'] > 50          # 1.10 → 0.50 inside one candle
