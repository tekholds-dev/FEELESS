"""⛏ Proof of Work: one intake coin, ≤4 sites × ≤5 moves × ≤3 vitals — the rules hold for every model (they are code, not a prompt)."""
import asyncio
import json

import cat_agent as ca
import pow as pw
from test_cat_agent import Page, scripted


def test_only_vitals_with_a_read_value_are_saved_three_per_site():
    p = pw.new({'mint': 'M', 'pair': 'P', 'sym': 'CAT'}, 1000)
    url = 'https://rugcheck.xyz/tokens/M'
    assert pw.pull(p, url, 'favourite colour', 'blue')[0] is False            # not a vital
    assert pw.pull(p, url, 'liquidity', 'looks fine')[0] is False             # no number / yes-no read
    assert pw.pull(p, 'https://html.duckduckgo.com/html/?q=x', 'mcap', '$1M')[0] is False   # a search page is not a source
    assert pw.pull(p, url, 'Mint Authority', 'revoked')[0] and pw.pull(p, url, 'liq', '$35K')[0]
    assert pw.pull(p, url, 'liquidity', '$36K')[0] is False                   # the same vital twice on one site
    assert pw.pull(p, url, 'top 10', '22%')[0]
    assert pw.pull(p, url, 'holders', '1,204')[0] is False                    # 4th vital on one site
    assert [x['label'] for x in pw.pulls(p)] == ['mint authority', 'liquidity', 'top 10 holders']


def test_five_moves_per_site_and_four_sites_then_refused():
    p = pw.new({'mint': 'M', 'pair': 'P', 'sym': 'CAT'}, 1000)
    assert all(pw.step(p, 'https://dexscreener.com/solana/P') is None for _ in range(5))
    assert '5 moves' in pw.step(p, 'https://dexscreener.com/solana/x')
    assert pw.step(p, 'https://html.duckduckgo.com/html/?q=a') is None        # the search page is free
    for h in ('a.com', 'b.com', 'c.com'):
        assert pw.step(p, f'https://{h}/') is None
    assert '4 sites' in pw.step(p, 'https://e.com/')


def test_pick_skips_thin_pools_and_coins_it_researched():
    coins = [{'mint': 'A', 'pair': 'pa', 'sym': 'A', 'liq': 900, 'rank': 9}, {'mint': 'B', 'pair': 'pb', 'sym': 'B', 'liq': 9000, 'rank': 5},
             {'mint': 'C', 'pair': 'pc', 'sym': 'C', 'liq': 50000, 'rank': 7}]
    assert pw.pick(coins, set())['mint'] == 'C' and pw.pick(coins, {'C'})['mint'] == 'B' and pw.pick(coins, {'B', 'C'}) is None


def test_a_pow_run_starts_on_a_search_obeys_the_rules_and_files_its_call():
    coin = pw.new({'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT'}, 1000)
    moves = [{'thought': 'rugcheck', 'action': 'open', 'url': 'https://rugcheck.xyz/tokens/Mint1'},
             {'thought': 'save', 'action': 'pull', 'label': 'mint authority', 'value': 'revoked'},
             {'thought': 'junk', 'action': 'pull', 'label': 'mood', 'value': 'bullish'},
             {'thought': 'save', 'action': 'pull', 'label': 'top holders', 'value': '18%'}]
    moves += [{'thought': f'tab {i}', 'action': 'click', 'text': f'tab {i}'} for i in range(5)]
    moves += [{'thought': 'early', 'action': 'answer', 'say': 'BUY'}, {'thought': 'save', 'action': 'pull', 'label': 'liquidity', 'value': '$90K'},
              {'thought': 'done', 'action': 'answer', 'say': 'BUY — mint revoked, top 10 hold 18%'}]
    pg = Page()
    t = ca.new_task('tp', pw.goal(coin), ['m/a'], 1.0, pw.STEPS_MAX, 'jobs'); t.update(pow=coin, research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, scripted({'m/a': moves}), [pg], None))
    assert pg.done[0][1].startswith('https://html.duckduckgo.com/html/?q=%24CAT+Mint1')   # 🔎 starts on a search of the coin
    assert [x['label'] for x in pw.pulls(coin)] == ['mint authority', 'top 10 holders', 'liquidity']   # the junk pull was refused
    assert any(s_['thought'] == 'not yet — pull the vitals first' for s_ in t['windows'][0]['steps'])   # no answer before 3 vitals
    i_ = pg.done.index(('goto', 'https://dexscreener.com/solana/Pair1'))               # open + 4 clicks = 5 moves on rugcheck → the ENGINE opens the next page
    assert [d[0] for d in pg.done[1:i_]] == ['goto', 'click', 'click', 'click', 'click'] and pg.done[i_ + 1] == ('click', 'tab 4')
    assert coin['sites']['rugcheck.xyz']['steps'] == 5 and coin['sites']['dexscreener.com']['steps'] == 2
    assert coin['call'] == 'BUY' and 'mint revoked' in coin['why'] and pw.public(coin)['strength'] > 0
    assert t['status'] == 'done' and 'PROOF OF WORK' in json.dumps(t['text'])


def test_the_service_starts_a_pow_on_an_intake_coin_and_files_it_graded_and_in_the_cabinet(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'h1', 'name': 'Happy', 'hive': {'on': True}, 'brainsCfg': {'kind': 'general', 'brains': ['x/m-a', 'x/m-b'], 'credit': 1.0}}
    store = {'cats': {'h1': cat}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s_: None)

    class R:
        def json(self):
            return {'coins': [{'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT', 'liq': 40000, 'rank': 3}]}

    class H:
        async def get(self, url, **k):
            assert 'familia/intake' in url
            return R()
    started = []
    monkeypatch.setattr(fs, '_work_start', lambda cid, c, text, to=None, files=None, pow_=None: started.append((to, pow_)))
    fs._WORK.pop('h1', None)
    assert asyncio.run(fs._pow_start(H(), cat, [], 10_000)) is True
    to, p = started[0]
    assert to == '0' and p['mint'] == 'Mint1' and p['by'] == 'm-a'                   # mind A first, the intake coin
    cat['hiveRun']['pow'] = 10_000
    assert asyncio.run(fs._pow_start(H(), cat, [], 10_100)) is False                  # ≥ 30 min between PoW runs
    assert asyncio.run(fs._pow_start(H(), cat, [{'cat': 'h1', 'mint': 'Mint1', 'at': 10_000}], 20_000)) is False   # researched it lately

    pw.pull(p, 'https://rugcheck.xyz/tokens/Mint1', 'mint authority', 'revoked'); pw.finish(p, 'AVOID — top 10 hold 61%')

    async def prices(http, pairs):
        return {'Pair1': {'priceUsd': '0.002'}}
    monkeypatch.setattr(fs, '_pair_prices', prices)
    t = {'pow': p, 'cost': 0.004, 'status': 'done', 'text': pw.goal(p)}
    asyncio.run(fs._pow_price(None, t))
    cell = fs._pow_settle(cat, t, 20_000)
    assert cell['call'] == 'AVOID' and cell['price'] == 0.002 and cell['pow']['pulls'][0]['label'] == 'mint authority'
    assert fs._hive_cells()[-1]['id'] == cell['id']                                   # graded an hour on like every cell
    assert cat['brainsCfg']['powLast']['0']['sym'] == 'CAT' and cat['brainsCfg']['cloud'][-1]['text'].startswith('⛏ PoW AVOID $CAT')
    assert fs._pow_view(cat)['0']['strength'] > 0
    assert fs._pow_settle(cat, {**t, 'status': 'stopped'}, 20_001) is None          # stopped for the owner's ask: nothing filed

    fs._WORK['h1'] = {'done': True, 'task': t, 'at': 1}                               # the settle pass: no flat fee, no chat line you did not type
    cat['chat'] = []; cat.pop('feesDue', None)
    monkeypatch.setattr(fs, '_pow_settle', lambda c, t_, now: None)
    fs._work_settle(store)
    assert cat['chat'] == [] and not cat.get('feesDue')
    fs._WORK.pop('h1', None)


def test_the_engine_drives_the_route_a_stalling_model_still_covers_the_sites_and_walls_are_skipped():
    """A small free model re-read FEELESS until it was stopped (live run 2026-10-31): FEELESS is read up front, a re-read moves it on,
    the coin's pages open in order, a walled one is skipped, and when the sites run out it must answer."""
    coin = pw.new({'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT'}, 1000)
    stall = {'thought': 'feeless again', 'action': 'feeless', 'tool': 'coin', 'q': 'Mint1'}
    moves = [{'thought': 'save', 'action': 'pull', 'label': 'liquidity', 'value': '$40K'}, stall,
             {'thought': 'save', 'action': 'pull', 'label': 'volume', 'value': '$1.2M'}, stall,
             {'thought': 'save', 'action': 'pull', 'label': 'holders', 'value': '2,310'}, stall, stall, stall,
             {'thought': 'done', 'action': 'answer', 'say': 'WATCH — thin pool for its volume'}]
    pg = Page(wall='rugcheck')
    asked = []

    async def feeless(tool, q=''):
        asked.append((tool, q)); return 'CAT · liq $40K · vol $1.2M', None
    t = ca.new_task('tq', pw.goal(coin), ['m/a'], 1.0, pw.STEPS_MAX, 'jobs'); t.update(pow=coin, research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, scripted({'m/a': moves}), [pg], None, ('A',), feeless))
    assert asked == [('coin', 'Mint1')]                                                    # FEELESS read once, by the engine
    opened = [d[1] for d in pg.done if d[0] == 'goto']
    assert opened[1:] == ['https://dexscreener.com/solana/Pair1', 'https://rugcheck.xyz/tokens/Mint1', 'https://solscan.io/token/Mint1', 'https://birdeye.so/token/Mint1?chain=solana']
    assert 'rugcheck.xyz' not in coin['sites'] and coin['walled'] == ['rugcheck.xyz']     # the wall was skipped and never counted
    assert [x['site'] for x in pw.pulls(coin)] == ['feeless.app', 'dexscreener.com', 'solscan.io'] and coin['call'] == 'WATCH'


# ═══ PoW v2: the Colony PoW loop (4-coin folder → agree → buy 1 on FEELESS → watch / research / decide → sell → filed)
def _intake():
    return [{'mint': 'A1', 'pair': 'pa', 'sym': 'AAA', 'liq': 40000, 'rank': 9, 'sources': ['open']},
            {'mint': 'B2', 'pair': 'pb', 'sym': 'BBB', 'liq': 30000, 'rank': 8, 'sources': ['runner']},
            {'mint': 'thin', 'pair': 'px', 'sym': 'THN', 'liq': 900, 'rank': 99, 'sources': ['open']},
            {'mint': 'Cpump', 'pair': 'pc', 'sym': 'CCC', 'liq': 12000, 'rank': 3, 'sources': ['pulse']}]


def test_a_folder_gathers_2_intake_1_pump_1_dex_and_the_hard_stops_hold():
    got = pw.gather(_intake(), [{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}])
    assert [(c['sym'], c['src']) for c in got] == [('AAA', 'intake'), ('BBB', 'intake'), ('CCC', 'pump'), ('DDD', 'dex')]   # the thin pool never makes it
    assert len(pw.gather(_intake(), [], {'A1'})) == 2                                       # a dry source = a short folder (the service waits)
    assert pw.agree({'0': 2, '1': 2}, 2) == 2 and pw.agree({'0': 2, '1': 1}, 2) is None and pw.agree({'0': 1}, 1) == 1
    assert pw.parse_pick('{"pick": 3, "why": "vol 4x"}') == (2, 'vol 4x') and pw.parse_pick('{"pick": 9}')[0] is None
    assert 'stop' in pw.hard_exit(1.0, 0.7, 0, 60, 0) and 'take profit' in pw.hard_exit(1.0, 1.7, 0, 60, 0)
    assert 'min' in pw.hard_exit(1.0, 1.0, 0, pw.HOLD_MAX_S, 0) and 'rounds' in pw.hard_exit(1.0, 1.0, 0, 60, pw.ROUNDS_MAX) and pw.hard_exit(1.0, 1.1, 0, 60, 1) is None
    assert pw.parse_decide('{"action": "SELL", "say": "lower highs"}') == ('SELL', 'lower highs') and pw.parse_decide('{"action":"HOLD"}')[0] == 'HOLD'


def test_the_service_runs_a_whole_folder_two_minds_discuss_buy_watch_research_decide_sell_and_file(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 't1', 'name': 'Trader', 'status': 'running', 'risk': {'maxPositionSol': 0.05}, 'positions': [],
           'brainsCfg': {'kind': 'trading', 'brains': ['x/m-a', 'x/m-b'], 'credit': 1.0}}
    assert fs._pow2_on(cat) and not fs._pow2_on({**cat, 'isLeader': True})              # every trader agent but Fee

    class R:
        def __init__(self, j): self.j = j
        def json(self): return self.j

    class H:
        async def get(self, url, **k):
            return R({'coins': _intake()}) if 'intake' in url else R([])
    monkeypatch.setattr(fs, '_pow2_dex', lambda http: _aw([{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]))
    monkeypatch.setattr(fs._ct, 'run_tool', lambda http, tool, q: _aw((f'read {q}', None)))
    px = {'v': 1.0}
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': str(px['v']), 'priceUsd': str(px['v'] * 200)} for p in pairs}))
    answers = {'0': ['{"pick": 1, "why": "deep pool"}', '{"pick": 2, "why": "ok, vol is better"}'], '1': ['{"pick": 2, "why": "vol 4x"}', '{"pick": 2, "why": "keep: vol"}']}
    decide = ['{"action": "HOLD", "say": "higher lows"}', '{"action": "SELL", "say": "it topped"}']

    async def ask(c, i, sys_, user_, max_tokens=180):
        return decide.pop(0) if 'CHART WATCHER' in sys_ else answers[str(i)].pop(0)
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    orders = []

    async def order(store, c, text, http):
        orders.append(text)
        if text.startswith('buy'):
            c['positions'].append({'pairAddress': 'pb', 'symbol': 'BBB'})
        else:
            c['positions'] = []
        return {'state': 'filled', 'why': 'paper fill'}
    monkeypatch.setattr(fs, '_run_order', order)
    monkeypatch.setattr(fs, '_work_start', lambda *a, **k: (_ for _ in ()).throw(fs.HTTPException(409, 'busy')))   # no window free: the round is skipped
    store = {'cats': {'t1': cat}}; t = 10_000.0

    def tick(dt=20):
        nonlocal t
        t += dt; asyncio.run(fs._pow2_tick(H(), store, cat, t))
    tick(); f = cat['powRun']['folder']
    assert [c['src'] for c in f['coins']] == ['intake', 'intake', 'pump', 'dex'] and f['name'].startswith('PoW #1 · ') and f['coins'][0]['read'] == 'read A1'
    tick(); assert f['disc'] == 1 and f['phase'] == 'choose'                                # A said AAA, B said BBB: one round of discussion
    tick(); assert f['phase'] == 'buy' and f['sym'] == 'BBB'                                # both agree on BBB
    tick(); assert orders == ['buy 0.05 SOL of B2'] and f['phase'] == 'watch' and not f['real']
    px['v'] = 1.1; tick(); assert f['phase'] == 'watch'                                     # it watches ≥ 3 min
    tick(pw.WATCH_S); assert f['phase'] == 'research'
    tick(); assert f['phase'] == 'decide'                                                    # no free window: research skipped, never stuck
    tick(); assert f['phase'] == 'watch' and f['rounds'] == 1                               # HOLD
    tick(pw.WATCH_S); tick(); tick(); assert f['phase'] == 'sell'                           # SELL said
    px['v'] = 1.2; tick()
    assert orders[-1] == 'sell all B2' and 'folder' not in cat['powRun']
    done = cat['powFolders'][-1]
    assert done['status'] == 'closed' and done['pnlPct'] == 20.0 and 'it topped' in done['why'] and any('higher lows' in x['text'] for x in done['talk'])
    assert fs._hive_cells()[-1]['folder']['name'] == done['name'] and fs._hive_cells()[-1]['won']   # graded + in the colony's feed
    assert cat['brainsCfg']['cloud'][-1]['text'].startswith('⛏ PoW #1')                     # the owner's cabinet
    tick(); assert 'folder' not in cat['powRun']                                            # it rests 5 min before the next folder


async def _aw_(v):
    return v


def _aw(v):
    return _aw_(v)


def test_file_a_pow_in_chat_starts_a_folder_on_any_agent_one_mind_or_both_and_stop_pow_sells(monkeypatch, tmp_path):
    import feecat_service as fs
    assert pw.command('file a PoW') == {'do': 'start', 'mind': None} and pw.command('B: file a PoW') == {'do': 'start', 'mind': 1}
    assert pw.command('/pow') and pw.command('stop PoW') == {'do': 'stop'} and pw.command('research pow on bonk') is None
    assert pw.command('Propose PoW for 3 coins thats not on feeless.')['do'] == 'start' and pw.command('Provide PoW for 3 coins on feeless intake list.')['do'] == 'start'   # the owner's own words
    assert pw.command('what is a PoW?') is None and pw.command('B: provide a pow') == {'do': 'start', 'mind': 1}
    import colony
    assert 'FOLDER' in pw.README and 'not crypto mining' in pw.README and 'PoW README' in colony.KNOWHOW          # every model's default memory
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'g1', 'name': 'Happy', 'status': 'stopped', 'risk': {}, 'positions': [], 'brainsCfg': {'kind': 'general', 'brains': ['x/m-a', 'x/m-b'], 'credit': 1.0}}
    assert not fs._pow2_on(cat)                                                              # a general agent never loops on its own …
    fs._POW_WANT['g1'] = pw.command('B: file a PoW'); assert fs._pow2_on(cat)               # … until you ask

    class R:
        def json(self): return {'coins': _intake()}

    class H:
        async def get(self, url, **k): return R()
    monkeypatch.setattr(fs, '_pow2_dex', lambda http: _aw([{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]))
    monkeypatch.setattr(fs._ct, 'run_tool', lambda http, tool, q: _aw(('read', None)))
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': '1', 'priceUsd': '200'} for p in pairs}))
    asked = []

    async def ask(c, i, sys_, user_, max_tokens=180):
        asked.append(i); return '{"pick": 4, "why": "boosted + deep"}'
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    orders = []

    async def order(store, c, text, http):
        orders.append(text); c['positions'] = [{'pairAddress': 'pd'}] if text.startswith('buy') else []
        return {'state': 'filled', 'why': 'ok'}
    monkeypatch.setattr(fs, '_run_order', order)
    store = {'cats': {'g1': cat}}
    for t in (100, 120, 140):
        asyncio.run(fs._pow2_tick(H(), store, cat, t))
    assert 'folder' in cat['powRun'], (cat['powRun'], cat.get('powFolders'))
    f = cat['powRun']['folder']
    assert f['minds'] == 1 and f['base'] == 1 and asked == [1] and orders == ['buy 0.05 SOL of D4'] and f['asked']   # mind B alone picked + bought
    assert fs._pow2_on(cat)                                                                  # its asked folder runs to the end
    fs._POW_WANT['g1'] = pw.command('stop PoW')
    asyncio.run(fs._pow2_tick(H(), store, cat, 160)); asyncio.run(fs._pow2_tick(H(), store, cat, 180))
    assert orders[-1] == 'sell all D4' and cat['powFolders'][-1]['why'] == 'you stopped it' and not fs._pow2_on(cat)
