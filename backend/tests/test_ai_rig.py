import ai_rig
import ai_router


def test_rig_keeps_listed_values_only_and_prints_the_load_command():
    r = ai_rig.clean({'lan': {'ctx': 16384, 'parallel': 3, 'timeout': 999}, 'bogus': {'ctx': 1}})
    assert r['lan']['ctx'] == 16384 and r['lan']['parallel'] == 3 and r['lan']['timeout'] == 90   # 999 is not an option
    assert 'win' not in r and 'bogus' not in r   # NEXA retired (owner 2026-10-31)
    v = ai_rig.view(r, {'lan': 'qwen/qwen3-4b-2507'})
    lan = next(x for x in v['rows'] if x['key'] == 'lan')
    assert '--parallel 3' in lan['cmd'] and '--context-length 49152' in lan['cmd'] and lan['name'] == 'G4'


def test_router_reads_the_rig_live():
    ai_router.RIG.clear()
    ai_router.RIG.update({'local': {'timeout': 120, 'parallel': 2, 'perMin': 8}})
    p = ai_router.provider({'LOCAL_LLM_ENABLED': 'true'}, 'local')
    assert p['timeout'] == 120 and p['conc'] == 2
    assert ai_router.rig('local', 'perMin', 4) == 8 and ai_router.rig('lan', 'perMin', 4) == 4
    ai_router.RIG.clear()


# 🎛 a chat line → model settings (owner, 2026-10-21: "a chat line truly changes model settings — proposal → applied")
def test_a_chat_line_becomes_listed_rig_changes():
    got = {x['key']: x for x in ai_rig.parse_line('set ossy context to 16k, max concurrent predictions 1 and g4 timeout 120, temp 0.6')}
    assert got['local.load']['value'] == 'ctx=16384 par=1' and got['local.load']['reload'] is True
    assert got['lan.timeout']['value'] == 120 and got['chat.temp']['value'] == 0.6
    assert ai_rig.parse_line('ossy flash attention off, kv cache to ram')[0]['value'] == 'flash=0 kv=0'
    assert {x['key'] for x in ai_rig.parse_line('both models context 32k')} == {'lan.load', 'local.load'}
    assert ai_rig.parse_line('g4 prompt budget 12k')[0]['key'] == 'lan.ctx'
    assert ai_rig.parse_line('gm, how are the agents doing?') == [] and ai_rig.parse_line('ossy is slow') == []
    assert ai_rig.parse_line('ossy context 20000')[0]['value'] == 'ctx=16384'   # between options → the nearest listed one


def test_the_rig_gate_refuses_anything_off_the_list():
    assert ai_rig.check_change('local.load', 'ctx=16384 par=9 wallet=1') == 'ctx=16384'
    assert ai_rig.check_change('win.load', 'ctx=16384') is None and ai_rig.check_change('lan.timeout', 999) is None
    assert ai_rig.check_change('chat.temp', '0.6') == 0.6 and ai_rig.check_change('chat.len', 'huge') is None
    assert ai_rig.check_change('lan.slippage', 1) is None and ai_rig.check_change('agentTp.x', 1) is None


def test_lm_studio_state_and_the_load_body():
    data = {'models': [{'type': 'llm', 'key': 'openai/gpt-oss-20b', 'format': 'mlx', 'max_context_length': 131072, 'size_bytes': 12e9,
                        'loaded_instances': [{'id': 'openai/gpt-oss-20b', 'config': {'context_length': 7659, 'parallel': 2}}]}]}
    row = ai_rig.lms_row(data, 'openai/gpt-oss-20b')
    assert row['fmt'] == 'mlx' and row['loaded'][0] == {'id': 'openai/gpt-oss-20b', 'ctx': 7659, 'par': 2} and row['sizeGb'] == 12.0
    b = ai_rig.load_body('openai/gpt-oss-20b', {'ctx': 16384, 'flash': 1}, row['loaded'], 'mlx')
    assert b == {'model': 'openai/gpt-oss-20b', 'echo_load_config': True, 'context_length': 16384, 'parallel': 2}   # MLX never gets GGUF-only fields
    assert ai_rig.load_body('m', {'flash': 0, 'kv': 1}, None, 'gguf') == {'model': 'm', 'echo_load_config': True, 'flash_attention': False, 'offload_kv_cache_to_gpu': True}
    assert ai_rig.load_diff({'ctx': 16384, 'par': 2}, row['loaded']) == {'ctx': (7659, 16384)}
    v = ai_rig.view(ai_rig.clean({'local': {'load': {'ctx': 16384}}}), None, {'local': row})
    loc = next(x for x in v['rows'] if x['key'] == 'local')
    assert loc['diff'] == {'ctx': [7659, 16384]} and loc['lms']['fmt'] == 'mlx' and v['loadOptions']['ctx'][0] == 4096


class _R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, str(body)

    def json(self):
        return self._b


class _LMS:   # a fake LM Studio: never the real one
    def __init__(self, take_parallel=True):
        self.calls, self.cfg, self.take_parallel = [], {'context_length': 7659, 'parallel': 2}, take_parallel

    async def get(self, url, **kw):
        self.calls.append(('GET', url.split('/api/')[-1], None))
        inst = [{'id': 'openai/gpt-oss-20b', 'config': dict(self.cfg)}] if self.cfg else []
        return _R(200, {'models': [{'type': 'llm', 'key': 'openai/gpt-oss-20b', 'format': 'mlx', 'loaded_instances': inst}]})

    async def post(self, url, json=None, **kw):
        self.calls.append(('POST', url.split('/api/')[-1], json))
        if url.endswith('/unload'):
            self.cfg = None
            return _R(200, {'instance_id': json['instance_id']})
        if 'parallel' in json and not self.take_parallel:
            return _R(400, {'error': 'unrecognized key parallel'})
        self.cfg = {'context_length': json.get('context_length'), 'parallel': json.get('parallel', 1)}
        return _R(200, {'status': 'loaded', 'load_config': self.cfg})


def _env():
    return {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BASE_URL': 'http://127.0.0.1:1234/v1', 'LOCAL_LLM_MODEL': 'openai/gpt-oss-20b'}


def test_an_approved_reload_unloads_then_loads_with_the_wanted_settings():
    import asyncio
    h = _LMS()
    res = asyncio.run(ai_router.Router().reload_model(h, _env(), {}, 'local', {'ctx': 16384}))
    assert res['ok'] and res['loaded']['ctx'] == 16384 and res['loaded']['par'] == 2   # parallel kept from what it ran
    posts = [(u, b) for m, u, b in h.calls if m == 'POST']
    assert posts[0] == ('v1/models/unload', {'instance_id': 'openai/gpt-oss-20b'}) and posts[1][1]['context_length'] == 16384
    h2 = _LMS(take_parallel=False)   # an LM Studio that refuses `parallel` over REST still loads the context, and says so
    res2 = asyncio.run(ai_router.Router().reload_model(h2, _env(), {}, 'local', {'ctx': 8192, 'par': 1}))
    assert res2['ok'] and res2['loaded']['ctx'] == 8192 and 'Load panel' in res2['note']


def test_a_question_that_mentions_context_or_temp_stays_a_question():
    assert ai_rig.parse_line('ossy what do you think about the context of 5 trades') == []
    assert ai_rig.parse_line('g4 the temp is 30 degrees outside lol') == []
    assert ai_rig.parse_line('ossy context 16384')[0]['value'] == 'ctx=16384' and ai_rig.parse_line('g4 ctx 8k')[0]['value'] == 'ctx=8192'
