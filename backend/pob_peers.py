"""🤝 FILED PROOFS ARE REFERENCE (Slice 11 · VISION › stash brain: "a new PoB is compared against any other agent's PoB on the same game, and the
record shows where they agree and disagree"). Pure.

A new PoB's picks are set beside every OTHER agent's PoB on the same real game (same ESPN game id, or the same two teams within 36 h) and
beside COMP's reference for that game (what ESPN's line, Kalshi and Polymarket favour, read with no model: comp_ahead.reference).
Two picks AGREE when they back the same side of the same thing (the same Kalshi market and side; the same team to win or to cover; the same
side of the total; or the same words), and DISAGREE when they back opposite sides of it (the other team to win, the other side of the line or
the total, the other side of one Kalshi market). Picks about different things are neither, and are not counted."""
import re
import time

import pob as _pob
import stash_sort as _sort

WINDOW_S = 36 * 3600
PEERS_MAX = 12
ROWS_MAX = 12
_WIN = re.compile(r'(?i)\b(win|wins|to beat|beat|beats|moneyline|ml|straight up|su)\b')
_TOTAL = re.compile(r'(?i)\b(over|under|o|u)\s*\d{2,3}(?:\.\d)?\b|\b(total|points scored)\b')
_SPREAD = re.compile(r'(?<![\w.])[+\-−]\d{1,2}(?:\.\d)?\b')


def _nicks(text):
    t = _sort.teams_on(str(text or ''))
    return {n for v in t.values() for n in v}


def _game_teams(f):
    """The two teams a folder is about: its saved games' names, else its topic's team words. Pure."""
    top = _nicks(f.get('topic') or f.get('q') or '')
    if len(top) >= 2:   # the matchup it was asked about decides (its saved games can hold a namesake from another sport)
        return top
    out = set(top)
    for g in f.get('games') or []:
        if isinstance(g, dict):
            out |= _nicks(f"{g.get('label') or ''} {g.get('side') or ''} {g.get('name') or ''}".replace(' at ', ' vs '))
    return out


def classify(pick):
    """A pick → what it is about and which side it backs. {'kind': win|spread|total|kalshi|other, 'teams', 'side', 'key'}. Pure."""
    p = pick if isinstance(pick, dict) else {'pick': str(pick)}
    text = str(p.get('pick') or ''); low = text.lower(); teams = _nicks(text)
    k = p.get('kalshi') if isinstance(p.get('kalshi'), dict) else {}
    base = {'pick': text[:90], 'teams': sorted(teams), 'key': _pob._key(text), 'conf': p.get('confidence')}
    if k.get('ticker') and k.get('side'):
        mk, sd = str(k['ticker']).upper(), str(k['side']).lower()
        win = next(iter(teams)) if 'GAME' in mk and sd == 'yes' and len(teams) == 1 else None   # 'Clippers to win' tagged LAC YES is still the Clippers to win
        return {**base, 'kind': 'kalshi', 'market': mk, 'side': sd, **({'win': win} if win else {})}
    if _TOTAL.search(text) and (re.search(r'(?i)\b(over|under)\b', text) or len(teams) != 1):
        side = 'over' if re.search(r'(?i)\bover\b|\bo\s*\d', text) else 'under' if re.search(r'(?i)\bunder\b|\bu\s*\d', text) else None
        if side and len(teams) != 1 and not re.search(r'(?i)\b(points|rebounds|assists|pts|reb|ast|yards|yds)\b.*\b(over|under)\b|\b(over|under)\b.*\b(points|rebounds|assists|pts|reb|ast|yards|yds)\b', low.replace('total points', '')):
            return {**base, 'kind': 'total', 'side': side}
    if len(teams) == 1 and _SPREAD.search(text) and not re.search(r'(?i)\b(points|rebounds|assists|pts|reb|ast)\b', low):
        return {**base, 'kind': 'spread', 'side': next(iter(teams))}
    if len(teams) == 1 and (_WIN.search(text) or len(text.split()) <= 3):
        return {**base, 'kind': 'win', 'side': next(iter(teams))}
    if len(teams) == 2 and re.search(r'(?i)\b(to beat|beat|beats|over)\b', text):
        first = min(teams, key=lambda n: low.find(n) if n in low else 999)
        return {**base, 'kind': 'win', 'side': first}
    return {**base, 'kind': 'other', 'side': None}


def picks_of(f):
    """Every pick a folder's minds made (each once), classified. Pure."""
    out, seen = [], set()
    for c in f.get('calls') or []:
        for p in (c.get('picks') or []) if isinstance(c, dict) else []:
            if not isinstance(p, dict) or not str(p.get('pick') or '').strip():
                continue
            x = {**classify(p), 'mind': c.get('name')}
            sig = (x['kind'], x.get('market'), x['side'], x['key'] if x['kind'] == 'other' else '')
            if sig in seen:
                continue
            seen.add(sig); out.append(x)
    return out


def versus(a, b, teams):
    """'agree', 'disagree' or None (about different things). Pure."""
    if a['kind'] == 'kalshi' or b['kind'] == 'kalshi':
        wa, wb = (a.get('win') if a['kind'] == 'kalshi' else a['side'] if a['kind'] == 'win' else None), (b.get('win') if b['kind'] == 'kalshi' else b['side'] if b['kind'] == 'win' else None)
        if a['kind'] != b['kind'] and wa and wb:   # one tagged its Kalshi market, the other said it in words
            return 'agree' if wa == wb else 'disagree' if {wa, wb} <= (teams or {wa, wb}) else None
        if a['kind'] == b['kind'] == 'kalshi' and a.get('market') == b.get('market'):
            return 'agree' if a['side'] == b['side'] else 'disagree'
        if a['kind'] == b['kind'] == 'kalshi':
            ga, gb = re.sub(r'-[A-Z]{2,4}$', '', a['market']), re.sub(r'-[A-Z]{2,4}$', '', b['market'])   # KXNBAGAME-..-LAC vs ..-SA: one game, two sides
            if ga == gb and 'GAME' in ga and a['side'] == b['side'] == 'yes':
                return 'disagree'
        return None
    if a['kind'] != b['kind'] or a['kind'] == 'other':
        return 'agree' if a['key'] and a['key'] == b['key'] else None
    if a['kind'] == 'total':
        return 'agree' if a['side'] == b['side'] else 'disagree'
    if a['side'] == b['side']:
        return 'agree'
    return 'disagree' if {a['side'], b['side']} <= (teams or {a['side'], b['side']}) else None


def _same_game(f, x):
    if _pob.same_game(f, x):
        return True
    ta, tb = _game_teams(f), _game_teams(x)
    try:
        close = abs(float(f.get('at') or time.time()) - float(x.get('at') or 0)) < WINDOW_S
    except (TypeError, ValueError):
        close = False
    return len(ta) >= 2 and ta == tb and close


def _vs_rows(mine, theirs, teams):
    agree, disagree = [], []
    for a in mine:
        for b in theirs:
            v = versus(a, b, teams)
            if v:
                (agree if v == 'agree' else disagree).append({'ours': a['pick'], 'theirs': b['pick'], 'about': a['kind']})
    return agree[:ROWS_MAX], disagree[:ROWS_MAX]


def vs_comp(mine, ref):
    """Our picks beside COMP's reference (each source's favourite to win, the line). → (agree, disagree) rows. Pure."""
    agree, disagree = [], []
    fav = (ref or {}).get('fav') or {}; teams = set((ref or {}).get('teams') or [])
    for a in mine:
        if a['kind'] not in ('win', 'kalshi'):   # a spread on the underdog can still agree with the favourite to win: only straight win picks are set beside it
            continue
        abbr = {str(v).upper(): k for k, v in ((ref or {}).get('abbr') or {}).items()}
        side = a['side'] if a['kind'] != 'kalshi' else a.get('win') or (abbr.get(str(a.get('market') or '').rsplit('-', 1)[-1]) if a['side'] == 'yes' and 'GAME' in str(a.get('market')) else None)
        if not side or (teams and side not in teams):
            continue
        for host, f_ in fav.items():
            row = {'ours': a['pick'], 'theirs': f'{host} favours the {f_}', 'about': 'win', 'source': host}
            (agree if f_ == side else disagree).append(row)
    return agree[:ROWS_MAX], disagree[:ROWS_MAX]


def ref_for(f, refs):
    """COMP's reference for this folder's game: its ESPN game id, else the same two teams. Pure."""
    ids = {str(g.get('id')) for g in f.get('games') or [] if isinstance(g, dict) and g.get('id')}
    for i in ids:
        if i in (refs or {}):
            return refs[i]
    teams = _game_teams(f)
    if len(teams) >= 2:
        rows = [r for r in (refs or {}).values() if set(r.get('teams') or []) == teams]
        if rows:
            return max(rows, key=lambda r: r.get('at') or 0)
    return None


def compare(f, cat_id, cats, refs=None, now=None):
    """🤝 The record's `peers`: this PoB beside every other agent's PoB on the same game, and COMP's reference. Pure.
    cats = [{'id', 'name', 'pobFolders'}]; refs = comp_ahead's references by game id."""
    now = float(now or time.time()); mine = picks_of(f); teams = _game_teams(f)
    rows = []
    for c in cats or []:
        if not isinstance(c, dict) or c.get('id') == cat_id:
            continue
        for x in (c.get('pobFolders') or [])[-40:]:
            if not isinstance(x, dict) or x.get('id') == f.get('id') or not _same_game(f, x):
                continue
            theirs = picks_of(x); ag, dis = _vs_rows(mine, theirs, teams)
            rows.append({'agent': c.get('name'), 'agentId': c.get('id'), 'n': x.get('n'), 'id': x.get('id'), 'at': x.get('at'), 'test': bool(x.get('test') or x.get('testRun')),
                         'topic': str(x.get('topic') or '')[:80], 'picks': [p['pick'] for p in theirs][:8], 'agree': ag, 'disagree': dis,
                         'graded': x.get('graded'), 'verdict': 'agree' if ag and not dis else 'disagree' if dis and not ag else 'split' if ag and dis else 'no overlap'})
    rows.sort(key=lambda r: -(float(r.get('at') or 0)))
    ref = ref_for(f, refs); cag, cdis = vs_comp(mine, ref)
    comp = {'game': ref.get('label'), 'id': ref.get('id'), 'readAt': ref.get('at'), 'fav': ref.get('fav'), 'line': ref.get('line'), 'total': ref.get('total'),
            'agree': cag, 'disagree': cdis} if ref else None
    out = {'teams': sorted(teams), 'picks': [p['pick'] for p in mine][:8], 'peers': rows[:PEERS_MAX], 'comp': comp,
           'agree': sum(len(r['agree']) for r in rows) + len(cag), 'disagree': sum(len(r['disagree']) for r in rows) + len(cdis),
           'agents': len({r['agentId'] for r in rows}), 'at': round(now)}
    return out


def say(p):
    """One plain line for the record's check. Pure."""
    if not p:
        return 'not compared'
    bits = []
    if p.get('peers'):
        bits.append(f"{len(p['peers'])} PoB{'s' if len(p['peers']) != 1 else ''} by {p['agents']} other agent{'s' if p['agents'] != 1 else ''} on this game")
    else:
        bits.append('no other agent has filed this game')
    if p.get('comp'):
        bits.append(f"COMP's reference ({', '.join(f'{h} {t}' for h, t in (p['comp'].get('fav') or {}).items()) or 'no favourite read'})")
    return f"{'; '.join(bits)}: {p.get('agree', 0)} agree, {p.get('disagree', 0)} disagree"
