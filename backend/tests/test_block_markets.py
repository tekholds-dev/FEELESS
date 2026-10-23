"""🏙 The family block = real markets: added by the Don, under construction until a real position is proved, errands from the position."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import block_markets as bm  # noqa: E402

FAM = {'owner': 'DON', 'block': []}
MK = {'jito': {'name': 'Jito', 'kind': 'stake', 'url': 'https://jito.network', 'tvl': 2e9}, 'orca': {'name': 'Orca', 'kind': 'dex', 'url': 'https://orca.so'},
      'meteora': {'name': 'Meteora', 'kind': 'dex'}, 'jupsol': {'name': 'JupSOL', 'kind': 'stake'}}


def test_only_the_don_underboss_or_creator_adds_and_the_block_grows():
    c = {**FAM, 'block': []}
    bm.add(c, 'jito', 'DON', 100, known=MK)
    bm.add(c, 'orca', 'UB', 101, rank={'UB': 'underboss'}, known=MK)
    bm.add(c, 'meteora', 'ANY', 102, staff=True, known=MK)
    assert [x['key'] for x in bm.lots_of(c)] == ['jito', 'orca', 'meteora']
    for bad, kw in (('jupsol', {'me': 'SOLDIER'}), ('jito', {'me': 'DON'}), ('nope', {'me': 'DON'})):
        with pytest.raises(ValueError):
            bm.add(c, bad, kw['me'], 103, known=MK)   # a soldier · a duplicate · a market not in the city
    bm.remove(c, 'orca', 'DON')
    assert [x['key'] for x in bm.lots_of(c)] == ['jito', 'meteora']
    big = {'owner': 'DON', 'block': [{'key': f'k{i}'} for i in range(bm.MAX)]}
    with pytest.raises(ValueError):
        bm.add(big, 'jito', 'DON', 1)


def test_a_building_is_under_construction_until_a_real_position_is_proved():
    lots = [{'key': 'jito'}, {'key': 'orca'}, {'key': 'meteora'}, {'key': 'jupsol'}]
    assert bm.needs(lots) == {'mints': {bm.MINTS['jito'], bm.MINTS['jupsol']}, 'nft': True, 'kamino': False}
    assets = [{'name': 'Orca Whirlpool Position', 'symbol': 'OWP'}, {'name': 'Mad Lads #1', 'symbol': 'MAD'}]
    assert bm.nft_count(assets, 'orca') == 1 and bm.nft_count(assets, 'raydium') == 0
    held = {'jito': {'amount': 2.5, 'usd': 540.0}, 'orca': {'n': bm.nft_count(assets, 'orca')}, 'meteora': {'usd': 999}}
    apys = bm.lst_apys([{'kind': 'stake', 'sym': 'JITOSOL', 'apy': 4.85}, {'kind': 'stake', 'sym': 'JUPSOL', 'apy': 5.4}, {'kind': 'lend', 'sym': 'JUPSOL', 'apy': 99}])
    assert apys == {'jito': 4.85, 'jupsol': 5.4}
    v = {b['key']: b for b in bm.view(lots, MK, held, apys=apys, mine=True)}
    assert v['jito']['state'] == 'built' and v['jito']['usd'] == 540.0 and v['jito']['band'] == '$$'
    assert v['orca']['state'] == 'built'
    assert v['meteora']['state'] == 'construction' and 'not wired' in v['meteora']['why']   # no reader → never shown as built
    assert v['jupsol']['state'] == 'construction' and v['jupsol']['errands'][0]['kind'] == 'build'
    sw = [e for e in v['jito']['errands'] if e['kind'] == 'switch'][0]
    assert sw['swap'] == {'from': bm.MINTS['jito'], 'to': bm.MINTS['jupsol']} and sw['gain'] == 0.55   # JupSOL pays 0.55 pp more → switch?
    assert [e['kind'] for e in v['orca']['errands']] == ['range']
    other = {b['key']: b for b in bm.view(lots, MK, held, apys=apys, mine=False)}
    assert 'usd' not in other['jito'] and 'errands' not in other['jito'] and other['jito']['band'] == '$$'   # other families: a band, never a balance


def test_the_service_adds_a_market_and_only_a_real_position_builds_it(monkeypatch):
    import asyncio
    rs = pytest.importorskip('reputation_service')
    don = 'D' * 44
    rs._json_save(rs.CREWS_PATH, {'crews': {'c1': {'id': 'c1', 'tag': 'FRT', 'name': 'Sicario', 'owner': don, 'members': [don]}}, 'by': {don: 'c1'}})
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: don)
    monkeypatch.setattr(rs, '_city_ctx', lambda c, me, now: (1.0, {}))

    async def mk():
        return {'markets': [{'key': 'jito', 'name': 'Jito', 'kind': 'stake', 'url': 'https://jito.network'}, {'key': 'meteora', 'name': 'Meteora', 'kind': 'dex'}]}

    async def pools():
        return {'pools': [{'kind': 'stake', 'sym': 'JITOSOL', 'apy': 4.85}]}
    monkeypatch.setattr(rs, 'familia_markets', mk); monkeypatch.setattr(rs, 'familia_pools', pools)
    held = {}

    async def reads(c, lots, now):
        return held
    monkeypatch.setattr(rs, '_fblock_reads', reads)
    v = asyncio.run(rs.familia_block_act(rs.BlockAct(address=don, session='s', act='add', key='jito')))
    assert [(b['key'], b['state']) for b in v['buildings']] == [('jito', 'construction')] and v['canBuild'] and v['open'] == 4
    assert {m['key'] for m in v['catalog']} == {'meteora'}                       # the catalog offers what is not on the block yet
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.familia_block_act(rs.BlockAct(address=don, session='s', act='add', key='notamarket')))
    held['jito'] = {'amount': 1.2, 'usd': 260.0}                                  # the Don really holds JitoSOL now
    v = asyncio.run(rs.familia_block(don, 's'))
    assert v['buildings'][0]['state'] == 'built' and v['total'] == 260.0 and v['built'] == 1 and v['buildings'][0]['apy'] == 4.85
    pub = asyncio.run(rs.familia_block_visit('c1'))
    assert pub['buildings'][0]['band'] == '$$' and 'usd' not in pub['buildings'][0] and 'catalog' not in pub   # visitors: a band, no balances


def test_the_intake_adds_safe_pump_front_runners_beside_the_agents_list(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    board = [{'mint': 'AAApump', 'symbol': 'AAA', 'pairAddress': 'PA', 'mcap': 50_000, 'liq': 9_000, 'chg5m': 4.0, 'ageH': 0.5, 'safe': True, 'rank': 1},
             {'mint': 'BBBpump', 'symbol': 'BBB', 'safe': False, 'rank': 2},                      # failed its scan → never shown
             {'mint': 'CCCxyz', 'symbol': 'CCC', 'safe': True, 'rank': 3},                        # not a Pump coin
             {'mint': 'DDDpump', 'symbol': 'DDD', 'safe': None, 'rank': 4}, {'mint': 'AGENTpump', 'symbol': 'AG', 'safe': True}]
    monkeypatch.setattr(rs, '_open_board', lambda n=None: board)
    out = rs._intake_pump([{'mint': 'AGENTpump'}], 5)
    assert [r['mint'] for r in out] == ['AAApump', 'DDDpump'] and out[0]['src'] == 'pump' and out[0]['ageMin'] == 30 and 'scan clean' in out[0]['read']
    assert rs._intake_pump([], 1) == out[:1] and rs._intake_pump([], 0) == []
