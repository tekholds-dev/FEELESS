"""⚙ owner 2026-11-21: every control in the desk settings panel works — the panel's $ cap and Browse / Forms switches are what the NEXT task
really runs with (fc_work._work_start), and a blocked tool is refused by the engine (cat_agent: test_feecat_priority covers the refusal)."""
import asyncio
import pytest


def test_panel_cap_and_tools_reach_the_next_task(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'g1': {'id': 'g1', 'name': 'Gen', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0,
                             'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 5.0, 'billing': 'payg'}}}, 'events': []}
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))   # a test session IS its wallet (test_cat_agent)
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    c = TestClient(fs.app)
    assert c.post('/api/cats/g1/work', json={'op': 'tools', 'ownerId': 'b1', 'session': 'b1', 'job': 'agent', 'tools': {'browse': False, 'forms': True}}).status_code == 200
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', 'session': 'b1', 'cap': 0.25}).json()['cap'] == 0.25
    cat = store['cats']['g1']; assert cat['tools'] == {'browse': False, 'forms': True}
    started = {}
    async def _noop(*a, **k):
        started['cap'] = a[4]
    monkeypatch.setattr(fs, '_work_run', _noop)
    async def go():
        fs._work_start('g1', cat, 'find the cheapest flight')
        await asyncio.sleep(0)
    asyncio.run(go())
    t = fs._WORK['g1']['task']
    assert t['tools']['browse'] is False and t['tools']['forms'] is True   # the engine reads THIS map: an `open` is refused (cat_agent need → tools)
    assert started['cap'] == pytest.approx(0.25)                           # the task stops at the panel's cap
    fs._WORK.pop('g1', None)
