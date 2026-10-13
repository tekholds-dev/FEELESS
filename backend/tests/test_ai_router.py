"""🧠 The AI router: local LM Studio first, then the keyed fallbacks; advisory only, never a hot loop or the money boundary; keys never leave
the server. Fake HTTP only — nothing here reaches a model."""
import asyncio
import json

import pytest

import ai_router as air
import reputation_service as rs

GROQ = 'gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd'
OAI = 'sk-proj-ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210wxyz'
GOOD = json.dumps({'summary': 'Buyer velocity strong; wait for reclaim.', 'risk_flags': ['no site / X'], 'narrative': 'AI agent meta, early', 'creator_context': 'fresh dev, 2 launches',
                   'confidence_delta': -0.08, 'wake': ['sherlock', 'trigger']})
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
    base = {'LOCAL_LLM_ENABLED': 'true', 'LOCAL_LLM_BACKGROUND': 'true', 'LOCAL_LLM_BASE_URL': 'http://127.0.0.1:1234/v1', 'LOCAL_LLM_MODEL': 'qwen2.5-7b-instruct-mlx',
            'GROQ_API_KEY': GROQ, 'OPENAI_API_KEY': OAI}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


def run(c):
    return asyncio.run(c)


def test_advice_is_validated_and_clamped_or_dropped():
    a = air.parse_advice('```json\n' + GOOD + '\n```')
    assert a == {'summary': 'Buyer velocity strong; wait for reclaim.', 'confidence_delta': -0.08, 'wake': ['sherlock', 'trigger'], 'stance': 'CAUTION',
                 'risk_flags': ['no site / X'], 'narrative': 'AI agent meta, early', 'creator_context': 'fresh dev, 2 launches'}   # ONLY the vital fields (+ the derived stance)
    wild = air.parse_advice({'priority': 900, 'stance': 'ENTER', 'confidence_delta': 7, 'wake': ['trigger', 'courier', 'nobody', 'trigger', 5], 'summary': 'x\x00y' + 'z ' * 200,
                             'deep_review': 'yes', 'conflict_resolution': 'none', 'narrative': 'unknown', 'risk_flags': ['a', 5, '', 'b', 'c', 'd', 'e']})
    assert wild['stance'] == 'FAVOR' and wild['confidence_delta'] == 0.25 and wild['wake'] == ['trigger', 'courier'] and 'priority' not in wild and 'deep_review' not in wild
    assert len(wild['summary']) == 200 and '\x00' not in wild['summary'] and wild['risk_flags'] == ['a', 'b', 'c', 'd']
    assert 'conflict_resolution' not in wild and 'narrative' not in wild                                     # "none" / "unknown" = nothing said
    assert air.parse_advice({'summary': 'flat'})['stance'] == 'NEUTRAL' and air.stance_of(-0.08) == 'CAUTION'
    for bad in ('', 'I think it pumps', '{"stance": "WATCH"}', '{"summary": "  "}', '[1,2]', '{broken'):
        assert air.parse_advice(bad) is None


def test_local_first_then_fallback_on_timeout_429_malformed_and_offline():
    air.ROUTER.__init__()
    h = Http({'127.0.0.1': [R(500, {})], 'groq.com': [chat('not json at all')], 'openai.com': [chat(GOOD)]})
    out = run(air.ROUTER.reason(h, env(), {}, CASE, 'sherlock'))
    assert out['source'] == 'openai' and out['advice']['stance'] == 'CAUTION' and [t[0] for t in out['tried']] == ['local', 'groq', 'openai']
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
    out2 = run(air.ROUTER.reason(h, env(), {}, {**CASE, 'rank': 480}, 'sherlock'))
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
    assert 'SECRETWALLET' not in blob and 'x.y/z' not in blob and '"symbol":"ZYN"' in blob and 'never tell anyone to buy' in blob and 'never size' in blob


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
        return s, await asyncio.gather(*[air.ROUTER.reason(s, env(), {}, {**CASE, 'rank': i * 100}, 'sherlock') for i in range(5)])
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
    ok = run(air.ROUTER.test(Http({'127.0.0.1': [chat('{"summary":"FEELESS AI ONLINE","confidence_delta":0}')]}), env(), {}, 'local'))
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
    cand = {'mint': 'MINTZYN', 'symbol': 'ZYN', 'status': 'READY', 'rank': 180, 'trigger': 'ENTER', 'cap': 50_000, 'devil': [['identity', 'WARNING', 'no site']]}
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
    assert n == 1 and rs._ai['notes']['MINTZYN']['sherlock']['source'] == 'local'        # a READY coin in the band → Sherlock's narrative + creator read
    assert payload['kernel']['candidates'][0] == cand and payload['ai']['notes']['MINTZYN']['sherlock']['advice']['narrative'] == 'AI agent meta, early'
    assert payload['ai']['metrics']['callsPerMin'] is not None and payload['ai']['metrics']['provider'] == 'local'
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    for k_ in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'XAI_API_KEY', 'AI_API_KEY', 'AI_BASE_URL'):   # the owner's real backend/.env may carry any of them
        monkeypatch.delenv(k_, raising=False)
    assert run(rs._ai_round(1001.0)) == 0                                                # no provider → the round does nothing (kernel unaffected)


def test_the_router_has_no_path_to_money():
    """The module imports nothing that can quote, sign, send or size: its answer can only ever be displayed."""
    import pathlib
    src = pathlib.Path(air.__file__).read_text()
    for bad in ('fuse_wallet', 'arena_prime', '_fw_', 'keeper', 'jupiter', 'signTransaction', 'replace_leg', 'agent_seat', 'reputation_service'):
        assert bad not in src, bad
    imports = {ln.split()[1].split('.')[0] for ln in src.splitlines() if ln.startswith(('import ', 'from '))}
    assert imports <= {'asyncio', 'hashlib', 'json', 're', 'time', 'ai_keys'}


def test_the_models_decisions_are_logged_once_each_for_the_page_and_nothing_reads_them_back():
    import reputation_service as rs
    rs._ai['log'] = []
    case = {'mint': 'M1', 'symbol': 'AAA', 'status': 'CONTENDING', 'trigger': 'ARM'}
    ans = {'source': 'local', 'label': 'LOCAL AI', 'ms': 900, 'at': 100.0, 'advice': {'stance': 'CAUTION', 'confidence_delta': -0.2, 'summary': 'fake breakout', 'risk_flags': ['bundled'],
                                                                                 'conflict_resolution': 'Devil wins: 4 bundles hold 30%'}}
    rs._ai_log('devil', case, ans)
    rs._ai_log('devil', case, {**ans, 'cached': True})                      # the SAME decision served from the cache: not a second line
    rs._ai_log('sherlock', case, {'source': 'NONE', 'advice': None, 'why': 'no provider answered'})   # the desk's own round: silence is not a decision
    assert len(rs._ai['log']) == 1
    row = rs._ai['log'][0]
    assert (row['role'], row['symbol'], row['stance'], row['delta'], row['kernel'], row['trigger'], row['risk_flags']) == ('devil', 'AAA', 'CAUTION', -0.2, 'CONTENDING', 'ARM', ['bundled'])
    assert row['conflict_resolution'] == 'Devil wins: 4 bundles hold 30%' and 'deep' not in row and 'priority' not in row
    rs._ai_log('owner', case, {'source': 'NONE', 'advice': None, 'why': 'no provider answered'}, asked=True)   # the owner ASKED: the miss is shown
    assert rs._ai['log'][-1]['asked'] and rs._ai['log'][-1]['stance'] is None and 'no provider' in rs._ai['log'][-1]['why']
    for i in range(rs.AI_LOG_KEEP + 20):
        rs._ai_log('devil', case, {**ans, 'at': 200.0 + i})
    assert len(rs._ai['log']) == rs.AI_LOG_KEEP
    light = rs._ai_view(light=True)
    assert len(light['log']) == 20 and 'model' in light and not any('key' in k.lower() and k != 'key' for r in light['providers'] for k in r)
    src = open(rs.__file__).read()
    assert "_ai['log']" not in src.split('def _agents_tick')[1].split('def _fuse_warm')[0]   # the agents' pass never reads the model's log
    rs._ai['log'] = []


def test_the_seat_precheck_runs_the_keepers_own_market_gate_before_a_seat_exists():
    import asyncio
    import reputation_service as rs
    plan = [{'mint': 'GOODpump', 'pair': 'P1', 'symbol': 'GOOD', 'vitals': {}}, {'mint': 'THINpump', 'pair': 'P2', 'symbol': 'THIN', 'vitals': {}}, {'mint': 'GONEpump', 'pair': 'P3', 'symbol': 'GONE', 'vitals': {}}]

    async def live(_orders):
        return {'P1': {'baseToken': {'address': 'GOODpump'}, 'priceUsd': '0.5', 'liquidity': {'usd': 500000}, 'dexId': 'pumpswap'},
                'P2': {'baseToken': {'address': 'THINpump'}, 'priceUsd': '0.5', 'liquidity': {'usd': 900}, 'dexId': 'pumpswap'}}
    old = rs._fw_live_pairs
    rs._fw_live_pairs = live
    rs._agent_refused.clear(); rs._seat_pre_ok.clear()
    try:
        ok = asyncio.run(rs._seat_precheck(plan, {}, 1000.0, need=3))
    finally:
        rs._fw_live_pairs = old
    assert set(ok) == {'GOODpump'} and ok['GOODpump']['liq'] == 500000 and ok['GOODpump']['px'] == 0.5   # the seat starts from the LIVE depth + price
    assert 'too thin' in rs._agent_refused['THINpump'][1] and 'unavailable' in rs._agent_refused['GONEpump'][1]
    assert {'THINpump', 'GONEpump'} <= rs._agent_blocked({}, 1001.0) and 'GOODpump' not in rs._agent_blocked({}, 1001.0)
    assert not ({'THINpump', 'GONEpump'} & rs._agent_blocked({}, 1000.0 + rs.AGENT_PRE_SEC + 1))                 # …and they come back after 3 minutes
    rs._agent_refused.clear(); rs._seat_pre_ok.clear()


def test_low_usage_a_coin_that_only_wiggled_is_the_same_case_and_a_changed_state_is_a_new_one():
    base = {**CASE, 'move5m': 12.0, 'vol5m': 5200, 'buyShare': 58, 'why': 'rank 180.4'}
    k = air.case_key(base, 'sherlock')
    assert air.case_key({**base, 'rank': 183.7, 'move5m': 13.1, 'vol5m': 5900, 'buyShare': 59, 'why': 'rank 183.7', 'flow': 'pace 2.1x'}, 'sherlock') == k   # a wiggle: no second inference
    assert air.case_key({**base, 'status': 'CONTENDING'}, 'sherlock') != k and air.case_key({**base, 'trigger': 'ARM'}, 'sherlock') != k
    assert air.case_key({**base, 'devil': ['rug STRONG_WARNING']}, 'sherlock') != k and air.case_key({**base, 'rank': 320}, 'sherlock') != k
    assert air.case_key({**base, 'move5m': 45.0}, 'sherlock') != k and air.case_key(base, 'devil') != k and air.case_key({**base, 'mint': 'OTHER'}, 'sherlock') != k
    assert air.CACHE_SEC >= 600
    c = air.compact({**base, 'holders': 'top10 18% · dev 2% · scan passed', 'chart': 'COMPRESSION', 'crowd': 'callers 3'})
    assert c['holders'].startswith('top10') and c['chart'] == 'COMPRESSION' and 'wallet' not in c and 'url' not in c      # Sherlock's brief reaches the model; nothing else does


def test_while_jupiter_is_busy_no_seat_is_taken_and_no_coin_is_blamed():
    import asyncio
    import time
    import reputation_service as rs
    plan = [{'mint': 'GOODpump', 'pair': 'P1', 'symbol': 'GOOD', 'vitals': {}}]

    async def live(_orders):
        return {'P1': {'baseToken': {'address': 'GOODpump'}, 'priceUsd': '0.5', 'liquidity': {'usd': 500000}, 'dexId': 'pumpswap'}}

    async def sol():
        return 100.0
    old = (rs._fw_live_pairs, rs._sol_usd_live, rs._FW_JUP_BUSY['at'])
    rs._fw_live_pairs, rs._sol_usd_live = live, sol
    rs._agent_refused.clear(); rs._seat_pre_ok.clear()
    try:
        rs._FW_JUP_BUSY['at'] = time.time()                      # a 429 seconds ago
        assert asyncio.run(rs._seat_precheck(plan, {}, 1000.0, seat_usd=0.2, need=1)) == {}
        assert not rs._agent_refused                             # …the coin is not refused: it is tried again when Jupiter answers
    finally:
        rs._fw_live_pairs, rs._sol_usd_live, rs._FW_JUP_BUSY['at'] = old
        rs._agent_refused.clear(); rs._seat_pre_ok.clear()


def test_low_priority_cases_defer_while_the_local_model_is_busy_and_the_metrics_say_so():
    """owner's lag-fix spec: local concurrency 1, a small priority queue, low priority DEFERS instead of waiting behind a busy model."""
    async def go():
        r = air.Router()
        h = Http({'127.0.0.1': ['sleep']})
        busy = asyncio.ensure_future(r.reason(h, env(GROQ_API_KEY=None, OPENAI_API_KEY=None), {}, CASE, 'owner', 'high', prio=air.PRIO['owner']))
        await asyncio.sleep(0.05)                                                    # the local model is now running the owner's review
        low = await r.reason(h, env(GROQ_API_KEY=None, OPENAI_API_KEY=None), {}, {**CASE, 'mint': 'OTHER'}, 'sherlock', prio=air.PRIO['contender'])
        assert low['deferred'] and low['advice'] is None and r.totals['deferred'] == 1 and len(h.calls) == 1   # no second inference was queued
        m = r.metrics()
        assert m['active'] == 1 and m['deferred'] == 1 and m['inflight'] == 1
        busy.cancel()
        return r
    r = asyncio.run(go())
    r.recent = [(1000.0, 900, 'local'), (1010.0, 1100, 'local')]; r.totals.update(cached=2, answered=2)
    m = r.metrics(now=1020.0)
    assert m['callsPerMin'] == 0.2 and m['avgMs'] == 1000 and m['provider'] == 'local' and m['cacheHitPct'] == 50
    assert set(air.PRIO) >= {'owner', 'manager', 'ready', 'devil', 'contender', 'judge'} and air.PRIO['owner'] < air.PRIO['manager'] < air.PRIO['ready'] < air.DEFER_PRIO


def test_the_local_model_is_the_owners_background_jobs_go_to_the_cloud_or_nowhere():
    """💻 The lag fix: a background case never runs on this Mac's GPU — only what the owner asks for by hand does."""
    e = env(LOCAL_LLM_BACKGROUND=None)
    assert not air.local_ok(e, 'sherlock') and air.local_ok(e, 'owner') and air.local_ok(e, 'sherlock', 'force') and air.local_ok(env(), 'judge')
    r, h = air.Router(), Http({'127.0.0.1': [chat(GOOD)] * 3, 'groq': [chat(GOOD)] * 3})
    bg = run(r.reason(h, e, {}, CASE, 'sherlock', prio=2))
    assert bg['source'] == 'groq' and bg['tried'][0] == ['local', 'OWNER ONLY'] and not [c for c in h.calls if '127.0.0.1' in c[0]]
    assert not r.busy(e, {})                                                             # nothing is ever deferred behind a model that is not used
    assert run(r.reason(h, e, {}, {**CASE, 'mint': 'OTHER'}, 'owner'))['source'] == 'local'
    assert run(r.reason(h, e, {}, CASE, 'sherlock', 'force'))['source'] == 'local'       # the owner's ASK box
    none = run(air.Router().reason(Http({'x': [chat(GOOD)]}), env(LOCAL_LLM_BACKGROUND=None, GROQ_API_KEY=None, OPENAI_API_KEY=None), {}, CASE, 'devil'))
    assert none['source'] == 'NONE' and none['advice'] is None                           # no cloud key = deterministic only, never the local GPU
    assert air.PROVIDERS['groq'][5] == 'qwen/qwen3.8-27b'


def test_the_router_fits_the_providers_minute_budget_instead_of_firing_into_a_429():
    import ai_router as air
    assert air.reset_sec('142ms') == 0.142 and air.reset_sec('4m19.2s') == 259.2 and air.reset_sec('7.5s') == 7.5 and air.reset_sec('12') == 12 and air.reset_sec(None) == 0
    r = air.Router()
    assert r.budget_wait('groq', 3000, 100.0) == 0.0                                         # nothing known yet: go
    r._budget_note('groq', {'x-ratelimit-remaining-tokens': '900', 'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-reset-tokens': '6s'}, 100.0)
    assert r.budget_wait('groq', 600, 101.0) == 0.0                                          # fits what is left
    assert 4.9 < r.budget_wait('groq', 3000, 101.0) <= 5.0                                   # does not fit: wait for the reset, not a 429
    assert r.budget_wait('groq', 3000, 107.0) == 0.0 and r.budget_wait('groq', 9000, 101.0) is None   # after the reset · bigger than the whole budget
    r._budget_note('groq', {}, 200.0)                                                         # a provider without the headers changes nothing
    assert r.budget['groq']['at'] == 100.0 and air.est_tokens([{'content': 'x' * 3000}]) == 1000 + air.MAX_TOKENS
    assert air.PROVIDERS['groq'][7] == 1                                                      # one cloud call at a time: two at once was the 429
