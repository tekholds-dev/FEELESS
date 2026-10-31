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


def test_a_saved_sign_in_keeps_only_the_sites_own_newest_live_cookies_and_nothing_injectable():
    """🧼 owner 2026-10-31: "why does Proton have 80 cookies? clean them, encrypted, nothing a hacker can inject"."""
    now = 1_800_000_000
    ck = lambda name, dom, exp=now + 3600, **k: {'name': name, 'value': 'v', 'domain': dom, 'path': '/', 'expires': exp, 'httpOnly': True, 'size': 9, 'session': False, **k}
    ctx = {'cookies': [ck('AUTH-' + 'a' * 32, 'account.proton.me'), ck('REFRESH-' + 'a' * 32, 'account.proton.me'),
                       ck('AUTH-' + 'b' * 32, 'mail.proton.me', now + 7200), ck('AUTH-' + 'c' * 32, 'mail.proton.me', now + 60),   # mail: an older login
                       ck('Session-Id', '.proton.me'), ck('Session-Id', '.proton.me', now + 99999),                                 # the newest copy wins
                       ck('_ga', '.proton.me'), ck('_fbp', '.proton.me'), ck('IDE', '.doubleclick.net'), ck('NID', '.google.com'),     # trackers + other sites
                       ck('old', 'proton.me', now - 5), ck('evil', 'proton.me', value='x; Domain=.bank.com'), ck('nl\nname', 'proton.me'),  # expired · smuggling
                       ck('Theme', 'proton.me', -1, sameSite='Bogus', partitionKey='p')],
           'localStorage': {'https://account.proton.me': {'ui': '1', '_ga_x': '2'}, 'https://ads.example.com': {'id': '3'}}}
    out, st = cb.clean_context(ctx, 'proton.me', now=now)
    names = sorted((c['name'][:8], c['domain']) for c in out['cookies'])
    assert names == [('AUTH-aaa', 'account.proton.me'), ('AUTH-bbb', 'mail.proton.me'), ('REFRESH-', 'account.proton.me'), ('Session-', '.proton.me'), ('Theme', 'proton.me')]
    assert next(c for c in out['cookies'] if c['name'] == 'Session-Id')['expires'] == now + 99999
    theme = next(c for c in out['cookies'] if c['name'] == 'Theme')
    assert 'sameSite' not in theme and 'partitionKey' not in theme and 'size' not in theme and 'session' not in theme   # only the keys a browser takes
    assert out['localStorage'] == {'https://account.proton.me': {'ui': '1'}} and st == {'kept': 5, 'dropped': 9}
    assert cb.clean_context(ctx, 'x.com', now=now)[0]['cookies'] == []   # one site's sign-in never carries another's
    assert cb.site_base('web.telegram.org') == 'telegram.org' and cb.site_base('www.bbc.co.uk') == 'bbc.co.uk'


def test_stored_sign_ins_are_re_cleaned_and_a_tampered_one_is_dropped(monkeypatch):
    import json as _j
    import feecat_service as fs
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-only-master')
    now = __import__('time').time()
    good = {'cookies': [{'name': 'auth', 'value': 'v', 'domain': 'x.com', 'path': '/', 'expires': now + 999}, {'name': '_ga', 'value': 'v', 'domain': '.x.com', 'path': '/', 'expires': now + 999}], 'localStorage': {}}
    cat = {'id': 'c9', 'siteSessions': {'x.com': {'ctx': fs._ck.seal(_j.dumps(good), 'c9'), 'n': 2, 'at': 1}, 'bad.com': {'ctx': 'not-a-token', 'n': 1, 'at': 1}}}
    assert fs.heal_site_sessions(cat) and list(cat['siteSessions']) == ['x.com'] and cat['siteSessions']['x.com']['n'] == 1 and cat['siteSessions']['x.com']['dropped'] == 1
    assert [c['name'] for c in fs._site_ctx(cat)['cookies']] == ['auth'] and not fs.heal_site_sessions(cat)
