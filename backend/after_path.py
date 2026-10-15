"""👁 AFTER THE EXIT (pure, tested `tests/test_after_path.py`). Reaper's self-tuning replays each real position's recorded path — but a
path ENDS at the exit, so a tighter trail can only ever look as good or better and a wider one can never show what it would have kept.
That truncation is how the trail walked 6 → 4 / 50 → 35 while winners banked +2% (2026-10-13: YUNG peaked +15.4%, banked +1.7%).

Every confirmed agent exit is watched for `AFTER_SEC` more: its price vs OUR entry, one reading every `STEP_SEC`. A replay then runs on
path + after — the whole move — for the live rule AND a candidate alike. `grid` = every arm × give-back pair on those full paths.
A coin with no price left counts as −100% from there (a rug after our exit is what a wider trail would have eaten)."""
AFTER_SEC = 1800.0
STEP_SEC = 30.0
KEEP = 400
GONE_SEC = 300.0     # no price from any source this long while watched = it is gone
ARMS = (4.0, 6.0, 8.0, 10.0, 15.0)
GIVES = (30.0, 40.0, 50.0, 60.0, 70.0)
MIN_N = 30           # full paths before the grid says anything
EDGE = 1.0           # a setting "pays" only ≥ this many points a trade over the live one, with a median no worse


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def key_of(p):
    return f"{(p or {}).get('mint')}|{int(_f((p or {}).get('closedAt')))}"


def watch(state, closed, now):
    """Confirmed exits with an entry price join the watch list (once)."""
    s = {'open': dict((state or {}).get('open') or {}), 'done': dict((state or {}).get('done') or {})}
    for p in closed or []:
        k = key_of(p)
        if p.get('confirmed') and p.get('mint') and _f(p.get('entry')) > 0 and k not in s['open'] and k not in s['done']:
            s['open'][k] = {'mint': p['mint'], 'entry': _f(p['entry']), 'from': now, 'at': 0.0, 'seen': now, 'pts': []}
    return s


def step(state, px, now):
    """One look: every watched exit gets a reading (≤ one per STEP_SEC); after AFTER_SEC — or GONE_SEC with no price — it is filed."""
    s = {'open': dict((state or {}).get('open') or {}), 'done': dict((state or {}).get('done') or {})}
    for k, o in list(s['open'].items()):
        o = dict(o)
        p = _f((px or {}).get(o['mint']))
        if p > 0 and now - _f(o.get('at')) >= STEP_SEC:
            o['pts'] = list(o['pts']) + [round((p / o['entry'] - 1) * 100, 2)]; o['at'] = now; o['seen'] = now
        elif p > 0:
            o['seen'] = now
        gone = now - _f(o.get('seen')) >= GONE_SEC
        if gone or now - _f(o.get('from')) >= AFTER_SEC:
            s['done'][k] = list(o['pts']) + ([-100.0] if gone else [])
            s['open'].pop(k)
        else:
            s['open'][k] = o
    if len(s['done']) > KEEP:
        for k in list(s['done'])[:len(s['done']) - KEEP]:
            s['done'].pop(k)
    return s


def mints(state):
    return sorted({o['mint'] for o in ((state or {}).get('open') or {}).values()})


def full(p, done):
    """A position's WHOLE move: its recorded path + what the coin did after we left. None = no after-path on file (not judged)."""
    a = (done or {}).get(key_of(p))
    return None if a is None else [_f(x) for x in (p.get('path') or [])] + list(a)


def grid(positions, done, replay, live, take):
    """Every arm × give-back pair replayed on the full paths (`replay(path, params, take)` = office.reaper_replay).
    → {n, need, live: {arm, give, avg, med}, best: {...}, rows: [...top 5], pays, left} — `left` = avg % the live trail left on the table
    against the best pair. Nothing here changes a setting: a pair that pays is PROPOSED to the shadow test like any candidate."""
    paths = [f for f in (full(p, done) for p in positions or [] if p.get('confirmed')) if f]
    n = len(paths)
    if not n:
        return {'n': 0, 'need': MIN_N, 'pays': False}
    med = lambda v: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2
    run = lambda arm, give: [replay(f, {**live, 'protectAt': arm, 'giveBackPct': give}, take) for f in paths]
    stat = lambda arm, give: (lambda v: {'arm': arm, 'give': give, 'avg': round(sum(v) / n, 2), 'med': round(med(v), 2), 'won': round(sum(1 for x in v if x > 0) / n * 100)})(run(arm, give))
    lv = stat(_f(live.get('protectAt')), _f(live.get('giveBackPct')))
    rows = sorted((stat(a, g) for a in ARMS for g in GIVES), key=lambda r: -r['avg'])
    best = rows[0]
    pays = n >= MIN_N and best['avg'] - lv['avg'] >= EDGE and best['med'] >= lv['med'] and (best['arm'], best['give']) != (lv['arm'], lv['give'])
    return {'n': n, 'need': MIN_N, 'live': lv, 'best': best, 'rows': rows[:5], 'pays': pays, 'left': round(best['avg'] - lv['avg'], 2)}


def words(g):
    """One line (the page, the model coach)."""
    if not g or not g.get('n'):
        return 'no exit has been watched to its end yet'
    lv, b = g['live'], g['best']
    head = f"{g['n']} exits watched 30 min past the sale · live trail (arm +{lv['arm']:g}%, give back {lv['give']:g}%) {lv['avg']:+.1f}% a trade"
    if g['n'] < g['need']:
        return f"{head} · {g['n']} of {g['need']} before a wider trail is judged"
    return f"{head} · best (arm +{b['arm']:g}%, give back {b['give']:g}%) {b['avg']:+.1f}% → " + ('PAYS: sent to the shadow test' if g['pays'] else 'not enough better to change anything')


def by_rule(positions, done, replay, live, take, min_n=3):
    """🟢 GREEN EXITS BY RULE (owner-approved build b8, 2026-10-13: "Muse AI went +7.5% and still left the card by another rule — green
    trade, goofy exit; let the trail manage it"): every confirmed exit that made money, grouped by the rule that sold it, beside what the
    LIVE trail would have made on the same whole move (path + the 30 min after the sale). `left` > 0 = that rule sold winners the trail
    would have kept longer. A measure only — no exit changes from here. → [{rule, n, real, trail, left}] (≥ min_n), most left first."""
    by = {}
    for p in positions or []:
        if not p.get('confirmed') or p.get('realPct') is None or _f(p['realPct']) <= 0:
            continue
        f = full(p, done)
        if not f:
            continue
        r = str(p.get('rule') or '?').split(' ')[0]
        by.setdefault(r, []).append((_f(p['realPct']), replay(f, dict(live or {}), take)))
    med = lambda v: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2
    rows = [{'rule': r, 'n': len(v), 'real': round(med([a for a, _b in v]), 2), 'trail': round(med([b for _a, b in v]), 2)} for r, v in by.items() if len(v) >= min_n]
    for x in rows:
        x['left'] = round(x['trail'] - x['real'], 2)
    return sorted(rows, key=lambda x: -x['left'])


def rule_words(rows):
    if not rows:
        return None
    return 'green exits by rule (typical real → what the live trail would have made): ' + ' · '.join(
        f"{x['rule']} {x['n']}× {x['real']:+.1f}% → {x['trail']:+.1f}%" for x in rows[:4])


def scale_twin(positions, done, at=10.0, give=30.0, min_n=20, frac=0.75):
    """💰 THE SCALE-OUT TWIN (paper, always on): on every confirmed real exit whose WHOLE move touched +`at`%, what "half at +at, the rest on
    the trail (give-back `give`%)" made vs what we REALLY got. A rug (≤ −99) after the half = −100% on the rest. Recomputed with every new exit,
    so the owner sees whether the scale-out keeps paying. → {n, real: {avg, med}, twin: {avg, med}, better, worse, pays}"""
    med = lambda v: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2
    rows = []
    for p in positions or []:
        if not p.get('confirmed') or p.get('realPct') is None:
            continue
        ser = full(p, done)
        if not ser:
            continue
        half, peak, out = None, -1e9, None
        for x in ser:
            if x <= -99:
                out = (frac * at - (1 - frac) * 100.0) if half else None
                break
            if half is None and x >= at:
                half = at
            if half is not None:
                peak = max(peak, x)
                if peak >= at and x <= peak * (1 - give / 100):
                    out = frac * half + (1 - frac) * x
                    break
        if out is None and half is not None and ser and ser[-1] > -99:
            out = frac * half + (1 - frac) * ser[-1]
        if out is not None:
            rows.append((_f(p['realPct']), out))
    if not rows:
        return {'n': 0, 'pays': False}
    r, t = [a for a, _ in rows], [b for _, b in rows]
    rn = lambda v: round(v, 1)
    return {'n': len(rows), 'real': {'avg': rn(sum(r) / len(r)), 'med': rn(med(r))}, 'twin': {'avg': rn(sum(t) / len(t)), 'med': rn(med(t))},
            'better': sum(1 for a, b in rows if b > a), 'worse': sum(1 for a, b in rows if b < a),
            'pays': len(rows) >= min_n and sum(t) > sum(r) and med(t) >= med(r)}
