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


def test_phantom_deeplink_round_trip_connect_then_sign():
    """The whole Phantom deeplink flow with a fake Phantom: connect (encrypted to the code's key) → sign-message deeplink → signature back."""
    import json
    from urllib.parse import parse_qs, urlparse, unquote
    import base58
    from nacl.public import Box, PrivateKey, PublicKey
    from nacl.signing import SigningKey
    import hq_auth
    st = {}; code = hp.new_code(st, 1000); site = 'http://10.0.0.5:51367'
    q = parse_qs(urlparse(hp.connect_link(st, code, site, 1000)).query)
    assert unquote(q['redirect_link'][0]) == f'{site}/hq-link?c={code}&s=connect'
    dapp_pub = PublicKey(base58.b58decode(q['dapp_encryption_public_key'][0]))
    phantom = PrivateKey.generate(); wallet = SigningKey.generate(); addr = base58.b58encode(bytes(wallet.verify_key)).decode()
    box = Box(phantom, dapp_pub); n = b'\x01' * 24
    data = box.encrypt(json.dumps({'public_key': addr, 'session': 'S1'}).encode(), n).ciphertext
    out = hp.on_connect(st, code, site, base58.b58encode(bytes(phantom.public_key)).decode(), base58.b58encode(n).decode(), base58.b58encode(data).decode(), 1001, ts=1001)
    assert out['address'] == addr and out['link'].startswith('https://phantom.app/ul/v1/signMessage?')
    sq = parse_qs(urlparse(out['link']).query)
    asked = json.loads(box.decrypt(base58.b58decode(sq['payload'][0]), base58.b58decode(sq['nonce'][0])))
    msg = base58.b58decode(asked['message']).decode()
    assert msg == f'FEELESS HQ\naddress:{addr}\nts:1001' and asked['session'] == 'S1'
    sig = base58.b58encode(wallet.sign(msg.encode()).signature).decode(); n2 = b'\x02' * 24
    back = box.encrypt(json.dumps({'signature': sig}).encode(), n2).ciphertext
    a, ts, got = hp.on_signed(st, code, base58.b58encode(n2).decode(), base58.b58encode(back).decode(), 1002)
    assert (a, ts) == (addr, 1001) and hq_auth.verify_solana(a, msg, got)                     # HQ's own check accepts Phantom's base58 signature
