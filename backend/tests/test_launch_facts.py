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
    rs = pytest.importorskip('reputation_service')
    calls = []

    async def slow_intel(chain, mint):
        calls.append(mint)
        await asyncio.sleep(0.05)
        return {'mint': mint, 'top10Pct': 12.0, 'checkedAt': 1}

    monkeypatch.setattr(rs, 'token_intel', slow_intel)
    rs._intel_cache.pop('DedupeMint', None); rs._intel_inflight.clear(); rs._intel_failed.clear()

    async def go():
        return await asyncio.gather(*[rs._runner_intel('DedupeMint') for _ in range(8)])   # 8 board builds ask for the same coin at once
    out = asyncio.run(go())
    assert len(calls) == 1 and all(o and o['top10Pct'] == 12.0 for o in out)

    async def boom(chain, mint):
        calls.append('boom')
        raise RuntimeError('pool exhausted')
    monkeypatch.setattr(rs, 'token_intel', boom)
    calls.clear(); rs._intel_cache.pop('FailMint', None)
    assert asyncio.run(rs._runner_intel('FailMint')) is None and asyncio.run(rs._runner_intel('FailMint')) is None
    assert calls == ['boom']       # the second ask inside 45s never reaches the RPC


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
