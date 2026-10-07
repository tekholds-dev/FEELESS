

def test_the_pump_pull_is_wide_and_deep_pages_are_cached_longer():
    import launchpad_board as lb
    t = lb.pump_pages('trending')
    assert sorted(off for s, off, _ in t if s == 'market_cap') == [0, 50, 100, 150, 200]          # Pump's 250 biggest coins
    assert sorted(off for s, off, _ in t if s == 'last_trade_timestamp') == [0, 50, 100, 150, 200, 250]   # + its 300 most recently traded
    assert all(ttl >= 20 for *_, ttl in t) and min(ttl for s, off, ttl in t if s == 'market_cap' and off) >= 120   # deep pages refresh slowly
    n = lb.pump_pages('new')
    assert {s for s, *_ in n} == {'created_timestamp', 'last_trade_timestamp'} and len(n) == 7
    assert lb.BOARD_MAX >= 600


def test_jupiter_mover_rows_become_launch_candidates_only_for_launchpad_mints():
    import launchpad_board as lb
    c = lb.jup_candidate({'id': 'AbCpump', 'symbol': 'RUN', 'name': 'Runner', 'mcap': 740000, 'icon': 'i.png', 'twitter': 'x', 'firstPool': {'createdAt': '2026-10-04T00:00:00Z'}})
    assert c['mint'] == 'AbCpump' and c['launchpad'] == 'pump' and c['marketCap'] == 740000 and c['createdAt'] > 1.7e12 and c['socials'] == 1 and c['mover']
    assert lb.jup_candidate({'id': 'XyZbonk', 'symbol': 'B'})['launchpad'] == 'bonk' and lb.jup_candidate({'id': 'XyZbonk'})['createdAt'] == 0.0
    assert lb.jup_candidate({'id': 'So11111111111111111111111111111111111111112'}) is None and lb.jup_candidate({}) is None and lb.jup_candidate(None) is None
    now = 1_800_000_000_000
    young = {'id': 'StonkMint111', 'symbol': 'COW', 'launchpad': 'stonkfun', 'mcap': 90000, 'firstPool': {'createdAt': '2027-01-14T00:00:00Z'}}
    c2 = lb.jup_candidate(young, now)                                              # any venue while it is young
    assert c2['launchpad'] == 'other' and c2['platformName'] == 'stonkfun' and 'jup.ag' in c2['url'] and lb.LAUNCHPAD_LABELS['other']
    assert lb.jup_candidate({**young, 'firstPool': {'createdAt': '2025-01-01T00:00:00Z'}}, now) is None    # an old coin from another venue is not a launch
    assert lb.jup_candidate({'id': 'NoAge111', 'symbol': 'X'}, now) is None                                # unknown age = out
    assert lb.jup_candidate({'id': 'Tagged111', 'launchpad': 'pump.fun', 'symbol': 'P'}, now)['launchpad'] == 'pump'
    assert ('toptrending', '1h') in lb.JUP_LISTS and ('toptraded', '5m') in lb.JUP_LISTS and len(lb.JUP_LISTS) == 9 and lb.JUP_RECENT.endswith('/recent')


def test_pump_profile_is_shaped_from_pumps_own_coin_record():
    import launchpad_board as lb
    d = {'mint': 'ABCpump', 'name': 'Super Kitty', 'symbol': 'SK', 'image_uri': 'https://img/x.png', 'twitter': 'https://x.com/sk', 'telegram': 'javascript:alert(1)',
         'website': '', 'creator': 'Dev111', 'created_timestamp': 1_000_000_000_000, 'complete': True, 'pump_swap_pool': 'Pool1', 'market_cap': 1000.0,
         'usd_market_cap': 200_000.0, 'ath_market_cap': 400_000.0, 'volume_1h_usd': 47_040.3, 'canonical_pool_liquidity_usd': 43_806.4, 'reply_count': 12,
         'is_currently_live': True, 'description': 'a cat'}
    p = lb.pump_profile(d, now_ms=1_000_000_000_000 + 7_200_000)
    assert p['symbol'] == 'SK' and p['image'] == 'https://img/x.png' and p['graduated'] and p['pool'] == 'Pool1' and p['ageH'] == 2.0
    assert p['links'] == [{'type': 'x', 'url': 'https://x.com/sk'}]                 # only real http(s) links survive (no script URLs, no blanks)
    assert p['athUsd'] == 400_000.0 and p['offAthPct'] == -50.0                     # Pump's ATH is in $
    assert p['replies'] == 12 and p['live'] and p['creator'] == 'Dev111' and p['url'].endswith('/coin/ABCpump')
    assert lb.pump_profile({'statusCode': 404}) is None and lb.pump_profile(None) is None


def test_pump_trending_board_rows_keep_pumps_order_and_skip_bad_rows():
    import launchpad_board as lb
    data = {'board': 'movers', 'entries': [
        {'m': 'AHmD5jaFKqWMGswNkTSwAfvaWNHVY8m6JJro9LFppump', 'c': 'solana:mainnet', 't': 'FLY', 'n': 'fly', 'mc': 752603.7, 'age': 4162,
         'gd': 1791396954000, 'tw': True, 'ws': True, 'tg': False, 'lp': 'pump'},
        {'m': 'bad mint!', 'c': 'solana:mainnet', 't': 'X'},
        {'m': '0xabc', 'c': 'base:mainnet', 't': 'BASE'},
        {'m': 'LoopMint1111111111111111111111111111111pump', 'c': 'solana:mainnet', 't': 'LOOP', 'mc': 158000, 'age': 600},
        {'m': 'AHmD5jaFKqWMGswNkTSwAfvaWNHVY8m6JJro9LFppump', 'c': 'solana:mainnet', 't': 'FLY'},   # duplicate
    ]}
    rows = lb.pump_trend_rows(data, now_ms=2_000_000_000_000)
    assert [r['symbol'] for r in rows] == ['FLY', 'LOOP'] and [r['pumpTrend'] for r in rows] == [1, 2]
    fly = rows[0]
    assert fly['launchpad'] == 'pump' and fly['graduated'] and fly['socials'] == 2 and fly['createdAt'] == 2_000_000_000_000 - 4_162_000
    assert lb.PUMP_TREND_TTL == 600 and lb.PUMP_TREND_PARAMS['surface'] == 'TRENDING'
    assert lb.pump_trend_rows(None) == [] and lb.pump_trend_rows({'entries': None}) == []


def test_pump_trending_coin_is_listed_even_under_the_trending_floors():
    import launchpad_board as lb
    cand = lb.pump_trend_rows({'entries': [{'m': 'LoopMint1111111111111111111111111111111pump', 'c': 'solana', 't': 'LOOP', 'mc': 9000, 'age': 600}]},
                              now_ms=2_000_000_000_000)[0]
    pair = {'pairAddress': 'P1', 'baseToken': {'address': cand['mint'], 'symbol': 'LOOP'}, 'priceUsd': '0.0001', 'marketCap': 9000, 'fdv': 9000,
            'volume': {'h1': 1000, 'h24': 2000, 'm5': 100}, 'txns': {'h1': {'buys': 10, 'sells': 5}, 'm5': {'buys': 2, 'sells': 1}, 'h24': {'buys': 20, 'sells': 10}},
            'priceChange': {'h1': 5, 'm5': 1, 'h24': 10}, 'liquidity': {'usd': 8000}, 'pairCreatedAt': 2_000_000_000_000 - 600_000}
    out = lb.build_board({cand['mint']: cand}, {cand['mint']: pair}, 'trending', now_ms=2_000_000_000_000)
    assert out and out[0]['pumpTrend'] == 1          # $9K cap / $1K an hour is under the board's floors — Pump trends it, so it shows


def test_a_board_built_while_dexscreener_refused_us_never_replaces_a_good_one():
    from launchpad_board import keep_last_board
    good = (100.0, list(range(120)), {})
    assert keep_last_board(good, [], 5, 130.0) is True                 # empty after refused batches → keep the last good board
    assert keep_last_board(good, list(range(30)), 3, 130.0) is True    # collapsed under a third → keep it
    assert keep_last_board(good, list(range(90)), 3, 130.0) is False   # a normal shrink is real
    assert keep_last_board(good, [], 0, 130.0) is False                # nothing refused → an empty board is the truth
    assert keep_last_board(good, [], 5, 800.0) is False                # the last board is too old to stand in
    assert keep_last_board(None, [], 5, 130.0) is False
