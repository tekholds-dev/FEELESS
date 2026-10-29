"""💵 Fund a cat: $2 one-time to FEELESS out of a ≥ $10 first funding, the rest to the cat's own wallet, in ONE transaction the owner signs —
and only that exact transaction, signed by that owner, is ever sent. Top-ups carry no fee. Up to 4 cats with a wallet per owner."""
import base64
import hashlib

import pytest
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.transaction import VersionedTransaction

import cat_fund as cf

BH = '11111111111111111111111111111111'


def _sign(b64, kp):
    """kp's signature over the built message — a forged copy (wrong key) arrives exactly like this."""
    msg = VersionedTransaction.from_bytes(base64.b64decode(b64)).message
    return base64.b64encode(bytes(VersionedTransaction.populate(msg, [kp.sign_message(to_bytes_versioned(msg))]))).decode()


def test_the_first_funding_pays_2_dollars_once_and_a_top_up_is_all_for_the_cat():
    p = cf.plan(10, 200, True)
    assert p['feeUsd'] == 2 and p['totalLamports'] == 50_000_000 and p['feeLamports'] == 10_000_000 and p['catLamports'] == 40_000_000 and p['catUsd'] == 8
    t = cf.plan(5, 200, False)
    assert t['feeLamports'] == 0 and t['catLamports'] == 25_000_000
    for bad in ((9.99, 200, True), (0.5, 200, False), (10, 0, True), (6000, 200, True)):
        with pytest.raises(ValueError):
            cf.plan(*bad)


def test_one_transaction_two_transfers_and_only_the_exact_one_signed_by_the_owner_passes():
    o, cat, fee, other = Keypair(), Keypair(), Keypair(), Keypair()
    p = cf.plan(10, 200, True)
    b = cf.build(str(o.pubkey()), str(cat.pubkey()), str(fee.pubkey()), p, BH)
    msg = VersionedTransaction.from_bytes(base64.b64decode(b)).message
    assert len(msg.instructions) == 2 and str(msg.account_keys[0]) == str(o.pubkey())
    assert cf.verify(_sign(b, o), b, str(o.pubkey()))
    with pytest.raises(ValueError, match='owner'):
        cf.verify(_sign(b, other), b, str(o.pubkey()))                                         # someone else's signature
    tampered = cf.build(str(o.pubkey()), str(other.pubkey()), str(fee.pubkey()), p, BH)      # same owner, money to another wallet
    with pytest.raises(ValueError, match='not the one FEELESS built'):
        cf.verify(_sign(tampered, o), b, str(o.pubkey()))
    top = cf.build(str(o.pubkey()), str(cat.pubkey()), str(cat.pubkey()), cf.plan(5, 200, False), BH)
    assert len(VersionedTransaction.from_bytes(base64.b64decode(top)).message.instructions) == 1   # a top-up: one transfer, no fee
    with pytest.raises(ValueError):
        cf.build(str(o.pubkey()), str(o.pubkey()), str(fee.pubkey()), p, BH)                    # paying yourself


def test_the_cat_service_records_a_funding_once_and_caps_wallets_at_four_per_owner(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    mk = lambda i, **k: {'id': i, 'name': i, 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0, **k}
    store = {'cats': {**{f'c{i}': mk(f'c{i}', agentWallet={'address': 'A' * 43, 'owner': 'WALLET'}) for i in range(4)}, 'n5': mk('n5')}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    tok = 'tok-1'
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(tok.encode()).hexdigest(): {'address': 'WALLET', 'exp': 9e18}}})
    c = TestClient(fs.app)
    r = c.post('/api/cats/n5/action', json={'action': 'agent_wallet', 'ownerId': 'b1', 'address': 'WALLET', 'session': tok})
    assert r.status_code == 400 and 'Up to 4' in r.json()['detail']
    (fs.DATA_DIR / 'internal.key').parent.mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'internal.key').write_text('k')
    assert c.post('/api/cats/c0/action', json={'action': 'agent_funded', 'sig': 'S1', 'amount': {'usd': 10}}).status_code == 403      # not internal
    ok = c.post('/api/cats/c0/action', headers={'x-feeless-internal': 'k'}, json={'action': 'agent_funded', 'sig': 'S1', 'result': 'confirmed', 'amount': {'usd': 10, 'feeUsd': 2, 'catLamports': 4e7}})
    assert ok.status_code == 200 and store['cats']['c0']['agentFunded'][0]['feeUsd'] == 2
    assert c.post('/api/cats/c0/action', headers={'x-feeless-internal': 'k'}, json={'action': 'agent_funded', 'sig': 'S1', 'amount': {}}).status_code == 400   # once
