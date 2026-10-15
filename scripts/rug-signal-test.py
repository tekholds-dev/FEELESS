#!/usr/bin/env python3
"""☠ Rug early-warning test (read-only): reads data/rug_replay.json (scripts/rug-replay.py) and, per signal, counts rugs it caught ≥ 6s before the pull vs young WINNERS it would have sold. Ship a signal only if it catches rugs without selling winners.  python3 scripts/rug-signal-test.py"""
import json, sys, statistics as S
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'backend/data/rug_replay.json'))


def pull_time(rows):
    """First tx where the pool's SOL falls ≥ 50% in one go (the pull), else None."""
    prev = None
    for r in rows:
        ps = r.get('poolSol') or 0
        if prev and ps and ps < prev * 0.5:
            return r['t']
        if ps:
            prev = ps
    return None


def feats(rows, t, win=30):
    w = [r for r in rows if t - win <= (r['t'] or 0) <= t]
    if not w:
        return None
    sells = [r for r in w if r['side'] == 'sell']
    buys = [r for r in w if r['side'] == 'buy']
    s_sol = sum(max(0, -(r['sol'] or 0)) for r in sells)   # SOL that left the pool on sells
    b_sol = sum(max(0, r['sol'] or 0) for r in buys)
    pool_now = next((r['poolSol'] for r in reversed(w) if r.get('poolSol')), None)
    pool_before = next((r['poolSol'] for r in w if r.get('poolSol')), None)
    big = max([max(0, -(r['sol'] or 0)) / max(1e-9, pool_now or 1) for r in sells] or [0])
    return {'drop': (1 - pool_now / pool_before) * 100 if pool_before and pool_now else 0, 'sellers': len({r['w'] for r in sells}),
            'ratio': s_sol / max(1e-9, b_sol) if b_sol else (99 if s_sol else 0), 'big': big * 100, 'n': len(w)}


SIGNALS = {
    'pool −15% in 30s': lambda f: f['drop'] >= 15,
    'pool −25% in 30s': lambda f: f['drop'] >= 25,
    'sells 3× buys + 4 sellers': lambda f: f['ratio'] >= 3 and f['sellers'] >= 4,
    'one sell ≥ 8% of pool': lambda f: f['big'] >= 8,
    'one sell ≥ 15% of pool': lambda f: f['big'] >= 15,
}

rugs = [d for d in D if d['kind'] == 'rug' and d['rows']]
wins = [d for d in D if d['kind'] == 'win' and d['rows']]
print('windows: rugs', len(rugs), 'winners', len(wins))
for d in rugs:
    pt = pull_time(d['rows'])
    print(f"  {d['sym']:12} txs {len(d['rows']):4} pull {'—' if not pt else round(pt - d['buyAt'])}s after buy · held {round(d['exitAt'] - d['buyAt'])}s")
for name, sig in SIGNALS.items():
    caught = 0; lead = []
    for d in rugs:
        pt = pull_time(d['rows']) or d['exitAt']
        ts = sorted({r['t'] for r in d['rows'] if r['t'] and d['buyAt'] <= r['t'] < pt})
        hit = next((t for t in ts if (f := feats(d['rows'], t)) and sig(f)), None)
        if hit and pt - hit >= 6:
            caught += 1; lead.append(pt - hit)
    blocked = 0
    for d in wins:
        ts = sorted({r['t'] for r in d['rows'] if r['t'] and d['buyAt'] <= r['t'] <= d['exitAt']})
        if any((f := feats(d['rows'], t)) and sig(f) for t in ts):
            blocked += 1
    print(f"{name:28} rugs caught ≥6s early {caught}/{len(rugs)}" + (f" (lead med {S.median(lead):.0f}s)" if lead else '') + f" · winners it would have sold {blocked}/{len(wins)}")
