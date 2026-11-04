"""Chart candles are sanitized and never skip a bar."""
import time

import pytest

cs = pytest.importorskip('candles_service')


def test_no_skipped_candles_and_bad_bars_are_cleaned():
    step = 60
    t0 = (int(time.time()) // step - 10) * step
    raw = [
        [t0 + 3 * step + 7, 2, 2.5, 1.9, 2.2, 5],   # off-grid -> snapped to its bucket
        [t0, 1, 1.2, 0.9, 1.1, 10],
        [t0 + 3 * step, 2.1, 2.0, 2.4, 2.3, 1],     # duplicate bucket, high/low swapped
        [t0 + 5 * step, float('nan'), 1, 1, 1, 0],  # non-finite -> dropped
        [t0 + 6 * step, 0, 0, 0, 0, 0],             # zero price -> dropped
    ]
    out = cs._fill_gaps(raw, step)
    times = [c[0] for c in out]
    assert times == list(range(t0, times[-1] + step, step))  # every bucket, in order, no gaps
    assert times[-1] >= (int(time.time()) // step - 1) * step  # runs up to now
    bar = next(c for c in out if c[0] == t0 + 3 * step)
    assert bar[1] == 1.1 and bar[4] == 2.2 and bar[2] == 2.5 and bar[3] == 1.1 and bar[5] == 6   # opens at the prior close
    for a_, b_ in zip(out, out[1:]):
        assert b_[1] == a_[4]   # continuous: every candle opens where the last closed (no floating dashes)
    for c in out:
        assert c[2] >= max(c[1], c[4]) and c[3] <= min(c[1], c[4]) and c[3] > 0
    gap = next(c for c in out if c[0] == t0 + step)
    assert gap[1:5] == [1.1, 1.1, 1.1, 1.1] and gap[5] == 0


def test_a_chart_gets_the_sources_own_candles_never_filled_forced_or_overwritten(monkeypatch):
    step = 60; t0 = 1_700_000_040
    hist = [[t0, 1.0, 1.2, 0.9, 1.1, 10.0], [t0 + 5 * step, 3.0, 3.5, 0.5, 3.2, 20.0]]   # a 4 minute gap, a big wick, and an open far from the last close
    cs._live_hist[('solana', 'POOL', '1m')] = (time.time(), hist, 'Jupiter')
    monkeypatch.setattr(cs, '_load', lambda: {cs._pair_key('solana', 'POOL'): [{'t': t0 * 1000, 'p': 9.0}]})
    out = cs._true_view('solana', 'POOL', '1m', {'interval': '1m', 'candles': [['filled']]})
    assert out['candles'] == hist and out['provider'] == 'Jupiter' and out['sampled'] is False   # every number exactly as the source sent it
    cs._live_hist.pop(('solana', 'POOL', '1m'))
    monkeypatch.setattr(cs, '_load', lambda: {})
    none = cs._true_view('solana', 'POOL', '1m', {'interval': '1m'})
    assert none['candles'] == [] and none['sampled'] is True and 'not trades' in none['source']
