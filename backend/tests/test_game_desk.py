"""🎮 Game desk: the structure check catches real Lua and manifest mistakes, the mind's reply parses into files and plans, paths stay inside
the project, game binaries and secrets never get in, and the zip lays out ready to drop in."""
import io
import zipfile

import pytest

import game_desk as gd
import game_lab


def test_lua_check_balances_blocks_strings_and_comments():
    ok = "local t = {1, 2}\n-- an end in a comment\nlocal s = 'end'\nlocal l = [[ function ]]\nfunction a()\n  if x then\n    for i = 1, 3 do print(i) end\n  end\n  repeat x = x + 1 until x > 3\nend\nlocal h = `hash`\n"
    assert gd.lua_check(ok) is None
    assert 'never closed' in gd.lua_check('function a()\n  if x then\n  end\n')
    assert 'line 2' in gd.lua_check("print('a')\nend\n")
    assert 'string' in gd.lua_check('local s = "open\n')
    assert gd.lua_check('local t = {1, 2') is not None


def test_fivem_starter_from_the_lab_passes_and_a_broken_manifest_fails():
    r = game_lab.resource('my_garage', 'gta5', 'park cars')
    files = {**r['files'], 'INSTALL.md': r['install']}
    assert gd.passed(gd.check('fivem', files)), gd.check('fivem', files)
    bad = {**files, 'fxmanifest.lua': files['fxmanifest.lua'].replace("game 'gta5'", '') + "client_script 'missing.lua'\n"}
    rows = gd.check('fivem', bad)
    assert not gd.passed(rows) and any('missing.lua' in r['msg'] for r in rows) and any("needs game 'gta5'" in r['msg'] for r in rows)
    red = game_lab.resource('camp', 'rdr3')['files']
    assert all(r['ok'] for r in gd.check('redm', red) if r['file'] != 'INSTALL.md')


def test_vita_and_web_rules():
    assert not gd.passed(gd.check('gtasa_vita', {'data/handling.cfg': 'x', 'INSTALL.md': 'i'}))
    assert gd.passed(gd.check('gtasa_vita', {'ux0/data/gtasa/mods/fast/handling_lines.txt': 'x', 'INSTALL.md': 'i'}))
    cm = 'include("$ENV{VITASDK}/share/vita.cmake")\nset(VITA_TITLEID "FEEL00001")\nvita_create_vpk(x.vpk FEEL00001 x.self)\n'
    assert gd.passed(gd.check('vita', {'CMakeLists.txt': cm, 'INSTALL.md': 'i'}))
    assert not gd.passed(gd.check('web', {'game.js': '', 'INSTALL.md': 'i'}))


def test_paths_stay_inside_and_secrets_never_get_in():
    assert gd.clean_path('../../etc/passwd') == 'etc/passwd'
    assert gd.clean_path('/abs/x.lua') == 'abs/x.lua'
    for bad in ('.env', 'lib/libGTASA.so', 'game.apk', 'main.obb', 'run.exe'):
        assert gd.clean_path(bad) == ''
    p = gd.new_project('x', 'fivem')
    with pytest.raises(ValueError):
        gd.put_file(p, 'model.ydd', 'x')
    with pytest.raises(ValueError):
        gd.put_bin(p, 'big.ytd', gd.MAX_BIN + 1)
    assert 'stream/chain.ydd' in gd.put_bin(p, 'stream/chain.ydd', 1000)['bins']


def test_parse_files_drop_and_plan():
    raw = "SAY: Added a garage.\n=== FILE: client.lua ===\n```lua\nprint('hi')\n```\n=== END ===\n=== FILE: ../x.so ===\nbad\n=== END ===\n=== DROP: old.lua ===\n"
    ch, drops, say = gd.parse_files(raw)
    assert ch == {'client.lua': "print('hi')"} and drops == ['old.lua'] and say == 'Added a garage.'
    proj = gd.apply_reply({'files': {'old.lua': 'x', 'a.lua': 'y'}}, ch, drops)
    assert set(proj['files']) == {'a.lua', 'client.lua'}
    plan, s = gd.parse_plan("SAY: ok\n=== PLAN ===\n## Base\n- Write the manifest | fxmanifest.lua\n- Pick a framework | -\n## Test\n- Boot it | -\n=== END ===")
    assert [p['name'] for p in plan['phases']] == ['Base', 'Test'] and plan['phases'][0]['steps'][0] == {'do': 'Write the manifest', 'file': 'fxmanifest.lua'}


def test_prompt_carries_style_and_target_rules():
    p = {**gd.new_project('chains', 'fivem'), 'files': {'a.lua': 'print(1)'}}
    sys_, user = gd.prompt(p, 'fix', 'it crashes', style=[{'path': 'mine/x.lua', 'text': 'local MyThing = {}'}], log='SCRIPT ERROR: x')
    assert 'fxmanifest' in sys_ and "BUILDER'S OWN CODE" in sys_ and 'local MyThing' in sys_ and 'SCRIPT ERROR' in user and 'cheats' in sys_


def test_zip_layout_and_shelf():
    p = {**gd.new_project('My Garage', 'fivem'), 'files': {'fxmanifest.lua': 'x', 'client.lua': 'y'}}
    z = zipfile.ZipFile(io.BytesIO(gd.zip_bytes(p, {'stream/a.ytd': b'\x00'})))
    assert sorted(z.namelist()) == ['my_garage/client.lua', 'my_garage/fxmanifest.lua', 'my_garage/stream/a.ytd']
    v = {**gd.new_project('Fast', 'gtasa_vita'), 'files': {'ux0/data/gtasa/mods/a.txt': 'x'}}
    assert zipfile.ZipFile(io.BytesIO(gd.zip_bytes(v))).namelist() == ['ux0/data/gtasa/mods/a.txt']
    row = gd.shelf_row(p, 'cat1', 'Happy')
    shelf = gd.shelf_put([], row, True)
    assert gd.shelf_find(shelf, 'garage')[0]['by'] == 'Happy' and gd.shelf_put(shelf, row, False) == []
    f = gd.fork({**p, 'bins': {'a.ytd': {'size': 3}, 'm.glb': {'size': 0, 'url': 'https://dl.polyhaven.org/x.glb'}}})
    assert f['id'] != p['id'] and set(f['bins']) == {'m.glb'} and f['files'] == p['files']


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {g: {'id': g, 'name': g.upper(), 'ownerId': g, 'revoked': False, 'brainsCfg': {'brains': ['m/x', 'm/y']}} for g in ('g', 'h')}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    return fs, TestClient(fs.app)


def test_the_whole_desk_journey_build_check_fix_plan_upload_zip_share_fork(monkeypatch, tmp_path):
    import base64
    fs, c = _server(monkeypatch, tmp_path)
    post = lambda op, who='g', **kw: c.post(f'/api/cats/{who}/work', json={'ownerId': who, 'session': who, 'op': op, **kw})
    replies, seen = [], []

    async def fake(cat, model, sys_, user_, tokens):
        seen.append((model, sys_, user_))
        return replies.pop(0), 0.002, True
    monkeypatch.setattr(fs, '_ws_ask', fake)
    r = post('gdesk_new', text='my garage', job='fivem', tools={'starter': True}).json()
    pid = r['project']['id']; assert gd.passed(r['project']['checks']) and r['projects'][0]['id'] == pid
    replies.append("SAY: Broke it on purpose.\n=== FILE: client.lua ===\nfunction a()\n  if x then\nend\n=== END ===\n")
    r = post('gdesk_ask', job='build', i=1, text='add a menu', tools={'id': pid}).json()
    assert seen[-1][0] == 'm/y' and not gd.passed(r['project']['checks']) and r['project']['chat'][-1]['files'] == ['client.lua']
    replies.append("SAY: The if had no end.\n=== FILE: client.lua ===\nfunction a()\n  if x then end\nend\n=== END ===\n")
    r = post('gdesk_ask', job='fix', text='it errors', tools={'id': pid, 'log': 'SCRIPT ERROR: client.lua:4'}).json()
    assert 'SCRIPT ERROR' in seen[-1][2] and gd.passed(r['project']['checks'])
    replies.append("SAY: ok\n=== PLAN ===\n## Build\n- Write it | client.lua\n=== END ===")
    assert post('gdesk_ask', job='plan', text='plan it', tools={'id': pid}).json()['project']['plan']['phases'][0]['name'] == 'Build'
    assert post('gdesk_upload', tools={'id': pid, 'path': 'stream/chain.ytd', 'b64': base64.b64encode(b'\x01\x02').decode()}).json()['project']['bins']['stream/chain.ytd']['size'] == 2
    assert post('gdesk_upload', tools={'id': pid, 'path': 'libGTASA.so', 'b64': 'AA=='}).status_code == 400
    assert post('gdesk_upload', tools={'path': 'mine.lua', 'b64': base64.b64encode(b'local MyStyle = {}').decode(), 'learn': True}).json()['style'][0]['path'] == 'mine.lua'
    replies.append("SAY: ok\n=== FILE: server.lua ===\nprint(1)\n=== END ===\n")
    post('gdesk_ask', job='build', text='more', tools={'id': pid}); assert 'local MyStyle' in seen[-1][1]
    z = post('gdesk_zip', tools={'id': pid}).json()
    names = zipfile.ZipFile(io.BytesIO(base64.b64decode(z['b64']))).namelist()
    assert z['name'] == 'my_garage.zip' and 'my_garage/stream/chain.ytd' in names and 'my_garage/fxmanifest.lua' in names
    assert post('gdesk_shelf', who='h').json()['rows'] == []
    post('gdesk_share', on=True, tools={'id': pid})
    row = post('gdesk_shelf', who='h').json()['rows'][0]; assert row['by'] == 'G'
    f = post('gdesk_fork', who='h', tools={'id': pid, 'cat': 'g'}).json()['project']
    assert f['files']['server.lua'] == 'print(1)' and 'stream/chain.ytd' not in f['bins']   # uploaded bytes stay with their builder
    post('gdesk_share', on=False, tools={'id': pid})
    assert post('gdesk_fork', who='h', tools={'id': pid, 'cat': 'g'}).status_code == 404
    lab = post('gdesk_lab', tools={'log': {'game': 'Garage', 'platform': 'fivem', 'fps': 60, 'bugs': ['x'], 'verdict': 'ship'}}).json()
    assert lab['stats']['sessions'] == 1 and post('gdesk_lab').json()['stats']['ship'] == 1
    assert post('gdesk_get', who='h').json()['projects'][0]['name'].endswith('(fork)')


def test_a_file_from_my_files_goes_into_a_project(monkeypatch, tmp_path):
    import base64
    fs, c = _server(monkeypatch, tmp_path)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    pid = post('gdesk_new', text='chains', job='fivem').json()['project']['id']
    aid = post('assets_put', tools={'name': 'chain.ytd', 'b64': base64.b64encode(b'YTD!').decode()}).json()['row']['id']
    pr = post('gdesk_take', text=aid, tools={'id': pid, 'dir': 'stream/'}).json()['project']
    assert pr['bins']['stream/chain.ytd']['size'] == 4
    z = post('gdesk_zip', tools={'id': pid}).json()
    assert zipfile.ZipFile(io.BytesIO(base64.b64decode(z['b64']))).read('chains/stream/chain.ytd') == b'YTD!'
    assert post('gdesk_take', text='ffffffffffff', tools={'id': pid}).status_code == 404
