#!/usr/bin/env python3
"""🗄 SITE-8 load test: uvicorn with N WORKER PROCESSES writing one shared store (backend/sql_store.Docs), hammered by concurrent clients.
Sandbox data only (a temp folder), its own port, nothing of the live services is touched. Proves: no lost write across workers, and the
check-in path's shape (one wallet's row read → changed → written in one transaction) under load.
  .venv/bin/python scripts/load-workers.py --workers 4 --wallets 50 --hits 2000"""
import argparse
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = '''
import os, sys, time
sys.path.insert(0, os.environ["FEELESS_BACKEND"])
from fastapi import FastAPI
import sql_store
app = FastAPI(); D = sql_store.Docs(os.path.join(os.environ["LOAD_DIR"], "quest_state.json"))
@app.post("/hit/{w}")
def hit(w: str):
    st = D.update(w, lambda cur: {**(cur or {"n": 0}), "n": (cur or {}).get("n", 0) + 1, "pid": os.getpid()})
    return {"n": st["n"], "pid": os.getpid()}
@app.get("/all")
def all_():
    return D.all()
'''


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=4); ap.add_argument('--wallets', type=int, default=50)
    ap.add_argument('--hits', type=int, default=2000); ap.add_argument('--port', type=int, default=5791); a = ap.parse_args()
    d = tempfile.mkdtemp(prefix='feeless-load-'); (pathlib.Path(d) / 'loadapp.py').write_text(APP)
    env = {**os.environ, 'FEELESS_BACKEND': str(ROOT / 'backend'), 'LOAD_DIR': d}
    srv = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'loadapp:app', '--port', str(a.port), '--workers', str(a.workers), '--log-level', 'warning'], cwd=d, env=env)
    try:
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{a.port}', timeout=30) as c:
            for _ in range(60):
                try:
                    await c.get('/all'); break
                except httpx.HTTPError:
                    await asyncio.sleep(0.25)
            sem = asyncio.Semaphore(64); lat = []; pids = set(); bad = 0

            async def one(i):
                nonlocal bad
                async with sem:
                    t = time.perf_counter()
                    try:
                        r = await c.post(f'/hit/w{i % a.wallets}')
                        pids.add(r.json()['pid']) if r.status_code == 200 else None
                        bad += r.status_code != 200
                    except httpx.HTTPError:
                        bad += 1
                    lat.append(time.perf_counter() - t)
            t0 = time.perf_counter(); await asyncio.gather(*[one(i) for i in range(a.hits)]); secs = time.perf_counter() - t0
            got = (await c.get('/all')).json(); total = sum(v['n'] for v in got.values())
        lat.sort()
        out = {'workers': a.workers, 'workerPidsSeen': len(pids), 'hits': a.hits, 'failed': bad, 'stored': total, 'lost': a.hits - bad - total,
               'rps': round(a.hits / secs), 'p50ms': round(lat[len(lat) // 2] * 1000, 1), 'p95ms': round(lat[int(len(lat) * 0.95)] * 1000, 1)}
        print(json.dumps(out)); return out
    finally:
        srv.terminate(); srv.wait(10)


if __name__ == '__main__':
    r = asyncio.run(main())
    sys.exit(0 if r['lost'] == 0 and r['failed'] == 0 and r['workerPidsSeen'] > 1 else 1)
