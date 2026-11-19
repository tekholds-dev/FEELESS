#!/usr/bin/env python3
"""🧪 DEV ONLY · Slice 14: one agent's real GitHub-folder proof files, built by the same code its folder uses (collective_git.agent_tree +
proof_file, then the leak guard), for `/dev/chats?proofs`. Reads backend/data, never writes it. Writes frontend/public/dev-git-agent.json
(never committed; it stays on this machine).   .venv/bin/python scripts/dev-git-agent.py <catId>"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))


def main(cat_id):
    import collective_git as cg
    import proof_file as pf
    import visitor_view as vv
    cat = json.loads((ROOT / 'backend' / 'data' / 'feecats.json').read_text())['cats'][cat_id]
    by = pf.index_calls(pf.read_calls(ROOT / 'backend' / 'data' / 'mind_calls.jsonl'))
    files = cg.without_leaks(cg.agent_tree(cat, lambda f: pf.redact(vv.public_folder(f)), record=lambda k, f: pf.record(k, f, cat_id=cat_id, by_ref=by, bids=cat.get('kalshiBids') or [])))[0]
    out = {'name': cat.get('name'), 'files': {p: json.loads(v) if p.endswith('.json') else v.decode('utf-8', 'replace')[:2000] for p, v in files.items() if p.startswith('proofs/') or p == 'index.json'}}
    (ROOT / 'frontend' / 'public' / 'dev-git-agent.json').write_text(json.dumps(out, default=str))
    print(f"{sum(p.startswith('proofs/') for p in out['files'])} proof files")


if __name__ == '__main__':
    main(sys.argv[1])
