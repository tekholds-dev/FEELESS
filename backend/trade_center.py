"""📈 THE TRADE CENTER (owner, 2026-10-22: "my family town should show a trade center with live P&L of OSSY / G4's real-money trades").
Pure + tested. Input = the agents' real-card seats (trench_kernel.positions.card_seats). Everyone sees the desk's AGGREGATE (how many seats,
who holds them, the average live % — no coin names, so nobody front-runs its exits); staff (`_is_staff`) also get every seat with its coin,
the model holding it, live %, state and the desk's last word on it.
"""

MODELS = ('G4', 'OSSY')


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def summary(card, staff=False):
    seats = [s for s in ((card or {}).get('seats') or []) if s.get('kind') != 'open' and s.get('symbol')]
    by = {}
    for s in seats:
        who = (s.get('model') or 'G4') if s.get('kind') == 'g4' else 'AGENTS' if s.get('kind') == 'agent' else None
        if who:
            by.setdefault(who, []).append(s.get('pct'))
    out = {'open': len(seats), 'green': sum(1 for s in seats if (s.get('pct') or 0) > 0), 'avgPct': _avg([s.get('pct') for s in seats]),
           'by': {k: {'n': len(v), 'avgPct': _avg(v)} for k, v in sorted(by.items())}, 'staff': bool(staff)}
    if staff:
        out['rows'] = [{'symbol': s.get('symbol'), 'pair': s.get('pair'), 'who': (s.get('model') or 'G4') if s.get('kind') == 'g4' else s.get('kind'),
                        'pct': s.get('pct'), 'state': s.get('state') or '', 'action': s.get('action') or '', 'why': str(s.get('why') or '')[:120]} for s in seats]
    return out


NAMES = {'lan': 'G4', 'local': 'OSSY'}


def who_of(p):
    return NAMES.get(p.get('aiBy'), str(p.get('aiBy') or 'G4').upper()) if p.get('g4') else 'OWNER' if p.get('pick') else 'AGENTS'


def closed_view(positions, n=120, last=10):
    """The REAL card's closed lots (agent_archive positions with realPct): each lane's honest record — trades, % won, typical result — and the
    last few lots (coin · who · result · exit rule). Fees never in the result (realPct is price-only)."""
    ps = [p for p in (positions or []) if isinstance(p, dict) and p.get('realPct') is not None][-n:]
    by = {}
    for p in ps:
        by.setdefault(who_of(p), []).append(float(p['realPct']))
    rec = {k: {'n': len(v), 'wonPct': round(100 * sum(1 for x in v if x > 0) / len(v)), 'median': round(sorted(v)[len(v) // 2], 1)} for k, v in sorted(by.items())}
    rows = [{'sym': p.get('sym') or p.get('symbol') or '?', 'who': who_of(p), 'pct': round(float(p['realPct']), 1), 'rule': str(p.get('rule') or (p.get('exit') or {}).get('rule') or '')[:24],
             'at': p.get('closedAt')} for p in ps[-last:][::-1]]
    return {'n': len(ps), 'by': rec, 'last': rows}
