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


def test_a_random_3_to_8_moves_per_site_and_four_sites_then_refused(monkeypatch):
    import random
    p = pw.new({'mint': 'M', 'pair': 'P', 'sym': 'CAT'}, 0)
    rnd = random.Random(7); monkeypatch.setattr(pw.random, 'randint', rnd.randint)
    for h in ('a.com', 'b.com', 'c.com', 'd.com'):
        pw.step(p, f'https://{h}/')
    draws = [p['sites'][h]['max'] for h in ('a.com', 'b.com', 'c.com', 'd.com')]
    assert all(3 <= x <= 8 for x in draws) and len(set(draws)) > 1                           # 🎲 each SITE draws its own moves, kept on the site
    assert pw.public(p)['moves']['a.com'] == {'max': draws[0], 'used': 1} and pw.budget(p) == 8 * pw.SITES_MAX + 2
    monkeypatch.setattr(pw.random, 'randint', lambda a, b: 5)
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


def test_a_pow_run_starts_on_a_search_obeys_the_rules_and_files_its_call(monkeypatch):
    monkeypatch.setattr(pw.random, 'randint', lambda a, b: 5)                                # this scenario walks 5 moves a site
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
    coin = {**pw.new({'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT'}, 1000), 'siteSteps': 5}   # this scenario walks 5 moves a site
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
    assert 'min' in pw.hard_exit(1.0, 1.0, 0, pw.HOLD_MAX_S, 0) and pw.hard_exit(1.0, 1.1, 0, 60, 1) is None
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
            return R({'coins': _intake() + [{'mint': 'E5', 'pair': 'pe', 'sym': 'EEE', 'liq': 20000, 'rank': 1, 'sources': ['open']}]}) if 'intake' in url else R([])
    monkeypatch.setattr(fs, '_pow2_dex', lambda http: _aw([{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]))
    monkeypatch.setattr(fs._ct, 'run_tool', lambda http, tool, q: _aw((f'read {q}', None)))
    monkeypatch.setattr(fs, '_order_pair', lambda http, m: _aw({'baseToken': {'address': m}}))   # the safety reads every coin gets
    monkeypatch.setattr(fs._co, 'buy_guards', lambda p, now_ms: (True, ''))
    monkeypatch.setattr(fs, '_safety', lambda http, p: _aw((p['baseToken']['address'] != 'A1', 'top 10 hold 61%', 1.0)))

    px = {'v': 1.0}
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': str(px['v']), 'priceUsd': str(px['v'] * 200)} for p in pairs}))
    answers = {'0': ['{"pick": 1, "why": "deep pool", "size_sol": 0.04, "tp_pct": 50, "sl_pct": 20}', '{"pick": 1, "why": "final: BBB"}'],
               '1': ['{"pick": 1, "why": "agree, vol 4x", "size_sol": 0.02, "sl_pct": 15}']}
    props = {0: '{"picks": [1, 2, 3], "why": "A: deep pools"}', 1: '{"picks": [1, 3, 4], "why": "B: volume"}'}
    splits = {0: '{"picks": [1, 2], "plan": "A: rugcheck + holders"}', 1: '{"picks": [3, 4], "plan": "B: buyers vs sellers"}'}
    decide = ['{"action": "HOLD", "say": "higher lows"}', '{"action": "SELL", "say": "it topped"}']
    agree = ['{"action": "HOLD", "say": "agree"}', '{"action": "SELL", "say": "agree, lower highs"}']

    async def ask(c, i, sys_, user_, max_tokens=180):
        if 'PROPOSE the 3' in sys_:
            return props[i]
        if 'YOU will research' in sys_:
            return splits[i]
        return decide.pop(0) if 'CHART WATCHER' in sys_ else agree.pop(0) if 'partner mind' in sys_ else answers[str(i)].pop(0)
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
    assert [c['mint'] for c in f['coins']] == ['B2', 'Cpump', 'D4', 'E5'] and f['dropped'][0]['mint'] == 'A1'   # 🧺 only buyable coins reach the minds (A1 failed the safety check)
    assert f['phase'] == 'propose' and f['name'].startswith('PoW #1 · ') and f['coins'][0]['read'] == 'read B2'
    tick(); assert f['turn'] == 1 and 'proposes $BBB, $CCC, $DDD' in cat['chat'][-1]['text']   # 1 · A proposes 3
    tick(); assert f['phase'] == 'split' and f['shortlist'] == [0, 1, 2, 3]                   # 2 · B proposes 3 → the shortlist
    assert f['proposed']['1']['picks'] == [3]                                                # B never re-proposes A's coins (only E5 was left)
    tick(); assert f['owner'] == {'B2': 0, 'Cpump': 0} and 'plan: A: rugcheck' in cat['chat'][-1]['text']   # 3 · A takes 2 + its plan
    tick(); assert f['owner'] == {'B2': 0, 'Cpump': 0, 'D4': 1, 'E5': 1} and f['plans']['D4'] == 'B: buyers vs sellers'
    assert f['phase'] == 'scout' and f['scout'] == ['B2', 'D4', 'Cpump', 'E5']                # 4 · each researches its own, taking turns
    tick(); assert f['phase'] == 'scout' and not f.get('scoutDone') and f.get('busyAt')       # a busy window: the coin WAITS, never skipped unread
    for _ in range(20):
        if f['phase'] == 'scout':
            tick(310)
    assert f['scouted'] and f['phase'] == 'choose' and set(f['scoutDone']) == set(f['scout'])   # 5 min busy → it keeps its FEELESS read, never stuck
    assert 'not researched' in str(f['talk'])
    tick(); tick(); tick(); assert f['phase'] == 'buy' and f['sym'] == 'BBB' and 'final plan' in cat['chat'][-1]['text']   # DECIDE: 3 turns again → the ONE
    assert (f['sol'], f['sl']) == (0.02, 15.0)                                              # the safer of their trades
    tick(); assert orders == ['buy 0.02 SOL of B2'] and f['phase'] == 'watch' and not f['real']
    px['v'] = 1.1; tick(5); assert f['phase'] == 'watch' and f.get('checks') is None       # before +15 s: no check yet
    tick(15); assert f['checks'] == 1 and any('check 1: HOLD' in x['text'] for x in f['talk']) and any(x['text'].startswith('agrees: HOLD') for x in f['talk'])   # ⏱ +15 s: 2-step check
    tick(10); assert f['checks'] == 1                                                       # the next one is +30 s later
    tick(25); assert f['checks'] == 2 and f['phase'] == 'sell'                              # both said SELL
    assert f['nextAt'] - t == 60
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
    assert pw.command('file a PoW') == {'do': 'start', 'mind': None, 'propose': False} and pw.command('B: file a PoW') == {'do': 'start', 'mind': 1, 'propose': False}
    assert pw.command('/pow') and pw.command('stop PoW') == {'do': 'stop'} and pw.command('research pow on bonk') is None
    assert pw.command('Propose PoW for 3 coins thats not on feeless.')['do'] == 'start' and pw.command('Provide PoW for 3 coins on feeless intake list.')['do'] == 'start'   # the owner's own words
    assert pw.command('what is a PoW?') is None and pw.command('B: provide a pow') == {'do': 'start', 'mind': 1, 'propose': False}
    assert pw.command('propose a PoW')['propose'] and pw.command('A: propose a PoW') == {'do': 'start', 'mind': 0, 'propose': True}   # 💡 propose = no buy
    import colony
    assert 'FOLDER' in pw.README and 'not crypto mining' in pw.README and 'PoW README' in colony.KNOWHOW          # every model's default memory
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'g1', 'name': 'Happy', 'status': 'stopped', 'risk': {}, 'positions': [], 'brainsCfg': {'kind': 'general', 'brains': ['x/m-a', 'x/m-b'], 'credit': 1.0}}
    assert not fs._pow2_on(cat)                                                              # a general agent never loops on its own …
    fs._POW_WANT['g1'] = pw.command('B: file a PoW'); assert fs._pow2_on(cat)               # … until you ask

    class R:
        def json(self): return {'coins': _intake() + [{'mint': 'E5', 'pair': 'pe', 'sym': 'EEE', 'liq': 20000, 'rank': 1, 'sources': ['open']}]}

    class H:
        async def get(self, url, **k): return R()
    monkeypatch.setattr(fs, '_pow2_dex', lambda http: _aw([{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]))
    monkeypatch.setattr(fs._ct, 'run_tool', lambda http, tool, q: _aw(('read', None)))
    monkeypatch.setattr(fs, '_order_pair', lambda http, m: _aw({'baseToken': {'address': m}}))   # the safety reads every coin gets
    monkeypatch.setattr(fs._co, 'buy_guards', lambda p, now_ms: (True, ''))
    monkeypatch.setattr(fs, '_safety', lambda http, p: _aw((p['baseToken']['address'] != 'A1', 'top 10 hold 61%', 1.0)))

    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': '1', 'priceUsd': '200'} for p in pairs}))
    asked = []

    async def ask(c, i, sys_, user_, max_tokens=180):
        asked.append(i); return '{"pick": 3, "picks": [3, 1, 2], "plan": "rugcheck first", "why": "boosted + deep"}'   # D4 = 3rd of the vetted pool
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    orders = []

    async def order(store, c, text, http):
        orders.append(text); c['positions'] = [{'pairAddress': 'pd'}] if text.startswith('buy') else []
        return {'state': 'filled', 'why': 'ok'}
    monkeypatch.setattr(fs, '_run_order', order)
    store = {'cats': {'g1': cat}}
    monkeypatch.setattr(fs, '_work_start', lambda *a, **k: (_ for _ in ()).throw(fs.HTTPException(409, 'busy')))
    for t in range(100, 7000, 160):   # folder → propose → split → scout (a busy window waits 5 min a coin) → decide → buy
        if not orders:
            asyncio.run(fs._pow2_tick(H(), store, cat, t))
    assert 'folder' in cat['powRun'], (cat['powRun'], cat.get('powFolders'))
    f = cat['powRun']['folder']
    assert f['minds'] == 1 and f['base'] == 1 and set(asked) == {1} and orders[0].endswith('SOL of D4') and f['asked']   # mind B alone planned, decided + bought
    assert fs._pow2_on(cat)                                                                  # its asked folder runs to the end
    fs._POW_WANT['g1'] = pw.command('stop PoW')
    asyncio.run(fs._pow2_tick(H(), store, cat, 160)); asyncio.run(fs._pow2_tick(H(), store, cat, 180))
    assert orders[-1] == 'sell all D4' and cat['powFolders'][-1]['why'] == 'you stopped it' and not fs._pow2_on(cat)


def test_propose_a_pow_agrees_on_one_coin_and_files_the_card_without_buying(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'p1', 'name': 'Happy', 'risk': {}, 'positions': [], 'brainsCfg': {'kind': 'general', 'brains': ['x/a', 'x/b'], 'credit': 1.0}}
    f = pw.folder_new(1, pw.gather(_intake(), [{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]), 100, 2); f.update(asked=True, propose=True)
    cat['powRun'] = {'folder': f}

    async def ask(c, i, sys_, user_, max_tokens=180):
        return '{"pick": 4, "why": "deepest"}'
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    monkeypatch.setattr(fs, '_run_order', lambda *a: (_ for _ in ()).throw(AssertionError('a proposal never buys')))
    monkeypatch.setattr(fs, '_pow2_vet', lambda *a, **k: _aw(None))   # the safety re-check is tested in the whole-folder test
    monkeypatch.setattr(fs, '_work_start', lambda *a, **k: (_ for _ in ()).throw(fs.HTTPException(409, 'busy')))
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({}))
    for t_ in range(200, 4000, 160):   # plan (3 turns) → scout every safe coin → decide (3 turns) → filed as a card
        if 'folder' in cat['powRun']:
            asyncio.run(fs._pow2_tick(None, {'cats': {'p1': cat}}, cat, t_))
    done = cat['powFolders'][-1]
    assert 'proposes $DDD' in done['why'] and done['propose'] and 'folder' not in cat['powRun']


def test_a_real_buy_waits_for_its_wallet_and_a_folder_never_tracks_a_buy_that_did_not_fill(monkeypatch, tmp_path):
    """Live 2026-11-01: Happy's buy was a proposal waiting for approval; the folder tracked it as bought, 'sold' a coin it never held and left
    the proposal pending. Now: it waits for the fill; unsigned in 10 min → the proposal is withdrawn and the folder closes."""
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'r1', 'name': 'Happy', 'risk': {'maxPositionSol': 0.01}, 'positions': [], 'proposals': [], 'agentWallet': {'mode': 'approve'},
           'brainsCfg': {'kind': 'general', 'brains': ['x/a'], 'credit': 1.0}}
    f = pw.folder_new(1, pw.gather(_intake(), [{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]), 100, 1)
    c0 = f['coins'][3]; f.update(asked=True, phase='buy', phaseAt=100, pick=c0, mint='D4', pair='pd', sym='DDD'); cat['powRun'] = {'folder': f}

    async def order(store, c, text, http):
        c['proposals'].append({'id': 'pp1', 'side': 'buy', 'mint': 'D4', 'status': 'pending'}); return {'state': 'proposed', 'pid': 'pp1', 'why': 'waiting'}
    monkeypatch.setattr(fs, '_run_order', order)
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': '2', 'priceUsd': '400'} for p in pairs}))
    tick = lambda t: asyncio.run(fs._pow2_tick(None, {'cats': {'r1': cat}}, cat, t))   # noqa: E731
    tick(110); assert f['phase'] == 'buy' and f['pid'] == 'pp1' and cat['proposals'][0]['approved'] and 'its wallet is buying' in f['talk'][-1]['text']   # its own wallet, no signature from you
    tick(200); assert f['phase'] == 'buy'                                                   # still unsigned: it waits, tracks nothing
    cat['proposals'][0]['status'] = 'done'; cat['realHeld'] = {'D4': {}}
    tick(260); assert f['phase'] == 'watch' and f['entry'] == 2.0                          # filled → now it watches
    cat2 = dict(cat, powRun={'folder': {**f, 'phase': 'buy', 'pid': 'pp2', 'phaseAt': 100}}, proposals=[{'id': 'pp2', 'status': 'pending'}], realHeld={})
    asyncio.run(fs._pow2_tick(None, {'cats': {'r1': cat2}}, cat2, 100 + pw.SIGN_WAIT_S + 1))
    assert cat2['proposals'][0]['status'] == 'expired' and 'did not fill' in cat2['powFolders'][-1]['why']   # withdrawn, folder closed


def test_the_minds_set_size_tp_sl_clamped_to_the_wallet_budget_and_agree_on_the_safer_one():
    a = pw.trade_of('{"pick": 2, "size_sol": 0.5, "tp_pct": 80, "sl_pct": -30}', 0.02)
    assert a == {'sol': 0.02, 'tp': 80.0, 'sl': 30.0}                                       # never past its budget
    b = pw.trade_of('{"pick": 2, "size_sol": 0.01, "tp_pct": 500, "sl_pct": 2}', 0.02)
    assert b == {'sol': 0.01, 'tp': 150.0, 'sl': 5.0}                                       # sane bounds
    assert pw.agree_trade([a, b]) == {'sol': 0.01, 'sl': 5.0, 'tp': 115.0}                 # smaller size, tighter stop, average target
    assert 'stop' in pw.hard_exit(1.0, 0.94, 0, 60, 0, tp=115, sl=5) and pw.hard_exit(1.0, 1.5, 0, 60, 0, tp=115, sl=5) is None
    assert 'CAPITALIZING' in pw.README                                                       # they know why: profit funds their own processing + capital


def test_a_new_research_round_never_reopens_the_sites_an_earlier_round_read():
    p = pw.new({'mint': 'M', 'pair': 'P', 'sym': 'CAT'}, 0)
    first = [pw.host_of(u) for u in pw.links(p)][:3]
    p2 = {**p, 'used': first}
    assert not set(first) & {pw.host_of(u) for u in pw.links(p2)} and 'jup.ag' in {pw.host_of(u) for u in pw.links(p2)}   # round 2 = new sources
    assert len(pw.links({**p, 'used': [pw.host_of(u) for u in pw.links(p)]})) == 7            # all used → it cycles, never empty


def test_each_researched_site_files_two_snapshots_for_the_coins_folder():
    coin = {**pw.new({'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT'}, 1000), 'siteSteps': 5}   # this scenario walks 5 moves a site

    class LivePage(Page):
        live = True
        async def shot(self):
            return b'JPG:' + str(self.url).encode()
    moves = [{'thought': 'open', 'action': 'open', 'url': 'https://rugcheck.xyz/tokens/Mint1'}, {'thought': 'p', 'action': 'pull', 'label': 'mint authority', 'value': 'revoked'},
             {'thought': 'p', 'action': 'pull', 'label': 'top holders', 'value': '18%'}, {'thought': 'p', 'action': 'pull', 'label': 'liquidity', 'value': '$9K'},
             {'thought': 'done', 'action': 'answer', 'say': 'WATCH — thin'}]
    t = ca.new_task('ts', pw.goal(coin), ['m/a'], 1.0, pw.STEPS_MAX, 'jobs'); t.update(pow=coin, research=True, tools={'browse': True, 'forms': True})
    asyncio.run(ca.run(t, scripted({'m/a': moves}), [LivePage()], None))
    shots = coin['_shots']
    assert [(s['site'], s['n']) for s in shots][:2] == [('rugcheck.xyz', 1), ('rugcheck.xyz', 2)] and shots[0]['jpg'].startswith(b'JPG:')
    assert all(sum(1 for x in shots if x['site'] == h) <= 2 for h in {x['site'] for x in shots})   # 2 a site, never more


def test_a_refused_buy_moves_to_the_folders_next_safe_coin_never_a_dead_end(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'q1', 'name': 'Happy', 'risk': {}, 'positions': [], 'brainsCfg': {'kind': 'general', 'brains': ['x/a'], 'credit': 1.0}}
    f = pw.folder_new(1, pw.gather(_intake(), [{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]), 100, 1)
    c0 = f['coins'][3]; f.update(asked=True, phase='buy', phaseAt=100, pick=c0, mint='D4', pair='pd', sym='DDD', sol=0.01); cat['powRun'] = {'folder': f}
    seen = []

    async def order(store, c, text, http):
        seen.append(text); return {'state': 'refused', 'why': '🛡 top 10 hold 28%'} if 'D4' in text else {'state': 'filled', 'why': 'ok'}
    monkeypatch.setattr(fs, '_run_order', order)
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pairs: _aw({p: {'priceNative': '1', 'priceUsd': '200'} for p in pairs}))
    asyncio.run(fs._pow2_tick(None, {'cats': {'q1': cat}}, cat, 120))
    assert f['phase'] == 'buy' and f['sym'] == 'AAA' and 'next safe coin' in f['talk'][-1]['text']   # the deepest safe one not tried
    asyncio.run(fs._pow2_tick(None, {'cats': {'q1': cat}}, cat, 140))
    assert seen[-1] == 'buy 0.01 SOL of A1' and f['phase'] == 'watch'


def test_a_folder_tracks_what_it_costs_per_mind_and_its_research_rounds():
    import feecat_service as fs
    f = {'id': 'pow1', 'base': 0}   # a fresh folder has no vitals yet (live 2026-11-01: KeyError 'vitals' stalled a scout)
    fs._pow2_cost(f, 0, 0.002); fs._pow2_cost(f, 1, 0.001); fs._pow2_cost(f, 0, 0)
    assert f['cost'] == 0.003 and f['spend'] == {'0': 0.002, '1': 0.001}
    t_ = {'cost': 0.0161, 'pow': {**pw.new({'mint': 'M', 'pair': 'P', 'sym': 'CAT'}, 0), 'mind': 1, 'folder': 'pow1'}}
    fs._pow2_collect(f, t_, 'B', 10); fs._pow2_collect(f, t_, 'B', 11)
    assert f['spend']['1'] == 0.0171 and abs(f['cost'] - 0.0191) < 1e-9                    # the research round counted once


def test_on_a_site_not_about_the_coin_the_engine_types_the_ca_into_the_sites_search():
    coin = {**pw.new({'mint': 'Mint1', 'pair': 'Pair1', 'sym': 'CAT'}, 1000), 'siteSteps': 5}   # this scenario walks 5 moves a site
    typed = []

    class SearchPage(Page):
        async def site_search(self, q):
            typed.append((self.url, q)); self.url = f'https://coinmarketcap.com/search?q={q}'; return f'CAT page for {q}'
    moves = [{'thought': 'cmc', 'action': 'open', 'url': 'https://coinmarketcap.com/'}, {'thought': 'done', 'action': 'answer', 'say': 'WATCH'}]
    t = ca.new_task('tc', pw.goal(coin), ['m/a'], 1.0, pw.STEPS_MAX, 'jobs'); t.update(pow=coin, research=True, tools={'browse': True, 'forms': True})
    pg = SearchPage()
    asyncio.run(ca.run(t, scripted({'m/a': moves}), [pg], None))
    assert typed and typed[0] == ('https://coinmarketcap.com/', 'Mint1')                     # typed the CA into CoinMarketCap's own search
    assert any(s['thought'] == 'searched coinmarketcap.com for the CA' for s in t['windows'][0]['steps'])


def test_a_wallet_that_cannot_afford_the_buy_closes_the_folder_at_once_and_says_how_much(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'w1', 'name': 'Happy', 'chat': [], 'proposals': [{'id': 'p9', 'status': 'pending', 'agentWhy': 'the wallet holds 0.0075 SOL — 0.006 + 0.01 for gas is needed'}],
           'brainsCfg': {'kind': 'general', 'brains': ['x/a'], 'credit': 1.0}}
    f = {**pw.folder_new(5, [], 100, 1), 'phase': 'buy', 'pid': 'p9', 'phaseAt': 100, 'sym': 'DAC', 'mint': 'D', 'pair': 'P', 'asked': True}
    cat['powRun'] = {'folder': f}
    asyncio.run(fs._pow2_tick(None, {'cats': {'w1': cat}}, cat, 130))
    assert cat['proposals'][0]['status'] == 'expired' and 'wallet is short' in cat['powFolders'][-1]['why'] and 'Add SOL' in cat['chat'][-1]['text']


def test_the_thinking_top_up_never_spends_the_sol_it_trades_with():
    """Live 2026-11-01: USDC ran low and the wallet swapped 0.0135 SOL into USDC for its model calls — its next PoW buy had no SOL."""
    import feecat_service as fs
    assert fs.think_keep_sol({'budgetSol': 0.01}) == 0.022                     # one trade (0.01) + gas (0.01) + room
    assert fs.think_keep_sol({}) == 0.012 and fs.THINK_SWAP_SOL <= 0.004                 # no budget set: still the trade gas + room


def test_no_coin_twice_random_sites_skip_the_last_folders_and_every_folder_reports():
    import random
    old = [{'coins': [{'mint': 'A1'}, {'mint': 'B2'}]}, {'coins': [{'mint': 'C3'}]}]
    assert pw.recent_mints(old) == {'A1', 'B2', 'C3'}
    got = pw.gather(_intake(), [{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}], pw.recent_mints(old))
    assert not {c['mint'] for c in got} & {'A1', 'B2', 'C3'}                                 # 🚫 a coin of a recent folder never comes back
    folders = [{'shots': [{'site': 'dexscreener.com'}], 'vitals': {'m': [{'site': 'rugcheck.xyz'}]}, 'pnlPct': 5},
               {'shots': [{'site': 'solscan.io'}], 'pnlPct': -3}, {'shots': [{'site': 'birdeye.so'}], 'pnlPct': -1}]
    recent, wins = pw.site_memory(folders)
    assert recent == {'solscan.io', 'birdeye.so'} and wins == {'dexscreener.com', 'rugcheck.xyz'}
    o = pw.site_order(recent, wins, random.Random(1))
    assert o[:2] == ['dexscreener.com', 'rugcheck.xyz'] and not set(o) & recent              # winners first, the last folders' sites skipped
    orders = {tuple(pw.site_order(set(), set(), random.Random(k))) for k in range(6)}
    assert len(orders) > 1                                                                   # 🎲 random, not one fixed route
    p = {**pw.new({'mint': 'M', 'pair': 'P', 'sym': 'X'}, 0), 'order': o}
    assert [pw.host_of(u) for u in pw.links(p)] == o
    f = {'name': 'PoW #9', 'coins': [{'mint': 'M', 'sym': 'X', 'src': 'pump'}, {'mint': 'N', 'sym': 'Y', 'src': 'dex', 'safe': False, 'risk': 'mint on'}],
         'pick': {'mint': 'M'}, 'sym': 'X', 'pnlPct': -4.2, 'pnlSol': -0.0003, 'why': 'stop: -4%', 'vitals': {'M': [{'site': 'rugcheck.xyz', 'label': 'risk score', 'value': 'GOOD'}]},
         'shots': [{'mint': 'M', 'site': 'rugcheck.xyz'}], 'cost': 0.05, 'talk': [{'by': 'A', 'text': 'buy X'}], 'boughtAt': 0, 'soldAt': 600}
    r, md = pw.report(f)
    assert r['grade'] == '👎 bad trade' and r['researched'] == 1 and r['held'] == 10 and r['costUsd'] == 0.05
    assert 'FINAL REPORT' in md and '⭐ $X' in md and 'UNSAFE: mint on' in md and '**A**: buy X' in md


def test_a_research_round_has_its_own_small_dollar_ceiling(monkeypatch):
    """Live 2026-11-01: folder #5 spent $0.062 researching (its whole credit was each round's cap) and never bought."""
    import feecat_service as fs

    async def run_(*a, **k):
        return None
    monkeypatch.setattr(fs, '_work_run', run_)
    cat = {'id': 'r1', 'brainsCfg': {'brains': ['m/a', 'm/b'], 'credit': 4.0}}

    async def go():
        fs._work_start('r1', cat, 'PROOF OF WORK on $X', '0', None, {**pw.new({'mint': 'M', 'pair': 'P', 'sym': 'X'}, 0)})
        return fs._WORK.pop('r1')['task']['cap']
    assert asyncio.run(go()) == pw.ROUND_USD == 0.03                                     # owner 2026-11-02: $0.03 a coin


def test_an_unsafe_coin_is_replaced_so_four_safe_coins_get_researched(monkeypatch, tmp_path):
    """Owner 2026-11-02 ("they must find 4 coins"): live folder #8 had 3 unsafe coins of 4 and researched only one."""
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json')
    cat = {'id': 'r1', 'name': 'Trader', 'status': 'running', 'positions': [], 'brainsCfg': {'kind': 'trading', 'brains': ['x/a', 'x/b'], 'credit': 1.0}}
    intake = _intake() + [{'mint': 'E5', 'pair': 'pe', 'sym': 'EEE', 'liq': 25000, 'rank': 2, 'sources': ['open']},
                          {'mint': 'F6', 'pair': 'pf', 'sym': 'FFF', 'liq': 25000, 'rank': 1, 'sources': ['open']}]

    class R:
        def __init__(self, j): self.j = j
        def json(self): return self.j

    class H:
        async def get(self, url, **k):
            return R({'coins': intake})
    monkeypatch.setattr(fs, '_pow2_dex', lambda http: _aw([{'mint': 'D4', 'pair': 'pd', 'sym': 'DDD', 'liq': 90000}]))
    monkeypatch.setattr(fs._ct, 'run_tool', lambda http, tool, q: _aw((f'read {q}', None)))
    monkeypatch.setattr(fs, '_order_pair', lambda http, m: _aw({'baseToken': {'address': m}}))
    monkeypatch.setattr(fs._co, 'buy_guards', lambda p, now_ms: (True, ''))
    monkeypatch.setattr(fs, '_safety', lambda http, p: _aw((p['baseToken']['address'] not in ('A1', 'E5'), 'top 10 hold 61%', 1.0)))   # A1 + its first stand-in unsafe
    fs._POW_WANT['r1'] = {'do': 'start'}
    asyncio.run(fs._pow2_tick(H(), {'cats': {'r1': cat}}, cat, 10_000.0))
    f = cat['powRun']['folder']
    assert [c['mint'] for c in f['coins']] == ['B2', 'Cpump', 'D4', 'F6'] and all(c['safe'] for c in f['coins'])   # A1 + E5 failed → F6 joins the pool
    assert [x['mint'] for x in f['dropped']] == ['A1', 'E5'] and 'replaced 2 unsafe: $AAA' in str(f['talk'])


def test_a_coin_that_runs_during_research_is_struck_before_they_decide(monkeypatch):
    """Live 2026-11-02 PoW #8: $pairless was safe at gather, ran +443 % in the 5 min of research, and the buy was refused."""
    import feecat_service as fs
    f = {'id': 'p8', 'name': 'PoW #8', 'phase': 'choose', 'scouted': True, 'turn': 0, 'minds': 1, 'base': 0, 'picks': {}, 'talk': [],
         'coins': [{'mint': 'M1', 'sym': 'PAIR', 'src': 'pump', 'liq': 28000, 'mc': 1, 'pair': 'p1'}, {'mint': 'M2', 'sym': 'OK', 'src': 'intake', 'liq': 9000, 'mc': 1, 'pair': 'p2'}]}
    cat = {'id': 'x1', 'brainsCfg': {'brains': ['x/a']}, 'powRun': {'folder': f}, 'chat': []}

    async def vet(http, c, now, read=True):
        if c['mint'] == 'M1':
            c.update(safe=False, risk='🚀 +443% in 1h — already ran')
    monkeypatch.setattr(fs, '_pow2_vet', vet)
    seen = []

    async def ask(c, i, sys_, user_, max_tokens=180):
        seen.append(user_); return '{"pick": 2, "why": "the only one left"}'
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    asyncio.run(fs._pow2_tick(None, {'cats': {'x1': cat}}, cat, 1000.0))
    assert 'PAIR is out now' in str(f['talk']) and '$PAIR' not in seen[0] and f.get('pick', {}).get('mint') == 'M2'   # struck: not even offered


def test_colony_flow_shows_real_trades_and_leaves_incognito_agents_out(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'HIVE_PATH', tmp_path / 'hive.json'); monkeypatch.setattr(fs, 'SHARES_PATH', tmp_path / 'shares.json')
    tx = lambda side, sol, sig: {'side': side, 'symbol': 'SIS', 'mint': 'M', 'sol': sol, 'sig': sig, 'status': 'success', 'at': 100}   # noqa: E731
    store = {'cats': {'a': {'id': 'a', 'name': 'Happy', 'agentTx': [tx('buy', 0.006, 'S1'), tx('sell', 0.005, 'S2')],
                            'powFolders': [{'mint': 'M', 'real': True, 'entry': 1, 'sol': 0.006, 'pnlSol': -0.001}]},
                      'b': {'id': 'b', 'name': 'Hidden', 'incognito': True, 'agentTx': [tx('buy', 1, 'S9')], 'powFolders': [{'real': True, 'entry': 1, 'sol': 1, 'pnlSol': 5}]}}}
    monkeypatch.setattr(fs, '_load', lambda: store)
    out = asyncio.run(fs.colony_flow())
    assert out['pow'] == {'folders': 1, 'trades': 1, 'inSol': 0.006, 'won': 0} and out['pnlSol'] == -0.001
    assert [r['sig'] for r in out['ledger']] == ['S1', 'S2'] and out['ledger'][0]['memo'] == 'PoW buy' and 'Hidden' not in str(out)


def test_duplicate_facts_are_dropped_and_every_filing_is_kept_forever_and_searchable(monkeypatch, tmp_path):
    import cat_tools as ct
    import feecat_service as fs
    p = {**pw.new({'mint': 'M', 'pair': 'P', 'sym': 'X'}, 0), 'siteSteps': 5}
    assert pw.pull(p, 'https://rugcheck.xyz/tokens/M', 'liquidity', '$35.2K')[0]
    ok, why = pw.pull(p, 'https://solscan.io/token/M', 'liquidity', '$35.2k')
    assert not ok and 'already saved from rugcheck.xyz' in why                              # 🧹 the same fact twice adds nothing
    assert pw.pull(p, 'https://solscan.io/token/M', 'liquidity', '$41K')[0]                  # a different value IS new evidence
    monkeypatch.setattr(fs, 'POW_ARCHIVE', tmp_path / 'pow_archive.jsonl')
    f = {'id': 'pow1', 'name': 'PoW #1'}
    fs._pow_archive_add(pw.archive_row('research', 'h1', f, {'mint': 'M', 'sym': 'X'}, 10, vitals=[{'label': 'risk score', 'value': 'GOOD', 'site': 'rugcheck.xyz'}]))
    fs._pow_archive_add(pw.archive_row('outcome', 'h1', f, {'mint': 'M', 'sym': 'X'}, 20, pnlPct=-4.2, bought=True, sol=0.006, why='stop'))
    fs._pow_archive_add(pw.archive_row('research', 'h1', f, {'mint': 'Q', 'sym': 'Y'}, 30))
    rows = fs._pow_archive_rows(); assert len(rows) == 3                                      # 🗄 append-only: every filing stays
    hit = pw.archive_find(rows, '$x'); assert [r['kind'] for r in hit] == ['outcome', 'research']
    assert pw.archive_brief(hit) == 'PRIOR PoW: researched 1× risk score GOOD · traded -4.2%'
    out = asyncio.run(fs.pow_archive(q='M')); assert out['total'] == 3 and len(out['rows']) == 2 and 'researched 1×' in out['brief']

    class R:
        def __init__(self, j): self.j = j
        def json(self): return self.j

    class H:
        async def get(self, url, params=None, **k):
            return R(asyncio.run(fs.pow_archive(q=params['q'])) if False else {'rows': hit, 'brief': pw.archive_brief(hit)})
    text, _ = asyncio.run(ct.run_tool(H(), 'pow', '$X'))
    assert 'PRIOR PoW' in text and 'risk score GOOD (rugcheck.xyz)' in text and 'bought 0.006 SOL' in text   # the agents' own tool reads it


def test_a_sell_is_only_the_minds_action_never_the_word_inside_a_sentence():
    """Live 2026-11-02 PoW $GATO check 3: both minds said hold, the parser read 'no signal to sell' as SELL."""
    assert pw.parse_decide('{"action": "HOLD", "say": "No signal to sell; holding for TP."}')[0] == 'HOLD'
    assert pw.parse_decide('Chart flat — no signal to sell; holding for TP.')[0] == 'HOLD'
    assert pw.parse_decide('{"action": "SELL", "say": "lower highs"}')[0] == 'SELL' and pw.parse_decide('SELL — it topped')[0] == 'SELL'


def test_no_used_site_is_reopened_and_a_known_fact_is_never_filed_twice():
    """Live PoW #9: rugcheck was opened again in the next round and PRICE was filed 3 times in $GATO's folder."""
    p = {**pw.new({'mint': 'M', 'pair': 'P', 'sym': 'X'}, 0), 'used': ['rugcheck.xyz', 'feeless.app', 'jup.ag', 'dexscreener.com', 'solscan.io'],
         'order': ['rugcheck.xyz', 'solscan.io', 'jup.ag'], 'known': ['price', 'lp locked']}
    hosts = [pw.host_of(u) for u in pw.links(p)]
    assert hosts and not set(hosts) & set(p['used']) and set(hosts) <= {'birdeye.so', 'pump.fun', 'coingecko.com'}   # only sites never read for this coin
    ok, why = pw.pull(p, 'https://birdeye.so/token/M', 'price', '$0.0074')
    assert not ok and 'already in this coin' in why and 'holders' in why                     # it is told what is still unknown
    assert pw.pull(p, 'https://birdeye.so/token/M', 'holders', '2,140')[0]
    m = pw.merge_vitals([{'label': 'price', 'value': '$0.007428', 'site': 'feeless.app'}], [{'label': 'price', 'value': '0.007420', 'site': 'birdeye.so'}, {'label': 'holders', 'value': '2,140', 'site': 'birdeye.so'}])
    assert [x['label'] for x in m] == ['price', 'holders'] and m[0]['value'] == '0.007420' and m[0]['sites'] == ['feeless.app', 'birdeye.so']   # one row a fact


def test_a_research_round_reviews_the_coins_archive_first_new_sites_new_facts(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'POW_ARCHIVE', tmp_path / 'a.jsonl')
    fs._pow_archive_add(pw.archive_row('research', 'h1', {'id': 'old'}, {'mint': 'M', 'sym': 'X'}, 900, sites=['rugcheck.xyz', 'feeless.app'],
                                       vitals=[{'label': 'lp locked', 'value': '97%', 'site': 'rugcheck.xyz'}]))
    seen = {}
    monkeypatch.setattr(fs, '_work_start', lambda cid, c, text, to=None, files=None, pow_=None: (seen.update(pw=pow_), fs._WORK.update({cid: {'task': {}}}))[0])
    fs._WORK.pop('h1', None)
    assert fs._pow2_research({'id': 'h1', 'powFolders': []}, {'id': 'f1', 'charts': {}}, {'mint': 'M', 'pair': 'P', 'sym': 'X'}, 0, 1000)
    rp = seen['pw']; t = fs._WORK.pop('h1')['task']
    assert 'lp locked' in rp['known'] and {'rugcheck.xyz', 'feeless.app'} <= set(rp['used'])   # the last research's facts + sites are not repeated
    assert 'PRIOR PoW: researched 1×' in rp['prior'] and 'do NOT repeat it' in t['handoffs'][-1]['text']
