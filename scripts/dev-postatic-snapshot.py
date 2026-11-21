#!/usr/bin/env python3
"""🧪 DEV ONLY · Slice 27: a read-only snapshot of ONE agent's real PoStatic desk for `/dev/posdesk` on 51366.
Reads backend/data through the services' own view (`_ws_view`, the same answer `ws_open` gives the desk; never writes a file), keeps the
agent's PoStatic folders, its filed PoStatics, and the folder views + every version's page for its newest built folders. NO keys, logins,
sessions, wallet records or vault. Writes the gitignored frontend/public/dev-postatic.json — it never leaves this machine.

  PYTHONPATH=backend:. .venv/bin/python scripts/dev-postatic-snapshot.py <catId> [folders=5]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))


def main(cat_id, n=5):
    import feecat_service as rs
    cat = rs._load()['cats'][cat_id]
    rows = [w for w in rs._ws_list(cat) if w.get('kind') == 'build']
    ps = cat.get('psFolders') or []
    out = {'cat': {'id': cat_id, 'name': cat.get('name')}, 'workspaces': rows, 'psFolders': ps, 'docs': {}, 'versions': {}}
    built = []
    for w in sorted(rows, key=lambda r: -max([int(f.get('at') or 0) for f in ps if f.get('ws') == r['id']] + [int(r.get('at') or 0)])):
        v = rs._ws_view(cat_id, w['id'])
        if v.get('versions'):
            built.append((w, v))
        if len(built) >= n:
            break
    for w, v in built:
        v['savedToRepo'] = False; v['project'] = None
        out['docs'][w['id']] = v
        raw = rs._ws_load(cat_id, w['id']) or {}
        out['versions'][w['id']] = [{'i': i + 1, 'of': len(raw.get('versions') or []), 'by': r.get('by'), 'at': r.get('at'), 'lines': len(str(r.get('html') or '').splitlines()),
                                     'preview': rs._feat.preview(rs._ws_placed(cat_id, r.get('html') or ''))} for i, r in enumerate(raw.get('versions') or [])]
    dest = ROOT / 'frontend' / 'public' / 'dev-postatic.json'
    dest.write_text(json.dumps(out, default=str))
    print(f"{dest.name}: {len(rows)} folders, {len(ps)} filed, {len(built)} opened ({', '.join(w['name'] for w, _ in built)}), {dest.stat().st_size // 1024} KB")


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)
