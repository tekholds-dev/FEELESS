"""Slice 2 (owner 2026-11-18: "I'm unable to have 3D pieces built to be used in the current static build"). Reproduced on his real data: he
opened the 3D studio inside "trench build" on 2026-11-17 and put a real model on the stage, yet no folder anywhere ever carried one. Adding a
model only marked the folder: the page he was looking at never changed, and the model was mounted only when a build wrote a NEW version. His
trench edits mostly ended "Its changes did not match the page. Nothing changed", so nothing was ever mounted. A game folder ignored it, the
page ignored the size he set, and no record said whether a build really carried the piece. Network is faked here."""
import asyncio
import json

import pytest

import owner_models as om
import proof_record as prec

URL = 'https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/tombstone_01/tombstone_01_1k.gltf'
STONE = {'id': 'o1', 'name': 'Tombstone', 'asset': {'id': 'tombstone_01', 'name': 'Tombstone', 'url': URL, 'files': {}}, 'height': 1.6,
         'rot': [0, 0.61, 0], 'scale': [2, 1, 1], 'spin': 6, 'pos': [3, 0, 1]}
PAGE = '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'"><title>T</title></head><body><header>THE TRENCH</header><main>gone</main></body></html>'


def test_a_page_carries_the_exact_piece_its_turn_spin_and_proportions_and_the_record_reads_it_back():
    rows = [om.take(STONE, 1)]; html = om.mount(PAGE, rows); got = om.mounted(html)['tombstone_01']
    assert got['url'] == URL and got['rot'] == [0, 0.61, 0] and got['spin'] == 6 and got['shape'] == [1.0, 0.5, 0.5] and got['height'] == 1.6
    assert om.record(rows, html) == [{'id': 'tombstone_01', 'name': 'Tombstone', 'url': URL, 'height': 1.6, 'turn': [0, 0.61, 0], 'spin': 6, 'used': True,
                                      'places': 1, 'pagePlaces': 1, 'room': 1}]   # Slice 3 adds where it sits: this page has no section breaks, so the hero is all the room
    assert not om.record(rows, PAGE)[0]['used']   # a page without it is never counted as carrying it
    other = om.mount(PAGE, [om.take({**STONE, 'spin': 0}, 1)]); assert not om.record(rows, other)[0]['used']   # a different spin is not THAT piece
    assert om._shape([0.01, 0.01, 0.01]) == [1.0, 1.0, 1.0]   # a uniform size never shrinks the page's model to a dot
    assert "feelessModelOff = 'no-webgl'" in html   # a browser with no 3D keeps the page and its other spots working


def test_place_puts_it_in_the_page_now_with_its_lock_opened_and_takes_it_out_clean():
    rows = [om.take(STONE, 1)]; on = om.place(PAGE, rows)
    csp = on.split('Content-Security-Policy" content="')[1].split('"')[0]
    assert 'data-feeless-spot="code"' in on and 'three.module.js' in csp and 'https://dl.polyhaven.org' in csp and om.mounted(on)
    assert om.place(on, rows) == on   # placing it again changes nothing (no new page for nothing)
    off = om.place(on, []); assert 'feeless-models' not in off and 'data-feeless-spot' not in off and '<main>gone</main>' in off
    assert om.place(PAGE, []) == PAGE


def test_the_record_has_a_studio_check_only_for_a_postatic_given_pieces():
    f = {'kits': ['three'], 'studio': [{'name': 'Tombstone', 'height': 1.6, 'spin': 6, 'used': True}]}
    keys = [c['key'] for c in prec.checks('pos', f, ['local/ossy'])]; assert keys[-1] == 'studio' and prec.checks('pos', f, [])[-1]['ok']
    bad = prec.checks('pos', {**f, 'studio': [{'name': 'Tombstone', 'used': False}]}, [])[-1]; assert not bad['ok'] and 'missing from the page: Tombstone' in bad['why']
    assert [c['key'] for c in prec.checks('pos', {'kits': ['three']}, [])] == ['minds', 'sources', 'footprint', 'kits']   # no piece: the four checks as before
    assert 'studio' not in [c['key'] for c in prec.checks('poc', f, [])]


def test_a_filed_postatic_records_each_studio_piece_and_whether_its_page_has_it():
    import agent_features as feat
    rows = [om.take(STONE, 1)]; doc = {'id': 'w1', 'name': 'TRENCH', 'models3d': rows, 'versions': [{'html': om.mount(PAGE, rows), 'by': 'Mind A', 'at': 1}]}
    cat = {}; row = feat.file_static(cat, doc, 'Mind A', 2)
    assert row['studio'][0]['used'] and row['studio'][0]['turn'] == [0, 0.61, 0]
    assert 'studio' not in feat.file_static({}, {'id': 'w2', 'name': 'x', 'versions': [{'html': PAGE}]}, 'Mind A', 2)   # no piece, no field


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    return fs, TestClient(fs.app), store


def test_the_owners_bug_an_edit_that_lands_nothing_still_leaves_the_piece_in_the_current_page(monkeypatch, tmp_path):
    """His trench: a page already built, a model added, then an edit whose changes did not match. Before: no version, no model, ever."""
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    ws = post('feature_create', text='build', job='trench build').json()['folder']['id']
    doc = fs._ws_load('g', ws); doc['versions'] = [{'html': PAGE, 'by': 'Mind B', 'at': 1}]; doc['cfg'] = {'research': False, 'suggest': False, 'review': False}; fs._ws_save('g', doc)
    r = post('play3d_model_to', tools={'to': ws, 'obj': STONE}); assert r.status_code == 200, r.text
    assert r.json()['paged'] and 'page 2 shows it now' in r.json()['say']
    seen = []
    async def ask(cat, model, sys_, user_, tokens):   # the edit path: its changes never match the page
        seen.append(sys_); return '<<<<<<< SEARCH\nnot in the page\n=======\nx\n>>>>>>> REPLACE', 0.0, False
    async def page(*_a, **_k):
        return '', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs, '_ws_page', page)
    asyncio.run(fs._ws_run('g', ws, 'a', 'make it look alive', None))
    d = fs._ws_load('g', ws); html = d['versions'][-1]['html']
    assert len(d['versions']) == 2 and om.record(d['models3d'], html)[0]['used']   # nothing new landed, and the piece is still in the page he sees
    assert "THE OWNER'S OWN 3D MODELS" in seen[0]   # the minds were told to use it


def test_a_build_after_the_piece_keeps_it_and_files_a_record_that_proves_it(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    ws = post('feature_create', text='build', job='TRENCH').json()['folder']['id']
    doc = fs._ws_load('g', ws); doc['cfg'] = {'research': False, 'suggest': False, 'review': False}; fs._ws_save('g', doc)
    assert post('play3d_model_to', tools={'to': ws, 'obj': STONE}).json()['paged'] is False   # no page yet: its first build puts it in
    async def page(cat, model, sys_, user_, tokens, on_part=None):   # a mind that never marks a spot: code still puts it in
        return '<!doctype html><html><head><title>T</title></head><body><header>THE TRENCH</header><p>new</p></body></html>', 0.0, False
    async def reads(*_a, **_k):
        return '', []
    monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs, '_site_reads', reads)
    asyncio.run(fs._ws_run('g', ws, 'a', 'a landing page for the trench', None))
    d = fs._ws_load('g', ws); html = d['versions'][-1]['html']; assert om.record(d['models3d'], html)[0]['used'] and 'data-feeless-spot="code"' in html
    fs._ws_pass(store); f = store['cats']['g']['psFolders'][-1]
    assert f['studio'][0]['used'] and f['studio'][0]['spin'] == 6 and [ch for ch in f['proofChecks'] if ch['key'] == 'studio'][0]['ok']
    json.dumps(f)


def test_a_game_folder_carries_the_piece_after_its_playtest(monkeypatch):
    import feecat_service as fs
    DESIGN = {'title': 'Grave Run', 'genre': 'runner', 'engine': 'phaser', 'pitch': 'run', 'coreLoop': 'jump graves', 'controls': {'keys': 'space', 'touch': 'tap'},
              'win': 'score', 'lose': 'fall', 'progression': [], 'juice': [], 'entities': [], 'screens': []}
    monkeypatch.setattr(fs, '_ws_save', lambda *a: None); monkeypatch.setattr(fs, '_parts_used', lambda *a: [])
    async def ask(*a): return json.dumps(DESIGN), 0.0, False
    async def page(*a, **k): return '<!doctype html><html><head></head><body><canvas></canvas></body></html>', 0.0, False
    async def play(html, chromium):
        assert 'feeless-models' not in html   # the playtest runs on the game alone
        return {'ok': True, 'why': [], 'facts': {'fps': 60, 'changed': 900, 'after': {'state': 'play'}}}
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs._forge, 'playtest', play); monkeypatch.setattr(fs._fb, 'chromium_path', lambda: 'x')
    doc = {'id': 'w', 'messages': [], 'versions': [], 'models3d': [om.take(STONE, 1)]}
    asyncio.run(fs._build_game({'id': 'c'}, doc, 'a game', ['a', 'b'], [0, 1], lambda i: 'Mind ' + 'AB'[i], 'both'))
    assert om.record(doc['models3d'], doc['versions'][-1]['html'])[0]['used']


def test_a_test_postatic_on_sicario_gets_its_studio_piece_through_the_studio_step_before_it_builds(monkeypatch):
    fs = pytest.importorskip('feecat_service'); import fc_test
    store = {'cats': {'s': {'id': 's', 'name': "Sicario's", 'handle': 'sicarios', 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}, 'workspaces': []}}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_internal', lambda r: None)
    monkeypatch.setattr(fs, '_ws_save', lambda *a: None); monkeypatch.setattr(fs, 'keep_owned', lambda c: None); fs._TEST_ON.pop(('s', 'pos'), None)
    ops = []
    async def work(cid, p):
        ops.append((p.op, p.tools)); return {}
    async def piece(m):
        return {**STONE, 'height': m['height'], 'rot': [0, round(m['turn'] * 3.14159265 / 180, 4), 0]}
    monkeypatch.setattr(fs, '_cat_work', work); monkeypatch.setattr(fc_test, '_studio_piece', piece)
    out = asyncio.run(fc_test.test_proof_start(fc_test.TestIn(kind='pos', model={'id': 'tombstone_01', 'height': 1.6, 'turn': 35, 'spin': 6}), None))
    assert [o[0] for o in ops] == ['play3d_model_to', 'ws_build'] and ops[0][1]['to'] == out['ws'] and ops[0][1]['obj']['height'] == 1.6
    fs._TEST_ON.pop(('s', 'pos'), None)
