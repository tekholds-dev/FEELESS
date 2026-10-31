"""🔏 owner 2026-10-31: "where does a recovery phrase I download go? keep it sealed in the agent's drawer — or I paste it, and nobody ever sees it"."""
import asyncio

import pytest

import cat_browser as cb
import cat_vault as cv


def test_a_pasted_note_and_a_downloaded_file_are_sealed_listed_without_content_opened_and_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-master')
    cat = {'id': 'c1'}
    rows = cv.put_secret(cat, 'Proton recovery', text='apple banana cherry', site='proton.me', data_dir=tmp_path)
    rows = cv.put_secret(cat, 'recovery.pdf', data=b'%PDF-1.7 secret', name='proton-recovery-phrase.pdf', data_dir=tmp_path)
    assert [r['kind'] for r in rows] == ['note', 'file'] and 'sealed' not in str(rows) and 'apple' not in str(cat) and b'secret' not in (tmp_path / 'vault' / 'c1' / f"{rows[1]['id']}.seal").read_bytes()
    assert cv.open_secret(cat, rows[0]['id'], data_dir=tmp_path)['text'] == 'apple banana cherry'
    import base64
    got = cv.open_secret(cat, rows[1]['id'], data_dir=tmp_path)
    assert base64.b64decode(got['b64']) == b'%PDF-1.7 secret' and got['name'] == 'proton-recovery-phrase.pdf'
    assert cv.drop_secret(cat, rows[1]['id'], data_dir=tmp_path) == cv.public_secrets(cat) and not list((tmp_path / 'vault' / 'c1').glob('*.seal'))
    with pytest.raises(ValueError):
        cv.put_secret(cat, 'x', text='', data_dir=tmp_path)
    with pytest.raises(ValueError):
        cv.put_secret(cat, 'big', data=b'x' * (cv.FILE_MAX + 1), data_dir=tmp_path)


def test_downloads_in_a_window_you_used_are_read_once_and_deleted_from_the_cloud_browser():
    calls = []

    class R:
        def __init__(self, code, body=None, content=b''): self.status_code, self._b, self.content = code, body, content
        def json(self): return self._b

    class H:
        async def get(self, url, headers=None, **_k):
            calls.append(('GET', url))
            return R(200, {'data': [{'path': '/files/g1', 'size': 9}]}) if url.endswith('/files') else R(200, content=b'%PDF-ok')
        async def delete(self, url, headers=None, **_k):
            calls.append(('DELETE', url)); return R(204)
    got = asyncio.run(cb.collect_downloads(H(), {'STEEL_API_KEY': 'k'}, 's1', {'g1': 'proton-recovery-phrase.pdf'}))
    assert got == [('proton-recovery-phrase.pdf', b'%PDF-ok')] and calls[-1] == ('DELETE', f'{cb.STEEL}/sessions/s1/files/g1')
    assert asyncio.run(cb.collect_downloads(H(), {}, 's1')) == []   # no Steel key: nothing read


def test_the_public_agent_view_never_carries_sealed_items():
    import feecat_service as fs
    out = fs._no_keys({'id': 'c', 'secrets': [{'id': 'a', 'sealed': 'TOKEN'}], 'name': 'Scout'})
    assert 'secrets' not in out and 'TOKEN' not in str(out)
