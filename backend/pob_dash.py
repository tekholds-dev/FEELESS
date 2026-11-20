"""🎲 Slice 13 · the PoB folder dashboard (owner: "make PoB a sleek dashboard that views everything beautifully when I / a user opens the PoB
folder: either build their own or see what to have the agent file").

One read for the Bids home: the agent's filings with their results, P&L without fees (money that reached Kalshi = filled × price; fees never in
it, CLAUDE.md §1, kalshi_bid.room_view), the judges' scores, fresh odds from the stash (COMP's per-game reference, comp_ahead refs.json, read
every 20 min with no model), the games live and coming up, and "what to file next" from tonight's markets, each one filed with one tap.

A user's own slip goes through the SAME checks as the minds' slip: only legs Kalshi really lists, 2..4 legs, no leg that repeats another, both
minds must back every leg on what they read (a player leg with its own evidence and number), every cap and guard on the send, a TEST never
bids. A slip the minds do not back whole is never sent, and the record says which leg failed and why. Everything here is pure except
`menu`, which makes public Kalshi reads (no key)."""
import calendar
import re
import time

import kalshi_bid as _kb
import pob as _pob

STALE_S = 45 * 60           # a stash odds read older than this is shown as stale (COMP reads every 20 min)
SOON_S = 36 * 3600          # "coming up" = the next 36 h, as COMP reads it
LEAD_S = 10 * 60            # a game this close to its start is not suggested: the minds need time to read
NEXT_MAX, ODDS_MAX, LIVE_MAX, ROWS_MAX = 6, 14, 8, 40
PROP_SPORTS = {'nba', 'nfl', 'nhl', 'mlb'}    # leagues whose Kalshi games have player/spread/total legs (kalshi_bid.PROP_SERIES)
KALSHI_SPORTS = {'nba', 'nfl', 'nhl', 'mlb', 'cbb', 'cfb', 'epl'}   # proof_tools.KALSHI: a game here can be bid
TICKER = re.compile(r'^KX[A-Z0-9]{2,24}-[A-Z0-9]{4,30}(?:-[A-Z0-9.]{1,40}){0,3}$')
_MENU = {}                  # topic → (at, rows): the leg menu, read at most once a minute per game
MENU_TTL = 60


def _ts(iso):
    try:
        return float(calendar.timegm(time.strptime(str(iso)[:16], '%Y-%m-%dT%H:%M'))) if iso else 0.0
    except (TypeError, ValueError):
        return 0.0


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── one filing as the dashboard shows it ─────────────────────────────────────────────────────────────────────────────────────────────
def bids_of(f):
    """Every ticket of a filing that really reached Kalshi, as the game room shows it (cost = filled × price, no fees). Pure."""
    out = []
    for k in _kb.tickets_of(f):
        if k.get('orderId'):
            v = _kb.room_view(k)
            out.append({x: v.get(x) for x in ('title', 'side', 'kind', 'count', 'filled', 'price', 'cost', 'now', 'pnl', 'status', 'outcome')}
                       | {'at': k.get('settledAt') or k.get('confirmedAt') or k.get('at')})
    return out


def result_of(f, bids=None):
    """won / lost / live (a real bid not settled) / waiting (a ticket waiting for his tap) / refused / test / nobid / research. Pure."""
    bids = bids_of(f) if bids is None else bids
    if bids:
        if any(b.get('outcome') not in ('won', 'lost') for b in bids):
            return 'live'
        return 'won' if sum(float(b.get('pnl') or 0) for b in bids) > 0 else 'lost'
    k = f.get('kalshi') or {}
    if f.get('test') or f.get('testRun') or k.get('test'):
        return 'test'
    if k.get('status') == 'waiting':
        return 'waiting'
    if k.get('status') in ('failed', 'refused', 'unknown'):
        return 'refused'
    return 'research' if f.get('status') != 'closed' else 'nobid'


def judge_of(f):
    """The judges' verdict on a filing: score 0..100, pass/fail, who judged, or why nobody could. Pure."""
    r = f.get('review') or {}
    if not r:
        return {'state': 'waiting', 'why': 'not judged yet'}
    by = sorted((r.get('by') or {}).keys())
    if r.get('score') is None:
        return {'state': 'none', 'why': str(r.get('why') or 'no judge could take it')[:120], 'recused': r.get('recused') or [], 'missing': r.get('missing') or []}
    return {'state': 'scored', 'score': int(r.get('score') or 0), 'verdict': r.get('verdict'), 'by': by, 'agree': r.get('agree')}


def mode_of(f):
    t = f.get('topic') or ''
    return 'slip' if f.get('userSlip') else 'parlay' if _kb.mode_of(t) == 'parlay' or (f.get('kalshi') or {}).get('kind') == 'parlay' else 'team' if t else 'board'


def game_of(f):
    g = next((g for g in f.get('games') or [] if isinstance(g, dict)), None)
    if not g:
        return None
    return {'id': g.get('id'), 'sport': g.get('sport'), 'state': g.get('state'), 'status': g.get('status'), 'at': g.get('at'),
            'teams': [{'short': t.get('short') or t.get('name'), 'abbr': t.get('abbr'), 'score': t.get('score'), 'logo': t.get('logo')} for t in g.get('teams') or []]}


def filing_row(f):
    bids = bids_of(f); k = f.get('kalshi') or {}
    return {'id': f.get('id'), 'n': f.get('n'), 'topic': f.get('topic') or f.get('q') or 'Free chips', 'at': f.get('at'), 'test': bool(f.get('test') or f.get('testRun')),
            'mode': mode_of(f), 'result': result_of(f, bids), 'bids': bids,
            'cost': round(sum(float(b.get('cost') or 0) for b in bids), 2) if bids else 0,
            'pnl': round(sum(float(b.get('pnl') or 0) for b in bids if b.get('pnl') is not None), 2) if bids else None,
            'judge': judge_of(f), 'game': game_of(f), 'ticket': {'status': k.get('status'), 'say': (k.get('end') or {}).get('say')} if k else None,
            'slip': (f.get('userSlip') or {}).get('say') if f.get('userSlip') else None, 'spent': round(float(f.get('cost') or 0), 4)}


def totals(rows):
    """The dashboard's numbers. P&L counts settled real bids only (pool basis: payout − money that reached Kalshi, no fees); open bids are
    their own number, never mixed in. Pure."""
    settled = [b for r in rows for b in r['bids'] if b.get('outcome') in ('won', 'lost')]
    open_ = [b for r in rows for b in r['bids'] if b.get('outcome') not in ('won', 'lost')]
    scored = [r['judge']['score'] for r in rows if r['judge'].get('state') == 'scored']
    return {'filings': len(rows), 'real': sum(1 for r in rows if r['bids']), 'won': sum(1 for b in settled if b['outcome'] == 'won'),
            'lost': sum(1 for b in settled if b['outcome'] == 'lost'), 'live': len(open_),
            'cost': round(sum(float(b.get('cost') or 0) for b in settled), 2), 'pnl': round(sum(float(b.get('pnl') or 0) for b in settled), 2),
            'atRisk': round(sum(float(b.get('cost') or 0) for b in open_), 2),
            'judged': len(scored), 'avg': round(sum(scored) / len(scored)) if scored else None,
            'passed': sum(1 for r in rows if r['judge'].get('verdict') == 'pass'), 'tests': sum(1 for r in rows if r['test']),
            'waiting': sum(1 for r in rows if r['result'] == 'waiting'), 'spent': round(sum(r['spent'] for r in rows), 4)}


def curve(rows):
    """Cumulative settled P&L, oldest first: one point per settled real bid. Pure."""
    pts = sorted(((float(b.get('at') or r.get('at') or 0), float(b.get('pnl') or 0), r.get('n')) for r in rows for b in r['bids'] if b.get('outcome') in ('won', 'lost')))
    out, run = [], 0.0
    for at, p, n in pts:
        run += p; out.append({'at': round(at), 'pnl': round(run, 2), 'n': n, 'step': round(p, 2)})
    return out


# ── fresh stash odds ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def odds(refs, now=None):
    """COMP's stash reads for games not started yet, soonest first: the line, the total and each team's win chance on Kalshi and Polymarket,
    with how old the read is. Pure."""
    now = float(now or time.time()); out = []
    for r in (refs or {}).values():
        st = _ts(r.get('start'))
        if r.get('settled') or not st or st <= now or st - now > SOON_S:
            continue
        ch = r.get('chance') or {}; names = r.get('names') or []; abbr = r.get('abbr') or {}; shorts = str(r.get('label') or '').split(' at ')
        teams = [{'key': t, 'name': names[i] if i < len(names) else t, 'short': shorts[i] if len(shorts) == 2 else _short(names[i] if i < len(names) else t), 'abbr': abbr.get(t), 'kalshi': _num((ch.get(t) or {}).get('kalshi')), 'poly': _num((ch.get(t) or {}).get('chance'))} for i, t in enumerate(r.get('teams') or [])]
        favs = list((r.get('fav') or {}).values()); age = max(0, round(now - float(r.get('at') or 0)))
        out.append({'id': r.get('id'), 'sport': r.get('sport'), 'label': r.get('label'), 'start': r.get('start'), 'line': r.get('line'), 'total': r.get('total'),
                    'teams': teams, 'agree': len(favs) >= 2 and len(set(favs)) == 1, 'sources': len(favs), 'age': age, 'stale': age > STALE_S})
    return sorted(out, key=lambda x: _ts(x['start']))[:ODDS_MAX]


# ── what to file next ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _short(name, abbr=None):
    words = str(name or '').split()
    return (words[-1] if len(words) > 1 and words[-1].lower() not in ('fc', 'sc') else str(name or abbr or '')).strip()


def topic_for(teams, mode, legs=3):
    """'Kings vs Maple Leafs team to win' / '… parlay slip 3 legs': the exact words the PoB door files (kalshi_bid.mode_of reads the mode,
    pob.legs_of the legs). Pure."""
    base = ' vs '.join(teams)
    return f'{base} team to win' if mode == 'team' else f'{base} parlay slip {max(_kb.SLIP_MIN, min(_kb.SLIP_MAX, int(legs or 3)))} legs'


def _filed_on(rows_raw, teams):
    key = _pob.game_key(' vs '.join(teams))
    return [f for f in rows_raw or [] if key and _pob.game_key(f.get('topic') or '') == key]


def suggest(odds_rows, board_games, folders, now=None, busy=False):
    """Tonight's markets → up to NEXT_MAX filings worth making, best first, each with the exact words one tap files. A game Kalshi cannot bid
    on, one about to start, one already bid team-to-win AND as a slip, or one with a filing waiting on his tap is left out. The reason is
    the market's own numbers (a close game, the two markets disagreeing), said so. Pure."""
    now = float(now or time.time()); seen = set(); cand = []
    src = [{'id': o['id'], 'sport': o['sport'], 'start': o['start'], 'names': [t['short'] for t in o['teams']],
            'kalshi': [t['kalshi'] for t in o['teams']], 'poly': [t['poly'] for t in o['teams']], 'from': 'stash', 'age': o['age']} for o in odds_rows or []]
    src += [{'id': str(g.get('id')), 'sport': g.get('sport'), 'start': g.get('at'), 'names': [t.get('short') or _short(t.get('name')) for t in g.get('teams') or []],
             'kalshi': [t.get('kalshi') for t in g.get('teams') or []], 'poly': [t.get('chance') for t in g.get('teams') or []], 'from': 'board'}
            for g in board_games or [] if g.get('state') == 'pre']
    for g in src:
        st = _ts(g['start'])
        if str(g['id']) in seen or g.get('sport') not in KALSHI_SPORTS or len(g['names']) != 2 or not st or st - now < LEAD_S or st - now > SOON_S:
            continue
        k = [_num(x) for x in g['kalshi']]
        if None in k:
            continue   # no Kalshi price: nothing it could bid
        seen.add(str(g['id']))
        teams = [str(n) for n in g['names']]
        if not _kb.series_for(topic_for(teams, 'team')):
            continue   # its words name no Kalshi series (a college or soccer side): a filing could research it but never bid
        on = _filed_on(folders, teams)
        if any((f.get('kalshi') or {}).get('status') == 'waiting' and not f.get('test') for f in on):
            continue   # a ticket already waits for his tap on this game
        team_bid = any(not (f.get('kalshi') or {}).get('legs') and (f.get('kalshi') or {}).get('orderId') for f in on)
        slip_bid = any((f.get('kalshi') or {}).get('legs') and (f.get('kalshi') or {}).get('orderId') for f in on)
        p = [_num(x) for x in g['poly']]
        gap = abs(k[0] - p[0]) if p[0] is not None else 0.0
        close = 1 - abs(k[0] - k[1])
        fav = 0 if k[0] >= k[1] else 1
        mins = round((st - now) / 60)
        modes = [m for m in ('team', 'parlay') if not ((m == 'team' and team_bid) or (m == 'parlay' and (slip_bid or g['sport'] not in PROP_SPORTS)))]
        if not modes:
            continue
        why = (f"Kalshi and Polymarket differ by {round(gap * 100)} pts on {teams[0]}" if gap >= 0.03 else
               f"A close game: Kalshi {round(k[0] * 100)}–{round(k[1] * 100)}" if close >= 0.8 else
               f"Kalshi favours {teams[fav]} at {round(k[fav] * 100)}%")
        if team_bid:
            why = 'Its team to win is already bid: the play left is a slip of players, spreads and totals'
        cand.append({'key': str(g['id']), 'game': str(g['id']), 'sport': g['sport'], 'start': g['start'], 'mins': mins,
                     'files': [{'mode': m, 'topic': topic_for(teams, m)} for m in modes], 'teams': teams, 'kalshi': k, 'poly': p, 'why': why,
                     'from': g['from'], 'filed': len(on), 'score': round(gap * 3 + close + (0.4 if team_bid else 0) - mins / 3000, 4)})
    cand.sort(key=lambda c: -c['score'])
    return [{**c, 'busy': busy} for c in cand[:NEXT_MAX]]


def live_games(board_games, folders):
    """Games in progress right now (live first), each flagged when the agent filed on it. Pure."""
    keys = {_pob.game_key(f.get('topic') or '') for f in folders or []}
    ids = {str(g.get('id')) for f in folders or [] for g in f.get('games') or [] if isinstance(g, dict)}
    out = []
    for g in board_games or []:
        if g.get('state') != 'in':
            continue
        teams = [t.get('short') or t.get('name') for t in g.get('teams') or []]
        mine = str(g.get('id')) in ids or _pob.game_key(' vs '.join(str(t) for t in teams)) in keys
        out.append({'id': str(g.get('id')), 'sport': g.get('sport'), 'status': g.get('status'), 'teams': [{'short': t.get('short') or t.get('name'), 'score': t.get('score'), 'logo': t.get('logo')} for t in g.get('teams') or []],
                    'label': ' vs '.join(str(t) for t in teams), 'mine': mine})
    return sorted(out, key=lambda x: not x['mine'])[:LIVE_MAX]


def build(folders, refs, board_games, now=None, busy=False):
    """The whole dashboard read. Pure."""
    now = float(now or time.time())
    rows = [filing_row(f) for f in sorted(folders or [], key=lambda f: -float(f.get('at') or 0)) if isinstance(f, dict)]
    od = odds(refs, now)
    return {'totals': totals(rows), 'curve': curve(rows), 'rows': rows[:ROWS_MAX], 'odds': od,
            'oddsAt': max([float(r.get('at') or 0) for r in (refs or {}).values()] or [0]) or None,
            'next': suggest(od, board_games, folders, now, busy), 'live': live_games(board_games, folders),
            'upcoming': sum(1 for g in board_games or [] if g.get('state') == 'pre'), 'at': round(now)}


# ── the user's own slip ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def event_of(ticker):
    """The game code inside a Kalshi ticker (KXNHLGOAL-26NOV19LATOR-TORAMATTHEWS34-1 → 26NOV19LATOR): every market on one game shares it."""
    p = str(ticker or '').upper().split('-')
    return p[1] if len(p) > 1 else ''


def slip_clean(legs):
    """His slip as he built it → (legs, '') or ([], why). 2..4 legs, real Kalshi ticker shapes, yes/no, one side per market, no leg that
    another already guarantees (Kalshi refuses those). Pure."""
    out, seen = [], set()
    for g in legs or []:
        if not isinstance(g, dict):
            return [], 'A leg was not a leg.'
        t = str(g.get('ticker') or '').strip().upper(); s = str(g.get('side') or '').strip().lower()
        if not TICKER.match(t) or s not in ('yes', 'no'):
            return [], 'Every leg needs a Kalshi market from the list and a side (over/yes or under/no).'
        if t in seen:
            return [], 'A market is on the slip twice.'
        seen.add(t); out.append({'ticker': t, 'side': s, 'title': str(g.get('title') or t)[:60]})
    if not _kb.SLIP_MIN <= len(out) <= _kb.SLIP_MAX:
        return [], f'A slip is {_kb.SLIP_MIN} to {_kb.SLIP_MAX} legs (Kalshi takes up to {_kb.SLIP_MAX}).'
    if len({event_of(g['ticker']) for g in out}) > 1:   # 🛡 review: the minds read ONE game, so every leg is on that game
        return [], 'Every leg must be on the one game this PoB reads.'
    for i, a in enumerate(out):
        for b in out[i + 1:]:
            if a['side'] == b['side'] == 'yes' and _kb.implied(a['ticker'], b['ticker']):
                return [], f"{a['title']} and {b['title']} repeat each other: Kalshi refuses that slip."
    wins = {}
    for g in out:   # one winner per game: both teams to win can never both hit
        if g['ticker'].split('-')[0] in _kb.PROP_SERIES:
            wins.setdefault(g['ticker'].split('-')[1], []).append(g)
    if any(len(v) > 1 for v in wins.values()):
        return [], 'Two team-to-win legs on one game fight each other.'
    return out, ''


def slip_note(legs):
    """What both minds are told: the owner built this slip himself. They check it; they never add, swap or flip a leg. Pure."""
    return ('\nTHE OWNER BUILT THIS SLIP HIMSELF (' + str(len(legs)) + ' legs, every leg must hit). Check EVERY leg against what you read. '
            'Back a leg only when the facts support it: give it as one of your picks with "kalshi": {"ticker", "side"} exactly as below, your honest '
            'confidence, and for a player leg its own "number" and "evidence". A leg you cannot back: leave it out and say why in "pass". Never add, '
            'swap or flip a leg; a slip both of you do not back whole is never sent:\n'
            + '\n'.join(f"- {g['ticker']} · {g['side'].upper()} · {g['title']}" for g in legs))


def slip_menu(menu, legs, extra=()):
    """The leg menu cut to his legs: (rows, missing tickers). `extra` = markets read one by one for a leg the menu no longer shows
    (it lists each player's line nearest a coin flip, which moves). A leg Kalshi does not list open and priced stays missing. Pure."""
    want = {g['ticker'] for g in legs}
    rows = [m for m in menu or [] if m.get('ticker') in want]
    have = {m['ticker'] for m in rows}
    for m in extra or []:
        if isinstance(m, dict) and m.get('ticker') in want - have and m.get('status') in ('active', 'open') and _kb.price_of(m, 'yes'):
            rows.append(m); have.add(m['ticker'])
    return rows, sorted(want - have)


def slip_verdict(legs, calls, menu, min_conf, missing=()):
    """→ {legs: [{ticker, side, title, minds: [{name, backs, conf, side}], ok}], whole, say}. A leg is ok when every mind backed it on his
    side at or over his minimum (a player leg with its evidence and number: kalshi_bid._legs drops one without). Whole = every leg ok and
    none missing from Kalshi. Pure."""
    by = {m['ticker']: m for m in menu or []}
    mind = [(c.get('name') or f"Mind {'AB'[i % 2]}", _kb._legs(c, by)) for i, c in enumerate((calls or [])[:2])]
    out = []
    for g in legs:
        ms = []
        for name, got in mind:
            h = got.get(g['ticker'])
            ms.append({'name': str(name).split('/')[-1], 'backs': bool(h and h[0] == g['side'] and h[1] >= min_conf), 'conf': h[1] if h else None, 'side': h[0] if h else None})
        ok = g['ticker'] not in missing and len(ms) >= 1 and all(m['backs'] for m in ms)
        out.append({**g, 'minds': ms, 'ok': ok, **({'gone': True} if g['ticker'] in missing else {})})
    whole = bool(out) and all(x['ok'] for x in out) and len(mind) == 2
    bad = [x for x in out if not x['ok']]
    say = ('Both minds back every leg of your slip: it goes through the same caps and guards as any slip.' if whole else
           'Your slip is not sent: ' + '; '.join(
               f"{x['title']}: " + ('Kalshi does not list it open now' if x.get('gone') else
                                     ', '.join(f"{m['name']} {'backs it' if m['backs'] else 'flipped it' if m['side'] and m['side'] != x['side'] else 'under your minimum' if m['conf'] is not None else 'did not back it'}" for m in x['minds']) or 'no mind answered')
               for x in bad)[:400] + '.' if bad else 'Your slip is not sent: it needs both minds.')
    return {'legs': out, 'whole': whole, 'say': say}


def slip_matches(ticket_legs, legs):
    """The ticket the engine built is exactly his slip: the same markets on the same sides, nothing added or dropped. Pure."""
    a = {(str(g.get('ticker')), str(g.get('side'))) for g in ticket_legs or []}
    return bool(a) and a == {(g['ticker'], g['side']) for g in legs}


# ── the leg menu he builds from (public Kalshi reads) ───────────────────────────────────────────────────────────────────────────────────
def menu_row(m):
    st = _kb.stat_of(m.get('ticker'))
    return {'ticker': m.get('ticker'), 'kind': 'player' if st else 'line' if any(x in str(m.get('ticker')) for x in ('SPREAD', 'TOTAL')) else 'team',
            'stat': st or None, 'line': _kb.prop_line(m) if st else None, 'yes': _kb.price_of(m, 'yes'), 'no': _kb.price_of(m, 'no'),
            'over': _kb.leg_title(m, 'yes'), 'under': _kb.leg_title(m, 'no')}


async def menu(http, topic, now=None):
    """The legs Kalshi lists for this game, the same menu the minds are shown: both teams to win, each player's line nearest a coin flip,
    a few spreads and totals. Cached a minute per topic."""
    now = float(now or time.time()); key = _pob.game_key(topic)
    hit = _MENU.get(key)
    if hit and now - hit[0] < MENU_TTL:
        return hit[1]
    games = await _kb.markets_for(http, topic)
    rows = [menu_row(m) for m in await _kb.legs_menu(http, games)] if games else []
    _MENU[key] = (now, rows)
    if len(_MENU) > 200:
        _MENU.pop(next(iter(_MENU)))
    return rows
