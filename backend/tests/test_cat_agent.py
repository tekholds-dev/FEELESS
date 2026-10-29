"""🧠🧠 The general cat at work: hosted browser chain with fallbacks, the two-model task (fast path · split + merge · human-needed pause · secrets
never typed · the $ cap), all with fakes — nothing is browsed or billed."""
import asyncio
import json

import pytest

import cat_agent as ca
import cat_browser as cb


class R:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


class Http:
    def __init__(self, steel=None, bb=None):
        self.steel, self.bb, self.calls = steel, bb, []

    async def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(url)
        if 'steel' in url:
            return self.steel or R(503, {})
        return self.bb or R(503, {})

    async def get(self, url, headers=None, timeout=None):
        return R(200, {'debuggerFullscreenUrl': 'https://www.browserbase.com/devtools/live?x=1'})


ENV = {'STEEL_API_KEY': 'ste-SECRET', 'BROWSERBASE_API_KEY': 'bb-SECRET', 'BROWSERBASE_PROJECT_ID': 'proj'}


def test_the_chain_falls_steel_then_browserbase_then_the_reader_and_a_live_url_with_a_key_never_leaves():
    assert cb.chain(ENV) == ['steel', 'browserbase', 'reader'] and cb.chain({}) == ['reader']
    assert cb.chain({**ENV, 'BROWSERLESS_API_KEY': 'bl'}) == ['steel', 'browserless', 'browserbase', 'reader']
    bl = asyncio.run(cb._browserless(None, {'BROWSERLESS_API_KEY': 'bl-TOKEN'}))
    assert bl['provider'] == 'browserless' and bl['live'] is None and 'bl-TOKEN' in bl['connect']       # its token rides the CDP address (server-only)
    s, tried = asyncio.run(cb.open_session(Http(steel=R(201, {'id': 'S1', 'debugUrl': 'https://api.steel.dev/v1/sessions/S1/player/tok', 'websocketUrl': 'wss://connect.steel.dev?sessionId=S1&token=t'})), ENV))
    assert s['provider'] == 'steel' and s['live'].endswith('/player/tok') and tried == []
    s, tried = asyncio.run(cb.open_session(Http(bb=R(201, {'id': 'B1', 'connectUrl': 'wss://bb'})), ENV))
    assert s['provider'] == 'browserbase' and s['live'].startswith('https://www.browserbase.com') and tried == [('steel', 'Steel 503')]
    s, tried = asyncio.run(cb.open_session(Http(), ENV))
    assert s['provider'] == 'reader' and s['live'] is None and len(tried) == 2 and 'Steel 503' in s['note']
    assert cb.safe_live('https://x.dev/v?apiKey=abc', ENV) is None and cb.safe_live('https://x.dev/ste-SECRET', ENV) is None and cb.safe_live('http://x', ENV) is None


def test_the_reader_reads_text_finds_results_and_spots_a_sign_in_wall():
    t, body = cb.page_text('<html><title>Kalshi</title><script>x=1</script><body><h1>Markets</h1> <p>Fed &amp; rates</p></body></html>')
    assert t == 'Kalshi' and body == 'Markets Fed & rates'
    hits = cb.search_hits('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fkalshi.com%2Fmarkets&rut=1">Kalshi <b>markets</b></a>')
    assert hits == [{'title': 'Kalshi markets', 'url': 'https://kalshi.com/markets'}]
    assert 'sign-in' in cb.needs_human('https://kalshi.com/sign-in', '') and 'CAPTCHA' in cb.needs_human('https://x.com', 'Verify you are human')
    assert cb.needs_human('https://kalshi.com/markets', 'Fed decision market') is None


class Page:
    def __init__(self, wall=None):
        self.url, self.title, self.wall, self.done = None, None, wall, []

    async def goto(self, url):
        self.url, self.title = url, 'page'; self.done.append(('goto', url))
        return 'Sign in to continue. Password' if self.wall and self.wall in url else 'some facts'

    async def search(self, q):
        self.url = f'search: {q}'; self.done.append(('search', q))
        return '1. a result — https://a.com'

    async def click(self, t):
        self.done.append(('click', t)); return 'clicked'

    async def type(self, label, value):
        self.done.append(('type', label, value)); return 'typed'

    async def read(self):
        return 'after you signed in'


def scripted(by_model):
    """A fake model: each call pops the next scripted reply for that model; every call costs $0.001."""
    async def ask(model, messages):
        return json.dumps(by_model[model].pop(0)), 0.001
    return ask


def test_the_fast_path_answers_from_memory_with_no_browsing():
    t = ca.new_task('t1', 'what is 2+2', ['m/a', 'm/b'], 0.05)
    asyncio.run(ca.run(t, scripted({'m/a': [{'fast': '4'}]}), [Page(), Page()], None))
    assert t['status'] == 'done' and t['fast'] and t['answer'] == '4' and t['cost'] == 0.001


def test_two_windows_split_the_task_each_browses_then_model_a_merges():
    ask = scripted({'m/a': [{'fast': '', 'a': 'Kalshi YES prices', 'b': 'news on US capital'},
                            {'thought': 'open Kalshi', 'action': 'open', 'url': 'https://kalshi.com/markets'},
                            {'thought': 'have it', 'action': 'answer', 'say': 'YES at $0.30'}, {'merged': 1}],
                    'm/b': [{'thought': 'search news', 'action': 'search', 'q': 'US capital'}, {'thought': 'done', 'action': 'answer', 'say': 'news says up'}]})

    async def ask2(model, messages):   # the merge step returns plain text
        txt, usd = await ask(model, messages)
        return ('Both agree: YES at $0.30, news says up' if '"merged"' in txt else txt), usd
    pa, pb = Page(), Page()
    t = ca.new_task('t2', 'best Kalshi bid on US capital', ['m/a', 'm/b'], 1.0)
    asyncio.run(ca.run(t, ask2, [pa, pb], None))
    assert t['status'] == 'done' and t['answer'].startswith('Both agree')
    assert pa.done == [('goto', 'https://kalshi.com/markets')] and pb.done == [('search', 'US capital')]
    assert t['windows'][0]['answer'] == 'YES at $0.30' and t['windows'][1]['goal'] == 'news on US capital'
    assert [s['action'] for s in t['windows'][1]['steps']] == ['search', 'answer'] and t['cost'] == pytest.approx(0.006)


def test_a_sign_in_wall_pauses_the_window_for_the_human_and_a_secret_is_never_typed():
    waits = []

    async def wait_human(i):
        waits.append(i); return True
    ask = scripted({'m/a': [{'fast': '', 'a': 'log in', 'b': 'x'}, {'thought': 'open', 'action': 'open', 'url': 'https://site.com/login'},
                            {'thought': 'type pw', 'action': 'type', 'label': 'Password', 'value': 'hunter2'}, {'action': 'answer', 'say': 'in'}, 'Merged'],
                    'm/b': [{'action': 'answer', 'say': 'ok'}]})

    async def ask2(model, messages):
        by = await ask(model, messages)
        return (by[0].strip('"') if by[0] == '"Merged"' else by[0]), by[1]
    pa = Page(wall='/login')
    t = ca.new_task('t3', 'sign me up', ['m/a', 'm/b'], 1.0)
    asyncio.run(ca.run(t, ask2, [pa, Page()], wait_human))
    assert waits == [0, 0]                                                    # the wall, then the password attempt — both handed to the human
    assert not any(d[0] == 'type' for d in pa.done)                           # it never typed the password
    assert ca.blocked_value('Password', 'x') and ca.blocked_value('Card', '4111 1111 1111 1111') and not ca.blocked_value('Search', 'fed rates')


def test_the_cap_stops_a_task_and_stop_keeps_what_it_has():
    async def pricey(model, messages):
        return json.dumps({'fast': '', 'a': 'x', 'b': 'y'}), 0.06
    t = ca.new_task('t4', 'research', ['m/a', 'm/b'], 0.05)
    asyncio.run(ca.run(t, pricey, [Page(), Page()], None))
    assert t['status'] == 'stopped' and 'budget reached' in t['why']
    assert ca.parse_json('noise {"a": {"b": 1}} tail') == {'a': {'b': 1}} and ca.parse_json('none') == {}


def test_the_workbench_is_the_owners_only_refuses_while_model_calls_are_off_and_settles_cost_into_the_chat(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'g1': {'id': 'g1', 'name': 'Gen', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0,
                             'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 1.0, 'billing': 'payg'}},
                      't1': {'id': 't1', 'name': 'Trd', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0, 'brainsCfg': {'kind': 'trading', 'brains': ['m/a']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    c = TestClient(fs.app)
    assert c.post('/api/cats/g1/work', json={'op': 'state', 'ownerId': 'b2'}).status_code == 403
    assert c.post('/api/cats/g1/work', json={'op': 'state', 'ownerId': 'b1'}).json()['task'] is None
    monkeypatch.setattr(fs, '_work_live', lambda: False)
    r = c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', 'text': 'research Kalshi'})
    assert r.status_code == 400 and 'Model calls are off' in r.json()['detail']                     # nothing sent, nothing charged
    assert c.post('/api/cats/t1/work', json={'op': 'ask', 'ownerId': 'b1', 'text': 'x'}).status_code == 400   # a trading cat does not browse
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', 'cap': 9}).json()['cap'] == fs.TASK_CAP_MAX
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', 'cap': 0.0001}).json()['cap'] == 0.005
    t = ca.new_task('x', 'q', ['m/a', 'm/b'], 0.05); t.update(status='done', answer='A', cost=0.012)
    fs._WORK['g1'] = {'task': t, 'done': True, 'at': 1.0}
    fs._work_settle(store)
    b = store['cats']['g1']['brainsCfg']
    assert b['credit'] == 0.988 and [m['by'] for m in store['cats']['g1']['chat']] == ['you', 'cats'] and store['cats']['g1']['chat'][1]['cost'] == 0.012
    fs._work_settle(store); assert b['credit'] == 0.988                                              # settled once
    fs._WORK.pop('g1', None)


def test_let_it_go_queues_asks_runs_the_next_on_its_own_and_gives_a_long_step_budget(monkeypatch):
    """Owner Q1: "let them go" — asks queue while it works; each finished task starts the next; a stopped one pauses the queue."""
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    assert ca.new_task('x', 'q', ['m/a'], 1, ca.GO_STEPS)['stepsMax'] == ca.GO_STEPS > ca.STEP_MAX
    store = {'cats': {'g1': {'id': 'g1', 'name': 'Gen', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0,
                             'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 1.0, 'billing': 'payg'}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda: True)
    started = []
    monkeypatch.setattr(fs, '_work_start', lambda cid, cat, text, to=None: started.append(text))
    c = TestClient(fs.app)
    fs._WORK['g1'] = {'task': ca.new_task('t', 'first', ['m/a'], 0.05), 'done': False, 'at': 1.0}
    assert c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', 'text': 'next'}).status_code == 409     # off: busy refuses
    assert c.post('/api/cats/g1/work', json={'op': 'go', 'ownerId': 'b1', 'on': True}).json()['go'] is True
    r = c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', 'text': 'next'}).json()
    assert [q['text'] for q in r['queue']] == ['next'] and started == []
    fs._WORK['g1']['task'].update(status='done', answer='A', cost=0.01); fs._WORK['g1']['done'] = True
    fs._work_settle(store)
    assert started == ['next'] and store['cats']['g1']['workQueue'] == []
    c.post('/api/cats/g1/work', json={'op': 'go', 'ownerId': 'b1', 'on': False}); assert store['cats']['g1']['workQueue'] == []
    fs._WORK.pop('g1', None)
