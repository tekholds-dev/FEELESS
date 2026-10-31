"""🧭 GENERAL AI CAT orders (owner, 2026-10-23): plain words → one guarded proposal your wallet signs (paper = a paper fill). Network faked."""
import time

from fastapi.testclient import TestClient

import cat_orders as co
import launch_cat as lc
import pytest

@pytest.fixture(autouse=True)
def _signed_owner(monkeypatch):
    """A test session token IS its wallet here; the wallet owner lock itself is proven in test_agent_owner_lock.py."""
    import feecat_service as svc
    monkeypatch.setattr(svc, '_session_wallet', lambda s: str(s or ''))

ROW = {'id': 'openai/gpt-oss-20b', 'name': 'gpt-oss-20b', 'context_length': 131072, 'pricing': {'prompt': '0.00000002', 'completion': '0.00000009'}}
MINT = 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'


def test_words_become_orders():
    assert co.parse_order('buy 0.05 SOL of $BONK') == {'side': 'buy', 'coin': 'BONK', 'sol': 0.05}
    assert co.parse_order('ape 0.1 sol into JUP please') == {'side': 'buy', 'coin': 'JUP', 'sol': 0.1}
    assert co.parse_order(f'buy {MINT} for 0.2 SOL') == {'side': 'buy', 'coin': MINT, 'sol': 0.2}
    assert co.parse_order('sell half of $WIF') == {'side': 'sell', 'coin': 'WIF', 'fraction': 0.5}
    assert co.parse_order('sell all BONK') == {'side': 'sell', 'coin': 'BONK', 'fraction': 1.0}
    assert co.parse_order('sell 25% of POPCAT') == {'side': 'sell', 'coin': 'POPCAT', 'fraction': 0.25}
    assert co.parse_order('trim my WIF') == {'side': 'sell', 'coin': 'WIF', 'fraction': 0.5}
    for t in ('what do you think of the market?', 'sell it', 'buy some bonk', '', None):
        assert co.parse_order(t) is None, t                                              # the brain is asked, never a guess
    assert co.order_from_json('ok {"side":"buy","coin":"$JUP","sol":0.03}') == {'side': 'buy', 'coin': 'JUP', 'sol': 0.03}
    assert co.order_from_json('{"side":"sell","coin":"WIF","fraction":0.3}') == {'side': 'sell', 'coin': 'WIF', 'fraction': 0.3}
    assert co.order_from_json('{"side":"none"}') is None and co.order_from_json('{"side":"buy","coin":"JUP"}') is None and co.order_from_json('nope') is None


def _p(sym='BONK', liq=90_000, age_min=600, h1=12.0, chain='solana', addr=MINT, pair='PAIR1'):
    return {'chainId': chain, 'pairAddress': pair, 'baseToken': {'symbol': sym, 'address': addr}, 'liquidity': {'usd': liq}, 'priceNative': '0.00002',
            'priceUsd': '0.003', 'marketCap': 2e8, 'volume': {'h1': 1e5}, 'priceChange': {'h1': h1}, 'pairCreatedAt': (time.time() - age_min * 60) * 1000}


def test_deepest_pool_and_the_new_door_guards():
    pairs = [_p(liq=10_000, pair='A'), _p(liq=900_000, pair='B'), _p(liq=5e6, chain='bsc', pair='C'), _p(sym='BONKO', liq=9e6, pair='D', addr='OtherMint1111111111111111111111111111111')]
    assert co.best_pair(pairs, '$bonk')['pairAddress'] == 'B' and co.best_pair(pairs, MINT.lower())['pairAddress'] == 'B'
    assert co.best_pair(pairs, 'NOPE') is None
    now = time.time() * 1000
    assert co.buy_guards(_p(), now) == (True, '')
    assert co.buy_guards(None, now)[1].startswith('🔎')
    assert co.buy_guards(_p(liq=3_000), now)[1].startswith('💧 pool $3,000')
    assert co.buy_guards(_p(age_min=4), now)[1].startswith('🐣 4 min old')
    assert co.buy_guards(_p(h1=450), now)[1].startswith('🚀 +450% in 1h')
    assert co.size_of({'sol': 2}, 0.25, 0.1) == (0.1, ' (capped from 2 SOL)') and co.size_of({'sol': 0.05}, 0.25) == (0.05, '')
    assert co.size_of({'sol': 50}, None) == (co.SOL_MAX, ' (capped from 50 SOL)')


def _svc(tmp_path, monkeypatch, pair):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog([ROW])})
    monkeypatch.delenv('LAUNCH_CAT_LIVE', raising=False)

    async def op(http, coin):
        return pair if coin.lstrip('$').upper() == 'BONK' else None

    async def safe(http, p):
        return (p.get('_rug') is None, p.get('_rug') or 'holders spread', 1.0)

    async def prices(http, pas):
        return {pa: {'priceNative': '0.00003', 'marketCap': 3e8} for pa in pas}
    monkeypatch.setattr(fs, '_order_pair', op)
    monkeypatch.setattr(fs, '_safety', safe)
    monkeypatch.setattr(fs, '_pair_prices', prices)
    monkeypatch.setattr(fs, '_post_as_fee', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_notify_real', lambda *a, **k: None)
    return fs, TestClient(fs.app)


def _cat(c, kind):
    r = c.post('/api/cats', json={'ownerId': 'w', "session": 'w', 'name': 'Doer', 'handle': f'doer-{kind}', 'brains': ['openai/gpt-oss-20b'], 'brainKind': kind, 'maxPositionSol': 0.2})
    assert r.status_code == 200, r.text
    return r.json()['cat']


def test_a_general_cat_fills_your_order_on_paper_and_refuses_what_the_guards_stop(tmp_path, monkeypatch):
    pair = _p()
    fs, c = _svc(tmp_path, monkeypatch, pair)
    cat = _cat(c, 'general')
    assert cat['brainsCfg']['kind'] == 'general'
    go = lambda t: c.post(f"/api/cats/{cat['id']}/action", json={'ownerId': 'w', "session": 'w', 'action': 'order', 'text': t})
    out = go('buy 0.05 SOL of $BONK').json()['cat']
    assert out['orders'][-1]['state'] == 'filled' and out['positions'][0]['symbol'] == 'BONK' and out['positions'][0]['order'] is True
    assert go('buy 0.05 SOL of $NOPE').json()['cat']['orders'][-1]['why'].startswith('🔎')
    pair['_rug'] = 'mint or freeze authority is still live'
    assert go('buy 0.05 SOL of $BONK').json()['cat']['orders'][-1]['why'] == '🛡 mint or freeze authority is still live'
    pair.pop('_rug')
    out = go('sell half of $BONK').json()['cat']
    assert out['orders'][-1]['state'] == 'filled' and abs(out['positions'][0]['notionalSol'] - 0.02475) < 1e-6
    assert go('what is up?').json()['cat']['orders'][-1]['state'] == 'unclear'               # calls off + no words = nothing traded
    assert go('sell all $WIF').json()['cat']['orders'][-1]['why'] == '🫥 it holds no $WIF'
    assert go('').status_code == 400
    trader = _cat(c, 'trading')
    assert c.post(f"/api/cats/{trader['id']}/action", json={'ownerId': 'w', "session": 'w', 'action': 'order', 'text': 'buy 0.05 SOL of $BONK'}).status_code == 400


def test_a_real_general_cat_turns_your_order_into_a_proposal_your_wallet_signs(tmp_path, monkeypatch):
    fs, c = _svc(tmp_path, monkeypatch, _p())
    cat = _cat(c, 'general')
    store = fs._load(); fs._real.go_real(store['cats'][cat['id']], 'WALLET1', 0.1, time.time()); fs._save(store)
    out = c.post(f"/api/cats/{cat['id']}/action", json={'ownerId': 'w', "session": 'w', 'action': 'order', 'text': 'buy 2 SOL of $BONK'}).json()['cat']
    row, prop = out['orders'][-1], out['proposals'][0]
    assert row['state'] == 'proposed' and 'capped from 2 SOL' in row['why'] and prop['side'] == 'buy' and prop['sol'] == 0.1 and prop['status'] == 'pending'
    assert not out['positions']                                                               # nothing bought until YOUR wallet signs


def test_a_general_cat_never_hunts_on_its_own():
    import inspect
    import feecat_service as fs
    src = inspect.getsource(fs.run_engine)
    assert "get('kind') == 'general'" in src and src.index("get('kind') == 'general'") < src.index('for score, reason, p in ranked')
    assert lc.clean({'brains': ['a/b'], 'brainKind': 'general'})['kind'] == 'general' and lc.clean({'brains': ['a/b']})['kind'] == 'trading'
    assert lc.clean({'brains': ['a/b'], 'brainKind': 'trading'}, prev={'kind': 'general'})['kind'] == 'general'   # set once
