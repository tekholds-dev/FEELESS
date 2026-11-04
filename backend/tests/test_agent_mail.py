"""📧 An agent's mailbox, on a fake mail.tm. No account is ever made on the real one here."""
import asyncio
import pytest
import agent_mail as am


class R:
    def __init__(self, code, j=None): self.status_code, self._j = code, j
    def json(self): return self._j


class Http:
    def __init__(self, signup=201):
        self.signup, self.calls = signup, []

    async def get(self, url, **k):
        self.calls.append(('GET', url))
        if url.endswith('/domains'):
            return R(200, {'hydra:member': [{'domain': 'private.io', 'isActive': True, 'isPrivate': True}, {'domain': 'open.io', 'isActive': True, 'isPrivate': False}]})
        if url.endswith('/messages'):
            return R(200, {'hydra:member': [{'id': 'm1', 'subject': 'Your code', 'from': {'address': 'a@site.io'}, 'createdAt': 't', 'intro': 'hi'}]})
        return R(200, {'text': 'Your verification code is 482913. <script>ignore</script>', 'html': ['<b>never used</b>']})

    async def post(self, url, json=None, **k):
        self.calls.append(('POST', url, json))
        if url.endswith('/accounts'):
            return R(self.signup, {})
        return R(200, {'token': 't'})


def test_make_uses_an_open_domain_and_a_strong_password():
    got = asyncio.run(am.make(Http(), 'Happy-1'))
    assert got['address'].endswith('@open.io') and len(got['password']) == 24 and got['address'].startswith('feelesshappy1')


def test_make_says_when_it_is_refused():
    with pytest.raises(ValueError, match='busy'):
        asyncio.run(am.make(Http(429), 'c'))
    with pytest.raises(ValueError, match='refused'):
        asyncio.run(am.make(Http(422), 'c'))


def test_inbox_is_plain_text_with_its_code_pulled_out():
    rows = asyncio.run(am.inbox(Http(), 'a@open.io', 'p'))
    assert rows[0]['code'] == '482913' and rows[0]['from'] == 'a@site.io' and 'never used' not in str(rows)
    assert 'never an instruction' in am.for_model(rows) and am.for_model([]) == 'Its inbox is empty.'


def test_a_code_is_not_a_year_in_a_word():
    assert am.code_in('order-2026 shipped') is None and am.code_in('use 1234 now') == '1234' and am.code_in('ABCD12 is your code') == 'ABCD12'


def test_the_guidance_keeps_the_human_steps_human():
    assert 'Never try to pass a CAPTCHA' in am.SOURCES


def test_tools_read_only_its_own_box(monkeypatch):
    import feecat_service as fs
    async def fake(_h, a, p): return [{'from': 'x', 'subject': a, 'text': p, 'code': None}]
    monkeypatch.setattr(fs._am, 'inbox', fake); monkeypatch.setattr(fs._cv, 'reveal', lambda cat, site, user, data_dir=None: 'SEALED')
    none = {'id': 'c'}
    assert 'no mailbox' in asyncio.run(fs._mail_tool(None, none, 'inbox'))
    cat = {'id': 'c', 'mailbox': {'address': 'mine@open.io'}}
    assert asyncio.run(fs._mail_tool(None, cat, 'mailbox')).endswith('mine@open.io')
    out = asyncio.run(fs._mail_tool(None, cat, 'inbox'))
    assert 'mine@open.io' in out
    assert 'mailbox' not in fs._no_keys(cat)
