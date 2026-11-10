"""⚖ COL-13 COMPARE BEFORE SETTLING (owner 2026-11-10: "always do what's best and smart"). A proof may only settle on its pick after it really
compared: at least NEED distinct sources read (each host once; a site that would not open does not count), at least 2 options weighed, and a
reason written. Enforced where an agent settles by itself with no real money (PoB bids, PoP practice trades): a thin pick goes back for more
research. Real-money PoW is recorded, never blocked (owner's money path unchanged); its grade still sees the number.

Measured from what the folder itself recorded, so nobody can claim it: data, never a mind's word. Pure."""
from urllib.parse import urlparse

NEED = 4
NEED_OPTIONS = 2
ENFORCED = ('pob', 'pop')   # settles by itself with no real money


def _host(x):
    s = str(x or '').strip().lower()
    if not s:
        return ''
    h = urlparse(s if '//' in s else '//' + s).netloc or s
    return h.split('@')[-1].split(':')[0].removeprefix('www.')


def sources(folder):
    """Distinct hosts the proof really read: its own sites, sites read that opened, refs, browser notes' sites, snapshot sites."""
    f = folder or {}; out = set()
    for s in f.get('sites') or []:
        out.add(_host(s))
    for r in f.get('sitesRead') or []:
        if isinstance(r, dict) and r.get('ok'):
            out.add(_host(r.get('host')))
    for r in f.get('refs') or []:
        if isinstance(r, dict):
            out.add(_host(r.get('url')))
    for n in (f.get('browsed') or {}).values():
        for s in (n or {}).get('sites') or []:
            out.add(_host(s))
    for sh in f.get('shots') or []:
        if isinstance(sh, dict):
            out.add(_host(sh.get('site')))
    for row in (f.get('usedBy') or {}).values():
        for s in row or []:
            out.add(_host(s))
    out.discard('')
    return sorted(out)


def options(folder):
    """How many alternatives were on the table: board markets, coins, picks or calls."""
    f = folder or {}
    return max(len(f.get('board') or []), len(f.get('coins') or []), len(f.get('picks') or []), len(f.get('games') or []), len(f.get('calls') or []))


def check(kind, folder):
    """→ {'sources': n, 'hosts': [...], 'options': n, 'reason': bool, 'ok': bool, 'enforced': bool, 'why': str}"""
    f = folder or {}; hosts = sources(f); opts = options(f)
    said = lambda c: [c.get('why'), c.get('reason'), *[(p or {}).get('why') or (p or {}).get('reason') for p in c.get('picks') or [] if isinstance(p, dict)]]
    reason = any(str(x or '').strip() for c in f.get('calls') or [] if isinstance(c, dict) for x in said(c)) or bool(str(f.get('why') or f.get('report') or '').strip())
    missing = []
    if len(hosts) < NEED:
        missing.append(f'compared {len(hosts)} of {NEED} sources')
    if opts < NEED_OPTIONS:
        missing.append(f'weighed {opts} of {NEED_OPTIONS} options')
    if not reason:
        missing.append('no reason written')
    return {'sources': len(hosts), 'hosts': hosts[:12], 'options': opts, 'reason': reason, 'ok': not missing, 'enforced': kind in ENFORCED,
            'why': '; '.join(missing)}
