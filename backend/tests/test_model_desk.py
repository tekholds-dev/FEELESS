"""🧠 Brain › Models (owner, 2026-10-23): INFO / SERVER / INFERENCE / VITALS read from what LM Studio, NEXA's llamafile, the router and the
FEELESS MCP really report — and the owner's Inference overrides ride every call to that model."""
import asyncio

import ai_rig as rg
import ai_router as ar
import model_desk as md

LMS = {'models': [{'type': 'llm', 'publisher': 'openai', 'key': 'openai/gpt-oss-20b', 'display_name': 'GPT-OSS 20B', 'architecture': 'gpt_oss',
                   'quantization': {'name': 'MXFP4', 'bits_per_weight': 4}, 'size_bytes': 12104314420, 'params_string': '20B', 'max_context_length': 131072,
                   'loaded_instances': [{'id': 'openai/gpt-oss-20b', 'config': {'context_length': 8192, 'parallel': 2}}], 'format': 'mlx',
                   'capabilities': {'vision': False, 'trained_for_tool_use': True, 'reasoning': {'allowed_options': ['low', 'medium', 'high'], 'default': 'low'}},
                   'selected_variant': 'openai/gpt-oss-20b@mxfp4'}, {'type': 'embedding', 'key': 'nomic'}]}


def test_info_reads_lm_studio_as_it_reports():
    row, n = md.lms_pick(LMS, 'openai/gpt-oss-20b')
    i = md.lms_info(row)
    assert n == 1 and i['name'] == 'GPT-OSS 20B' and i['arch'] == 'gpt_oss' and i['quant'] == 'MXFP4' and i['bits'] == 4 and i['sizeGb'] == 12.1
    assert i['loadedCtx'] == 8192 and i['parallel'] == 2 and i['toolUse'] and not i['vision'] and i['reasoning'] == {'options': ['low', 'medium', 'high'], 'default': 'low'}
    assert md.lms_info(None) is None and md.host_of('http://10.0.0.249:1236/v1') == 'http://10.0.0.249:1236'


def test_vitals_from_the_call_log():
    log = [{'prov': 'lan', 'ok': True, 'ms': 2000, 'out': 100, 'in': 3000, 'at': 10}, {'prov': 'lan', 'ok': True, 'ms': 4000, 'out': 100, 'at': 20},
           {'prov': 'lan', 'ok': False, 'err': 'timeout', 'at': 30, 'tok': 4352, 'mindset': 'elite'}, {'prov': 'local', 'ok': True, 'ms': 9000, 'at': 40}]
    v = md.vitals(log, {'c1': {'prov': 'lan'}, 'c2': {'prov': 'local'}}, 'lan', 8704)
    assert v['calls'] == 3 and v['okPct'] == 67 and v['medMs'] == 4000 and v['tokPerSec'] == 50.0 and v['queue'] == 1 and v['errors'] == 1
    assert v['lastErr'] == 'timeout' and v['ctxFill'] == 0.5 and v['lastOkAt'] == 20 and v['mindset'] == 'elite'
    assert md.vitals([], {}, 'win')['okPct'] is None


def test_inference_overrides_are_bounded_and_ride_every_call():
    r = rg.clean({'lan': {'infer': {'temp': 3, 'maxTok': 10, 'topK': 40, 'stop': 'END|###|', 'bogus': 1}}})
    assert r['lan']['infer'] == {'temp': 1.5, 'maxTok': 32, 'topK': 40, 'stop': ['END', '###']}
    r2 = rg.clean({'lan': {'infer': {'temp': None, 'stop': ''}}}, r)
    assert r2['lan']['infer'] == {'maxTok': 32, 'topK': 40} and 'infer' not in r2['local']
    assert rg.infer_body({'temp': 0.4, 'topP': 0.9, 'stop': ['X']}) == {'temperature': 0.4, 'top_p': 0.9, 'stop': ['X']}
    src = open(ar.__file__).read()
    assert "inf_ = (RIG.get(p['key']) or {}).get('infer')" in src and src.index("body.update(_rg.infer_body(inf_))") < src.index("tn = TUNE.get()")   # chat tuning still wins


def test_mcp_view_and_the_endpoint(monkeypatch):
    m = md.mcp_view([{'name': 'now', 'description': "Today's date. Call it."}, {'description': 'nameless'}], 12, None, ':8765/mcp')
    assert m['ok'] and m['n'] == 1 and m['tools'][0] == {'name': 'now', 'desc': "Today's date"}
    assert not md.mcp_view([], None, 'ConnectError')['ok']
    import reputation_service as rs

    async def lms(key):
        return {'data': LMS, 'ms': 30, 'base': 'http://10.0.0.249:1236/v1', 'model': 'openai/gpt-oss-20b'}


    async def mcp():
        return m
    monkeypatch.setattr(rs, '_mdk_lms', lms); monkeypatch.setattr(rs, '_mdk_mcp', mcp)
    v = asyncio.run(rs._model_desk_view())
    assert [x['key'] for x in v['models']] == ['lan', 'local'] and v['mcp']['n'] == 1 and v['bounds']['temp'] == [0.0, 1.5]
    g4 = v['models'][0]
    assert g4['info']['arch'] == 'gpt_oss' and g4['server']['endpoint'] == 'http://10.0.0.249:1236' and g4['server']['ok'] and g4['inference']['desk']['temp'] == 0.1


def test_the_stall_watchdog_only_flags_a_model_that_keeps_failing_while_asked(monkeypatch):
    import model_desk as md
    now = 10_000.0
    stalled = {'state': 'OFFLINE', 'streak': 4, 'timeouts': 4, 'lastOkAt': now - 1500, 'lastAt': now - 30, 'lastErr': 'timed out'}
    st = md.stall_of(stalled, now)
    assert st['streak'] == 4 and st['sinceOk'] == 1500 and st['why'].startswith('4 timeouts in a row, last good answer 25m ago')
    assert md.stall_of({**stalled, 'state': 'ONLINE'}, now) is None                         # answering again
    assert md.stall_of({**stalled, 'streak': 2}, now) is None                               # a blip, not a stall
    assert md.stall_of({**stalled, 'lastOkAt': now - 120}, now) is None                     # a good answer 2 min ago
    assert md.stall_of({**stalled, 'lastAt': now - 3600}, now) is None                      # nobody is asking it any more
    assert md.stall_of({**stalled, 'lastOkAt': None}, now)['why'].endswith('no good answer yet (timed out)')
    import reputation_service as rs
    sent = []
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: sent.append((a, k)))
    monkeypatch.setattr(rs, '_owner_wallets', lambda: ['OWNER'])
    monkeypatch.setattr(rs._air.ROUTER, 'stats', {'lan': stalled, 'local': {'state': 'ONLINE'}, 'win': {}})
    rs._stall_seen.clear()
    assert rs._ai_stall_watch(now) == ['lan'] and 'stalled' in sent[0][0][2] and 'your call' in sent[0][0][2]
    assert rs._ai_stall_watch(now + 60) == [] and len(sent) == 1                             # once per 30 min
    src = open(rs._air.__file__).read()
    assert 'Never called by a timer' in src                                                 # the watchdog alerts; the reload stays the owner's
    rs._stall_seen.clear()
