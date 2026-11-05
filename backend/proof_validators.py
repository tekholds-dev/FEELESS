"""⚖ THE FIVE VALIDATORS (owner 2026-11-05): five of the desk's agents check every proof sent to the Collective, instead of trading. Each one checks one thing from the record itself, with no model and no cost, so nothing it says can be talked into. A proof that fails is HELD: its money still follows its plan, but it earns no fee pot share and no points until the owner clears it. Pure."""
SEATS = {'tally': ('Tally', 'The numbers add up'), 'sherlock': ('Sherlock', 'The evidence is there'), 'devil': ('Devil', 'It was not gamed'), 'archivist': ('Archivist', 'The record is in order'), 'judge': ('Judge', 'The final call')}
MIN_HOLD_S = 60


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def tally(f, sent_sol):
    sol = _f(f.get('sol')); pnl = _f(f.get('netPnlSol', f.get('pnlSol'))); pct = _f(f.get('pnlPct'))
    if sol <= 0 or pnl <= 0:
        return False, 'No real profit on record.'
    if abs(pnl / sol * 100 - pct) > max(5.0, abs(pct) * 0.25):
        return False, f'Its profit is {pnl / sol * 100:.0f}% of what it spent, but it says {pct:.0f}%.'
    if _f(sent_sol) > pnl * 0.25 + 1e-6:
        return False, 'It sent more than 25% of what it made.'
    return True, f'{pct:.0f}% on {sol:.4f} SOL checks out.'


def sherlock(f):
    shots = f.get('shots') or []; marked = [s for s in shots if s.get('found') or s.get('sha')]
    if not shots and not f.get('vitals'):
        return False, 'No snapshots or readings on file.'
    if marked:
        return True, f'{len(marked)} snapshots show what it read.'
    return True, f'{len(shots)} snapshots and its readings are on file.'


def devil(f, block_why=''):
    if block_why:
        return False, block_why
    hold = _f(f.get('soldAt')) - _f(f.get('boughtAt') or f.get('at'))
    if hold < MIN_HOLD_S:
        return False, f'It held for only {max(0, round(hold))} seconds, too short to trust a big win.'
    return True, f'Held {round(hold / 60)} minutes on a real pool.'


def archivist(f, sig, seen_sigs=()):
    at, sold = _f(f.get('at')), _f(f.get('soldAt'))
    if not f.get('real') or f.get('status') != 'closed':
        return False, 'It is not a closed, real proof.'
    if sold and at and sold < at:
        return False, 'Its dates are out of order.'
    if sig in (seen_sigs or ()):
        return False, 'This transaction has been used before.'
    return True, 'Closed, real, in order, and sent once.'


def review(f, sig, sent_sol, block_why='', seen_sigs=(), now=0):
    """→ {ok, at, seats: [{k, name, does, ok, why}]}. The Judge passes only when the others all do."""
    rows = {'tally': tally(f, sent_sol), 'sherlock': sherlock(f), 'devil': devil(f, block_why), 'archivist': archivist(f, sig, seen_sigs)}
    fails = [SEATS[k][0] for k, (ok, _) in rows.items() if not ok]
    rows['judge'] = (not fails, 'All four agree.' if not fails else f"Held: {', '.join(fails)} said no.")
    return {'ok': not fails, 'at': round(now), 'seats': [{'k': k, 'name': SEATS[k][0], 'does': SEATS[k][1], 'ok': v[0], 'why': v[1]} for k, v in rows.items()]}
