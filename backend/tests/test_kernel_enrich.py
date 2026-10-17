"""🔎 The ONE enrichment scheduler (trench_kernel/enrich.py): priority, budget, freshness that survives a restart, negative caching —
and the proof that a restart cannot start a scan avalanche."""
import asyncio
from pathlib import Path

import chain_rpc as cr
import trench_kernel.enrich as en
import trench_kernel.kernel as tk

from kernel_helpers import row

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()
P = en.PRIO


def drain(e, now, limit=10_000):
    """Start everything that is due right now. → the mints started, in order."""
    out = []
    for m in e.due(now):
        e.started(m, now); out.append(m)
    return out


def test_the_queue_serves_held_and_ready_before_everything_else():
    e = en.Enricher(boot_at=-1000.0, calls_per_sec=100.0, concurrency=3)
    for m, p in (('rest1', 'REST'), ('mover', 'MOVER'), ('cont', 'CONTENDING'), ('lane', 'ARMED'), ('ready', 'READY'), ('held', 'HELD'), ('rest2', 'REST')):
        assert e.request(m, P[p], p.lower(), 0.0) == 'queued'
    e.tokens = 1000.0
    assert drain(e, 1.0) == ['held', 'ready', 'lane']                       # concurrency 3: the three most important, in order
    for m in ('held', 'ready', 'lane'):
        e.finished(m, 2.0, True)
    assert drain(e, 3.0) == ['cont', 'mover', 'rest1']
    assert e.request('rest2', P['HELD'], 'now held', 3.0) == 'queued' and e.queue['rest2']['prio'] == 0   # a queued coin takes the higher priority


def test_a_restart_cannot_start_a_scan_avalanche():
    """The measured storm: 104 holder scans in flight after a restart, 612 rate-limit answers. Now the same 104 board requests queue up
    and are drained inside the concurrency limit and the call budget, the held and ready coins first."""
    e = en.Enricher(boot_at=0.0, calls_per_sec=2.0, concurrency=4)
    board = [f'coin{i}' for i in range(104)]
    for m in board:
        assert e.request(m, P['REST'], 'board', 0.5, known=False) == 'queued'
    e.request('HELD1', P['HELD'], 'held', 0.5); e.request('READY1', P['READY'], 'ready', 0.5)
    first = drain(e, 1.0)
    assert first[0] == 'HELD1' and len(first) <= 2 and len(e.inflight) <= 4          # NOT 104: the held coin, then what the budget allows
    assert e.metrics(1.0)['queueDepth'] >= 100 and e.metrics(1.0)['oldestQueueAge'] == 0.5
    started, t = list(first), 1.0
    for _ in range(600):                                                              # 10 minutes, a second at a time, every scan succeeding
        t += 1.0
        for m in list(e.inflight):
            e.finished(m, t, True)
        started += drain(e, t)
        assert len(e.inflight) <= 4
    calls = sum(en.COST_NEW if m.startswith('coin') else en.COST_RESCAN for m in started)
    assert calls <= 2.0 * 601 + en.BURST + en.COST_NEW                                 # never more RPC than the budget over the window
    assert 'READY1' in started[:3] and 20 <= len(started) < 104                        # steady progress — and the rest still queued, not fired
    spread = sorted(q['notBefore'] for q in e.queue.values())
    assert spread[-1] - spread[0] > 20                                                 # the low-priority first scans were staggered over the boot window


def test_fresh_evidence_is_not_scanned_again_and_low_priority_waits_four_times_longer():
    e = en.Enricher(boot_at=-1000.0, ttl=900.0)
    e.request('A', P['READY'], 'x', 0.0); e.tokens = 100.0
    drain(e, 0.0); e.finished('A', 1.0, True)
    assert e.request('A', P['READY'], 'x', 600.0) == 'fresh' and e.count['skippedFresh'] == 1
    assert e.request('A', P['READY'], 'x', 1000.0) == 'queued'                          # past the TTL for a coin someone acts on …
    e.queue.clear()
    assert e.request('A', P['REST'], 'board', 1000.0) == 'fresh' and e.request('A', P['REST'], 'board', 3700.0) == 'queued'   # … an idle one: 4× the TTL
    assert e.status('A', 600.0) == 'FRESH' and e.status('B', 0.0) == 'PENDING'


def test_a_failed_scan_backs_off_and_a_rate_limited_one_slows_the_whole_scheduler():
    e = en.Enricher(boot_at=-1000.0, calls_per_sec=2.0)
    e.request('F', P['CONTENDING'], 'x', 0.0); e.tokens = 100.0
    drain(e, 0.0); e.finished('F', 1.0, False, rate_limited=True)
    assert e.rate == 1.0 and e.status('F', 2.0) == 'RATE_LIMITED'                      # half the rate, and the EVIDENCE says why it is missing
    assert e.request('F', P['CONTENDING'], 'x', 10.0) == 'deferred'                    # not asked again inside its back-off
    assert e.request('F', P['HELD'], 'held', 10.0) == 'queued'                         # … unless we HOLD it
    drain(e, 10.0); e.finished('F', 11.0, False)
    assert e.status('F', 12.0) == 'UNAVAILABLE' and e.fresh['F']['until'] - 11.0 == en.BACKOFF[1]
    for i in range(6):
        e.request(f'ok{i}', P['READY'], 'x', 100.0 + i); e.tokens = 100.0; drain(e, 100.0 + i); e.finished(f'ok{i}', 100.5 + i, True)
    assert 1.0 < e.rate <= 2.0                                                          # clean scans bring the rate back, never above the budget
    for _ in range(9):
        e.rate = max(e.base * en.RATE_FLOOR, e.rate * 0.5)
    assert e.rate == 0.5                                                                # the floor: a quarter of the budget


def test_freshness_survives_a_restart_and_a_result_that_is_gone_is_not_called_fresh():
    a = en.Enricher(boot_at=0.0)
    for m in ('KEPT', 'LOST', 'BAD'):
        a.request(m, P['READY'], 'x', 1.0); a.tokens = 100.0
    drain(a, 1.0)
    a.finished('KEPT', 2.0, True); a.finished('LOST', 2.0, True); a.finished('BAD', 2.0, False, rate_limited=True)
    snap = a.snapshot(10.0)
    b = en.Enricher(boot_at=20.0)                                                       # the process restarted
    assert b.restore(snap, 20.0, have={'KEPT'}) == 3
    assert b.request('KEPT', P['READY'], 'x', 21.0) == 'fresh'                          # scanned 19s ago and its result is in memory: no scan
    assert b.request('LOST', P['READY'], 'x', 21.0) == 'queued'                         # its result did not come back: it is scanned, in its turn
    assert b.request('BAD', P['READY'], 'x', 21.0) == 'deferred' and b.status('BAD', 21.0) == 'RATE_LIMITED'   # the back-off survived too
    assert b.metrics(21.0)['holderScansSkippedFresh'] == 1


def test_the_queue_is_bounded_and_keeps_the_important_coins():
    e = en.Enricher(boot_at=-1000.0)
    for i in range(en.QUEUE_MAX):
        e.request(f'r{i}', P['REST'], 'board', float(i))
    assert e.request('extra', P['REST'], 'board', 999.0) == 'deferred' and len(e.queue) == en.QUEUE_MAX
    assert e.request('held', P['HELD'], 'held', 999.0) == 'queued' and len(e.queue) == en.QUEUE_MAX and 'held' in e.queue
    assert e.metrics(1000.0)['holderScansDeferred'] == 2


def test_a_pending_or_rate_limited_scan_never_rejects_the_coin():
    k = tk.Kernel()
    k.run([row('N', vitals={'mcap': 40_000, 'liq': 20_000, 'ageH': 0.05, 'vol1h': 20_000, 'safe': None})], 100.0)
    assert k.dec['N']['status'] in ('READY', 'CONTENDING') and 'holders' in k.dec['N']['opinions']['sherlock']['unknown']
    en.Enricher(boot_at=0.0)
    for st in ('PENDING', 'RATE_LIMITED', 'UNAVAILABLE', 'STALE', 'FRESH'):
        assert st in en.STATUS and st not in tk._s.STATES                              # an evidence state is not a candidate state


def test_new_coin_intake_needs_zero_rpc(monkeypatch):
    calls = []
    async def phys(http, method, params, scan=True):
        calls.append(method); return {}
    monkeypatch.setattr(cr, '_rpc_physical', phys)
    k = tk.Kernel()
    k.run([row(f'N{i}', vitals={'mcap': 30_000 + i, 'liq': 20_000, 'ageH': 0.02, 'vol1h': 9_000, 'safe': None}) for i in range(300)], 100.0)
    assert len(k.store.mints) == 300 and calls == [] and k.metrics(100.0)['byStatus']['DISCOVERED'] == 0   # discovered, judged and ranked with no chain call
    import trench_kernel.senses as sn
    sn.sense({}, [{'mint': f'S{i}', 'symbol': 's', 'pairAddress': 'p', 'price': 1.0, 'liq': 20_000, 'mcap': 30_000, 'ageH': 0.1} for i in range(50)], 100.0)
    assert calls == []


def test_identical_reads_still_share_one_request_and_a_send_is_never_merged(monkeypatch):
    cr.rpc_stats_reset()
    phys = []
    async def fake(http, method, params, scan=True):
        phys.append(method); await asyncio.sleep(0.01); return {'ok': params}
    monkeypatch.setattr(cr, '_rpc_physical', fake)
    async def go():
        tok = cr.RPC_TAG.set('MINT')
        try:
            await asyncio.gather(*[cr._rpc(None, 'getTokenLargestAccounts', ['MINT']) for _ in range(8)])
            await asyncio.gather(*[cr._rpc(None, 'sendTransaction', ['TX']) for _ in range(3)])
        finally:
            cr.RPC_TAG.reset(tok)
    asyncio.run(go())
    assert phys.count('getTokenLargestAccounts') == 1 and phys.count('sendTransaction') == 3      # reads coalesced, writes never
    m = cr.rpc_metrics()
    assert m['logical'] == 11 and m['saved'] == 7 and m['requestsByMethod']['getTokenLargestAccounts']['logical'] == 8
    assert m['requestsPerMint']['mints'] == 1 and m['requestsPerMint']['logicalTotal'] == 11         # every call of the scan is attributed to its coin
    for w in ('sendTransaction', 'requestAirdrop', 'simulateTransaction'):
        assert w in cr._SF_WRITE


def test_the_service_has_one_door_to_a_deep_scan_and_no_caller_starts_one_itself():
    assert SRC.count("await asyncio.wait_for(token_intel('solana', mint), 12)") == 1                  # the scheduler's own scan
    assert '_runner_sem' not in SRC and 'asyncio.create_task(_quiet(token_intel(' not in SRC and '_scan_wake' not in SRC
    door = SRC[SRC.index('async def _runner_intel('):SRC.index("_runner_widen = {'level'")]
    assert '_ENRICH.request(mint, prio, why, now' in door and '_intel_boot()' in door
    assert SRC.count('_runner_intel(') >= 8
    for call in ("_enr.PRIO['HELD'], 'card leg'", "_enr.PRIO['REST'], 'board'", "_enr.PRIO['LOOK'], 'coin read'", "ask(m_, P['HELD'], 'held')", "ask(m_, P['READY'], 'ready')", "P['ARMED'], 'hunter lane'"):
        assert call in SRC, call
    assert "_json_save(ENRICH_DISK, _ENRICH.snapshot(now))" in SRC and "_ENRICH.restore(_json_load(ENRICH_DISK, {}) or {}, now, have=set(_intel_cache))" in SRC


def test_a_scan_request_in_the_service_never_blocks_a_low_priority_caller(monkeypatch):
    import reputation_service as rs
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    monkeypatch.setitem(rs._fuse_warm_n, 'restored', True)
    e = en.Enricher(boot_at=0.0)
    monkeypatch.setattr(rs, '_ENRICH', e)
    monkeypatch.setattr(rs, '_enrich_pump', lambda: None)                              # nothing may start: we only watch what is asked
    monkeypatch.setitem(rs._intel_cache, 'OLD', (1.0, {'top10Pct': 12.0}))
    async def go():
        a = await rs._runner_intel('OLD', en.PRIO['REST'], 'board')                     # stale result served at once, refresh queued
        b = await rs._runner_intel('NEW', en.PRIO['REST'], 'board')                     # nothing known: None at once, queued
        return a, b
    a, b = asyncio.run(go())
    assert a == {'top10Pct': 12.0} and b is None and set(e.queue) == {'OLD', 'NEW'} and e.queue['NEW']['cost'] == en.COST_NEW
