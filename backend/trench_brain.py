"""🧠 TRENCH BRAIN (pure, tested). Owner, 2026-10-09: "a never-before-seen trench category to outsmart and learn to profit trench coins,
and on to the next".

Every other trench list is judged on ONE number: the price an hour later. A trench trade is not held an hour — it is a ticket that
either runs (take it) or dies (cut it). So the brain judges every trench coin it sees on the PLAY a ticket would make: it watches the
coin's price on every pass and records which line it touched FIRST — +TP_PCT (🎯 hit, "on to the next") or −SL_PCT (🩸 cut). A coin
that touched neither in an hour is settled at its 1h move (inside the two lines); a coin with no price = −100% (it vanished).

It learns which coins hit first from what they looked like when it first saw them — single features AND pairs of features (a fresh
coin can be fine, a fresh coin with a 40% top-10 not) — `table()`. `score()` = the learned play of a coin, every matched cell
shrunk toward the global result by its sample size, so a thin cell can't carry a coin. `proof()` = walk-forward: learn on the
oldest 60%, rank the newest 40% it never saw; the brain is only TRUSTED (`proven`) when its top third beat its bottom third by
≥ PROOF_SPREAD points AND its top third played positive. Until then it is a list and a record, never an engine buy. Never a promise.
"""

TP_PCT = 50.0          # 🎯 the ticket's win line: +50% first = take it, on to the next
SL_PCT = 30.0          # 🩸 the ticket's cut line: −30% first = out
SETTLE_SEC = 3600.0    # a coin that touched neither line is settled at its 1h move
RECENT_SEC = 6 * 3600  # a coin is not noted again for 6h after it settled
OPEN_MAX = 400         # coins watched at once (oldest dropped first — still counted as their last move, never −100% unfairly)
KEEP = 4000            # settled coins kept
MIN_N = 8              # a cell needs this many settled coins before it counts
SHRINK = 20.0          # cell weight = n / (n + SHRINK)
PROOF_MIN = 30         # walk-forward test coins needed before the brain can be trusted
PROOF_SPREAD = 10.0    # top third vs bottom third, points of play


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


def _med(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def feats(r):
    """The trench features of a coin RIGHT NOW (missing readings are left out, never guessed)."""
    r = r or {}
    out = []
    if r.get('ageH') is not None:
        out.append('age:' + _band(_f(r['ageH']), (0.25, 1, 3, 12), ('<15m', '15-60m', '1-3h', '3-12h', '12h+')))
    if _f(r.get('mcap')) > 0:
        out.append('cap:' + _band(_f(r['mcap']), (30e3, 100e3, 300e3, 1e6), ('<30K', '30-100K', '100-300K', '300K-1M', '1M+')))
    if r.get('curve') is not None:
        out.append('stage:' + ('curve' if r['curve'] else 'graduated'))
    if _f(r.get('vol1h')) > 0:
        out.append('pace:' + _band(_f(r.get('vol5m')) * 12 / _f(r['vol1h']), (0.5, 1, 2), ('fading', 'steady', 'rising', 'surging')))
    if r.get('buyShare') is not None:
        out.append('buy:' + _band(_f(r['buyShare']), (45, 55, 65), ('<45', '45-55', '55-65', '65+')))
    if r.get('chg5m') is not None:
        out.append('5m:' + _band(_f(r['chg5m']), (-5, 0, 5, 15), ('<-5', '-5..0', '0..5', '5..15', '15+')))
    if r.get('chg1h') is not None:
        out.append('1h:' + _band(_f(r['chg1h']), (0, 50, 200), ('red', '0..50', '50..200', '200+')))
    if r.get('safe') is not None:
        out.append('safe:' + ('yes' if r['safe'] else 'no'))
    if _f(r.get('top10')) > 0:
        out.append('top10:' + _band(_f(r['top10']), (15, 25, 35), ('<15', '15-25', '25-35', '35+')))
    if r.get('site') is not None or r.get('x') is not None:
        out.append('soc:' + {2: 'site+x', 1: 'one'}.get(bool(r.get('site')) + bool(r.get('x')), 'none'))
    call = ((r.get('tv') or {}).get('call') or [None, None])[1]
    if call:
        out.append('read:' + str(call))
    tape = (r.get('tape') or {}).get('read') if isinstance(r.get('tape'), dict) else r.get('tape')
    if tape:
        out.append('tape:' + str(tape))
    return out


def cells(fs):
    """Every single feature + every pair (sorted, so a pair always has one name)."""
    fs = sorted(set(fs or []))
    return fs + [a + ' & ' + b for i, a in enumerate(fs) for b in fs[i + 1:]]


def track(state, rows, price_of, now):
    """One pass: open coins see their price (first touch of +TP / −SL settles them; an hour settles the rest), then new rows are
    noted once with their features. `rows` = [row with mint + price]; `price_of(mint)` = live price or None.
    → new state {open: {mint: {px, at, f, sym}}, done: [{mint, sym, at, play, end, peak, how, f}]}."""
    st = state or {}
    opened, done = dict(st.get('open') or {}), list(st.get('done') or [])
    for mint, o in list(opened.items()):
        px, e = _f(price_of(mint)), _f(o.get('px'))
        if e <= 0:
            opened.pop(mint); continue
        if px > 0:
            pct = (px / e - 1) * 100
            o = {**o, 'hi': max(_f(o.get('hi')), pct), 'lo': min(_f(o.get('lo')), pct), 'last': pct}
            opened[mint] = o
        how = None
        if _f(o.get('hi')) >= TP_PCT:
            how, play = 'hit', TP_PCT
        elif _f(o.get('lo')) <= -SL_PCT:
            how, play = 'cut', -SL_PCT
        elif now - _f(o.get('at')) >= SETTLE_SEC:
            how, play = ('end', _f(o.get('last'))) if px > 0 else ('gone', -100.0)
        if how:
            done.append({'mint': mint, 'sym': o.get('sym'), 'at': now, 'play': round(play, 2), 'end': round(_f(o.get('last')), 2),
                         'peak': round(_f(o.get('hi')), 2), 'how': how, 'f': o.get('f') or []})
            opened.pop(mint)
    recent = {d['mint'] for d in done if now - _f(d.get('at')) < RECENT_SEC}
    for r in rows or []:
        m, px = (r or {}).get('mint'), _f((r or {}).get('price'))
        if m and px > 0 and m not in opened and m not in recent:
            opened[m] = {'px': px, 'at': now, 'sym': r.get('symbol'), 'f': feats(r), 'hi': 0.0, 'lo': 0.0, 'last': 0.0}
    if len(opened) > OPEN_MAX:   # the oldest leave as their last move (no fake −100%)
        for m, o in sorted(opened.items(), key=lambda kv: _f(kv[1].get('at')))[:len(opened) - OPEN_MAX]:
            done.append({'mint': m, 'sym': o.get('sym'), 'at': now, 'play': round(_f(o.get('last')), 2), 'end': round(_f(o.get('last')), 2),
                         'peak': round(_f(o.get('hi')), 2), 'how': 'end', 'f': o.get('f') or []})
            opened.pop(m)
    return {'open': opened, 'done': done[-KEEP:]}


def table(done):
    """{cell: {n, med, hit}} over settled coins: median play and % that touched +TP first. Plus '*' = everything."""
    by = {}
    for d in done or []:
        for c in cells(d.get('f')) + ['*']:
            by.setdefault(c, []).append(d)
    out = {}
    for c, ds in by.items():
        ps = [_f(d.get('play')) for d in ds]
        out[c] = {'n': len(ps), 'med': round(_med(ps), 2), 'hit': round(sum(1 for d in ds if d.get('how') == 'hit') / len(ps) * 100)}
    return out


def score(r_or_feats, tbl):
    """→ {est, hit, n, why: [(cell, med, n) best-evidence 3]} — the learned play of a coin like this; None when nothing is learned."""
    base = (tbl or {}).get('*')
    if not base:
        return None
    fs = r_or_feats if isinstance(r_or_feats, list) else feats(r_or_feats)
    hits = [(c, tbl[c]) for c in cells(fs) if c in tbl and tbl[c]['n'] >= MIN_N]
    if not hits:
        return {'est': base['med'], 'hit': base['hit'], 'n': 0, 'why': []}
    sh = lambda v, key: base[key] + v['n'] / (v['n'] + SHRINK) * (v[key] - base[key])   # a cell's result, shrunk by its sample
    lean = sorted(hits, key=lambda kv: -abs(sh(kv[1], 'med') - base['med']))[:3]          # the 3 cells that say the most about THIS coin
    est = sum(sh(v, 'med') for _, v in lean) / len(lean)
    hit = sum(sh(v, 'hit') for _, v in lean) / len(lean)
    return {'est': round(max(-100.0, min(TP_PCT, est)), 1), 'hit': int(max(0, min(100, round(hit)))), 'n': len(hits),
            'why': [(c, v['med'], v['n']) for c, v in lean]}


def proof(done):
    """Walk-forward: learn on the oldest 60%, rank the newest 40% → {n, top, bottom, spread, proven, hitTop}. Never trusted on the
    same coins it learned from."""
    ds = sorted(done or [], key=lambda d: _f(d.get('at')))
    cut = int(len(ds) * 0.6)
    train, test = ds[:cut], ds[cut:]
    if len(test) < 3 or not train:
        return {'n': len(test), 'proven': False}
    tbl = table(train)
    ranked = sorted(test, key=lambda d: -(score(d.get('f') or [], tbl) or {'est': 0})['est'])
    k = max(1, len(ranked) // 3)
    top, bot = ranked[:k], ranked[-k:]
    t, b = _med([_f(d['play']) for d in top]), _med([_f(d['play']) for d in bot])
    return {'n': len(test), 'top': round(t, 1), 'bottom': round(b, 1), 'spread': round(t - b, 1),
            'hitTop': round(sum(1 for d in top if d.get('how') == 'hit') / len(top) * 100),
            'proven': bool(len(test) >= PROOF_MIN and t > 0 and t - b >= PROOF_SPREAD)}


def lessons(tbl, top=4):
    """The pair / single cells that played best and worst (≥ MIN_N) — what the brain has learned, in words."""
    rows = [(c, v) for c, v in (tbl or {}).items() if c != '*' and v['n'] >= MIN_N]
    rows.sort(key=lambda kv: -kv[1]['med'])
    return {'best': [{'cell': c, **v} for c, v in rows[:top]], 'worst': [{'cell': c, **v} for c, v in rows[::-1][:top]]}


def summary(state):
    """What the brain knows: settled / watching counts, how coins ended (hit / cut / end / gone), the global play, proof, lessons."""
    done = (state or {}).get('done') or []
    tbl = table(done)
    how = {}
    for d in done:
        how[d.get('how')] = how.get(d.get('how'), 0) + 1
    return {'n': len(done), 'open': len((state or {}).get('open') or {}), 'how': how, 'all': tbl.get('*'), 'proof': proof(done),
            'lessons': lessons(tbl), 'tp': TP_PCT, 'sl': SL_PCT}
