

def test_the_pump_pull_is_wide_and_deep_pages_are_cached_longer():
    import launchpad_board as lb
    t = lb.pump_pages('trending')
    assert sorted(off for s, off, _ in t if s == 'market_cap') == [0, 50, 100, 150, 200]          # Pump's 250 biggest coins
    assert sorted(off for s, off, _ in t if s == 'last_trade_timestamp') == [0, 50, 100, 150]     # + its 200 most recently traded
    assert all(ttl >= 20 for *_, ttl in t) and min(ttl for s, off, ttl in t if s == 'market_cap' and off) >= 120   # deep pages refresh slowly
    n = lb.pump_pages('new')
    assert {s for s, *_ in n} == {'created_timestamp', 'last_trade_timestamp'} and len(n) == 6
    assert lb.BOARD_MAX >= 450
