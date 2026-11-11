"""📺 LIVE GAMES BESIDE THE STREAM (owner 2026-11-10: "if they added nfl+ or nba tv to each room ... how agents work live").

The watch room plays the owner's own NFL+ / NBA TV / ESPN in its official player; beside it this reads ESPN's free public scoreboard:
the live score, the clock, the last play, the home side's win chance after every play, the line, and which network carries the game.
Team colours and short names only, never league logos. Read-only, cached, nothing here trades or moves money.
"""
import time

from proof_tools import SPORTS

BASE = 'https://site.api.espn.com/apis/site/v2/sports/{}/{}'
TTL = 15
_CACHE: dict = {}


def _f(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _side(c):
    t = c.get('team') or {}
    rec = (c.get('records') or [{}])[0].get('summary') if c.get('records') else None
    col = str(t.get('color') or '').strip('#')
    return {'abbr': str(t.get('abbreviation') or '')[:6], 'name': str(t.get('shortDisplayName') or t.get('displayName') or '')[:30], 'score': int(_f(c.get('score'), 0) or 0),
            'color': f'#{col}' if len(col) == 6 else None, 'record': rec, 'winner': bool(c.get('winner'))}


def slim_board(raw):
    """ESPN scoreboard JSON → the games, live first, then upcoming, then final."""
    out = []
    for e in (raw or {}).get('events') or []:
        c = (e.get('competitions') or [{}])[0]; st = (e.get('status') or {}).get('type') or {}
        sides = {x.get('homeAway'): _side(x) for x in c.get('competitors') or []}
        if 'home' not in sides or 'away' not in sides:
            continue
        lp = (c.get('situation') or {}).get('lastPlay') or {}; pr = lp.get('probability') or {}
        tv = sorted({n for b in c.get('broadcasts') or [] for n in b.get('names') or []} | {(g.get('media') or {}).get('shortName') for g in c.get('geoBroadcasts') or [] if (g.get('media') or {}).get('shortName')})
        out.append({'id': str(e.get('id') or '')[:20], 'state': st.get('state') or 'pre', 'detail': str(st.get('shortDetail') or '')[:40], 'start': e.get('date'),
                    'home': sides['home'], 'away': sides['away'], 'last': str(lp.get('text') or '')[:160] or None,
                    'homeWin': round(_f(pr.get('homeWinPercentage')) * 100, 1) if _f(pr.get('homeWinPercentage')) is not None else None, 'tv': [x for x in tv if x][:4]})
    order = {'in': 0, 'pre': 1, 'post': 2}
    return sorted(out, key=lambda g: (order.get(g['state'], 3), str(g.get('start') or '')))


def slim_game(raw, plays=8, points=80):
    """ESPN summary JSON → the win chance line (thinned), the newest plays, the line and total."""
    raw = raw or {}; wp = [p for p in raw.get('winprobability') or [] if _f(p.get('homeWinPercentage')) is not None]
    step = max(1, len(wp) // points)
    line = [round(_f(p['homeWinPercentage']) * 100, 1) for p in wp[::step]]
    if wp and (not line or line[-1] != round(_f(wp[-1]['homeWinPercentage']) * 100, 1)):
        line.append(round(_f(wp[-1]['homeWinPercentage']) * 100, 1))
    pl = [{'text': str(p.get('text') or '')[:160], 'clock': (p.get('clock') or {}).get('displayValue'), 'period': (p.get('period') or {}).get('number'), 'score': bool(p.get('scoringPlay'))}
          for p in (raw.get('plays') or [])[-plays:]][::-1]
    pc = (raw.get('pickcenter') or [{}])[0] if raw.get('pickcenter') else {}
    return {'win': line, 'plays': [p for p in pl if p['text']], 'spread': pc.get('details'), 'total': _f(pc.get('overUnder')), 'by': (pc.get('provider') or {}).get('name')}


async def _cached(http, key, url, slim):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        r = await http.get(url, timeout=8)
        v = slim(r.json()) if r.status_code == 200 else None
    except Exception:   # noqa: BLE001 — ESPN down: the last good copy stays
        v = None
    if v is None:
        return hit[1] if hit else None
    _CACHE[key] = (time.time(), v)
    return v


async def board(http, league):
    if league not in SPORTS:
        raise ValueError('No such league.')
    return await _cached(http, f'b:{league}', BASE.format(SPORTS[league][1], 'scoreboard'), slim_board)


async def game(http, league, event):
    if league not in SPORTS or not str(event).isdigit() or len(str(event)) > 14:
        raise ValueError('No such game.')
    return await _cached(http, f'g:{league}:{event}', BASE.format(SPORTS[league][1], 'summary') + f'?event={event}', slim_game)


LEAGUES = [(k, v[0]) for k, v in SPORTS.items()]
