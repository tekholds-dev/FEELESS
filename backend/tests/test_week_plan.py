"""🗓 POC-PLAY items 4+5: week boards and brain-made week scenarios, each filed as its own PoC. Network faked (no model is called)."""
import asyncio
import json

import pytest

import week_plan as wk


def test_a_plan_is_checked_sorted_and_capped():
    raw = 'Sure! ' + json.dumps({'idea': 'Teaser to reveal', 'posts': [
        {'day': 'wed', 'platform': 'Twitter', 'time': '6pm', 'caption': 'Reveal day.', 'media': 'm1'},
        {'day': 'Mon', 'platform': 'instagram', 'time': '9:05', 'caption': 'Something is coming', 'media': 'nope'},
        {'day': 'Funday', 'platform': 'x', 'caption': 'bad day'}, {'day': 'Tue', 'platform': 'myspace', 'caption': 'bad platform'},
        {'day': 'Tue', 'platform': 'x', 'caption': ''}] + [{'day': 'Thu', 'platform': 'x', 'caption': f'n{i}'} for i in range(5)]})
    p = wk.parse(raw, ['m1'])
    assert [x['day'] for x in p['posts']] == ['Mon', 'Wed', 'Thu', 'Thu', 'Thu']             # sorted, junk gone, ≤3 a day
    assert p['posts'][1] == {'day': 'Wed', 'platform': 'x', 'time': '18:00', 'caption': 'Reveal day.', 'media': 'm1'}
    assert 'media' not in p['posts'][0] and p['posts'][0]['time'] == '09:05'                  # an unknown media id is dropped
    assert set(wk.board(p)) == {'x', 'instagram'} and wk.board(p)['x']['Thu'][0]['caption'] == 'n0'
    for bad in ('no json here', '{"posts": []}', '{bad json}'):
        with pytest.raises(ValueError):
            wk.parse(bad)


def test_three_styles_and_honest_prompts():
    assert [s[0] for s in wk.STYLES] == ['launch', 'drip', 'hype']
    sys_, user_ = wk.prompt('hype', 'GLINT', [{'id': 'm1', 'kind': 'video', 'prompt': 'camera spin'}])
    assert 'no made-up numbers' in sys_ and 'Hype into event' in sys_ and 'm1 (video)' in user_


def test_the_minds_file_three_week_plans_as_pocs_and_the_owner_edits_one(monkeypatch):
    import feecat_service as fs
    cat = {'id': 'c1', 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}, 'pocFolders': [], 'chat': []}
    store = {'cats': {'c1': cat}}
    doc = {'id': 'w1', 'kind': 'content', 'messages': [{'media': {'id': 'm1', 'kind': 'image', 'status': 'done', 'url': '/u', 'prompt': 'shoe'}}]}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_ws_load', lambda cid, ws: doc if ws == 'w1' else None)
    monkeypatch.setattr(fs._lc, 'minds_for', lambda cfg, kind: ['local/ossy', 'local/g4'])
    asked = []

    async def ask(cat_, model, sys_, user_, tok):
        asked.append(model)
        if 'Steady drip' in sys_:
            return 'I cannot do that', 0.0, False                                   # one mind fumbles: skipped, never invented
        return json.dumps({'idea': 'a week', 'posts': [{'day': 'Mon', 'platform': 'x', 'time': '09:00', 'caption': 'Hello', 'media': 'm1'}]}), 0.001, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    asyncio.run(fs._week_file('c1', 'w1', 'shoe drop'))
    weeks = [f for f in cat['pocFolders'] if f.get('week')]
    assert [f['week']['style'] for f in weeks] == ['launch', 'hype'] and sorted(asked) == ['local/g4', 'local/ossy', 'local/ossy']
    assert all(f['kind'] == 'PoC' and f['status'] == 'closed' and f['paper'] and f['ws'] == 'w1' for f in weeks)
    assert weeks[0]['week']['posts'][0]['media'] == 'm1' and '2 week plans filed' in cat['chat'][-1]['text']
    moved = {'idea': 'moved', 'posts': [{'day': 'Fri', 'platform': 'instagram', 'time': '12:00', 'caption': 'Moved to Friday'}]}
    asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='week_save', job=weeks[0]['id'], cap=moved, session='s')))
    assert weeks[0]['week']['posts'][0]['day'] == 'Fri' and weeks[0]['weekOrig']['posts'][0]['day'] == 'Mon' and weeks[0]['week']['style'] == 'launch'
    with pytest.raises(fs.HTTPException):
        asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='week_save', job=weeks[0]['id'], cap={'posts': []}, session='s')))
