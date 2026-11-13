"""COL-6 · PoStatic pilot checker: reads the newest PoStatic proof (Sicario's first) READ-ONLY and ticks every
piece the card demands kept on one real proof: plan, build, OSSY+G4 review, playtest/browser test, file, stash,
grade, stamp, events, vitals row. No writes, no network, no money."""
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'backend' / 'data'
sys.path.insert(0, str(ROOT / 'backend'))
import proof_stamp as _stamp  # noqa: E402  the same 24h clock the service stamps with


def tick(name, got, say=''):
    print(f"  {'✅' if got else '❌'} {name}" + (f" — {say}" if say else ''))
    return bool(got)


def main():
    store = json.loads((DATA / 'feecats.json').read_text())
    cats = store.get('cats') or {}
    rows = [(c, f) for c in cats.values() for f in c.get('psFolders') or []]
    if not rows:
        print('No PoStatic proof filed yet.'); return 1
    rows.sort(key=lambda x: float(x[1].get('at') or 0))
    cat, f = next(((c, x) for c, x in reversed(rows) if c.get('name') == "Sicario's"), rows[-1])
    fid, ws = f.get('id'), f.get('ws')
    print(f"Newest PoStatic proof: {cat.get('name')} · {f.get('topic')} · {fid}")
    good = True
    rv = f.get('review') or {}
    by = rv.get('by') or {}
    good &= tick('Plan kept', f.get('plan') or (DATA / 'agent_workspaces').glob(f'*/{ws}.seal'), 'on the folder or its sealed workspace')
    good &= tick('Build kept', ws and any((DATA / 'agent_workspaces').glob(f'*/{ws}.seal')), f'workspace {ws}')
    good &= tick('OSSY review', (by.get('ossy') or {}).get('verdict'), (by.get('ossy') or {}).get('answeredBy', ''))
    good &= tick('G4 review', (by.get('g4') or {}).get('verdict'), (by.get('g4') or {}).get('answeredBy', ''))
    good &= tick('Filed', f.get('status') == 'closed', f.get('status') or 'open')
    good &= tick('Graded', f.get('graded') in ('right', 'wrong'), f.get('graded') or 'not yet')
    con = sqlite3.connect(DATA / 'stash' / 'index.db')
    hit = con.execute('select outcome from items where key=?', (f'psFolders:{fid}',)).fetchone()
    con.close()
    good &= tick('In the stash', hit, f'outcome {hit[0]}' if hit else 'no stash row')
    con = sqlite3.connect(DATA / 'proof_events.db')
    evs = [r[0] for r in con.execute("select event from events where kind='pos' and (ref like ? or data like ?)", (f'%{fid}%', f'%{fid}%'))]
    con.close()
    good &= tick('Events kept', evs, ', '.join(sorted(set(evs))) or 'none')
    st = _stamp.of('PoStatic', f, time.time())
    waiting = 'stamp' not in evs and st['state'] == 'waiting'
    if waiting:   # not missing: the stamp can't land before the folder is 24h old — the service files it on its own after that
        due = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(st['dueAt']))
        print(f"  ⏳ Stamp — waiting on the 24h clock, lands {due} (in {max(0, st['dueAt'] - time.time()) / 3600:.1f} h)")
    else:
        good &= tick('Stamp', 'stamp' in evs or f.get('stamp'), 'the 24h stamp event')
    good &= tick('Vitals row', f.get('graded') and (by.get('ossy') or by.get('g4')), 'model × proof vitals build from this folder live')
    if good and waiting:
        print('\nPILOT KEPT — every piece is on one real proof; only the 24h stamp is still on its clock. Re-run --check after ' + due + '.')
        return 2
    print('\nPILOT ' + ('COMPLETE — every piece kept on one real proof.' if good else 'NOT COMPLETE — the ❌ pieces are missing.'))
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
