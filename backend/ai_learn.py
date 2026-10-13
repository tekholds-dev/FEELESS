"""🧠 THE AGENTS LEARN FROM THE MODEL — ON ITS RECORD (owner, 2026-10-12: "agents should learn from AI … LM Studio used to the best of
its ability while using little, so the agents grow stronger"). Pure: no I/O, no model call.

Every stance the model gives on a coin is NOTED once at that price and JUDGED 15 minutes later (no price after an hour = −100%, a
vanished coin is never dropped). Per stance: how many were judged, the typical result, the share that went up. A stance moves the
kernel's rank ONLY once it is proven on that record, and only a little (×0.9 … ×1.1):
    a stance whose coins typically LOSE  → coins it is given on rank lower   (the model is a good warning)
    a stance whose coins typically WIN   → coins it is given on rank higher  (the model is a good spotter)
    anything else, or under MIN_N judged → ×1.0 (the model is shown, not used)
The model still never places, sizes, blocks or sells anything; an unproven model weighs exactly nothing."""

JUDGE_SEC = 900.0        # a call is judged 15 min later (the trench desk's own window)
GONE_SEC = 3600.0        # no price for an hour = the coin is gone: −100%
RENOTE_SEC = 1800.0      # the same stance on the same coin is one call per 30 min
MIN_N = 20               # a stance weighs nothing until this many of its calls are judged
KEEP_OPEN, KEEP_DONE = 200, 600
WIN_MED, LOSE_MED = 2.0, -5.0     # typical 15-min result that makes a stance a proven spotter / a proven warning
UP, DOWN = 1.0, 0.85   # 🚫 VETO-ONLY (owner, 2026-10-13: "do #5"): the model's ENTER calls fell a typical 39% — it can no longer rank a coin UP. A warning PROVEN on its own judged record ranks one down 15%; nothing else it says weighs anything
FRESH_SEC = 600.0        # a stance applies to its coin for 10 minutes


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x and x not in (float('inf'), float('-inf')) else d
    except (TypeError, ValueError):
        return d


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return None if not n else s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def note(book, role, mint, stance, px, now, symbol=None, flags=None):
    """One model stance → an open call (once per coin + stance per 30 min, only with a live price). How many risk flags it raised rides
    on the call, so "the model flagged 2+ risks" is judged on its own record too (`vital_record`). → new book"""
    b = {'open': list((book or {}).get('open') or []), 'done': list((book or {}).get('done') or [])}
    if not mint or not stance or _f(px) <= 0:
        return b
    st = str(stance).upper()
    if any(c['mint'] == mint and c['stance'] == st and now - _f(c['at']) < RENOTE_SEC for c in b['open'] + b['done'][-80:]):
        return b
    c = {'mint': mint, 'symbol': symbol, 'role': role, 'stance': st, 'px': _f(px), 'at': round(now, 1)}
    if isinstance(flags, int):
        c['flags'] = flags
    b['open'] = (b['open'] + [c])[-KEEP_OPEN:]
    return b


def settle(book, prices, now):
    """Judge every open call that is due at today's price ({mint: px}); a call with no price waits until GONE_SEC, then = −100%. → new book"""
    b = {'open': [], 'done': list((book or {}).get('done') or [])}
    for c in (book or {}).get('open') or []:
        age = now - _f(c.get('at'))
        if age < JUDGE_SEC:
            b['open'].append(c); continue
        px = _f((prices or {}).get(c['mint']))
        if px > 0:
            b['done'].append({**c, 'pct': round((px / c['px'] - 1) * 100, 2), 'doneAt': round(now, 1)})
        elif age >= GONE_SEC:
            b['done'].append({**c, 'pct': -100.0, 'gone': True, 'doneAt': round(now, 1)})
        else:
            b['open'].append(c)
    b['done'] = b['done'][-KEEP_DONE:]
    return b


def record(book):
    """{stance: {n, med, up}} + 'ALL' — the model's own record, judged calls only."""
    by = {}
    for c in (book or {}).get('done') or []:
        by.setdefault(c['stance'], []).append(_f(c.get('pct')))
        by.setdefault('ALL', []).append(_f(c.get('pct')))
    return {k: {'n': len(v), 'med': round(_median(v), 2), 'up': round(100 * sum(1 for x in v if x > 0) / len(v))} for k, v in by.items()}


# 🚩 THE MODEL'S RISK FLAGS on their OWN record: "it raised 2+ risk flags" and "it raised none", each read against the base rate of ALL
# its calls exactly like a stance. (The 2026-10-12 rug / timing meters were retired by the owner's vital-intel spec on 2026-10-13: their
# record separated winners in one half of the night only.)
BUCKETS = (('FLAGS:2+', '2+ risk flags', lambda c: isinstance(c.get('flags'), int) and c['flags'] >= 2),
           ('FLAGS:0', 'no risk flag', lambda c: c.get('flags') == 0))
BUCKET_LABEL = {k: lab for k, lab, _t in BUCKETS}


def buckets_of(c):
    """The vital buckets one call (or one advice: {rug, timing}) falls in."""
    return [k for k, _lab, t in BUCKETS if t(c or {})]


def vital_record(book):
    """{bucket: {n, med, up}} + 'ALL' — judged calls only (a call made before vitals existed is in ALL, never in a bucket)."""
    by = {}
    for c in (book or {}).get('done') or []:
        by.setdefault('ALL', []).append(_f(c.get('pct')))
        for k in buckets_of(c):
            by.setdefault(k, []).append(_f(c.get('pct')))
    return {k: {'n': len(v), 'med': round(_median(v), 2), 'up': round(100 * sum(1 for x in v if x > 0) / len(v))} for k, v in by.items()}


def advice_factor(rec, vrec, advice):
    """One model answer → ×0.9 … ×1.1 from its stance AND every vital bucket it falls in (proven ones only). Any proven warning wins
    (the most cautious factor); otherwise a proven spotter; otherwise ×1.0."""
    a = advice or {}
    fs = [factor(rec, a.get('stance'))] + [factor(vrec, k) for k in buckets_of({'flags': len(a.get('risk_flags') or [])})]
    lo, hi = min(fs), max(fs)
    return lo if lo < 1.0 else hi


def factor(rec, stance):
    """What a stance is worth on the rank: ×0.9 (a proven warning) · ×1.1 (a proven spotter) · ×1.0 (unproven or neutral). The model's
    stance is read against the base rate of ALL its calls, so a market that falls on everything does not prove every warning."""
    r, base = (rec or {}).get(str(stance or '').upper()), (rec or {}).get('ALL')
    if not r or r['n'] < MIN_N or not base:
        return 1.0
    edge = r['med'] - base['med']
    if r['med'] <= LOSE_MED and edge <= -2.0:
        return DOWN
    if r['med'] >= WIN_MED and edge >= 2.0 and r['up'] >= 55:
        return UP
    return 1.0


def weights(notes, rec, now, vrec=None):
    """{mint: factor} for the coins the model spoke on in the last 10 minutes (`notes` = {mint: {role: {advice: {stance, vitals, timing}, at}}});
    several desks' answers on one coin = the most cautious factor. Only non-1.0 factors are returned (±10% at most, stance + vitals together)."""
    out = {}
    for m, roles in (notes or {}).items():
        fs = [advice_factor(rec, vrec, (n or {}).get('advice')) for n in (roles or {}).values() if now - _f((n or {}).get('at')) <= FRESH_SEC and (n or {}).get('advice')]
        if fs and min(fs) != 1.0:
            out[m] = min(fs)
        elif fs and max(fs) != 1.0:
            out[m] = max(fs)
    return out


def view(book, rec=None):
    """The page's line: per stance n / typical / % up / what it is worth now, how many calls are waiting, and the state in a word."""
    rec = rec if rec is not None else record(book)
    rows = [{'stance': k, **v, 'factor': factor(rec, k), 'proven': v['n'] >= MIN_N} for k, v in sorted(rec.items(), key=lambda kv: -kv[1]['n']) if k != 'ALL']
    vrec = vital_record(book)
    vrows = [{'bucket': k, 'label': lab, **vrec.get(k, {'n': 0, 'med': None, 'up': None}), 'factor': factor(vrec, k), 'proven': (vrec.get(k) or {}).get('n', 0) >= MIN_N}
             for k, lab, _t in BUCKETS]
    used = [r for r in rows + vrows if r['factor'] != 1.0]
    n = (rec.get('ALL') or {}).get('n', 0)
    return {'rows': rows, 'vitals': vrows, 'all': rec.get('ALL'), 'open': len((book or {}).get('open') or []), 'minN': MIN_N, 'judgeMin': round(JUDGE_SEC / 60),
            'state': 'IN USE' if used else 'LEARNING' if n < MIN_N else 'NO EDGE YET',
            'why': (f"{len(used)} proven stance{'s' if len(used) != 1 else ''} rank{'' if len(used) != 1 else 's'} a coin DOWN by up to 15% — the model never ranks one up" if used
                    else f"{n} of {MIN_N} judged calls — the model is shown, not used" if n < MIN_N else 'judged, but no stance or vital separates winners from losers yet — the model is shown, not used')}
