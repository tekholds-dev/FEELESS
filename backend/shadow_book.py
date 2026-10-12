"""📄 SHADOW BOOK + CONTROL GROUP (owner's emergency edge audit, 2026-10-12). Pure + tested (`tests/test_shadow_book.py`).

While the agents trade on PAPER, every seat they WOULD have filled is noted at the live price at decision time, next to three controls
from the SAME moment and the same candidate pool:
  ctl_top    — the best-ranked candidate they did NOT choose
  ctl_random — a random eligible candidate (deterministic seed: the decision time)
  ctl_wait   — a coin the desk said WAIT / not cleared on
Each is graded at 30s · 1m · 2m · 5m · 10m · 15m · 30m · 1h from the first price read after each horizon (no hindsight: only prices seen
after the decision). A coin with no price at 1h = −100% (vanished). NET = gross − the round-trip cost measured on the real card's own
recent fills (passed in, never a constant guess). The report answers one question: do the agents beat a random trench coin after costs?
"""
import random as _rnd
import statistics as _st

HORIZONS = (30, 60, 120, 300, 600, 900, 1800, 3600)
GROUPS = ('fill', 'switch', 'ctl_top', 'ctl_random', 'ctl_wait')
DEDUP_SEC = 600.0     # the same coin in the same group is noted once per 10 min
KEEP = 4000
VANISHED = -100.0


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def entry(row, group, now, px, cost_pct):
    v, n = row.get('vitals') or {}, row.get('nums') or {}
    return {'mint': row.get('mint'), 'sym': row.get('symbol'), 'group': group, 'at': now, 'px': _f(px), 'cost': round(_f(cost_pct), 3),
            'tier': row.get('tier'), 'go': bool(row.get('go')), 'near': bool(row.get('nearReady')), 'score': row.get('opp'),
            'ageH': v.get('ageH'), 'mcap': v.get('mcap'), 'liq': n.get('liq') or v.get('liq'), 'd5': n.get('d5'),
            'phase': (row.get('li') or {}).get('phase'), 'src': list(row.get('srcs') or row.get('src') or [])[:6] if isinstance(row.get('srcs') or row.get('src'), (list, tuple)) else row.get('src'),
            'h': {}, 'hi': 0.0, 'lo': 0.0}


def note(book, row, group, now, px, cost_pct):
    """Add one decision. → the book. A row without a price is not noted (nothing to measure from)."""
    b = dict(book or {}); rows = list(b.get('rows') or [])
    if not row or not row.get('mint') or _f(px) <= 0 or group not in GROUPS:
        return b
    if any(r['mint'] == row['mint'] and r['group'] == group and now - _f(r['at']) < DEDUP_SEC for r in rows[-400:]):
        return b
    rows.append(entry(row, group, now, px, cost_pct))
    b['rows'] = rows[-KEEP:]
    return b


def controls(chosen, pool, waits, now):
    """→ {group: row} the control picks for one decision (none of them a chosen coin)."""
    ch = {r.get('mint') for r in chosen or []}
    cand = [r for r in pool or [] if r.get('mint') and r.get('mint') not in ch]
    seen, uniq = set(), []
    for r in cand:
        if r['mint'] not in seen:
            seen.add(r['mint']); uniq.append(r)
    out = {}
    if uniq:
        out['ctl_top'] = max(uniq, key=lambda r: _f(r.get('opp') or r.get('score')))
        rest = [r for r in uniq if r is not out['ctl_top']] or uniq
        out['ctl_random'] = _rnd.Random(int(now)).choice(rest)
    w = [r for r in waits or [] if r.get('mint') and r.get('mint') not in ch]
    if w:
        out['ctl_wait'] = _rnd.Random(int(now) + 7).choice(w)
    return out


def settle(book, prices, now):
    """Grade every open row with the prices read NOW (each horizon takes the first price seen after it). → the book."""
    b = dict(book or {}); out = []
    for r in b.get('rows') or []:
        r = {**r, 'h': dict(r.get('h') or {})}
        age = now - _f(r['at'])
        if len(r['h']) < len(HORIZONS) and age <= HORIZONS[-1] + 600:
            p = _f((prices or {}).get(r['mint']))
            if p > 0 and _f(r['px']) > 0:
                g = (p / r['px'] - 1) * 100
                r['hi'], r['lo'] = round(max(_f(r.get('hi')), g), 2), round(min(_f(r.get('lo')), g), 2)
                for h in HORIZONS:
                    if age >= h and str(h) not in r['h']:
                        r['h'][str(h)] = round(g, 2)
            elif age > HORIZONS[-1] + 300:   # no price at all well past an hour = vanished
                for h in HORIZONS:
                    r['h'].setdefault(str(h), VANISHED)
        out.append(r)
    b['rows'] = out
    return b


def due(book, now):
    """Mints that still need a price read."""
    return sorted({r['mint'] for r in (book or {}).get('rows') or [] if len(r.get('h') or {}) < len(HORIZONS) and now - _f(r['at']) <= HORIZONS[-1] + 600})


def stats(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    win, loss = sum(x for x in v if x > 0), -sum(x for x in v if x < 0)
    return {'n': len(v), 'med': round(_st.median(v), 2), 'avg': round(sum(v) / len(v), 2), 'won': round(sum(1 for x in v if x > 0) / len(v) * 100),
            'pf': round(win / loss, 2) if loss > 0 else None}


def report(book):
    """Per group × horizon: NET (gross − its own measured round-trip cost) n · median · average · % won · profit factor."""
    rows = (book or {}).get('rows') or []
    out = {}
    for g in GROUPS:
        rs = [r for r in rows if r['group'] == g]
        if not rs:
            continue
        out[g] = {str(h): stats([(r['h'][str(h)] - _f(r.get('cost'))) for r in rs if str(h) in r['h']]) for h in HORIZONS}
        out[g]['n'] = len(rs)
    return out


def verdict(rep, horizon='300', min_n=30):
    """Do the agents beat the random control after costs? → words (never more than the numbers say)."""
    a, c = ((rep or {}).get('fill') or {}).get(horizon), ((rep or {}).get('ctl_random') or {}).get(horizon)
    if not a or not c or a['n'] < min_n or c['n'] < min_n:
        return f"not enough yet — needs {min_n} graded agent picks and {min_n} random picks at {int(horizon) // 60} min"
    if a['avg'] > 0 and a['avg'] > c['avg']:
        return f"agents {a['avg']:+.1f}% vs random {c['avg']:+.1f}% net at {int(horizon) // 60} min — positive and better than random"
    if a['avg'] > c['avg']:
        return f"agents {a['avg']:+.1f}% vs random {c['avg']:+.1f}% net — better than random but still losing after costs"
    return f"agents {a['avg']:+.1f}% vs random {c['avg']:+.1f}% net — NOT better than a random trench coin"
