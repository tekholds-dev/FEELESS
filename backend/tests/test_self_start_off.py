"""🛑 owner 2026-11-14: Fee has no engine (she trades as a trader agent through the 2 brains he picks), and agents never start model work by
themselves (the hive, scheduled auto runs, Sicario's own loop, the debate grader)."""
import asyncio


def test_fee_has_no_engine():
    import feecat_service as fs
    store = {'cats': {fs.LEADER_ID: {'id': fs.LEADER_ID, 'status': 'running', 'revoked': False},
                      't': {'id': 't', 'status': 'running', 'revoked': False}, 's': {'id': 's', 'status': 'stopped', 'revoked': False}}}
    assert [c['id'] for c in fs._engine_cats(store)] == ['t']


def test_no_self_started_usage(monkeypatch):
    import feecat_service as fs
    assert fs.SELF_START is False
    called = []

    async def boom(*_a, **_k):
        called.append(1); raise AssertionError('a model was called')
    for name in ('_think', '_ws_ask', '_cat_work', '_poc_file'):
        monkeypatch.setattr(fs, name, boom)
    hive_cat = {'id': 'h', 'handle': 'sicarios', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m'], 'debateOn': True}, 'revoked': False}
    monkeypatch.setattr(fs, '_hive_on', lambda c: True)
    assert fs._hive_works(hive_cat) is False and fs._self_start_ok() is False
    store = {'cats': {'h': hive_cat}}
    assert asyncio.run(fs._debate_pass(store)) == 0
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setattr(fs, '_auto_cfg', lambda c, cid: {'on': True, 'kind': 'poc', 'line': 'go'})
    assert asyncio.run(fs._auto_tick(1e9)) == []
    assert asyncio.run(fs._sicario_free(None, store)) is None
    assert not called
