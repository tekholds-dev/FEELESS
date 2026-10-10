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
    assert r['n'] == 1 and r['suggested'] == {'n': 3, 'med': 8.0, 'won': 67}
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
