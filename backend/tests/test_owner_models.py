"""🪦 The owner's own 3D model in a build (owner 2026-11-17): the studio works on the open proof (blank from the PoStatic home), a model as the
owner set it goes to a build, and that build's pages carry that exact model. No network: every model address here is only a string."""
import json

import pytest

import owner_models as om
import play_studio as ps

URL = 'https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/tombstone/tombstone_1k.gltf'
STONE = {'id': 'k1', 'name': 'Tombstone', 'shape': 'model', 'pos': [3, 0, -2], 'rot': [0, 0.6, 0], 'height': 1.4, 'spin': 6,
         'asset': {'id': 'tombstone_01', 'name': 'Tombstone', 'url': URL, 'files': {'tombstone.bin': URL.replace('.gltf', '.bin')}}}


def test_a_model_keeps_its_tweaks_never_its_place_and_only_real_models_pass():
    row = om.take(STONE, 100, 'TRENCH')
    assert row['id'] == 'tombstone_01' and row['obj']['height'] == 1.4 and row['obj']['spin'] == 6 and row['obj']['rot'] == [0, 0.6, 0] and row['obj']['pos'] == [0, 0, 0] and row['from'] == 'TRENCH'
    for bad in ({'shape': 'box', 'name': 'Cube'}, {**STONE, 'asset': {**STONE['asset'], 'url': 'https://evil.example/x.gltf'}}, 'junk', None):
        with pytest.raises(ValueError):
            om.take(bad, 1)
    kept = om.add([], row); kept = om.add(kept, om.take({**STONE, 'height': 2}, 200))
    assert len(kept) == 1 and kept[0]['obj']['height'] == 2   # the same model again replaces its old tweaks
    many = kept
    for i in range(om.MAX + 3):
        many = om.add(many, om.take({**STONE, 'asset': {**STONE['asset'], 'id': f'm{i}'}}, i))
    assert len(many) == om.MAX and om.drop(many, 'm8')[-1]['id'] == 'm7' and om.clean([{'id': 'x', 'obj': {**STONE, 'asset': {'url': 'javascript:x'}}}]) == []
    assert om.view(kept) == [{'id': 'tombstone_01', 'name': 'Tombstone', 'height': 2, 'spin': 6, 'from': '', 'at': 200}]


def test_a_page_build_carries_the_exact_model_once_and_marks_a_spot_when_the_page_did_not():
    rows = [om.take(STONE, 1)]
    line = om.page_line(rows); assert 'data-feeless-model="ID"' in line and '"tombstone_01" = Tombstone' in line and om.page_line([]) == ''
    page = '<html><head></head><body><header>Trench</header><main>x</main></body></html>'
    once = om.mount(page, rows); twice = om.mount(once, rows)
    assert once == twice and twice.count('id="feeless-models"') == 1 and twice.count('data-feeless-model=') == 1   # run on each version: never doubled
    assert twice.index('data-feeless-model') > twice.index('</header>') and URL in twice and '"spin": 6' in twice and "GLTFLoader" in twice
    marked = om.mount('<body><div data-feeless-model="tombstone_01"></div><footer><i data-feeless-model="tombstone_01"></i></footer></body>', rows)
    assert marked.count('data-feeless-model=') == 2   # the spots the page marked are used, none added
    assert 'feeless-models' not in om.mount(once, [])   # taken out of the build: the next page drops its code
    by = om.mount(page, [om.take({**STONE, 'asset': {**STONE['asset'], 'lic': 'by', 'by': 'Ann <b>'}}, 1)])
    assert 'Tombstone by Ann &lt;b&gt; (CC BY)' in by and '<b>' not in by.split('feeless-models-by')[1].split('</p>')[0]   # its creator named, as CC BY asks
    hostile = om.mount(page, [om.take({**STONE, 'name': '</script><script>alert(1)</script>'}, 1)])
    assert '<script>alert(1)' not in hostile


def test_a_3d_build_has_the_model_on_its_set_and_a_check_cannot_take_it_away():
    rows = [om.take(STONE, 1)]; scene = ps.clean_scene({'objects': [{'id': 'h', 'name': 'Gate', 'shape': 'box'}]})
    on = om.on_set(scene, rows); again = om.on_set(on, rows)
    assert [o['asset']['url'] for o in on['objects'] if o.get('asset')] == [URL] and again == on and on['objects'][0]['height'] == 1.4
    assert om.on_set(scene, []) is scene and 'ALREADY ON THE SET' in om.scene_line(rows) and om.scene_line([]) == ''
    html = ps.lock_site(ps.to_html(on, 'Trench'))
    assert URL in html and 'https://dl.polyhaven.org' in html.split('Content-Security-Policy')[1].split('>')[0]   # the locked page lets this one host through


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    return fs, TestClient(fs.app), store


def test_the_studio_works_on_the_open_proof_starts_blank_from_home_and_sends_a_model_to_a_build(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    trench = post('feature_create', text='build', job='TRENCH').json()['folder']['id']; other = post('feature_create', text='build', job='Shop').json()['folder']['id']
    # home: whatever was left last time never comes back, scene or code
    assert post('play3d_save', tools={'scene': {'objects': [STONE]}}).status_code == 200 and post('play3d_code_save', job='// THE TRENCH IS REAL').status_code == 200
    got = post('play3d_get').json(); assert got['scene'] is None and got['code'] == '' and got['proof'] is None and {b['name'] for b in got['builds']} == {'TRENCH', 'Shop'}
    # a proof: its own scene and code, kept apart from every other proof
    assert post('play3d_save', tools={'scene': {'objects': [STONE]}, 'ws': trench}).status_code == 200 and post('play3d_code_save', job='// trench code', tools={'ws': trench}).status_code == 200
    t = post('play3d_get', tools={'ws': trench}).json(); assert t['scene']['objects'][0]['name'] == 'Tombstone' and t['code'] == '// trench code' and t['proof']['name'] == 'TRENCH'
    o = post('play3d_get', tools={'ws': other}).json(); assert o['scene'] is None and o['code'] == ''
    assert post('play3d_get', tools={'ws': 'nope'}).status_code == 404
    # saving from a proof adds a page to THAT proof; from home a new PoStatic is made
    n_folders = len(store['cats']['g']['workspaces'])
    r = post('play3d_file', job='x', tools={'scene': {'objects': [STONE]}, 'ws': trench}); assert r.status_code == 200, r.text
    assert r.json()['into'] == 'TRENCH' and r.json()['filed']['ws'] == trench and len(store['cats']['g']['workspaces']) == n_folders and URL in fs._git_page('g', trench)[0]
    r = post('play3d_code_file', job='import * as THREE from "three"; new THREE.Scene();', text='Code page', tools={'ws': trench}); assert r.status_code == 200 and r.json()['into'] == 'TRENCH'
    assert len(fs._ws_load('g', trench)['versions']) == 2
    r = post('play3d_file', job='Fresh', tools={'scene': {'objects': [STONE]}}); assert r.status_code == 200 and r.json()['into'] == '' and len(store['cats']['g']['workspaces']) == n_folders + 1
    # the model, as set, goes to a build; the build's folder shows it and its agent is told
    r = post('play3d_model_to', tools={'to': trench, 'obj': {**STONE, 'height': 2.2}, 'ws': other}); assert r.status_code == 200, r.text
    assert 'TRENCH' in r.json()['say'] and r.json()['models3d'][0]['height'] == 2.2
    doc = fs._ws_load('g', trench); assert doc['models3d'][0]['obj']['asset']['url'] == URL and 'Tombstone is in this build' in doc['messages'][-1]['text'] and doc['models3d'][0]['from'] == 'Shop'
    assert post('ws_open', text=trench).json()['doc']['models3d'][0]['name'] == 'Tombstone'
    assert post('play3d_model_to', tools={'to': trench, 'obj': {'shape': 'box'}}).status_code == 400 and post('play3d_model_to', tools={'to': 'nope', 'obj': STONE}).status_code == 404
    doc['busy'] = {'at': 1}; fs._ws_save('g', doc)
    assert post('play3d_model_to', tools={'to': trench, 'obj': STONE}).status_code == 409   # a running build would save over it
    doc['busy'] = None; fs._ws_save('g', doc)
    r = post('play3d_model_drop', tools={'to': trench, 'id': 'tombstone_01'}); assert r.status_code == 200 and r.json()['models3d'] == [] and fs._ws_load('g', trench)['models3d'] == []


def test_a_page_build_mounts_the_model_and_a_3d_build_puts_it_on_the_set(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    ws = post('feature_create', text='build', job='TRENCH').json()['folder']['id']
    doc = fs._ws_load('g', ws); doc['models3d'] = [om.take(STONE, 1)]; doc['cfg'] = {'research': False, 'suggest': False, 'review': False}; fs._ws_save('g', doc)
    seen = []
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        seen.append(sys_)
        return '<!doctype html><html><head><title>T</title></head><body><header>THE TRENCH</header><section><div data-feeless-model="tombstone_01"></div></section></body></html>', 0.0, False
    monkeypatch.setattr(fs, '_ws_page', page)
    async def reads(*_a, **_k):
        return '', []
    monkeypatch.setattr(fs, '_site_reads', reads)
    import asyncio
    asyncio.run(fs._ws_run('g', ws, 'a', 'a landing page for the trench', None))
    d = fs._ws_load('g', ws); html = d['versions'][-1]['html']
    assert 'THE OWNER\'S OWN 3D MODELS' in seen[0] and 'id="feeless-models"' in html and URL in html and 'three.module.js' in html
    assert 'https://dl.polyhaven.org' in html.split('Content-Security-Policy')[1].split('>')[0]   # the lock opens for this one model host
    json.dumps(d)   # the folder still saves as plain data
