"""🪟 THE OFFICE'S VIEW OF A KERNEL CANDIDATE — pipeline · decision trace · the Archivist's record · the current-case block. Pure.

Everything here is built from ONE kernel case file (`Kernel.cases()`: the sensed row + the ten opinions + the reduced status). Nothing is
re-decided: a desk's line is the opinion the brain already gave, and the FINAL word is the reducer's status. One meaning of Devil
everywhere: `devil_view` → 'veto' (the hard wall — the only thing that blocks) · 'warn' (evidence that lowers the rank) · 'clear'.
"""
import market_data as _md

CHAIN = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge')
STAGE_STATES = ('WAITING', 'WORKING', 'PASS', 'WARN', 'VETO', 'DONE', 'ERROR', 'STALE')
FINAL = {'READY': 'READY', 'CONTENDING': 'CONTENDING', 'TRACKING': 'TRACKING', 'HELD': 'HELD', 'EXIT_PENDING': 'EXIT PENDING', 'ORDER_PENDING': 'ORDER PENDING', 'CLOSED': 'CLOSED', 'DISCOVERED': 'DISCOVERED'}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def devil_view(op):
    """Devil's opinion in the ONE vocabulary every surface uses. → {verdict: veto | warn | clear, word, objections: [{rule, evidence,
    severity, hard}], confidence}"""
    dv = (op or {}).get('devil') or {}
    objs = [{'rule': o, 'evidence': str(w)[:160], 'severity': s, 'hard': s == 'HARD_VETO'} for o, s, w in dv.get('objections') or []]
    verdict = 'veto' if dv.get('hard') else 'warn' if objs else 'clear'
    return {'verdict': verdict, 'word': {'veto': '✕ BLOCKED', 'warn': '⚠ DEVIL WARNS', 'clear': 'NO OBJECTION'}[verdict], 'objections': objs, 'confidence': dv.get('confidence')}


def pipeline(case, ctx):
    """One line per desk for a candidate: state + elapsed ms + the word that explains it. Only a VETO / ERROR stops the desks after it —
    a Devil warning or Sherlock's unknowns never do."""
    ms = (ctx or {}).get('ms') or {}
    if not case:
        return [{'agent': a, 'state': 'WAITING', 'ms': ms.get(a), 'word': 'no candidate this pass'} for a in CHAIN]
    ctx = ctx or {}
    op, row = case['op'], case['row']
    t, c, wd = ctx.get('tally') or {}, ctx.get('courier') or {}, ctx.get('warden')
    q = (row.get('chart') or {}).get('q')
    dv = devil_view(op)
    stop, out = False, []

    def add(a, state, word):
        nonlocal stop
        out.append({'agent': a, 'state': 'WAITING' if stop and a not in ('archivist', 'judge') else state, 'ms': ms.get(a), 'word': str(word)[:200]})
        if state in ('VETO', 'ERROR') and a in ('tally', 'trigger', 'devil', 'warden', 'courier'):
            stop = True
    add('tally', 'STALE' if t.get('stale') else 'ERROR' if q and not q.get('readOk') else 'PASS',
        (f"{_md.word(q)} · " if q else '') + (f"{t.get('readings')} readings · {t.get('ageSec')}s old" if t else f"{op['tally'].get('fresh') or 'age unknown'} · ${_f(op['tally'].get('vpm')):,.0f}/min"))
    sh = op['sherlock']
    add('sherlock', 'PASS' if not sh['unknown'] else 'WORKING', (f"{row['chart']['state']} · " if row.get('chart') else '') + f"known: {', '.join(sh['known']) or 'nothing yet'}"
        + (f" · researching: {', '.join(sh['unknown'])}" if sh['unknown'] else '') + (f" · scan {ctx.get('scan')}" if ctx.get('scan') else ''))
    add('weather', 'PASS', f"{op['weather']['regime']} · rank ×{op['weather']['factor']:g}")
    tr = op['trigger']
    add('trigger', {'ENTER': 'PASS', 'NO': 'VETO'}.get(tr['state'], 'WORKING'), f"{tr['state']} — {tr['narrative']}: {tr['why']}")
    add('devil', {'veto': 'VETO', 'warn': 'WARN', 'clear': 'PASS'}[dv['verdict']],
        dv['word'] + (f" — {dv['objections'][0]['evidence']}" if dv['objections'] else '') + (f" · confidence ×{_f(dv['confidence']):g}" if dv['verdict'] == 'warn' else ''))
    add('warden', ('VETO' if wd['veto'] else 'DONE') if wd else ('VETO' if _f(op['warden']['size']) <= 0 else 'PASS'),
        f"${wd['requested']:.2f} → ${wd['allowed']:.2f} (×{wd['eff']:g}) · {wd['decided']}" if wd else f"would size ×{op['warden']['size']:g} — {op['warden']['why']}")
    add('courier', 'VETO' if not op['courier']['ok'] else 'WORKING' if c.get('pending') else 'WARN' if c.get('health') == 'DEGRADED' else 'PASS', f"{c.get('health') or ('READY' if op['courier']['ok'] else 'BLOCKED')} · {op['courier']['why']}")
    rp = op.get('reaper')
    add('reaper', 'WAITING' if not rp else 'WORKING', 'takes over once the fill is confirmed' if not rp else f"{rp.get('action')} — {rp.get('why')}")
    add('archivist', 'DONE' if ctx.get('filed') else 'WAITING', 'decision filed' if ctx.get('filed') else 'files it when the pass ends')
    add('judge', 'WAITING', f"evidence weight ×{_f(op['judge']['weight']):g} · reviews the real exit")
    return out


def trace(case, ctx, report=None):
    """🧵 THE TEAM DECISION TRACE: each desk's answer to ITS OWN question, in chain order, then the reducer's FINAL status and its reason."""
    op, row = case['op'], case['row']
    ctx = ctx or {}
    q = (row.get('chart') or {}).get('q')
    ch, wd, c = row.get('chart') or {}, ctx.get('warden'), ctx.get('courier') or {}
    dv, sh, tr = devil_view(op), op['sherlock'], op['trigger']
    lines = [['tally', _md.word(q) if q else str(op['tally'].get('fresh') or 'AGE UNKNOWN'), (q or {}).get('why') or f"${_f(op['tally'].get('vpm')):,.0f}/min traded"],
             ['sherlock', (f"{ch['state']} / " if ch.get('state') else '') + ('EVIDENCE COMPLETE' if not sh['unknown'] else 'RESEARCHING'), 'unknown: ' + ', '.join(sh['unknown']) if sh['unknown'] else 'holders · early wallets · site / X known'],
             ['weather', f"{op['weather']['regime']} MARKET", f"rank ×{op['weather']['factor']:g}"],
             ['trigger', tr['state'], f"{tr['narrative']} — {str(tr['why'])[:110]}"],
             ['devil', dv['word'], '; '.join(f"{o['rule']} ({o['severity'].replace('_', ' ').lower()})" for o in dv['objections'][:3])],
             ['warden', 'NOT SIZED YET' if not wd else 'VETO' if wd['veto'] else f"MAX {wd['eff']:g}x", f"would size ×{op['warden']['size']:g}: {op['warden']['why']}" if not wd else wd['decided']],
             ['courier', {'HEALTHY': 'READY', 'DEGRADED': 'EXECUTION DEGRADED', 'BAD': 'EXECUTION BAD — BLOCKED'}.get(c.get('health'), 'READY' if op['courier']['ok'] else 'BLOCKED'), str(op['courier']['why'])[:110]],
             ['reaper', (report or {}).get('decision') or ((op.get('reaper') or {}).get('action')) or 'NOT APPLICABLE UNTIL FILLED', (report or {}).get('rule') or ((op.get('reaper') or {}).get('why')) or '']]
    return {'mint': case['mint'], 'symbol': case.get('symbol'), 'lines': lines, 'final': FINAL.get(case['status'], case['status']), 'why': str(case.get('kwhy') or '')[:160], 'rank': case.get('rank')}


def lineage(case, ctx, action=None):
    """The decision record the Archivist files: what the KERNEL decided and on what — compact, numbers not prose."""
    op, row = case['op'], case['row']
    ctx = ctx or {}
    n, v = row.get('nums') or {}, row.get('vitals') or {}
    wd, ch = ctx.get('warden'), row.get('chart') or {}
    dv = devil_view(op)
    q = ch.get('q')
    return {'mint': case['mint'], 'sym': case.get('symbol'), 'px': case.get('px'), 'cleared': bool(case.get('cleared')), 'status': case['status'], 'rank': case.get('rank'), 'action': action, 'ageH': v.get('ageH'),
            'tally': {'pts': n.get('pts'), 'd5': n.get('d5'), 'c1': n.get('c1'), 'buy': n.get('buy'), 'liq': n.get('liq'), 'pace': n.get('pace')},
            'launch': row.get('launch'), 'scanFailed': v.get('safe') is False, 'noFill': ctx.get('noFill'),
            'sherlock': {'known': op['sherlock']['known'], 'unknown': op['sherlock']['unknown'], 'factor': op['sherlock']['factor']},
            'weather': {'regime': op['weather']['regime'], 'factor': op['weather']['factor']}, 'trigger': [op['trigger']['state'].lower(), str(op['trigger']['why'])[:80], op['trigger']['narrative']],
            'devil': [dv['verdict'], [o['rule'] for o in dv['objections']][:5]],
            'blocked': [k[0] for k in case.get('checks') or [] if not k[1]],
            'chart': None if not ch else {'state': ch.get('state'), 'entry': (ch.get('entry') or [None, None])[:2], 'trend': ch.get('trend'), 'chop': ch.get('chop'), 'mom': ch.get('mom'), 'ext': ch.get('ext'), 'src': ch.get('src')},
            'data': None if not q else {'state': q.get('state'), 'conf': q.get('conf'), 'why': q.get('why'), 'label': q.get('label'), 'realOhlc': q.get('realOhlc'), 'volume': q.get('volume'), 'liquidity': q.get('liquidity')},
            'warden': None if not wd else {'req': wd['requested'], 'allowed': wd['allowed'], 'mult': wd['eff'], 'rule': wd['decided'],
                                           'evidence': next((r_.get('evidence') for r_ in wd.get('rules') or [] if r_.get('id') == wd.get('decided') and r_.get('evidence')), None)},
            'courier': (ctx.get('courier') or {}).get('health'), 'evidence': ctx.get('evidence')}


def case_view(case, ctx):
    """The CURRENT candidate, desk by desk, for the page (every block is the kernel's own opinion)."""
    op, row = case['op'], case['row']
    dv = devil_view(op)
    return {'mint': case['mint'], 'symbol': case.get('symbol'), 'pair': case.get('pair'), 'px': case.get('px'), 'rank': case.get('rank'), 'lean': case.get('rank'), 'status': case['status'],
            'cleared': case.get('cleared'), 'go': case.get('cleared'), 'checks': case['checks'], 'tally': {**(ctx.get('tally') or {}), **{k: op['tally'].get(k) for k in ('fresh', 'vpm', 'bpm', 'cap', 'liq', 'sources')}},
            'sherlock': {**op['sherlock'], 'scan': ctx.get('scan'), 'vitals': row.get('vitals')}, 'trigger': {'call': [op['trigger']['state'].lower(), op['trigger']['why']], 'state': op['trigger']['state'],
                                                                                                           'narrative': op['trigger']['narrative'], 'checks': [k for k in case['checks'] if k[0] in ('timing', 'rank')]},
            'devil': dv, 'warden': ctx.get('warden') or {'preview': True, 'size': op['warden']['size'], 'why': op['warden']['why']}, 'why': case.get('kwhy'), 'parts': case.get('parts')}
