#!/usr/bin/env python3
"""🧭 SITE-5 · the route table, before and after a move. Moving a handler out of reputation_service.py must leave the app answering exactly the
same (method, path) pairs IN THE SAME ORDER (order decides which handler wins when two paths could match), with the same parameters.
  .venv/bin/python scripts/route-table.py --save      # before the move: writes backend/data/route_table.json (gitignored data folder)
  .venv/bin/python scripts/route-table.py --check     # after: exit 0 only when identical; prints any route that moved, vanished or appeared
  .venv/bin/python scripts/route-table.py --left      # what is still inside reputation_service.py, by kind: money · write · admin · read
Imports the app only (no server, no network). Money = a handler whose source signs, sends, quotes, swaps, withdraws or pays."""
import argparse
import inspect
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('FEELESS_NO_LOOPS', '1')
SNAP = ROOT / 'backend' / 'data' / 'route_table.json'
MONEY = re.compile(r'sendTransaction|_circle\(|_circle_post|signedTransaction|/swap|withdraw|_rpc_broadcast|broadcast\(|payout|refund|deposit|transfer|quote', re.I)


def table():
    import reputation_service as rs
    rows = []
    for r in rs.app.routes:
        ms = sorted(getattr(r, 'methods', None) or [])
        if not ms:
            continue
        ep = getattr(r, 'endpoint', None)
        params = sorted(inspect.signature(ep).parameters) if ep else []
        rows.append({'methods': ms, 'path': r.path, 'params': params, 'name': getattr(ep, '__name__', ''), 'module': getattr(ep, '__module__', '')})
    return rows


def kind(row, src):
    if 'admin' in row['path'] or '_require_owner' in src or '_require_admin' in src:
        return 'admin'
    if MONEY.search(src):
        return 'money'
    return 'write' if set(row['methods']) - {'GET', 'HEAD'} else 'read'


def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--save', action='store_true'); g.add_argument('--check', action='store_true'); g.add_argument('--left', action='store_true')
    a = ap.parse_args(); rows = table()
    if a.save:
        SNAP.write_text(json.dumps(rows, indent=0)); print(f'saved {len(rows)} routes → {SNAP.relative_to(ROOT)}'); return 0
    if a.check:
        old = json.loads(SNAP.read_text()); key = lambda r: (tuple(r['methods']), r['path'], tuple(r['params']))
        same = [key(r) for r in old] == [key(r) for r in rows]
        if not same:
            o, n = {key(r) for r in old}, {key(r) for r in rows}
            for k in sorted(o - n):
                print('GONE   ', *k)
            for k in sorted(n - o):
                print('NEW    ', *k)
            if o == n:
                print('ORDER CHANGED: same routes, different order (a wildcard may now shadow a static path)')
        moved = sum(1 for x, y in zip(old, rows) if x['module'] != y['module'])
        print(f"{'IDENTICAL' if same else 'DIFFERENT'} · {len(rows)} routes · {moved} now served from another module"); return 0 if same else 1
    import reputation_service as rs
    left = {'money': [], 'write': [], 'admin': [], 'read': []}
    for r in rows:
        if r['module'] != 'reputation_service':
            continue
        try:
            src = inspect.getsource(getattr(rs, r['name']))
        except (AttributeError, OSError, TypeError):
            src = ''
        left[kind(r, src)].append(f"{'/'.join(r['methods'])} {r['path']}")
    for k, v in left.items():
        print(f'{k:<6} {len(v)}')
    print(json.dumps(left, indent=1) if '-v' in sys.argv else '(add -v for the list)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
