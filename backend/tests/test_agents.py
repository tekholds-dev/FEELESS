import agents as ag


def row(m, px=1.0, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'price': px, 'vol5m': 20_000, 'vol1h': 80_000, 'buyShare': 64, 'liq': 60_000,
            'ageH': 8, 'chg1h': 30, 'safe': True, 'tv': {'call': ['🔥', 'SEND IT', 'good'], 'rug': 10}, **k}


def test_the_four_are_one_chain_and_go_needs_trigger_and_devil():
    st = {}
    for t in (0, 60, 120):                                                       # Tally needs a few readings before Trigger may call
        st, table = ag.desk(st, [row('GOOD'), row('RUN', tv={'call': ['🎢', 'BOND RUN', 'good'], 'rug': 10}), row('RUG', safe=False)], t)
    by = {x['symbol']: x for x in table}
    g = by['GOOD']
    assert [d[0] for d in g['why']['drivers']][:2] == ['surge', 'buyers'] or set(d[0] for d in g['why']['drivers']) >= {'surge', 'buyers'}
    assert g['trigger'][0] == 'enter' and g['devil'][0] == 'agree' and g['go']
    assert by['RUN']['trigger'][0] == 'enter' and by['RUN']['devil'][0] == 'object' and 'BOND RUN' in by['RUN']['devil'][1] and not by['RUN']['go']
    assert by['RUG']['trigger'][0] == 'skip' and by['RUG']['devil'][0] == '—'
    assert table[0]['symbol'] == 'GOOD'                                           # GO calls first


def test_trigger_never_buys_a_top_a_falling_knife_or_a_thin_pool():
    n = {'d5': 20, 'pts': 5, 'liq': 60_000}
    why = {'lean': 5, 'drivers': []}
    assert ag.trigger(n, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': -12}, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': 2, 'liq': 9000}, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': 2}, why, {}, {})[0] == 'enter'


def test_calls_are_judged_at_5_15_60_and_every_agent_keeps_its_own_card():
    st, table = {}, []
    for t in (0, 60, 120):
        st, table = ag.desk(st, [row('GOOD'), row('RUN', tv={'call': ['🎢', 'BOND RUN', 'good'], 'rug': 10}), row('W', vol5m=1000, buyShare=50)], t)
    st = ag.record(st, table, 120)
    assert set(st['open']) == {'GOOD', 'RUN', 'W'} and st['open']['GOOD']['go'] and st['open']['W']['kind'] == 'wait'
    px = {'GOOD': 1.1, 'RUN': 0.8, 'W': 1.0}
    st = ag.settle(st, lambda m: px.get(m), 120 + 5 * 60)
    assert st['open']['GOOD']['p5'] == 10.0 and st['open']['RUN']['p5'] == -20.0 and 'p15' not in st['open']['GOOD']
    lr = ag.learn(st, 5)
    assert lr['cards']['team']['n'] == 1 and lr['cards']['team']['med'] == 10.0
    assert lr['cards']['devil']['right'] == 100                                    # it objected to RUN (−20%) and agreed to GOOD (+10%)
    assert lr['cards']['trigger']['n'] == 2 and lr['cards']['control']['n'] == 1
    st = ag.settle(st, lambda m: None, 120 + 61 * 60)                              # an hour later every coin vanished
    assert not st['open'] and all(d['p60'] == -100.0 for d in st['done'])


def test_sherlock_learns_what_a_driver_really_did_and_devil_uses_it():
    done = [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': ['callers'], 'lean': 1, 'p5': -6.0} for i in range(10)]
    st = {'done': done}
    lr = ag.learn(st, 5)
    assert lr['drivers']['callers'] == {'n': 10, 'med': -6.0}
    assert ag.weights(lr)['callers'] == round((10 * -6.0 + 8 * 0.5) / 18, 3)        # the belief (+0.5) is outweighed by 10 judged calls (−6%)
    assert ag.learned_share(['callers'], lr) == round(10 / 18, 2) and ag.learned_share(['buyers'], lr) == 0.0
    w = ag.sherlock({'buy': 70, 'pace': 1.2, 'd5': 1, 'pts': 4, 'liq': 50_000}, {'pc': {'callers': 4}}, lr)
    assert ('callers', round((10 * -6.0 + 8 * 0.5) / 18, 2), 'Pump callers piling in') in w['drivers']
    assert lr['bar'] == 1.5                                                        # under 15 Trigger calls → the default bar


def test_5_minutes_is_passed_only_by_10x_ing_the_trench_desk_and_a_bust_starts_over():
    mk = lambda ps: {'done': [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2, 'p5': p} for i, p in enumerate(ps)]}
    steady = mk([4.0 if i % 3 else -2.0 for i in range(30)])                    # a fine record, but nowhere near 10×
    assert ag.stage(steady)['h'] == 5 and ag.paper(steady)['x'] < 1.5
    run = mk([50.0] * 30)                                                        # 25% of the desk in, +50% each → compounds past 10×
    p = ag.paper(run)
    assert p['x'] >= 10 and p['busts'] == 0 and p['trades'] == 30
    assert ag.stage(run)['h'] == 15 and ag.stage(run)['conquered'] == [5]
    assert ag.stage(mk([50.0] * 20))['h'] == 5                                   # 10× on 20 calls: still needs 30 judged
    bust = ag.paper(mk([-100.0] * 11 + [10.0]))
    assert bust['busts'] == 1 and bust['runTrades'] == 1                          # under $1 → busted, a new $20 run
    r = ag.road(steady)
    assert r['paper'] == {'done': False, 'x': ag.paper(steady)['x'], 'need': 10.0, 'n': 30, 'needN': 30} and not r['real']['open'] and 0 <= r['pct'] < 50
    rr = ag.road(run, {'n': 12, 'med': 3.0, 'won': 60})
    assert rr['paper']['done'] and rr['real']['open'] and rr['real']['done'] and rr['pct'] == 100   # paper 10× + the real Fuse card test
    v = ag.view(run, [], feed=True, real={'n': 2, 'med': 1.0})
    assert [a['name'] for a in v['agents']] == ['Tally', 'Sherlock', 'Trigger', 'Devil'] and v['proven5'] and v['feed'] and v['road']['real']['n'] == 2
    assert not ag.view(steady, [], feed=True)['feed']                            # switched on, not proven → never feeds the card


def test_thoughts_and_results_read_as_the_agents_talking():
    st = {}
    for t in (0, 60, 120):
        st, table = ag.desk(st, [row('GOOD'), row('RUN', tv={'call': ['🎢', 'BOND RUN', 'good'], 'rug': 10})], t)
    who = [x['who'] for x in st['feed'][-8:]]
    assert {'tally', 'sherlock', 'trigger', 'devil'} <= set(who)
    assert any('GO' in x['text'] for x in st['feed'] if x['who'] == 'devil') and any('OBJECTS' in x['text'] for x in st['feed'])
    before = ag.record(st, table, 120)
    after = ag.settle(before, lambda m: {'GOOD': 1.2, 'RUN': 0.7}.get(m), 120 + 301)
    lines = {x['sym']: x['text'] for x in ag.results(before, after, 421)}
    assert lines['GOOD'].startswith('✅ $GOOD GO → +20.0%') and 'Devil was right' in lines['RUN']


def test_go_calls_reach_the_real_card_only_when_proven_and_switched_on(monkeypatch):
    import reputation_service as rs
    table = [{'mint': 'M', 'symbol': 'M', 'pair': 'P', 'px': 1.0, 'nums': {'liq': 50_000}, 'why': {'lean': 3}, 'go': True}]
    monkeypatch.setitem(rs._agents, 'table', table)
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows() == []
    monkeypatch.setitem(rs._agents, 'view', {'feed': True})
    r = rs._agents_go_rows()
    assert r[0]['mint'] == 'M' and r[0]['trenchOnly'] and r[0]['tag'] == '🤖 agents GO'
    import arena_prime as ap
    assert ap.clean_cfg({'agentFeed': True})['agentFeed'] is True and ap.clean_cfg({})['agentFeed'] is False


def test_agent_seats_hold_until_profit_then_the_desk_decides():
    agent = lambda m, entry, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'units': 1.0, 'entry': entry, 'bought': {'tag': '🤖 agents GO'}, **k}
    legs = [agent('LOSS', 1.0), agent('RUN', 1.0), agent('FADE', 1.0), agent('GONE', 1.0), {'mint': 'MINE', 'pairAddress': 'PMINE', 'units': 1, 'entry': 1}]
    px = {'PLOSS': 0.6, 'PRUN': 1.3, 'PFADE': 1.25, 'PGONE': 1.2, 'PMINE': 2.0}
    row = lambda m, lean, d5, call='wait', go=False: {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1, 'nums': {'d5': d5, 'buy': 60}, 'why': {'lean': lean}, 'trigger': [call, 'x'], 'go': go}
    table = [row('RUN', 2.0, 3.0), row('FADE', -1.0, -4.0), row('NEW', 3.0, 1.0, 'enter', True)]
    out = {x['symbol']: x for x in ag.manage(legs, table, px, {'agentTakePct': 10, 'agentMode': 'auto'})}
    assert out['LOSS']['action'] == 'hold' and 'until +10%' in out['LOSS']['why']                 # −40%: it stays — agent picks hold until profit
    assert out['RUN']['action'] == 'hold' and 'let it run' in out['RUN']['why']
    assert out['FADE']['action'] == 'swap' and out['FADE']['to']['symbol'] == 'NEW'              # in profit, read turned → swapped for a fresh GO
    assert out['GONE']['action'] == 'pull'                                                       # off the radar → banked, seat left open
    assert 'MINE' not in out                                                                     # never touches coins the agents did not pick
    pull = {x['symbol']: x['action'] for x in ag.manage(legs, table, px, {'agentTakePct': 10, 'agentMode': 'pull'})}
    assert pull['FADE'] == 'pull'


def test_strategies_ideas_and_a_true_opinion():
    r = {'curve': False, 'ageH': 2, 'mind': {}}
    assert 'migration_dip' in ag.strats(r, {'d5': -4, 'buy': 60}) and 'volume_burst' in ag.strats(r, {'d5': 1, 'pace': 3.5, 'buy': 65})
    assert ag.word('strat:migration_dip') == '🎯 first dip after bonding' and ag.PRIOR.get('strat:migration_dip') is None   # no starting belief
    done = [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': ['buyers', 'strat:volume_burst'], 'lean': 2, 'p5': 6.0 if i % 4 else -1.0} for i in range(12)]
    st = ag.ideas({'done': done})
    (iid, idea), = st['ideas'].items()
    assert idea['kind'] == 'take' and idea['status'] == 'new' and 'buyers in charge' in idea['text'] and '12 calls' in idea['text']
    assert ag.ideas(st)['ideas'] == st['ideas']                                                 # never proposed twice
    st = ag.review(st, iid, 'approve')
    lr = ag.learn(st, 5)
    assert lr['approved'] == {iid: ['buyers', 'strat:volume_burst']}
    why = ag.sherlock({'buy': 70, 'pace': 3.5, 'd5': 1, 'pts': 5}, {'curve': None, 'mind': {}}, lr)
    assert f'idea:{iid}' in [d[0] for d in why['drivers']] and 0 < why['learned'] <= 1
    op = ag.opinion(why, 'enter', 'agree', '')
    assert op.startswith("We'd take it") and '% of this read is our own record' in op
    import pytest
    with pytest.raises(ValueError):
        ag.review(st, 'nope', 'approve')
