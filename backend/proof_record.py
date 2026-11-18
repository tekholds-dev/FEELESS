"""🧾 THE TRUE RECORD (Slice 0, owner 2026-11-18: "every proof type and filing were to create a new footprint and to never do the same shit
twice"; docs/VISION.md "Checks for EVERY proof type"). Pure and tested; the service hands it the call log and the folders.

Every filed proof of every kind gets, on its own folder:
  · `ran`      — the minds that REALLY answered, read from the call log (data/mind_calls.jsonl), never from the setting
  · `minds`    — the same model ids (a folder that kept none, like every PoStatic, now has them; PoW keeps its own count)
  · `mindsCheck` — do they match the pair set for that kind in Brains (or the agent's own pair when none is set)?
  · `read`     — every source it read: hosts and pages
  · `foot`     — how new its footprint is next to the past filings of its kind on this agent, and whether it was sent back once first
  · `proofChecks` — the four VISION checks, each with its plain reason
  · `test`     — only on a TEST proof Claude started on Sicario's agent ($0, local minds)

THE FOOTPRINT GATE: a filing that would read mostly the same sources, topic and angle as a past filing of its kind and agent is sent back
ONCE to find new info (its repeated sites go last and its minds are told what to avoid). The retry files with `foot.sentBack = 1`, so a
gate can never loop a proof forever or swallow it."""
import re

import proof_footprint as _foot

KEYS = {'pow': 'powFolders', 'pop': 'popFolders', 'pob': 'pobFolders', 'poc': 'pocFolders', 'pos': 'psFolders', 'poe': 'poeFolders'}
CODE = {'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'pos': 'PoStatic', 'poe': 'PoEco'}
NO_MINDS = {'poe': 'no model call: PoEco is pure math on live pools, and reality grades it a day later'}
REPEAT_AT = 0.7          # footprint likeness at or above this is "mostly the same work"
SITES_AT = 0.5           # ... and at least this share of its sources the same (when both read any)
BACK_S = 3 * 3600        # a send-back is answered by the next filing of that kind within this time
FREE_ROUTES = ('local', 'lan')


def _rows(v):
    return v if isinstance(v, list) else []


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def refs_of(f):
    """Every id this proof's calls are logged under: the folder, its workspace (page / post), and its browser read."""
    f = f if isinstance(f, dict) else {}
    out = [f.get('id'), f.get('ws')] + _rows(f.get('callRefs')) + [f"read:{t}" for t in _rows(f.get('readTids')) + [f.get('readTid')] if t]
    return [str(x) for x in dict.fromkeys(out) if x]


def ran(rows, kind, refs, since=0.0, until=None):
    """The minds that really answered this proof, from the call log: one row per model asked, in the order they first ran. Judges'
    review calls never count. → [{asked, answered, routes, calls, ok, usd, secs, standIn}]"""
    want = {str(r) for r in refs or [] if r}; out = {}
    for r in rows or []:
        if not isinstance(r, dict) or r.get('kind') != kind or str(r.get('ref')) not in want or str(r.get('ref') or '').startswith('review:'):
            continue
        at = _f(r.get('at'))
        if at < _f(since) or (until is not None and at > _f(until) + 120):
            continue
        m = str(r.get('asked') or '?')
        o = out.setdefault(m, {'asked': m, 'answered': [], 'routes': [], 'calls': 0, 'ok': 0, 'usd': 0.0, 'secs': 0.0, 'standIn': False})
        o['calls'] += 1; o['usd'] = round(o['usd'] + _f(r.get('usd')), 6); o['secs'] = round(o['secs'] + _f(r.get('ms')) / 1000, 1)
        if r.get('ok'):
            o['ok'] += 1
            for key, v in (('answered', r.get('model')), ('routes', r.get('route'))):
                if v and v not in o[key]:
                    o[key].append(str(v)[:60])
            if m.startswith('local/') and str(r.get('route') or '') not in FREE_ROUTES:
                o['standIn'] = True   # a local mind must answer from its own LM Studio; anything else stood in
            if 'stood in' in str(r.get('route') or '') or 'stood in' in str(r.get('via') or ''):
                o['standIn'] = True
    return list(out.values())


def match(ran_, pair, kind=None):
    """Do the minds that really answered match the pair set for this kind? → {ok, set, ran, missing, extra, why}"""
    pair = [str(m) for m in pair or [] if m]; did = [r['asked'] for r in ran_ or [] if r.get('ok')]
    if kind in NO_MINDS:
        return {'ok': not did, 'set': pair, 'ran': did, 'missing': [], 'extra': did, 'why': NO_MINDS[kind]}
    missing = [m for m in pair if m not in did]; extra = [m for m in did if m not in pair]; stood = [r['asked'] for r in ran_ or [] if r.get('standIn')]
    if not did:
        why = 'no mind answered (the call log has no answered call for this proof)'
    elif extra:
        why = f"{', '.join(extra)} ran but {'the pair is ' + ' + '.join(pair) if pair else 'no pair is set'}"
    elif stood:
        why = f"{', '.join(stood)} did not answer from its own machine (a stand-in answered)"
    elif missing:
        why = f"only {' + '.join(did)} answered; {' + '.join(missing)} gave no answer"
    else:
        why = f"{' + '.join(did)} ran, the pair set for it"
    return {'ok': bool(did) and not extra and not stood and not missing, 'set': pair, 'ran': did, 'missing': missing, 'extra': extra, 'why': why}


def _host(u):
    return re.sub(r'^www\.', '', re.sub(r'^https?://', '', str(u or '').lower()).split('/')[0])


def sources(kind, f):
    """Every source this proof read: → {sites: [hosts], pages: [urls]}. Search boxes count as sites here (they were opened), never in
    the footprint (proof_footprint keeps them out of the likeness)."""
    f = f if isinstance(f, dict) else {}; hosts, pages = set(_foot.footprint(kind, f)['sites']), []
    for s in _rows(f.get('shots')):
        if isinstance(s, dict):
            hosts.add(_host(s.get('site') or s.get('url'))); pages.append(s.get('url'))
    for r in _rows(f.get('refs')):
        if isinstance(r, dict):
            pages.append(r.get('url'))
    for r in _rows(f.get('sitesRead')):
        if isinstance(r, dict) and r.get('host') and r.get('ok', True):
            hosts.add(_host(r.get('host')))
    br = f.get('browsed')
    if isinstance(br, dict):
        for v in br.values():
            if isinstance(v, dict):
                pages += [x for x in _rows(v.get('pages')) if isinstance(x, str)]
    for rows in (f.get('sources') or {}).values() if isinstance(f.get('sources'), dict) else []:
        for r in _rows(rows):
            if isinstance(r, dict) and r.get('url'):
                pages.append(r['url'])
    if kind == 'poe' and isinstance(f.get('baseline'), dict):
        hosts.add('dexscreener.com')
        pages += [f"https://dexscreener.com/solana/{(f['baseline'].get(k) or {}).get('addr')}" for k in ('pick', 'other') if (f['baseline'].get(k) or {}).get('addr')]
    return {'sites': sorted(h for h in hosts if h), 'pages': [p for p in dict.fromkeys(str(x)[:300] for x in pages if x and str(x).startswith('http'))][:40]}


def _jac(a, b):
    return len(a & b) / len(a | b) if a and b else None


def gate(kind, f, earlier):
    """Is this filing mostly the same work as a past one of its kind on this agent? → {repeat, like, nearest, shared, avoid}.
    'Mostly the same' = footprint likeness ≥ REPEAT_AT (topic, sources, calls) and, when both read sites, ≥ SITES_AT of them shared."""
    me = _foot.footprint(kind, f); best, near, sites_j = 0.0, None, None
    for e in [x for x in earlier or [] if isinstance(x, dict) and x.get('id') != (f or {}).get('id')][-_foot.KEEP * 3:]:
        them = _foot.footprint(kind, e); v = _foot.likeness(me, them)
        if v >= best and (v > 0 or near is None):
            best, near, sites_j = v, e, _jac(me['sites'], them['sites'])
    shared = sorted(me['sites'] & _foot.footprint(kind, near)['sites']) if near else []
    repeat = bool(near) and best >= REPEAT_AT and (sites_j is None or sites_j >= SITES_AT)
    return {'repeat': repeat, 'like': round(best, 2), 'nearest': (near or {}).get('n'), 'shared': shared[:8], 'avoid': shared[:12]}


def back_due(back, kind, now):
    """The send-back this kind is answering now, or None (it expires after BACK_S)."""
    b = (back or {}).get(kind) if isinstance(back, dict) else None
    return b if isinstance(b, dict) and _f(now) - _f(b.get('at')) < BACK_S else None


def back_line(back, kind, now):
    """What the minds read when their last try was sent back. '' when it was not."""
    b = back_due(back, kind, now)
    if not b:
        return ''
    on = ', '.join(b.get('avoid') or []) or 'the same sites'
    return (f"\nSENT BACK ONCE: your last try repeated {CODE.get(kind, kind)} #{b.get('nearest')} (same topic and angle, and it read {on}). "
            "Find NEW information this time: read other sources than those, say what is new, and never file the same work twice.")


def fresh_sites(back, kind, now, sites, keep=4):
    """A sent-back proof's site list without the sites its repeat read, while at least `keep` others are left (else they go last, so a
    thin list never empties). No send-back: the list as it was."""
    b = back_due(back, kind, now); bad = {_host(x) for x in (b or {}).get('avoid') or []}
    if not bad:
        return list(sites or [])
    good = [s for s in sites or [] if _host(s) not in bad]
    return good if len(good) >= keep else good + [s for s in sites or [] if _host(s) in bad]


def checks(kind, f, pair):
    """The VISION checks for every proof, on this one folder. → [{key, label, ok, why}]"""
    m = f.get('mindsCheck') or match(f.get('ran'), pair, kind); rd = f.get('read') or sources(kind, f); ft = f.get('foot') or {}
    kits = [k for k in _rows(f.get('kits')) if k]
    rows = [
        {'key': 'minds', 'label': 'The minds that really ran, from the call log', 'ok': bool(m.get('ok')), 'why': m.get('why')},
        {'key': 'sources', 'label': 'Every source it read is listed', 'ok': bool(rd.get('sites')) or kind == 'poe' and bool(rd.get('pages')),
         'why': f"{len(rd.get('sites') or [])} sites, {len(rd.get('pages') or [])} pages" if rd.get('sites') or rd.get('pages') else 'no source was recorded'},
        {'key': 'footprint', 'label': 'A new footprint (a repeat is sent back first)', 'ok': not ft.get('repeat'),
         'why': (f"{ft.get('pct')}% new" + (f" next to #{ft.get('nearest')}" if ft.get('nearest') else '') + (', after one send-back' if ft.get('sentBack') else ''))
         if not ft.get('repeat') else f"still {100 - int(ft.get('pct') or 0)}% like #{ft.get('nearest')} after one send-back"},
        {'key': 'kits', 'label': "Its kind's own kits, and which it used", 'ok': bool(kits) or kind in ('poe', 'pow'),
         'why': ', '.join(map(str, kits[:6])) if kits else ('PoEco uses no kit: pure math' if kind == 'poe' else 'PoW reads its own coin tools' if kind == 'pow' else 'no kit was recorded')},
    ]
    return rows


def stamp(kind, f, calls, pair, earlier, since=0.0, back=None, test=None, now=None):
    """Writes the true record onto a folder that is being filed. Never removes a field the folder had. → the folder."""
    now = _f(now) or _f(f.get('closedAt') or f.get('at'))
    f['ran'] = ran(calls, kind, refs_of(f), since, now)
    did = [r['asked'] for r in f['ran'] if r.get('ok')]
    if did and not isinstance(f.get('minds'), (int, float)):   # PoW keeps its own count of minds; every other kind keeps the ids
        f['minds'] = did
    f['mindsCheck'] = match(f['ran'], pair, kind)
    f['read'] = sources(kind, f)
    g = gate(kind, f, earlier)
    f['foot'] = {'pct': round((1 - g['like']) * 100), 'nearest': g['nearest'], 'shared': g['shared'], 'repeat': g['repeat'],
                 'sentBack': 1 if back else 0, **({'backOf': back.get('nearest')} if back else {})}
    if test:
        f['test'] = test
    f['proofChecks'] = checks(kind, f, pair)   # never `checks`: a PoW folder's `checks` is its live-trade counter
    return f


def test_row(kind, f, started_at=None):
    """A TEST proof's Test bench row (test_bench.file_run kwargs) from its true record."""
    ch = f.get('proofChecks') or []; ok = bool(ch) and all(c.get('ok') for c in ch)
    usd = round(sum(_f(r.get('usd')) for r in f.get('ran') or []), 6)
    secs = max(0.0, _f(f.get('closedAt') or f.get('at')) - _f(started_at)) if started_at else sum(_f(r.get('secs')) for r in f.get('ran') or [])
    return {'kind': {'pos': 'static', 'poe': 'other'}.get(kind, kind), 'title': f"TEST {CODE.get(kind, kind)} #{f.get('n')} · {str(f.get('topic') or f.get('sym') or f.get('market') or '')[:80]}".strip(' ·'),
            'ok': ok, 'why': '; '.join(f"{c['key']}: {'✓' if c['ok'] else '✗'} {c['why']}" for c in ch)[:600],
            'models': [r['asked'] for r in f.get('ran') or [] if r.get('ok')], 'cost_usd': usd, 'secs': secs,
            'steps': [f"{c['label']}: {'pass' if c['ok'] else 'FAIL'}" for c in ch]}
