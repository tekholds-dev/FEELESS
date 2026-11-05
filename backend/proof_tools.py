"""🧰 THE PROOF FOLDERS' DASHES (owner 2026-11-04): each folder opens on live rows from its top 5 free sources. PoB: pick a sport and a team, see the games and the parlays the market likes most.
Every number comes from a source named on screen. "Best" means the market's own odds say it is most likely: never a promise."""
import asyncio
import json
import re
import time

SPORTS = {'nfl': ('NFL', 'football/nfl'), 'nba': ('NBA', 'basketball/nba'), 'mlb': ('MLB', 'baseball/mlb'), 'nhl': ('NHL', 'hockey/nhl'), 'cfb': ('College football', 'football/college-football'), 'cbb': ('College basketball', 'basketball/mens-college-basketball'), 'epl': ('Soccer', 'soccer/eng.1')}
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
        row = [{'name': (t.get('team') or {}).get('displayName'), 'short': (t.get('team') or {}).get('shortDisplayName') or (t.get('team') or {}).get('name'), 'abbr': (t.get('team') or {}).get('abbreviation'), 'score': t.get('score'), 'winner': t.get('winner')} for t in teams]
        odds = (c.get('odds') or [{}])[0]
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
        espn, poly, kal = await asyncio.gather(_get(http, f'https://site.api.espn.com/apis/site/v2/sports/{SPORTS[sport][1]}/scoreboard'), _get(http, 'https://gamma-api.polymarket.com/events', params={'active': 'true', 'closed': 'false', 'limit': 60, 'tag_slug': POLY_TAG[sport], 'order': 'volume24hr', 'ascending': 'false'}),
                                               _get(http, 'https://api.elections.kalshi.com/trade-api/v2/events', params={'series_ticker': KALSHI[sport], 'status': 'open', 'limit': 60, 'with_nested_markets': 'true'}))
        games = parse_espn(espn)
        for g in games:
            g['sport'] = sport
        return {'games': merge_kalshi(merge_odds(games, parse_poly(poly)), kal), 'espn': bool(espn), 'poly': bool(poly), 'kalshi': bool(kal)}
    return await _cached(f'sport:{sport}', go) or {'games': [], 'espn': False, 'poly': False}


async def bids(http, sport='nfl', team=''):
    b = await sport_board(http, sport); games = b.get('games') or []; legs = best_legs(games, team); card = None
    if team:
        got = await _get(http, 'https://www.thesportsdb.com/api/v1/json/123/searchteams.php', params={'t': team})
        t0 = ((got or {}).get('teams') or [None])[0]
        card = {'name': t0.get('strTeam'), 'league': t0.get('strLeague'), 'stadium': t0.get('strStadium'), 'formed': t0.get('intFormedYear')} if t0 else None
    shown = [g for g in games if not team or any(_word(team) in _word(t.get('name')) for t in g['teams'])]
    return {'kind': 'bids', 'sports': [[k, v[0]] for k, v in SPORTS.items()], 'sport': sport, 'teams': team_list(games), 'games': shown[:24], 'legs': legs[:8], 'parlays': parlays(legs), 'team': card,
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
    def link(x):
        part = re.sub(r'[^\w-]', '', str(x.get('scriptIdPart') or ''))
        return f'https://www.tradingview.com/script/{part}/' if part else f'https://www.tradingview.com/scripts/search/{q}/'
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
