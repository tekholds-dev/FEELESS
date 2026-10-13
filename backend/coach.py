"""👑 THE COACH — the creator (and the model, inside tighter bounds) STRENGTHEN the agents with directives the desk actually uses
(owner, 2026-10-13: "I the creator can strengthen agents and advise to pull coins on seats with a reason that can be used and vital, not
just a note … AI should be able to understand and instruct / strengthen agents"). Pure + tested (`tests/test_coach.py`).

A DIRECTIVE = one cause from a FIXED vocabulary (`CAUSES` — the same features the Judge's repeat-loss rules test on a live coin,
`opportunity.judge_hits`) + points. It reaches the kernel as a ranking weight beside the Judge's own (`pens`): every coin the cause
matches ranks down, all penalties together never under the brain's floor. A directive NEVER buys, sells, sizes or blocks a seat.

  owner  −8 by default (strengthened: −12), lives 24h, refreshed each time the owner repeats it
  ai     −4 only, lives 6h — the owner may ✅ strengthen it into an owner rule or ✕ kill it
  PULL + TEACH: the owner pulls a coin off a seat WITH a cause → the existing sell path sells it (not here), the cause becomes an owner
  directive, and that coin is off the agents' buy list for 6h.

Also here: `trade_tape` — every real agent trade as ONE story (decision → fill → the agents' reason → the model's read → exit → result →
the Judge's ruling), built only from records that already exist (ledger rows, the archive, the Judge's reviews, the model's log).
"""

CAUSES = {
    'crowd fomo': "bought the crowd's top (launch phase CROWD FOMO)",
    'bundled': 'a bundled / insider-like launch',
    'early selling': 'early wallets were unloading',
    'falling now': 'it was falling when we bought (−3% in 5 min)',
    'thin pool': 'the pool was under $20K',
    'weak holders': 'top-10 wallets held 30%+',
    'chart says wait': 'the chart did not say ENTER NOW',
    'thin data': 'the chart data was sparse / stale',
}
OWNER_PTS, OWNER_MAX, AI_PTS = -8.0, -12.0, -4.0
OWNER_TTL, AI_TTL = 24 * 3600.0, 6 * 3600.0
BLOCK_SEC = 6 * 3600.0
MAX_RULES = 12
LOG_KEEP = 60
WHY_LEN = 120


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def _why(v):
    return ' '.join(str(v or '').split())[:WHY_LEN]


def new_state():
    return {'rules': [], 'blocked': {}, 'log': [], 'n': 0}


def _st(state):
    s = dict(state or {})
    return {'rules': [dict(r) for r in s.get('rules') or []], 'blocked': dict(s.get('blocked') or {}), 'log': list(s.get('log') or []), 'n': int(_f(s.get('n')))}


def active(state, now):
    """The directives still alive, strongest first."""
    return sorted([r for r in (state or {}).get('rules') or [] if _f(r.get('until')) > now], key=lambda r: _f(r.get('points')))


def add(state, key, by, why, now, mint=None, sym=None, strong=False):
    """One directive. → (state, rule) or (state, None) when the cause is not in the vocabulary / the writer is unknown.
    The same cause from the same writer is REFRESHED (never stacked); an AI directive never overrides an owner one."""
    s = _st(state)
    key = str(key or '').strip().lower()
    if key not in CAUSES or by not in ('owner', 'ai'):
        return s, None
    s['rules'] = [r for r in s['rules'] if _f(r.get('until')) > now]
    if by == 'ai' and any(r['key'] == key and r['by'] == 'owner' for r in s['rules']):
        return s, None
    pts = (OWNER_MAX if strong else OWNER_PTS) if by == 'owner' else AI_PTS
    old = next((r for r in s['rules'] if r['key'] == key and r['by'] == by), None)
    if old:
        old.update(points=min(_f(old.get('points')), pts), why=_why(why) or old.get('why'), at=now, until=now + (OWNER_TTL if by == 'owner' else AI_TTL), n=int(_f(old.get('n'))) + 1,
                   **({'sym': sym} if sym else {}))
        rule = old
    else:
        s['n'] += 1
        rule = {'id': s['n'], 'key': key, 'by': by, 'points': pts, 'why': _why(why), 'at': now, 'until': now + (OWNER_TTL if by == 'owner' else AI_TTL), 'n': 1, **({'sym': sym} if sym else {})}
        s['rules'].append(rule)
        s['rules'] = sorted(s['rules'], key=lambda r: (r['by'] != 'owner', -_f(r.get('at'))))[:MAX_RULES]
    if mint:
        s['blocked'][mint] = now + BLOCK_SEC
    s['log'] = (s['log'] + [{'at': now, 'by': by, 'key': key, 'why': rule['why'], 'points': rule['points'], **({'sym': sym} if sym else {}), **({'pull': True} if mint else {})}])[-LOG_KEEP:]
    return s, rule


def strengthen(state, rid, now):
    """✅ The owner backs a directive (the model's or their own): it becomes an owner rule at full strength for 24h."""
    s = _st(state)
    r = next((r for r in s['rules'] if r.get('id') == rid and _f(r.get('until')) > now), None)
    if not r:
        return s, None
    s['rules'] = [x for x in s['rules'] if not (x is not r and x['key'] == r['key'] and x['by'] == 'owner')]
    r.update(by='owner', points=OWNER_MAX, at=now, until=now + OWNER_TTL, backed=True)
    s['log'] = (s['log'] + [{'at': now, 'by': 'owner', 'key': r['key'], 'why': 'strengthened', 'points': OWNER_MAX}])[-LOG_KEEP:]
    return s, r


def kill(state, rid, now):
    s = _st(state)
    r = next((r for r in s['rules'] if r.get('id') == rid), None)
    if not r:
        return s, None
    s['rules'] = [x for x in s['rules'] if x is not r]
    s['log'] = (s['log'] + [{'at': now, 'by': 'owner', 'key': r['key'], 'why': 'killed', 'points': 0}])[-LOG_KEEP:]
    return s, r


def pens(state, now, base=None):
    """{cause: points} for the kernel — the coach's live directives merged with the Judge's own (the stronger of the two per cause)."""
    out = {k: _f(v) for k, v in (base or {}).items()}
    for r in active(state, now):
        out[r['key']] = min(out.get(r['key'], 0.0), _f(r.get('points')))
    return out


def blocked(state, now):
    """Coins the owner pulled with a reason: off the agents' buy list until the block runs out."""
    return {m for m, until in ((state or {}).get('blocked') or {}).items() if _f(until) > now}


def prune(state, now):
    s = _st(state)
    s['rules'] = [r for r in s['rules'] if _f(r.get('until')) > now]
    s['blocked'] = {m: u for m, u in s['blocked'].items() if _f(u) > now}
    return s


def from_ai(advice):
    """The model's `directives` → [(cause, why)] — only causes from the vocabulary, at most 2 an answer."""
    out = []
    for d in (advice or {}).get('directives') or []:
        if isinstance(d, dict) and str(d.get('key') or '').strip().lower() in CAUSES:
            k = str(d['key']).strip().lower()
            if k not in [x for x, _ in out]:
                out.append((k, _why(d.get('why'))))
    return out[:2]


def coach_case(reviews, mem=None, rules=None):
    """What the model coach is shown: the last real trades as cause / result lines, the memory's worst buckets, the directives already
    live and the vocabulary it may answer from. Small, text only — one cheap cloud call."""
    rv = [r for r in reviews or [] if r.get('pct') is not None][-12:]
    losses = [f"{r.get('sym')}: {_f(r.get('pct')):+.0f}% · {r.get('cause') or r.get('lossClass') or 'no cause'} · phase {r.get('phase') or '?'} · {r.get('cls') or '?'} · held {_f(r.get('held')):.0f}m" for r in rv if _f(r.get('pct')) < 0][-5:]
    wins = [f"{r.get('sym')}: {_f(r.get('pct')):+.0f}% · phase {r.get('phase') or '?'} · held {_f(r.get('held')):.0f}m" for r in rv if _f(r.get('pct')) > 0][-5:]
    return {'symbol': 'DESK', 'state': 'coach', 'losses': losses, 'wins': wins,
            'memory': ' · '.join(f"{k} {e:+.0f}% (n {n})" for e, k, n in (mem or {}).get('worst') or [][:4])[:230] or None,
            'rules': [f"{r['key']} {r['points']:+.0f} by {r['by']}" for r in rules or []][:5], 'vocab': list(CAUSES)[:8]}


def view(state, now, judge_pens=None):
    """The page's coach box: every weight on the ranking right now (owner · ai · judge) + the vocabulary + the last moves."""
    rows = [{**r, 'left': round(_f(r['until']) - now), 'words': CAUSES.get(r['key'])} for r in active(state, now)]
    mine = {r['key'] for r in rows}
    rows += [{'id': None, 'key': k, 'by': 'judge', 'points': _f(p), 'why': 'repeat real-loss cause (≥ 3 of the last 20 reviews)', 'words': CAUSES.get(k)} for k, p in (judge_pens or {}).items() if k not in mine]
    return {'rules': rows, 'causes': [{'key': k, 'words': w} for k, w in CAUSES.items()], 'blocked': len(blocked(state, now)),
            'log': list(reversed(((state or {}).get('log') or [])[-12:])), 'pts': {'owner': OWNER_PTS, 'strong': OWNER_MAX, 'ai': AI_PTS}}


# ── 🎬 the real trade tape ───────────────────────────────────────────────────────────────────────────────────────────────────────
def trade_tape(ledger, positions, reviews=None, ai_log=None, card=None, n=30):
    """Every REAL agent trade, newest first, as one story built from records that already exist:
      buy  = the confirmed fill (ledger): $ in, fill price vs the market price of the decision (`slipPct`), seconds to land, tx
      why  = the agents' door / tag + the entry thesis (archive) · ai = the model's read of that coin nearest the buy (its log)
      sell = the confirmed exit fills · result = real % (archive) · judge = the Judge's ruling (cause · desk · words)
    An open position has no sell / result yet. Nothing is estimated: a missing piece is absent."""
    buys = [r for r in ledger or [] if r.get('side') == 'buy' and r.get('status') == 'filled' and r.get('agent') and r.get('sig') and (card is None or r.get('card') == card)]
    sells = [r for r in ledger or [] if r.get('side') == 'sell' and r.get('status') == 'filled' and r.get('sig') and (card is None or r.get('card') == card)]
    pos_by = {}
    for p in positions or []:
        pos_by.setdefault(p.get('mint'), []).append(p)
    rev_by = {}
    for r in reviews or []:
        rev_by.setdefault(r.get('mint'), []).append(r)
    out = []
    for b in sorted(buys, key=lambda r: -_f(r.get('confirmedAt') or r.get('at')))[:n]:
        t = _f(b.get('confirmedAt') or b.get('at'))
        m = b.get('mint')
        nxt = min([_f(x.get('confirmedAt') or x.get('at')) for x in buys if x.get('mint') == m and _f(x.get('confirmedAt') or x.get('at')) > t] or [float('inf')])
        ss = [s for s in sells if s.get('mint') == m and t < _f(s.get('confirmedAt') or s.get('at')) <= nxt]
        p = next((p for p in sorted(pos_by.get(m) or [], key=lambda p: abs(_f(p.get('since')) - t)) if abs(_f(p.get('since')) - t) <= 900), None)
        rv = next((r for r in rev_by.get(m) or [] if p and abs(_f(r.get('at')) - _f(p.get('closedAt'))) <= 120), None)
        ai = next((a for a in sorted(ai_log or [], key=lambda a: abs(_f(a.get('at')) - t)) if a.get('mint') == m and abs(_f(a.get('at')) - t) <= 1800), None)
        mid, px = _f(b.get('midPx')), _f(b.get('px'))
        th = (p or {}).get('thesis') or {}
        row = {'mint': m, 'sym': b.get('symbol'), 'at': t,
               'buy': {'usd': _f(b.get('usd')) or None, 'px': px or None, 'mid': mid or None, 'slipPct': round((px / mid - 1) * 100, 2) if px > 0 and mid > 0 else None,
                       'landSec': b.get('landSec'), 'impactPct': b.get('impactPct'), 'sig': b.get('sig'), 'why': b.get('why')},
               'why': {'tag': (p or {}).get('tag'), 'structure': th.get('structure'), 'rule': th.get('triggerRule'), 'src': list((p or {}).get('src') or [])[:5] or None,
                       'phase': ((p or {}).get('li') or {}).get('phase'), 'size': (p or {}).get('warden')},
               'ai': {k: ai.get(k) for k in ('stance', 'summary', 'risk_flags', 'label', 'role')} if ai else None,
               'sells': [{'at': _f(s.get('confirmedAt') or s.get('at')), 'usd': _f(s.get('usd')) or None, 'why': s.get('why'), 'sig': s.get('sig'), 'landSec': s.get('landSec')} for s in sorted(ss, key=lambda s: _f(s.get('confirmedAt') or s.get('at')))][:4],
               'open': not (p and p.get('closedAt')) and not ss}
        if p and p.get('closedAt') and p.get('realPct') is not None:
            usd = _f(b.get('usd'))
            row['result'] = {'pct': round(_f(p['realPct']), 2), 'usd': round(sum(_f(s.get('usd')) for s in ss) - usd, 3) if ss and usd else None, 'peak': p.get('peak'),
                             'heldMin': round((_f(p['closedAt']) - _f(p.get('since'))) / 60, 1) if p.get('since') else None, 'rule': p.get('rule')}
        if rv:
            row['judge'] = {k: rv.get(k) for k in ('kind', 'cause', 'lossClass', 'desk', 'why', 'change') if rv.get(k) is not None}
        out.append(row)
    return out


def tape_stats(rows):
    """One line over the tape's closed trades — counts and a median, never a sum of percentages."""
    done = sorted(_f(r['result']['pct']) for r in rows or [] if r.get('result'))
    slips = sorted(_f(r['buy']['slipPct']) for r in rows or [] if (r.get('buy') or {}).get('slipPct') is not None)
    med = lambda v: round(v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2, 2) if v else None
    return {'n': len(done), 'won': sum(1 for x in done if x > 0), 'medPct': med(done), 'open': sum(1 for r in rows or [] if r.get('open')), 'medSlipPct': med(slips)}


# ── 📏 graded on REAL fills: every source list and every exit rule gets its own record ───────────────────────────────────────────
SRC_MIN_N = 8          # a source needs this many real exits before its record weighs
SRC_BAD_MED = -15.0    # … and a typical real result this bad
SRC_DOWN = 0.9         # a coin ALL of whose sources are proven losers ranks down 10% (one decent source = no penalty)


def _med(v):
    v = sorted(v)
    return round(v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2, 2) if v else None


def _rec(groups):
    return {k: {'n': len(v), 'med': _med(v), 'won': sum(1 for x in v if x > 0)} for k, v in groups.items() if v}


def source_record(positions):
    """{source: {n, med, won}} over confirmed real exits — a coin counts for every source that listed it. Results capped at ±100%."""
    g = {}
    for p in positions or []:
        if p.get('confirmed') and p.get('realPct') is not None:
            for s_ in list(p.get('src') or [])[:6]:
                g.setdefault(str(s_), []).append(max(-100.0, min(100.0, _f(p['realPct']))))
    return _rec(g)


def source_factor(rec, srcs):
    """×0.9 when EVERY source that listed this coin is a proven loser on real money; else ×1.0 (unknown / unproven = not judged)."""
    known = [rec.get(str(s_)) for s_ in srcs or [] if rec.get(str(s_))]
    if not known or len(known) < len(list(srcs or [])):
        return 1.0
    return SRC_DOWN if all(r['n'] >= SRC_MIN_N and _f(r['med']) <= SRC_BAD_MED for r in known) else 1.0


def rule_record(positions):
    """{exit rule id: {n, med, won}} over confirmed real exits (R4f sellers took over, R4c buying climax, R5 stop, R7 trail …) — how each
    exit rule's trades really ended. The new tape exits are judged here before anyone trusts them."""
    g = {}
    for p in positions or []:
        if p.get('confirmed') and p.get('realPct') is not None and p.get('rule'):
            k = str(p['rule']).split(' ')[0]
            g.setdefault(k if k[:1] == 'R' and k[1:2].isdigit() else 'other', []).append(max(-100.0, min(100.0, _f(p['realPct']))))
    return _rec(g)
