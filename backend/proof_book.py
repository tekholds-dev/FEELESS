"""📚 Each agent's own SITE BOOK per proof (owner 2026-11-07: "each proof type should have its own kits, sites etc … a user can see and organize
which sites / kits per proof goes first, and the agent still chooses if repeated steps"). Pure.

book = {kind: {'order': [host, …], 'off': [host, …]}}. Untouched kinds keep the engine's own order. The owner's order goes first, an off site is
never opened, and the engine's repeat rules (sites used lately wait, a repeating window moves on) still pick among what is left."""
import re

import pow as _pow

KINDS = ('pow', 'pop', 'pob')   # the proofs whose minds browse sites. PoC and PoStatic build: their kits are picked per proof in the kit picker
DEFAULTS = {
    'pow': list(_pow.HOSTS),
    'pop': ['coinglass.com', 'hyperliquid.xyz', 'coingecko.com', 'defillama.com', 'tradingview.com', 'x.com'],
    'pob': ['espn.com', 'cbssports.com', 'actionnetwork.com', 'covers.com', 'oddsshark.com', 'rotowire.com', 'vegasinsider.com',
            'foxsports.com', 'sports.yahoo.com', 'bleacherreport.com', 'theathletic.com', 'kalshi.com', 'polymarket.com'],
}
WHAT = {'pow': 'Coin research', 'pop': 'Perps: funding, open interest, liquidations', 'pob': 'Games and markets'}
MAX = 24
MIN_ON = 2   # a proof always keeps at least two sites to read
_HOST = re.compile(r'^(?=.{4,80}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$')


def host(v):
    """'https://www.ESPN.com/nba' → 'espn.com', or '' when it is not a public host name."""
    h = re.sub(r'^[a-z]+://', '', str(v or '').strip().lower()).split('/')[0].split('?')[0].split(':')[0]
    h = h[4:] if h.startswith('www.') else h
    return h if _HOST.match(h) and not h.endswith(('.local', '.internal', '.lan')) else ''


def clean(kind, raw):
    """The owner's list for one kind → {'order', 'off'}. A coin research site must be one the PoW can open by the coin's address. → ValueError."""
    if kind not in KINDS:
        raise ValueError('Pick PoW, PoP or PoB')
    raw = raw if isinstance(raw, dict) else {}
    seen, order = set(), []
    for v in list(raw.get('order') or [])[:MAX * 2]:
        h = host(v)
        if h and h not in seen and (kind != 'pow' or h in _pow.HOSTS):
            seen.add(h); order.append(h)
    order = order[:MAX]
    off = [h for h in dict.fromkeys(host(v) for v in raw.get('off') or []) if h and h in seen]
    if len([h for h in order if h not in off]) < MIN_ON:
        raise ValueError(f'Keep at least {MIN_ON} sites on')
    return {'order': order, 'off': off}


def of(book, kind):
    b = (book or {}).get(kind) if isinstance(book, dict) else None
    return b if isinstance(b, dict) else {}


def view(book, kind):
    """Rows for the folder: the owner's order, then the defaults it has not placed. → [{host, on, mine}]"""
    b = of(book, kind); order = list(b.get('order') or []); off = set(b.get('off') or [])
    rows = order + [h for h in DEFAULTS[kind] if h not in order]
    return [{'host': h, 'on': h not in off, 'mine': h not in DEFAULTS[kind]} for h in rows]


def apply(book, kind, sites):
    """The engine's sites for one job with the owner's book on top: their on sites first in their order, then the engine's, never an off one.
    An untouched kind returns the engine's list as it was."""
    b = of(book, kind)
    if not b:
        return list(sites or [])
    off = set(b.get('off') or [])
    first = [h for h in b.get('order') or [] if h not in off]
    rest = [s for s in sites or [] if host(s) not in off and host(s) not in first]
    return first + rest


def rank(book, kind, order, keep=()):
    """A PoW round's ranked sites (repeats already rotated out by the engine): off sites dropped unless the proof requires them, the owner's
    placed sites first in their order. → list"""
    b = of(book, kind)
    if not b:
        return list(order or [])
    off = set(b.get('off') or []) - set(keep); pos = {h: i for i, h in enumerate(b.get('order') or [])}
    left = [h for h in order or [] if h not in off]
    return sorted(left, key=lambda h: (h not in keep, pos.get(h, len(pos)), left.index(h)))


def goal_line(book, kind):
    b = of(book, kind)
    if not b:
        return ''
    on = [h for h in b.get('order') or [] if h not in set(b.get('off') or [])][:6]
    off = list(b.get('off') or [])[:8]
    return (f" Your owner's sites for this proof, best first: {', '.join(on)}." if on else '') + (f" Never open {', '.join(off)}." if off else '')
