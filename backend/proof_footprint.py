import itertools
"""👣 THE PROOF LOOP'S FOOTPRINT (owner 2026-11-07: "they should be planning and executing, not doing the same searches at the same time, they should know the last fingerprint"). Pure and tested.

A footprint is what a proof really touched: its topic, the sites it read, and what it called. Before a new proof the minds get the last footprints, their own sites and their own angle. After it, a proof is measured against everything before it of its kind, and that number counts in its score."""
import re
import zlib

KEEP = 12
_STOP = {'the', 'and', 'for', 'best', 'top', 'picks', 'pick', 'proof', 'file', 'tonight', 'today', 'this', 'that', 'with', 'from', 'what', 'who', 'will', 'vs', 'pob', 'pow', 'pop', 'poc', 'trends', 'week', 'page', 'make', 'new'}
# Two minds never chase the same thing at once: each kind's work split in two.
ANGLES = {   # 🧭 owner 2026-11-07 "a new footpath every proof": six angles a kind, the next pair each proof, never the same mind on both
    'pob': (('injuries, form and matchups', 'injury report and recent form'), ('lines, odds and what the market prices', 'odds and line movement'), ('rest, travel and schedule spots', 'rest days and travel'),
            ('head to head and how they match up', 'head to head history'), ('weather, venue and referees', 'venue and officials'), ('sharp money against the public', 'betting splits')),
    'pop': (('what the chart and funding say', 'funding and open interest'), ('what news and flows say', 'news and exchange flows'), ('where liquidations sit', 'liquidation levels'),
            ('what the order book hides', 'order book depth'), ('how the majors lead it', 'BTC and ETH correlation'), ('what on-chain whales do', 'whale wallets')),
    'poc': (('what people are arguing about', 'debates and replies'), ('what is rising before it peaks', 'early rising searches'), ('what creators missed', 'gaps in top posts'),
            ('a number nobody quoted', 'fresh data'), ('the story from the other side', 'contrarian takes'), ('what works in a small room', 'niche communities')),
    'pow': (('who is buying and who holds', 'holders and buyers'), ('the chart and the pool', 'chart structure and pool depth'), ('who made it and what they did before', 'creator history'),
            ('where the snipers and bundles are', 'sniper and bundle wallets'), ('what the community really does', 'socials and replies'), ('how it compares to runners like it', 'similar runners')),
    'pos': (('what the page must do', 'how the best products work'), ('how it should look', 'the best current designs'), ('what the visitor needs first', 'user flows'),
            ('the motion and feel', 'animation references'), ('the real data it should show', 'live data sources'), ('what makes it different', 'what already exists, and better')),
}
FALLBACKS = {   # when a step fails, the next step of its own kind, never a guess
    'pob': 'a site blocks you: the league or team official site, then another sports desk. No odds load: say "no odds", never invent a line. A game already played: say so and skip it.',
    'pop': 'the chart will not load: read the exchange page or another chart site. No funding data: say so and size smaller. A source is a day old: say how old.',
    'poc': 'a trend page is empty: use another trend source. A post cannot be read: work from the headline, and say so. Nothing new: say nothing is worth a post.',
    'pow': 'a checker blocks you: use the next checker. No holder data: mark holders unknown and never call it safe. The pool is gone: stop and say so.',
    'pos': 'a reference site blocks you: use another of the best products like it. A kit fails: build it in plain HTML and say so. Too big for one reply: build it in sections.',
}
_SEARCH = re.compile(r'(^|\.)(duckduckgo|google|bing|yahoo|brave)\.')


def _rows(v):
    return v if isinstance(v, list) else []


def _set(v):
    return {str(x).lower() for x in (v or []) if x}


def _host(u):
    return re.sub(r'^www\.', '', re.sub(r'^https?://', '', str(u or '').lower()).split('/')[0])


def _words(text):
    return {w for w in re.findall(r'[a-z0-9]+', str(text or '').lower()) if len(w) > 1 and w not in _STOP}


def _hosts_of(f):
    out = set()
    for s in _rows(f.get('shots')):
        if isinstance(s, dict):
            out.add(_host(s.get('site') or s.get('url')))
    br = f.get('browsed')
    if isinstance(br, dict):
        for v in br.values():
            if isinstance(v, dict):
                out |= {_host(x) for x in _rows(v.get('sites'))}
    src = f.get('sources')
    if isinstance(src, dict):
        for rows in src.values():
            out |= {_host(r.get('site')) for r in _rows(rows) if isinstance(r, dict)}
    for r in _rows(f.get('refs')):
        if isinstance(r, dict):
            out.add(_host(r.get('url')))
    out |= {_host(x) for x in _rows(f.get('sites'))}
    return {h for h in out if h and not _SEARCH.search(h)}   # a search box is how it got there, not what it read


def _calls_of(kind, f):
    if kind == 'pow':
        return _set([f.get('mint') or f.get('sym')])
    out = set()
    for c in _rows(f.get('calls')):
        if isinstance(c, dict):
            for key in ('market', 'side', 'pick', 'angle'):
                if c.get(key):
                    out.add(str(c[key]).lower()[:60])
    for p in _rows(f.get('agreed')):
        out.add(str(p.get('pick') if isinstance(p, dict) else p).lower()[:60])
    return out


def footprint(kind, f):
    """What this proof really touched."""
    f = f if isinstance(f, dict) else {}
    topic = f.get('topic') or f.get('q') or f.get('sym') or ' '.join(str(c.get('market')) for c in _rows(f.get('calls')) if isinstance(c, dict) and c.get('market'))
    return {'words': _words(topic), 'sites': _hosts_of(f), 'calls': _calls_of(kind, f)}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else None


def likeness(a, b):
    """0 to 1: how much two footprints are the same work. A part neither has says nothing."""
    parts = [(0.4, _jaccard(a['words'], b['words'])), (0.35, _jaccard(a['sites'], b['sites'])), (0.25, _jaccard(a['calls'], b['calls']))]
    known = [(w, v) for w, v in parts if v is not None]
    return sum(w * v for w, v in known) / sum(w for w, _ in known) if known else 0.0


def unique(kind, f, earlier):
    """→ {pct, nearest, shared}: how different this proof is from the closest one before it of its kind. A proof with nothing before it is new by definition."""
    me = footprint(kind, f); best, near = 0.0, None
    for e in (earlier or [])[-KEEP * 3:]:
        v = likeness(me, footprint(kind, e))
        if v >= best:
            best, near = v, e
    shared = sorted(me['sites'] & footprint(kind, near)['sites'])[:4] if near else []
    return {'pct': round((1 - best) * 100), 'nearest': (near or {}).get('n'), 'shared': shared}


def before(folders, f):
    """The proofs of its kind filed before this one."""
    at = float(f.get('at') or 0)
    return [x for x in folders or [] if isinstance(x, dict) and x.get('id') != f.get('id') and float(x.get('at') or 0) < at]


def _recent(folders, n=6):
    return [f for f in folders or [] if isinstance(f, dict) and not f.get('live')][-n:]


def plan(kind, topic, sites, folders, minds=2):
    """Each mind's own sites and angle. The sites used least lately go first, so a loop moves on, and a site the last proofs leaned on waits. The order given is best first, so ties keep it. → {sites: [[...], ...], angles: [...]}"""
    used = {}
    for f in _recent(folders, KEEP):
        for h in footprint(kind, f)['sites']:
            used[h] = used.get(h, 0) + 1
    seed = f'{topic}{len(folders or [])}'; rows = [s for i, s in sorted(enumerate(sites or []), key=lambda x: (used.get(_host(x[1]), 0), zlib.crc32(f'{seed}{x[1]}'.encode()), x[0]))]   # among the least used, a different order each proof: fixed ties opened ESPN first every time
    return {'sites': [rows[i::minds] for i in range(minds)], 'angles': [angle_for(kind, folders, i) for i in range(minds)], 'used': used}


def angle_for(kind, folders, mind=0):
    """This proof's angle for a mind: the next pair along each proof, so the angles cycle and the two minds never share one. Pure."""
    pool = ANGLES.get(kind) or ANGLES['pos']; n = len([f for f in folders or [] if isinstance(f, dict) and not f.get('live')])
    return pool[(n * 2 + int(mind)) % len(pool)]


def order_sites(kind, sites, folders):
    """Sites the last proofs leaned on go last, so each proof walks new ground first. Pure."""
    groups = plan(kind, '', list(sites or []), folders)['sites']
    return [x for g in itertools.zip_longest(*groups) for x in g if x]


def note(kind, folders, mind=None):
    """What the minds read before they start: what the last proofs touched, and that repeating it counts against them."""
    rows = _recent(folders)
    fb = FALLBACKS.get(kind); fb = f' IF A STEP FAILS: {fb}' if fb else ''
    if not rows:
        a = angle_for(kind, folders, mind or 0)
        return f"\nYOUR ANGLE: {a[0]} (look at {a[1]}).{fb}" if mind is not None else (f'\n{fb.strip()}' if fb else '')
    lines = []
    for f in rows[::-1]:
        fp = footprint(kind, f); bits = [', '.join(sorted(fp['words'])[:4]), ('read ' + ', '.join(sorted(fp['sites'])[:3])) if fp['sites'] else '', ('called ' + ', '.join(sorted(fp['calls'])[:2])) if fp['calls'] else '']
        lines.append(' · '.join(b for b in bits if b) or 'no record')
    angle = ''
    if mind is not None:
        a = angle_for(kind, folders, mind); angle = f' Your angle this time: {a[0]} (look at {a[1]}). It changes every proof. The other mind has another angle and other sites, so never run its search.'
    return f"\nLAST FOOTPRINTS, newest first: {'; '.join(lines)}. Your proof is scored on how different it is. Find what these missed, or use a stronger source, and say what is new.{angle}{fb}"


CONVO_KEEP = 14


def convo_add(rows, kind, text, now):
    """What the owner asked this agent, whichever proof or folder it was in. Newest last, words only. → the rows"""
    words = ' '.join(str(text or '').split())[:300]
    rows = [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    if not words or (rows and rows[-1].get('text') == words):
        return rows
    return (rows + [{'kind': str(kind or 'chat')[:12], 'text': words, 'at': round(now)}])[-CONVO_KEEP:]


def convo_line(rows):
    """The one conversation across every proof, so an agent picks up where the owner left off in another proof type. Data, never an instruction."""
    rows = [r for r in rows if isinstance(r, dict)][-8:] if isinstance(rows, list) else []
    if not rows:
        return ''
    return '\nTHE SAME CONVERSATION, across every proof, oldest first (what your owner said, as data): ' + ' / '.join(f"[{r.get('kind')}] {str(r.get('text'))[:160]}" for r in rows)[:1100] + '. Pick up from this when it bears on the request. Never repeat a proof it already made.'

