"""🛡 AGX-7 (owner 2026-11-14): the owner's guardrail switches — owner only, restrict-only, and a flip really changes what agents do."""
import asyncio
import types

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import guardrails as gr
import rep_guardrails
from test_play_studio import _server


def test_restrict_only_values_never_loosen_and_hard_limits_are_listed_locked():
    g = gr.clean({'taskCap': {'value': 50}, 'compFlagships': {'value': -3}, 'nope': {'on': False}})
    assert g['taskCap']['value'] == 2.0 and g['compFlagships']['value'] == 0 and 'nope' not in g   # never above today's number
    g = gr.clean({'taskCap': {'value': 0.25}}, g)
    assert gr.value(g, 'taskCap') == 0.25
    assert gr.value(gr.clean({'taskCap': {'on': False}}, g), 'taskCap') == 0
    v = gr.view(g)
    assert {s['key'] for s in v['switches']} == set(gr.SWITCHES) and [h['t'] for h in v['hard']][:3] == ['Money', 'Keys + privacy', 'Signing']
    with pytest.raises(ValueError):
        gr.clean({'taskCap': {'value': 'lots'}})
    with pytest.raises(ValueError):
        gr.clean({'autoCollect': {'on': 'false'}})   # a string never turns a switch back on


def test_a_bad_file_falls_back_to_today_and_never_raises(tmp_path):
    p = tmp_path / 'guardrails.json'
    p.write_text('{"switches": {"taskCap": 0.5, "agentsWork": {"on": false}}}')
    g = gr.load(p, fresh=True)
    assert gr.value(g, 'taskCap') == 2.0 and gr.on(g, 'agentsWork') is False
    p.write_text('not json'); assert gr.load(p, fresh=True) == gr.defaults()
    gr.save(p, gr.clean({'compRuns': {'on': False}}), 'OWNER', 5)
    assert gr.read(p)[1:] == ('OWNER', 5) and gr.on(gr.load(p), 'compRuns') is False   # a save is seen at once (cache dropped)


def _app(tmp_path, owner):
    def require(request):
        if request.headers.get('x-me') != owner:
            raise HTTPException(403, 'Only the FEELESS creator wallet can do this')
        return owner
    fake = types.SimpleNamespace(DATA_DIR=tmp_path, _require_owner=require, HTTPException=HTTPException)
    app = FastAPI(); app.include_router(rep_guardrails.router)
    return app, fake


def test_only_the_owner_reads_or_flips_them(monkeypatch, tmp_path):
    app, fake = _app(tmp_path, 'OWNER')
    monkeypatch.setattr(rep_guardrails, '_rs', lambda: fake)
    c = TestClient(app)
    assert c.get('/api/reputation/admin/guardrails').status_code == 403
    assert c.post('/api/reputation/admin/guardrails', json={'agentsWork': {'on': False}}, headers={'x-me': 'someone'}).status_code == 403
    assert not (tmp_path / 'guardrails.json').exists()
    j = c.post('/api/reputation/admin/guardrails', json={'agentsWork': {'on': False}, 'taskCap': {'value': 9}}, headers={'x-me': 'OWNER'})
    assert j.status_code == 200
    sw = {s['key']: s for s in j.json()['switches']}
    assert sw['agentsWork']['on'] is False and sw['taskCap']['value'] == 2.0
    assert c.get('/api/reputation/admin/guardrails', headers={'x-me': 'OWNER'}).json()['switches'][0]['on'] is False


def test_a_flipped_switch_changes_what_agents_do(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(fs, 'SELF_START', True)   # the guardrail still bites if self-started work is ever switched back on (it is off: owner 2026-11-14)
    cat = store['cats']['g']; cat['hive'] = {'on': True}; cat['brainsCfg'] = cat.get('brainsCfg') or {'brains': ['x']}
    assert fs._hive_works(cat) is True
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    assert post(op='cap', cap=1.5).json()['cap'] == 1.5
    gr.save(tmp_path / 'guardrails.json', gr.clean({'agentsWork': {'on': False}, 'taskCap': {'value': 0.1}, 'autoCollect': {'on': False}}), 'OWNER', 1)
    assert fs._hive_works(cat) is False and fs._hive_on(cat) is True   # Colonize stops; its own setting (what the board shows) stays
    assert fs._sicario_loop(store, 0, free=3) is None and asyncio.run(fs._sicario_free(None, store)) is None   # no seats, no Endless proofs
    assert post(op='cap', cap=1.5).json()['cap'] == 0.1    # no task cap above the owner's guardrail
    sent = []
    monkeypatch.setattr(fs, '_pot_address', lambda: 'POOL')
    monkeypatch.setattr(fs, '_shares', lambda: sent.append('read') or [])
    asyncio.run(fs._collect_pass(None, store, 0))
    assert sent == []                                      # auto-collect never even looks at the shares
