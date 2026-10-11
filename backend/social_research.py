"""🔎 SOCIAL / WEBSITE RESEARCH — the narrative packet for the agents' strongest candidates. No paid API, no X API.

One shared worker (the service's `_research_tick`) reads ONLY the top few candidates after the cheap screen, through the local headless
Chromium that Playwright installed on this Mac (rendered DOM, `--dump-dom`), each run in a THROWAWAY profile (no cookies, no login,
nothing stored). READ ONLY: it never clicks, posts, follows or signs in.

Order per coin: the links the coin already carries (website · X · Telegram — from Jupiter / Pump / the board), then ONE bounded web search
(DuckDuckGo's plain HTML page) only when the coin carries no link at all. Everything below `fetch_dom` is pure and tested on fixtures.

The packet feeds the desks as CONTEXT: Sherlock reads the narrative + identity, Devil may WARN (conflicting mint, impersonation, dead site),
the Warden may only SHRINK a seat on weak identity, never grow one on hype. Missing social data is UNKNOWN — never a veto."""
import asyncio
import html as _html
import os
import re
import shutil
import tempfile
import time

TTL = {'site': 20 * 60, 'social': 8 * 60, 'fail': 3 * 60, 'search': 30 * 60}
PER_PASS = 3                 # coins researched per agent pass (strongest only)
FETCH_SEC = 14.0
ACTIVE_H = 48.0              # newest visible post within 48h = ACTIVE
NARRATIVES = ('MEME', 'ANIMAL', 'AI / TECH', 'CELEBRITY / PERSON', 'EVENT / NEWS', 'POLITICAL', 'COMMUNITY', 'UTILITY / PROJECT', 'COPYCAT / DERIVATIVE', 'TREND PARODY', 'UNKNOWN')
FRESH = ('ACTIVE', 'STALE', 'UNAVAILABLE', 'UNKNOWN')
_WORDS = {
    'ANIMAL': r'\b(dog|doge|inu|shib|pup|puppy|cat|kitty|meow|frog|pepe|toad|monkey|ape|bear|bull|fish|penguin|hamster|goat|duck|bird|wolf|fox|panda|capybara)\b',
    'AI / TECH': r'\b(ai|agi|gpt|llm|agent|agents|neural|robot|bot|quantum|chip|compute|tech|protocol|blockchain|defi)\b',
    'CELEBRITY / PERSON': r'\b(elon|musk|snoop|drake|kanye|taylor|mrbeast|tate|speed|ishowspeed|ceo|founder|rapper|actor|singer|streamer)\b',
    'POLITICAL': r'\b(trump|maga|biden|harris|president|election|vote|congress|senate|politic\w*|government|usa|america)\b',
    'EVENT / NEWS': r'\b(breaking|news|today|announced|launch event|world cup|olympics|halloween|christmas|election day|war|earthquake|record)\b',
    'COMMUNITY': r'\b(community|cto|holders|fam|together|movement|army|cult|raid|join us|telegram)\b',
    'UTILITY / PROJECT': r'\b(utility|roadmap|staking|dapp|platform|app|tool|whitepaper|tokenomics|ecosystem|swap|bridge|nft)\b',
    'COPYCAT / DERIVATIVE': r'\b(2\.0|v2|baby|mini|son of|wife of|the real|official|classic|reborn|returns)\b',
    'TREND PARODY': r'\b(parody|satire|meme of|joke|ironic|not financial advice|lol|lmao)\b',
    'MEME': r'\b(meme|memecoin|moon|degen|pump|wagmi|gm|hodl|send it|lfg|based|chad|wojak)\b',
}
# a base58 Solana address: 32–44 chars, no 0 O I l
MINT_RE = re.compile(r'(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])')
X_RE = re.compile(r'https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})(?:[/?#]|$)', re.I)
TG_RE = re.compile(r'https?://(?:t\.me|telegram\.me)/([A-Za-z0-9_+]{3,64})', re.I)
X_SKIP = {'home', 'intent', 'share', 'search', 'i', 'hashtag', 'explore', 'login', 'signup', 'settings', 'tos', 'privacy'}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _text(html):
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', html or '')
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', _html.unescape(t)).strip()


def _meta(html, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(n) + r'["\'][^>]*content=["\']([^"\']*)["\']', html or '', re.I) \
            or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']' + re.escape(n) + r'["\']', html or '', re.I)
        if m and m.group(1).strip():
            return _html.unescape(m.group(1).strip())
    return None


def mints_in(text):
    """Every Solana-address-shaped string on the page (deduped, page order). Pure regex: a match is a CLAIM the page makes."""
    return list(dict.fromkeys(MINT_RE.findall(text or '')))


def links_in(html):
    """{x: [handles], tg: [groups], hrefs: [...]} from every href on the page."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html or '', re.I)
    xs = [m.group(1) for h in hrefs for m in [X_RE.match(h)] if m and m.group(1).lower() not in X_SKIP]
    tgs = [m.group(1) for h in hrefs for m in [TG_RE.match(h)] if m]
    return {'x': list(dict.fromkeys(xs)), 'tg': list(dict.fromkeys(tgs)), 'hrefs': hrefs[:200]}


def site_read(html, url, mint):
    """🌐 What a coin's website shows → {url, reachable, title, description, mints, mintShown, mintMatch, x, tg, text}."""
    if not html:
        return {'url': url, 'reachable': False, 'title': None, 'description': None, 'mints': [], 'mintShown': False, 'mintMatch': 'unknown', 'x': [], 'tg': [], 'text': ''}
    title = (re.search(r'(?is)<title[^>]*>(.*?)</title>', html) or [None, None])[1]
    txt = _text(html)
    ms = mints_in(html)
    ln = links_in(html)
    match = 'yes' if mint and mint in ms else ('no' if ms else 'unknown')   # a page showing ONLY other addresses = a mismatch claim
    return {'url': url, 'reachable': True, 'title': _html.unescape(title.strip())[:140] if title else None,
            'description': (_meta(html, 'og:description', 'description', 'twitter:description') or '')[:280] or None,
            'mints': ms[:6], 'mintShown': bool(mint and mint in ms), 'mintMatch': match, 'x': ln['x'][:4], 'tg': ln['tg'][:3], 'text': txt[:2000]}


def _count(s):
    s = str(s or '').replace(',', '').strip().upper()
    m = re.match(r'([\d.]+)\s*([KM]?)', s)
    if not m:
        return None
    return int(_f(m.group(1)) * {'K': 1e3, 'M': 1e6}.get(m.group(2), 1))


def x_read(html, url, mint, now=None):
    """🐦 What the public X profile page shows when rendered without a login → {url, available, name, bio, followers, following, posts:
    [{text, at}], lastPostAt, mintMentioned, website}. X often shows only a login wall to a signed-out browser: that is UNAVAILABLE
    (never a bad sign about the coin)."""
    if not html or re.search(r'(?i)(log in to x|sign in to x|something went wrong|this account doesn.t exist|account suspended)', _text(html)[:3000]) and not _meta(html, 'og:title'):
        return {'url': url, 'available': False, 'name': None, 'bio': None, 'followers': None, 'following': None, 'posts': [], 'lastPostAt': None, 'mintMentioned': False, 'website': None}
    name = _meta(html, 'og:title') or None
    bio = _meta(html, 'og:description', 'description')
    times = [t for t in re.findall(r'<time[^>]+datetime=["\']([^"\']+)["\']', html or '')]
    tw = re.findall(r'(?is)<div[^>]+data-testid=["\']tweetText["\'][^>]*>(.*?)</div>', html or '')
    posts = [{'text': _text(t)[:200], 'at': _iso(times[i]) if i < len(times) else None} for i, t in enumerate(tw[:5])]
    fol = re.search(r'([\d.,]+\s*[KM]?)\s*Followers', _text(html), re.I)
    fng = re.search(r'([\d.,]+\s*[KM]?)\s*Following', _text(html), re.I)
    web = next((h for h in links_in(html)['hrefs'] if h.startswith('http') and not X_RE.match(h) and 't.co/' not in h), None)
    last = max([p['at'] for p in posts if p['at']] or [_iso(t) for t in times if _iso(t)] or [None]) if (posts or times) else None
    return {'url': url, 'available': bool(name or bio or posts), 'name': name, 'bio': (bio or '')[:280] or None, 'followers': _count(fol.group(1)) if fol else None,
            'following': _count(fng.group(1)) if fng else None, 'posts': posts, 'lastPostAt': last, 'mintMentioned': bool(mint and mint in (html or '')), 'website': web}


def _iso(s):
    import datetime as _dt
    try:
        return _dt.datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return None


def search_read(html):
    """🔍 DuckDuckGo's plain HTML results → [{title, url}] (the result links only)."""
    out = []
    for href, title in re.findall(r'(?is)<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or ''):
        u = _html.unescape(href)
        m = re.search(r'uddg=([^&]+)', u)
        if m:
            from urllib.parse import unquote
            u = unquote(m.group(1))
        out.append({'title': _text(title)[:120], 'url': u})
    return out[:10]


def narrative(name, symbol, *texts):
    """→ (class, confidence 0–1, keywords). Keyword counts over the name, ticker and the pages read; nothing found = UNKNOWN, 0."""
    blob = ' '.join([str(name or ''), str(symbol or '')] + [str(t or '') for t in texts]).lower()
    nm = f"{name or ''} {symbol or ''}".lower()
    score = {}
    kw = {}
    for k, rx in _WORDS.items():
        hits = re.findall(rx, blob)
        if hits:
            score[k] = len(hits) + 3 * len(re.findall(rx, nm))   # the coin's own name weighs most
            kw[k] = list(dict.fromkeys(hits))[:4]
    if not score:
        return 'UNKNOWN', 0.0, []
    best = max(score, key=lambda k: score[k])
    tot = sum(score.values())
    return best, round(min(0.95, score[best] / tot * min(1.0, score[best] / 4)), 2), kw[best]


def freshness(x, now):
    """ACTIVE (a visible post within 48h) · STALE (older) · UNAVAILABLE (page could not be read signed-out) · UNKNOWN (no X link at all)."""
    if not x:
        return 'UNKNOWN'
    if not x.get('available'):
        return 'UNAVAILABLE'
    last = x.get('lastPostAt')
    if not last:
        return 'UNKNOWN'
    return 'ACTIVE' if _f(now) - _f(last) <= ACTIVE_H * 3600 else 'STALE'


def crosscheck(mint, row_x, site, x):
    """🧾 Identity: website mint vs the launch mint, X mint vs the launch mint, the site links the same X, the X links the same site,
    conflicting addresses, a possible copycat. → {mintMatch, xMintMatch, siteLinksX, xLinksSite, conflict, copycat, confidence 0–100, flags}"""
    s, xx = site or {}, x or {}
    flags = []
    handle = (X_RE.match(row_x or '') or [None, None])[1] if row_x else None
    site_x = [h.lower() for h in s.get('x') or []]
    links_x = None if not (handle and s.get('reachable')) else (handle.lower() in site_x)
    x_site = xx.get('website')
    links_site = None if not (x_site and s.get('url')) else (_host(x_site) == _host(s.get('url')))
    conflict = bool(s.get('mints')) and mint not in (s.get('mints') or []) and s.get('mintMatch') == 'no'
    if conflict:
        flags.append(f"the website shows another contract ({(s.get('mints') or ['?'])[0][:6]}…), not this mint")
    if links_x is False:
        flags.append(f"the website links a different X ({', '.join('@' + h for h in (s.get('x') or [])[:2]) or 'none'})")
    if links_site is False:
        flags.append('the X profile links a different website')
    if s.get('url') and s.get('reachable') is False:
        flags.append('the website is unreachable (dead link — maybe temporary)')
    conf = 50
    conf += 25 if s.get('mintMatch') == 'yes' else -35 if conflict else 0
    conf += 10 if links_x else -15 if links_x is False else 0
    conf += 10 if links_site else -10 if links_site is False else 0
    conf += 5 if xx.get('mintMentioned') else 0
    conf -= 10 if s.get('url') and s.get('reachable') is False else 0
    if not s.get('url') and not xx.get('url'):
        conf = None   # nothing to judge: unknown, never low
    return {'mintMatch': s.get('mintMatch') or 'unknown', 'xMintMatch': 'yes' if xx.get('mintMentioned') else 'unknown', 'siteLinksX': links_x, 'xLinksSite': links_site,
            'conflict': conflict, 'copycat': conflict or links_x is False, 'confidence': None if conf is None else max(0, min(100, conf)), 'flags': flags}


def _host(u):
    m = re.match(r'https?://([^/]+)', str(u or ''), re.I)
    return (m.group(1).lower().removeprefix('www.')) if m else None


def packet(row, site, x, now, tg=None, search=None):
    """One compact packet per researched coin: IDENTITY · WEBSITE · X / SOCIAL · CROSS-CHECK · NARRATIVE · freshness · when."""
    r = row or {}
    cls, conf, kw = narrative(r.get('name'), r.get('symbol'), (site or {}).get('title'), (site or {}).get('description'), (site or {}).get('text', '')[:800],
                              (x or {}).get('bio'), ' '.join(p.get('text') or '' for p in (x or {}).get('posts') or []))
    cc = crosscheck(r.get('mint'), r.get('x'), site, x)
    return {'at': now, 'mint': r.get('mint'), 'symbol': r.get('symbol'), 'identity': {'name': r.get('name'), 'symbol': r.get('symbol'), 'mint': r.get('mint'),
            'launchpad': (r.get('launch') or {}).get('pad'), 'stage': (r.get('launch') or {}).get('type')},
            'website': None if not site else {k: site.get(k) for k in ('url', 'reachable', 'title', 'description', 'mintShown', 'mintMatch', 'x', 'tg')},
            'x': None if not x else {k: x.get(k) for k in ('url', 'available', 'name', 'bio', 'followers', 'following', 'lastPostAt', 'mintMentioned', 'website')} | {'posts': (x.get('posts') or [])[:3]},
            'tg': tg, 'search': (search or [])[:5], 'cross': cc, 'narrative': {'class': cls, 'confidence': conf, 'keywords': kw},
            'social': freshness(x, now) if x is not None else ('UNKNOWN' if not r.get('x') else 'UNAVAILABLE'),
            'warnings': list(cc['flags'])}


def due(cache, mint, now):
    """Is this coin's packet due for (re)research? Fresh packet → no; a failed read waits TTL['fail']; website identity TTL['site'],
    the social half TTL['social']."""
    p = (cache or {}).get(mint)
    if not p:
        return True
    age = _f(now) - _f(p.get('at'))
    if p.get('failed'):
        return age >= TTL['fail']
    return age >= TTL['social']


def pick(cases, cache, now, n=PER_PASS):
    """The strongest candidates that are due — the ONLY coins the browser ever opens (cleared first, then the strongest read)."""
    return [c for c in sorted(cases or [], key=lambda c: (not c.get('cleared'), -_f(c.get('lean')))) if _f(c.get('lean')) > 0 and due(cache, c.get('mint'), now)][:n]


def chrome_path():
    """The headless Chromium Playwright installed on this Mac (newest), or None."""
    base = os.path.expanduser('~/Library/Caches/ms-playwright')
    try:
        dirs = sorted((d for d in os.listdir(base) if d.startswith('chromium_headless_shell-')), key=lambda d: int(d.rsplit('-', 1)[-1]), reverse=True)
    except (OSError, ValueError):
        return None
    for d in dirs:
        for sub in ('chrome-headless-shell-mac-arm64', 'chrome-headless-shell-mac-x64', 'chrome-headless-shell-linux64'):
            p = os.path.join(base, d, sub, 'chrome-headless-shell')
            if os.path.exists(p):
                return p
    return None


async def fetch_dom(url, timeout=FETCH_SEC):
    """The rendered DOM of one page through local headless Chromium in a THROWAWAY profile (deleted after; no cookies, no login).
    http(s) only. → html or None. Tests never call this."""
    exe = chrome_path()
    if not exe or not re.match(r'^https?://', str(url or ''), re.I):
        return None
    prof = tempfile.mkdtemp(prefix='feeless-research-')
    try:
        proc = await asyncio.create_subprocess_exec(exe, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
                                                    f'--user-data-dir={prof}', '--virtual-time-budget=6000', '--dump-dom', str(url),
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return None
        return out.decode('utf-8', 'replace')[:1_500_000] if out else None
    except Exception:
        return None
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def search_url(q):
    from urllib.parse import quote_plus
    return 'https://html.duckduckgo.com/html/?q=' + quote_plus(q)


async def research(row, fetch=fetch_dom, now=None, cache_search=None):
    """One coin: its own links first (website · X), ONE search only when it carries no link. → (packet, requests made). `fetch` is
    injected (tests hand in fixtures)."""
    now = now or time.time()
    r = row or {}
    n = 0
    site = x = None
    search = None
    if r.get('site'):
        h = await fetch(r['site']); n += 1
        site = site_read(h, r['site'], r.get('mint'))
    if r.get('x'):
        h = await fetch(r['x']); n += 1
        x = x_read(h, r['x'], r.get('mint'), now)
    if not r.get('site') and not r.get('x') and r.get('mint') and not (cache_search or {}).get(r['mint']):
        h = await fetch(search_url(f"\"{r['mint']}\"")); n += 1
        search = search_read(h)
        site_hit = next((s['url'] for s in search if s['url'].startswith('http') and not X_RE.match(s['url']) and 'dexscreener' not in s['url'] and 'pump.fun' not in s['url']), None)
        x_hit = next((s['url'] for s in search if X_RE.match(s['url'])), None)
        if site_hit:
            h = await fetch(site_hit); n += 1
            site = site_read(h, site_hit, r.get('mint'))
        if x_hit:
            x = {'url': x_hit, 'available': False, 'name': None, 'bio': None, 'followers': None, 'following': None, 'posts': [], 'lastPostAt': None, 'mintMentioned': False, 'website': None}
    p = packet(r, site, x, now, tg=r.get('tg'), search=search)
    p['failed'] = bool((r.get('site') or r.get('x')) and not ((site or {}).get('reachable') or (x or {}).get('available')))
    p['requests'] = n
    return p, n
