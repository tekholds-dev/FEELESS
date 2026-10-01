"""FUSE API: admin creates a Fuse (launch prices captured, index 100), list shows live meta + score, a verified buy
credits the creator once, unverified signatures are refused, payouts reduce what's owed. Network faked."""
import asyncio
import time

import pytest

rs = pytest.importorskip('reputation_service')
W = 'Aaaa1111111111111111111111111111111111111111'
PAIRS = {'P1': {'pairAddress': 'P1', 'priceUsd': '2.0', 'liquidity': {'usd': 500000}, 'volume': {'h24': 400000}, 'priceChange': {'h24': 4}, 'baseToken': {'symbol': 'SOL'}},
         'P2': {'pairAddress': 'P2', 'priceUsd': '0.01', 'liquidity': {'usd': 80000}, 'volume': {'h24': 60000}, 'priceChange': {'h24': -8}, 'baseToken': {'symbol': 'FEE', 'address': 'FeeMint'}}}


class Req:
    def __init__(self, body=None): self._b = body or {}
    async def json(self): return self._b


def test_fuse_lifecycle(monkeypatch):
    async def pairs(legs): return {leg['pairAddress']: PAIRS[leg['pairAddress']] for leg in legs}
    monkeypatch.setattr(rs, '_fuse_pairs', pairs)
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_fuses_save(Req({'name': 'Solo', 'legs': [{'chainId': 'solana', 'pairAddress': 'P1', 'weight': 1}]})))
    fid = asyncio.run(rs.admin_fuses_save(Req({'name': 'FEE Core', 'emoji': '⚛️', 'creatorBps': 2500,
                                                'legs': [{'chainId': 'solana', 'pairAddress': 'P1', 'weight': 60}, {'chainId': 'solana', 'pairAddress': 'P2', 'weight': 40}]})))['id']
    f = asyncio.run(rs.fuses_list())['fuses'][0]
    assert f['index'] == 100 and f['tvlUsd'] == 580000 and f['score']['grade'] in 'ABCDF' and f['legs'][0]['weight'] == 60
    rs._json_save(rs.FEELESS_TRADES_PATH, {rs.primary_of(W): [{'tx': 'SIGX', 'usd': 50, 'feelessFeeUsd': 0.8, 'ts': time.time()}]})
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_buy(fid, rs.FuseBuy(address=W, session='s', signature='FAKE')))
    assert asyncio.run(rs.fuse_buy(fid, rs.FuseBuy(address=W, session='s', signature='SIGX')))['counted']
    assert not asyncio.run(rs.fuse_buy(fid, rs.FuseBuy(address=W, session='s', signature='SIGX')))['counted']
    st = asyncio.run(rs.fuses_list())['fuses'][0]['stats']
    assert st == {'buys': 1, 'volumeUsd': 50.0, 'creatorEarnedUsd': 0.2, 'creatorPaidUsd': 0.0, 'creatorOwedUsd': 0.2}
    asyncio.run(rs.admin_fuses_save(Req({'id': fid, 'paidUsd': 0.15})))
    assert asyncio.run(rs.fuses_list())['fuses'][0]['stats']['creatorOwedUsd'] == 0.05


def test_fuse_lab_discover_and_preview(monkeypatch):
    async def pairs(legs): return {leg['pairAddress']: PAIRS[leg['pairAddress']] for leg in legs}
    async def disc(chain): return [{**p, 'chainId': 'solana'} for p in PAIRS.values()] + [{**PAIRS['P1'], 'pairAddress': 'B1', 'chainId': 'base'}]
    async def px(): return 200.0
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_fuse_discover_pairs', disc); monkeypatch.setattr(rs, '_sol_usd_live', px)
    d = asyncio.run(rs.fuses_discover(lens='deep', chain='solana'))
    assert [p['pairAddress'] for p in d['pools']] == ['P1', 'P2']
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuses_preview(rs.FusePreview(pools=[{'chainId': 'solana', 'pairAddress': 'P1'}], sol=1)))
    p = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=[{'chainId': 'solana', 'pairAddress': 'P1'}, {'chainId': 'solana', 'pairAddress': 'P2'}], sol=2)))
    assert round(sum(x['sol'] for x in p['legs']), 6) == 2 and p['usd'] == 400 and abs(sum(x['weight'] for x in p['legs']) - 100) < 0.1
