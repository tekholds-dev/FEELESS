"""🧪 Market-data truth: a chart that rendered is not evidence. Tally's gate, what each desk may do with bad data, and the real-money
stage rule (breakeven = milestone 1 · 2× the put-in = graduation)."""
import math

import agents as ag
import chart_intel as ci
import market_data as md
import office as of

NOW = 100_000.0


def bars(closes, wick=0.002, vol=1500.0, end=NOW - 30):
    """Real-looking 1-minute candles ending just before NOW: open = the close before, small wicks, a volume figure on every bar."""
    out, prev, t0 = [], closes[0], end - (len(closes) - 1) * 60
    for i, c in enumerate(closes):
        out.append([t0 + i * 60, prev, max(prev, c) * (1 + wick), min(prev, c) * (1 - wick), c, vol])
        prev = c
    return out


def stair(n=24, step=0.012, dip=0.004):
    out, px = [], 1.0
    for i in range(n):
        px *= (1 - dip) if i % 3 == 2 else (1 + step)
        out.append(px)
    return out


META = {'provider': 'Jupiter', 'source': 'Jupiter price history, sharpened with FEELESS-recorded live ticks.', 'tickCount': 60, 'vol5m': 12_000, 'vol1h': 90_000, 'liqAge': 0.0}
UP = bars(stair())


def test_real_candlestick_data_passes_the_quality_gate_and_says_where_every_number_came_from():
    q = md.quality(UP, NOW, True, 'candles', META, liq=80_000, flow={'buyUsd': 900, 'sellUsd': 300, 'n': 14})
    assert q['state'] == 'TRUSTED' and q['conf'] >= md.TRUSTED_MIN and q['readOk'] and q['structOk'] and q['enterOk'] and q['risk'] == 1.0 and not q['fails']
    p = q['prov']
    assert p['realOhlc'] and p['realVolume'] and p['realFlow'] and p['realLiquidity'] and not p['synthetic'] and p['label'] == '24 real 1m' and p['nCandles'] == 24 and p['nTrades'] == 14
    assert 'Jupiter' in p['candleSource'] and 'candles service' in p['dataSource'] and 'trade tape' in p['tradeSource'] and 'launch board' in p['liquiditySource'] and 'candle bars' in p['volumeSource']
    assert p['firstTs'] == UP[0][0] and p['lastTs'] == UP[-1][0] and p['ageSec'] == 30.0
    c = ci.read(UP, NOW, True, 'candles', META, buy=60, liq=80_000)
    assert c['state'] in ('STRONG UPTREND', 'UPTREND') and c['entry'][0] == 'ENTER NOW' and c['q']['state'] == 'TRUSTED' and c['risk'][0] == 1.0   # good data changes nothing about a good chart
    assert md.word(c['q']).startswith('DATA TRUSTED ') and md.compact(c['q'])['label'] == '24 real 1m'


def test_malformed_ohlc_is_rejected_and_is_never_read_as_a_bad_coin():
    for breaker, check in ((lambda r: r.__setitem__(2, r[4] * 0.9), 'ohlc'),            # high under the close
                           (lambda r: r.__setitem__(3, r[1] * 1.1), 'ohlc'),            # low above the open
                           (lambda r: r.__setitem__(4, float('nan')), 'finite'),
                           (lambda r: r.__setitem__(1, 0.0), 'finite'),
                           (lambda r: r.__setitem__(4, -1.0), 'finite'),
                           (lambda r: r.__setitem__(4, float('inf')), 'finite'),
                           (lambda r: r.__setitem__(5, -40.0), 'volume_valid')):
        rows = [list(r) for r in UP]
        breaker(rows[10])
        q = md.quality(rows, NOW, True, 'candles', META, liq=80_000)
        assert q['state'] == 'MALFORMED' and check in q['fails'] and not q['readOk'] and not q['enterOk'] and q['risk'] == 0.0 and q['conf'] <= 5, check
        c = ci.read(rows, NOW, True, 'candles', META, buy=70, liq=80_000)
        # DATA INVALID is its own state: no trend, no "downtrend", no "failed breakout", no momentum claim is made from the rows
        assert c['state'] == ci.DATA_INVALID and c['state'] not in ci.BAD and c['state'] not in ci.GOOD and c['trend'] is None and c['mom'] is None and c['ev'] == []
        assert c['entry'][0] == 'WAIT FOR DATA' and c['risk'][0] == 0.0 and c['objs'][0][0] == 'data_integrity' and 'MALFORMED' in c['con'][0]
    assert all(math.isfinite(md.quality([[1, 'x', None, {}, [], 2], None, [3]], NOW)['conf']) for _ in (0,))            # garbage in never throws


def test_duplicate_out_of_order_future_and_stale_candle_streams_are_flagged():
    dup = [list(r) for r in UP]
    dup[5][0] = dup[4][0]; dup[9][0] = dup[8][0]
    assert md.quality(dup, NOW)['state'] == 'INCONSISTENT' and 'duplicates' in md.quality(dup, NOW)['fails']
    one = [list(r) for r in UP]; one[5][0] = one[4][0]
    assert md.quality(one, NOW)['state'] != 'TRUSTED' and 'duplicates' in md.quality(one, NOW)['soft']               # one duplicate: caution, not trusted
    back = [list(r) for r in UP]; back[7][0] = back[3][0] - 5
    assert md.quality(back, NOW)['state'] == 'INCONSISTENT' and 'order' in md.quality(back, NOW)['fails']
    fut = bars(stair(), end=NOW + 900)
    assert md.quality(fut, NOW)['state'] == 'INCONSISTENT' and 'future' in md.quality(fut, NOW)['fails']
    old = bars(stair(), end=NOW - 600)
    q = md.quality(old, NOW, True, 'candles', META, liq=80_000)
    assert q['state'] == 'STALE' and not q['readOk'] and q['prov']['ageSec'] == 600.0 and ci.read(old, NOW, True, 'candles', META, liq=80_000)['state'] == ci.DATA_INVALID
    holes = UP[:8] + [[r[0] + 1800] + list(r[1:]) for r in UP[8:16]] + [[r[0] + 5400] + list(r[1:]) for r in UP[16:]]
    assert 'gaps' in md.quality(holes, NOW + 5400, True, 'candles', META, liq=80_000)['soft'] + md.quality(holes, NOW + 5400, True, 'candles', META, liq=80_000)['fails']
    rep = [list(r) for r in UP]
    for i in (11, 12, 13):
        rep[i][1:5] = rep[10][1:5]
    assert md.quality(rep, NOW)['state'] == 'INCONSISTENT' and 'repeat' in md.quality(rep, NOW)['fails']             # the same candle printed again and again
    jump = [list(r) for r in UP]
    jump[12][1] = jump[11][4] * 3; jump[12][2] = max(jump[12][2], jump[12][1])
    assert 'jump' in md.quality(jump, NOW)['fails']


def test_giant_alternating_candles_are_a_broken_feed_but_a_real_chop_is_still_a_chart():
    ping = bars([1.0 * (1.08 if i % 2 else 1.0) for i in range(26)], wick=0.0)                                         # two prices trading places, full range every bar
    q = md.quality(ping, NOW, True, 'candles', META, liq=80_000)
    assert q['state'] == 'INCONSISTENT' and 'alternating' in q['fails'] and any('not a traded market' in c[2] for c in q['checks'])
    c = ci.read(ping, NOW, True, 'candles', META, buy=80, liq=80_000)
    assert c['state'] == ci.DATA_INVALID and c['entry'][0] == 'WAIT FOR DATA'                                         # it is not called CHOP, a DOWNTREND or anything else
    chop = bars([1.0 * (1 + (0.05 if i % 2 else -0.05) * (0.7 + 0.3 * ((i * 7) % 5) / 4)) for i in range(26)])       # violent, but every swing lands somewhere new
    assert md.quality(chop, NOW, True, 'candles', META, liq=80_000)['readOk'] and ci.read(chop, NOW, True, 'candles', META, liq=80_000)['state'] == 'CHOP'
    boxes = bars(stair(), wick=0.0)
    for i in range(6, 18):
        boxes[i][2], boxes[i][3] = 1.30, 1.00                                                                          # twelve candles with the exact same high and low
    assert 'repeat_range' in md.quality(boxes, NOW)['fails']
    flat = bars([1.0] * 20 + [1.001, 1.002, 1.003, 1.004], wick=0.0, vol=0.0)
    assert md.quality(flat, NOW, True, 'candles', META, liq=80_000)['state'] == 'SPARSE'                              # mostly nothing happened: sparse, said so
    assert md.quality(UP[-4:], NOW, True, 'candles', META, liq=80_000)['state'] == 'SPARSE' and md.quality([], NOW)['state'] == 'SPARSE' and ci.read([])['state'] == 'UNKNOWN'


def test_missing_volume_never_becomes_fake_volume_and_a_trade_count_is_never_called_volume():
    nov = [r[:5] + [0.0] for r in UP]                                                                                  # bars built from recorded prices: no volume figure
    q = md.quality(nov, NOW, True, 'candles', {'provider': 'Jupiter', 'txns1h': 420, 'liqAge': 0.0}, liq=80_000)
    p = q['prov']
    assert q['state'] == 'NO_VOLUME' and not q['enterOk'] and p['volume'] == 'UNAVAILABLE' and p['volumeWord'] == 'VOLUME UNAVAILABLE' and p['realVolume'] is False and p['volBars'] == 0
    assert p['volumeSource'] is None and p['txns1h'] == 420 and p['nTrades'] is None and p['tradeSource'] is None        # 420 transactions an hour is a TRADE count: it is not turned into volume
    withflow = md.quality(nov, NOW, True, 'candles', {'provider': 'Jupiter', 'liqAge': 0.0}, liq=80_000, flow={'buyUsd': 50, 'sellUsd': 40, 'n': 9})['prov']
    assert withflow['nTrades'] == 9 and withflow['volume'] == 'UNAVAILABLE' and withflow['flowCalc'] == md.TAPE_CALC      # 9 trades on the tape are TRADES; the flow says exactly how it was computed
    board = md.quality(nov, NOW, True, 'candles', META, liq=80_000)
    assert board['state'] == 'USABLE_WITH_CAUTION' and board['enterOk'] and board['prov']['volume'] == 'PARTIAL' and board['prov']['realVolume'] is False
    assert 'no per-candle volume' in board['prov']['volumeWord'] and 'launch board' in board['prov']['volumeWord'] and board['conf'] < 100
    mixed = [r[:5] + [900.0 if i < 6 else 0.0] for i, r in enumerate(UP)]
    assert md.quality(mixed, NOW, True, 'candles', META, liq=80_000)['prov']['volumeWord'].startswith('per-candle volume on 6 of 24 rows')
    assert ci.read(nov, NOW, True, 'candles', {'provider': 'Jupiter', 'liqAge': 0.0}, liq=80_000)['entry'][0] == 'WAIT FOR DATA'
    # liquidity: unknown is unknown — never a known $0, never a known deep pool
    for liq in (None, 0, float('nan'), -5):
        ql = md.quality(UP, NOW, True, 'candles', META, liq=liq)
        assert ql['state'] == 'NO_LIQUIDITY' and ql['prov']['liquidity'] == 'UNKNOWN' and not ql['prov']['realLiquidity'] and not ql['enterOk'] and ql['risk'] <= 0.5
    assert md.quality(UP, NOW, True, 'candles', {**META, 'liqAge': 400}, liq=80_000)['prov']['liquidity'] == 'STALE'
    held = md.quality(UP, NOW, True, 'candles', {'provider': 'Jupiter', 'noCtx': True})                               # a held coin off the board: provenance kept, pool / board volume not judged
    assert held['state'] == 'TRUSTED' and held['prov']['liquidity'] == 'NOT SUPPLIED' and held['prov']['provider'] == 'Jupiter'


def test_a_reconstructed_tape_is_explicitly_marked_reconstructed_and_is_never_enter_grade():
    tape = ci.from_tape([{'t': NOW - (23 - i) * 60, 'px': p} for i, p in enumerate(stair())])
    q = md.quality(tape, NOW, False, 'tape', {'vol5m': 12_000, 'vol1h': 90_000, 'liqAge': 0.0}, liq=80_000)
    p = q['prov']
    assert q['state'] == 'NO_REAL_CANDLES' and q['readOk'] and not q['enterOk'] and q['conf'] <= 45 and p['synthetic'] and not p['realOhlc'] and not p['realVolume']
    assert p['label'].startswith('RECONSTRUCTED FROM TAPE') and 'RECONSTRUCTED FROM TAPE' in p['candleSource'] and 'tape' in p['dataSource'] and 'reconstructed' in q['why']
    c = ci.read(tape, NOW, False, 'tape', {'vol5m': 12_000, 'vol1h': 90_000, 'liqAge': 0.0}, buy=62, liq=80_000)
    assert c['state'] in ('STRONG UPTREND', 'UPTREND') and c['entry'][:2] == ['WAIT FOR DATA', 'E0d data quality'] and c['risk'][0] <= 0.5     # the structure is read and labelled; it is not entered on
    own = md.quality(UP, NOW, True, 'candles', {**META, 'provider': 'FEELESS'}, liq=80_000)
    assert own['state'] == 'NO_REAL_CANDLES' and own['prov']['synthetic'] and 'recorded prices only' in own['prov']['label']                     # bars from our own recorded prices alone are derived, and say so


def _desk(cmap, cmeta=None, flows=None, n=24, **row):
    """The four desks over a coin whose own tape is a clean uptrend, with `cmap` as the candle map of the final pass."""
    mk = lambda m, px, **k: {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'price': px, 'vol5m': 20_000, 'vol1h': 80_000, 'buyShare': 64, 'liq': 60_000, 'ageH': 8, 'chg1h': 30, 'safe': True,
                             'tv': {'call': ['🔥', 'SEND IT', 'good'], 'rug': 10}, **k}
    st, t = {}, []
    for i in range(n):
        last = i == n - 1
        st, t = ag.desk(st, [mk('GOOD', stair()[i], **row)] + [mk(f'c{j}', 1 + i * 0.001) for j in range(10)], NOW - (n - 1 - i) * 60, candles=(cmap if last else {}), flows=flows, cmeta=cmeta)
    return st, {x['mint']: x for x in t}


def test_untrusted_data_cannot_produce_a_trigger_enter_from_chart_structure(monkeypatch):
    monkeypatch.setattr(ag, 'trigger', lambda n, why, row, learned: ('enter', 'lean over the bar'))   # Trigger's own numbers say ENTER on every pass: only the chart layer can stop it
    meta = {'GOOD': {'provider': 'Jupiter', 'source': 'Jupiter price history'}}
    _, plain = _desk(None)                                                                                             # no chart layer at all: what Trigger says on its own
    _, real = _desk({'GOOD': UP}, meta)
    assert real['GOOD']['chart']['q']['state'] in md.ENTER_OK and real['GOOD']['trigger'][0] == plain['GOOD']['trigger'][0] == 'enter' and '📈 E12' in real['GOOD']['trigger'][1]   # real, intact candles: the entry stands
    ok = {k[0]: k[1] for k in next(c for c in ag.investigate(real.values(), set(), 1, {}, top=0) if c['mint'] == 'GOOD')['checks']}
    assert ok['chart'] and ok['data']
    bad = [list(r) for r in UP]; bad[12][2] = bad[12][4] * 0.5
    ping = bars([1.0 * (1.08 if i % 2 else 1.0) for i in range(26)], wick=0.0)
    for name, cmap in (('tape', {}), ('malformed', {'GOOD': bad}), ('alternating', {'GOOD': ping}), ('stale', {'GOOD': bars(stair(), end=NOW - 900)}), ('no volume', {'GOOD': [r[:5] + [0.0] for r in UP]})):
        st, t = _desk(cmap, meta, **({'vol5m': 0, 'vol1h': 0} if name == 'no volume' else {}))
        g = t['GOOD']
        assert g['trigger'][0] != 'enter' and not g['go'] and g['chart']['entry'][0] == 'WAIT FOR DATA' and not g['chart']['q']['enterOk'], name
        case = next((c for c in ag.investigate(t.values(), set(), 1, {}, top=0) if c['mint'] == 'GOOD'), None)      # (no case file at all when the read is no longer positive)
        assert case is None or (not case['cleared'] and [k for k in case['checks'] if k[0] == 'data'][0][1] is False), name   # the duty waives Trigger's bar, never the data gate
        assert case is not None or name != 'tape'
        assert ag.record(st, list(t.values()), NOW, controls=99)['open']['GOOD']['dq'] == g['chart']['q']['state']                # the data-quality state is stored WITH the call
        if name in ('malformed', 'alternating', 'stale'):
            assert g['chart']['state'] == ci.DATA_INVALID and not any(d[0].startswith('chart:') for d in g['why']['drivers']), name   # Sherlock infers no structure from rejected rows
            assert g['case'] is None or (g['case'][0] == 'object' and 'data_integrity' in [o[0] for o in g['objs']]), name
    assert plain['GOOD'].get('chart') is None


def test_bad_data_is_a_hard_devil_objection_that_no_record_can_waive():
    assert ci.CHART_RULES['data_integrity'][0] is True and ag.DEVIL_RULES['data_integrity'][0] is True
    bad = [list(r) for r in UP]; bad[3][3] = bad[3][2] * 2
    ch = ci.read(bad, NOW, True, 'candles', META, liq=80_000)
    row = {'safe': True, 'tv': {'rug': 5, 'call': ['', 'X', '']}, 'chart': ch}
    args = ag.devil_args('enter', {}, {'drivers': [], 'lean': 4}, row, {'objrec': {'data_integrity': {'n': 500, 'med': 90.0}}})   # even a "winning" record does not waive it
    assert args[0][0] == 'data_integrity' and 'integrity' in args[0][1] and 'MALFORMED' in args[0][1]
    assert ag.devil_args('enter', {}, {'drivers': [], 'lean': 4}, {**row, 'chart': ci.read(UP, NOW, True, 'candles', META, liq=80_000)}, {}) == []


LEG = {'mint': 'A', 'symbol': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 1.0, 'at': NOW - 600, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}}
ROW = {'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': 1.0, 'why': {'lean': 2.0, 'drivers': []}, 'trigger': ['wait', ''], 'devil': ['—', ''], 'nums': {'d5': 1, 'buy': 60, 'liq': 60_000}, 'vitals': {'safe': True, 'rug': 5}}


def test_bad_chart_data_alone_never_makes_reaper_sell_an_existing_position_and_it_reports_data_degraded():
    good = ci.read(UP, NOW, True, 'candles', None)
    th = ci.thesis(good, NOW - 600)
    assert th['data']['state'] == 'TRUSTED' and th['data']['label'] == '24 real 1m'                                    # the thesis keeps the data-quality state it was made on
    bad = [list(r) for r in UP]; bad[20][2] = bad[20][4] * 0.2
    ping = bars([1.0 * (1.08 if i % 2 else 1.0) for i in range(26)], wick=0.0)
    for name, rows in (('malformed', bad), ('alternating', ping), ('stale', bars(stair(), end=NOW - 2000)), ('sparse', bars([1.0] * 22 + [0.6, 0.5], wick=0.0, vol=0.0))):
        ch = ci.read(rows, NOW, True, 'candles', META, liq=60_000)
        rv = ci.review(th, ch, -4.0, 10.0)
        assert rv['verdict'] == 'unknown' and rv['degraded'] and 'DATA DEGRADED' in rv['why'][0], name
        pos, rep, _ = of.reap([LEG], [ROW], {'PA': 0.96}, {}, None, NOW, charts={'A': ch}, theses={'A': th})
        r = rep[0]
        assert r['action'] is None and r['state'] == 'HOLD' and r['dataDegraded'] is True and 'DATA DEGRADED' in r['evidence'] and r['data']['state'] == ch['q']['state'], name
        assert not r['rule'].startswith(('R5t', 'R7s', 'R9'))                                                          # no chart-based exit is invented from it
    # … and the hard protections do not depend on the chart at all: the stop, the catastrophic stop and the pool rule still fire on bad data
    dead = ci.read(bad, NOW, True, 'candles', META, liq=60_000)
    assert of.reap([LEG], [ROW], {'PA': 0.50}, {}, None, NOW, charts={'A': dead}, theses={'A': th})[1][0]['rule'] == 'R5x catastrophic stop'
    assert of.reap([LEG], [ROW], {'PA': 1.0 - th['stopPct'] / 100 - 0.01}, {}, None, NOW, charts={'A': dead}, theses={'A': th})[1][0]['rule'] == 'R5 stop'
    assert of.reap([{**LEG, 'liqNow': 20_000}], [ROW], {'PA': 0.99}, {}, None, NOW, charts={'A': dead}, theses={'A': th})[1][0]['rule'] == 'R1 liquidity collapse'
    # with INTACT data the same thesis can still be invalidated by a real break (the rule itself is unchanged)
    fall = stair(12) + [stair(12)[-1] * (0.97 ** i) for i in range(1, 13)]
    brk = ci.read(bars(fall), NOW, True, 'candles', META, liq=60_000)
    th2 = {**th, 'invalidation': fall[-1] * 1.2}
    assert brk['q']['structOk'] and ci.review(th2, brk, -9.0, 10.0)['verdict'] == 'invalid'


def test_warden_only_ever_shrinks_on_degraded_data_and_tallys_confidence_is_on_every_trace():
    base = {'value': 2.0, 'cash': 2.0, 'seats': 1, 'liq': 80_000, 'ageH': 24}
    ok = ci.read(UP, NOW, True, 'candles', META, liq=80_000)
    tape = ci.read(ci.from_tape([{'t': NOW - (23 - i) * 60, 'px': p} for i, p in enumerate(stair())]), NOW, False, 'tape', {'vol5m': 1, 'liqAge': 0.0}, liq=80_000)
    bad = [list(r) for r in UP]; bad[3][3] = bad[3][2] * 2
    dead = ci.read(bad, NOW, True, 'candles', META, liq=80_000)
    assert of.warden(0.4, {**base, 'chart': ok})['mult'] == 1.0
    w = of.warden(0.4, {**base, 'chart': tape})
    assert w['mult'] <= 0.5 and any(r['id'] == 'W13 market data' for r in w['rules'])
    assert of.warden(0.4, {**base, 'chart': dead})['veto'] and all(of.warden(0.4, {**base, 'chart': c})['allowed'] <= 0.4 for c in (ok, tape, dead))
    assert all(v <= 1.0 for v in md.RISK.values()) and set(md.RISK) <= set(md.STATES)                                  # there is no data state that grows a seat
    # the trace: each desk answers its own question; Tally's data confidence leads it
    mk = lambda ch, call='wait', **k: {'mint': 'T', 'symbol': 'T', 'pair': 'PT', 'px': 1.0, 'lean': 2.0, 'go': False, 'cleared': False,
                                       'checks': [['scan', True, 'ok'], ['age', True, '8h'], ['pool', True, '$80K'], ['burn', True, 'ok'], ['devil', True, 'no evidence against it'],
                                                  ['chart', ch['entry'][0] == 'ENTER NOW', f"{ch['state']} → {ch['entry'][0]}"], ['data', ch['q']['enterOk'], 'data']],
                                       'row': {'mint': 'T', 'symbol': 'T', 'why': {'lean': 2.0, 'drivers': []}, 'trigger': [call, 'bar'], 'nums': {'pts': 9}, 'vitals': {}, 'chart': ci.compact(ch), 'objs': [], **k}}
    ctx = {'tally': {'readings': 9, 'ageSec': 20}, 'sherlock': {'lean': 2.0}, 'weather': {'regime': 'CHOP'}, 'courier': {'health': 'HEALTHY', 'why': ['12 of 12 sends landed']}}
    t = of.trace(mk(ok), ctx)
    assert [l[0] for l in t['lines']] == ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper']
    assert t['lines'][0][1] == md.word(ok['q']) and t['lines'][0][1].startswith('DATA TRUSTED') and t['lines'][2][1] == 'CHOP MARKET' and t['lines'][4][1] == 'NO HARD OBJECTION'
    assert t['lines'][6][1] == 'READY' and t['lines'][7][1] == 'NOT APPLICABLE UNTIL FILLED' and t['final'] in ('WAIT', 'CLEARED FOR THE DUTY')
    assert of.trace(mk(ok), {**ctx, 'courier': {'health': 'DEGRADED', 'why': ['x']}})['lines'][6][1] == 'EXECUTION DEGRADED — WAIT'
    tt = of.trace(mk(tape), ctx)
    assert tt['lines'][0][1].startswith('DATA NO REAL CANDLES') and tt['lines'][3][1] == 'WAIT FOR DATA' and tt['final'] == 'WAIT'
    td = of.trace(mk(dead), ctx)
    assert td['final'] == 'WAIT' and 'not a verdict on the coin' in td['why'] and of.pipeline(mk(dead), ctx)[0]['state'] == 'ERROR' and 'DATA MALFORMED' in of.pipeline(mk(dead), ctx)[0]['word']
    assert of.lineage_of(mk(ok), ctx)['data']['state'] == 'TRUSTED' and of.lineage_of(mk(dead), ctx)['data']['state'] == 'MALFORMED'   # the Archivist files the data state of the decision
    assert all(of.JOBS[a][0] and of.JOBS[a][1].endswith('?') or a == 'warden' for a in of.CHAIN) and len({of.JOBS[a][0] for a in of.CHAIN}) == 10   # ten different jobs


def test_the_judge_counts_acting_on_bad_data_as_a_violation_and_never_invents_a_dollar_attribution():
    call = lambda i, **k: {'at': i * 400, 'kind': 'enter', 'go': True, 'devil': 'agree', 'p5': 4.0, 'p15': 4.0, 'p60': 4.0, 'mint': f'm{i}', 'lean': 3, 'cs': 'UPTREND', 'ce': 'ENTER NOW', 'dq': 'TRUSTED', 'dqc': 92, **k}
    clean = {'done': [call(i) for i in range(12)]}
    dirty = {'done': [call(i) for i in range(9)] + [call(9, dq='MALFORMED'), call(10, dq='NO_REAL_CANDLES'), call(11, dq='STALE')]}
    a, b = of.scorecards(clean, {}, {}), of.scorecards(dirty, {}, {})
    assert a['trigger']['badData'] == 0 and b['trigger']['badData'] == 3 and b['trigger']['violations'] == a['trigger']['violations'] + 3 and b['trigger']['survival'] < a['trigger']['survival']
    assert b['devil']['badData'] == 2 and b['sherlock']['badData'] == 2 and b['tally']['dataCaught'] == 3 and a['tally']['dataCaught'] == 0
    c = of.contribution(dirty, {}, {'wardenLog': [{'req': 0.4, 'allowed': 0.2}, {'req': 0.3, 'allowed': 0.3}]}, {'fills': 5, 'sends': 6, 'deltaMed': 1.2}, {'n': 4, 'won': 50, 'med': -1.0}, {'value': 1.3, 'putIn': 29.5})
    ag_ = c['agents']
    assert dict((x[0], x[1]) for x in ag_['tally'])['data errors caught'] == 3 and dict((x[0], x[1]) for x in ag_['trigger'])['entered on bad data'] == 3
    assert dict((x[0], x[1]) for x in ag_['warden'])['over-sizing prevented'] == 0.2 and dict((x[0], x[1]) for x in ag_['reaper'])['peak profit retained'] is None   # nothing closed yet → no number
    assert c['team']['phase'] == 'RECOVERY' and c['team']['toDouble'] == 57.7 and c['team']['drawdownPct'] == 95.6
    assert {'slippage saved', 'false data warnings', '$ per agent'} <= {x[0] for x in c['notMeasured']}                # said plainly, not estimated


def test_breakeven_is_a_milestone_and_only_real_equity_at_twice_the_put_in_makes_the_next_stage_eligible():
    paper10x = {'done': [{'at': i * 400, 'kind': 'enter', 'go': True, 'devil': 'agree', 'p5': 60.0, 'p15': 60.0, 'p60': 60.0, 'mint': f'm{i}', 'lean': 3} for i in range(40)]}
    assert ag.paper(paper10x)['x'] >= ag.PROVE_X and ag.GRADUATE_X == 2.0
    st = lambda v: {**paper10x, 'money': {'value': v, 'putIn': 29.5}}
    under = ag.stage(st(1.30))
    assert under['h'] == 5 and under['needBE'] and under['need2x'] and under['phase'] == 'RECOVERY'
    at_be = ag.stage(st(29.5))                                                                                          # value = PUT_IN: breakeven DOES NOT unlock the next stage
    assert at_be['h'] == 5 and at_be['conquered'] == [] and not at_be['needBE'] and at_be['need2x'] and at_be['phase'] == 'GROWTH'
    assert all(ag.stage(st(v))['h'] == 5 and ag.stage(st(v))['phase'] == 'GROWTH' for v in (29.51, 40.0, 58.99))        # anywhere between PUT_IN and 2× PUT_IN: still locked, growth mode
    done = ag.stage(st(59.0))                                                                                           # value ≥ 2× PUT_IN: eligible for the next stage under the existing rules
    assert done['h'] > 5 and 5 in done['conquered'] and ag.real_phase({'value': 59.0, 'putIn': 29.5}) | {} == {'known': True, 'putIn': 29.5, 'value': 59.0, 'phase': 'GRADUATED', 'breakeven': 29.5,
                                                                                                                 'double': 59.0, 'toBreakeven': 0.0, 'toDouble': 0.0, 'eligible': True, 'x': 2.0}
    # the real half does not replace the existing progression rules: 2× real equity with a paper desk that has NOT 10×'d stays at 5 min too
    assert ag.stage({'done': paper10x['done'][:3], 'money': {'value': 100.0, 'putIn': 29.5}})['h'] == 5
    # paper performance cannot unlock a real-money stage; the targets read ONLY the real card's value and put-in
    assert ag.stage(paper10x)['h'] == 5 and ag.stage({**paper10x, 'money': {}})['h'] == 5 and ag.stage({**paper10x, 'money': {'putIn': 29.5}})['h'] == 5
    assert ag.stage({**paper10x, 'money': {'value': 5.0, 'putIn': 29.5, 'paperValue': 900, 'takenUsd': 66.81, 'paidOut': 80, 'realizedGross': 400}})['h'] == 5
    r = ag.real_phase({'value': 1.30, 'putIn': 29.5})
    assert (r['phase'], r['breakeven'], r['double'], r['toBreakeven'], r['toDouble'], r['eligible']) == ('RECOVERY', 29.5, 59.0, 28.2, 57.7, False)
    m = of.mission({'value': 1.30, 'putIn': 29.5}, 9, under, 0, NOW, None, True)
    assert (m['phase'], m['breakevenTarget'], m['doubleTarget'], m['stage'], m['nextStage'], m['unlock'], m['locked']) == ('RECOVERY', 29.5, 59.0, 5, 'LOCKED', 'real equity ≥ $59.00', True)
    g = of.mission({'value': 31.0, 'putIn': 29.5}, 9, at_be, 0, NOW, None, False)
    assert g['phase'] == 'GROWTH' and g['locked'] and g['nextStage'] == 'LOCKED' and g['toBreakeven'] == 1.5 and g['toDouble'] == -28.0 and not g['underwater']
    assert of.mission({'value': 60.0, 'putIn': 29.5}, 9, done, 0, NOW)['nextStage'] == 'ELIGIBLE' and m['goal'] == list(of.TEAM_GOAL)
    assert ag.mission(1.30, 29.5, {'x': 50})['key'] == 'breakeven' and ag.mission(31.0, 29.5, {'x': 50})['key'] == 'double' and ag.mission(59.0, 29.5, {'x': 50})['key'] == 'tenx'
