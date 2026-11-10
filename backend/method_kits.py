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


def reliability(envelopes, folders_by_id, extra=None):
    """Per kit: proofs that followed it vs did not, the outside-settled win rate of each side, and the verdict. → {kit: row}"""
    out = {}
    for kid, kit in all_kits(extra).items():
        row = {'kit': kid, 'v': kit['v'], 'what': kit['what'], 'kinds': list(kit['kinds']), 'followed': 0, 'skipped': 0, 'fw': 0, 'fl': 0, 'sw': 0, 'sl': 0, 'rfp': 0, 'rfn': 0, 'rsp': 0, 'rsn': 0}
        for e in envelopes or []:
            k = e.get('kind'); f = folders_by_id.get((k, str(e.get('id'))))
            if k not in kit['kinds'] or f is None:
                continue
            ok = bool(kit['check'](k, f)); row['followed' if ok else 'skipped'] += 1
            o = e.get('outcome') or {}
            rv = (f.get('review') or {}).get('verdict')   # 🧑‍⚖️ OSSY + G4's review: a fast second signal, shown, never used to quarantine
            if rv in ('pass', 'fail'):
                row[('rf' if ok else 'rs') + ('p' if rv == 'pass' else 'n')] += 1
            if o.get('strength') in ('chain', 'outside') and o.get('state') in ('proved', 'not'):
                row[('f' if ok else 's') + ('w' if o['state'] == 'proved' else 'l')] += 1
        nf, ns = row['fw'] + row['fl'], row['sw'] + row['sl']
        row['followedWin'] = round(row['fw'] / nf, 3) if nf else None; row['skippedWin'] = round(row['sw'] / ns, 3) if ns else None
        rf_, rs_ = row['rfp'] + row['rfn'], row['rsp'] + row['rsn']
        row['followedReview'] = round(row['rfp'] / rf_, 3) if rf_ else None; row['skippedReview'] = round(row['rsp'] / rs_, 3) if rs_ else None
        if nf < MIN_SETTLED or ns < MIN_SETTLED:
            row['state'] = 'unmeasured'
        elif row['skippedWin'] - row['followedWin'] >= QUARANTINE_GAP:
            row['state'] = 'quarantined'
        else:
            row['state'] = 'active'
        out[kid] = row
    return out


def active_line(kind, states=None, extra=None):
    """The methods a proof of this kind is told to follow: every kit for the kind that is not quarantined. Data, never a wallet or file permission."""
    rows = [(kid, k) for kid, k in all_kits(extra).items() if kind in k['kinds'] and (states or {}).get(kid, {}).get('state') != 'quarantined']
    return ('\nMETHOD KITS for this proof (follow them; each is checked against your record): ' + '; '.join(f"{kid} v{k['v']}: {k['what']}" for kid, k in rows) + '.\n') if rows else ''


# ── 🧪 COL-10 rest (2026-11-10): kits the Collective proposes from its own reviews, approved by the owner, then measured like the rest ──
import json as _json
import time as _time

EXTRA_FILE = 'method_kits_extra.json'
LOG_FILE = 'method_kits_log.jsonl'
PROPOSE_MIN = 4          # reviewed proofs of a kind before a weak check can become a proposal
PROPOSE_FAIL = 0.6       # a rubric check failed this often → propose a kit for it


def _check_failed(f, i):
    """Did the reviewers fail rubric check i on this folder? None when nobody graded it. Pure."""
    by = ((f.get('review') or {}).get('by') or {}).values()
    marks = [str((v.get('checks') or [None] * 5)[i] or '') for v in by if len(v.get('checks') or []) > i]
    marks = [m for m in marks if m[:1] in ('✓', '✗')]
    return None if not marks else any(m.startswith('✗') for m in marks)


def load_extra(root):
    try:
        return _json.loads((root / EXTRA_FILE).read_text())
    except (OSError, ValueError):
        return {}


def all_kits(extra=None):
    """The built-in kits plus the approved proposals. A proposal's check: the reviewers passed that rubric check. Read-only, always."""
    out = dict(KITS)
    for kid, e in (extra or {}).items():
        i = int(e['check'])
        out[kid] = {'v': e.get('v', 1), 'kinds': (e['kind'],), 'permissions': ('read',), 'what': e['what'], 'proposed': True,
                    'check': (lambda k, f, i=i: _check_failed(f, i) is False)}
    return out


def proposals(cats, rubric, extra=None):
    """Per kind, the rubric checks OSSY + G4 fail most across every agent's reviewed proofs. → rows to approve. Pure."""
    import mission
    have = {(e['kind'], int(e['check'])) for e in (extra or {}).values()}; rows = []
    for k, (_c, key) in mission.KINDS.items():
        folders = [f for c in cats for f in c.get(key) or [] if (f.get('review') or {}).get('by')]
        for i, what in enumerate(rubric.get(k) or []):
            seen = [x for x in (_check_failed(f, i) for f in folders) if x is not None]
            if len(seen) < PROPOSE_MIN or (k, i) in have:
                continue
            rate = sum(seen) / len(seen)
            if rate >= PROPOSE_FAIL:
                rows.append({'id': f'fix-{k}-{i + 1}', 'kind': k, 'check': i, 'what': what.split('. ', 1)[-1], 'failRate': round(rate, 2), 'seen': len(seen)})
    return sorted(rows, key=lambda r: -r['failRate'])


def approve(root, row, now=None):
    """The owner's yes: the proposal becomes a kit every proof of its kind is told to follow. Read-only by construction."""
    ex = load_extra(root)
    ex[row['id']] = {'kind': row['kind'], 'check': int(row['check']), 'what': f"pass the reviewers' check: {row['what']}", 'v': 1, 'approvedAt': round(now or _time.time())}
    root.mkdir(parents=True, exist_ok=True); (root / EXTRA_FILE).write_text(_json.dumps(ex, indent=1))
    return ex


def log_changes(root, prev, new, now=None):
    """Every kit whose state moved (unmeasured → active → quarantined and back) is one line in the history: the rollback record."""
    last = {}   # the last state each kit was logged at: a restart empties memory, so memory alone re-logged every kit (seen live 2026-11-10)
    try:
        for line in (root / LOG_FILE).read_text().splitlines():
            x = _json.loads(line); last[x['kit']] = x['to']
    except (OSError, ValueError, KeyError):
        pass
    was = lambda k: (prev.get(k) or {}).get('state') or last.get(k) or 'unmeasured'
    rows = [{'kit': k, 'from': was(k), 'to': r.get('state'), 'at': round(now or _time.time())} for k, r in (new or {}).items() if was(k) != r.get('state')]
    if rows:
        try:
            with (root / LOG_FILE).open('a') as fh:
                for r in rows:
                    fh.write(_json.dumps(r) + '\n')
        except OSError:
            pass
    return rows


def history(root, n=12):
    try:
        return [_json.loads(x) for x in (root / LOG_FILE).read_text().splitlines()[-n:]][::-1]
    except (OSError, ValueError):
        return []
