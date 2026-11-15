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
    assert post('gdesk_share', on=True, tools={'id': pid}).status_code == 400   # only your own work: the page asks first
    post('gdesk_share', on=True, tools={'id': pid, 'mine': True})
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


def test_blocked_files_and_the_project_cap():
    for bad in ('client.fxap', 'gta3.img', 'x.rpf', 'game.vpk', 'a/b.iso', '.env', 'lib.so'):
        assert gd.clean_path(bad) == ''
    with pytest.raises(ValueError):
        gd.put_bin(gd.new_project('x', 'fivem'), 'stream/x.rpf', 10)
    big = {f'f{i}.lua': 'x' * 90_000 for i in range(7)}
    with pytest.raises(ValueError):
        gd.apply_reply(gd.new_project('x', 'fivem'), big, [])


def test_undo_keeps_the_last_files():
    p = gd.put_file(gd.new_project('x', 'fivem'), 'a.lua', 'one')
    h = gd.snap([], p, 'before two', now=1); p2 = gd.put_file(p, 'a.lua', 'two')
    back, h2 = gd.undo(h, p2)
    assert back['files']['a.lua'] == 'one' and h2 == []
    with pytest.raises(ValueError):
        gd.undo([], p2)
    for i in range(10):
        h = gd.snap(h, p, str(i))
    assert len(h) == gd.UNDO_KEEP and h[0]['why'] == '9'


CONSOLE = """[    c-scripting-core] Creating script environments for my_garage
[           resources] Started resource my_garage
[ script:my_garage] SCRIPT ERROR: @my_garage/server.lua:12: attempt to index a nil value (global 'Config')
[ script:my_garage] > handler (@my_garage/server.lua:12)
[           resources] Started resource other_thing
[ script:other_thing] SCRIPT ERROR: @other_thing/x.lua:1: nope
"""


def test_read_console_from_a_real_server_log():
    p = {**gd.new_project('my garage', 'fivem'), 'files': {'server.lua': 'x', 'fxmanifest.lua': 'y'}}
    r = gd.read_console(CONSOLE, p)
    assert r['name'] == 'my_garage' and r['started'] and not r['ok']
    err = [x for x in r['rows'] if x['kind'] == 'error']
    assert not any(x['kind'] == 'warn' for x in r['rows'])   # the '> handler' stack frame is not a second problem
    assert len(err) == 1 and err[0]['file'] == 'server.lua' and err[0]['line'] == 12 and err[0]['known'] and 'nil value' in err[0]['msg']
    assert not any('other_thing' in x['msg'] for x in r['rows'])   # another resource's errors are not this one's
    ok = gd.read_console('[ resources] Started resource my_garage\n', p)
    assert ok['ok'] and 'no errors' in ok['verdict']
    none = gd.read_console('[ resources] Started resource something_else', p)
    assert not none['started'] and 'ensure my_garage' in none['verdict']
    miss = gd.read_console("Warning: could not find client_script 'cl.lua' for resource my_garage", p)
    assert miss['rows'][0]['kind'] == 'missing' and miss['rows'][0]['file'] == 'cl.lua' and not miss['rows'][0]['known']


def test_desk_undo_console_upload_folder_and_a_reply_that_lands_on_the_newest_files(monkeypatch, tmp_path):
    import base64
    fs, c = _server(monkeypatch, tmp_path)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    pid = post('gdesk_new', text='my garage', job='fivem', tools={'starter': True}).json()['project']['id']
    assert post('gdesk_get', tools={'id': pid}).json()['undo'] == 0

    async def fake(cat, model, sys_, user_, tokens):   # while the mind works, its builder saves another file
        st = fs._play_load('g', 'game'); pr = next(x for x in st['projects'] if x['id'] == pid)
        pr['files']['notes.md'] = 'mine'; fs._play_save('g', 'game', st)
        return "SAY: ok\n=== FILE: client.lua ===\nprint('new')\n=== END ===\n", 0.0, True
    monkeypatch.setattr(fs, '_ws_ask', fake)
    r = post('gdesk_ask', job='build', text='change it', tools={'id': pid}).json()
    assert r['project']['files']['client.lua'] == "print('new')" and r['project']['files']['notes.md'] == 'mine' and r['undo'] == 1
    r = post('gdesk_undo', tools={'id': pid}).json()
    assert "print('new')" not in r['project']['files']['client.lua'] and r['undo'] == 0
    assert post('gdesk_undo', tools={'id': pid}).status_code == 400
    up = post('gdesk_upload', tools={'id': pid, 'path': 'chain.ydd', 'dir': 'stream/', 'b64': base64.b64encode(b'YDD').decode()}).json()['project']
    assert 'stream/chain.ydd' in up['bins']
    up = post('gdesk_upload', tools={'id': pid, 'path': 'clothes.ymt', 'dir': 'stream/', 'b64': base64.b64encode(b'<x/>').decode()}).json()['project']
    assert up['files']['clothes.ymt'] == '<x/>'   # text by the desk's own list, whatever folder the page named for binaries
    con = post('gdesk_console', text=CONSOLE, tools={'id': pid}).json()['console']
    assert con['started'] and con['rows'][1]['file'] == 'server.lua'
    assert post('gdesk_console', text='  ', tools={'id': pid}).status_code == 400


def test_main_desk_proof_picker_focuses_the_proof_in_the_chat(monkeypatch, tmp_path):
    fs, c = _server(monkeypatch, tmp_path)
    cat = fs._load()['cats']['g']
    cat['powFolders'] = [{'id': 'w1', 'topic': 'Hold $BONK an hour', 'at': 1}]
    cat['psFolders'] = [{'id': 's1', 'topic': 'Tip page', 'ws': 'ws9', 'at': 2}]
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    r = post('desk_focus', job='pow', text='w1').json()
    assert cat['deskProof']['kind'] == 'pow' and cat['deskProof']['id'] == 'w1' and cat['deskProof']['name'] == 'Hold $BONK an hour'
    assert 'is on the desk' in r['chat'][-1]['text']
    post('desk_focus', job='postatic', text='s1')
    assert cat['deskProof']['kind'] == 'pos' and cat['deskProof']['ws'] == 'ws9'
    assert post('desk_focus', job='poe', text='x').status_code == 400
    assert post('desk_focus', job='pow', text='nope').status_code == 404
    assert c.post('/api/cats/g/work', json={'ownerId': 'h', 'session': 'h', 'op': 'desk_focus', 'job': 'pow', 'text': 'w1'}).status_code in (401, 403)
