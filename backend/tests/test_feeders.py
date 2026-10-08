import feeders as fd

R1, R2 = 'Y9ccqrALa5Yr3Bxzv8NQe37KP1Yy9uTCSJuap4Cpump', 'GeoepSP9AvW3AKWvknybTXVWibhZ3W97shjtkQ9npump'
SOL1, WSOL, USDC = '11111111111111111111111111111111', 'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
NOW = 1791502720000.0


def _c(i, quote, age_min=10, last_min=1, cap=3000, **kw):
    return {'mint': f'{i:0>3}' + 'A' * 40, 'symbol': f'K{i}', 'quote_mint': quote, 'usd_market_cap': cap, 'created_timestamp': NOW - age_min * 60000,
            'last_trade_timestamp': None if last_min is None else NOW - last_min * 60000, **kw}


def test_only_a_coin_paired_with_another_coin_is_a_feeder():
    assert fd.paired(_c(1, R1)) == R1
    for q in (SOL1, WSOL, USDC, None, 'not a mint!', 12):
        assert fd.paired(_c(2, q)) is None
    assert fd.paired({'mint': R1, 'quote_mint': R1}) is None and fd.paired('x') is None


def test_the_board_counts_who_is_feeding_each_runner_right_now():
    coins = [_c(1, R1, 10, 1, 4000), _c(2, R1, 30, 3, 2000), _c(3, R1, 300, 90, 9000), _c(4, R1, 5, None, 1000), _c(1, R1), _c(5, R2, 2, 0.5, 1800),
             _c(6, SOL1), _c(7, R1, is_banned=True), 'junk']
    b = fd.board(coins, NOW)
    r = b['runners'][R1]
    assert (r['n'], r['fresh'], r['active'], r['capUsd']) == (4, 3, 2, 16000)   # the duplicate and the banned coin are not counted
    assert [k['symbol'] for k in r['kids']][:2] == ['K1', 'K2'] and r['kids'][-1]['lastMin'] is None   # trading now first, never-traded last
    assert b['kids'][_c(5, R2)['mint']] == R2 and b['seen'] == 6
    assert fd.ranked(b) == [R1] and fd.ranked(b, 1) == [R1, R2]   # one paired coin is not a feed yet
    assert fd.label(r) == '🧲 4 coins paired · 2 trading now · 3 new this hour' and fd.label({'n': 1}) == '🧲 1 coin paired'
    assert fd.board(None, NOW) == {'runners': {}, 'kids': {}, 'seen': 0}


def test_feed_score_is_bounded_and_trading_now_counts_most():
    assert fd.feed_score(0, 0, 0, 0) == 0 and fd.feed_score(99, 99, 99, 1e9) == 100
    assert fd.feed_score(4, 0, 4, 0) > fd.feed_score(4, 4, 0, 0)
