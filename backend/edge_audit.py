"""🧪 EDGE AUDIT + PROOF GATE (pure, tested). Is there ANY rule in our own records that makes money after costs, on coins it was not
picked from? (owner, 2026-10-10, card $28.50 → $0.47: "you just do small tasks and not thinking of the bigger picture" … "fix".)

`audit(brain_done, agent_done, cost)`: every feature and feature pair of the trench brain's watched coins (each watched an hour;
vanished = −100%) is learned on the oldest 60% and tested on the newest 40%, after a round-trip `cost` %. Means are capped at +100% a
coin so one freak cannot decide a bucket. A rule PASSES only when its capped mean AND its median are above zero in BOTH halves.
→ {n, cost, base, tested, trainPos, held, rules, agents, at}.

`gate(audit, min_n)`: the PROOF GATE's verdict — 'hold' while no rule passes (the real card stops BUYING; its stops, rug shield and
profit takes keep running; the owner's own picks still work), 'trade' once one does, 'wait' when there is too little data to judge."""
import collections
import itertools
import statistics as st

COST = 3.0            # % round trip: ~1.5% a swap, measured on the real card's own fills
TRAIN, MIN_TRAIN, MIN_TEST = 0.6, 40, 25
MIN_COINS = 500       # under this many watched coins the gate does not judge
_cap = lambda v: min(100.0, v)


def _end(x, cost):
    if x.get('gone'):
        return -100.0
    return None if x.get('end') is None else float(x['end']) - cost


def _card(vals):
    r = [v for v in vals if v is not None]
    if not r:
        return {'n': 0, 'med': None, 'avg': None, 'up': None}
    return {'n': len(r), 'med': round(st.median(r), 1), 'avg': round(st.mean(map(_cap, r)), 1), 'up': round(sum(1 for v in r if v > 0) / len(r) * 100)}


def audit(brain_done, agent_done=None, cost=COST, now=0.0):
    d = sorted((x for x in brain_done or [] if x.get('f')), key=lambda x: x.get('at') or 0)
    cut = int(len(d) * TRAIN)
    tr, te = d[:cut], d[cut:]
    keys = list(collections.Counter(f for x in d for f in x['f']))
    cells = [(k,) for k in keys] + [tuple(sorted(p)) for p in itertools.combinations(keys, 2) if p[0].split(':')[0] != p[1].split(':')[0]]
    tested = train_pos = 0
    rules = []
    for c in cells:
        a = [v for v in (_end(x, cost) for x in tr if all(k in x['f'] for k in c)) if v is not None]
        b = [v for v in (_end(x, cost) for x in te if all(k in x['f'] for k in c)) if v is not None]
        if len(a) < MIN_TRAIN or len(b) < MIN_TEST:
            continue
        tested += 1
        if st.mean(map(_cap, a)) > 0 and st.median(a) > 0:
            train_pos += 1
            if st.mean(map(_cap, b)) > 0 and st.median(b) > 0:
                rules.append({'rule': list(c), **_card(b)})
    ag = {}
    for h in ('p5', 'p15', 'p60'):
        for kind in ('enter', 'wait'):
            ag[f'{kind}{h[1:]}'] = _card(x[h] - cost for x in agent_done or [] if x.get('kind') == kind and x.get(h) is not None)
    return {'n': len(d), 'cost': cost, 'base': _card(_end(x, cost) for x in d), 'old': _card(_end(x, cost) for x in d if 'age:12h+' in x['f']),
            'tested': tested, 'trainPos': train_pos, 'held': len(rules), 'rules': sorted(rules, key=lambda r: -r['avg'])[:8], 'agents': ag, 'at': now}


def gate(a, min_n=MIN_COINS):
    if not a or int(a.get('n') or 0) < min_n or not a.get('tested'):
        return 'wait'
    return 'trade' if int(a.get('held') or 0) > 0 else 'hold'


def words(a):
    """One line for the card and the inbox."""
    if gate(a) == 'wait':
        return f"🧪 proof gate: only {int((a or {}).get('n') or 0)} coins on record — not enough to judge yet"
    b = a['base']
    if a['held']:
        r = a['rules'][0]
        return f"🧪 proof gate: {a['held']} of {a['tested']} rules pass on unseen coins — best: {' + '.join(r['rule'])} ({r['med']:+.1f}% typical, n {r['n']})"
    return (f"🧪 proof gate: 0 of {a['tested']} rules make money after a {a['cost']:g}% round trip on unseen coins "
            f"({a['n']} coins: {b['med']:+.0f}% typical in an hour, {b['up']}% up) — the engine is not buying with real money until one does")
