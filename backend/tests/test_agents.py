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
    assert ag.weights(lr)['callers'] == -6.0                                       # a prior of +0.5 replaced by what really happened
    w = ag.sherlock({'buy': 70, 'pace': 1.2, 'd5': 1, 'pts': 4, 'liq': 50_000}, {'pc': {'callers': 4}}, lr)
    assert ('callers', -6.0, 'Pump callers piling in') in w['drivers']
    assert lr['bar'] == 1.5                                                        # under 15 Trigger calls → the default bar


def test_the_5_minute_stage_is_conquered_only_on_the_record_and_the_desk_books_it():
    win = [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2, 'p5': 4.0 if i % 3 else -2.0} for i in range(30)]
    s = ag.stage({'done': win})
    assert s['h'] == 15 and s['conquered'] == [5]                                  # 5 min conquered → the desk moves on to 15
    assert ag.stage({'done': win[:20]})['h'] == 5                                  # 20 calls are not enough
    d = ag.paper({'done': win})
    assert d['trades'] == 30 and d['now'] > d['start']
    v = ag.view({'done': win}, [], feed=True)
    assert [a['name'] for a in v['agents']] == ['Tally', 'Sherlock', 'Trigger', 'Devil'] and v['proven5'] and v['feed']
    assert not ag.view({'done': win[:20]}, [], feed=True)['feed']                 # asked for, but not proven → never feeds the card


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
