

def test_the_tick_store_keeps_the_400_freshest_coins_and_drops_coins_nobody_charted_for_3_days():
    import candles_service as cs
    now = 1_000_000.0
    store = {f'p{i}': [{'t': now - i}] for i in range(500)}
    store['old'] = [{'t': now - 4 * 86400}]
    cs.prune_pairs(store, now)
    assert len(store) == cs.MAX_PAIRS and 'old' not in store and 'p0' in store and 'p499' not in store
