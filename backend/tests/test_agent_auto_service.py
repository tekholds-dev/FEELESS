"""🤖 AGENT-AUTO end to end on fakes: `auto pob` → 3 answers → confirm (config sealed) → the scheduler fires the owner's own chat path →
bounds stop it → the kill-switch stops it. No model, no network, no money."""
import asyncio

import pytest

import feecat_service as fs


@pytest.fixture
def env(monkeypatch, tmp_path):
    cat = {'id': 'a1', 'brainsCfg': {'brains': ['m1', 'm2'], 'kind': 'general'}, 'chat': []}
    store = {'cats': {'a1': cat}}; fired = []
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-key')
    for d in (fs._POW_WANT, fs._POP_WANT, fs._POB_WANT):
        d.pop('a1', None)

    async def work(cat_id, p):
        fired.append((cat_id, p.op, p.text, p.auto, p.session == fs._AUTO_TOKEN)); return {}
    monkeypatch.setattr(fs, '_cat_work', work)
    return store, cat, fired


def _say(cat, line):
    return fs._auto_chat(cat, 'a1', line)


def test_setup_seals_then_fires_then_bounds_then_kill(monkeypatch, env):
    import feecat_service as _fs_ss; monkeypatch.setattr(_fs_ss, 'SELF_START', True)   # the mechanic, dormant since owner 2026-11-14 (self-started usage discontinued)
    store, cat, fired = env
    assert '1 of 3' in _say(cat, 'auto pob') and '2 of 3' in _say(cat, '$0.40') and '3 of 3' in _say(cat, 'every 1h')
    assert 'confirm' in _say(cat, '$1 total, 24h') and 'autoRun' not in cat          # nothing set before confirm
    assert asyncio.run(fs._auto_tick(10 ** 9)) == [] and fired == []                    # and nothing fires
    assert 'is ON' in _say(cat, 'confirm')
    assert cat['autoRun'].startswith('v2:') and 'perUsd' not in cat['autoRun']          # sealed at rest
    now = fs._auto_cfg(cat, 'a1')['since']
    assert asyncio.run(fs._auto_tick(now)) == ['a1'] and fired[-1] == ('a1', 'ask', 'file a pob', True, True)
    assert asyncio.run(fs._auto_tick(now + 60)) == []                                   # waits its hour
    fs._POB_WANT['a1'] = 'start'
    assert asyncio.run(fs._auto_tick(now + 3600)) == []                                 # the last one still running: no second fire
    fs._POB_WANT.pop('a1')
    assert asyncio.run(fs._auto_tick(now + 3600)) == ['a1']
    cfg = fs._auto_cfg(cat, 'a1'); assert cfg['runs'] == 2 and cfg['spentUsd'] == 0.8 and cfg['on'] is False and 'budget' in cfg['stopped']
    assert asyncio.run(fs._auto_tick(now + 99999)) == [] and len(fired) == 2            # a 3rd would cross $1: never fired
    assert 'OFF' in _say(cat, 'auto status')


def test_kill_switch(env):
    store, cat, fired = env
    for line in ('auto pop', '$1', 'every 30m', '10 proofs', 'confirm'):
        _say(cat, line)
    assert fs._auto_cfg(cat, 'a1')['on'] and 'Kill-switch' in _say(cat, 'stop auto')
    assert asyncio.run(fs._auto_tick(10 ** 10)) == [] and fired == [] and 'No auto run is on' in _say(cat, 'kill')


def test_only_the_in_process_token_skips_the_owner_gate(monkeypatch):
    calls = []
    store = {'cats': {'a1': {'id': 'a1'}}}
    monkeypatch.setattr(fs, '_load', lambda: store)

    def gate(*a, **k):
        calls.append(a); raise fs.HTTPException(401, 'sign in')
    monkeypatch.setattr(fs, '_owner_gate', gate)
    p = fs.WorkPayload(op='state', session='forged', auto=True)
    with pytest.raises(fs.HTTPException):
        asyncio.run(fs._cat_work('a1', p))
    assert calls and p.auto is False                                                    # a forged flag is dropped and the gate still runs
