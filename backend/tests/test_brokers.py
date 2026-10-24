import asyncio
import base64
import hashlib
import hmac
import json

import pytest

import brokers as bk

ENV = {'SNAPTRADE_CLIENT_ID': 'CID', 'SNAPTRADE_CONSUMER_KEY': 'CKEY', 'BROKER_SECRET_KEY': 'k' * 40}


def test_snaptrade_signature_is_hmac_sha256_over_the_canonical_content_path_query():
    url, hd = bk.signed('POST', '/trade/place', {'userId': 'U', 'userSecret': 'S'}, {'b': 1, 'a': 2}, 'CID', 'CKEY', now=1700000000)
    assert url == 'https://api.snaptrade.com/api/v1/trade/place?userId=U&userSecret=S&clientId=CID&timestamp=1700000000'
    raw = json.dumps({'content': {'a': 2, 'b': 1}, 'path': '/api/v1/trade/place', 'query': 'userId=U&userSecret=S&clientId=CID&timestamp=1700000000'}, separators=(',', ':'), sort_keys=True)
    assert hd['Signature'] == base64.b64encode(hmac.new(b'CKEY', raw.encode(), hashlib.sha256).digest()).decode()
    _, h2 = bk.signed('GET', '/accounts', None, {}, 'CID', 'CKEY', now=1)                                   # an empty body signs as null
    raw2 = json.dumps({'content': None, 'path': '/api/v1/accounts', 'query': 'clientId=CID&timestamp=1'}, separators=(',', ':'), sort_keys=True)
    assert h2['Signature'] == base64.b64encode(hmac.new(b'CKEY', raw2.encode(), hashlib.sha256).digest()).decode()
    assert bk.keys(ENV) == ('CID', 'CKEY') and bk.keys({}) == (None, None)


def test_the_broker_secret_is_sealed_at_rest_and_never_without_a_key():
    t = bk.seal('user-secret', ENV)
    assert 'user-secret' not in t and bk.unseal(t, ENV) == 'user-secret'
    with pytest.raises(RuntimeError):
        bk.seal('x', {})
    assert bk.user_id('WALLET') == bk.user_id('WALLET') != bk.user_id('OTHER') and bk.user_id('WALLET').startswith('fl-')


def test_orders_only_in_your_own_account_with_a_real_ticker_and_a_capped_size():
    b = bk.order_body({'accountId': 'A1', 'symbol': 'spy', 'action': 'buy', 'usd': 25}, ['A1'])
    assert b == {'account_id': 'A1', 'action': 'BUY', 'symbol': 'SPY', 'universal_symbol_id': None, 'order_type': 'Market', 'time_in_force': 'Day',
                 'price': None, 'stop': None, 'units': None, 'notional_value': 25.0}
    assert bk.order_body({'accountId': 'A1', 'symbol': 'AAPL', 'action': 'SELL', 'units': 2}, ['A1'])['units'] == 2
    lim = bk.order_body({'accountId': 'A1', 'symbol': 'TSLA', 'action': 'BUY', 'type': 'Limit', 'price': 200, 'units': 3}, ['A1'])
    assert (lim['order_type'], lim['price'], lim['units']) == ('Limit', 200.0, 3.0)
    for bad in ({'accountId': 'NOT-MINE', 'symbol': 'SPY', 'action': 'BUY', 'usd': 5}, {'accountId': 'A1', 'symbol': 'spy; drop', 'action': 'BUY', 'usd': 5},
                {'accountId': 'A1', 'symbol': 'SPY', 'action': 'SHORT', 'usd': 5}, {'accountId': 'A1', 'symbol': 'SPY', 'action': 'BUY', 'usd': 0.5},
                {'accountId': 'A1', 'symbol': 'SPY', 'action': 'BUY', 'usd': 99999}, {'accountId': 'A1', 'symbol': 'SPY', 'action': 'BUY'},
                {'accountId': 'A1', 'symbol': 'SPY', 'action': 'BUY', 'type': 'Limit', 'price': 600, 'units': 10}):
        with pytest.raises(ValueError):
            bk.order_body(bad, ['A1'])


def test_the_buildings_view_of_accounts_cash_and_positions():
    acc = [{'id': 'A1', 'institution_name': 'Webull', 'name': 'Margin', 'number': '123456789', 'balance': {'total': {'amount': 1530}}}]
    pos = {'A1': [{'symbol': {'symbol': {'symbol': 'SPY', 'description': 'SPDR S&P 500', 'type': {'code': 'et'}}}, 'units': 2, 'price': 600, 'average_purchase_price': 550},
                  {'symbol': {'symbol': {'symbol': 'BTC'}}, 'units': 0.001, 'price': 80000, 'open_pnl': -2}]}
    v = bk.view(acc, pos, {'A1': [{'cash': 250, 'buying_power': 500}]})
    a = v['accounts'][0]
    assert (a['broker'], a['number'], a['cash'], a['buyingPower'], a['value']) == ('Webull', '6789', 250, 500, 1530)
    assert [(p['ticker'], p['value'], p['pnl']) for p in a['positions']] == [('SPY', 1200, 100), ('BTC', 80, -2)] and a['positions'][0]['pnlPct'] == 9.09
    assert v['value'] == 1530 and v['pnl'] == 98


def test_the_endpoints_link_read_trade_and_unlink_on_the_wallet_session(monkeypatch):
    import reputation_service as rs
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: 'WALLET' if s == 'ok' else (_ for _ in ()).throw(rs.HTTPException(401, 'sign in')))
    monkeypatch.setattr(rs, '_brk_cache', {})
    calls = []

    class R:
        def __init__(self, code, b):
            self.status_code, self.b = code, b

        def json(self):
            return self.b

    class C:
        async def request(self, method, url, headers=None, json=None, timeout=None):
            path = url.split('/api/v1', 1)[1].split('?')[0]
            calls.append((method, path, json))
            assert headers['Signature'] and 'clientId=CID' in url
            if path == '/snapTrade/registerUser':
                return R(200, {'userId': json['userId'], 'userSecret': 'SECRET'})
            if path == '/snapTrade/login':
                assert 'userSecret=SECRET' in url and json['connectionType'] == 'trade-if-available'
                return R(200, {'redirectURI': 'https://app.snaptrade.com/portal/x', 'sessionId': 's'})
            if path == '/accounts':
                return R(200, [{'id': 'A1', 'institution_name': 'Webull', 'name': 'Cash', 'number': '9999'}])
            if path.endswith('/positions'):
                return R(200, [{'symbol': {'symbol': {'symbol': 'SPY'}}, 'units': 1, 'price': 600, 'average_purchase_price': 500}])
            if path.endswith('/balances'):
                return R(200, [{'cash': 40, 'buying_power': 40}])
            if path == '/trade/place':
                return R(200, {'status': 'EXECUTED', 'brokerage_order_id': 'O1', 'filled_quantity': '0.008', 'execution_price': '600'})
            if path == '/snapTrade/deleteUser':
                return R(200, {})
            return R(404, {})
    monkeypatch.setattr(rs, '_fmk_http', C())

    class Q:
        def __init__(self, b):
            self.b = b

        async def json(self):
            return self.b
    assert asyncio.run(rs.familia_broker('WALLET', 'ok')) == {'ready': True, 'linked': False}
    out = asyncio.run(rs.familia_broker_link(Q({'address': 'WALLET', 'session': 'ok', 'back': 'http://localhost:51367/familia'})))
    assert out['url'].startswith('https://app.snaptrade.com/')
    stored = json.dumps(rs._json_load(rs.BROKERS_PATH, {}))
    assert 'SECRET' not in stored and 'WALLET' in stored                                                      # the secret is sealed at rest
    v = asyncio.run(rs.familia_broker('WALLET', 'ok'))
    assert v['linked'] and v['accounts'][0]['positions'][0]['ticker'] == 'SPY' and v['value'] == 640.0
    o = asyncio.run(rs.familia_broker_order(Q({'address': 'WALLET', 'session': 'ok', 'accountId': 'A1', 'symbol': 'SPY', 'action': 'BUY', 'usd': 5})))
    assert o['status'] == 'EXECUTED' and [c for c in calls if c[1] == '/trade/place'][0][2]['notional_value'] == 5.0
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.familia_broker_order(Q({'address': 'WALLET', 'session': 'ok', 'accountId': 'SOMEONE-ELSES', 'symbol': 'SPY', 'action': 'BUY', 'usd': 5})))
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.familia_broker_link(Q({'address': 'WALLET', 'session': 'bad'})))                           # no signed session, no link
    assert asyncio.run(rs.familia_broker_unlink(Q({'address': 'WALLET', 'session': 'ok'}))) == {'ok': True}
    assert 'WALLET' not in (rs._json_load(rs.BROKERS_PATH, {}) or {}) and ('DELETE', '/snapTrade/deleteUser', None) in calls
