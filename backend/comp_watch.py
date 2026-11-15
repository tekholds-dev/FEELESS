"""👁 COMP WATCH (owner 2026-11-15: "nun on comps folder is real and true live animations or data, fix that"). Pure: the three things that
really move while COMP is idle, shaped for the COMP page.

  · board   every coin the internet learner is holding right now: what it saw at the snapshot, the price NOW (DexScreener), the move so far,
            when it settles, and the call it would make if it settled this second (up ≥ +20% won, down ≤ -20% lost, else flat)
  · minds   every model call the agents made in the last hour, per minute (ok vs failed, average latency) and the newest calls as a tape
  · settled the last rows the learner graded itself, plus its won / lost / flat totals
Nothing is invented: a coin DexScreener did not answer for keeps price None and the page shows "—".
"""
import comp_market as _cm

TAPE_N = 14
SETTLED_N = 12
WINDOW_MIN = 60


def _call(snap, move):
    if move is None:
        return None
    return 'won' if move >= _cm.WIN_PCT else 'lost' if move <= _cm.LOSS_PCT else 'flat'


def board(snaps, pairs, now):
    """snaps = market_open.json rows; pairs = {pairAddress: DexScreener pair or None (gone)} → rows, newest first."""
    out = []
    for s in snaps or []:
        p = (pairs or {}).get(s.get('pair'), 'unknown')
        if p == 'unknown':
            price = None; gone = False
        else:
            f = _cm.features(p, now) if p else None
            price = f['price'] if f else None; gone = f is None
        move = round((price / s['price'] - 1) * 100, 2) if price and s.get('price') else (-100.0 if gone else None)
        left = max(0, round(s.get('at', now) + _cm.HOLD_SEC - now))
        out.append({'pair': s.get('pair'), 'mint': s.get('mint'), 'symbol': s.get('symbol') or '?', 'dex': s.get('dex') or '', 'entry': s.get('price'),
                    'price': price, 'move': move, 'gone': gone, 'left': left, 'held': round(now - s.get('at', now)), 'call': 'lost' if gone else _call(s, move),
                    'liq': s.get('liq'), 'ageMin': s.get('ageMin'), 'h1': s.get('h1'), 'buys': s.get('buys'), 'sells': s.get('sells')})
    out.sort(key=lambda r: r['held'])
    return out


def minds(calls, now, window_min=WINDOW_MIN):
    """calls = mind_calls.jsonl rows → {'perMin': [{'m','ok','fail','ms'}], 'unit', 'tape': [...], 'models': [...], totals}.
    The last hour by the minute; when nothing was called this hour, the last day by the hour (the page says which)."""
    rows = [c for c in calls or [] if isinstance(c, dict) and c.get('at')]
    unit, step, n_bins = 'min', 60, window_min
    if not any(c['at'] >= now - window_min * 60 for c in rows):
        unit, step, n_bins = 'hour', 3600, 24
    t0 = now - n_bins * step
    recent = [c for c in rows if c['at'] >= t0]
    bins = [{'m': i - n_bins + 1, 'ok': 0, 'fail': 0, 'ms': 0} for i in range(n_bins)]
    sums = [0] * n_bins
    by = {}
    for c in recent:
        i = min(n_bins - 1, max(0, int((c['at'] - t0) // step)))
        ok = bool(c.get('ok')); bins[i]['ok' if ok else 'fail'] += 1
        sums[i] += c.get('ms') or 0
        name = c.get('model') or c.get('asked') or 'unknown'
        b = by.setdefault(name, {'model': name, 'calls': 0, 'fail': 0, 'msSum': 0, 'local': bool(c.get('local'))})
        b['calls'] += 1; b['fail'] += 0 if ok else 1; b['msSum'] += c.get('ms') or 0
    for i, b in enumerate(bins):
        n = b['ok'] + b['fail']; b['ms'] = round(sums[i] / n) if n else 0
    models = sorted(({'model': b['model'], 'calls': b['calls'], 'fail': b['fail'], 'ms': round(b['msSum'] / b['calls']), 'local': b['local']} for b in by.values()), key=lambda x: -x['calls'])
    last = sorted((c for c in calls or [] if isinstance(c, dict)), key=lambda c: c.get('at') or 0)[-TAPE_N:][::-1]
    tape = [{'at': c.get('at'), 'kind': c.get('kind'), 'model': c.get('model') or c.get('asked'), 'ms': c.get('ms'), 'ok': bool(c.get('ok')),
             'usd': c.get('usd') or 0, 'local': bool(c.get('local')), 'tokens': c.get('tokens')} for c in last]
    n = len(recent); fails = sum(1 for c in recent if not c.get('ok'))
    return {'perMin': bins, 'unit': unit, 'tape': tape, 'models': models[:8], 'calls': n, 'fail': fails, 'usd': round(sum(c.get('usd') or 0 for c in recent), 4)}


def view(snaps, pairs, calls, rows, stats, now):
    b = board(snaps, pairs, now)
    lean = {'won': sum(1 for r in b if r['call'] == 'won'), 'lost': sum(1 for r in b if r['call'] == 'lost'), 'flat': sum(1 for r in b if r['call'] == 'flat')}
    st = stats or {}
    return {'at': round(now, 1), 'board': b, 'lean': lean, 'minds': minds(calls, now),
            'settled': [{k: r.get(k) for k in ('title', 'outcome', 'at', 'plan')} for r in (rows or [])[-SETTLED_N:][::-1]],
            'totals': {k: st.get(k) for k in ('won', 'lost', 'flat', 'collects', 'rows', 'nextSettle', 'at')}}
