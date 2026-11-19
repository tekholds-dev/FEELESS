"""📡 COMP STAYS AHEAD (Slice 11 · owner: "COMP always web scraping and staying ahead of the game, having PoBs filed already to compare a PoB
filed by another agent").

Every EVERY_S, COMP reads what is coming up, with PLAIN page reads only (no model is ever called here: RULINGS 2026-11-14 stopped self-started
model usage; a page read is not model usage and costs $0):
  · tonight's and tomorrow's games in each league (ESPN's board for those dates): each game's ESPN data (records, injuries, leaders, line,
    total) and both markets' win chance (Kalshi, Polymarket) → into the STASH (stash_brain.keep, sealed by league) and the ATLAS (atoms).
  · each league's public odds pages that list every game (covers, oddsshark, cbssports, actionnetwork), kept 3 ways (scrape, static, picture).
  · the hottest Solana coins on our own board (DexScreener data via our feed): price, liquidity, volume, move, launch → stash + atlas.
A page still fresh in the stash, or a game whose atoms are all fresh, is not read again (delta reading).

COMP's REFERENCE per game ("PoBs filed already"): what each source favours (ESPN's line, Kalshi, Polymarket), made with no model. A new PoB is
compared against it and every other agent's PoB on that game (pob_peers). When the game is final, each source's favourite was right or
wrong, and the atlas moves that source's trust (settle_refs).

Nothing here prints, logs or returns a page's words: the pass log is counts only."""
import asyncio
import json
import re
import time
from pathlib import Path

import atlas as _atlas
import stash_brain as _sb
import stash_sort as _sort

EVERY_S = 20 * 60          # a pass every 20 min
FIRST_S = 120              # after a restart, the first pass waits for the service to settle
WITHIN_S = 36 * 3600       # "coming up" = starts in the next 36 h
LEAGUES = ('nba', 'nfl', 'nhl', 'cbb')
MAX_GAMES = 18             # per pass, soonest first
MAX_COINS = 6
MAX_SHOTS = 4              # pictures per pass (the free local browser, one at a time)
LOG_MAX = 400
REF_KEEP_S = 4 * 86400
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
ODDS_PAGES = {
    'nba': ('https://www.covers.com/sport/basketball/nba/odds', 'https://www.oddsshark.com/nba/odds', 'https://www.cbssports.com/nba/odds/', 'https://www.actionnetwork.com/nba/odds'),
    'nfl': ('https://www.covers.com/sport/football/nfl/odds', 'https://www.oddsshark.com/nfl/odds', 'https://www.cbssports.com/nfl/odds/', 'https://www.actionnetwork.com/nfl/odds'),
    'nhl': ('https://www.covers.com/sport/hockey/nhl/odds', 'https://www.oddsshark.com/nhl/odds', 'https://www.cbssports.com/nhl/odds/', 'https://www.actionnetwork.com/nhl/odds'),
    'cbb': ('https://www.covers.com/sport/basketball/ncaab/odds', 'https://www.oddsshark.com/ncaab/odds', 'https://www.cbssports.com/college-basketball/odds/', 'https://www.actionnetwork.com/ncaab/odds'),
}
GAME_WHATS = ('line', 'total', 'schedule')
CAT_OF = {'nba': 'nba', 'nfl': 'nfl', 'nhl': 'nhl', 'cbb': 'ncaa'}   # the stash seal (stash_sort's league names)
STATE = {'running': False, 'last': None}


def dir_of(data_dir):
    return Path(data_dir) / 'comp_ahead'


def _iso_ts(iso):
    m = re.match(r'(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)', str(iso or ''))
    if not m:
        return 0.0
    import calendar
    return float(calendar.timegm(tuple(int(x) for x in m.groups()) + (0, 0, 0, 0)))


def nick_of(name):
    """'LA Clippers' → 'clippers' (stash_sort's team word, so a brain's ask and COMP's atoms name the same team). Pure."""
    t = _sort.teams_on(name)
    ns = sorted(n for v in t.values() for n in v)
    return ns[0] if ns else re.sub(r'[^a-z0-9 ]', '', str(name or '').lower()).strip()


# ── what is coming up ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def board(http, sport, now):
    """ESPN's board for today and tomorrow in this league, with both markets' win chance merged in. Games not started, inside WITHIN_S."""
    import proof_tools as _pt
    path = _pt.SPORTS[sport][1]; days = sorted({time.strftime('%Y%m%d', time.localtime(now + d * 86400)) for d in (0, 1)})
    reads = [_pt._get(http, f'https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard', params={'dates': d}) for d in days]
    reads += [_pt._get(http, 'https://gamma-api.polymarket.com/events', params={'active': 'true', 'closed': 'false', 'limit': 60, 'tag_slug': _pt.POLY_TAG.get(sport, sport), 'order': 'volume24hr', 'ascending': 'false'}),
              _pt._get(http, 'https://api.elections.kalshi.com/trade-api/v2/events', params={'series_ticker': _pt.KALSHI.get(sport, 'NONE'), 'status': 'open', 'limit': 60, 'with_nested_markets': 'true'})]
    got = await asyncio.gather(*reads)
    games, seen = [], set()
    for data in got[:len(days)]:
        for g in _pt.parse_espn(data):
            if g.get('id') in seen:
                continue
            seen.add(g.get('id')); g['sport'] = sport; games.append(g)
    games = _pt.merge_kalshi(_pt.merge_odds(games, _pt.parse_poly(got[-2])), got[-1])
    return [g for g in games if g.get('state') == 'pre' and 0 < _iso_ts(g.get('at')) - now <= WITHIN_S]


async def upcoming(http, now, leagues=LEAGUES):
    rows = []
    for s in leagues:
        try:
            rows += await board(http, s, now)
        except Exception as e:   # noqa: BLE001 — one league down never stops the others
            print(f'[comp ahead] board {s}: {type(e).__name__}')
    return sorted(rows, key=lambda g: _iso_ts(g.get('at')))


def label_of(g):
    return ' at '.join(str((t or {}).get('short') or '') for t in (g or {}).get('teams') or [])


# ── atoms + COMP's reference ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def game_atoms(g, d=None):
    """One game's ESPN data + both markets → atoms. Pure."""
    sport = g.get('sport') or ''; cat = CAT_OF.get(sport, sport); subj = f"game:{sport}:{g.get('id')}"; lab = label_of(g); rows = []
    add = lambda s, w, v, host, kind, label=lab: rows.append({'subject': s, 'what': w, 'value': v, 'host': host, 'kind': kind, 'cat': cat, 'label': label}) if v not in (None, '', []) else None
    d = d or {}
    add(subj, 'line', d.get('line') or g.get('line'), 'espn.com', 'line')
    add(subj, 'total', d.get('total') or g.get('total'), 'espn.com', 'total')
    add(subj, 'schedule', g.get('at'), 'espn.com', 'schedule')
    for t in g.get('teams') or []:
        n = nick_of(t.get('name'))
        if t.get('kalshi') is not None:
            add(subj, f'win chance {n}', round(float(t['kalshi']), 3), 'kalshi.com', 'winchance')
        if t.get('chance') is not None:
            add(subj, f'win chance {n}', round(float(t['chance']), 3), 'polymarket.com', 'winchance')
    for t in d.get('teams') or []:
        n = nick_of(t.get('name')); ts = f'team:{n}'; tl = str(t.get('name') or n)
        add(ts, 'record', t.get('record'), 'espn.com', 'record', tl)
        add(ts, f"{t.get('side') or 'side'} record", t.get('sideRecord'), 'espn.com', 'record', tl)
        add(ts, 'form', ''.join(t.get('form') or []), 'espn.com', 'form', tl)
        for x in (t.get('injuries') or [])[:8]:
            if isinstance(x, dict) and x.get('name'):
                add(f"player:{str(x['name']).lower()}", 'status', x.get('status'), 'espn.com', 'injury', f"{x['name']} ({tl})")
        for x in (t.get('leaders') or [])[:4]:
            if isinstance(x, dict) and x.get('name'):
                add(f"player:{str(x['name']).lower()}", f"season {str(x.get('stat') or 'stat').lower()}", x.get('value'), 'espn.com', 'leader', f"{x['name']} ({tl})")
    return rows


def _line_fav(line, teams):
    """'SA -16.5' → the favoured team's word. Pure."""
    m = re.match(r'\s*([A-Za-z]{2,5})\s*-\d', str(line or ''))
    if not m:
        return None
    ab = m.group(1).upper()
    t = next((t for t in teams or [] if str(t.get('abbr') or '').upper() == ab), None)
    return nick_of(t.get('name')) if t else None


def reference(g, d=None, now=None):
    """🧭 COMP's reference reading of one game, made with no model: what each source favours, the line and total. Pure."""
    teams = g.get('teams') or []; d = d or {}
    fav = {}
    lf = _line_fav(d.get('line') or g.get('line'), teams)
    if lf:
        fav['espn.com'] = lf
    for host, key in (('kalshi.com', 'kalshi'), ('polymarket.com', 'chance')):
        ps = [(float(t[key]), nick_of(t.get('name'))) for t in teams if isinstance(t.get(key), (int, float))]
        if len(ps) == 2 and ps[0][0] != ps[1][0]:
            fav[host] = max(ps)[1]
    return {'id': str(g.get('id')), 'sport': g.get('sport'), 'label': label_of(g), 'start': g.get('at'), 'teams': [nick_of(t.get('name')) for t in teams],
            'names': [t.get('name') for t in teams], 'abbr': {nick_of(t.get('name')): t.get('abbr') for t in teams if t.get('abbr')}, 'fav': fav, 'line': d.get('line') or g.get('line'), 'total': d.get('total') or g.get('total'),
            'chance': {nick_of(t.get('name')): {k: t.get(k) for k in ('kalshi', 'chance') if t.get(k) is not None} for t in teams}, 'at': round(float(now or time.time()))}


def load_refs(data_dir):
    try:
        return json.loads((dir_of(data_dir) / 'refs.json').read_text())
    except (OSError, ValueError):
        return {}


def save_refs(data_dir, refs, now=None):
    now = float(now or time.time())
    keep = {k: v for k, v in refs.items() if now - float(v.get('at') or 0) < REF_KEEP_S}
    p = dir_of(data_dir) / 'refs.json'; p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(keep, separators=(',', ':'))); tmp.replace(p)
    return keep


def game_text(g, d):
    """The words kept in the stash for one game's ESPN data read (what a brain is handed when it asks about this game). Pure."""
    import kalshi_bid as _kb
    lines = [f"{label_of(g)} · {g.get('status') or g.get('at')} · {str(g.get('sport') or '').upper()}"]
    lines.append(_kb.game_facts(d, g) if d else '')
    ch = [f"{t.get('short')} Kalshi {round(t['kalshi'] * 100)}%" for t in g.get('teams') or [] if t.get('kalshi') is not None]
    ch += [f"{t.get('short')} Polymarket {round(t['chance'] * 100)}%" for t in g.get('teams') or [] if t.get('chance') is not None]
    if ch:
        lines.append('Market win chance: ' + ', '.join(ch) + '.')
    return '\n'.join(x for x in lines if x)


# ── one pass ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def _keep_page(http, root, tok, url, why, counts, shots, now=None):
    """A public odds page read plainly → stash, kept 3 ways (its picture by the free local browser, a few per pass)."""
    import cat_browser as _cb
    if _sb.fresh_copy(root, url, now):
        counts['fresh'] += 1; return
    p = _cb.ReaderPage(http); t0 = time.perf_counter()
    try:
        await p.goto(url)
    except Exception as e:   # noqa: BLE001 — a site down is skipped
        counts['failed'] += 1; print(f'[comp ahead] read skipped: {type(e).__name__}'); return
    load = time.perf_counter() - t0; html = p._html or ''; title, text = _cb.page_text(html, _sb.TEXT_MAX)
    counts['read'] += 1
    if len(text) < 120 or _cb.needs_human(str(p.url or url), text[:3000]):
        counts['skipped'] += 1; return
    got = _sb.keep(root, tok, str(p.url or url), title, text, html, None, load, 'reader', now=now, why=why)
    counts['kept'] += 1
    if shots[0] < MAX_SHOTS:
        shots[0] += 1
        try:
            jpg = await asyncio.wait_for(_sb._free_shot(str(p.url or url)), 40)
            if jpg and _sb.add_shot(root, tok, got['pid'], jpg):
                counts['shots'] += 1
        except Exception as e:   # noqa: BLE001
            print(f'[comp ahead] picture skipped: {type(e).__name__}')


async def read_game(http, root, aroot, tok, g, counts, now, force=False):
    """One game: ESPN's data read plainly → the stash (its words) + the atlas (its atoms). Skipped when its atoms are all fresh. → the detail."""
    import proof_tools as _pt
    subj = f"game:{g.get('sport')}:{g.get('id')}"
    if not force and not _atlas.due(aroot, subj, GAME_WHATS, now):
        counts['fresh'] += 1
        return None
    t0 = time.perf_counter()
    d = await _pt.game_detail(http, g.get('sport'), str(g.get('id')), [t.get('name') for t in g.get('teams') or []])
    load = time.perf_counter() - t0; counts['read'] += 1
    text = game_text(g, d or {})
    if len(text) > 60:
        path = _pt.SPORTS[g['sport']][1]
        _sb.keep(root, tok, f"https://site.api.espn.com/apis/site/v2/sports/{path}/summary?event={g.get('id')}", f'{label_of(g)} · ESPN game data', text,
                 json.dumps(d or {}, default=str)[:_sb.HTML_MAX], None, load, 'reader', now=now, why='ahead')
        counts['kept'] += 1
    counts['newAtoms'] += _atlas.put(aroot, tok, game_atoms(g, d), now)
    return d or {}


def coin_atoms(p):
    """One pair from our board (DexScreener's data) → atoms. Pure."""
    sym = str(((p.get('baseToken') or {}).get('symbol')) or '').lower()
    if not sym:
        return []
    subj = f'coin:{sym}'; lab = f"${(p.get('baseToken') or {}).get('symbol')}"; rows = []
    for what, val, kind in (('price usd', p.get('priceUsd'), 'price'), ('liquidity usd', (p.get('liquidity') or {}).get('usd'), 'liquidity'),
                            ('volume 24h', (p.get('volume') or {}).get('h24'), 'volume'), ('move 1h %', (p.get('priceChange') or {}).get('h1'), 'change'),
                            ('pair created', p.get('pairCreatedAt'), 'launch'), ('mint', (p.get('baseToken') or {}).get('address'), 'launch')):
        if val not in (None, ''):
            rows.append({'subject': subj, 'what': what, 'value': val, 'host': 'dexscreener.com', 'kind': kind, 'cat': 'coins', 'label': lab})
    return rows


def coin_text(p):
    b = p.get('baseToken') or {}
    return (f"${b.get('symbol')} ({b.get('name')}) on Solana · {p.get('dexId')} · DexScreener data via the FEELESS board. Price ${p.get('priceUsd')}, "
            f"liquidity ${round(float((p.get('liquidity') or {}).get('usd') or 0))}, 24h volume ${round(float((p.get('volume') or {}).get('h24') or 0))}, "
            f"move 1h {(p.get('priceChange') or {}).get('h1')}%, 24h {(p.get('priceChange') or {}).get('h24')}%, market cap ${p.get('marketCap')}. "
            f"Buys/sells 1h {((p.get('txns') or {}).get('h1') or {}).get('buys')}/{((p.get('txns') or {}).get('h1') or {}).get('sells')}. Mint {b.get('address')}. Pair {p.get('pairAddress')}.")


async def hot_coins(http, n=MAX_COINS):
    """Our own board's hottest Solana coins (by the last hour's volume). [] when the main service does not answer."""
    import cat_tools as _ct
    try:
        r = await http.get(f'{_ct.MAIN}/api/market/feed', params={'chain': 'solana'}, timeout=15)
        ps = (r.json() or {}).get('pairs') or []
    except Exception as e:   # noqa: BLE001
        print(f'[comp ahead] coins: {type(e).__name__}'); return []
    return sorted([p for p in ps if isinstance(p, dict) and p.get('pairAddress')], key=lambda p: -float((p.get('volume') or {}).get('h1') or 0))[:n]


async def run_pass(data_dir, http=None, now=None, leagues=LEAGUES):
    """📡 One pass: read what is coming up, keep it, atomise it, file COMP's reference per game, settle the references whose game is final.
    Plain reads only, no model call. → the pass row (counts only)."""
    import httpx
    if STATE['running']:
        return {'skipped': 'a pass is already running'}
    STATE['running'] = True; t0 = time.time(); now = float(now or t0)
    root, aroot = _sb.root_of(data_dir), _atlas.root_of(data_dir)
    counts = {'games': 0, 'read': 0, 'kept': 0, 'fresh': 0, 'skipped': 0, 'failed': 0, 'shots': 0, 'newAtoms': 0, 'coins': 0, 'pages': 0, 'refs': 0, 'settled': 0}
    tok = _sb.open_run(f'comp:ahead:{int(now)}', 'comp', 'comp', now); own = http is None; shots = [0]; games = []
    try:
        if own:
            http = httpx.AsyncClient(timeout=15, headers=UA, follow_redirects=True)
        games = (await upcoming(http, now, leagues))[:MAX_GAMES]; counts['games'] = len(games)
        refs = load_refs(data_dir)
        for g in games:
            try:
                d = await read_game(http, root, aroot, tok, g, counts, now)
                if d is not None or str(g.get('id')) not in refs:
                    refs[str(g.get('id'))] = reference(g, d, now); counts['refs'] += 1
            except Exception as e:   # noqa: BLE001 — one game never stops the pass
                counts['failed'] += 1; print(f'[comp ahead] game skipped: {type(e).__name__}')
        for lg in sorted({g.get('sport') for g in games}):
            for url in ODDS_PAGES.get(lg, ()):
                counts['pages'] += 1
                await _keep_page(http, root, tok, url, 'ahead', counts, shots, now)
        for p in await hot_coins(http):
            sym = str((p.get('baseToken') or {}).get('symbol') or '').lower()
            if not _atlas.due(aroot, f'coin:{sym}', ('price usd',), now):
                counts['fresh'] += 1; continue
            _sb.keep(root, tok, f"https://dexscreener.com/solana/{str(p.get('pairAddress')).lower()}", f"${(p.get('baseToken') or {}).get('symbol')} · DexScreener", coin_text(p),
                     json.dumps(p, default=str)[:200_000], None, 0.0, 'reader', now=now, why='ahead')
            counts['kept'] += 1; counts['coins'] += 1; counts['newAtoms'] += _atlas.put(aroot, tok, coin_atoms(p), now)
        counts['settled'] = await settle_refs(http, data_dir, refs, now)
        save_refs(data_dir, refs, now)
    finally:
        _sb.close_run(tok); STATE['running'] = False
        if own and http is not None:
            await http.aclose()
    row = {'at': round(now), 'secs': round(time.time() - t0, 1), **counts, 'leagues': sorted({g.get('sport') for g in games})}
    log(data_dir, row)
    STATE['last'] = row
    return row


async def settle_refs(http, data_dir, refs, now):
    """🏁 A game COMP read is final: each source's favourite was right or wrong, and the atlas moves that source's trust (once per game)."""
    import proof_tools as _pt
    todo = [r for r in refs.values() if not r.get('settled') and r.get('fav') and _iso_ts(r.get('start')) and now - _iso_ts(r.get('start')) > 2.5 * 3600]
    n = 0
    for sport in {r.get('sport') for r in todo}:
        boards = {}
        for day in sorted({time.strftime('%Y%m%d', time.localtime(_iso_ts(r.get('start')))) for r in todo if r.get('sport') == sport}):
            data = await _pt._get(http, f'https://site.api.espn.com/apis/site/v2/sports/{_pt.SPORTS[sport][1]}/scoreboard', params={'dates': day})
            boards.update({str(g.get('id')): g for g in _pt.parse_espn(data)})
        for r in [x for x in todo if x.get('sport') == sport]:
            g = boards.get(str(r.get('id')))
            if not g or not g.get('final'):
                continue
            won = next((nick_of(t.get('name')) for t in g.get('teams') or [] if t.get('winner')), None)
            if not won:
                continue
            for host, fav in r['fav'].items():
                _atlas.settle(_atlas.root_of(data_dir), f"comp:{r['id']}", [host], sport, fav == won, now)
            r['settled'] = {'winner': won, 'at': round(now), 'right': sorted(h for h, f in r['fav'].items() if f == won), 'wrong': sorted(h for h, f in r['fav'].items() if f != won)}
            n += 1
    return n


def folder_topic(f):
    """A PoB's topic for trust: the league of its games, else the league its words name. Pure."""
    for g in f.get('games') or []:
        if isinstance(g, dict) and g.get('sport'):
            return str(g['sport'])
    lg = _sort.leagues_on(str(f.get('topic') or ''))
    return lg[0] if lg else 'sports'


def settle_folders(data_dir, cats, now=None):
    """🏁 Every PoB that settled (a real Kalshi result first, else the scoreboard or Polymarket grade) moves the trust of each source it read,
    once (`atlasAt` on the folder). → how many folders moved trust now."""
    now = float(now or time.time()); root = _atlas.root_of(data_dir); n = 0
    for c in cats or []:
        for f in (c.get('pobFolders') or [])[-80:] if isinstance(c, dict) else []:
            if not isinstance(f, dict) or f.get('atlasAt'):
                continue
            out = ((f.get('kalshi') or {}) if isinstance(f.get('kalshi'), dict) else {}).get('outcome')
            ok = out == 'won' if out in ('won', 'lost') else (f.get('graded') == 'right' if f.get('graded') in ('right', 'wrong') else None)
            if ok is None:
                continue
            hosts = list((f.get('read') or {}).get('sites') or []) + list(f.get('sites') or [])
            moved = _atlas.settle(root, f"pob:{c.get('id')}:{f.get('id')}", hosts, folder_topic(f), ok, now)
            f['atlasAt'] = round(now); f['atlasTrust'] = {'ok': ok, 'by': 'kalshi' if out in ('won', 'lost') else f.get('gradedBy') or 'graded', 'moved': moved, 'topic': folder_topic(f)}
            n += 1
    return n


def log(data_dir, row):
    p = dir_of(data_dir) / 'passes.jsonl'; p.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = p.read_text().splitlines()[-(LOG_MAX - 1):] if p.exists() else []
    except OSError:
        rows = []
    p.write_text('\n'.join(rows + [json.dumps(row, separators=(',', ':'))]) + '\n')


def passes(data_dir, n=40):
    try:
        return [json.loads(x) for x in (dir_of(data_dir) / 'passes.jsonl').read_text().splitlines()[-n:] if x.strip()]
    except (OSError, ValueError):
        return []


def panel(data_dir, now=None):
    """📡 The COMP-ahead panel: the passes (counts), what it holds fresh, the atlas counts and its trust table. Never a page or a fact."""
    now = float(now or time.time()); ps = passes(data_dir); refs = load_refs(data_dir)
    nxt = (ps[-1]['at'] + EVERY_S) if ps else None
    return {'every': EVERY_S, 'running': STATE['running'], 'last': ps[-1] if ps else None, 'next': nxt, 'passes': ps[-24:],
            'refs': {'games': len(refs), 'upcoming': sum(1 for r in refs.values() if _iso_ts(r.get('start')) > now), 'settled': sum(1 for r in refs.values() if r.get('settled'))},
            'atlas': _atlas.stats(_atlas.root_of(data_dir), now), 'models': 0}


async def loop(data_dir):
    """The schedule: a pass every EVERY_S, forever. Never takes the service down."""
    await asyncio.sleep(FIRST_S)
    while True:
        try:
            await run_pass(data_dir)
        except Exception as e:   # noqa: BLE001
            STATE['running'] = False
            print(f'[comp ahead] pass failed: {type(e).__name__}')
        await asyncio.sleep(EVERY_S)
