"""🎯 Real Kalshi bids: every guard, the signature Kalshi checks, the order shape, and the key as the owner pastes it. No network, no money."""
import base64
import time

import kalshi_bid as kb

NOW = 1_800_000_000


def _iso(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


def _mkt(ticker='KXNBAGAME-26NOV16ORLBOS-ORL', yes='0.4000', no='0.6100', close=NOW + 7200, status='active', title='Orlando wins'):
    return {'ticker': ticker, 'title': title, 'yes_sub_title': title.split()[0], 'status': status, 'close_time': _iso(close), 'yes_ask_dollars': yes, 'no_ask_dollars': no}


ON = {'mode': 'auto', 'bidUsd': 1, 'dayUsd': 3, 'floorUsd': 2, 'minConf': 65}
PICK = {'ticker': 'KXNBAGAME-26NOV16ORLBOS-ORL', 'side': 'yes', 'conf': [72, 70]}


def _pem():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return k, k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()


def test_settings_default_and_clamp_to_the_hard_limits_with_no_on_switch():
    c = kb.cfg({'on': False})   # an old saved Off no longer blocks anything (owner 2026-11-15: no cutting on)
    assert 'on' not in c and c['mode'] == 'approve' and c['bidUsd'] == 1.0
    c = kb.cfg({'mode': 'auto', 'bidUsd': 500, 'dayUsd': 999, 'minConf': 5})
    assert c['bidUsd'] == kb.HARD_BID and c['dayUsd'] == kb.HARD_DAY and c['minConf'] == 50


def test_a_pob_he_asked_for_bids_now_an_auto_run_only_when_auto_is_on():
    assert kb.sends_now({}, 'you') and kb.sends_now({'mode': 'approve'}, None)
    assert not kb.sends_now({'mode': 'approve'}, 'auto') and kb.sends_now({'mode': 'auto'}, 'auto')


def test_every_guard_refuses_with_its_reason():
    m = _mkt(); bal = 10.0
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
    assert kb.relevant(rows, 'chiefs tonight', NOW) == []   # a named team with no market: none, never the league's other games (owner 2026-11-15)
    assert [m['ticker'] for m in kb.relevant(rows, 'best picks tonight', NOW)] == ['KXNBAGAME-26NOV16ORLBOS-ORL', 'T2']   # no team named: the league's open games
    assert kb.series_for('lakers vs celtics') == ['KXNBAGAME'] and 'ticker' in kb.brief(got) and kb.brief([]) == ''


def test_the_owner_taps_approve_and_exactly_one_limit_order_goes_out_on_his_key(monkeypatch, tmp_path):
    import pytest
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    _, pem = _pem(); now = time.time()
    tk = {'id': 'kb1', 'ticker': PICK['ticker'], 'side': 'yes', 'conf': [72, 70], 'price': 0.4, 'status': 'waiting', 'folder': 'pob1', 'title': 'Orlando wins'}
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'kalshiCfg': {'mode': 'approve', 'bidUsd': 1, 'dayUsd': 3, 'floorUsd': 2, 'minConf': 65},
                            'pobFolders': [{'id': 'pob1', 'kind': 'PoB', 'topic': 'orlando', 'kalshi': tk}]}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, prov, **kw: f'a952bcbe-ec3b-4b5b-b8f9-11dae589608c {pem}' if prov == 'kalshi' else None)
    sent = []; mk = _mkt(close=now + 7200)
    async def market(h, t): return mk
    async def balance(h, k, p): return 10.0
    async def place(h, k, p, body): sent.append(body); return {'order_id': 'o-1', 'status': 'resting'}
    monkeypatch.setattr(fs._kb, 'market', market); monkeypatch.setattr(fs._kb, 'balance', balance); monkeypatch.setattr(fs._kb, 'place', place)
    async def unstarted(h, m): return True
    monkeypatch.setattr(fs._kb, 'unstarted', unstarted)
    c = TestClient(fs.app); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    j = post('kalshi_bid', job='kb1').json()
    assert len(sent) == 1 and sent[0]['type'] == 'limit' and sent[0]['yes_price'] == 40 and sent[0]['count'] == 2
    assert j['ticket']['status'] == 'resting' and j['ticket']['usd'] == 0.8 and j['spentToday'] == 0.8 and j['bids'][0]['orderId'] == 'o-1'
    assert post('kalshi_bid', job='kb1').status_code == 409 and len(sent) == 1   # one tap, one order
    # a price that ran away from the minds' pick is refused
    post('kalshi_cfg', tools={'mode': 'approve'})
    store['cats']['g']['pobFolders'].append({'id': 'pob3', 'kind': 'PoB', 'kalshi': {**tk, 'id': 'kb3', 'ticker': 'T3', 'status': 'waiting', 'price': 0.30}})
    mk3 = _mkt(ticker='T3', yes='0.4500', close=now + 7200)
    async def market3(h, t): return mk3
    monkeypatch.setattr(fs._kb, 'market', market3)
    j = post('kalshi_bid', job='kb3').json()
    assert j['ticket']['status'] == 'refused' and 'price moved' in j['ticket']['why'] and len(sent) == 1


def test_sealing_a_kalshi_or_fal_key_runs_one_free_live_check_and_shows_it(monkeypatch):
    import asyncio
    import pytest
    fs = pytest.importorskip('feecat_service')
    _, pem = _pem()
    async def bal(h, k, p): return 10.0
    monkeypatch.setattr(fs._kb, 'balance', bal)
    got = asyncio.run(fs._key_check('kalshi', 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c ' + pem))
    assert got['ok'] and '$10.00' in got['why']
    assert asyncio.run(fs._key_check('kalshi', 'nonsense'))['ok'] is False
    class R:
        def __init__(self, code): self.status_code = code
    class H:
        def __init__(self, code): self.code = code
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None): assert headers['Authorization'].startswith('Key ') and '/status' in url; return R(self.code)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H(401))
    assert asyncio.run(fs._key_check('fal', 'abc-123:deadbeefdeadbeef'))['ok'] is False
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H(404))
    assert asyncio.run(fs._key_check('fal', 'abc-123:deadbeefdeadbeef'))['ok'] is True


def test_ed25519_key_seals_splits_and_signs():
    # 🔑 Kalshi's default key type is Ed25519 now (the owner's key was one, 2026-11-11): it must seal, split and sign (RSA still works)
    import base64 as b64
    import re as re_
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
    import cat_keys
    for key in (ed25519.Ed25519PrivateKey.generate(), rsa.generate_private_key(public_exponent=65537, key_size=2048)):
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        secret = 'b7990b29-83c1-4017-a192-3de083000000 ' + pem.strip()
        assert re_.match(cat_keys.PROVIDERS['kalshi'][3], secret)
        kid, clean = kb.split_key(secret)
        assert kid == 'b7990b29-83c1-4017-a192-3de083000000' and clean.startswith('-----BEGIN ' + 'PRIVATE KEY')
        sig = b64.b64decode(kb.sign(clean, 'GET', '/trade-api/v2/portfolio/balance?x=1', 1700000000000))
        msg = b'1700000000000GET/trade-api/v2/portfolio/balance'
        if isinstance(key, ed25519.Ed25519PrivateKey):
            key.public_key().verify(sig, msg)   # raises if wrong
        else:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            key.public_key().verify(sig, msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())


def _game(t, a, b, close=NOW + 7200, occ=NOW + 3 * 3600):
    side = t.split('-')[-1]; lab = {'DAL': 'Dallas', 'BOS': 'Boston', 'LAL': 'Los Angeles L', 'PHX': 'Phoenix', 'ORL': 'Orlando'}[side]
    return {**_mkt(ticker=t, title=f'{lab} wins', close=close), 'yes_sub_title': lab, 'occurrence_datetime': _iso(occ), 'rules_primary': f'If {lab} wins the {a} vs {b} Pro Basketball game originally scheduled for Nov 15, 2026, then the market resolves to Yes.'}


ROWS = [_game('KXNBAGAME-26NOV15DALBOS-DAL', 'Dallas', 'Boston'), _game('KXNBAGAME-26NOV15DALBOS-BOS', 'Dallas', 'Boston'),
        _game('KXNBAGAME-26NOV15LALPHX-LAL', 'Los Angeles L', 'Phoenix', close=NOW + 3600), _game('KXNBAGAME-26NOV16ORLBOS-BOS', 'Orlando', 'Boston', close=NOW + 90000)]


def test_a_pob_sees_only_its_own_game_on_kalshi():
    """Owner 2026-11-15: a Mavericks vs Celtics PoB was shown Lakers–Suns. Nicknames map to Kalshi's city labels; two teams = the game between them."""
    tick = lambda topic: [m['ticker'] for m in kb.relevant(ROWS, topic, NOW, series=['KXNBAGAME'])]
    assert kb.teams_in('Mavericks vs Celtics') == ['Dallas', 'Boston'] and kb.teams_in('lakers vs clippers', ['KXNBAGAME']) == ['Los Angeles L', 'Los Angeles C']
    assert tick('Mavericks vs Celtics') == ['KXNBAGAME-26NOV15DALBOS-DAL', 'KXNBAGAME-26NOV15DALBOS-BOS']
    assert tick('celtics tonight') == ['KXNBAGAME-26NOV15DALBOS-DAL', 'KXNBAGAME-26NOV15DALBOS-BOS', 'KXNBAGAME-26NOV16ORLBOS-BOS']
    assert tick('Lakers vs Celtics') == [] and tick('Foo vs Bar') == []   # no such game / unknown names: none, never a stranger's game
    assert tick('best nba picks')[0] == 'KXNBAGAME-26NOV15LALPHX-LAL'   # no team: soonest first


def test_a_game_that_started_is_never_offered_for_a_bid():
    """Already-ran guard: ESPN's state and start time decide; off the board, only a game Kalshi expects to end 6 h+ out counts as not started."""
    m = ROWS[0]; at = lambda s: time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(s))
    g = lambda state, start: [{'state': state, 'at': at(start), 'teams': [{'short': 'Mavericks', 'name': 'Dallas Mavericks'}, {'short': 'Celtics', 'name': 'Boston Celtics'}]}]
    assert kb.not_started(m, g('pre', NOW + 600), NOW) is True
    assert kb.not_started(m, g('in', NOW + 600), NOW) is False and kb.not_started(m, g('post', NOW - 9000), NOW) is False
    assert kb.not_started(m, g('pre', NOW - 120), NOW) is False   # ESPN still says pre two minutes past tip-off
    assert kb.not_started(m, [], NOW) is False   # off the board, ends in 3 h: unsure → not offered
    assert kb.not_started(_game('KXNBAGAME-26NOV18DALBOS-DAL', 'Dallas', 'Boston', occ=NOW + 3 * 86400), [], NOW) is True


def test_kalshi_goes_first_in_the_research_and_the_chat_says_so():
    note = kb.first_note(ROWS[:2])
    assert note.startswith('THE LIVE KALSHI MARKET') and 'KXNBAGAME-26NOV15DALBOS-DAL' in note and kb.first_note([]) == ''
    assert 'Kalshi first: Dallas wins 0.4' in kb.first_say(ROWS[:2], True) and 'without a real bid' in kb.first_say([], True) and kb.first_say(ROWS, False) == ''


def test_a_split_still_ends_in_a_pick_he_can_place():
    """Owner 2026-11-15 'they either choose or give me a option or pick'. Only HIS tap places an offer; under his minimum, nothing is offered."""
    k = lambda t, s, c, name='a': {'mind': 0, 'name': name, 'picks': [{'pick': 'x', 'confidence': c, 'why': 'w', 'kalshi': {'ticker': t, 'side': s}}]}
    ids = {'T1', 'T2'}
    assert kb.offer([k('T1', 'yes', 70, 'hy4'), k('T2', 'no', 80, 'glm')], ids, 65) == {'ticker': 'T2', 'side': 'no', 'conf': [80], 'why': ['w'], 'by': 'glm'}
    assert kb.offer([k('T1', 'yes', 45)], ids, 65) is None and kb.offer([k('T9', 'yes', 90)], ids, 65) is None
    assert 'tap Approve' in kb.outcome_line({'status': 'waiting', 'offer': 'glm', 'side': 'no', 'title': 'Boston wins', 'conf': [80]}, True)
    assert 'Real Kalshi bid placed' in kb.outcome_line({'orderId': 'o', 'side': 'yes', 'title': 'Dallas wins', 'count': 2, 'price': 0.4, 'usd': 0.8}, True)
    assert 'no single pick' in kb.outcome_line(None, True) and 'on paper' in kb.outcome_line(None, False)
    assert 'You MUST back exactly one' in kb.brief(ROWS[:1])


def test_the_room_shows_money_in_worth_now_and_the_payout_without_fees():
    t = {'ticker': 'T', 'side': 'yes', 'title': 'Dallas wins', 'price': 0.4, 'count': 2, 'filled': 2, 'orderId': 'o', 'status': 'filled', 'livePx': 0.55}
    v = kb.room_view(t)
    assert (v['cost'], v['now'], v['pnl'], v['placed']) == (0.8, 1.1, 0.3, True)
    assert kb.room_view({**t, 'outcome': 'won'})['pnl'] == 1.2 and kb.room_view({**t, 'outcome': 'lost'})['pnl'] == -0.8
    assert kb.room_view({**t, 'orderId': None, 'status': 'waiting', 'offer': 'glm'})['filled'] == 0 and kb.room_view({**t, 'orderId': None})['pnl'] is None


def test_review_fixes_resting_text_confidence_and_utc():
    """Second pass 2026-11-15: a resting order with nothing filled shows $0 in, not the whole order; '70%' reads as 70; Kalshi times are UTC all year."""
    v = kb.room_view({'orderId': 'o1', 'ticker': 'T', 'count': 3, 'filled': 0, 'price': 0.4, 'status': 'resting', 'livePx': 0.6})
    assert v['filled'] == 0 and v['cost'] == 0 and v['pnl'] is None
    assert kb.room_view({'orderId': 'o1', 'count': 3, 'price': 0.4, 'status': 'filled'})['cost'] == 1.2
    calls = [{'name': 'A', 'picks': [{'confidence': '70%', 'kalshi': {'ticker': 'T', 'side': 'yes'}}]}, {'name': 'B', 'picks': [{'confidence': 'high', 'kalshi': {'ticker': 'T', 'side': 'no'}}]}]
    o = kb.offer(calls, {'T'}, 65)
    assert o['by'] == 'A' and o['conf'] == [70]
    assert kb._ts('2026-07-01T00:00:00Z') == 1782864000 and kb._ts('2026-12-01T00:00:00Z') == 1796083200
