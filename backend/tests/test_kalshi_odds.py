import asyncio

import kalshi_odds as ko

M15 = [{'ticker': 'KXBTC15M-B', 'status': 'active', 'market_type': 'binary', 'close_time': '2026-10-24T03:30:00Z', 'floor_strike': 81000, 'yes_ask_dollars': '0.5500', 'no_ask_dollars': '0.4600'},
       {'ticker': 'KXBTC15M-A', 'status': 'active', 'market_type': 'binary', 'close_time': '2026-10-24T03:15:00Z', 'floor_strike': 80875.28, 'yes_ask_dollars': '0.9000',
        'no_ask_dollars': '0.1100', 'volume_24h_fp': '185427.65', 'open_interest_fp': '486769.10'}]
DAY = [{'ticker': 'KXBTCD-T80', 'status': 'active', 'floor_strike': 79999.99, 'yes_ask_dollars': '0.8100', 'close_time': 'c'},
       {'ticker': 'KXBTCD-T81', 'status': 'active', 'floor_strike': 80999.99, 'yes_ask_dollars': '0.4400', 'close_time': 'c'},
       {'ticker': 'KXBTCD-T82', 'status': 'active', 'floor_strike': 81999.99, 'yes_ask_dollars': '0.0000', 'close_time': 'c'}]


def test_the_15_minute_window_running_now_with_its_target_and_odds():
    m = ko.fifteen(M15)
    assert m == {'ticker': 'KXBTC15M-A', 'target': 80875.28, 'yes': 0.9, 'no': 0.11, 'closes': '2026-10-24T03:15:00Z', 'vol24': 185428, 'oi': 486769}
    assert ko.fifteen([]) is None and ko.fifteen([{**M15[1], 'yes_ask_dollars': '0', 'no_ask_dollars': ''}]) is None   # no ask = no odds, never invented


def test_the_5pm_strike_nearest_the_live_mark_and_the_payout_per_dollar():
    assert ko.nearest(DAY, 80700)['ticker'] == 'KXBTCD-T81' and ko.nearest(DAY, 80100)['strike'] == 79999.99
    later = [{**DAY[1], 'ticker': 'LATER', 'floor_strike': 80700, 'close_time': 'd'}]
    assert ko.nearest(DAY + later, 80700)['ticker'] == 'KXBTCD-T81'                                    # the soonest day wins, never next week's closer strike
    assert ko.nearest(DAY, None) is None and ko.nearest([DAY[2]], 82000) is None                       # a strike with no ask is skipped
    assert ko.payout(0.5) == 2.0 and ko.payout(0.9, 10) == 11.11 and ko.payout(0) is None
    assert ko.series('SOL', '15m') == 'KXSOL15M' and ko.series('ETH', 'day') == 'KXETHD'


def test_the_service_reads_every_coin_once_in_parallel_and_keeps_the_last_good_read(monkeypatch):
    import reputation_service as rs
    asked = []

    class R:
        status_code = 200

        def __init__(self, b):
            self.b = b

        def json(self):
            return {'markets': self.b}

    class C:
        async def get(self, url, params=None, timeout=None):
            asked.append(params['series_ticker'])
            if params['series_ticker'].startswith('KXETH'):
                raise RuntimeError('down')
            return R(M15 if params['series_ticker'].endswith('15M') else DAY)
    monkeypatch.setattr(rs, '_fmk_http', C())
    monkeypatch.setitem(rs._perps_cache, 'rows', [{'coin': 'BTC', 'mark': 80700}])
    monkeypatch.setattr(rs, '_kalshi_cache', {'at': 0.0, 'rows': {'ETH': {'m15': {'yes': 0.4}, 'day': None}}})
    out = asyncio.run(rs.familia_kalshi())
    assert sorted(asked) == sorted(['KXBTC15M', 'KXBTCD', 'KXETH15M', 'KXETHD', 'KXSOL15M', 'KXSOLD'])
    assert out['coins']['BTC']['m15']['yes'] == 0.9 and out['coins']['BTC']['day']['ticker'] == 'KXBTCD-T81'
    assert out['coins']['ETH'] == {'m15': {'yes': 0.4}, 'day': None}                                  # ETH's read failed → its last good read stays
    asyncio.run(rs.familia_kalshi()); assert len(asked) == 6                                           # cached 10 s — one shared read
