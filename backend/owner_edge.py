"""🎯 THE OWNER'S OWN EDGE (pure, read-only): the hand picks logged in pick_style (what each coin looked like at the pick) joined to what
the card's closed pieces did with them (price result, fees apart). It names the entries that pay and the ones that bleed, from the
owner's own record — and lets the pick warning quote it. 2026-10-07, 99 joined picks: picks bought mid-pump (5m > +3%) 42 picks,
26% won, −8%; thin coins (< $20K an hour) 16 picks, 6% won; a 5-minute dip with ≥ $50K an hour 18 picks, 55% won, +6%.
The warning NEVER blocks: the owner holds when it is right and may pick anything — this only shows them their own numbers."""

CHASE_5M = 3.0           # up more than this in the last 5 minutes at the pick
THIN_VOL = 20_000.0      # 1h volume under this = thin
SETUP_DIP = -3.0         # 5-minute dip inside the coin …
SETUP_VOL = 50_000.0     # … with real volume

RULES = (
    ('chase', '🔥 bought mid-pump (5m over +3%)', lambda f: _f(f.get('chg5m')) > CHASE_5M if f.get('chg5m') is not None else False),
    ('thin', '🪫 thin coin (under $20K an hour)', lambda f: f.get('vol1h') is not None and _f(f.get('vol1h')) < THIN_VOL),
    ('setup', '✅ dip with volume (5m under −3%, $50K+ an hour)', lambda f: f.get('chg5m') is not None and _f(f.get('chg5m')) < SETUP_DIP and _f(f.get('vol1h')) >= SETUP_VOL),
)


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def join(log, pcs, window=900.0):
    """Each logged pick → {f, usd, cost, ret, mx, hold}: the pieces of that coin that opened within `window` seconds of the pick."""
    out = []
    for p in log or []:
        ps = [x for x in pcs or [] if x.get('mint') == p.get('mint') and abs(_f(x.get('bat')) - _f(p.get('at'))) < window]
        cost = sum(_f(x.get('cost')) for x in ps)
        if not ps or cost <= 0:
            continue
        usd = sum(_f(x.get('usd')) for x in ps)
        out.append({'f': p.get('f') or {}, 'usd': usd, 'cost': cost, 'ret': usd / cost, 'mx': max(_f(x.get('ret')) for x in ps),
                    'hold': sum(_f(x.get('hold')) * _f(x.get('cost')) for x in ps) / cost})
    return out


def _agg(js):
    n = len(js)
    if not n:
        return {'n': 0, 'wonPct': None, 'usd': 0.0, 'cost': 0.0, 'pct': None, 'big': 0}
    usd, cost = sum(j['usd'] for j in js), sum(j['cost'] for j in js)
    return {'n': n, 'wonPct': round(100 * sum(1 for j in js if j['usd'] > 0) / n), 'usd': round(usd, 2), 'cost': round(cost, 2),
            'pct': round(100 * usd / cost, 1) if cost > 0 else None, 'big': sum(1 for j in js if j['mx'] >= 0.5)}


def records(log, pcs):
    js = join(log, pcs)
    return {'sample': len(js), 'all': _agg(js), 'rules': {k: {'label': label, **_agg([j for j in js if fn(j['f'])])} for k, label, fn in RULES},
            'held': _agg([j for j in js if j['hold'] >= 30]), 'fast': _agg([j for j in js if j['hold'] < 30])}


def matches(f):
    """→ [rule keys] this coin's numbers at the pick match."""
    return [k for k, _l, fn in RULES if fn(f or {})]


def line(key, rec):
    r = ((rec or {}).get('rules') or {}).get(key) or {}
    if r.get('n', 0) < 8 or r.get('pct') is None:
        return ''
    return f"your own picks like this: {r['n']} picks, {r['wonPct']}% won, {r['pct']:+.0f}% ({'price only, fees apart'})"


def warnings(f, rec):
    """Warning sentences for a pick (never a block): the entries that bled for the owner, quoting their own record. Only when the
    record has ≥ 8 picks AND lost — a rule that did not lose says nothing."""
    out = []
    for k in matches(f):
        if k == 'setup':
            continue
        r = ((rec or {}).get('rules') or {}).get(k) or {}
        if r.get('n', 0) >= 8 and (r.get('pct') or 0) < 0:
            out.append(f"{dict((a, b) for a, b, _ in RULES)[k]} — {line(k, rec)}")
    return out
