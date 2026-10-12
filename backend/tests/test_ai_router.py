"""🧠 The AI router: local LM Studio first, then the keyed fallbacks; advisory only, never a hot loop or the money boundary; keys never leave
the server. Fake HTTP only — nothing here reaches a model."""
import asyncio
import json

import pytest

import ai_router as air
import reputation_service as rs

GROQ = 'gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd'
OAI = 'sk-proj-ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210wxyz'
GOOD = json.dumps({'priority': 82, 'stance': 'WATCH', 'confidence_delta': -0.08, 'wake': ['sherlock', 'trigger'], 'summary': 'Buyer velocity strong; wait for reclaim.', 'deep_review': False})
CASE = {'mint': 'MINTZYN', 'symbol': 'ZYN', 'status': 'READY', 'rank': 180, 'ageMin': 3, 'liq': 21000, 'trigger': 'ENTER', 'devil': ['identity WARNING'], 'wallet': 'SECRETWALLET', 'url': 'https://x.y/z'}


class R:
    def __init__(self, code=200, body=None, headers=None):
        self.status_code, self._b, self.headers = code, body, headers or {}

    def json(self):
        if isinstance(self._b, Exception):
            raise self._b
        return self._b


def chat(text):
    return R(200, {'choices': [{'message': {'content': text}}]})


class Http:
    """route → a list of answers (R, an Exception to raise, or 'sleep' = never answers). Records every call."""

    def __init__(self, by):
        self.by, self.calls = by, []

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, dict(headers or {})))
        host = next(k for k in self.by if k in url)
        a = self.by[host].pop(0) if len(self.by[host]) > 1 else self.by[host][0]
        if a == 'sleep':
            await asyncio.sleep(60)
        if isinstance(a, Exception):
            raise a
        return a


def env(**kw):
    base = {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://127.0.0.1:1234/v1', 'LOCAL_LLM_MODEL': 'qwen2.5-7b-instruct-mlx',
            'GROQ_API_KEY': GROQ, 'OPENAI_API_KEY': OAI}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


def run(c):
    return asyncio.run(c)


def test_advice_is_validated_and_clamped_or_dropped():
    a = air.parse_advice('```json\n' + GOOD + '\n```')
    assert a == {'priority': 82, 'stance': 'WATCH', 'confidence_delta': -0.08, 'wake': ['sherlock', 'trigger'], 'summary': 'Buyer velocity strong; wait for reclaim.', 'deep_review': False}
    wild = air.parse_advice({'priority': 900, 'stance': 'enter', 'confidence_delta': 7, 'wake': ['trigger', 'courier', 'nobody', 'trigger', 5], 'summary': 'x\x00y' + 'z' * 400, 'deep_review': 'yes'})
    assert wild['priority'] == 100 and wild['stance'] == 'ENTER' and wild['confidence_delta'] == 0.25 and wild['wake'] == ['trigger', 'courier']
    assert len(wild['summary']) == 200 and '\x00' not in wild['summary'] and wild['deep_review'] is False
    for bad in ('', 'I think it pumps', '{"stance": "MOON", "summary": "x"}', '{"stance": "WATCH"}', '{"stance": "WATCH", "summary": "  "}', '[1,2]', '{broken'):
        assert air.parse_advice(bad) is None


def test_local_first_then_fallback_on_timeout_429_malformed_and_offline():
    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [R(500, {})], 'groq.com': [chat('not json at all')], 'openai.com': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    assert out['source'] == 'openai' and out['advice']['stance'] == 'WATCH' and [t[0] for t in out['tried']] == ['local', 'groq', 'openai']
    assert air.ROUTER.stats['local']['state'] == 'OFFLINE' and air.ROUTER.stats['groq']['state'] == 'BAD ANSWER' and air.ROUTER.totals['fallbacks'] == 2

    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'devil'))
    assert out['source'] == 'local' and out['label'] == 'LOCAL AI' and len(h.calls) == 1
    url, body, hdr = h.calls[0]
    assert url == 'http://127.0.0.1:1234/v1/chat/completions' and body['model'] == 'qwen2.5-7b-instruct-mlx' and 'Authorization' not in hdr

    air.ROUTER.__init__()                                                               # 429 → rested, the next provider answers
    h = Http({'127.0.0.1': [R(429, {}, {'retry-after': '30'})], 'groq.com': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    assert out['source'] == 'groq' and air.ROUTER.stats['local']['state'] == 'RATE LIMITED' and air.ROUTER.stats['local']['coolUntil'] > 0
    assert h.calls[1][2]['Authorization'] == f'Bearer {GROQ}'                           # the key goes ONLY to its own provider's header
    out2 = run(air.ROUTER.reason(h, env(), {}, {**CASE, 'rank': 181}, 'sherlock'))
    assert ['local', 'RATE LIMITED'] in out2['tried'] and out2['source'] == 'groq'      # still resting: skipped without a call


def test_timeout_falls_through(monkeypatch):
    air.ROUTER.__init__()
    monkeypatch.setitem(air.PROVIDERS, 'local', air.PROVIDERS['local'][:6] + (0.05, 1))
    h = Http({'127.0.0.1': ['sleep'], 'groq.com': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'judge'))
    assert out['source'] == 'groq' and air.ROUTER.stats['local']['timeouts'] == 1 and out['tried'][0][1].startswith('no answer in')


def test_disabled_keyless_and_all_failing_mean_deterministic_only():
    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [R(503, {})], 'groq.com': [ConnectionError('refused')], 'openai.com': [R(401, {})]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    assert out['source'] == 'NONE' and out['advice'] is None and 'deterministic only' in out['why']
    air.ROUTER.__init__()
    e = env(LOCAL_LLM_ENABLED='false', GROQ_API_KEY=None)
    h = Http({'openai.com': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, e, {'enabled': {'openai': False}}, CASE, 'sherlock'))
    assert out['source'] == 'NONE' and h.calls == []                                    # local off by env, groq keyless, openai off by the owner
    rows = {r['key']: r for r in air.ROUTER.view(e, {'enabled': {'openai': False}})['providers']}
    assert rows['local']['state'] == 'DISABLED' and rows['groq']['state'] == 'KEY MISSING' and rows['openai']['state'] == 'DISABLED' and rows['xai']['state'] == 'KEY MISSING'


def test_hot_loops_and_the_money_boundary_never_ask_a_model():
    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [chat(GOOD)]})
    for role in ('tally', 'trigger', 'reaper', 'courier', 'warden'):
        out = run(air.ROUTER.reason(h, env(), {}, CASE, role))
        assert out['source'] == 'NONE' and out['advice'] is None and 'never asks a model' in out['why']
    assert h.calls == [] and air.ROUTER.totals['refused'] == 5
    assert set(air.FORBIDDEN_ROLES).isdisjoint(air.ADVISORY_ROLES)


def test_the_local_base_must_be_this_machine_and_the_case_is_whitelisted():
    for bad in ('http://192.168.1.5:1234/v1', 'https://evil.example/v1', 'http://10.0.0.2/v1', 'http://localhost.evil.com/v1'):
        assert air.provider(env(LOCAL_LLM_BASE_URL=bad), 'local')['why']
    for ok in ('http://127.0.0.1:1234/v1', 'http://localhost:1234/v1', 'http://[::1]:1234/v1'):
        assert air.provider(env(LOCAL_LLM_BASE_URL=ok), 'local')['why'] is None
    msgs = air.messages(CASE, 'sherlock')
    blob = msgs[0]['content'] + msgs[1]['content']
    assert 'SECRETWALLET' not in blob and 'x.y/z' not in blob and '"symbol":"ZYN"' in blob and 'ADVISORY' in blob


def test_cache_and_shared_inflight_mean_one_inference_per_case():
    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [chat(GOOD)]})
    run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    again = run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    assert again['cached'] and len(h.calls) == 1

    air.ROUTER.__init__()

    class Slow(Http):
        async def post(self, url, json=None, headers=None):
            self.calls.append(url)
            await asyncio.sleep(0.05)
            return chat(GOOD)

    async def both():
        s = Slow({})
        a, b = await asyncio.gather(air.ROUTER.reason(s, env(), {}, CASE, 'sherlock'), air.ROUTER.reason(s, env(), {}, CASE, 'sherlock'))
        return s, a, b
    s, a, b = run(both())
    assert len(s.calls) == 1 and a['source'] == b['source'] == 'local'


def test_local_is_one_at_a_time_with_a_bounded_queue():
    air.ROUTER.__init__()

    class Slow(Http):
        async def post(self, url, json=None, headers=None):
            self.calls.append(url)
            await asyncio.sleep(0.05 if '127.0.0.1' in url else 0)
            return chat(GOOD)

    async def many():
        s = Slow({})
        return s, await asyncio.gather(*[air.ROUTER.reason(s, env(), {}, {**CASE, 'rank': i}, 'sherlock') for i in range(5)])
    s, outs = run(many())
    srcs = [o['source'] for o in outs]
    assert srcs.count('local') == 3 and srcs.count('groq') == 2                           # 1 running + 2 queued; the rest go to the next provider
    assert any(t == ['local', 'BUSY'] for o in outs for t in o['tried'])


def test_order_config_and_the_view_never_carry_a_key():
    assert air.order_of({'AI_PROVIDER_ORDER': 'groq, local ,bogus'})[:3] == ['groq', 'local', 'openrouter']
    assert air.order_of({}, {'order': ['xai']})[0] == 'xai'
    c = air.clean_cfg({'order': ['openai', 'nope', 'local', 'openai'], 'enabled': {'groq': 0, 'bad': True}, 'key': GROQ}, {'enabled': {'xai': False}})
    assert c == {'order': ['openai', 'local'], 'enabled': {'xai': False, 'groq': False}}
    air.ROUTER.__init__()
    air.ROUTER._bad('groq', 0, f'boom {GROQ}', 'fail')
    v = air.ROUTER.view(env(), {})
    blob = json.dumps(v)
    assert GROQ not in blob and OAI not in blob and GROQ[:12] not in blob
    g = next(r for r in v['providers'] if r['key'] == 'groq')
    assert g['hint'] == f'…{GROQ[-4:]}' and g['priority'] == 2 and v['never'] == list(air.FORBIDDEN_ROLES)


def test_the_test_button_reports_state_and_latency():
    air.ROUTER.__init__()
    ok = run(air.ROUTER.test(Http({'127.0.0.1': [chat('{"stance":"WATCH","summary":"FEELESS AI ONLINE","priority":50}')]}), env(), {}, 'local'))
    assert ok['ok'] and ok['state'] == 'ONLINE' and air.ROUTER.stats['local']['lastOkAt']
    assert run(air.ROUTER.test(Http({}), env(XAI_API_KEY=None), {}, 'xai')) == {'ok': False, 'state': 'KEY MISSING', 'err': 'KEY MISSING'}
    bad = run(air.ROUTER.test(Http({'groq.com': [R(429, {})]}), env(), {}, 'groq'))
    assert not bad['ok'] and bad['state'] == 'RATE LIMITED'


class _Req:
    def __init__(self, body):
        self._b = body

    async def json(self):
        return self._b


def test_owner_routes_save_order_test_and_never_echo_a_key(monkeypatch):
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    monkeypatch.setattr(rs, '_audit', lambda *a: None)
    monkeypatch.setenv('GROQ_API_KEY', GROQ)
    out = run(rs.admin_ai_providers_set(_Req({'order': ['groq', 'local'], 'enabled': {'openai': False}})))
    assert out['order'][:2] == ['groq', 'local'] and GROQ not in json.dumps(out)
    assert json.dumps(run(rs.admin_ai_providers(None))).count(GROQ) == 0

    async def fake_test(http, e, cfg, key):
        return {'ok': True, 'ms': 42, 'state': 'ONLINE'}
    monkeypatch.setattr(rs._air.ROUTER, 'test', fake_test)
    t = run(rs.admin_ai_test(_Req({'provider': 'local'})))
    assert t['ok'] and t['ms'] == 42
    with pytest.raises(rs.HTTPException):
        run(rs.admin_ai_test(_Req({'provider': 'nope'})))


def test_the_advisory_round_only_writes_notes(monkeypatch):
    """An AI answer lands in office.ai.notes with its source — the kernel's candidates, ranks and statuses are untouched."""
    air.ROUTER.__init__()
    cand = {'mint': 'MINTZYN', 'symbol': 'ZYN', 'status': 'READY', 'rank': 180, 'trigger': 'ENTER', 'devil': [['identity', 'WARNING', 'no site']]}
    payload = {'kernel': {'candidates': [dict(cand)]}, 'ownerReview': []}
    monkeypatch.setattr(rs, '_office', {'payload': payload})
    monkeypatch.setattr(rs, '_office_state', lambda: {})
    monkeypatch.setattr(rs, '_ai_cfg', lambda: {})
    for k, v in env().items():
        monkeypatch.setenv(k, v)
    h = Http({'127.0.0.1': [chat(GOOD)]})
    monkeypatch.setitem(rs._ai, 'http', h)
    monkeypatch.setitem(rs._ai, 'notes', {})
    n = run(rs._ai_round(1000.0))
    assert n == 1 and rs._ai['notes']['MINTZYN']['devil']['source'] == 'local'          # a conflicted case (ENTER + a warning) → Devil's second opinion
    assert payload['kernel']['candidates'][0] == cand and payload['ai']['notes']['MINTZYN']['devil']['advice']['stance'] == 'WATCH'
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    monkeypatch.delenv('GROQ_API_KEY'); monkeypatch.delenv('OPENAI_API_KEY')
    assert run(rs._ai_round(1001.0)) == 0                                                # no provider → the round does nothing (kernel unaffected)


def test_the_router_has_no_path_to_money():
    """The module imports nothing that can quote, sign, send or size: its answer can only ever be displayed."""
    import pathlib
    src = pathlib.Path(air.__file__).read_text()
    for bad in ('fuse_wallet', 'arena_prime', '_fw_', 'keeper', 'jupiter', 'signTransaction', 'replace_leg', 'agent_seat', 'reputation_service'):
        assert bad not in src, bad
    imports = {ln.split()[1].split('.')[0] for ln in src.splitlines() if ln.startswith(('import ', 'from '))}
    assert imports <= {'asyncio', 'hashlib', 'json', 're', 'time', 'ai_keys'}
