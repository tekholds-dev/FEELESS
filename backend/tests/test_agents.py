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
    bust = ag.paper(mk([-100.0] * 18 + [10.0]))                                  # 25% in, then 15% a call after a loss (stake_pct)
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
    lines = {x['sym']: x['text'] for x in ag.results(before, after, 421) if x['who'] == 'desk'}
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
    import pytest
    with pytest.raises(ValueError, match='approve at 15'):
        ag.review(st, iid, 'approve')                                                         # 12 calls: proposed, not approvable yet
    assert not idea['ready']
    more = done + [{**d, 'mint': f'x{d["mint"]}', 'at': 100 + d['at']} for d in done[:4]]       # 16 calls behind it now
    st = ag.ideas({**st, 'done': more})
    assert st['ideas'][iid]['n'] == 16 and st['ideas'][iid]['ready']                            # a waiting idea keeps counting
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


def test_the_crawl_sources_are_learned_and_the_creed_is_engraved():
    assert 'src:ptrend' in ag.drivers({'buy': 60}, {'src': ['open', 'ptrend']}) and ag.word('src:new') == '🕸 found on the newest launches (≤ 1h)'
    assert ag.PRIOR.get('src:ptrend') is None                                                  # no belief about a source — only its record
    assert any('never sign' in c for c in ag.CREED) and any('scrapped' in c for c in ag.CREED) and any('beginning' in c for c in ag.CREED)


def test_an_agent_that_stays_wrong_is_scrapped_and_reborn_with_nothing_but_belief():
    mk = lambda i, up, p: {'mint': str(i), 'at': 1000 + i, 'kind': 'wait', 'go': False, 'devil': '—', 'drivers': ['buyers'], 'lean': -1, 'tallyUp': up, 'p5': p}   # Sherlock leaned down and was right
    wrong = [mk(i, True, -2.0) for i in range(40)]                                              # Tally said "keeps going", it fell — 40 times
    assert ag.survival({'done': wrong})['tally']['status'] == 'probation'
    st = {'done': wrong + [mk(100 + i, True, -2.0) for i in range(25)]}
    assert ag.survival(st)['tally']['status'] == 'scrap'
    st2, dead = ag.evolve(st, 5000.0)
    assert 'tally' in dead and st2['gen']['tally'] == 2 and st2['born']['tally'] == 5000.0
    assert st2['lineage'][-1]['agent'] == 'tally' and st2['lineage'][-1]['n'] == 65
    assert ag.survival(st2)['tally'] == {'gen': 2, 'born': 5000.0, 'n': 0, 'right': None, 'med': None, 'status': 'alive'}   # a fresh life
    assert 'reborn as generation 2' in st2['feed'][-1]['text']
    assert ag.learn(st2)['drivers'].get('buyers', {}).get('n') == 65                           # Sherlock is alive: it keeps its own record


def test_the_live_desk_uses_its_own_record_regime_and_burned_memory():
    # Sherlock's record says 'buyers in charge' LOST over 20 calls → the live desk must weigh it negative (it used to ignore the record)
    done = [{'mint': f'd{i}', 'at': i, 'kind': 'wait', 'drivers': ['buyers', 'surge'], 'lean': 1, 'p5': -8.0} for i in range(20)]
    st = {'done': done}
    for t in (100, 160, 220):
        st, table = ag.desk(st, [row('GOOD')], t)
    g = {d[0]: d[1] for d in table[0]['why']['drivers']}
    assert g['buyers'] < 0 and g['surge'] < 0 and table[0]['trigger'][0] != 'enter'      # learned → no ENTER
    assert set(st['perf']) >= {'tally', 'sherlock', 'trigger', 'devil', 'coins', 'regime'} and st['perf']['coins'] == 1
    assert ag.regime({str(i): {'d5': -1} for i in range(12)})['adj'] == 0.5 and ag.regime({'a': {'d5': 1}})['word'] == 'unknown'
    burnt = ag.burn({'done': [{'mint': 'R', 'at': 1000.0, 'go': True, 'p5': -35.0}]}, 1500.0)
    assert 'R' in burnt['burned']
    lr = {**ag.learn({}, 5), 'burned': burnt['burned']}
    v, why = ag.devil('enter', {'pts': 5, 'liq': 50000}, {'drivers': [], 'lean': 3}, {'mint': 'R', 'safe': True}, lr)
    assert v == 'object' and 'burned us' in why


def test_a_rug_gets_one_second_opinion_and_a_death_passes_its_lesson_on():
    mk = lambda i, p: {'mint': str(i), 'at': 1000 + i, 'kind': 'wait', 'drivers': ['callers'], 'lean': -1, 'tallyUp': True, 'p5': p}
    one_rug = [mk(i, -0.1) for i in range(64)] + [mk(99, -95.0)]                          # 65 wrong calls, but one rug is most of the loss
    st, dead = ag.evolve({'done': one_rug}, 5000.0)
    assert dead == [] and st['grace']['tally'] == 1 and 'spared once' in st['feed'][-1]['text']
    st2, dead2 = ag.evolve(st, 5100.0)                                                      # same generation: no second grace
    assert dead2 == ['tally'] and st2['gen']['tally'] == 2 and 'I carry what killed it' in st2['feed'][-1]['text']
    spread = [mk(i, -3.0) for i in range(65)]
    st3, dead3 = ag.evolve({'done': spread}, 5000.0)
    assert dead3 == ['tally'] and 'spread over' in st3['lineage'][-1]['why']
    les = ag.lesson({'done': [{**mk(i, -6.0), 'kind': 'enter', 'drivers': ['callers']} for i in range(10)]}, 'sherlock')
    assert les['drivers'][0][0] == 'callers' and les['drivers'][0][1] == -6.0
    w = ag.weights({'drivers': {}, 'lessons': {'sherlock': les}})
    assert w['callers'] == -6.0                                                             # the reborn Sherlock starts from what killed the last
    assert ag.lesson({}, 'trigger')['barBump'] == 0.5


def test_war_log_and_calibration():
    done = [{'mint': str(i), 'sym': f'C{i}', 'at': 10_000 + i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2.5 if i % 2 else 0.5, 'p5': 5.0 if i % 2 else -2.0} for i in range(8)]
    log, md = ag.war_log({'done': done}, 10_100, 24)
    assert log['go']['n'] == 8 and log['calibration']['2–3']['med'] == 5.0 and log['calibration']['0–1']['med'] == -2.0
    assert md.startswith('# 🤖 Agent desk — war log') and '✅ $C1 +5.0%' in md and 'A record, never a promise' in md


def test_an_agent_coin_whose_pool_drains_is_pulled_at_once_even_at_a_loss():
    legs = [{'mint': 'D', 'pairAddress': 'PD', 'symbol': 'D', 'units': 1.0, 'entry': 1.0, 'liq': 60_000, 'liqNow': 20_000, 'bought': {'tag': '🤖 agents GO'}}]
    out = ag.manage(legs, [], {'PD': 0.7}, {'agentTakePct': 10})
    assert out[0]['action'] == 'pull' and 'pool fell to 33%' in out[0]['why']


def test_rug_autopsy_teaches_devil_its_rug_signs_and_history_snapshots():
    rugs = [{'mint': f'r{i}', 'sym': f'R{i}', 'at': 100 + i, 'kind': 'enter', 'go': True, 'drivers': ['fresh', 'callers', 'src:open'], 'lean': 2, 'p5': -80.0} for i in range(3)]
    st = ag.autopsy({'done': rugs}, 1000.0)
    assert len(st['autopsies']) == 3 and st['rugSigns']['fresh'] == 3 and 'rugged (-80% in 5 min) after a GO' in st['autopsies'][0]['text']
    assert ag.autopsy(st, 1100.0)['rugSigns']['fresh'] == 3                                   # each rug is counted once
    v, why = ag.devil('enter', {'pts': 5, 'liq': 50000}, {'drivers': [('fresh', 1, 'x'), ('callers', 1, 'y')], 'lean': 3}, {'mint': 'Z', 'safe': True}, ag.learn(st, 5))
    assert v == 'object' and 'rug signs from our autopsies' in why
    h = ag.history({}, 5000.0)
    assert len(h['hist']) == 1 and set(h['hist'][0]) >= {'at', 'tally', 'trigger'}
    assert len(ag.history(h, 5100.0)['hist']) == 1 and len(ag.history(h, 5000.0 + ag.HIST_EVERY)['hist']) == 2
    r = ag.rules(ag.learn({}, 5))
    assert set(r) == {'tally', 'sherlock', 'trigger', 'devil'} and any('bar 1.5' in x for x in r['trigger'])


def test_the_learning_seat_is_one_small_ticket_before_they_are_proven(monkeypatch):
    import reputation_service as rs
    table = [{'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'nums': {'liq': 50_000}, 'why': {'lean': 3}, 'go': True} for m in ('A', 'B')]
    monkeypatch.setitem(rs._agents, 'table', table)
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows([], 2, learn=False) == []                                         # not proven, not learning → nothing
    r = rs._agents_go_rows([], 2, learn=True, learn_pct=10)
    assert len(r) == 1 and r[0]['stakePct'] == 10 and '🎓 learning seat' in r[0]['tag']
    assert rs._agents_go_rows([{'bought': {'tag': '🤖 agents GO · 🎓 learning seat'}}], 2, learn=True) == []   # one learning seat at a time
    assert rs._agents_go_rows([], 2, learn=False) == []


def test_the_agents_seat_defaults_to_a_whole_seat_and_suggestions_taken_are_scored_apart(monkeypatch):
    import reputation_service as rs
    table = [{'mint': 'A', 'symbol': 'A', 'pair': 'PA', 'px': 1.0, 'nums': {'liq': 50_000}, 'why': {'lean': 3}, 'go': True}]
    monkeypatch.setitem(rs._agents, 'table', table)
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows([], 2, learn=True)[0]['stakePct'] == 100
    rs._json_save(rs.REAL_LEARN_PATH, {'pieces': [{'k': ['tag:🤝'], 'pct': 12.0}, {'k': ['tag:🤝'], 'pct': -4.0}, {'k': ['tag:🤝'], 'pct': 8.0}, {'k': ['tag:🤖'], 'pct': 3.0}]})
    r = rs._agents_real()
    assert r['n'] == 1 and r['suggested'] == {'n': 3, 'med': 8.0, 'won': 67, 'last': [12.0, -4.0, 8.0]}
    assert ag.road({}, r)['real']['suggested']['n'] == 3


def test_trust_gives_a_second_seat_only_once_taken_suggestions_prove_out(monkeypatch):
    import reputation_service as rs
    table = [{'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'nums': {'liq': 50_000}, 'why': {'lean': 3}, 'go': True} for m in ('A', 'B')]
    monkeypatch.setitem(rs._agents, 'table', table)
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    one = [{'bought': {'tag': '🤖 agents GO'}}]
    monkeypatch.setattr(rs, '_agents_real', lambda: {'suggested': {'n': 4, 'med': 9.0}})
    assert rs._agents_go_rows(one, 2, learn=True, trust=True) == []                       # not proven yet → still one seat
    monkeypatch.setattr(rs, '_agents_real', lambda: {'suggested': {'n': 12, 'med': 3.0}})
    assert len(rs._agents_go_rows(one, 2, learn=True, trust=True)) == 1                   # proven → a 2nd seat
    assert rs._agents_go_rows(one, 2, learn=True, trust=False) == []                      # owner switch off → one seat
    monkeypatch.setitem(rs._agents, 'table', [{**table[0], 'vitals': {'ageH': 0.2}}])
    assert rs._agents_go_rows([], 2, learn=True)[0]['ageH'] == 0.2                        # a GO row carries its age → the real card's trench min age applies to the agents too
    assert rs._prime.clean_cfg({})['agentTrust'] is False


def test_growth_levels_only_while_alive_power_mirrors_the_seat_rule_and_the_card_reads_as_seats():
    # XP = calls judged this life; a level is HELD only while alive (probation stunts it back to a hatchling)
    st = {'gen': {'sherlock': 2}, 'lessons': {'sherlock': {'words': ['Pump callers piling in (-6%)']}}, 'lineage': [{'agent': 'sherlock', 'gen': 1}],
          'ideas': {'i1': {'status': 'approved', 'kind': 'avoid', 'pair': ['swarm', 'surge']}, 'i2': {'status': 'new', 'kind': 'take', 'pair': ['buyers', 'surge']}}}
    g = ag.growth(st)
    assert g['tally']['name'] == 'Egg' and g['tally']['xp'] == 0 and g['tally']['next'] == 10 and g['tally']['pct'] == 0
    assert g['sherlock']['gen'] == 2 and g['sherlock']['genes'] == ['Pump callers piling in (-6%)'] and g['sherlock']['scars'] == 1
    assert len(g['devil']['skills']) == 1 and g['sherlock']['skills'] == []          # only APPROVED ideas are skills; avoid → Devil
    assert [lv[0] for lv in ag.LEVELS][2:4] == [ag.SURVIVE_N, ag.SCRAP_N]             # levels sit on the lines a life is already judged on
    # 🪜 power = the same rule the real card buys by
    assert ag.seat_limit({}, False, {}) == 0 and ag.seat_limit({'agentLearn': True}, False, {}) == 1
    good = {'suggested': {'n': 12, 'med': 3.0}}
    assert ag.seat_limit({'agentLearn': True, 'agentTrust': True}, False, {'suggested': {'n': 4, 'med': 9}}) == 1
    assert ag.seat_limit({'agentLearn': True, 'agentTrust': True}, False, good) == 2 and ag.seat_limit({'agentLearn': True}, False, good) == 1
    assert ag.seat_limit({'agentFeed': True, 'agentSeats': 3, 'agentLearn': True}, True, {}) == 3 and ag.seat_limit({'agentFeed': True, 'agentSeats': 3}, False, {}) == 0
    card = {'tpl': 'degen', 'legs': [
        {'symbol': 'BOT', 'pairAddress': 'P1', 'mint': 'M1', 'entry': 1.0, 'bought': {'tag': '🤖 agents GO · 🎓 learning seat'}},
        {'symbol': 'SUG', 'pairAddress': 'P2', 'mint': 'M2', 'entry': 2.0, 'picked': True, 'bought': {'tag': '🤝 agents suggested · your pick'}},
        {'symbol': 'MINE', 'pairAddress': 'P3', 'mint': 'M3', 'entry': 1.0, 'picked': True}, {'symbol': 'ENG', 'pairAddress': 'P4', 'mint': 'M4', 'entry': 1.0, 'bought': {'tag': '🌊 volume'}}]}
    cs = ag.card_seats(card, [{'pair': 'P1', 'action': 'hold', 'why': '+4.0% — holding until +10%'}], {'P1': 1.04, 'P2': 1.0, 'P4': 0}, {'agentTakePct': 10, 'coins': 5})
    assert [x['kind'] for x in cs['seats']] == ['agent', 'suggested', 'yours', 'engine', 'open']       # the owner's 5th seat is open
    assert cs['seats'][0]['pct'] == 4.0 and cs['seats'][0]['take'] == 10 and cs['seats'][0]['action'] == 'hold' and cs['seats'][1]['pct'] == -50.0
    assert cs['seats'][2]['pct'] is None and cs['seats'][3]['pct'] is None and 'action' not in cs['seats'][2]   # no price = no number, never a fake 0%
    pw = ag.power({}, good, {'agentLearn': True, 'agentTrust': True, 'agentSeats': 3}, cs)
    assert pw['seats'] == 2 and pw['held'] == 1 and [x['done'] for x in pw['steps']] == [True, True, False] and pw['steps'][1]['pct'] == 100
    v = ag.view({}, [], card=cs)
    assert v['card']['seats'][0]['symbol'] == 'BOT' and set(v['growth']) == {'tally', 'sherlock', 'trigger', 'devil'} and v['power']['seats'] == 0


def test_the_judge_rules_five_minutes_later_names_one_bot_and_a_trial_only_ever_tightens():
    call = lambda **k: {'kind': 'enter', 'go': True, 'devil': 'agree', 'lean': 1.6, 'tallyUp': False, 'sym': 'X', **k}
    assert ag.ruling(call(p5=8, lean=2.5)) == {'verdict': 'win', 'credit': 'sherlock', 'blame': None, 'kind': 'go'}        # a strong read that won
    assert ag.ruling(call(p5=8, tallyUp=True))['credit'] == 'tally' and ag.ruling(call(p5=8))['credit'] == 'trigger'
    assert ag.ruling(call(p5=-30, lean=2.5))['blame'] == 'devil'                                                            # a dump: the gate failed
    assert ag.ruling(call(p5=-6, lean=2.5))['blame'] == 'sherlock' and ag.ruling(call(p5=-6))['blame'] == 'trigger'
    assert ag.ruling(call(p5=1))['verdict'] == 'push'                                                                       # ±3% is no ruling
    obj = lambda p: ag.ruling(call(p5=p, go=False, devil='object'))
    assert (obj(-9)['credit'], obj(-9)['blame']) == ('devil', 'trigger') and (obj(9)['credit'], obj(9)['blame']) == ('trigger', 'devil')
    assert ag.ruling({'kind': 'wait', 'p5': 14})['blame'] == 'trigger' and ag.ruling({'kind': 'wait', 'p5': 4})['verdict'] == 'push'
    assert ag.ruling({'kind': 'wait', 'p5': 14})['verdict'] == 'miss'
    missy = ag.judge({'done': [{'kind': 'wait', 'p5': 40, 'mint': f'W{i}', 'at': i, 'sym': 'W'} for i in range(6)]})
    assert missy['missed'] == 6 and missy['trial'] is None and missy['score']['trigger']['net'] == 0      # missed runners never put a bot on trial
    # three thin-lean GO losses → Trigger is ON TRIAL with a handicap; nobody is crowned on a losing book
    st = {'done': [{**call(p5=-6), 'mint': f'M{i}', 'at': i} for i in range(3)]}
    j = ag.judge(st)
    assert j['trial'] == 'trigger' and j['handicap'] == 'bar +0.5' and j['mvp'] is None and j['losses'] == 3 and j['score']['trigger']['net'] == -3
    assert ag.bar_now({'bar': 1.5, 'trial': 'trigger'}) == 2.0 and ag.bar_now({'bar': 1.5}) == 1.5                         # the trial only tightens
    assert ag.bar_now({'bar': 1.5, 'dial': 'crazy'}) == 1.0 and ag.bar_now({'bar': 1.5, 'dial': 'chill'}) == 2.0 and ag.bar_now({'bar': 1.0, 'dial': 'crazy'}) == ag.BAR_FLOOR
    assert ag.trigger({'pts': 4, 'buy': 60}, {'lean': 3, 'drivers': []}, {'safe': True}, {'trial': 'tally'})[0] == 'wait'  # Tally on trial: 5 readings
    assert ag.trigger({'pts': 4, 'buy': 60}, {'lean': 3, 'drivers': []}, {'safe': True}, {})[0] == 'enter'
    assert ag.trigger({'pts': 9, 'buy': 60, 'd5': 22}, {'lean': 9, 'drivers': []}, {'safe': True}, {'dial': 'crazy'})[0] == 'skip'   # crazy never lifts a hard SKIP
    good = {'done': [{**call(p5=9, lean=2.6), 'mint': f'G{i}', 'at': i} for i in range(3)]}
    assert ag.judge(good)['mvp'] == 'sherlock' and ag.judge(good)['trial'] is None and ag.judge({})['n'] == 0
    out = ag.results({'open': {'A': {'kind': 'enter', 'go': True, 'sym': 'A', 'lean': 1}}}, {'open': {'A': {'kind': 'enter', 'go': True, 'sym': 'A', 'lean': 1, 'p5': -7.0}}}, 5)
    assert [x['who'] for x in out] == ['desk', 'judge'] and 'Trigger takes the L' in out[1]['text']


def test_the_paper_desk_presses_winners_cuts_after_a_loss_and_proof_counts_wins_and_losses():
    assert [ag.stake_pct(k) for k in (-2, -1, 0, 1, 2, 3, 7)] == [15.0, 15.0, 25.0, 25.0, 35.0, 45.0, 45.0]
    go = lambda i, p: {'kind': 'enter', 'go': True, 'sym': f'S{i}', 'mint': f'M{i}', 'at': i, 'p5': p}
    st = {'done': [go(0, 10), go(1, 10), go(2, 10), go(3, -10), go(4, 10)]}
    pp = ag.paper(st)
    assert [t['stake'] for t in pp['trail']] == [25.0, 25.0, 35.0, 45.0, 15.0]          # even · even · 2 wins · 3 wins · right after the loss
    assert round(pp['now'], 2) == round(20 * 1.025 * 1.025 * 1.035 * 0.955 * 1.015, 2) and pp['streak'] == 1 and pp['heat'] == 'even'
    pr = ag.proof(st, {'last': [4.0, -2.0], 'suggested': {'last': [9.0]}})
    assert (pr['paper']['w'], pr['paper']['l'], pr['paper']['best'], pr['paper']['last'][0], pr['paper']['syms'][0]) == (4, 1, 10.0, 10.0, 'S4')
    assert (pr['card']['w'], pr['card']['l'], pr['card']['last']) == (1, 1, [-2.0, 4.0]) and pr['suggested']['n'] == 1 and ag.proof({})['card']['n'] == 0
    v = ag.view(st, [], cfg={'agentDial': 'crazy'})
    assert v['cfg']['agentDial'] == 'crazy' and v['judge']['wins'] == 4 and v['proof']['paper']['n'] == 5 and v['desk']['stake'] == 25.0
    import arena_prime as ap
    assert ap.clean_cfg({'agentDial': 'crazy'})['agentDial'] == 'crazy' and ap.clean_cfg({'agentDial': 'yolo'})['agentDial'] == 'normal'


def test_they_learn_to_scalp_from_their_own_paths_without_look_ahead_and_the_real_seat_banks_at_the_learned_line():
    # the exit: the take line at the first reading at / above it (booked AT the line), the stop at what was SEEN, else the 5-min price
    assert ag.scalp_exit([3, 9, -4], -6.0, 8, 5) == 8.0 and ag.scalp_exit([2, -11, 30], 25.0, 20, 8) == -11.0 and ag.scalp_exit([1, 2], 4.0, 8, 0) == 4.0
    # 5-minute paths that spike then fade: holding loses, taking +8% wins
    spike = lambda i: {'kind': 'enter', 'go': True, 'sym': f'S{i}', 'mint': f'M{i}', 'at': i * 400, 'px': 1.0, 'path': [4, 9, 3, -2, -5], 'p5': -5.0, 'lean': 2}
    st = {'done': [spike(i) for i in range(20)]}
    sp = ag.scalp_plan(st)
    assert sp['n'] == 20 and sp['flat']['avg'] == -5.0 and sp['best']['tp'] == 8 and sp['best']['avg'] == 8.0 and sp['proven'] and sp['peak'] == 9.0
    assert not ag.scalp_plan({'done': st['done'][:19]})['proven']                              # 19 paths: not yet
    assert ag.paper(st)['x'] < 1                                                               # those calls were made BEFORE the plan → graded flat
    st = ag.scalp_adopt(st, 9000)
    assert st['scalp']['tp'] == 8 and st['scalp']['at'] == 9000
    row = {'mint': 'NEW', 'symbol': 'NEW', 'px': 1.0, 'go': True, 'trigger': ['enter', ''], 'devil': ['agree', ''], 'why': {'lean': 2, 'drivers': []}, 'nums': {'d5': 1}}
    st = ag.record(st, [row], 9100)
    assert st['open']['NEW']['scalp'] == [8, st['scalp']['sl']]                                # only calls made AFTER adoption carry the plan
    prices = iter([1.04, 1.09, 1.03, 0.98, 0.95, 0.95])
    for k in range(6):
        st = ag.settle(st, lambda m, p=next(prices): p if m == 'NEW' else None, 9100 + 60 * (k + 1))
    new = st['open']['NEW']
    assert new['path'][:2] == [4.0, 9.0] and new['p5'] == -5.0
    assert ag.paper(st)['trail'][-1]['pct'] == 8.0 and ag.paper(st)['trail'][-1]['scalp'] is True   # the paper desk banks it at +8
    assert 'scalp' not in ag.scalp_adopt({'scalp': {'tp': 8, 'sl': 0}}, 1)                     # a plan that is no longer proven is dropped
    # the real agent seat: banks AT the learned line (swap into the next GO, else cash) — the creator's take line when no plan / switched off
    leg = {'symbol': 'BOT', 'pairAddress': 'P1', 'mint': 'B', 'units': 1, 'entry': 1.0, 'bought': {'tag': '🤖 agents GO'}}
    cfg = {'agentTakePct': 50, 'agentMode': 'auto'}
    assert ag.manage([leg], [], {'P1': 1.10}, cfg)[0]['action'] == 'hold'
    d = ag.manage([leg], [{**row, 'pair': 'PN'}], {'P1': 1.10}, cfg, {'tp': 8, 'sl': 0})[0]
    assert d['action'] == 'swap' and d['to']['symbol'] == 'NEW' and 'scalp' in d['why']
    assert ag.manage([leg], [], {'P1': 1.10}, cfg, {'tp': 8})[0]['action'] == 'pull'
    assert ag.manage([leg], [], {'P1': 1.05}, cfg, {'tp': 8})[0]['action'] == 'hold'           # under the line: still held, never stopped
    assert ag.manage([leg], [], {'P1': 1.10}, {**cfg, 'agentScalp': False}, {'tp': 8})[0]['action'] == 'hold'
    # 🎯 the mission: breakeven first — a distance, never a promise
    m = ag.mission(0.81, 22.5, {'x': 1.0}, st['scalp'])
    assert m == {'key': 'breakeven', 'value': 0.81, 'putIn': 22.5, 'pct': 3.6, 'needX': 27.8, 'scalping': True}
    assert ag.mission(30, 22.5, {'x': 2.0})['key'] == 'tenx' and ag.mission(0, 0, {'x': 2.0})['needX'] == 5.0
    v = ag.view(st, [], money={'value': 0.81, 'putIn': 22.5})
    assert v['mission']['key'] == 'breakeven' and v['scalp']['live']['tp'] == 8 and v['cfg']['agentScalp'] is True
    import arena_prime as ap
    assert ap.clean_cfg({})['agentScalp'] is True and ap.clean_cfg({'agentScalp': False})['agentScalp'] is False


def test_in_control_they_buy_only_eligible_go_coins_switch_a_broken_read_after_15_min_and_stay_inside_the_hourly_budget():
    row = lambda m, go=True, lean=2.0, age=3.0, liq=60_000, safe=True, trig='enter', d5=1.0, buy=60: {
        'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'go': go, 'trigger': [trig, 'why'], 'devil': ['agree' if go else 'object', ''],
        'why': {'lean': lean, 'drivers': []}, 'nums': {'d5': d5, 'buy': buy, 'liq': liq}, 'vitals': {'ageH': age, 'safe': safe, 'liq': liq}}
    table = [row('GOOD', lean=3), row('YOUNG', age=0.2), row('NOAGE', age=None), row('THIN', liq=9_000), row('UNSCAN', safe=None), row('NOGO', go=False), row('HELD'), row('OK2', lean=2.5)]
    assert [x['mint'] for x in ag.eligible(table, {'HELD'}, 1.0)] == ['GOOD', 'OK2']                 # minutes-old / unknown age / thin pool / unscanned / objected / on the card: all out
    assert [x['mint'] for x in ag.eligible(table, set(), 1.0, burned={'GOOD'})] == ['OK2', 'HELD']
    leg = lambda m, at=0, **k: {'symbol': m, 'pairAddress': 'P' + m, 'mint': m, 'units': 1, 'entry': 1.0, 'at': at, **k}
    cfg = {'agentTakePct': 20, 'agentMode': 'auto', 'trenchMinAgeH': 1}
    now = 3600
    broke = row('MINE', go=False, lean=-1.0, trig='wait')
    legs = [leg('MINE', at=now - 20 * 60), leg('FRESH', at=now - 5 * 60), leg('ICE', at=0, frozen=True)]
    d = {x['symbol']: x for x in ag.manage(legs, table + [broke], {'PMINE': 0.9, 'PFRESH': 0.9, 'PICE': 0.5}, cfg, control=True, now=now, moves_left=4)}
    assert d['MINE']['action'] == 'swap' and d['MINE']['to']['mint'] == 'GOOD' and 'lean turned' in d['MINE']['why']    # your coin, broken read, 20 min held → switched
    assert d['FRESH']['action'] == 'hold' and 'ICE' not in d                                                            # 5 min held: never · your ❄ frozen coin: never theirs
    assert ag.manage(legs[:1], table + [broke], {'PMINE': 0.9}, cfg, control=True, now=now, moves_left=0)[0]['action'] == 'hold'   # hourly budget spent → no switch
    assert ag.manage(legs[:1], table + [broke], {'PMINE': 0.9}, cfg)  == []                                             # not in control: your coin is not theirs to manage
    assert ag.manage(legs[:1], [broke, row('YOUNG', age=0.2)], {'PMINE': 0.9}, cfg, control=True, now=now, moves_left=4)[0]['action'] == 'hold'   # nothing eligible → never to cash at a loss
    won = ag.manage([leg('MINE', at=now - 60)], table, {'PMINE': 1.3}, cfg, {'tp': 8, 'sl': 0}, control=True, now=now, moves_left=4)[0]
    assert won['action'] == 'swap' and 'scalp' in won['why']                                                            # at the take line they bank it into the next GO
    assert ag.seat_limit({'agentControl': True, 'coins': 4}, False, {}) == 4 and ag.view({}, [], cfg={'agentControl': True})['cfg']['agentControl'] is True
    assert ag.CONTROL_HOLD_MIN == 15 and ag.CONTROL_MOVES_HR == 4


def test_agent_control_holds_the_card_for_the_agents_the_proof_gate_stands_aside_and_a_manual_release_hands_it_back(monkeypatch):
    import asyncio, reputation_service as rs
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: None); monkeypatch.setattr(rs, '_owner_wallets', lambda: [])
    base = lambda **c: rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'realCfg': rs._prime.clean_cfg({'proofGate': True}), 'cards': {'degen': {'real': True, 'events': [], **c}, 'safe': {'events': []}}}})
    get = lambda: rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    base(holdAll=True, holdBy='proof')
    asyncio.run(rs._agent_control_set(True, 100))
    p = get()
    assert p['realCfg']['agentControl'] is True and p['cards']['degen']['holdBy'] == 'agents' and p['cards']['degen']['holdAll'] is True and not p['cards']['safe'].get('holdAll')
    rs._json_save(rs.BRAIN_PATH, {'done': [{'at': i, 'f': ['age:<15m'], 'end': -60.0} for i in range(600)]}); rs._json_save(rs.AGENTS_PATH, {'done': []})
    asyncio.run(rs._proof_gate_tick(200))
    assert get()['cards']['degen']['holdBy'] == 'agents'                                    # the gate does not take the card back from them
    asyncio.run(rs._agent_control_set(False, 300))
    p = get()
    assert p['realCfg']['agentControl'] is False and not p['cards']['degen'].get('holdAll') and 'holdBy' not in p['cards']['degen']
    asyncio.run(rs._proof_gate_tick(400))
    assert get()['cards']['degen']['holdBy'] == 'proof'                                     # control off → the proof gate judges the card again
    base(holdAll=True)                                                                      # the owner's OWN hold: agent control never takes it over
    asyncio.run(rs._agent_control_set(True, 500))
    assert 'holdBy' not in get()['cards']['degen'] and get()['cards']['degen']['holdAll'] is True
