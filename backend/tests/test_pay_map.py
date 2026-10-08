import pay_map as pm


def _fill(i, side, px, at, units=1.0, picked=False, why=''):
    return {'id': f'x{i}', 'card': 'degen', 'status': 'filled', 'side': side, 'mint': 'M', 'symbol': 'M', 'px': px, 'units': units, 'at': at, 'picked': picked, 'why': why}


def test_pieces_match_fifo_with_hold_time_opener_and_exit_kind():
    led = [_fill(1, 'buy', 1.0, 0, 2.0, True), _fill(2, 'sell', 1.5, 20 * 60, 1.0, why='🔒 locked: trim of the winner'), _fill(3, 'sell', 0.8, 40 * 60, 1.0, why='not on the card any more')]
    ps = pm.pieces(led, 'degen')
    assert [(round(p['usd'], 2), round(p['hold']), p['you'], p['kind']) for p in ps] == [(0.5, 20, True, 'trim'), (-0.2, 40, True, 'whole')]


def test_a_partial_sell_spans_lots_in_order_and_other_cards_are_ignored():
    led = [_fill(1, 'buy', 1.0, 0, 1.0), _fill(2, 'buy', 2.0, 60, 1.0), _fill(3, 'sell', 3.0, 120, 1.5)]
    led.append({**_fill(4, 'sell', 9.0, 130, 1.0), 'card': 'other'})
    ps = pm.pieces(led, 'degen')
    assert [round(p['usd'], 2) for p in ps] == [2.0, 0.5]                      # 1.0 @ cost 1 → +2.0 · 0.5 @ cost 2 → +0.5
    assert pm.pieces([{**_fill(1, 'buy', 1, 0), 'status': 'failed'}], 'degen') == []


def test_advice_names_the_hold_rule_and_the_trim_vs_whole_gap_with_the_numbers():
    led, i, t = [], 0, 0.0
    def piece(hold_min, ret, kind_why, picked=False):
        nonlocal i, t
        i += 1; led.append(_fill(i, 'buy', 1.0, t, 1.0, picked)); i += 1; led.append(_fill(i, 'sell', 1.0 + ret, t + hold_min * 60, 1.0, why=kind_why)); t += 4000
    for _ in range(45): piece(4, -0.05, 'not on the card any more')            # many fast losing exits
    for _ in range(25): piece(40, 0.12, 'trim')                                 # fewer held winners, trimmed
    out = pm.pay_map(led, 'degen', t)
    assert out['byHold']['<5m']['n'] == 45 and out['byHold']['30-60m']['wonPct'] == 100
    keys = [a['key'] for a in out['advice']]
    assert 'hold' in keys and 'exits' in keys
    assert 'min hold' in next(a for a in out['advice'] if a['key'] == 'hold')['text']
    assert pm.pay_map([], 'degen', 0)['advice'] == []                           # nothing to say without a record


def test_the_opener_line_names_the_side_that_really_did_better():
    led, i, t = [], 0, 0.0
    def piece(ret, picked):
        nonlocal i, t
        i += 1; led.append(_fill(i, 'buy', 1.0, t, 1.0, picked)); i += 1; led.append(_fill(i, 'sell', 1.0 + ret, t + 600, 1.0, why='not on the card any more')); t += 4000
    for _ in range(45): piece(-0.05, True)        # the owner's picks lose
    for _ in range(45): piece(+0.02, False)       # the engine's win
    txt = next(a['text'] for a in pm.pay_map(led, 'degen', t)['advice'] if a['key'] == 'opener')
    assert txt.startswith('The engine did better')
