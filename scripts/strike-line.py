#!/usr/bin/env python3
"""✗ Strike an agent desk line that claims a withdraw which never landed on chain (staff, this machine only — the server's internal key).
The live route proves it on chain first (a line that landed, is under 3 min old, or can't be proven is refused); the line is kept, marked
struck, and hidden from every feed. Moves no money.

  .venv/bin/python scripts/strike-line.py <catId> <eventId>      (no eventId: lists that agent's withdraw lines and their ids)
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(cat_id, event_id=None):
    if not event_id:
        store = json.loads((ROOT / 'backend' / 'data' / 'feecats.json').read_text())
        for e in store.get('events') or []:
            if e.get('catId') == cat_id and e.get('type') == 'WITHDRAW':
                print(f"{e['id']}  {'STRUCK ' if e.get('voided') else ''}{e.get('detail')}")
        return 0
    key = (ROOT / 'backend' / 'data' / 'internal.key').read_text().strip()
    req = urllib.request.Request(f'http://127.0.0.1:5077/api/reputation/cats/{cat_id}/events/{event_id}/void', b'{}',
                                 {'content-type': 'application/json', 'x-feeless-internal': key})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            print('✗ struck:', json.loads(r.read()).get('struck')); return 0
    except urllib.error.HTTPError as e:
        print('not struck:', json.loads(e.read() or b'{}').get('detail') or e.code); return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:3]))
