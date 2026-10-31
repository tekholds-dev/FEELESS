"""☁ Each agent's own storage (FC08, owner 2026-10-31): owner-only add / list / delete, images only (real magic bytes), 1 GB + 40 files,
7-day clean after last use, attached files named in the task and handed to its browser's `upload` action. No network."""
import asyncio
import base64
import time

import pytest

import agent_files as af

@pytest.fixture(autouse=True)
def _signed_owner(monkeypatch):
    """A test session token IS its wallet here; the wallet owner lock itself is proven in test_agent_owner_lock.py."""
    import feecat_service as svc
    monkeypatch.setattr(svc, '_session_wallet', lambda s: str(s or ''))

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
URL = 'data:image/png;base64,' + base64.b64encode(PNG).decode()


def test_only_real_images_under_the_cap_are_kept(tmp_path):
    cat = {'id': 'c1', 'cloud': {'pool': 'feeless'}}
    row = af.save(tmp_path, cat, URL, 'coin <logo>.png')
    assert row['name'] == 'coin logo.png' and row['size'] == len(PNG) and (tmp_path / 'agent_files' / 'c1' / f"{row['id']}.png").read_bytes() == PNG
    for bad in ('data:text/html;base64,PGh0bWw+', 'data:image/png;base64,' + base64.b64encode(b'<svg onload=x>').decode(), 'data:image/svg+xml;base64,AAAA', 'nope'):
        with pytest.raises(ValueError):
            af.save(tmp_path, cat, bad)
    big = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG' + b'\x00' * (af.MAX_STILL + 1)).decode()
    with pytest.raises(ValueError, match='Too big'):
        af.save(tmp_path, cat, big)
    with pytest.raises(ValueError):
        af.save(tmp_path, {'id': '../etc', 'cloud': {'pool': 'feeless'}}, URL)                                     # no path escapes
    assert af.find(cat, '../../x') is None and af.find(cat, row['id']) is row


def test_quota_files_cap_and_the_seven_day_clean(tmp_path, monkeypatch):
    cat = {'id': 'c1', 'cloud': {'pool': 'feeless'}}
    monkeypatch.setattr(af, 'QUOTA', len(PNG) * 2)
    a = af.save(tmp_path, cat, URL, now=1000); af.save(tmp_path, cat, URL, now=1000)
    with pytest.raises(ValueError, match='cloud is full'):
        af.save(tmp_path, cat, URL)
    af.touch(cat, [a['id']], now=1000 + af.TTL)                                     # used again: 7 more days
    assert af.clean(tmp_path, {'cats': {'c1': cat}}, now=1000 + af.TTL + 5) == 1      # the other one was never used again
    assert [f['id'] for f in cat['files']] == [a['id']] and len(list((tmp_path / 'agent_files' / 'c1').iterdir())) == 1
    assert af.delete(tmp_path, cat, a['id']) and cat['files'] == [] and not af.delete(tmp_path, cat, a['id'])


def test_the_task_names_attached_files():
    assert af.task_note([]) == ''
    note = af.task_note([{'name': 'logo.png', 'mime': 'image/png', 'size': 4096}])
    assert 'logo.png (image/png, 4 KB)' in note and 'action "upload"' in note


def test_endpoints_are_owner_only_and_the_upload_reaches_its_browser(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {'kind': 'general', 'brains': ['m/a']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    c = TestClient(fs.app)
    assert c.post('/api/cats/g/files', json={'ownerId': 'intruder', "session": 'intruder', 'dataUrl': URL}).status_code == 403
    assert c.get('/api/cats/g/files?ownerId=intruder&session=intruder').status_code == 403
    r = c.post('/api/cats/g/files', json={'ownerId': 'me', "session": 'me', 'dataUrl': URL, 'name': 'logo.png'})
    assert r.status_code == 200, r.text
    f = r.json()['file']
    assert r.json()['quota'] == af.QUOTA and f['url'] == f"/api/cats/g/files/{f['id']}.png"
    got = c.get(f['url'])
    assert got.status_code == 200 and got.content == PNG and got.headers['content-type'] == 'image/png' and got.headers['x-content-type-options'] == 'nosniff'
    assert c.get('/api/cats/g/files/0123456789abcdef0123456789abcdef.png').status_code == 404
    assert c.post('/api/cats/g/files', json={'ownerId': 'me', "session": 'me', 'dataUrl': 'data:text/html;base64,PGh0bWw+'}).status_code == 400
    # ask with it attached → the task text names it and the task carries its path for `upload`
    monkeypatch.setattr(fs, '_work_live', lambda: True)
    monkeypatch.setattr(fs._lc, 'can_ask', lambda b: True)
    seen = {}
    def start(cid, cat, text, to=None, files=None):
        seen.update(text=text, files=files)
    monkeypatch.setattr(fs, '_work_start', start)
    r = c.post('/api/cats/g/work', json={'ownerId': 'me', "session": 'me', 'op': 'ask', 'text': 'launch a coin on pump.fun with my logo', 'files': [f['id'], 'bogus']})
    assert r.status_code == 200, r.text
    assert seen['files'] == [f['id']] and 'logo.png (image/png' in seen['text']
    assert c.post(f"/api/cats/g/files/{f['id']}/delete", json={'ownerId': 'me', "session": 'me'}).json()['files'] == []
    assert c.get(f['url']).status_code == 404


def test_the_upload_action_hands_the_file_to_the_page():
    import cat_browser as cb
    assert 'cannot upload' in asyncio.run(cb.ReaderPage(None).upload('Image', {'name': 'x.png'}))


def test_a_live_page_really_puts_the_file_in_the_field(tmp_path):
    """Real headless Chromium (skips where none is installed): by label, and by a button that opens the file chooser."""
    pw_ = pytest.importorskip('playwright.async_api')
    import cat_browser as cb
    (tmp_path / 'logo.png').write_bytes(PNG)
    f = {'name': 'logo.png', 'mime': 'image/png', 'path': str(tmp_path / 'logo.png')}

    async def run():
        async with pw_.async_playwright() as p:
            import glob
            exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome') or [None])[0]   # a preinstalled Chromium of another revision, when the pip one is missing
            try:
                b = await p.chromium.launch()
            except Exception:
                try:
                    b = await p.chromium.launch(executable_path=exe) if exe else None
                except Exception:
                    b = None
            if b is None:
                pytest.skip('no browser here')
            pg = await b.new_page()
            lp = cb.LivePage('cdp://unused'); lp._p = lp_page = pg
            await pg.set_content('<label for="i">Coin image</label><input id="i" type="file"><button onclick="document.getElementById(\'h\').click()">Pick art</button><input id="h" type="file" style="display:none">')
            lp._sync = lambda: asyncio.sleep(0, 'ok')
            out = await lp.upload('Coin image', f)
            got = await lp_page.evaluate("() => [document.getElementById('i').files[0].name, document.getElementById('i').files[0].size]")
            await pg.set_content('<button onclick="document.getElementById(\'h\').click()">Pick art</button><input id="h" type="file" style="display:none">')
            out2 = await lp.upload('Pick art', f)
            got2 = await lp_page.evaluate("() => document.getElementById('h').files[0].name")
            await b.close()
            return out, got, out2, got2
    out, got, out2, got2 = asyncio.run(run())
    assert out.startswith('(uploaded logo.png)') and got == ['logo.png', len(PNG)]
    assert out2.startswith('(uploaded logo.png)') and got2 == 'logo.png'
