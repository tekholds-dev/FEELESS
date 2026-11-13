"""🧪 EVOLUTION LAB (COL-11, Supreme Intelligence). Pure + tested (`tests/test_evolution_lab.py`).

One role's exit settings evolve like a model, never on one lucky trade:
  FREEZE      the generation in control is frozen: its params + a hash, never edited after.
  CHALLENGE   a challenger is searched on the OLDEST 60% of real closed positions only (the learn set).
  HELD-OUT    both are replayed on the NEWEST 40% — exits the challenger never saw. Every changed exit is a SHADOW TRADE row.
  GATE        promote only if: ≥ MIN_HELD held-out exits, ≥ MIN_CHANGED of them exit differently, the held-out mean beats the
              baseline by ≥ EDGE_PTS, and it is not worse on the learn set. Anything less is HOLD or REJECT, with the reason.
  ROLLBACK    any promoted generation can be undone to the one before; every step is appended to the history, never rewritten.
The lab keeps its OWN ledger. It never writes the live trading tunables — applying a promoted generation is the owner's call.
"""
import hashlib
import itertools
import json

HELD_FRAC = 0.4
MIN_HELD = 20
MIN_CHANGED = 5
EDGE_PTS = 0.5      # mean exit % points on the held-out set


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def phash(params):
    return hashlib.sha256(json.dumps({k: round(_f(v), 4) for k, v in sorted((params or {}).items())}, separators=(',', ':')).encode()).hexdigest()[:16]


def split(positions):
    """Chronological: (learn = oldest 60%, held = newest 40%). Only positions with a recorded path count."""
    ps = sorted((p for p in positions or [] if p.get('path')), key=lambda p: _f(p.get('closedAt')))
    cut = int(round(len(ps) * (1 - HELD_FRAC)))
    return ps[:cut], ps[cut:]


def score(positions, params, replay, take):
    xs = [replay(p['path'], params, take) for p in positions]
    if not xs:
        return {'n': 0, 'mean': 0.0, 'win': 0.0}
    return {'n': len(xs), 'mean': round(sum(xs) / len(xs), 3), 'win': round(sum(1 for x in xs if x > 0) / len(xs), 3)}


def challenger(base, tunable, learn, replay, take, steps=3):
    """Grid search on the LEARN set only, inside each tunable's (lo, hi) bounds. → the best params (the baseline when nothing beats it)."""
    keys = [k for k in tunable if k in base and k != 'timeMaxMin']
    grids = []
    for k in keys:
        _d, lo, hi = tunable[k][:3]
        grids.append(sorted({round(lo + (hi - lo) * i / (steps - 1), 2) for i in range(steps)} | {round(_f(base[k]), 2)}))
    best, best_s = dict(base), score(learn, base, replay, take)['mean']
    for combo in itertools.product(*grids):
        p = {**base, **dict(zip(keys, combo))}
        s = score(learn, p, replay, take)['mean']
        if s > best_s + 1e-9:
            best, best_s = p, s
    return best


def judge(base, chall, positions, replay, take):
    """Baseline vs challenger, learn and held-out, the shadow trades, and the gate's verdict with its reason."""
    learn, held = split(positions)
    bl, cl = score(learn, base, replay, take), score(learn, chall, replay, take)
    bh, ch = score(held, base, replay, take), score(held, chall, replay, take)
    shadow = []
    for p in held:
        a, b = replay(p['path'], base, take), replay(p['path'], chall, take)
        if abs(a - b) > 1e-9:
            shadow.append({'sym': p.get('sym') or '?', 'closedAt': round(_f(p.get('closedAt'))), 'base': round(a, 2), 'chall': round(b, 2), 'diff': round(b - a, 2)})
    edge_h, edge_l = round(ch['mean'] - bh['mean'], 3), round(cl['mean'] - bl['mean'], 3)
    if phash(base) == phash(chall):
        verdict, why = 'HOLD', 'Nothing beat the frozen baseline on the learn set.'
    elif bh['n'] < MIN_HELD:
        verdict, why = 'HOLD', f'{bh["n"]} of {MIN_HELD} held-out exits: too few to judge.'
    elif len(shadow) < MIN_CHANGED:
        verdict, why = 'HOLD', f'Only {len(shadow)} held-out exits change ({MIN_CHANGED} needed). One trade is never learning.'
    elif edge_h >= EDGE_PTS and edge_l >= 0:
        verdict, why = 'PROMOTE', f'Beats the baseline by {edge_h:+.2f} pts on {bh["n"]} exits it never saw, and holds on the learn set ({edge_l:+.2f}).'
    else:
        verdict, why = 'REJECT', f'Held-out edge {edge_h:+.2f} pts (needs {EDGE_PTS:+.2f}), learn edge {edge_l:+.2f}: it fit the past, not the future.'
    return {'learn': {'n': bl['n'], 'base': bl, 'chall': cl, 'edge': edge_l}, 'held': {'n': bh['n'], 'base': bh, 'chall': ch, 'edge': edge_h},
            'shadow': sorted(shadow, key=lambda r: -abs(r['diff']))[:40], 'changed': len(shadow), 'verdict': verdict, 'why': why}


def _gen_rows(ledger):
    return [e for e in ledger if e.get('action') in ('freeze', 'promote', 'rollback')]


def baseline(ledger):
    """The generation in control: the last freeze / promote / rollback row."""
    rows = _gen_rows(ledger)
    return rows[-1] if rows else None


def run(ledger, role, current, tunable, positions, replay, take, now):
    """One lab pass, appended to `ledger` (in place): freeze the baseline if none, search a challenger, judge it, promote on PASS."""
    base = baseline(ledger)
    if not base:
        base = {'action': 'freeze', 'role': role, 'gen': 1, 'params': dict(current), 'hash': phash(current), 'at': round(now)}
        ledger.append(base)
    learn, _held = split(positions)
    chall = challenger(base['params'], tunable, learn, replay, take)
    j = judge(base['params'], chall, positions, replay, take)
    row = {'action': 'challenge', 'role': role, 'gen': base['gen'], 'params': chall, 'hash': phash(chall), 'at': round(now),
           'verdict': j['verdict'], 'why': j['why'], 'held': j['held'], 'learn': j['learn'], 'changed': j['changed']}
    ledger.append(row)
    if j['verdict'] == 'PROMOTE':
        ledger.append({'action': 'promote', 'role': role, 'gen': base['gen'] + 1, 'params': chall, 'hash': phash(chall), 'from': base['hash'], 'at': round(now), 'why': j['why']})
    return j


def rollback(ledger, now):
    """Undo the generation in control to the one before it. → the new baseline row, or None at generation 1."""
    rows = _gen_rows(ledger)
    if len(rows) < 2:
        return None
    prev = rows[-2]
    row = {'action': 'rollback', 'role': prev.get('role'), 'gen': rows[-1]['gen'] + 1, 'params': dict(prev['params']), 'hash': prev['hash'], 'from': rows[-1]['hash'], 'at': round(now), 'why': f'Rolled back to generation {prev["gen"]}.'}
    ledger.append(row)
    return row


def history(ledger):
    """Generation history, newest first, for the page."""
    return [{k: e.get(k) for k in ('action', 'gen', 'hash', 'at', 'verdict', 'why', 'params')} for e in reversed(ledger)][:60]
