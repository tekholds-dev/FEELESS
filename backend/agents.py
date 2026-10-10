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

import trench_mind as _tm

AGENTS = (('tally', '📊', 'Tally', 'tracks the numbers'), ('sherlock', '🔍', 'Sherlock', 'knows why they moved'),
          ('trigger', '⏱', 'Trigger', 'knows when to enter'), ('devil', '⚖', 'Devil', 'argues it is right — or not'))
STAGES = (5, 15, 60)            # minutes: conquer 5 first, then 15, then the hour
SERIES_N = 15                   # points kept per coin (one a pass, ~1 min apart)
SERIES_COINS = 160
KEEP_DONE = 3000
PROVE_N, PROVE_WIN = 30, 55.0
PROVE_X = 10.0                  # 🎯 owner, 2026-10-09: "they should trench and 10x what they start with to pass 5 min"
DESK_START, DESK_PCT, DESK_BUST = 20.0, 25.0, 1.0   # paper desk: each GO = 25% of the desk (compounds); under $1 = busted → starts over
FEED_KEEP = 80                  # live thoughts kept
DRIVER_MIN_N = 8                # a driver's learned weight counts from this many judged calls
PRIOR = {'buyers': 1.0, 'sellers': -1.5, 'surge': 1.0, 'quiet': -0.5, 'whale_in': 1.5, 'whale_out': -2.0, 'callers': 0.5,
         'drain': -3.0, 'fresh': -0.5, 'wash': -2.0, 'pullback': 1.0, 'chasing': -1.5, 'falling': -1.5, 'holders_up': 0.5}
WORDS = {'buyers': 'buyers in charge', 'sellers': 'sellers in charge', 'surge': 'volume surging vs the hour', 'quiet': 'volume drying up',
         'whale_in': 'big buys on the tape', 'whale_out': 'big sells on the tape', 'callers': 'Pump callers piling in', 'drain': 'pool draining',
         'fresh': 'launched under an hour ago', 'wash': 'wash-traded volume', 'pullback': 'pulled back after a run', 'chasing': 'already spiking (5 min)',
         'falling': 'falling right now', 'holders_up': 'holders arriving', 'narr_hot': 'riding a hot narrative', 'crowd_real': 'real callers on it',
         'swarm': 'botted callout swarm', 'botted': 'botted launch', 'tug': 'dip tuggers catching a dump'}


def word(k):
    """Words for a driver key — a learned narrative driver reads as its label ('narr:ai' → 'the 🤖 AI narrative')."""
    if str(k).startswith('narr:'):
        lab = (_tm.NARRATIVES.get(k[5:]) or (k[5:],))[0]
        return f'the {lab} narrative'
    return WORDS.get(k, k)
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
    out += list(((row.get('mind') or {}).get('drivers')) or [])   # 🧠 the human read: narrative, crowd vs swarm, botted, dip tuggers
    return [d for d in dict.fromkeys(out) if d]


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
    ds = sorted(((k, round(w.get(k, 0.0), 2), word(k)) for k in drivers(n, row)), key=lambda x: -abs(x[1]))
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
    mind = row.get('mind') or {}
    if (mind.get('crowd') or {}).get('swarm'):
        args.append(f"the callers are a bot swarm ({round(_f(mind['crowd'].get('swarmShare')) * 100)}% the same line)")
    if _f((mind.get('bots') or (0, []))[0]) >= 40:
        args.append('botted launch: ' + '; '.join((mind['bots'][1] or [])[:2]))
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
        rd = r.get('mind') or _tm.read(r)
        table.append({'mint': m, 'symbol': r.get('symbol'), 'pair': r.get('pairAddress'), 'px': _f(r.get('price')), 'nums': n, 'why': why,
                      'trigger': [call, reason], 'devil': [verdict, arg], 'go': call == 'enter' and verdict == 'agree',
                      'mind': {'narr': rd['narr'][1], 'hot': rd['narr'][2], 'callers': rd['crowd']['callers'], 'swarm': rd['crowd']['swarm'],
                               'slang': rd['crowd']['slang'], 'bots': rd['bots'][0], 'tug': rd['tug'][0]},
                      'analysis': _tm.analysis(r.get('symbol'), rd, n, call, verdict, arg)})
    table.sort(key=lambda x: (not x['go'], x['trigger'][0] != 'enter', -x['why']['lean']))
    st['feed'] = (list(st.get('feed') or []) + thoughts(table, now))[-FEED_KEEP:]
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
        o = dict(o)   # never mutate the caller's copy (the 5-min verdict feed compares before / after)
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
        if h == 5 and not (paper(state)['x'] >= PROVE_X and int(c['n'] or 0) >= PROVE_N):   # 5 min: the trench desk must 10× in one run
            return {'h': h, 'conquered': [], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN, 'needX': PROVE_X}
        if h != 5 and not (int(c['n'] or 0) >= PROVE_N and _f(c['med']) > 0 and _f(c['won']) >= PROVE_WIN):
            return {'h': h, 'conquered': [x for x in STAGES if x < h], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN}
    return {'h': STAGES[-1], 'conquered': list(STAGES), 'team': learn(state, STAGES[-1])['cards']['team'], 'needN': PROVE_N, 'needWin': PROVE_WIN}


def paper(state):
    """The team's paper desk, TRENCH style: every GO call puts 25% of the desk in at its price and sells at its 5-minute price, so wins
    compound (a 10× needs a real run of good calls). Under $1 the desk is BUSTED: it starts over at $20 and the bust is counted. Fees and
    slippage are not modelled — read it as an upper bound. → {start, now, x (this run), best (best run ×), busts, trades, trail}"""
    gos = sorted((d for d in _judged(state, 5) if d.get('go')), key=lambda d: _f(d.get('at')))
    cash, best, busts, trail, run_trades = DESK_START, 1.0, 0, [], 0
    for d in gos:
        stake = cash * DESK_PCT / 100
        pnl = stake * max(-100.0, _f(d['p5'])) / 100
        cash = round(cash + pnl, 4); run_trades += 1
        best = max(best, cash / DESK_START)
        trail.append({'at': d['at'], 'sym': d.get('sym'), 'pct': d['p5'], 'usd': round(pnl, 4), 'book': cash})
        if cash < DESK_BUST:
            busts += 1; cash = DESK_START; run_trades = 0
            trail.append({'at': d['at'], 'sym': '💥 BUST', 'pct': None, 'usd': 0.0, 'book': cash})
    return {'start': DESK_START, 'now': cash, 'x': round(cash / DESK_START, 3), 'best': round(best, 2), 'busts': busts, 'trades': len(gos),
            'runTrades': run_trades, 'trail': trail[-20:]}


def road(state, real=None):
    """🛣 How close the desk is to REAL money (owner: "how close it is to real money"): step 1 = the 5-minute paper desk reaches 10× in one
    run with ≥ PROVE_N judged GO calls; step 2 = the REAL-money test on the owner's Fuse card (their GO coins in the card's rush, judged
    on the card's own ledger: ≥ 10 closed pieces, typical result > 0); then 15 min, then 60. `real` = the agents' pieces on the real card."""
    pp, team = paper(state), learn(state, 5)['cards']['team']
    x_prog = min(1.0, max(0.0, __import__('math').log(max(pp['x'], 1e-9)) / __import__('math').log(PROVE_X))) if pp['x'] > 1 else 0.0
    n_prog = min(1.0, int(team['n'] or 0) / PROVE_N)
    paper_done = pp['x'] >= PROVE_X and int(team['n'] or 0) >= PROVE_N
    r = real or {}
    real_done = int(r.get('n') or 0) >= 10 and _f(r.get('med')) > 0
    pct = round((min(x_prog, n_prog) * 0.5 + (0.5 * min(1.0, int(r.get('n') or 0) / 10) * (1 if _f(r.get('med')) > 0 else 0.5) if paper_done else 0.0)) * 100)
    return {'pct': 100 if paper_done and real_done else pct, 'paper': {'done': paper_done, 'x': pp['x'], 'need': PROVE_X, 'n': int(team['n'] or 0), 'needN': PROVE_N},
            'real': {'open': paper_done, 'done': real_done, 'n': int(r.get('n') or 0), 'med': r.get('med'), 'won': r.get('won'), 'needN': 10}}


def thoughts(table, now, top=4):
    """🗯 What the four said this pass, in their own words and their own humor, for the coins worth a line (every ENTER, else the strongest
    leans) — plus the desk's written analysis of each."""
    pick = [x for x in table if x['trigger'][0] == 'enter'][:top] or sorted(table, key=lambda x: -abs(x['why']['lean']))[:2]
    out = []
    for x in pick:
        n, sym = x['nums'], x['symbol']
        j = (x.get('analysis') or {}).get('jokes') or {}
        joke = lambda k: f" — “{j[k]}”" if j.get(k) else ''
        out.append({'at': now, 'who': 'tally', 'sym': sym, 'text': f"${sym} {n['d5']:+.1f}% in 5 min" + (f" · pace {n['pace']}×" if n.get('pace') is not None else '')
                    + (f" · {round(_f(n['buy']))}% buys" if n.get('buy') is not None else '') + (f" · pool {n['liqD']:+.0f}%" if n.get('liqD') else '') + joke('tally')})
        ds = x['why']['drivers']
        out.append({'at': now, 'who': 'sherlock', 'sym': sym, 'text': ('; '.join(f"{d[2]} ({d[1]:+.1f})" for d in ds[:3]) if ds else 'nothing is moving it') + f" → lean {x['why']['lean']:+.1f}" + joke('sherlock')})
        out.append({'at': now, 'who': 'trigger', 'sym': sym, 'text': f"{x['trigger'][0].upper()} — {x['trigger'][1]}" + joke('trigger')})
        if x['devil'][0] != '—':
            out.append({'at': now, 'who': 'devil', 'sym': sym, 'text': f"{'agrees' if x['devil'][0] == 'agree' else 'OBJECTS'} — {x['devil'][1]}" + (' → 🟢 GO' if x['go'] else ' → ✋ no trade') + joke('devil')})
        if (x.get('analysis') or {}).get('text'):
            out.append({'at': now, 'who': 'desk', 'sym': sym, 'text': '✍ ' + x['analysis']['text']})
    return out


def results(before, after, now):
    """🧾 Calls that just got their 5-minute verdict (in `after`, not judged in `before`) → feed lines."""
    was = {m for m, o in ((before or {}).get('open') or {}).items() if o.get('p5') is not None}
    out = []
    for m, o in ((after or {}).get('open') or {}).items():
        if o.get('p5') is not None and m not in was and o.get('kind') == 'enter':
            ok = _f(o['p5']) > 0
            out.append({'at': now, 'who': 'desk', 'sym': o.get('sym'), 'text': f"{'✅' if ok else '❌'} ${o.get('sym')} {'GO' if o.get('go') else 'objected'} → {_f(o['p5']):+.1f}% after 5 min"
                        + ('' if o.get('go') else (' (Devil was right)' if not ok else ' (Devil was wrong)'))})
    return out


def view(state, table, feed=False, real=None, mind=None):
    """What the HQ tab shows: the four agents with their scorecards, the live table (every agent's word per coin), the desk, the stage."""
    lr = learn(state, 5)
    st_ = stage(state)
    names = {a[0]: a for a in AGENTS}
    cards = [{'key': k, 'icon': names[k][1], 'name': names[k][2], 'job': names[k][3], **lr['cards'][k]} for k in ('tally', 'sherlock', 'trigger', 'devil')]
    proven = 5 in st_['conquered']
    return {'agents': cards, 'team': lr['cards']['team'], 'control': lr['cards']['control'], 'bar': lr['bar'], 'stage': st_, 'proven5': proven,
            'drivers': sorted(({'key': k, 'words': word(k), **v} for k, v in lr['drivers'].items()), key=lambda x: -_f(x['med'])),
            'table': table[:24], 'desk': paper(state), 'open': len((state or {}).get('open') or {}), 'feed': bool(feed and proven), 'feedAsked': bool(feed),
            'road': road(state, real), 'thoughts': list(reversed(((state or {}).get('feed') or [])[-40:])), 'real': real or {}, 'mind': mind or {}}
