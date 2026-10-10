"""🤖 THE AGENT DESK (pure, tested). Owner, 2026-10-09: "code your own agents to learn trading and trenching — 4 minimum: one tracks the
numbers, one knows why they moved, one knows exactly when to enter, one argues it's right or not; none can work without the others;
they start by conquering the 5 minute; they live in HQ, their own tab; they prove themselves on the creator's side only."

The four are ONE chain — each needs the one before it, and no call exists without all four:
  📊 TALLY     (tracker)   — reads every coin's numbers each pass and keeps its own 5-min tape: price, volume pace, buyers, pool, trades.
  🔍 SHERLOCK  (why)       — turns Tally's numbers into DRIVERS (buyers in charge, volume surge, pool drained, callers piling in …) and
                             weighs each by what that driver was really followed by over the next 5 minutes (learned, not hand-set).
  ⏱ TRIGGER   (timer)     — reads Sherlock's lean + Tally's numbers and calls ENTER / WAIT / SKIP for the next 5 minutes.
  ⚖ DEVIL     (critic)    — argues against every ENTER with the evidence (busted reads, wash, a drained pool, a launch minutes old, a
                             driver that has been LOSING lately, Trigger's own recent record). GO = Trigger says enter AND Devil can't
                             knock it down.
Every call is paper-recorded at its price and judged 5 minutes later (then 15 and 60). Each agent keeps its OWN scorecard; the team's GO
calls run a $20 paper desk ($5 a ticket, out at 5 minutes). The 5-minute stage is "conquered" only with ≥ PROVE_N judged GO calls, a
positive median and ≥ PROVE_WIN % won — then the 15-minute stage opens. A record, never a promise: nothing here can promise not to lose.
"""

AGENTS = (('tally', '📊', 'Tally', 'tracks the numbers'), ('sherlock', '🔍', 'Sherlock', 'knows why they moved'),
          ('trigger', '⏱', 'Trigger', 'knows when to enter'), ('devil', '⚖', 'Devil', 'argues it is right — or not'))
STAGES = (5, 15, 60)            # minutes: conquer 5 first, then 15, then the hour
SERIES_N = 15                   # points kept per coin (one a pass, ~1 min apart)
SERIES_COINS = 160
KEEP_DONE = 3000
PROVE_N, PROVE_WIN = 30, 55.0
DESK_START, DESK_TICKET = 20.0, 5.0
DRIVER_MIN_N = 8                # a driver's learned weight counts from this many judged calls
PRIOR = {'buyers': 1.0, 'sellers': -1.5, 'surge': 1.0, 'quiet': -0.5, 'whale_in': 1.5, 'whale_out': -2.0, 'callers': 0.5,
         'drain': -3.0, 'fresh': -0.5, 'wash': -2.0, 'pullback': 1.0, 'chasing': -1.5, 'falling': -1.5, 'holders_up': 0.5}
WORDS = {'buyers': 'buyers in charge', 'sellers': 'sellers in charge', 'surge': 'volume surging vs the hour', 'quiet': 'volume drying up',
         'whale_in': 'big buys on the tape', 'whale_out': 'big sells on the tape', 'callers': 'Pump callers piling in', 'drain': 'pool draining',
         'fresh': 'launched under an hour ago', 'wash': 'wash-traded volume', 'pullback': 'pulled back after a run', 'chasing': 'already spiking (5 min)',
         'falling': 'falling right now', 'holders_up': 'holders arriving'}
BUSTED = {'BOND RUN', 'EARLY RUSH', 'RUG BAIT', 'DUMPING', 'SLOW CURVE', 'BREAKOUT', 'FALLING KNIFE', 'WASH TRADED', 'BLOW-OFF TOP', 'DEAD DIP', 'TREND DOWN'}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _med(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


# ── 📊 TALLY ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def tally(state, rows, now):
    """Note this pass's numbers per coin (its own tape) → (series, nums{mint: numbers Tally reports})."""
    ser = {m: list(v) for m, v in ((state or {}).get('series') or {}).items()}
    nums = {}
    for r in rows or []:
        m, px = r.get('mint'), _f(r.get('price'))
        if not m or px <= 0:
            continue
        pt = {'t': now, 'px': px, 'v5': _f(r.get('vol5m')), 'v1': _f(r.get('vol1h')), 'b': r.get('buyShare'), 'liq': _f(r.get('liq')), 'h': r.get('holders')}
        s = (ser.get(m) or [])[-(SERIES_N - 1):] + [pt]
        ser[m] = s
        old = next((p for p in s if now - p['t'] >= 240), s[0])        # ~5 minutes back on Tally's own tape (else the oldest point)
        d5 = (px / old['px'] - 1) * 100 if old is not s[-1] and old['px'] > 0 else _f(r.get('chg5m'))
        pace = pt['v5'] * 12 / pt['v1'] if pt['v1'] > 0 else None
        liq0 = next((p['liq'] for p in s if p['liq'] > 0), 0.0)
        nums[m] = {'d5': round(d5, 2), 'c1': r.get('chg1h'), 'pace': None if pace is None else round(pace, 2), 'buy': r.get('buyShare'),
                   'liq': pt['liq'], 'liqD': round((pt['liq'] / liq0 - 1) * 100, 1) if liq0 > 0 and pt['liq'] > 0 else None,
                   'holdD': (_f(pt['h']) - _f(s[0].get('h'))) if pt['h'] is not None and s[0].get('h') is not None else None,
                   'age': r.get('ageH'), 'pts': len(s)}
    if len(ser) > SERIES_COINS:   # keep the most recently seen coins
        for m in sorted(ser, key=lambda k: ser[k][-1]['t'])[:len(ser) - SERIES_COINS]:
            ser.pop(m)
    return ser, nums


# ── 🔍 SHERLOCK ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def drivers(n, row):
    """What is moving this coin, from Tally's numbers + the coin's read / tape / callers → [driver keys]."""
    n, row = n or {}, row or {}
    out = []
    b = n.get('buy')
    if b is not None and _f(b) >= 60:
        out.append('buyers')
    if b is not None and _f(b) <= 45:
        out.append('sellers')
    if n.get('pace') is not None:
        out.append('surge' if n['pace'] >= 2 else 'quiet' if n['pace'] < 0.5 else None)
    tape = (row.get('tape') or {}).get('read') if isinstance(row.get('tape'), dict) else row.get('tape')
    if tape in ('burst', 'absorb'):
        out.append('whale_in')
    if tape in ('dump', 'climax'):
        out.append('whale_out')
    if _f((row.get('pc') or {}).get('callers')) >= 2:
        out.append('callers')
    if n.get('liqD') is not None and n['liqD'] <= -15:
        out.append('drain')
    if n.get('age') is not None and _f(n['age']) < 1:
        out.append('fresh')
    if ((row.get('tv') or {}).get('call') or [None, None])[1] == 'WASH TRADED':
        out.append('wash')
    c1, d5 = n.get('c1'), _f(n.get('d5'))
    if c1 is not None and _f(c1) >= 20 and -8 <= d5 <= -1:
        out.append('pullback')
    if d5 > 8:
        out.append('chasing')
    if d5 < -6:
        out.append('falling')
    if n.get('holdD') is not None and _f(n['holdD']) >= 20:
        out.append('holders_up')
    return [d for d in out if d]


def weights(learned):
    """Each driver's weight: what it was REALLY followed by over 5 minutes (median %) once judged DRIVER_MIN_N times, else its prior."""
    w = dict(PRIOR)
    for k, v in ((learned or {}).get('drivers') or {}).items():
        if int(v.get('n') or 0) >= DRIVER_MIN_N and v.get('med') is not None:
            w[k] = _f(v['med'])
    return w


def sherlock(n, row, learned):
    """→ {drivers: [(key, weight, words)], lean} — why it moved, strongest first."""
    w = weights(learned)
    ds = sorted(((k, round(w.get(k, 0.0), 2), WORDS.get(k, k)) for k in drivers(n, row)), key=lambda x: -abs(x[1]))
    return {'drivers': ds, 'lean': round(sum(x[1] for x in ds), 2)}


# ── ⏱ TRIGGER ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def trigger(n, why, row, learned):
    """ENTER / WAIT / SKIP for the next 5 minutes, with the reason. Its bar (`bar`, default 1.5) moves with its own record."""
    n, row = n or {}, row or {}
    bar = _f((learned or {}).get('bar') or 1.5)
    if row.get('safe') is False:
        return 'skip', 'failed the holder safety scan'
    if 0 < _f(n.get('liq')) < 20_000:
        return 'skip', f"pool ${_f(n.get('liq')) / 1000:.0f}K — pullable"
    d5 = _f(n.get('d5'))
    if d5 > 15:
        return 'skip', f'+{d5:.0f}% in 5 min — that is the top'
    if d5 < -8:
        return 'skip', f'{d5:.0f}% in 5 min — falling'
    if int(n.get('pts') or 0) < 3:
        return 'wait', 'Tally has under 3 readings of this coin yet'
    if why['lean'] >= bar and (n.get('buy') is None or _f(n['buy']) >= 55):
        return 'enter', f"lean {why['lean']:+.1f} ≥ bar {bar:.1f}: " + ', '.join(d[2] for d in why['drivers'][:2])
    return 'wait', f"lean {why['lean']:+.1f} under the bar {bar:.1f}"


# ── ⚖ DEVIL ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def devil(call, n, why, row, learned):
    """Argue against an ENTER. → (verdict 'agree' | 'object' | '—', the strongest argument). Its learned distrust: any driver of this call
    whose own 5-min record is negative, and Trigger's own record when it is losing."""
    if call != 'enter':
        return '—', ''
    n, row = n or {}, row or {}
    args = []
    rd = ((row.get('tv') or {}).get('call') or [None, None])[1]
    if rd in BUSTED:
        args.append(f'its read is {rd} — a busted call on its own record')
    if _f((row.get('tv') or {}).get('rug')) >= 50:
        args.append(f"rug meter {_f(row['tv']['rug']):.0f}")
    if n.get('c1') is not None and _f(n['c1']) > 150:
        args.append(f"already +{_f(n['c1']):.0f}% on the hour — it ran")
    if n.get('age') is not None and _f(n['age']) < 0.25:
        args.append('under 15 minutes old')
    if row.get('safe') is not True:
        args.append('holders never scanned')
    bad = [d for d in why['drivers'] if d[1] < 0]
    if bad:
        args.append('against it: ' + ', '.join(d[2] for d in bad[:2]))
    learned_d = (learned or {}).get('drivers') or {}
    for k, _w, words in why['drivers']:
        v = learned_d.get(k) or {}
        if int(v.get('n') or 0) >= DRIVER_MIN_N and _f(v.get('med')) < 0 and _f(_w) > 0:
            args.append(f"'{words}' has been followed by {_f(v['med']):+.1f}% lately")
    tr = ((learned or {}).get('cards') or {}).get('trigger') or {}
    if int(tr.get('n') or 0) >= 15 and _f(tr.get('med')) < 0:
        args.append(f"Trigger's last {tr['n']} calls: {_f(tr['med']):+.1f}% typical")
    return ('object', args[0]) if args else ('agree', 'no evidence against it')


# ── the chain ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def desk(state, rows, now):
    """One pass of all four, in order. → (new state, table rows for the screen). Each coin's line carries every agent's word."""
    st = dict(state or {})
    learned = st.get('learned') or {}
    ser, nums = tally(st, rows, now)
    st['series'] = ser
    table = []
    for r in rows or []:
        m = r.get('mint')
        if m not in nums:
            continue
        n = nums[m]
        why = sherlock(n, r, learned)
        call, reason = trigger(n, why, r, learned)
        verdict, arg = devil(call, n, why, r, learned)
        table.append({'mint': m, 'symbol': r.get('symbol'), 'pair': r.get('pairAddress'), 'px': _f(r.get('price')), 'nums': n, 'why': why,
                      'trigger': [call, reason], 'devil': [verdict, arg], 'go': call == 'enter' and verdict == 'agree'})
    table.sort(key=lambda x: (not x['go'], x['trigger'][0] != 'enter', -x['why']['lean']))
    return st, table


def record(state, table, now, controls=3):
    """Note every ENTER (agreed or objected) once at its price, plus a few WAIT coins as the control group; Tally's 5-min direction call
    rides along (does the move keep going?). A coin is not noted again while open or 30 min after its last call."""
    st = dict(state or {})
    opened, done = dict(st.get('open') or {}), list(st.get('done') or [])
    recent = {d['mint'] for d in done if now - _f(d.get('at')) < 1800}
    waits = 0
    for x in table:
        m = x['mint']
        if m in opened or m in recent or x['px'] <= 0:
            continue
        kind = 'enter' if x['trigger'][0] == 'enter' else ('wait' if x['trigger'][0] == 'wait' and waits < controls else None)
        if not kind:
            continue
        waits += kind == 'wait'
        opened[m] = {'px': x['px'], 'at': now, 'sym': x['symbol'], 'kind': kind, 'go': x['go'], 'devil': x['devil'][0],
                     'drivers': [d[0] for d in x['why']['drivers']], 'lean': x['why']['lean'], 'tallyUp': _f(x['nums'].get('d5')) > 0}
    st['open'], st['done'] = opened, done[-KEEP_DONE:]
    return st


def settle(state, price_of, now):
    """Judge open calls at 5 / 15 / 60 minutes (no price at 60 = −100%: it vanished). A call is done after 60 minutes."""
    st = dict(state or {})
    opened, done = dict(st.get('open') or {}), list(st.get('done') or [])
    for m, o in list(opened.items()):
        age = (now - _f(o['at'])) / 60
        px = _f(price_of(m))
        for h in STAGES:
            key = f'p{h}'
            if key not in o and age >= h:
                o[key] = round((px / _f(o['px']) - 1) * 100, 2) if px > 0 and _f(o['px']) > 0 else (-100.0 if h == 60 else None)
        opened[m] = o
        if age >= STAGES[-1]:
            done.append({**o, 'mint': m, 'at': o['at'], 'doneAt': now})
            opened.pop(m)
    st['open'], st['done'] = opened, done[-KEEP_DONE:]
    return st


def _judged(state, h):
    k = f'p{h}'
    return [d for d in list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or []) if d.get(k) is not None]


def _card(ps, right):
    n = len(ps)
    return {'n': n, 'med': None if not n else round(_med(ps), 2), 'won': None if not n else round(sum(1 for p in ps if p > 0) / n * 100),
            'right': None if not right else round(sum(right) / len(right) * 100)}


def learn(state, h=5):
    """Every agent's scorecard on the `h`-minute result + Sherlock's learned driver weights + Trigger's bar. Pure."""
    js = _judged(state, h)
    k = f'p{h}'
    drv = {}
    for d in js:
        for x in d.get('drivers') or []:
            drv.setdefault(x, []).append(_f(d[k]))
    drivers_ = {x: {'n': len(v), 'med': round(_med(v), 2)} for x, v in drv.items()}
    enters = [d for d in js if d.get('kind') == 'enter']
    gos = [d for d in enters if d.get('go')]
    objected = [d for d in enters if d.get('devil') == 'object']
    agreed = [d for d in enters if d.get('devil') == 'agree']
    cards = {
        'tally': _card([_f(d[k]) for d in js], [(_f(d[k]) > 0) == bool(d.get('tallyUp')) for d in js]),          # the move keeps going?
        'sherlock': _card([_f(d[k]) for d in js if d.get('lean')], [(_f(d[k]) > 0) == (_f(d.get('lean')) > 0) for d in js if d.get('lean')]),
        'trigger': _card([_f(d[k]) for d in enters], [_f(d[k]) > 0 for d in enters]),
        'devil': _card([_f(d[k]) for d in objected], [_f(d[k]) <= 0 for d in objected] + [_f(d[k]) > 0 for d in agreed]),
        'team': _card([_f(d[k]) for d in gos], [_f(d[k]) > 0 for d in gos]),
        'control': _card([_f(d[k]) for d in js if d.get('kind') == 'wait'], None),
    }
    t = cards['trigger']
    bar = 1.5 if not t['n'] or t['n'] < 15 else (2.5 if _f(t['med']) < 0 else 1.0 if _f(t['won']) >= 60 else 1.5)   # losing → pickier
    return {'drivers': drivers_, 'cards': cards, 'bar': bar, 'h': h}


def stage(state):
    """The timeframe the desk is on: 5 until it is conquered (team GO ≥ PROVE_N judged, median > 0, ≥ PROVE_WIN % won), then 15, then 60."""
    for h in STAGES:
        c = learn(state, h)['cards']['team']
        if not (int(c['n'] or 0) >= PROVE_N and _f(c['med']) > 0 and _f(c['won']) >= PROVE_WIN):
            return {'h': h, 'conquered': [x for x in STAGES if x < h], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN}
    return {'h': STAGES[-1], 'conquered': list(STAGES), 'team': learn(state, STAGES[-1])['cards']['team'], 'needN': PROVE_N, 'needWin': PROVE_WIN}


def paper(state):
    """The team's $20 paper desk: every GO call is a $5 ticket bought at its price and sold at its 5-minute price (fees not modelled —
    a 5-min scalp on a launch coin costs real slippage; read it as an upper bound)."""
    gos = sorted((d for d in _judged(state, 5) if d.get('go')), key=lambda d: _f(d.get('at')))
    cash, trail = DESK_START, []
    for d in gos:
        pnl = DESK_TICKET * _f(d['p5']) / 100
        cash = round(cash + pnl, 4)
        trail.append({'at': d['at'], 'sym': d.get('sym'), 'pct': d['p5'], 'usd': round(pnl, 4), 'book': cash})
    return {'start': DESK_START, 'now': cash, 'trades': len(gos), 'trail': trail[-20:]}


def view(state, table, feed=False):
    """What the HQ tab shows: the four agents with their scorecards, the live table (every agent's word per coin), the desk, the stage."""
    lr = learn(state, 5)
    st_ = stage(state)
    names = {a[0]: a for a in AGENTS}
    cards = [{'key': k, 'icon': names[k][1], 'name': names[k][2], 'job': names[k][3], **lr['cards'][k]} for k in ('tally', 'sherlock', 'trigger', 'devil')]
    proven = 5 in st_['conquered']
    return {'agents': cards, 'team': lr['cards']['team'], 'control': lr['cards']['control'], 'bar': lr['bar'], 'stage': st_, 'proven5': proven,
            'drivers': sorted(({'key': k, 'words': WORDS.get(k, k), **v} for k, v in lr['drivers'].items()), key=lambda x: -_f(x['med'])),
            'table': table[:24], 'desk': paper(state), 'open': len((state or {}).get('open') or {}), 'feed': bool(feed and proven), 'feedAsked': bool(feed)}
