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
    assert asyncio.run(rs.familia_broker('WALLET', 'ok')) == {'ready': True, 'snaptrade': True, 'linked': False, 'signup': bk.ALPACA_SIGNUP}
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


KEY, SEC = 'PK' + 'A1B2C3D4E5F6G7H8', 'x' * 40


def test_alpaca_bring_your_own_key_bodies_and_view():
    assert bk.alpaca_keys_ok(KEY, SEC) and not bk.alpaca_keys_ok('short', SEC) and not bk.alpaca_keys_ok(KEY, 'tiny')
    assert bk.alpaca_order({'symbol': 'spy', 'action': 'BUY', 'usd': 5}) == {'symbol': 'SPY', 'side': 'buy', 'type': 'market', 'time_in_force': 'day', 'notional': '5.00'}
    assert bk.alpaca_order({'symbol': 'BTC', 'action': 'BUY', 'usd': 10})['symbol'] == 'BTC/USD' and bk.alpaca_order({'symbol': 'BTC', 'action': 'BUY', 'usd': 10})['time_in_force'] == 'gtc'
    assert bk.alpaca_order({'symbol': 'AAPL', 'action': 'SELL', 'units': 2})['qty'] == '2.0'
    lim = bk.alpaca_order({'symbol': 'TSLA', 'action': 'BUY', 'type': 'Limit', 'price': 200, 'units': 3})
    assert (lim['type'], lim['limit_price'], lim['qty']) == ('limit', '200.0', '3.0')
    for bad in ({'symbol': 'SPY', 'action': 'BUY', 'usd': 0.5}, {'symbol': 'SPY', 'action': 'SHORT', 'usd': 5}, {'symbol': 'SPY', 'action': 'BUY'}):
        with pytest.raises(ValueError):
            bk.alpaca_order(bad)
    v = bk.alpaca_view({'account_number': 'PA12345678', 'cash': '40.5', 'buying_power': '81', 'equity': '640.5', 'status': 'ACTIVE'},
                       [{'symbol': 'SPY', 'qty': '1', 'current_price': '600', 'market_value': '600', 'unrealized_pl': '100', 'unrealized_plpc': '0.2', 'asset_class': 'us_equity'}], True)
    assert (v['id'], v['broker'], v['number'], v['value'], v['positions'][0]['pnlPct']) == ('alpaca', 'Alpaca · PAPER', '5678', 640.5, 20.0)


def test_the_seal_key_is_made_once_and_private(tmp_path):
    import os
    p = tmp_path / '.broker_seal'
    k = bk.seal_key_file(p)
    assert len(k) > 40 and bk.seal_key_file(p) == k and oct(os.stat(p).st_mode)[-3:] == '600'


def test_alpaca_keys_are_proven_live_then_sealed_and_trade_your_own_account(monkeypatch):
    import reputation_service as rs
    monkeypatch.delenv('SNAPTRADE_CLIENT_ID', raising=False); monkeypatch.delenv('BROKER_SECRET_KEY', raising=False)
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: 'WALLET')
    monkeypatch.setattr(rs, '_brk_cache', {})
    calls = []

    class R:
        def __init__(self, code, b):
            self.status_code, self.b = code, b

        def json(self):
            return self.b

    class C:
        async def request(self, method, url, headers=None, json=None, timeout=None):
            calls.append((method, url, json))
            if headers['APCA-API-SECRET-KEY'] != SEC:
                return R(401, {'message': 'unauthorized.'})
            assert url.startswith('https://paper-api.alpaca.markets')
            if url.endswith('/v2/account'):
                return R(200, {'account_number': 'PA1', 'cash': '100', 'buying_power': '200', 'equity': '100'})
            if url.endswith('/v2/positions'):
                return R(200, [])
            if url.endswith('/v2/orders'):
                return R(200, {'id': 'o1', 'status': 'accepted', 'filled_qty': '0'})
            return R(404, {})
    monkeypatch.setattr(rs, '_fmk_http', C())

    class Q:
        def __init__(self, b):
            self.b = b

        async def json(self):
            return self.b
    with pytest.raises(rs.HTTPException):                                                               # wrong secret → nothing stored
        asyncio.run(rs.familia_broker_keys(Q({'address': 'W', 'session': 's', 'key': KEY, 'secret': 'y' * 40, 'paper': True})))
    assert 'WALLET' not in (rs._json_load(rs.BROKERS_PATH, {}) or {})
    out = asyncio.run(rs.familia_broker_keys(Q({'address': 'W', 'session': 's', 'key': KEY, 'secret': SEC, 'paper': True})))
    assert out['ok'] and out['account']['broker'] == 'Alpaca · PAPER'
    raw = json.dumps(rs._json_load(rs.BROKERS_PATH, {}))
    assert SEC not in raw and KEY not in raw and rs.BROKER_SEAL_PATH.exists()                              # sealed with FEELESS's own key
    v = asyncio.run(rs.familia_broker('W', 's'))
    assert v['linked'] and v['accounts'][0]['id'] == 'alpaca' and v['accounts'][0]['cash'] == 100
    o = asyncio.run(rs.familia_broker_order(Q({'address': 'W', 'session': 's', 'accountId': 'alpaca', 'symbol': 'SPY', 'action': 'BUY', 'usd': 5})))
    assert o['status'] == 'accepted' and calls[-1][2] == {'symbol': 'SPY', 'side': 'buy', 'type': 'market', 'time_in_force': 'day', 'notional': '5.00'}
    assert asyncio.run(rs.familia_broker_keys(Q({'address': 'W', 'session': 's', 'remove': True}))) == {'ok': True}
    assert 'WALLET' not in (rs._json_load(rs.BROKERS_PATH, {}) or {})


def test_a_personal_snaptrade_key_is_the_owners_own_broker(monkeypatch):
    import reputation_service as rs
    monkeypatch.setenv('SNAPTRADE_CLIENT_ID', 'PERS-TESTCLIENT'); monkeypatch.setenv('SNAPTRADE_CONSUMER_KEY', 'CKEY'); monkeypatch.setenv('BROKER_SECRET_KEY', 'k' * 40)
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'OWNER')
    monkeypatch.setattr(rs, '_brk_cache', {})
    calls = []
    accounts = []

    class R:
        def __init__(self, code, b):
            self.status_code, self.b = code, b

        def json(self):
            return self.b

    class C:
        async def request(self, method, url, headers=None, json=None, timeout=None):
            path = url.split('/api/v1', 1)[1].split('?')[0]
            calls.append((method, path, url))
            assert 'userId' not in url and 'userSecret' not in url                                       # a personal key never sends user creds
            if path == '/accounts':
                return R(200, accounts)
            if path == '/snapTrade/login':
                return R(200, {'redirectURI': 'https://app.snaptrade.com/x'})
            if path.endswith('/positions') or path.endswith('/balances'):
                return R(200, [])
            if path == '/trade/place':
                return R(200, {'status': 'ACCEPTED', 'brokerage_order_id': 'T1'})
            return R(404, {})
    monkeypatch.setattr(rs, '_fmk_http', C())

    class Q:
        def __init__(self, b):
            self.b = b

        async def json(self):
            return self.b
    assert bk.personal('PERS-X') and not bk.personal('CID')
    v = asyncio.run(rs.familia_broker('OWNER', 's'))
    assert v['snaptrade'] and not v['linked']                                                               # set up, nothing linked → the link door
    assert asyncio.run(rs.familia_broker_link(Q({'address': 'OWNER', 'session': 's'})))['url'].startswith('https://app.snaptrade.com/')
    assert not [c for c in calls if c[1] == '/snapTrade/registerUser']
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.familia_broker_link(Q({'address': 'SOMEONE', 'session': 's'})))
    assert e.value.status_code == 403
    assert asyncio.run(rs.familia_broker('SOMEONE', 's'))['snaptrade'] is False                            # others get the Alpaca door only
    accounts.append({'id': 'TS1', 'institution_name': 'TradeStation', 'name': 'Margin', 'number': '11112222'})
    rs._brk_cache.clear()
    v = asyncio.run(rs.familia_broker('OWNER', 's'))
    assert v['linked'] and v['accounts'][0]['broker'] == 'TradeStation'
    o = asyncio.run(rs.familia_broker_order(Q({'address': 'OWNER', 'session': 's', 'accountId': 'TS1', 'symbol': 'SPY', 'action': 'BUY', 'usd': 5})))
    assert o['status'] == 'ACCEPTED'


def test_cryptocom_signing_order_and_view():
    import hashlib
    import hmac as _h
    import brokers as bk
    # the params string is Crypto.com's reference algorithm: sorted keys, key then value
    assert bk.cdc_params({'side': 'BUY', 'instrument_name': 'BTC_USD', 'notional': '25.00'}) == 'instrument_nameBTC_USDnotional25.00sideBUY'
    b = bk.cdc_signed('private/create-order', {'side': 'BUY', 'instrument_name': 'BTC_USD'}, 'KEY', 'SECRET', nonce=1700000000000, req_id=7)
    want = _h.new(b'SECRET', b'private/create-order7KEYinstrument_nameBTC_USDsideBUY1700000000000', hashlib.sha256).hexdigest()
    assert b['sig'] == want and b['nonce'] == 1700000000000 and b['api_key'] == 'KEY'
    assert bk.cdc_order({'symbol': 'sol', 'action': 'buy', 'usd': 25}) == {'instrument_name': 'SOL_USD', 'side': 'BUY', 'type': 'MARKET', 'notional': '25.00'}
    assert bk.cdc_order({'symbol': 'BTC/USD', 'action': 'sell', 'units': 0.001})['quantity'] == '0.001'
    for bad in ({'symbol': 'BTC', 'action': 'buy', 'usd': 0.5}, {'symbol': 'BTC', 'action': 'hold', 'usd': 5}, {'symbol': 'BTC', 'action': 'buy', 'type': 'limit', 'units': 1}):
        with pytest.raises(ValueError):
            bk.cdc_order(bad)
    v = bk.cdc_view({'data': [{'total_available_balance': '40', 'total_cash_balance': '120.5', 'position_balances': [
        {'instrument_name': 'USD', 'quantity': '40', 'market_value': '40'}, {'instrument_name': 'SOL', 'quantity': '0.5', 'market_value': '80.5'}, {'instrument_name': 'CRO', 'quantity': '0'}]}]})
    assert v['id'] == 'cdc' and v['cash'] == 40 and v['value'] == 120.5 and [r['ticker'] for r in v['positions']] == ['SOL', 'USD']
    assert bk.cdc_keys_ok('a' * 24, 'b' * 32) and not bk.cdc_keys_ok('short', 'b' * 32)
