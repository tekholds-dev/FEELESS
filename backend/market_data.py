"""🧪 MARKET-DATA TRUTH for the office — pure, deterministic, tested (`tests/test_market_data.py`).

A chart that RENDERED is not evidence. Before any desk may read structure from a coin's rows, Tally validates them here:

  quality(rows, now, ohlc, src, meta, liq, flow) → {state, conf 0–100, checks, fails, why, readOk, structOk, enterOk, risk, prov}

`rows` = [t, o, h, l, c, v] exactly as they were fetched (nothing dropped first). `meta` = what the fetcher knows about them
(provider, source words, tick count, the board's 5-min / 1-hour volume, how old the liquidity reading is). `meta` None = a bare
structure read (tests, a helper): the row checks still run, the context checks (volume source, liquidity) are "not supplied".

WHAT THE ROWS REALLY ARE (2026-10-10, read from the candles service on this machine):
  · "candles" = the candles service's 1-minute bars: the provider's price history (carries a volume figure per bar) sharpened with
    prices FEELESS recorded itself. A bar built only from recorded prices has NO volume figure (0.0 = not measured, not "no trades").
  · "tape"    = Tally's own readings, one board price a pass: closes only. Highs / lows are not measured. It is RECONSTRUCTED.
So per-candle volume is real only on the bars that carry it; the 5-min / 1-hour totals come from the launch board; trade counts
come only from the 90-second trade tape, and only for coins whose tape the service already holds. Each is labelled as what it is.
"""
import math

WINDOW = 30          # the rows a chart snapshot reads
MIN_BARS = 6
STALE_CANDLE_SEC = 240   # a 1-minute bar stream whose newest bar STARTED over 4 min ago
STALE_TAPE_SEC = 150
STALE_LIQ_SEC = 150
FUTURE_SEC = 120
GAP_JUMP = 0.5       # an open more than 50% away from the close before it
PING_MOVE, PING_BACK, PING_MIN, PING_SHARE = 0.02, 0.003, 6, 0.4   # ≥ 2% candles that land back on the price of two bars ago, 6+ times, ≥ 40% of the window
REPEAT_RUN = 3       # the same non-flat O/H/L/C this many times in a row
REPEAT_RANGE_MIN, REPEAT_RANGE_SHARE, REPEAT_RANGE_PCT = 5, 0.3, 0.01
FLAT_SPARSE, FLAT_CAUTION = 0.5, 0.25
VOL_REAL = 0.8       # share of moving bars that must carry a volume figure for per-candle volume to be called REAL
TRUSTED_MIN = 80

STATES = ('TRUSTED', 'USABLE_WITH_CAUTION', 'SPARSE', 'STALE', 'INCONSISTENT', 'MALFORMED', 'NO_REAL_CANDLES', 'NO_VOLUME', 'NO_LIQUIDITY', 'UNTRUSTED')
READ_FAIL = ('MALFORMED', 'INCONSISTENT', 'STALE', 'UNTRUSTED')    # an INTEGRITY failure: no desk may infer structure from these rows
STRUCT_FAIL = READ_FAIL + ('SPARSE',)                              # … and an existing position's thesis is not reviewed against them
ENTER_OK = ('TRUSTED', 'USABLE_WITH_CAUTION')                      # the only states a chart-based ENTER may stand on
CAP = {'UNTRUSTED': 0, 'MALFORMED': 5, 'INCONSISTENT': 20, 'STALE': 30, 'SPARSE': 40, 'NO_REAL_CANDLES': 45, 'NO_VOLUME': 60, 'NO_LIQUIDITY': 60}
RISK = {'TRUSTED': 1.0, 'USABLE_WITH_CAUTION': 1.0, 'NO_REAL_CANDLES': 0.5, 'NO_VOLUME': 0.5, 'NO_LIQUIDITY': 0.5, 'SPARSE': 0.5}   # everything else 0 — bad data never sizes a seat up
WORDS = {'TRUSTED': 'trusted', 'USABLE_WITH_CAUTION': 'usable with caution', 'SPARSE': 'sparse', 'STALE': 'stale', 'INCONSISTENT': 'inconsistent', 'MALFORMED': 'malformed',
         'NO_REAL_CANDLES': 'no real candles', 'NO_VOLUME': 'no volume', 'NO_LIQUIDITY': 'no liquidity', 'UNTRUSTED': 'untrusted'}
FLOW_CALC = 'buy % = buys ÷ (buys + sells) by transaction COUNT over the board\'s last hour'
TAPE_CALC = 'trade tape: $ bought vs $ sold in the last 90 seconds (parsed swaps)'


def _num(v):
    """→ a finite float, or None (None / NaN / inf / text are all "not a number" — never coerced to 0)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _eq(a, b):
    return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1e-300)


def quality(rows, now=0.0, ohlc=True, src='candles', meta=None, liq=None, flow=None):
    """📊 Tally's verdict on ONE coin's rows. Every line below is a deterministic check on the numbers as fetched."""
    judged = meta is not None and not meta.get('noCtx')   # noCtx = provenance only (a held coin off the board: no pool / volume reading exists to judge)
    m = meta or {}
    raw = [r for r in (rows or []) if r is not None][-WINDOW:]
    n = len(raw)
    checks, fails, soft = [], [], []

    def chk(cid, ok, word, hard=True):
        checks.append([cid, bool(ok), word])
        if not ok:
            (fails if hard else soft).append(cid)
        return ok

    derived = (not ohlc) or src != 'candles' or str(m.get('provider') or '').upper() == 'FEELESS'
    prov = {'dataSource': 'candles service (this machine)' if src == 'candles' else "Tally's own tape — one board price a pass",
            'candleSource': (m.get('source') or (f"{m['provider']} price history" if m.get('provider') else '1-minute OHLC rows')) if ohlc and src == 'candles' else 'RECONSTRUCTED FROM TAPE — closes only, highs / lows not measured',
            'provider': m.get('provider'), 'nCandles': n, 'realOhlc': bool(ohlc and src == 'candles' and not derived), 'synthetic': bool(derived), 'ticks': m.get('tickCount'),
            'firstTs': None, 'lastTs': None, 'ageSec': None}
    if not n:
        chk('rows', False, 'no rows at all', hard=False)   # nothing fetched = INSUFFICIENT (not a broken feed, not a bad coin)
        return _out('SPARSE', 0, checks, fails, soft, {**prov, **_ctx(m, judged, None, None, None, liq, flow, ohlc, src), 'label': 'NO DATA'})

    # ── numbers + OHLC invariants ───────────────────────────────────────────────────────────────────────────────────────────────
    bad_num = bad_ohlc = bad_vol = 0
    good = []
    for r in raw:
        vals = [_num(x) for x in (list(r) + [None] * 6)[:6]]
        t, o, h, l, c, v = vals
        if t is None or any(x is None or x <= 0 for x in (o, h, l, c)):
            bad_num += 1
            continue
        if not (h + 1e-12 * h >= max(o, c) and l - 1e-12 * l <= min(o, c) and h >= l):
            bad_ohlc += 1
        if len(r) > 5 and r[5] is not None and (v is None or v < 0):
            bad_vol += 1
        good.append((t, o, h, l, c, v if (len(r) > 5 and r[5] is not None) else None))
    chk('finite', not bad_num, f'{bad_num} of {n} rows have a price that is missing, zero, negative or not a number' if bad_num else 'every price is finite and positive')
    chk('ohlc', not bad_ohlc, f'{bad_ohlc} of {n} rows break high ≥ open/close ≥ low' if bad_ohlc else 'high ≥ open/close ≥ low on every row')
    chk('volume_valid', not bad_vol, f'{bad_vol} rows carry a negative or non-numeric volume' if bad_vol else 'no impossible volume figure')
    malformed = bool(bad_num or bad_ohlc or bad_vol)

    # ── timestamps ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ts = [g[0] for g in good]
    back = sum(1 for a, b in zip(ts, ts[1:]) if b < a)
    dup = sum(1 for a, b in zip(ts, ts[1:]) if b == a)
    deltas = sorted(b - a for a, b in zip(ts, ts[1:]) if b > a)
    step = 60.0 if ohlc and src == 'candles' else (deltas[len(deltas) // 2] if deltas else 60.0)
    gaps = sum(1 for d in deltas if d > 3 * max(step, 1.0))
    big_gap = max(deltas) if deltas else 0.0
    chk('order', not back, f'{back} rows are out of time order' if back else 'timestamps strictly ordered')
    if dup:
        chk('duplicates', False, f'{dup} duplicate timestamp(s)', hard=dup > 1)
    else:
        chk('duplicates', True, 'no duplicate timestamps')
    if gaps:
        chk('gaps', False, f'{gaps} gap(s) in the stream, the longest {big_gap / 60:.0f} min', hard=bool(ohlc and src == 'candles' and gaps > 2))
    else:
        chk('gaps', True, 'no unexplained gap')
    age = None
    if ts:
        prov.update(firstTs=ts[0], lastTs=ts[-1])
    stale = False
    if now and ts:
        age = round(now - ts[-1], 1)
        prov['ageSec'] = age
        chk('future', ts[-1] <= now + FUTURE_SEC, f'the newest row is {(ts[-1] - now) / 60:.0f} min in the FUTURE' if ts[-1] > now + FUTURE_SEC else 'no row from the future')
        lim = STALE_CANDLE_SEC if ohlc and src == 'candles' else STALE_TAPE_SEC
        stale = age > lim
        checks.append(['fresh', not stale, f'newest row {age:.0f}s old (limit {lim}s)'])
    else:
        checks.append(['fresh', True, 'freshness not judged (no clock handed in)'])

    # ── candle behaviour ────────────────────────────────────────────────────────────────────────────────────────────────────────
    g = len(good)
    flat = [(_eq(o, h) and _eq(h, l) and _eq(l, c)) for _, o, h, l, c, _ in good]
    flat_share = sum(flat) / g if g else 1.0
    run = best = 0
    for i in range(1, g):
        same = not flat[i] and all(_eq(good[i][k], good[i - 1][k]) for k in (1, 2, 3, 4))
        run = run + 1 if same else 0
        best = max(best, run)
    chk('repeat', best + 1 < REPEAT_RUN, f'the same O/H/L/C printed {best + 1} times in a row' if best + 1 >= REPEAT_RUN else 'no repeated identical candle')
    ranges = {}
    for i in range(g):
        if not flat[i] and good[i][2] / good[i][3] - 1 >= REPEAT_RANGE_PCT:   # tiny two-tick wiggles between two price sources are normal; a REPEATED big range is not
            key = (round(math.log(good[i][2]), 9), round(math.log(good[i][3]), 9))
            ranges[key] = ranges.get(key, 0) + 1
    top_r = max(ranges.values()) if ranges else 0
    chk('repeat_range', not (top_r >= REPEAT_RANGE_MIN and top_r >= REPEAT_RANGE_SHARE * g), f'{top_r} candles share the exact same high and low' if top_r >= REPEAT_RANGE_MIN and top_r >= REPEAT_RANGE_SHARE * g else 'ranges are not repeating')
    cl = [x[4] for x in good]
    ping = sum(1 for i in range(2, g) if abs(cl[i] / cl[i - 1] - 1) >= PING_MOVE and abs(cl[i] / cl[i - 2] - 1) <= PING_BACK)
    alt = ping >= PING_MIN and ping >= PING_SHARE * max(1, g - 2)
    chk('alternating', not alt, f'{ping} candles jump ≥ {PING_MOVE * 100:.0f}% and land back on the price of two bars before — two prices alternating, not a traded market' if alt else 'no full-range alternating candles')
    jumps = sum(1 for i in range(1, g) if abs(good[i][1] / good[i - 1][4] - 1) > GAP_JUMP) if ohlc else 0
    chk('jump', not jumps, f'{jumps} candle(s) open more than {GAP_JUMP * 100:.0f}% away from the close before' if jumps else 'opens follow the close before')
    inconsistent = any(c in fails for c in ('order', 'duplicates', 'gaps', 'future', 'repeat', 'repeat_range', 'alternating', 'jump'))
    chk('enough', g >= MIN_BARS, f'{g} usable rows — {MIN_BARS} are needed', hard=False)
    if g >= MIN_BARS:
        chk('active', flat_share <= FLAT_CAUTION, f'{round(flat_share * 100)}% of the rows are flat (no price change: nothing traded or nothing was read)', hard=False)

    # ── volume · trades · liquidity (context) ───────────────────────────────────────────────────────────────────────────────────
    moved = [i for i in range(g) if not flat[i]]
    with_v = [i for i in range(g) if good[i][5] is not None and good[i][5] > 0]
    need = sorted(set(moved) | set(with_v))
    cover = len(with_v) / len(need) if need else 0.0
    ctx = _ctx(m, judged, cover, len(with_v), g, liq, flow, ohlc, src)
    if ctx['volume'] == 'PARTIAL':
        chk('volume', False, ctx['volumeWord'], hard=False)
    elif ctx['volume'] == 'UNAVAILABLE' and judged:
        chk('volume', False, 'no measured volume from any source', hard=False)
    else:
        checks.append(['volume', True, ctx['volumeWord']])
    if flow is not None and int(_num(flow.get('n')) or 0) == 0 and g >= 3 and abs(cl[-1] / cl[-3] - 1) >= 0.02:
        chk('trades_vs_price', False, f'price moved {(cl[-1] / cl[-3] - 1) * 100:+.1f}% over 2 rows with 0 trades on the 90s tape', hard=False)
    if judged:
        checks.append(['liquidity', ctx['liquidity'] == 'REAL', ctx['liquidityWord']])
    if g < 15 and g >= MIN_BARS:
        soft.append('short')

    # ── the state: the first line that holds ────────────────────────────────────────────────────────────────────────────────────
    conf = 100 - sum({'active': 15, 'volume': 12, 'gaps': 10, 'duplicates': 10, 'trades_vs_price': 15, 'short': 10, 'enough': 40}.get(c, 0) for c in soft)
    if malformed:
        state = 'MALFORMED'
    elif inconsistent:
        state = 'INCONSISTENT'
    elif stale:
        state = 'STALE'
    elif derived:
        state = 'NO_REAL_CANDLES'
    elif g < MIN_BARS or flat_share > FLAT_SPARSE or m.get('partial') or (not ohlc and big_gap > 600):
        state = 'SPARSE'
    elif judged and ctx['volume'] == 'UNAVAILABLE':
        state = 'NO_VOLUME'
    elif judged and ctx['liquidity'] != 'REAL':
        state = 'NO_LIQUIDITY'
    elif conf < 40:
        state = 'UNTRUSTED'
    else:
        state = 'TRUSTED' if conf >= TRUSTED_MIN and not soft else 'USABLE_WITH_CAUTION'
    if derived and (g < MIN_BARS or flat_share > FLAT_SPARSE or big_gap > 600) and state == 'NO_REAL_CANDLES':
        state = 'SPARSE'   # a reconstructed line that is also thin is not even a line
    conf = max(0, min(conf, CAP.get(state, 100)))
    label = (f'{g} real 1m' if not derived else f'RECONSTRUCTED FROM TAPE · {g} readings' if src != 'candles' or not ohlc else f'{g} bars from recorded prices only')
    return _out(state, conf, checks, fails, soft, {**prov, **ctx, 'label': label, 'flatPct': round(flat_share * 100)})


def _ctx(m, judged, cover, with_v, g, liq, flow, ohlc, src):
    """Volume / trades / liquidity: what is measured, by whom, and what is not. Nothing here is estimated."""
    v5, v1 = _num(m.get('vol5m')), _num(m.get('vol1h'))
    board = (v5 is not None and v5 > 0) or (v1 is not None and v1 > 0)
    bars_real = bool(ohlc and src == 'candles' and cover is not None and cover >= VOL_REAL)
    if bars_real:
        vol, vword = 'REAL', f'per-candle volume on {with_v} of {g} rows'
    elif with_v or board:
        vol = 'PARTIAL'
        vword = (f'per-candle volume on {with_v} of {g} rows' if with_v else 'no per-candle volume (these bars are built from recorded prices)') + (f" · 5-min ${v5:,.0f} / 1-hour ${_num(v1) or 0:,.0f} from the launch board" if board else '')
    else:
        vol, vword = 'UNAVAILABLE', 'VOLUME UNAVAILABLE'
    vsrc = ' + '.join(x for x in ((f"candle bars ({m.get('provider') or 'provider'} history)" if with_v else None), ('launch board 5-min / 1-hour totals (DexScreener / Jupiter)' if board else None)) if x) or None
    nt = None if flow is None else int(_num(flow.get('n')) or 0)
    lq, la = _num(liq), _num(m.get('liqAge'))
    if not judged and lq is None:
        liqs, lword = 'NOT SUPPLIED', 'liquidity not supplied to this read'
    elif lq is None or lq <= 0:
        liqs, lword = 'UNKNOWN', 'no pool depth reading (never treated as a known $0 or a known deep pool)'
    elif la is not None and la > STALE_LIQ_SEC:
        liqs, lword = 'STALE', f'pool ${lq:,.0f} read {la:.0f}s ago'
    else:
        liqs, lword = 'REAL', f'pool ${lq:,.0f}' + (f' read {la:.0f}s ago' if la is not None else '')
    return {'volume': vol, 'volumeWord': vword, 'volumeSource': vsrc, 'realVolume': vol == 'REAL', 'volBars': with_v, 'vol5m': v5, 'vol1h': v1,
            'nTrades': nt, 'tradeSource': None if flow is None else 'candles service trade tape, last 90s (Helius / Solana RPC parsed swaps)', 'realFlow': flow is not None,
            'flowCalc': TAPE_CALC if flow is not None else FLOW_CALC if m.get('buy') is not None else None, 'txns1h': m.get('txns1h'),
            'liquidity': liqs, 'liquidityWord': lword, 'liquiditySource': 'launch board pool depth (DexScreener / Jupiter), on Tally\'s tape' if liqs in ('REAL', 'STALE') else None,
            'realLiquidity': liqs == 'REAL', 'liqUsd': lq if liqs in ('REAL', 'STALE') else None, 'liqAge': la}


def _out(state, conf, checks, fails, soft, prov):
    bad = [c for c in checks if not c[1]]
    why = bad[0][2] if bad else {'NO_REAL_CANDLES': 'reconstructed from the tape — not exchange candles'}.get(state, 'every integrity check passed')
    if state == 'NO_REAL_CANDLES':
        why = 'reconstructed — not real OHLC candles' + (f' ({bad[0][2]})' if bad else '')
    return {'state': state, 'conf': int(conf), 'checks': checks, 'fails': list(fails), 'soft': list(soft), 'why': why,
            'readOk': state not in READ_FAIL, 'structOk': state not in STRUCT_FAIL, 'enterOk': state in ENTER_OK, 'risk': RISK.get(state, 0.0), 'prov': prov}


def word(q):
    """One line for a trace: 'DATA TRUSTED 92%'."""
    return 'DATA NOT READ' if not q else f"DATA {str(q.get('state')).replace('_', ' ')} {int(q.get('conf') or 0)}%"


def compact(q):
    """What a table row / the page carries next to a chart (the checks stay in the shared snapshot)."""
    if not q:
        return None
    p = q.get('prov') or {}
    return {'state': q['state'], 'conf': q['conf'], 'why': q['why'], 'readOk': q['readOk'], 'enterOk': q['enterOk'], 'fails': q['fails'],
            'checks': [c for c in q['checks'] if not c[1]][:6], 'passed': sum(1 for c in q['checks'] if c[1]), 'of': len(q['checks']),
            **{k: p.get(k) for k in ('dataSource', 'candleSource', 'tradeSource', 'volumeSource', 'liquiditySource', 'firstTs', 'lastTs', 'ageSec', 'nCandles', 'nTrades', 'realOhlc',
                                     'realVolume', 'realFlow', 'realLiquidity', 'synthetic', 'label', 'volume', 'volumeWord', 'liquidity', 'liquidityWord', 'flowCalc', 'flatPct', 'provider', 'ticks')}}
