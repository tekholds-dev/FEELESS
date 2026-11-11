"""🌊 SITE-17 C03: the Meteora building is built only by a real open position, read from Meteora's own by-wallet portfolio (fixture = a real
answer for a real wallet, 2026-11-10: 21 positions, all out of range). Out-of-range positions become a real errand."""
import json
from pathlib import Path

import block_markets as bm

REAL = json.loads((Path(__file__).parent / 'fixtures' / 'meteora_portfolio.json').read_text())


def test_a_real_portfolio_builds_the_meteora_building_with_its_out_of_range_errand():
    h = bm.meteora_held([REAL])
    assert h['n'] == 21 and h['ranges']['out'] == 21 and h['ranges']['worst']['pair'] == 'WBTC-USDC'
    assert bm.proof_of('meteora') == ('api', 'meteora') and bm.needs([{'key': 'meteora'}])['meteora'] is True
    b = bm.view([{'key': 'meteora', 'at': 1}], {'meteora': {'name': 'Meteora'}}, {'meteora': h}, mine=True)[0]
    assert b['state'] == 'built' and any(e['kind'] == 'range' and e['urgent'] and '21 of 21' in e['text'] for e in b['errands'])


def test_no_open_position_stays_under_construction_and_others_never_see_the_numbers():
    assert bm.meteora_held([{'total': {'totalPositions': 0}, 'pools': []}]) is None and bm.meteora_held([]) is None
    b = bm.view([{'key': 'meteora'}], {}, {}, mine=False)[0]
    assert b['state'] == 'construction' and 'usd' not in b and 'errands' not in b
    two = bm.meteora_held([{'total': {'totalPositions': 1, 'balances': '15.93', 'unclaimedFees': '0.67', 'pnl': '-1.4'}, 'pools': [{'tokenX': 'SOL', 'tokenY': 'USDC', 'positionsOutOfRange': [], 'outOfRange': False}]}])
    assert two == {'n': 1, 'usd': 15.93, 'fees': 0.67, 'pnl': -1.4, 'ranges': {'n': 1, 'out': 0, 'near': 0, 'worst': {}}}
    assert [e['kind'] for e in bm.errands({'key': 'meteora', 'state': 'built', 'name': 'Meteora', 'ranges': two['ranges'], 'fees': 0.67}, {})] == ['claim']
