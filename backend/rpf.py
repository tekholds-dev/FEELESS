"""🏗 RPF — REAL PROJECT FINDER (owner, 2026-10-19: "there are some dope projects that launch and we treat them like memes instead of getting in as
early as possible and riding it out"). Pure. Scores a launch on the evidence a REAL project leaves and a meme doesn't, from the research packet
the office already reads (social_research.packet: website · X · Telegram · legal · narrative) plus the desk row's market numbers. Every point is a
cited part; a fact we could not read scores 0 and is NAMED (never a fake value). A site showing ANOTHER coin's CA, a copycat or an X that
belongs to someone else = out.

It is a LIST + a RECORD, never a buy: each pick is noted once at its price and graded 1h and 24h later (a project thesis is a hold, so the 24h
number is the one that decides). The kernel driver `src:rpf` carries no belief — only that record can ever weigh it."""
import time

REAL, MAYBE = 50, 35                 # grade lines: ≥ 50 REAL PROJECT · 35–49 MAYBE · below = MEME
PROJECT_NARR = ('UTILITY / PROJECT', 'AI / TECH', 'COMMUNITY')
H1, H24, GONE = 3600, 86400, 1800   # grade horizons; no price for 30 min past a horizon = −100% (vanished)
KEEP = 400                          # settled picks kept
PROVEN_N = 10


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def score(p, row=None, now=None):
    """→ {score 0–100, grade REAL | MAYBE | MEME | OUT, parts [(why, pts)], unknown [what we could not read], out reason | None}."""
    now = time.time() if now is None else now
    p, r = p or {}, row or {}
    s, x, cr, lg = p.get('website') or {}, p.get('x') or {}, p.get('cross') or {}, p.get('legal') or {}
    parts, unk = [], []
    add = lambda why, pts: parts.append((why, pts))
    if cr.get('conflict') or cr.get('copycat') or s.get('mintMatch') == 'no':
        return {'score': 0, 'grade': 'OUT', 'parts': [], 'unknown': [], 'out': 'its own links point at another coin / a copycat'}
    # 🌐 the website — a project builds one before launch and shows its contract
    if not s.get('url'):
        unk.append('no website')
    elif s.get('reachable') is False:
        add("website doesn't load", -4)
    else:
        add('website shows THIS contract', 16) if s.get('mintMatch') == 'yes' else add('website loads', 6)
        dm = s.get('domain') or {}
        age = dm.get('ageDays')
        if dm.get('free') or (age is not None and age > 3650):   # a free host / a decade-old platform domain says nothing about THIS project
            unk.append('domain age (hosted on a big platform)')
        elif age is None:
            unk.append('domain age')
        elif age >= 30:
            add(f'domain {int(age)} days old — registered long before launch', 14)
        elif age >= 7:
            add(f'domain {int(age)} days old', 6)
        elif age < 2:
            add('domain registered in the last 2 days', -6)
        if s.get('docs'):
            add('docs / whitepaper / GitHub linked', 10)
    # 𝕏 — a real team has a history, an audience and talks about the coin
    if not x.get('url'):
        unk.append('no X')
    elif not x.get('available'):
        unk.append('X behind a login wall')
    else:
        fol = x.get('followers')
        if fol is not None:
            add(f'{int(fol):,} X followers', 12 if fol >= 5000 else 8 if fol >= 1000 else 3 if fol >= 200 else 0)
        jd = (now - _f(x['joined'])) / 86400 if x.get('joined') else None
        if jd is None:
            unk.append('X account age')
        elif jd >= 90:
            add(f'X account {int(jd)} days old', 10)
        elif jd >= 30:
            add(f'X account {int(jd)} days old', 5)
        elif jd < 7:
            add('X account under a week old', -4)
        if x.get('mintMentioned'):
            add('X names this contract', 6)
        if x.get('lastPostAt') and now - _f(x['lastPostAt']) <= 86400:
            add('X posted in the last 24h', 4)
    if (p.get('tg') or {}).get('url') if isinstance(p.get('tg'), dict) else s.get('tg'):
        add('Telegram linked', 3)
    lvl = lg.get('level')
    if lvl == 'PARTIAL':
        add('legal entity / registration shown', 8)
    elif lvl == 'WEAK':
        add('terms / legal page found', 3)
    cls = (p.get('narrative') or {}).get('class')
    if cls in PROJECT_NARR:
        add(f'narrative reads {cls}', 6)
    elif cls in ('MEME', 'ANIMAL', 'TREND PARODY', 'CELEBRITY / PERSON'):
        add(f'narrative reads {cls}', -4)
    # 📈 the market agrees it is alive
    org = _f((r.get('vital') or {}).get('organicPct') or r.get('organicPct'), -1)
    if org >= 20:
        add(f'{int(org)}% organic volume', 5)
    elif org < 0:
        unk.append('organic share')
    if _f(r.get('liq')) >= 20000:
        add(f"${_f(r.get('liq')) / 1000:.0f}K pool", 4)
    sc = max(0, min(100, round(sum(pts for _, pts in parts))))
    return {'score': sc, 'grade': 'REAL' if sc >= REAL else 'MAYBE' if sc >= MAYBE else 'MEME', 'parts': parts, 'unknown': unk, 'out': None}


def board(packets, rows_by, now=None, limit=30):
    """Every researched coin scored, REAL first then MAYBE (memes and outs dropped), best score first."""
    out = []
    for m, p in (packets or {}).items():
        if not isinstance(p, dict) or p.get('failed'):
            continue
        r = (rows_by or {}).get(m) or {}
        sc = score(p, r, now)
        if sc['grade'] in ('REAL', 'MAYBE'):
            out.append({'mint': m, 'symbol': p.get('symbol') or r.get('symbol'), 'pair': r.get('pair') or r.get('pairAddress'), 'cap': r.get('mcap') or r.get('cap'),
                        'ageH': r.get('ageH'), 'site': (p.get('website') or {}).get('url'), 'x': (p.get('x') or {}).get('url'), 'researchedAt': p.get('at'), **sc})
    return sorted(out, key=lambda o: (o['grade'] != 'REAL', -o['score']))[:limit]


def track(state, picks, price_of, now):
    """Note each REAL / MAYBE pick ONCE at its price; settle at 1h and 24h (no price 30 min past a horizon = −100%). → new state."""
    st = {'open': dict((state or {}).get('open') or {}), 'done': list((state or {}).get('done') or [])}
    for m, o in list(st['open'].items()):
        for h, k in ((H1, 'pct1h'), (H24, 'pct24h')):
            if o.get(k) is None and now - _f(o['at']) >= h:
                px = _f(price_of(m))
                if px > 0:
                    o[k] = round((px / _f(o['px']) - 1) * 100, 2)
                elif now - _f(o['at']) >= h + GONE:
                    o[k] = -100.0
        if o.get('pct24h') is not None:
            st['done'].append({**o, 'mint': m}); st['open'].pop(m)
    seen = set(st['open']) | {d.get('mint') for d in st['done'][-KEEP:] if now - _f(d.get('at')) < 7 * 86400}
    for pk in picks or []:
        px = _f(price_of(pk['mint']))
        if pk['mint'] not in seen and px > 0:
            st['open'][pk['mint']] = {'px': px, 'at': now, 'grade': pk['grade'], 'score': pk['score'], 'symbol': pk.get('symbol')}
    st['done'] = st['done'][-KEEP:]
    return st


def _med(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 1)


def proof(state):
    """The finder's own record by grade: n, typical 1h, typical 24h, % up at 24h; `proven` = ≥ 10 settled with a positive typical 24h AND ≥ half up."""
    out = {}
    for g in ('REAL', 'MAYBE'):
        rows = [d for d in (state or {}).get('done') or [] if d.get('grade') == g]
        h24 = [_f(d.get('pct24h')) for d in rows]
        open_1h = [_f(o.get('pct1h')) for o in ((state or {}).get('open') or {}).values() if o.get('grade') == g and o.get('pct1h') is not None]
        won = round(100 * sum(1 for v in h24 if v > 0) / len(h24)) if h24 else None
        m24 = _med(h24)
        out[g] = {'n': len(h24), 'med1h': _med([_f(d.get('pct1h')) for d in rows] + open_1h), 'med24h': m24, 'wonPct': won,
                  'open': sum(1 for o in ((state or {}).get('open') or {}).values() if o.get('grade') == g),
                  'proven': bool(len(h24) >= PROVEN_N and m24 is not None and m24 > 0 and (won or 0) >= 50)}
    return out
