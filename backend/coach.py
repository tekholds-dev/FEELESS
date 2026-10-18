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

import real_memory as _rmem

CAUSES = {
    'crowd fomo': "bought the crowd's top (launch phase CROWD FOMO)",
    'bundled': 'a bundled / insider-like launch',
    'early selling': 'early wallets were unloading',
    'falling now': 'it was falling when we bought (−3% in 5 min)',
    'thin pool': 'the pool was under $20K',
    'weak holders': 'top-10 wallets held 30%+',
    'chart says wait': 'the chart did not say ENTER NOW',
    'thin data': 'the chart data was sparse / stale',
    'fake candles': 'a straight run of green candles, no red (painted)',
    'same narrative': 'the same theme / name the card already holds or just traded',
    'copycat': 'a copycat of a ticker wave, not the original',
    'clone': 'the same ticker as a coin already traded / a bigger original',
}
OWNER_PTS, OWNER_MAX, AI_PTS = -8.0, -12.0, -4.0
OWNER_TTL, AI_TTL = 24 * 3600.0, 6 * 3600.0
BLOCK_SEC = 6 * 3600.0
MAX_RULES = 12
LOG_KEEP = 60
WHY_LEN = 120
GRADE_SEC = 1800.0     # a coin a directive ranked down is judged 30 min later …
GRADE_GONE_SEC = 7200.0  # … no price for 2h = it is gone (−100%)
GRADE_AGAIN = 6 * 3600.0  # the same coin is noted for the same cause at most every 6h
GRADE_MIN_N = 10       # a directive's own record weighs from 10 judged coins
GRADE_BAD_MED = 3.0    # coins it ranked DOWN went UP a typical 3%+ → the lesson is wrong
GRADE_OPEN, GRADE_DONE = 300, 60


from fnum import nan_safe as _f


def _why(v):
    return ' '.join(str(v or '').split())[:WHY_LEN]


def new_state():
    return {'rules': [], 'blocked': {}, 'log': [], 'n': 0}


def _st(state):
    s = dict(state or {})
    return {'rules': [dict(r) for r in s.get('rules') or []], 'blocked': dict(s.get('blocked') or {}), 'log': list(s.get('log') or []), 'n': int(_f(s.get('n'))),
            **({'grade': s['grade']} if s.get('grade') else {})}


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


def coach_case(reviews, mem=None, rules=None, grades_=None, exits=None, speed=None):
    """What the model coach is shown: the last real trades as cause / result lines, the memory's worst buckets, the directives already
    live and the vocabulary it may answer from. Small, text only — one cheap cloud call."""
    rv = [r for r in reviews or [] if r.get('pct') is not None][-12:]
    losses = [f"{r.get('sym')}: {_f(r.get('pct')):+.0f}% · {r.get('cause') or r.get('lossClass') or 'no cause'} · phase {r.get('phase') or '?'} · {r.get('cls') or '?'} · held {_f(r.get('held')):.0f}m" for r in rv if _f(r.get('pct')) < 0][-5:]
    wins = [f"{r.get('sym')}: {_f(r.get('pct')):+.0f}% · phase {r.get('phase') or '?'} · held {_f(r.get('held')):.0f}m" for r in rv if _f(r.get('pct')) > 0][-5:]
    return {'symbol': 'DESK', 'state': 'coach', 'losses': losses, 'wins': wins,
            'memory': ' · '.join(f"{k} {e:+.0f}% (n {n})" for e, k, n in (mem or {}).get('worst') or [][:4])[:230] or None,
            'rules': [f"{r['key']} {r['points']:+.0f} by {r['by']}" + (f" · its record: {g['verdict']}, coins it ranked down {_f(g['med']):+.0f}% (n {g['n']})" if (g := (grades_ or {}).get(r['key'])) else '') for r in rules or []][:5],
            # what the desk has MEASURED since the last coaching (so the model instructs from evidence, not from a vibe)
            'exits': ' · '.join(f"{k} {_f(v.get('med')):+.0f}% (n {v.get('n')})" for k, v in sorted((exits or {}).items(), key=lambda kv: _f(kv[1].get('med')))[:6] if v.get('n', 0) >= 3)[:230] or None,
            'speed': (f"call→sent {_f(speed.get('medWaitSec')):.0f}s · sent→landed {_f(speed.get('medLandSec')):.0f}s · fills {_f(speed.get('medSlipPct')):+.1f}% vs the call" if speed and speed.get('medWaitSec') is not None else None),
            'vocab': list(CAUSES)}


# ── 📏 every directive is GRADED on what the coins it ranked down did next (a bad lesson expires on evidence) ─────────────────────
def grade_note(state, hits, now):
    """`hits` = {cause: [(mint, sym, px)]} — the coins a LIVE directive matched this pass. Each coin is noted once per cause per 6h at
    its price; nothing is bought, sold or blocked by a note."""
    s = _st(state)
    g = dict(s.get('grade') or {})
    opn, seen = list(g.get('open') or []), dict(g.get('seen') or {})
    for key, rows in (hits or {}).items():
        if key not in CAUSES:
            continue
        for mint, sym, px in rows or []:
            k = f'{key}|{mint}'
            if not mint or _f(px) <= 0 or (k in seen and now - _f(seen[k]) < GRADE_AGAIN):
                continue
            seen[k] = now
            opn.append({'key': key, 'mint': mint, 'sym': sym, 'px': _f(px), 'at': now})
    g.update(open=opn[-GRADE_OPEN:], seen={k: t for k, t in seen.items() if now - _f(t) < GRADE_AGAIN})
    s['grade'] = g
    return s


def grade_settle(state, prices, now):
    """Notes ≥ 30 min old are judged at the coin's price now (`prices` {mint: px}); no price for 2h = −100%. → (state, settled n)"""
    s = _st(state)
    g = dict(s.get('grade') or {})
    done, keep, n = {k: list(v) for k, v in (g.get('done') or {}).items()}, [], 0
    for o in g.get('open') or []:
        age, px = now - _f(o.get('at')), _f((prices or {}).get(o.get('mint')))
        if age < GRADE_SEC or (px <= 0 and age < GRADE_GONE_SEC):
            keep.append(o); continue
        pct = max(-100.0, min(300.0, (px / _f(o['px']) - 1) * 100)) if px > 0 else -100.0
        done[o['key']] = (done.get(o['key'], []) + [round(pct, 1)])[-GRADE_DONE:]
        n += 1
    g.update(open=keep, done=done)
    s['grade'] = g
    return s, n


def grades(state):
    """{cause: {n, med, up, verdict}} — what the coins each directive ranked down did in the next 30 min. `right` = they typically
    fell (the lesson holds) · `wrong` = they typically ROSE 3%+ (it ranks winners down) · `open` = under 10 judged or in between."""
    out = {}
    for k, v in (((state or {}).get('grade') or {}).get('done') or {}).items():
        if not v:
            continue
        med = _med(v)
        out[k] = {'n': len(v), 'med': med, 'up': sum(1 for x in v if x > 0),
                  'verdict': 'open' if len(v) < GRADE_MIN_N else 'wrong' if med >= GRADE_BAD_MED else 'right' if med < 0 else 'open'}
    return out


def drop_wrong(state, now):
    """A MODEL directive whose own record says it is wrong ends now (logged). An owner directive is never ended for them — the page
    shows its record and the owner decides. → (state, [ended causes])"""
    s = _st(state)
    gr = grades(s)
    bad = [r for r in s['rules'] if r.get('by') == 'ai' and _f(r.get('until')) > now and (gr.get(r['key']) or {}).get('verdict') == 'wrong']
    if not bad:
        return s, []
    s['rules'] = [r for r in s['rules'] if r not in bad]
    s['log'] = (s['log'] + [{'at': now, 'by': 'record', 'key': r['key'], 'points': 0,
                             'why': f"ended by its own record: coins it ranked down rose a typical {gr[r['key']]['med']:+.1f}% (n {gr[r['key']]['n']})"} for r in bad])[-LOG_KEEP:]
    return s, [r['key'] for r in bad]


def view(state, now, judge_pens=None):
    """The page's coach box: every weight on the ranking right now (owner · ai · judge) + its own record + the vocabulary + the last moves."""
    gr = grades(state)
    rows = [{**r, 'left': round(_f(r['until']) - now), 'words': CAUSES.get(r['key'])} for r in active(state, now)]
    mine = {r['key'] for r in rows}
    rows += [{'id': None, 'key': k, 'by': 'judge', 'points': _f(p), 'why': 'repeat real-loss cause (≥ 3 of the last 20 reviews)', 'words': CAUSES.get(k)} for k, p in (judge_pens or {}).items() if k not in mine]
    rows = [{**r, 'grade': gr.get(r['key'])} for r in rows]
    return {'rules': rows, 'causes': [{'key': k, 'words': w, 'grade': gr.get(k)} for k, w in CAUSES.items()], 'blocked': len(blocked(state, now)),
            'watching': len(((state or {}).get('grade') or {}).get('open') or []),
            'log': list(reversed(((state or {}).get('log') or [])[-12:])), 'pts': {'owner': OWNER_PTS, 'strong': OWNER_MAX, 'ai': AI_PTS}}


# ── 🎬 the real trade tape ───────────────────────────────────────────────────────────────────────────────────────────────────────
def merge_topups(buys, sells):
    """🧩 ONE story per position: a buy of a coin still held is a TOP-UP folded into the position's first buy — "still held" counted in
    UNITS (bought − sold), so a trim (a partial sale) never ends the position (2026-10-17: $Glow's trim read "SOLD −59%" and the idle-cash
    top-up after it read as a new trade). Each kept buy carries `unitsIn` (every unit the position bought)."""
    t_ = lambda r: _f(r.get('confirmedAt') or r.get('at'))
    ev = sorted([('b', r) for r in buys or []] + [('s', r) for r in sells or []], key=lambda x: t_(x[1]))
    out, open_ = [], {}
    for k, r in ev:
        m = r.get('mint')
        cur = open_.get(m)
        if k == 's':
            if cur is not None:
                cur['left'] = _f(cur.get('left')) - _f(r.get('units'))
                cur['sold'] = True
            continue
        u = _f(r.get('units'))
        if cur is not None and (cur['left'] > 0.02 * _f(cur['row'].get('unitsIn')) if _f(cur['row'].get('unitsIn')) > 0 and u > 0 else not cur.get('sold')):   # no units on record: a sale in between = a new trade (the old rule)
            fb = cur['row']
            fb['usd'] = round(_f(fb.get('usd')) + _f(r.get('usd')), 6)
            fb['topups'] = int(fb.get('topups') or 0) + 1
            fb['unitsIn'] = _f(fb.get('unitsIn')) + u
            cur['left'] = _f(cur.get('left')) + u
            continue
        nb = dict(r)
        nb['unitsIn'] = u
        open_[m] = {'row': nb, 'left': u}
        out.append(nb)
    return out


def trade_tape(ledger, positions, reviews=None, ai_log=None, card=None, n=60):
    """Every REAL agent trade, newest first, as one story built from records that already exist:
      buy  = the confirmed fill (ledger): $ in, fill price vs the market price of the decision (`slipPct`), seconds to land, tx
      why  = the agents' door / tag + the entry thesis (archive) · ai = the model's read of that coin nearest the buy (its log)
      sell = the confirmed exit fills · result = real % (archive) · judge = the Judge's ruling (cause · desk · words)
    An open position has no sell / result yet. Nothing is estimated: a missing piece is absent."""
    # every confirmed buy on the card — the agents' AND the owner's own picks (2026-10-15: "where my coins Macca and STREAM?" — they were left out)
    buys = [r for r in ledger or [] if r.get('side') == 'buy' and r.get('status') == 'filled' and r.get('sig') and (card is None or r.get('card') == card)
            and (r.get('agent') or r.get('picked'))]
    sells = [r for r in ledger or [] if r.get('side') == 'sell' and r.get('status') == 'filled' and r.get('sig') and (card is None or r.get('card') == card)]
    buys = merge_topups(buys, sells)
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
        left_ = (_f(b.get('unitsIn')) - sum(_f(s.get('units')) for s in ss)) if _f(b.get('unitsIn')) > 0 else 0.0   # units still on the card
        row = {'mint': m, 'sym': b.get('symbol'), 'at': t, 'who': 'models' if (b.get('aiSeat') or (p or {}).get('g4')) else 'agents' if b.get('agent') else 'you',   # 🔁 an OSSY / G4 buy is flagged `picked` (your pick limits) — never call it yours
               'buy': {'usd': _f(b.get('usd')) or None, 'px': px or None, 'mid': mid or None, 'slipPct': round((px / mid - 1) * 100, 2) if px > 0 and mid > 0 else None,
                       'landSec': b.get('landSec'), 'impactPct': b.get('impactPct'), 'sig': b.get('sig'), 'why': b.get('why'),
                       # decided → sent: the thesis is written the moment the fill was allowed; the keeper's send is stamped on the row
                       'waitSec': round(_f(b.get('sentAt')) - _f(th.get('at')), 1) if th.get('at') and 0 <= _f(b.get('sentAt')) - _f(th.get('at')) <= 1800 else None},
               'why': {'tag': (p or {}).get('tag'), 'structure': th.get('structure'), 'rule': th.get('triggerRule'), 'src': list((p or {}).get('src') or [])[:5] or None,
                       'phase': ((p or {}).get('li') or {}).get('phase'), 'size': (p or {}).get('warden')},
               'ai': {k: ai.get(k) for k in ('stance', 'summary', 'risk_flags', 'label', 'role')} if ai else None,
               'sells': [{'at': _f(s.get('confirmedAt') or s.get('at')), 'usd': _f(s.get('usd')) or None, 'why': s.get('why'), 'sig': s.get('sig'), 'landSec': s.get('landSec')} for s in sorted(ss, key=lambda s: _f(s.get('confirmedAt') or s.get('at')))][:4],
               'open': not (p and p.get('closedAt')) and not ss,
               # still held · part sold (a sale landed, the position is still open) · sold — the tape says which (owner, 2026-10-15)
               'state': 'held' if not ss and not (p and p.get('closedAt')) else 'part' if ss and ((p and not p.get('closedAt')) or left_ > 0.02 * _f(b.get('unitsIn'))) else 'sold'}
        if row['state'] == 'part':
            row['open'] = True
            cs_ = [s for s in ss if _f(s.get('costUsd')) > 0]
            if cs_:   # 💰 what the trims banked so far: each sale against what ITS coins cost (a trim in profit is never a loss)
                got_, cost_ = sum(_f(s.get('usd')) for s in cs_), sum(_f(s.get('costUsd')) for s in cs_)
                row['banked'] = {'usd': round(got_ - cost_, 3), 'pct': round((got_ / cost_ - 1) * 100, 2), 'sold': round(got_, 3), 'n': len(cs_)}
        row['closedAt'] = (_f(p.get('closedAt')) if p and p.get('closedAt') else (_f(ss[-1].get('confirmedAt') or ss[-1].get('at')) if ss and row['state'] == 'sold' else None)) or None   # 🏁 the Trades tab sorts closes by THIS
        if row['state'] == 'sold' and ss and _f(b.get('usd')) > 0:
            # 🏁 the WHOLE position from the ledger's own fills: every sale (trims included) against everything put in (top-ups included) —
            # the archive's % only knows the last sale (2026-10-17: a trimmed winner read as a loss)
            usd, out_ = _f(b.get('usd')), sum(_f(s.get('usd')) for s in ss)
            row['result'] = {'pct': round((out_ / usd - 1) * 100, 2), 'usd': round(out_ - usd, 3), 'peak': None,
                             'heldMin': round((_f(ss[-1].get('confirmedAt') or ss[-1].get('at')) - t) / 60, 1), 'rule': ((p or {}).get('rule') or ss[-1].get('why') or None), 'src': 'ledger'}
            if p and p.get('peak') is not None:
                row['result']['peak'] = p.get('peak')
        if p and p.get('closedAt') and p.get('realPct') is not None and not (row.get('result') or {}).get('src') == 'ledger':
            usd = _f(b.get('usd'))
            row['result'] = {'pct': round(_f(p['realPct']), 2), 'usd': round(usd * _f(p['realPct']) / 100, 3) if usd else None, 'peak': p.get('peak'),   # $ = what went in × the real % (summing sells counted top-ups / later sells: illusion +0.6% read +$0.13)
                             'heldMin': round((_f(p['closedAt']) - _f(p.get('since'))) / 60, 1) if p.get('since') else None, 'rule': p.get('rule')}
        if rv:
            row['judge'] = {k: rv.get(k) for k in ('kind', 'cause', 'lossClass', 'desk', 'why', 'change') if rv.get(k) is not None}
        if p and len(p.get('path') or []) > 1:   # 🎬 every trade's replay: the % path (+ for yours, every moment the agents would have sold)
            row['replay'] = replay_of(p)
        sn_ = snap_of_pos(p) if p else None
        if sn_:
            row['snap'] = sn_   # 📸 the market at the entry
        out.append(row)
    return out


def snap_of_pos(p):
    """📸 The entry snapshot for a trade card: your trades keep `snaps.entry` (chart · germ · buyers · pool …); an agent trade has its
    entry thesis (structure · germ distance · buyers on the tape · % under its high). Only what was read — None when nothing was."""
    e = (p.get('snaps') or {}).get('entry') or {}
    th = p.get('thesis') or {}
    out = {'chart': e.get('chart') or th.get('structure'), 'germ': e.get('germ') if e.get('germ') is not None else th.get('germDist'),
           'buyers': e.get('buyers') if e.get('buyers') is not None else (th.get('flow') or {}).get('buyPct'),
           'offHigh': e.get('offHigh') if e.get('offHigh') is not None else th.get('distHigh'), 'd5': e.get('d5'), 'pool': e.get('pool'), 'cap': e.get('cap')}
    out = {k: (round(_f(v), 1) if isinstance(v, (int, float)) else v) for k, v in out.items() if v is not None}
    return out or None


def replay_of(p, keep=30):
    """🎬 One of YOUR trades as a small replay: the % path (≤ `keep` points, evenly picked), the would-sell moments (rule + % from its
    snapshots), the germ distance at entry and the real result. Small on purpose — it rides in the one Agents payload."""
    path = [round(_f(x), 1) for x in (p.get('path') or [])]
    if len(path) > keep:
        step = (len(path) - 1) / (keep - 1)
        path = [path[round(i * step)] for i in range(keep)]
    sn = p.get('snaps') or {}
    would = [{'rule': w.get('rule'), 'pct': w.get('pct')} for w in (sn.get('would') or [])][:6]
    if not would and (p.get('would') or {}).get('pct') is not None:
        would = [{'rule': str(p['would'].get('rule') or '').split(' ')[0], 'pct': p['would']['pct']}]
    return {'path': path, 'would': would, 'germ': (sn.get('entry') or {}).get('germ'), 'end': p.get('realPct'), 'peak': p.get('peak')}


def germ_at(ticks, since, look=3600):
    """🦠 The germ distance at a moment in the past, rebuilt from recorded price ticks [{t, p}] of the hour before it: 1-minute bars (a
    minute with no trade carries the last close) → chart_intel.germ → % above the floor (None when no run ≥ 15% or too few ticks)."""
    import chart_intel as _ci
    tk = sorted((_f(x.get('t')), _f(x.get('p'))) for x in ticks or [] if since - look <= _f(x.get('t')) <= since and _f(x.get('p')) > 0)
    if len(tk) < 5:
        return None
    bars, cur, b = [], None, None
    for t, p in tk:
        m = int(t // 60) * 60
        if cur is None:
            cur, b = m, [m, p, p, p, p, 0]
        while m > cur:
            bars.append(b); cur += 60; pc = b[4]; b = [cur, pc, pc, pc, pc, 0]
        b[2], b[3], b[4] = max(b[2], p), min(b[3], p), p
    bars.append(b)
    g = _ci.germ(bars[-60:])
    return None if not g else round(_f(g['dist']), 1)


def germ_fill(positions, fill):
    """Overlay the backfilled germ-at-entry (`arch.germFill` {"mint:since": %}) on copies of the positions that have none."""
    out = []
    for p in positions or []:
        g = (fill or {}).get(f"{p.get('mint')}:{round(_f(p.get('since')))}")
        if g is not None and ((p.get('snaps') or {}).get('entry') or {}).get('germ') is None:
            p = {**p, 'snaps': {**(p.get('snaps') or {}), 'entry': {**((p.get('snaps') or {}).get('entry') or {}), 'germ': g}}}
        out.append(p)
    return out


GERM_ENTRY_PCT = 15.0   # your entry counts as "at the germ" this close above the germ floor


def germ_record(positions):
    """🦠 YOUR entries by where they sat against the germ floor at the first look (snaps.entry.germ): at the germ (0 … 15%) · off it ·
    not read → {bucket: {n, med, won}} on closed real results. A record, never a rule."""
    out = {}
    for p in positions or []:
        if not p.get('pick') or p.get('realPct') is None:
            continue
        g = ((p.get('snaps') or {}).get('entry') or {}).get('germ')
        k = 'no read' if g is None else 'at the germ' if 0 <= _f(g) <= GERM_ENTRY_PCT else 'off the germ'
        out.setdefault(k, []).append(_f(p['realPct']))
    med = lambda v: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2
    return {k: {'n': len(v), 'med': round(med(v), 1), 'won': round(100 * sum(x > 0 for x in v) / len(v))} for k, v in out.items()}


def tape_stats(rows):
    """One line over the tape's closed trades — counts and a median, never a sum of percentages."""
    done = sorted(_f(r['result']['pct']) for r in rows or [] if r.get('result'))
    slips = sorted(_f(r['buy']['slipPct']) for r in rows or [] if (r.get('buy') or {}).get('slipPct') is not None)
    med = lambda v: round(v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2, 2) if v else None
    waits = sorted(_f(r['buy']['waitSec']) for r in rows or [] if (r.get('buy') or {}).get('waitSec') is not None)
    lands = sorted(_f(r['buy']['landSec']) for r in rows or [] if (r.get('buy') or {}).get('landSec') is not None)
    return {'n': len(done), 'won': sum(1 for x in done if x > 0), 'medPct': med(done), 'open': sum(1 for r in rows or [] if r.get('open')), 'medSlipPct': med(slips),
            'medWaitSec': med(waits), 'medLandSec': med(lands)}


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
    for p in _rmem.trades(positions):   # one record per sale
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
    for p in _rmem.trades(positions):   # one record per sale
        if p.get('rule'):
            k = str(p['rule']).split(' ')[0]
            g.setdefault(k if k[:1] == 'R' and k[1:2].isdigit() else 'other', []).append(max(-100.0, min(100.0, _f(p['realPct']))))
    return _rec(g)


# ── 🧪 "exit on the thesis, not the stop" — replayed on every real trade before anyone ships it ─────────────────────────────────
LINE_SLIP = 4.0   # points a cut typically fills past the reading that triggered it (the real stops' own median)
LINE_TRY = (8, 12, 15)
LINE_MIN_N, LINE_EDGE = 40, 3.0   # a tighter line is worth proposing from 40 real trades, +3 points on the average AND no worse a median


def line_replay(positions):
    """Would a TIGHTER invalidation line have paid? Each real trade's recorded path is replayed with a cut at −X% (filled LINE_SLIP
    lower; a trade that really ended worse keeps its real result) against what really happened. Also counts the trades that were
    already past −15% at the FIRST look after the fill (`gapped`): no exit line saves those — only a faster / better entry does.
    → {n, actual, lines: [{x, avg, med, won, cutWinners}], gapped, best, verdict}"""
    ts = _rmem.trades(positions)
    real = [max(-100.0, min(100.0, _f(p['realPct']))) for p in ts]
    if not real:
        return {'n': 0}
    stat = lambda v: {'avg': round(sum(v) / len(v), 2), 'med': _med(v), 'won': sum(1 for x in v if x > 0)}
    lines = []
    for x in LINE_TRY:
        out, cut = [], 0
        for p, r in zip(ts, real):
            path = [_f(v) for v in p.get('path') or []]
            hit = next((v for v in path if v <= -x), None)
            if hit is None and _f(p.get('low')) <= -x:
                hit = _f(p.get('low'))
            if hit is None:
                out.append(r); continue
            new = max(-100.0, hit - LINE_SLIP)
            if r <= 0:
                new = max(new, r)   # it lost anyway: the cut can only have ended it earlier, never worse than it really ended
            else:
                cut += 1            # a real WINNER this line would have thrown away
            out.append(new)
        lines.append({'x': x, **stat(out), 'cutWinners': cut})
    act = stat(real)
    best = max(lines, key=lambda l: l['avg'])
    ok = len(real) >= LINE_MIN_N and best['avg'] - act['avg'] >= LINE_EDGE and _f(best['med']) >= _f(act['med'])
    return {'n': len(real), 'actual': act, 'lines': lines, 'gapped': sum(1 for p in ts if (p.get('path') or [0])[0] <= -15), 'best': best['x'],
            'verdict': 'pays' if ok else 'not proven'}

