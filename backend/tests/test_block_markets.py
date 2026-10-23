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
