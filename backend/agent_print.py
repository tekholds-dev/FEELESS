"""🧬 THE AGENT'S FINGERPRINT (owner 2026-11-04): every proof it files teaches it what it is good and bad at. Each trait is weighed by outcome and fades with age. Contents are sealed for its owner; everyone else sees only a level. Pure."""
import math
import re

HALF_LIFE_S = 30 * 86400
KIND = {'powFolders': 'trade', 'popFolders': 'perp', 'pobFolders': 'bid', 'pocFolders': 'content'}
_STOP = {'best', 'top', 'the', 'and', 'for', 'picks', 'pick', 'good', 'this', 'next', 'week', 'today', 'tonight', 'with'}


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _size(v, cuts, names):
    return names[next((i for i, c in enumerate(cuts) if _f(v) < c), len(cuts))]


def _result(key, f):
    """+1 won, -1 lost, 0 not known."""
    if key == 'powFolders':
        return 0 if f.get('status') != 'closed' or f.get('pnlSol') is None else (1 if _f(f.get('pnlSol')) > 0 else -1)
    if key == 'popFolders':
        return 0 if f.get('status') != 'closed' or f.get('roePct') is None else (1 if _f(f.get('roePct')) > 0 else -1)
    return {'right': 1, 'wrong': -1}.get(f.get('graded'), 0)


def _traits(key, f):
    if key == 'powFolders':
        c = next((x for x in f.get('coins') or [] if x.get('mint') == f.get('mint')), {})
        return [f"source {c.get('src') or 'any'}", f"pool {_size(c.get('liq'), (20e3, 100e3), ('small', 'mid', 'deep'))}", f"cap {_size(c.get('mc'), (5e5, 1e7), ('micro', 'mid', 'large'))}"] if c else []
    if key == 'popFolders':
        return [f"market {f.get('market')}", f"side {f.get('side')}"] if f.get('market') else []
    words = [w for w in re.findall(r'[a-z0-9]+', str(f.get('topic') or '').lower()) if len(w) > 2 and w not in _STOP]
    return [f'topic {w}' for w in words[:4]]


def build(cat, now):
    """→ {level, proofs, kinds, traits: [{t, kind, score, n, won}]}: strongest and weakest are its own to read."""
    rows = {}; proofs = 0; kinds = set()
    for key, kind in KIND.items():
        for f in (cat or {}).get(key) or []:
            if f.get('noTrade') or f.get('propose'):
                continue
            res = _result(key, f); proofs += 1; kinds.add(kind)
            age = max(0.0, now - _f(f.get('soldAt') or f.get('closedAt') or f.get('at')))
            w = 0.5 ** (age / HALF_LIFE_S)
            if not res:
                continue
            for t in _traits(key, f):
                r = rows.setdefault(t, {'t': t, 'kind': kind, 'score': 0.0, 'n': 0, 'won': 0})
                r['score'] += res * w; r['n'] += 1; r['won'] += 1 if res > 0 else 0
    traits = sorted(({**r, 'score': round(r['score'], 2)} for r in rows.values()), key=lambda r: -r['score'])
    depth = sum(r['n'] for r in traits)
    level = round(100 * (1 - math.exp(-(proofs + depth / 3 + 4 * len(kinds)) / 60)))
    return {'level': level, 'proofs': proofs, 'kinds': sorted(kinds), 'traits': traits[:40]}


def public(p):
    """All anyone else ever sees."""
    return {'level': int((p or {}).get('level') or 0), 'proofs': int((p or {}).get('proofs') or 0), 'kinds': len((p or {}).get('kinds') or [])}


def note(p):
    """A short line for its next research: what its own record says. It studies this; every guard stays."""
    t = (p or {}).get('traits') or []
    good = [r['t'] for r in t if r['score'] > 0 and r['n'] >= 3][:2]; bad = [r['t'] for r in t[::-1] if r['score'] < 0 and r['n'] >= 3][:2]
    if not good and not bad:
        return ''
    return ' YOUR OWN RECORD:' + (f" strongest on {', '.join(good)}." if good else '') + (f" weakest on {', '.join(bad)}." if bad else '')
