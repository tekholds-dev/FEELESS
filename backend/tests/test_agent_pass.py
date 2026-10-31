"""🎫 The Agent Pass: fee = HQ's number or 2× Solana's cost; 10% royalty to FEELESS; a Pass is recorded only after its mint transaction checks
out on-chain (owner signed, fee reached FEELESS, a Core asset, no error). Fakes only — never mainnet."""
import pytest

OWNER, FEE_W, ASSET = 'Own3r' + 'a' * 39, 'FeeW' + 'b' * 40, 'Ass3t' + 'c' * 39


def _tx(fee=40_000, signer=OWNER, err=None, core=True, asset=ASSET):
    ixs = [{'programId': '11111111111111111111111111111111', 'parsed': {'type': 'transfer', 'info': {'source': OWNER, 'destination': FEE_W, 'lamports': fee}}}]
    if core:
        ixs.append({'programId': 'CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d', 'data': 'x'})
    return {'meta': {'err': err}, 'transaction': {'message': {'accountKeys': [{'pubkey': signer, 'signer': True}, {'pubkey': asset, 'signer': True}, {'pubkey': FEE_W, 'signer': False}], 'instructions': ixs}}}


def test_fee_and_metadata():
    ap = pytest.importorskip('agent_pass')
    prov = ap.provider_lamports(3_800_000)
    assert prov == 3_810_000 and ap.fee_lamports(prov) == 7_620_000 and ap.fee_lamports(prov, 5_000_000) == 5_000_000 and ap.ROYALTY_BPS == 1000
    m = ap.metadata('https://feeless.xyz', {'id': 'g', 'name': 'Happy', 'handle': 'happy', 'brainsCfg': {'kind': 'general', 'brains': ['a/x', 'b/y']}}, 7, 'https://feeless.xyz/i.png')
    assert m['name'] == 'FEELESS Agent #0007 · Happy' and m['image'].endswith('i.png') and {'trait_type': 'Minds', 'value': 'x + y'} in m['attributes']


def test_only_a_real_paid_owner_signed_core_mint_counts():
    ap = pytest.importorskip('agent_pass')
    assert ap.check_mint(_tx(), OWNER, FEE_W, 40_000, ASSET) is None
    assert 'not found' in ap.check_mint(None, OWNER, FEE_W, 40_000, ASSET)
    assert 'failed' in ap.check_mint(_tx(err={'x': 1}), OWNER, FEE_W, 40_000, ASSET)
    assert 'owner wallet' in ap.check_mint(_tx(signer='Someone' + 'd' * 37), OWNER, FEE_W, 40_000, ASSET)
    assert 'fee did not reach' in ap.check_mint(_tx(fee=39_999), OWNER, FEE_W, 40_000, ASSET)
    assert 'Core' in ap.check_mint(_tx(core=False), OWNER, FEE_W, 40_000, ASSET)
    assert 'did not create' in ap.check_mint(_tx(asset='Other' + 'e' * 39), OWNER, FEE_W, 40_000, ASSET)


def test_the_agent_records_a_pass_only_from_feeless(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    cat = {'id': 'g', 'ownerId': 'b1', 'ownerWallet': OWNER, 'name': 'Happy', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'createdAt': 1, 'brainsCfg': {'kind': 'general', 'brains': ['m/a']}}
    store = {'cats': {'g': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    (fs.DATA_DIR / 'internal.key').parent.mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'internal.key').write_text('k')
    c = TestClient(fs.app)
    body = {'action': 'pass_minted', 'passInfo': {'number': 7, 'asset': ASSET, 'sig': 'S', 'owner': OWNER}}
    assert c.post('/api/cats/g/action', json=body).status_code in (401, 403)
    assert c.post('/api/cats/g/action', json=body, headers={'x-feeless-internal': 'k'}).status_code == 200
    assert cat['pass']['number'] == 7 and c.get('/api/cats/g').json()['cat']['pass']['asset'] == ASSET   # the public card shows its Pass
