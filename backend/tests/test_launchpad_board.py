

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
    assert ('toptrending', '1h') in lb.JUP_LISTS
