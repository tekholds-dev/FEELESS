"""⏱ NSFA SURVIVAL WATCH (owner 2026-10-28: "the agents observe the 1, 5 and 15 min to understand per-coin survival").
Every coin the desk senses gets three checkpoints from the moment we FIRST saw it: its move at +1m, +5m and +15m, and whether it
survived each (never fell 50 % or more under the first price we saw). Pure: the caller keeps the book (a dict) and feeds it the sensed rows.
It feeds the Warden's risk scale (a failed checkpoint / a coin watched under a minute = a risk flag — it can only shrink a seat) and the
agents' vitals (the last hour's cohort survival at 1 / 5 / 15 min)."""

CHECKS = ((1, 60), (5, 300), (15, 900))
RUG_PCT = -50.0
KEEP = 3000          # coins remembered
FORGET_SEC = 6 * 3600


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _px(r):
    return _f(r.get('price') or r.get('priceUsd') or r.get('px'))


def observe(book, rows, now):
    """Feed one pass of sensed rows {mint, price | priceUsd | px, symbol}. Fills each coin's checkpoints the first pass after they are due."""
    for r in rows or []:
        m, p = r.get('mint'), _px(r)
        if not m or p <= 0:
            continue
        e = book.get(m)
        if e is None:
            e = book[m] = {'t0': now, 'p0': p, 'min': p, 'sym': r.get('symbol') or r.get('sym')}
        e['min'] = min(_f(e.get('min')) or p, p); e['last'], e['lastAt'] = p, now
        for lab, sec in CHECKS:
            k = f'm{lab}'
            if k not in e and now - e['t0'] >= sec:
                pct = (p / e['p0'] - 1) * 100
                e[k] = round(pct, 1)
                e[f'ok{lab}'] = pct > RUG_PCT and (e['min'] / e['p0'] - 1) * 100 > RUG_PCT
    if len(book) > KEEP:   # forget the oldest first
        for m in sorted(book, key=lambda k: book[k].get('lastAt') or 0)[:len(book) - KEEP]:
            book.pop(m, None)
    for m in [k for k, v in book.items() if now - _f(v.get('lastAt')) > FORGET_SEC]:
        book.pop(m, None)
    return book


def coin(book, mint, now):
    """→ {watchedSec, m1, m5, m15, ok1, ok5, ok15} for one coin, or None if we never sensed it."""
    e = (book or {}).get(mint)
    if not e:
        return None
    out = {'watchedSec': round(now - e['t0'])}
    for lab, _s in CHECKS:
        out[f'm{lab}'], out[f'ok{lab}'] = e.get(f'm{lab}'), e.get(f'ok{lab}')
    return out


def flags(s):
    """The risk flags one coin's watch raises (for the Warden's risk scale) — [] when it is clean or unknown."""
    if not s:
        return []
    bad = [lab for lab, _s in CHECKS if s.get(f'ok{lab}') is False]
    if bad:
        return [f"failed its {bad[0]}m survival ({s.get(f'm{bad[0]}'):+.0f}%)"]
    if s.get('watchedSec') is not None and s['watchedSec'] < 60:
        return ['watched under 1 min']
    return []


def cohort(book, now, window=3600):
    """The last hour's coins: of those that reached each checkpoint, the share that survived it + their typical move. → {m1: {n, pct, med}, …}"""
    out = {}
    rows = [e for e in (book or {}).values() if now - _f(e.get('t0')) <= window + 900]
    for lab, _s in CHECKS:
        got = [e for e in rows if e.get(f'ok{lab}') is not None]
        moves = sorted(_f(e.get(f'm{lab}')) for e in got)
        out[f'm{lab}'] = {'n': len(got), 'pct': round(sum(1 for e in got if e[f'ok{lab}']) / len(got) * 100) if got else None,
                          'med': round(moves[len(moves) // 2], 1) if moves else None}
    return out
