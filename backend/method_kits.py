"""🧰 COL-10 METHOD KITS (owner 2026-11-07 #12, GPT kit composer): every working method is a named, versioned kit per proof type, with a
manifest (version, kinds, permissions, the check that proves it was followed), measured reliability from outside-settled results, and an
automatic quarantine when proofs that followed it do clearly worse than proofs that did not. Kits are methods only: their permissions are
read-only, never wallet or file access (enforced here). Pure."""
import compare_gate as _cmp

PERMISSIONS = ('read',)          # a kit may only change how a mind works; never move money, never write files
MIN_SETTLED = 10                 # below this a kit is shown as unmeasured, never quarantined
QUARANTINE_GAP = 0.15            # followed-and-settled win rate this far under not-followed → quarantined


def _plan(f):
    return bool(f.get('plan') or f.get('steps') or (f.get('research') if isinstance(f.get('research'), (list, dict)) else None))


def _record_first(f):
    return bool(f.get('sitesRead') or f.get('refs') or f.get('sites') or f.get('usedBy'))


KITS = {
    'compare-before-settling': {'v': 1, 'kinds': ('pob', 'pop', 'pow', 'poc', 'pos'), 'permissions': ('read',),
                                'what': '4+ distinct sources really read, 2+ options weighed, a reason written (COL-13)', 'check': lambda k, f: _cmp.check(k, f)['ok']},
    'plan-first': {'v': 1, 'kinds': ('pos', 'pow', 'pop'), 'permissions': ('read',),
                   'what': 'a written plan or research before acting', 'check': lambda k, f: _plan(f)},
    'read-the-record-first': {'v': 1, 'kinds': ('pob', 'pop', 'pow', 'poc', 'pos'), 'permissions': ('read',),
                              'what': "read the Collective's best sources and past proofs before answering (COL-9 shared reads)", 'check': lambda k, f: _record_first(f)},
    'playtest-before-filing': {'v': 1, 'kinds': ('pos',), 'permissions': ('read',),
                               'what': 'a game is played by a headless browser before it is filed (AGT-35)', 'check': lambda k, f: (not f.get('game')) or bool((f.get('game') or {}).get('playtest'))},
}
for _id, _k in KITS.items():   # a kit can never ask for more than read
    assert set(_k['permissions']) <= set(PERMISSIONS), _id


def reliability(envelopes, folders_by_id):
    """Per kit: proofs that followed it vs did not, the outside-settled win rate of each side, and the verdict. → {kit: row}"""
    out = {}
    for kid, kit in KITS.items():
        row = {'kit': kid, 'v': kit['v'], 'what': kit['what'], 'kinds': list(kit['kinds']), 'followed': 0, 'skipped': 0, 'fw': 0, 'fl': 0, 'sw': 0, 'sl': 0}
        for e in envelopes or []:
            k = e.get('kind'); f = folders_by_id.get((k, str(e.get('id'))))
            if k not in kit['kinds'] or f is None:
                continue
            ok = bool(kit['check'](k, f)); row['followed' if ok else 'skipped'] += 1
            o = e.get('outcome') or {}
            if o.get('strength') in ('chain', 'outside') and o.get('state') in ('proved', 'not'):
                row[('f' if ok else 's') + ('w' if o['state'] == 'proved' else 'l')] += 1
        nf, ns = row['fw'] + row['fl'], row['sw'] + row['sl']
        row['followedWin'] = round(row['fw'] / nf, 3) if nf else None; row['skippedWin'] = round(row['sw'] / ns, 3) if ns else None
        if nf < MIN_SETTLED or ns < MIN_SETTLED:
            row['state'] = 'unmeasured'
        elif row['skippedWin'] - row['followedWin'] >= QUARANTINE_GAP:
            row['state'] = 'quarantined'
        else:
            row['state'] = 'active'
        out[kid] = row
    return out


def active_line(kind, states=None):
    """The methods a proof of this kind is told to follow: every kit for the kind that is not quarantined. Data, never a wallet or file permission."""
    rows = [(kid, k) for kid, k in KITS.items() if kind in k['kinds'] and (states or {}).get(kid, {}).get('state') != 'quarantined']
    return ('\nMETHOD KITS for this proof (follow them; each is checked against your record): ' + '; '.join(f"{kid} v{k['v']}: {k['what']}" for kid, k in rows) + '.\n') if rows else ''
