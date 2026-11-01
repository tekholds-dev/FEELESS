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
