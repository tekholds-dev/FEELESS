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
    k.run([row('D', ev=[['rug_meter', 'rug meter 60'], ['identity', 'no site']])], 100.0)
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
    b = tl.new_book(100.0, {'gen': {'tally': 7}}, {'gen': {'reaper': 2}, 'lineage': [{'agent': 'reaper', 'gen': 1, 'at': 50, 'why': 'x'}]})
    gens = tl.generations(b, 100.0)
    assert [g['role'] for g in gens] == list(tb.ROLES) and all(g['status'] == 'ACTIVE' for g in gens)
    r = next(g for g in gens if g['role'] == 'reaper')
    assert r['generation'] == 2 and r['lineage'][0]['gen'] == 1 and gens[0]['generation'] == 7
    assert set(gens[0]) >= {'role', 'generation', 'bornAt', 'status', 'decisions', 'winsAttributed', 'lossesAttributed', 'netImpact', 'lessons', 'lessonVector', 'lineage', 'lastEvaluation'}


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
    assert 'ENRICH_TOP = 4' in SRC and 'asyncio.ensure_future(_runner_intel(m_, p_, why_, wait=False))' in SRC   # → the ONE scheduler (tests/test_kernel_enrich.py)
    k = tk.Kernel()
    k.run([row(f'S{i}', vitals={'mcap': 40_000, 'liq': 20_000, 'ageH': 0.05, 'vol1h': 20_000, 'safe': None}) for i in range(6)], 100.0)
    assert all('holders' in d['opinions']['sherlock']['requests'] for d in k.dec.values())   # Sherlock asks; the scheduler decides how many


def test_the_view_is_consistent_after_a_newer_price_event():
    k = tk.Kernel()
    k.run([row('A'), row('B')], 100.0, {'held': {}})
    k.price_event('B', 1.05, 130.0, {'held': {'B': {'entry': 1.0, 'peak': 0, 'stopNow': 20}}})   # B became held after the pass
    v = k.view(120.0)
    assert [l['mint'] for l in v['lanes'] if l['state'] == 'HELD'] == ['B'] and all(c['decidedAgo'] >= 0 for c in v['candidates'])


def test_the_live_tape_decides_triggers_moment_and_a_crowd_only_ranks_a_little_higher():
    ms = lambda **k: ts.from_row(row('F', **k), 100.0)
    plain = tb.trigger(ms())
    assert plain['state'] in ('ENTER', 'ARM') and plain['flow'] is None                      # no fresh tape = not judged
    sell = tb.trigger(ms(fv={'state': 'SELLERS', 'why': 'sellers lead: $5 vs $90'}))
    assert sell['state'] == 'WAIT' and 'sellers lead' in sell['why']
    peak = tb.trigger(ms(fv={'state': 'PEAK', 'why': 'already +8.0% inside 90s'}))
    assert peak['state'] == 'ARM' and 'not bought at the top' in peak['why']
    assert tb.trigger(ms(fv={'state': 'THIN', 'why': 'x'}))['state'] == plain['state']
    a, b = tb.think(ms()), tb.think(ms(fv={'state': 'BUYERS', 'hot': True, 'why': 'a crowd is buying'}))
    assert round(b['rank'] / a['rank'], 2) == tb.CROWD_F                                     # a rank weight, never a gate
    assert 'flow' in ts.material(ms(), ms(fv={'state': 'SELLERS', 'why': 'x'})) and 'flow' not in ts.material(ms(), ms())


def test_the_judges_repeat_loss_causes_rank_a_matching_coin_down_and_never_veto_it():
    fomo = lambda **k: ts.from_row(row('J', li={'phase': 'CROWD FOMO', 'cls': 'BUNDLED'}, **k), 100.0)
    a = tb.think(fomo())
    b = tb.think(fomo(), {'pens': {'crowd fomo': -8.0}})
    c = tb.think(fomo(), {'pens': {'crowd fomo': -8.0, 'bundled': -8.0, 'thin pool': -8.0, 'falling now': -8.0}})
    assert round(b['rank'] / a['rank'], 2) == 0.92 and b['status'] == a['status']               # one cause: −8%, same lifecycle state
    assert round(c['rank'] / a['rank'], 2) >= tb.PEN_FLOOR and any('judge: crowd fomo' in str(p[0]) for p in b['parts'])
    clean = ts.from_row(row('K'), 100.0)
    assert tb.think(clean, {'pens': {'crowd fomo': -8.0}})['rank'] == tb.think(clean)['rank']   # a coin the cause does not match is untouched


def test_a_candidate_that_left_the_desk_steps_down_instead_of_staying_ready_on_an_old_reading():
    """Lynk ran to $18K, died back to $3K and stayed "2 min old, +3%" for 25 minutes: seated three times on a reading nobody refreshed."""
    k = tk.Kernel()
    k.run([row('GONE'), row('LIVE')], 100.0)
    assert k.dec['GONE']['status'] in ('READY', 'CONTENDING')
    k.run([row('LIVE')], 150.0)                                   # one missed pass is not stale
    assert k.dec['GONE']['status'] in ('READY', 'CONTENDING')
    k.run([row('LIVE')], 100.0 + tk.STALE_SEC + 1)
    assert k.dec['GONE']['status'] == 'TRACKING' and 'off the desk' in k.dec['GONE']['why'] and k.dec['LIVE']['status'] in ('READY', 'CONTENDING')
    assert 'GONE' not in [m for m, _d in k.ready()] and 'GONE' not in [c['mint'] for c in k.cases(statuses=('READY', 'CONTENDING'))]
    k.price_event('GONE', 1.5, 100.0 + tk.STALE_SEC + 5)          # a live price alone never makes it a candidate again
    assert k.dec['GONE']['status'] == 'TRACKING'
    k.price_event('GONE', 1.0, 100.0 + tk.STALE_SEC + 6)          # (back at the row's own price: the fresh row below raises no price event)
    k.run([row('GONE'), row('LIVE')], 100.0 + tk.STALE_SEC + 20)  # the desk reads it again: judged on the fresh row
    assert k.dec['GONE']['status'] in ('READY', 'CONTENDING')
