"""🕵 ADVERSARIAL LAUNCH INTELLIGENCE (owner's spec, 2026-10-11). Pure + tested (`tests/test_launch_intel.py`).

Public on-chain launch behaviour only — the first buyers of a launch (read ONCE with the launch facts), the live balances the holder scan
already re-reads, the 90s trade tape the office already reads for held coins, and the funder links the bot shield already keeps. No new
scanner, no private flow, no copying a wallet: the early wallets are INFORMATION — when they buy, size, hold and sell — and the office
learns from settled outcomes which behaviour is dangerous. Behavioural labels only; never a claim about a person.

  early_map      first 10 / 25 buyers: supply bought, largest, clustered (same slot / same size / known funder), still held now
  classify       NORMAL · HEAVY SNIPER ACTIVITY · BUNDLED · INSIDER-LIKE CLUSTER · UNKNOWN (with the evidence)
  action         per wallet: HOLD · ADD · PARTIAL SELL · EXIT · DUMP
  trend          early-wallet supply over reads: IMPROVING · STABLE · WORSENING
  memory / wclass  recurring wallets across settled launches → EARLY WINNER WALLET · FAST DUMPER · RUG-ASSOCIATED · DEV-LINKED · UNKNOWN (n ≥ 3)
  phase          PRE-FOMO · EARLY FOMO · ACCELERATING · CROWD FOMO · DISTRIBUTION · COLLAPSE + healthy vs exit-liquidity
  pressure       live exit pressure from early wallets selling on the tape: NONE · WATCH · HIGH
  rank_band      our buyer rank: FIRST 10 · FIRST 25 · FIRST 50 · LATER (exact only when we are in the early map, else ≈ holders)
"""

CLASSES = ('NORMAL', 'HEAVY SNIPER ACTIVITY', 'BUNDLED', 'INSIDER-LIKE CLUSTER', 'UNKNOWN')
PHASES = ('PRE-FOMO', 'EARLY FOMO', 'ACCELERATING', 'CROWD FOMO', 'DISTRIBUTION', 'COLLAPSE')
GOOD_PHASES = ('EARLY FOMO', 'ACCELERATING')
WCLASSES = ('EARLY WINNER WALLET', 'FAST DUMPER', 'RUG-ASSOCIATED', 'DEV-LINKED', 'UNKNOWN')
EARLY_N = 25
SAME_SIZE_TOL = 0.02     # two buys within 2% of each other = the same size
SETTLE_SEC = 3600        # a launch is judged 1h after we first noted it
RUG_PCT, WIN_PCT = -80.0, 50.0
WALLET_MIN_N = 3         # never a label from fewer launches
MEM_KEEP = 4000          # wallets kept (most recently seen)
NOTE_KEEP = 400          # launches kept in the open / settled lists


from fnum import nan_safe as _f


# ── 1 · 3 · EARLY BUYER MAP + CONCENTRATION ──────────────────────────────────────────────────────────────────────────────────────────
def clusters(early, funders=None):
    """Wallet groups that look coordinated: same slot (≥ 3 buyers), the same buy size (≥ 3 within 2%), or the same known funder (≥ 2).
    → [{kind, wallets, why}] — behaviour only."""
    out = []
    by_slot = {}
    for e in early or []:
        by_slot.setdefault(e.get('slot'), []).append(e['w'])
    for s, ws in by_slot.items():
        if s is not None and len(ws) >= 3:
            out.append({'kind': 'slot', 'wallets': sorted(set(ws)), 'why': f'{len(set(ws))} buyers in one slot'})
    sized = sorted((e for e in early or [] if _f(e.get('sol')) > 0), key=lambda e: _f(e['sol']))
    i = 0
    while i < len(sized):
        j = i
        while j + 1 < len(sized) and _f(sized[j + 1]['sol']) <= _f(sized[i]['sol']) * (1 + SAME_SIZE_TOL):
            j += 1
        if j - i + 1 >= 3:
            g = sorted({e['w'] for e in sized[i:j + 1]})
            out.append({'kind': 'size', 'wallets': g, 'why': f"{len(g)} buys of the same size (~{_f(sized[i]['sol']):.3f} SOL)"})
        i = j + 1
    fund = {}
    for w, fr in (funders or {}).items():
        if fr:
            fund.setdefault(fr, []).append(w)
    for fr, ws in fund.items():
        if len(ws) >= 2:
            out.append({'kind': 'funder', 'wallets': sorted(ws), 'why': f'{len(ws)} early wallets funded by one wallet already seen bankrolling launches'})
    return out


def early_map(early, holdings=None, funders=None, creator=None, young=False):
    """`early` = the launch's first buyers in order [{w, slot, sol, pct}] (pct = supply bought). `holdings` {w: % held now} (None = not
    read). → the EARLY BUYER MAP: concentration bought and held now, clusters, every wallet's action. None when there is no early read."""
    ev = [e for e in (early or []) if e.get('w')][:EARLY_N]
    if not ev:
        return None
    hold = holdings or {}
    cl = clusters(ev, funders)
    cw = {w for c in cl for w in c['wallets']}
    p10 = sum(_f(e.get('pct')) for e in ev[:10])
    p25 = sum(_f(e.get('pct')) for e in ev)
    big = max(ev, key=lambda e: _f(e.get('pct')))
    known = [e for e in ev if hold.get(e['w']) is not None]
    now_pct = sum(_f(hold[e['w']]) for e in known) if known else None
    wallets = [{'w': e['w'], 'rank': i + 1, 'slot': e.get('slot'), 'sol': e.get('sol'), 'bought': e.get('pct'), 'now': hold.get(e['w']),
                'action': action(e.get('pct'), hold.get(e['w']), young), 'cluster': e['w'] in cw, 'dev': bool(creator) and e['w'] == creator} for i, e in enumerate(ev)]
    return {'n': len(ev), 'first10Pct': round(p10, 2), 'first25Pct': round(p25, 2), 'largestPct': round(_f(big.get('pct')), 2), 'largest': big['w'],
            'clusterPct': round(sum(_f(e.get('pct')) for e in ev if e['w'] in cw), 2), 'clusters': cl,
            'nowPct': None if now_pct is None else round(now_pct, 2), 'read': len(known),
            'exited': sum(1 for w in wallets if w['action'] in ('EXIT', 'DUMP')), 'wallets': wallets}


def action(bought, now, young=False):
    """What one early wallet did since its buy: HOLD · ADD · PARTIAL SELL · EXIT (· DUMP = gone while the launch is still young). None = not read."""
    if now is None or bought is None:
        return None
    b, n = _f(bought), _f(now)
    if b <= 0:
        return 'ADD' if n > 0 else None
    if n <= b * 0.02:
        return 'DUMP' if young else 'EXIT'
    if n < b * 0.7:
        return 'PARTIAL SELL'
    if n > b * 1.2:
        return 'ADD'
    return 'HOLD'


def classify(m, bundled_n=None, snipers_n=None, insiders_pct=None, known_ring=False):
    """→ (class, [evidence]). Measurable behaviour only: same-slot buys, ~1s snipes, coordinated clusters, a known funder / crew."""
    if m is None and bundled_n is None and snipers_n is None:
        return 'UNKNOWN', ['no launch read yet']
    ev, cl = [], (m or {}).get('clusters') or []
    funder = any(c['kind'] == 'funder' for c in cl)
    clp = _f((m or {}).get('clusterPct'))
    if funder or known_ring or (clp >= 15 and len(cl) >= 2):
        ev += [c['why'] for c in cl if c['kind'] == 'funder'] + (['a known crew is inside'] if known_ring else []) + ([f'clustered wallets bought {clp:.1f}% of supply'] if clp >= 15 else [])
        return 'INSIDER-LIKE CLUSTER', ev
    if _f(bundled_n) >= 3 or any(c['kind'] == 'slot' for c in cl):
        ev.append(f'{int(_f(bundled_n))} wallets bought in the creation slot' if _f(bundled_n) >= 3 else next(c['why'] for c in cl if c['kind'] == 'slot'))
        return 'BUNDLED', ev
    if _f(snipers_n) >= 5 or _f(insiders_pct) >= 10:
        ev.append(f'{int(_f(snipers_n))} wallets sniped within ~1s' if _f(snipers_n) >= 5 else f'snipers / bundlers still hold {_f(insiders_pct):.1f}%')
        return 'HEAVY SNIPER ACTIVITY', ev
    if m is None and (bundled_n is None or snipers_n is None):
        return 'UNKNOWN', ['launch not fully read']
    return 'NORMAL', [f"{int(_f(bundled_n))} bundled · {int(_f(snipers_n))} snipers" if bundled_n is not None else 'first buyers spread']


def trend(hist, tol=1.0):
    """Early-wallet supply over reads [(t, pct)] → IMPROVING (falling = spreading out) · STABLE · WORSENING · None (< 2 reads)."""
    xs = [(t, _f(p)) for t, p in (hist or []) if p is not None]
    if len(xs) < 2:
        return None
    d = xs[-1][1] - xs[0][1]
    return 'IMPROVING' if d <= -tol else 'WORSENING' if d >= tol else 'STABLE'


# ── 5 · WALLET MEMORY ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def remember(mem, m, result, ageH_seen=None, creators=()):
    """One SETTLED launch into the wallet memory: every early wallet gets the launch, its rank, what it did by settle time and the launch's
    1h result (None = no price = treated as a rug, the coin vanished). → new memory {wallet: record}."""
    mem = dict(mem or {})
    if not m:
        return mem
    res = RUG_PCT if result is None else _f(result)
    rug, win = res <= RUG_PCT, res >= WIN_PCT
    for w in m.get('wallets') or []:
        r = dict(mem.get(w['w']) or {'n': 0, 'rug': 0, 'win': 0, 'soldEarly': 0, 'soldBeforeRug': 0, 'heldWin': 0, 'rankSum': 0, 'dev': 0})
        sold = w.get('action') in ('EXIT', 'DUMP')
        r['n'] += 1
        r['rug'] += rug
        r['win'] += win
        r['soldEarly'] += 1 if w.get('action') == 'DUMP' else 0
        r['soldBeforeRug'] += 1 if sold and rug else 0
        r['heldWin'] += 1 if win and w.get('action') in ('HOLD', 'ADD', 'PARTIAL SELL') else 0
        r['rankSum'] += int(w.get('rank') or 0)
        r['dev'] += 1 if w.get('dev') or w['w'] in (creators or ()) else 0
        mem[w['w']] = r
    if len(mem) > MEM_KEEP:
        mem = dict(list(mem.items())[-MEM_KEEP:])
    return mem


def wclass(r):
    """A wallet's behaviour class from its record → (class, confidence 0–100, n). Never a label under WALLET_MIN_N launches."""
    r = r or {}
    n = int(r.get('n') or 0)
    if n < WALLET_MIN_N:
        return 'UNKNOWN', 0, n
    conf = min(100, round(100 * n / (n + 4)))
    if r.get('dev', 0) >= 2:
        return 'DEV-LINKED', conf, n
    if r.get('rug', 0) / n >= 0.5:
        return 'RUG-ASSOCIATED', conf, n
    if (r.get('soldEarly', 0) + r.get('soldBeforeRug', 0)) / n >= 0.5:
        return 'FAST DUMPER', conf, n
    if r.get('heldWin', 0) / n >= 0.34:
        return 'EARLY WINNER WALLET', conf, n
    return 'UNKNOWN', conf, n


DANGER = ('FAST DUMPER', 'RUG-ASSOCIATED', 'DEV-LINKED')


def known_players(m, mem):
    """The early wallets with a behaviour class → {wallet: class} (UNKNOWN left out)."""
    out = {}
    for w in (m or {}).get('wallets') or []:
        c = wclass((mem or {}).get(w['w']))[0]
        if c != 'UNKNOWN':
            out[w['w']] = c
    return out


# ── 11 · LIVE EXIT PRESSURE ──────────────────────────────────────────────────────────────────────────────────────────────────────────
PRESS_USD = 50.0         # an early wallet selling at least this much in the window counts


def pressure(win, m, players=None, creator=None):
    """The early buyers SELLING on the live tape (90s window, `flow.window`) → (NONE · WATCH · HIGH, why). HIGH = the creator sold, a known
    dangerous wallet sold, or ≥ 2 early wallets sold (a cluster unwinding). WATCH = one early wallet sold. Never 'copy a wallet'."""
    if not win or not m:
        return 'NONE', None
    early = {w['w']: w for w in m.get('wallets') or []}
    cl = {w for c in m.get('clusters') or [] for w in c['wallets']}
    by = {}
    for w, u in win.get('sells') or []:
        if w in early or (creator and w == creator):
            by[w] = by.get(w, 0.0) + _f(u)
    by = {w: u for w, u in by.items() if u >= PRESS_USD}
    if not by:
        return 'NONE', None
    tot = sum(by.values())
    bad = [w for w in by if (players or {}).get(w) in DANGER]
    if creator and creator in by:
        return 'HIGH', f'the creator sold ${by[creator]:,.0f}'
    if bad:
        return 'HIGH', f"{len(bad)} early wallet(s) with a {(players or {})[bad[0]].lower()} record sold ${sum(by[w] for w in bad):,.0f}"
    if len(by) >= 2:
        cw = [w for w in by if w in cl]
        return 'HIGH', f"{len(by)} early wallets sold ${tot:,.0f}" + (f' ({len(cw)} from a coordinated cluster)' if cw else '')
    return 'WATCH', f"early buyer #{early[next(iter(by))]['rank'] if next(iter(by)) in early else '?'} sold ${tot:,.0f}"


# ── 7 · 8 · FOMO PHASE ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
def phase(n, m=None, tr=None, press=None, ext=None):
    """→ (phase, healthy bool | None, [why]). `n` = Tally's numbers (d5, c1, pace, buy, holdD, liqD). Goal: enter EARLY / ACCELERATING,
    never the crowd's top or the insiders' exit."""
    n = n or {}
    d5, c1, pace, buy = _f(n.get('d5')), n.get('c1'), n.get('pace'), n.get('buy')
    c1 = None if c1 is None else _f(c1)
    liqD, holdD = n.get('liqD'), n.get('holdD')
    exited = _f((m or {}).get('exited')) / max(1, _f((m or {}).get('read'))) if m and m.get('read') else 0.0
    dumping = press == 'HIGH' or tr == 'WORSENING' or exited >= 0.4
    why = []
    if d5 <= -15 or (c1 is not None and c1 <= -30 and d5 < 0) or (liqD is not None and _f(liqD) <= -30):
        ph = 'COLLAPSE'; why.append(f'{d5:+.0f}% in 5 min' if d5 <= -15 else f'pool {_f(liqD):+.0f}%' if liqD is not None and _f(liqD) <= -30 else f'{c1:+.0f}% on the hour')
    elif ((c1 is not None and c1 >= 50) or _f(ext) >= 75) and dumping and (pace is None or _f(pace) <= 1.2):
        ph = 'DISTRIBUTION'; why.append('price up big while early wallets sell' + (f' ({exited * 100:.0f}% of the read ones are out)' if exited else ''))
    elif (c1 is not None and c1 >= 100) or (c1 is not None and c1 >= 50 and d5 >= 10):
        ph = 'CROWD FOMO'; why.append(f'{c1:+.0f}% on the hour' + (f', {d5:+.0f}% in 5 min' if d5 >= 10 else '') + ' — the crowd is already in')
    elif pace is not None and _f(pace) >= 1.5 and d5 > 2 and (buy is None or _f(buy) >= 55):
        ph = 'ACCELERATING'; why.append(f'volume {_f(pace):.1f}× the hour, {d5:+.1f}% in 5 min')
    elif pace is not None and _f(pace) >= 1.0 and d5 >= 0 and (buy is None or _f(buy) >= 52) and (holdD is None or _f(holdD) > 0):
        ph = 'EARLY FOMO'; why.append('buyers arriving at a steady pace')
    else:
        ph = 'PRE-FOMO'; why.append('quiet — no crowd yet')
    healthy = None
    if ph in ('EARLY FOMO', 'ACCELERATING', 'CROWD FOMO'):
        bad = [x for x in (('early wallets unloading' if dumping else None), ('pool weakening' if liqD is not None and _f(liqD) <= -10 else None),
                           ('holders not growing' if holdD is not None and _f(holdD) <= 0 else None), ('sellers lead' if buy is not None and _f(buy) < 50 else None),
                           ('vertical' if d5 >= 25 else None)) if x]
        healthy = not bad
        why += bad if bad else ['buyers growing, early wallets holding, pool steady']
    return ph, healthy, why


PUMP_PHASES = ('DISCOVERY', 'EARLY ACCELERATION', 'FIRST PULLBACK', 'RECLAIM', 'BREAKOUT', 'RUNNING', 'LATE FOMO', 'DISTRIBUTION', 'COLLAPSE')


def pump_phase(n, chart_state=None, fomo=None, age_min=None, candles=None):
    """🎢 A fresh launch's entry phase from the CURRENT read (Tally's numbers + the live chart's state + the FOMO phase). Recent momentum, never
    launch → now. Preferred: EARLY ACCELERATION · FIRST PULLBACK · RECLAIM · BREAKOUT. Avoided: LATE FOMO · DISTRIBUTION · COLLAPSE."""
    n = n or {}
    d5, c1, pace = _f(n.get('d5')), n.get('c1'), n.get('pace')
    if fomo in ('COLLAPSE', 'DISTRIBUTION'):
        return fomo
    if fomo == 'CROWD FOMO' or (c1 is not None and _f(c1) >= 150 and d5 >= 15):
        return 'LATE FOMO'
    if chart_state in ('CONFIRMED BREAKOUT', 'BREAKOUT ATTEMPT'):
        return 'BREAKOUT'
    if chart_state == 'PULLBACK IN UPTREND':
        return 'RECLAIM' if d5 >= 0 else 'FIRST PULLBACK'
    if chart_state in ('UPTREND', 'STRONG UPTREND'):
        return 'RUNNING'
    if pace is not None and _f(pace) >= 1.5 and d5 > 2:
        return 'EARLY ACCELERATION'
    if (age_min is not None and _f(age_min) < 5) or (candles is not None and candles <= 3):
        return 'DISCOVERY'
    return 'DISCOVERY' if pace is None or _f(pace) >= 0.5 else None


def wallet_pressure(m, tr=None, press=None):
    """EARLY WALLET PRESSURE: POSITIVE (first buyers holding / adding, supply spreading out) · NEUTRAL · WARNING (some selling, supply
    re-concentrating) · DUMPING (selling now on the tape, or half the read ones gone). None = no early-buyer map read."""
    if press == 'HIGH':
        return 'DUMPING'
    if not m or not m.get('read'):
        return 'WARNING' if press == 'WATCH' else None
    acts = [w.get('action') for w in m.get('wallets') or [] if w.get('action')]
    out = sum(a in ('EXIT', 'DUMP') for a in acts) / max(1, len(acts))
    add = sum(a == 'ADD' for a in acts)
    if out >= 0.5:
        return 'DUMPING'
    if press == 'WATCH' or tr == 'WORSENING' or out >= 0.25:
        return 'WARNING'
    if tr == 'IMPROVING' or (add and out < 0.1):
        return 'POSITIVE'
    return 'NEUTRAL'


# ── 10 · OUR BUYER RANK ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def rank_band(our_rank=None, holders=None):
    """FIRST 10 · FIRST 25 · FIRST 50 · LATER. Exact when our wallet is in the early map (`our_rank`); else ≈ the holder count at entry."""
    r = our_rank if our_rank else (int(_f(holders)) + 1 if holders is not None else None)
    if r is None:
        return None, None
    band = 'FIRST 10' if r <= 10 else 'FIRST 25' if r <= 25 else 'FIRST 50' if r <= 50 else 'LATER'
    return band, ('exact' if our_rank else '≈ holders at entry')


# ── the record: launches noted → settled 1h later → wallet memory + what early winners look like ─────────────────────────────────────
def note(st, mint, m, cls, px, now, ageH=None, creator=None):
    """Note a launch the first time its early map is read (with its price); later reads append the early-supply history."""
    st = dict(st or {})
    op = dict(st.get('open') or {})
    e = op.get(mint)
    if e is None:
        if not m or _f(px) <= 0:
            return st
        e = {'t': now, 'px': _f(px), 'cls': cls, 'ageH': ageH, 'creator': creator, 'hist': []}
    else:
        e = dict(e)
    if m and m.get('nowPct') is not None and (not e['hist'] or now - e['hist'][-1][0] >= 120):
        e['hist'] = (list(e['hist']) + [[now, m['nowPct']]])[-20:]
    e['map'] = m or e.get('map')
    op[mint] = e
    if len(op) > NOTE_KEEP:
        op = dict(sorted(op.items(), key=lambda kv: -_f(kv[1]['t']))[:NOTE_KEEP])
    st['open'] = op
    return st


def settle(st, price_of, now):
    """Launches noted ≥ 1h ago → judged at their price now (None = vanished = −100%); every early wallet's behaviour joins the memory."""
    st = dict(st or {})
    op, done, mem = dict(st.get('open') or {}), list(st.get('done') or []), dict(st.get('mem') or {})
    creators = {e.get('creator') for e in op.values() if e.get('creator')}
    for mint, e in list(op.items()):
        if now - _f(e.get('t')) < SETTLE_SEC:
            continue
        p = price_of(mint)
        res = None if not p else (_f(p) / _f(e['px']) - 1) * 100
        mem = remember(mem, e.get('map'), res, e.get('ageH'), creators)
        done.append({'mint': mint, 'cls': e.get('cls'), 'res': None if res is None else round(res, 1), 'trend': trend(e.get('hist')), 'at': now})
        op.pop(mint)
    st.update(open=op, done=done[-NOTE_KEEP:], mem=mem)
    return st


def by_class(done):
    """The record per launch class → {class: {n, med, up %, rug %}} — whether a bundled launch really does worse is LEARNED here."""
    g = {}
    for d in done or []:
        g.setdefault(d.get('cls') or 'UNKNOWN', []).append(-100.0 if d.get('res') is None else _f(d['res']))
    out = {}
    for k, xs in g.items():
        s = sorted(xs)
        out[k] = {'n': len(s), 'med': round(s[len(s) // 2], 1), 'up': round(100 * sum(x > 0 for x in s) / len(s)), 'rug': round(100 * sum(x <= RUG_PCT for x in s) / len(s))}
    return out


def view(m, cls, cls_ev, tr, ph, healthy, ph_why, press, press_why, players, band, ageH, mcap):
    """The candidate's launch-intel line for the Agents tab (every field with its evidence)."""
    danger = sum(1 for c in (players or {}).values() if c in DANGER)
    conf = 0
    conf += 40 if m else 0
    conf += 20 if m and m.get('read') else 0
    conf += 20 if tr else 0
    conf += 20 if players else 0
    acts = {}
    for w in (m or {}).get('wallets') or []:
        if w.get('action'):
            acts[w['action']] = acts.get(w['action'], 0) + 1
    return {'ageH': ageH, 'mcap': mcap, 'rank': band, 'first10': (m or {}).get('first10Pct'), 'first25': (m or {}).get('first25Pct'),
            'largest': (m or {}).get('largestPct'), 'cluster': (m or {}).get('clusterPct'), 'early': (m or {}).get('nowPct'),
            'cls': cls, 'clsWhy': cls_ev, 'trend': tr, 'acts': acts, 'phase': ph, 'healthy': healthy, 'phaseWhy': ph_why,
            'press': press, 'pressWhy': press_why, 'players': len(players or {}), 'danger': danger, 'conf': conf, 'ewp': wallet_pressure(m, tr, press)}
