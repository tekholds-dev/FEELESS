"""🗂 The studios' asset shelf: My files take only real media kinds and stay under their caps; Discover rows come from the source's own answer
with licence and creator; keeping a file only ever downloads from the free libraries (network faked); only its owner opens a file."""
import base64

import pytest

import agent_assets as aa


def test_kinds_caps_and_names():
    assert aa.kind_of('a.PNG') == 'image' and aa.kind_of('x.glb') == 'model' and aa.kind_of('run.exe') is None and aa.clean_name('../../x.sh') == ''
    rows, r = aa.add([], 'Neon <b>.png', 10)
    assert r['name'] == 'Neon b.png' and r['kind'] == 'image' and rows[0] is r
    with pytest.raises(ValueError):
        aa.add([], 'big.mp4', aa.MAX_FILE + 1)
    with pytest.raises(ValueError):
        aa.add([{'size': aa.MAX_TOTAL}], 'a.png', 1)
    assert aa.drop(rows, r['id']) == []


def test_commons_and_openverse_rows_keep_licence_and_refuse_other_hosts():
    j = {'query': {'pages': {'1': {'pageid': 1, 'index': 1, 'title': 'File:Neon.jpg', 'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/a/a4/Neon.jpg?utm_source=x', 'thumburl': 't', 'size': 5, 'extmetadata': {'LicenseShortName': {'value': 'CC BY-SA 4.0'}, 'Artist': {'value': '<a href="x">Ann</a>'}}}]}},
                       '2': {'pageid': 2, 'index': 2, 'title': 'File:Evil.jpg', 'imageinfo': [{'url': 'https://evil.example/x.jpg'}]}}}
    rows = aa.commons_rows(j)
    assert len(rows) == 1 and rows[0]['lic'] == 'CC BY-SA 4.0' and rows[0]['by'] == 'Ann' and rows[0]['name'] == 'Neon.jpg'
    a = aa.openverse_rows({'results': [{'id': 'z', 'title': 'Synth', 'url': 'https://cdn.freesound.org/previews/1/1-hq.mp3', 'license': 'cc0', 'license_version': '1.0', 'duration': 46829, 'creator': 'Bo', 'source': 'freesound'},
                                       {'id': 'y', 'url': 'http://bad/x.mp3'}]})
    assert [x['id'] for x in a] == ['ov-z'] and a[0]['lic'] == 'CC0 1.0' and a[0]['secs'] == 47


def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'G', 'ownerId': 'g', 'revoked': False}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    return fs, TestClient(fs.app)


def test_upload_keep_open_and_drop(monkeypatch, tmp_path):
    fs, c = _server(monkeypatch, tmp_path)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    r = post('assets_put', tools={'name': 'logo.png', 'b64': base64.b64encode(b'PNG!').decode()}).json()
    aid = r['row']['id']; assert r['counts']['image'] == 1 and r['used'] == 4
    got = c.get(f'/api/cats/g/asset/{aid}?ownerId=g&session=g')
    assert got.status_code == 200 and got.content == b'PNG!' and got.headers['content-type'] == 'image/png'
    assert c.get(f'/api/cats/g/asset/{aid}?ownerId=x&session=x').status_code in (401, 403)
    assert post('assets_put', tools={'name': 'run.exe', 'b64': 'AA=='}).status_code == 400
    assert post('assets_keep', tools={'url': 'https://evil.example/a.png', 'name': 'a'}).status_code == 400

    class R:
        status_code = 200; content = b'ID3sound'

    class H:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k):
            assert url.startswith('https://cdn.freesound.org/'); return R()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', H)
    k = post('assets_keep', tools={'url': 'https://cdn.freesound.org/previews/1/1-hq.mp3', 'name': 'Synth', 'lic': 'CC0 1.0', 'by': 'Bo', 'src': 'Freesound'}).json()
    assert k['row']['name'] == 'Synth.mp3' and k['row']['kind'] == 'audio' and k['row']['lic'] == 'CC0 1.0'
    assert len(post('assets_drop', text=aid).json()['rows']) == 1
    assert c.get(f'/api/cats/g/asset/{aid}?ownerId=g&session=g').status_code == 404
