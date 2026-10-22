"""🏦 Fee City's markets: live DeFi markets + today's top coins, read-only (owner, 2026-10-21). Network faked."""
import fee_markets as fm

P = lambda dex, base, addr, liq, vol, ch, pair: {'chainId': 'solana', 'dexId': dex, 'pairAddress': pair, 'baseToken': {'symbol': base, 'address': addr}, 'quoteToken': {'symbol': 'SOL'},
                                                 'priceUsd': '1.5', 'liquidity': {'usd': liq}, 'volume': {'h24': vol}, 'priceChange': {'h24': ch, 'h1': 1}, 'marketCap': 9e6}
PAIRS = [P('raydium', 'WIF', 'W1', 5e6, 9e6, 4.2, 'R1'), P('raydium', 'BONK', 'B1', 9e6, 3e6, -2, 'R2'), P('orca', 'WIF', 'W1', 7e6, 1e6, 1, 'O1'),
         P('pumpswap', 'SOL', fm.SOL, 1e9, 1e9, 0, 'S1'), P('meteora', 'USDC', 'U1', 1e9, 1e9, 0, 'M1')]


def test_markets_take_their_tvl_move_and_deepest_pool():
    v = fm.build({'raydium': 1.2e9, 'kamino-lend': 1.3e9}, {'raydium': (1.0e9, 0)}, PAIRS, 100)
    m = {x['key']: x for x in v['markets']}
    assert len(v['markets']) == len(fm.MARKETS) and m['raydium']['tvl'] == 1_200_000_000 and m['raydium']['move'] == 20.0
    assert m['raydium']['pool']['base'] == 'WIF' and m['raydium']['pool']['vol'] == 9_000_000                  # the busiest real pool, not the deepest
    assert fm.top_pool([P('orca', 'X', 'X1', 10, 9e9, 0, 'Z')], ('orca',)) is None                              # a pool under the liquidity floor never shows
    assert m['kamino']['district'] == 'vault' and m['kamino']['pool'] is None and m['kamino']['move'] is None and m['jito']['tvl'] is None
    assert all(x['url'].startswith('https://') and x['offer'] for x in v['markets'])


def test_top_coins_one_row_a_token_never_sol_or_stables():
    c = fm.top_coins(PAIRS)
    assert [x['sym'] for x in c] == ['WIF', 'BONK'] and c[0]['pair'] == 'O1' and c[0]['vol'] == 10_000_000   # WIF: both pools' volume, opened on its deepest (Orca)
