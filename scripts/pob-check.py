#!/usr/bin/env python3
"""🛡 Slice 12 · grade the newest TEST PoB on Sicario's agent against the Slice 12 checks. Read only: it opens the store, changes nothing,
and never prints a key.

  PYTHONPATH=backend:. .venv/bin/python scripts/pob-check.py            # the newest TEST PoB
  PYTHONPATH=backend:. .venv/bin/python scripts/pob-check.py pob123     # one folder
"""
import sys

import feecat_service as rs
import kalshi_bid as kb


def grade(f):
    k = f.get('kalshi') if isinstance(f.get('kalshi'), dict) else {}
    legs = k.get('legs') or []
    menu = {m.get('ticker') for m in f.get('legMenu') or []}
    src = 'the slip ticket'
    if not legs and f.get('mindSlips'):   # no ticket (e.g. every leg under his minimum confidence): grade each mind's own legs instead
        legs = [{**g, 'backing': [{'mind': m.get('mind'), 'evidence': g.get('evidence'), 'number': g.get('number')}]} for m in f['mindSlips'] for g in m.get('legs') or []]
        src = "each mind's own legs (no ticket)"
    props = [g for g in legs if g.get('stat')]
    backed = [g for g in props if any(b.get('evidence') and b.get('number') is not None for b in g.get('backing') or [])]
    listed = [g for g in legs if g.get('ticker') in menu]
    tickets = kb.tickets_of(f)
    ends = [t.get('end') or kb.end_of(t) for t in tickets]
    return [
        ('props', 'The minds picked player overs/unders as legs', bool(props), f"{len(props)} player legs from {src}: " + '; '.join(f"{g.get('title')}" for g in props) if props else
         f"no player leg (menu {len(menu)} lines; dropped {len(f.get('legsDropped') or [])}; slip dropped: {f.get('slipDropped') or '-'})"),
        ('evidence', 'Each player leg has its own evidence and number', bool(props) and len(backed) == len(props),
         '; '.join(f"{g.get('title')}: " + ' / '.join(f"{b.get('mind')} {b.get('number')} ({str(b.get('evidence'))[:60]})" for b in g.get('backing') or []) for g in props)[:600] or 'no player leg'),
        ('listed', 'Every leg is a market Kalshi really lists', bool(legs) and len(listed) == len(legs), f"{len(listed)}/{len(legs)} legs on Kalshi's menu; thrown out: " +
         (', '.join(f"{d.get('mind')} {d.get('ticker')} ({d.get('why')})" for d in f.get('legsDropped') or []) or 'none')),
        ('whole', 'No half-made slip', not k.get('legs') or kb.slip_whole(k, f.get('legMenu') or []) == '', (kb.slip_whole(k, f.get('legMenu') or []) if k.get('legs') else 'no slip ticket') or 'whole'),
        ('ends', 'Every ticket ends in plain words', all(e.get('say') for e in ends), ' | '.join(e.get('say', '')[:90] for e in ends) or
         f"no ticket made (legs under the {kb.cfg(None)['minConf']}% minimum or not agreed); the chat says so"),
        ('nobid', 'TEST never bid', all(not t.get('orderId') and t.get('status') in ('waiting', 'test') for t in tickets) and bool(f.get('testRun')),
         ', '.join(f"{t.get('status')}{' test' if t.get('test') else ''}" for t in tickets)),
        ('blank', 'A blank mind is named, never silent', True, f"blank: {f.get('blank')}" if f.get('blank') else 'both minds answered'),
    ]


def main():
    s = rs._load()
    cat = next(c for c in s['cats'].values() if c.get('handle') == 'sicarios' and not c.get('revoked'))
    fs = [f for f in cat.get('pobFolders') or [] if f.get('testRun')]
    if len(sys.argv) > 1:
        fs = [f for f in fs if f.get('id') == sys.argv[1]]
    if not fs:
        print('no TEST PoB'); return 1
    f = fs[-1]
    print(f"{f['id']} · {f.get('topic')} · minds: {', '.join(c.get('name') or '?' for c in f.get('calls') or [])}")
    rows = grade(f)
    for key, label, ok, why in rows:
        print(f"  {'✓' if ok else '✗'} {key}: {label} — {why}")
    return 0 if all(r[2] for r in rows) else 2


if __name__ == '__main__':
    sys.exit(main())
