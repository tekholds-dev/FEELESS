"""OpenAI-compatible base URLs: http only for localhost / 127.0.0.1 / private LAN IPv4; https for every public host."""
import asyncio

import ai_keys
import ai_router


OK = ['http://127.0.0.1:1234/v1', 'http://localhost:1234/v1', 'http://10.0.0.249:1236/v1', 'http://10.1.2.3:1236/v1',
      'http://192.168.1.20:1236/v1', 'http://172.16.0.5:1236/v1', 'http://172.31.255.1:1236/v1', 'http://[::1]:1234/v1',
      'https://api.together.xyz/v1', 'https://10.0.0.249:1236/v1']
BAD = ['http://api.together.xyz/v1', 'http://8.8.8.8:1234/v1', 'http://172.32.0.1:1236/v1', 'http://172.15.0.1:1236/v1',
       'http://169.254.169.254/v1', 'http://0.0.0.0:1234/v1', 'http://192.169.1.1/v1', 'https://8.8.8.8/v1', 'https://box.local/v1',
       'ftp://10.0.0.249/v1', 'http://10.0.0.249:1236/v1?x=1', 'http://user@10.0.0.249/v1', 'http://10.0.0.249:99999/v1', '']


def test_private_http_passes_and_public_http_fails():
    for u in OK:
        assert ai_keys.base_check(u) == (u, None), u
    for u in BAD:
        b, why = ai_keys.base_check(u)
        assert b is None and why, u
    assert 'https' in ai_keys.base_check('http://api.together.xyz/v1')[1]
    assert ai_keys.clean_base('http://10.0.0.249:1236/v1/') == 'http://10.0.0.249:1236/v1'


def test_local_and_custom_provider_accept_the_lan_lm_studio():
    env = {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://10.0.0.249:1236/v1', 'LOCAL_LLM_MODEL': 'google/gemma-4-e4b'}
    p = ai_router.provider(env, 'local')
    assert p['why'] is None and p['base'] == 'http://10.0.0.249:1236/v1'
    p = ai_router.provider({**env, 'LOCAL_LLM_BASE_URL': 'http://example.com:1236/v1'}, 'local')
    assert p['why'] and 'https' in p['why']
    c = ai_router.provider({'AI_API_KEY': 'k' * 20, 'AI_BASE_URL': 'http://192.168.1.9:1234/v1', 'AI_MODEL': 'qwen'}, 'custom')
    assert c['why'] is None
    c = ai_router.provider({'AI_API_KEY': 'k' * 20, 'AI_BASE_URL': 'http://example.com/v1', 'AI_MODEL': 'qwen'}, 'custom')
    assert c['why'] and 'https' in c['why']


class _R:
    def __init__(self, code, text=''):
        self.status_code, self.headers, self._t = code, {}, text

    def json(self):
        return {'choices': [{'message': {'content': self._t}}]}


class _H:
    def __init__(self):
        self.models = []

    async def post(self, url, json=None, headers=None, **kw):
        self.models.append(json['model'])
        return _R(404) if json['model'] == 'google/gemma-4-e4b' else _R(200, 'ok from qwen')


def test_local_fallback_model_answers_when_the_primary_is_refused():
    env = {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://10.0.0.249:1236/v1', 'LOCAL_LLM_MODEL': 'google/gemma-4-e4b',
           'LOCAL_LLM_FALLBACK_MODEL': 'qwen2.5-7b-instruct-mlx'}
    r, h = ai_router.Router(), _H()
    text, err = asyncio.run(r._call(h, ai_router.provider(env, 'local'), env, [{'role': 'user', 'content': 'hi'}], 0))
    assert err is None and text == 'ok from qwen' and h.models == ['google/gemma-4-e4b', 'qwen2.5-7b-instruct-mlx']
    assert r.lastModel['local'] == 'qwen2.5-7b-instruct-mlx'
    h2 = _H()
    _t, err = asyncio.run(r._call(h2, ai_router.provider({**env, 'LOCAL_LLM_FALLBACK_MODEL': ''}, 'local'), env | {'LOCAL_LLM_FALLBACK_MODEL': ''}, [{'role': 'user', 'content': 'hi'}], 0))
    assert err and h2.models == ['google/gemma-4-e4b']


class _G:
    def __init__(self):
        self.hdr = []

    async def get(self, url, headers=None, **kw):
        self.hdr.append(headers)
        return type('R', (), {'status_code': 200, 'json': lambda s: {'data': [{'id': 'google/gemma-4-e4b'}]}})()

    async def post(self, url, json=None, headers=None, **kw):
        self.hdr.append(headers)
        return _R(200, 'hi')


def test_lm_studio_token_is_sent_as_a_bearer_and_never_shown():
    env = {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://10.0.0.249:1236/v1', 'LOCAL_LLM_MODEL': 'google/gemma-4-e4b',
           'LOCAL_LLM_API_KEY': 'sk-lm-secret-token-123'}
    r, h = ai_router.Router(), _G()
    assert asyncio.run(r.heartbeat(h, env, {}, now=100.0)) is True
    asyncio.run(r._call(h, ai_router.provider(env, 'local'), env, [{'role': 'user', 'content': 'x'}], 0))
    assert all((x or {}).get('Authorization') == 'Bearer sk-lm-secret-token-123' for x in h.hdr)
    p = ai_router.provider(env, 'local')
    assert p['keySet'] is True and 'secret' not in repr(p)


def test_a_remote_lm_studio_may_serve_the_agents_a_local_one_stays_the_owners():
    assert ai_router.local_remote({'LOCAL_LLM_BASE_URL': 'http://10.0.0.249:1236/v1'}) is True
    for u in ('http://127.0.0.1:1234/v1', 'http://localhost:1234/v1', 'http://[::1]:1234/v1', ''):
        assert ai_router.local_remote({'LOCAL_LLM_BASE_URL': u}) is False
    assert ai_router.local_ok({'LOCAL_LLM_BASE_URL': 'http://10.0.0.249:1236/v1'}, 'sherlock') is True
    assert ai_router.local_ok({'LOCAL_LLM_BASE_URL': 'http://127.0.0.1:1234/v1'}, 'sherlock') is False
