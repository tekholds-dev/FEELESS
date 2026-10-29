import asyncio
import json
import pytest
import cat_policy as policy
import cat_agent as agent
import launch_cat as launch


@pytest.mark.parametrize('url', ['http://localhost:51367/', 'http://127.0.0.1/', 'https://feecat.com/', 'https://x.feecat.app/', 'https://feeless.app/', 'https://example.org/api/cats', 'file:///etc/passwd', 'https://user:pass@example.org', 'http://[::1]/', 'http://169.254.169.254/'])
def test_cat_network_boundary(url):
    with pytest.raises(ValueError):
        policy.check_url(url)


def test_own_public_hostname_is_blocked(monkeypatch):
    monkeypatch.setenv('PUBLIC_SITE_URL', 'https://custom.example')
    with pytest.raises(ValueError):
        policy.check_url('https://custom.example/login')
    assert policy.check_url('https://docs.python.org/3/') == 'docs.python.org'


@pytest.mark.parametrize('text', ['rug ppl', 'impersonate the creator', 'mass spam', 'create another FeeCat', 'sign in to FEELESS'])
def test_prohibited_jobs(text):
    assert policy.refusal(text)


def test_job_tools_cannot_be_elevated():
    assert policy.toolkit('content', {'build': True, 'storage': False}) == {'browse': True, 'storage': False}
    assert policy.toolkit('code')['build']
    with pytest.raises(ValueError):
        policy.toolkit('root')


def test_three_models_are_all_scheduled_and_share_locked_brief():
    b = launch.clean({'brains': ['a','b','c'], 'brainMode': 'together', 'prompt': 'Shared instructions'}, max_models=3)
    assert launch.who_asks(b, 0) == ['a','b','c']
    b['brainMode'] = 'turns'
    assert [launch.who_asks(b, i) for i in range(3)] == [['a'],['b'],['c']]
    assert launch.clean({'prompt': 'replacement'}, b, max_models=3)['prompt'] == 'Shared instructions'
    assert launch.plan([{'perDecision': 1}] * 3, 'together')['perDecision'] == 3


def test_efforts_are_only_from_model_metadata():
    m = launch.slim({'id': 'm/test', 'pricing': {'prompt': '.000001', 'completion': '.000002'}, 'reasoning': {'supported_efforts': ['low','max']}})
    assert m['efforts'] == ['low','max']
    assert launch.slim({'id':'m/other'})['efforts'] == []


def test_disabled_tool_never_reaches_page_and_refusal_is_visible():
    class Page:
        url = title = ''
        async def goto(self, url):
            raise AssertionError('Disabled browser must not execute')
    calls = iter([{'a':'find info'}, {'action':'open', 'url':'https://example.org'}, {'action':'answer','say':'No browsing permission'}])
    async def ask(*_):
        return json.dumps(next(calls)), 0
    t = agent.new_task('x', 'find info', ['m'], 1)
    t['tools'] = {'browse': False}
    asyncio.run(agent.run(t, ask, [Page()], None, ['M']))
    assert t['status'] == 'done' and t['refusals']


def test_coder_saves_actual_html_as_preview_artifact():
    class Page:
        url = title = ''
    calls = iter([{'a':'build'}, {'action':'build', 'say':'<!doctype html><h1>My page</h1>'}, {'action':'answer','say':'Preview ready'}])
    async def ask(*_):
        return json.dumps(next(calls)), 0
    t = agent.new_task('x', 'build a page', ['m'], 1)
    t['tools'] = policy.toolkit('code')
    asyncio.run(agent.run(t, ask, [Page()], None, ['M']))
    assert t['artifacts'][0]['content'] == '<!doctype html><h1>My page</h1>'


def test_call_bound_stops_before_provider_charge():
    async def ask(*_):
        raise AssertionError('Over-budget model must not be called')
    ask.cost_bound = lambda *_: 2
    t = agent.new_task('x', 'question', ['m'], 1)
    asyncio.run(agent.run(t, ask, [None], None, ['M']))
    assert t['status'] == 'stopped' and t['cost'] == 0


def test_cat_wallet_cannot_get_user_session(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_json_load', lambda *_: {'cats': {'x': {'agentWallet': {'address': 'cat-wallet'}}}})
    with pytest.raises(rs.HTTPException) as exc:
        asyncio.run(rs.chat_session(rs.SessionIn(address='cat-wallet', ts=0, signature='x')))
    assert exc.value.status_code == 403
