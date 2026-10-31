import asyncio
import json
import pytest
import cat_agent as ca
import cat_policy as cp
import cat_tools as ct

@pytest.fixture(autouse=True)
def _signed_owner(monkeypatch):
    """A test session token IS its wallet here; the wallet owner lock itself is proven in test_agent_owner_lock.py."""
    import feecat_service as svc
    monkeypatch.setattr(svc, '_session_wallet', lambda s: str(s or ''))
    monkeypatch.setattr(svc, '_fresh_session_wallet', lambda s, now=None: str(s or ''))

PAIR = {'pairAddress': 'P1', 'baseToken': {'symbol': 'JUP', 'address': 'M1'}, 'priceUsd': '0.42', 'marketCap': 1.2e9, 'liquidity': {'usd': 3.4e6},
        'volume': {'h24': 8.1e6}, 'priceChange': {'h24': -2.5}, 'dexId': 'raydium'}


def test_feeless_tools_read_our_data_and_hand_back_the_coin_for_the_chart():
    text, coin = ct.coin_text([PAIR], 'JUP')
    assert '$JUP' in text and '$1.2B' in text and '−' not in text and coin == {'pair': 'P1', 'mint': 'M1', 'symbol': 'JUP'}
    assert ct.coin_text([], 'NOPE') == ('FEELESS found no coin for "NOPE".', None)
    assert 'APY 40.0%' in ct.pools_text({'pools': [{'sym': 'SOL-USDC', 'proto': 'raydium', 'apy': 40, 'tvl': 2e6}, {'sym': 'X', 'apy': None}]})
    assert 'OPEN' in ct.gaps_text([{'sym': 'JLP', 'gapPct': 0.7, 'netPct': 0.1, 'n': 3, 'open': True}])
    assert 'SOL-PERP up to 250x' in ct.perps_text()


@pytest.mark.parametrize('text', ['launch a new memecoin on FEELESS', 'create a liquidity pool on feeless', 'make another agent', 'spawn a new AI agent', 'create a FeeCat',
                                  'create an AI agent on FEELESS', 'make a fee cat on virtuals.io', 'deploy a token on feecat'])
def test_agents_never_create_agents_or_launch_on_feeless(text):
    assert cp.refusal(text)


@pytest.mark.parametrize('text', ['research the newest coins on the trench', 'is this pool worth it?', 'compare two agents', 'launch a memecoin on pump.fun for my brand',
                                  'create an AI agent on virtuals.io for my brand', 'launch a coin on pump.fun with the image I uploaded'])
def test_reading_about_coins_pools_agents_is_fine(text):
    assert cp.refusal(text) is None


def test_each_mind_gets_its_own_job():
    assert ca.split_jobs('A: write the video script  B: make 5 social posts') == ['write the video script', 'make 5 social posts']
    one = ca.split_jobs('best sports bet tonight?')   # no labels: one mind owns it, the other supports, the job never runs twice
    assert one[0] == 'best sports bet tonight?' and one[1].startswith('SUPPORT ROLE') and 'Do NOT do it too' in one[1]
    assert ca.split_jobs('A: write the thread') == ['write the thread', '']   # addressed to one mind: the other stays idle
    assert ca.split_jobs('B: find sources') == ['', 'find sources']
    assert ca.split_jobs('solo job', 1) == ['solo job']


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
        return asyncio.run(svc.cat_action('g1', svc.ActionPayload(ownerId='o', session='o', **k), req))
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
    act(action='skin', ownerId='o', session='o', look={'bg': 'creek', 'acc': '#7FD3FF'})
    assert cat['skin'] == {'bg': 'creek', 'acc': '#7fd3ff'}
    with pytest.raises(HTTPException):
        act(action='skin', ownerId='o', session='o', look={'bg': 'lava', 'acc': '#000000'})
    with pytest.raises(HTTPException):
        act(action='skin', ownerId='someone-else', session='someone-else', look={'bg': 'globe', 'acc': '#b388ff'})


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
    act = lambda cid, **k: asyncio.run(svc.cat_action(cid, svc.ActionPayload(ownerId='o', session='o', **k), SimpleNamespace(headers={})))
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
    assert asyncio.run(svc.get_cat('z1', ownerId='browser-secret-123', session='browser-secret-123'))['cat']['mine'] is True
    assert asyncio.run(svc.get_cat('z1', ownerId='guess', session='guess'))['cat']['mine'] is False
    assert 'browser-secret-123' not in json.dumps(asyncio.run(svc.list_cats(ownerId='browser-secret-123', session='browser-secret-123')))


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

    async def open_session(http, env, ctx=None):
        return {'provider': 'reader'}, []
    monkeypatch.setattr(fs._cb, 'open_session', open_session)
    monkeypatch.setattr(fs._cb, 'ReaderPage', lambda http: Page())

    async def close_session(*a):
        return None
    monkeypatch.setattr(fs._cb, 'close_session', close_session)
    with TestClient(fs.app) as c:
        brief = 'Answer my question like an analyst, cite sources.\n\nHOW YOU TWO WORK — each of you owns a separate job.\n\nRULES — never invent facts.'
        r = c.post('/api/cats', json={'ownerId': 'w', "session": 'w', 'name': 'Scout', 'handle': 'scout', 'brains': ['m/a', 'm/b'], 'brainKind': 'general', 'brainMode': 'turns',
                                      'billing': 'payg', 'prompt': brief, 'job': 'researcher', 'workMode': 'jobs', 'taskCap': 0.25})
        assert r.status_code == 200, r.text
        cid = r.json()['cat']['id']
        cat = fs._load()['cats'][cid]
        assert cat['taskCap'] == 0.25 and cat['workMode'] == 'jobs' and cat['brainsCfg']['kind'] == 'general' and cat['job'] == 'researcher'
        assert c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'intruder', "session": 'intruder', 'text': 'hi'}).status_code == 403   # only its owner
        assert cat['brainsCfg']['credit'] == 0.0                                             # 🧭 a general agent starts at $0 — only real money buys credit
        st_ = fs._load(); st_['cats'][cid]['brainsCfg']['credit'] = 10.0; st_['cats'][cid]['creditPaid'] = [{'sig': 'REALSIG', 'usd': 10.0}]; fs._save(st_)   # (as if its owner paid $10 of credit)
        r = c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'w', "session": 'w', 'text': 'A: research Solana B: write a thread on it'})
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


def test_a_new_model_sorts_the_old_cloud_and_a_bad_answer_never_loses_memory(tmp_path, monkeypatch):
    import feecat_service as fs
    assert fs._kept('{"keep": [0, 2, 2, 9, -1]}', 3) == [0, 2] and fs._kept('no json', 3) == [0, 1, 2]
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    store = {'events': [], 'cats': {'c1': {'id': 'c1', 'name': 'Scout', 'brainsCfg': {'brains': ['m/new'], 'credit': 1.0, 'spent': 0.0,
             'cloud': [{'text': 'JUP pool 3.4M'}, {'text': 'stale: SOL at $20'}, {'text': 'threads under 6 posts land best'}]}}}}
    fs._save(store)
    seen = {}

    async def or_call(model, messages, **k):
        seen['model'] = model; seen['notes'] = messages[1]['content']
        return '{"keep": [0, 2]}', 0.002
    monkeypatch.setattr(fs, '_or_call', or_call)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(fs.asyncio, 'sleep', lambda s: real_sleep(0))
    asyncio.run(fs._sort_cloud('c1', 'm/new'))
    b = fs._load()['cats']['c1']['brainsCfg']
    assert seen['model'] == 'm/new' and '1: stale: SOL at $20' in seen['notes']
    assert [c['text'] for c in b['cloud']] == ['JUP pool 3.4M', 'threads under 6 posts land best'] and b['spent'] > 0


def test_house_rules_are_hardcoded_in_every_step_not_the_editable_brief():
    s = ca.ACT_SYS
    assert 'Never launch a coin or pool or create an agent ON FEELESS' in s
    assert 'its own email at a free provider' in s and 'ONLY for the user\'s OWN accounts' in s


def test_an_agents_own_wallet_can_never_make_an_agent_or_launch_a_coin_on_feeless(monkeypatch):
    """🚫 hard lock (owner 2026-10-31): whatever the prompt says, the agent's own wallet is refused by FEELESS's create-agent and launch endpoints."""
    fs = pytest.importorskip("feecat_service")
    from fastapi.testclient import TestClient
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'o', 'revoked': False, 'agentWallet': {'address': 'AGENTWALLET1111'}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_session_wallet', lambda s: {'agent-sess': 'AGENTWALLET1111', 'user-sess': 'USERWALLET'}.get(s, ''))
    async def staff(session=''): return False
    monkeypatch.setattr(fs, '_session_staff', staff)
    c = TestClient(fs.app)
    r = c.post('/api/cats', json={'ownerId': 'x', 'name': 'Spawn', 'handle': 'spawn', 'session': 'agent-sess', 'brains': ['m/a'], 'brainKind': 'general'})
    assert r.status_code == 403 and 'never creates another agent' in r.json()['detail']
    assert fs.agent_wallets(store) == {'AGENTWALLET1111'}
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_any_agent_wallets', lambda: {'AGENTWALLET1111'})
    r = TestClient(rs.app).post('/api/reputation/feeless-launch', json={'wallet': 'AGENTWALLET1111', 'mint': 'MINT', 'signature': None})
    assert r.status_code == 403 and 'never launches a coin on FEELESS' in r.json()['detail']


def test_addressed_ask_runs_only_that_mind():
    """owner 2026-10-31: "i asked model b and model a worked" — 'B: …' runs B alone, in plan mode too, and A spends nothing."""
    import asyncio
    calls = []
    async def ask(model, messages):
        calls.append(model); return '{"action": "answer", "say": "done"}', 0.0
    class P:
        url = title = None
        async def read(self): return 'page'
    task = ca.new_task('t1', 'B: find the trending coin', ['m-a', 'm-b'], 0.05, 4, 'plan', None)
    out = asyncio.run(ca.run(task, ask, [P(), P()], lambda i: True))
    assert out['status'] == 'done' and calls == ['m-b'] and out['windows'][1]['answer'] == 'done'
    assert out['windows'][0]['goal'] == '' and out['windows'][0]['bubble'] == 'not asked — idle'


def test_stop_cancels_a_hung_task():
    """owner 2026-10-31: "the stop btn not stopping them" — a model call that never returns is cancelled after the grace."""
    import asyncio
    import feecat_service as fs
    async def main():
        async def hung():
            try:
                await asyncio.sleep(60)
            finally:
                w['done'] = True
        w = {'task': {'status': 'working', 'windows': [{'status': 'working'}, {'status': 'done'}]}}
        w['runner'] = asyncio.create_task(hung())
        await fs._hard_stop(w, grace=0.01)
        await asyncio.sleep(0)
        return w
    w = asyncio.run(main())
    assert w['done'] and w['task']['status'] == 'stopped' and [x['status'] for x in w['task']['windows']] == ['stopped', 'done']


def test_a_window_that_errors_never_stays_working():
    import asyncio
    async def ask(model, messages):
        raise RuntimeError('model_not_found')
    class P:
        url = title = None
        async def read(self): return 'page'
    task = ca.new_task('t2', 'B: anything', ['m-a', 'm-b'], 0.05, 4, 'jobs', None)
    out = asyncio.run(ca.run(task, ask, [P(), P()], lambda i: True))
    assert out['windows'][1]['status'] == 'error' and 'model_not_found' in out['windows'][1]['answer']


def test_the_coin_tool_hands_the_mind_the_chart_snapshot_and_the_research_doors():
    """owner 2026-10-31: proof the models read the FEELESS chart + research from the chart's icons (X search by CA) — network faked."""
    import asyncio
    pair = {**PAIR, 'info': {'socials': [{'type': 'twitter', 'url': 'https://x.com/jup'}]}}
    bars = [[1700000000 + i * 300, 1.0 + i * .01, 1.02 + i * .01, .99 + i * .01, 1.01 + i * .01, 100 if i < 18 else 400] for i in range(24)]
    class R:
        def __init__(self, j): self._j = j
        def json(self): return self._j
    class H:
        async def get(self, url, params=None, timeout=None):
            return R({'candles': bars}) if '/api/candles/' in url else R({'pairs': [pair]})
    text, coin = asyncio.run(ct.run_tool(H(), 'coin', 'JUP'))
    assert coin['pair'] == PAIR['pairAddress']
    assert 'FEELESS chart $' in text and 'last 120 min' in text and 'up its range' in text and 'volume last 30 min' in text
    mint = PAIR['baseToken']['address']
    assert f'https://x.com/search?q={mint}&f=live' in text and 'https://x.com/jup' in text and f'https://rugcheck.xyz/tokens/{mint}' in text
    import cat_policy as cp
    assert cp.research_ok(f'https://x.com/search?q={mint}&f=live') and cp.research_ok(f'https://rugcheck.xyz/tokens/{mint}')


def test_a_cloud_window_can_never_reach_this_machine():
    """owner 2026-10-31: FEELESS on localhost stays private — the agents' cloud browser refuses every private / loopback address."""
    import asyncio, pytest
    import cat_browser as cb
    for u in ('http://localhost:51367/', 'http://127.0.0.1:5001/api/market/feed', 'http://192.168.1.10/', 'http://[::1]:5088/'):
        with pytest.raises((ValueError, OSError)):
            asyncio.run(cb.public_url(u))


def test_agent_windows_are_view_only_until_they_ask_a_person():
    """owner 2026-10-31: "agent windows locked so only the models control them" — the clickable view exists only for a hand-off."""
    import cat_browser as cb
    assert cb.steel_view('https://x.steel.dev/v?s=1').endswith('interactive=false')
    assert cb.steel_view('https://x.steel.dev/v?s=1', hand=True).endswith('interactive=true')


def test_a_trader_mind_is_told_to_read_the_chart_then_the_x_search():
    import asyncio
    seen = []
    async def ask(model, messages):
        seen.append(messages[0]['content']); return '{"action": "answer", "say": "ok"}', 0.0
    class P:
        url = title = None
        async def read(self): return 'page'
    task = ca.new_task('t3', 'A: research $BONK', ['m-a', 'm-b'], 0.05, 4, 'jobs', None); task['research'] = True
    asyncio.run(ca.run(task, ask, [P(), P()], lambda i: True))
    assert 'RESEARCH ORDER' in seen[0] and 'X live search for the contract' in seen[0]


def test_x_login_wall_asks_a_person():
    """a real run (2026-10-31) landed on X's onboarding login and kept going — it is a sign-in: the owner saves X once in Credentials."""
    import cat_browser as cb
    assert cb.needs_human('https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fsearch&mode=login', 'See what is happening')
    assert cb.needs_human('https://x.com/i/flow/login', '')
    assert cb.needs_human('https://x.com/search?q=abc&f=live', 'Latest posts') is None


def test_no_answer_in_5_min_files_the_task_and_moves_on(monkeypatch):
    """owner 2026-10-31: "if no human interaction within 5 mins the agent moves on … and files it to come back to when the user is active"."""
    import asyncio
    calls = []
    async def ask(model, messages):
        calls.append(1)
        return ('{"action": "open", "url": "https://x.com/i/flow/login"}' if len(calls) == 1 else '{"action": "answer", "say": "x"}'), 0.0
    class P:
        url = title = None
        async def goto(self, u): self.url = u; return 'Sign in to X'
        async def read(self): return 'Sign in to X'
    task = ca.new_task('t4', 'B: read my X feed', ['m-a', 'm-b'], 0.05, 4, 'jobs', None)
    async def wait_human(i):   # the service's wait_human after HUMAN_WAIT_S with nobody there
        task['windows'][i]['parked'] = f'{ca.PARKED}: no answer in 5 min — filed to come back to (a sign-in)'
        task.setdefault('parked', []).append({'why': 'a sign-in', 'mind': i})
        return False
    out = asyncio.run(ca.run(task, ask, [P(), P()], wait_human))
    assert out['status'] == 'parked' and out['why'].startswith(ca.PARKED) and out['parked'][0]['why'] == 'a sign-in'


def test_the_service_files_an_unanswered_window_and_the_desk_can_drop_it(tmp_path, monkeypatch):
    """⏸ end to end in the service: a sign-in nobody answers → after HUMAN_WAIT_S the task is parked + filed (workParked), the desk lists it, Drop removes it."""
    import time as _t
    from fastapi.testclient import TestClient
    import launch_cat as lc
    import feecat_service as fs
    rows = [{'id': f'm/{x}', 'name': x, 'context_length': 131072, 'pricing': {'prompt': '0.0000001', 'completion': '0.0000002'}} for x in ('a', 'b')]
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog(rows)})
    monkeypatch.setattr(fs, 'HUMAN_WAIT_S', 0.05)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test'); monkeypatch.setenv('GENERAL_CAT_LIVE', '1')

    async def or_call(model, messages, **k):
        return json.dumps({'action': 'open', 'url': 'https://x.com/i/flow/login'}), 0.001
    monkeypatch.setattr(fs, '_or_call', or_call)

    async def open_session(http, env, ctx=None):
        return {'provider': 'reader'}, []
    monkeypatch.setattr(fs._cb, 'open_session', open_session)
    class Login(Page):
        async def goto(self, u):
            self.url = u; return 'Sign in to X'
    monkeypatch.setattr(fs._cb, 'ReaderPage', lambda http: Login())

    async def close_session(*a):
        return None
    monkeypatch.setattr(fs._cb, 'close_session', close_session)
    with TestClient(fs.app) as c:
        r = c.post('/api/cats', json={'ownerId': 'w', 'session': 'w', 'name': 'Scout', 'handle': 'scout', 'brains': ['m/a', 'm/b'], 'brainKind': 'general', 'brainMode': 'turns',
                                      'billing': 'payg', 'prompt': 'help', 'job': 'researcher', 'workMode': 'jobs', 'taskCap': 0.25})
        cid = r.json()['cat']['id']
        st_ = fs._load(); st_['cats'][cid]['brainsCfg']['credit'] = 10.0; st_['cats'][cid]['creditPaid'] = [{'sig': 'REALSIG', 'usd': 10.0}]; fs._save(st_)
        assert c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'w', 'session': 'w', 'text': 'B: read my X feed'}).status_code == 200
        for _ in range(100):
            if fs._WORK[cid].get('done'):
                break
            _t.sleep(0.05)
        assert fs._WORK[cid]['task']['status'] == 'parked'
        store = fs._load(); fs._work_settle(store); fs._save(store)
        st = c.post(f'/api/cats/{cid}/work', json={'op': 'state', 'ownerId': 'w', 'session': 'w'}).json()
        assert st['parked'] and st['parked'][0]['text'] == 'B: read my X feed' and 'sign-in' in st['parked'][0]['why']
        c.post(f'/api/cats/{cid}/work', json={'op': 'unpark', 'i': 0, 'ownerId': 'w', 'session': 'w'})
        assert fs._load()['cats'][cid].get('workParked') == []


def test_a_window_handed_to_you_is_let_go_then_taken_back(tmp_path, monkeypatch):
    """🙋 owner 2026-10-31: Cloudflare's "I'm human" box reloaded forever — every request was routed through the agent. While a person has the window,
    the agent lets go (release: nothing routed or attached), then takes it back (start) on the page they left."""
    import time as _t
    from fastapi.testclient import TestClient
    import launch_cat as lc
    import feecat_service as fs
    rows = [{'id': f'm/{x}', 'name': x, 'context_length': 131072, 'pricing': {'prompt': '0.0000001', 'completion': '0.0000002'}} for x in ('a', 'b')]
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog(rows)})
    monkeypatch.setattr(fs, 'HUMAN_WAIT_S', 0.05)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test'); monkeypatch.setenv('GENERAL_CAT_LIVE', '1')

    async def or_call(model, messages, **k):
        return json.dumps({'action': 'open', 'url': 'https://x.com/i/flow/login'}), 0.001
    monkeypatch.setattr(fs, '_or_call', or_call)

    async def open_session(http, env, ctx=None):
        return {'provider': 'steel', 'connect': 'wss://steel/x', 'live': 'https://view'}, []
    monkeypatch.setattr(fs._cb, 'open_session', open_session)
    seen = []
    class Live(Page):
        live = True
        def __init__(self, connect): pass
        async def start(self): seen.append('start'); return self
        async def release(self): seen.append('release')
        async def goto(self, u):
            self.url = u; return 'Sign in to X'
    monkeypatch.setattr(fs._cb, 'LivePage', Live)

    async def close_session(*a):
        return None
    monkeypatch.setattr(fs._cb, 'close_session', close_session)
    with TestClient(fs.app) as c:
        r = c.post('/api/cats', json={'ownerId': 'w', 'session': 'w', 'name': 'Scout', 'handle': 'scout', 'brains': ['m/a', 'm/b'], 'brainKind': 'general', 'brainMode': 'turns',
                                      'billing': 'payg', 'prompt': 'help', 'job': 'researcher', 'workMode': 'jobs', 'taskCap': 0.25})
        cid = r.json()['cat']['id']
        st_ = fs._load(); st_['cats'][cid]['brainsCfg']['credit'] = 10.0; st_['cats'][cid]['creditPaid'] = [{'sig': 'REALSIG', 'usd': 10.0}]; fs._save(st_)
        assert c.post(f'/api/cats/{cid}/work', json={'op': 'ask', 'ownerId': 'w', 'session': 'w', 'text': 'B: read my X feed'}).status_code == 200
        for _ in range(100):
            if fs._WORK[cid].get('done'):
                break
            _t.sleep(0.05)
        assert fs._WORK[cid]['task']['status'] == 'parked' and seen == ['start', 'start', 'release', 'start']   # both windows open · B let go for you · taken back


def test_a_task_cut_off_by_a_restart_is_filed_to_resume_never_lost():
    """🛟 owner 2026-10-31: an ask sent while the service restarted vanished ("nothing happened, I don't see my request")."""
    import feecat_service as fs
    cat = {'id': 'c', 'workNow': {'text': 'B: browse pump.fun and find the best trending coin', 'to': 'both', 'at': 1}}
    assert fs.file_interrupted(cat, now=5) and 'workNow' not in cat
    assert cat['workParked'][0]['text'].startswith('B: browse pump.fun') and 'restarted' in cat['workParked'][0]['why'] and 'restarted' in cat['chat'][-1]['text']
    assert not fs.file_interrupted(cat)
    assert 'workNow' not in fs._no_keys({'workNow': {'text': 'secret ask'}, 'name': 'x'})
