"""📡 THE SENSES — what the kernel KNOWS about a coin before anyone has an opinion (moved out of the old four-desk module, 2026-10-12).

Tally's own tape (price / volume pace / buyers / pool, one point a pass) · the shared chart snapshot (real 1-minute candles when fetched,
else the tape) · the human read (callers, narratives, bots) · the launch context · Devil's EVIDENCE about the coin itself.
`sense()` builds ONE row per mint with measurements and evidence ONLY — no ENTER / WAIT / SKIP, no agree / object, no GO. The kernel
(trench_kernel/brain.py) is the one that judges these rows; the paper desk (paper_desk.py) may annotate them afterwards for its own graded
practice calls, and nothing it writes is read back by the kernel. Pure (no I/O)."""
import time as _t

import chart_intel as _ci
import flow as _fl
import trench_mind as _tm

# 🕸 THE CRAWL: every place the desk pulls coins from each pass — each one is a driver `src:<key>` judged on its own record, so the agents
# learn which corner of the trench pays (owner: "access multiple ends to get info — only for trenching")
SOURCES = {'open': 'the open launch list', 'new': 'the newest launches (≤ 1h)', 'pulse': 'Pump pulse (PumpPortal live launches)', 'migr': 'Pump migrations (PumpPortal live)', 'outlet': 'callouts / fed runners / radar / runner board', 'ptrend': 'Pump trending', 'calls': 'Pump callouts',
           'pump': 'Pump live', 'movers': 'movers', 'volume': 'volume leaders', 'fed': 'fed runners (paired launches)', 'wave': 'narrative leaders',
           'exhale': 'cooling-off coins', 'procall': 'proven callers', 'prebreak': 'before-the-break setups', 'double': 'double signal', 'rpf': 'Real Project Finder (site + X + docs history)'}


SERIES_N = 15                   # points kept per coin (one a pass, ~1 min apart)


SERIES_COINS = 340                # ≥ the intake (office_edge.INTAKE_MAX 300) so nothing read this pass loses its tape


from fnum import nan_safe as _f


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
                   'age': r.get('ageH'), 'pts': len(s),
                   'v5': None if r.get('vol5m') is None else round(_f(r['vol5m']), 1), 'tx': r.get('txns1h')}   # 💀 5-min $ traded + trades in the hour (is anyone trading it NOW?)
    if len(ser) > SERIES_COINS:   # keep the most recently seen coins
        for m in sorted(ser, key=lambda k: ser[k][-1]['t'])[:len(ser) - SERIES_COINS]:
            ser.pop(m)
    return ser, nums


FIRST_KEEP, FIRST_SEC = 4000, 24 * 3600   # 🔎 first-seen stamps: newest 4,000 coins, ≤ 24h (the missed-winner lookback is 6h)


def first_seen(state, now):
    """{mint: {t, c, r, l}} = the first call the desk ever stamped on a coin, kept past the tape's eviction, bounded."""
    fs = {m: v for m, v in ((state or {}).get('first') or {}).items() if now - _f((v or {}).get('t')) <= FIRST_SEC}
    if len(fs) > FIRST_KEEP:
        fs = dict(sorted(fs.items(), key=lambda kv: -_f(kv[1].get('t')))[:FIRST_KEEP])
    return fs

# ── ⚖ DEVIL'S EVIDENCE ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
BUST_HARD = -50.0   # a read type whose coins typically lose half in an hour (its own settled record)
EVIDENCE = {'busted_read': 'the read type of this coin has a losing 1-hour record of its own', 'rug_meter': 'rug meter ≥ 50',
            'ran': 'already ran > +150% on the hour (a coin under 1h old: that is launch-to-now)', 'swarm': 'the callers are a bot swarm',
            'botted': 'botted launch', 'identity': 'an identity flag from the website / X research'}


def evidence(row, n, chart=None, mind=None, busted=None):
    """What speaks AGAINST this coin, from this pass's measurements only → [(id, words)]. It is evidence, not a verdict: the kernel's Devil
    grades each item (INFO · WARNING · STRONG_WARNING; only the hard wall is a no) and it lowers a rank — it never needs an ENTER call to
    exist, a lean, a burn list, a trial or anybody's losing streak (the old desk's Devil was gated by Trigger's bar and Sherlock's lean).
    `busted` = {read label: its typical 1-hour %} from the reads' own settled records (None = no record: nothing is claimed)."""
    r, n = row or {}, n or {}
    out = []
    tv = r.get('tv') or {}
    rd = (tv.get('call') or [None, None])[1]
    if busted and rd in busted:
        med = busted.get(rd) if isinstance(busted, dict) else None
        out.append(('busted_read', f"its read is {rd}" + (f" — coins with it typically {_f(med):+.0f}% in an hour" if med is not None else ' — a losing call on its own record')))
    if _f(tv.get('rug')) >= 50:
        out.append(('rug_meter', f"rug meter {_f(tv['rug']):.0f}"))
    if n.get('c1') is not None and _f(n['c1']) > 150 and not (n.get('age') is not None and _f(n['age']) < 1):
        out.append(('ran', f"already +{_f(n['c1']):.0f}% on the hour — it ran"))
    cc = (r.get('social') or {}).get('cross') or {}
    for fl in ((r.get('social') or {}).get('warnings') or [])[:2]:
        proof = f" [launch mint {str(cc.get('launchMint') or r.get('mint') or '?')[:8]}… · source shows {str(cc.get('sourceMint') or '?')[:8]}…]" if 'contract' in fl else ''
        out.append(('identity', f'identity: {fl}{proof}'))
    mind = mind or {}
    if (mind.get('crowd') or {}).get('swarm'):
        out.append(('swarm', f"the callers are a bot swarm ({round(_f(mind['crowd'].get('swarmShare')) * 100)}% the same line)"))
    if _f((mind.get('bots') or (0, []))[0]) >= 40:
        out.append(('botted', 'botted launch: ' + '; '.join((mind['bots'][1] or [])[:2])))
    for rule, text in (chart or {}).get('objs') or []:   # 📈 the chart read attacked on its own measurements (chart_intel.objections)
        out.append((rule, text))
    return out


VITAL_KEYS = ('mcap', 'ageH', 'liq', 'vol1h', 'buyShare', 'top10', 'bundledN', 'snipersN', 'insiders', 'dev', 'holders', 'safe', 'curve', 'curvePct', 'txns1h', 'holderSoft',
              'chg5m', 'chg1h', 'vol5m', 'holdD')   # the last four: the edge audit's own tags (trench_brain.feats) read off the sensed row


def audit_row(t):
    """A sensed row → the flat shape `trench_brain.feats` tags (the edge audit learned its rules on that shape: a nested row tags nothing)."""
    v = dict((t or {}).get('vitals') or {})
    return {**v, 'site': (t or {}).get('site'), 'x': (t or {}).get('x'), 'tv': {'call': [None, v.get('read')]} if v.get('read') else None}


def sense(state, rows, now, candles=None, flows=None, charts_out=None, cmeta=None, busted=None, weather_fn=None):
    """One sensing pass over the intake rows. → (state with the tape, [row], ctx).
    row = {mint, symbol, pair, px, nums (Tally), vitals (the board's numbers), chart (compact), launch, mind, band-free context, src, ev
    (Devil's evidence), li / mp are attached later by the launch-intelligence pass}. `ctx` = {'nums', 'perf', 'raw': {mint: {r, chart,
    rd}}} — the full objects for a caller that wants to annotate the same pass (the paper desk); the kernel reads only the rows."""
    import office_edge as _oe   # (lazy: office_edge imports the universe from this package)
    st = dict(state or {})
    perf = {'tally': 0.0, 'chart': 0.0}
    t0 = _t.perf_counter()
    ser, nums = tally(st, rows, now)
    perf['tally'] += _t.perf_counter() - t0
    st['series'] = ser
    st['first'] = first_seen(st, now)
    if weather_fn:   # 🌦 Weather reads the board once a pass (office.weather)
        t0 = _t.perf_counter(); st['weather'] = weather_fn(nums, rows, st, now); perf['weather'] = _t.perf_counter() - t0
    charting = candles is not None   # chart reading is on when the service hands the pass its candle map (possibly empty: the tape stands in)
    table, raw = [], {}
    for r in rows or []:
        m = r.get('mint')
        if m not in nums:
            continue
        n = nums[m]
        r = {**r, 'launch': _oe.launch_context(r)}
        chart = None
        if charting:   # ONE snapshot per coin per pass: real 1-min candles when fetched for this coin, else Tally's own tape
            t0 = _t.perf_counter()
            real = candles.get(m)
            meta = {**((cmeta or {}).get(m) or {} if real else {}), 'vol5m': r.get('vol5m'), 'vol1h': r.get('vol1h'), 'txns1h': r.get('txns1h'), 'buy': n.get('buy'), 'liqAge': 0.0,
                    'ageMin': None if r.get('ageH') is None else _f(r['ageH']) * 60}
            chart = _ci.read(real if real else _ci.from_tape(ser.get(m)), now, bool(real), 'candles' if real else 'tape', meta, buy=n.get('buy'), liq=n.get('liq') or None, liq_d=n.get('liqD'), flow=(flows or {}).get(r.get('pairAddress')))
            perf['chart'] += _t.perf_counter() - t0
            if charts_out is not None:
                charts_out[m] = chart
            r = {**r, 'chart': chart}
        rd = r.get('mind') or _tm.read(r)
        raw[m] = {'r': r, 'chart': chart, 'rd': rd}
        table.append({'mint': m, 'symbol': r.get('symbol'), 'pair': r.get('pairAddress'), 'px': _f(r.get('price')), 'nums': n, 'chart': _ci.compact(chart),
                      'launch': {k: r['launch'].get(k) for k in ('pad', 'type', 'key', 'graduated', 'curvePct', 'ageH', 'poolAgeH')},
                      'mind': {'narr': rd['narr'][1], 'hot': rd['narr'][2], 'callers': rd['crowd']['callers'], 'swarm': rd['crowd']['swarm'],
                               'slang': rd['crowd']['slang'], 'bots': rd['bots'][0], 'tug': rd['tug'][0]},
                      'src': list(r.get('src') or []), 'ev': [list(e) for e in evidence(r, n, chart, rd, busted)[:8]],
                      # 🌊 the buy / sell vital from the coin's last 90s of real swaps (only when its tape is fresh) + how far under its high it trades
                      **({'fv': fv_} if (fv_ := _fl.vital((flows or {}).get(r.get('pairAddress')))) else {}),
                      **({'distHigh': ((chart or {}).get('f') or {}).get('distHigh')} if ((chart or {}).get('f') or {}).get('distHigh') is not None else {}),
                      **({'social': r['social']} if r.get('social') else {}), **({'site': r['site']} if r.get('site') else {}), **({'x': r['x']} if r.get('x') else {}),
                      'vitals': {k: r.get(k) for k in VITAL_KEYS}
                                | {'organic': (r.get('vital') or {}).get('organicPct'), 'rug': (r.get('tv') or {}).get('rug'), 'read': ((r.get('tv') or {}).get('call') or [None, None])[1]}})
    return st, table, {'nums': nums, 'perf': perf, 'raw': raw}


BUST_N, BUST_MED = 30, -20.0


def busted(proof, call_keys):
    """Which READ types are busted on their OWN settled 1-hour records (`/fuses/call-proof`): ≥ BUST_N settled, typical result ≤ BUST_MED %.
    → {read label: its typical 1h %} — or None when there is no record to judge from (then nothing is claimed)."""
    if not proof:
        return None
    out = {}
    for label, key in (call_keys or {}).items():
        r = proof.get(key) or {}
        if int(_f(r.get('n'))) >= BUST_N and r.get('medPct') is not None and _f(r['medPct']) <= BUST_MED:
            out[label] = round(_f(r['medPct']), 1)
    return out
