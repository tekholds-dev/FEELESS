"""🧠 LEARNS FROM YOUR REAL TRADES (pure, tested). Owner, 2026-10-08: "update and clean the engine to be a learning engine to my trades / real money".

Every coin that LEAVES the real card is one lesson: how it looked when it was bought (leg `bought`: age, 1h move, buyers, pool, the tag that
brought it in; who picked it) → how it ended (exit price vs the book's entry, hold time, why it left). `table()` = the typical result per
feature bucket (median, ≥ MIN_N pieces). The 🧬 edge score reads it as one more part ("coins like this on YOUR card did X%"), so the ranking
drifts toward what actually paid with the owner's money and away from what lost it. Coin moves in %, never the card's $.
"""

MIN_N = 5
KEEP = 2000


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _band(v, cuts, names):
    for c, n in zip(cuts, names):
        if v < c:
            return n
    return names[-1]


def keys(row):
    """The feature buckets a coin falls in (works for a card leg's `bought` snapshot AND for a list row)."""
    r = row or {}
    out = []
    if r.get('ageH') is not None:
        out.append('age:' + _band(_f(r['ageH']), (1, 6, 24, 168), ('<1h', '1-6h', '6-24h', '1-7d', '>7d')))
    c1 = r.get('chg1h')
    if c1 is not None:
        out.append('1h:' + _band(_f(c1), (-10, 0, 20, 60, 150), ('<-10', '-10..0', '0..20', '20..60', '60..150', '>150')))
    bs = r.get('buyShare')
    if bs is not None:
        b = _f(bs) * (100 if 0 < _f(bs) <= 1 else 1)
        out.append('buy:' + _band(b, (45, 55, 65), ('<45', '45-55', '55-65', '>65')))
    lq = r.get('liq')
    if lq is not None and _f(lq) > 0:
        out.append('pool:' + _band(_f(lq), (15e3, 50e3, 150e3), ('<15K', '15-50K', '50-150K', '>150K')))
    v1 = r.get('vol1h')
    if v1 is not None and _f(v1) > 0:
        out.append('vol:' + _band(_f(v1), (10e3, 50e3, 200e3), ('<10K', '10-50K', '50-200K', '>200K')))
    t = str(r.get('tag') or '').split(' ')[0]
    if t:
        out.append('tag:' + t)
    if r.get('picked') is not None:
        out.append('by:' + ('you' if r.get('picked') else 'engine'))
    return out


def note(state, leg, px_exit, now, why=''):
    """Record a coin that left the real card → new state {pieces: [...]}. Needs a real entry and exit price."""
    st = dict(state or {})
    entry, px = _f((leg or {}).get('entry')), _f(px_exit)
    if entry <= 0 or px <= 0:
        return st
    b = dict((leg or {}).get('bought') or {})
    b['picked'] = bool((leg or {}).get('picked'))
    piece = {'at': now, 'mint': (leg or {}).get('mint'), 'symbol': (leg or {}).get('symbol'), 'pct': round((px / entry - 1) * 100, 2),
             'holdMin': round(max(0.0, now - _f((leg or {}).get('firstEntry') or (leg or {}).get('at'))) / 60, 1), 'why': str(why)[:60], 'k': keys(b)}
    st['pieces'] = ((st.get('pieces') or []) + [piece])[-KEEP:]
    return st


def table(state):
    """{bucket: {n, medPct, wonPct}} over every recorded piece (median: one moonshot can't carry a bucket)."""
    by = {}
    for p in (state or {}).get('pieces') or []:
        for k in p.get('k') or []:
            by.setdefault(k, []).append(_f(p.get('pct')))
    out = {}
    for k, xs in by.items():
        xs = sorted(xs); n = len(xs)
        out[k] = {'n': n, 'medPct': round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 2), 'wonPct': round(sum(1 for x in xs if x > 0) / n * 100)}
    return out


def match(row, tbl):
    """The typical result of coins like this one on the owner's card → (median of the matched buckets, [(bucket, med, n)]) or (None, [])."""
    hits = [(k, (tbl or {})[k]['medPct'], (tbl or {})[k]['n']) for k in keys(row) if k in (tbl or {}) and (tbl or {})[k]['n'] >= MIN_N]
    if not hits:
        return None, []
    ms = sorted(h[1] for h in hits); n = len(ms)
    return (ms[n // 2] if n % 2 else (ms[n // 2 - 1] + ms[n // 2]) / 2), hits


def lessons(tbl, top=4):
    """The buckets that paid most and lost most (≥ MIN_N pieces) for the screen."""
    rows = [(k, v) for k, v in (tbl or {}).items() if v['n'] >= MIN_N]
    rows.sort(key=lambda kv: -kv[1]['medPct'])
    return {'best': [{'bucket': k, **v} for k, v in rows[:top]], 'worst': [{'bucket': k, **v} for k, v in rows[::-1][:top]]}
