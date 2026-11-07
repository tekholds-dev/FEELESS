"""⚖ HOW A PROOF SCORES (owner 2026-11-06: "true mechanical weights and ranks so all proofs dont get the same judgement"). Pure and tested.

Each kind of proof has its own parts and weights, each read from that proof's own record by code, not by a model. A part that is not known yet counts as nothing, so an unproven proof cannot rank high. The minds read these facts and argue with them inside a limit, and the owner's word stays last.

The py agents learn from OSSY and G4: once enough proofs of a kind are scored, `learn` fits how the minds really weigh each part and tests it on proofs it did not see. It only proposes. The owner applies it, and no weight may move past half or one and a half times its start."""
import json
from pathlib import Path

STORE = 'proof_weights.json'
LEARN_MIN = 12
MINDS_LIFT = 0.15   # the minds may lift a proof at most this part of the top above what its record shows
MINDS_PART = 0.4
FLAWLESS = 0.95
ALIASES = {'pow': 'pow', 'pop': 'pop', 'pob': 'pob', 'poc': 'poc', 'pos': 'pos', 'postatic': 'pos', 'bids': 'pob'}
RANKS = ((0.9, 'S'), (0.75, 'A'), (0.55, 'B'), (0.35, 'C'), (0.0, 'D'))


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


def _both(f, key='whys'):
    n = _n(f.get(key)) or _n(f.get('calls'))
    return _clip(n / 2), f'{n} of 2 minds on file'


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
    return _clip(n / 3), f'{n} builds studied'


def _filed(f):
    return (1.0, 'Filed') if _closed(f) else (0.0, 'Not filed')


# kind → [(part, what it is, weight, how to read it)]. Each kind's weights add up to 100.
RUBRIC = {
    'pow': [('result', 'Real result', 30, _pow_result), ('real', 'Real money', 20, _pow_real), ('hold', 'Hold time', 15, _pow_hold), ('evidence', 'Evidence', 15, _pow_evidence), ('exits', 'Exits set first', 10, _pow_exits), ('minds', 'Both minds', 10, _both)],
    'pop': [('result', 'Practice result', 35, _pop_result), ('sources', 'Sources read', 20, _pop_sources), ('reads', 'True prices', 15, _pop_reads), ('plan', 'Exits on calls', 15, _pop_plan), ('blind', 'Blind calls', 15, _pob_blind)],
    'pob': [('result', 'Real result', 30, _mark), ('evidence', 'What it read', 25, _pob_evidence), ('series', 'Its run', 15, _pob_series), ('odds', 'Games and odds', 15, _pob_odds), ('blind', 'Blind picks', 15, _pob_blind)],
    'poc': [('mark', 'Your mark', 35, _mark), ('trends', 'Trends read', 20, _poc_trends), ('earned', 'What it earned', 15, _poc_earned), ('shots', 'Snapshots', 15, _shots3), ('pitch', 'Pitches', 15, _poc_pitch)],
    'pos': [('mark', 'Your mark', 40, _mark), ('review', 'Second mind', 20, _pos_review), ('plan', 'Its plan', 15, _pos_plan), ('refs', 'Builds studied', 15, _pos_refs), ('filed', 'Filed', 10, _filed)],
}


def kind_of(kind):
    return ALIASES.get(str(kind or '').lower())


def rank_of(frac, all_known=True):
    """S needs every part known: nothing unproven tops the board."""
    got = next(r for lo, r in RANKS if frac >= lo)
    return 'A' if got == 'S' and not all_known else got


def view(kind, folder, top=300.0, weights=None):
    """→ {kind, frac, score, rank, known, parts:[{key,label,weight,value,note}]}, or None for a kind with no rubric. A part that is not known scores nothing."""
    k = kind_of(kind)
    if not k or not isinstance(folder, dict):
        return None
    mine = (weights or {}).get(k) or {}; parts = []
    for key, label, w, read in RUBRIC[k]:
        try:
            v, note = read(folder)
        except (TypeError, ValueError, AttributeError, KeyError):
            v, note = None, 'Could not be read'
        parts.append({'key': key, 'label': label, 'weight': round(_f(mine.get(key)) or w, 2), 'value': None if v is None else round(v, 3), 'note': note})
    total = sum(p['weight'] for p in parts) or 1.0; frac = sum(p['weight'] * (p['value'] or 0.0) for p in parts) / total; known = all(p['value'] is not None for p in parts)
    return {'kind': k, 'frac': round(frac, 4), 'score': round(frac * float(top), 1), 'top': float(top), 'rank': rank_of(frac, known), 'known': known, 'parts': parts}


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
    return f"FACTS CHECKED BY CODE, score against these: {rows}. On the record alone this is {v['score']:g} of {v['top']:g}, rank {v['rank']}."


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
