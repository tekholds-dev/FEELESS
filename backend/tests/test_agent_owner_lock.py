"""🔒 An agent belongs to a signed-in WALLET (owner 2026-10-30: signed out, refreshed, and could still chat with and drive the agent).
The browser id alone never controls an agent: signed out ⇒ 401 + a public view, another wallet ⇒ 403, an older agent is claimed once."""
import hashlib

import pytest


def _client(monkeypatch, cats):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': cats, 'events': []}
    toks = {'tok-me': 'WALLET_ME', 'tok-them': 'WALLET_THEM'}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(t.encode()).hexdigest(): {'address': w, 'exp': 9e18} for t, w in toks.items()}})
    return fs, store, TestClient(fs.app)


def _general(owner_wallet=None):
    c = {'id': 'g', 'ownerId': 'browser-1', 'name': 'Happy', 'handle': 'happy', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False,
         'createdAt': 1, 'brainsCfg': {'kind': 'general', 'brains': ['m/a'], 'credit': 0}}
    if owner_wallet:
        c['ownerWallet'] = owner_wallet
    return c


def test_signed_out_the_browser_id_alone_controls_nothing(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': _general('WALLET_ME')})
    assert c.post('/api/cats/g/work', json={'op': 'state', 'ownerId': 'browser-1'}).status_code == 401
    assert c.post('/api/cats/g/action', json={'action': 'stop', 'ownerId': 'browser-1'}).status_code == 401
    assert c.get('/api/cats/g/files?ownerId=browser-1').status_code == 401
    assert c.get('/api/cats/g/work/shot/0?ownerId=browser-1').status_code == 401
    assert c.post('/api/cats/g/recovery-pin', json={'action': 'recovery', 'ownerId': 'browser-1'}).status_code == 401
    assert c.get('/api/cats/g?ownerId=browser-1').json()['cat']['mine'] is False          # the public view
    assert c.get('/api/cats?ownerId=browser-1').json()['cats'] == []
    assert 'WALLET_ME' not in c.get('/api/cats/g?ownerId=browser-1&session=tok-me').text   # the owner wallet never leaves the server


def test_another_wallet_is_refused_even_with_the_browser_id(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': _general('WALLET_ME')})
    assert c.post('/api/cats/g/work', json={'op': 'state', 'ownerId': 'browser-1', 'session': 'tok-them'}).status_code == 403
    assert c.post('/api/cats/g/action', json={'action': 'stop', 'ownerId': 'browser-1', 'session': 'tok-them'}).status_code == 403
    assert c.get('/api/cats/g?ownerId=browser-1&session=tok-them').json()['cat']['mine'] is False
    assert c.get('/api/cats/g?session=tok-me').json()['cat']['mine'] is True               # the owner wallet, any browser
    assert c.post('/api/cats/g/work', json={'op': 'state', 'session': 'tok-me'}).status_code == 200


def test_an_older_agent_is_claimed_once_by_its_browser_plus_a_signed_wallet(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': _general()})
    assert c.post('/api/cats/g/work', json={'op': 'state', 'ownerId': 'browser-2', 'session': 'tok-them'}).status_code == 403   # wrong browser
    assert c.post('/api/cats/g/work', json={'op': 'state', 'ownerId': 'browser-1', 'session': 'tok-me'}).status_code == 200
    assert store['cats']['g']['ownerWallet'] == 'WALLET_ME'
    assert c.post('/api/cats/g/work', json={'op': 'state', 'ownerId': 'browser-1', 'session': 'tok-them'}).status_code == 403   # claimed: the browser id no longer helps


def test_create_and_recover_need_a_signed_wallet(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': _general('WALLET_ME')})
    form = {'ownerId': 'browser-9', 'name': 'New', 'handle': 'new', 'brains': ['m/a']}
    assert c.post('/api/cats', json=form).status_code == 401
    assert c.post('/api/cats/recover', json={'handle': 'happy', 'pin': '123456', 'ownerId': 'browser-9'}).status_code == 401


def test_owner_check_is_pure():
    fs = pytest.importorskip('feecat_service')
    assert fs.owner_check({'ownerWallet': 'A'}, '') == 'signin'
    assert fs.owner_check({'ownerWallet': 'A'}, 'A') == 'ok'
    assert fs.owner_check({'ownerWallet': 'A'}, 'B', 'b1') == 'no'
    assert fs.owner_check({'ownerId': 'b1'}, 'B', 'b1') == 'claim'
    assert fs.owner_check({'ownerId': 'b1', 'agentWallet': {'owner': 'A'}}, 'B', 'b1') == 'no'   # its agent wallet's signer owns it


def test_a_visitor_sees_the_card_never_the_vitals(monkeypatch):
    cat = {**_general('WALLET_ME'), 'chat': [{'by': 'you', 'text': 'my secret plan'}], 'realWallet': 'WALLET_ME', 'agentWallet': {'address': 'AGENTW', 'owner': 'WALLET_ME'},
           'creditPaid': [{'sig': 'SIG1', 'usd': 2.5}], 'limits': {'dayUsd': 1}, 'apiKeys': {'birdeye': {'last4': 'k9z1', 'at': 1}}, 'logins': [{'site': 'x.com', 'user': 'me'}],
           'wins': 3, 'losses': 1, 'look': {'tag': 'HAPPY'}}
    cat['brainsCfg'].update(credit=2.5, cloud=[{'text': 'agreed: BONK looks thin'}], minds={'m/a': [{'text': 'private note'}]})
    fs, store, c = _client(monkeypatch, {'g': cat})
    for sess in ('', 'tok-them'):
        body = c.get(f'/api/cats/g?session={sess}').text
        for secret in ('my secret plan', 'WALLET_ME', 'AGENTW', 'SIG1', 'dayUsd', 'k9z1', 'apiDrawer', 'x.com', 'private note', '"credit"'):
            assert secret not in body, (sess, secret)
        d = c.get(f'/api/cats/g?session={sess}').json()['cat']
        assert d['wins'] == 3 and d['look'] == {'tag': 'HAPPY'} and d['brainsCfg']['cloud'][0]['text'].startswith('agreed') and d['mine'] is False
    assert 'my secret plan' in c.get('/api/cats/g?session=tok-me').text   # the owner sees all of it


def test_every_owner_door_refuses_a_signed_out_caller(monkeypatch):
    """🔒 The sweep: every agent route that changes or shows owner-only things answers 401/403 with no session — a new door can't slip by."""
    fs, store, c = _client(monkeypatch, {'g': _general('WALLET_ME')})
    public_ok = {'/api/cats/{cat_id}', '/api/cats/{cat_id}/profile', '/api/cats/{cat_id}/files/{name}', '/api/cats/{cat_id}/live'}
    seen = 0
    for r in fs.app.routes:
        path = getattr(r, 'path', '')
        if not path.startswith('/api/cats/{cat_id}') or path in public_ok:
            continue
        url = path.replace('{cat_id}', 'g').replace('{i}', '0').replace('{file_id}', 'a' * 32).replace('{name}', 'x')
        for m in getattr(r, 'methods', []) - {'HEAD', 'OPTIONS'}:
            code = c.request(m, url, json={'ownerId': 'browser-1', 'op': 'state', 'action': 'stop'}).status_code
            assert code in (401, 403, 404, 405, 422), (m, path, code)
            seen += 1
    assert seen >= 10


def test_responses_carry_armor_and_owner_doors_are_rate_limited(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': _general('WALLET_ME')})
    h = c.get('/api/cats/g').headers
    assert h['x-frame-options'] == 'DENY' and h['x-content-type-options'] == 'nosniff' and "frame-ancestors 'none'" in h['content-security-policy']
    box = {}
    assert all(fs.rate_ok(('ip', 'g'), now=100, store=box) for _ in range(fs.RATE_MAX))
    assert not fs.rate_ok(('ip', 'g'), now=101, store=box) and fs.rate_ok(('ip', 'g'), now=100 + fs.RATE_WIN + 1, store=box)


def test_the_public_live_view_shows_hosts_and_step_kinds_never_the_page():
    fs = pytest.importorskip('feecat_service')
    w = {'task': {'status': 'working', 'text': 'my secret ask', 'windows': [{'i': 0, 'model': 'openai/gpt-x', 'status': 'working', 'url': 'https://mail.google.com/inbox/secret?u=me',
         'shot': True, 'live': 'https://steel/x', 'pw': {'pw': 'hunter2'}, 'steps': [{'action': 'type', 'thought': 'typing the password', 'detail': 'hunter2'}]}]}}
    out = fs.public_live(w)
    assert out == {'status': 'working', 'windows': [{'i': 0, 'model': 'gpt-x', 'status': 'working', 'host': 'mail.google.com', 'action': 'type', 'steps': 1, 'provider': None}]}
    assert fs.public_live(None) == {'status': 'idle', 'windows': []}


def test_live_now_lists_working_agents_with_visitor_safe_windows(monkeypatch):
    fs, store, c = _client(monkeypatch, {'g': {**_general('WALLET_ME'), 'chat': [{'by': 'you', 'text': 'secret ask'}]}})
    monkeypatch.setitem(fs._WORK, 'g', {'at': 5, 'task': {'status': 'working', 'text': 'secret ask', 'windows': [{'i': 0, 'model': 'a/x', 'status': 'working', 'url': 'https://x.com/home?t=1', 'steps': [{'action': 'open', 'thought': 'secret'}]}]}})
    j = c.get('/api/cats/live-now').json()
    assert j['agents'][0]['id'] == 'g' and j['agents'][0]['windows'][0]['host'] == 'x.com'
    assert 'secret' not in c.get('/api/cats/live-now').text and 'WALLET_ME' not in c.get('/api/cats/live-now').text


def test_the_creator_and_hq_admins_run_five_agents_everyone_else_two(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    assert fs.agent_max(True) == 5 and fs.agent_max(False) == 2
    cats = {f'c{i}': {**_general('WALLET_ME'), 'id': f'c{i}', 'handle': f'h{i}'} for i in range(2)}
    fs, store, c = _client(monkeypatch, cats)
    async def staff(session=''):
        return session == 'tok-me'
    monkeypatch.setattr(fs, '_session_staff', staff)
    assert c.get('/api/cats?session=tok-me').json()['max'] == 5
    form = {'ownerId': 'browser-1', 'name': 'Third', 'handle': 'third', 'brains': ['m/a'], 'session': 'tok-me'}
    assert c.post('/api/cats', json=form).status_code != 400 or 'agents' not in c.post('/api/cats', json=form).text
