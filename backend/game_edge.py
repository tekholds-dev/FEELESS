"""🏟 THE GAME ROOM'S NUMBERS (owner 2026-11-05). Pure functions over ESPN's free game summary, so every number on screen can be traced to a field ESPN sent.
- `plays_of`: the play by play, each play placed on the game's own clock (`at`, 0 to 1). The live fingerprint draws from this.
- `edge_of`: the vitals behind a bid: the officials, how the line moved, rest, recent form, pace against the total, the current run, foul trouble.
- `reads_of`: those vitals in one sentence each. They are readings of real numbers, never a promise and never a tip to bet. The two reads that need the board's market prices are made on the page (`lib/gamePrint.js` `marketReads`).
- `print_rows`: a team's or a player's stats this season against last season. Their fingerprint draws from this.
Nothing here is invented: a field ESPN did not send stays missing, and the screen leaves it out."""
import re

# periods and minutes per period. Baseball runs on innings, so its periods have no clock.
GAME_SHAPE = {'nfl': (4, 15), 'cfb': (4, 15), 'nba': (4, 12), 'cbb': (2, 20), 'nhl': (3, 20), 'mlb': (9, 0)}
SOCCER_SHAPE = (2, 45)
QUIET = re.compile(r'substitution|timeout|time out|tvtimeout|end period|end of', re.I)
LOWER_IS_BETTER = {'TO', 'TOV', 'PF', 'GA', 'ERA', 'L', 'INT', 'SACK', 'WHIP', 'GAA', 'BB', 'AST/TO-'}
FOUL_LIMIT = 4
HOT_PCT = 20.0


def _f(v):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return None


def _shape(sport):
    return GAME_SHAPE.get(sport, SOCCER_SHAPE)


def _clock_s(text):
    m = re.fullmatch(r'(\d+):(\d+(?:\.\d+)?)', str(text or '').strip())
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    return _f(text)


def game_at(sport, period, clock):
    """Where a moment sits on the game: 0 at the start, 1 at the end of regulation. Overtime stays at 1."""
    n, mins = _shape(sport); per = max(1, int(_f(period) or 1))
    if not mins:
        return min(1.0, (per - 1) / n)
    left = _clock_s(clock)
    part = 0.0 if left is None else max(0.0, min(1.0, 1 - left / (mins * 60)))
    return min(1.0, (per - 1 + part) / n)


def _raw_plays(data):
    rows = data.get('plays') or []
    if rows:
        return rows
    drives = (data.get('drives') or {})
    out = []
    for d in (drives.get('previous') or []) + ([drives['current']] if isinstance(drives.get('current'), dict) else []):
        tid = (d.get('team') or {}).get('id')
        out += [{**p, 'team': p.get('team') or ({'id': tid} if tid else None)} for p in d.get('plays') or []]
    return out or data.get('scoringPlays') or []


def plays_of(data, sport, away_id, keep_text=60):
    """Every play worth drawing, oldest first. Only the newest keep their words, to keep the poll small. side: 'a' away, 'b' home, None neither."""
    wp = {str(w.get('playId')): w.get('homeWinPercentage') for w in data.get('winprobability') or []}
    rows = []
    for p in _raw_plays(data):
        kind = str((p.get('type') or {}).get('text') or '')
        if QUIET.search(kind):
            continue
        tid = str((p.get('team') or {}).get('id') or ''); xy = p.get('coordinate') or {}; x, y = _f(xy.get('x')), _f(xy.get('y'))
        per = (p.get('period') or {}); clock = (p.get('clock') or {}).get('displayValue')
        row = {'id': str(p.get('id') or p.get('sequenceNumber') or len(rows)), 'type': kind, 'text': p.get('text') or '', 'clock': clock, 'per': per.get('number'), 'perName': per.get('displayValue'),
               'a': int(_f(p.get('awayScore')) or 0), 'b': int(_f(p.get('homeScore')) or 0), 'pts': int(_f(p.get('scoreValue')) or 0) if p.get('scoringPlay') else 0,
               'side': None if not tid else 'a' if tid == str(away_id) else 'b', 'at': round(game_at(sport, per.get('number'), clock), 4), 'shot': bool(p.get('shootingPlay')), 'made': bool(p.get('scoringPlay'))}
        w = wp.get(str(p.get('id')))
        if w is not None:
            row['wp'] = round(float(w), 3)
        if row['shot'] and x is not None and y is not None and 0 <= x <= 50 and 0 <= y <= 94:
            row['x'], row['y'] = x, y
        rows.append(row)
    for r in rows[:-keep_text] if keep_text else []:
        r.pop('text', None); r.pop('perName', None)
    return rows


def current_run(plays):
    """The points in a row one side has scored, newest back. → {'side', 'pts'} or None."""
    side = None; pts = 0
    for p in reversed(plays or []):
        if not p.get('pts'):
            continue
        if side is None:
            side = p.get('side')
        if p.get('side') != side:
            break
        pts += p['pts']
    return {'side': side, 'pts': pts} if side and pts else None


def _line(row):
    """'-1.5', 'o222.5', 'PK' → a number or None."""
    m = re.search(r'-?\d+(?:\.\d+)?', str(row or '').lower().replace('pk', '0'))
    return float(m.group(0)) if m else None


def _odds_moves(pick):
    home = (pick.get('pointSpread') or {}).get('home') or {}; over = (pick.get('total') or {}).get('over') or {}
    out = {}
    s_open, s_now = _line((home.get('open') or {}).get('line')), _line((home.get('close') or {}).get('line'))
    t_open, t_now = _line((over.get('open') or {}).get('line')), _line((over.get('close') or {}).get('line'))
    if s_open is not None and s_now is not None:
        out['spread'] = {'open': s_open, 'now': s_now}
    if t_open is not None and t_now is not None:
        out['total'] = {'open': t_open, 'now': t_now}
    return out


def _form(row, tid, now_iso=None):
    """A side's last games: wins, losses, average margin and points."""
    ev = (row or {}).get('events') or []; w = l = 0; mine = []; them = []; dates = []
    for e in ev:
        r = str(e.get('gameResult') or '')[:1]; w += r == 'W'; l += r == 'L'
        h, a = _f(e.get('homeTeamScore')), _f(e.get('awayTeamScore'))
        if h is not None and a is not None:
            home = str(e.get('homeTeamId')) == str(tid); mine.append(h if home else a); them.append(a if home else h)
        if e.get('gameDate'):
            dates.append(str(e['gameDate']))
    if not ev:
        return None
    return {'n': len(ev), 'w': w, 'l': l, 'ppg': round(sum(mine) / len(mine), 1) if mine else None, 'opp': round(sum(them) / len(them), 1) if them else None, 'margin': round((sum(mine) - sum(them)) / len(mine), 1) if mine else None, 'last': max(dates) if dates else None}


def _days_between(a, b):
    from datetime import datetime
    try:
        pa = datetime.fromisoformat(str(a).replace('Z', '+00:00')); pb = datetime.fromisoformat(str(b).replace('Z', '+00:00'))
        return round((pb - pa).total_seconds() / 86400, 1)
    except ValueError:
        return None


def _box_players(data, away_id):
    """Each side's players as ESPN's box has them now: {side: [{id, name, vals}]}."""
    out = {'a': [], 'b': []}
    for t in (data.get('boxscore') or {}).get('players') or []:
        side = 'a' if str((t.get('team') or {}).get('id')) == str(away_id) else 'b'
        for g in t.get('statistics') or []:
            labels = g.get('labels') or []
            for r in g.get('athletes') or []:
                vals = dict(zip(labels, r.get('stats') or []))
                if vals and (r.get('athlete') or {}).get('displayName'):
                    out[side].append({'id': str(r['athlete'].get('id') or ''), 'name': r['athlete']['displayName'], 'vals': vals})
    return out


def _team_box(data, away_id):
    """{side: {statName: display}} from the box."""
    out = {}
    for t in (data.get('boxscore') or {}).get('teams') or []:
        side = 'a' if str((t.get('team') or {}).get('id')) == str(away_id) else 'b'
        out[side] = {x.get('name'): x.get('displayValue') for x in t.get('statistics') or []}
    return out


def edge_of(data, sport, teams, plays=None):
    """🎯 The vitals behind a bid, from what ESPN sent. Left out when missing."""
    if len(teams) != 2:
        return {}
    away, home = teams; aid = away.get('id'); gi = data.get('gameInfo') or {}; pick = (data.get('pickcenter') or [{}])[0] or {}; comp = ((data.get('header') or {}).get('competitions') or [{}])[0]
    state = ((comp.get('status') or {}).get('type') or {}).get('state'); date = comp.get('date'); out = {}
    crew = [{'name': o.get('displayName'), 'role': (o.get('position') or {}).get('name')} for o in gi.get('officials') or [] if o.get('displayName')]
    if crew:
        out['crew'] = crew[:5]
    w = gi.get('weather') or {}
    if w.get('temperature') is not None:
        out['weather'] = {'temp': w.get('temperature'), 'gust': w.get('gust'), 'rain': w.get('precipitation')}
    if gi.get('attendance'):
        out['attendance'] = gi['attendance']
    moves = _odds_moves(pick)
    if moves:
        out['moves'] = moves
    if pick.get('details'):
        out['ml'] = {'a': (pick.get('awayTeamOdds') or {}).get('moneyLine'), 'b': (pick.get('homeTeamOdds') or {}).get('moneyLine'), 'by': (pick.get('provider') or {}).get('name')}
    pr = data.get('predictor') or {}
    pa, ph = _f((pr.get('awayTeam') or {}).get('gameProjection')), _f((pr.get('homeTeam') or {}).get('gameProjection'))
    if pa is not None and ph is not None:
        out['model'] = {'a': round(pa / 100, 3), 'b': round(ph / 100, 3)}
    ats = {}
    for row in data.get('againstTheSpread') or []:
        rec = [{'k': r.get('type') or r.get('displayName'), 'v': r.get('summary')} for r in row.get('records') or [] if r.get('summary')]
        if rec:
            ats['a' if str((row.get('team') or {}).get('id')) == str(aid) else 'b'] = rec[:3]
    if ats:
        out['ats'] = ats
    forms = {}
    for row in data.get('lastFiveGames') or []:
        tid = (row.get('team') or {}).get('id'); f = _form(row, tid)
        if f:
            if date and f.get('last'):
                f['restDays'] = _days_between(f['last'], date)
            forms['a' if str(tid) == str(aid) else 'b'] = f
    if forms:
        out['form'] = forms
    total = _f(pick.get('overUnder'))
    fa, fb = forms.get('a') or {}, forms.get('b') or {}
    if fa.get('ppg') is not None and fb.get('ppg') is not None and total:
        out['formTotal'] = {'sum': round(fa['ppg'] + fb['ppg'], 1), 'total': total}
    if plays and state in ('in', 'post'):
        last = plays[-1]; at = max((p.get('at') or 0) for p in plays); now_pts = last['a'] + last['b']
        out['score'] = {'a': last['a'], 'b': last['b'], 'at': at}
        if state == 'in' and at >= 0.1:
            out['pace'] = {'proj': round(now_pts / at, 1), 'total': total, 'at': at}
        run = current_run(plays)
        if run and state == 'in':
            out['run'] = run
    tb = _team_box(data, aid)
    if state in ('in', 'post') and tb:
        rows = [('Lead changes', 'leadChanges'), ('Biggest lead', 'largestLead'), ('Fast break', 'fastBreakPoints'), ('In the paint', 'pointsInPaint'), ('Off turnovers', 'turnoverPoints'), ('Fouls', 'fouls')]
        out['flow'] = [{'label': l, 'a': (tb.get('a') or {}).get(k), 'b': (tb.get('b') or {}).get(k)} for l, k in rows if (tb.get('a') or {}).get(k) is not None or (tb.get('b') or {}).get(k) is not None]
    if state == 'in':
        box = _box_players(data, aid); trouble = []
        for side, rows in box.items():
            for r in rows:
                pf = _f(r['vals'].get('PF'))
                if pf is not None and pf >= FOUL_LIMIT:
                    trouble.append({'side': side, 'name': r['name'], 'pf': int(pf), 'pts': r['vals'].get('PTS')})
        if trouble:
            out['fouls'] = sorted(trouble, key=lambda r: -r['pf'])[:5]
    return out


def box_of(data, away_id):
    """Tonight's box per player, so a season average can stand beside tonight's number. {playerId: {'side', 'name', 'vals'}}"""
    out = {}
    for side, rows in _box_players(data, away_id).items():
        for r in rows:
            if r['id']:
                out[r['id']] = {'side': side, 'name': r['name'], 'vals': r['vals']}
    return out


def hot_of(rows):
    """Who is well above or below their own season, from their last games. rows: [{'name','side','stat','season','recent'}]. → hottest and coldest first."""
    out = []
    for r in rows or []:
        s, n = _f(r.get('season')), _f(r.get('recent'))
        if s is None or n is None or s < 3:
            continue
        pct = round((n - s) / s * 100)
        if abs(pct) >= HOT_PCT:
            out.append({**r, 'pct': pct, 'hot': pct > 0})
    return sorted(out, key=lambda r: -abs(r['pct']))[:6]


def reads_of(edge, teams):
    """One honest sentence per vital worth a look. tone: 'a' / 'b' for the side it leans to, '' for neither. Never a promise."""
    if len(teams) != 2:
        return []
    nm = {'a': teams[0].get('abbr') or 'Away', 'b': teams[1].get('abbr') or 'Home'}; out = []
    m = (edge.get('moves') or {}).get('spread')
    if m and abs(m['now'] - m['open']) >= 0.5:
        d = m['now'] - m['open']; out.append({'k': 'LINE MOVE', 'text': f"The spread moved {abs(d):g} toward {nm['b'] if d < 0 else nm['a']}, from {m['open']:g} to {m['now']:g}.", 'tone': 'b' if d < 0 else 'a'})
    t = (edge.get('moves') or {}).get('total')
    if t and abs(t['now'] - t['open']) >= 0.5:
        out.append({'k': 'TOTAL MOVE', 'text': f"The total moved from {t['open']:g} to {t['now']:g}.", 'tone': ''})
    p = edge.get('pace')
    if p and p.get('total'):
        d = p['proj'] - p['total']; out.append({'k': 'PACE', 'text': f"At this pace it ends near {p['proj']:g}, {abs(d):.1f} {'over' if d > 0 else 'under'} the {p['total']:g} total.", 'tone': ''})
    r = edge.get('run')
    if r and r['pts'] >= 6:
        out.append({'k': 'RUN', 'text': f"{nm[r['side']]} has scored the last {r['pts']} unanswered.", 'tone': r['side']})
    f = edge.get('formTotal')
    if f and abs(f['sum'] - f['total']) >= 4:
        d = f['sum'] - f['total']; out.append({'k': 'FORM AND TOTAL', 'text': f"Their last games add up to {f['sum']:g} a night, {abs(d):.1f} {'above' if d > 0 else 'below'} the {f['total']:g} total. Opponents differ.", 'tone': ''})
    fo = edge.get('form') or {}; ra, rb = (fo.get('a') or {}).get('restDays'), (fo.get('b') or {}).get('restDays')
    if ra is not None and rb is not None and abs(ra - rb) >= 1 and min(ra, rb) <= 2:
        out.append({'k': 'REST', 'text': f"{nm['a']} last played {ra:g} days ago, {nm['b']} {rb:g}.", 'tone': 'a' if ra > rb else 'b'})
    tr = edge.get('fouls') or []
    if tr:
        out.append({'k': 'FOUL TROUBLE', 'text': ', '.join(f"{x['name']} ({x['pf']} fouls)" for x in tr[:2]) + '.', 'tone': 'b' if tr[0]['side'] == 'a' else 'a'})
    return out[:7]


def _num(v):
    return _f(str(v).replace('%', '')) if v is not None else None


def score_change(abbr, now, last):
    """A ring's ink, 0 to 100: 50 is the same as last season, higher is better. A stat where less is better counts the other way."""
    if now is None or last is None or not last:
        return 50.0
    d = (now - last) / abs(last) * 100
    return round(max(0.0, min(100.0, 50 - d * 1.5 if abbr in LOWER_IS_BETTER else 50 + d * 1.5)), 1)


def print_rows(labels, now_vals, last_vals, want=None):
    """This season against last, one row per stat, for a fingerprint. Non numbers and shared attempts ('3-7') are dropped."""
    out = []
    for i, ab in enumerate(labels or []):
        if want and ab not in want:
            continue
        n = _num(now_vals[i]) if i < len(now_vals or []) else None
        l = _num(last_vals[i]) if last_vals and i < len(last_vals) else None
        if n is None:
            continue
        out.append({'abbr': ab, 'now': n, 'last': l, 'score': score_change(ab, n, l)})
    return out


def team_rows(now_stats, last_stats, limit=10):
    """Two seasons of a team's stat categories → print rows. Pure."""
    def flat(d):
        out = {}
        for c in (((d or {}).get('results') or {}).get('stats') or {}).get('categories') or []:
            for x in c.get('stats') or []:
                ab = x.get('abbreviation'); v = _num(x.get('displayValue'))
                if ab and v is not None and ab not in out and ab != 'GP':
                    out[ab] = (v, x.get('displayName'))
        return out
    a, b = flat(now_stats), flat(last_stats); first = ('PTS', 'REB', 'AST', 'FG%', '3P%', 'FT%', 'STL', 'BLK', 'TO', 'YDS', 'TD', 'G', 'SOG', 'R', 'HR', 'AVG', 'ERA')
    keys = sorted(a, key=lambda k: first.index(k) if k in first else 99)[:limit]
    return [{'abbr': k, 'label': a[k][1], 'now': a[k][0], 'last': (b.get(k) or (None,))[0], 'score': score_change(k, a[k][0], (b.get(k) or (None,))[0])} for k in keys]


def player_rows(stats, limit=10):
    """ESPN's per-season stat table for a player → print rows for this season against the one before. Pure."""
    cat = next((c for c in (stats or {}).get('categories') or [] if c.get('name') == 'averages'), None) or ((stats or {}).get('categories') or [None])[0]
    if not cat:
        return [], None
    rows = cat.get('statistics') or []
    if not rows:
        return [], None
    first = ('PTS', 'REB', 'AST', '3P%', 'FG%', 'FT%', 'STL', 'BLK', 'TO', 'MIN', 'YDS', 'TD', 'G', 'A', 'AVG', 'HR', 'RBI', 'ERA')
    labels = cat.get('labels') or []; now = rows[-1].get('stats') or []; last = rows[-2].get('stats') if len(rows) > 1 else None
    all_ = print_rows(labels, now, last)
    y = rows[-1].get('season') or {}
    return sorted((r for r in all_ if r['abbr'] not in ('GP', 'GS')), key=lambda r: first.index(r['abbr']) if r['abbr'] in first else 99)[:limit], (y.get('displayName') if isinstance(y, dict) else y)
