"""COL-16: a proof sent WITH funds. Amount + % quoted first, the owner's wallet signs exactly the quote, used once, the agent adds its %
from its own wallet on AUTO, the receipt is filed on the proof. Fake chain + fake Circle; real keypairs sign locally. No network, no funds."""
import asyncio
import base64
import json

import pytest
from solders.keypair import Keypair
from solders.transaction import Transaction

import feecat_service as fs
import proof_funds as pf

POT = '7poJPeupTfM1vd8fKWU694WaQ6sie52mbPTByJCRGpaQ'
AGENT = '2CkRAi2Hb3k4EAUNxTWhwSnY54qasQB7JKRLM1hcczQ7'
BH = '11111111111111111111111111111111'


def test_the_quote_shows_both_amounts_and_the_percent():
    assert pf.quote(0.1, 10, True, 1) == {'userSol': 0.1, 'pct': 10.0, 'agentSol': 0.01, 'totalSol': 0.11, 'auto': True}
    assert pf.quote(0.1, 10, False, 0)['agentSol'] == 0.0
    for args, why in [((0.0001, 10, False, 0), 'at least'), ((0.1, 0, True, 1), 'between 1%'), ((0.005, 10, True, 1), 'under'), ((0.1, 50, True, 0.01), 'can add')]:
        with pytest.raises(ValueError, match=why):
            pf.quote(*args)


def test_only_the_quoted_message_signed_by_the_owner_matches():
    me, other = Keypair(), Keypair()
    q = fs.pot_transfer_tx(str(me.pubkey()), POT, 1000, BH)
    assert pf.signed_matches(_sign(me, q), q, str(me.pubkey()))
    assert not pf.signed_matches(_sign(me, fs.pot_transfer_tx(str(me.pubkey()), POT, 2000, BH)), q, str(me.pubkey()))   # another amount
    assert not pf.signed_matches(q, q, str(me.pubkey()))   # never signed
    assert not pf.signed_matches(_sign(other, fs.pot_transfer_tx(str(other.pubkey()), POT, 1000, BH)), q, str(me.pubkey()))
    assert not pf.signed_matches('junk', q, str(me.pubkey()))


def _desk(monkeypatch, tmp_path, auto=True, agent_sol=0.5):
    me = Keypair(); sent, circled = [], []
    cat = {'id': 'w1', 'ownerWallet': str(me.pubkey()), 'agentWallet': {'address': AGENT, 'circleAcct': 'agent', 'circleId': 'cid'},
           'pocFolders': [{'id': 'c1', 'n': 1, 'topic': 't'}], 'fundGrade': {'auto': auto, 'pct': 20}}
    store = {'cats': {'w1': cat}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: 'OWNER')
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 'shares.json')
    (tmp_path / 'colony.json').write_text(json.dumps({'wallet': {'address': POT}}))

    async def usdc(http, addr):
        return 0.0, agent_sol

    async def rpc(http, m, ps, scan=True):
        if m == 'sendTransaction':
            sent.append(ps[0]); return 'USERSIG'
        return {'value': {'blockhash': BH}}

    async def circle(http, c, rec):
        circled.append(rec); rec['sig'] = 'AGENTSIG'
    monkeypatch.setattr(fs, '_agent_usdc', usdc); monkeypatch.setattr(fs._crpc, '_rpc', rpc); monkeypatch.setattr(fs._at, '_circle_post', circle)
    work = lambda **k: asyncio.run(fs.cat_work('w1', fs.WorkPayload(session='s', **k)))   # noqa: E731
    return me, cat, sent, circled, work


def _sign(kp, b64):
    m = Transaction.from_bytes(base64.b64decode(b64)).message
    return base64.b64encode(bytes(Transaction([kp], m, m.recent_blockhash))).decode()


def test_auto_send_files_both_amounts_on_the_proof_and_a_quote_is_used_once(monkeypatch, tmp_path):
    me, cat, sent, circled, work = _desk(monkeypatch, tmp_path)
    out = work(op='fund_quote', job='c1', cap=0.1)
    q = out['quote']; assert (q['userSol'], q['pct'], q['agentSol'], q['totalSol'], q['to']) == (0.1, 20.0, 0.02, 0.12, POT)
    tx = Transaction.from_bytes(base64.b64decode(out['tx'])); keys = [str(k) for k in tx.message.account_keys]
    assert keys[0] == str(me.pubkey()) and POT in keys and len(tx.message.instructions) == 1
    r = work(op='fund_send', job='c1', text=q['id'], sig=_sign(me, out['tx']))['receipt']
    assert r['userSig'] == 'USERSIG' and r['agentSig'] == 'AGENTSIG' and r['totalSol'] == 0.12 and r['pct'] == 20.0 and len(sent) == 1
    assert circled[0]['key'] == f"feeless-w1-fund-{q['id']}"
    assert [str(k) for k in Transaction.from_bytes(base64.b64decode(circled[0]['tx'])).message.account_keys][0] == AGENT
    assert cat['pocFolders'][0]['funds'] == [r]
    shares = fs._shares()[-2:]; assert [s['by'] for s in shares] == ['owner', 'agent'] and [s['sol'] for s in shares] == [0.1, 0.02]
    with pytest.raises(fs.HTTPException) as e:
        work(op='fund_send', job='c1', text=q['id'], sig=_sign(me, out['tx']))
    assert 'gone' in e.value.detail and len(sent) == 1   # no resubmit


def test_a_tampered_or_late_signature_sends_nothing(monkeypatch, tmp_path):
    me, cat, sent, circled, work = _desk(monkeypatch, tmp_path, auto=False)
    out = work(op='fund_quote', job='c1', cap=0.1); assert out['quote']['agentSol'] == 0.0
    bad = _sign(me, fs.pot_transfer_tx(str(me.pubkey()), POT, 999_999_999, BH))
    with pytest.raises(fs.HTTPException) as e:
        work(op='fund_send', job='c1', text=out['quote']['id'], sig=bad)
    assert 'not the one quoted' in e.value.detail and sent == [] and circled == []
    cat['fundQuote']['exp'] = 1
    with pytest.raises(fs.HTTPException) as e:
        work(op='fund_send', job='c1', text=out['quote']['id'], sig=_sign(me, out['tx']))
    assert 'expired' in e.value.detail and sent == [] and 'funds' not in cat['pocFolders'][0]


def test_auto_needs_room_in_its_wallet_and_cfg_is_bounded(monkeypatch, tmp_path):
    me, cat, sent, circled, work = _desk(monkeypatch, tmp_path, agent_sol=0.011)
    with pytest.raises(fs.HTTPException) as e:
        work(op='fund_quote', job='c1', cap=0.1)
    assert 'can add' in e.value.detail and sent == []
    assert work(op='fund_cfg', tools={'auto': False, 'pct': 500})['fundGrade'] == {'auto': False, 'pct': 100.0}
