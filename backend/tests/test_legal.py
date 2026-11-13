"""LEGAL-1: versioned per-wallet acceptance, the per-feature country / age gate, and self-serve export / delete."""
import json
import re
from pathlib import Path

import pytest

import legal as L

ME = 'A' * 32
OTHER = 'B' * 32


def test_frontend_shows_the_same_terms_version_the_server_checks():
    src = (Path(__file__).resolve().parents[2] / 'frontend/src/lib/legal.js').read_text()
    assert re.search(r"LEGAL_VERSION = '([^']+)'", src).group(1) == L.VERSION


def test_accept_needs_all_three_statements_this_version_and_an_open_country():
    s = L.new_state()
    with pytest.raises(ValueError):
        L.accept(s, ME, '2020-01-01', 'US', True, True)          # stale version
    with pytest.raises(ValueError):
        L.accept(s, ME, L.VERSION, 'US', False, True)            # not 18+
    with pytest.raises(ValueError):
        L.accept(s, ME, L.VERSION, 'US', True, False)            # no "not sanctioned / restricted"
    with pytest.raises(ValueError):
        L.accept(s, ME, L.VERSION, 'Narnia', True, True)         # not a country code
    with pytest.raises(ValueError):
        L.accept(s, ME, L.VERSION, 'KP', True, True)             # sanctioned, stated
    with pytest.raises(ValueError):
        L.accept(s, ME, L.VERSION, 'US', True, True, ip_country='IR')   # sanctioned, seen by the CDN
    row = L.accept(s, ME, L.VERSION, 'us', True, True, now=1.0)
    assert row['country'] == 'US' and L.status(s, ME)['accepted'] and not L.status(s, OTHER)['accepted']


def test_a_new_version_asks_again_and_keeps_the_old_one_in_history():
    s = L.new_state()
    s['accept'][ME] = {'v': '2026-09-26', 'at': 1.0, 'country': 'US', 'adult': True}
    assert not L.status(s, ME)['accepted']
    row = L.accept(s, ME, L.VERSION, 'US', True, True, now=2.0)
    assert row['history'][-1]['v'] == '2026-09-26'


def test_gate_per_feature_country_and_age():
    cfg = L.clean_cfg({'features': {'perps': {'blocked': ['US']}, 'launch': {'blocked': ['gb']}}})
    adult = {'adult': True, 'country': 'US'}
    assert L.gate(cfg, 'swap', None, adult)['ok']
    assert not L.gate(cfg, 'perps', None, adult)['ok']             # stated US → perps closed
    assert L.gate(cfg, 'perps', 'DE', adult)['ok']                 # the CDN's country wins over the stated one
    assert not L.gate(cfg, 'launch', 'GB', adult)['ok']
    assert not L.gate(cfg, 'swap', 'CU', adult)['ok']              # sanctioned = closed everywhere
    assert not L.gate(cfg, 'swap', None, None)['ok']               # wallet features need the 18+ acceptance
    assert L.gate(cfg, 'site', None, None)['ok']                   # browsing never does


def test_owner_cannot_empty_the_sanctioned_list_and_bad_input_is_dropped():
    cfg = L.clean_cfg({'everywhere': [], 'minAge': 3, 'features': {'swap': {'blocked': ['US', 'nope', 'us']}, 'fake': {'blocked': ['US']}}})
    assert all(c in cfg['everywhere'] for c in L.SANCTIONED)
    assert cfg['minAge'] == 18 and cfg['features']['swap']['blocked'] == ['US'] and 'fake' not in cfg['features']


def test_export_scrubs_secrets():
    b = L.export_bundle(ME, {'push': [{'prefs': {'address': ME, 'session': 'tok'}, 'subscription': {'endpoint': 'https://p', 'keys': {'p256dh': 'x'}}}],
                             'brokers': {'uid': 'u', 'sec': 'sealed'}, 'empty': []})
    txt = json.dumps(b)
    assert 'tok' not in txt and 'sealed' not in txt and 'p256dh' not in txt and 'https://p' not in txt
    assert 'empty' not in b['data'] and set(b['onDelete']['removed']) == set(L.DELETE)


def test_country_header_only_from_a_cdn():
    assert L.country_of({'cf-ipcountry': 'gb'}) == 'GB'
    assert L.country_of({'cf-ipcountry': 'XX'}) is None and L.country_of({'cf-ipcountry': 'T1'}) is None
    assert L.country_of({}) is None


def test_service_accept_export_delete_end_to_end(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(rs, '_legal_state', None)
    monkeypatch.setattr(rs, 'session_address', lambda t: {'mine': ME, 'theirs': OTHER}.get(t))
    c = TestClient(rs.app)

    def sandboxed():   # this test writes stores: prove every one is the conftest sandbox, never backend/data
        for P in (rs.LEGAL_PATH, rs.SESSIONS_PATH, rs.CHAT_PATH, rs.DM_PATH, rs.FOLLOW_PATH, rs.NOTIF_PATH, rs.PROFILE_PATH, rs.PUSH_PATH, rs.IDENTITY_PATH):
            assert Path(P).resolve().parent != (Path(rs.__file__).resolve().parent / 'data'), P
    sandboxed()

    st = c.get(f'/api/reputation/legal/status?wallet={ME}').json()
    assert st['version'] == L.VERSION and not st['accepted'] and not st['gates']['swap']['ok'] and st['gates']['site']['ok']
    body = {'wallet': ME, 'session': 'mine', 'version': L.VERSION, 'country': 'US', 'adult': True, 'notRestricted': True}
    assert c.post('/api/reputation/legal/accept', json={**body, 'session': 'theirs'}).status_code == 401      # someone else's session
    assert c.post('/api/reputation/legal/accept', json={**body, 'adult': False}).status_code == 400
    assert c.post('/api/reputation/legal/accept', json=body).json()['ok']
    st = c.get(f'/api/reputation/legal/status?wallet={ME}').json()
    assert st['accepted'] and st['gates']['swap']['ok'] and st['stated'] is None                       # country private without a session
    assert c.get(f'/api/reputation/legal/status?wallet={ME}', headers={'x-feeless-session': 'mine'}).json()['stated'] == 'US'

    # the wallet's personal rows, spread over the stores
    rs._prof().put(ME, {'displayName': 'me'})
    rs._json_save(rs.FOLLOW_PATH, {'following': {ME: [OTHER], OTHER: [ME]}})
    rs._notif().put(ME, [{'id': 'n1', 'text': 'hi'}]); rs._notif().put(OTHER, [{'id': 'n2'}])
    rs._json_save(rs.DM_PATH, {rs._dm_key(ME, OTHER): [{'from': ME, 'to': OTHER, 'text': 'mine'}, {'from': OTHER, 'to': ME, 'text': 'theirs'}]})
    rs.CHAT_PATH.write_text(json.dumps({'rooms': {'lobby': [{'identity': ME, 'address': ME, 'text': 'x'}, {'identity': OTHER, 'address': OTHER, 'text': 'y'}]}, 'lastTs': {}}))
    rs._json_save(rs.SESSIONS_PATH, {'s': {'h1': {'address': ME, 'exp': 9e12}, 'h2': {'address': OTHER, 'exp': 9e12}}})

    ex = c.post('/api/reputation/legal/export', json={'wallet': ME, 'session': 'mine'}).json()
    assert ex['data']['profile']['displayName'] == 'me' and ex['data']['follows'] == [OTHER]
    assert len(ex['data']['dms']) == 2 and len(ex['data']['chat']) == 1 and ex['data']['consent']['country'] == 'US'
    assert 'h1' not in json.dumps(ex)                                                                   # no session hashes

    assert c.post('/api/reputation/legal/delete', json={'wallet': ME, 'session': 'mine'}).status_code == 400   # must type DELETE
    import hashlib
    import time
    with monkeypatch.context() as m:   # ⚠ never monkeypatch.undo(): it would also undo conftest's data sandbox
        m.setattr(rs, '_sess', lambda: {'s': {hashlib.sha256(b'mine').hexdigest(): {'address': ME, 'exp': 0}}})
        assert c.post('/api/reputation/legal/delete', json={'wallet': ME, 'session': 'mine', 'confirm': 'DELETE'}).status_code == 401   # stale sign-in
    sandboxed()
    d = rs._sess(); d['s'][hashlib.sha256(b'mine').hexdigest()] = {'address': ME, 'exp': time.time() + rs.SESSION_TTL}; rs._json_save(rs.SESSIONS_PATH, d)
    out = c.post('/api/reputation/legal/delete', json={'wallet': ME, 'session': 'mine', 'confirm': 'DELETE'}).json()
    assert out['ok'] and out['removed']['profile'] == 1 and out['removed']['dms'] == 1 and out['removed']['chat'] == 1 and 'consent' in out['kept']
    assert rs._prof().get(ME) is None and ME not in rs._fol()['following'] and OTHER in rs._fol()['following']
    assert [m['text'] for m in rs._json_load(rs.DM_PATH, {})[rs._dm_key(ME, OTHER)]] == ['theirs']              # their side stays
    assert [m['text'] for m in rs._chat_load()['rooms']['lobby']] == ['y']
    assert set(rs._sess()['s']) == {'h2'}                                                                       # signed out everywhere
    assert rs._legal_s()['accept'][ME]['country'] == 'US'                                                       # proof of consent kept
    assert [r['kind'] for r in rs._legal_s()['requests']] == ['export', 'delete']

    assert c.get('/api/reputation/admin/legal').status_code in (401, 403)                                      # owner only


def test_no_test_undoes_the_whole_monkeypatch():
    """monkeypatch.undo() also undoes conftest's sandbox → the rest of that test writes the owner's real backend/data (2026-11-13)."""
    stmt = re.compile(r'^\s*monkeypatch\.undo\(\)', re.M)   # the statement, not a comment or this string
    hits = [p.name for p in Path(__file__).parent.glob('test_*.py') if stmt.search(p.read_text())]
    assert hits == []
