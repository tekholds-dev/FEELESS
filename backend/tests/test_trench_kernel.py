"""⚙ The command kernel: one MintState per mint, one candidate lifecycle, one ten-agent brain, four hunter lanes, singleflight RPC."""
import asyncio
import time
from pathlib import Path

import chain_rpc as cr
import trench_kernel.brain as tb
import trench_kernel.kernel as tk
import trench_kernel.lifecycle as tl
import trench_kernel.state as ts

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def row(m='M', age=0.05, mc=40_000, d5=6.0, buy=62, liq=20_000, v5=8_000, pace=2.0, px=1.0, **k):
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': px, 'nums': {'v5': v5, 'pace': pace, 'liq': liq, 'd5': d5, 'buy': buy},
            'vitals': {'mcap': mc, 'liq': liq, 'ageH': age, 'vol1h': 20_000, 'txns1h': 300}, **k}


def test_one_canonical_object_across_sources_and_duplicates_are_dropped():
    k = tk.Kernel()
    ev = k.run([row('A'), row('A'), row('B')], 100.0, source='pump')
    assert set(ev) == {'A', 'B'} and k.store.stats['dupes'] == 1
    k.run([row('A')], 110.0, source='callouts')
    assert len([m for m in k.store.mints if m == 'A']) == 1 and k.store.mints['A']['identity']['sources'] == ['callouts', 'pump']


def test_pending_holder_and_research_data_never_reject_a_candidate():
    k = tk.Kernel()
    k.run([row('P', vitals={'mcap': 40_000, 'liq': 20_000, 'ageH': 0.05, 'vol1h': 20_000, 'safe': None})], 100.0)
    d = k.dec['P']
    assert d['status'] in ('READY', 'CONTENDING') and 'holders' in d['opinions']['sherlock']['unknown'] and 'holders' in d['opinions']['sherlock']['requests']
    assert 'site / X' in d['opinions']['sherlock']['unknown']


def test_an_ordinary_devil_warning_never_hard_blocks_and_warden_shrinks():
    k = tk.Kernel()
    k.run([row('D', objs=[['rug_signs', 'x'], ['identity', 'no site']])], 100.0)
    d = k.dec['D']
    dv = d['opinions']['devil']
    assert not dv['hard'] and {s for _o, s, _w in dv['objections']} == {'STRONG_WARNING', 'WARNING'}
    assert d['status'] in ('READY', 'CONTENDING') and 0.5 <= d['opinions']['warden']['size'] < 1.0


def test_only_the_hard_wall_is_a_hard_veto_and_it_tracks_rather_than_rejects():
    k = tk.Kernel()
    k.run([row('C', d5=-25), row('U', vitals={'mcap': None, 'liq': 20_000, 'ageH': None})], 100.0)
    assert k.dec['C']['opinions']['devil']['hard'] and k.store.cand['C']['status'] == 'TRACKING'
    assert k.store.cand['U']['status'] == 'TRACKING' and 'outside' in k.dec['U']['why']   # unknown cap / age: pending, never CLOSED


def test_a_held_winner_over_200k_is_not_sold_and_cannot_be_replaced_by_the_seat_filler():
    k = tk.Kernel()
    ctx = {'held': {'H': {'entry': 0.5, 'peak': 90, 'stopNow': 30}}}
    k.run([row('H', mc=900_000, age=9), row('N')], 100.0, ctx)
    assert k.dec['H']['status'] == 'HELD' and k.dec['H']['opinions']['reaper']['action'] in ('HOLD', 'PROTECT')
    assert 'H' not in [m for m, _d in k.ready()]
    assert [l['state'] for l in k.lanes][0] == 'HELD'


def test_four_hunter_lanes_stay_active_without_four_paid_positions():
    k = tk.Kernel()
    k.run([row(f'X{i}', v5=1_000 * (i + 1)) for i in range(6)], 100.0)
    assert len(k.lanes) == 4 and all(l['state'] in ('ARMED', 'HUNTING') for l in k.lanes) and all(l['mint'] for l in k.lanes)


def test_only_affected_mints_are_rejudged_and_a_live_price_wakes_reaper_now():
    k = tk.Kernel()
    ctx = {'held': {'H': {'entry': 1.0, 'peak': 0, 'stopNow': 15}}}
    k.run([row('H'), row('Q')], 100.0, ctx)
    n = k.counts['rejudged']
    k.run([row('H'), row('Q')], 110.0, ctx)                  # nothing changed: only the held coin is re-judged
    assert k.counts['rejudged'] - n == 1
    d = k.price_event('H', 0.8, 115.0, ctx)                  # −20% vs a 15% stop: Reaper says EXIT on the event itself
    assert d['opinions']['reaper']['action'] == 'EXIT' and d['status'] == 'EXIT_PENDING' and k.lat['priceToReaper']


def test_new_mint_intake_needs_zero_rpc_calls(monkeypatch):
    calls = []
    async def boom(*a, **k):
        calls.append(a); raise AssertionError('no RPC on intake')
    monkeypatch.setattr(cr, '_rpc_physical', boom)
    tk.Kernel().run([row(f'Z{i}') for i in range(50)], 100.0)
    assert calls == []


def test_singleflight_collapses_identical_in_flight_reads_into_one_physical_call(monkeypatch):
    phys = []
    async def fake(http, method, params, scan=True):
        phys.append(method); await asyncio.sleep(0.05); return {'ok': params}
    monkeypatch.setattr(cr, '_rpc_physical', fake)
    async def go():
        return await asyncio.gather(*[cr._rpc(None, 'getTokenLargestAccounts', ['MINT']) for _ in range(8)], cr._rpc(None, 'getAccountInfo', ['MINT']))
    out = asyncio.run(go())
    assert len(phys) == 2 and all(o == {'ok': ['MINT']} for o in out[:8])
    phys.clear()
    async def sends():
        return await asyncio.gather(*[cr._rpc(None, 'sendTransaction', ['TX']) for _ in range(3)])
    asyncio.run(sends())
    assert len(phys) == 3                                     # writes are never coalesced


def test_all_ten_roles_share_one_lifecycle_record():
    gens = tl.generations({'gen': {'tally': 7}}, {'gen': {'reaper': 2}, 'lineage': [{'agent': 'reaper', 'gen': 1, 'at': 50, 'why': 'x'}]}, 100.0)
    assert [g['role'] for g in gens] == list(tb.ROLES) and all(g['status'] == 'ACTIVE' for g in gens)
    r = next(g for g in gens if g['role'] == 'reaper')
    assert r['generation'] == 2 and r['lineage'][0]['status'] == 'SHADOW'
    assert set(gens[0]) >= {'role', 'generation', 'bornAt', 'status', 'decisions', 'winsAttributed', 'lossesAttributed', 'netImpact', 'lessons', 'lineage', 'lastEvaluation'}


def test_the_seat_fill_reads_the_kernel_and_there_is_one_execution_path():
    assert '_tk.KERNEL.ready(exclude=blk_)' in SRC and SRC.count('_prime.agent_seat(') == 1 and SRC.count('def _fw_execute(') == 1
    assert "_tk.KERNEL.price_event(m_, px_, time.time(), kctx_)" in SRC


def test_local_latency_targets_on_a_500_coin_batch():
    k = tk.Kernel()
    rows = [row(f'L{i}', v5=500 + i * 10, d5=(i % 20) - 5) for i in range(500)]
    k.run(rows, 100.0)
    k.run([{**r, 'px': 1.05} for r in rows], 110.0)
    m = k.metrics(110.0)['latencyMs']
    assert m['ingest']['p95'] < 25 and m['rank']['p95'] < 10 and m['agents']['p95'] < 50
    t0 = time.perf_counter(); k.price_event('L1', 1.2, 120.0, {}); assert (time.perf_counter() - t0) * 1000 < 250


def test_one_enrichment_scheduler_asks_only_for_the_strongest_and_reuses_the_deduped_scan():
    assert 'ENRICH_TOP = 4' in SRC and 'asyncio.ensure_future(_runner_intel(m_))' in SRC
    k = tk.Kernel()
    k.run([row(f'S{i}', vitals={'mcap': 40_000, 'liq': 20_000, 'ageH': 0.05, 'vol1h': 20_000, 'safe': None}) for i in range(6)], 100.0)
    assert all('holders' in d['opinions']['sherlock']['requests'] for d in k.dec.values())   # Sherlock asks; the scheduler decides how many
