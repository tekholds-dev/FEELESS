"""🏆 Arena league — the competition behind The Pit (pure, tested).

A SEASON is a fixed field of at most FIELD_MAX cards (like the engine playground). Every card starts the season on its own $20
paper book (true fills) that it keeps for the WHOLE season — nothing resets between bells. A season is ROUNDS bells long:
  • each bell pairs the field by the table (1v2, 3v4 … no rematch when another pairing exists), the bigger move THIS bell wins:
    win 3 pts · draw 1 · loss 0;
  • a card whose book is at ≤ $1, or that lost ≥ 75% over its last 3 bells, is CYCLED OUT for a fresh engine-playground card
    (new $20 book, record kept);
  • after the last bell the table decides: points, then the book's $ — the champion is crowned and a new season starts with a
    fresh field, every book back at $20.
Ranking only: it never trades and never promises a result.
"""
import math

FIELD_MAX = 8
ROUNDS = 7
START_USD = 20.0
CUT_USD = 1.0          # a book at or under this is out
CUT_DROP = 75.0        # … or one that lost this much over its last CUT_BELLS bells
CUT_BELLS = 3


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def row(card, now):
    """A card entering the season: its key, look and coins (the book is dealt by the caller at true fills)."""
    return {'key': card['key'], 'name': card.get('name'), 'emoji': card.get('emoji'), 'legs': list(card.get('legs') or [])[:12],
            'w': 0, 'd': 0, 'l': 0, 'pts': 0, 'joinedAt': now, 'hist': [START_USD], 'src': card.get('src') or 'stage'}


def new_season(cards, n, now, field_max=FIELD_MAX):
    """Season n: the first `field_max` unique cards (callers pass them best first)."""
    seen, field = set(), []
    for c in cards or []:
        if c.get('key') and c['key'] not in seen and c.get('legs') and len(field) < field_max:
            seen.add(c['key']); field.append(row(c, now))
    return {'n': n, 'round': 0, 'rounds': ROUNDS, 'startUsd': START_USD, 'at': now, 'field': field, 'played': [], 'cycled': []}


def table(season):
    """Standings: points, then the book's latest $, then fewer losses."""
    return sorted(season.get('field') or [], key=lambda r: (-int(r.get('pts') or 0), -_f((r.get('hist') or [0])[-1]), int(r.get('l') or 0)))


def pair_round(season):
    """Pair by the table: 1v2, 3v4 … — a pairing that already happened this season is swapped with the next card when possible."""
    t = [r['key'] for r in table(season)]
    met = {frozenset(p) for p in season.get('played') or []}
    pairs = []
    while len(t) >= 2:
        a = t.pop(0)
        j = next((i for i, b in enumerate(t) if frozenset((a, b)) not in met), 0)
        pairs.append((a, t.pop(j)))
    return pairs


def settle(season, results, books):
    """results = [{aKey, bKey, winnerKey|None, draw}] for this bell; books = {key: $ now}. Points + the book trail per card."""
    s = {**season, 'field': [dict(r) for r in season.get('field') or []], 'played': list(season.get('played') or [])}
    by = {r['key']: r for r in s['field']}
    for x in results or []:
        a, b = by.get(x.get('aKey')), by.get(x.get('bKey'))
        if not a or not b:
            continue
        s['played'].append([a['key'], b['key']])
        if x.get('draw') or not x.get('winnerKey'):
            a['d'] += 1; b['d'] += 1; a['pts'] += 1; b['pts'] += 1
        else:
            w, l = (a, b) if x['winnerKey'] == a['key'] else (b, a)
            w['w'] += 1; w['pts'] += 3; l['l'] += 1
    for r in s['field']:
        if r['key'] in (books or {}):
            r['hist'] = (list(r.get('hist') or [START_USD]) + [round(_f(books[r['key']]), 4)])[-(ROUNDS + 2):]
    s['round'] = int(s.get('round') or 0) + 1
    return s


def cut(r):
    """Why a card leaves mid-season, or None: book ≤ $1, or ≥ 75% lost over its last 3 bells."""
    h = [_f(x) for x in r.get('hist') or []]
    if h and h[-1] <= CUT_USD:
        return f"book at ${h[-1]:.2f} (≤ ${CUT_USD:g})"
    if len(h) > 1:
        base = h[-(CUT_BELLS + 1)] if len(h) > CUT_BELLS else h[0]
        if base > 0 and (1 - h[-1] / base) * 100 >= CUT_DROP:
            return f"lost {(1 - h[-1] / base) * 100:.0f}% in {min(CUT_BELLS, len(h) - 1)} rounds"
    return None


def cycle(season, fresh, now):
    """Cards that hit a cut leave; the next fresh engine-playground cards (not already in the field) take their seats on $20.
    Returns (season, [{out, why, in}])."""
    s = {**season, 'field': [dict(r) for r in season.get('field') or []], 'cycled': list(season.get('cycled') or [])}
    have = {r['key'] for r in s['field']}
    pool = [c for c in fresh or [] if c.get('key') and c['key'] not in have and c.get('legs')]
    moves = []
    for i, r in enumerate(list(s['field'])):
        why = cut(r)
        if not why:
            continue
        nxt = pool.pop(0) if pool else None
        moves.append({'at': now, 'out': r['name'], 'outKey': r['key'], 'why': why, 'in': (nxt or {}).get('name')})
        if nxt:
            s['field'][s['field'].index(r)] = {**row(nxt, now), 'src': 'playground'}
            have.add(nxt['key'])
        else:
            s['field'].remove(r)
    s['cycled'] = (s['cycled'] + moves)[-40:]
    return s, moves


def done(season):
    return int(season.get('round') or 0) >= int(season.get('rounds') or ROUNDS)


def champion(season):
    t = table(season)
    return t[0] if t else None
