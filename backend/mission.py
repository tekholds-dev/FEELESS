"""🧾 THE MISSION ENVELOPE (owner + GPT 2026-11-09, HANDOFF COL-1). One read-only shape over every proof folder of all six kinds, so the
pieces after it (event history, model × proof vitals, the PoStatic pilot) read one schema instead of six folder shapes.

Pure: it reads a folder and its agent, never writes, never fetches, never grades. Quality comes in from the service's own `_proof_view`,
so there is one score, not two. An outcome names who verified it and how strong that is. Improvement stays 'unverified' until a matched
baseline exists. PoEco gets no invented grade or outcome. Nothing imports this yet, so it changes nothing that runs."""
import hashlib
import json

import proof_footprint as _foot
import proof_stamp as _stamp
import compare_gate as _cmp

VERSION = 1
KINDS = {   # kind → (its code, the folder list on an agent)
    'pow': ('PoW', 'powFolders'), 'pop': ('PoP', 'popFolders'), 'pob': ('PoB', 'pobFolders'),
    'poc': ('PoC', 'pocFolders'), 'pos': ('PoStatic', 'psFolders'), 'poe': ('PoEco', 'poeFolders'),
}
ALIASES = {**{k: k for k in KINDS}, **{v[0].lower(): k for k, v in KINDS.items()}, 'bids': 'pob', 'eco': 'poe'}
LEVELS = {   # how far a proof's evidence reaches; never the same thing as pass or fail
    'L0': 'Claimed: words only', 'L1': 'Filed with its record', 'L2': 'An outside fact recorded, its authority named',
    'L3': 'Re-checked independently', 'L4': 'Beat a frozen baseline on held-out data',
}
NOT_YET = 'not recorded yet (COL-2)'


def kind_of(kind):
    return ALIASES.get(str(kind or '').lower())


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _rows(v):
    return v if isinstance(v, list) else []


def record_sha(folder):
    """The folder exactly as read, hashed, so a later event can say which version it saw."""
    raw = json.dumps(folder, sort_keys=True, separators=(',', ':'), default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _title(k, f):
    calls = ' '.join(str(c.get('market')) for c in _rows(f.get('calls')) if isinstance(c, dict) and c.get('market'))
    return str(f.get('name') or f.get('topic') or f.get('sym') or calls or f"{KINDS[k][0]} #{f.get('n') or '?'}")[:120]


def _authority(k, f):
    """→ (who verified the outcome, how strong, plain words, tx signatures it rests on)."""
    if k == 'pow':
        if f.get('settlementVerified') and f.get('buySig') and f.get('sellSig'):
            return 'chain', 'chain', 'Both trades read back from the chain, fees included', [f['buySig'], f['sellSig']]
        if f.get('real'):
            return 'server prices', 'server', "A real trade, but its P&L is the server's own price read: the buy and sell are not linked to chain fills in the folder", []
        return 'none', 'paper', 'Proposed or paper only: no money moved', []
    if k == 'pop':
        return 'true prices', 'outside', 'A practice trade measured against true prices: the call is checkable, no money moved', []
    if k == 'poe':
        return 'none', 'none', "A hash of the owner's own books: it proves the numbers were not changed, not that anything happened", []
    if f.get('gradedBy') == 'scoreboard':
        return 'scoreboard', 'outside', 'Graded from the final score or the market settlement', []
    if f.get('graded') in ('right', 'wrong'):
        return 'owner mark', 'self', "The owner's own mark: not independent", []
    return 'none', 'none', 'Nobody has marked it and nothing outside settles it yet', []


def outcome(k, f, now):
    who, strength, why, sigs = _authority(k, f)
    value = f.get('pnlPct') if k == 'pow' else f.get('roePct') if k == 'pop' else f.get('graded') if k != 'poe' else None
    if k == 'poe':   # books carry no outcome; an old mark on a test folder is kept apart, never read as a result
        return {'state': 'none', 'won': None, 'dueAt': None, 'value': None, 'authority': who, 'strength': strength, 'why': why, 'sigs': []}
    if k == 'pow' and strength == 'paper':
        return {'state': 'none', 'won': None, 'dueAt': None, 'value': value, 'authority': who, 'strength': strength, 'why': why, 'sigs': []}
    st = _stamp.of(KINDS[k][0], f, now); state = st['state']; won = st.get('lean')
    if state in ('proved', 'not') and (won is None or strength == 'none'):   # the stamp says NOT PROVED once a day passes with no result; here that is no result
        state, won = 'unsettled', None
    return {'state': state, 'won': won if strength != 'none' else None, 'dueAt': st.get('dueAt'), 'value': value,
            'authority': who, 'strength': strength, 'why': why, 'sigs': sigs}


def _artifacts(k, f):
    out = {'sites': sorted(_foot.footprint(k, f)['sites']) if k != 'poe' else [], 'shots': len(_rows(f.get('shots'))),
           'calls': len(_rows(f.get('calls'))) or len(_rows(f.get('coins')))}
    if f.get('ws'):
        out['page'] = {'ws': f.get('ws'), 'version': f.get('version')}
    if k == 'poe' and f.get('hash'):
        out['booksHash'] = f.get('hash')
    return out


def evidence(k, f, out, arts):
    """L0 to L4 from what is really on file. L3 and L4 need machinery that does not exist yet (COL-3, COL-11), so nothing reaches them today."""
    filed = arts['sites'] or arts['shots'] or arts['calls'] or arts.get('page') or arts.get('booksHash') or f.get('refs') or f.get('plan')
    if out['strength'] in ('chain', 'outside') and out['state'] in ('proved', 'not'):
        return {'level': 'L2', 'why': f"{LEVELS['L2']}: {out['authority']}"}
    if filed:
        return {'level': 'L1', 'why': LEVELS['L1'] + ('' if out['state'] in ('proved', 'not') else ', no settled outcome yet')}
    return {'level': 'L0', 'why': LEVELS['L0']}


def _minds(cat, f):
    brains = (((cat or {}).get('brainsCfg') or {}).get('brains') or [])[:2]; spend = f.get('spend') if isinstance(f.get('spend'), dict) else {}
    n = max(len(brains), len(spend), 1 if f.get('cost') else 0)
    return [{'i': i, 'configuredNow': brains[i] if i < len(brains) else None, 'local': str(brains[i] if i < len(brains) else '').startswith('local/'),
             'spentUsd': round(_f(spend.get(str(i), spend.get(i))), 6), 'answeredBy': None, 'route': None} for i in range(n)]


def call_row(cat_id, kind, ref, mind, asked, answer, via, usd, ms, ok, now):
    """🧾 COL-2: one model call during a proof, as it really went: the model asked for, the route and model that answered (from the deepest
    caller, never guessed), its $, tokens and time. `answer` is what that caller reported; empty when nothing answered."""
    answer = answer or {}
    return {'at': round(float(now), 3), 'cat': cat_id, 'kind': kind_of(kind), 'ref': ref, 'mind': mind, 'asked': asked,
            'route': answer.get('route') if ok else None, 'model': answer.get('model') if ok else None, 'tokens': answer.get('tokens') if ok else None,
            'via': str(via or '')[:80] or None, 'usd': round(_f(usd), 6), 'ms': int(_f(ms)), 'ok': bool(ok),
            'local': answer.get('route') in ('local', 'lan') if ok else None}


def calls_for(rows, kind, ref):
    """This proof's calls, from the call log."""
    k = kind_of(kind)
    return [r for r in rows or [] if isinstance(r, dict) and r.get('ref') == ref and r.get('kind') == k] if ref else []


def _attribute(minds, calls):
    """Who really answered each mind, from the log: the routes and models seen, counted. Local calls cost $0 of API, never an invented price."""
    for m in minds:
        mine = [c for c in calls if c.get('mind') == m['i']]
        if not mine:
            continue
        seen = {}
        for c in mine:
            if c.get('ok'):
                key = f"{c.get('route') or '?'}:{c.get('model') or '?'}"; seen[key] = seen.get(key, 0) + 1
        m.update(answeredBy=[{'route': kk.split(':', 1)[0], 'model': kk.split(':', 1)[1], 'calls': n} for kk, n in sorted(seen.items(), key=lambda x: -x[1])],
                 calls=len(mine), failed=sum(1 for c in mine if not c.get('ok')), tokens=sum(int(_f(c.get('tokens'))) for c in mine),
                 ms=sum(int(_f(c.get('ms'))) for c in mine), apiUsd=round(sum(_f(c.get('usd')) for c in mine if not c.get('local')), 6),
                 localCalls=sum(1 for c in mine if c.get('local')))
    return minds


def _quality(k, q):
    if k == 'poe':
        return {'state': 'none', 'why': 'PoEco has no rubric yet: no grade is invented'}
    if not isinstance(q, dict) or not q.get('parts'):
        return {'state': 'not computed', 'why': "Pass the service's own _proof_view: there is one score, not two"}
    return {'state': 'scored', 'score': q.get('score'), 'top': q.get('top'), 'rank': q.get('rank'), 'frac': q.get('frac'), 'known': q.get('known'),
            'held': q.get('held'), 'parts': [{'key': p.get('key'), 'weight': p.get('weight'), 'value': p.get('value')} for p in q['parts']]}


def ref_of(k, f):
    """The id its calls are logged under: a page or post's workspace, else the folder."""
    return f.get('ws') if k in ('pos', 'poc') and f.get('ws') else f.get('id')


def _record(k, f, record):
    """COL-3's history for this proof: its own rows plus, for a page or post, its workspace's plan, build and review rows."""
    if record is None:
        return {'state': NOT_YET.replace('COL-2', 'COL-3')}
    rows = [record.get('rows', {}).get((k, str(x))) for x in dict.fromkeys([f.get('id'), f.get('ws')]) if x]
    rows = [r for r in rows if r]
    steps = list(dict.fromkeys(s for r in rows for s in r['steps']))
    return {'state': 'recorded' if rows else 'none', 'events': sum(r['events'] for r in rows), 'steps': steps,
            'last': max(rows, key=lambda r: r['at'] or 0)['last'] if rows else None, 'chainIntact': record.get('intact')}


def envelope(kind, folder, now, cat=None, quality=None, calls=None, record=None):
    """→ one proof in the shared shape, or None for an unknown kind or a folder that is not a dict. Never changes `folder` or `cat`.
    `calls` = the call log rows (COL-2); this proof's own are picked out by its ref."""
    k = kind_of(kind)
    if not k or not isinstance(folder, dict):
        return None
    f = folder; out = outcome(k, f, now); arts = _artifacts(k, f); sent = f.get('sent')
    mine = calls_for(calls, k, ref_of(k, f)); minds = _attribute(_minds(cat, f), mine)
    return {
        'v': VERSION, 'id': f.get('id'), 'kind': k, 'code': KINDS[k][0], 'n': f.get('n'), 'title': _title(k, f),
        'agent': {'id': (cat or {}).get('id'), 'name': (cat or {}).get('name')},
        'status': f.get('status'), 'at': f.get('at'), 'closedAt': f.get('soldAt') or f.get('closedAt'),
        'real': bool(f.get('real')) if k == 'pow' else False,
        'minds': minds, 'attribution': f'{len(mine)} calls recorded' if mine else NOT_YET,
        'cost': {'usd': round(_f(f.get('cost')), 6), 'byMind': {m['i']: m['spentUsd'] for m in minds},
                 'apiVsLocal': {'apiUsd': round(sum(_f(c.get('usd')) for c in mine if not c.get('local')), 6), 'localCalls': sum(1 for c in mine if c.get('local'))} if mine else NOT_YET},
        'sources': arts['sites'], 'kits': [str(x.get('id') if isinstance(x, dict) else x) for x in _rows(f.get('kits'))],
        'artifacts': arts, 'recordSha': record_sha(f),
        'quality': _quality(k, quality), 'outcome': out,
        'improvement': {'state': 'unverified', 'why': 'No matched baseline yet (COL-11). A better grade than an earlier proof is not proof of improvement.'},
        'evidence': evidence(k, f, out, arts), 'record': _record(k, f, record), 'compare': {x: v for x, v in _cmp.check(k, f).items() if x != 'hosts'},
        'mark': f.get('graded') if f.get('graded') in ('right', 'wrong') else None, 'markedBy': f.get('gradedBy') or ('owner' if f.get('graded') in ('right', 'wrong') else None),
        'sent': {'sent': bool(sent), 'sig': sent.get('sig') if isinstance(sent, dict) else None},
    }


def all_of(cat, now, quality_of=None, calls=None, record=None):
    """Every proof of one agent, newest first. `quality_of(kind, folder)` is the service's own scorer, when given."""
    out = []; calls = [c for c in calls or [] if isinstance(c, dict) and c.get('cat') == (cat or {}).get('id')]
    for k, (_, key) in KINDS.items():
        for f in _rows((cat or {}).get(key)):
            e = envelope(k, f, now, cat, quality_of(k, f) if quality_of and k != 'poe' else None, calls, record)
            if e:
                out.append(e)
    return sorted(out, key=lambda e: -_f(e.get('at')))


MIN_SAMPLE = 5   # fewer proofs than this for a model on a kind: shown, never ranked or recommended


def vitals(envelopes, calls):
    """COL-5: model × proof kind, from the real record only. Per row: proofs, calls, failed calls, API $ apart from local calls,
    average quality, outcomes settled from outside (chain / scoreboard / true prices) and how many won. A recommendation only where
    the sample is big enough: the cheapest model whose verified win rate is at least the kind's best minus 10 points. Pure."""
    by_ref = {}
    for c in calls or []:
        if isinstance(c, dict) and c.get('kind') in KINDS:
            by_ref.setdefault((c['kind'], str(c.get('ref'))), []).append(c)
    rows = {}
    for e in envelopes or []:
        k = e.get('kind'); refs = {str(e.get('id'))} | ({str(e['artifacts']['page']['ws'])} if (e.get('artifacts') or {}).get('page') else set())
        mine = [c for r in refs for c in by_ref.get((k, r), [])]
        for model in dict.fromkeys(str(c.get('model') or c.get('asked') or '?') for c in mine):
            mc = [c for c in mine if str(c.get('model') or c.get('asked') or '?') == model]
            r = rows.setdefault((model, k), {'model': model, 'kind': k, 'proofs': 0, 'calls': 0, 'failed': 0, 'apiUsd': 0.0, 'localCalls': 0, 'q': [], 'verified': 0, 'won': 0})
            r['proofs'] += 1; r['calls'] += len(mc); r['failed'] += sum(1 for c in mc if not c.get('ok'))
            r['apiUsd'] += sum(_f(c.get('usd')) for c in mc if not c.get('local')); r['localCalls'] += sum(1 for c in mc if c.get('local'))
            q = (e.get('quality') or {}).get('score')
            if q is not None:
                r['q'].append(_f(q))
            out = e.get('outcome') or {}
            if out.get('strength') in ('chain', 'outside') and out.get('state') in ('proved', 'not'):
                r['verified'] += 1; r['won'] += 1 if out.get('state') == 'proved' else 0
    out = []
    for r in rows.values():
        q = r.pop('q'); r['quality'] = round(sum(q) / len(q), 1) if q else None
        r['apiUsd'] = round(r['apiUsd'], 6); r['perProofUsd'] = round(r['apiUsd'] / r['proofs'], 6) if r['proofs'] else None
        r['failRate'] = round(r['failed'] / r['calls'], 3) if r['calls'] else None
        r['winRate'] = round(r['won'] / r['verified'], 3) if r['verified'] else None
        r['enough'] = r['proofs'] >= MIN_SAMPLE
        out.append(r)
    pick = {}
    for k in KINDS:
        ok = [r for r in out if r['kind'] == k and r['enough'] and r['winRate'] is not None and r['verified'] >= MIN_SAMPLE]
        if ok:
            best = max(r['winRate'] for r in ok)
            fit = sorted((r for r in ok if r['winRate'] >= best - 0.10), key=lambda r: (r['perProofUsd'] or 0, -r['winRate']))
            pick[k] = {'model': fit[0]['model'], 'why': f"cheapest within 10 points of the best verified win rate ({round(best * 100)}%) on {fit[0]['verified']} settled proofs"}
        else:
            pick[k] = {'model': None, 'why': f'not enough settled proofs yet (needs {MIN_SAMPLE} per model)'}
    return {'rows': sorted(out, key=lambda r: (r['kind'], -r['proofs'])), 'pick': pick, 'minSample': MIN_SAMPLE}
