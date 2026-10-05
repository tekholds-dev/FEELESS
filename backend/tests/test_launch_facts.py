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
