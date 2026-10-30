import asyncio
import json
import pytest
import cat_agent as ca
import cat_policy as cp
import cat_tools as ct

PAIR = {'pairAddress': 'P1', 'baseToken': {'symbol': 'JUP', 'address': 'M1'}, 'priceUsd': '0.42', 'marketCap': 1.2e9, 'liquidity': {'usd': 3.4e6},
        'volume': {'h24': 8.1e6}, 'priceChange': {'h24': -2.5}, 'dexId': 'raydium'}


def test_feeless_tools_read_our_data_and_hand_back_the_coin_for_the_chart():
    text, coin = ct.coin_text([PAIR], 'JUP')
    assert '$JUP' in text and '$1.2B' in text and '−' not in text and coin == {'pair': 'P1', 'mint': 'M1', 'symbol': 'JUP'}
    assert ct.coin_text([], 'NOPE') == ('FEELESS found no coin for "NOPE".', None)
    assert 'APY 40.0%' in ct.pools_text({'pools': [{'sym': 'SOL-USDC', 'proto': 'raydium', 'apy': 40, 'tvl': 2e6}, {'sym': 'X', 'apy': None}]})
    assert 'OPEN' in ct.gaps_text([{'sym': 'JLP', 'gapPct': 0.7, 'netPct': 0.1, 'n': 3, 'open': True}])
    assert 'SOL-PERP up to 250x' in ct.perps_text()


@pytest.mark.parametrize('text', ['launch a new memecoin on FEELESS', 'create a liquidity pool on feeless', 'make another agent', 'spawn a new AI agent', 'create a FeeCat'])
def test_agents_never_create_agents_or_launch_on_feeless(text):
    assert cp.refusal(text)


@pytest.mark.parametrize('text', ['research the newest coins on the trench', 'is this pool worth it?', 'compare two agents', 'launch a memecoin on pump.fun for my brand'])
def test_reading_about_coins_pools_agents_is_fine(text):
    assert cp.refusal(text) is None


def test_each_mind_gets_its_own_job():
    assert ca.split_jobs('A: write the video script  B: make 5 social posts') == ['write the video script', 'make 5 social posts']
    assert ca.split_jobs('best sports bet tonight?') == ['best sports bet tonight?'] * 2


class Page:
    url = ''
    title = ''

    async def read(self):
        return ''

    async def close(self):
        pass


def test_jobs_mode_runs_feeless_first_keeps_the_best_and_throws_the_scratch_away():
    script = {'m/a': [{'action': 'feeless', 'tool': 'coin', 'q': 'JUP', 'thought': 'check JUP on FEELESS'}, {'action': 'note', 'say': 'JUP pool 3.4M'},
                      {'action': 'answer', 'say': 'JUP looks liquid'}],
              'm/b': [{'action': 'answer', 'say': '5 posts drafted'}]}

    async def ask(model, messages):
        return json.dumps(script[model].pop(0)), 0.001

    async def feeless(tool, q=''):
        return ct.coin_text([PAIR], q)
    task = ca.new_task('t1', 'A: check JUP B: write posts', ['m/a', 'm/b'], 1.0, mode='jobs')
    out = asyncio.run(ca.run(task, ask, [Page(), Page()], None, ('A', 'B'), feeless))
    a, b = out['windows']
    assert out['status'] == 'done' and a['goal'] == 'check JUP' and b['goal'] == 'write posts'
    assert a['coin']['pair'] == 'P1' and a['url'] == 'feeless:coin'          # its window shows OUR chart of the coin
    assert a['scratch'] == [] and a['scratchN'] == 1                          # the scratch pad is thrown away after the task
    assert 'JUP looks liquid' in out['answer'] and '5 posts drafted' in out['answer'] and len(out['keep']) == 2


def test_plan_mode_merge_returns_the_answer_and_what_to_keep():
    calls = {'n': 0}

    async def ask(model, messages):
        calls['n'] += 1
        sys = messages[0]['content']
        if 'lead two AI models' in sys:
            return json.dumps({'fast': '', 'a': 'half A', 'b': 'half B'}), 0
        if 'Combine the two halves' in sys:
            return json.dumps({'answer': 'one answer', 'keep': ['fact both saw']}), 0
        return json.dumps({'action': 'answer', 'say': 'done'}), 0
    task = ca.new_task('t2', 'best sports bet tonight?', ['m/a', 'm/b'], 1.0)
    out = asyncio.run(ca.run(task, ask, [Page(), Page()], None))
    assert out['answer'] == 'one answer' and out['keep'] == ['fact both saw'] and out['mode'] == 'plan'


def test_models_switch_after_24h_and_delete_is_guarded(monkeypatch):
    import time
    import feecat_service as svc
    from fastapi import HTTPException
    from types import SimpleNamespace
    cat = {'id': 'g1', 'ownerId': 'o', 'name': 'Scout', 'createdAt': time.time(), 'status': 'running', 'positions': [],
           'brainsCfg': {'brains': ['a/x'], 'brainMode': 'turns', 'billing': 'payg', 'prompt': 'sealed', 'kind': 'general', 'decisions': [], 'cloud': [{'text': 'kept'}]}}
    store = {'cats': {'g1': cat}, 'events': []}
    monkeypatch.setattr(svc, '_load', lambda: store)
    monkeypatch.setattr(svc, '_save', lambda s: None)
    req = SimpleNamespace(headers={})

    def act(**k):
        return asyncio.run(svc.cat_action('g1', svc.ActionPayload(ownerId='o', **k), req))
    with pytest.raises(HTTPException) as e:
        act(action='models', brains=['b/y'])
    assert '24 h' in e.value.detail
    cat['createdAt'] -= svc.MODEL_LOCK_SEC + 1

    async def models():
        return {'models': [{'id': 'b/y'}, {'id': 'a/x'}]}

    async def limit(session=''):
        return 2
    monkeypatch.setattr(svc, '_or_models', models)
    monkeypatch.setattr(svc, '_model_limit', limit)
    act(action='models', brains=['b/y'])
    assert cat['brainsCfg']['brains'] == ['b/y'] and cat['brainsCfg']['prompt'] == 'sealed' and cat['brainsCfg']['cloud'] == [{'text': 'kept'}]
    with pytest.raises(HTTPException):
        act(action='delete', text='Scout')                    # retire first
    cat['revoked'] = True
    with pytest.raises(HTTPException):
        act(action='delete', text='wrong name')
    assert act(action='delete', text='scout')['deleted'] == 'g1' and 'g1' not in store['cats']


@pytest.mark.parametrize('url,ok', [('https://feeless.app/', True), ('https://feeless.app/terminal/trenches', True), ('https://feeless.app/terminal/launch', False),
                                    ('https://feeless.app/terminal/feecat/agents', False), ('https://feeless.app/api/cats', False), ('https://feeless.app/login', False),
                                    ('http://localhost:51367/', False)])
def test_agents_browse_feeless_but_never_launch_create_or_sign_in(url, ok):
    if ok:
        assert cp.check_url(url)
    else:
        with pytest.raises(ValueError):
            cp.check_url(url)


def test_owner_types_a_model_id_in_the_rig_and_the_router_uses_it(monkeypatch):
    import ai_rig as rg
    import ai_router as ar
    r = rg.clean({'local': {'model': 'qwen/qwen3.5-9b'}, 'lan': {'model': 'bad id with spaces'}})
    assert r['local']['model'] == 'qwen/qwen3.5-9b' and not r['lan'].get('model')
    monkeypatch.setattr(ar, 'RIG', r)
    assert ar.provider({'LOCAL_LLM_MODEL': 'old-model', 'LOCAL_LLM_ENABLED': '1'}, 'local')['model'] == 'qwen/qwen3.5-9b'
    v = rg.view(r, {'local': 'qwen/qwen3.5-9b'})
    assert next(x for x in v['rows'] if x['key'] == 'local')['rigModel'] == 'qwen/qwen3.5-9b'


def test_sign_up_password_is_sealed_never_seen_by_the_model_and_typed_only_as_the_placeholder(monkeypatch):
    import feecat_service as svc
    import cat_vault as cv
    monkeypatch.setenv('BROKER_SECRET_KEY', 'test-secret')
    typed = {}

    class SignupPage(Page):
        async def type(self, label, value):
            typed[label] = value
            return 'typed'
    seen_by_model = []
    script = [{'action': 'new_login', 'url': 'https://proton.me/signup', 'label': 'scout@proton.me'}, {'action': 'type', 'label': 'password', 'value': '{{password}}'},
              {'action': 'media', 'url': 'https://cdn.example.com/ad.mp4', 'text': 'launch ad'}, {'action': 'answer', 'say': 'signed up'}]

    async def ask(model, messages):
        seen_by_model.append(messages[-1]['content'])
        return json.dumps(script.pop(0)), 0
    task = ca.new_task('t3', 'make a proton email', ['m/a'], 1.0)
    task['mode'] = 'jobs'
    out = asyncio.run(ca.run(task, ask, [SignupPage()], None, ('A',)))
    pw = out['logins'][0]['pw']
    assert typed['password'] == pw and len(pw) == 20 and not any(pw in m for m in seen_by_model)   # typed for real, never shown to the model
    assert 'pw' not in out['windows'][0]
    cat = {'id': 'g', 'ownerId': 'o', 'brainsCfg': {'brains': ['m/a']}}
    cv.put_login(cat, 'proton.me', 'scout@proton.me', pw)
    assert pw not in json.dumps(svc._no_keys(cat)) and svc._no_keys(cat)['logins'] == [{'site': 'proton.me', 'user': 'scout@proton.me', 'at': cat['logins'][0]['at']}]
    assert cv.reveal(cat, 'https://proton.me/x', 'scout@proton.me') == pw
    cv.add_media(cat, 'https://cdn.example.com/ad.mp4', 'launch ad', now=1)
    assert cat['media'][0]['kind'] == 'video' and cv.clean_media(cat, now=1 + cv.MEDIA_TTL + 1) == []
