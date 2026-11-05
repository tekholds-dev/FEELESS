"""🧰 THE PROOF FOLDERS' DASHES (owner 2026-11-04): each folder opens on live rows from its top 5 free sources. PoB: pick a sport and a team, see the games and the parlays the market likes most.
Every number comes from a source named on screen. "Best" means the market's own odds say it is most likely: never a promise."""
import asyncio
import json
import re
import time
from urllib.parse import quote

SPORTS = {'nfl': ('NFL', 'football/nfl'), 'nba': ('NBA', 'basketball/nba'), 'mlb': ('MLB', 'baseball/mlb'), 'nhl': ('NHL', 'hockey/nhl'), 'cfb': ('College football', 'football/college-football'), 'cbb': ('College basketball', 'basketball/mens-college-basketball'), 'epl': ('Premier League', 'soccer/eng.1'), 'mls': ('MLS', 'soccer/usa.1'), 'ucl': ('Champions League', 'soccer/uefa.champions'), 'laliga': ('La Liga', 'soccer/esp.1'), 'wnba': ('WNBA', 'basketball/wnba'), 'ufc': ('UFC', 'mma/ufc')}
KALSHI = {'nfl': 'KXNFLGAME', 'nba': 'KXNBAGAME', 'mlb': 'KXMLBGAME', 'nhl': 'KXNHLGAME', 'cfb': 'KXNCAAFGAME', 'cbb': 'KXNCAAMBGAME', 'epl': 'KXEPLGAME'}
POLY_TAG = {'nfl': 'nfl', 'nba': 'nba', 'mlb': 'mlb', 'nhl': 'nhl', 'cfb': 'cfb', 'cbb': 'cbb', 'epl': 'epl'}
SOURCES = {'bids': [('ESPN', 'Games, scores, teams', True), ('Polymarket', 'Market odds on each game', True), ('Kalshi', 'US regulated markets', True), ('TheSportsDB', 'Team records', True), ('The Odds API', 'Sportsbook lines: needs your key', False)],
           'pow': [('FEELESS intake', 'New coins it already watches', True), ('DexScreener new', 'Fresh token profiles', True), ('DexScreener boosts', 'Boosted coins', True), ('RugCheck', 'Trending, safety', True), ('CoinGecko', 'Trending coins', True)],
           'pop': [('Hyperliquid', 'Funding, open interest, price', True), ('Coinbase', 'Spot price feed', True), ('Fear & Greed', 'Market mood', True), ('CoinGecko', 'Global market', True), ('DefiLlama', 'Perp volume', True)]}
TTL = 60
_cache = {}


async def _cached(key, fn):
    now = time.time(); got = _cache.get(key)
    if got and now - got[0] < TTL:
        return got[1]
    val = await fn()
    if val:
        _cache[key] = (now, val)
    return val or (got[1] if got else val)


async def _get(http, url, **kw):
    try:
        r = await http.get(url, timeout=8, **kw)
        return r.json() if r.status_code == 200 else None
    except Exception:   # noqa: BLE001 — a source that is down is shown as down
        return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def parse_espn(data):
    """ESPN's scoreboard → games. Pure."""
    out = []
    for e in (data or {}).get('events') or []:
        c = ((e.get('competitions') or [{}])[0]); st = (e.get('status') or {}).get('type') or {}
        teams = sorted(c.get('competitors') or [], key=lambda t: t.get('homeAway') != 'away')
        if len(teams) != 2:
            continue
        row = [{'name': (t.get('team') or t.get('athlete') or {}).get('displayName'), 'short': (t.get('team') or t.get('athlete') or {}).get('shortDisplayName') or (t.get('team') or t.get('athlete') or {}).get('name'), 'abbr': (t.get('team') or t.get('athlete') or {}).get('abbreviation'), 'score': t.get('score'), 'winner': t.get('winner')} for t in teams]
        odds = (c.get('odds') or [{}])[0] or {}
        out.append({'id': e.get('id'), 'at': e.get('date'), 'state': st.get('state'), 'final': bool(st.get('completed')), 'status': st.get('shortDetail') or st.get('description'), 'teams': row, 'line': odds.get('details'), 'total': odds.get('overUnder')})
    return out


def parse_poly(events):
    """Polymarket's game markets → {'Jaguars vs. Ravens': {'Jaguars': .815, 'Ravens': .185}}. Only two-sided winner markets. Pure."""
    out = {}
    for ev in events or []:
        title = str(ev.get('title') or '')
        if ' vs' not in title.lower():
            continue
        for m in ev.get('markets') or []:
            try:
                names, prices = json.loads(m.get('outcomes') or '[]'), json.loads(m.get('outcomePrices') or '[]')
            except (ValueError, TypeError):
                continue
            if m.get('groupItemTitle') in (None, '') and len(names) == 2 and names[0] not in ('Yes', 'No'):
                out[title] = {names[0]: _f(prices[0]), names[1]: _f(prices[1])}
                break
    return out


def _word(s):
    return re.sub(r'[^a-z0-9 ]', '', str(s or '').lower())


def merge_odds(games, poly):
    """Each game not yet started gets the market's chance per team, when Polymarket lists it. Pure."""
    for g in games:
        names = [_word(t.get('short')) for t in g['teams']]
        for title, sides in poly.items():
            t = _word(title)
            if all(n and n.split()[-1] in t for n in names):
                for tm in g['teams']:
                    last = _word(tm.get('short')).split()[-1]
                    hit = next((v for k, v in sides.items() if last in _word(k)), None)
                    if hit is not None:
                        tm['chance'] = round(hit, 3)
                break
    return games


def best_legs(games, team=''):
    """The sides the market likes most, one per game, games not yet played. Pure."""
    legs = []
    for g in games:
        if g.get('state') != 'pre' or (team and not any(_word(team) in _word(t.get('name')) for t in g['teams'])):
            continue
        sides = [t for t in g['teams'] if t.get('chance') and 0.01 < t['chance'] < 0.995]
        if sides:
            top = max(sides, key=lambda t: t['chance'])
            legs.append({'pick': f"{top['short']} to beat {next(t['short'] for t in g['teams'] if t is not top)}", 'team': top['name'], 'chance': top['chance'], 'game': g['id'], 'at': g.get('at')})
    return sorted(legs, key=lambda x: -x['chance'])


def parlays(legs):
    """2 and 3 leg parlays of the strongest sides, with the chance all of them land if the games are independent. Pure."""
    out = []
    for n in (2, 3):
        if len(legs) >= n:
            pick = legs[:n]; p = 1.0
            for x in pick:
                p *= x['chance']
            out.append({'legs': [x['pick'] for x in pick], 'chance': round(p, 3), 'pays': round(1 / p, 2), 'games': [x['game'] for x in pick]})
    return out


def merge_kalshi(games, data):
    """A second market's price per team, when Kalshi lists the game. Pure."""
    for ev in (data or {}).get('events') or []:
        for m in ev.get('markets') or []:
            name = _word(m.get('yes_sub_title')); price = _f(m.get('last_price_dollars') or m.get('yes_ask_dollars'))
            if not name or not price:
                continue
            for g in games:
                if g.get('state') == 'pre' and all(any(w in _word(ev.get('title')) for w in _word(t.get('name')).split()) for t in g['teams']):
                    for t in g['teams']:
                        if name in _word(t.get('name')):
                            t['kalshi'] = round(price, 3)
    return games


def team_list(games):
    return sorted({t['name'] for g in games for t in g['teams'] if t.get('name')})


def games_for(text, games):
    """The games a proof's words are about: a team's name in the text. Saved on the folder so its result can be read later. Pure."""
    t = _word(text); out = []
    for g in games:
        for tm in g['teams']:
            short = _word(tm.get('short')).split()
            if (short and re.search(rf'\b{re.escape(short[-1])}\b', t)) or (_word(tm.get('name')) and _word(tm.get('name')) in t):
                out.append({'id': g['id'], 'sport': g.get('sport'), 'side': tm.get('name'), 'short': tm.get('short'), 'label': ' at '.join(x.get('short') or '' for x in g['teams']), 'final': bool(g.get('final'))})
                break
    return out[:6]


def grade_games(rows, games):
    """Update a folder's saved games from the scoreboard. → (rows, 'right'|'wrong'|None). The grade appears only when every game is final; one lost side loses it, like a parlay. Pure."""
    by = {g['id']: g for g in games}; out = []
    for r in rows or []:
        g = by.get(r.get('id'))
        if not g:
            out.append(r); continue
        tm = next((t for t in g['teams'] if t.get('name') == r.get('side')), None)
        out.append({**r, 'final': bool(g.get('final')), 'status': g.get('status'), 'score': ' - '.join(str(t.get('score') or 0) for t in g['teams']), 'won': bool(tm and tm.get('winner')) if g.get('final') else None})
    if not out or not all(r.get('final') for r in out):
        return out, None
    return out, 'right' if all(r.get('won') for r in out) else 'wrong'


async def sport_board(http, sport):
    if sport not in SPORTS:
        sport = 'nfl'

    async def go():
        espn, poly, kal = await asyncio.gather(_get(http, f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[sport][1]}/scoreboard'), _get(http, 'https://gamma-api.polymarket.com/events', params={'active': 'true', 'closed': 'false', 'limit': 60, 'tag_slug': POLY_TAG.get(sport, sport), 'order': 'volume24hr', 'ascending': 'false'}),
                                               _get(http, 'https://api.elections.kalshi.com/trade-api/v2/events', params={'series_ticker': KALSHI.get(sport, 'NONE'), 'status': 'open', 'limit': 60, 'with_nested_markets': 'true'}))
        games = parse_espn(espn)
        for g in games:
            g['sport'] = sport
        return {'games': merge_kalshi(merge_odds(games, parse_poly(poly)), kal), 'espn': bool(espn), 'poly': bool(poly), 'kalshi': bool(kal)}
    return await _cached(f'sport:{sport}', go) or {'games': [], 'espn': False, 'poly': False}


ORDER = {'in': 0, 'pre': 1, 'post': 2}


def order_games(games):
    """Live first, then what starts soonest, then what just finished. Pure."""
    return sorted(games or [], key=lambda g: (ORDER.get(g.get('state'), 3), str(g.get('at') or '')))


async def board_all(http):
    """Every sport's board at once, each cached on its own. A sport that is down just shows nothing."""
    rows = await asyncio.gather(*(sport_board(http, k) for k in SPORTS))
    return {'games': order_games([g for r in rows for g in (r.get('games') or [])]), 'espn': any(r.get('espn') for r in rows), 'poly': any(r.get('poly') for r in rows), 'kalshi': any(r.get('kalshi') for r in rows)}


MARKET_CATS = (('Politics', ('politics', 'elections', 'us election', 'geopolitics', 'world')), ('Crypto', ('crypto', 'bitcoin', 'ethereum', 'solana')), ('Sports', ('sports', 'nba', 'nfl', 'soccer', 'games')), ('Pop culture', ('pop culture', 'culture', 'movies', 'music', 'awards')), ('Tech', ('tech', 'ai', 'science')), ('Business', ('business', 'economy', 'finance', 'fed')))


def parse_markets(events):
    """The biggest open prediction markets, each with its category, its leading side and when it ends. Pure."""
    out = []
    for e in events or []:
        tags = [str(t.get('label') or '').lower() for t in e.get('tags') or []]
        cat = next((c for c, keys in MARKET_CATS if any(k in tags for k in keys)), 'Other')
        best = None
        for m in (e.get('markets') or [])[:12]:
            try:
                names = json.loads(m.get('outcomes') or '[]'); prices = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
            except (TypeError, ValueError):
                continue
            if names[:1] == ['Yes'] and prices:   # a Yes market: only Yes is the side to show
                if not 0.01 < prices[0] < 0.995:
                    continue
                side = {'name': str(m.get('groupItemTitle') or m.get('question') or 'Yes')[:60], 'chance': round(prices[0], 3)}
            elif names and prices:
                k = prices.index(max(prices)); side = {'name': str(names[k])[:60], 'chance': round(prices[k], 3)}
            else:
                continue
            if not best or side['chance'] > best['chance']:
                best = side
        if best:
            out.append({'id': str(e.get('id')), 'title': str(e.get('title'))[:110], 'cat': cat, 'end': e.get('endDate'), 'lead': best, 'volume': _f(e.get('volume24hr')), 'slug': e.get('slug')})
    return out


async def markets(http):
    async def go():
        return parse_markets(await _get(http, 'https://gamma-api.polymarket.com/events', params={'active': 'true', 'closed': 'false', 'limit': 60, 'order': 'volume24hr', 'ascending': 'false'}))
    return await _cached('markets', go) or []


def poly_for(words, rows):
    """The open market a bid is about, if any: most of its title's words are in the ask. Pure."""
    ask = {w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}', ' '.join(words) if isinstance(words, (list, tuple)) else str(words or ''))}; best = None; top = 0.0
    for m in rows or []:
        t = {w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}', m.get('title') or '')}
        hit = len(t & ask) / max(1, len(t))
        if hit > top and hit >= 0.6:
            best, top = m, hit
    return {k: best.get(k) for k in ('id', 'title', 'end', 'slug')} if best else None


def poly_winner(event):
    """The side that won a settled market, or None while it is open. Pure."""
    ms = (event or {}).get('markets') or []
    if not ms or not all(m.get('closed') for m in ms):
        return None
    for m in ms:
        try:
            names = json.loads(m.get('outcomes') or '[]'); prices = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
        except (TypeError, ValueError):
            continue
        if prices and max(prices) >= 0.99:
            k = prices.index(max(prices))
            return str(m.get('groupItemTitle')) if names[k] == 'Yes' and m.get('groupItemTitle') else str(names[k])
    return None


FREE_LICENSES = ('public domain', 'cc0', 'cc by', 'cc-by', 'pd')
_img_cache = {}


def parse_images(data, must, n=5):
    """Freely licensed pictures whose name really mentions the subject, each with its credit. No match means no picture: nothing is faked. Pure."""
    words = [w.lower() for w in must if len(w) > 2]; out = []
    for p in ((data or {}).get('query') or {}).get('pages', {}).values():
        i = (p.get('imageinfo') or [{}])[0]; meta = i.get('extmetadata') or {}; lic = str((meta.get('LicenseShortName') or {}).get('value') or ''); title = str(p.get('title') or '')
        if not i.get('thumburl') or not lic.lower().startswith(FREE_LICENSES) or (words and not any(w in title.lower() for w in words)) or 'logo' in title.lower() or title.lower().endswith(('.pdf', '.svg', '.ogv', '.webm', '.tif', '.djvu')):
            continue
        out.append({'url': i['thumburl'], 'page': i.get('descriptionurl'), 'license': lic, 'by': re.sub(r'<[^>]+>', '', str((meta.get('Artist') or {}).get('value') or 'Wikimedia Commons'))[:60].strip(), 'title': title.replace('File:', '')[:70]})
        if len(out) >= n:
            break
    return out


def parse_image(data, must):
    got = parse_images(data, must, 1)
    return got[0] if got else None


async def free_images(http, q, must=()):
    """Real, freely licensed photos from Wikimedia Commons. Only their links are held, in memory for a day, and the browser loads them from Wikimedia: nothing is ever stored here. Team logos stay out: they are trademarks."""
    key = f'{q}|{",".join(must)}'.lower(); got = _img_cache.get(key)
    if got and time.time() - got[0] < 86400:
        return got[1]
    imgs = []
    for query in dict.fromkeys([q, *[w for w in must if len(w) > 3][:2]]):   # the matchup first, then either side
        data = await _get(http, 'https://commons.wikimedia.org/w/api.php', headers={'User-Agent': 'FEELESS/1.0 (https://github.com/tekholds-dev/FEELESS)'}, params={'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrsearch': query, 'gsrlimit': 12, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 480, 'iiextmetadatafilter': 'LicenseShortName|Artist'})
        seen = {x['url'] for x in imgs}
        imgs += [x for x in parse_images(data, list(must) or q.split()) if x['url'] not in seen]
        if len(imgs) >= 5:
            break
    imgs = imgs[:5]
    _img_cache[key] = (time.time(), imgs)
    if len(_img_cache) > 2000:
        _img_cache.pop(next(iter(_img_cache)))
    return imgs


async def free_image(http, q, must=()):
    got = await free_images(http, q, must)
    return got[0] if got else None


def _rec(text):
    """'8-1' or '6-2-1' → how often it wins, or None. Pure."""
    p = [int(x) for x in re.findall(r'\d+', str(text or ''))]
    return round(p[0] / sum(p), 3) if len(p) >= 2 and sum(p) else None


def parse_summary(data):
    """ESPN's game summary → what the game window shows: records and how often each side wins, recent form, team stats side by side, top players, injuries, the win chance over the game. Only what ESPN sent; a missing part stays missing. Pure."""
    data = data or {}
    comp = ((data.get('header') or {}).get('competitions') or [{}])[0]
    st = ((comp.get('status') or {}).get('type') or {})
    teams = []
    for c in sorted(comp.get('competitors') or [], key=lambda x: x.get('homeAway') != 'away'):
        t = c.get('team') or c.get('athlete') or {}; recs = {r.get('type'): r.get('summary') or r.get('displayValue') for r in c.get('record') or []}
        side = 'home' if c.get('homeAway') == 'home' else 'road'
        teams.append({'id': str(t.get('id') or ''), 'abbr': t.get('abbreviation'), 'name': t.get('displayName'), 'side': c.get('homeAway'), 'score': c.get('score'), 'winner': bool(c.get('winner')),
                      'record': recs.get('total') or recs.get('overall') or recs.get('ytd'), 'sideRecord': recs.get(side) or recs.get('away' if side == 'road' else side), 'winRate': _rec(recs.get('total') or recs.get('overall') or recs.get('ytd')), 'sideRate': _rec(recs.get(side) or recs.get('away' if side == 'road' else side)),
                      'form': [], 'leaders': [], 'injuries': []})
    by = {t['id']: t for t in teams}; by_abbr = {t['abbr']: t for t in teams}
    def find(x):
        tt = (x or {}).get('team') or {}
        return by.get(str(tt.get('id') or '')) or by_abbr.get(tt.get('abbreviation'))
    for row in data.get('lastFiveGames') or []:
        t = find(row)
        if t:
            t['form'] = [str(e.get('gameResult') or '')[:1] for e in row.get('events') or [] if e.get('gameResult')][:5]
    for row in data.get('leaders') or []:
        t = find(row)
        if t:
            for cat in (row.get('leaders') or [])[:3]:
                top = (cat.get('leaders') or [{}])[0]; who = (top.get('athlete') or {}).get('displayName')
                if who:
                    t['leaders'].append({'stat': cat.get('displayName'), 'name': who, 'value': top.get('displayValue')})
    for row in data.get('injuries') or []:
        t = find(row)
        if t:
            t['injuries'] = [{'name': (i.get('athlete') or {}).get('displayName'), 'status': i.get('status')} for i in (row.get('injuries') or [])[:6] if (i.get('athlete') or {}).get('displayName')]
    stats = []; box = (data.get('boxscore') or {}).get('teams') or []
    if len(box) == 2 and teams:
        a, b = (box if find(box[0]) is teams[0] else box[::-1]); bm = {x.get('label'): x.get('displayValue') for x in b.get('statistics') or []}
        for x in (a.get('statistics') or [])[:14]:
            if x.get('label') in bm and '-' not in str(x.get('displayValue')):
                stats.append({'label': x.get('label'), 'a': x.get('displayValue'), 'b': bm[x['label']]})
    wp = [round(_f(w.get('homeWinPercentage')), 3) for w in data.get('winprobability') or [] if w.get('homeWinPercentage') is not None]
    if len(wp) > 60:
        wp = [wp[int(i * (len(wp) - 1) / 59)] for i in range(60)]
    pick = (data.get('pickcenter') or [{}])[0] or {}; series = (data.get('seasonseries') or [{}])[0] or {}; venue = ((data.get('gameInfo') or {}).get('venue') or {})
    return {'state': st.get('state'), 'status': st.get('shortDetail') or st.get('description'), 'teams': teams, 'stats': stats, 'wp': wp, 'series': series.get('summary'), 'line': pick.get('details'), 'total': pick.get('overUnder'), 'venue': venue.get('fullName'), 'source': 'ESPN'}


ESPN_HOSTS = ('site.api.espn.com', 'site.web.api.espn.com')


def _name_hit(name, row):
    w = _word(name).split()
    return bool(w) and w[-1] in _word(row)


def _ratio(w, l, o=0):
    t = (w or 0) + (l or 0) + (o or 0)
    return round((w or 0) / t, 3) if t else None


def _fallback_team(name, side, source, record=None, side_record=None, win=None, side_win=None, form=None):
    return {'id': '', 'abbr': name.split()[-1][:3].upper() if name else '', 'name': name, 'side': side, 'score': None, 'winner': False, 'record': record, 'sideRecord': side_record, 'winRate': win, 'sideRate': side_win, 'form': form or [], 'leaders': [], 'injuries': []}


def parse_nhl(data, names):
    """The NHL's own standings → each side's record. Pure."""
    out = []
    for name, side in zip(names, ('away', 'home')):
        r = next((x for x in (data or {}).get('standings') or [] if _name_hit(name, ((x.get('teamName') or {}).get('default') or ''))), None)
        if not r:
            return None
        pre = 'home' if side == 'home' else 'road'; w, l, o = r.get(f'{pre}Wins'), r.get(f'{pre}Losses'), r.get(f'{pre}OtLosses')
        out.append(_fallback_team(name, side, 'NHL', f"{r.get('wins')}-{r.get('losses')}-{r.get('otLosses')}", f'{w}-{l}-{o}', _ratio(r.get('wins'), r.get('losses'), r.get('otLosses')), _ratio(w, l, o)))
    return out


def parse_mlb(data, names):
    """MLB's own standings → each side's record. Pure."""
    rows = [t for rec in (data or {}).get('records') or [] for t in rec.get('teamRecords') or []]; out = []
    for name, side in zip(names, ('away', 'home')):
        r = next((x for x in rows if _name_hit(name, (x.get('team') or {}).get('name') or '')), None)
        if not r:
            return None
        sp = next((x for x in (r.get('records') or {}).get('splitRecords') or [] if x.get('type') == ('home' if side == 'home' else 'away')), {})
        out.append(_fallback_team(name, side, 'MLB', f"{r.get('wins')}-{r.get('losses')}", f"{sp.get('wins')}-{sp.get('losses')}" if sp else None, _ratio(r.get('wins'), r.get('losses')), _ratio(sp.get('wins'), sp.get('losses')) if sp else None))
    return out


def parse_tsdb_form(events, name):
    """TheSportsDB's last games for one team → W / L / D, newest first. Pure."""
    out = []
    for e in events or []:
        try:
            hs, aw = int(e.get('intHomeScore')), int(e.get('intAwayScore'))
        except (TypeError, ValueError):
            continue
        home = _name_hit(name, e.get('strHomeTeam') or ''); mine, them = (hs, aw) if home else (aw, hs)
        out.append('W' if mine > them else 'L' if mine < them else 'D')
    return out[:5]


async def _tsdb_team(http, name, side):
    got = await _get(http, 'https://www.thesportsdb.com/api/v1/json/123/searchteams.php', params={'t': name}); tid = ((got or {}).get('teams') or [{}])[0].get('idTeam')
    if not tid:
        return None
    ev = await _get(http, 'https://www.thesportsdb.com/api/v1/json/123/eventslast.php', params={'id': tid}); form = parse_tsdb_form((ev or {}).get('results'), name)
    if not form:
        return None
    return _fallback_team(name, side, 'TheSportsDB', f"{form.count('W')}-{form.count('L')} last {len(form)}", None, _ratio(form.count('W'), form.count('L'), form.count('D')), None, form)


async def _fallback_read(http, sport, names):
    """ESPN did not answer: the league's own numbers, then TheSportsDB. Records and form only; player stats need ESPN, and the window says which source answered."""
    teams = None; source = None
    if sport == 'nhl':
        teams = parse_nhl(await _get(http, 'https://api-web.nhle.com/v1/standings/now'), names); source = 'NHL'
    elif sport == 'mlb':
        teams = parse_mlb(await _get(http, 'https://statsapi.mlb.com/api/v1/standings', params={'leagueId': '103,104'}), names); source = 'MLB'
    if not teams:
        got = await asyncio.gather(*[_tsdb_team(http, n, s) for n, s in zip(names, ('away', 'home'))])
        if all(got):
            teams = list(got); source = 'TheSportsDB'
    if not teams:
        return None
    return {'state': None, 'status': None, 'teams': teams, 'stats': [], 'wp': [], 'series': None, 'line': None, 'total': None, 'venue': None, 'source': source}


async def game_detail(http, sport, gid, names=()):
    """🏟 One game's window, held for a minute. ESPN, ESPN's second host, the league's own numbers, then TheSportsDB: the first that answers."""
    if sport not in SPORTS or not re.fullmatch(r'[0-9]{1,14}', str(gid or '')):
        return None
    return await _cached(f'game:{sport}:{gid}', lambda: _game_read(http, sport, gid, [str(n)[:60] for n in names if n][:2]))


async def _game_read(http, sport, gid, names=()):
    for host in ESPN_HOSTS:
        data = await _get(http, f'https://{host}/apis/site/v2/sports/{SPORTS[sport][1]}/summary', params={'event': gid})
        got = parse_summary(data) if data else None
        if got and got.get('teams'):
            return got
    return await _fallback_read(http, sport, names) if len(names) == 2 else None


async def bids(http, sport='all', team=''):
    b = await (board_all(http) if sport == 'all' else sport_board(http, sport)); games = order_games(b.get('games') or []); legs = best_legs(games, team); card = None
    if team:
        got = await _get(http, 'https://www.thesportsdb.com/api/v1/json/123/searchteams.php', params={'t': team})
        t0 = ((got or {}).get('teams') or [None])[0]
        card = {'name': t0.get('strTeam'), 'league': t0.get('strLeague'), 'stadium': t0.get('strStadium'), 'formed': t0.get('intFormedYear')} if t0 else None
    shown = [g for g in games if not team or any(_word(team) in _word(t.get('name')) for t in g['teams'])]
    return {'kind': 'bids', 'sports': [['all', 'Everything'], *[[k, v[0]] for k, v in SPORTS.items()]], 'sport': sport, 'teams': team_list(games), 'games': shown[:40], 'live': sum(1 for g in games if g.get('state') == 'in'), 'markets': await markets(http), 'legs': legs[:8], 'parlays': parlays(legs), 'team': card,
            'sources': [{'name': n, 'use': u, 'on': {'ESPN': b.get('espn'), 'Polymarket': b.get('poly'), 'Kalshi': b.get('kalshi'), 'TheSportsDB': bool(card)}.get(n, False)} for n, u, _ in SOURCES['bids']]}


async def pow_tool(http):
    async def go():
        boosts, rug, gecko, fresh, intake = await asyncio.gather(_get(http, 'https://api.dexscreener.com/token-boosts/top/v1'), _get(http, 'https://api.rugcheck.xyz/v1/stats/trending'), _get(http, 'https://api.coingecko.com/api/v3/search/trending'), _get(http, 'https://api.dexscreener.com/token-profiles/latest/v1'), _get(http, 'http://127.0.0.1:5077/api/reputation/familia/intake'))
        return {'boosted': [{'mint': b.get('tokenAddress'), 'url': b.get('url'), 'boost': b.get('totalAmount')} for b in (boosts or []) if b.get('chainId') == 'solana'][:8],
                'rug': [{'mint': r.get('mint'), 'votes': r.get('vote_count') or r.get('up_count')} for r in (rug or [])][:8],
                'trending': [{'sym': (c.get('item') or {}).get('symbol'), 'name': (c.get('item') or {}).get('name'), 'rank': (c.get('item') or {}).get('market_cap_rank')} for c in (gecko or {}).get('coins') or []][:8],
                'fresh': [{'mint': f.get('tokenAddress'), 'url': f.get('url')} for f in (fresh or []) if f.get('chainId') == 'solana'][:8],
                'intake': [{'mint': c.get('mint') or c.get('address'), 'sym': c.get('symbol') or c.get('sym')} for c in (intake or {}).get('coins') or []][:8]}
    d = await _cached('pow', go) or {}
    return {'kind': 'pow', **d, 'sources': [{'name': n, 'use': u, 'on': bool(d.get(k))} for (n, u, _), k in zip(SOURCES['pow'], ('intake', 'fresh', 'boosted', 'rug', 'trending'))]}


def parse_book(data, depth=12):
    """Hyperliquid's book → bids, asks, spread and how much each side holds. Pure."""
    try:
        bids, asks = data['levels']
    except (TypeError, KeyError, ValueError):
        return None
    row = lambda x: {'px': _f(x.get('px')), 'sz': _f(x.get('sz'))}
    b, a = [row(x) for x in bids[:depth]], [row(x) for x in asks[:depth]]
    bs, az = sum(x['sz'] for x in b), sum(x['sz'] for x in a)
    return {'bids': b, 'asks': a, 'spread': round(a[0]['px'] - b[0]['px'], 6) if a and b else None, 'tilt': round(bs / (bs + az), 3) if bs + az else None}


async def book(http, market):
    m = re.sub(r'[^A-Za-z0-9]', '', str(market or 'BTC')).upper()[:12] or 'BTC'

    async def go():
        try:
            r = await http.post('https://api.hyperliquid.xyz/info', json={'type': 'l2Book', 'coin': m}, timeout=8)
            return parse_book(r.json())
        except Exception:   # noqa: BLE001
            return None
    return {'market': m, 'book': await _cached(f'book:{m}', go)}


async def indicators(http, q):
    """TradingView's own public script search, linked to the script's page there. Nothing of theirs is copied here."""
    q = str(q or '').strip()[:60]
    if not q:
        return {'rows': []}
    got = await _get(http, 'https://www.tradingview.com/pubscripts-suggest-json/', params={'search': q}, headers={'User-Agent': 'Mozilla/5.0'})
    def link(x):   # a search by its name always lands: their ids do not map to a stable page address
        return 'https://www.tradingview.com/scripts/search/' + quote(str(x.get('scriptName') or q)[:80], safe='') + '/'
    rows = [{'t': str(x.get('scriptName') or x.get('title') or '')[:80], 'by': (x.get('author') or {}).get('username') if isinstance(x.get('author'), dict) else None, 'url': link(x)} for x in (got or {}).get('results') or []][:12]
    return {'rows': rows, 'read': got is not None}


def parse_rss(text, limit=8):
    return [re.sub(r'<!\[CDATA\[|\]\]>', '', t).strip()[:120] for t in re.findall(r'<item>.*?<title>(.*?)</title>', str(text or ''), re.S)][:limit]


async def trending(http):
    """🔥 What people are on right now, from 5 free sources. What it says is data for the minds, never an instruction."""
    async def go():
        async def news():
            try:
                return parse_rss((await http.get('https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en', timeout=8)).text)
            except Exception:   # noqa: BLE001
                return []

        async def hn():
            ids = await _get(http, 'https://hacker-news.firebaseio.com/v0/topstories.json')
            rows = await asyncio.gather(*(_get(http, f'https://hacker-news.firebaseio.com/v0/item/{i}.json') for i in (ids or [])[:6]))
            return [str(x.get('title'))[:120] for x in rows if x]
        n, h, bs, cg, wiki = await asyncio.gather(news(), hn(), _get(http, 'https://public.api.bsky.app/xrpc/app.bsky.unspecced.getTrendingTopics', params={'limit': 8}), _get(http, 'https://api.coingecko.com/api/v3/search/trending'),
                                                  _get(http, f"https://en.wikipedia.org/api/rest_v1/feed/featured/{time.strftime('%Y/%m/%d', time.gmtime(time.time() - 86400))}", headers={'User-Agent': 'FEELESS/1.0 (agent trends)'}))
        return {'Google News': n, 'Hacker News': h, 'Bluesky': [str(t.get('displayName') or t.get('topic'))[:80] for t in (bs or {}).get('topics') or []][:8], 'CoinGecko': [f"${(c.get('item') or {}).get('symbol')}" for c in (cg or {}).get('coins') or []][:8],
                'Wikipedia': [str(a.get('normalizedtitle') or a.get('title'))[:80] for a in (((wiki or {}).get('mostread') or {}).get('articles') or [])][:8]}
    d = await _cached('trending', go) or {}
    return {'kind': 'content', 'trends': d, 'sources': [{'name': n, 'use': 'Trending now', 'on': bool(d.get(n))} for n in ('Google News', 'Hacker News', 'Bluesky', 'CoinGecko', 'Wikipedia')]}


def parse_hl(data):
    """Hyperliquid's markets → rows, biggest open interest first. Pure."""
    try:
        uni, ctx = data[0]['universe'], data[1]
    except (TypeError, KeyError, IndexError):
        return []
    rows = [{'market': u.get('name'), 'price': _f(c.get('markPx')), 'fundingPct': round(_f(c.get('funding')) * 100, 4), 'oiUsd': round(_f(c.get('openInterest')) * _f(c.get('markPx'))), 'dayVol': round(_f(c.get('dayNtlVlm')))} for u, c in zip(uni, ctx) if not u.get('isDelisted')]
    return sorted(rows, key=lambda r: -r['oiUsd'])


async def pop_tool(http):
    async def go():
        async def hl():
            try:
                r = await http.post('https://api.hyperliquid.xyz/info', json={'type': 'metaAndAssetCtxs'}, timeout=8)
                return r.json()
            except Exception:   # noqa: BLE001
                return None
        h, fng, glob, spot, llama = await asyncio.gather(hl(), _get(http, 'https://api.alternative.me/fng/'), _get(http, 'https://api.coingecko.com/api/v3/global'), _get(http, 'https://api.exchange.coinbase.com/products/BTC-USD/ticker'), _get(http, 'https://api.llama.fi/overview/derivatives?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true'))
        rows = parse_hl(h)
        return {'markets': rows[:12], 'hotFunding': sorted(rows[:40], key=lambda r: -abs(r['fundingPct']))[:5], 'mood': ((fng or {}).get('data') or [{}])[0].get('value_classification'), 'moodValue': ((fng or {}).get('data') or [{}])[0].get('value'), 'btcDom': (((glob or {}).get('data') or {}).get('market_cap_percentage') or {}).get('btc'), 'btcSpot': _f((spot or {}).get('price')), 'perpVol24h': (llama or {}).get('total24h'), 'read': {'Hyperliquid': bool(rows), 'Coinbase': bool(spot), 'Fear & Greed': bool(fng), 'CoinGecko': bool(glob), 'DefiLlama': bool(llama)}}
    d = await _cached('pop', go) or {}
    return {'kind': 'pop', **d, 'sources': [{'name': n, 'use': u, 'on': bool((d.get('read') or {}).get(n))} for n, u, _ in SOURCES['pop']]}


def sport_named(text):
    """The sport a question names, or None. Whole words only. Pure."""
    t = f' {_word(text)} '
    for k, (label, _) in SPORTS.items():
        if f' {k} ' in t or f' {_word(label)} ' in t:
            return k
    return None


async def best_topic(http, ask=''):
    """🏈 The strongest 2 or 3 sides, from free scores and market odds. A question that names a sport only ever gets that sport: an NBA question never gets NFL picks. → the topic, or '' when there are none."""
    named = sport_named(ask)
    for sport, (label, _) in ([(named, SPORTS[named])] if named else SPORTS.items()):
        try:
            legs = (await bids(http, sport)).get('legs') or []
        except Exception:   # noqa: BLE001 — try the next sport
            continue
        if len(legs) >= 2:
            return f"best {label} picks: {', '.join(x['pick'] for x in legs[:3])}"[:120]
    return ''


_STOP_WORDS = {'make', 'build', 'create', 'me', 'a', 'an', 'the', 'with', 'and', 'for', 'that', 'this', 'please', 'want', 'need', 'page', 'site', 'website', 'app', 'of', 'to', 'in', 'on', 'my', 'i', 'it', 'some', 'like', 'can', 'you', 'so', 'is'}


def keywords(ask, n=4):
    """The words worth searching for. Pure."""
    seen = []
    for w in re.findall(r'[a-z0-9][a-z0-9+#.-]+', str(ask or '').lower()):
        if w not in _STOP_WORDS and w not in seen:
            seen.append(w)
    return seen[:n]


def parse_refs(gh, hn):
    """Real references from two free public sources: repos by stars, Show HN by points. Pure."""
    out = []
    for r in (gh or {}).get('items') or []:
        out.append({'title': str(r.get('full_name') or '')[:80], 'url': str(r.get('html_url') or ''), 'why': str(r.get('description') or '')[:160], 'source': 'GitHub', 'score': int(r.get('stargazers_count') or 0)})
    for h in (hn or {}).get('hits') or []:
        if h.get('url'):
            out.append({'title': str(h.get('title') or '').replace('Show HN: ', '')[:80], 'url': str(h.get('url'))[:300], 'why': '', 'source': 'Hacker News', 'score': int(h.get('points') or 0)})
    return out


async def _reach(http, ref):
    """Can a plain visitor open it? A wall or an error marks it blocked, so the plan never leans on a site nobody can read."""
    try:
        r = await http.get(ref['url'], timeout=6, follow_redirects=True, headers={'User-Agent': 'Mozilla/5.0 FEELESS-agent'})
        return {**ref, 'open': r.status_code < 400 and not r.headers.get('cf-mitigated')}
    except Exception:   # noqa: BLE001
        return {**ref, 'open': False}


async def build_refs(http, ask, deep=False):
    """🔎 The best current builds for a request, from free sources, each checked as reachable. → [{title, url, why, source, score, open}]"""
    words = keywords(ask)
    if not words:
        return []
    q = ' '.join(words); n = 8 if deep else 4
    gh, hn = await asyncio.gather(_get(http, 'https://api.github.com/search/repositories', params={'q': f'{q} stars:>20', 'sort': 'stars', 'per_page': n}), _get(http, 'https://hn.algolia.com/api/v1/search', params={'query': q, 'tags': 'show_hn', 'hitsPerPage': n}))
    refs = parse_refs(gh, hn)
    if not refs and len(words) > 2:   # a long ask can match nothing: widen once
        q = ' '.join(words[:2])
        gh, hn = await asyncio.gather(_get(http, 'https://api.github.com/search/repositories', params={'q': f'{q} stars:>20', 'sort': 'stars', 'per_page': n}), _get(http, 'https://hn.algolia.com/api/v1/search', params={'query': q, 'tags': 'show_hn', 'hitsPerPage': n}))
        refs = parse_refs(gh, hn)
    return sorted(await asyncio.gather(*(_reach(http, r) for r in refs[:n * 2])), key=lambda r: (not r['open'], -r['score']))
