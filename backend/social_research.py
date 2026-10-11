"""🔎 SOCIAL / WEBSITE RESEARCH — the narrative packet for the agents' strongest candidates. No paid API, no X API.

One shared worker (the service's `_research_tick`) reads ONLY the top few candidates after the cheap screen, through the local headless
Chromium that Playwright installed on this Mac (rendered DOM, `--dump-dom`), each run in a THROWAWAY profile (no cookies, no login,
nothing stored). READ ONLY: it never clicks, posts, follows or signs in.

Order per coin: the links the coin already carries (website · X · Telegram — from Jupiter / Pump / the board), then ONE bounded web search
(DuckDuckGo's plain HTML page) only when the coin carries no link at all. Everything below `fetch_dom` is pure and tested on fixtures.

EVIDENCE, NEVER PROSE: every claim in the packet carries its proof — `evidence` = one item per source kind (🌐 website · 𝕏 X · 🚀 launch page ·
💬 Telegram · 💻 GitHub · ⚖️ legal / entity · 📄 terms / docs · 🛡 audit), each FOUND / NOT FOUND / UNKNOWN with the source URL, when it was
fetched, the page title / account name, the direct mint match (YES / NO / UNKNOWN, with the exact launch mint and the address the source
showed) and a short excerpt. Legal / entity evidence is read ONLY from pages the project itself links (one bounded fetch) and is graded
NONE · WEAK · PARTIAL — STRONG would need a public-registry confirmation, which is never performed here, so it is never claimed. A legal
page, terms or an audit link is a FACT about the website, never a verdict about the token: no "legit", "official" or "verified" label exists.

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
    """Every Solana-address-shaped string in the page's VISIBLE text (deduped, page order) — mixed case with a digit, never pure hex
    (build hashes / EVM-style ids in scripts and attributes were read as "another contract" on 2026-10-10). A match is a CLAIM."""
    out = []
    for m in MINT_RE.findall(text or ''):
        if re.fullmatch(r'[0-9a-fA-F]+', m) or not (re.search(r'[a-z]', m) and re.search(r'[A-Z]', m) and re.search(r'[1-9]', m)):
            continue
        out.append(m)
    return list(dict.fromkeys(out))


def links_in(html):
    """{x: [handles], tg: [groups], hrefs: [...]} from every href on the page."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html or '', re.I)
    xs = [m.group(1) for h in hrefs for m in [X_RE.match(h)] if m and m.group(1).lower() not in X_SKIP]
    tgs = [m.group(1) for h in hrefs for m in [TG_RE.match(h)] if m]
    return {'x': list(dict.fromkeys(xs)), 'tg': list(dict.fromkeys(tgs)), 'hrefs': hrefs[:200]}


GH_RE = re.compile(r'https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]{1,39})(?:/[A-Za-z0-9_.-]+)?/?(?:[?#]|$)', re.I)
AUDITORS = ('certik', 'hacken', 'solidproof', 'sourcehat', 'cyberscope', 'interfi', 'peckshield', 'halborn', 'ottersec', 'osec.io', 'zellic', 'neodyme', 'sec3', 'trailofbits', 'quillaudits', 'coinsult')
DOC_KINDS = {'legal': r'\b(legal|imprint|impressum|disclaimer)\b', 'terms': r'\b(terms|tos|terms[- ]of[- ](?:service|use)|conditions)\b', 'privacy': r'\bprivacy\b',
             'docs': r'\b(docs|documentation|whitepaper|white[- ]paper|litepaper|gitbook)\b', 'audit': r'\baudit(?:s|ed| report)?\b'}
ENTITY_RE = re.compile(r"(?:©|\(c\)|copyright)\s*(?:\d{4}(?:\s*[-–]\s*\d{4})?\s*)?((?:[A-Z][A-Za-z0-9&'.-]*\s){0,5}(?:Inc\.?|LLC|L\.L\.C\.|Ltd\.?|Limited|Corp\.?|Corporation|GmbH|AG|S\.A\.|SAS|B\.V\.|Pte\.?\s?Ltd\.?|Foundation|Labs|Holdings|DAO LLC))")
JURIS_RE = re.compile(r"(?:governed by|construed in accordance with|subject to)\s+(?:and construed in accordance with\s+)?the laws of\s+(?:the\s+)?([A-Z][A-Za-z .'-]{2,40}?)(?=[,.;)]|\s+(?:without|excluding|with|as))|(?:incorporated|registered|organi[sz]ed)\s+(?:in|under the laws of)\s+(?:the\s+)?([A-Z][A-Za-z .'-]{2,30}?)(?=[,.;)]|\s+(?:with|under|as))")
REG_RE = re.compile(r"(?:company|registration|reg\.?|incorporation|business|entity|corporate)\s*(?:no\.?|number|nr\.?|#|id)\s*[:.]?\s*([A-Z]{0,4}[0-9][A-Z0-9-]{3,19})", re.I)


def _abs(base, h):
    from urllib.parse import urljoin
    try:
        u = urljoin(base or '', h or '')
    except ValueError:
        return None
    return u if u.startswith(('http://', 'https://')) else None


def doc_links(html, base):
    """Every link on the page that points at proof of who is behind it → {github, legal, terms, privacy, docs, audit: [absolute urls]}.
    A link is classified by its URL and its visible anchor text; only http(s) links count."""
    out = {k: [] for k in ('github', 'legal', 'terms', 'privacy', 'docs', 'audit')}
    for href, inner in re.findall(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or ''):
        u = _abs(base, _html.unescape(href))
        if not u:
            continue
        label = (_text(inner) + ' ' + u).lower()
        if GH_RE.match(u):
            out['github'].append(u)
            continue
        if any(a in u.lower() for a in AUDITORS):
            out['audit'].append(u)
            continue
        for k, rx in DOC_KINDS.items():
            if re.search(rx, label):
                out[k].append(u)
                break
    return {k: list(dict.fromkeys(v))[:3] for k, v in out.items()}


def excerpt(text, needle, pad=60):
    """A short verbatim slice of the visible text around `needle` (the proof a reader can find on the page), or None."""
    t = text or ''
    i = t.find(needle) if needle else -1
    if i < 0:
        return None
    return ('…' if i > pad else '') + t[max(0, i - pad):i + len(needle) + pad].strip() + ('…' if i + len(needle) + pad < len(t) else '')


def entity_read(text):
    """⚖️ What a page's visible text SAYS about a legal entity → {entity, jurisdiction, regRef, excerpt} (None where the page says nothing).
    A claim on the project's own page — never checked against a registry here."""
    t = text or ''
    em = ENTITY_RE.search(t)
    jm = JURIS_RE.search(t)
    rm = REG_RE.search(t)
    ent = re.sub(r'\s+', ' ', em.group(1)).strip(' .,') if em else None
    jur = (jm.group(1) or jm.group(2)).strip(' .,') if jm else None
    reg = rm.group(1) if rm else None
    ex = excerpt(t, em.group(0)) if em else excerpt(t, jm.group(0)) if jm else excerpt(t, rm.group(0)) if rm else None
    return {'entity': ent, 'jurisdiction': jur, 'regRef': reg, 'excerpt': ex[:200] if ex else None}


def legal_read(html, url, mint=None):
    """📄 One legal / terms page the project links → {url, reachable, title, entity, jurisdiction, regRef, excerpt, mintShown}."""
    if not html:
        return {'url': url, 'reachable': False, 'title': None, 'entity': None, 'jurisdiction': None, 'regRef': None, 'excerpt': None, 'mintShown': False}
    title = (re.search(r'(?is)<title[^>]*>(.*?)</title>', html) or [None, None])[1]
    txt = _text(html)
    return {'url': url, 'reachable': True, 'title': _html.unescape(title.strip())[:140] if title else None, **entity_read(txt[:20000]), 'mintShown': bool(mint and mint in txt)}


LEGAL_LEVELS = ('NONE', 'WEAK', 'PARTIAL', 'STRONG')


def legal_level(site, legal):
    """⚖️ → {level, labels, entity, jurisdiction, regRef, sources, mintConnection, confidence, note}. Factual labels only:
    ENTITY FOUND · ENTITY NOT VERIFIED · TERMS FOUND · REGISTRATION NUMBER SHOWN · AUDIT DOCUMENT FOUND · NO PUBLIC LEGAL EVIDENCE FOUND.
    NONE = nothing · WEAK = a terms / privacy / legal link, or an entity named only in the site footer · PARTIAL = a linked legal page names an
    entity AND a jurisdiction or registration number. STRONG needs a public-registry confirmation — never performed here, never claimed."""
    s, lg = site or {}, legal or {}
    docs = s.get('docs') or {}
    ent = lg.get('entity') or (s.get('entityClaim') or {}).get('entity')
    jur, reg = lg.get('jurisdiction'), lg.get('regRef')
    labels, src = [], []
    if not s.get('reachable'):
        return {'level': 'NONE', 'labels': ['NO PUBLIC LEGAL EVIDENCE FOUND'] if s.get('url') else [], 'entity': None, 'jurisdiction': None, 'regRef': None, 'sources': [],
                'mintConnection': 'unknown', 'confidence': None, 'note': 'no reachable website' if s.get('url') else 'no website to read'}
    if docs.get('terms') or docs.get('privacy') or docs.get('legal'):
        labels.append('TERMS FOUND')
        src += (docs.get('legal') or []) + (docs.get('terms') or []) + (docs.get('privacy') or [])
    if ent:
        labels += ['ENTITY FOUND', 'ENTITY NOT VERIFIED']
    if reg:
        labels.append('REGISTRATION NUMBER SHOWN')
    if docs.get('audit'):
        labels.append('AUDIT DOCUMENT FOUND')
        src += docs['audit']
    if lg.get('url') and lg.get('reachable'):
        src = [lg['url']] + [u for u in src if u != lg['url']]
    level = 'PARTIAL' if ent and (jur or reg) and lg.get('reachable') else 'WEAK' if (ent or labels) else 'NONE'
    if level == 'NONE':
        labels = ['NO PUBLIC LEGAL EVIDENCE FOUND']
    conf = {'NONE': 0, 'WEAK': 25, 'PARTIAL': 50}[level]
    return {'level': level, 'labels': list(dict.fromkeys(labels)), 'entity': ent, 'jurisdiction': jur, 'regRef': reg, 'sources': list(dict.fromkeys(src))[:4],
            'mintConnection': 'mint shown on the legal page' if lg.get('mintShown') else 'the legal page does not show this mint' if lg.get('reachable') else 'unknown',
            'confidence': conf, 'note': 'claims on the project\'s own pages — no public registry was checked; legal paperwork does not make a token safe'}


def site_read(html, url, mint):
    """🌐 What a coin's website shows → {url, reachable, title, description, mints, mintShown, mintMatch, x, tg, text}."""
    if not html:
        return {'url': url, 'reachable': False, 'title': None, 'description': None, 'mints': [], 'mintShown': False, 'mintMatch': 'unknown', 'x': [], 'tg': [], 'text': ''}
    title = (re.search(r'(?is)<title[^>]*>(.*?)</title>', html) or [None, None])[1]
    txt = _text(html)
    ms = mints_in(txt)   # visible text only — never script / style / attribute hashes
    ln = links_in(html)
    match = 'yes' if mint and mint in ms else ('no' if ms else 'unknown')   # a page showing ONLY other addresses = a mismatch claim
    shown = mint if mint and mint in ms else (ms[0] if ms else None)
    return {'url': url, 'reachable': True, 'title': _html.unescape(title.strip())[:140] if title else None,
            'description': (_meta(html, 'og:description', 'description', 'twitter:description') or '')[:280] or None,
            'mints': ms[:6], 'mintShown': bool(mint and mint in ms), 'mintMatch': match, 'x': ln['x'][:4], 'tg': ln['tg'][:3], 'text': txt[:2000],
            'mintExcerpt': (excerpt(txt, shown) or '')[:200] or None, 'docs': doc_links(html, url), 'entityClaim': entity_read(txt[-4000:])}


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
    st = next((h for h in links_in(html)['hrefs'] if re.search(r'/status/\d+', h)), None)   # the direct link of the newest visible post (proof of activity)
    return {'url': url, 'available': bool(name or bio or posts), 'name': name, 'bio': (bio or '')[:280] or None, 'followers': _count(fol.group(1)) if fol else None,
            'following': _count(fng.group(1)) if fng else None, 'posts': posts, 'lastPostAt': last, 'mintMentioned': bool(mint and mint in (html or '')), 'website': web,
            'postUrl': None if not st else ('https://x.com' + st if st.startswith('/') else st)}


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


def narrative_sources(cls, srcs):
    """Which sources SUPPORT a narrative class → [{source, url, keywords}] (each source whose own text matches that class's words)."""
    rx = _WORDS.get(cls)
    if not rx:
        return []
    out = []
    for label, url, text in srcs:
        hits = list(dict.fromkeys(re.findall(rx, str(text or '').lower())))
        if hits:
            out.append({'source': label, 'url': url, 'keywords': hits[:4]})
    return out[:5]


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
    links_x = None if not (handle and s.get('reachable') and site_x) else (handle.lower() in site_x)   # a site that links NO X is unknown, never "a different X"
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


EVIDENCE_KINDS = (('website', '🌐 Website'), ('x', '𝕏 X'), ('launch', '🚀 Launch page'), ('telegram', '💬 Telegram'), ('github', '💻 GitHub'),
                  ('legal', '⚖️ Legal / entity'), ('terms', '📄 Terms / docs'), ('audit', '🛡 Audit'))
LAUNCH_PAGES = {'pump': 'https://pump.fun/coin/{mint}', 'bonk': 'https://letsbonk.fun/token/{mint}'}


def _mm(v):
    return {'yes': 'YES', 'no': 'NO'}.get(str(v or '').lower(), 'UNKNOWN')


def evidence(row, site, x, legal, now, tg=None):
    """🧾 One proof item per source kind → [{kind, label, status FOUND | NOT FOUND | UNKNOWN, url, fetchedAt, title, mintMatch YES | NO | UNKNOWN,
    launchMint, sourceMint, excerpt, confidence, note}]. `fetchedAt` is set only for a page this worker really opened; a link that was only
    LISTED on another page says so in `note`. Missing evidence is UNKNOWN — never NOT FOUND unless the place it would be was read."""
    r, s, xx, lg = row or {}, site or {}, x or {}, legal or {}
    mint = r.get('mint')
    docs = s.get('docs') or {}
    read_site = bool(s.get('reachable'))
    base = lambda kind: {'kind': kind, 'label': dict(EVIDENCE_KINDS)[kind], 'status': 'UNKNOWN', 'url': None, 'fetchedAt': None, 'title': None, 'mintMatch': 'UNKNOWN',
                         'launchMint': mint, 'sourceMint': None, 'excerpt': None, 'confidence': None, 'note': None}
    out = []
    w = base('website')
    if s.get('url'):
        w.update(url=s['url'], fetchedAt=now, status='FOUND' if read_site else 'NOT FOUND', title=s.get('title'), mintMatch=_mm(s.get('mintMatch')),
                 sourceMint=(mint if s.get('mintShown') else (s.get('mints') or [None])[0]), excerpt=s.get('mintExcerpt') or (s.get('description') or None),
                 confidence=90 if s.get('mintMatch') == 'yes' else 10 if s.get('mintMatch') == 'no' else 50 if read_site else None,
                 note=None if read_site else 'the link did not load (maybe temporary)')
    else:
        w['note'] = 'the coin carries no website link'
    out.append(w)
    e = base('x')
    if xx.get('url'):
        posts = xx.get('posts') or []
        e.update(url=xx['url'], fetchedAt=now, status='FOUND' if xx.get('available') else 'UNKNOWN', title=xx.get('name'), mintMatch='YES' if xx.get('mintMentioned') else 'UNKNOWN',
                 sourceMint=mint if xx.get('mintMentioned') else None, excerpt=((posts[0].get('text') if posts else None) or xx.get('bio')),
                 confidence=None if not xx.get('available') else 70 if xx.get('mintMentioned') else 40,
                 note=('latest visible post ' + time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(xx['lastPostAt']))) if xx.get('lastPostAt') else
                      ('the profile page showed only a login wall to a signed-out browser' if not xx.get('available') else 'no post timestamp visible signed-out'))
    else:
        e['note'] = 'the coin carries no X link'
    e['lastPostAt'] = xx.get('lastPostAt')
    e['postUrl'] = xx.get('postUrl')
    out.append(e)
    ln = base('launch')
    pad = next((k for k in LAUNCH_PAGES if str(mint or '').endswith(k)), None)
    if pad:
        ln.update(status='FOUND', url=LAUNCH_PAGES[pad].format(mint=mint), mintMatch='YES', sourceMint=mint, confidence=100,
                  note=f'the launch mint ends in "{pad}" — that launchpad\'s own page for this exact mint (link derived from the mint, not opened)')
    else:
        ln['note'] = 'the launchpad cannot be read from the mint'
    out.append(ln)
    t = base('telegram')
    tgs = [f'https://t.me/{g}' for g in (s.get('tg') or [])] or ([tg] if isinstance(tg, str) and tg.startswith('http') else [])
    if tgs:
        t.update(status='FOUND', url=tgs[0], note='listed on the coin\'s own links (not opened)' if not s.get('tg') else 'linked from the website (not opened)')
    elif read_site:
        t.update(status='NOT FOUND', note='the website links no Telegram')
    out.append(t)
    g = base('github')
    if docs.get('github'):
        g.update(status='FOUND', url=docs['github'][0], note='linked from the website (not opened)')
    elif read_site:
        g.update(status='NOT FOUND', note='the website links no GitHub')
    out.append(g)
    lv = legal_level(s, lg)
    lgi = base('legal')
    lgi.update(status='FOUND' if lv['level'] in ('PARTIAL', 'STRONG') or lv['entity'] else 'NOT FOUND' if read_site else 'UNKNOWN', url=(lv['sources'] or [None])[0],
               fetchedAt=now if lg.get('reachable') else None, title=lg.get('title') or lv['entity'], excerpt=lg.get('excerpt') or (s.get('entityClaim') or {}).get('excerpt'),
               confidence=lv['confidence'], note=f"{lv['level']} · " + ' · '.join(lv['labels']) + (f" · {lv['entity']}" if lv['entity'] else '') + (f" · {lv['jurisdiction']}" if lv['jurisdiction'] else '')
               + (f" · reg. {lv['regRef']}" if lv['regRef'] else ''), mintMatch='YES' if lg.get('mintShown') else 'UNKNOWN')
    out.append(lgi)
    tm = base('terms')
    tu = (docs.get('terms') or docs.get('legal') or docs.get('privacy') or docs.get('docs') or [None])[0]
    if tu:
        tm.update(status='FOUND', url=tu, fetchedAt=now if lg.get('url') == tu and lg.get('reachable') else None, title=lg.get('title') if lg.get('url') == tu else None,
                  note='opened and read' if lg.get('url') == tu and lg.get('reachable') else 'linked from the website (not opened)')
    elif read_site:
        tm.update(status='NOT FOUND', note='the website links no terms, privacy, legal or docs page')
    out.append(tm)
    au = base('audit')
    if docs.get('audit'):
        au.update(status='FOUND', url=docs['audit'][0], note='AUDIT DOCUMENT FOUND — linked from the website (not opened; an audit never guarantees safety)')
    elif read_site:
        au.update(status='NOT FOUND', note='the website links no audit')
    out.append(au)
    return out


def packet(row, site, x, now, tg=None, search=None, legal=None):
    """One compact packet per researched coin: IDENTITY · WEBSITE · X / SOCIAL · CROSS-CHECK · NARRATIVE (+ the sources behind it) · LEGAL ·
    EVIDENCE (one proof item per source kind) · freshness · when."""
    r = row or {}
    srcs = [('coin name / ticker', None, f"{r.get('name') or ''} {r.get('symbol') or ''}")]
    if site:
        srcs += [('website title + description', site.get('url'), f"{site.get('title') or ''} {site.get('description') or ''}"), ('website text', site.get('url'), (site.get('text') or '')[:800])]
    if x:
        srcs += [('X bio', x.get('url'), x.get('bio')), ('X posts', x.get('url'), ' '.join(p.get('text') or '' for p in x.get('posts') or []))]
    cls, conf, kw = narrative(r.get('name'), r.get('symbol'), *[t for _, _, t in srcs[1:]])
    cc = crosscheck(r.get('mint'), r.get('x'), site, x)
    ev = evidence(r, site, x, legal, now, tg)
    return {'at': now, 'mint': r.get('mint'), 'symbol': r.get('symbol'), 'identity': {'name': r.get('name'), 'symbol': r.get('symbol'), 'mint': r.get('mint'),
            'launchpad': (r.get('launch') or {}).get('pad'), 'stage': (r.get('launch') or {}).get('type')},
            'website': None if not site else {k: site.get(k) for k in ('url', 'reachable', 'title', 'description', 'mintShown', 'mintMatch', 'mints', 'mintExcerpt', 'x', 'tg', 'docs')},
            'x': None if not x else {k: x.get(k) for k in ('url', 'available', 'name', 'bio', 'followers', 'following', 'lastPostAt', 'mintMentioned', 'website', 'postUrl')} | {'posts': (x.get('posts') or [])[:3]},
            'tg': tg, 'search': (search or [])[:5], 'cross': {**cc, 'launchMint': r.get('mint'), 'sourceMint': (site or {}).get('mints', [None])[0] if (site or {}).get('mints') else None,
                                                               'sourceUrl': (site or {}).get('url')},
            'narrative': {'class': cls, 'confidence': conf, 'keywords': kw, 'sources': narrative_sources(cls, srcs)},
            'legal': legal_level(site, legal), 'evidence': ev,
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
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(exe, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
                                                    f'--user-data-dir={prof}', '--virtual-time-budget=6000', '--dump-dom', str(url),
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        return out.decode('utf-8', 'replace')[:1_500_000] if out else None
    except Exception:   # timeout / cancel / crash: the WHOLE browser (its own process group: renderers too) goes, never left running
        return None
    finally:
        if proc is not None and proc.returncode is None:
            _kill_group(proc.pid)
        shutil.rmtree(prof, ignore_errors=True)


def _kill_group(pid):
    import signal
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _etime_sec(s):
    """ps etime ([[dd-]hh:]mm:ss) → seconds."""
    d, _, rest = str(s).strip().rpartition('-')
    parts = [int(x) for x in rest.split(':')]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(d) if d else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def orphans(ps_lines, older_than=2 * FETCH_SEC):
    """PIDs of research browsers (our throwaway-profile marker in the command line) running longer than `older_than` — e.g. left by a
    backend restart in the middle of a fetch. Pure: `ps_lines` = 'pid etime args' rows."""
    out = []
    for ln in ps_lines or []:
        bits = str(ln).split(None, 2)
        if len(bits) == 3 and 'feeless-research-' in bits[2] and bits[0].isdigit():
            try:
                if _etime_sec(bits[1]) > older_than:
                    out.append(int(bits[0]))
            except ValueError:
                continue
    return out


def reap_orphans():
    """Kill every research browser older than 2 × FETCH_SEC (called before each research job). → how many."""
    import subprocess
    try:
        lines = subprocess.run(['ps', '-Ao', 'pid,etime,args'], capture_output=True, text=True, timeout=5).stdout.splitlines()[1:]
    except Exception:
        return 0
    pids = orphans(lines)
    for pid in pids:
        _kill_group(pid)
        try:
            os.kill(pid, 9)
        except OSError:
            pass
    return len(pids)


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
    legal = None
    lk = None if not (site or {}).get('reachable') else next(iter(((site.get('docs') or {}).get('legal') or []) + ((site.get('docs') or {}).get('terms') or []) + ((site.get('docs') or {}).get('privacy') or [])), None)
    if lk:   # ⚖️ ONE bounded read: the legal / terms page the project itself links (never a registry, never a crawl)
        h = await fetch(lk); n += 1
        legal = legal_read(h, lk, r.get('mint'))
    p = packet(r, site, x, now, tg=r.get('tg'), search=search, legal=legal)
    p['failed'] = bool((r.get('site') or r.get('x')) and not ((site or {}).get('reachable') or (x or {}).get('available')))
    p['requests'] = n
    return p, n
