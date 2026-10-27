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


def test_index_ladders_trade_their_at_the_money_strike_and_strikes_come_from_any_field():
    lad = [{'ticker': 'NDX-T29340', 'status': 'active', 'floor_strike': 29340, 'yes_ask_dollars': '0.8100', 'no_ask_dollars': '0.2100', 'close_time': 'a'},
           {'ticker': 'NDX-T29440', 'status': 'active', 'floor_strike': 29440, 'yes_ask_dollars': '0.5000', 'no_ask_dollars': '0.5200', 'close_time': 'a'},
           {'ticker': 'NDX-T29540', 'status': 'active', 'floor_strike': 29540, 'yes_ask_dollars': '0.2200', 'no_ask_dollars': '0.8000', 'close_time': 'a'}]
    a = ko.atm(lad)
    assert (a['ticker'], a['target'], a['yes'], a['no']) == ('NDX-T29440', 29440.0, 0.5, 0.52) and ko.atm([]) is None
    assert ko.strike({'custom_strike': {'floor_strike': '0.2649999'}}) == 0.2649999 and ko.strike({'ticker': 'KXXRPD-26OCT2401-T2.0399'}) == 2.0399
    assert ko.soonest_event([{'event_ticker': 'B', 'strike_date': '2026-10-26T15:00:00Z'}, {'event_ticker': 'A', 'strike_date': '2026-10-26T14:00:00Z'}]) == 'A'
    assert set(ko.MARKETS) == {'BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'SPX', 'NDX'} and ko.series('DOGE', '15m') == 'KXDOGE15M' and ko.series('SPX', 'day') == 'KXINXU'


def test_the_service_reads_every_market_once_in_parallel_and_keeps_the_last_good_read(monkeypatch):
    import reputation_service as rs
    asked = []
    LAD = [{'ticker': 'SPX-T7795', 'status': 'active', 'floor_strike': 7795, 'yes_ask_dollars': '0.4800', 'no_ask_dollars': '0.5400', 'close_time': 'z'}]

    class R:
        status_code = 200

        def __init__(self, b):
            self.b = b

        def json(self):
            return self.b

    class C:
        async def get(self, url, params=None, timeout=None):
            key = params.get('series_ticker') or params.get('event_ticker')
            asked.append(key)
            if key.startswith('KXETH'):
                raise RuntimeError('down')
            if url.endswith('/events'):
                return R({'events': [{'event_ticker': key + '-EV', 'strike_date': '2026-10-26T14:00:00Z'}]})
            if params.get('event_ticker'):
                return R({'markets': LAD})
            return R({'markets': M15 if key.endswith('15M') else DAY})
    monkeypatch.setattr(rs, '_fmk_http', C())
    monkeypatch.setitem(rs._perps_cache, 'rows', [{'coin': 'BTC', 'mark': 80700}])
    monkeypatch.setattr(rs, '_kalshi_cache', {'at': 0.0, 'rows': {'ETH': {'up': {'yes': 0.4}, 'm15': {'yes': 0.4}, 'day': None}}})
    out = asyncio.run(rs.familia_kalshi())
    assert {'KXBTC15M', 'KXBTCD', 'KXDOGE15M', 'KXXRPD', 'KXINXU', 'KXINXU-EV', 'KXNASDAQ100U', 'KXNASDAQ100U-EV'} <= set(asked)
    c = out['coins']
    assert c['BTC']['up']['yes'] == 0.9 and c['BTC']['day']['ticker'] == 'KXBTCD-T81' and c['BTC']['name'] == 'Bitcoin'
    assert c['SPX']['up']['target'] == 7795 and c['SPX']['kind'] == 'index' and c['SPX']['day'] is None
    assert c['ETH']['up'] == {'yes': 0.4}                                                              # ETH's read failed → its last good read stays
    n = len(asked); asyncio.run(rs.familia_kalshi()); assert len(asked) == n                          # cached 10 s — one shared read


def test_the_strike_ladder_lists_the_soonest_days_strikes_round_the_mark_with_payouts():
    import kalshi_odds as ko
    mk = lambda s, y, n, close='2026-10-27T21:00:00Z': {'ticker': f'KXBTCD-T{s}', 'floor_strike': s, 'yes_ask_dollars': y, 'no_ask_dollars': n, 'close_time': close, 'status': 'active'}
    rows = [mk(78000, '0.92', '0.10'), mk(79000, '0.66', '0.36'), mk(80000, '0.41', '0.61'), mk(81000, '0.18', '0.84'), mk(90000, '0.01', '0.99'),
            mk(80000, '0.50', '0.52', '2026-10-28T21:00:00Z')]                       # tomorrow's strike stays out
    lad = ko.ladder(rows, 79600, n=4)
    assert [r['strike'] for r in lad] == [78000, 79000, 80000, 81000]               # the 4 nearest, lowest first
    r80 = lad[2]
    assert r80['yes'] == 0.41 and r80['pay'] == round(1 / 0.41, 2) and r80['payNo'] == round(1 / 0.61, 2) and r80['away'] == round((80000 / 79600 - 1) * 100, 2)
    assert ko.ladder(rows, 0) == [] and ko.ladder([], 79600) == []
