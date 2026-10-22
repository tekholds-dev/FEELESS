#!/usr/bin/env python3
"""⚡ Load test for the Familia world endpoints (P1 "scale for thousands"). Read-only GETs against the LOCAL reputation service — never a write,
never mainnet. Fires `--users` concurrent viewers for `--rounds` rounds at each endpoint and prints p50 / p95 / max latency + errors.

    .venv/bin/python scripts/load-world.py --users 50 --rounds 4
"""
import argparse
import asyncio
import statistics
import time

import httpx

BASE = 'http://127.0.0.1:5077/api/reputation'
PATHS = ['/familia-world', '/familia/street/fee', '/familia-pools', '/familia-pools/sleep', '/familia/street/harbor']


async def hit(client, path):
    t0 = time.perf_counter()
    try:
        r = await client.get(BASE + path, timeout=30)
        return (time.perf_counter() - t0) * 1000, r.status_code
    except Exception as e:
        return (time.perf_counter() - t0) * 1000, type(e).__name__


async def main(users, rounds):
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)
    async with httpx.AsyncClient(limits=limits) as client:
        for path in PATHS:
            ms, bad = [], 0
            for _ in range(rounds):
                res = await asyncio.gather(*[hit(client, path) for _ in range(users)])
                ms += [m for m, _s in res]
                bad += sum(1 for _m, s in res if s != 200)
            ms.sort()
            p95 = ms[int(len(ms) * 0.95) - 1]
            print(f'{path:28s} n={len(ms):4d}  p50 {statistics.median(ms):7.1f} ms  p95 {p95:7.1f} ms  max {ms[-1]:7.1f} ms  errors {bad}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--users', type=int, default=50)
    ap.add_argument('--rounds', type=int, default=4)
    a = ap.parse_args()
    asyncio.run(main(a.users, a.rounds))
