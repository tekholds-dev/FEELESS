"""⚡ Earn Mode's planner: open gaps that beat their costs, then compounding, then the busiest bands — filtered by the owner's risk, ranked by
$/day on their budget. It never signs. Pure + one owner-gated endpoint (faked feeds)."""
import hashlib

import pytest

GAPS = {'gaps': [{'sym': 'SOL', 'open': True, 'netPct': 0.4, 'lo': {'dex': 'orca', 'liq': 3e6}, 'hi': {'dex': 'meteora'}},
                 {'sym': 'JUP', 'open': True, 'netPct': -0.1, 'lo': {'dex': 'orca', 'liq': 3e6}, 'hi': {'dex': 'ray'}},
                 {'sym': 'BONK', 'open': False, 'netPct': 2.0, 'lo': {'liq': 3e6}, 'hi': {}}]}
VAULT = {'strategies': [{'key': 'lst', 'name': 'STAKE', 'top': 'JITOSOL', 'apy': 7.0}, {'key': 'loop', 'name': 'LOOP', 'top': 'X', 'apy': 40.0}]}
POOLS = {'pools': [{'sym': 'SOL-USDC', 'proto': 'orca', 'kind': 'v3', 'apy': 30.0, 'tvl': 2e7, 'il': True, 'tier': 'mid'},
                   {'sym': 'MEME-SOL', 'proto': 'ray', 'kind': 'v2', 'apy': 400.0, 'tvl': 3e5, 'il': True, 'tier': 'risky'},
                   {'sym': 'USDC lend', 'proto': 'kamino', 'kind': 'lend', 'apy': 9.0, 'tvl': 9e7, 'tier': 'safe'}]}


def test_safe_keeps_only_safe_plays_and_only_gaps_that_beat_costs():
    em = pytest.importorskip('earn_mode')
    p = em.plays(GAPS, VAULT, POOLS, 'safe', 100)
    assert [x['kind'] for x in p] == ['gap', 'vault'] and p[0]['title'].startswith('SOL') and p[0]['dayUsd'] == 0.4
    assert all(x['tier'] == 'safe' for x in p)


def test_risky_adds_the_bands_ranked_by_dollars_a_day():
    em = pytest.importorskip('earn_mode')
    p = em.plays(GAPS, VAULT, POOLS, 'risky', 100)
    assert p[0]['title'].startswith('MEME-SOL') and p[0]['tab'] == 'pools' and {'range', 'vault', 'gap'} <= {x['kind'] for x in p}
    assert [x['dayUsd'] for x in p] == sorted([x['dayUsd'] for x in p], reverse=True)


def test_clean_and_the_owner_only_plan(monkeypatch):
    em = pytest.importorskip('earn_mode')
    assert em.clean({'on': 1, 'risk': 'yolo', 'budgetUsd': -5}) == {'on': True, 'risk': 'safe', 'budgetUsd': 1.0}
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    cat = {'id': 'g', 'ownerId': 'b1', 'ownerWallet': 'W', 'name': 'Happy', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'createdAt': 1,
           'brainsCfg': {'kind': 'general', 'brains': ['m/a']}}
    store = {'cats': {'g': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {hashlib.sha256(b'tok').hexdigest(): {'address': 'W', 'exp': 9e18}}})

    class R:
        def __init__(self, j):
            self.status_code, self._j = 200, j

        def json(self):
            return self._j

    class H:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return R(GAPS if url.endswith('/gaps') else VAULT if url.endswith('/sleep') else POOLS)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda *a, **k: H())
    c = TestClient(fs.app)
    assert c.get('/api/cats/g/earn').status_code == 401
    assert c.post('/api/cats/g/action', json={'action': 'earn', 'session': 'tok', 'earn': {'on': True, 'risk': 'mid', 'budgetUsd': 50}}).status_code == 200
    j = c.get('/api/cats/g/earn?session=tok').json()
    assert j['earn'] == {'on': True, 'risk': 'mid', 'budgetUsd': 50.0} and j['gapsOpen'] == 2 and {x['tier'] for x in j['plays']} <= {'safe', 'mid'}
