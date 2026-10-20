"""🚀 Launch a Cat wired into the paper engine: brains, budget, chime, pull / top-up (owner, 2026-10-20)."""
import asyncio

from fastapi.testclient import TestClient

import launch_cat as lc

ROW = {'id': 'openai/gpt-oss-20b', 'name': 'gpt-oss-20b', 'context_length': 131072, 'pricing': {'prompt': '0.00000002', 'completion': '0.00000009'}}


def _svc(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog([ROW, {**ROW, 'id': 'qwen/qwen3-4b-2507'}])})
    monkeypatch.delenv('LAUNCH_CAT_LIVE', raising=False)
    return fs, TestClient(fs.app)


def test_launch_with_two_brains_then_chime_pull_and_topup(tmp_path, monkeypatch):
    fs, c = _svc(tmp_path, monkeypatch)
    assert c.get('/api/cats/models').json()['rec'][0]['tag'] == 'OSSY'
    r = c.post('/api/cats', json={'ownerId': 'w', 'name': 'Duo', 'handle': 'duo', 'brains': ['openai/gpt-oss-20b', 'qwen/qwen3-4b-2507'],
                                  'brainMode': 'battle', 'billing': 'payg', 'prompt': 'only buy germ floors'})
    cat = r.json()['cat']
    assert cat['brainsCfg']['promptLocked'] and cat['brainsCfg']['credit'] == lc.START_CREDIT and cat['brainLabel'] == 'gpt-oss-20b + qwen3-4b-2507'
    assert c.post('/api/cats', json={'ownerId': 'w', 'name': 'X', 'handle': 'x', 'brains': ['nope/model']}).status_code == 400
    cid = cat['id']
    assert c.post(f'/api/cats/{cid}/action', json={'action': 'chime', 'text': 'watch the dev wallet'}).json()['cat']['brainsCfg']['chime'][0]['text'] == 'watch the dev wallet'
    assert c.post(f'/api/cats/{cid}/action', json={'action': 'pull'}).json()['cat']['balanceSol'] == 0
    assert c.post(f'/api/cats/{cid}/action', json={'action': 'start'}).status_code == 400
    assert c.post(f'/api/cats/{cid}/action', json={'action': 'topup'}).json()['cat']['needsTopup'] is False
    assert c.post(f'/api/cats/{cid}/action', json={'action': 'start'}).json()['cat']['status'] == 'running'


def test_calls_off_means_rule_engine_and_no_charge_on_means_charged_and_paused_at_zero(tmp_path, monkeypatch):
    fs, _ = _svc(tmp_path, monkeypatch)
    store = {'events': [], 'cats': {}}
    cat = {'id': 'a', 'name': 'A', 'status': 'running', 'brainsCfg': lc.clean({'brains': ['openai/gpt-oss-20b'], 'billing': 'payg'})}
    assert asyncio.run(fs._brain_decide(store, cat, 'buy', 'AAA', 'case')) is None
    assert cat['brainsCfg']['decisions'][-1]['word'] == 'RULES' and cat['brainsCfg']['spent'] == 0
    monkeypatch.setenv('LAUNCH_CAT_LIVE', '1'); monkeypatch.setenv('OPENROUTER_API_KEY', 'test')
    async def call(model, messages):
        assert 'OWNER SAYS' in messages[1]['content']
        return '{"word": "BUY", "why": "germ floor held"}', 6.0
    monkeypatch.setattr(fs, '_or_call', call)
    assert asyncio.run(fs._brain_decide(store, cat, 'buy', 'AAA', 'case'))[0] == 'BUY'
    assert asyncio.run(fs._brain_decide(store, cat, 'buy', 'BBB', 'case'))[0] == 'BUY'
    assert cat['brainsCfg']['credit'] == 0 and cat['brainsCfg']['owed'] == 2.0
    assert asyncio.run(fs._brain_decide(store, cat, 'buy', 'CCC', 'case')) is None and cat['status'] == 'stopped'
