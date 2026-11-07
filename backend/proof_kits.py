"""🧰 THE FEELESS KITS (owner 2026-11-06: "so the agents truly have stuff to use"). Our own working kits, one set per proof, read before the internet: a method, the sums it needs, and for some of them fresh numbers read from free public sources.

A kit is reference data. It moves no money and runs no code. A PoW kit reaches a proof only when its owner picks it, never by the agent's own choice, because a PoW can buy real coins. Every guard stays where it is."""
import json
import time
from pathlib import Path

LIVE_FILE = 'live.dat'   # not *.json: rows() reads every .json in the kit folder as a kit
LIVE_MAX_AGE = 6 * 3600   # older numbers than this are not shown as fresh
HL = 'https://api.hyperliquid.xyz/info'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/{}/scoreboard'
POLY = 'https://gamma-api.polymarket.com/markets?active=true&closed=false&order=volume24hr&ascending=false&limit=25'
HN = 'https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=12'
WIKI = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{}'

BOOK = [
    {'id': 'fl-coin-vet', 'name': 'Coin Vetter', 'what': 'Checks a coin before anyone trusts it', 'kinds': ['pow'], 'cat': 'Research', 'task': 'Trading research', 'skills': ['rug checks', 'holders', 'liquidity', 'snipers'], 'version': '1.0', 'compat': 'Read by the minds', 'pickOnly': True,
     'can': ['A check list in the order that kills bad coins fastest', 'What each warning really means', 'What to write down as evidence'],
     'examples': ['Vet the 4 hottest Solana coins and say which you would drop first', 'Is this dev wallet still holding? Show where you read it'],
     'text': 'COIN VETTER. Work in this order and stop at the first fatal one. 1) Mint and freeze authority: still on is a fail. 2) Pool: how deep, is it locked or burned, who added it. 3) Holders: top 10 share with pools and known burn wallets taken out. 4) Dev: what they still hold, what their earlier coins did. 5) Bundles and snipers: how much the first block bought and whether they left. 6) Volume: real buyers or the same wallets round and round. 7) Age against price: how far it already ran. Sources: rugcheck.xyz, solsniffer.com, dexscreener.com. Quote the number and the site for each check. A site that would not open is NOT a pass: say it was not read. This list adds evidence only. It changes no buy rule, and every guard still applies.'},
    {'id': 'fl-risk-desk', 'name': 'Risk Desk', 'what': 'Size, exits and hold time on the evidence', 'kinds': ['pow'], 'cat': 'Risk', 'task': 'Risk and execution', 'skills': ['position size', 'exits', 'hold time', 'expectancy'], 'version': '1.0', 'compat': 'Read by the minds', 'pickOnly': True,
     'can': ['Exits written before the entry', 'Expectancy sums from your own record', 'What a hold time has really paid here'],
     'examples': ['Given my last 20 proofs, what did short holds cost me?', 'Write the exit plan for this coin before you call it'],
     'text': 'RISK DESK. Write the exits first: where it is wrong, where you take some, and what would make you leave early. Expectancy = win rate x average win - loss rate x average loss. Show it from the proofs on file, and say how few they are when they are few. The real Fuse card ledger (943 pieces) shows holds of 30 minutes or more won, holds under 15 minutes lost, and trims made the money. That is evidence about the past and no promise. Never average down to rescue a call. P&L here never includes fees. This kit changes no size, no cap and no guard: the engine decides those.'},
    {'id': 'fl-funding', 'name': 'Funding Reader', 'what': 'Who is paying whom, right now', 'kinds': ['pop'], 'cat': 'Research', 'task': 'Perp analysis', 'skills': ['funding', 'open interest', 'crowding'], 'version': '1.0', 'compat': 'Read by the minds', 'live': 'funding', 'source': 'Hyperliquid',
     'can': ['The most extreme funding on Hyperliquid, refreshed', 'Open interest beside each rate', 'How to read crowding without guessing'],
     'examples': ['Which perp is most crowded long right now, and what would unwind it?', 'Call a practice trade against the worst funding on the board'],
     'text': 'FUNDING READER. Positive funding: longs pay shorts, the long side is crowded. Negative: the reverse. Extreme funding with rising open interest means a crowded trade that can unwind hard. Extreme funding with falling open interest means it is already unwinding. Funding alone is not a signal: say what would prove you wrong, and give exits on every call. Hourly rate x 8760 is the yearly pace, and it rarely lasts.'},
    {'id': 'fl-liq', 'name': 'Leverage Math', 'what': 'Where you get liquidated, worked out', 'kinds': ['pop'], 'cat': 'Risk', 'task': 'Leverage and liquidation', 'skills': ['leverage', 'liquidation', 'margin', 'practice'], 'version': '1.0', 'compat': 'Read by the minds', 'live': 'liq', 'source': 'Hyperliquid',
     'can': ['Rough liquidation prices at live marks', 'Sums for ROE from a price move', 'A stop that always sits before liquidation'],
     'examples': ['At 5x on SOL, how far is liquidation and where must my stop sit?', 'What leverage survives a normal day of this coin?'],
     'text': 'LEVERAGE MATH. ROE % = price move % x leverage. A rough isolated liquidation price: long = entry x (1 - 1/lev + m), short = entry x (1 + 1/lev - m), with m = 1 / (2 x max leverage) as the maintenance margin. It is rough: the venue decides the real one. A stop must sit well before liquidation, and if the move you expect is smaller than the normal noise, the leverage is wrong. Practice calls move no money and must say they are practice.'},
    {'id': 'fl-value', 'name': 'Value Scorer', 'what': 'Your odds against the market price', 'kinds': ['pob'], 'cat': 'Decision', 'task': 'Pricing and value', 'skills': ['implied odds', 'edge', 'vig', 'comparing'], 'version': '1.0', 'compat': 'Read by the minds', 'live': 'markets', 'source': 'Polymarket',
     'can': ['Biggest open markets with their implied odds', 'Sums to strip the house cut', 'A score for comparing picks side by side'],
     'examples': ['Compare these 3 picks by edge, not by feel', 'What does this market imply, and what would you need to believe to bet it?'],
     'text': 'VALUE SCORER. A Yes price of 0.62 implies 62%. American odds: -150 implies 150 / 250 = 60%, +150 implies 100 / 250 = 40%. Strip the cut: divide each side by the sum of all sides. Edge = your chance - implied chance. Give your chance BEFORE you look at the price, say what it rests on, and bet nothing on an edge you cannot explain. Rank picks by edge, then by how strong the sources are. No edge is a fine answer: say no bid.'},
    {'id': 'fl-source-check', 'name': 'Source Check', 'what': 'Every claim traced to where it was read', 'kinds': ['pob', 'poc'], 'cat': 'Research', 'task': 'Source verification', 'skills': ['fact checks', 'two sources', 'dates', 'injuries'], 'version': '1.0', 'compat': 'Read by the minds', 'live': 'games', 'source': 'ESPN',
     'can': ["Today's real games from ESPN", 'A two source rule for anything that decides a call', 'How to spot a stale or made up number'],
     'examples': ['Check every claim in this pick against two sites', 'Who is really out tonight? Show me where you read it'],
     'text': 'SOURCE CHECK. Anything a decision rests on needs two independent sources, and copies of one report count as one. Check the date on every source against today: a date after your training is real. A lineup, injury or line older than a few hours is stale, say so. Mark each claim as read on a named site, worked out, or not found. Never fill a gap from memory.'},
    {'id': 'fl-trend', 'name': 'Trend Desk', 'what': 'What people are reading today', 'kinds': ['poc'], 'cat': 'Research', 'task': 'Content research', 'skills': ['trends', 'angles', 'timing'], 'version': '1.0', 'compat': 'Read by the minds', 'live': 'trends', 'source': 'Hacker News + Wikipedia',
     'can': ['Hacker News front page, refreshed', "Yesterday's most read Wikipedia pages", 'How to find an angle nobody took'],
     'examples': ['Find 3 angles from what is trending that fit our audience', 'What is everyone reading today that nobody tied to crypto yet?'],
     'text': 'TREND DESK. A trend is only useful with an angle: who cares, why now, what do you know that the first ten posts did not say. Check what has already been written before you write. If a trend does not fit the audience, drop it. Never tie a person or a tragedy to a coin for attention.'},
    {'id': 'fl-publish', 'name': 'Publish Desk', 'what': 'From research to a post worth sending', 'kinds': ['poc'], 'cat': 'Publishing', 'task': 'Writing and publishing', 'skills': ['hooks', 'threads', 'claims check', 'calls to action'], 'version': '1.0', 'compat': 'Read by the minds',
     'can': ['A hook, body and ask for each format', 'A last pass that removes every unbacked claim', 'A version for each channel'],
     'examples': ['Turn this research into a thread and a short post', 'Tighten this and flag anything we cannot back up'],
     'text': 'PUBLISH DESK. The first line earns the second. One idea per post. Say the concrete number, name and source. Then a last pass: remove every claim you cannot back, every promise of profit, and every word a person would not say out loud. Crypto can lose all its value and agents make mistakes: say so where it matters. Give the post for each channel asked, sized for it. Nothing is sent without its owner.'},
    {'id': 'fl-tool-page', 'name': 'Working Tool', 'what': 'Pages that do a job, not brochures', 'kinds': ['pos'], 'cat': 'Business tools', 'task': 'Business tools', 'skills': ['calculators', 'forms', 'dashboards', 'saved state'], 'version': '1.0', 'compat': 'Runs in the page',
     'can': ['A plan for inputs, logic and output', 'How to keep work when the page reloads', 'What scores as a real build'],
     'examples': ['Build a quote calculator with saved customers', 'Build a bill tracker that shows what is due this week'],
     'text': 'WORKING TOOL. Build something a person uses again: real inputs, real logic, an output that changes, and work that survives a reload through localStorage. Empty, error and full states all drawn. Pages run with no network: no fetch, no outside calls, so put sample data in the page and label it sample. Keyboard works, and it fits a 360 px phone. Split logic into small named functions. A pretty page with one button scores low however good it looks.'},
    {'id': 'fl-real-3d', 'name': 'Real Materials', 'what': 'Glass, chrome and light that look real', 'kinds': ['pos', 'poc'], 'cat': '3D', 'task': 'Realistic 3D', 'skills': ['glass', 'metal', 'lighting', 'textures', 'commercials'], 'version': '1.0', 'compat': 'Runs in the page',
     'can': ['Exact numbers for glass, water, chrome and gold', 'Three light setups that sell a product', 'Where to get free CC0 textures'],
     'examples': ['Build a glass bottle on marble with studio light', 'Make a 6 second product commercial shot'],
     'text': 'REAL MATERIALS. Use three.js MeshPhysicalMaterial with an environment map, because reflections are what make it look real. Glass: transmission 1, roughness 0.02, ior 1.5, metalness 0, thickness 0.6. Water: transmission 0.95, ior 1.33. Chrome: metalness 1, roughness 0.05. Gold: color #ffc24d, metalness 1, roughness 0.2. Car paint: clearcoat 1. A product shot: dark ground, one strong key light from above and to the side, a rim light behind, slow camera move. Keep glass away from a plain black background: it needs something to refract. Free CC0 textures: polyhaven.com and ambientcg.com. A filed page cannot load outside images, so draw textures on a canvas in the page, or use data in the file.'},
    {'id': 'fl-free-media', 'name': 'Free Media Finder', 'what': 'Real footage, pictures and generators, free to use', 'kinds': ['poc', 'pos'], 'cat': 'Video', 'task': 'Finding free media', 'skills': ['stock footage', 'public domain', 'licenses', 'image generation'], 'version': '1.0', 'compat': 'Read by the minds',
     'can': ['Public domain video and pictures from NASA', 'Openly licensed media from Openverse and Wikimedia Commons', 'Generated images from Pollinations'],
     'examples': ['Find real launch footage I can cut', 'Find a free picture for this post and say its license'],
     'text': 'FREE MEDIA FINDER. Every source here answered a real call on 2026-11-07. Video and pictures, public domain: images.nasa.gov (search, then the item page lists ~mobile.mp4 files). Pictures and audio with licenses: openverse.org. Video, pictures and audio: commons.wikimedia.org, search and filter by file type. Generated images: pollinations.ai (free, one at a time, it says no when asked too fast). Always name the source and its license next to what you use. NASA material is public domain, but never imply NASA endorses anything. Cut video in the browser with mediabunny, already on this desk. A license you could not read is a file you do not use.'},
    {'id': 'fl-short-edit', 'name': 'Shorts Editor', 'what': 'Cuts that hold people to the end', 'kinds': ['poc'], 'cat': 'Video', 'task': 'Video editing', 'skills': ['hooks', 'pacing', 'captions', 'retention'], 'version': '1.0', 'compat': 'Read by the minds',
     'can': ['A hook in the first 3 seconds', 'Pacing that fits short form', 'Text overlays people can read on a phone'],
     'examples': ['Cut this to 30 seconds with a hook and big words', 'Plan a tighter edit: where would viewers leave?'],
     'text': 'SHORTS EDITOR. Open on the payoff or the question, never on hello. Change something on screen every 2 to 4 seconds: a cut, a zoom or new words. Cut every pause and every word that repeats. Words on screen: 1 to 5 at a time, big, high contrast, away from the bottom edge where the app buttons sit. End on the point, then stop. Upright 9:16 for Shorts, Reels and TikTok. Long YouTube: promise in the first 15 seconds, a new beat every minute. You see only clip names and lengths unless you are told more, so say what you could not judge.'},
    {'id': 'fl-thumbnail', 'name': 'Thumbnail Lab', 'what': 'Images that get the click', 'kinds': ['poc'], 'cat': 'Image editing', 'task': 'Thumbnails and images', 'skills': ['thumbnails', 'contrast', 'composition', 'prompts'], 'version': '1.0', 'compat': 'Read by the minds',
     'can': ['A layout that reads at phone size', 'Three words at most', 'Image prompts that come out usable'],
     'examples': ['Three thumbnail ideas for this video', 'Write the image prompt, then the words on top'],
     'text': 'THUMBNAIL LAB. It must read at the size of a thumb. One subject, one idea, three words at most, and those words must not repeat the title. Bright subject on a dark or plain ground. Image prompt: subject, action, setting, light, lens, in that order. Never show a real named person without their permission, and never promise what the content does not deliver.'},
    {'id': 'fl-3d-stage', 'name': '3D Stage', 'what': 'A real 3D scene with no extra setup', 'kinds': ['pos', 'poc'], 'cat': '3D', 'task': 'Interactive 3D', 'skills': ['three.js', 'lighting', 'camera', 'scroll scenes'], 'version': '1.0', 'compat': 'Runs in the page',
     'can': ['Scene, light and camera rules that look good first time', 'Drag and scroll controls', 'A fallback for slow phones'],
     'examples': ['Build a 3D product stage you can spin', 'Make a scroll story where the camera moves through a city'],
     'text': 'THE 3D STAGE. Pick the React Three Fiber kit too: it brings the three.js file a page may load. One key light, one soft fill, one rim light. Fog hides the edge of the world. Use requestAnimationFrame and pause when the tab is hidden. Cap device pixel ratio at 2 and keep to a few thousand objects. If WebGL is missing, show a drawn still instead of a blank box. Respect reduced motion.'},
]
STACKS = [
    {'id': 'perp-desk', 'name': 'Perp desk', 'kind': 'pop', 'picks': ['fl-funding', 'fl-liq', 'lwcharts'], 'what': 'Funding, liquidation sums and price charts'},
    {'id': 'pick-room', 'name': 'Pick room', 'kind': 'pob', 'picks': ['fl-value', 'fl-source-check', 'echarts'], 'what': 'Prices, checked sources and a comparison chart'},
    {'id': 'coin-desk', 'name': 'Coin desk', 'kind': 'pow', 'picks': ['fl-coin-vet', 'fl-risk-desk', 'lwcharts'], 'what': 'Vetting, exits and charts. Only when you pick it'},
    {'id': 'content-room', 'name': 'Content room', 'kind': 'poc', 'picks': ['fl-trend', 'fl-source-check', 'fl-publish'], 'what': 'From what is trending to a checked post'},
    {'id': 'business-tool', 'name': 'Business tool', 'kind': 'pos', 'picks': ['fl-tool-page', 'heroui', 'echarts'], 'what': 'A working tool with real parts and charts'},
    {'id': 'commercial', 'name': '3D commercial', 'kind': 'poc', 'picks': ['fl-real-3d', 'fl-short-edit', 'three'], 'what': 'Real materials, a filmed shot, a tight edit'},
    {'id': 'yt-editor', 'name': 'YouTube editor', 'kind': 'poc', 'picks': ['fl-short-edit', 'fl-thumbnail', 'fabric'], 'what': 'Tight cuts and thumbnails that get the click'},
    {'id': 'glass-page', 'name': 'Glass landing page', 'kind': 'pos', 'picks': ['fl-real-3d', 'three', 'motion'], 'what': 'A real 3D landing page with glass and motion'},
    {'id': 'wow-page', 'name': '3D showpiece', 'kind': 'pos', 'picks': ['fl-3d-stage', 'r3f', 'motion'], 'what': 'A 3D scene with animation around it'},
]
IDS = {k['id'] for k in BOOK}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _usd(v):
    v = _f(v)
    return f'${v / 1e9:.1f}B' if v >= 1e9 else f'${v / 1e6:.1f}M' if v >= 1e6 else f'${v / 1e3:.0f}K'


def _px(v):
    v = _f(v)
    return f'${v:,.0f}' if v >= 1000 else f'${v:,.2f}' if v >= 1 else f'${v:.5f}'


def _say(text, n=96):
    return ' '.join(str(text or '').split())[:n]


def read_funding(j):
    """The most extreme funding among perps with real open interest."""
    uni, ctx = (j + [[], []])[:2] if isinstance(j, list) else ([], [])
    uni = (uni or {}).get('universe') or [] if isinstance(uni, dict) else []; rows = []
    for u, c in zip(uni, ctx or []):
        oi = _f(c.get('openInterest')) * _f(c.get('markPx'))
        if oi >= 5e6 and not u.get('isDelisted'):
            rows.append((abs(_f(c.get('funding'))), u.get('name'), _f(c.get('funding')), oi))
    rows.sort(reverse=True)
    return [f"{n} funding {r * 100:+.4f}%/h ({r * 876000:+.0f}%/yr pace), open interest {_usd(oi)}" for _a, n, r, oi in rows[:6]]


def read_liq(j, names=('BTC', 'ETH', 'SOL')):
    """Rough liquidation prices at the live mark. Maintenance is half of what the top leverage needs."""
    uni, ctx = (j + [[], []])[:2] if isinstance(j, list) else ([], [])
    uni = (uni or {}).get('universe') or [] if isinstance(uni, dict) else []; rows = []
    for u, c in zip(uni, ctx or []):
        px = _f(c.get('markPx')); top = _f(u.get('maxLeverage'))
        if u.get('name') in names and px and top:
            m = 1 / (2 * top); bits = [f"{lev}x long {_px(px * (1 - 1 / lev + m))} / short {_px(px * (1 + 1 / lev - m))}" for lev in (3, 10) if lev <= top]
            rows.append(f"{u['name']} mark {_px(px)}: " + ', '.join(bits))
    return rows


def read_markets(rows_):
    """Biggest open markets that still have a price worth reading, with what the price implies."""
    out = []
    for m in rows_ if isinstance(rows_, list) else []:
        try:
            names = json.loads(m.get('outcomes') or '[]'); px = [_f(x) for x in json.loads(m.get('outcomePrices') or '[]')]
        except (TypeError, ValueError):
            continue
        if len(names) < 2 or len(px) != len(names) or not 0.03 <= px[0] <= 0.97:
            continue
        out.append(f"{_say(m.get('question'), 70)}: {names[0]} {px[0] * 100:.0f}%, {_usd(m.get('volume24hr'))} today")
    return out[:6]


def read_games(boards):
    """Real games on the boards: who, and how it stands."""
    out = []
    for lg, j in boards:
        for e in ((j or {}).get('events') or [])[:5]:
            st = ((e.get('status') or {}).get('type') or {}).get('shortDetail') or ''
            cs = ((e.get('competitions') or [{}])[0].get('competitors')) or []
            if len(cs) == 2:
                by = {c.get('homeAway'): c for c in cs}; a, h = by.get('away') or cs[0], by.get('home') or cs[1]
                out.append(f"{lg} {(a.get('team') or {}).get('abbreviation')} {a.get('score', '')} at {(h.get('team') or {}).get('abbreviation')} {h.get('score', '')}, {_say(st, 30)}")
    return out[:8]


def read_trends(hn, wiki):
    """What is on the front page and what was most read."""
    out = [f"Hacker News: {_say(h.get('title'), 80)} ({int(_f(h.get('points')))} points)" for h in ((hn or {}).get('hits') or [])[:4]]
    arts = (((wiki or {}).get('items') or [{}])[0].get('articles')) or []
    good = [a for a in arts if ':' not in str(a.get('article')) and a.get('article') != 'Main_Page'][:4]
    return out + [f"Wikipedia: {_say(str(a.get('article')).replace('_', ' '), 60)} ({int(_f(a.get('views'))) // 1000}K reads)" for a in good]


async def _json(http, url, **kw):
    r = await http.get(url, timeout=15, headers={'User-Agent': 'FEELESS'}, **kw)
    return r.json() if r.status_code == 200 else None


async def refresh(http, root, now=None):
    """Reads the kits' fixed public addresses and keeps a few lines from each. A source that fails keeps its last read. → {key: rows}"""
    now = now or time.time(); got = {}
    async def step(key, go):
        try:
            rows_ = await go()
        except Exception as e:   # noqa: BLE001 — one dead source never stops the others
            print(f'[kits] {key}: {str(e)[:100]}')
            return
        if rows_:
            got[key] = {'at': round(now), 'rows': rows_}

    async def hl():
        r = await http.post(HL, json={'type': 'metaAndAssetCtxs'}, timeout=15)
        return r.json() if r.status_code == 200 else None
    j = None
    try:
        j = await hl()
    except Exception as e:   # noqa: BLE001
        print(f'[kits] hyperliquid: {str(e)[:100]}')
    if j:
        await step('funding', lambda: _ready(read_funding(j)))
        await step('liq', lambda: _ready(read_liq(j)))
    await step('markets', lambda: _then(_json(http, POLY), read_markets))

    async def games():
        return read_games([('NBA', await _json(http, ESPN.format('basketball/nba'))), ('NFL', await _json(http, ESPN.format('football/nfl')))])
    await step('games', games)

    async def trends():
        day = time.strftime('%Y/%m/%d', time.gmtime(now - 2 * 86400))   # the day before yesterday: yesterday's count may not be out yet
        return read_trends(await _json(http, HN), await _json(http, WIKI.format(day)))
    await step('trends', trends)
    if got:
        Path(root).mkdir(parents=True, exist_ok=True); old = load_live(root); (Path(root) / LIVE_FILE).write_text(json.dumps({**old, **got}))
    return got


async def _ready(v):
    return v


async def _then(aw, fn):
    return fn(await aw)


def load_live(root):
    try:
        d = json.loads((Path(root) / LIVE_FILE).read_text())
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def fresh(live, kit, now=None):
    """→ the kit's fresh lines, or [] when they are too old to call fresh. Pure."""
    row = (live or {}).get(kit.get('live')) or {}
    return row.get('rows') or [] if (now or time.time()) - _f(row.get('at')) <= LIVE_MAX_AGE else []


def rows(root, now=None):
    """The book as kits, each carrying its fresh numbers in the text a proof reads."""
    live = load_live(root); out = []
    for k in BOOK:
        lines = fresh(live, k, now)
        out.append({**k, 'license': 'FEELESS', 'by': 'FEELESS', 'added': True, 'fresh': lines, 'site': '', 'text': k['text'] + (f"\nFRESH NUMBERS read from {k.get('source')}, reference data: " + '; '.join(lines) + '.' if lines else '')})
    return out
