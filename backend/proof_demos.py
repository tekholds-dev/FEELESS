"""🖼 The real demo gallery. Each proof type's best real filed proof and its worst, from staff agents only.
Only what is named here leaves: no wallets, mints, prompts, owners' notes or model names. Nothing is made up: a type nobody filed shows empty."""
import hashlib
import re

KINDS = [('PoW', 'powFolders', 'Traded on-chain, with what it read'), ('PoP', 'popFolders', 'A perp call, with the real reason'), ('PoB', 'pobFolders', 'A game or market call, graded by the score'),
         ('PoC', 'pocFolders', 'Content planned, made and marked'), ('PoStatic', 'psFolders', 'A page it built, tried and reviewed')]
MAX_PARTS = 8


def _n(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _len(v):
    return len(v) if isinstance(v, (list, dict)) else 0


def verdict(kind, f):
    """(good | bad | open, words). Read from its own record."""
    if f.get('noTrade'):
        return 'open', 'Passed: no trade'
    if kind == 'PoW':
        if f.get('pnlPct') is None:
            return 'open', 'No fill' if f.get('status') == 'closed' else 'Still open'
        p = _n(f.get('pnlPct'))
        return ('good' if p > 0 else 'bad'), f'{p:+.1f}%'
    g = f.get('graded')
    return ('good', 'Marked right') if g == 'right' else ('bad', 'Marked wrong') if g == 'wrong' else ('open', 'Not marked yet')


def facts(kind, f):
    if kind == 'PoW':
        held = round((_n(f.get('soldAt')) - _n(f.get('boughtAt'))) / 60) if f.get('soldAt') and f.get('boughtAt') else None
        rows = [['Money', 'Real' if f.get('real') else 'Paper'], ['Sites shot', _len(f.get('shots'))], ['Read rounds', _len(f.get('scout'))]]
        return rows + ([['Held', f'{held} min']] if held is not None else [])
    if kind == 'PoP':
        return [['Money', 'Paper' if f.get('paper') else 'Real'], ['Calls', _len(f.get('calls'))], ['Reads', _len(f.get('reads'))], ['Sources', _len(f.get('sources'))]]
    if kind == 'PoB':
        return [['Money', 'Paper' if f.get('paper') else 'Real'], ['Games', _len(f.get('games'))], ['Calls', _len(f.get('calls'))], ['Sites shot', _len(f.get('shots'))]]
    if kind == 'PoC':
        return [['Money', 'Paper'], ['Calls', _len(f.get('calls'))]]
    return [['Version', int(_n(f.get('version')))], ['Steps', _len(f.get('steps'))], ['References', _len(f.get('refs'))]]


def card(kind, cid, f, v, title, clean=str):
    """One proof, whitelisted. clean strips internal names from its words."""
    tone, said = verdict(kind, f)
    if kind == 'PoW' and f.get('sym'):
        title = f"${f['sym']}"
    elif str(title or '').startswith('Proof #'):
        title = {'PoP': 'Perp read', 'PoB': 'Game read', 'PoC': 'Content plan'}.get(kind, kind)
    return {'id': hashlib.sha256(f"{cid}:{f.get('id')}".encode()).hexdigest()[:16], 'print': str(f.get('id') or ''), 'kind': kind, 'title': clean(str(title or kind))[:70], 'at': f.get('at'),
            'tone': tone, 'said': said, 'why': re.sub(r'\s*→\s*\w*:?\s*$', '', clean(str(f.get('why') or '')))[:170], 'rank': v.get('rank'), 'score': v.get('score'), 'top': v.get('top'), 'frac': v.get('frac'), 'held': clean(str(v.get('held') or ''))[:90],
            'parts': [{'label': p.get('label'), 'value': p.get('value'), 'weight': p.get('weight')} for p in (v.get('parts') or [])[:MAX_PARTS]], 'facts': facts(kind, f), 'page': kind in ('PoStatic',) and bool(f.get('ws'))}


def pick(rows):
    """[(folder, view)] → the best, plus the worst when it really failed and is not the same proof. Unscored and unfiled proofs never show."""
    done = [(f, v) for f, v in rows if v and f.get('status') == 'closed']
    if not done:
        return []
    done.sort(key=lambda r: (-_n(r[1].get('frac')), -_n(r[0].get('at'))))
    best = done[0]; bad = [r for r in done[1:] if verdict(r[1].get('kind') or '', r[0])[0] == 'bad' or r[0].get('graded') == 'wrong' or _n(r[0].get('pnlPct')) < 0]
    return [best] + ([bad[-1]] if bad else [])
