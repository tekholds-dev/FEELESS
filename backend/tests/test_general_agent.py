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


def test_an_agents_desk_look_is_saved_on_the_agent_by_its_owner(monkeypatch):
    import feecat_service as svc
    from fastapi import HTTPException
    from types import SimpleNamespace
    cat = {'id': 'k1', 'ownerId': 'o', 'name': 'Scout', 'status': 'running', 'positions': [], 'createdAt': 0}
    store = {'cats': {'k1': cat}, 'events': []}
    monkeypatch.setattr(svc, '_load', lambda: store)
    monkeypatch.setattr(svc, '_save', lambda s: None)
    act = lambda **k: asyncio.run(svc.cat_action('k1', svc.ActionPayload(**k), SimpleNamespace(headers={})))
    act(action='skin', ownerId='o', look={'bg': 'creek', 'acc': '#7FD3FF'})
    assert cat['skin'] == {'bg': 'creek', 'acc': '#7fd3ff'}
    with pytest.raises(HTTPException):
        act(action='skin', ownerId='o', look={'bg': 'lava', 'acc': '#000000'})
    with pytest.raises(HTTPException):
        act(action='skin', ownerId='someone-else', look={'bg': 'globe', 'acc': '#b388ff'})


def test_general_brief_hourly_edits_and_proposals_need_approval_trader_stays_sealed(monkeypatch):
    import time
    import feecat_service as svc
    from fastapi import HTTPException
    from types import SimpleNamespace
    gen = {'id': 'g1', 'ownerId': 'o', 'name': 'Scout', 'status': 'running', 'positions': [], 'chat': [{'text': 'best bet tonight?'}],
           'brainsCfg': {'brains': ['a/x'], 'kind': 'general', 'prompt': 'old brief', 'credit': 5, 'spent': 0, 'billing': 'payg'}}
    tr = {'id': 't1', 'ownerId': 'o', 'name': 'Degen', 'status': 'running', 'positions': [], 'brainsCfg': {'brains': ['a/x'], 'kind': 'trading', 'prompt': 'sealed'}}
    store = {'cats': {'g1': gen, 't1': tr}, 'events': []}
    monkeypatch.setattr(svc, '_load', lambda: store)
    monkeypatch.setattr(svc, '_save', lambda s: None)

    async def fake_or(model, messages, **k):
        return json.dumps({'brief': 'Research FEELESS first, cite sources, and ask before spending anything.', 'why': 'clearer for both'}), 0.001
    monkeypatch.setattr(svc, '_or_call', fake_or)
    act = lambda cid, **k: asyncio.run(svc.cat_action(cid, svc.ActionPayload(ownerId='o', **k), SimpleNamespace(headers={})))
    with pytest.raises(HTTPException):
        act('t1', action='brief', text='a brand new trading brief for it')
    act('g1', action='brief', text='Find the three best sports bets with sources every evening.')
    assert gen['brainsCfg']['prompt'].startswith('Find the three')
    with pytest.raises(HTTPException) as e:
        act('g1', action='brief', text='another brief within the same hour please')
    assert 'once an hour' in e.value.detail
    act('g1', action='brief_propose')
    assert gen['brainsCfg']['briefProposal']['text'].startswith('Research FEELESS first') and gen['brainsCfg']['prompt'].startswith('Find the three')   # not live yet
    with pytest.raises(HTTPException):
        act('g1', action='brief_propose')                                              # once an hour
    act('g1', action='brief_approve')
    assert gen['brainsCfg']['prompt'].startswith('Research FEELESS first') and gen['brainsCfg']['briefProposal'] is None


def test_user_login_popout_types_their_credentials_blind():
    typed = {}

    class LoginPage(Page):
        async def type(self, label, value):
            typed[label] = value
            return 'typed'
    script = [{'action': 'ask_login', 'url': 'https://x.com/login'}, {'action': 'type', 'label': 'username', 'value': '{{username}}'},
              {'action': 'type', 'label': 'password', 'value': '{{password}}'}, {'action': 'answer', 'say': 'logged in'}]
    seen = []

    async def ask(model, messages):
        seen.append(messages[-1]['content'])
        return json.dumps(script.pop(0)), 0
    task = ca.new_task('t4', 'post my draft on X', ['m/a'], 1.0, mode='jobs')

    async def wait_human(i):   # the owner types their login in the window's private form
        w = task['windows'][i]
        assert w['human']['kind'] == 'login' and w['human']['site'] == 'x.com'
        w['pw'] = {'site': 'x.com', 'user': 'me@mail.com', 'pw': 'S3cret!pass'}
        return True
    out = asyncio.run(ca.run(task, ask, [LoginPage()], wait_human, ('A',)))
    assert typed == {'username': 'me@mail.com', 'password': 'S3cret!pass'} and not any('S3cret' in m or 'me@mail.com' in m for m in seen)
    assert 'pw' not in out['windows'][0]


def test_the_owner_id_never_leaves_the_server_and_only_mine_is_answered(monkeypatch):
    import feecat_service as svc
    cat = {'id': 'z1', 'ownerId': 'browser-secret-123', 'name': 'Scout', 'status': 'running', 'positions': [], 'createdAt': 1, 'brainsCfg': {'brains': ['a/x'], 'kind': 'general'}}
    store = {'cats': {'z1': cat}, 'events': []}
    monkeypatch.setattr(svc, '_load', lambda: store)
    pub = asyncio.run(svc.get_cat('z1'))
    assert 'browser-secret-123' not in json.dumps(pub) and pub['cat']['mine'] is False
    assert asyncio.run(svc.get_cat('z1', ownerId='browser-secret-123'))['cat']['mine'] is True
    assert asyncio.run(svc.get_cat('z1', ownerId='guess'))['cat']['mine'] is False
    assert 'browser-secret-123' not in json.dumps(asyncio.run(svc.list_cats(ownerId='browser-secret-123')))


def test_fee_takes_an_openrouter_model_and_a_new_model_can_start_fresh(monkeypatch):
    import feecat_service as svc
    from types import SimpleNamespace
    fee = {'id': 'leader', 'ownerId': 'feeless-system', 'isLeader': True, 'name': 'Fee', 'status': 'running', 'positions': [], 'createdAt': 0}
    store = {'cats': {'leader': fee}, 'events': []}
    monkeypatch.setattr(svc, '_load', lambda: store)
    monkeypatch.setattr(svc, '_save', lambda s: None)

    async def models():
        return {'models': [{'id': 'a/x'}, {'id': 'b/y'}]}

    async def limit(session=''):
        return 2

    async def creator(addr):
        return True
    monkeypatch.setattr(svc, '_or_models', models)
    monkeypatch.setattr(svc, '_model_limit', limit)
    monkeypatch.setattr(svc, '_is_creator', creator)
    monkeypatch.setattr(svc._real, 'session_wallet', lambda sessions, s: 'CREATOR' if s == 'ok' else None)
    req = SimpleNamespace(headers={})
    act = lambda **k: asyncio.run(svc.cat_action('leader', svc.ActionPayload(address='CREATOR', session='ok', **k), req))
    act(action='models', brains=['a/x'], text='Trade the trenches like a desk; never chase.')
    assert fee['brainsCfg']['brains'] == ['a/x'] and fee['brainsCfg']['prompt'].startswith('Trade the trenches')
    fee['brainsCfg']['cloud'] = [{'text': 'old memory'}]
    act(action='models', brains=['b/y'], memory='keep'); assert fee['brainsCfg']['cloud'] == [{'text': 'old memory'}]
    act(action='models', brains=['a/x'], memory='fresh'); assert fee['brainsCfg']['cloud'] == [] and fee['brainsCfg']['decisions'] == []
    act(action='brief', text='A brand new desk brief for Fee, any time she likes.'); assert fee['brainsCfg']['prompt'].startswith('A brand new')


def test_minds_hand_off_on_separate_jobs_and_each_keeps_its_own_cloud():
    script = {'m/a': [{'action': 'note', 'say': 'Solana: 400ms blocks'}, {'action': 'handoff', 'say': 'research: Solana does 400ms blocks (solana.com)'}, {'action': 'answer', 'say': 'researched'}],
              'm/b': [{'action': 'answer', 'say': 'thread written'}]}
    seen = {}

    async def ask(model, messages):
        seen.setdefault(model, []).append(messages[0]['content'])
        return json.dumps(script[model].pop(0)), 0.001
    task = ca.new_task('t5', 'A: research Solana B: write a thread', ['m/a', 'm/b'], 1.0, mode='jobs')
    task['clouds'] = {1: ['my threads land best under 6 posts']}
    out = asyncio.run(ca.run(task, ask, [Page(), Page()], None, ('A', 'B')))
    a, b = out['windows']
    assert 'FROM YOUR PARTNER: research: Solana does 400ms blocks' in seen['m/b'][0]          # 📦 B gets A's handoff
    assert 'YOUR CLOUD' in seen['m/b'][0] and 'under 6 posts' in seen['m/b'][0]              # ☁ B reads its own cloud
    assert 'YOUR CLOUD' not in seen['m/a'][0]                                                 # A has no cloud yet — never B's
    assert any(s['action'] == 'handoff' for s in a['steps'])
    assert a['best'] == ['Solana: 400ms blocks'] and a['scratch'] == [] and b['best'] == []   # its best notes → its own cloud at settle


def test_each_minds_cloud_never_leaves_in_a_public_cat_view():
    import feecat_service as fs
    out = fs._no_keys({'id': 'c1', 'ownerId': 'o', 'brainsCfg': {'brains': ['m/a'], 'cloud': [], 'minds': {'m/a': [{'text': 'private research'}]}}})
    assert 'minds' not in out['brainsCfg'] and 'ownerId' not in out


def test_a_general_agent_end_to_end_from_the_wizard_to_its_answer_and_clouds(tmp_path, monkeypatch):
    """🚀 the owner's first real general agent, network faked: the wizard's exact create → a two-job ask → both minds work, hand off,
    note → one answer in its chat, each mind's best notes in ITS cloud, $ charged inside its cap, nothing private on the public view."""
    import time as _t
    from fastapi.testclient import TestClient
    import launch_cat as lc
    import feecat_service as fs
    rows = [{'id': f'm/{x}', 'name': x, 'context_length': 131072, 'pricing': {'prompt': '0.0000001', 'completion': '0.0000002'}} for x in ('a', 'b')]
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog(rows)})
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test'); monkeypatch.setenv('GENERAL_CAT_LIVE', '1')
    script = {'m/a': [{'action': 'note', 'say': 'Solana: 400ms blocks'}, {'action': 'handoff', 'say': 'Solana: 400ms blocks (solana.com)'}, {'action': 'answer', 'say': 'Solana researched'}],
              'm/b': [{'action': 'answer', 'say': 'thread drafted from A'}]}
    briefs = []

    async def or_call(model, messages, **k):
        briefs.append(messages[0]['content'])
        return json.dumps(script[model].pop(0)), 0.001
    monkeypatch.setattr(fs, '_or_call', or_call)

    async def open_session(http, env):
        return {'provider': 'reader'}, []
    monkeypatch.setattr(fs._cb, 'open_session', open_session)
    monkeypatch.setattr(fs._cb, 'ReaderPage', lambda http: Page())

    async def close_session(*a):
        return None
    monkeypatch.setattr(fs._cb, 'close_session', close_session)
    with TestClient(fs.app) as c:
        brief = 'Answer my question like an analyst, cite sources.\n\nHOW YOU TWO WORK — each of you owns a separate job.\n\nRULES — never invent facts.'
        r = c.post('/api/cats', json={'ownerId': 'w', 'name': 'Scout', 'handle': 'scout', 'brains': ['m/a', 'm/b'], 'brainKind': 'general', 'brainMode': 'turns',
                                      'billing': 'payg', 'prompt': brief, 'job': 'researcher', 'workMode': 'jobs', 'taskCap': 0.25})
        assert r.status_code == 200, r.text
        cid = r.json()['cat']['id']
        cat = fs._load()['cats'][cid]
        assert cat['taskCap'] == 0.25 and cat['workMode'] == 'jobs' and cat['brainsCfg']['kind'] == 'general' and cat['job'] == 'researcher'
        assert c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'intruder', 'text': 'hi'}).status_code == 403   # only its owner
        r = c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'w', 'text': 'A: research Solana B: write a thread on it'})
        assert r.status_code == 200, r.text
        for _ in range(100):
            if fs._WORK[cid].get('done'):
                break
            _t.sleep(0.05)
        assert fs._WORK[cid].get('done')
        store = fs._load(); fs._work_settle(store); fs._save(store)
        cat = fs._load()['cats'][cid]
        assert all('Answer my question like an analyst' in b for b in briefs)                       # the brief rides every call
        assert 'thread drafted from A' in cat['chat'][-1]['text'] and 'Solana researched' in cat['chat'][-1]['text']
        assert [x['text'] for x in cat['brainsCfg']['minds']['m/a']] == ['Solana: 400ms blocks'] and 'm/b' not in cat['brainsCfg']['minds']
        assert 0 < cat['brainsCfg']['spent'] <= 0.25
        pub = c.get(f'/api/cats/{cid}').json()
        assert 'minds' not in json.dumps(pub.get('cat', pub).get('brainsCfg', {})) and 'ownerId' not in json.dumps(pub)
