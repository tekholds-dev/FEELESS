import chart_intel as ci
import office_edge as oe


def _bars(seq):
    # (high, low, close) per minute
    return [[i * 60, c, h, l, c, 100] for i, (h, l, c) in enumerate(seq)]


def test_bullish_gap_is_support_until_traded_through():
    rows = _bars([(1.0, 0.95, 0.98), (1.06, 0.97, 1.01), (1.10, 1.05, 1.08), (1.12, 1.06, 1.07)])   # bar 2 low 1.05 > bar 0 high 1.00 → gap 1.00–1.05
    g = ci.fvg(rows)
    assert g and abs(g['bot'] - 1.0) < 1e-9 and abs(g['top'] - 1.05) < 1e-9 and g['open'] == 1
    assert ci.fvg_word(g) == 'on' and 0 < g['dist'] < 5
    gone = rows + [[300, 1.0, 1.01, 0.98, 0.99, 100]]   # a later low under the gap bottom
    assert ci.fvg(gone) is None


def test_fvg_support_is_a_setup_with_a_higher_low():
    assert 'fvg' in oe.setups_of({'chart': {'fvgDist': 2.0, 'hl': 1, 'll': 0}})
    assert 'fvg' not in oe.setups_of({'chart': {'fvgDist': 2.0, 'hl': 1, 'll': 1}})   # a lower low = no support
    assert 'fvg' not in oe.setups_of({'chart': {'fvg5Dist': 12.0, 'hl': 2, 'll': 0}})   # too far above it
