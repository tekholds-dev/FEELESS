"""⚡ The chart drives the timing: a material live change wakes Reaper / Trigger without waiting for the clock — the exact failure the owner
showed (a run → local top → a fast red reversal) and a WAIT candidate breaking out."""
import market_wake as mw
import office as of
import chart_intel as ci


def _bars(closes):
    out, prev = [], closes[0]
    for i, c in enumerate(closes):
        out.append([i * 60, prev, max(prev, c), min(prev, c), c, 1000.0]); prev = c
    return out


def _stair(n=24):
    out, px = [], 1.0
    for i in range(n):
        px *= 0.996 if i % 3 == 2 else 1.012
        out.append(px)
    return out


def test_profitable_new_high_holds_then_a_sharp_drop_wakes_reaper_and_it_exits():
    closes = _stair()
    up = ci.read(_bars(closes))
    th = ci.thesis(up, 0, {'liq': 60_000, 'ageH': 8})
    top = closes[-1]
    leg = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}}
    row = {'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': top, 'why': {'lean': 2.0, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''], 'nums': {'d5': 4, 'buy': 60, 'liq': 60_000}, 'vitals': {'safe': True, 'rug': 5}}
    cfg = {'agentTakePct': 50, 'agentScalp': False}
    pos, rep, _ = of.reap([leg], [row], {'PA': top}, cfg, None, 120, charts={'A': up}, theses={'A': th})
    assert rep[0]['action'] is None and rep[0]['run'] in ('RUNNING', 'ACCELERATING')            # profitable, at its high: HOLD / PROTECT
    assert pos['A']['decPx'] == top
    drop = th['invalidation'] * 0.97                                                                # the next live price: a sharp red candle through the line
    why = mw.position_wake(pos['A'], drop)
    assert any('since the last decision' in w for w in why) and any('below' in w for w in why)       # the fast guard sees it NOW — no rediscovery, no 60s wait
    dn = ci.read(_bars(closes + [drop]))                                                            # the refreshed live chart shows the same candle
    _, rep2, _ = of.reap([leg], [row], {'PA': drop}, cfg, pos, 130, charts={'A': dn}, theses={'A': th})
    assert rep2[0]['action'] is None and 'runway' in rep2[0]['evidence']                           # 🛫 still green, 10s in: not banked on its runway
    _, rep3, _ = of.reap([leg], [row], {'PA': drop}, cfg, pos, 120 + of.RUNWAY_SEC + 1, charts={'A': dn}, theses={'A': th})
    assert rep3[0]['action'] == 'pull' and rep3[0]['run'] == 'BREAKING DOWN' and rep3[0]['rule'] in ('R7b breakdown', 'R5t thesis invalidated')


def test_nothing_material_is_not_a_wake():
    p = {'entry': 1.0, 'peak': 5.0, 'decPx': 1.04}
    assert mw.position_wake(p, 1.045) == []
    assert mw.position_wake({}, 1.0) == []


def test_wait_candidate_breaking_out_wakes_trigger():
    c = {'px': 1.00, 'high': 1.02}
    assert mw.candidate_wake(c, 1.01) == []
    assert 'live breakout above its local high' in mw.candidate_wake(c, 1.026)
    assert mw.candidate_wake(c, 0.96)                                                             # a material fall wakes it too


def test_run_states_and_phase_and_freshness():
    assert mw.run_state(10, 12, 'ACCELERATING') == 'ACCELERATING'
    assert mw.run_state(10, 10.5) == 'RUNNING'
    assert mw.run_state(4, 12) == 'REVERSING'
    assert mw.run_state(-1, 0) == 'STALLING'
    assert mw.run_state(5, 6, broke=True) == 'BREAKING DOWN'
    assert mw.market_phase({'state': 'CONFIRMED BREAKOUT'}) == 'BREAKOUT' and mw.market_phase({'state': 'COMPRESSION'}) == 'DISCOVERY'
    assert mw.market_phase({'state': 'UPTREND'}, {'phase': 'DISTRIBUTION'}) == 'DISTRIBUTION'
    a = mw.ages(100, price_at=95, candle_at=40, decision_at=99)
    assert a['price'] == 5 and a['candle'] == 60 and a['tape'] is None and a['stale'] is False
    assert mw.ages(100, price_at=50)['stale'] is True
    assert mw.due(0, 10, 6) and not mw.due(8, 10, 6)
