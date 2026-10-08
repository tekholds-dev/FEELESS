import track_record as rc


def _t(side, tokens, pool, ts, token='M1', tx='x'):
    return {'side': side, 'tokens': tokens, 'poolUsd': pool, 'fillPrice': pool / tokens, 'ts': ts, 'token': token, 'tx': f'{tx}{ts}'}


def test_trades_close_first_in_first_out_with_price_hold_and_tx():
    rows = [_t('buy', 100, 1.0, 0), _t('buy', 100, 2.0, 600), _t('sell', 150, 3.0, 3600)]
    closed, open_ = rc.trade_receipts(rows, {'M1': 'COIN'})
    assert [(c['symbol'], round(c['ret'], 2), round(c['usd'], 2), c['holdMin']) for c in closed] == [('COIN', 1.0, 1.0, 60.0), ('COIN', -0.0, 0.0, 50.0)]
    assert closed[0]['tx'] == 'x3600' and closed[0]['buyTx'] == 'x0'
    assert len(open_) == 1 and round(open_[0]['tokens']) == 50 and open_[0]['symbol'] == 'COIN'      # 50 tokens of the second lot are still held


def test_a_losing_entry_is_shown_as_losing_and_dust_lots_are_dropped():
    closed, open_ = rc.trade_receipts([_t('buy', 100, 2.0, 0), _t('sell', 100, 1.0, 60)])
    assert closed[0]['ret'] == -0.5 and closed[0]['usd'] == -1.0 and open_ == []
    _, dust = rc.trade_receipts([_t('buy', 1000, 0.001, 0)])
    assert dust == []


def test_calls_for_a_wallet_with_result_and_peak_multiple_and_summary():
    calls = {'1': {'callerAddress': 'W', 'mint': 'A' * 40, 'symbol': 'AAA', 'priceAtCall': 1.0, 'lastPrice': 0.5, 'peakPrice': 3.0, 'at': 5},
             '2': {'callerAddress': 'OTHER', 'mint': 'B', 'priceAtCall': 1.0, 'lastPrice': 9, 'peakPrice': 9, 'at': 6}}
    cs = rc.call_receipts(calls, 'W')
    assert len(cs) == 1 and cs[0]['ret'] == -0.5 and cs[0]['peakX'] == 3.0
    s = rc.summary([{'ret': 1.0, 'usd': 1.0, 'symbol': 'A'}, {'ret': -0.5, 'usd': -1.0, 'symbol': 'B'}, {'ret': 0.2, 'usd': 0.2, 'symbol': 'C'}], cs)
    assert s['trades'] == 3 and s['wonPct'] == 67 and s['medianPct'] == 20.0 and s['best'] == 'A' and s['callHit2xPct'] == 100
    assert rc.summary([], [])['wonPct'] is None
