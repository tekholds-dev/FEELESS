#!/usr/bin/env python
"""Does an auto range really earn? Reads real pools and hourly bars, read only, and tests each pool on history it did not choose its band from."""
import asyncio
import statistics as st
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
import env_loader  # noqa: E402,F401
import grow_board as gb  # noqa: E402
import range_sim as rs  # noqa: E402


async def main(n=40):
    async with httpx.AsyncClient(timeout=25) as h:
        rows = (await h.get('http://127.0.0.1:5077/api/reputation/familia-pools/ranges', params={'top': 1, 'reads': 1})).json().get('pools') or []
        rows = sorted((r for r in rows if r.get('pool') and float(r.get('tvl') or 0) > 200_000), key=lambda r: -float(r.get('tvl') or 0))[:n]; sol = (await h.get('http://127.0.0.1:5099/api/candles/solana/8sLbNZoA1cfnvMJLPfp98ZLAnFSYCFApfJKMbiXNLwxj', params={'interval': '1h'})).json().get('candles') or []; out = []
        for r in rows:
            row = gb.pool_row(r); b = (await h.get(f"http://127.0.0.1:5099/api/candles/solana/{r['pool']}", params={'interval': '1h'})).json().get('candles') or []; pts, why = gb.pool_points(row, b, sol); w = rs.walk_forward(pts)
            if w:
                out.append({**w, 'name': row['name']}); print(f"{row['name'][:18]:18} band {w['width']:>3}% wait {w['wait']:>2}h | test {w['pct']:+7.2f}%  hold {w['holdPct']:+7.2f}%  full {w['fullPct']:+7.2f}%  in range {w['inRange']:5.1f}%  moves {w['moves']}")
    if not out:
        print('no pool had enough history')
        return
    beat_hold = sum(1 for x in out if x['pct'] > x['holdPct']); beat_full = sum(1 for x in out if x['pct'] > x['fullPct']); pos = sum(1 for x in out if x['pct'] > 0)
    print(f"\n{len(out)} pools on unseen hours. Median test {st.median(x['pct'] for x in out):+.2f}%, hold {st.median(x['holdPct'] for x in out):+.2f}%, full range {st.median(x['fullPct'] for x in out):+.2f}%. Made money {pos}. Beat holding {beat_hold}. Beat full range {beat_full}.")

asyncio.run(main())
