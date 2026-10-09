import degen as dg


def test_smart_wallet_radar_learns_wallets_whose_buys_win():
    st = {}
    for i in range(4):   # W buys 4 coins early, each doubles; L buys the same coins late and they halve
        st = dg.note_buys(st, f'M{i}', [{'kind': 'buy', 'wallet': 'W', 'price': 1.0, 'usd': 50}, {'kind': 'buy', 'wallet': 'L', 'price': 4.0},
                                        {'kind': 'buy', 'wallet': 'W', 'price': 1.2}], 0)   # W's second buy of a coin is not counted again
    assert len(st['buys']) == 8
    st = dg.settle(st, lambda m: 2.0, 4000)
    sm = dg.smart_set(st)
    assert 'W' in sm and 'L' not in sm and sm['W']['med'] == 100.0
    assert dg.smart_hits([{'kind': 'buy', 'wallet': 'W', 'usd': 30}, {'kind': 'sell', 'wallet': 'W'}], sm) == [('W', 30.0)]
    assert dg.settle({'buys': [{'w': 'X', 'm': 'Z', 'px': 1, 'at': 0}]}, lambda m: None, 4000)['wallets']['X']['r'] == [-100.0]   # vanished = −100%


def test_buy_burst_needs_money_ratio_and_a_rising_price():
    assert dg.burst_why({'n': 9, 'buyUsd': 400, 'sellUsd': 100, 'pxChg': 3})
    assert dg.burst_why({'n': 9, 'buyUsd': 400, 'sellUsd': 300, 'pxChg': 3}) is None
    assert dg.burst_why({'n': 9, 'buyUsd': 100, 'sellUsd': 10, 'pxChg': 3}) is None
    assert dg.burst_why({'n': 9, 'buyUsd': 400, 'sellUsd': 100, 'pxChg': -1}) is None


def test_callout_spike_sells_only_a_winner_once_an_hour():
    card = {'legs': [{'mint': 'A', 'pairAddress': 'PA', 'entry': 1.0, 'units': 10}, {'mint': 'B', 'pairAddress': 'PB', 'entry': 1.0, 'units': 10}]}
    px = {'PA': 1.5, 'PB': 1.1}
    hits = dg.spike_sells(card, px, {'A': 4, 'B': 5}, 10_000)
    assert [h[0] for h in hits] == ['PA']   # B is only +10%
    assert dg.spike_sells({**card, 'spikeAt': {'A': 9_000}}, px, {'A': 4}, 10_000) == []
