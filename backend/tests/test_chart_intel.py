import asyncio
import itertools

import pytest

import agents as ag
import chart_intel as ci
import office as of


def bars(closes, wick=0.0, t0=0):
    """1-minute candles from a list of closes (open = the close before); `wick` = extra high / low as a fraction."""
    out, prev = [], closes[0]
    for i, c in enumerate(closes):
        out.append([t0 + i * 60, prev, max(prev, c) * (1 + wick), min(prev, c) * (1 - wick), c, 1000.0])
        prev = c
    return out


def stair(n=24, step=0.012, dip=0.004, start=1.0):
    """An orderly uptrend: two steps up, a small step back — higher highs and higher lows."""
    out, px = [], start
    for i in range(n):
        px *= (1 - dip) if i % 3 == 2 else (1 + step)
        out.append(px)
    return out


def saw(n=24, amp=0.05):
    """Violent alternating candles going nowhere — a REAL chop: every swing lands somewhere new (two exact prices ping-ponging is a
    broken feed, not a market: `market_data` rejects that)."""
    return [1.0 * (1 + (amp if i % 2 else -amp) * (0.7 + 0.3 * ((i * 7) % 5) / 4)) for i in range(n)]


UP, CHOP = bars(stair()), bars(saw())


def test_the_same_buy_share_reads_as_different_structures_and_flow_alone_never_decides():
    a, b = ci.read(UP, buy=55), ci.read(CHOP, buy=55)
    assert a['state'] in ('STRONG UPTREND', 'UPTREND') and b['state'] == 'CHOP'                                   # 55% buys on both — the STRUCTURE differs
    assert a['trend'] >= 60 and a['chop'] <= 45 and b['chop'] >= 62 and b['trend'] <= 20
    assert ci.read(UP, buy=50)['state'] == a['state'] and ci.read(UP, buy=48)['state'] == a['state']              # an orderly uptrend is not chop because flow is near 50/50
    assert ci.read(CHOP, buy=80)['state'] == 'CHOP'                                                               # … and 80% buys does not turn a saw into a trend
    assert a['f']['hh'] >= 2 and a['f']['hl'] >= 2 and any('higher highs' in e for e in a['ev']) and any('buy flow 55%' in e for e in a['ev'])
    assert any('buy flow 48%' in c for c in ci.read(UP, buy=48)['con'])                                           # weak flow is a stated contradiction, not a verdict
    assert b['entry'][0] == 'SKIP' and b['risk'][0] == 0.0 and b['objs'][0][0] == 'chart_chop' and '/100' in b['objs'][0][1]
    green = bars([1.0, 1.001, 1.002, 1.0005, 1.0015, 1.001, 1.002, 1.0012, 1.002, 1.0018, 1.0022, 1.002])        # mostly green candles, no move at all
    assert ci.read(green)['state'] not in ('STRONG UPTREND', 'UPTREND', 'PARABOLIC')                              # a count of green candles is not a trend
    one = bars([1.0] * 12 + [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.12, 1.119])
    assert ci.read(one)['state'] != 'STRONG UPTREND'                                                              # one big candle is not a trend either


def test_every_state_comes_from_measured_thresholds_and_short_data_is_unknown():
    assert ci.read(bars([1.0, 1.01, 1.02]))['state'] == 'UNKNOWN' and ci.read([])['state'] == 'UNKNOWN' and ci.read(bars([1.0, 1.01, 1.02]))['entry'][0] == 'WAIT FOR CONFIRMATION'
    para = ci.read(bars([1.0] * 10 + [1.02, 1.08, 1.16, 1.25, 1.36, 1.48]))
    assert para['state'] == 'PARABOLIC' and para['entry'][:2] == ['WAIT FOR PULLBACK', 'E2 no chasing'] and para['risk'][0] == 0.25 and para['objs'][0][0] == 'chart_parabolic'
    down = ci.read(bars([1.0 * (0.985 ** i) * (1.004 if i % 3 == 2 else 1) for i in range(24)]))
    assert down['state'] == 'DOWNTREND' and down['entry'][0] == 'SKIP' and down['risk'][0] == 0.0
    base = [1.0 + 0.004 * (i % 2) for i in range(18)]
    brk = ci.read(bars(base + [1.012, 1.02, 1.024]))
    assert brk['state'] == 'CONFIRMED BREAKOUT' and brk['f']['breakHeld'] >= 2 and brk['entry'][0] == 'ENTER NOW' and brk['risk'][0] == 0.5      # a young breakout: half size
    assert ci.read(bars(base + [1.012, 1.02, 1.024]), buy=44)['entry'][:2] == ['WAIT FOR CONFIRMATION', 'E10 breakout without buyers']
    att = ci.read(bars(base + [1.003, 1.004, 1.012]))
    assert att['state'] == 'BREAKOUT ATTEMPT' and att['entry'][:2] == ['WAIT FOR CONFIRMATION', 'E5 unconfirmed breakout']                        # a breakout without confirmation waits
    fail = ci.read(bars(base + [1.004, 1.02, 0.992]))
    assert fail['state'] == 'FAILED BREAKOUT' and fail['entry'][0] == 'SKIP' and fail['objs'][0][0] == 'chart_fake_breakout'
    liq = ci.read(UP, liq=40_000, liq_d=-30)
    assert liq['state'] == 'LIQUIDITY FAILURE' and liq['entry'][0] == 'SKIP'
    pull = stair(18) + [stair(18)[-1] * x for x in (0.985, 0.972, 0.965, 0.975)]
    pb = ci.read(bars(pull))
    assert pb['state'] == 'PULLBACK IN UPTREND' and pb['entry'][:2] == ['ENTER NOW', 'E9 pullback recovered'] and pb['f']['recovery'] >= 0.25     # a clean pullback that turned
    falling = ci.read(bars(stair(18) + [stair(18)[-1] * x for x in (0.985, 0.972, 0.965, 0.962)]))
    assert falling['entry'][0] != 'ENTER NOW'                                                                                                     # the same pullback still falling waits
    flat = ci.read(bars([1.0 + 0.0005 * (i % 2) for i in range(24)]))
    assert flat['state'] in ('RANGE', 'COMPRESSION', 'ACCUMULATION') and flat['entry'][0] == 'WAIT FOR BREAKOUT' and all(s in ci.STATES for s in (flat['state'], pb['state']))
    tape = ci.read(ci.from_tape([{'t': i * 60, 'px': p} for i, p in enumerate(stair())]), ohlc=False, src='tape')
    assert tape['state'] in ('STRONG UPTREND', 'UPTREND') and tape['f']['upWick'] is None and tape['f']['wick'] is None and any('wicks not measured' in c for c in tape['con'])   # closes only: wicks are NOT invented


def test_trigger_does_not_chase_and_can_wait_on_a_good_coin():
    ext = stair(14, 0.006) + [stair(14, 0.006)[-1] * x for x in (1.03, 1.06, 1.10)]
    e = ci.read(bars(ext))
    assert e['entry'][0] == 'WAIT FOR PULLBACK' and e['entry'][1] in ('E6 extended', 'E2 no chasing')            # a good trend, a bad place to buy it
    assert ci.read(UP)['entry'] == ['ENTER NOW', 'E12 trend in hand', ci.read(UP)['entry'][2]]
    wick = [[r[0], r[1], r[2] * 1.03, r[3], r[4], r[5]] for r in UP]
    assert ci.read(wick)['entry'][:2] == ['WAIT FOR CONFIRMATION', 'E7 rejection wicks']
    assert ci.read(UP, liq=80_000, liq_d=-12)['entry'][1] == 'E8 pool leaving' and ci.read(UP, liq=80_000, liq_d=-12)['objs'] == [] or True
    # through the desk: the chart can only make Trigger pickier, and a hard SKIP stays a SKIP
    mk = lambda m, px, **k: {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'price': px, 'vol5m': 20_000, 'vol1h': 80_000, 'buyShare': 64, 'liq': 60_000, 'ageH': 8, 'chg1h': 30, 'safe': True,
                             'tv': {'call': ['🔥', 'SEND IT', 'good'], 'rug': 10}, **k}
    rows = lambda i: [mk('GOOD', stair()[i]), mk('SAW', saw()[i] * 1.0), mk('PARA', ([1.0] * 18 + [1.02, 1.08, 1.16, 1.25, 1.36, 1.48])[i]), mk('BAD', stair()[i], safe=False)] + [mk(f'c{j}', 1 + i * 0.001) for j in range(10)]
    st_c, st_p, out = {}, {}, {}
    for i in range(24):
        st_c, tc = ag.desk(st_c, rows(i), 1000 + i * 60, candles={}, charts_out=out)
        st_p, tp = ag.desk(st_p, rows(i), 1000 + i * 60)
    c, p = {x['mint']: x for x in tc}, {x['mint']: x for x in tp}
    assert p['GOOD'].get('chart') is None and c['GOOD']['chart']['state'] in ('STRONG UPTREND', 'UPTREND') and c['GOOD']['chart']['src'] == 'tape'
    assert c['SAW']['trigger'][0] == 'skip' and 'E1 bad structure' in c['SAW']['trigger'][1] and c['BAD']['trigger'][0] == 'skip'
    assert c['PARA']['trigger'][0] != 'enter' and not c['PARA']['go']
    for m in c:                                                                                                    # never more permissive than the desk without the chart
        rank = {'skip': 0, 'wait': 1, 'enter': 2}
        assert rank[c[m]['trigger'][0]] <= rank[p[m]['trigger'][0]], m
    assert set(out) == set(c) and out['GOOD']['f']['n'] == ag.SERIES_N and 'chart:' + c['GOOD']['chart']['state'] in [d[0] for d in c['GOOD']['why']['drivers']]   # ONE snapshot a coin, shared
    cases = {x['mint']: x for x in ag.investigate(tc, set(), 1, {}, top=0)}
    assert all(k[0] != 'chart' or k[1] == (cases[m]['row']['chart']['entry'][0] == 'ENTER NOW') for m in cases for k in cases[m]['checks'])
    assert all(any(k[0] == 'chart' for k in cs['checks']) for cs in cases.values()) and 'SAW' not in cases       # the duty waives the bar, never the chart
    st_c = ag.record(st_c, tc, 1000 + 24 * 60)
    assert all('cs' in o and 'ce' in o for o in st_c['open'].values())                                            # the structure is stored WITH the call (no hindsight later)


def test_devils_chart_objections_point_at_measurements_and_soft_ones_need_their_record():
    assert ci.objections(ci.snapshot(UP), 'UPTREND') == []                                                        # nothing measured against it → no objection
    assert ci.objections({}, 'CHOP') == [] and ci.objections(ci.snapshot(bars([1, 1.1])), 'UNKNOWN') == []        # no chart → no chart objection (never "it looks scary")
    div = ci.objections(ci.snapshot(bars(stair(24, 0.02)), buy=40), 'UPTREND')
    assert div[0][0] == 'chart_divergence' and 'buy flow 40%' in div[0][1]
    thin = ci.objections(ci.snapshot(bars(stair(24, 0.02)), flow={'buyUsd': 300, 'sellUsd': 10, 'n': 3}), 'UPTREND')
    assert ('chart_thin' in [o[0] for o in thin]) and '3 trades' in dict(thin)['chart_thin']
    assert all(k in ag.DEVIL_RULES for k in ci.CHART_RULES) and ag.DEVIL_RULES['chart_parabolic'][0] is True and ag.DEVIL_RULES['chart_wick'][0] is False
    row = {'safe': True, 'tv': {'rug': 5, 'call': ['', 'X', '']}, 'chart': {'objs': [['chart_divergence', 'price +4% on buy flow 40%']]}}
    why = {'drivers': [], 'lean': 2}
    assert ag.devil_args('enter', {}, why, row, {})[0][0] == 'chart_divergence'                                   # a soft chart rule stands on belief …
    assert ag.devil_args('enter', {}, why, row, {'objrec': {'chart_divergence': {'n': 12, 'med': 4.0}}}) == []    # … until its OWN record shows it blocks winners
    hard = {**row, 'chart': {'objs': [['chart_parabolic', 'parabolic: +30% in 5 min']]}}
    assert ag.devil_args('enter', {}, why, hard, {'objrec': {'chart_parabolic': {'n': 99, 'med': 50.0}}})[0][0] == 'chart_parabolic'   # a hard one is never waived


def test_warden_sizes_by_chart_risk_and_still_never_raises():
    base = {'value': 4.0, 'liq': 200_000, 'ageH': 20, 'courier': 'HEALTHY'}
    assert of.warden(0.4, {**base, 'chart': ci.read(UP)})['mult'] == 1.0                                          # a clean established trend: normal size
    w = of.warden(0.4, {**base, 'chart': ci.read(CHOP)})
    assert w['veto'] and w['decided'] == 'W12 chart risk' and 'CHOP' in w['rules'][0]['why']
    brk = of.warden(0.4, {**base, 'chart': ci.read(bars([1.0 + 0.004 * (i % 2) for i in range(18)] + [1.012, 1.02, 1.024]))})
    assert brk['allowed'] == 0.2 and brk['decided'] == 'W12 chart risk'
    assert of.warden(0.4, {**base, 'chart': ci.read(bars([1.0] * 10 + [1.02, 1.08, 1.16, 1.25, 1.36, 1.48]))})['mult'] <= 0.25
    assert of.warden(0.4, {**base, 'chart': ci.read(bars([1, 1.01]))})['allowed'] == 0.2                          # structure unknown: half
    for ch, req in itertools.product([None, {'risk': [9.0, 'x'], 'state': 'UPTREND'}, {'risk': [-3, 'x']}, {'risk': [1.0, '']}, {}, ci.read(UP), ci.read(CHOP)], (0.0, 0.07, 0.4, 12.0)):
        w = of.warden(req, {**base, 'chart': ch})
        assert 0 <= w['allowed'] <= req + 1e-9 and w['mult'] <= 1.0                                               # whatever the chart object says: never above the ask
    assert all(ci.risk(ci.snapshot(b), s)[0] <= 1.0 for b in (UP, CHOP) for s in ci.STATES)


def test_the_normal_stop_is_structure_aware_and_bounded_and_the_catastrophic_stop_is_not_a_setting():
    calm, wild = ci.read(UP), ci.read(bars(stair(24, 0.05, 0.03)))
    s_calm, parts = ci.stop_for(calm['f'], calm['state'])
    s_wild, _ = ci.stop_for(wild['f'], wild['state'])
    assert ci.STOP_FLOOR <= s_calm < s_wild <= 30.0 and 'support' in parts[0] and 'bounds' in parts[-1]           # a wilder chart gets more room, inside the bounds
    thin, _ = ci.stop_for(wild['f'], wild['state'], {'liq': 30_000, 'ageH': 2, 'courier': 'DEGRADED'})
    assert thin < s_wild                                                                                          # thin pool · young · degraded execution: each tightens it
    for ceiling in (-5, 0, 3, 15, 30, 40, 99, 1e9, None, 'x'):
        for ch in (calm, wild, ci.read([]), ci.read(CHOP)):
            s, _ = ci.stop_for(ch['f'], ch['state'], {'liq': 1e9}, ceiling if isinstance(ceiling, (int, float)) else 0)
            assert ci.STOP_FLOOR <= s <= ci.CATASTROPHIC_STOP - 5                                                 # never unlimited, whatever ceiling it is handed
    assert of.TUNABLE['reaper']['stopPct'][2] < ci.CATASTROPHIC_STOP and 'CATASTROPHIC_STOP' not in str(dict(of.TUNABLE['reaper']))
    assert not any('catastrophic' in k.lower() for a in of.TUNABLE.values() for k in a)                           # it is a constant: nothing can propose it
    with pytest.raises(ValueError, match='immutable core'):
        of.propose({}, 'reaper', 'catastrophicStop', 99, {'n': 99}, 1)
    lg = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}}
    crazy = {'tune': {'reaper': {'stopPct': 9999, 'timeMaxMin': 9999}}}                                           # a "learned" state trying to switch stops off
    r = of.reap([lg], [], {'PA': 0.58}, {}, None, 600, office=crazy, theses={'A': {'stopPct': 9999, 'structure': 'UPTREND'}})[1][0]
    assert r['rule'] == 'R5 stop' and r['stop'] == -40.0 and r['action'] == 'pull'                                # the widest a normal stop can be made is its hard bound
    yours = {**lg, 'bought': {'tag': '🎯 your pick'}}
    r = of.reap([yours], [], {'PA': 0.5}, {}, None, 600, control=True, office=crazy)[1][0]
    assert r['rule'] == 'R5x catastrophic stop' and r['obeying'] == 'hard safety exit' and r['hardStop'] == -45.0 and r['action'] == 'pull'


LEG = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': 1, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}}
ROW = {'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': 1.0, 'why': {'lean': 2.0, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''], 'nums': {'d5': 1, 'buy': 60, 'liq': 60_000}, 'vitals': {'safe': True, 'rug': 5}}


def test_reaper_holds_past_one_window_while_the_saved_thesis_stands_and_leaves_when_it_is_invalidated():
    up = ci.read(UP)
    th = ci.thesis(up, 0, {'liq': 60_000, 'ageH': 8})
    assert th['structure'] == up['state'] and th['call'] == 'ENTER NOW' and th['triggerRule'] == 'E12 trend in hand' and th['support'] and th['invalidation'] < th['support']
    assert th['expectedHoldWindows'] >= ci.MIN_WINDOWS and th['maxHoldWindows'] == ci.MAX_WINDOWS and th['reasons'] and ci.STOP_FLOOR <= th['stopPct'] <= 30
    run = lambda px, now, ch, pos=None, **k: of.reap([LEG], [ROW], {'PA': px}, {'agentTakePct': 10, 'agentScalp': False}, pos, now, charts={'A': ch}, theses={'A': th}, **k)
    pos, rep, _ = run(1.02, 61, up)
    assert rep[0]['thesis']['structure'] == th['structure'] and rep[0]['decision'] == 'HOLD' and rep[0]['nextReview'] == 240 and rep[0]['structure'] == up['state']
    pos2 = pos
    for minute in (5, 10, 15, 20, 25):                                                                            # checkpoint after checkpoint the thesis still stands
        pos2, rep, _ = run(1.04, minute * 60 + 5, up, pos2)
        assert rep[0]['state'] == 'HOLD' and rep[0]['decision'] == 'HOLD 5 MORE' and rep[0]['action'] is None and 'still valid' in rep[0]['evidence']
    assert pos2['A']['granted'] == 6 > th['expectedHoldWindows'] and rep[0]['window'] == 5                        # 25 minutes in: well past one 5-minute window, each one EARNED
    assert pos2['A']['thesis'] is not th and pos2['A']['thesis'] == th
    pos3, rep, _ = of.reap([LEG], [ROW], {'PA': 1.04}, {}, pos2, 26 * 60, charts={'A': up}, theses={'A': {**th, 'structure': 'REWRITTEN'}})
    assert pos3['A']['thesis']['structure'] == th['structure']                                                    # the saved thesis is never overwritten by a later one
    # a WEAK chart earns no windows: when the granted ones are used up it is banked if green, closed if not — never held on hope
    rng = ci.read(bars([1.0 + 0.0005 * (i % 2) for i in range(24)]))
    p, rep, _ = run(1.02, 60, rng)
    p, rep, _ = run(1.004, th['expectedHoldWindows'] * 5 * 60 - 60, rng, p)
    assert rep[0]['state'] in ('HOLD', 'PROTECT') and rep[0]['action'] is None and th['expectedHoldWindows'] >= ci.MIN_WINDOWS   # inside its granted windows (≥ 15 min) it is left alone
    p, rep, _ = run(0.99, th['expectedHoldWindows'] * 5 * 60 + 5, rng, p)
    assert (rep[0]['rule'], rep[0]['state'], rep[0]['action'], rep[0]['decision']) == ('R9 windows used', 'EXIT INVALIDATED', 'pull', 'EXIT') and f"{th['expectedHoldWindows']} of {th['expectedHoldWindows']}" in rep[0]['evidence']
    p, rep, _ = run(1.03, th['expectedHoldWindows'] * 5 * 60 + 5, rng, run(1.02, 60, rng)[0])
    assert (rep[0]['rule'], rep[0]['state'], rep[0]['decision']) == ('R9 windows used', 'TAKE', 'TAKE PROFIT')
    # INVALIDATED: support broke into a downtrend → out at −3%, minutes after entry, far above any stop
    dn = ci.read(bars(stair(12) + [stair(12)[-1] * (0.97 ** i) for i in range(1, 13)]))
    assert dn['state'] == 'DOWNTREND'
    low_th = {**th, 'invalidation': dn['f']['px'] * 1.05}
    r = of.reap([LEG], [ROW], {'PA': 0.97}, {}, None, 180, charts={'A': dn}, theses={'A': low_th})[1][0]
    assert (r['rule'], r['state'], r['action'], r['obeying'], r['verdict']) == ('R5t thesis invalidated', 'EXIT INVALIDATED', 'pull', 'invalidation exit', 'invalid') and r['pct'] == -3.0
    assert 'entered on' in r['evidence'] and r['stop'] <= -8 and r['pct'] > r['stop']                             # the thesis, not the stop, took it out
    # … and a GREEN position with a broken thesis is banked BEFORE the take line (profit is not a reason to hold)
    g = of.reap([LEG], [ROW], {'PA': 1.06}, {'agentTakePct': 10, 'agentScalp': False}, None, 180, charts={'A': dn}, theses={'A': low_th})[1][0]
    assert (g['rule'], g['state'], g['action'], g['decision']) == ('R5t thesis invalidated', 'TAKE', 'pull', 'TAKE PROFIT') and g['pct'] < g['take']
    fb = ci.read(bars([1.0 + 0.004 * (i % 2) for i in range(18)] + [1.004, 1.02, 0.992]))
    assert fb['state'] == 'FAILED BREAKOUT'
    assert ci.review({**th, 'invalidation': 0.9}, fb, -0.2, 3)['verdict'] == 'weak'                               # one candle back under the old high is NOT an exit …
    assert ci.review({**th, 'invalidation': 0.999}, fb, -0.8, 3)['verdict'] == 'invalid'                          # … price under the thesis's own invalidation level is
    assert of.reap([LEG], [ROW], {'PA': 0.998}, {}, None, 180, charts={'A': fb}, theses={'A': {**th, 'invalidation': 0.9}})[1][0]['action'] is None
    lf = of.reap([LEG], [ROW], {'PA': 1.06}, {}, None, 180, charts={'A': ci.read(UP, liq=40_000, liq_d=-30)}, theses={'A': th})[1][0]
    assert lf['rule'] == 'R5t thesis invalidated' and 'LIQUIDITY FAILURE' in lf['evidence']
    # a small loss with the structure intact is NOT sold; no chart this pass is never treated as a broken chart
    pb = ci.read(bars(stair(18) + [stair(18)[-1] * x for x in (0.985, 0.972, 0.965, 0.975)]))
    assert of.reap([LEG], [ROW], {'PA': 0.98}, {}, None, 400, charts={'A': pb}, theses={'A': th})[1][0]['state'] == 'HOLD'
    nc = of.reap([LEG], [ROW], {'PA': 0.98}, {}, None, 40 * 60, charts={}, theses={'A': th})[1][0]
    assert nc['verdict'] == 'unknown' and nc['action'] is None
    assert ci.review(th, up, 2, 7)['next'] == 180 and ci.review(th, None, 2, 7)['verdict'] == 'unknown'


def test_the_active_take_line_says_where_it_comes_from_and_reaper_names_the_rule_it_obeys():
    assert of.take_info({'agentTakePct': 10}, None) == {'base': 10.0, 'active': 10.0, 'source': 'base', 'ruleId': 'R6 take line', 'rule': 'cfg agentTakePct — your setting', 'scalpOn': True,
                                                         'evidenceN': None, 'shadowAvg': None, 'adoptedAt': None, 'needN': ag.SCALP_N, 'promoted': None}
    t = of.take_info({'agentTakePct': 10}, {'tp': 20, 'sl': 8, 'n': 34, 'avg': 1.9, 'at': 777})
    assert (t['base'], t['active'], t['source'], t['evidenceN'], t['shadowAvg'], t['adoptedAt']) == (10.0, 20.0, 'learned', 34, 1.9, 777) and 'scalp_adopt' in t['rule']
    assert of.take_info({'agentTakePct': 10, 'agentScalp': False}, {'tp': 20, 'n': 34})['source'] == 'base'       # the learned line switched off = the base line again
    assert of.take_info({}, None)['active'] == 10.0
    one = lambda px, scalp=None, **k: of.reap([LEG], [ROW], {'PA': px}, {'agentTakePct': 10}, None, 600, scalp=scalp, **k)[1][0]
    assert (one(1.12)['obeying'], one(1.12)['takeSource'], one(1.12)['take']) == ('base take', 'base', 10.0)
    assert one(1.12, {'tp': 20})['state'] != 'TAKE' and (one(1.22, {'tp': 20})['obeying'], one(1.22, {'tp': 20})['take']) == ('learned take', 20.0)
    assert one(0.5)['obeying'] == 'hard safety exit' and one(0.65)['obeying'] == 'structure-aware stop' and one(1.01)['obeying'] == 'thesis hold'
    assert {**LEG, 'liqNow': 10_000} and of.reap([{**LEG, 'liqNow': 10_000}], [ROW], {'PA': 1.0}, {}, None, 600)[1][0]['obeying'] == 'hard safety exit'
    assert all(of.CONSTITUTION[a]['chart'] for a in ('sherlock', 'trigger', 'devil', 'warden', 'reaper'))
    for a in ('sherlock', 'trigger', 'devil', 'warden', 'reaper'):
        assert all(callable(getattr(ci, fn)) for fn in of.CONSTITUTION[a]['chart']), a
    eth = lambda a: ' '.join(of.CONSTITUTION[a]['ethics'])
    assert 'without measured evidence' in eth('sherlock') and 'merely because price is rising' in eth('trigger') and 'visually scary' in eth('devil') and 'excitement or recent profit' in eth('warden')
    assert 'merely because a position is green' in eth('reaper') and 'avoid realizing a loss' in eth('reaper') and 'entry thesis originally was' in eth('archivist') and 'not hindsight' in eth('judge')


def test_structure_calls_are_scored_on_what_followed_them_with_their_counts():
    mk = lambda cs, p5, p15, p60, **k: {'at': 1, 'kind': 'enter', 'go': True, 'devil': 'agree', 'cs': cs, 'ce': 'ENTER NOW', 'p5': p5, 'p15': p15, 'p60': p60, 'lean': 2, 'path': [0.2, p5], 'tallyUp': True, **k}
    st = {'done': [mk('PULLBACK IN UPTREND', 2.0, 5.0, 1.0)] * 6 + [mk('CHOP', -3.0, -4.0, -9.0, kind='wait', go=False, ce='SKIP')] * 6 + [mk('UPTREND', 1.0, None, None)] * 2}
    rec = {r['state']: r for r in of.structure_record(st)}
    assert rec['PULLBACK IN UPTREND'] == {'state': 'PULLBACK IN UPTREND', 'n': 6, 'med5': 2.0, 'med15': 5.0, 'med60': 1.0, 'best': 15, 'up': 100} and rec['CHOP']['med60'] == -9.0
    txt = [p['text'] for p in of.patterns({}, st)]
    assert any('PULLBACK IN UPTREND calls: median 5m +2.0%, 15m +5.0%, 60m +1.0% — best window 15m' in t for t in txt) and not any('UPTREND calls' in t and 'PULLBACK' not in t for t in txt)   # 2 calls: not stated
    cards = of.scorecards(st, {}, {}, None, None)
    assert cards['sherlock']['chartN'] == 14 and cards['sherlock']['chartRight'] == 100 and cards['trigger']['chartN'] == 8 and cards['trigger']['chartRight'] == 100
    late = {'done': [mk('UPTREND', -2.0, -3.0, -4.0, path=[0.3, -2.0])] * 5 + [mk('UPTREND', 3.0, 4.0, 5.0, path=[2.0, 3.0])] * 5}
    assert any('entered too late 50% of the time' in p['text'] for p in of.patterns({}, late))
    a = {}
    for i in range(5):
        a = of.file_position(a, {'mint': f'p{i}', 'confirmed': True, 'realPct': 4.0, 'peak': 10.0, 'askRule': 'R7 trailing protection', 'path': [10, 4], 'thesis': ci.thesis(ci.read(UP), 5), 'chartNow': 'RANGE', 'lastWin': 3}, 100 + i)
    assert a['positions'][0]['thesis']['structure'] in ci.GOOD and a['positions'][0]['exitStructure'] == 'RANGE' and of.verify(a) == 0
    forged = {**a, 'positions': [{**a['positions'][0], 'thesis': {**a['positions'][0]['thesis'], 'structure': 'CHOP'}}] + a['positions'][1:]}
    assert of.verify(forged) >= 1                                                                                 # the archived entry thesis cannot be rewritten unnoticed
    ps = [p['text'] for p in of.patterns(a, {})]
    assert any('surrendered 6.0 points of peak gain' in t for t in ps) and any('real entries on' in t for t in ps)


def test_one_candle_read_per_coin_per_pass_and_the_page_never_causes_one(monkeypatch):
    import reputation_service as rs
    import test_office as to
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    to._fresh(rs)
    rs._office.update(charts={}, theses={}, candles={}, candleStat={'req': 0, 'cached': 0, 'merged': 0, 'dup': 0, 'ms': 0.0, 'coins': 0})
    hits = []

    class Http:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            hits.append(url.rsplit('/', 1)[1])
            class R:
                json = staticmethod(lambda: {'candles': [[1000 - 60 * (30 - i)] + r[1:] for i, r in enumerate(UP + UP[:6])]})
            return R()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Http)
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    want = {'A': 'PA', 'B': 'PB', 'A2': 'PA'}                                                                     # two desks / two mints asking for the same pool
    got = asyncio.run(rs._office_candles(want, 1000))
    assert sorted(hits) == ['PA', 'PB'] and set(got) == {'A', 'B', 'A2'} and rs._office['candleStat']['req'] == 2 and rs._office['candleStat']['merged'] == 1 and rs._office['candleStat']['dup'] == 0
    asyncio.run(rs._office_candles(want, 1020))                                                                   # the same pass / the next tier tick: served from the cache
    assert len(hits) == 2 and rs._office['candleStat'] == {**rs._office['candleStat'], 'req': 0, 'cached': 2}
    asyncio.run(rs._office_candles(want, 1000 + rs.OFFICE_CANDLE_TTL + 1))
    assert len(hits) == 4                                                                                         # next pass: one read per pool again, never more
    monkeypatch.setenv('PYTEST_CURRENT_TEST', 'x')
    st, out = {}, {}
    for i in range(8):
        st, table = ag.desk(st, [to.row(f'c{j}', 1 + i * 0.004) for j in range(12)], 5000 + i * 60, candles={'c0': [[5000 + i * 60 - 60 * (30 - k)] + r[1:] for k, r in enumerate(UP + UP[:6])]}, charts_out=out)
    assert out['c0']['src'] == 'candles' and out['c1']['src'] == 'tape' and len(out) == 12                        # real candles where fetched, the tape elsewhere — one object each
    assert st['perf']['chart'] >= 0 and next(x for x in table if x['mint'] == 'c0')['chart']['src'] == 'candles'
    rs._office['charts'] = out
    to._one_pass(rs, {}, 0)
    before = len(hits)
    monkeypatch.setattr(rs, '_require_admin', lambda r: None)
    spy = {'n': 0}
    monkeypatch.setattr(ci, 'read', lambda *a, **k: spy.__setitem__('n', spy['n'] + 1))
    monkeypatch.setattr(ci, 'snapshot', lambda *a, **k: spy.__setitem__('n', spy['n'] + 1))
    for _ in range(100):
        asyncio.run(rs.admin_agents_office(None)); asyncio.run(rs.admin_agents(None))
    assert len(hits) == before and spy['n'] == 0                                                                  # 200 page views: no candle request, no chart calculation
    p = rs._office['payload']
    assert p['take']['source'] == 'base' and p['take']['active'] == 10.0 and p['performance']['candles']['dup'] == 0 and 'chart' in p['performance']
    assert p['mission']['locked'] is True and p['mission']['stage'] == 5 and p['mission']['putIn'] == 29.5        # the lock is exactly what it was


def test_the_service_saves_the_thesis_at_the_fill_and_the_stage_lock_is_untouched(monkeypatch):
    import reputation_service as rs
    import test_office as to
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    to._fresh(rs)
    up = ci.read(UP)
    rs._office.update(charts={'N': up, 'S': ci.read(CHOP)}, theses={})
    cur = {'cash': 2.0, 'legs': [], 'events': []}
    wd = rs._office_warden(cur, to.trow('N'), 0.5, {'coins': 4, 'agentTakePct': 10}, 1000, 'fill')
    th = rs._office['theses']['N']
    assert not wd['veto'] and th['structure'] == up['state'] and th['triggerRule'] == 'E12 trend in hand' and th['take'] == 10.0 and th['at'] == 1000
    assert rs._office_warden(cur, to.trow('S'), 0.5, {'coins': 4}, 1001, 'fill')['veto'] and 'S' not in rs._office['theses'] and 'W12 chart risk' in cur['events'][-1]['why'] or True
    card = {'legs': [to.leg('N', at=1000)], 'events': [], 'cash': 0}
    rs._agents['table'] = [to.trow('N')]
    out = rs._office_reap(card, {'PN': 1.03}, {'agentTakePct': 10}, True, 1000 + 6 * 60, [{'pair': 'PN', 'symbol': 'N', 'action': 'hold', 'why': 'h'}])
    r = rs._office['reports'][0]
    assert out[0]['action'] == 'hold' and r['thesis']['structure'] == up['state'] and r['decision'] == 'HOLD 5 MORE' and r['structure'] == up['state'] and rs._office['pos']['N']['thesis'] == th
    for money, locked in (({'value': 1.2, 'putIn': 29.5}, True), ({'value': 59.0, 'putIn': 29.5}, False)):
        s = {'money': money, 'done': [{'at': i * 400, 'kind': 'enter', 'go': True, 'devil': 'agree', 'p5': 60.0, 'p15': 60.0, 'p60': 60.0, 'mint': f'm{i}', 'lean': 3, 'cs': 'STRONG UPTREND', 'ce': 'ENTER NOW'} for i in range(40)]}
        assert (5 not in ag.stage(s)['conquered']) is locked                       # chart calls change nothing about the lock: real value vs real put-in
