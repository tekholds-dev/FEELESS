"""COL-2: each proof kind may have its own two minds, every proof call files who REALLY answered, and a model switch keeps every other setting."""
import asyncio
import json

import pytest

import launch_cat as lc
import mission


def test_a_kind_uses_its_own_pair_else_the_agents():
    cfg = {'brains': ['a/one', 'b/two'], 'byKind': {'pos': ['c/three', 'd/four']}}
    assert lc.minds_for(cfg, 'pos') == ['c/three', 'd/four']
    assert lc.minds_for(cfg, 'pow') == ['a/one', 'b/two'] and lc.minds_for(cfg, None) == ['a/one', 'b/two']
    assert lc.minds_for(cfg, 'not-a-kind') == ['a/one', 'b/two'] and lc.minds_for(None, 'pos') == []


def test_set_minds_checks_kind_count_and_list_and_clears():
    cfg = {'brains': ['a/one']}
    lc.set_minds(cfg, 'pob', ['c/three', 'c/three', 'd/four'], ids={'c/three', 'd/four'})
    assert cfg['byKind'] == {'pob': ['c/three', 'd/four']}
    with pytest.raises(ValueError):
        lc.set_minds(cfg, 'nope', ['c/three'])
    with pytest.raises(ValueError):
        lc.set_minds(cfg, 'pob', ['c/three', 'd/four', 'e/five'])
    with pytest.raises(ValueError):
        lc.set_minds(cfg, 'pob', ['local/ossy'], ids={'c/three'})   # the owner's own LM Studio is never open to any agent by name alone
    with pytest.raises(ValueError):
        lc.set_minds(cfg, 'pob', ['c/three', 'd/four'], ids={'c/three', 'd/four'}, max_models=1)
    lc.set_minds(cfg, 'pob', [])
    assert cfg['byKind'] == {} and lc.minds_for(cfg, 'pob') == ['a/one']


def test_a_model_switch_keeps_every_other_setting():
    prev = lc.clean({'brains': ['a/one', 'b/two'], 'prompt': 'trade the trenches'})
    prev.update(kitsBy={'pos': {'mode': 'mine', 'picks': ['heroui']}}, daySpend={'2026-11-09': 0.42}, persona='calm', cardSeat=True,
                byKind={'pos': ['c/three', 'gone/model'], 'pow': ['a/one']})
    nxt = lc.clean({'brains': ['b/two']}, prev, ids={'a/one', 'b/two', 'c/three'})
    assert nxt['brains'] == ['b/two'] and nxt['prompt'] == 'trade the trenches'
    assert nxt['kitsBy'] == prev['kitsBy'] and nxt['daySpend'] == {'2026-11-09': 0.42}   # today's spend used to reset on a switch
    assert nxt['persona'] == 'calm' and nxt['cardSeat'] is True
    assert nxt['byKind'] == {'pos': ['c/three'], 'pow': ['a/one']}   # a model no longer on the list drops out of its kind


def test_call_rows_and_attribution():
    calls = [mission.call_row('cat1', 'PoStatic', 'ws1', 0, 'local/ossy', {'route': 'local', 'model': 'qwen3.5-9b', 'tokens': 900}, 'openrouter', 0, 41000, True, 100),
             mission.call_row('cat1', 'pos', 'ws1', 1, 'z-ai/glm', {'route': 'groq free', 'model': 'llama-x', 'tokens': 300}, 'Groq free · llama-x stood in', 0, 2000, True, 101),
             mission.call_row('cat1', 'pos', 'ws1', 1, 'z-ai/glm', {}, '', 0, 9000, False, 102),
             mission.call_row('cat1', 'pos', 'other', 0, 'local/ossy', {'route': 'local', 'model': 'qwen3.5-9b'}, '', 0, 1, True, 103)]
    assert calls[0]['kind'] == 'pos' and calls[0]['local'] is True and calls[2]['route'] is None and calls[2]['ok'] is False
    cat = {'id': 'cat1', 'brainsCfg': {'brains': ['local/ossy', 'z-ai/glm']}}
    e = mission.envelope('pos', {'id': 'p1', 'ws': 'ws1', 'status': 'closed', 'at': 1}, 10 ** 10, cat, calls=calls)
    a, b = e['minds']
    assert a['answeredBy'] == [{'route': 'local', 'model': 'qwen3.5-9b', 'calls': 1}] and a['localCalls'] == 1 and a['apiUsd'] == 0
    assert b['answeredBy'] == [{'route': 'groq free', 'model': 'llama-x', 'calls': 1}] and b['failed'] == 1 and b['calls'] == 2
    assert e['attribution'] == '3 calls recorded' and e['cost']['apiVsLocal'] == {'apiUsd': 0, 'localCalls': 1}


def _rows(fs):
    p = fs.DATA_DIR / 'mind_calls.jsonl'
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_think_files_who_really_answered_only_inside_a_proof(monkeypatch):
    import feecat_service as fs
    async def fake_routes(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        fs._heard(route='lan', model='qwen3.5-4b', tokens=77)
        return 'an answer', 0.0, 'openrouter'   # the router's own label says openrouter: the leaf knows better
    monkeypatch.setattr(fs, '_think_routes', fake_routes)
    before = len(_rows(fs)); cat = {'id': 'catX'}
    asyncio.run(fs._think(cat, 'local/g4', [{'role': 'user', 'content': 'hi'}]))
    assert len(_rows(fs)) == before   # chat and other work outside a proof is not filed
    async def in_proof():
        tok = fs._CALL_CTX.set({'kind': 'pos', 'ref': 'wsZ', 'minds': ['local/ossy', 'local/g4']})
        try:
            return await fs._think(cat, 'local/g4', [{'role': 'user', 'content': 'hi'}])
        finally:
            fs._CALL_CTX.reset(tok)
    assert asyncio.run(in_proof())[0] == 'an answer'
    row = _rows(fs)[-1]
    assert (row['cat'], row['kind'], row['ref'], row['mind'], row['asked']) == ('catX', 'pos', 'wsZ', 1, 'local/g4')
    assert (row['route'], row['model'], row['tokens'], row['via'], row['ok'], row['local']) == ('lan', 'qwen3.5-4b', 77, 'openrouter', True, True)


def test_a_proof_call_uses_its_kinds_minds_and_is_filed(monkeypatch):
    import feecat_service as fs
    asked = []
    async def fake_routes(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        asked.append(model); fs._heard(route='openrouter', model=model + '-0813', tokens=10)
        return 'call', 0.0, 'openrouter'
    monkeypatch.setattr(fs, '_think_routes', fake_routes)
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)
    cat = {'id': 'catY', 'brainsCfg': {'brains': ['a/one', 'b/two'], 'byKind': {'pop': ['c/three', 'd/four'], 'pow': ['e/five']}, 'credit': 5}}
    box = {'cost': 0, 'ref': 'pop123', 'proof': 'pop'}   # how _pop_open hands its box over
    assert asyncio.run(fs._pow2_ask(cat, 1, 'sys', 'user', 50, box)) == 'call'
    assert asked == ['d/four']
    row = _rows(fs)[-1]
    assert (row['kind'], row['ref'], row['mind'], row['asked'], row['model']) == ('pop', 'pop123', 1, 'd/four', 'd/four-0813')
    assert fs._CALL_CTX.get() is None   # the proof's context ends with the call
    asyncio.run(fs._pow2_ask(cat, 0, 'sys', 'user', 50, {'cost': 0}))   # a box with no proof (a convo, a polish): the agent's own pair, nothing filed
    assert asked[-1] == 'a/one' and _rows(fs)[-1]['ref'] == 'pop123'
    cat['powRun'] = {'folder': {'id': 'pow9'}}   # no box at all = the open PoW folder
    asyncio.run(fs._pow2_ask(cat, 1, 'sys', 'user', 50))
    assert asked[-1] == 'e/five' and (_rows(fs)[-1]['kind'], _rows(fs)[-1]['ref'], _rows(fs)[-1]['mind']) == ('pow', 'pow9', 0)
