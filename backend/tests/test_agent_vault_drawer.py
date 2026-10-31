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
