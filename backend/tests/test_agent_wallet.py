"""👛 Agent wallets (Crossmint): one wallet per cat / family, no key stored, trading rides / general switches / family approves — network faked."""
import asyncio
import hashlib

import pytest

import agent_wallet as aw

ADDR = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'


class FakeHttp:
    def __init__(self, code=201, body=None):
        self.code, self.body, self.calls = code, body if body is not None else {'address': ADDR, 'locator': 'userId:feeless-cat-c1:solana:smart'}, []

    async def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(('POST', url, headers, json)); return _R(self.code, self.body)

    async def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(('GET', url, headers, params)); return _R(self.code, self.body)


class _R:
    def __init__(self, code, body):
        self.status_code, self._b = code, body
        self.text = str(body)

    def json(self):
        return self._b


def test_env_owner_and_modes():
    assert aw.env_of('sk_production_x') == 'production' and aw.env_of('sk_staging_x') == 'staging' and aw.env_of('') is None
    assert aw.owner_of('cat', 'c1') == 'userId:feeless-cat-c1'
    with pytest.raises(ValueError):
        aw.owner_of('cat', 'bad id!')
    assert aw.default_mode('cat', 'trading') == 'auto' and aw.default_mode('cat', 'general') == 'approve' and aw.default_mode('family') == 'approve'
    g = aw.record('cat', 'c1', {'address': ADDR}, 'OWNER', 10.0, 'general')
    assert g['mode'] == 'approve' and 'key' not in str(g).lower() and aw.set_mode(g, 'auto', 'general')['mode'] == 'auto'
    with pytest.raises(ValueError):
        aw.set_mode(aw.record('cat', 'c2', {'address': ADDR}, 'O', 1, 'trading'), 'approve', 'trading')   # a trading cat rides
    with pytest.raises(ValueError):
        aw.set_mode(aw.record('family', 'f1', {'address': ADDR}, 'O', 1), 'auto')                         # a family never goes auto
    with pytest.raises(ValueError):
        aw.record('cat', 'c1', {'address': 'nope'}, 'O', 1)


def test_create_posts_one_idempotent_smart_wallet_and_balances_read_sol_usdc():
    h = FakeHttp()
    rep = asyncio.run(aw.create(h, 'sk_production_k', 'cat', 'c1'))
    m, url, hdr, body = h.calls[0]
    assert m == 'POST' and url == aw.API['production'] + '/wallets' and hdr['X-API-KEY'] == 'sk_production_k'
    assert body == {'chainType': 'solana', 'type': 'smart', 'owner': 'userId:feeless-cat-c1', 'config': {'adminSigner': {'type': 'api-key'}}} and rep['address'] == ADDR
    with pytest.raises(ValueError, match='scope'):
        asyncio.run(aw.create(FakeHttp(403, {'message': 'missing scope wallets.create'}), 'sk_staging_k', 'cat', 'c1'))
    with pytest.raises(ValueError, match='CROSSMINT_API_KEY'):
        asyncio.run(aw.create(FakeHttp(), '', 'cat', 'c1'))
    b = asyncio.run(aw.balances(FakeHttp(200, [{'symbol': 'sol', 'amount': '0.25'}, {'symbol': 'usdc', 'amount': '3.5'}]), 'sk_staging_k', ADDR))
    assert b == {'sol': 0.25, 'usdc': 3.5}


def test_the_cat_service_makes_one_wallet_for_its_signed_owner_and_the_switch_follows_the_cat_kind(monkeypatch):
    monkeypatch.setenv('CIRCLE_AGENT_API_KEY', '')   # this test is the Crossmint path
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'g1': {'id': 'g1', 'name': 'Gen', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 1.0, 'brainsCfg': {'kind': 'general'}},
                      't1': {'id': 't1', 'name': 'Trd', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 1.0, 'brainsCfg': {'kind': 'trading'}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    tok = 'tok-1'
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(tok.encode()).hexdigest(): {'address': 'WALLET', 'exp': 9e18}}})
    made = []

    async def fake_create(http, key, kind, ref):
        made.append((kind, ref)); return {'address': ADDR}
    monkeypatch.setattr(fs._aw, 'create', fake_create)
    c = TestClient(fs.app)
    base = {'ownerId': 'b1', 'address': 'WALLET', 'session': tok}
    assert c.post('/api/cats/g1/action', json={'action': 'agent_wallet', 'ownerId': 'b1', 'address': 'WALLET'}).status_code == 401   # unsigned
    assert c.post('/api/cats/g1/action', json={**base, 'action': 'agent_wallet', 'ownerId': 'b2'}).status_code == 403              # not the owner
    assert c.post('/api/cats/g1/action', json={**base, 'action': 'agent_wallet'}).status_code == 200
    assert c.post('/api/cats/g1/action', json={**base, 'action': 'agent_wallet'}).status_code == 200 and made == [('cat', 'g1')]   # one wallet, ever
    w = store['cats']['g1']['agentWallet']
    assert w['address'] == ADDR and w['owner'] == 'WALLET' and w['mode'] == 'approve'
    assert c.post('/api/cats/g1/action', json={**base, 'action': 'agent_mode', 'mode': 'auto'}).status_code == 200 and store['cats']['g1']['agentWallet']['mode'] == 'auto'
    c.post('/api/cats/t1/action', json={**base, 'action': 'agent_wallet'})
    assert store['cats']['t1']['agentWallet']['mode'] == 'auto'
    assert c.post('/api/cats/t1/action', json={**base, 'action': 'agent_mode', 'mode': 'approve'}).status_code == 400              # a trading cat rides


def test_n16_fee_takes_an_assigned_wallet_crossmint_trades_anything_else_is_watch_only(monkeypatch):
    import agent_trade as at
    h = FakeHttp(200, {'address': ADDR, 'locator': 'email:x:solana:smart'})
    assert asyncio.run(aw.lookup(h, 'sk_production_k', ADDR))['address'] == ADDR and h.calls[0][1].endswith(f'/wallets/{ADDR}')
    assert asyncio.run(aw.lookup(FakeHttp(404, {'message': 'not found'}), 'sk_production_k', ADDR)) is None
    with pytest.raises(ValueError):
        asyncio.run(aw.lookup(FakeHttp(500, {'message': 'down'}), 'sk_production_k', ADDR))
    cm, watch = aw.assigned(ADDR, {'locator': 'L'}, 'OWNER', 1), aw.assigned(ADDR, None, 'OWNER', 1)
    assert cm['provider'] == 'crossmint' and cm['assigned'] and watch['provider'] == 'watch' and 'key' not in str(watch).lower()
    cat = {'agentWallet': watch, 'proposals': [{'id': 'p', 'status': 'pending', 'until': 9e9, 'side': 'buy'}]}
    assert not at.wants(cat, cat['proposals'][0], 1.0) and asyncio.run(at.run(FakeHttp(), 'sk_production_k', cat, 1.0)) == []   # never traded from
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'leader': {'id': 'leader', 'name': 'Fee', 'isLeader': True, 'ownerId': 'system', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'balanceSol': 1.0},
                      'u1': {'id': 'u1', 'name': 'Mine', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 1.0}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    sess = {'own': 'OWNERWALLET', 'usr': 'USERWALLET'}
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(k.encode()).hexdigest(): {'address': v, 'exp': 9e18} for k, v in sess.items()}})
    monkeypatch.setattr(fs, 'owner_wallets', lambda: ['OWNERWALLET'])

    async def fake_lookup(http, key, a):
        return {'locator': 'L'} if a == ADDR else None
    monkeypatch.setattr(fs._aw, 'lookup', fake_lookup)
    c = TestClient(fs.app)
    assert c.post('/api/cats/leader/action', json={'action': 'agent_assign', 'address': 'USERWALLET', 'session': 'usr', 'text': ADDR}).status_code == 403   # not the creator
    assert c.post('/api/cats/leader/action', json={'action': 'agent_assign', 'address': 'OWNERWALLET', 'session': 'own', 'text': ADDR}).status_code == 200
    assert store['cats']['leader']['agentWallet']['provider'] == 'crossmint' and store['cats']['leader']['agentWallet']['owner'] == 'OWNERWALLET'
    other = '9mbBeav7E52pxfED9h6AHBymggfvj119DyNGC1qqSkMj'
    assert c.post('/api/cats/leader/action', json={'action': 'agent_assign', 'address': 'OWNERWALLET', 'session': 'own', 'text': other}).status_code == 200
    assert store['cats']['leader']['agentWallet']['provider'] == 'watch'
    r = c.post('/api/cats/u1/action', json={'action': 'agent_assign', 'ownerId': 'b1', 'address': 'USERWALLET', 'session': 'usr', 'text': ADDR})
    assert r.status_code == 400 and 'Only Fee' in r.json()['detail']                                                                       # a user's cat gets a fresh one


def test_wallet_create_sends_no_idempotency_header_and_says_plainly_when_crossmint_has_it_off():
    import asyncio

    class R:
        def __init__(self, code, body): self.status_code, self._b = code, body
        def json(self): return self._b
        text = ''

    class H:
        def __init__(self, r): self.r, self.hdr = r, None
        async def post(self, _url, headers=None, json=None, timeout=None):
            self.hdr = headers
            return self.r
    ok = H(R(201, {'address': 'A'}))
    assert asyncio.run(aw.create(ok, 'sk_production_k', 'cat', 'c1'))['address'] == 'A' and 'x-idempotency-key' not in ok.hdr   # Crossmint refuses it beside `owner`
    off = H(R(400, {'message': 'Smart wallets with api-key signers are not enabled for this project.'}))
    with pytest.raises(ValueError, match='Nothing was charged'):
        asyncio.run(aw.create(off, 'sk_production_k', 'cat', 'c1'))
