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
    got, say = ps.parse_reply(cut); assert [o['name'] for o in got['objects']] == ['One', 'Two'] and say
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
    keep, _s = ps.parse_reply(json.dumps({'scene': {'objects': [{**OBJ, 'name': 'Tower'}]}}), big); assert len(keep['objects']) == 72   # re-sending part of it never removes the rest


ROWS = {'at': 9e12, 'rows': {'model': [{'id': 'Camera_01', 'name': 'Camera 01', 'tags': ['vintage', 'camera'], 'pop': 5}, {'id': 'Chair', 'name': 'Chair', 'tags': ['chair'], 'pop': 900}], 'hdri': [{'id': 'studio_small_08', 'name': 'Studio', 'tags': ['studio'], 'pop': 1}], 'texture': [{'id': 'marble_01', 'name': 'Marble', 'tags': ['marble'], 'pop': 1}]}}
FILES = {'gltf': {'1k': {'gltf': {'url': 'https://dl.polyhaven.org/file/m.gltf', 'include': {'m.bin': {'url': 'https://dl.polyhaven.org/file/m.bin'}, 'textures/d.jpg': {'url': 'https://evil.example/d.jpg'}}}}}, 'hdri': {'1k': {'hdr': {'url': 'https://dl.polyhaven.org/file/s.hdr'}}}, 'Diffuse': {'1k': {'jpg': {'url': 'https://dl.polyhaven.org/d.jpg'}}}, 'nor_gl': {'1k': {'jpg': {'url': 'https://dl.polyhaven.org/n.jpg'}}}, 'Rough': {'1k': {'jpg': {'url': 'https://dl.polyhaven.org/r.jpg'}}}}


class _PH:
    def __init__(self):
        self.n = 0

    async def get(self, url, **kw):
        self.n += 1; assert kw['headers']['User-Agent'].startswith('FEELESS')   # Poly Haven asks for our own name

        class R:
            status_code = 200
            json = staticmethod(lambda: FILES)
        return R()


def test_a_described_thing_becomes_a_real_asset_and_what_is_not_there_is_never_faked(tmp_path):
    import asyncio
    import asset_packs as ap
    (tmp_path / ap.INDEX).write_text(json.dumps(ROWS)); h = _PH()
    assert ap.search(tmp_path, 'vintage camera')[0]['id'] == 'Camera_01' and ap.search(tmp_path, '')[0]['id'] == 'Chair' and ap.search(tmp_path, 'unicorn') == []
    scene, say = ps.parse_reply(json.dumps({'say': 'x', 'scene': {'light_find': 'studio', 'objects': [{'find': 'vintage camera', 'pos': [0, 0, 0], 'height': 0.4}, {'find': 'unicorn'}, {'name': 'Stage', 'shape': 'cylinder', 'look': 'marble'}], 'page': {'headline': 'Real <b>', 'sections': [{'title': 'A', 'body': 'B'}]}}}))
    scene, used, missing = asyncio.run(ap.fill(h, tmp_path, scene))
    assert used == ['Camera 01', 'marble 01', 'studio small 08'] and missing == ['unicorn'] and len(scene['objects']) == 2
    cam = scene['objects'][0]; assert cam['asset']['url'].endswith('m.gltf') and cam['asset']['files'] == {'m.bin': 'https://dl.polyhaven.org/file/m.bin'} and cam['height'] == 0.4   # an address not on their host is dropped
    asyncio.run(ap.resolve(h, tmp_path, 'Camera_01', 'model')); assert h.n == 3   # asked once each
    html = ps.to_html(scene, 'T'); assert 'GLTFLoader' in html and 'RGBELoader' in html and ap.CREDIT in html and 'Real &lt;b&gt;' in html and '<h2>A</h2>' in html


def test_a_page_with_real_assets_may_load_that_one_host_and_nothing_else():
    import ai_play as ap2
    import collective_kits as ck
    scene = ps.clean_scene({'objects': [{'find': 'x', 'asset': {'id': 'a', 'url': 'https://dl.polyhaven.org/m.gltf', 'files': {}}, 'pos': [0, 0, 0]}]})
    rule = ck.open_for_kits(ap2.lock_html(ps.to_html(scene)), ['three']).split('content="')[1].split('">')[0]
    assert 'connect-src blob: data: https://dl.polyhaven.org' in rule and 'img-src data: blob: https://dl.polyhaven.org' in rule and 'evil' not in rule
    assert 'connect-src' not in ck.open_for_kits(ap2.lock_html(ps.to_html({'objects': [OBJ]})), ['three']).split('content="')[1].split('">')[0]
    assert ps.clean_scene({'objects': [{'asset': {'url': 'https://evil.example/m.gltf'}, 'shape': 'box'}]})['objects'][0]['shape'] == 'box' and 'asset' not in ps.clean_scene({'objects': [{'asset': {'url': 'https://evil.example/m.gltf'}, 'shape': 'box'}]})['objects'][0]


def test_only_real_words_read_as_a_3d_request():
    import asset_packs as ap
    for t in ('idea for a 3D landing page', 'use three.js', 'a webgl hero', 'load this glb'):
        assert ap.wants_3d(t), t
    for t in ('write a post about trends', 'pick 3 winners', 'a 30 day plan'):
        assert not ap.wants_3d(t), t


def test_a_full_3d_prompt_to_postatic_builds_real_assets_and_checks_against_the_prompt(monkeypatch, tmp_path):
    import asyncio
    fs, c, store = _server(monkeypatch, tmp_path); import asset_packs as ap; kits = tmp_path / 'kits'; kits.mkdir(); (kits / ap.INDEX).write_text(json.dumps(ROWS)); (kits / ap.FILES).write_text(json.dumps({'model:Camera_01:1k': {'id': 'Camera_01', 'name': 'Camera 01', 'kind': 'model', 'url': 'https://dl.polyhaven.org/m.gltf', 'files': {}}, 'model:Chair:1k': {'id': 'Chair', 'name': 'Chair 1', 'kind': 'model', 'url': 'https://dl.polyhaven.org/c.gltf', 'files': {}}, 'hdri:studio_small_08:1k': {'id': 'studio_small_08', 'name': 'Studio', 'kind': 'hdri', 'url': 'https://dl.polyhaven.org/s.hdr', 'files': {}}}))
    cat = store['cats']['g']; row = fs._feat.new_folder(cat, 'build', 'Glint', 1.0); fs._ws_save('g', fs._feat.new_doc(row)); asks = []
    async def fake(cat_, model, sys_, user_, tokens):
        asks.append((sys_, user_))
        if 'You check a 3D build' in sys_:
            assert 'vintage camera and a chair' in user_ and 'Camera 01' in user_
            return json.dumps({'say': 'Added the chair you named', 'add': [{'find': 'chair', 'pos': [1, 0, 0], 'height': 1}]}), 0.001, False
        assert 'Build exactly what this prompt says' in sys_ and 'vintage camera and a chair' in user_
        return json.dumps({'say': 'Built', 'scene': {'light_find': 'studio', 'objects': [{'find': 'vintage camera', 'pos': [0, 0, 0], 'height': 0.4}], 'page': {'headline': 'GLINT', 'cta': 'Enter'}}}), 0.002, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    asyncio.run(fs._ws_run('g', row['id'], 'a', 'Build a 3D landing page for GLINT with a vintage camera and a chair', None))
    doc = fs._ws_load('g', row['id']); assert len(asks) == 2 and len(doc['versions']) == 1 and doc['scene3d']['hdri']['id'] == 'studio_small_08'
    names = [o['name'] for o in doc['scene3d']['objects']]; assert 'Chair 1' in names or 'chair' in names
    page = doc['versions'][0]['html']; assert 'GLINT' in page and 'GLTFLoader' in page and 'dl.polyhaven.org/m.gltf' in page and 'dl.polyhaven.org/c.gltf' in page and "connect-src blob: data: https://dl.polyhaven.org" in page
    said = doc['messages'][-1]['text']; assert 'Real assets: Camera 01' in said and 'Added the chair you named' in said
    assert fs._WS_DONE and fs._WS_DONE[-1]['doc']['id'] == row['id']
    fs._WS_DONE.clear()
    assert fs._play_load('g', '3d')['scene']['page']['headline'] == 'GLINT'   # the studio opens on what it built


def test_a_plain_page_request_still_takes_the_normal_build():
    import asset_packs as ap
    assert not ap.wants_3d('Build a bakery landing page with a menu')


def test_what_real_models_really_send_is_repaired_not_thrown_away():
    # the real OSSY reply that failed: hex colors, a camera inside the set, and light as objects
    raw = '{"say":"Built","scene":{"light_find":"studio","camera":[0,0,0],"objects":[{"find":"vintage camera","pos":[0,0,0],"height":0.4,"material":{"color":0x888888,},},{"find":"spot light source","name":"Key Light","shape":"sphere"},{"name":"Fill Light","shape":"sphere"},{"find":"wooden chair","pos":[0,0,-1.5],"height":1}]}}'
    scene, say = ps.parse_reply(raw)
    assert say == 'Built' and [o['find'] for o in scene['objects']] == ['vintage camera', 'wooden chair'] and (scene['camera'][0] ** 2 + scene['camera'][2] ** 2) ** 0.5 > 2
    cut, why = ps.parse_reply('{"say":"x","scene":{"objects":[{"find":"vintage camera","pos":[0,0,0]},{"find":"chair","pos":[1,0,')
    assert [o['find'] for o in cut['objects']] == ['vintage camera'] and why
    # the real replies: every object and the whole page were fine, only the last brace was missing
    real = '{"say":"Built","scene":{"light_find":"dark studio","page":{"headline":"GLINT","sections":[{"title":"A","body":"B"}]},"objects":[{"find":"wooden chair","pos":[-0.8,0.8,1.5],"height":1.1},{"find":"old leather books","pos":[0.8,0.6,1.5],"height":0.35}]}'
    whole, said = ps.parse_reply(real); assert said == 'Built' and whole['light_find'] == 'dark studio' and whole['page']['headline'] == 'GLINT' and len(whole['objects']) == 2
    kept, _s = ps.parse_reply('{"scene":{"camera":[9,4,9],"objects":[{"find":"vintage camera","pos":[0,0,0],"height":1}]}}'); assert kept['camera'] == [9, 4, 9]


def test_a_chair_must_be_a_chair_and_a_stage_gets_a_real_surface(tmp_path):
    import asyncio
    import asset_packs as ap
    rows = {'at': 9e12, 'rows': {'model': [{'id': 'marble_bust_01', 'name': 'Marble Bust', 'tags': ['marble', 'bust'], 'pop': 9}, {'id': 'round_wooden_table_01', 'name': 'Table', 'tags': ['wooden', 'table'], 'pop': 9}, {'id': 'ArmChair_01', 'name': 'Arm Chair', 'tags': ['chair'], 'pop': 1}, {'id': 'Camera_01', 'name': 'Camera', 'tags': ['camera'], 'pop': 1}, {'id': 'book_stack', 'name': 'Book Stack', 'tags': ['book'], 'pop': 1}], 'texture': [{'id': 'marble_01', 'name': 'Marble', 'tags': ['marble'], 'pop': 1}], 'hdri': []}}
    (tmp_path / ap.INDEX).write_text(json.dumps(rows))
    assert ap.best(tmp_path, 'wooden chair', 'model')['id'] == 'ArmChair_01' and ap.best(tmp_path, 'vintage film camera, brass and leather', 'model')['id'] == 'Camera_01' and ap.best(tmp_path, 'stack of old books', 'model')['id'] == 'book_stack'
    assert ap.best(tmp_path, 'polished marble slab', 'model') is None and ap.best(tmp_path, 'dark velvet backdrop', 'model') is None and ap.best(tmp_path, 'sneaker', 'model') is None
    scene = ps.clean_scene({'objects': [{'find': 'polished marble slab', 'pos': [0, 0, 0]}, {'find': 'dark velvet backdrop'}, {'find': 'sneaker', 'pos': [1, 0, 0]}]})
    class H:
        async def get(self, *a, **k):
            class R:
                status_code = 200
                json = staticmethod(lambda: FILES)
            return R()
    got, used, missing = asyncio.run(ap.fill(H(), tmp_path, scene))
    assert 'sneaker' in missing and 'sneaker' not in [o.get('find') for o in got['objects']] and [o['shape'] for o in got['objects']] == ['cylinder', 'box'] and got['objects'][0]['pbr']['name'] == 'marble 01'


def test_a_checker_that_resends_the_scene_keeps_the_light_page_and_models():
    now = ps.clean_scene({'hdri': {'id': 's', 'url': 'https://dl.polyhaven.org/s.hdr'}, 'page': {'headline': 'GLINT'}, 'objects': [{'name': 'Cam', 'find': 'camera', 'asset': {'id': 'c', 'url': 'https://dl.polyhaven.org/c.gltf'}, 'pos': [0, 0, 0], 'height': 1}]})
    got, _s = ps.parse_reply(json.dumps({'say': 'Fixed', 'scene': {'objects': [{'name': 'Cam', 'find': 'camera', 'pos': [0, 0, 0], 'height': 2}, {'find': 'chair', 'pos': [1, 0, 0]}]}}), now)
    assert got['hdri']['id'] == 's' and got['page']['headline'] == 'GLINT' and got['objects'][0]['asset']['id'] == 'c' and got['objects'][0]['height'] == 2 and got['objects'][1]['find'] == 'chair'


def test_a_material_is_a_surface_and_things_stand_on_the_stage(tmp_path):
    import asyncio
    import asset_packs as ap
    (tmp_path / ap.INDEX).write_text(json.dumps({'at': 9e12, 'rows': {'model': [{'id': 'marble_bust_01', 'name': 'Bust', 'tags': ['marble', 'bust'], 'pop': 9}, {'id': 'Camera_01', 'name': 'Camera', 'tags': ['camera'], 'pop': 1}], 'texture': [{'id': 'marble_01', 'name': 'Marble', 'tags': ['marble'], 'pop': 1}], 'hdri': []}}))
    class H:
        async def get(self, *a, **k):
            class R:
                status_code = 200
                json = staticmethod(lambda: FILES)
            return R()
    got, _u, missing = asyncio.run(ap.fill(H(), tmp_path, ps.clean_scene({'objects': [{'find': 'polished marble', 'pos': [0, 0, 0]}, {'find': 'vintage camera', 'pos': [0, 0, 0], 'height': 0.2}]})))
    stage, cam = got['objects']; assert stage['shape'] == 'cylinder' and stage['pbr']['name'] == 'marble 01' and cam['asset'] and cam['pos'][1] == 0.12 and stage['scale'][0] == 1.4 and not missing
    assert ps._aim({'objects': [cam], 'page': {'headline': 'x'}})[1] < ps._aim({'objects': [cam]})[1]


def test_one_bad_reply_never_ends_a_build(monkeypatch, tmp_path):
    import asyncio
    fs, _c, store = _server(monkeypatch, tmp_path); import asset_packs as ap; kits = tmp_path / 'kits'; kits.mkdir(); (kits / ap.INDEX).write_text(json.dumps(ROWS))
    (kits / ap.FILES).write_text(json.dumps({'model:Camera_01:1k': {'id': 'Camera_01', 'name': 'Camera 01', 'kind': 'model', 'url': 'https://dl.polyhaven.org/m.gltf', 'files': {}}}))
    cat = store['cats']['g']; cat['brainsCfg']['brains'] = ['m/a', 'm/b']; row = fs._feat.new_folder(cat, 'build', 'P', 1.0); fs._ws_save('g', fs._feat.new_doc(row)); who = []
    async def fake(cat_, model, sys_, user_, tokens):
        who.append(model)
        if 'You check' in sys_:
            return '{"say":"Matches the prompt"}', 0, False
        return ('sorry, words only', 0, False) if model == 'm/a' else (json.dumps({'scene': {'objects': [{'find': 'camera', 'pos': [0, 0, 0]}]}}), 0, False)
    monkeypatch.setattr(fs, '_ws_ask', fake)
    asyncio.run(fs._ws_run('g', row['id'], 'a', 'a 3D camera page', None)); doc = fs._ws_load('g', row['id'])
    assert who[:2] == ['m/a', 'm/b'] and len(doc['versions']) == 1 and doc['versions'][0]['by'] == 'Mind B' and 'Matches the prompt' in doc['messages'][-1]['text']; fs._WS_DONE.clear()


def test_real_things_never_float():
    import asset_packs as ap
    a = {'id': 'a', 'url': 'https://dl.polyhaven.org/a.gltf'}
    s = ps.clean_scene({'objects': [{'name': 'Stage', 'shape': 'cylinder', 'pos': [0, 0.06, 0], 'scale': [3, 0.12, 3]}, {'name': 'Cam', 'asset': a, 'pos': [0, 1.6, 0], 'height': 0.8}, {'name': 'Chair', 'asset': a, 'pos': [-0.5, 0.9, 0], 'height': 0.9}, {'name': 'Far', 'asset': a, 'pos': [9, 3, 0], 'height': 1}]})
    s['objects'] = s['objects'][:3] + s['objects'][3:]; ap.compose(s); by = {o['name']: o for o in s['objects']}
    assert by['Cam']['pos'][1] == 0.12 and by['Chair']['pos'][1] == 0.12 and by['Far']['pos'][1] in (0, 0.12) and by['Stage']['scale'][1] == 0.12


def test_a_whole_room_with_three_monitors_and_posters_is_one_short_reply(tmp_path):
    import asyncio
    import asset_packs as ap
    import collective_kits as ck
    import ai_play as aip
    reply = json.dumps({'say': 'Room', 'scene': {'objects': [{'prefab': 'room', 'look': 'concrete', 'w': 8, 'd': 6, 'h': 3}, {'find': 'camera', 'pos': [0, 0.8, -2], 'rest': False, 'height': 0.3}, {'find': 'camera', 'pos': [1, 0.8, -2], 'rest': False, 'height': 0.3}] + [{'prefab': 'monitor', 'pos': [x, 0.76, -2], 'size': 0.6, 'picture': f'chart {x}'} for x in (-0.6, 0, 0.6)] + [{'prefab': 'poster', 'pos': [-2, 1.8, -2.95], 'picture': 'neon arcade'}]}})
    scene, _s = ps.parse_reply(reply); names = [o['name'] for o in scene['objects']]
    assert names.count('Monitor screen') == 3 and names.count('Poster') == 1 and 'Back wall' in names
    screen = next(o for o in scene['objects'] if o['name'] == 'Monitor screen'); assert screen['image'].startswith('https://image.pollinations.ai/prompt/chart') and screen['glow'] == 0.9
    (tmp_path / ap.INDEX).write_text(json.dumps(ROWS)); (tmp_path / ap.FILES).write_text(json.dumps({'model:Camera_01:1k': {'id': 'Camera_01', 'name': 'Cam', 'kind': 'model', 'url': 'https://dl.polyhaven.org/m.gltf', 'files': {}}}))
    class H:
        async def get(self, *a, **k):
            class R:
                status_code = 200
                json = staticmethod(lambda: FILES)
            return R()
    got, _u, _m = asyncio.run(ap.fill(H(), tmp_path, scene, many=True)); cams = [o for o in got['objects'] if o.get('asset')]
    assert len(cams) == 2 and cams[0]['pos'][1] == 0.8 and sum(1 for o in got['objects'] if o['name'] == 'Monitor frame') == 3   # stays on the desk, and built pieces are kept
    assert len([o for o in asyncio.run(ap.fill(H(), tmp_path, ps.clean_scene({'objects': cams}), many=False))[0]['objects']]) == 1   # not asked for two: one
    rule = ck.open_for_kits(aip.lock_html(ps.to_html(got)), ['three']).split('content="')[1].split('">')[0]
    assert 'image.pollinations.ai' in rule and ps.room_camera(got)[2] > 3
    assert ps.clean_scene({'objects': [{'name': 'x', 'shape': 'plane', 'image': 'https://evil.example/a.png'}]})['objects'][0].get('image') is None
    assert ap.MANY.search('triple monitors') and not ap.MANY.search('a chair') and ap.wants_3d('create a whole room')


def test_what_the_prompt_names_is_built_even_when_the_model_forgets():
    # the real OSSY reply: the room became a find, and the monitors and posters were lost
    bad = ps.clean_scene({'objects': [{'find': 'dark gamer room', 'pos': [0, 0, 0], 'height': 2.4}, {'find': 'trader desk', 'pos': [0, 0, -2.5], 'height': 0.75}, {'find': 'crypto candlestick chart left'}, {'find': 'potted plant', 'pos': [2.8, 0, -2.6]}]})
    got = ps.ensure_named(bad, 'Create a 3D whole room: a dark gamer room with a desk, triple monitors showing crypto charts, a chair, a plant, and posters on the walls.')
    names = [o['name'] for o in got['objects']]
    assert names.count('Monitor screen') == 3 and names.count('Poster') == 2 and 'Back wall' in names and 'dark gamer room' not in names and 'potted plant' in names and 'trader desk' in names
    assert 'crypto charts' in next(o for o in got['objects'] if o['name'] == 'Monitor screen')['image'].replace('%20', ' ')
    plain = ps.ensure_named(ps.clean_scene({'objects': [{'find': 'vintage camera', 'pos': [0, 0, 0]}]}), 'a 3D landing page with a vintage camera'); assert [o['find'] for o in plain['objects']] == ['vintage camera']
    assert ps._count_of('five gaming monitors', r'monitors?', 1) == 5 and ps._count_of('12 posters', r'posters?', 2) == 12 and ps._count_of('a monitor', r'monitors?', 1) == 1
    twice = ps.ensure_named(got, 'triple monitors and posters in a room'); assert [o['name'] for o in twice['objects']].count('Monitor screen') == 3 and [o['name'] for o in twice['objects']].count('Back wall') == 1   # never built twice


def test_a_site_has_a_button_into_a_second_place_with_a_dash_and_no_cards():
    first = {'page': {'headline': 'GLINT', 'cta': 'Enter the room'}, 'objects': [OBJ]}
    room = {'page': {'headline': 'The room', 'dash': {'title': 'Live', 'note': 'Sample numbers', 'stats': [{'label': 'Price', 'value': '$1.20'}], 'points': [1, 2, 3]}}, 'objects': [{'prefab': 'x', **OBJ}]}
    html = ps.to_html(first, 'GLINT', room)
    assert 'data-go="1"' in html and 'data-page="1"' in html and 'Sample numbers' in html and '$1.20' in html and '<polyline' in html and 'Enter the room' in html
    style = html.split('.stats{{')[0] if False else html; assert '.dash{' in style and 'background' not in style.split('.dash{')[1].split('}')[0]   # no card behind the dash
    assert 'data-go="' not in ps.to_html(first) and 'href="#more0"' in ps.to_html(first)


def test_pictures_go_inside_the_file_and_a_bad_address_never_does():
    import asyncio
    good = 'data:image/jpeg;base64,/9j/AAAA'
    assert ps.clean_scene({'objects': [{**OBJ, 'image': good}]})['objects'][0]['image'] == good and 'image' not in ps.clean_scene({'objects': [{**OBJ, 'image': 'data:text/html;base64,AAAA'}]})['objects'][0]
    class H:
        async def get(self, url, **k):
            class R:
                status_code = 200; content = b'\xff\xd8img'; headers = {'content-type': 'image/jpeg'}
            return R()
    s = ps.clean_scene({'objects': [{**OBJ, 'picture': 'a poster'}]}); assert s['objects'][0]['image'].startswith(ps.FREE_IMAGE)
    asyncio.run(ps.embed_pictures(H(), [s])); assert s['objects'][0]['image'].startswith('data:image/jpeg;base64,')
    class No:
        n = 0

        async def get(self, url, **k):
            No.n += 1
            class R:
                status_code = 429; content = b''; headers = {'content-type': 'text/plain'}
            return R()
    import pytest as _p
    with _p.MonkeyPatch.context() as mp:
        mp.setattr(ps, 'PICTURE_WAITS', (0, 0)); t = ps.clean_scene({'objects': [{**OBJ, 'picture': 'b'}]}); asyncio.run(ps.embed_pictures(No(), [t])); assert No.n == 2 and 'image' not in t['objects'][0]
    room = ps.ensure_named(ps.clean_scene({'objects': []}), 'a whole room'); assert room['ground'] is False
    locked = ps.lock_site(ps.to_html({'objects': [{**OBJ, 'image': 'data:image/jpeg;base64,' + 'A' * 70000}]})); assert 'three.module.js' in locked.split('content="')[1].split('">')[0] and 'A' * 70000 in locked and locked.rstrip().endswith('</html>')


def test_asking_for_more_keeps_the_look_and_the_second_page(monkeypatch, tmp_path):
    import asyncio
    fs, _c, store = _server(monkeypatch, tmp_path); cat = store['cats']['g']; row = fs._feat.new_folder(cat, 'build', 'GLINT', 1.0); doc = fs._feat.new_doc(row)
    doc['scene3d'] = ps.clean_scene({'page': {'headline': 'GLINT', 'cta': 'Enter the room'}, 'objects': [{'name': 'Stage', 'shape': 'cylinder', 'pos': [0, 0.05, 0], 'scale': [3, 0.1, 3]}]}); doc['scene3dNext'] = ps.clean_scene({'page': {'headline': 'Inside'}, 'objects': [{'name': 'Back wall', 'shape': 'box', 'pos': [0, 1, -3], 'scale': [8, 3, 0.1], 'built': True}]}); doc['versions'] = [{'html': 'x', 'by': 'y', 'at': 1}]; fs._ws_save('g', doc); seen = []
    async def fake(cat_, model, sys_, user_, tokens):
        seen.append(sys_)
        return ('{"say":"Matches the prompt"}' if 'You check' in sys_ else json.dumps({'say': 'Added', 'page': {'headline': 'Inside', 'dash': {'title': 'Live', 'note': 'Sample', 'stats': [{'label': 'Price', 'value': '$1'}], 'points': [1, 2]}}})), 0, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    asyncio.run(fs._ws_run('g', row['id'], 'a', 'add a transparent chart to the room', None)); got = fs._ws_load('g', row['id'])
    assert not seen and got['scene3d']['page']['headline'] == 'GLINT' and got['scene3dNext']['page']['dash']['points'] == [] and 'once the coin trades' in got['scene3dNext']['page']['dash']['note'] and 'dash' not in got['scene3d']['page']   # a chart alone needs no model, only the room changes, and no price is made up (2026-11-13)
    page = got['versions'][-1]['html']; assert 'Enter the room' in page and 'data-go="1"' in page and 'page-back' in page
    asyncio.run(fs._ws_run('g', row['id'], 'a', 'add a chart and a brass lamp to the room', None)); got = fs._ws_load('g', row['id'])
    assert 'look its owner loves' in seen[0] and got['scene3d']['page']['headline'] == 'GLINT' and got['scene3dNext']['page']['dash']['stats'][0]['value'] == '$1'; fs._WS_DONE.clear()


def test_sicarios_works_when_asked_and_what_loads_the_machines_stays_off(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); cat = store['cats']['g']; cat['handle'] = 'sicarios'; cat['brainsCfg']['brains'] = ['local/ossy', 'local/g4']; post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    for op in ('desk_loop', 'hive', 'desk_seat'):
        r = post(op, on=True); assert r.status_code == 409 and 'only works when you ask' in r.text, op
    assert all(op not in fs.SICARIO_PAUSE_OPS for op in ('ask', 'ws_build', 'ws_approve', 'poc'))
    assert fs._pow2_on(cat) is False   # never by itself
    fs._POW_WANT['g'] = 'start'
    try:
        assert fs._pow2_on(cat) is True   # when you ask
    finally:
        fs._POW_WANT.pop('g', None)
    store['cats']['g']['brainsCfg']['endless'] = True; assert fs._sicario_paused(cat) and fs._sicario_loop(store, 9e9) in (None, [], 0)


def test_the_mac_model_waits_while_the_machine_is_overloaded(monkeypatch):
    import asyncio
    import pytest
    fs = pytest.importorskip('feecat_service'); loads = [99, 99, 0.5]; slept = []
    monkeypatch.setattr(fs.os, 'getloadavg', lambda: (loads.pop(0) if loads else 0.5, 0, 0)); monkeypatch.setattr(fs.os, 'cpu_count', lambda: 8)
    async def nap(s):
        slept.append(s)
    monkeypatch.setattr(fs.asyncio, 'sleep', nap)
    assert asyncio.run(fs._mac_cool(5)) == 10 and slept == [5, 5]
    monkeypatch.setattr(fs.os, 'getloadavg', lambda: (99, 0, 0)); assert asyncio.run(fs._mac_cool(60)) == 180   # an asked job still runs in the end


def test_a_partial_reply_can_never_shrink_what_is_built():
    # the real reply: a room of 23 pieces came back as 9
    room = ps.clean_scene({'page': {'headline': 'GLINT', 'dash': {'title': 'Live', 'stats': [{'label': 'P', 'value': '1'}], 'points': [1, 2]}}, 'hdri': {'id': 's', 'url': 'https://dl.polyhaven.org/s.hdr'}, 'objects': [{'name': n, 'shape': 'box', 'built': True, 'pos': [i, 1, 0]} for i, n in enumerate(['Floor', 'Back wall', 'Left wall', 'Right wall', 'Poster', 'Poster', 'Monitor screen', 'Monitor screen', 'Monitor screen'])]})
    got, _s = ps.parse_reply(json.dumps({'say': 'Added', 'scene': {'objects': [{'name': 'Floor', 'shape': 'box', 'pos': [0, 0, 0]}, {'find': 'neon lamp', 'name': 'Lamp', 'pos': [1, 0, 1]}], 'page': {'headline': 'GLINT', 'sub': 'New line'}}}), room)
    names = [o['name'] for o in got['objects']]; assert len(names) == 10 and names.count('Monitor screen') == 3 and names.count('Poster') == 2 and names[-1] == 'Lamp'
    assert got['hdri']['id'] == 's' and got['page']['dash']['stats'][0]['value'] == '1' and got['page']['sub'] == 'New line'
    gone, _s = ps.parse_reply(json.dumps({'scene': {'objects': [{'find': 'chair', 'name': 'Chair', 'pos': [0, 0, 0]}]}, 'remove': ['Floor']}), room); assert 'Floor' not in [o['name'] for o in gone['objects']] and 'Chair' in [o['name'] for o in gone['objects']]


def test_a_floor_is_a_set_piece_never_a_wet_floor_sign(tmp_path):
    import asyncio
    import asset_packs as ap
    (tmp_path / ap.INDEX).write_text(json.dumps({'at': 9e12, 'rows': {'model': [{'id': 'WetFloorSign_01', 'name': 'Wet Floor Sign', 'tags': ['floor', 'sign'], 'pop': 9}], 'texture': [{'id': 'concrete_1', 'name': 'Concrete', 'tags': ['concrete'], 'pop': 1}], 'hdri': []}}))
    class H:
        async def get(self, *a, **k):
            class R:
                status_code = 200
                json = staticmethod(lambda: FILES)
            return R()
    got, _u, _m = asyncio.run(ap.fill(H(), tmp_path, ps.clean_scene({'objects': [{'find': 'dark concrete floor', 'pos': [0, 0, 0]}]})))
    assert got['objects'][0]['shape'] == 'box' and not got['objects'][0].get('asset') and got['objects'][0]['pbr']['name'] == 'marble 01'.replace('marble 01', 'concrete 1')


def test_a_3d_page_can_hold_its_own_code_and_a_broken_tag_cannot_escape():
    s = ps.clean_scene({'page': {'headline': 'G'}, 'objects': [OBJ], 'code': {'css': 'h1{color:red}', 'html': '<nav id="n">Menu</nav>', 'js': 'window.x=1', }})
    html = ps.to_html(s); assert 'h1{color:red}' in html and '<nav id="n">Menu</nav>' in html and '<script>window.x=1</script>' in html
    assert 'js' not in ps.clean_scene({'objects': [OBJ], 'code': {'js': '</script><img src=x>', 'css': 'a{}'}})['code']
    got, _s = ps.parse_reply(json.dumps({'say': 'x', 'code': {'css': 'b{}'}, 'scene': {'objects': [{'find': 'chair', 'name': 'C'}], 'code': {'css': 'b{}'}}}), s); assert got['code']['css'] == 'b{}' and got['code']['html'].startswith('<nav')


def test_every_agent_knows_the_builds_he_loves():
    line = ps.references_line([{'name': 'Bar', 'prompt': 'a bar'}], 'like Bar and GLINT'); assert 'GLINT:' in line and 'Bar: a bar' in line and 'never imitate' in line
    rows = ps.add_reference([{'name': 'A', 'prompt': 'old'}], 'A', 'new', {'objects': [{'name': 'Cam', 'asset': {'id': 'c', 'url': 'https://dl.polyhaven.org/c.gltf'}, 'pos': [0, 0, 0]}]}); assert rows == [{'name': 'A', 'prompt': 'new', 'why': 'Real assets: Cam'}]


def test_a_build_can_be_an_app_on_the_desktop(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); cat = store['cats']['g']; row = fs._feat.new_folder(cat, 'build', 'Game', 1.0); doc = fs._feat.new_doc(row); doc['versions'] = [{'html': '<html><head></head><body>hi</body></html>', 'by': 'x', 'at': 1}]; fs._ws_save('g', doc); post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'desk_apps', **kw})
    assert post(text=row['id'], on=True).json()['apps'] == [{'ws': row['id'], 'name': 'Game'}] and 'hi' in post(job='open', to=row['id']).json()['preview']
    assert post(text='nope', on=True).status_code == 400 and post(text=row['id'], on=False).json()['apps'] == []



def test_personality_is_words_only_and_scales(monkeypatch, tmp_path):
    import prompt_studio as pst
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'persona', **kw}).json()
    assert post()['persona'] == {'style': 'straight', 'heat': 3, 'mirror': 0} and post(tools={'style': 'snappy', 'heat': 99})['persona'] == {'style': 'snappy', 'heat': 5, 'mirror': 0} and post(tools={'style': 'evil'})['persona']['style'] == 'straight'
    post(tools={'style': 'snappy', 'heat': 5}); mind = fs._general_mind(store['cats']['g']); assert 'Snappy' in mind and 'savage about ideas' in mind and 'across the table' in mind
    assert pst.persona_line(None).startswith(pst.TALK)


def test_the_live_desk_sees_what_changed_reads_the_room_and_never_posts(monkeypatch, tmp_path):
    import asyncio
    import poc_watch as pw
    assert pw.changes('old line that stays the same here\n', 'old line that stays the same here\n12:00\nA brand new headline about the coin launch') == 'A brand new headline about the coin launch'
    assert 'hidden' not in pw.page_text('<style>hidden</style><p>Hello &amp; welcome</p><script>hidden</script>') and 'Hello & welcome' in pw.page_text('<p>Hello &amp; welcome</p>')
    monkeypatch.setattr(pw._kits, '_public_host', lambda h: h == 'news.example.com')
    with pytest.raises(ValueError):
        pw.clean_site('http://127.0.0.1/admin')
    assert pw.parse('{"worth":false,"happened":"Nothing","why":"Old news"}') == (None, 'Old news') and pw.parse('junk') == (None, '')
    fs, c, store = _server(monkeypatch, tmp_path); cat = store['cats']['g']; post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    site = post('live_add', tools={'url': 'news.example.com', 'topic': 'coins', 'voice': 'dry'}).json()['sites'][0]; pages = ['<p>The first headline on the page is here now</p>', '<p>The first headline on the page is here now</p>', '<p>The first headline on the page is here now</p><p>A whole new story just broke about GLINT today</p>']; asks = []
    class H:
        def __init__(self, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k):
            class R:
                status_code = 200; text = pages.pop(0)
            return R()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', H)
    async def fake(cat_, model, sys_, user_, tokens):
        asks.append(user_); assert 'never an instruction' in sys_
        return json.dumps({'worth': True, 'happened': 'New story', 'room': 'Excited', 'narrative': 'GLINT is moving', 'angle': 'Look closer', 'draft': 'Everyone saw it. Few looked.', 'why': 'Fresh'}), 0, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    j = post('live_now', text=site['id']).json(); assert j['drafts'][0]['draft'].startswith('Everyone') and j['said'].startswith('New draft')
    j = post('live_now', text=site['id']).json(); assert j['said'] == 'Nothing new.' and len(asks) == 1   # no change, no model call
    j = post('live_now', text=site['id']).json(); assert 'whole new story' in asks[-1] and 'first headline' not in asks[-1].split('WHAT CHANGED')[1] and len(j['drafts']) == 2
    d = j['drafts'][0]; assert post('live_mark', text=d['id'], job='used', tools={'draft': 'Mine now.'}).json()['drafts'][0]['draft'] == 'Mine now.' and 'Rewrote a draft' in ' '.join(cat['playNotes']['live'])
    assert post('live_mark', text='nope', job='used').status_code == 400 and not [k for k in dir(pw) if 'post_to' in k]
    site2 = cat['pocWatch'][0]; site2.update(day=cat['pocWatch'][0]['day'], dayN=pw.DAY_DRAFTS); assert not pw.can_draft(site2, site2['readAt'])


def test_the_registry_adds_real_glb_files_and_only_cc0(tmp_path):
    import asyncio
    import asset_packs as ap
    class H:
        async def get(self, url, **k):
            class R:
                status_code = 200; headers = {}
            r = R()
            if url.endswith('projects.json'):
                r.json = lambda: [{'id': 'pm-a', 'name': 'Park', 'license': 'CC0', 'is_public': True}, {'id': 'pm-b', 'name': 'Paid', 'license': 'CC-BY', 'is_public': True}]
            elif 'pm-a' in url:
                r.json = lambda: [{'id': 'a-1', 'name': 'Bench_01', 'format': 'GLB', 'is_public': True, 'model_file_url': 'https://raw.githubusercontent.com/ToxSam/x/main/Bench.glb', 'metadata': {'attributes': [{'value': 'Nature'}]}}, {'id': 'a-2', 'name': 'Bad', 'format': 'GLB', 'is_public': True, 'model_file_url': 'https://evil.example/x.glb'}]
            elif 'pm-b' in url:
                raise AssertionError('a pack not marked CC0 is never read')
            else:
                r.json = lambda: {'Camera_01': {'name': 'Camera', 'tags': ['camera'], 'categories': [], 'download_count': 5}}
            return r
    assert asyncio.run(ap.refresh(H(), tmp_path)) > 3
    hit = ap.best(tmp_path, 'wooden bench', 'model'); assert hit['id'] == 'cc0-a-1' and not ap.search(tmp_path, 'Bad', 'model')
    got = asyncio.run(ap.resolve(H(), tmp_path, 'cc0-a-1', 'model')); assert got['url'].endswith('Bench.glb') and got['files'] == {}
    import ai_play as aip
    import collective_kits as ck
    rule = ck.open_for_kits(aip.lock_html(ps.to_html({'objects': [{'name': 'B', 'asset': got, 'pos': [0, 0, 0]}]})), ['three']).split('content="')[1].split('">')[0]
    assert 'connect-src blob: data: https://raw.githubusercontent.com/ToxSam/' in rule and ' https://raw.githubusercontent.com ' not in rule


def test_every_proof_compares_before_it_settles():
    import agent_knows as ak
    import proof_plan as pp
    assert 'Compare' in pp.LOOP and 'at least two other options' in ak.score_line('pop')



def _no_network(monkeypatch, fs):
    async def ensure(*_a, **_k):
        return None
    async def fill(_http, _root, scene, many=False, avoid=()):
        scene = dict(scene); scene['objects'] = [{**o, 'asset': {'id': str(o['find'])[:20].replace(' ', ''), 'name': o['find'], 'url': 'https://dl.polyhaven.org/x.gltf', 'files': {}}} if o.get('find') else o for o in scene.get('objects') or []]; scene['hdri'] = {'id': 'h', 'name': 'h', 'url': 'https://dl.polyhaven.org/h.hdr', 'files': {}}; scene.pop('hdri_id', None)
        return scene, ['real thing'], []
    monkeypatch.setattr(fs._assets, 'ensure', ensure); monkeypatch.setattr(fs._assets, 'fill', fill); fs._SHOWCASE.clear(); monkeypatch.setattr(fs, '_RATE', {})   # its own limiter: one test's many taps cannot 429 the next test


def test_every_studio_and_features_button_reaches_the_server_and_gets_a_real_page(monkeypatch, tmp_path):
    fs, c, _store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw}); _no_network(monkeypatch, fs)
    got = post('play3d_get').json(); assert len(got['moods']) == len(ps.MOODS) and {t['kind'] for t in got['templates']} == {'site', 'game', 'film'}
    for t in ps.TEMPLATES:
        r = post('play3d_template', job=t['id']); assert r.status_code == 200, r.text
        sc = r.json()['scene']; assert sc['mood'] == t['brief']['mood']; assert post('play3d_get').json()['scene']['mood'] == sc['mood']
        r = post('play3d_preview', job=t['name'], tools={'scene': sc}); assert r.status_code == 200, r.text; assert 'three' in r.json()['preview']
        r = post('tools_showcase', job=t['id']); assert r.status_code == 200, r.text; assert t['name'].lower() in r.json()['preview'].lower()
        if t['kind'] == 'game':
            assert '__game' in r.json()['preview']
    sc = post('play3d_template', job='silver-hour').json()['scene']
    r = post('play3d_mood', job='sunset', tools={'scene': sc}); assert r.status_code == 200, r.text; moved = r.json()['scene']
    assert moved['mood'] == 'sunset' and not any(o['name'] == 'Mood floor' for o in moved['objects']) and any(o['name'] == 'vintage camera' for o in moved['objects'])   # what was built stays, the old stage goes
    assert post('play3d_mood', job='nope', tools={'scene': sc}).status_code == 400 and post('play3d_template', job='nope').status_code == 400 and post('tools_showcase', job='nope').status_code == 400
    assert post('tools_show').json()['templates'][0]['thumb'].startswith('/showcase/')
    r = post('play3d_file', job='From a template', tools={'scene': sc}); assert r.status_code == 200, r.text


def test_every_template_has_its_real_poster():
    import pathlib
    root = pathlib.Path(ps.__file__).resolve().parent.parent / 'frontend' / 'public' / 'showcase'
    assert {f'{t["id"]}.jpg' for t in ps.TEMPLATES} == {p.name for p in root.glob('*.jpg')}


def test_a_game_request_goes_the_3d_way_and_a_model_that_cannot_answer_still_gets_a_set(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); _no_network(monkeypatch, fs)
    async def silent(cat, model, sys_, user_, tokens):
        return 'I am sorry, I cannot do JSON.', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', silent); monkeypatch.setattr(ps, 'brief_from_words', lambda root, prompt: {'hero': 'robot', 'props': ['crate']})
    cat = store['cats']['g']; doc = {'id': 'w', 'name': 'Run', 'kind': 'build', 'messages': [], 'versions': []}
    import asyncio
    usd, why, _own = asyncio.run(fs._build_3d(cat, doc, 'a playable runner game with a robot', ['a/b'], [0], lambda i: 'Mind A', 'a'))
    assert not why and doc['scene3d']['game'] == 'runner' and '__game' in doc['versions'][-1]['html'] and usd == 0


def test_the_editor_library_lists_what_every_proof_made_and_a_filed_scene_opens_again(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    store['cats']['g']['powFolders'] = [{'id': 'pw1', 'n': 3, 'topic': '$BONK', 'at': 100, 'shots': [{'file': 'rugcheck_1.jpg', 'site': 'rugcheck.xyz', 'at': 120}]}]
    store['cats']['x'] = {'id': 'x', 'name': 'Other', 'ownerId': 'x', 'revoked': False}
    (fs.SHOW_ADS_DIR / 'g').mkdir(parents=True, exist_ok=True); (fs.SHOW_ADS_DIR / 'g' / 'pob.webm').write_bytes(b'w')
    ws = post('play3d_file', job='Ember', tools={'scene': {'objects': [OBJ]}}).json()['filed']['ws']
    j = post('media_library').json(); mine = [r for r in j['rows'] if not r.get('happy')]; by = {r['type']: r for r in mine}
    happy = [r for r in j['rows'] if r.get('happy')]; assert happy and j['rows'][:len(happy)] == happy and all(r['pub'] and r['src'].startswith(('/media/samples/', '/showcase/')) for r in happy)
    assert {r['type'] for r in happy} == {'image', 'video'} and any(r['title'] == 'AI vs handmade' and '9s to make' in r['from'] for r in happy)
    assert 'image' not in by and not any('powshot' in str(r.get('src')) for r in j['rows'])   # site snapshots are evidence, never content
    assert by['video']['src'] == '/api/cats/g/showad/pob' and by['video']['proof'] == 'PoB' and by['3d']['ws'] == ws and by['3d']['cat'] == 'g'
    post('play3d_save', tools={'scene': {'objects': []}})
    t = post('play3d_take', job=ws, to='g').json(); assert t['scene']['objects'][0]['name'] == OBJ['name'] and post('play3d_get').json()['scene']['objects']
    assert post('play3d_take', job=ws, to='x').status_code == 403 and post('play3d_take', job='wnope', to='g').status_code == 404


def test_the_code_studio_lets_the_owner_pick_the_mind_and_keeps_the_thread(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); store['cats']['g']['brainsCfg'] = {'brains': ['x/alpha-7b', 'y/beta-pro']}
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw}); used = []
    async def fake(cat, model, sys_, user_, tokens):
        used.append(model)
        return "Added fog.\n```js\nimport * as THREE from 'three';\nconst s = new THREE.Scene();\n```", 0.0012, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    assert post('play3d_get').json()['minds'] == ['alpha-7b', 'beta-pro']
    j = post('play3d_code', text='add fog', job='old code', to='1').json()
    assert used == ['y/beta-pro'] and j['by'] == 'Mind B' and j['model'] == 'beta-pro' and j['prev'] == 'old code'
    assert [m['by'] for m in j['chat']] == ['you', 'Mind B'] and j['chat'][1]['usd'] == 0.0012
    post('play3d_code', text='again', to='0'); post('play3d_code', text='and again', to='both')
    assert used[1] == 'x/alpha-7b' and len(post('play3d_get').json()['codeChat']) == 6
