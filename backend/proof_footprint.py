"""👣 THE PROOF LOOP'S FOOTPRINT (owner 2026-11-07: "they should be planning and executing, not doing the same searches at the same time, they should know the last fingerprint"). Pure and tested.

A footprint is what a proof really touched: its topic, the sites it read, and what it called. Before a new proof the minds get the last footprints, their own sites and their own angle. After it, a proof is measured against everything before it of its kind, and that number counts in its score."""
import re

KEEP = 12
_STOP = {'the', 'and', 'for', 'best', 'top', 'picks', 'pick', 'proof', 'file', 'tonight', 'today', 'this', 'that', 'with', 'from', 'what', 'who', 'will', 'vs', 'pob', 'pow', 'pop', 'poc', 'trends', 'week', 'page', 'make', 'new'}
# Two minds never chase the same thing at once: each kind's work split in two.
ANGLES = {
    'pob': (('injuries, form and matchups', 'injury report and recent form'), ('lines, odds and what the market prices', 'odds and line movement')),
    'pop': (('what the chart and funding say', 'funding and open interest'), ('what news and flows say', 'news and exchange flows')),
    'poc': (('what people are arguing about', 'debates and replies'), ('what is rising before it peaks', 'early rising searches')),
    'pow': (('who is buying and who holds', 'holders and buyers'), ('the chart and the pool', 'chart structure and pool depth')),
    'pos': (('what the page must do', 'how the best products work'), ('how it should look', 'the best current designs')),
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
    rows = [s for i, s in sorted(enumerate(sites or []), key=lambda x: (used.get(_host(x[1]), 0), x[0]))]
    angles = ANGLES.get(kind) or ANGLES['pos']
    return {'sites': [rows[i::minds] for i in range(minds)], 'angles': [angles[i % len(angles)] for i in range(minds)], 'used': used}


def note(kind, folders, mind=None):
    """What the minds read before they start: what the last proofs touched, and that repeating it counts against them."""
    rows = _recent(folders)
    if not rows:
        return ''
    lines = []
    for f in rows[::-1]:
        fp = footprint(kind, f); bits = [', '.join(sorted(fp['words'])[:4]), ('read ' + ', '.join(sorted(fp['sites'])[:3])) if fp['sites'] else '', ('called ' + ', '.join(sorted(fp['calls'])[:2])) if fp['calls'] else '']
        lines.append(' · '.join(b for b in bits if b) or 'no record')
    angle = ''
    if mind is not None:
        a = (ANGLES.get(kind) or ANGLES['pos'])[int(mind) % 2]; angle = f' Your angle this time: {a[0]}. The other mind has the other angle and other sites, so never run its search.'
    return f"\nLAST FOOTPRINTS, newest first: {'; '.join(lines)}. Your proof is scored on how different it is. Find what these missed, or use a stronger source, and say what is new.{angle}"
