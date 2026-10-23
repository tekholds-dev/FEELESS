"""👑 The creator styles Fee + finds her wallet (owner, 2026-10-23): only a signed FEELESS owner wallet may set her look; every viewer sees it."""
import hashlib

import pytest


def test_her_look_is_cleaned_and_only_an_owner_wallet_may_set_it():
    fs = pytest.importorskip('feecat_service')
    assert fs.clean_fee_look({'coat': 'Gold', 'pattern': 'spots', 'gear': 'crown', 'eyes': 'laser', 'aura': 'blaze', 'name': '  Fee  the  Don ', 'title': 'Boss <b>of</b> cats'}) == \
        {'coat': 'gold', 'pattern': 'spots', 'gear': 'crown', 'eyes': 'laser', 'aura': 'blaze', 'name': 'Fee the Don', 'title': 'Boss bof/b cats'}
    assert fs.clean_fee_look({'coat': 'x y', 'gear': '<script>', 'name': 'NEXA'}) == {'name': '🔮 FeeCat AI'}   # junk keys dropped · names scrubbed
    assert fs.clean_fee_look(None) == {}
    fee = {'isLeader': True}
    assert fs.fee_owner_real(fee, 'look', 'OWNER', owners=['OWNER']) is True and fs.fee_owner_real(fee, 'look', 'STRANGER', owners=['OWNER']) is False
    assert fs.fee_owner_real({'isLeader': False}, 'look', 'OWNER', owners=['OWNER']) is False


def test_the_look_action_dresses_fee_for_the_creator_only(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'leader': {'id': 'leader', 'name': 'FeeCat', 'isLeader': True, 'ownerId': 'system', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    monkeypatch.setenv('FEELESS_ADMIN_WALLETS', 'OWNERW')
    sess = {hashlib.sha256(t.encode()).hexdigest(): {'address': a, 'exp': 9e18} for t, a in (('tok-o', 'OWNERW'), ('tok-x', 'STRANGER'))}
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': sess})
    c = TestClient(fs.app)
    look = {'coat': 'gold', 'gear': 'crown', 'eyes': 'laser', 'aura': 'blaze', 'name': 'Fee the Don'}
    assert c.post('/api/cats/leader/action', json={'action': 'look', 'look': look}).status_code in (401, 403)                       # nobody signed
    assert c.post('/api/cats/leader/action', json={'action': 'look', 'look': look, 'session': 'tok-x', 'address': 'STRANGER'}).status_code in (401, 403)
    r = c.post('/api/cats/leader/action', json={'action': 'look', 'look': look, 'session': 'tok-o', 'address': 'OWNERW'})
    assert r.status_code == 200 and r.json()['cat']['look']['gear'] == 'crown' and store['cats']['leader']['name'] == 'Fee the Don'
