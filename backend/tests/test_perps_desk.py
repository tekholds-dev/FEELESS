import perps_desk as pd

PAYLOAD = [{'universe': [{'name': 'BTC', 'maxLeverage': 40}, {'name': 'HYPE', 'maxLeverage': 10}, {'name': 'OLD', 'maxLeverage': 3, 'isDelisted': True}]},
           [{'markPx': '100000', 'prevDayPx': '98000', 'funding': '0.0000125', 'openInterest': '20', 'dayNtlVlm': '5000000'},
            {'markPx': '30', 'prevDayPx': '33', 'funding': '-0.00005', 'openInterest': '1000', 'dayNtlVlm': '9000000'},
            {'markPx': '1', 'prevDayPx': '1', 'funding': '0', 'openInterest': '1', 'dayNtlVlm': '1'}]]


def test_perps_rows_busiest_first_with_funding_apr_and_oi():
    r = pd.rows(PAYLOAD)
    assert [x['coin'] for x in r] == ['HYPE', 'BTC']                                   # delisted dropped, busiest first
    btc = r[1]; assert btc['oiUsd'] == 2_000_000 and btc['ch24'] == 2.04 and btc['fundApr'] == 11.0 and btc['maxLev'] == 40
    assert btc['venues'][0] == 'jupiter' and r[0]['venues'] == ['drift', 'hyperliquid'] and r[0]['fundApr'] < 0
    assert pd.rows(None) == [] and pd.rows([{}]) == []
    assert pd.liq_move(50) == 2.0 and pd.liq_move(0) == 100.0
