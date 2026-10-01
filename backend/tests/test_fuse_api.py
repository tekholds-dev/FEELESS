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


def test_fuse_lab_caps_users_at_3_and_admin_gets_6_and_manual_weights(monkeypatch):
    P = {f'P{i}': {**PAIRS['P1'], 'pairAddress': f'P{i}'} for i in range(1, 7)}
    async def pairs(legs): return {leg['pairAddress']: P[leg['pairAddress']] for leg in legs}
    async def px(): return 100.0
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_sol_usd_live', px)
    four = [{'chainId': 'solana', 'pairAddress': f'P{i}'} for i in range(1, 5)]
    monkeypatch.setattr(rs, '_require_admin', lambda r: (_ for _ in ()).throw(rs.HTTPException(403, 'no')))
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuses_preview(rs.FusePreview(pools=four, sol=1), Req()))
    assert asyncio.run(rs.fuses_preview(rs.FusePreview(pools=four[:3], sol=1), Req()))['cap'] == 3
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    man = [{**four[0], 'weight': 75}, {**four[1], 'weight': 25}]
    p = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=man, sol=4, manual=True), Req()))
    assert p['cap'] == 10 and [x['weight'] for x in p['legs']] == [75, 25] and p['legs'][0]['sol'] == 3
    six = [{'chainId': 'solana', 'pairAddress': f'P{i}'} for i in range(1, 7)]
    assert len(asyncio.run(rs.fuses_preview(rs.FusePreview(pools=six, sol=1), Req()))['legs']) == 6


def test_admin_evolve_breeds_from_discovered_pools(monkeypatch):
    raw = [{'chainId': 'solana', 'pairAddress': f'Q{i}', 'priceUsd': '1', 'liquidity': {'usd': 100000 + i * 20000}, 'volume': {'h24': 50000 * (i + 1)},
            'priceChange': {'h24': i - 3}, 'baseToken': {'symbol': f'T{i}', 'address': f'M{i}'}, 'quoteToken': {'symbol': 'SOL'}} for i in range(8)]
    async def disc(chain): return raw
    async def px(): return 150.0
    monkeypatch.setattr(rs, '_fuse_discover_pairs', disc); monkeypatch.setattr(rs, '_sol_usd_live', px)
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    d = asyncio.run(rs.fuses_evolve(Req(), rs.FuseEvolveIn(style='degen', legs=3, generations=5, population=10, sol=0.05, seed=2)))
    c = d['champions'][0]
    assert len(d['history']) == 5 and len(c['legs']) == 3 and c['legs'][0]['symbol'].startswith('T') and d['pool'] == 8


def test_fuse_hq_position_pnl_arena_bloodline_best3(monkeypatch):
    px = {'P1': 4.0, 'P2': 0.01}
    async def pairs(legs): return {leg['pairAddress']: {**PAIRS[leg['pairAddress']], 'priceUsd': str(px[leg['pairAddress']])} for leg in legs}
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    me = rs.primary_of(W)
    rs._json_save(rs.FEELESS_TRADES_PATH, {me: [{'tx': 'S1', 'side': 'buy', 'usd': 2.0, 'tokens': 1.0, 'token': 'M1'}]})
    legs = [{'pairAddress': 'P1', 'symbol': 'SOL', 'signature': 'S1'}, {'pairAddress': 'P2', 'symbol': 'FEE', 'signature': 'FAKE'}]
    assert asyncio.run(rs.fuse_position(rs.FusePositionIn(address=W, session='s', legs=legs)))['legs'] == 1     # fake sig dropped
    assert asyncio.run(rs.fuse_position(rs.FusePositionIn(address=W, session='s', legs=legs)))['counted'] is False  # once only
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuse_position(rs.FusePositionIn(address=W, session='s', legs=[legs[1]])))
    pnl = asyncio.run(rs.fuse_pnl(W))
    assert pnl['costUsd'] == 2 and pnl['valueUsd'] == 4 and pnl['pnlPct'] == 100
    champ = {'fitness': 70, 'legs': [{'pairAddress': 'P1', 'symbol': 'SOL', 'weight': 50}, {'pairAddress': 'P2', 'symbol': 'FEE', 'weight': 50}]}
    asyncio.run(rs.fuse_hq_admin_save(Req({'action': 'arena', 'style': 'degen', 'champion': champ})))
    asyncio.run(rs.fuse_hq_admin_save(Req({'action': 'bloodline', 'style': 'degen', 'champion': champ})))
    d = rs._json_load(rs.FUSE_HQ_PATH, {}); d['arena'][0]['at'] -= 25 * 3600; rs._json_save(rs.FUSE_HQ_PATH, d)
    px['P1'] = 8.0
    hq = asyncio.run(rs.fuse_hq_admin(Req()))
    assert hq['arena'][0]['settled'] and hq['arena'][0]['pnlPct'] == 50 and len(hq['bloodline']) == 1 and hq['book']['positions'] == 1
    assert hq['board'][0]['style'] == 'degen' and hq['bestStyle'] == 'yield'      # one run isn't proof yet


def test_creator_buying_own_fuse_earns_no_cut_and_costs_rep(monkeypatch):
    async def pairs(legs): return {leg['pairAddress']: PAIRS[leg['pairAddress']] for leg in legs}
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    me = rs.primary_of(W)
    fid = asyncio.run(rs.admin_fuses_save(Req({'name': 'Mine', 'creator': me, 'creatorBps': 5000, 'legs': [{'chainId': 'solana', 'pairAddress': 'P1', 'weight': 1}, {'chainId': 'solana', 'pairAddress': 'P2', 'weight': 1}]})))['id']
    rs._json_save(rs.FEELESS_TRADES_PATH, {me: [{'tx': 'SELF', 'usd': 50, 'feelessFeeUsd': 1.0, 'side': 'buy', 'tokens': 1, 'ts': time.time()}]})
    rs._shield_cache.clear()
    asyncio.run(rs.fuse_buy(fid, rs.FuseBuy(address=W, session='s', signature='SELF')))
    b = rs._json_load(rs.FUSES_PATH, {})['buys'][-1]
    assert b['selfDeal'] and b['creatorUsd'] == 0
    assert rs._fuse_rep(me)['points'] < 0


def test_prebuilt_rail_one_card_per_style_and_user_cap(monkeypatch):
    raw = [{'chainId': 'solana', 'pairAddress': f'R{i}', 'priceUsd': '1', 'liquidity': {'usd': 100000 + i * 30000}, 'volume': {'h24': 60000 * (i + 1)},
            'priceChange': {'h24': i * 2 - 6}, 'baseToken': {'symbol': f'K{i}', 'address': f'N{i}'}, 'quoteToken': {'symbol': 'SOL'}} for i in range(9)]
    async def disc(chain): return raw
    async def px(): return 150.0
    monkeypatch.setattr(rs, '_fuse_discover_pairs', disc); monkeypatch.setattr(rs, '_sol_usd_live', px)
    monkeypatch.setattr(rs, '_require_admin', lambda r: (_ for _ in ()).throw(rs.HTTPException(403, 'no')))
    rs._fuse_prebuilt_cache.clear()
    d = asyncio.run(rs.fuses_prebuilt(Req(), legs=6, budget=5))
    assert d['legs'] == 3 and {c['style'] for c in d['cards']} == set(rs._fuse.STYLES) and all(len(c['legs']) == 3 for c in d['cards'])
    assert d['cards'][0]['legs'][0]['baseAddress'].startswith('N')


def test_fuse_holders_board(monkeypatch):
    async def pairs(legs): return {leg['pairAddress']: {**PAIRS[leg['pairAddress']], 'priceUsd': '3'} for leg in legs}
    monkeypatch.setattr(rs, '_fuse_pairs', pairs)
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': '1', 'wallet': 'A' * 43, 'name': 'Core', 'at': 5, 'legs': [{'pairAddress': 'P1', 'usd': 2, 'tokens': 1}]},
                                                  {'id': '2', 'wallet': 'B' * 43, 'name': 'Meme', 'at': 6, 'legs': [{'pairAddress': 'P1', 'usd': 6, 'tokens': 1}]}]})
    rs._fuse_holders_cache.clear()
    d = asyncio.run(rs.fuse_holders())
    assert d['total'] == 2 and d['holders'][0]['pnlPct'] == 50 and d['holders'][1]['pnlPct'] == -50 and 'valueUsd' not in d['holders'][0]


def test_autopilot_tick_enters_each_style_once_and_alerts_bots(monkeypatch):
    raw = [{'chainId': 'solana', 'pairAddress': f'U{i}', 'priceUsd': '1', 'liquidity': {'usd': 100000 + i * 30000}, 'volume': {'h24': 60000 * (i + 1)},
            'priceChange': {'h24': i - 4}, 'baseToken': {'symbol': f'Z{i}', 'address': f'Y{i}'}, 'quoteToken': {'symbol': 'SOL'}} for i in range(8)]
    async def disc(chain): return raw
    async def px(): return 150.0
    async def prices(legs): return {leg['pairAddress']: 1.0 for leg in legs}
    sent = []
    monkeypatch.setattr(rs, '_fuse_discover_pairs', disc); monkeypatch.setattr(rs, '_sol_usd_live', px); monkeypatch.setattr(rs, '_hq_prices', prices)
    monkeypatch.setattr(rs, '_admin_wallets', lambda: ['ADMINWALLET'])
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: sent.append((a, k)))
    farm = 'Farm222222222222222222222222222222222222222'
    rs._json_save(rs.QUEST_STATE_PATH, {farm: {'days': [f'2026-08-{d:02d}' for d in range(1, 20)], 'first': 1}})
    asyncio.run(rs._fuse_autopilot_tick(now=1_000_000))
    asyncio.run(rs._fuse_autopilot_tick(now=1_000_100))      # same hour → no duplicates, no repeat alert
    arena = rs._json_load(rs.FUSE_HQ_PATH, {})['arena']
    assert sorted(e['style'] for e in arena) == sorted(rs._fuse.STYLES) and all(e['auto'] for e in arena)
    assert len(sent) == 1 and 'Bot shield flagged' in sent[0][0][2] and sent[0][1]['meta']['source']
