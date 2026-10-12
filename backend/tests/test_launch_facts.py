"""🧬 A coin's launch forensics (creator, bundlers, snipers) are read from the chain ONCE; later scans only re-read holders."""
import asyncio
import pytest


def test_launch_forensics_are_read_once_and_later_scans_only_read_holders(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    calls = []

    async def fake_rpc(http, method, params, scan=True):
        calls.append(method)
        if method == 'getTokenSupply':
            return {'value': {'uiAmount': 1_000_000_000.0}}
        if method == 'getTokenLargestAccounts':
            return {'value': []}
        if method == 'getSignaturesForAddress':
            return [{'signature': 's1', 'slot': 5}, {'signature': 's2', 'slot': 5}]
        if method == 'getTransaction':
            who = 'CREATOR' if params[0] == 's1' else 'BUNDLER'
            return {'slot': 5, 'transaction': {'message': {'accountKeys': [{'pubkey': who}]}}}
        return {'value': []}

    async def none(*a, **k):
        return None
    monkeypatch.setattr(rs, '_rpc', fake_rpc)
    monkeypatch.setattr(rs, '_record_offenders', none)
    monkeypatch.setattr(rs, 'funder_lookup', lambda w: None)
    mint = 'LaunchFactsTestMint1111111111111111111111pump'
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None); rs._flag_hold.pop(mint, None)
    one = asyncio.run(rs.token_intel('solana', mint))
    assert one['creator'] == 'CREATOR' and one['bundledWallets'] == ['BUNDLER'] and 'getSignaturesForAddress' in calls
    assert rs._launch_facts[mint]['creator'] == 'CREATOR'
    calls.clear(); rs._intel_cache.pop(mint, None)
    two = asyncio.run(rs.token_intel('solana', mint))
    assert two['creator'] == 'CREATOR' and two['bundledWallets'] == ['BUNDLER'] and two['createSlot'] == 5        # same facts …
    assert 'getSignaturesForAddress' not in calls and 'getTransaction' not in calls                              # … no launch re-read
    assert 'getTokenAccountsByOwner' not in calls                                                                # flagged balances reused (15 min)
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None); rs._flag_hold.pop(mint, None)


def test_an_empty_holder_reading_is_incomplete_not_zero_percent(monkeypatch):
    rs = pytest.importorskip('reputation_service')

    async def fake_rpc(http, method, params, scan=True):
        if method == 'getTokenSupply':
            return {'value': {'uiAmount': 1_000_000_000.0}}
        if method == 'getTokenLargestAccounts':
            return {'value': []}          # a node that refuses the holder lookup
        if method == 'getSignaturesForAddress':
            return []
        return {'value': []}

    async def none(*a, **k):
        return None
    monkeypatch.setattr(rs, '_rpc', fake_rpc)
    monkeypatch.setattr(rs, '_record_offenders', none)
    monkeypatch.setattr(rs, 'funder_lookup', lambda w: None)
    mint = 'EmptyHoldersTestMint11111111111111111111pump'
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None)
    out = asyncio.run(rs.token_intel('solana', mint))
    assert out['top10Pct'] is None and out['poolPct'] is None      # → the retry-after-60s path, never a clean 0%
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None)


def test_one_scan_per_coin_in_flight_and_a_failed_one_is_not_re_queued_for_45s(monkeypatch):
    """Every request goes through the ONE scheduler (trench_kernel/enrich.py): eight askers share one scan, a failed coin rests."""
    rs = pytest.importorskip('reputation_service')
    import trench_kernel.enrich as en
    calls = []

    async def slow_intel(chain, mint):
        calls.append(mint)
        await asyncio.sleep(0.05)
        rs._intel_cache[mint] = (rs.time.time(), {'mint': mint, 'top10Pct': 12.0, 'checkedAt': 1})
        return rs._intel_cache[mint][1]

    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    monkeypatch.setitem(rs._fuse_warm_n, 'restored', True)
    monkeypatch.setattr(rs, 'token_intel', slow_intel)
    e = en.Enricher(boot_at=0.0); e.tokens = 500.0
    monkeypatch.setattr(rs, '_ENRICH', e)
    monkeypatch.setattr(rs, '_intel_waiters', {})
    monkeypatch.setitem(rs._enrich_timer, 'h', None)
    rs._intel_cache.pop('DedupeMint', None); rs._intel_failed.clear()

    async def go():
        return await asyncio.gather(*[rs._runner_intel('DedupeMint', en.PRIO['READY'], 'test', wait=True) for _ in range(8)])   # 8 askers, the same coin, at once
    out = asyncio.run(go())
    assert len(calls) == 1 and all(o and o['top10Pct'] == 12.0 for o in out) and e.count['started'] == 1 and e.count['joined'] == 7

    async def boom(chain, mint):
        calls.append('boom')
        raise RuntimeError('pool exhausted')
    monkeypatch.setattr(rs, 'token_intel', boom)
    monkeypatch.setitem(rs._enrich_timer, 'h', None)
    calls.clear(); rs._intel_cache.pop('FailMint', None)
    e.tokens, e.tokAt = en.BURST, rs.time.time()   # (the first scan spent the budget: a second FIRST scan would wait ~16s for it — refill for the test)
    ask = lambda: asyncio.run(rs._runner_intel('FailMint', en.PRIO['READY'], 'test', wait=True))
    assert ask() is None and ask() is None
    assert calls == ['boom'] and e.status('FailMint', rs.time.time()) == 'UNAVAILABLE'       # the second ask inside its back-off never reaches the RPC
    rs._intel_cache.pop('DedupeMint', None)


def test_a_busy_coin_pages_back_to_its_launch_and_unknown_launch_is_never_a_fake_zero(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    calls = []

    def page(n, start):
        return [{'signature': f's{start + i}', 'slot': 10_000 - start - i} for i in range(n)]

    async def fake_rpc(http, method, params, scan=True):
        calls.append(method)
        if method == 'getTokenSupply':
            return {'value': {'uiAmount': 1_000_000_000.0}}
        if method == 'getTokenLargestAccounts':
            return {'value': []}
        if method == 'getSignaturesForAddress':
            before = (params[1] or {}).get('before')
            return page(1000, 0) if not before else page(5, 1000)          # 1,005 txs: the launch is on page 2
        if method == 'getTransaction':
            return {'slot': 10_000 - 1004, 'transaction': {'message': {'accountKeys': [{'pubkey': 'REAL_CREATOR'}]}}}
        return {'value': []}

    async def none(*a, **k):
        return None
    monkeypatch.setattr(rs, '_rpc', fake_rpc); monkeypatch.setattr(rs, '_record_offenders', none); monkeypatch.setattr(rs, 'funder_lookup', lambda w: None)
    mint = 'BusyCoinTestMint111111111111111111111111pump'
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None)
    out = asyncio.run(rs.token_intel('solana', mint))
    assert calls.count('getSignaturesForAddress') == 2 and out['creator'] == 'REAL_CREATOR' and out['historyComplete'] is True

    async def endless(http, method, params, scan=True):            # never reaches the launch within the page budget
        if method == 'getSignaturesForAddress':
            return page(1000, 0)
        return await fake_rpc(http, method, params, scan)
    monkeypatch.setattr(rs, '_rpc', endless)
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None)
    out = asyncio.run(rs.token_intel('solana', mint))
    assert out['historyComplete'] is False and out['bundledWallets'] is None and out['insidersHoldingPct'] is None   # unknown, not 0
    rs._launch_facts.pop(mint, None); rs._intel_cache.pop(mint, None)
