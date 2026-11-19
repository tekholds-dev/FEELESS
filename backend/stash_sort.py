"""🗂 THE STASH SORTER (Slice 10, owner 2026-11-18: "they went on a site for Bulls–Lakers and the site had Clippers and Spurs odds on there: it
should easily get sorted so any new agent can reuse it from the stash"). Pure: a page's text in → everything ON it out (teams, players, coins,
leagues, markets, dates), its category (the seal it is kept under) and how long it stays fresh. Never only the reason it was opened.

Tags are plain words here ("team:nba:clippers", "league:nba", "market:spread", "date:2026-11-18", "coin:sol", "player:lebron james");
the store keeps them only as keyed hashes, so the index on disk names nothing."""
import re
import time

# league → {nickname: [other words that name the same team]}. A nickname that is also a plain word ("heat", "magic") must be Capitalised.
TEAMS = {
    'nba': {'hawks': ['atlanta'], 'celtics': ['boston'], 'nets': ['brooklyn'], 'hornets': ['charlotte'], 'bulls': ['chicago bulls'], 'cavaliers': ['cavs', 'cleveland'],
            'mavericks': ['mavs', 'dallas mavericks'], 'nuggets': ['denver nuggets'], 'pistons': ['detroit pistons'], 'warriors': ['golden state'], 'rockets': ['houston rockets'],
            'pacers': ['indiana'], 'clippers': ['la clippers'], 'lakers': ['los angeles lakers'], 'grizzlies': ['memphis'], 'heat': ['miami heat'], 'bucks': ['milwaukee'],
            'timberwolves': ['wolves', 'minnesota timberwolves'], 'pelicans': ['new orleans'], 'knicks': ['new york knicks'], 'thunder': ['oklahoma city', 'okc'],
            'magic': ['orlando magic'], '76ers': ['sixers', 'philadelphia 76ers'], 'suns': ['phoenix suns'], 'trail blazers': ['blazers', 'portland'], 'kings': ['sacramento kings'],
            'spurs': ['san antonio'], 'raptors': ['toronto raptors'], 'jazz': ['utah jazz'], 'wizards': ['washington wizards']},
    'nfl': {'cardinals': ['arizona cardinals'], 'falcons': ['atlanta falcons'], 'ravens': ['baltimore'], 'bills': ['buffalo bills'], 'panthers': ['carolina panthers'],
            'bears': ['chicago bears'], 'bengals': ['cincinnati'], 'browns': ['cleveland browns'], 'cowboys': ['dallas cowboys'], 'broncos': ['denver broncos'],
            'lions': ['detroit lions'], 'packers': ['green bay'], 'texans': ['houston texans'], 'colts': ['indianapolis'], 'jaguars': ['jacksonville'], 'chiefs': ['kansas city'],
            'raiders': ['las vegas raiders'], 'chargers': ['la chargers'], 'rams': ['la rams'], 'dolphins': ['miami dolphins'], 'vikings': ['minnesota vikings'],
            'patriots': ['new england'], 'saints': ['new orleans saints'], 'giants': ['new york giants'], 'jets': ['new york jets'], 'eagles': ['philadelphia eagles'],
            'steelers': ['pittsburgh'], '49ers': ['niners', 'san francisco 49ers'], 'seahawks': ['seattle'], 'buccaneers': ['bucs', 'tampa bay buccaneers'],
            'titans': ['tennessee titans'], 'commanders': ['washington commanders']},
    'nhl': {'bruins': ['boston bruins'], 'sabres': ['buffalo sabres'], 'red wings': ['detroit red wings'], 'panthers': ['florida panthers'], 'canadiens': ['habs', 'montreal'],
            'senators': ['ottawa'], 'lightning': ['tampa bay lightning'], 'maple leafs': ['leafs', 'toronto maple leafs'], 'hurricanes': ['carolina hurricanes'],
            'blue jackets': ['columbus'], 'devils': ['new jersey devils'], 'islanders': ['new york islanders'], 'rangers': ['new york rangers'], 'flyers': ['philadelphia flyers'],
            'penguins': ['pittsburgh penguins'], 'capitals': ['caps', 'washington capitals'], 'blackhawks': ['chicago blackhawks'], 'avalanche': ['colorado avalanche'],
            'stars': ['dallas stars'], 'wild': ['minnesota wild'], 'predators': ['nashville'], 'blues': ['st. louis blues'], 'jets': ['winnipeg'], 'ducks': ['anaheim'],
            'flames': ['calgary'], 'oilers': ['edmonton'], 'kings': ['la kings', 'los angeles kings'], 'sharks': ['san jose'], 'kraken': ['seattle kraken'],
            'canucks': ['vancouver'], 'golden knights': ['vegas golden knights'], 'utah hockey club': ['utah hc', 'mammoth']},
    'mlb': {'diamondbacks': ['dbacks', 'arizona diamondbacks'], 'braves': ['atlanta braves'], 'orioles': ['baltimore orioles'], 'red sox': ['boston red sox'], 'cubs': ['chicago cubs'],
            'white sox': ['chicago white sox'], 'reds': ['cincinnati reds'], 'guardians': ['cleveland guardians'], 'rockies': ['colorado rockies'], 'tigers': ['detroit tigers'],
            'astros': ['houston astros'], 'royals': ['kansas city royals'], 'angels': ['la angels'], 'dodgers': ['la dodgers'], 'marlins': ['miami marlins'], 'brewers': ['milwaukee brewers'],
            'twins': ['minnesota twins'], 'mets': ['new york mets'], 'yankees': ['new york yankees'], 'athletics': ["a's", 'oakland'], 'phillies': ['philadelphia phillies'],
            'pirates': ['pittsburgh pirates'], 'padres': ['san diego'], 'giants': ['san francisco giants'], 'mariners': ['seattle mariners'], 'cardinals': ['st. louis cardinals'],
            'rays': ['tampa bay rays'], 'rangers': ['texas rangers'], 'blue jays': ['toronto blue jays'], 'nationals': ['washington nationals']},
}
LEAGUE_WORDS = {'nba': ('nba', 'basketball'), 'nfl': ('nfl', 'football', 'touchdown', 'quarterback'), 'nhl': ('nhl', 'hockey', 'puck line'), 'mlb': ('mlb', 'baseball', 'run line'),
                'ncaa': ('ncaa', 'college football', 'college basketball', 'march madness'), 'soccer': ('premier league', 'la liga', 'champions league', 'mls', 'serie a', 'bundesliga'),
                'ufc': ('ufc', 'mma')}
PLAIN_WORDS = {'heat', 'magic', 'thunder', 'jazz', 'suns', 'kings', 'nets', 'bulls', 'stars', 'wild', 'lightning', 'blues', 'jets', 'giants', 'rays', 'reds', 'twins',
               'royals', 'angels', 'saints', 'bills', 'lions', 'bears', 'eagles', 'rams', 'titans', 'chiefs', 'cardinals', 'rangers', 'devils', 'ducks', 'flames', 'sharks',
               'capitals', 'senators', 'pirates', 'tigers', 'athletics', 'commanders', 'guardians', 'nationals', 'predators', 'avalanche', 'hurricanes', 'panthers', 'colts'}
MARKETS = {'moneyline': ('moneyline', 'money line', ' ml '), 'spread': ('spread', 'ats', 'against the spread', 'puck line', 'run line'), 'total': ('total', 'over/under', 'o/u', 'total points', 'totals', ' over ', ' under '),
           'props': ('player prop', 'props', 'points prop', 'rebounds', 'assists'), 'parlay': ('parlay', 'same game parlay', 'sgp'), 'futures': ('futures', 'to win the championship', 'mvp odds'),
           'injuries': ('injury report', 'injuries', 'questionable', 'out for', 'day-to-day'), 'lineups': ('starting lineup', 'lineups', 'starters'), 'odds': ('odds', 'betting line', 'line movement'),
           'prediction': ('kalshi', 'polymarket', 'yes price', 'contract'), 'price': ('price', 'market cap', 'liquidity', 'volume 24h', '24h volume'),
           'schedule': ('schedule', 'tip-off', 'kickoff', 'start time'), 'standings': ('standings', 'record', 'win-loss', 'conference')}
COINS = {'bitcoin': 'btc', 'btc': 'btc', 'ethereum': 'eth', 'eth': 'eth', 'solana': 'sol', 'sol': 'sol', 'bonk': 'bonk', 'jupiter': 'jup', 'jup': 'jup', 'usdc': 'usdc', 'dogecoin': 'doge', 'doge': 'doge'}
COIN_HOSTS = ('dexscreener.com', 'solscan.io', 'rugcheck.xyz', 'birdeye.so', 'pump.fun', 'jup.ag', 'coingecko.com', 'coinmarketcap.com', 'defillama.com')
MONTHS = {m: i + 1 for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
STAT_WORDS = r'(?:pts|points|reb|rebounds|ast|assists|yds|yards|td|tds|goals|saves|era|hr|avg|ppg|rpg|apg|questionable|probable|doubtful|out|minutes|min)'
MINT = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
TICKER = re.compile(r'\$([A-Za-z][A-Za-z0-9]{1,9})\b')
NUM = re.compile(r'(?<![\w.])([+\-−]?\$?\d(?:[\d,]*\d)?(?:\.\d+)?%?)(?![\w])')

# 🕐 how long a page stays fresh, by what is on it (live odds age in minutes, a roster in hours). The first that matches wins.
FRESH = (('price', 5 * 60), ('prediction', 10 * 60), ('odds', 30 * 60), ('moneyline', 30 * 60), ('spread', 30 * 60), ('total', 30 * 60), ('props', 30 * 60),
         ('parlay', 30 * 60), ('lineups', 60 * 60), ('injuries', 2 * 3600), ('schedule', 6 * 3600), ('standings', 12 * 3600), ('futures', 12 * 3600))
FRESH_SEARCH = 30 * 60
FRESH_DEFAULT = 3600
TAG_MAX = 60


def _low(t):
    return ' ' + re.sub(r'\s+', ' ', str(t or '')).lower() + ' '


def _has(low, word):
    return re.search(r'(?<![a-z0-9])' + re.escape(word.strip()) + r'(?![a-z0-9])', low) is not None


def _cap_has(text, word):
    """A nickname that is also a plain word counts only Capitalised ("the Heat", never "the heat of the game")."""
    return re.search(r'(?<![A-Za-z0-9])' + re.escape(word.title() if not word[0].isdigit() else word) + r'(?![A-Za-z0-9])', text) is not None


def teams_on(text):
    """→ {league: {nickname}} for every team named on the page. A nickname two leagues share (Kings, Jets, Giants…) goes to the league the
    rest of the page is about; a page about neither keeps both."""
    raw, low = str(text or ''), _low(text); hits = {}
    for lg, rows in TEAMS.items():
        for nick, alts in rows.items():
            ok = any(_has(low, a) for a in alts) or (_cap_has(raw, nick) if nick in PLAIN_WORDS else _has(low, nick))
            if ok:
                hits.setdefault(lg, set()).add(nick)
    shared = {}
    for lg, ns in hits.items():
        for n in ns:
            shared.setdefault(n, []).append(lg)
    weight = {lg: len([n for n in ns if len(shared[n]) == 1]) + 3 * sum(1 for w in LEAGUE_WORDS.get(lg, ()) if _has(low, w)) for lg, ns in hits.items()}
    out = {}
    for n, lgs in shared.items():
        if len(lgs) > 1:
            best = max(weight[x] for x in lgs)
            lgs = [x for x in lgs if weight[x] == best] if best > 0 else lgs
        for lg in lgs:
            out.setdefault(lg, set()).add(n)
    return out


def leagues_on(text, teams=None):
    low = _low(text); teams = teams_on(text) if teams is None else teams
    return sorted({lg for lg, ws in LEAGUE_WORDS.items() if any(_has(low, w) for w in ws)} | {lg for lg, ns in teams.items() if ns})


def markets_on(text):
    low = _low(text)
    return sorted(m for m, ws in MARKETS.items() if any((w in low) if w.startswith(' ') else _has(low, w) for w in ws))


def dates_on(text, now=None):
    """Every calendar date written on the page (ISO, "Nov 18", "November 18, 2026", "11/18"), plus 'today'/'tonight' as the read date."""
    raw, low = str(text or ''), _low(text); yr = time.localtime(now or time.time()).tm_year; out = set()
    for y, m, d in re.findall(r'\b(20\d\d)-(\d\d)-(\d\d)\b', raw):
        out.add(f'{y}-{m}-{d}')
    for mo, d, y in re.findall(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?(?:,? (20\d\d))?\b', low):
        if 1 <= int(d) <= 31:
            out.add(f'{y or yr}-{MONTHS[mo]:02d}-{int(d):02d}')
    for m, d in re.findall(r'\b(1[0-2]|0?[1-9])/(3[01]|[12]\d|0?[1-9])\b', raw):
        out.add(f'{yr}-{int(m):02d}-{int(d):02d}')
    if _has(low, 'today') or _has(low, 'tonight'):
        out.add(time.strftime('%Y-%m-%d', time.localtime(now or time.time())))
    return sorted(out)[:12]


def players_on(text, n=20):
    """People named next to a stat or an injury word ("LeBron James 27 pts", "Kawhi Leonard (questionable)"). A name with no number or
    status beside it is not guessed at."""
    raw = re.sub(r'\s+', ' ', str(text or '')); out = []
    pat = r"\b([A-Z][a-zA-Z'’.-]+(?: [A-Z][a-zA-Z'’.-]+){1,2})\b[ ,:()-]{0,4}(?:\d+(?:\.\d+)? ?)?" + STAT_WORDS + r'\b'
    for m in re.finditer(pat, raw):
        name = m.group(1).strip()
        low = name.lower()
        if any(_has(' ' + low + ' ', t) for lg in TEAMS.values() for t in lg) or low.split()[0] in ('the', 'game', 'team', 'over', 'under'):
            continue
        if low not in out:
            out.append(low)
        if len(out) >= n:
            break
    return out


def coins_on(text, host=''):
    raw, low = str(text or ''), _low(text); out = set()
    for w, sym in COINS.items():
        if len(w) > 3 and _has(low, w) or len(w) <= 4 and re.search(r'(?<![A-Za-z0-9$])\$?' + w.upper() + r'(?![A-Za-z0-9])', raw):
            out.add(sym)
    out |= {t.lower() for t in TICKER.findall(raw)}
    if any(h in str(host) for h in COIN_HOSTS):
        out |= {f'mint:{m}' for m in MINT.findall(raw)[:6]}
    return sorted(out)[:20]


def numbers_of(text, n=400):
    """Every number on the page, each with the few words before it (so "+3.5" stays "Clippers +3.5"). → [{n, ctx}]"""
    raw = re.sub(r'\s+', ' ', str(text or '')); out = []
    for m in NUM.finditer(raw):
        v = m.group(1)
        if len(v.strip('+-−$%,.')) == 0:
            continue
        out.append({'n': v, 'ctx': raw[max(0, m.start() - 40):m.start()].strip()[-40:]})
        if len(out) >= n:
            break
    return out


def sort(text, url='', title='', now=None, search=False):
    """🗂 Everything ON the page → {tags, cat, fresh, leagues, teams, markets, dates, players, coins}. `cat` is the seal it is kept under."""
    host = re.sub(r'^www\.', '', re.sub(r'^https?://', '', str(url or '').lower()).split('/')[0])
    body = f'{title} {text}'
    teams = teams_on(body); leagues = leagues_on(body, teams); markets = markets_on(body); coins = coins_on(body, host)
    tags = [f'league:{lg}' for lg in leagues] + [f'team:{lg}:{n}' for lg in sorted(teams) for n in sorted(teams[lg])] + [f'team:{n}' for n in sorted({n for ns in teams.values() for n in ns})]
    tags += [f'market:{m}' for m in markets] + [f'date:{d}' for d in dates_on(body, now)] + [f'player:{p}' for p in players_on(body)] + [f'coin:{c}' for c in coins]
    tags += [f'site:{host}'] if host else []
    if leagues:   # the seal: the league most of the page is about
        cat = max(leagues, key=lambda lg: (len(teams.get(lg) or ()), lg))
    elif coins or any(h in host for h in COIN_HOSTS):
        cat = 'coins'
    elif search:
        cat = 'search'
    elif 'prediction' in markets:
        cat = 'markets'
    else:
        cat = 'web'
    fresh = FRESH_SEARCH if search else next((s for k, s in FRESH if k in markets), FRESH_DEFAULT)
    return {'tags': list(dict.fromkeys(tags))[:TAG_MAX], 'cat': cat, 'fresh': fresh, 'leagues': leagues, 'teams': {k: sorted(v) for k, v in teams.items()},
            'markets': markets, 'dates': dates_on(body, now), 'players': players_on(body), 'coins': coins}


def ask_tags(text, now=None):
    """What a brain is about to look for (its job / topic) → the tags to ask the stash for, most specific first. Teams beat leagues,
    leagues beat markets; a bare league or market alone never counts as a hit (too broad to be the page it needs)."""
    s = sort(text, now=now)
    specific = [t for t in s['tags'] if t.startswith(('team:', 'player:', 'coin:')) and t.count(':') == 1]
    return {'want': specific, 'leagues': [f'league:{lg}' for lg in s['leagues']], 'markets': [f'market:{m}' for m in s['markets']]}
