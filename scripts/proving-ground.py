#!/usr/bin/env python3
"""🏟 COL-19 · run the proving ground on the FREE local minds (OSSY = this Mac's LM Studio, G4 = the desktop's, over the LAN).
Fake coins, fake traps; no chain, no wallet, no paid model. Each batch is filed on Fee's Test bench (Proofs › Test bench) and the
mind's whole record decides its live permission (backend/data/proving_ground.json).
  .venv/bin/python scripts/proving-ground.py --mind ossy --n 30
  .venv/bin/python scripts/proving-ground.py --mind g4 --n 30
  .venv/bin/python scripts/proving-ground.py --mind rules --n 30      # the arena's reference player (proves every trap is answerable)"""
import argparse
import asyncio
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import proving_ground as pg   # noqa: E402
import test_bench as tb   # noqa: E402

DATA = ROOT / 'backend' / 'data'
REC = DATA / 'proving_ground.json'
MODEL = {'ossy': 'local/ossy', 'g4': 'local/g4'}


async def ask(mind, s):
    if mind == 'rules':
        return pg.rules_mind(s), 0.0
    import feecat_service as fs   # its own LM Studio or nothing: no fallback (owner 2026-11-13)
    t = time.time(); text, _usd = await fs._lm_call_one(MODEL[mind], [{'role': 'user', 'content': pg.prompt(s)}], 40)
    return text or '', time.time() - t


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--mind', choices=('ossy', 'g4', 'rules'), default='ossy'); ap.add_argument('--n', type=int, default=30)
    a = ap.parse_args()
    rec = json.loads(REC.read_text()) if REC.exists() else {}
    rows = rec.get(a.mind, []); start = len(rows); t0 = time.time(); silent = 0
    for i in range(start, start + a.n):
        s = pg.scenario(i); said, secs = await ask(a.mind, s)
        if not str(said).strip():
            silent += 1
            if silent >= 3:
                print(f'{a.mind} is not answering (3 silent in a row). Stopped; nothing was faked.'); break
            continue
        silent = 0; g = pg.grade(s, said); g['secs'] = round(secs, 2); rows.append(g)
        print(f"{s['id']:>6} {s['kind']:<6} said {g['said'] or '—':<8} {'✓' if g['ok'] else '✗ (' + g['right'] + ')'}")
    rec[a.mind] = rows; REC.write_text(json.dumps(rec))
    batch = rows[start:]; v = pg.permit(rows)
    if batch:
        ok = sum(x['ok'] for x in batch)
        tb.file_run(DATA, 'leader', kind='other', title=f"Proving ground · {a.mind.upper()} · {ok}/{len(batch)} right", ok=v['live'], why=v['why'],
                    models=[MODEL.get(a.mind, 'rules')], cost_usd=0.0, secs=time.time() - t0,
                    steps=[f"{k}: {b['ok']}/{b['n']}" for k, b in v['byKind'].items()], files={'runs.json': json.dumps(batch, indent=1)}, by='Claude')
    print(json.dumps({'mind': a.mind, **{k: v[k] for k in ('live', 'runs', 'passPct', 'why')}}))


if __name__ == '__main__':
    asyncio.run(main())
