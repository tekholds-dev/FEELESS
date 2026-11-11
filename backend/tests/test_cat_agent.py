"""🧠🧠 The general cat at work: hosted browser chain with fallbacks, the two-model task (fast path · split + merge · human-needed pause · secrets
never typed · the $ cap), all with fakes — nothing is browsed or billed."""
import asyncio
import json

import pytest

import cat_agent as ca
import cat_browser as cb

@pytest.fixture(autouse=True)
def _signed_owner(monkeypatch):
    """A test session token IS its wallet here; the wallet owner lock itself is proven in test_agent_owner_lock.py."""
    import feecat_service as svc
    monkeypatch.setattr(svc, '_session_wallet', lambda s: str(s or ''))
    monkeypatch.setattr(svc, '_fresh_session_wallet', lambda s, now=None: str(s or ''))


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
    assert s['provider'] == 'steel' and s['live'].endswith('/player/tok?showControls=false&theme=dark&interactive=false') and s['hand'].endswith('interactive=true') and tried == []
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
    assert pa.done == [('goto', 'https://html.duckduckgo.com/html/?q=Kalshi+YES+prices'), ('goto', 'https://kalshi.com/markets')] and pb.done == [('goto', 'https://html.duckduckgo.com/html/?q=news+US+capital'), ('search', 'US capital')]   # 🔎 a blank window starts on a search
    assert t['windows'][0]['answer'] == 'YES at $0.30' and t['windows'][1]['goal'] == 'news on US capital'
    assert [s['action'] for s in t['windows'][1]['steps']] == ['open', 'plan', 'search', 'answer'] and t['cost'] == pytest.approx(0.006)


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
    assert c.post('/api/cats/g1/work', json={'op': 'state', 'ownerId': 'b2', "session": 'b2'}).status_code == 403
    assert c.post('/api/cats/g1/work', json={'op': 'state', 'ownerId': 'b1', "session": 'b1'}).json()['task'] is None
    monkeypatch.setattr(fs, '_work_live', lambda *_a: False)
    r = c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', "session": 'b1', 'text': 'research Kalshi'})
    assert r.status_code == 400 and 'Model calls are off' in r.json()['detail']                     # nothing sent, nothing charged
    assert c.post('/api/cats/t1/work', json={'op': 'ask', 'ownerId': 'b1', "session": 'b1', 'text': 'x'}).status_code == 400   # a trading cat does not browse
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', "session": 'b1', 'cap': 9}).json()['cap'] == fs.TASK_CAP_MAX
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', "session": 'b1', 'cap': 0.0001}).json()['cap'] == 0.005
    fs.keep_owned({**fs._load()['cats']['g1'], 'taskCap': 0.15})   # an earlier owner action remembered $0.15 (laid over every save)
    assert c.post('/api/cats/g1/work', json={'op': 'cap', 'ownerId': 'b1', "session": 'b1', 'cap': 0.25}).json()['cap'] == 0.25
    assert fs._KEPT['g1']['taskCap'] == 0.25   # the new cap is what every later save keeps (owner 2026-10-31: "$0.25 doesn't change")
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
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda *_a: True)
    started = []
    monkeypatch.setattr(fs, '_work_start', lambda cid, cat, text, to=None, files=None: started.append(text))
    c = TestClient(fs.app)
    fs._WORK['g1'] = {'task': ca.new_task('t', 'first', ['m/a'], 0.05), 'done': False, 'at': 1.0}
    assert c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', "session": 'b1', 'text': 'next'}).status_code == 409     # off: busy refuses
    assert c.post('/api/cats/g1/work', json={'op': 'go', 'ownerId': 'b1', "session": 'b1', 'on': True}).json()['go'] is True
    r = c.post('/api/cats/g1/work', json={'op': 'ask', 'ownerId': 'b1', "session": 'b1', 'text': 'next'}).json()
    assert [q['text'] for q in r['queue']] == ['next'] and started == []
    fs._WORK['g1']['task'].update(status='done', answer='A', cost=0.01); fs._WORK['g1']['done'] = True
    fs._work_settle(store)
    assert started == ['next'] and store['cats']['g1']['workQueue'] == []
    c.post('/api/cats/g1/work', json={'op': 'go', 'ownerId': 'b1', "session": 'b1', 'on': False}); assert store['cats']['g1']['workQueue'] == []
    fs._WORK.pop('g1', None)


def test_a_creator_or_admin_wallet_pays_no_feeless_fee_on_any_trade(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {**rs.FEE_DEFAULTS, 'platformFeeBps': 150})
    monkeypatch.setattr(rs, '_is_staff', lambda w: w == 'STAFF')
    f = asyncio.run(rs.effective_fee('STAFF', 'So11111111111111111111111111111111111111112', 'MINTX', amount=1))
    assert f['bps'] == 0 and 'site-wide' in ' '.join(f['notes'])


def test_an_agent_wallet_owned_by_staff_pays_no_fee_but_a_users_agent_still_does(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {**rs.FEE_DEFAULTS, 'platformFeeBps': 1500})
    monkeypatch.setattr(rs, '_is_staff', lambda w: w == 'STAFF')
    async def mints():
        return {}
    monkeypatch.setattr(rs, '_ecosystem_mints', mints)
    cats = {'cats': {'a': {'agentWallet': {'address': 'AGENT1', 'owner': 'STAFF'}}, 'b': {'agentWallet': {'address': 'AGENT2', 'owner': 'USER'}},
                     'c': {'revoked': True, 'agentWallet': {'address': 'AGENT3', 'owner': 'STAFF'}}}}
    (rs.DATA_DIR / 'feecats.json').write_text(json.dumps(cats))
    sol = 'So11111111111111111111111111111111111111112'
    assert asyncio.run(rs.effective_fee('AGENT1', sol, 'MINTX', amount=1))['bps'] == 0
    assert asyncio.run(rs.effective_fee('AGENT2', sol, 'MINTX', amount=1))['bps'] > 0      # a user's agent pays like its owner would
    assert asyncio.run(rs.effective_fee('AGENT3', sol, 'MINTX', amount=1))['bps'] > 0      # a retired agent is no longer exempt


def test_a_traders_browser_reads_coins_and_narrative_only_never_types_or_leaves_the_research_list():
    from cat_policy import research_ok
    assert research_ok('https://x.com/search?q=btc') and research_ok('https://www.coindesk.com/policy') and research_ok('https://dexscreener.com/solana')
    assert not research_ok('https://mail.proton.me') and not research_ok('https://evil.example') and not research_ok('http://localhost:5001')
    assert research_ok('https://x.com/login', login=True) and not research_ok('https://coindesk.com/login', login=True)   # its only sign-in is the user's own X
    ask = scripted({'m/a': [{'fast': '', 'a': 'BTC narrative', 'b': ''},
                            {'thought': 'sign up', 'action': 'new_login', 'url': 'https://mail.proton.me'},
                            {'thought': 'off list', 'action': 'open', 'url': 'https://evil.example'},
                            {'thought': 'type', 'action': 'type', 'label': 'q', 'value': 'x'},
                            {'thought': 'policy news', 'action': 'open', 'url': 'https://www.coindesk.com/policy'},
                            {'thought': 'done', 'action': 'answer', 'say': 'policy tailwind'}, {'merged': 1}]})
    pa = Page()
    t = ca.new_task('t9', 'what moves BTC today', ['m/a'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, ask, [pa], None))
    assert pa.done == [('goto', 'https://html.duckduckgo.com/html/?q=BTC+narrative'), ('goto', 'https://www.coindesk.com/policy')]   # the sign-up, the off-list site and the typing never reached the page
    acts = [s['action'] for s in t['windows'][0]['steps']]
    assert acts[:5] == ['open', 'plan', 'refused', 'blocked', 'refused'] and 'new_login' not in acts and t['windows'][0]['answer'] == 'policy tailwind'


def test_a_named_site_opens_first_and_a_bare_address_is_never_refused():
    """Owner 2026-10-31: "Browse pump.fun …" left both windows on about:blank — one mind answered unvisited, the other's "pump.fun" (no https) was refused 8×."""
    assert ca.full_url('pump.fun') == 'https://pump.fun' and ca.named_site('Browse pump.fun and find the best coin') == 'https://pump.fun'
    assert ca.named_site('write 5 posts e.g. a thread') is None and ca.named_site('mail a@b.com') is None
    pa = Page()
    t = ca.new_task('t10', 'A: Browse pump.fun and find your best coin on trending list', ['m/a', 'm/b'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    ask = scripted({'m/a': [{'thought': 'board', 'action': 'open', 'url': 'pump.fun/board'}, {'thought': 'done', 'action': 'answer', 'say': '$CAT leads'}]})
    asyncio.run(ca.run(t, ask, [pa, Page()], None))
    assert pa.done == [('goto', 'https://pump.fun'), ('goto', 'https://pump.fun/board')]   # opened before its first thought, then its bare address went through
    assert [s['action'] for s in t['windows'][0]['steps']] == ['open', 'plan', 'open', 'answer'] and t['windows'][0]['answer'] == '$CAT leads'
    pb = Page(); pb.url = 'https://pump.fun/?__cf_chl_rt_tk=x'
    t = ca.new_task('t11', 'A: pick the best coin', ['m/a', 'm/b'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    ask = scripted({'m/a': [{'thought': 'again', 'action': 'open', 'url': 'pump.fun/'}, {'thought': 'got it', 'action': 'report', 'best_coin': 'HUSS', 'reason': '+3947% 1h'}]})
    asyncio.run(ca.run(t, ask, [pb, Page()], None))
    assert pb.done == [] and t['windows'][0]['answer'] == 'best_coin: HUSS; reason: +3947% 1h'   # the page it was on is re-read, never reloaded · "report" is its answer


def test_the_ai_cursor_follows_its_click_into_the_window_view():
    """🖱 owner 2026-10-31: "the cursor actually shows and is controlled by the AI" — where the page says it acted rides to the window."""
    class Pointed(Page):
        async def click(self, t):
            self.cursor = {'x': 0.2, 'y': 0.4, 'act': 'click', 'at': 1}; return await super().click(t)
    pa = Pointed()
    t = ca.new_task('t12', 'A: open the first result', ['m/a', 'm/b'], 1.0)
    asyncio.run(ca.run(t, scripted({'m/a': [{'thought': 'first', 'action': 'click', 'text': 'Result'}, {'thought': 'done', 'action': 'answer', 'say': 'ok'}]}), [pa, Page()], None))
    assert t['windows'][0]['cursor'] == {'x': 0.2, 'y': 0.4, 'act': 'click', 'at': 1} and t['windows'][1].get('cursor') is None


def test_browse_for_n_minutes_keeps_it_browsing_and_a_failed_click_on_a_bot_check_goes_to_the_person(monkeypatch):
    """⏱ owner 2026-10-31: "browse pump.fun for 1-2 minutes" was answered from the first page in 27 s; then its clicks timed out on Cloudflare, retried blind."""
    assert ca.browse_secs('browse pump.fun for 1-2 minutes until a coin stands out') == 60 and ca.browse_secs('look for 30 seconds') == 30 and ca.browse_secs('find the best coin') == 0
    monkeypatch.setattr(ca.time, 'time', lambda: 1000.0)   # the clock stands still: the minute never passes
    class Walled(Page):
        async def click(self, t): raise TimeoutError('Timeout 8000ms exceeded')
        async def read(self): return 'pump.fun Performing security verification'
    pa = Walled(); asked = []
    async def human(i): asked.append(t['windows'][i]['human']['why']); return False
    t = ca.new_task('t13', 'A: browse pump.fun for 1 minute and report the coin that stands out', ['m/a', 'm/b'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    ask = scripted({'m/a': [{'thought': 'easy', 'action': 'answer', 'say': 'HUSS'}, {'thought': 'into it', 'action': 'click', 'text': 'ANSEM $0.05 $52.9M'}]})
    asyncio.run(ca.run(t, ask, [pa, Page()], human))
    assert t['status'] == 'stopped'   # you did not pass it (the stub says no) → it stops there, never retries blind
    acts = [s_['action'] for s_ in t['windows'][0]['steps']]
    assert acts[:4] == ['open', 'plan', 'browse', 'click'] and 'bot check' in asked[0]   # too early to answer → it browsed on; the walled click went to the person


def test_scroll_is_a_research_move_and_a_checkpoint_on_the_first_page_goes_straight_to_the_person():
    """👀 owner 2026-10-31: "it's not visually browsing" — it reads what is on screen and scrolls; a first-page checkpoint burns no steps."""
    class Scrolly(Page):
        async def scroll(self, way): self.done.append(('scroll', way)); return 'ON SCREEN (view 40% down the page): [link] HUSS'
    pa = Scrolly(); t = ca.new_task('t14', 'A: look around reddit.com', ['m/a', 'm/b'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, scripted({'m/a': [{'thought': 'more', 'action': 'scroll', 'q': 'down'}, {'thought': 'done', 'action': 'answer', 'say': 'HUSS'}]}), [pa, Page()], None))
    assert ('scroll', 'down') in pa.done and t['windows'][0]['answer'] == 'HUSS'
    class Walled(Page):
        async def goto(self, u): self.url = u; return 'Vercel Security Checkpoint — security checkpoint'
    asked = []
    async def human(i): asked.append(i); return False
    t = ca.new_task('t15', 'A: browse coindesk.com', ['m/a', 'm/b'], 1.0); t.update(research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, scripted({'m/a': []}), [Walled(), Page()], human))
    assert asked == [0] and [s_['action'] for s_ in t['windows'][0]['steps']] == ['open'] and t['cost'] == 0   # no model call spent on a wall


def test_kernel_leads_the_chain_then_steel_then_anchor_each_a_real_browser_with_a_read_only_view_for_watchers():
    """🌐 owner 2026-10-31: "a true browser — Steel, Kernel and another"; stealth / CAPTCHA solving stays off (a check goes to a person)."""
    env = {'KERNEL_API_KEY': 'kk', 'STEEL_API_KEY': 'ss', 'ANCHOR_API_KEY': 'aa'}
    assert cb.chain(env) == ['kernel', 'steel', 'anchor', 'reader']
    sent = []
    class R:
        def __init__(self, code, j): self.status_code, self._j = code, j
        def json(self): return self._j
    class H:
        async def post(self, u, headers=None, json=None, timeout=None):
            sent.append((u, json))
            if 'onkernel' in u: return R(500, {})   # Kernel down → the next real browser
            if 'steel' in u: return R(500, {})
            return R(200, {'data': {'id': 'an1', 'cdp_url': 'wss://anchor/x', 'live_view_url': 'https://live.anchor/v/1'}})
    s, tried = asyncio.run(cb.open_session(H(), env, {'cookies': [{'name': 'auth', 'value': 'v', 'domain': '.x.com'}]}))
    assert [t[0] for t in tried] == ['kernel', 'steel'] and s['provider'] == 'anchor'
    assert s['live'] == 'https://live.anchor/v/1?readOnly=true' and s['hand'] == 'https://live.anchor/v/1' and s['cookies'][0]['name'] == 'auth'
    assert sent[0][1]['stealth'] is False and sent[0][1]['headless'] is False   # Kernel: headful, never stealth
    class K(H):
        async def post(self, u, headers=None, json=None, timeout=None):
            return R(200, {'session_id': 'k1', 'cdp_ws_url': 'wss://k/1', 'browser_live_view_url': 'https://api.onkernel.com/browser/live/T'})
    s, _ = asyncio.run(cb.open_session(K(), env))
    assert s['provider'] == 'kernel' and s['live'].endswith('?readOnly=true') and s['hand'] == 'https://api.onkernel.com/browser/live/T'


def test_a_spam_ticker_never_becomes_the_coin_and_the_mouse_reports_its_target_before_it_glides():
    """Owner 2026-10-31: after a bot check a mind's FEELESS search picked a token named 'PUMPBDXJUP…NVOONOBS' — its tab label blew the desk apart;
    and the cursor only moved after the click had happened."""
    import asyncio
    import cat_tools as ct, cat_browser as cb
    junk = {'pairAddress': 'J', 'baseToken': {'symbol': 'PUMPBDXJUPGHOFILXDCTBLLXFLRVVV', 'address': 'm1'}, 'liquidity': {'usd': 900}}
    zero = {'pairAddress': 'Z', 'baseToken': {'symbol': 'edith.fun', 'address': 'm2'}, 'liquidity': {'usd': 0}}
    real = {'pairAddress': 'R', 'baseToken': {'symbol': 'PUMP', 'address': 'm3'}, 'liquidity': {'usd': 2e6}}
    assert ct.coin_text([junk, zero, real], 'pump')[1]['symbol'] == 'PUMP' and ct.coin_text([junk], 'x')[1] is None
    seen, moves = [], []
    class M:
        async def move(self, x, y): moves.append((x, y, len(seen)))
    class P:
        mouse = M()
        async def evaluate(self, js): return [1000, 800, 1000, 900]
        async def wait_for_timeout(self, ms): return None
    pg = cb.LivePage.__new__(cb.LivePage); pg._p = P(); pg.on_cursor = seen.append
    asyncio.run(pg.glide(500, 400, 'click'))
    assert seen and seen[0]['x'] == 0.5 and moves[0][2] == 1 and len(moves) == cb.GLIDE_STEPS and moves[-1][:2] == (500, 400)   # target out first, then an eased glide


def test_no_step_is_ever_repeated_and_scrolling_a_page_is_capped():
    """Owner 2026-10-31: 'it scrolled up and down 20 times — agents can't repeat the same steps EVER' (same site, different info, is fine)."""
    import cat_agent as ca
    w = {'sigs': []}
    s1 = ca.step_sig('scroll', {'q': 'down'}, 'https://x.io/pools', 'ON SCREEN (view 0% down the page')
    assert ca.repeat_why(w, 'scroll', s1, 'https://x.io/pools') is None; w['sigs'].append(s1)
    assert ca.repeat_why(w, 'scroll', s1, 'https://x.io/pools') == 'you already did exactly this step'
    s2 = ca.step_sig('scroll', {'q': 'up'}, 'https://x.io/pools', 'view 40% down')
    assert ca.repeat_why(w, 'scroll', s2, 'https://x.io/pools') is None   # a new spot is new
    w['sigs'] += [ca.step_sig('scroll', {'q': 'down'}, 'https://x.io/pools', f'view {p}% down') for p in (10, 20, 30)]
    assert 'scrolls on this page already' in ca.repeat_why(w, 'scroll', ca.step_sig('scroll', {'q': 'down'}, 'https://x.io/pools', 'view 90% down'), 'https://x.io/pools')
    w['sigs'].append(ca.step_sig('click', {'text': 'Pools'}, 'https://x.io', ''))
    assert ca.repeat_why(w, 'click', ca.step_sig('click', {'text': 'pools'}, 'https://x.io/', ''), 'https://x.io/') == 'you already did exactly this step'
    assert ca.repeat_why(w, 'click', ca.step_sig('click', {'text': 'Volume'}, 'https://x.io', ''), 'https://x.io') is None   # same site, different info
    assert ca.repeat_why(w, 'answer', 'a', '') is None


def test_a_mind_that_keeps_repeating_is_never_stopped_the_engine_moves_it_to_a_new_page_and_what_it_notes_is_filed():
    """Owner 2026-11-01: "it should never be stopped unless the user requests — if it keeps doing the same thing, stop it from doing that thing"."""
    same = {'thought': 'again', 'action': 'feeless', 'tool': 'coin', 'q': 'BONK'}
    ask = scripted({'m/a': [same, same, same, same, {'thought': 'note', 'action': 'note', 'say': 'BONK pool $2M'}, {'thought': 'done', 'action': 'answer', 'say': 'BONK holds'}]})

    async def feeless(tool, q=''):
        return 'BONK · pool $2M', None
    pa = Page()
    t = ca.new_task('tr', 'check BONK', ['m/a'], 1.0, 8, 'jobs'); t.update(alts=['https://rugcheck.xyz'])
    asyncio.run(ca.run(t, ask, [pa], None, ('A',), feeless))
    w = t['windows'][0]
    assert ('goto', 'https://rugcheck.xyz') in pa.done and any('diverted to rugcheck.xyz' in s['thought'] for s in w['steps'])   # moved, not stopped
    assert w['answer'] == 'BONK holds' and t['filed'][-1]['text'] == 'BONK pool $2M'                                             # it finished + its note is filed


def test_each_mind_plans_3_steps_on_its_first_reply_and_the_plan_rides_every_step():
    """Owner 2026-11-01: "they must plan in 3 steps, then execute in their browser window" — no extra call: the plan comes with its first move."""
    ask = scripted({'m/a': [{'thought': 'go', 'action': 'search', 'q': 'BONK', 'plan': ['search BONK', 'open dexscreener', 'answer']}, {'thought': 'done', 'action': 'answer', 'say': 'ok'}]})
    t = ca.new_task('tp3', 'check BONK', ['m/a'], 1.0, 8, 'jobs')
    asyncio.run(ca.run(t, ask, [Page()], None, ('A',)))
    w = t['windows'][0]
    assert w['plan'] == ['search BONK', 'open dexscreener', 'answer'] and w['steps'][1]['thought'].startswith('plan: search BONK')
    t2 = ca.new_task('tp4', 'check BONK', ['m/a'], 1.0, 8, 'jobs')
    asyncio.run(ca.run(t2, scripted({'m/a': [{'thought': 'done', 'action': 'answer', 'say': 'ok'}]}), [Page()], None, ('A',)))
    assert len(t2['windows'][0]['plan']) == 3                                                # no plan given → the engine's default 3 steps
