"""✅ THE 24-HOUR STAMP (owner 2026-11-04): every proof gets PROVED or NOT PROVED a day after it closes. Worked out from the folder each time,
so nothing can be set by hand. Pure.

🔒 RESULTS BEAT GRADES (owner 2026-11-13, GPT · Grok · Claude agreed): wherever a real result exists it alone decides the stamp.
  · PoW = the trade's P&L · PoP = the position's return · PoB on real games = the final scores (a market settlement graded by Polymarket counts too)
  · a hand mark ('right' / 'wrong') decides only where nothing outside can: a research-only PoB, PoC, PoStatic, PoEco. It is still kept
    (as `graded`, the prediction-quality note) and shown, it just never overrides a score.
  · PoB legs: a leg that lost → NOT PROVED (a parlay is lost once one leg loses). A leg still unplayed waits. A leg the scoreboard never
    finished (postponed, dropped) is VOID after the grace in the proof's OWN rule version (`stampRules`, saved when it was filed, so a rule
    can never be changed after the result is known). If every leg is void there is no result: state 'void', never a win.
"""
from fnum import plain as _f
DAY_S = 86400
RULES = {   # 📜 settlement rules by version. A new version is ADDED, never edited: each proof settles by the version it was filed under.
    1: {'gameGraceS': 3 * DAY_S, 'since': '2026-11-13', 'why': 'A game unfinished 3 days past the stamp is void (folders filed before rule versions existed get this one, all alike)'},
}
CURRENT_RULES = 1
GAME_GRACE_S = RULES[CURRENT_RULES]['gameGraceS']   # kept for callers / tests that read it
OUTSIDE = ('scoreboard', 'polymarket')   # graders that are the outside world, not a person


def rules_of(f):
    return RULES.get(int((f or {}).get('stampRules') or 1), RULES[1])


def _games_result(f, now):
    """PoB legs → (won True/False/None, 'void' | 'pending' | 'settled'). Pure."""
    games = [g for g in (f.get('games') or []) if isinstance(g, dict)]
    start = _f(f.get('soldAt') or f.get('closedAt') or f.get('at')); due = start + DAY_S
    grace = rules_of(f)['gameGraceS']
    lost = any(g.get('final') and g.get('won') is False for g in games)
    pending = [g for g in games if not g.get('final') and now < due + grace]
    live = [g for g in games if g.get('final')]
    if lost:
        return False, 'settled'
    if pending:
        return None, 'pending'
    if not live:
        return None, 'void'
    return all(g.get('won') for g in live), 'settled'


def _result(kind, f, now=None):
    """True won, False lost, None not known yet."""
    if kind == 'PoW':
        if f.get('status') != 'closed' or f.get('propose') or f.get('pnlSol') is None:
            return None
        return _f(f.get('pnlSol')) > 0
    if kind == 'PoP':
        if f.get('status') != 'closed' or f.get('roePct') is None:
            return None
        return _f(f.get('roePct')) > 0
    if kind == 'PoB' and f.get('gradedBy') not in OUTSIDE and f.get('games'):   # the scores decide, never a hand mark
        return _games_result(f, now if now is not None else float('inf'))[0]
    if f.get('graded') in ('right', 'wrong'):   # an outside settlement, or a hand mark where nothing outside settles it
        return f.get('graded') == 'right'
    if f.get('net') is not None:
        return _f(f.get('net')) > 0
    return None


def of(kind, f, now):
    """{'state': live|waiting|proved|not|void, 'dueAt', 'lean'}. `lean` is how it stands while waiting."""
    f = f or {}
    if kind in ('PoW', 'PoP') and f.get('status') != 'closed':
        return {'state': 'live', 'dueAt': None, 'lean': None}
    start = _f(f.get('soldAt') or f.get('closedAt') or f.get('at')); due = start + DAY_S; won = _result(kind, f, now)
    if kind == 'PoB' and f.get('gradedBy') not in OUTSIDE and f.get('games'):
        _w, how = _games_result(f, now)
        if now < due or how == 'pending':
            return {'state': 'waiting', 'dueAt': round(due), 'lean': won}
        if how == 'void':
            return {'state': 'void', 'dueAt': round(due), 'lean': None}
        return {'state': 'proved' if won else 'not', 'dueAt': round(due), 'lean': won}
    if now < due:
        return {'state': 'waiting', 'dueAt': round(due), 'lean': won}
    return {'state': 'proved' if won else 'not', 'dueAt': round(due), 'lean': won}
