"""💵 Real-money cats = option A (docs/DECISIONS.md #2): the cat proposes, the user's wallet signs every trade; FEELESS never holds funds."""
import hashlib
import json

import pytest

import cat_real as cr

NOW = 1_800_000_000.0


def _cat():
    return {'id': 'c1', 'name': 'Mittens', 'ownerId': 'browser-1', 'wins': 3, 'losses': 1, 'realizedPnlSol': 0.12}


def test_sessions_read_the_same_store_reputation_signs_into():
    tok = 'secret-token'
    store = {'s': {hashlib.sha256(tok.encode()).hexdigest(): {'address': 'WALLET', 'exp': NOW + 60}}}
    assert cr.session_wallet(store, tok, NOW) == 'WALLET' and cr.session_wallet(store, tok, NOW + 120) is None and cr.session_wallet(store, 'nope', NOW) is None


def test_a_real_cat_proposes_buys_within_budget_and_sells_only_what_you_bought():
    c = _cat()
    with pytest.raises(ValueError):
        cr.go_real(c, 'W', 50)
    cr.go_real(c, 'W', 0.05, NOW)
    assert cr.propose(c, 'sell', 'M1', 'P1', 'AAA', 'stop', NOW, fraction=1) is None           # nothing real behind it yet
    b = cr.propose(c, 'buy', 'M1', 'P1', 'AAA', 'buyers lead', NOW, sol=0.2, px=1e-6)
    assert b['sol'] == 0.05 and b['record'] == {'trades': 4, 'wonPct': 75, 'pnlSol': 0.12} and b['until'] == NOW + cr.PROPOSAL_SEC
    b2 = cr.propose(c, 'buy', 'M1', 'P1', 'AAA', 'again', NOW + 5, sol=0.01)
    assert b['status'] == 'replaced' and b2['sol'] == 0.01
    cr.resolve(c, b2['id'], 'done', NOW + 30, sig='5xSig')
    assert c['realHeld']['M1']['symbol'] == 'AAA'
    s = cr.propose(c, 'sell', 'M1', 'P1', 'AAA', 'first take', NOW + 60, fraction=0.5)
    assert s['fraction'] == 0.5
    with pytest.raises(ValueError, match='already'):
        cr.resolve(c, b2['id'], 'skip', NOW + 61)
    cr.resolve(c, s['id'], 'done', NOW + 90)
    assert 'M1' in c['realHeld']                                                                # half sold: still held
    s2 = cr.propose(c, 'sell', 'M1', 'P1', 'AAA', 'stop', NOW + 120, fraction=1)
    cr.resolve(c, s2['id'], 'done', NOW + 130)
    assert 'M1' not in c['realHeld']


def test_proposals_expire_and_paper_cancels_them():
    c = _cat(); cr.go_real(c, 'W', 0.1, NOW)
    p = cr.propose(c, 'buy', 'M2', 'P2', 'BBB', 'x', NOW)
    with pytest.raises(ValueError, match='expired'):
        cr.resolve(c, p['id'], 'done', NOW + cr.PROPOSAL_SEC + 1)
    q = cr.propose(c, 'buy', 'M3', 'P3', 'CCC', 'y', NOW)
    v = cr.view(c, NOW + 10)
    assert v['pending'] == 1 and v['proposals'][0]['id'] == q['id'] and v['mode'] == 'real'
    cr.go_paper(c)
    assert q['status'] == 'cancelled' and not cr.is_real(c) and cr.propose(c, 'buy', 'M4', 'P4', 'D', 'z', NOW) is None


def test_the_service_guards_every_action_and_real_needs_a_signed_wallet(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'u1': {'id': 'u1', 'name': 'Mine', 'ownerId': 'browser-1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 1.0}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    tok = 'tok-1'
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(tok.encode()).hexdigest(): {'address': 'WALLET', 'exp': 9e18}}})
    sent = []
    monkeypatch.setattr(fs, '_notify_real', lambda cat, p: sent.append(p))
    c = TestClient(fs.app)
    assert c.post('/api/cats/u1/action', json={'action': 'stop'}).status_code == 403                                  # no owner id
    assert c.post('/api/cats/u1/action', json={'action': 'stop', 'ownerId': 'browser-2'}).status_code == 403          # someone else's
    assert c.post('/api/cats/u1/action', json={'action': 'stop', 'ownerId': 'browser-1'}).status_code == 200
    (fs.DATA_DIR / 'internal.key').parent.mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'internal.key').write_text('k')
    assert c.post('/api/cats/u1/action', headers={'x-feeless-internal': 'k'}, json={'action': 'stop'}).status_code == 200   # HQ's run
    assert c.post('/api/cats/u1/action', json={'action': 'real', 'ownerId': 'browser-1', 'address': 'WALLET', 'budgetSol': 0.05}).status_code == 401   # unsigned
    r = c.post('/api/cats/u1/action', json={'action': 'real', 'ownerId': 'browser-1', 'address': 'WALLET', 'session': tok, 'budgetSol': 0.05})
    assert r.status_code == 200 and r.json()['cat']['mode'] == 'real' and r.json()['cat']['realWallet'] == 'WALLET'
    cat = store['cats']['u1']
    p = fs._real.propose(cat, 'buy', 'M1', 'P1', 'AAA', 'x', fs.time.time())
    r = c.post('/api/cats/u1/action', json={'action': 'proposal', 'ownerId': 'browser-1', 'address': 'WALLET', 'session': tok, 'proposal': p['id'], 'result': 'done', 'sig': 'S1'})
    assert r.status_code == 200 and cat['realHeld']['M1'] and p['sig'] == 'S1'
    src = open(fs.__file__).read()
    assert src.count('_real.propose(') == 4                                                                        # the buy + every exit + a General cat's order (sell / buy)
    order = src[src.index('async def _run_order'):src.index('class ActionPayload')]                               # 🧭 the order's buy proposal sits behind every guard
    assert order.index('_co.buy_guards(') < order.index('await _safety(') < order.index("_real.propose(cat, 'buy'")
