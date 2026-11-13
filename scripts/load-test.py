#!/usr/bin/env python3
"""🏋 SITE-8 load test — read-only GETs against the four running services, N requests at C at a time per endpoint.

Reports per endpoint: ok %, requests/s, p50 / p95 / max ms, and status codes; files the run to the Test bench (Proofs › Test bench) of the
agent given by --cat (default Sicario's). Only GETs on cached or local reads: never a write, a trade, a model call or a fresh outside read
per request. Keep the default size on the owner's live machine (300 × 25).

    .venv/bin/python scripts/load-test.py                 # default set, files to the bench
    .venv/bin/python scripts/load-test.py -n 600 -c 50 --no-file
"""
import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

SICARIO = 'b5e0fc0eddb64cba98ed4b1028521bd2'
JUP = 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'
TARGETS = [   # (name, url) — every one a cached / local read
    ('5001 market root', 'http://127.0.0.1:5001/api/'),
    ('5001 chat history', 'http://127.0.0.1:5001/api/chat/global'),
    ('5077 perks (wallet)', 'http://127.0.0.1:5077/api/reputation/perks/11111111111111111111111111111111'),
    ('5077 coin price gap', f'http://127.0.0.1:5077/api/reputation/price-gap/{JUP}'),
    ('5088 agents health', 'http://127.0.0.1:5088/api/cats/health'),
    ('5099 candles health', 'http://127.0.0.1:5099/api/candles/health'),
]


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


async def hammer(client, url, n, c):
    sem = asyncio.Semaphore(c); lat, codes = [], {}

    async def one():
        async with sem:
            t = time.perf_counter()
            try:
                r = await client.get(url, timeout=15)
                code = r.status_code
            except Exception as e:
                code = type(e).__name__
            lat.append((time.perf_counter() - t) * 1000); codes[str(code)] = codes.get(str(code), 0) + 1
    await client.get(url, timeout=20)   # warm (fills the service's own cache once)
    t0 = time.perf_counter()
    await asyncio.gather(*(one() for _ in range(n)))
    wall = time.perf_counter() - t0
    ok = sum(v for k, v in codes.items() if k.startswith('2'))
    return {'n': n, 'c': c, 'okPct': round(ok / n * 100, 1), 'rps': round(n / wall, 1), 'p50': round(pct(lat, 50), 1), 'p95': round(pct(lat, 95), 1),
            'max': round(max(lat), 1), 'mean': round(statistics.mean(lat), 1), 'codes': codes, 'wallS': round(wall, 2)}


async def main(a):
    out = []
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=a.c + 5)) as client:
        for name, url in TARGETS:
            r = await hammer(client, url, a.n, a.c)
            out.append({'name': name, 'url': url, **r})
            print(f"{name:22s} ok {r['okPct']:5.1f}%  {r['rps']:7.1f} req/s  p50 {r['p50']:7.1f} ms  p95 {r['p95']:7.1f} ms  max {r['max']:7.1f} ms  {r['codes']}")
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, default=300); ap.add_argument('-c', type=int, default=25)
    ap.add_argument('--cat', default=SICARIO); ap.add_argument('--no-file', action='store_true')
    a = ap.parse_args()
    t0 = time.time(); rows = asyncio.run(main(a))
    bad = [r for r in rows if r['okPct'] < 99 or r['p95'] > 1000]
    why = (f"{len(rows)} endpoints × {a.n} GETs at {a.c} at a time on the live services: "
           + '; '.join(f"{r['name']} {r['rps']} req/s p95 {r['p95']} ms ok {r['okPct']}%" for r in rows)
           + ('. Slow or failing: ' + ', '.join(r['name'] for r in bad) if bad else '. Every endpoint ≥ 99% ok with p95 under 1 s.'))
    print(why)
    if not a.no_file:
        import test_bench
        row = test_bench.file_run(ROOT / 'backend' / 'data', a.cat, kind='other', title=f'SITE-8 load test — {len(rows)} live endpoints × {a.n} at {a.c}',
                                  ok=not bad, why=why, secs=time.time() - t0, steps=[f"{r['name']}: {r['codes']}" for r in rows],
                                  files={'load-test.json': json.dumps(rows, indent=1)})
        print('filed to the Test bench:', row['id'])
    sys.exit(1 if bad else 0)
