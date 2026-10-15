import ai_snapshot as sn


def test_snapshot_is_the_same_bars_as_one_line_and_never_invents_a_bar():
    rows = [[i, 1.0 + i * 0.01, 1.02 + i * 0.01, 0.99 + i * 0.01, 1.0 + i * 0.01, 100.0] for i in range(10)]
    s = sn.snapshot({'src': 'candles', 'rows': rows}, entry=1.0)
    assert s['src'] == 'candles' and s['pts'][0] == 0.0 and s['pts'][-1] == 9.0
    assert 'vs entry' in s['line'] and 'range high' in s['line'] and 'higher lows' in s['line'] and 'green of the last 5' in s['line']
    t = sn.snapshot({'src': 'tape', 'rows': [[i, 0, 0, 0, 2.0 + i, None] for i in range(4)]})
    assert t['src'] == 'tape' and 'closes only' in t['line'] and 'no highs / lows / volume' in t['line'] and 'range high' not in t['line']
    assert sn.snapshot({'src': 'candles', 'rows': rows[:2]}) is None and sn.snapshot(None) is None
    assert len(sn.snapshot({'src': 'candles', 'rows': rows * 5})['pts']) == sn.PTS
