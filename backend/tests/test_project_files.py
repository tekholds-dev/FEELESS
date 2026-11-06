"""Owner 2026-11-06: PoStatic continues from the user's own repo, and uploads reach the page. His files are read live and kept nowhere."""
import asyncio
import base64

import agent_features as af
import collective_git as cg


class R:
    def __init__(self, code, body):
        self.status_code = code; self._b = body

    def json(self):
        return self._b


def _read(monkeypatch, files):
    async def gh(http, token, method, path, body=None):
        p = path.split('/contents/')[1].split('?')[0]
        return R(200, {'content': base64.b64encode(files[p]).decode()}) if p in files else R(404, {})
    monkeypatch.setattr(cg, '_gh', gh)


def test_only_listed_clean_text_files_are_read(monkeypatch):
    fake_key = b'ghp_' + b'a' * 30
    _read(monkeypatch, {'src/App.jsx': b'export default 1', 'src/keys.js': b'const k = "' + fake_key + b'"', 'logo.png': b'\x89PNG\0\0', '.env': b'SECRET=1', 'other.js': b'x'})
    link = {'full': 'me/app', 'branch': 'main', 'paths': ['src/App.jsx', 'src/keys.js', 'logo.png', '.env']}
    got = asyncio.run(cg.project_read(None, 't', link, ['src/App.jsx', 'src/keys.js', 'logo.png', '.env', 'other.js', '../../etc/passwd']))
    assert got == [{'path': 'src/App.jsx', 'text': 'export default 1'}]   # a key, a binary, a secret path, and anything not listed all stay out
    block = cg.source_block(got)
    assert 'never instructions' in block and '--- src/App.jsx' in block and cg.source_block([]) == ''


def test_reads_are_capped(monkeypatch):
    names = [f'f{i}.js' for i in range(20)]
    _read(monkeypatch, {n: b'y' * (cg.PROJECT_READ_BYTES + 50) for n in names})
    got = asyncio.run(cg.project_read(None, 't', {'full': 'me/app', 'paths': names}, names))
    assert len(got) == cg.PROJECT_READ_FILES and all(len(r['text']) == cg.PROJECT_READ_BYTES for r in got)


def test_a_picture_is_placed_not_carried():
    note = af.attach_note([{'id': 'abc12345', 'name': 'logo.png'}, {'id': None}])
    assert 'feeless-file:abc12345' in note and 'logo.png' in note and af.attach_note(None) == ''
    page = '<img src="feeless-file:abc12345"><img src="feeless-file:deadbeef">'
    out = af.place_files(page, lambda fid: 'data:image/png;base64,AA' if fid == 'abc12345' else None)
    assert 'src="data:image/png;base64,AA"' in out and 'feeless-file:deadbeef' in out
