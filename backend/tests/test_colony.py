"""🐝 The Colony (owner 2026-10-31): graded trades, the FEECAT stake gate, and the pot's guards — growth only, honey split, never a send."""
import asyncio

import colony as col
import hive as hv


def test_the_pot_only_pays_growth_under_the_epoch_cap_and_the_floor_only_rises():
    assert col.growth(1200, 1000) == 200 and col.growth(900, 1000) == 0          # a dip pays nothing, never principal
    assert col.payable(1200, 1000, {'epochCapPct': 20}) == 40                     # 20 % of the growth leaves this epoch
    assert col.payable(1200, 1000, {'epochCapPct': 99}) == 100                     # the cap is clamped to 50 %
    assert col.raise_floor(1000, 1200) == 1200 and col.raise_floor(1200, 900) == 1200   # lock gains in; it never goes down
    assert col.clean_policy({'timelockH': 1}) == {'epochCapPct': 20, 'timelockH': 6, 'cadence': 'daily'}
    assert set(col.FIXED_GUARDS) == {'principalLock', 'allowlist', 'ownerSigns'}


def test_airdrops_follow_what_each_owner_shared_never_who_was_right():
    sh = [{'owner': 'A', 'sol': 0.1, 'at': 100}, {'owner': 'B', 'sol': 0.3, 'at': 150}, {'owner': 'C', 'sol': 1.0, 'at': 150}, {'owner': 'A', 'sol': 9, 'at': 10}]
    out = col.airdrop(sh, {'A', 'B'}, 40, since=50)   # C never signed; A's old share is from the last period
    assert [(r['owner'], r['usd'], r['pct']) for r in out] == [('B', 30.0, 75.0), ('A', 10.0, 25.0)]
    assert col.share_cut(0.5, 10) == 0.05 and col.share_cut(-2, 10) == 0 and col.share_cut(1, 7) == 0   # only the offered %s, nothing on a loss
    assert col.period_of(86400 * 3 + 5, 'daily') == (3, 86400 * 4) and col.clean_policy({'cadence': 'weekly'})['cadence'] == 'weekly'


def test_a_signed_sharing_agent_owes_the_colony_on_wins_only_from_its_own_wallet(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 's.json')
    cat = {'id': 'k1', 'ownerWallet': 'W1', 'colonyShare': {'on': True, 'pct': 20}, 'agentWallet': {'address': 'AW'}}
    fs._colony_share(cat, {'symbol': 'HUSS'}, 0.5); fs._colony_share(cat, {'symbol': 'RUG'}, -0.2)
    fs._colony_share({**cat, 'agentWallet': None}, {'symbol': 'X'}, 1.0)   # paper winnings are not money
    assert [(x['owner'], x['sol'], x['sent']) for x in fs._shares()] == [('W1', 0.1, False)]
    assert fs.share_ok('k1', 20, 1, 'sig', 'W1', now=500) is False   # a stale signature never counts
    src = open(fs.__file__).read(); i = src.index("if p.op == 'share':"); assert 'share_ok(cat_id, pct_, p.ts, p.sig' in src[i:i + 900]


def test_an_entry_is_a_buy_cell_and_an_exit_an_avoid_cell_graded_like_any_other():
    cat = {'id': 'k1', 'name': 'Kit'}; pos = {'pairAddress': 'PAIR123456789', 'symbol': 'HUSS', 'mint': 'M'}
    e = col.trade_cell(cat, 'buy', pos, 0.01, 1_800_000_000); x = col.trade_cell(cat, 'sell', pos, 0.02, 1_800_000_100)
    assert (e['call'], e['kind'], x['call'], x['kind']) == ('BUY', 'entry', 'AVOID', 'exit')
    assert hv.grade(x, 0.014, 1_800_003_800) == 2 and x['move'] == -30.0   # it fell 30 % after the exit: a great exit
    assert col.trade_cell(cat, 'buy', pos, 0, 1) is None and col.trade_cell(cat, 'buy', {}, 1, 1) is None


def test_a_colonized_agents_buy_files_a_cell(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'k1', 'name': 'Kit', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m/a']}}
    fs._colony_trade(cat, 'buy', {'pairAddress': 'P1', 'symbol': 'HUSS'}, 0.01)
    fs._colony_trade({**cat, 'hive': {'on': False}}, 'buy', {'pairAddress': 'P2', 'symbol': 'X'}, 0.01)   # not colonized: nothing filed
    cells = fs._hive_cells(); assert len(cells) == 1 and cells[0]['kind'] == 'entry' and cells[0]['epoch'] == hv.epoch_of(cells[0]['at'])


def test_the_colony_feed_for_the_pot_is_internal_and_names_browsers_never_keys(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    store = {'cats': {'k1': {'id': 'k1', 'name': 'Kit', 'ownerWallet': 'W1', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setenv('KERNEL_API_KEY', 'sk_secret_value'); (fs.DATA_DIR / 'internal.key').write_text('test-internal')
    c = TestClient(fs.app)
    assert c.get('/api/cats/internal/colony').status_code == 403
    r = c.get('/api/cats/internal/colony', headers=fs._internal_headers()).json()
    assert r['owners'] == {'k1': 'W1'} and r['colonized'] == 1 and r['browsers'][0] == 'kernel' and 'sk_secret' not in str(r)


def test_the_colony_page_lists_agents_colonized_first_ten_a_page_never_a_secret(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cats = {f'c{i}': {'id': f'c{i}', 'name': f'Cat {i}', 'ownerWallet': 'OWNER_W', 'brainsCfg': {'kind': 'general', 'brains': ['openai/gpt-x:free', 'm/b']}, 'secrets': {'k': 'hunter2'}} for i in range(12)}
    cats['c7']['hive'] = {'on': True}
    store = {'cats': cats, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    c = TestClient(fs.app)
    j = c.get('/api/cats/colony').json()
    assert len(j['agents']) == 10 and j['more'] is True and j['agents'][0]['id'] == 'c7' and j['agents'][0]['colonized'] and j['agents'][0]['brains'][0] == 'gpt-x'
    assert len(c.get('/api/cats/colony?page=1').json()['agents']) == 2
    assert [a['id'] for a in c.get('/api/cats/colony?ids=c3,c9').json()['agents']] == ['c3', 'c9']   # My agents: only those
    t = c.get('/api/cats/colony').text; assert 'hunter2' not in t and 'OWNER_W' not in t


def test_a_visitor_sees_its_colony_vitals_beside_the_windows(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import time as _t
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    now = _t.time(); fs._hive_save([{'id': 'x1', 'cat': 'k1', 'call': 'BUY', 'sym': 'HUSS', 'at': now - 10, 'honey': 2, 'why': 'secret-ish reasoning'},
                                    {'id': 'x2', 'cat': 'k1', 'call': 'AVOID', 'sym': 'RUG', 'at': now - 5, 'honey': None, 'kind': 'exit'}])
    store = {'cats': {'k1': {'id': 'k1', 'name': 'Kit', 'hive': {'on': True}, 'brainsCfg': {'brains': ['m']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store)
    j = TestClient(fs.app).get('/api/cats/k1/live').json()
    assert j['colonized'] is True and j['honey'] == 2 and (j['right'], j['graded']) == (1, 1) and j['lastCall'] == {'call': 'AVOID', 'sym': 'RUG', 'honey': None, 'kind': 'exit'}


def test_agents_can_read_the_colony_as_a_feeless_tool():
    import asyncio
    import cat_tools as ct
    assert 'colony' in ct.TOOLS
    assert ct.colony_text([{'call': 'BUY', 'sym': 'HUSS', 'name': 'Happy', 'honey': 2, 'move': 25.0}, {'call': 'AVOID', 'sym': 'X'}], '$huss') == \
        "FEELESS Colony (other agents' calls, graded an hour on):\n- BUY $HUSS by Happy: +2 honey (+25.0%)"
    class R:
        def json(self): return {'cells': [{'call': 'WATCH', 'sym': 'KIM', 'name': 'Happy', 'honey': None}]}
    class H:
        async def get(self, u, **k): assert u.endswith('/api/cats/hive'); return R()
    text, coin = asyncio.run(ct.run_tool(H(), 'colony', 'KIM')); assert 'WATCH $KIM by Happy: grading' in text and coin is None


def test_the_sources_book_learns_blocks_and_offers_the_best_other_sites():
    import agent_sources as src
    b = {}
    for _ in range(2):
        src.record(b, 'https://pump.fun/board', False)
    src.record(b, 'https://www.dexscreener.com/solana', True); src.record(b, 'gecko' + 'terminal.com', True)
    assert ('gecko' + 'terminal.com') not in b and b['dexscreener.com']['ok'] == 1   # never the banned site
    alts = src.best(b, exclude=['pump.fun']); assert alts[0] == 'dexscreener.com' and 'pump.fun' not in alts and len(alts) == 3
    assert 'pump.fun' not in src.best(b, n=8)[:5] and 'Recently BLOCKED (bot checks): pump.fun' in src.brief(b)


def test_a_popup_is_closed_with_the_careful_button_first():
    import cat_browser as cb
    btns = [{'t': 'Accept all'}, {'t': 'Reject non-essential'}, {'t': 'Settings'}]
    assert cb.pick_close(btns)['t'] == 'Reject non-essential'
    assert cb.pick_close([{'t': "I'm ready to pump"}, {'t': 'Learn more'}])['t'] == "I'm ready to pump" and cb.pick_close([{'t': 'Buy now'}]) is None


def test_a_blocked_window_can_be_sent_elsewhere_and_every_mind_knows_the_colony(monkeypatch):
    import asyncio
    import cat_agent as ca, colony as col
    class Pg:
        url, title = 'https://pump.fun', 't'
        async def goto(self, u): self.url = u; return 'ON SCREEN: pairs'
        async def read(self): return 'same page'
    w = {'i': 0, 'steps': [], 'redirect': 'https://dexscreener.com'}
    out = asyncio.run(ca._after_human(w, Pg()))
    assert 'now on dexscreener.com' in out and w['url'] == 'https://dexscreener.com' and 'redirect' not in w
    assert asyncio.run(ca._after_human({'i': 0, 'steps': []}, Pg())) == 'same page'
    assert 'HONEY' in col.KNOWHOW and 'nobody is paid for being right' in col.KNOWHOW
    src = open(ca.__file__).read(); assert "extra += '\\n' + str(task['knowhow'])" in src and 'you just scrolled the other way' in src


def test_the_desks_big_stop_also_stops_running_minds_and_a_third_repeat_read_ends_the_turn():
    """Owner 2026-10-31: 'stop btn not working' (it only stopped trades) · 'it said already read this like 15 times' (each one paid)."""
    import feecat_service as fs, cat_agent as ca
    src = open(fs.__file__).read(); i = src.index("elif payload.action == 'stop':")
    assert "w_['task']['stop'] = True" in src[i:i + 900] and '_hard_stop(w_)' in src[i:i + 900]
    assert ca.REPEAT_MAX == 3 and "if w['repeats'] >= REPEAT_MAX" in open(ca.__file__).read()
    assert fs.BLOCK_PIVOT_S == 30


def test_a_bot_check_you_pass_is_kept_sealed_so_its_next_windows_skip_it(monkeypatch, tmp_path):
    import asyncio, json, time as _t
    import feecat_service as fs
    store = {'cats': {'k1': {'id': 'k1', 'name': 'Kit'}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s_: None)
    monkeypatch.setattr(fs, 'SOURCES_PATH', tmp_path / 'src.json')
    class Pg:
        url = 'https://pump.fun/board'
        async def site_context(self, url=None):
            return {'cookies': [{'name': 'cf_clearance', 'value': 'abc', 'domain': '.pump.fun', 'path': '/', 'expires': _t.time() + 3600},
                                {'name': '_ga', 'value': 'track', 'domain': '.pump.fun', 'path': '/'},
                                {'name': 'other', 'value': 'x', 'domain': '.evil.com', 'path': '/'}], 'localStorage': {}}
    assert asyncio.run(fs._keep_pass('k1', Pg(), 'https://pump.fun/board')) is True
    sess = store['cats']['k1']['siteSessions']['pump.fun']; assert sess['kind'] == 'pass' and sess['n'] == 1   # the tracker + the other site's cookie dropped
    ctx = json.loads(fs._ck.unseal(sess['ctx'], 'k1', data_dir=fs.DATA_DIR)); assert [c['name'] for c in ctx['cookies']] == ['cf_clearance']
    assert fs._site_ctx(store['cats']['k1'])['cookies'][0]['name'] == 'cf_clearance'   # its next windows start with it
    assert 'cf_clearance' not in json.dumps(fs._no_keys(store['cats']['k1']))   # never leaves the server


def test_the_colony_pool_needs_a_clean_preview_of_the_same_amounts_before_circle_signs(monkeypatch, tmp_path):
    """🌊 Meteora pool from the colony wallet: preview (free simulation) → create only with the same amounts within 10 min → Circle signs → broadcast."""
    from fastapi.testclient import TestClient
    import reputation_service as rs
    monkeypatch.setattr(rs, 'COLONY_PATH', tmp_path / 'colony.json')
    rs._json_save(rs.COLONY_PATH, {'wallet': {'address': 'PotWa11et1111111111111111111111111111111111', 'id': 'cw1'}})
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    async def view(): return {'ok': True}
    monkeypatch.setattr(rs, '_colony_view', view)
    sims = iter([{'ok': True, 'pool': 'POOL1', 'price': 5e-7, 'tx': 'TX', 'sim': {'err': None}}] * 3)
    async def build(d, body): return ({'amountA': float(body['feecat']), 'amountB': float(body['sol']), 'feeBps': 100, 'compoundingBps': 5000, 'lock': True}, next(sims))
    monkeypatch.setattr(rs, '_colony_pool_build', build)
    signed = []
    async def circle(m, path, body=None, agent=False): signed.append((path, body['walletId'], agent)); return {'signedTransaction': 'SIGNED', 'signature': 'SIG'}
    monkeypatch.setattr(rs, '_circle', circle)
    async def bcast(http, tx): return 3
    monkeypatch.setattr(rs, '_rpc_broadcast', bcast)
    c = TestClient(rs.app)
    assert c.post('/api/reputation/admin/colony', json={'action': 'pool_create', 'feecat': 1e6, 'sol': 0.5}).status_code == 400 and not signed   # no preview yet
    assert c.post('/api/reputation/admin/colony', json={'action': 'pool_preview', 'feecat': 1e6, 'sol': 0.5}).status_code == 200
    assert c.post('/api/reputation/admin/colony', json={'action': 'pool_create', 'feecat': 2e6, 'sol': 0.5}).status_code == 400 and not signed   # different amounts
    assert c.post('/api/reputation/admin/colony', json={'action': 'pool_create', 'feecat': 1e6, 'sol': 0.5}).status_code == 200
    d = rs._json_load(rs.COLONY_PATH, {}); assert signed == [('/sign', 'cw1', True)] and d['pool']['address'] == 'POOL1' and d['pool']['platform'] == 'Meteora DAMM v2'
    assert c.post('/api/reputation/admin/colony', json={'action': 'pool_create', 'feecat': 1e6, 'sol': 0.5}).status_code == 400   # once, ever


def test_every_monitor_idles_on_its_own_models_last_page_kept_on_disk(monkeypatch, tmp_path):
    """Owner 2026-11-01: "all monitors idle on the last thing they were on as a snapshot" — per model, so B alone never paints over A, and a restart keeps it."""
    import asyncio
    import feecat_service as fs
    monkeypatch.setattr(fs, 'SHOTS_DIR', tmp_path / 'shots'); fs._LAST.clear()
    cat = {'id': 'c1', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {'c1': cat}})
    assert fs._slot_of(cat, 'x/b') == 1 and fs._slot_of(cat, 'x/zz') == 0
    fs._last_put('c1', 1, b'JPG-B'); fs._LAST.clear()                                      # a restart: memory gone, the file stays
    assert fs._last_get('c1', 1) == b'JPG-B' and fs._last_get('c1', 0) is None
    r = asyncio.run(fs.cat_last_page('c1', 1)); assert r.body == b'JPG-B' and r.headers['X-Last-Page'] == '1'
    live = fs.public_live({'task': {'status': 'done', 'windows': [{'i': 0, 'model': 'x/b', 'status': 'done', 'url': 'https://a.com'}]}}, cat)
    assert live['windows'][0]['slot'] == 1 and live['windows'][0]['last']                    # mind B worked alone: its own monitor, its own page
    cat['incognito'] = True
    try:
        asyncio.run(fs.cat_last_page('c1', 1)); assert False
    except fs.HTTPException as e:
        assert e.status_code == 404                                                            # private agents show nothing
