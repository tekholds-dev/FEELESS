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


def test_tight_flow_exit_waits_out_the_first_minutes_but_the_rug_radar_does_not():
    w = fl.window([T(20, 'buy', 20, 1.0), T(15, 'sell', 80, 0.98), T(10, 'sell', 80, 0.97), T(5, 'sell', 80, 0.96), T(2, 'sell', 80, 0.95)], NOW)
    leg = {'symbol': 'A', 'mint': 'm', 'pairAddress': 'p', 'units': 10, 'real': True, 'entry': 1.0, 'at': NOW - 120}
    card = {'legs': [leg]}
    _, hits = fl.flow_exits(card, {'p': w}, {'m': 0.95}, {'flowExit': 'tight', 'flowMinHoldMins': 10, 'rugRadar': False}, NOW)
    assert hits == []                                                                      # bought 2 min ago: the tight exit waits
    _, hits = fl.flow_exits({'legs': [{**leg, 'at': NOW - 900}]}, {'p': w}, {'m': 0.95}, {'flowExit': 'tight', 'flowMinHoldMins': 10, 'rugRadar': False}, NOW)
    assert hits and hits[0][1] == 'flow'


def test_tape_read_tells_burst_absorb_climax_and_dump_apart():
    assert fl.tape_read(fl.window([T(30, 'buy', 120, 1.0), T(20, 'buy', 150, 1.01), T(10, 'sell', 40, 1.02), T(5, 'buy', 90, 1.025)], NOW)) == 'burst'
    assert fl.tape_read(fl.window([T(30, 'sell', 120, 1.0), T(20, 'sell', 150, 1.0), T(10, 'buy', 40, 1.0), T(5, 'sell', 90, 0.998)], NOW)) == 'absorb'
    assert fl.tape_read(fl.window([T(30, 'buy', 300, 1.0), T(20, 'buy', 250, 1.0), T(10, 'sell', 50, 1.001), T(5, 'buy', 200, 1.001)], NOW)) == 'climax'
    assert fl.tape_read(fl.window([T(30, 'sell', 300, 1.0), T(20, 'sell', 250, 0.99), T(10, 'buy', 50, 0.98), T(5, 'sell', 200, 0.97)], NOW)) == 'dump'
    assert fl.tape_read(fl.window([T(5, 'buy', 10, 1.0)], NOW)) is None
    assert 'climax' in fl.entry_why(fl.window([T(30, 'buy', 300, 1.0), T(20, 'buy', 250, 1.0), T(10, 'sell', 50, 1.001), T(5, 'buy', 200, 1.001)], NOW))


def test_a_winner_at_a_buying_climax_sells_half_its_profit_and_keeps_riding():
    w = fl.window([T(30, 'buy', 300, 1.5), T(20, 'buy', 250, 1.5), T(10, 'sell', 50, 1.5), T(5, 'buy', 200, 1.5)], NOW)
    leg = {'symbol': 'W', 'mint': 'm', 'pairAddress': 'p', 'units': 10, 'real': True, 'entry': 1.0, 'costUsd': 10.0, 'at': NOW - 3600}
    out, hits = fl.flow_exits({'legs': [leg], 'cash': 0.0}, {'p': w}, {'m': 1.5}, {'flowExit': 'tight', 'rugRadar': False}, NOW)
    l = out['legs'][0]
    assert hits[0][1] == 'climax' and not l.get('placeholder') and abs(l['units'] - 10 * (1 - 2.5 / 15)) < 1e-6 and out['cash'] > 2.4
    out2, hits2 = fl.flow_exits(out, {'p': w}, {'m': 1.5}, {'flowExit': 'tight', 'rugRadar': False}, NOW + 60)
    assert hits2 == []                                                     # once per 15 min
