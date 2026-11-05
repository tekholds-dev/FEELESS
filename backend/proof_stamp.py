"""✅ THE 24-HOUR STAMP (owner 2026-11-04): every proof gets PROVED or NOT PROVED a day after it closes. A bid on a game not yet played waits for the final score. Worked out from the folder each time, so nothing can be set by hand. Pure."""
DAY_S = 86400


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _result(kind, f):
    """True won, False lost, None not known yet."""
    if kind == 'PoW':
        if f.get('status') != 'closed' or f.get('propose') or f.get('pnlSol') is None:
            return None
        return _f(f.get('pnlSol')) > 0
    if kind == 'PoP':
        if f.get('status') != 'closed' or f.get('roePct') is None:
            return None
        return _f(f.get('roePct')) > 0
    if f.get('graded') in ('right', 'wrong'):   # PoB and PoC: an owner's mark, or the scoreboard
        return f.get('graded') == 'right'
    if f.get('net') is not None:
        return _f(f.get('net')) > 0
    return None


def of(kind, f, now):
    """{'state': live|waiting|proved|not, 'dueAt', 'lean'}. `lean` is how it stands while waiting."""
    f = f or {}
    if kind in ('PoW', 'PoP') and f.get('status') != 'closed':
        return {'state': 'live', 'dueAt': None, 'lean': None}
    start = _f(f.get('soldAt') or f.get('closedAt') or f.get('at')); due = start + DAY_S; won = _result(kind, f)
    games = f.get('games') or []
    unfinished = kind == 'PoB' and games and not all(g.get('final') for g in games)
    if now < due or unfinished:
        return {'state': 'waiting', 'dueAt': round(due), 'lean': won}
    return {'state': 'proved' if won else 'not', 'dueAt': round(due), 'lean': won}
