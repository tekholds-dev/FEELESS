"""🎯 Real Kalshi bids: every guard, the signature Kalshi checks, the order shape, and the key as the owner pastes it. No network, no money."""
import base64
import time

import kalshi_bid as kb

NOW = 1_800_000_000


def _iso(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


def _mkt(ticker='KXNBAGAME-26NOV16ORLBOS-ORL', yes='0.4000', no='0.6100', close=NOW + 7200, status='active', title='Orlando wins'):
    return {'ticker': ticker, 'title': title, 'yes_sub_title': title.split()[0], 'status': status, 'close_time': _iso(close), 'yes_ask_dollars': yes, 'no_ask_dollars': no}


ON = {'on': True, 'mode': 'auto', 'bidUsd': 1, 'dayUsd': 3, 'floorUsd': 2, 'minConf': 65}
PICK = {'ticker': 'KXNBAGAME-26NOV16ORLBOS-ORL', 'side': 'yes', 'conf': [72, 70]}


def _pem():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k, k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()


def test_settings_are_off_by_default_and_clamped_to_the_hard_limits():
    c = kb.cfg({})
    assert c['on'] is False and c['mode'] == 'approve' and c['bidUsd'] == 1.0
    c = kb.cfg({'on': True, 'mode': 'auto', 'bidUsd': 500, 'dayUsd': 999, 'minConf': 5})
    assert c['bidUsd'] == kb.HARD_BID and c['dayUsd'] == kb.HARD_DAY and c['minConf'] == 50
    assert kb.cfg({'on': 'yes'})['on'] is False   # only a real true switches it on


def test_every_guard_refuses_with_its_reason():
    m = _mkt(); bal = 10.0
    assert kb.check({**ON, 'on': False}, m, PICK, [], bal, NOW)[1].startswith('Real Kalshi bids are off')
    assert 'not open' in kb.check(ON, _mkt(ticker='OTHER'), PICK, [], bal, NOW)[1]
    assert 'under 10 minutes' in kb.check(ON, _mkt(close=NOW + 300), PICK, [], bal, NOW)[1]
    assert '65%' in kb.check(ON, m, {**PICK, 'conf': [80, 60]}, [], bal, NOW)[1]
    assert '5¢ to 95¢' in kb.check(ON, _mkt(yes='0.9700'), PICK, [], bal, NOW)[1]
    assert 'last 24 hours' in kb.check(ON, m, PICK, [{'ticker': PICK['ticker'], 'at': NOW - 3600, 'status': 'sent', 'usd': 0.4}], bal, NOW)[1]
    spent = [{'ticker': f'T{i}', 'at': NOW - 60, 'status': 'filled', 'usd': 1.0} for i in range(3)]
    assert 'cap' in kb.check(ON, m, PICK, spent, bal, NOW)[1]
    assert 'floor' in kb.check(ON, m, PICK, [], 2.2, NOW)[1]
    assert 'balance' in kb.check(ON, m, PICK, [], None, NOW)[1]


def test_a_passing_bid_buys_whole_contracts_inside_the_cap_as_a_limit_order():
    ok, why, count, price = kb.check(ON, _mkt(), PICK, [], 10.0, NOW)
    assert ok and count == 2 and price == 0.4 and '$0.80' in why   # $1 cap / 40¢ = 2 contracts, never more than the cap
    o = kb.order(PICK, count, price, 'cid')
    assert o == {'ticker': PICK['ticker'], 'action': 'buy', 'side': 'yes', 'count': 2, 'type': 'limit', 'yes_price': 40, 'client_order_id': 'cid'}
    assert kb.order({**PICK, 'side': 'no'}, 1, 0.61)['no_price'] == 61


def test_only_a_market_both_minds_backed_on_the_same_side_becomes_a_ticket():
    ids = {PICK['ticker'], 'X-2'}
    a = {'picks': [{'pick': 'Magic', 'confidence': 72, 'kalshi': {'ticker': PICK['ticker'], 'side': 'yes'}}]}
    b = {'picks': [{'pick': 'Orlando', 'confidence': 70, 'kalshi': {'ticker': PICK['ticker'], 'side': 'yes'}}]}
    got = kb.chosen([a, b], ids)
    assert got['ticker'] == PICK['ticker'] and got['side'] == 'yes' and got['conf'] == [72, 70]
    assert kb.chosen([a, {'picks': [{'pick': 'x', 'confidence': 90, 'kalshi': {'ticker': PICK['ticker'], 'side': 'no'}}]}], ids) is None
    assert kb.chosen([a, {'picks': [{'pick': 'x', 'kalshi': {'ticker': 'MADE-UP', 'side': 'yes'}}]}], ids) is None   # a ticker it was never shown
    assert kb.chosen([a], ids) is None


def test_the_signature_is_what_kalshi_verifies():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    key, pem = _pem()
    h = kb.headers('a952bcbe-ec3b-4b5b-b8f9-11dae589608c', pem, 'POST', '/portfolio/orders', now=NOW)
    assert h['KALSHI-ACCESS-TIMESTAMP'] == str(NOW * 1000)
    msg = f"{NOW * 1000}POST/trade-api/v2/portfolio/orders".encode()
    key.public_key().verify(base64.b64decode(h['KALSHI-ACCESS-SIGNATURE']), msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())


def test_the_key_pasted_on_one_line_is_rebuilt_and_sealed_in_the_vault():
    import cat_keys as ck
    _, pem = _pem()
    one_line = 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c ' + pem.replace('\n', ' ')
    kid, clean = kb.split_key(one_line)
    assert kid == 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c' and clean.startswith('-----BEGIN RSA ' + 'PRIVATE KEY-----\n') and kb.sign(clean, 'GET', '/x', 1)
    cat = {'id': 'c1'}
    rows = ck.put(cat, 'kalshi', one_line, env={'BROKER_SECRET_KEY': 'k' * 44})
    row = next(r for r in rows if r['provider'] == 'kalshi')
    assert row['saved'] and row['last4'] == '608c' and 'PRIVATE' not in str(cat['apiKeys']['kalshi'])
    glued = 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c' + pem.replace('\n', '')   # Chrome drops line breaks in a one-line box
    assert kb.split_key(glued)[0] == 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c' and kb.sign(kb.split_key(glued)[1], 'GET', '/x', 1)
    assert next(r for r in ck.put({'id': 'c2'}, 'kalshi', glued, env={'BROKER_SECRET_KEY': 'k' * 44}) if r['provider'] == 'kalshi')['last4'] == '608c'
    assert kb.split_key('not a key') == (None, None)


def test_only_open_markets_on_the_topic_are_shown_to_the_minds():
    rows = [_mkt(), _mkt(ticker='T2', title='Boston wins'), _mkt(ticker='T3', close=NOW + 100), _mkt(ticker='T4', status='settled')]
    got = kb.relevant(rows, 'orlando magic tonight', NOW)
    assert [m['ticker'] for m in got] == ['KXNBAGAME-26NOV16ORLBOS-ORL']
    assert [m['ticker'] for m in kb.relevant(rows, 'chiefs tonight', NOW)] == ['KXNBAGAME-26NOV16ORLBOS-ORL', 'T2']   # no word matched: the league's open games
    assert kb.series_for('lakers vs celtics') == ['KXNBAGAME'] and 'ticker' in kb.brief(got) and kb.brief([]) == ''


def test_the_owner_taps_approve_and_exactly_one_limit_order_goes_out_on_his_key(monkeypatch, tmp_path):
    import pytest
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    _, pem = _pem(); now = time.time()
    tk = {'id': 'kb1', 'ticker': PICK['ticker'], 'side': 'yes', 'conf': [72, 70], 'price': 0.4, 'status': 'waiting', 'folder': 'pob1', 'title': 'Orlando wins'}
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'kalshiCfg': {'on': True, 'mode': 'approve', 'bidUsd': 1, 'dayUsd': 3, 'floorUsd': 2, 'minConf': 65},
                            'pobFolders': [{'id': 'pob1', 'kind': 'PoB', 'topic': 'orlando', 'kalshi': tk}]}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, prov, **kw: f'a952bcbe-ec3b-4b5b-b8f9-11dae589608c {pem}' if prov == 'kalshi' else None)
    sent = []; mk = _mkt(close=now + 7200)
    async def market(h, t): return mk
    async def balance(h, k, p): return 10.0
    async def place(h, k, p, body): sent.append(body); return {'order_id': 'o-1', 'status': 'resting'}
    monkeypatch.setattr(fs._kb, 'market', market); monkeypatch.setattr(fs._kb, 'balance', balance); monkeypatch.setattr(fs._kb, 'place', place)
    c = TestClient(fs.app); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    j = post('kalshi_bid', job='kb1').json()
    assert len(sent) == 1 and sent[0]['type'] == 'limit' and sent[0]['yes_price'] == 40 and sent[0]['count'] == 2
    assert j['ticket']['status'] == 'resting' and j['ticket']['usd'] == 0.8 and j['spentToday'] == 0.8 and j['bids'][0]['orderId'] == 'o-1'
    assert post('kalshi_bid', job='kb1').status_code == 409 and len(sent) == 1   # one tap, one order
    # the door switched off: a new ticket is refused and nothing is sent
    store['cats']['g']['pobFolders'].append({'id': 'pob2', 'kind': 'PoB', 'kalshi': {**tk, 'id': 'kb2', 'ticker': 'T2', 'status': 'waiting'}})
    mk2 = {**_mkt(ticker='T2', close=now + 7200)}
    async def market2(h, t): return mk2
    monkeypatch.setattr(fs._kb, 'market', market2)
    post('kalshi_cfg', tools={'on': False})
    j = post('kalshi_bid', job='kb2').json()
    assert j['ticket']['status'] == 'refused' and 'off' in j['ticket']['why'] and len(sent) == 1
    # a price that ran away from the minds' pick is refused too
    post('kalshi_cfg', tools={'on': True, 'mode': 'approve'})
    store['cats']['g']['pobFolders'].append({'id': 'pob3', 'kind': 'PoB', 'kalshi': {**tk, 'id': 'kb3', 'ticker': 'T3', 'status': 'waiting', 'price': 0.30}})
    mk3 = _mkt(ticker='T3', yes='0.4500', close=now + 7200)
    async def market3(h, t): return mk3
    monkeypatch.setattr(fs._kb, 'market', market3)
    j = post('kalshi_bid', job='kb3').json()
    assert j['ticket']['status'] == 'refused' and 'price moved' in j['ticket']['why'] and len(sent) == 1
