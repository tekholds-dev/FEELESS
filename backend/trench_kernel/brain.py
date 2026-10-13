"""🧠 THE TEN-AGENT BRAIN — pure opinions over a MintState, ONE reducer, four hunter lanes (owner's command-kernel spec, 2026-10-12).

Agents never fetch: each reads the MintState (+ a small context: weather, execution health, the Judge's weights, held positions) and
returns an opinion; Sherlock may ask for evidence (`requests`) that the central scheduler fulfils — when it lands, the mint raises an event
and Sherlock wakes again. The reducer turns the ten opinions into ONE candidate status + rank. The philosophy is backend/trench_crew.py:
everything before the money boundary weighs; only the hard wall (`opportunity.open_ok`) or an execution failure blocks.

Devil severities: INFO · WARNING · STRONG_WARNING · HARD_VETO — only the hard wall reaches HARD_VETO.
Hunter lanes: four always hunting — HUNTING (searching) · ARMED (a READY candidate is lined up) · HELD (capital deployed).
"""
import opportunity as _opp
import rule_lab as _lab
import trench_crew as _crew

from . import lifecycle as _lc

ROLES = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge')
SEVERITY = ('INFO', 'WARNING', 'STRONG_WARNING', 'HARD_VETO')
TRIGGER_OF = {'HOT EARLY MOVE': 'ENTER', 'BREAKOUT': 'ENTER', 'RUNNING': 'ENTER', 'BUILDING': 'ARM', 'STALLING': 'WAIT', 'DISTRIBUTING': 'NO', 'COLLAPSING': 'NO'}
WEATHER_F = {'HOT': 1.1, 'NORMAL': 1.0, 'CHOP': 0.9, 'THIN': 0.85, 'HOSTILE': 0.8}
LANES = 4
MEM_SIZE = 0.5       # a coin the real-money memory ranks in the worse half takes half a seat (never under the Warden's own floor)
PEN_FLOOR = 0.75    # the most the Judge's repeat-loss penalties may rank a coin down (a weight, never a veto)
CROWD_F = 1.05      # ≥ 8 different buyers in 90s with buyers leading (flow.vital `hot`)
READY_MIN = 120.0     # an open_score this high with Trigger ENTER = READY (the base score is 100 for an average coin)
CHART_GO = 'ENTER NOW'   # 🎯 the chart's own call a real seat needs (real card 2026-10-13, 107 agent trades: ENTER NOW +14% typical, 70% won;
                         # every WAIT / SKIP call −3…−29%, 16–30% won). `chartWait` off (owner, or the regret ledger) = the old open trenching
NO_CHART_SIZE = 0.5      # no chart read yet = half a seat (the 16 such trades: about break-even)


def chart_call(ms):
    """(call, rule) of the coin's chart this pass, or (None, None) when there is no chart read."""
    e = (((ms or {}).get('row') or {}).get('chart') or {}).get('entry') or []
    return (e[0] if e else None) or None, (e[1] if len(e) > 1 else None) or None


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def tally(ms):
    m, i = ms['market'], ms['identity']
    vpm, bpm = _opp.velocity(ms['row'])
    return {'ageMin': None if i.get('ageH') is None else round(_f(i['ageH']) * 60, 1), 'fresh': _opp.fresh_bucket(ms['row'])[0],
            'cap': m.get('marketCap'), 'liq': m.get('liquidity'), 'vpm': vpm, 'bpm': bpm, 'move5m': m.get('move5m'), 'sources': len(i.get('sources') or [])}


def sherlock(ms, lessons=None):
    """Known evidence vs UNKNOWN / PENDING (a research state, never a rejection) + what to fetch next. `walletTrust` (the live Sherlock
    generation's lesson) scales how hard early-wallet evidence moves the rank."""
    c, r = ms['chain'], ms['research']
    known, unknown, req = [], [], []
    (known if c['holderStatus'] == 'READY' else unknown).append('holders')
    (known if c['earlyWallets'] not in ('PENDING', 'UNKNOWN') else unknown).append('early wallets')
    (known if r['status'] == 'READY' else unknown).append('site / X')
    if c['holderStatus'] == 'PENDING':
        req.append('holders')
    if r['status'] != 'READY':
        req.append('research')
    f = {'POSITIVE': 1.08, 'NEUTRAL': 1.0, 'WARNING': 0.92, 'DUMPING': 0.85}.get(c.get('earlyWallets'), 1.0)
    f = round(1 + (f - 1) * _lc.lesson_value(lessons, 'sherlock', 'walletTrust'), 3)
    return {'known': known, 'unknown': unknown, 'requests': req, 'factor': f, 'holderStatus': c['holderStatus']}


def weather(ms, ctx):
    reg = (ctx or {}).get('regime') or 'NORMAL'
    return {'regime': reg, 'factor': WEATHER_F.get(reg, 1.0)}


def trigger(ms, lessons=None, lab=None, waits=None):
    """WHEN, from the live narrative of this pass. `lateMove` (the live Trigger generation's lesson, 0 = off): a coin already up that much
    in 5 minutes is ARMED, not entered."""
    nar, why = _opp.narrative(ms['row'])
    st = TRIGGER_OF.get(nar, 'WAIT')
    late = _lc.lesson_value(lessons, 'trigger', 'lateMove')
    if st == 'ENTER' and late > 0 and _f(ms['market'].get('move5m')) >= late:
        st, why = 'ARM', f"{why} — already {_f(ms['market'].get('move5m')):+.0f}% in 5 min (armed, not chased)"
    fv = ms['market'].get('flow') or {}   # 🌊 the live tape decides the MOMENT: never into sellers, never into the top of a spike
    w = waits or {}   # 😴 the regret ledger may switch a tape wait OFF when the coins it held back kept beating the ones taken (regret.tune)
    if st in ('ENTER', 'ARM') and fv.get('state') == 'SELLERS' and w.get('sellersWait', True):
        st, why = 'WAIT', f"{why} — but {fv.get('why')}"
    elif st == 'ENTER' and fv.get('state') == 'PEAK' and w.get('peakWait', True):
        st, why = 'ARM', f"{why} — {fv.get('why')} (armed for the dip, not bought at the top)"
    call, rule = chart_call(ms)
    if st in ('ENTER', 'ARM') and call and call != CHART_GO and w.get('chartWait', True):   # 🎯 THE CHART SAYS GO: no real seat on a WAIT / SKIP chart (not even an armed half)
        st, why = 'WAIT', f"{why} — the chart says {call.lower()} ({rule or '?'}): waits for ENTER NOW"
    if st == 'ENTER' and lab:   # 🧪 Trigger's lessons from the rule lab: a live AVOID rule on the entry moment, proven on our real fills, arms the coin
        fs = set(_lab.row_feats(ms['row']))
        hit = next((r for r in lab if set(r.get('when') or ()) <= fs), None)
        if hit:
            st, why = 'ARM', f"{why} — 🧪 lesson '{hit.get('name')}' (proven on our real fills): armed, not entered"
    return {'narrative': nar, 'why': why, 'state': st, 'flow': fv.get('state'), 'chart': call, 'chartRule': rule,
            'chartWait': bool(call and call != CHART_GO and w.get('chartWait', True))}


def devil(ms, lessons=None):
    """→ {objections: [(id, severity, why)], hard, confidence}. Only the hard wall is HARD_VETO; the rest weigh. Reads the senses'
    evidence (`ms['objections']`) — never the paper desk's agree / object."""
    out = []
    wall = _opp.open_ok(ms['row'])
    if wall:
        out.append(('wall', 'HARD_VETO', wall))
    for o, why in ms.get('objections') or []:
        sev = 'HARD_VETO' if o in _crew.DEVIL_HARD else 'STRONG_WARNING' if o in _crew.DEVIL_STRONG else 'WARNING'
        out.append((o, sev, why))
    if ms['chain'].get('earlyWallets') == 'WARNING':
        out.append(('early_wallets', 'WARNING', 'an early wallet is selling'))
    conf, _ = _crew.devil_factor(ms['row'], _lc.lesson_value(lessons, 'devil', 'strong'))
    return {'objections': out, 'hard': any(s == 'HARD_VETO' for _o, s, _w in out), 'confidence': conf}


def warden(ms, dv, sh):
    """Uncertainty → SIZE (≥ ×0.5); ×0 only on a hard veto. No chart read yet = half a seat."""
    if dv['hard']:
        return {'size': 0.0, 'why': 'hard wall'}
    m, why = 1.0, []
    if sum(1 for _o, s, _w in dv['objections'] if s == 'STRONG_WARNING'):
        m *= 0.75; why.append('strong warnings')
    if 'holders' in sh['unknown']:
        m *= 0.85; why.append('holders unknown')
    age = ms['identity'].get('ageH')
    if age is not None and _f(age) < 0.25:
        m *= 0.85; why.append('newborn')
    if chart_call(ms)[0] is None:
        m = min(m, NO_CHART_SIZE); why.append('no chart read yet')
    return {'size': round(max(_crew.SHRINK_FLOOR, m), 2), 'why': ', '.join(why) or 'full size'}


def courier(ctx):
    c = ctx or {}
    bad = c.get('halt') or c.get('courier') == 'BAD' or c.get('live') is False
    return {'ok': not bad, 'why': c.get('halt') or ('Courier reads execution BAD' if c.get('courier') == 'BAD' else 'office not live' if c.get('live') is False else 'execution healthy')}


def reaper(ms, pos):
    """For a HELD mint: HOLD · PROTECT · TAKE · EXIT from the live P/L, peak and stop (the same lines `office.fast_reap` acts on)."""
    if not pos:
        return None
    px, entry = _f(ms['market'].get('price')), _f(pos.get('entry'))
    if px <= 0 or entry <= 0:
        return {'action': 'HOLD', 'why': 'no live price this pass'}
    pct = (px / entry - 1) * 100
    peak, stop = max(_f(pos.get('peak')), pct), _f(pos.get('stopNow')) or 30.0
    if pct <= -stop:
        return {'action': 'EXIT', 'why': f'{pct:+.1f}% at its stop −{stop:g}%', 'pct': round(pct, 2)}
    if peak >= 6 and pct <= peak * 0.65 and pct >= 1.5:
        return {'action': 'TAKE', 'why': f'peaked {peak:+.1f}%, giving it back', 'pct': round(pct, 2)}
    if peak >= 6:
        return {'action': 'PROTECT', 'why': f'trail armed at {peak:+.1f}% peak', 'pct': round(pct, 2)}
    return {'action': 'HOLD', 'why': f'{pct:+.1f}%', 'pct': round(pct, 2)}


def judge(ms, weights):
    return {'weight': max(0.7, min(1.3, _f((weights or {}).get(ms['identity']['mint'], 1.0)) or 1.0))}


def think(ms, ctx=None):
    """All ten opinions + the reduced decision for ONE mint. Pure."""
    c = ctx or {}
    held = (c.get('held') or {}).get(ms['identity']['mint'])
    ls = c.get('lessons')   # {role: lesson} of the generations IN CONTROL (lifecycle.lessons) — a shadow / retired one is never in it
    t, sh, we, tr, dv = tally(ms), sherlock(ms, ls), weather(ms, c), trigger(ms, ls, c.get('lab'), c.get('waits')), devil(ms, ls)
    wa, co = warden(ms, dv, sh), courier(c)
    mw = (c.get('weights') or {}).get(ms['identity']['mint'])
    if mw is not None and _f(mw) < 1.0 and wa['size'] > 0:   # 🧠 the real-money memory puts this coin in the WORSE half of what the card has bought: it still takes the seat, at half size
        wa = {'size': round(max(_crew.SHRINK_FLOOR, wa['size'] * MEM_SIZE), 2), 'why': (wa['why'] + ', ' if wa['why'] != 'full size' else '') + 'worse half of our real trades'}
    base, parts = _opp.open_score(ms['row'], c.get('weights'), _lc.lesson_value(ls, 'devil', 'strong'), c.get('aiw'))
    fv = ms['market'].get('flow') or {}
    crowd = CROWD_F if fv.get('state') == 'BUYERS' and fv.get('hot') else 1.0   # 🌊 a crowd buying on the live tape ranks a little higher (never past a gate)
    hits = _opp.judge_hits(ms['row'], c.get('pens'))   # 👨‍⚖️ the Judge's repeat real-loss causes that match THIS coin: each ranks it down, together never under ×PEN_FLOOR
    pen = 1.0
    for _w, pts in hits:
        pen *= max(0.5, 1 + pts / 100.0)
    pen = max(PEN_FLOOR, round(pen, 3))
    if hits:
        parts = list(parts) + [('judge: ' + ' · '.join(w.replace('judge: ', '') for w, _p in hits), pen)]
    rank = round(base * we['factor'] * sh['factor'] * crowd * pen, 1)
    op = {'tally': t, 'sherlock': sh, 'weather': we, 'trigger': tr, 'devil': dv, 'warden': wa, 'courier': co,
          'reaper': reaper(ms, held), 'archivist': {'sources': ms['identity']['sources']}, 'judge': judge(ms, c.get('weights'))}
    return {'opinions': op, 'rank': rank, 'parts': parts,
            **reduce(op, rank, held, ms['identity']['mint'] in (c.get('pending') or ()), ms['identity']['mint'] in (c.get('watchOnly') or ()))}


def reduce(op, rank, held, pending=False, watch=False):
    """ONE decision: HELD / EXIT_PENDING for a position; else READY (ENTER, no hard veto, execution ok, rank ≥ READY_MIN) · CONTENDING
    (passes the wall) · TRACKING (data pending / outside the universe / blocked by the wall — never 'rejected')."""
    if held:
        a = (op['reaper'] or {}).get('action')
        return {'status': 'EXIT_PENDING' if a in ('EXIT', 'TAKE') else 'HELD', 'why': (op['reaper'] or {}).get('why')}
    if pending:   # a seat exists for it and the keeper is buying: it is not a candidate any more, and the ledger — not this — says when it is HELD
        return {'status': 'ORDER_PENDING', 'why': 'seat created — waiting for the keeper\'s confirmed fill'}
    dv = op['devil']
    if dv['hard']:
        w = next((why for _o, s, why in dv['objections'] if s == 'HARD_VETO'), 'hard wall')
        return {'status': 'TRACKING', 'why': w}
    if op['trigger']['state'] == 'ENTER' and op['courier']['ok'] and rank >= READY_MIN:
        if watch:   # 👤 on the desk only because the owner asked for a review: judged and shown, never a fill — ARM is the owner's own step
            return {'status': 'CONTENDING', 'why': f"would be READY (rank {rank:g}) — owner review only; ARM lets the agents take it", 'wouldBeReady': True}
        return {'status': 'READY', 'why': f"{op['trigger']['narrative']} — {op['trigger']['why']}"}
    return {'status': 'CONTENDING', 'why': f"{op['trigger']['narrative']} — rank {rank:g}"}


def lanes(decisions, held_mints, n=LANES):
    """Four hunter lanes, always hunting: HELD (capital in) · ARMED (a READY coin lined up, best rank first, one coin per lane) · HUNTING."""
    out, used = [], set()
    for m in list(held_mints)[:n]:
        out.append({'lane': len(out) + 1, 'state': 'HELD', 'mint': m}); used.add(m)
    ready = sorted([(m, d) for m, d in decisions.items() if d['status'] == 'READY' and m not in used], key=lambda kv: -kv[1]['rank'])
    cont = sorted([(m, d) for m, d in decisions.items() if d['status'] == 'CONTENDING' and m not in used], key=lambda kv: -kv[1]['rank'])
    for m, d in ready:
        if len(out) >= n:
            break
        out.append({'lane': len(out) + 1, 'state': 'ARMED', 'mint': m, 'rank': d['rank']}); used.add(m)
    while len(out) < n:
        best = next(((m, d) for m, d in cont if m not in used), None)
        if best:
            used.add(best[0])
        out.append({'lane': len(out) + 1, 'state': 'HUNTING', 'mint': best[0] if best else None, 'rank': best[1]['rank'] if best else None})
    return out
