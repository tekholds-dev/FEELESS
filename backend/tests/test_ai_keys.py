"""🔑 AI API keys in HQ › Agents: tested, stored server-side, never shown back. Pure + the two owner routes (no network)."""
import asyncio
import json

import pytest

import ai_keys as aik
import reputation_service as rs

KEY = 'sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789wxyz'


def test_keys_providers_and_bases_are_checked():
    c = aik.clean('openai', f'  {KEY}\n', model='gpt-4o-mini')
    assert c == {'provider': 'openai', 'key': KEY, 'base': '', 'model': 'gpt-4o-mini'}
    for bad in ('', 'short', 'has space in it 1234567890', '"quoted-key-1234567890"', 'x' * 400):
        with pytest.raises(ValueError):
            aik.clean('openai', bad)
    with pytest.raises(ValueError):
        aik.clean('nope', KEY)                                                              # only the listed providers
    assert aik.clean('custom', KEY, 'https://api.together.xyz/v1/')['base'] == 'https://api.together.xyz/v1'
    for bad in ('http://api.x.com/v1', 'http://8.8.8.8/v1', 'http://169.254.169.254/v1', 'https://intranet.local/v1', 'https://api.x.com/v1?k=1', 'ftp://a.b'):
        with pytest.raises(ValueError):
            aik.clean('custom', KEY, bad)                                                   # never plain http to a public host, a metadata IP or a query URL
    assert aik.clean('custom', KEY, 'http://10.0.0.249:1236/v1')['base'] == 'http://10.0.0.249:1236/v1'   # LM Studio on the LAN
    with pytest.raises(ValueError):
        aik.clean('openai', KEY, model='gpt 4; rm -rf')


def test_the_page_only_ever_sees_set_and_the_last_four():
    env = {'OPENAI_API_KEY': KEY, 'AI_PROVIDER': 'openai', 'AI_MODEL': 'gpt-4o-mini', 'ANTHROPIC_API_KEY': 'sk-ant-0123456789abcdefghij'}
    st = aik.status(env)
    blob = json.dumps(st)
    assert KEY not in blob and KEY[:12] not in blob and 'sk-ant-0123' not in blob
    rows = {r['key']: r for r in st['providers']}
    assert rows['openai'] == {'key': 'openai', 'label': 'OpenAI', 'set': True, 'hint': '…wxyz', 'active': True}
    assert rows['anthropic']['set'] and not rows['anthropic']['active'] and not rows['gemini']['set']
    assert st['active'] == 'openai' and st['model'] == 'gpt-4o-mini' and st['used'] == 'advisory' and 'never places, sizes, blocks or sells anything; a stance moves the ranking (±10% at most) only once it is proven on its own judged record' in st['note']
    assert aik.status({'AI_PROVIDER': 'openai'})['active'] is None                               # a provider with no key is not active
    assert aik.scrub(f'boom {KEY} and {KEY[5:25]}', KEY).count('•••') >= 2 and KEY[5:17] not in aik.scrub(f'x {KEY[5:25]}', KEY)


def test_env_lines_and_clearing():
    c = aik.clean('custom', KEY, 'https://api.together.xyz/v1', 'meta-llama/Llama-3-70b')
    assert aik.env_lines(c) == [('AI_API_KEY', KEY), ('AI_PROVIDER', 'custom'), ('AI_MODEL', 'meta-llama/Llama-3-70b'), ('AI_BASE_URL', 'https://api.together.xyz/v1')]
    assert aik.env_lines(aik.clean('groq', KEY, model='llama-3.1-8b-instant'))[-1] == ('GROQ_MODEL', 'llama-3.1-8b-instant')   # the router reads each provider's own model
    assert aik.env_without('A=1\nOPENAI_API_KEY=old\n# OPENAI_API_KEY=older\nB=2', 'OPENAI_API_KEY') == 'A=1\n# OPENAI_API_KEY=old\n# OPENAI_API_KEY=older\nB=2'


class _Req:
    def __init__(self, body):
        self._b = body

    async def json(self):
        return self._b


def test_the_owner_routes_test_then_store_and_never_echo_the_key(monkeypatch):
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    audits = []
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    monkeypatch.setattr(rs, '_audit', lambda ad, me, kind, text: audits.append((kind, text)))
    for v in ('OPENAI_API_KEY', 'AI_PROVIDER', 'AI_MODEL', 'OPENAI_MODEL', 'AI_BASE_URL', 'AI_API_KEY'):
        monkeypatch.delenv(v, raising=False)
    calls = []

    async def ok(http, c):
        calls.append(c['provider']); return {'ok': True, 'ms': 120, 'models': ['gpt-4o-mini']}
    monkeypatch.setattr(rs._aik, 'probe', ok)
    out = asyncio.run(rs.admin_ai_key_set(_Req({'provider': 'openai', 'key': KEY, 'model': 'gpt-4o-mini'})))
    assert KEY not in json.dumps(out) and out['ok'] and out['active'] == 'openai' and out['models'] == ['gpt-4o-mini']
    assert rs.os.environ['OPENAI_API_KEY'] == KEY and rs.os.environ['AI_PROVIDER'] == 'openai' and calls == ['openai']
    assert audits == [('ai-key', 'openai saved')] and KEY not in json.dumps(audits)
    assert KEY not in json.dumps(asyncio.run(rs.admin_ai_key_status(None)))

    async def refused(http, c):
        return {'ok': False, 'ms': 80, 'err': 'OpenAI refused the key (401) — check it was copied whole and is active'}
    monkeypatch.setattr(rs._aik, 'probe', refused)
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.admin_ai_key_set(_Req({'provider': 'openai', 'key': KEY[::-1]})))
    assert e.value.status_code == 400 and 'Not saved' in e.value.detail and KEY[::-1] not in e.value.detail
    assert rs.os.environ['OPENAI_API_KEY'] == KEY                                                     # a refused key changes nothing
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_ai_key_set(_Req({'provider': 'custom', 'key': KEY, 'base': 'http://api.x.com/v1'})))
    gone = asyncio.run(rs.admin_ai_key_set(_Req({'provider': 'openai', 'clear': True})))
    assert 'OPENAI_API_KEY' not in rs.os.environ and gone['active'] is None and audits[-1] == ('ai-key', 'openai cleared')
