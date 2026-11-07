"""⚖ HOW A PROOF SCORES (owner 2026-11-06: "true mechanical weights and ranks so all proofs dont get the same judgement"). Pure and tested.

Each kind of proof has its own parts and weights, each read from that proof's own record by code, not by a model. A part that is not known yet counts as nothing, so an unproven proof cannot rank high. The minds read these facts and argue with them inside a limit, and the owner's word stays last.

The py agents learn from OSSY and G4: once enough proofs of a kind are scored, `learn` fits how the minds really weigh each part and tests it on proofs it did not see. It only proposes. The owner applies it, and no weight may move past half or one and a half times its start."""
import json
import re
from pathlib import Path

import proof_footprint as fp

STORE = 'proof_weights.json'
LEARN_MIN = 12
MINDS_LIFT = 0.08   # the minds may lift a proof at most this part of the top above what its record shows
MINDS_PART = 0.4
FLAWLESS = 0.95
ALIASES = {'pow': 'pow', 'pop': 'pop', 'pob': 'pob', 'poc': 'poc', 'pos': 'pos', 'postatic': 'pos', 'bids': 'pob'}
RANKS = ((0.92, 'S'), (0.78, 'A'), (0.6, 'B'), (0.4, 'C'), (0.0, 'D'))
# 🔒 owner 2026-11-07: "doing a simple request well is not a high score". How high a proof can reach depends on how deep the work went, so no mark or win lifts simple work past its ceiling.
CEIL_SIMPLE = 0.3   # the ceiling with no depth at all; full depth opens it to the top
CEIL_FAILED = 0.4    # marked wrong, or it lost
CEIL_UNPROVEN = 0.6  # nobody has marked it or it has no result yet
LINE_LIKE = 0.25     # this alike, or the same page, counts as the same line of work
GROW_FULL = 0.25     # this much more depth than where its line started is full marks for evolution


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _clip(v):
    return max(0.0, min(1.0, float(v)))


def _n(v):
    return len(v) if isinstance(v, (list, dict)) else 0


def _won(pct):
    """+50% or better is full marks, flat or worse is none: the same line a win must cross to send a proof."""
    return _clip(_f(pct) / 50)


def _closed(f):
    return f.get('status') == 'closed'


def _mark(f):
    g = f.get('graded')
    return (1.0, 'Marked right') if g == 'right' else (0.0, 'Marked wrong') if g == 'wrong' else (None, 'Not marked yet')


def _pow_result(f):
    if not _closed(f) or f.get('pnlPct') is None:
        return None, 'Still open'
    return _won(f.get('pnlPct')), f"{_f(f.get('pnlPct')):+.1f}%"


def _pow_real(f):
    return (1.0, 'Real money') if f.get('real') else (0.3, 'Practice')


def _pow_exits(f):
    has = sum(1 for k in ('tp', 'sl') if f.get(k) not in (None, 0, ''))
    return has / 2, ('Exits set first' if has == 2 else 'One exit set' if has else 'No exits set')


def _pow_hold(f):
    a, b = _f(f.get('boughtAt')), _f(f.get('soldAt'))
    if not a or not b or b < a:
        return None, 'No hold on record'
    m = (b - a) / 60
    return (1.0 if m >= 30 else 0.5 if m >= 15 else 0.1), f'Held {m:.0f} min'   # the real card's ledger: under 15 minutes loses, 30 and up wins


def _pow_evidence(f):
    n = _n(f.get('shots')) + (1 if f.get('vitals') else 0) + (1 if any(isinstance(c, dict) and c.get('read') for c in f.get('coins') or []) else 0)
    return _clip(n / 4), f"{_n(f.get('shots'))} snapshots{', vitals' if f.get('vitals') else ''}"


def _pop_result(f):
    if f.get('noTrade'):
        return None, 'No trade filed'
    if not _closed(f) or f.get('roePct') is None:
        return None, 'Still open'
    return _won(f.get('roePct')), f"{_f(f.get('roePct')):+.1f}%"


def _pop_sources(f):
    src = f.get('sources') if isinstance(f.get('sources'), dict) else {}
    n = sum(1 for rows in src.values() if isinstance(rows, list) for r in rows if isinstance(r, dict) and r.get('ok'))
    return _clip(n / 4), f'{n} sources read'


def _pop_reads(f):
    n = _n(f.get('reads'))
    return (1.0 if n else 0.0), f'{n} true prices'


def _pop_plan(f):
    rows = [c for c in f.get('calls') or [] if isinstance(c, dict) and c.get('side')]
    n = sum(1 for c in rows if c.get('tp') and c.get('sl'))
    return (n / len(rows) if rows else 0.0), f'{n} of {len(rows)} calls with exits'


def _pob_evidence(f):
    n = _n(f.get('shots')); sites = _n(f.get('browsed'))
    return _clip((n + sites) / 5), f'{n} snapshots, {sites} sites read'


def _pob_blind(f):
    n = sum(1 for c in f.get('calls') or [] if isinstance(c, dict))
    return _clip(n / 2), f'{n} of 2 minds picked'


def _pob_odds(f):
    return (1.0 if f.get('poly') or f.get('games') else 0.0), ('Real games and odds on file' if f.get('poly') or f.get('games') else 'No games or odds on file')


def _pob_series(f):
    """One right pick can be luck, so a call on the same topic only counts in full after a run of them."""
    lp = f.get('loop') if isinstance(f.get('loop'), dict) else {}; w, l = int(_f(lp.get('wins'))), int(_f(lp.get('losses'))); n = w + l
    return (None, 'First of its series') if not n else (_clip(w / n) * _clip(n / 5), f'{w} right of {n} before it')


def _poc_earned(f):
    return (None, 'Nothing earned yet') if not _f(f.get('earned')) else (1.0, f"${_f(f.get('earned')):.2f} earned")


def _poc_trends(f):
    t = f.get('trends') if isinstance(f.get('trends'), dict) else {}
    n = sum(1 for v in t.values() if v)
    return _clip(n / 3), f'{n} trend sources'


def _shots3(f):
    n = _n(f.get('shots'))
    return _clip(n / 3), f'{n} snapshots'


def _poc_pitch(f):
    n = sum(1 for c in f.get('calls') or [] if isinstance(c, dict) and c.get('post') and c.get('angle'))
    return _clip(n / 2), f'{n} pitches written'


def _pos_review(f):
    v = int(_f(f.get('version')))
    return (1.0 if v >= 2 else 0.0), f'{v} pages, ' + ('a second mind reviewed' if v >= 2 else 'no second read')


def _pos_plan(f):
    n = _n(f.get('steps'))
    return (_clip(n / 3) if f.get('plan') else 0.0), f'{n} planned steps'


def _pos_refs(f):
    n = sum(1 for r in f.get('refs') or [] if isinstance(r, dict) and r.get('open', True))
    return _clip(n / 3), f"{n} build{'' if n == 1 else 's'} studied"


def page_stats(html):
    """What a page really holds, read from its code. Pages run with no network, so live calls are not counted: what counts is how much it really does."""
    h = str(html or '')
    if not h:
        return None
    js = ' '.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S | re.I))
    return {'chars': len(h), 'fns': len(re.findall(r'\bfunction\b|=>', js)), 'handlers': len(re.findall(r'addEventListener|\bon(?:click|input|change|submit)\b', h)), 'state': len(re.findall(r'localStorage|useState|setInterval|requestAnimationFrame', js)), 'visuals': len(re.findall(r'<canvas|<svg|new Chart|createChart', h)), 'kits': len(re.findall(r'<script[^>]+src=|<link[^>]+href=', h))}


def _page_depth(st):
    """A one screen page with a button stays low; a working tool with logic, inputs, state and drawn data goes high."""
    return (0.35 * _clip(st['fns'] / 60) + 0.2 * _clip(st['handlers'] / 10) + 0.15 * _clip(st['state'] / 4) + 0.15 * _clip(st['chars'] / 50000) + 0.1 * _clip(st['visuals'] / 3) + 0.05 * _clip(st['kits'] / 3)) if st else None


def _sites(k, f):
    return len(fp.footprint(k, f)['sites'])


def _legs(f):
    rows = f.get('agreed') if isinstance(f.get('agreed'), list) else []
    return len({str(x.get('pick') if isinstance(x, dict) else x) for x in rows})


def depth(k, f, page=None):
    """→ (0 to 1 or None, note): how much real work this proof took, from its own record. Each kind by what is hard in it."""
    if k == 'pos':
        st = page(f) if page else None
        return (None, 'Page not measured') if st is None else (round(_page_depth(st), 3), f"{st['chars'] // 1000}K page, {st['fns']} functions, {st['handlers']} inputs")
    if k == 'poc':
        e = f.get('edit') if isinstance(f.get('edit'), dict) else None
        if e:   # a real edit: how much was cut and built, from its edit list
            return round(0.5 * _clip(_f(e.get('cuts')) / 15) + 0.2 * _clip(_f(e.get('texts')) / 5) + 0.15 * _clip((_f(e.get('fades')) + _f(e.get('speedChanges'))) / 4) + 0.15 * _clip(_f(e.get('music'))), 3), f"{int(_f(e.get('cuts')))} cuts, {int(_f(e.get('texts')))} text overlays, {_f(e.get('seconds')):.0f}s"
        st = page(f) if page and f.get('ws') else None; n = _n(f.get('calls'))
        return round(0.5 * (_page_depth(st) or 0.0) + 0.2 * _clip(n / 3) + 0.15 * _poc_trends(f)[0] + 0.15 * _clip(_sites(k, f) / 4), 3), f"{'a real build, ' if st else ''}{n} pitches, {_sites(k, f)} sites"
    if k == 'pow':
        n = _n(f.get('scout'))
        return round(0.35 * _clip(n / 4) + 0.35 * _clip(_sites(k, f) / 5) + 0.3 * _clip(_f(f.get('rounds')) / 3), 3), f"{n} coins vetted, {_sites(k, f)} sites, {int(_f(f.get('rounds')))} rounds"
    if k == 'pop':
        m = len({str(c.get('market')) for c in f.get('calls') or [] if isinstance(c, dict) and c.get('market') and c.get('side')})
        return round(0.4 * _clip(m / 3) + 0.3 * _clip(_sites(k, f) / 6) + 0.3 * _pop_sources(f)[0], 3), f"{m} markets called, {_sites(k, f)} sites"
    legs = max(_legs(f), int(_f((f.get('parlay') or {}).get('agreed'))) if isinstance(f.get('parlay'), dict) else 0); g = _n(f.get('games'))
    return round(0.4 * _clip(legs / 3) + 0.2 * _clip(g / 3) + 0.4 * _clip(_sites(k, f) / 6), 3), f"{legs} picks agreed, {g} games, {_sites(k, f)} sites"


def _evolved(k, f, earlier, page=None):
    """Did its line of work get deeper? The same work repeated earns nothing, and a first try has nothing to grow from yet."""
    if earlier is None:
        return None, 'Not compared yet'
    me = fp.footprint(k, f); line = [e for e in earlier if (f.get('ws') and e.get('ws') == f.get('ws')) or fp.likeness(me, fp.footprint(k, e)) >= LINE_LIKE]
    if not line:
        return None, 'First of its line'
    start, now = depth(k, line[0], page)[0], depth(k, f, page)[0]
    if start is None or now is None:
        return None, 'Not measured'
    return _clip((now - start) / GROW_FULL), f'{(now - start) * 100:+.0f} depth over {len(line)} before it'


# kind → [(part, what it is, weight, how to read it)]. Each kind's weights add up to 100. Unique reads against the proofs before it.
RUBRIC = {
    'pow': [('result', 'Real result', 25, _pow_result), ('build', 'Depth of work', 20, None), ('real', 'Real money', 15, _pow_real), ('evolve', 'Evolution', 10, None), ('unique', 'Unique', 10, None), ('hold', 'Hold time', 10, _pow_hold), ('evidence', 'Evidence', 5, _pow_evidence), ('exits', 'Exits set first', 5, _pow_exits)],
    'pop': [('result', 'Practice result', 25, _pop_result), ('build', 'Depth of work', 20, None), ('unique', 'Unique', 15, None), ('evolve', 'Evolution', 10, None), ('sources', 'Sources read', 10, _pop_sources), ('plan', 'Exits on calls', 10, _pop_plan), ('reads', 'True prices', 5, _pop_reads), ('blind', 'Blind calls', 5, _pob_blind)],
    'pob': [('result', 'Real result', 20, _mark), ('build', 'Depth of work', 20, None), ('unique', 'Unique', 15, None), ('series', 'Its run', 15, _pob_series), ('evolve', 'Evolution', 10, None), ('evidence', 'What it read', 10, _pob_evidence), ('odds', 'Games and odds', 5, _pob_odds), ('blind', 'Blind picks', 5, _pob_blind)],
    'poc': [('build', 'Depth of work', 25, None), ('mark', 'Your mark', 15, _mark), ('unique', 'Unique', 15, None), ('earned', 'What it earned', 15, _poc_earned), ('evolve', 'Evolution', 10, None), ('trends', 'Trends read', 10, _poc_trends), ('pitch', 'Pitches', 5, _poc_pitch), ('shots', 'Snapshots', 5, _shots3)],
    'pos': [('build', 'Real build', 35, None), ('mark', 'Your mark', 15, _mark), ('evolve', 'Evolution', 15, None), ('unique', 'Unique', 15, None), ('review', 'Second mind', 10, _pos_review), ('plan', 'Its plan', 5, _pos_plan), ('refs', 'Builds studied', 5, _pos_refs)],
}


def kind_of(kind):
    return ALIASES.get(str(kind or '').lower())


def rank_of(frac, all_known=True):
    """S needs every part known: nothing unproven tops the board."""
    got = next(r for lo, r in RANKS if frac >= lo)
    return 'A' if got == 'S' and not all_known else got


def ceiling(parts):
    """→ (the most this record may reach, why). Simple work stays low however well it was done, a failure stays low however much was done, and no result yet is not proof."""
    by = {p['key']: p['value'] for p in parts}; deep = by.get('build') or 0.0; simple = CEIL_SIMPLE + (1 - CEIL_SIMPLE) * deep
    proof = next(((by[x], x) for x in ('result', 'mark') if x in by), (None, None))[0]
    rows = [(simple, 'Simple work')]
    if proof is None:
        rows.append((CEIL_UNPROVEN, 'Not proven yet'))
    elif proof <= 0:
        rows.append((CEIL_FAILED, 'It failed'))
    cap, why = min(rows, key=lambda r: r[0])
    return round(cap, 4), f'{why}: held at {round(cap * 100)}% of the top'


def view(kind, folder, top=300.0, weights=None, earlier=None, page=None):
    """→ {kind, frac, score, rank, known, parts:[{key,label,weight,value,note}]}, or None for a kind with no rubric. A part that is not known scores nothing."""
    k = kind_of(kind)
    if not k or not isinstance(folder, dict):
        return None
    mine = (weights or {}).get(k) or {}; parts = []
    for key, label, w, read in RUBRIC[k]:
        try:
            if key == 'unique':
                u = fp.unique(k, folder, [e for e in earlier if not folder.get('ws') or e.get('ws') != folder.get('ws')]) if earlier is not None else None   # a later version of its own page is growth, not a copy
                v, note = (None, 'Not compared yet') if u is None else (u['pct'] / 100, f"{u['pct']}% new" + (f", closest is #{u['nearest']}" if u.get('nearest') else ''))
            elif key == 'build':
                v, note = depth(k, folder, page)
            elif key == 'evolve':
                v, note = _evolved(k, folder, earlier, page)
            else:
                v, note = read(folder)
        except (TypeError, ValueError, AttributeError, KeyError):
            v, note = None, 'Could not be read'
        parts.append({'key': key, 'label': label, 'weight': round(_f(mine.get(key)) or w, 2), 'value': None if v is None else round(v, 3), 'note': note})
    total = sum(p['weight'] for p in parts) or 1.0; frac = sum(p['weight'] * (p['value'] or 0.0) for p in parts) / total; known = all(p['value'] is not None for p in parts)
    cap, held = ceiling(parts); earned = frac; frac = min(frac, cap)
    return {'kind': k, 'frac': round(frac, 4), 'score': round(frac * float(top), 1), 'top': float(top), 'rank': rank_of(frac, known), 'known': known, 'parts': parts, 'held': held if earned > cap else None}


def blend(frac, minds, top, both_reject=False):
    """What the record shows, then the minds' read inside a limit: they can correct a proof, but cannot talk an empty record up. Flawless takes a full record."""
    top = float(top); base = _clip(frac) * top; m = max(0.0, min(top, _f(minds)))
    if both_reject:   # both minds call it trash, quoting why: their word stands until the owner says otherwise
        return round(m, 1)
    score = (1 - MINDS_PART) * base + MINDS_PART * m
    score = min(score, base + MINDS_LIFT * top)
    return round(min(score, top if frac >= FLAWLESS else top * (FLAWLESS - 0.01)), 1)


def at_top(v, top):
    """The same reading on today's top score."""
    return {**v, 'top': float(top), 'score': round(_f(v.get('frac')) * float(top), 1)} if isinstance(v, dict) and v.get('parts') else None


def facts_line(v):
    """The record as the minds read it, checked by code and not by the file."""
    if not v:
        return ''
    rows = '; '.join(f"{p['label']} (weight {p['weight']:g}): {'not known yet' if p['value'] is None else f'{round(p['value'] * 100)}%'}, {p['note']}" for p in v['parts'])
    return f"FACTS CHECKED BY CODE, score against these: {rows}. On the record alone this is {v['score']:g} of {v['top']:g}, rank {v['rank']}.{' ' + v['held'] + '.' if v.get('held') else ''}"


def sample(v, minds, top):
    """One scored proof, for the py agents to learn from."""
    return {'kind': v['kind'], 'parts': {p['key']: (p['value'] or 0.0) for p in v['parts']}, 'label': _clip(_f(minds) / (float(top) or 1.0))}


def _predict(w, parts):
    total = sum(w.values()) or 1.0
    return sum(w[k] * parts.get(k, 0.0) for k in w) / total


def _mae(w, rows):
    return sum(abs(_predict(w, r['parts']) - r['label']) for r in rows) / len(rows) if rows else None


def _fit(base, rows, steps=400, rate=0.02):
    """Nudges each weight toward how the minds really scored, and never past half or one and a half times its start."""
    w = dict(base)
    for _ in range(steps):
        total = sum(w.values()) or 1.0; grad = dict.fromkeys(w, 0.0)
        for r in rows:
            err = _predict(w, r['parts']) - r['label']
            for k in w:
                grad[k] += err * (r['parts'].get(k, 0.0) - _predict(w, r['parts'])) / total
        for k in w:
            w[k] = max(base[k] * 0.5, min(base[k] * 1.5, w[k] - rate * grad[k] * total / max(1, len(rows)) * total))
    return {k: round(v, 2) for k, v in w.items()}


def learn(samples, weights=None):
    """Per kind: how close the code's weights come to OSSY and G4, and the weights fitted on the older three quarters, tested on the newest quarter. ready only when they really do better on proofs they never saw."""
    out = []
    for k, rubric in RUBRIC.items():
        rows = [s for s in samples or [] if isinstance(s, dict) and s.get('kind') == k]; now = (weights or {}).get(k) or {}; base = {key: _f(now.get(key)) or w for key, _, w, _r in rubric}
        row = {'kind': k, 'n': len(rows), 'need': LEARN_MIN, 'mae': None, 'learnedMae': None, 'weights': None, 'ready': False, 'now': base}
        if len(rows) >= LEARN_MIN:
            cut = int(len(rows) * 0.75); fitted = _fit(base, rows[:cut]); row.update(mae=round(_mae(base, rows[cut:]), 4), learnedMae=round(_mae(fitted, rows[cut:]), 4), weights=fitted)
            row['ready'] = row['learnedMae'] < row['mae']
        out.append(row)
    return out


def load(root):
    try:
        d = json.loads((Path(root) / STORE).read_text())
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def apply(root, kind, fitted):
    """The owner's word: a kind moves to its fitted weights, each still inside its limits. → all weights"""
    k = kind_of(kind)
    if not k or not isinstance(fitted, dict):
        raise ValueError('No such kind.')
    base = {key: w for key, _, w, _r in RUBRIC[k]}; d = load(root)
    d[k] = {key: max(base[key] * 0.5, min(base[key] * 1.5, _f(fitted.get(key)) or base[key])) for key in base}
    (Path(root) / STORE).write_text(json.dumps(d))
    return d
