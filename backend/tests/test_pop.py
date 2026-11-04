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
    assert pow_kernel.fingerprint() == 'e4d4a46f250d', 'A hard limit changed: if it was on purpose, bump pow_kernel.VERSION and this pin.'
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

    async def ask(cat, i, sys_, user_, max_tokens=180):
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
