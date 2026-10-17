"""👤 THE OWNER STUDY (owner, 2026-10-15: "AI and agents should truly build a report and study my trades and adjust any configs and ideologies").

Pure. Reads what FEELESS already records about the owner's own hand — every move graded 30 min later (owner_moves), the seats he filled vs
where the agents would have sold (office.owner_seats), his dragged SL / TP vs the agents' lines on closed real trades (office.owner_hand) and the
bands his picks sit in (pick_style) — and turns it into a REPORT (numbers, each finding backed by its n) and SUGGESTIONS in the chat's proposal
shape (lessons the agents and the model read). A suggestion is filed only with enough evidence (MIN_N) and is never applied without the owner's ✅.
"""

MIN_N = 6          # a finding needs this many graded moves / trades behind it
EDGE = 2.0         # points apart before one side is said to be better


from fnum import nan_safe as _f


def _rate(x):
    n = int(x.get('n') or 0)
    return round(100 * int(x.get('good') or 0) / n) if n else None


def report(moves=None, seats=None, hand=None, style_words=None):
    """→ {score, kinds, seats, hand, style, findings: [str], suggestions: [proposal dict]}. Every number is copied from its record."""
    moves = moves or {}
    kinds = [{'kind': k, 'label': v.get('label'), 'n': int(v.get('n') or 0), 'goodPct': _rate(v), 'medPct': v.get('medPct')} for k, v in moves.items()]
    kinds.sort(key=lambda x: -x['n'])
    findings, sugg = [], []
    graded = [k for k in kinds if k['n'] >= MIN_N]
    total = sum(k['n'] for k in kinds)
    good = sum(int(moves[k['kind']].get('good') or 0) for k in kinds)
    score = round(100 * good / total) if total else None
    for k in graded:
        findings.append(f"{k['label']}: {k['n']} graded · {k['goodPct']}% good · the coin typically {_f(k['medPct']):+.0f}% 30 min later")
    best = max(graded, key=lambda k: k['goodPct'] or 0, default=None)
    worst = min(graded, key=lambda k: k['goodPct'] if k['goodPct'] is not None else 101, default=None)
    if best and (best['goodPct'] or 0) >= 55:
        sugg.append({'agent': 'sherlock', 'kind': 'lesson', 'key': 'note', 'value': f"The owner's {best['label']} moves are {best['goodPct']}% good over {best['n']} graded — weigh coins that look like his picks higher.",
                     'reason': f"{best['n']} graded {best['label']} · {best['goodPct']}% good", 'effect': 'the model and agents read it on every fitting case'})
    if worst and worst is not best and (worst['goodPct'] or 0) <= 40:
        sugg.append({'agent': 'devil', 'kind': 'lesson', 'key': 'note', 'value': f"The owner's {worst['label']} moves are only {worst['goodPct']}% good over {worst['n']} graded — challenge that kind of move.",
                     'reason': f"{worst['n']} graded {worst['label']} · {worst['goodPct']}% good", 'effect': 'Devil and the model push back on it'})
    s = seats or {}
    cmp_ = s.get('cmp') or {}
    if int(cmp_.get('n') or 0) >= MIN_N:
        you, them = _f(cmp_.get('you')), _f(cmp_.get('agents'))
        findings.append(f"your seats: {cmp_['n']} closed with an agent exit call · you {you:+.1f}% vs where they'd have sold {them:+.1f}% · you did better {cmp_.get('youBetter', 0)}/{cmp_['n']}")
        if you - them >= EDGE:
            sugg.append({'agent': 'reaper', 'kind': 'lesson', 'key': 'note', 'value': f"On the owner's seats holding paid {you - them:+.1f} pts more than Reaper's first exit call ({cmp_['n']} seats) — Reaper sells too early; let winners run.",
                         'reason': f"you {you:+.1f}% vs agents {them:+.1f}% over {cmp_['n']}", 'effect': 'Reaper and the model read it before an exit'})
        elif them - you >= EDGE:
            findings.append(f"Reaper's exits would have done {them - you:+.1f} pts better on your seats — its calls are worth a look before you hold")
    h = hand or {}
    y, a = h.get('yours') or {}, h.get('agents') or {}
    if int(y.get('n') or 0) >= MIN_N and int(a.get('n') or 0) >= MIN_N:
        dy, da = _f(y.get('med')), _f(a.get('med'))
        findings.append(f"your dragged SL / TP: {y['n']} trades typical {dy:+.1f}% vs the agents' own lines {a['n']} trades {da:+.1f}%")
        if dy - da >= EDGE:
            sugg.append({'agent': 'reaper', 'kind': 'lesson', 'key': 'note', 'value': f"The owner's own SL / TP lines beat the agents' ({dy:+.1f}% vs {da:+.1f}%, {y['n']} vs {a['n']} trades) — copy his stop distance and patience.",
                         'reason': f"yours {dy:+.1f}% vs agents {da:+.1f}%", 'effect': 'Reaper and the model read it on every exit'})
    if style_words:
        findings.append('your picks look like: ' + '; '.join(list(style_words)[:4]))
    return {'score': score, 'graded': total, 'kinds': kinds, 'seats': {'n': s.get('n'), 'cmp': cmp_}, 'hand': {'yours': y, 'agents': a},
            'style': list(style_words or [])[:6], 'findings': findings[:8], 'suggestions': sugg[:4]}
