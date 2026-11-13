"""MODEL-CFG: each model shows exactly the knobs OpenRouter lists for it; saved values are clamped and ride with the agent's requests."""
import asyncio

import launch_cat as lc

# shapes copied from a live GET https://openrouter.ai/api/v1/models (2026-11-13)
CLAUDE = {'id': 'anthropic/claude-fable-5.2', 'name': 'Claude Fable 5.2', 'pricing': {'prompt': '0.000003', 'completion': '0.000015'},
          'supported_parameters': ['include_reasoning', 'max_completion_tokens', 'max_tokens', 'reasoning', 'reasoning_effort', 'response_format', 'stop',
                                   'structured_outputs', 'tool_choice', 'tools', 'verbosity'],
          'reasoning': {'mandatory': True, 'supported_efforts': ['max', 'xhigh', 'high', 'medium', 'low'], 'default_effort': 'high'}}
QWEN = {'id': 'qwen/qwen3.8-max-prime', 'name': 'Qwen', 'pricing': {'prompt': '0.000001', 'completion': '0.000004'},
        'supported_parameters': ['frequency_penalty', 'include_reasoning', 'logprobs', 'max_tokens', 'presence_penalty', 'reasoning', 'reasoning_effort',
                                 'response_format', 'seed', 'stop', 'structured_outputs', 'temperature', 'tool_choice', 'tools', 'top_k', 'top_logprobs', 'top_p'],
        'reasoning': {'mandatory': True, 'supported_efforts': ['xhigh', 'high', 'medium', 'low', 'minimal'], 'default_effort': 'xhigh'}}
BARE = {'id': 'some/bare-model', 'name': 'Bare', 'pricing': {'prompt': '0', 'completion': '0'}, 'supported_parameters': ['stop']}


def keys(row):
    return [k['key'] for k in row['knobs']]


def test_each_model_shows_only_its_own_knobs():
    c, q, b = lc.slim(CLAUDE), lc.slim(QWEN), lc.slim(BARE)
    assert keys(c) == ['verbosity', 'max_tokens']                 # no temperature on this one: it isn't listed
    assert c['efforts'] == ['max', 'xhigh', 'high', 'medium', 'low'] and c['defaultEffort'] == 'high'
    assert keys(q) == ['temperature', 'top_p', 'top_k', 'frequency_penalty', 'presence_penalty', 'max_tokens', 'seed']
    assert b['knobs'] == [] and b['efforts'] == []                # a bare model → a clean default, nothing to show


def test_clamp_keeps_supported_values_in_range():
    q = lc.slim(QWEN)
    out = lc.clamp_knobs(q['knobs'], {'temperature': 9, 'top_p': -1, 'top_k': '40', 'verbosity': 'high', 'nonsense': 1, 'seed': None})
    assert out == {'temperature': 2.0, 'top_p': 0.0, 'top_k': 40}   # verbosity not supported by Qwen → dropped; unknown dropped
    c = lc.slim(CLAUDE)
    assert lc.clamp_knobs(c['knobs'], {'verbosity': 'loud'}) == {}
    assert lc.clamp_knobs(c['knobs'], {'verbosity': 'low', 'temperature': 0.5}) == {'verbosity': 'low'}


def test_body_drops_off_values():
    assert lc.body_knobs({'seed': 0, 'top_k': 0, 'temperature': 0.7}) == {'temperature': 0.7}


def test_clean_keeps_knobs_only_for_picked_models():
    b = lc.clean({'brains': ['qwen/qwen3.8-max-prime'], 'knobs': {'qwen/qwen3.8-max-prime': {'temperature': 0.5}, 'other/x': {'top_p': 0.1}}})
    assert b['knobs'] == {'qwen/qwen3.8-max-prime': {'temperature': 0.5}}


def test_service_clamps_and_the_knobs_ride_in_the_openrouter_request(monkeypatch):
    import feecat_service as fs
    catalog = lc.catalog([QWEN, CLAUDE])
    clean = fs._model_knobs_clean(catalog, {'qwen/qwen3.8-max-prime': {'temperature': 5, 'verbosity': 'high'}, 'anthropic/claude-fable-5.2': {'temperature': 0.3}})
    assert clean == {'qwen/qwen3.8-max-prime': {'temperature': 2.0}}   # Claude lists no temperature → nothing saved for it

    sent = {}

    class R:
        status_code = 200

        def json(self):
            return {'id': 'x', 'model': 'qwen/qwen3.8-max-prime', 'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}], 'usage': {'cost': 0}}

    class Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            sent.update(json or {})
            return R()

    monkeypatch.setattr(fs.httpx, 'AsyncClient', Client)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-test')

    async def go():
        tok = fs._OR_KNOBS.set({'qwen/qwen3.8-max-prime': {'temperature': 0.9, 'top_k': 40, 'max_tokens': 100, 'seed': 0}})
        try:
            return await fs._or_call('qwen/qwen3.8-max-prime', [{'role': 'user', 'content': 'hi'}], max_tokens=500)
        finally:
            fs._OR_KNOBS.reset(tok)
    text, _ = asyncio.run(go())
    assert text == 'ok'
    assert sent['temperature'] == 0.9 and sent['top_k'] == 40 and 'seed' not in sent   # seed 0 = off
    assert sent['max_tokens'] == 100                                                    # the owner's cap wins when lower

    sent.clear()
    asyncio.run(fs._or_call('qwen/qwen3.8-max-prime', [{'role': 'user', 'content': 'hi'}], max_tokens=500))
    assert sent['temperature'] == 0.2 and 'top_k' not in sent                           # nothing saved → the old default
