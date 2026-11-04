import pytest
"""📉 Proof of Perps: both minds must agree, the safer numbers win, hard exits on true prices, and nothing real is ever sent. 🤖 Free-chip bids settle on the real result."""
import pop
import poi
import pow_kernel
import rep_markets as rm


def call(side='long', market='SOL', lev=3, tp=4, sl=2):
    return {'market': market, 'side': side, 'lev': lev, 'tp': tp, 'sl': sl, 'why': 'x'}


def test_a_reply_without_a_real_side_or_market_is_no_call_and_numbers_are_clamped():
    assert pop.parse_call('I would go long') is None and pop.parse_call('{"market":"DOGE","side":"long"}') is None and pop.parse_call('{"market":"SOL","side":"none"}') is None
    c = pop.parse_call('sure {"market":"sol","side":"LONG","lev":100,"tp_pct":90,"sl_pct":0}')
    assert c['market'] == 'SOL' and c['side'] == 'long' and c['lev'] == pop.LEV_MAX and c['tp'] == pop.TP_RANGE[1] and c['sl'] == pop.SL_RANGE[0]


def test_the_minds_must_agree_and_the_safer_numbers_win():
    t, _ = pop.agree([call(lev=4, tp=6, sl=3), call(lev=2, tp=3, sl=1)])
    assert t == {'market': 'SOL', 'side': 'long', 'lev': 2, 'tp': 3, 'sl': 1}
    assert pop.agree([call(), call('short')])[0] is None and pop.agree([call(), call(market='ETH')])[0] is None and pop.agree([call(), None])[0] is None and pop.agree([])[0] is None


def test_hard_exits_for_both_sides_and_liquidation_beats_the_stop():
    t = {'entry': 100.0, 'side': 'long', 'lev': 5, 'tp': 3, 'sl': 2, 'openedAt': 0}
    assert pop.hard_exit(t, 100.5, 10) is None and pop.hard_exit(t, 103, 10) == 'take profit' and pop.hard_exit(t, 98, 10) == 'stop' and pop.hard_exit(t, 80, 10) == 'liquidated' and pop.hard_exit(t, 100, pop.HOLD_MAX_S) == 'time' and pop.hard_exit(t, 0, 10) is None
    s = {**t, 'side': 'short'}
    assert pop.hard_exit(s, 97, 10) == 'take profit' and pop.hard_exit(s, 102, 10) == 'stop'


def test_the_filed_result_is_leveraged_roe_on_the_paper_stake_and_a_liquidation_loses_exactly_the_stake():
    t = {'entry': 100.0, 'side': 'short', 'lev': 2, 'tp': 3, 'sl': 2, 'openedAt': 0}
    r = pop.close(t, 97, 60, 'take profit')
    assert r['roePct'] == 6.0 and r['pnlUsd'] == 0.6 and r['won'] and r['status'] == 'closed'
    assert pop.close(t, 500, 60, 'liquidated')['pnlUsd'] == -pop.COLLATERAL_USD


def test_the_chat_commands_never_catch_a_question():
    assert pop.command('file a PoP') == 'start' and pop.command('/pop') == 'start' and pop.command('stop pop') == 'stop'
    assert pop.command('what is a pop star') is None and pop.command('pop.fun is down') is None


def test_a_market_read_needs_real_numbers():
    assert pop.read_market('SOL', {'open': '90'}, {'price': '99'})['chgPct'] == 10.0
    assert pop.read_market('SOL', None, {'price': '99'}) is None and pop.read_market('SOL', {'open': '90'}, None) is None


def test_the_kernel_is_pinned_so_a_limit_cannot_change_quietly():
    assert pow_kernel.fingerprint() == 'efec14752ff3', 'A hard limit changed: if it was on purpose, bump pow_kernel.VERSION and this pin.'
    v = pow_kernel.view()
    assert v['hash'] == pow_kernel.fingerprint() and dict(next(g for g in v['groups'] if g['name'] == 'Proof of Perps')['rows'])['Real orders'] is False


def test_a_retired_source_can_roll_back_only_through_new_useful_visits():
    def row(g, facts, gap=False):
        return {'generation': g, 'visited': ['a.io'], 'facts': [{'site': 'a.io'}] * facts, 'metrics': {'gaps': ['a.io'] if gap else []}}
    rows = [row(i + 1, 2) for i in range(4)]
    assert poi.evolution(rows)['states']['a.io'] == 'promoted'
    rows += [row(5, 0), row(6, 0)]
    assert poi.evolution(rows)['states']['a.io'] == 'retired'
    assert poi.evolution(rows + [row(7, 2), row(8, 0)])['states']['a.io'] == 'retired'
    back = poi.evolution(rows + [row(7, 2), row(8, 2)])
    assert back['states']['a.io'] == 'candidate' and back['events'][-1]['state'] == 'rollback'


def test_a_bid_market_opens_on_a_live_proof_the_agent_backs_itself_and_the_real_result_settles_it():
    st = {}
    feed = [{'id': 'pop1', 'cat': 'c1', 'agent': 'Happy', 'kind': 'pop', 'label': 'long SOL PoP', 'open': True}]
    assert rm.sync_agents(st, feed, 1000) == 1 and rm.sync_agents(st, feed, 1001) == 0
    m = st['markets'][0]
    assert m['kind'] == 'agent' and any(s['w'] == 'agent:c1' and s['side'] == 'yes' for s in m['stakes'])
    rm.stake(st, 'me', m['id'], 'no', 100, 1002)
    assert rm.settle(st, 1003) == []                                                  # no result yet: still open
    rm.sync_agents(st, [{**feed[0], 'open': False, 'won': False}], 1004)
    assert [x['id'] for x in rm.settle(st, 1005)] == [m['id']] and m['result'] == 'no'
    assert rm.bank(st, 'me', 1005)['chips'] > rm.CHIPS_WEEK                             # a right call paid out, in chips


def test_chips_lock_after_the_bid_window_and_a_proof_with_no_result_refunds():
    st = {}
    rm.sync_agents(st, [{'id': 'p', 'cat': 'c', 'agent': 'A', 'label': 'x', 'open': True}], 1000)
    m = st['markets'][0]; rm.stake(st, 'me', m['id'], 'yes', 50, 1001)
    try:
        rm.stake(st, 'me', m['id'], 'yes', 50, 1000 + rm.AGENT_BID_S + 1)
        assert False, 'should be locked'
    except ValueError:
        pass
    rm.settle(st, 1000 + rm.AGENT_VOID_S + 1)
    assert m['result'] == 'void' and rm.bank(st, 'me', 1000 + rm.AGENT_VOID_S + 1)['chips'] == rm.CHIPS_WEEK


def _fake_http(prices):
    class R:
        status_code = 200
        def __init__(self, j): self.j = j
        def json(self): return self.j

    class H:
        async def get(self, url, **k):
            m = url.split('/products/')[1].split('-')[0]
            return R({'open': '90', 'high': '100', 'low': '80', 'volume': '5'} if url.endswith('/stats') else {'price': str(prices.get(m, 0))})
    return H()


def test_the_engine_opens_on_agreement_runs_true_prices_and_files_it_and_a_disagreement_files_no_trade(monkeypatch):
    import asyncio
    import feecat_service as fs
    answers = {0: '{"market":"SOL","side":"long","lev":4,"tp_pct":5,"sl_pct":2,"why":"up on the day"}', 1: '{"market":"SOL","side":"long","lev":2,"tp_pct":3,"sl_pct":2,"why":"volume"}'}

    async def ask(cat, i, sys_, user_, max_tokens=180, cost_to=None):
        assert 'SOL-PERP price' in user_
        return answers[i]
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    cat = {'id': 'c9', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    fs._POP_WANT['c9'] = 'start'
    asyncio.run(fs._pop_tick(_fake_http({'SOL': 100, 'ETH': 10, 'BTC': 1000}), cat, 1000.0))
    run = cat['popRun']
    assert run['entry'] == 100 and run['lev'] == 2 and run['tp'] == 3 and run['paper'] is True and 'proposals' not in cat   # no order or proposal exists anywhere
    asyncio.run(fs._pop_tick(_fake_http({'SOL': 101}), cat, 1010.0))
    assert cat['popRun']['roePct'] == 2.0 and cat['popRun']['mark'] == 101
    asyncio.run(fs._pop_tick(_fake_http({'SOL': 104}), cat, 1020.0))
    assert 'popRun' not in cat and cat['popFolders'][-1]['why'] == 'take profit' and cat['popFolders'][-1]['roePct'] == 8.0
    answers[1] = '{"market":"BTC","side":"short","lev":2,"tp_pct":3,"sl_pct":2,"why":"topping"}'
    fs._POP_WANT['c9'] = 'start'
    asyncio.run(fs._pop_tick(_fake_http({'SOL': 100, 'ETH': 10, 'BTC': 1000}), cat, 2000.0))
    assert 'popRun' not in cat and cat['popFolders'][-1]['noTrade'] and 'long SOL vs short BTC' in cat['popFolders'][-1]['why']


def _ppop_fakes(monkeypatch, answers):
    import feecat_service as fs
    seen = []

    async def ask(cat, i, sys_, user_, max_tokens=180, cost_to=None):
        seen.append((i, sys_))
        cost_to['cost'] = round(cost_to['cost'] + 0.001, 6)
        return answers[i].pop(0)
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    return fs, seen


LONG, SHORT = '{"market":"SOL","side":"long","lev":4,"tp_pct":5,"sl_pct":2,"why":"up"}', '{"market":"SOL","side":"short","lev":2,"tp_pct":3,"sl_pct":2,"why":"down"}'
_P = {'SOL': 100, 'ETH': 10, 'BTC': 1000}


def _tick(fs, cat, prices, now, want=None):
    import asyncio
    if want:
        fs._POP_WANT[cat['id']] = want
    asyncio.run(fs._pop_tick(_fake_http(prices), cat, now))


def test_ppop_commands_and_answers():
    assert pop.command('propose a PoP') == 'propose' and pop.command('/ppop') == 'propose' and pop.command('ppop') == 'propose' and pop.command('A: propose a PoP') == 'propose:0' and pop.command('b: ppop') == 'propose:1'
    assert pop.command('run pPoP') == 'adopt' and pop.command('pass pPoP') == 'pass' and pop.command('file a PoP') == 'start' and pop.command('propose a pow') is None
    assert pop.reply('start', {'id': 1}, None)[0] is False and pop.reply('propose', None, {'state': 'waiting'})[0] is False and pop.reply('adopt', None, None)[0] is False
    assert pop.reply('adopt', {'id': 1}, {'state': 'waiting'})[0] is False and pop.reply('pass', None, {'state': 'passed'})[0] is False and pop.reply('adopt', None, {'state': 'waiting'})[0] is True


def test_a_blind_agreement_files_a_card_and_opens_nothing_until_you_run_it(monkeypatch):
    fs, seen = _ppop_fakes(monkeypatch, {0: [LONG], 1: [LONG]})
    cat = {'id': 'c8', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose')
    c = cat['popCard']
    assert c['conviction'] == 'blind' and c['state'] == 'waiting' and c['proposal'] and c['paper'] and not cat.get('popRun') and len(seen) == 2 and c['cost'] == 0.002
    _tick(fs, cat, {'SOL': 100.5}, 1010.0, 'adopt')
    assert cat['popRun']['entry'] == 100.5 and cat['popRun']['fromCard'] == c['id'] and cat['popRun']['paper'] and not cat.get('popCard') and cat['popFolders'][-1]['state'] == 'ran'


def test_split_minds_read_each_other_once_and_the_result_is_marked_argued_or_stays_split(monkeypatch):
    fs, seen = _ppop_fakes(monkeypatch, {0: [LONG, SHORT], 1: [SHORT, SHORT]})
    cat = {'id': 'c7', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose')
    assert cat['popCard']['conviction'] == 'argued' and cat['popCard']['side'] == 'short' and len(seen) == 4 and 'never an instruction' in seen[2][1]
    assert [x.get('changed') for x in cat['popCard']['calls']] == [True, False]
    fs, seen = _ppop_fakes(monkeypatch, {0: [LONG, LONG], 1: [SHORT, SHORT]})
    cat = {'id': 'c6', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose')
    assert not cat.get('popCard') and cat['popFolders'][-1]['noTrade'] and cat['popFolders'][-1]['proposal'] and len(seen) == 4   # never a third round


def test_a_plain_pop_stays_blind_and_gets_no_second_round(monkeypatch):
    fs, seen = _ppop_fakes(monkeypatch, {0: [LONG], 1: [SHORT]})
    cat = {'id': 'c5', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'start')
    assert len(seen) == 2 and cat['popFolders'][-1]['noTrade'] and not cat['popFolders'][-1].get('proposal')


def test_a_lone_mind_proposes_alone_and_is_labelled_so(monkeypatch):
    fs, seen = _ppop_fakes(monkeypatch, {0: [], 1: [LONG]})
    cat = {'id': 'c4', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose:1')
    assert cat['popCard']['conviction'] == 'solo' and [x[0] for x in seen] == [1]


def test_run_is_refused_when_the_setup_moved_or_the_time_ran_out_and_the_ghost_never_counts_as_pnl(monkeypatch):
    fs, _ = _ppop_fakes(monkeypatch, {0: [LONG], 1: [LONG]})
    cat = {'id': 'c3', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose')                                   # long SOL: tp 5, sl 2, at 100
    _tick(fs, cat, {'SOL': 101.5}, 1010.0, 'adopt')                         # used 30% of its room: still fine? refused only at half
    assert cat.get('popRun') and not cat.get('popCard')
    fs, _ = _ppop_fakes(monkeypatch, {0: [LONG], 1: [LONG]})
    cat = {'id': 'c2', 'brainsCfg': {'brains': ['x/a', 'x/b']}}
    _tick(fs, cat, _P, 1000.0, 'propose')
    _tick(fs, cat, {'SOL': 99}, 1010.0, 'adopt')                            # half way to its stop
    assert not cat.get('popRun') and 'setup is gone' in cat['popCard']['refused']
    _tick(fs, cat, {'SOL': 100}, 1000.0 + pop.PROPOSE_WINDOW_S, 'adopt')    # back at entry, but too late
    assert not cat.get('popRun') and '15 minutes' in cat['popCard']['refused'] or cat['popCard']['state'] == 'expired'
    _tick(fs, cat, {'SOL': 103}, 1000.0 + pop.PROPOSE_WINDOW_S + 5)         # tp is the tighter of both minds' numbers
    _tick(fs, cat, {'SOL': 106}, 1000.0 + pop.PROPOSE_WINDOW_S + 9)
    rec = cat['popFolders'][-1]
    assert rec['ghost'] and rec['won'] and 'pnlUsd' not in rec and not cat.get('popCard') and rec['state'] == 'expired'


def test_a_proposal_never_touches_an_open_pop_and_no_market_settles_on_it(monkeypatch):
    fs, _ = _ppop_fakes(monkeypatch, {0: [LONG], 1: [LONG]})
    run = {'id': 'popR', 'market': 'ETH', 'side': 'long', 'lev': 2, 'tp': 50, 'sl': 50, 'entry': 10, 'mark': 10, 'openedAt': 1000, 'status': 'open'}
    cat = {'id': 'c1', 'brainsCfg': {'brains': ['x/a', 'x/b']}, 'popRun': run}
    _tick(fs, cat, _P, 1000.0, 'propose')
    assert cat['popRun'] is run and cat['popCard']['state'] == 'waiting'
    _tick(fs, cat, {'SOL': 100, 'ETH': 10}, 1010.0, 'adopt')
    assert cat['popRun'] is run and 'already open' in cat['popCard']['refused']                 # never a second PoP
    _tick(fs, cat, {'SOL': 100, 'ETH': 10}, 1020.0, 'pass')
    assert cat['popCard']['state'] == 'passed'
    _tick(fs, cat, {'SOL': 106, 'ETH': 10}, 1030.0)                                             # its ghost closes: the live PoP stays open
    assert cat['popRun'] is run and not cat.get('popCard') and cat['popFolders'][-1]['state'] == 'passed'


def test_a_pops_calls_never_land_on_the_open_pow_folders_bill():
    import inspect
    import feecat_service as fs
    assert 'cost_to' in inspect.signature(fs._pow2_ask).parameters
    folder = {}; box = {'cost': 0}
    fs._pow2_cost(box, 0, 0.002)
    assert box['cost'] == 0.002 and not folder


def test_walls_one_window_each_then_the_minds_move_on():
    import agent_sources as src
    book = src.record({}, 'solscan.io', False, now=1000)
    assert src.walled_lately(book, 'https://solscan.io/token/x', now=1000 + 60) and not src.walled_lately(book, 'solscan.io', now=1000 + src.WALL_MEMORY_S)
    assert not src.walled_lately(src.record(book, 'solscan.io', True, now=1100), 'solscan.io', now=1101)


def test_a_filed_proof_becomes_a_numbered_folder_with_a_report_and_discussion_and_a_ghost_never_reports_pnl():
    calls = [{'mind': 0, 'name': 'A', 'side': 'long', 'market': 'SOL', 'lev': 3, 'tp': 2, 'sl': 1, 'why': 'trend'}]
    trade = {'id': 'p1', 'at': 100, 'status': 'closed', 'side': 'long', 'market': 'SOL', 'entry': 100.0, 'openedAt': 100, 'closedAt': 700, 'roePct': 6.0, 'pnlUsd': 0.6, 'won': True, 'why': 'take profit', 'calls': calls}
    f = pop.folder(trade, 3)
    assert f['n'] == 3 and f['report']['grade'] == 'GOOD TRADE' and f['report']['held'] == 10.0 and f['report']['pnlUsd'] == 0.6
    assert [t['by'] for t in f['talk']] == ['A', 'Engine', 'Engine'] and 'take profit' in f['talk'][-1]['text']
    g = pop.report({**trade, 'ghost': True, 'proposal': True})
    assert g['grade'] == 'GHOST WIN' and g['pnlUsd'] is None and 'Never counted' in g['lesson']
    none = pop.report({'status': 'closed', 'noTrade': True, 'why': 'long SOL vs long BTC', 'calls': calls})
    assert none['grade'] == 'NO TRADE' and none['roePct'] is None and 'long SOL vs long BTC' in none['lesson']
    assert pop.report({'status': 'open'}) is None


def test_kept_folders_survive_the_trim_numbers_never_repeat_and_the_line_is_sampled_slowly():
    rows = [{'id': i, 'kept': i == 0} for i in range(pop.FILED_MAX + 2)]
    out = pop.trim(rows)
    assert len(out) == pop.FILED_MAX and out[0]['id'] == 0 and {1, 2} not in [{r['id'] for r in out}] and all(r['id'] not in (1, 2) for r in out)
    cat = {'popFolders': [{}, {}], 'popSeq': 9}
    assert pop.number(cat) == 10 and pop.number({'popFolders': [{}, {}]}) == 3
    t = {}
    pop.sample(t, 100, 1000); pop.sample(t, 101, 1010); pop.sample(t, 102, 1030); pop.sample(t, 0, 1090)
    assert t['line'] == [100.0, 102.0]


def test_the_folder_says_the_size_the_wallet_really_sends():
    fs = pytest.importorskip('feecat_service')
    cat = {'proposals': [{'id': 'a', 'sol': 0.008}, {'id': 'b'}]}
    assert fs._pow2_real_sol(cat, 'a', 0.01) == 0.008 and fs._pow2_real_sol(cat, 'b', 0.01) == 0.01 and fs._pow2_real_sol(cat, 'gone', 0.01) == 0.01


def test_perp_words_work_like_pop_and_never_catch_a_question():
    assert pop.command('file a perp') == 'start' and pop.command('place a perp trade') == 'start' and pop.command('/perp') == 'start'
    assert pop.command('propose a perp') == 'propose' and pop.command('A: propose a perp') == 'propose:0' and pop.command('stop perp') == 'stop'
    assert pop.command('what is a perp?') is None and pop.command('should I file a perp?') is None


def test_each_mind_gets_different_sources_every_proof_and_one_carries_funding():
    import pop_sources as ps
    a = ps.pick([], 0); b = ps.pick([], 1, a)
    assert len(a) == 2 and not set(a) & set(b) and ps.SOURCES[a[0]][0] == 'perp' and ps.SOURCES[b[0]][0] == 'perp'
    filed = [{'sources': {'0': [{'site': s, 'ok': True, 'devBps': 1.0} for s in a]}}]
    assert not set(ps.pick(filed, 0)) & set(a)                                          # never its own last sources
    bad = next(iter(ps.SOURCES)); fails = [{'sources': {'0': [{'site': bad, 'ok': False}]}}, {'sources': {'0': [{'site': 'okx.com', 'ok': True, 'devBps': 1.0}]}}]
    assert bad not in ps.pick(fails, 0)                                                  # a failing source drops down


def test_reads_are_measured_against_the_chart_and_off_or_failed_reads_are_not_facts():
    import pop_sources as ps
    good = ps.measure('okx.com', 'SOL', {'px': 100.1, 'funding': 0.01}, 100.0)
    off = ps.measure('kraken.com', 'SOL', {'px': 102.0}, 100.0); none = ps.measure('gemini.com', 'SOL', None, 100.0)
    assert good['devBps'] == 10.0 and not good['off'] and off['off'] is True and none['ok'] is False
    assert 'no read' in ps.line(none) and '+10.0 bps' in ps.line(good) and 'OFF' in ps.line(off)
    assert sorted(f['label'] for f in ps.facts([good, off, none], 1)) == ['SOL funding', 'SOL price']


def test_each_parser_reads_its_sources_real_shape():
    import pop_sources as ps
    assert ps._kraken({'result': {'XXBTZUSD': {'c': ['78000.1', '1']}}}, 'BTC')['px'] == 78000.1
    h = ps._hyper([{'universe': [{'name': 'BTC'}, {'name': 'SOL'}]}, [{}, {'markPx': '93.2', 'funding': '0.0000125', 'openInterest': '5'}]], 'SOL')
    assert h['px'] == 93.2 and abs(h['funding'] - 0.01) < 1e-9 and h['oi'] == 5.0
    assert pop.chart_line('SOL', [[3, 1.0, 5.0, 2.0, 4.0, 9], [2, 2.0, 4.0, 2.0, 3.0, 9]]).startswith('SOL chart, last 2 5m closes: 3.00, 4.00') and pop.chart_line('SOL', []) == ''


def test_a_no_trade_folder_says_who_passed_and_why_and_a_missed_pow_says_what_dropped_the_coins():
    calls = [{'name': 'a', 'side': 'long'}, {'name': 'glm', 'why': '{"market": "SOL", "side": "none", "why": "pinned near the top"'}]
    assert pop.no_trade_why('a mind called no trade', calls) == 'glm passed: pinned near the top'
    assert pop.no_trade_why('long SOL vs long BTC', calls) == 'long SOL vs long BTC'
    import pow as pw
    assert 'top 10' in pw.top_reason([{'risk': 'top 10 wallets hold 36%'}, {'risk': 'top 10 wallets hold 41%'}, {'risk': 'no pool'}]) and pw.top_reason([]) == 'no coin could be read'
