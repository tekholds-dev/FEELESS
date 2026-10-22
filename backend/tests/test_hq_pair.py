"""📱 Scan to sign in to HQ: one-time code, 3-minute life, verified like a normal sign-in, handed over once (owner, 2026-10-21)."""
import pytest
import hq_pair as hp


def test_code_lifecycle_once_and_expiry():
    st = {}
    c = hp.new_code(st, 100)
    assert hp.take(st, c, 110)['status'] == 'waiting'
    hp.put(st, c, {'address': 'A', 'ts': 100, 'sig': 'S'}, 120)
    with pytest.raises(KeyError, match='already used'):
        hp.put(st, c, {'address': 'B'}, 121)
    assert hp.take(st, c, 130) == {'status': 'signed', 'session': {'address': 'A', 'ts': 100, 'sig': 'S'}}
    assert hp.take(st, c, 131)['status'] == 'expired'                          # handed over once
    d = hp.new_code(st, 200)
    with pytest.raises(KeyError, match='expired'):
        hp.put(st, d, {'address': 'A'}, 200 + hp.TTL + 1)
    for i in range(hp.MAX_OPEN + 5):
        hp.new_code(st, 300 + i)
    assert len(st) == hp.MAX_OPEN and len(c) >= 24


def test_routes_verify_the_signature_like_a_normal_sign_in(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    c = TestClient(rs.app)
    code = c.post('/api/reputation/hq/pair').json()['code']
    monkeypatch.setattr(rs, '_admin_wallets', lambda: {'OWNER'})
    monkeypatch.setattr(rs, '_verify_wallet', lambda a, m, s: s == 'good' and m.startswith('FEELESS HQ'))
    now = int(rs.time.time())
    assert c.post(f'/api/reputation/hq/pair/{code}', json={'address': 'STRANGER', 'ts': now, 'sig': 'good'}).status_code == 403
    assert c.post(f'/api/reputation/hq/pair/{code}', json={'address': 'OWNER', 'ts': now, 'sig': 'bad'}).status_code == 401
    assert c.get(f'/api/reputation/hq/pair/{code}').json()['status'] == 'waiting'
    assert c.post(f'/api/reputation/hq/pair/{code}', json={'address': 'OWNER', 'ts': now, 'sig': 'good'}).status_code == 200
    assert c.get(f'/api/reputation/hq/pair/{code}').json()['session']['address'] == 'OWNER'
    assert c.get(f'/api/reputation/hq/pair/{code}').json()['status'] == 'expired'
