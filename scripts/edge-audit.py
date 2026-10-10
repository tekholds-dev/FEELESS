#!/usr/bin/env python3
"""EDGE AUDIT (read-only): is there ANY rule in our own records that makes money after costs, on data it was not picked from?

  .venv/bin/python scripts/edge-audit.py [round-trip cost %, default 3]

Reads backend/data/trench_brain.json (every busy / new launch coin watched for an hour) and agents.json (every agent call with its
5 / 15 / 60-minute result). For every feature and feature pair: learn on the oldest 60%, test on the newest 40%. A vanished coin = −100%.
Means are capped at +100% a coin so one freak cannot decide a bucket. Prints the baseline, the groups that matter and how many rules
survive. Run it BEFORE building or funding anything that buys launch coins."""
import collections, itertools, json, statistics as st, sys
from pathlib import Path

COST = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
DATA = Path(__file__).resolve().parent.parent / 'backend' / 'data'
cap = lambda v: min(100.0, v)


def line(name, vals):
    r = [v for v in vals if v is not None]
    if not r:
        return f'  {name:26} n 0'
    return f"  {name:26} n {len(r):5} · typical {st.median(r):+6.1f}% · capped avg {st.mean(map(cap, r)):+6.1f}% · {sum(1 for v in r if v > 0) / len(r) * 100:3.0f}% up"


def main():
    d = sorted(json.load(open(DATA / 'trench_brain.json')).get('done') or [], key=lambda x: x['at'])
    end = lambda x: -100.0 if x.get('gone') else (float(x['end']) - COST if x.get('end') is not None else None)
    print(f'EDGE AUDIT · round-trip cost {COST:g}% · {len(d)} coins watched for an hour')
    print(line('hold 1 hour', map(end, d)))
    print(line('out at +50 / −30', (float(x['play']) - COST if x.get('play') is not None else None for x in d)))
    for tag in ('age:<15m', 'age:15-60m', 'age:1-3h', 'age:3-12h', 'age:12h+', 'cap:1M+', 'safe:yes', 'stage:graduated', 'stage:curve'):
        print(line(tag, (end(x) for x in d if tag in x['f'])))
    cut = int(len(d) * 0.6)
    tr, te = d[:cut], d[cut:]
    keys = list(collections.Counter(f for x in d for f in x['f']))
    cells = [(k,) for k in keys] + [tuple(sorted(p)) for p in itertools.combinations(keys, 2) if p[0].split(':')[0] != p[1].split(':')[0]]
    tested = train_pos = held = 0
    for c in cells:
        a = [end(x) for x in tr if all(k in x['f'] for k in c)]; a = [v for v in a if v is not None]
        b = [end(x) for x in te if all(k in x['f'] for k in c)]; b = [v for v in b if v is not None]
        if len(a) < 40 or len(b) < 25:
            continue
        tested += 1
        if st.mean(map(cap, a)) > 0 and st.median(a) > 0:
            train_pos += 1
            if st.mean(map(cap, b)) > 0 and st.median(b) > 0:
                held += 1; print('  ✅', ' + '.join(c), line('', b))
    print(f'  rules tested {tested} · positive where they were learned {train_pos} · still positive on unseen coins {held}')
    a = sorted(json.load(open(DATA / 'agents.json')).get('done') or [], key=lambda x: x['at'])
    print(f'\nAGENT CALLS · {len(a)} judged')
    for h in ('p5', 'p15', 'p60'):
        for kind in ('enter', 'wait'):
            print(line(f'{kind} → {h[1:]} min', (x[h] - COST for x in a if x.get('kind') == kind and x.get(h) is not None)))
    print(line('wait → 5 min, NO cost', (x['p5'] for x in a if x.get('kind') == 'wait' and x.get('p5') is not None)))
    print('\nA rule is worth real money only when it is positive on coins it was not picked from. 0 = there is no edge here yet.')


if __name__ == '__main__':
    main()
    sys.path.insert(0, str(DATA.parent))
    import edge_audit as ea
    a = ea.audit(json.load(open(DATA / 'trench_brain.json')).get('done') or [], json.load(open(DATA / 'agents.json')).get('done') or [], COST)
    print('\nGATE:', ea.gate(a).upper(), '·', ea.words(a))
