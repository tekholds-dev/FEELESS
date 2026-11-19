"""🧬 SLICE 3 · POSTATIC UNIQUENESS (owner: "every proof type and filing were to create a new footprint and to never do the same shit twice";
VISION › PoStatic › Unique). Every build is fingerprinted against ALL past builds (every agent's PoStatics, every folder but its own):
a near-copy is refused before it files. And every build starts from a NEW brief: code (never the model) picks a centrepiece and a layout
no recent build used, and never a pair any past build had, so the minds cannot hand back their favourite page every time.

A fingerprint is what a visitor would call "the same page": the words, the shape of the markup, the colours, its layout and its
centrepiece. Pure: page HTML in, numbers out."""
import hashlib
import re
import zlib

VERSION = 1
KEEP = 64         # hashes kept per part (the smallest ones: the same sample for every page, so two pages compare fairly)
COPY_AT = 0.72    # likeness at or above this to any past build = a near-copy (calibrated on real PoStatics 2026-11-18)
RECENT = 3        # a centrepiece or layout any of the last 3 builds had is not briefed again

CENTRES = {   # id → (what the minds read, words in an ask it fits)
    '3d': ('a live 3D scene (three.js) the visitor can turn or scroll through', ('3d', 'scene', 'model', 'product', 'object', 'world', 'space', 'sculpture')),
    'candles': ('a live price chart with candles (Lightweight Charts + the FEELESS candle index)', ('price', 'chart', 'candle', 'trading', 'sol', 'coin', 'token', 'market')),
    'datachart': ('one big interactive data chart (Recharts) that answers the main question', ('data', 'chart', 'compare', 'turnover', 'volume', 'stats', 'trend', 'dashboard')),
    'map': ('an interactive map with markers (Leaflet)', ('map', 'where', 'city', 'place', 'local', 'travel', 'store', 'venue', 'route')),
    'tool': ('a working calculator or form at the centre: inputs in, a result that changes, saved on the device', ('tool', 'calculator', 'form', 'planner', 'quote', 'estimate', 'converter', 'tracker')),
    'table': ('a live, sortable table or leaderboard the visitor filters', ('table', 'list', 'rank', 'leaderboard', 'pools', 'compare', 'top', 'directory')),
    'numbers': ('a wall of big live numbers that count up and change', ('live', 'stats', 'numbers', 'kpi', 'metrics', 'counter', 'pulse')),
    'story': ('a scroll story: the main idea told in steps as the visitor scrolls', ('story', 'explain', 'explainer', 'how', 'guide', 'learn', 'history', 'why')),
}
LAYOUTS = {
    'bento': 'a bento grid: tiles of different sizes, the centrepiece in the biggest tile',
    'split': 'a split screen: the centrepiece fills one half, words and controls the other',
    'sidebar': 'an app shell: a left sidebar of tools, the centrepiece in the work area',
    'scroll': 'a long scroll in full-height chapters, each with its own background',
    'magazine': 'a magazine page: a big headline, columns of text, pull quotes around the centrepiece',
    'stage': 'a full-bleed stage: the centrepiece edge to edge behind the words, a slim bar of controls',
    'cards': 'a rail of cards that scroll sideways under a short hero',
    'console': 'a terminal-like console: dense panels, monospace numbers, a status bar',
}
_WORD = re.compile(r'[a-z0-9]{2,}')
_BLOCK = ('header', 'nav', 'main', 'section', 'article', 'aside', 'footer', 'form', 'canvas', 'svg', 'table', 'ul', 'ol', 'h1', 'h2', 'h3', 'button', 'input', 'select', 'img', 'video', 'dl', 'figure')
_TAG = re.compile(r'<(' + '|'.join(_BLOCK) + r')\b', re.I)
_HEX = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')


def _strip(h):
    h = re.sub(r'<script type="module" id="feeless-models">.*?</script>', ' ', str(h or ''), flags=re.S)   # the studio piece's own code is the same on every page that has one
    return h


def _text(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.I | re.S))).lower()


def _sample(items):
    return sorted({zlib.crc32(x.encode()) for x in items})[:KEEP]


def _shingles(seq, n):
    return [' '.join(seq[i:i + n]) for i in range(max(0, len(seq) - n + 1))] or ([' '.join(seq)] if seq else [])


def _hexes(h):
    out = {}
    for m in _HEX.finditer(h):
        v = m.group(1).lower(); v = ''.join(c * 2 for c in v) if len(v) == 3 else v
        out[v] = out.get(v, 0) + 1
    return sorted(out, key=lambda k: -out[k])[:12]


def layout_of(html):
    """The layout a page says it has (data-feeless-layout), else read from its code. → (id, 'said' | 'read')"""
    h = str(html or ''); m = re.search(r'data-feeless-layout=["\']([a-z]+)', h)
    if m and m.group(1) in LAYOUTS:
        return m.group(1), 'said'
    low = h.lower(); secs = len(re.findall(r'<section\b', low))
    if re.search(r'\bbento\b|grid-template-areas', low):
        return 'bento', 'read'
    if re.search(r'<aside\b|class="[^"]*sidebar', low):
        return 'sidebar', 'read'
    if re.search(r'monospace|jetbrains mono|class="[^"]*\b(console|terminal)\b', low) and re.search(r'status', low):
        return 'console', 'read'
    if re.search(r'column-count|<article\b[\s\S]*<article\b[\s\S]*<article\b|blockquote', low):
        return 'magazine', 'read'
    if re.search(r'overflow-x:\s*auto|scroll-snap-type:\s*x|grid-auto-flow:\s*column', low):
        return 'cards', 'read'
    if re.search(r'grid-template-columns:\s*(1fr\s+1fr|repeat\(2,)|md:grid-cols-2|lg:grid-cols-2', low):
        return 'split', 'read'
    if secs >= 5 or re.search(r'min-height:\s*100vh|h-screen|scroll-snap-type:\s*y', low):
        return 'scroll', 'read'
    return 'stage', 'read'


def centre_of(html):
    """The centrepiece a page says it has (data-feeless-centre), else read from its code. → (id, 'said' | 'read')"""
    h = str(html or ''); m = re.search(r'data-feeless-centre=["\']([a-z0-9]+)', h)
    if m and m.group(1) in CENTRES:
        return m.group(1), 'said'
    for cid, rx in (('3d', r'THREE\.WebGLRenderer|data-feeless-model='), ('candles', r'LightweightCharts\.createChart'), ('map', r'\bL\.map\('),
                    ('datachart', r'Recharts|new Chart\(|echarts\.init|d3\.select'), ('tool', r'<form\b'), ('table', r'<table\b'),
                    ('numbers', r'data-n=|count-?up|requestAnimationFrame\([^)]*count')):
        if re.search(rx, h):
            return cid, 'read'
    return 'story', 'read'


def fingerprint(html):
    """🧬 → {v, text, struct, palette, layout, centre, hash}, or None for no page. Pure."""
    h = _strip(html)
    if len(h) < 40:
        return None
    words = _WORD.findall(_text(h)); tags = [t.lower() for t in _TAG.findall(re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.I | re.S))]
    return {'v': VERSION, 'text': _sample(_shingles(words, 4)), 'struct': _sample(_shingles(tags, 5)), 'palette': _hexes(h),
            'layout': layout_of(h)[0], 'centre': centre_of(h)[0], 'hash': hashlib.sha256(h.encode()).hexdigest()[:16]}


def _jac(a, b):
    a, b = set(a or []), set(b or [])
    return len(a & b) / len(a | b) if a and b else 0.0


def likeness(a, b):
    """0..1: how much two pages are the same page. Identical code = 1. A part neither page has (no colours in either) says nothing. Pure."""
    if not a or not b:
        return 0.0
    if a.get('hash') and a.get('hash') == b.get('hash'):
        return 1.0
    parts = [(0.4, a.get('text'), b.get('text')), (0.3, a.get('struct'), b.get('struct')), (0.1, a.get('palette'), b.get('palette'))]
    known = [(w, _jac(x, y)) for w, x, y in parts if x or y] + [(0.1, float(a.get('layout') == b.get('layout'))), (0.1, float(a.get('centre') == b.get('centre')))]
    return round(sum(w * v for w, v in known) / sum(w for w, _ in known), 3)


def nearest(pr, past):
    """The closest past build. past = [{n, ws, print}] (other folders only). → {like, n, ws, layout, centre} or None"""
    best = None
    for p in past or []:
        v = likeness(pr, p.get('print'))
        if best is None or v > best['like']:
            best = {'like': v, 'n': p.get('n'), 'ws': p.get('ws'), 'layout': (p.get('print') or {}).get('layout'), 'centre': (p.get('print') or {}).get('centre')}
    return best


def gate(pr, past):
    """Is this page a near-copy of any past build? → {copy, like, nearest, ws, layout, centre}. Pure."""
    n = nearest(pr, past) or {'like': 0.0, 'n': None, 'ws': None}
    return {'copy': bool(pr) and n['like'] >= COPY_AT, 'like': n['like'], 'nearest': n.get('n'), 'ws': n.get('ws'),
            'layout': n.get('layout'), 'centre': n.get('centre')}


def _fit(cid, words):
    return sum(1 for w in CENTRES[cid][1] if w in words)


def brief(ask, past_briefs, seed=''):
    """🆕 This build's brief: a centrepiece that fits the ask and a layout, neither used by the last RECENT builds, and never a pair any past
    build had. past_briefs = [{centre, layout}] oldest first (every past PoStatic). → {id, centre, layout, new: True}. Pure."""
    words = set(_WORD.findall(str(ask or '').lower())); rows = [b for b in past_briefs or [] if isinstance(b, dict)]
    pairs = {(b.get('centre'), b.get('layout')) for b in rows}; recent = rows[-RECENT:]
    no_c = {b.get('centre') for b in recent}; no_l = {b.get('layout') for b in recent}
    key = lambda x: zlib.crc32(f'{seed}{ask}{x}{len(rows)}'.encode())   # among equals, a different order each build
    cs = sorted(CENTRES, key=lambda c: (c in no_c, -_fit(c, words), key(c)))
    ls = sorted(LAYOUTS, key=lambda lay: (lay in no_l, key(lay)))
    pick = next(((c, lay) for c in cs for lay in ls if (c, lay) not in pairs), (cs[0], ls[0]))
    bid = hashlib.sha256(f'{ask}|{pick[0]}|{pick[1]}|{len(rows)}|{seed}'.encode()).hexdigest()[:10]
    return {'id': bid, 'centre': pick[0], 'layout': pick[1], 'new': (pick[0], pick[1]) not in pairs}


def brief_line(b, near=None):
    """What the build minds read: the centrepiece and layout code chose for this build (and, on a retry, what it was too close to)."""
    if not b:
        return ''
    out = (f"\nTHIS BUILD'S BRIEF (new, chosen so no past build looks like it): the centrepiece is {CENTRES[b['centre']][0]}; the layout is "
           f"{LAYOUTS[b['layout']]}. Mark them in the code: data-feeless-centre=\"{b['centre']}\" on the centrepiece element and "
           f"data-feeless-layout=\"{b['layout']}\" on <main>. Choose your own fonts, colours and words for this ask; reuse nothing from another page.")
    if near:
        out += (f"\nTOO CLOSE: your last try was {round(near['like'] * 100)}% like PoStatic #{near.get('nearest')} (an earlier build). Write it again from a blank "
                'page with this brief: different words, a different structure and a different palette.')
    return out


def record(b, pr, g):
    """🧾 The uniqueness row a filed PoStatic carries. → {brief, layout, centre, like, nearest, copy, briefKept}"""
    lay, cen = (pr or {}).get('layout'), (pr or {}).get('centre')
    return {'brief': b.get('id') if b else None, 'briefNew': bool(b and b.get('new')), 'want': {'centre': (b or {}).get('centre'), 'layout': (b or {}).get('layout')},
            'layout': lay, 'centre': cen, 'like': (g or {}).get('like', 0.0), 'nearest': (g or {}).get('nearest'), 'copy': bool((g or {}).get('copy')),
            'nearestPair': [(g or {}).get('centre'), (g or {}).get('layout')] if (g or {}).get('nearest') is not None else None,
            'briefKept': bool(b) and lay == b.get('layout') and cen == b.get('centre')}
