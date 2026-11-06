"""The money board measures with real rows and never invents a price it cannot read."""
import grow_board as gb
import py_agents as pa

SOLM = gb.SOL_MINT


def pool(x='CARDS', y='USDC', **k):
    return gb.pool_row({'pool': 'P', 'name': f'{x}-{y}', 'venue': 'raydium', 'symX': x, 'symY': y, 'feePct': 0.25, 'tvl': 1000.0, 'vol24': 100, 'rate': 0.001, **k})


def bars(*closes, t0=3600, vol=400.0):
    return [[t0 + i * 3600, c, c, c, c, vol] for i, c in enumerate(closes)]


def test_kinds_and_risks_read_honestly():
    assert pool()['risk'] == 'half' and pool('USDC', 'USDT')['risk'] == 'none' and pool('BONK', 'SOL')['risk'] == 'both' and pool()['per1k24'] == 1.0 and pool()['yearPct'] == 36.5
    rows = gb.lend_rows([{'chain': 'Solana', 'exposure': 'single', 'ilRisk': 'no', 'tvlUsd': 9e6, 'pool': 'a', 'symbol': 'USDC', 'stablecoin': True, 'project': 'kamino-lend', 'apy': 6.0, 'apyReward': 1.0},
                         {'chain': 'Solana', 'exposure': 'single', 'ilRisk': 'no', 'tvlUsd': 9e6, 'pool': 'b', 'symbol': 'JITOSOL', 'project': 'jito', 'apy': 7.0, 'underlyingTokens': [SOLM]},
                         {'chain': 'Solana', 'exposure': 'single', 'ilRisk': 'no', 'tvlUsd': 9e6, 'pool': 'c', 'symbol': 'WEIRD', 'project': 'x', 'apy': 900.0},
                         {'chain': 'Ethereum', 'exposure': 'single', 'ilRisk': 'no', 'tvlUsd': 9e6, 'pool': 'd', 'symbol': 'USDC', 'stablecoin': True, 'project': 'x'},
                         {'chain': 'Solana', 'exposure': 'single', 'ilRisk': 'no', 'tvlUsd': 1e3, 'pool': 'e', 'symbol': 'USDC', 'stablecoin': True, 'project': 'x', 'apy': 90}])
    assert [(r['kind'], r['risk']) for r in rows] == [('lend', 'none'), ('stake', 'coin')] and rows[0]['rewardPct'] == 1.0


def test_stocks_take_their_deepest_dollar_pool_and_earn_nothing():
    pairs = [{'chainId': 'solana', 'pairAddress': 'a', 'dexId': 'raydium', 'baseToken': {'symbol': 'SPYx'}, 'quoteToken': {'symbol': 'USDC'}, 'liquidity': {'usd': 1e6}}, {'chainId': 'solana', 'pairAddress': 'b', 'baseToken': {'symbol': 'SPYx'}, 'quoteToken': {'symbol': 'USDC'}, 'liquidity': {'usd': 2e6}},
             {'chainId': 'solana', 'pairAddress': 'c', 'baseToken': {'symbol': 'SPYx'}, 'quoteToken': {'symbol': 'SOL'}, 'liquidity': {'usd': 9e6}}, {'chainId': 'solana', 'pairAddress': 'd', 'baseToken': {'symbol': 'STONK'}, 'quoteToken': {'symbol': 'USDC'}, 'liquidity': {'usd': 9e6}}, {'chainId': 'base', 'pairAddress': 'e', 'baseToken': {'symbol': 'QQQx'}, 'quoteToken': {'symbol': 'USDC'}, 'liquidity': {'usd': 9e6}}]
    rows = gb.stock_rows(pairs); assert [r['pair'] for r in rows] == ['b'] and rows[0]['per1k24'] == 0
    assert gb.stock_points(bars(2.0, 3.0))[0][1] == {'t': 7200, 'a': 3.0, 'b': 1.0, 'fee': 0.0}


def test_a_pool_earns_what_the_venue_says_it_paid_and_candle_volume_only_shapes_the_hours():
    pts, why = gb.pool_points(pool(), bars(1.0, 1.1)); assert not why and abs(sum(q['fee'] for q in pts) - 0.001) < 1e-12
    big = [[3600 * i, 1.0, 1.0, 1.0, 1.0, 9e9 if i == 5 else 1.0] for i in range(1, 25)]   # absurd candle volume can never inflate what it earned
    pts, _ = gb.pool_points(pool(), big); assert abs(sum(q['fee'] for q in pts) - 0.001) < 1e-12 and pts[4]['fee'] > pts[3]['fee']
    pts, _ = gb.pool_points(pool(), [[3600 * i, 1.0, 1.0, 1.0, 1.0, 0.0] for i in range(1, 25)]); assert abs(sum(q['fee'] for q in pts) - 0.001) < 1e-12   # no volume: an even pace


def test_it_never_guesses_a_coin_it_cannot_price():
    assert gb.pool_points(pool('BONK', 'WIF'), bars(1.0, 1.1))[0] == []
    sol = bars(100.0, 110.0)
    assert gb.pool_points(pool('SOL', 'BONK'), bars(101.0, 111.0), sol)[0] == []   # the candles follow SOL, so BONK is unknown
    pts, _ = gb.pool_points(pool('BONK', 'SOL'), bars(0.001, 0.002), sol); assert pts[1]['b'] == 110.0
    assert gb.pool_points(pool('BONK', 'SOL'), bars(0.001), [])[0] == []


def test_lending_uses_its_real_daily_rate_and_staking_moves_with_sol():
    now = 20 * 86400.0; chart = [{'timestamp': '1970-01-02T00:00:00.000Z', 'apy': 8.76}]
    pts, _ = gb.lend_points({'kind': 'lend'}, chart, [], now); assert pts and abs(pts[-1]['fee'] - 0.00001 ) < 1e-9 and pts[-1]['a'] == 1.0
    start = int(now // 3600 * 3600) - gb.HOURS * 3600
    sp, _ = gb.lend_points({'kind': 'stake'}, chart, bars(100.0, 90.0, t0=start), now); assert [p['a'] for p in sp] == [100.0, 90.0]
    assert gb.lend_points({'kind': 'lend'}, [], [], now)[0] == []


def test_py_agents_practise_on_filed_proofs_and_keep_the_others_waiting():
    store = {'cats': {'a': {'powFolders': [{'status': 'closed', 'id': 'x'}, {'status': 'open'}], 'popFolders': [{'status': 'closed', 'shots': [{'file': 'a'}]}]}}}
    folders = pa.filed(store); assert len(folders) == 2
    rows = {r['k']: r for r in pa.record({}, folders)}
    assert rows['sherlock']['tried'] == 2 and rows['sherlock']['triedOk'] == 1 and rows['sherlock']['triedNo'] and rows['devil']['tried'] == 2 and 'tried' not in rows['tally'] and rows['tally']['checked'] == 0
