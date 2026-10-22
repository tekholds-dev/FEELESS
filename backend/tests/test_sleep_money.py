import sleep_money as sm

SOL = 'So11111111111111111111111111111111111111112'
JUPSOL = 'jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v'
POOLS = [{'id': 'p1', 'kind': 'stake', 'sym': 'JUPSOL', 'apy': 7.2, 'tvl': 9e8, 'hold': JUPSOL, 'proto': 'Jupiter'},
         {'id': 'p2', 'kind': 'stake', 'sym': 'JITOSOL', 'apy': 6.8, 'tvl': 2e9, 'hold': 'J1to', 'proto': 'Jito'},
         {'id': 'p3', 'kind': 'lend', 'sym': 'USDC', 'apy': 6.1, 'tvl': 5e8, 'stable': True, 'proto': 'Jupiter Lend', 'project': 'jupiter-lend'},
         {'id': 'p4', 'kind': 'lend', 'sym': 'SOL', 'apy': 4.0, 'tvl': 5e8, 'stable': False},
         {'id': 'p5', 'kind': 'perps', 'sym': 'JLP', 'apy': 21.0, 'tvl': 1e9},
         {'id': 'p6', 'kind': 'vault', 'sym': 'SOL-USDC', 'apy': 33.0, 'tvl': 4e6, 'il': True},
         {'id': 'p7', 'kind': 'v2', 'sym': 'X-SOL', 'apy': None, 'tvl': 1e6}]
KAMINO = [{'liquidityTokenMint': SOL, 'liquidityToken': 'SOL', 'supplyApy': 0.04, 'borrowApy': 0.053, 'maxLtv': 0.74, 'totalSupplyUsd': 2.5e8},
          {'liquidityTokenMint': SOL, 'liquidityToken': 'SOL', 'supplyApy': 0.0, 'borrowApy': 0.5, 'maxLtv': 0.1, 'totalSupplyUsd': 10},     # a dust dupe never wins
          {'liquidityTokenMint': JUPSOL, 'liquidityToken': 'JupSOL', 'supplyApy': 0.0, 'borrowApy': 0.025, 'maxLtv': 0.65, 'totalSupplyUsd': 4.9e7}]


def test_kamino_rates_keep_the_deepest_reserve():
    k = sm.kamino_rates(KAMINO)
    assert k[SOL] == {'sym': 'SOL', 'supply': 4.0, 'borrow': 5.3, 'maxLtv': 0.74, 'tvl': 250000000}
    assert k[JUPSOL]['maxLtv'] == 0.65 and sm.kamino_rates([None, {'x': 1}]) == {}


def test_loop_math_and_its_safety_cap():
    plays = sm.loop_plays(7.2, 5.3, 0.65)
    assert [p['x'] for p in plays] == [1.5, 2.0]                         # 3x = 0.667 LTV > 0.9 × 0.65 → never offered
    two = plays[1]
    assert two['apy'] == round(7.2 * 2 - 5.3, 2) and two['ltv'] == 0.5 and two['cushion'] == round(1 - 0.5 / 0.65, 3)
    assert sm.loop_plays(7.2, 5.3, 0) == []


def test_strategies_ride_only_on_live_rows():
    st = {s['key']: s for s in sm.strategies(POOLS, sm.kamino_rates(KAMINO))}
    assert list(st) == ['lst', 'stable', 'jlp', 'vault', 'loop']
    assert st['lst']['rows'] == ['p1', 'p2'] and st['stable']['rows'] == ['p3'] and st['jlp']['rows'] == ['p5'] and st['vault']['rows'] == ['p6']
    assert st['stable']['earn'] == {'day': round(1000 * 0.061 / 365, 4), 'month': round(1000 * 0.061 / 12, 2), 'year': 61.0}
    lp = st['loop']['loops']
    assert [x['sym'] for x in lp] == ['JUPSOL'] and lp[0]['borrow'] == 5.3     # JitoSOL has no Kamino reserve here → no loop for it
    assert st['loop']['risk']['liq'] == 3 and st['jlp']['risk']['il'] == 2
    assert [s['key'] for s in sm.strategies([POOLS[6]], {})] == []              # nothing live → nothing offered
    assert 'loop' not in {s['key'] for s in sm.strategies(POOLS, None)}          # Kamino unread → no loop numbers invented
