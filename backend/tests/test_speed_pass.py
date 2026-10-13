"""⚡ Final speed pass: /fuses/prime is served from the last good snapshot on the first request after a restart (one background build),
its three reads run at once with DexScreener budgeted; a logo lookup never takes longer than its budget and a slow miss is not retried
at once; SSE + RPC are measured. Fakes only."""
import asyncio
import time

import pytest
import reputation_service as rs


def test_prime_reads_run_at_once_and_dexscreener_is_budgeted(monkeypatch):
    async def slow(*a, **k):
        await asyncio.sleep(5)
        return {'P': 9.0}

    async def jup(mints):
        await asyncio.sleep(0.05)
        return {'M': 2.0}

    async def sol():
        await asyncio.sleep(0.05)
        return 150.0
    monkeypatch.setattr(rs, '_hq_prices', slow); monkeypatch.setattr(rs, '_jup_prices', jup); monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs, 'PRIME_DS_BUDGET', 0.1)
    t0 = time.time()
    px, j, s = asyncio.run(rs._prime_reads([{'pairAddress': 'P', 'mint': 'M'}]))
    assert time.time() - t0 < 1 and px == {} and j == {'M': 2.0} and s == 150.0
    assert rs._prime_stages['dexscreener'] >= 90 and rs._prime_stages['jupiter'] < 1000


def test_first_request_after_a_restart_is_the_snapshot_while_one_build_runs(monkeypatch, tmp_path):
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    monkeypatch.setattr(rs, 'PRIME_SNAPSHOT_PATH', tmp_path / 'prime_snapshot.json')
    rs._json_save(rs.PRIME_SNAPSHOT_PATH, {'at': time.time() - 120, 'data': {'cards': ['snap']}})
    calls = {'n': 0}

    async def build():
        calls['n'] += 1
        await asyncio.sleep(0.2)
        return {'cards': ['fresh']}
    monkeypatch.setattr(rs, '_fuse_prime_build', build)
    rs._prime_resp.update(at=0.0, data=None, task=None, cleared=0.0, snap=False, snapTried=False, savedAt=0.0)

    async def go():
        t0 = time.time(); first = await rs.fuse_prime(); took = time.time() - t0
        second = await rs.fuse_prime()
        await asyncio.sleep(0.3)
        return first, took, second, await rs.fuse_prime()
    first, took, second, third = asyncio.run(go())
    assert first == {'cards': ['snap']} and took < 0.1 and second == {'cards': ['snap']} and calls['n'] == 1   # one build, snapshot meanwhile
    assert third == {'cards': ['fresh']} and rs.PRIME_SNAPSHOT_PATH.exists()
    assert rs._json_load(rs.PRIME_SNAPSHOT_PATH, {})['data'] == {'cards': ['fresh']}                          # the new good answer is saved
    old = tmp_path / 'old.json'; rs._json_save(old, {'at': time.time() - 99999, 'data': {'x': 1}})
    monkeypatch.setattr(rs, 'PRIME_SNAPSHOT_PATH', old)
    assert rs._prime_snapshot() is None                                                                       # never a stale snapshot


def test_a_logo_lookup_never_outlives_its_budget_and_a_slow_miss_is_not_retried_at_once(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'LOGO_DIR', tmp_path); monkeypatch.setattr(rs, 'LOGO_BUDGET', 0.1)
    monkeypatch.setattr(rs, 'LOGO_OVERRIDE_PATH', tmp_path / 'none.json')

    class Slow:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k):
            await asyncio.sleep(5)
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Slow)
    M = 'So11111111111111111111111111111111111111112'
    rs._logo_miss.pop(M, None)
    t0 = time.time()
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.token_logo(M))
    assert time.time() - t0 < 1 and e.value.status_code == 404
    t1 = time.time()
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.token_logo(M))
    assert time.time() - t1 < 0.05                                                                            # the miss is remembered


def test_net_stats_measure_streams_and_rpc():
    n = rs._net_stats()
    assert set(n) == {'sse', 'rpc', 'prime'} and {'active', 'connects', 'resyncs', 'subscribers', 'connectsPerMin'} <= set(n['sse'])
    assert {'logicalPerMin', 'physicalPerMin', 'r429PerMin', 'topMethods', 'perMint'} <= set(n['rpc'])
