

def test_the_pump_pull_is_wide_and_deep_pages_are_cached_longer():
    import launchpad_board as lb
    t = lb.pump_pages('trending')
    assert sorted(off for s, off, _ in t if s == 'market_cap') == [0, 50, 100, 150, 200]          # Pump's 250 biggest coins
    assert sorted(off for s, off, _ in t if s == 'last_trade_timestamp') == [0, 50, 100, 150]     # + its 200 most recently traded
    assert all(ttl >= 20 for *_, ttl in t) and min(ttl for s, off, ttl in t if s == 'market_cap' and off) >= 120   # deep pages refresh slowly
    n = lb.pump_pages('new')
    assert {s for s, *_ in n} == {'created_timestamp', 'last_trade_timestamp'} and len(n) == 6
    assert lb.BOARD_MAX >= 450


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
    assert ('toptrending', '1h') in lb.JUP_LISTS


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
