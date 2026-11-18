"""🧬 EVERY PROOF'S OWN FINGERPRINT (owner 2026-11-17: "true fingerprinting … each proof type should have unique fingerprints").

The ridge drawn on a folder used to come from its id alone, so two proofs that did the same work looked different and nothing in the print said
what the proof did. Here a proof's fingerprint is a digest of its own evidence, read by the rules of ITS kind:

  · PoB — the games, the Kalshi markets and sides, the minds' picks, the sites read
  · PoW — the coin, its sources, its entry and exit, the minds' calls
  · PoP — the market, the side, entry / stop / take, the sources
  · PoC — what was trending, the pitch, the media it made
  · PoStatic — the build's own code hash, its plan and references
  · PoEco — its sealed hash and rule

Same work → the same digest (and the same ridge); any different fact → a different one. Worked out from the folder every time, so it can never
be set by hand (like the 24-hour stamp). How new it is beside the proofs of its kind before it comes from proof_footprint.unique. Pure.
"""
import hashlib
import json
import re

import proof_footprint as _foot

CODE = {'pob': 'PoB', 'pow': 'PoW', 'pop': 'PoP', 'poc': 'PoC', 'ps': 'PoStatic', 'poe': 'PoEco'}
FOLDERS = {'pob': 'pobFolders', 'pow': 'powFolders', 'pop': 'popFolders', 'poc': 'pocFolders', 'ps': 'psFolders', 'poe': 'poeFolders'}


def _host(u):
    return re.sub(r'^www\.', '', re.sub(r'^https?://', '', str(u or '').lower()).split('/')[0])


def _picks(f):
    out = []
    for c in f.get('calls') or []:
        if isinstance(c, dict):
            for p in c.get('picks') or []:
                if isinstance(p, dict) and p.get('pick'):
                    out.append(f"{str(p['pick']).lower()[:60]}@{p.get('confidence')}")
            for k in ('market', 'side', 'pick', 'angle', 'call'):
                if c.get(k) and not isinstance(c.get(k), (dict, list)):
                    out.append(f'{k}:{str(c[k]).lower()[:60]}')
    return sorted(set(out))


def _tickets(f):
    rows = [f.get('kalshi')] + list(f.get('kalshiPicks') or [])
    out = []
    for k in rows:
        if isinstance(k, dict):
            legs = '+'.join(sorted(f"{g.get('ticker')}:{g.get('side')}" for g in k.get('legs') or []))
            out.append(legs or f"{k.get('ticker')}:{k.get('side')}")
    return sorted(set(out))


def evidence(kind, f):
    """The facts its fingerprint is made of, by the rules of its kind. Pure."""
    f = f if isinstance(f, dict) else {}
    sites = sorted(_foot.footprint(kind, f)['sites'])
    if kind == 'pob':
        return {'games': sorted(str(g.get('id')) for g in f.get('games') or [] if isinstance(g, dict) and g.get('id')), 'bets': _tickets(f), 'picks': _picks(f),
                'agreed': sorted(str(x).lower()[:60] for x in f.get('agreed') or []), 'sites': sites, 'topic': str(f.get('topic') or '').lower()[:80]}
    if kind == 'pow':
        return {'coin': str(f.get('mint') or f.get('sym') or ''), 'sources': sites, 'entry': f.get('entryPx') or f.get('buyPx'), 'exit': f.get('exitPx') or f.get('sellPx'),
                'picks': _picks(f), 'coins': sorted(str(c.get('mint') or c.get('sym')) for c in f.get('coins') or [] if isinstance(c, dict))[:8]}
    if kind == 'pop':
        return {'market': f.get('market'), 'side': f.get('side'), 'entry': f.get('entry') or f.get('entryPx'), 'stop': f.get('stop'), 'take': f.get('take'), 'sources': sites, 'picks': _picks(f)}
    if kind == 'poc':
        trends = f.get('trends') or {}
        return {'topic': str(f.get('topic') or '').lower()[:80], 'trends': sorted(str(x.get('title') if isinstance(x, dict) else x)[:60] for v in trends.values() for x in (v or [])[:5]) if isinstance(trends, dict) else [],
                'media': sorted(str((m or {}).get('id') or (m or {}).get('url') or '') for m in f.get('media') or [] if isinstance(m, dict)), 'sources': sites, 'picks': _picks(f)}
    if kind == 'ps':
        return {'code': f.get('codeSha') or f.get('sha') or hashlib.sha256(str(f.get('code') or f.get('ws') or '').encode()).hexdigest()[:16], 'plan': str(f.get('plan') or '')[:200],
                'refs': sorted(_host((r or {}).get('url')) for r in f.get('refs') or [] if isinstance(r, dict)), 'version': f.get('version')}
    if kind == 'poe':
        return {'hash': f.get('hash'), 'rule': str(f.get('rule') or f.get('topic') or '')[:120], 'net': f.get('net')}
    return {'sites': sites, 'picks': _picks(f)}


def digest(kind, f):
    """16 hex characters, from its kind and its evidence only (never its id or its time). Pure."""
    raw = json.dumps({'kind': kind, **evidence(kind, f)}, sort_keys=True, default=str, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def traits(kind, f):
    """The few words that say what this proof did, by its kind. Pure."""
    e = evidence(kind, f)
    if kind == 'pob':
        return [x for x in [f"{len(e['games'])} game{'s' if len(e['games']) != 1 else ''}" if e['games'] else '', f"{len(e['bets'])} Kalshi bet{'s' if len(e['bets']) != 1 else ''}" if e['bets'] else 'paper',
                f"{len(e['sites'])} sites", f"{len(e['agreed'])} agreed"] if x]
    if kind == 'pow':
        return [x for x in [f"coin {str(e['coin'])[:6]}" if e['coin'] else '', f"{len(e['sources'])} sources", 'traded' if e['entry'] else 'no trade'] if x]
    if kind == 'pop':
        return [x for x in [str(e['market'] or ''), str(e['side'] or ''), f"{len(e['sources'])} sources"] if x]
    if kind == 'poc':
        return [f"{len(e['trends'])} trends", f"{len(e['media'])} made", f"{len(e['sources'])} sources"]
    if kind == 'ps':
        return [f"code {e['code'][:6]}", f"{len(e['refs'])} refs"] + ([f"v{e['version']}"] if e['version'] else [])
    if kind == 'poe':
        return [f"hash {str(e['hash'] or '')[:6]}"]
    return []


def tokens(kind, f):
    """Its evidence as single facts ('sites:espn.com', 'bets:KX…:yes'), so two proofs can be compared fact by fact. Pure."""
    out = set()
    for k, v in evidence(kind, f).items():
        for x in (v if isinstance(v, list) else [v]):
            if x not in (None, '', []):
                out.add(f'{k}:{x}')
    return out


def unique(kind, f, earlier):
    """→ {pct, nearest, shared}: the share of its facts that no proof of its kind before it had (100 = all new). Pure."""
    me = tokens(kind, f); best, near = 0.0, None
    for e in list(earlier or [])[-_foot.KEEP * 3:]:
        them = tokens(kind, e)
        v = len(me & them) / len(me | them) if me and them else 0.0
        if v >= best and them:
            best, near = v, e
    shared = sorted(x.split(':', 1)[1] for x in me & tokens(kind, near) if x.startswith(('sites:', 'sources:', 'refs:')))[:4] if near else []
    return {'pct': round((1 - best) * 100), 'nearest': (near or {}).get('n'), 'shared': shared}


def of(kind, f, earlier=()):
    """→ {id, digest, kind, traits, uniquePct, nearest, shared}. Pure."""
    d = digest(kind, f); u = unique(kind, f, earlier)
    return {'id': f"{CODE.get(kind, kind)}-{d[:4].upper()}-{d[4:8].upper()}", 'digest': d, 'kind': kind, 'traits': traits(kind, f),
            'uniquePct': u['pct'], 'nearest': u['nearest'], 'shared': u['shared']}


def all_of(cat, n=30):
    """Every recent proof's fingerprint, keyed by folder id, each measured against the proofs of its own kind before it. Pure."""
    out = {}
    for kind, key in FOLDERS.items():
        rows = [f for f in (cat or {}).get(key) or [] if isinstance(f, dict) and f.get('id')]
        for f in rows[-n:]:
            out[f['id']] = of(kind, f, _foot.before(rows, f))
    return out
