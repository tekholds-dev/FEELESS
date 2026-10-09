import flow as fl

NOW = 1_000_000.0


def T(sec_ago, kind, usd, px, wallet='w'):
    return {'ts': NOW - sec_ago, 'kind': kind, 'usd': usd, 'price': px, 'wallet': wallet}


def test_window_reads_the_last_90s_only():
    w = fl.window([T(200, 'buy', 999, 1.0), T(60, 'buy', 10, 1.0), T(30, 'sell', 40, 0.95), T(5, 'sell', 30, 0.9, 'x')], NOW)
    assert w['buyUsd'] == 10 and w['sellUsd'] == 70 and w['n'] == 3 and w['pxChg'] == -10.0 and w['bigSell']['usd'] == 40


def test_flow_exit_needs_sellers_in_charge_money_trades_and_a_falling_price():
    sellers = [T(80 - i * 8, 'sell' if i % 3 else 'buy', 30 if i % 3 else 5, 1.0 - i * 0.01) for i in range(9)]
    w = fl.window(sellers, NOW)
    assert fl.exit_why(w, 'normal') and fl.exit_why(w, 'off') is None
    flat = fl.window([T(80 - i * 8, 'sell' if i % 3 else 'buy', 30 if i % 3 else 5, 1.0) for i in range(9)], NOW)
    assert fl.exit_why(flat, 'normal') is None            # price not sliding: no exit on noise
    thin = fl.window([T(10, 'sell', 5, 1.0), T(5, 'sell', 5, 0.9)], NOW)
    assert fl.exit_why(thin, 'tight') is None             # 2 trades: not enough to judge


def test_rug_radar_dev_whale_and_one_big_seller():
    w = fl.window([T(10, 'buy', 50, 1.0), T(5, 'sell', 25, 0.98, 'DEV')], NOW)
    assert 'creator' in fl.rug_why(w, creator='DEV')
    w2 = fl.window([T(10, 'buy', 50, 1.0), T(5, 'sell', 150, 0.9, 'TOP')], NOW)
    assert 'top holder' in fl.rug_why(w2, watch={'TOP'})
    w3 = fl.window([T(10, 'buy', 100, 1.0), T(5, 'sell', 400, 0.8, 'Z')], NOW)
    assert 'one wallet' in fl.rug_why(w3)
    assert fl.rug_why(fl.window([T(5, 'buy', 500, 1.0)], NOW), creator='DEV') is None


def test_flow_exits_take_the_coin_off_like_a_fast_stop_and_respect_riders_and_per_coin_settings():
    legs = [{'symbol': 'A', 'mint': 'MA', 'pairAddress': 'PA', 'units': 100, 'entry': 1.0, 'real': True},
            {'symbol': 'R', 'mint': 'MR', 'pairAddress': 'PR', 'units': 100, 'entry': 1.0, 'real': True, 'ride': True},
            {'symbol': 'O', 'mint': 'MO', 'pairAddress': 'PO', 'units': 100, 'entry': 1.0, 'real': True, 'flowExit': 'off'}]
    sell = fl.window([T(80 - i * 8, 'sell' if i % 3 else 'buy', 30 if i % 3 else 5, 1.0 - i * 0.01) for i in range(9)], NOW)
    flows = {'PA': sell, 'PR': sell, 'PO': sell}
    c, hits = fl.flow_exits({'legs': legs, 'cash': 0}, flows, {'MA': 0.9, 'MR': 0.9, 'MO': 0.9}, {'flowExit': 'normal'}, NOW)
    assert [h[0] for h in hits] == ['A'] and c['legs'][0]['placeholder'] and c['cash'] == 90.0 and c['events'][-1]['kind'] == 'flow'
    # the rug radar still watches the rider
    rug = fl.window([T(10, 'buy', 50, 1.0), T(5, 'sell', 25, 0.98, 'DEV')], NOW)
    c2, hits2 = fl.flow_exits({'legs': legs, 'cash': 0}, {'PR': rug}, {'MR': 0.98}, {'flowExit': 'off'}, NOW, intel={'MR': {'creator': 'DEV'}})
    assert hits2 == [('R', 'rug', hits2[0][2])] and c2['legs'][1]['placeholder']


def test_entry_flow_blocks_buying_into_sellers():
    w = fl.window([T(50, 'buy', 10, 1.0), T(40, 'sell', 30, 0.99), T(30, 'sell', 30, 0.98), T(20, 'buy', 5, 0.97)], NOW)
    assert fl.entry_why(w) and fl.entry_why(None) is None


def test_one_big_seller_on_a_deep_pool_is_trading_not_a_rug():
    # 2026-10-09: STONK / WETH / RAY / Fartcoin / DARK ×3 sold on a whale's sell into a deep pool — 23 exits, median −0.4% an hour later
    w = fl.window([T(10, 'buy', 100, 1.0), T(5, 'sell', 13598, 0.99, 'WHALE')], NOW)
    assert fl.rug_why(w, liq=1_200_000) is None                     # ~1% of a $1.2M pool: ordinary flow
    assert 'one wallet' in fl.rug_why(w, liq=200_000)               # ~7% of a $200K pool: a real hit
    assert 'one wallet' in fl.rug_why(w)                            # depth unknown: judged as before
    dev = fl.window([T(10, 'buy', 100, 1.0), T(5, 'sell', 50, 0.97, 'DEV')], NOW)
    assert 'creator' in fl.rug_why(dev, creator='DEV', liq=5_000_000)   # the creator selling always counts, however deep
