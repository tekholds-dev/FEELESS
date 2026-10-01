"""Vault designer API: ≤3 pools, fee caps, fee wallet from Trading & fees, live simulation. Network faked."""
import asyncio

import pytest

rs = pytest.importorskip('reputation_service')
PAIRS = {'A': {'pairAddress': 'A', 'priceUsd': '1', 'liquidity': {'usd': 5e6}, 'volume': {'h24': 2e6}, 'priceChange': {'h24': 1}, 'labels': ['CLMM'], 'dexId': 'raydium'},
         'B': {'pairAddress': 'B', 'priceUsd': '1', 'liquidity': {'usd': 1e6}, 'volume': {'h24': 3e5}, 'priceChange': {'h24': -2}, 'dexId': 'raydium'}}


class Req:
    def __init__(self, body=None): self._b = body or {}
    async def json(self): return self._b


def test_vault_design_and_simulation(monkeypatch):
    async def pairs(legs): return {leg['pairAddress']: PAIRS[leg['pairAddress']] for leg in legs if leg['pairAddress'] in PAIRS}
    async def sol(): return 200.0
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {**rs.FEE_DEFAULTS, 'vaultFeeWallet': 'FeeWa11et1111111111111111111111111111111111'})
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_vaults_save(Req({'name': 'Too many', 'pools': [{'pairAddress': x} for x in 'ABCD'][:0]})))
    vid = asyncio.run(rs.admin_vaults_save(Req({'name': 'FEE Yield', 'mgmtBps': 9999, 'perfBps': 9999,
                                                 'pools': [{'pairAddress': 'A', 'kind': 'v3', 'weight': 1}, {'pairAddress': 'B', 'kind': 'v2', 'weight': 1}, {'pairAddress': 'C'}, {'pairAddress': 'D'}]})))['id']
    out = asyncio.run(rs.admin_vaults(Req(), deposit=100))
    v = out['vaults'][0]
    assert v['id'] == vid and len(v['pools']) == 3 and v['mgmtBps'] == 300 and v['perfBps'] == 3000 and v['status'] == 'design'
    assert v['feeWallet'].startswith('FeeWa11et') and out['maxPools'] == 3
    assert round(sum(v['sim']['allocation'].values()) + v['sim']['bufferSol'], 6) == 100
    assert rs.FeeCfg(platformFeeBps=100, vaultFeeWallet='not a wallet').vaultFeeWallet == ''   # junk is dropped, not saved
