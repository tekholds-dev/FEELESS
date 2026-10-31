"""☁ An agent's cloud is its OWNER's (owner 2026-10-30: "FEELESS will not fund any storage"): Google Drive / Dropbox through the provider's own
sign-in; FEELESS keeps only the refresh pass, sealed with the agent's own key. Attachments on the server: 100 MB, gone after 24 h. Faked HTTP."""
import base64
import hashlib

import pytest

PNG = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'0' * 64).decode()
MP4 = 'data:video/mp4;base64,' + base64.b64encode(b'\x00\x00\x00\x18ftypmp42' + b'0' * 64).decode()
ENV = {'GOOGLE_OAUTH_CLIENT_ID': 'gid', 'GOOGLE_OAUTH_CLIENT_SECRET': 'gsec'}


def test_attachments_are_a_small_24h_cache_not_storage(tmp_path):
    af = pytest.importorskip('agent_files')
    assert af.QUOTA == 100 * 1024 ** 2 and af.TTL == 86400
    cat = {'id': 'a1'}
    f = af.save(tmp_path, cat, PNG, 'logo.png', now=1000)
    assert af.read(tmp_path, cat, f['id']).startswith(b'\x89PNG') and af.save(tmp_path, cat, MP4, 'clip.mp4')['mime'] == 'video/mp4'
    assert af.clean(tmp_path, {'cats': {'a1': cat}}, now=1000 + 86401) >= 1 and af.find(cat, f['id']) is None
    with pytest.raises(ValueError):
        af.save(tmp_path, cat, 'data:video/mp4;base64,' + base64.b64encode(b'not a video at all').decode())


def test_the_sign_in_url_and_its_one_time_state():
    acl = pytest.importorskip('agent_cloud')
    with pytest.raises(ValueError, match='not set up'):
        acl.start('a1', 'dropbox', 'http://x/cb', env=ENV)
    url = acl.start('a1', 'gdrive', 'http://x/cb', env=ENV, now=100)
    assert url.startswith('https://accounts.google.com/') and 'drive.file' in url and 'access_type=offline' in url and 'gsec' not in url
    state = url.split('state=')[1].split('&')[0]
    assert acl.take_state(state, now=200) == ('a1', 'gdrive') and acl.take_state(state, now=200) is None   # once
    s2 = acl.start('a1', 'gdrive', 'http://x/cb', env=ENV, now=100).split('state=')[1].split('&')[0]
    assert acl.take_state(s2, now=100 + acl.STATE_TTL + 1) is None                                            # expired


class _R:
    def __init__(self, j, code=200):
        self._j, self.status_code = j, code

    def json(self):
        return self._j


class FakeGoogle:
    def __init__(self):
        self.files, self.calls = [], []

    async def post(self, url, **k):
        self.calls.append(url)
        if 'oauth2.googleapis.com/token' in url:
            d = k['data']
            return _R({'refresh_token': 'R-1'} if d['grant_type'] == 'authorization_code' else {'access_token': 'A-1'})
        if '/upload/drive/' in url:
            self.files.append({'id': f'f{len(self.files)}', 'name': 'coin.png', 'mimeType': 'image/png', 'size': '72'})
            return _R({'id': self.files[-1]['id'], 'name': 'coin.png'})
        return _R({'id': 'folder1'})                                   # folder create

    async def get(self, url, **k):
        if url.endswith('/about'):
            return _R({'storageQuota': {'usage': '1000', 'limit': '16106127360'}})
        if "mimeType = 'application/vnd.google-apps.folder'" in k['params'].get('q', ''):
            return _R({'files': [{'id': 'folder1'}]})
        return _R({'files': list(reversed(self.files))})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def test_connect_seals_the_pass_shows_its_space_and_keeps_a_file_in_the_owners_drive(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    g = FakeGoogle()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda *a, **k: g)
    cat = {'id': 'g', 'ownerId': 'b1', 'ownerWallet': 'W', 'name': 'Happy', 'positions': [], 'risk': {}, 'status': 'running', 'revoked': False, 'createdAt': 1,
           'brainsCfg': {'kind': 'general', 'brains': ['m/a']}}
    store = {'cats': {'g': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: 'W' if s == 'tok' else '')
    c = TestClient(fs.app)
    assert c.post('/api/cats/g/cloud/connect', json={'provider': 'gdrive'}).status_code == 401
    url = c.post('/api/cats/g/cloud/connect', json={'provider': 'gdrive', 'session': 'tok'}).json()['url']
    state = url.split('state=')[1].split('&')[0]
    r = c.get(f'/api/cats/cloud/callback?code=C&state={state}', follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'].endswith('cloud=ok')
    assert cat['cloudLink']['sealed'].startswith('v2:') and 'R-1' not in str(cat)                       # the refresh pass, sealed per agent
    assert c.get(f'/api/cats/cloud/callback?code=C&state={state}', follow_redirects=False).headers['location'].endswith('cloud=failed')   # state once
    fid = c.post('/api/cats/g/files', json={'session': 'tok', 'dataUrl': PNG, 'name': 'coin.png'}).json()['file']['id']
    assert c.post(f'/api/cats/g/files/{fid}/keep', json={'session': 'tok'}).json()['kept']['name'] == 'coin.png'
    o = c.get('/api/cats/g/cloud?session=tok').json()
    assert o['link']['label'] == 'Google Drive' and o['total'] == 16106127360 and o['recent'][0]['name'] == 'coin.png'
    assert 'sealed' not in str(o) and c.get('/api/cats/g/cloud').status_code == 401
    assert c.get('/api/cats/g?session=nope').text.find('cloudLink') == -1                               # a visitor never sees it
    assert c.post('/api/cats/g/cloud/disconnect', json={'session': 'tok'}).json() == {'ok': True} and 'cloudLink' not in cat
    assert [x['what'] for x in cat['vaultLog']] == ['cloud connected', 'cloud disconnected']


def test_a_reveal_needs_a_fresh_wallet_signature(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from nacl.signing import SigningKey
    import base58
    sk = SigningKey.generate(); w = base58.b58encode(bytes(sk.verify_key)).decode()
    sig = base64.b64encode(sk.sign(fs.reveal_message('g', 'x.com', 1000).encode()).signature).decode()
    assert fs.reveal_ok('g', 'x.com', 1000, sig, w, now=1060)
    assert not fs.reveal_ok('g', 'x.com', 1000, sig, w, now=1200)          # stale
    assert not fs.reveal_ok('g', 'y.com', 1000, sig, w, now=1060)          # another site
    assert not fs.reveal_ok('h', 'x.com', 1000, sig, w, now=1060)          # another agent


def test_owner_control_needs_a_sign_in_from_the_last_day(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    tok = 't'; h = hashlib.sha256(tok.encode()).hexdigest()
    monkeypatch.setattr(fs._real, 'load_sessions', lambda p: {'s': {h: {'address': 'W', 'exp': 10_000 + fs.SESSION_TTL_S}}})
    assert fs._fresh_session_wallet(tok, now=10_000 + 3600) == 'W'
    assert fs._fresh_session_wallet(tok, now=10_000 + 2 * 86400) == ''    # still a valid chat session, too old to drive an agent
