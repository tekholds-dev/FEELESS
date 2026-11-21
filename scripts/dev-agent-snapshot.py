#!/usr/bin/env python3
"""🧪 DEV ONLY · a read-only snapshot of ONE agent's real desk data for the `/dev/cats?live=<kind>` preview (the chat while a proof runs).
Reads backend/data (never writes it), keeps only what the desk draws: name, its two models, its last chat lines, its newest proof folders of
every kind and the code of its newest PoStatic pages. NO keys, logins, site sessions, mailbox, wallet records or vault. Writes the
gitignored frontend/public/dev-agent.json — it never leaves this machine.

  .venv/bin/python scripts/dev-agent-snapshot.py <catId>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
KINDS = {'powFolders': 3, 'psFolders': 4, 'pobFolders': 3, 'pocFolders': 3, 'popFolders': 2, 'poeFolders': 2}


def main(cat_id):
    import cat_keys as ck
    cat = json.loads((ROOT / 'backend' / 'data' / 'feecats.json').read_text())['cats'][cat_id]
    out = {'id': cat_id, 'name': cat.get('name'), 'brains': (cat.get('brainsCfg') or {}).get('brains') or [],
           'chat': [{k: m.get(k) for k in ('by', 'text', 'at', 'open')} for m in (cat.get('chat') or [])[-40:]],
           **{k: (cat.get(k) or [])[-n:] for k, n in KINDS.items()}, 'docs': {}}
    for f in out['psFolders'] + out['pocFolders']:
        ws = f.get('ws')
        p = ROOT / 'backend' / 'data' / 'agent_workspaces' / cat_id / f'{ws}.seal'
        if not ws or not p.exists():
            continue
        try:
            d = json.loads(ck.unseal_bytes(p.read_bytes(), cat_id))
        except Exception:
            continue
        html = ((d.get('versions') or [{}])[-1] or {}).get('html') or ''
        out['docs'][ws] = {'code': html, 'preview': html, 'name': d.get('name'), 'messages': (d.get('messages') or [])[-12:]}
    dst = ROOT / 'frontend' / 'public' / 'dev-agent.json'
    dst.write_text(json.dumps(out))
    print(f"wrote {dst.relative_to(ROOT)}: {len(out['chat'])} chat · " + ' · '.join(f"{len(out[k])} {k}" for k in KINDS) + f" · {len(out['docs'])} pages")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
