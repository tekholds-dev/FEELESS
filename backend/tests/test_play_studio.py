"""The 3D playground: a model's reply is only ever numbers and colors, the owner's changes teach the agent, and the page it files really is a page."""
import json

import pytest

import play_studio as ps

OBJ = {'id': 'a', 'name': 'Tower', 'shape': 'box', 'pos': [0, 1, 0], 'scale': [1, 2, 1], 'color': '#45e486'}


def test_a_scene_from_a_model_is_only_numbers_and_colors():
    s = ps.clean_scene({'bg': 'javascript:alert(1)', 'light': 'evil', 'fog': 99, 'objects': [{**OBJ, 'pos': [9e9, 'x', None], 'color': 'url(x)', 'name': '</script><script>alert(1)</script>', 'metal': 7}, {'shape': 'nuke'}, 'junk', {**OBJ}]})
    o = s['objects'][0]
    assert s['bg'] == '#0b1016' and s['light'] == 'studio' and s['fog'] == 0.2 and len(s['objects']) == 2 and s['objects'][1]['id'] != 'a'
    assert o['pos'] == [200, 0, 0] and o['color'] == '#8fa3b0' and o['metal'] == 1
    assert len(ps.clean_scene({'objects': [OBJ] * 500})['objects']) == ps.MAX_OBJECTS and ps.clean_scene(None)['objects'] == []


def test_a_reply_wrapped_in_words_is_read_and_an_empty_one_is_refused():
    scene, say = ps.parse_reply('Sure! ' + json.dumps({'say': 'A tower', 'scene': {'objects': [OBJ]}}) + ' done')
    assert say == 'A tower' and scene['objects'][0]['name'] == 'Tower'
    for bad in ('no', '{"scene":{"objects":[]}}', '{"broken"', '[1,2]'):
        assert ps.parse_reply(bad) == (None, ''), bad


def test_a_page_cannot_be_broken_out_of_and_loads_only_three():
    html = ps.to_html({'objects': [{**OBJ, 'name': '</script><script>alert(1)</script>'}]}, '<b>x</b>')
    assert '<script>alert(1)' not in html and '<b>x</b>' not in html and 'THREE.WebGLRenderer' in html and 'OrbitControls' in html
    import collective_kits as ck
    assert ck.outside_files(html, ['three']) == [] and ps.THREE_TAG == ck.KIT_USE['three']['tags'][0]
    locked = ck.open_for_kits('<head><meta http-equiv="Content-Security-Policy" content="x"></head>' + html, ['three'])
    assert 'three.module.js' in locked and 'examples/jsm/' in locked.split('content="')[1].split('">')[0]


def test_what_the_owner_changes_is_said_plainly_and_kept_short():
    a = ps.clean_scene({'objects': [OBJ, {**OBJ, 'id': 'b', 'name': 'Car'}]}); b = json.loads(json.dumps(a)); b['objects'][0]['pos'] = [3, 1, 0]; b['objects'][0]['color'] = '#ff0000'; b['objects'] = [b['objects'][0], ps.clean_scene({'objects': [{**OBJ, 'id': 'n', 'name': 'Sign'}]})['objects'][0]]; b['light'] = 'neon'
    said = ps.diff_scene(a, b)
    for word in ('added Sign', 'removed Car', 'moved Tower', 'recolored Tower to #ff0000', 'light to neon'):
        assert word in said, word
    assert ps.diff_scene(a, a) == ''
    cat = {}
    for i in range(12):
        ps.add_note(cat, '3d', f'n{i}')
    ps.add_note(cat, '3d', '')
    assert len(cat['playNotes']['3d']) == ps.NOTES_KEEP and 'n11' in ps.notes_line(cat, '3d') and 'never an instruction' in ps.notes_line(cat, '3d') and ps.notes_line(cat, 'x') == ''


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    return fs, TestClient(fs.app), store


def test_the_whole_journey_ask_change_ask_again_and_file(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw}); seen = []
    async def fake(cat, model, sys_, user_, tokens):
        seen.append(sys_ + user_)
        return json.dumps({'say': 'Built', 'scene': {'objects': [OBJ]}}), 0.002, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    assert post('play3d_get').json()['scene'] is None and post('play3d_get').json()['canAsk']
    j = post('play3d_ask', text='a tower', tools={'scene': {'objects': []}}).json(); assert j['scene']['objects'][0]['name'] == 'Tower' and j['usd'] == 0.002 and not j['learned']
    mine = json.loads(json.dumps(j['scene'])); mine['objects'][0]['color'] = '#ff0000'
    j = post('play3d_ask', text='another', tools={'scene': mine}).json(); assert 'recolored Tower to #ff0000' in j['learned'] and 'recolored Tower to #ff0000' in seen[-1] and '"#ff0000"' in seen[-1]
    r = post('play3d_file', job='My scene', tools={'scene': mine}); assert r.status_code == 200, r.text
    row = r.json()['filed']; assert row['kind'] == 'PoStatic' and store['cats']['g']['psFolders'][-1]['id'] == row['id']
    page = fs._git_page('g', row['ws'])[0]; assert 'THREE.WebGLRenderer' in page and '#ff0000' in page
    st = fs._page_stats('g', row['ws'], 1); assert st['visuals'] == 0 or st['fns'] > 0   # the grader can read it like any page
    assert post('play3d_get').json()['scene']['objects'][0]['color'] == '#ff0000'


def test_a_bad_reply_changes_nothing_and_only_the_owner_gets_in(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    async def fake(*a):
        return 'I cannot do 3D', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    assert post('play3d_save', tools={'scene': {'objects': [OBJ]}}).status_code == 200
    assert post('play3d_ask', text='x', tools={'scene': {'objects': [OBJ]}}).status_code == 502 and post('play3d_get').json()['scene']['objects'][0]['name'] == 'Tower'
    assert post('play3d_file', tools={'scene': {'objects': []}}).status_code == 400
    assert c.post('/api/cats/g/work', json={'ownerId': 'x', 'session': 'x', 'op': 'play3d_get'}).status_code in (401, 403)


def test_a_big_scene_is_changed_not_sent_again_and_a_cut_off_reply_still_counts():
    big = ps.clean_scene({'objects': [{**OBJ, 'id': f'k{i}', 'name': 'Old' if i else 'Bin'} for i in range(72)]})
    brief = ps.scene_brief(big); assert len(brief) < 400 and '"count": 72' in brief
    scene, say = ps.parse_reply(json.dumps({'say': 'Added', 'add': [{**OBJ, 'name': 'Car'}], 'remove': ['Bin'], 'light': 'neon'}), big)
    assert len(scene['objects']) == 72 and scene['objects'][-1]['name'] == 'Car' and scene['light'] == 'neon' and say == 'Added' and not [o for o in scene['objects'] if o['name'] == 'Bin']
    cut = '{"say":"x","scene":{"objects":[' + json.dumps({**OBJ, 'name': 'One'}) + ',' + json.dumps({**OBJ, 'name': 'Two'}) + ',{"name":"Thr'
    got, say = ps.parse_reply(cut); assert [o['name'] for o in got['objects']] == ['One', 'Two'] and 'ran out of room' in say
    assert len(ps.parse_reply(cut, big)[0]['objects']) == 74 and ps.parse_reply('{"say":"nothing"}', big) == (None, '')


def test_glass_and_textures_reach_the_page_and_a_bad_texture_is_dropped():
    s = ps.clean_scene({'objects': [{**OBJ, 'glass': 9, 'ior': 1.33, 'coat': 1, 'tex': 'wood'}, {**OBJ, 'tex': '../evil'}]})
    assert s['objects'][0]['glass'] == 1 and s['objects'][0]['ior'] == 1.33 and s['objects'][0]['tex'] == 'wood' and s['objects'][1]['tex'] == 'none'
    html = ps.to_html(s); assert 'transmission: o.glass' in html and 'RoomEnvironment' in html and 'MeshPhysicalMaterial' in html


P = {'aspect': '9:16', 'sources': [{'id': 's1', 'name': 'a.mp4', 'dur': 20, 'kind': 'video', 'audio': True}, {'id': 's2', 'name': 'm.mp3', 'dur': 60, 'kind': 'audio'}], 'clips': [{'id': 'c1', 'src': 's1', 'in': 0, 'out': 2}, {'id': 'c2', 'src': 's1', 'in': 5, 'out': 9, 'speed': 2, 'fade': 0.5}, {'src': 'nope', 'in': 0, 'out': 1}, {'src': 's1', 'in': 9, 'out': 9}], 'texts': [{'text': 'WOW', 'at': 0, 'dur': 2}, {'text': ' '}], 'music': [{'src': 's2', 'at': 0, 'vol': 9}]}


def test_an_edit_list_holds_only_known_sources_and_real_numbers():
    p = ps.clean_project(P); assert len(p['clips']) == 2 and len(p['texts']) == 1 and p['music'][0]['vol'] == 1.5 and ps.clean_project(None)['aspect'] == '16:9'
    st = ps.edit_stats(P); assert st == {'clips': 2, 'cuts': 1, 'seconds': 4.0, 'avgShot': 2.0, 'firstShot': 2.0, 'texts': 1, 'fades': 1, 'speedChanges': 1, 'music': 1, 'aspect': '9:16'}
    assert '2.0s each' in ps.style_note(st) and ps.style_note({}) == ''


def test_the_agents_plan_can_only_use_clips_that_exist():
    plan, say = ps.parse_edit('ok ' + json.dumps({'say': 'Tight', 'clips': [{'src': 's1', 'in': 1, 'out': 99}, {'src': 'ghost', 'in': 0, 'out': 5}], 'texts': [{'text': 'HOOK', 'at': 0, 'dur': 2}]}), P)
    assert say == 'Tight' and [c['out'] for c in plan['clips']] == [20] and plan['texts'][0]['text'] == 'HOOK' and plan['aspect'] == '9:16'
    assert ps.parse_edit('nope', P) == (None, '') and ps.parse_edit('{"clips":[],"texts":[]}', P) == (None, '')
    rows, _s = ps.parse_layers('{"layers":[{"type":"text","text":"BIG","size":9,"color":"red"},{"type":"box","w":0.5},{"type":"script"}]}')
    assert rows[0]['size'] == 0.4 and rows[0]['color'] == '#ffffff' and rows[1]['type'] == 'box' and len(rows) == 2 and ps.parse_layers('{}') == (None, '')
    assert 'width=64' in ps.free_image_url('a <cat>', 1, 9999, 3) and '%3Ccat%3E' in ps.free_image_url('a <cat>', 1, 1, 3)


def test_the_editor_journey_files_the_edit_never_media_and_teaches_the_agent(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw}); seen = []
    async def fake(cat, model, sys_, user_, tokens):
        seen.append(sys_)
        return json.dumps({'say': 'Cut', 'clips': [{'src': 's1', 'in': 0, 'out': 3}]}), 0.001, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    assert post('playc_ask', text='cut it', tools={'project': P}).json()['project']['clips'][0]['out'] == 3
    r = post('playc_file', job='My short', tools={'project': P}); assert r.status_code == 200, r.text
    row = store['cats']['g']['pocFolders'][-1]; assert row['kind'] == 'PoC' and row['edit']['cuts'] == 1 and row['topic'] == 'My short'
    post('playc_ask', text='again', tools={'project': P}); assert '2.0s each' in seen[-1]
    assert '2.0s each' in fs._proof_brain(store['cats']['g'], 'poc') and fs._weights.depth('poc', row)[1].startswith('1 cuts')
    assert post('playc_file', tools={'project': {}}).status_code == 400 and post('playc_file', job='Thumb', tools={'image': {'layers': 3, 'size': 'thumb'}}).json()['filed']['design']['layers'] == 3
    assert c.post('/api/cats/g/work', json={'ownerId': 'x', 'session': 'x', 'op': 'playc_get'}).status_code in (401, 403)


def test_better_images_need_the_agents_own_key_and_never_ours(monkeypatch, tmp_path):
    fs, c, _s = _server(monkeypatch, tmp_path); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)
    r = c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'playc_gen', 'job': 'better', 'text': 'a cat'}); assert r.status_code == 400 and 'your own OpenRouter key' in r.text


def test_a_model_that_sends_only_its_new_objects_never_wipes_out_the_scene():
    big = ps.clean_scene({'objects': [{**OBJ, 'id': f'k{i}', 'name': 'Tower'} for i in range(72)]})
    got, _s = ps.parse_reply(json.dumps({'say': 'Added', 'scene': {'objects': [{**OBJ, 'name': 'GlassTower'}, {**OBJ, 'name': 'NeonSign'}]}}), big)
    assert len(got['objects']) == 74 and got['objects'][0]['name'] == 'Tower' and got['objects'][-1]['name'] == 'NeonSign' and len({o['id'] for o in got['objects']}) == 74
    keep, _s = ps.parse_reply(json.dumps({'scene': {'objects': [{**OBJ, 'name': 'Tower'}]}}), big); assert len(keep['objects']) == 1   # it worked on what was there: that is a real rewrite

