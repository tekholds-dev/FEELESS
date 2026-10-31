"""🔐 The credentials drawer (owner 2026-10-30): you save a site's login once, sealed; a window that hits that site's sign-in gets it on the
server and goes on — the model only ever types {{username}} / {{password}}, and nothing in a response carries the password."""
import asyncio
import hashlib

import pytest


def test_saved_for_returns_the_newest_login_for_a_site(monkeypatch):
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-secret')
    cv = pytest.importorskip('cat_vault')
    cat = {}
    cv.put_login(cat, 'https://dropbox.com/login', 'old@mail.com', 'pw-old', now=1)
    cv.put_login(cat, 'dropbox.com', 'new@mail.com', 'pw-new', now=2)
    assert cv.saved_for(cat, 'https://www.dropbox.com/home') == ('new@mail.com', 'pw-new')
    assert cv.saved_for(cat, 'x.com') is None
    assert 'pw-new' not in str(cv.public_logins(cat))


def test_the_drawer_saves_sealed_and_hands_a_waiting_window_its_login(monkeypatch):
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-secret')
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    cat = {'id': 'g', 'ownerId': 'b1', 'ownerWallet': 'W', 'name': 'Happy', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'createdAt': 1,
           'brainsCfg': {'kind': 'general', 'brains': ['m/a'], 'credit': 1}}
    store = {'cats': {'g': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(b'tok').hexdigest(): {'address': 'W', 'exp': 9e18}}})
    ev = asyncio.Event()
    win = {'i': 0, 'model': 'm/a', 'status': 'human', 'human': {'kind': 'login', 'site': 'dropbox.com', 'why': 'log in to dropbox.com'}, 'steps': []}
    monkeypatch.setitem(fs._WORK, 'g', {'task': {'windows': [win]}, 'events': {0: ev}, 'go': {}})
    c = TestClient(fs.app)
    body = {'op': 'save_login', 'session': 'tok', 'text': 'https://www.dropbox.com/login', 'user': 'me@mail.com', 'secret': 'Sup3r!secret'}
    assert c.post('/api/cats/g/work', json={**body, 'session': ''}).status_code == 401
    r = c.post('/api/cats/g/work', json=body)
    assert r.status_code == 200 and 'Sup3r!secret' not in r.text and r.json()['logins'][0]['site'] == 'dropbox.com'
    assert 'Sup3r!secret' not in str(cat['logins'])                       # sealed at rest
    assert ev.is_set() and win['pw'] == {'site': 'dropbox.com', 'user': 'me@mail.com', 'pw': 'Sup3r!secret'}
    assert fs._WORK['g']['go'][0] is True
    assert 'Sup3r!secret' not in c.get('/api/cats/g?session=tok').text      # never echoed, even to its owner's desk


def test_each_agent_has_its_own_key_and_a_copied_data_folder_opens_nothing(monkeypatch, tmp_path):
    monkeypatch.delenv('BROKER_SECRET_KEY', raising=False)   # another test may leave one in the process env
    ck = pytest.importorskip('cat_keys')
    from cryptography.fernet import InvalidToken
    a = ck.seal('hunter2', 'agent-a')
    assert a.startswith('v2:') and ck.unseal(a, 'agent-a') == 'hunter2'
    with pytest.raises(InvalidToken):
        ck.unseal(a, 'agent-b')                                         # one agent's seal never opens with another's key
    monkeypatch.setenv('FEELESS_VAULT_KEY_FILE', str(tmp_path / 'other-machine.key'))
    with pytest.raises(InvalidToken):
        ck.unseal(a, 'agent-a')                                         # the data alone, without the master outside it: nothing


def test_older_seals_are_resealed_per_agent_at_startup(monkeypatch, tmp_path):
    monkeypatch.delenv('BROKER_SECRET_KEY', raising=False)   # another test may leave one in the process env
    ck = pytest.importorskip('cat_keys')
    (tmp_path / 'internal.key').write_text('old-shared-key')
    old = ck._fernet({}, tmp_path).encrypt(b'pw-old').decode()
    cat = {'id': 'z9', 'logins': [{'site': 'x.com', 'user': 'me', 'sealed': old}]}
    assert ck.reseal_cat(cat, data_dir=tmp_path) == 1 and cat['logins'][0]['sealed'].startswith('v2:')
    assert ck.unseal(cat['logins'][0]['sealed'], 'z9') == 'pw-old' and ck.reseal_cat(cat, data_dir=tmp_path) == 0


def test_signed_in_sites_the_owner_signs_in_by_hand_the_cookies_are_sealed_and_every_window_starts_with_them(monkeypatch):
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-secret'); monkeypatch.setenv('STEEL_API_KEY', 'fake')
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    cat = {'id': 'g', 'ownerId': 'b1', 'ownerWallet': 'W', 'name': 'Happy', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'createdAt': 1,
           'brainsCfg': {'kind': 'general', 'brains': ['m/a'], 'credit': 1}}
    store = {'cats': {'g': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(b'tok').hexdigest(): {'address': 'W', 'exp': 9e18}}})
    opened, closed = [], []

    async def steel(http, env, ctx=None):
        opened.append(ctx); return {'id': 'sid1', 'live': 'https://steel/live?interactive=true', 'connect': 'wss://x'}

    async def read_ctx(http, env, sid):
        return {'cookies': [{'name': 'auth_token', 'value': 'SECRET-COOKIE', 'domain': '.x.com', 'path': '/'}], 'localStorage': {}}

    class Page:
        def __init__(self, c): pass
        async def start(self): return self
        async def goto(self, u): return ''
        async def close(self): pass

    async def close(http, env, s):
        closed.append(s['id'])
    monkeypatch.setattr(fs._cb, '_steel', steel); monkeypatch.setattr(fs._cb, 'read_context', read_ctx)
    monkeypatch.setattr(fs._cb, 'LivePage', Page); monkeypatch.setattr(fs._cb, 'close_session', close)
    c = TestClient(fs.app)
    assert c.post('/api/cats/g/work', json={'op': 'signin_open', 'session': '', 'text': 'x.com'}).status_code == 401   # the owner's only
    assert c.post('/api/cats/g/work', json={'op': 'signin_save', 'session': 'tok'}).status_code == 400                # nothing open yet
    r = c.post('/api/cats/g/work', json={'op': 'signin_open', 'session': 'tok', 'text': 'x.com'})
    assert r.status_code == 200 and r.json() == {'live': 'https://steel/live?interactive=true', 'site': 'x.com'} and opened == [None]
    r = c.post('/api/cats/g/work', json={'op': 'signin_save', 'session': 'tok'})
    assert r.status_code == 200 and r.json()['signedIn'][0]['site'] == 'x.com' and 'SECRET-COOKIE' not in r.text and closed == ['sid1']
    assert 'SECRET-COOKIE' not in str(cat['siteSessions'])                                       # sealed at rest
    assert 'SECRET-COOKIE' not in c.get('/api/cats/g?session=tok').text                          # never on a page, even the owner's
    assert fs._site_ctx(cat)['cookies'][0]['value'] == 'SECRET-COOKIE'                          # …but its next window starts signed in
    r = c.post('/api/cats/g/work', json={'op': 'signin_drop', 'session': 'tok', 'text': 'https://x.com/home'})
    assert r.json()['signedIn'] == [] and fs._site_ctx(cat) is None


def test_saved_sign_ins_merge_later_wins_and_an_oversized_jar_is_dropped():
    cb = pytest.importorskip('cat_browser')
    a = {'cookies': [{'name': 't', 'domain': '.x.com', 'path': '/', 'value': 'old'}], 'localStorage': {'https://x.com': {'k': '1'}}}
    b = {'cookies': [{'name': 't', 'domain': '.x.com', 'path': '/', 'value': 'new'}], 'localStorage': {'https://x.com': {'j': '2'}}}
    m = cb.merge_contexts([a, b])
    assert [k['value'] for k in m['cookies']] == ['new'] and m['localStorage']['https://x.com'] == {'k': '1', 'j': '2'}
    assert cb.merge_contexts([]) is None and cb.merge_contexts([{'cookies': [{'name': 'big', 'value': 'x' * 500_000}]}]) is None
