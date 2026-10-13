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
    assert by['RUN']['trigger'][0] == 'enter' and by['RUN']['devil'][0] == 'agree' and any(w[0] == 'busted_read' for w in by['RUN']['warns'])   # no live record: the old list only WARNS (rank penalty)
    assert by['RUG']['trigger'][0] == 'skip' and by['RUG']['devil'][0] == '—'
    assert table[0]['symbol'] == 'GOOD'                                           # GO calls first


def test_trigger_never_buys_a_top_a_falling_knife_or_a_thin_pool():
    n = {'d5': 20, 'pts': 5, 'liq': 60_000}
    why = {'lean': 5, 'drivers': []}
    assert ag.trigger(n, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': -12}, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': 2, 'liq': 7000}, why, {}, {})[0] == 'skip'
    assert ag.trigger({**n, 'd5': 2}, why, {}, {})[0] == 'enter'


def test_calls_are_judged_at_5_15_60_and_every_agent_keeps_its_own_card():
    st, table = {}, []
    for t in (0, 60, 120):
        st, table = ag.desk(st, [row('GOOD'), row('RUN', tv={'call': ['🎢', 'BOND RUN', 'good'], 'rug': 10}), row('W', vol5m=1000, buyShare=50)], t, None, {'BOND RUN': -82.0})
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
    won = {'value': 60.0, 'putIn': 29.5}   # the REAL card at 2× its put-in: the real-money half of the rule is met in this test
    mk = lambda ps: {'money': won, 'done': [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2, 'p5': p} for i, p in enumerate(ps)]}
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
        st, table = ag.desk(st, [row('GOOD'), row('RUN', tv={'call': ['🎢', 'BOND RUN', 'good'], 'rug': 10})], t, None, {'BOND RUN': -82.0})   # BOND RUN's real record: −82% typical = a hard veto
    who = [x['who'] for x in st['feed'][-8:]]
    assert {'tally', 'sherlock', 'trigger', 'devil'} <= set(who)
    assert any('GO' in x['text'] for x in st['feed'] if x['who'] == 'devil') and any('OBJECTS' in x['text'] for x in st['feed'])
    before = ag.record(st, table, 120)
    after = ag.settle(before, lambda m: {'GOOD': 1.2, 'RUN': 0.7}.get(m), 120 + 301)
    lines = {x['sym']: x['text'] for x in ag.results(before, after, 421) if x['who'] == 'desk'}
    assert lines['GOOD'].startswith('✅ $GOOD GO → +20.0%') and 'Devil was right' in lines['RUN']


def test_go_calls_reach_the_real_card_only_when_proven_and_switched_on(monkeypatch):
    import reputation_service as rs
    from kernel_helpers import row as krow, seed
    seed(monkeypatch, [krow('M')])
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows() == []
    monkeypatch.setitem(rs._agents, 'view', {'feed': True})
    r = rs._agents_go_rows()
    assert r[0]['mint'] == 'M' and r[0]['trenchOnly'] and r[0]['tag'] == '🤖 agents READY'      # the kernel's READY coin (never a paper GO)
    import arena_prime as ap
    assert ap.clean_cfg({'agentFeed': True})['agentFeed'] is True and ap.clean_cfg({})['agentFeed'] is False




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




def test_war_log_and_calibration():
    done = [{'mint': str(i), 'sym': f'C{i}', 'at': 10_000 + i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2.5 if i % 2 else 0.5, 'p5': 5.0 if i % 2 else -2.0} for i in range(8)]
    log, md = ag.war_log({'done': done}, 10_100, 24)
    assert log['go']['n'] == 8 and log['calibration']['2–3']['med'] == 5.0 and log['calibration']['0–1']['med'] == -2.0
    assert md.startswith('# 🤖 Agent desk — war log') and '✅ $C1 +5.0%' in md and 'A record, never a promise' in md




def test_rug_autopsy_teaches_devil_its_rug_signs_and_history_snapshots():
    rugs = [{'mint': f'r{i}', 'sym': f'R{i}', 'at': 100 + i, 'kind': 'enter', 'go': True, 'drivers': ['whale', 'callers', 'src:open'], 'lean': 2, 'p5': -80.0} for i in range(3)]
    fine = [{'mint': f'f{i}', 'sym': f'F{i}', 'at': 200 + i, 'kind': 'enter', 'go': True, 'drivers': (['whale', 'callers'] if i < 5 else ['buyers']) + ['src:open'], 'lean': 2, 'p5': 3.0} for i in range(40)]
    st = ag.autopsy({'done': rugs + fine}, 1000.0)   # 3 of the 8 whale + callers coins rugged (38%) vs 7% of all coins → a real sign
    assert len(st['autopsies']) == 3 and st['rugSigns']['whale'] == 3 and 'src:open' not in st['rugSigns'] and 'fresh' not in ag.rug_lift(rugs + fine) and 'rugged (-80% in 5 min) after a GO' in st['autopsies'][0]['text']
    assert ag.autopsy(st, 1100.0)['rugSigns']['whale'] == 3                                   # each rug is counted once
    v, why = ag.devil('enter', {'pts': 5, 'liq': 50000}, {'drivers': [('whale', 1, 'x'), ('callers', 1, 'y')], 'lean': 3}, {'mint': 'Z', 'safe': True}, ag.learn(st, 5))
    assert v == 'object' and 'rug signs from our autopsies' in why
    h = ag.history({}, 5000.0)
    assert len(h['hist']) == 1 and set(h['hist'][0]) >= {'at', 'tally', 'trigger'}
    assert len(ag.history(h, 5100.0)['hist']) == 1 and len(ag.history(h, 5000.0 + ag.HIST_EVERY)['hist']) == 2
    r = ag.rules(ag.learn({}, 5))
    assert set(r) == {'tally', 'sherlock', 'trigger', 'devil'} and any('bar 1.5' in x for x in r['trigger'])


def test_the_learning_seat_is_one_small_ticket_before_they_are_proven(monkeypatch):
    import reputation_service as rs
    from kernel_helpers import row as krow, seed
    seed(monkeypatch, [krow('A'), krow('B')])
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows([], 2, learn=False) == []                                         # not proven, not learning → nothing
    r = rs._agents_go_rows([], 2, learn=True, learn_pct=10)
    assert len(r) == 1 and r[0]['stakePct'] == 10 and '🎓 learning seat' in r[0]['tag']
    assert rs._agents_go_rows([{'bought': {'tag': '🤖 agents READY · 🎓 learning seat'}}], 2, learn=True) == []   # one learning seat at a time
    assert rs._agents_go_rows([], 2, learn=False) == []


def test_the_agents_seat_defaults_to_a_whole_seat_and_suggestions_taken_are_scored_apart(monkeypatch):
    import reputation_service as rs
    from kernel_helpers import row as krow, seed
    seed(monkeypatch, [krow('A')])
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    assert rs._agents_go_rows([], 2, learn=True)[0]['stakePct'] == 100
    rs._json_save(rs.REAL_LEARN_PATH, {'pieces': [{'k': ['tag:🤝'], 'pct': 12.0}, {'k': ['tag:🤝'], 'pct': -4.0}, {'k': ['tag:🤝'], 'pct': 8.0}, {'k': ['tag:🤖'], 'pct': 3.0}]})
    r = rs._agents_real()
    assert r['n'] == 1 and r['suggested'] == {'n': 3, 'med': 8.0, 'won': 67, 'last': [12.0, -4.0, 8.0]}
    assert ag.road({}, r)['real']['suggested']['n'] == 3


def test_trust_gives_a_second_seat_only_once_taken_suggestions_prove_out(monkeypatch):
    import reputation_service as rs
    from kernel_helpers import row as krow, seed
    seed(monkeypatch, [krow('A'), krow('B')])
    monkeypatch.setitem(rs._agents, 'view', {'feed': False})
    one = [{'bought': {'tag': '🤖 agents READY'}}]
    monkeypatch.setattr(rs, '_agents_real', lambda: {'suggested': {'n': 4, 'med': 9.0}})
    assert rs._agents_go_rows(one, 2, learn=True, trust=True) == []                       # not proven yet → still one seat
    monkeypatch.setattr(rs, '_agents_real', lambda: {'suggested': {'n': 12, 'med': 3.0}})
    assert len(rs._agents_go_rows(one, 2, learn=True, trust=True)) == 1                   # proven → a 2nd seat
    assert rs._agents_go_rows(one, 2, learn=True, trust=False) == []                      # owner switch off → one seat
    seed(monkeypatch, [krow('A', age=0.2)])
    assert rs._agents_go_rows([], 2, learn=True)[0]['ageH'] == 0.2                        # a READY row carries its age → the real card's trench min age applies to the agents too
    assert rs._prime.clean_cfg({})['agentTrust'] is False




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


def test_every_objection_keeps_its_reason_so_we_can_see_what_devil_blocks_and_whether_it_saved_the_desk():
    row = {'mint': 'A', 'symbol': 'A', 'px': 1.0, 'go': False, 'trigger': ['enter', ''], 'devil': ['object', 'rug meter 62'], 'why': {'lean': 2, 'drivers': []}, 'nums': {'d5': 1}}
    st = ag.record({}, [row, {**row, 'mint': 'B', 'devil': ['object', 'rug meter 71']}, {**row, 'mint': 'C', 'go': True, 'devil': ['agree', 'no evidence against it']}], 100)
    assert st['open']['A']['devilWhy'] == 'rug meter 62' and 'devilWhy' not in st['open']['C']
    st['open']['A']['p5'] = -9.0; st['open']['B']['p5'] = 4.0
    o = ag.objections(st, 24, 200)
    assert o == [{'why': 'rug meter #', 'n': 2, 'med': -2.5, 'saved': 50}] and ag.view(st, [], now=200)['objections'][0]['n'] == 2
    assert ag.objections(st, 1, 100 + 7200) == []




def test_they_stay_in_five_minutes_until_the_real_card_is_back_to_breakeven_and_their_lives_ride_on_real_exits():
    mk = lambda ps, **k: {'done': [{'mint': str(i), 'at': i, 'kind': 'enter', 'go': True, 'devil': 'agree', 'drivers': [], 'lean': 2, 'p5': p} for i, p in enumerate(ps)], **k}
    run = mk([50.0] * 30)
    assert ag.stage(run)['h'] == 5 and ag.stage(run)['need2x'] is True                        # paper 10× with NO real money read: paper alone never unlocks a real-money stage
    locked = ag.stage(mk([50.0] * 30, money={'value': 1.35, 'putIn': 29.5}))
    assert locked['h'] == 5 and locked['conquered'] == [] and locked['needBE'] is True        # 10× on paper is NOT enough while the real card is underwater
    grow = ag.stage(mk([50.0] * 30, money={'value': 30, 'putIn': 29.5}))
    assert grow['h'] == 5 and grow['needBE'] is False and grow['need2x'] is True and grow['phase'] == 'GROWTH'   # breakeven is a milestone: still locked on the way to 2×
    assert ag.stage(mk([50.0] * 30, money={'value': 29.5, 'putIn': 29.5}))['phase'] == 'GROWTH' and ag.stage(mk([50.0] * 30, money={'value': 58.99, 'putIn': 29.5}))['h'] == 5
    assert ag.stage(mk([50.0] * 30, money={'value': 59.0, 'putIn': 29.5}))['h'] == 15 and ag.underwater({'money': {'value': 0, 'putIn': 0}}) is False   # real equity ≥ 2× put-in → eligible for the next stage


def test_devils_busted_reads_come_from_the_reads_own_live_records_not_a_fixed_list():
    keys = {'WASH TRADED': 'wash', 'BOND RUN': 'bond', 'TREND DOWN': 'tdown', 'NEW': 'new'}
    proof = {'wash': {'n': 60, 'medPct': -0.2}, 'bond': {'n': 60, 'medPct': -62.1}, 'tdown': {'n': 60, 'medPct': 0.3}, 'new': {'n': 8, 'medPct': -90}}
    assert ag.busted_now(proof, keys) == {'BOND RUN': -62.1} and ag.busted_now({}, keys) is None    # flat reads are not busted · 8 settled is too few to call
    why = {'lean': 3, 'drivers': []}
    row = lambda rd: {'safe': True, 'tv': {'call': ['x', rd], 'rug': 5}, 'mint': 'M'}
    n = {'c1': 5, 'age': 3}
    assert ag.devil('enter', n, why, row('WASH TRADED'), {'busted': {'BOND RUN': -62.1}})[0] == 'agree'      # its record is flat → no objection
    assert ag.devil('enter', n, why, row('BOND RUN'), {'busted': {'BOND RUN': -62.1}})[0] == 'object'       # −62% typical: a safety failure → hard veto
    assert ag.devil('enter', n, why, row('BOND RUN'), {'busted': {'BOND RUN': -25.0}})[0] == 'agree'        # busted but milder: a strong WARNING
    assert ag.devil('enter', n, why, row('WASH TRADED'), {})[0] == 'agree'                           # no live record → the old list only warns
    assert ag.devil('enter', n, why, {**row('WASH TRADED'), 'tv': {'call': ['x', 'WASH TRADED'], 'rug': 62}}, {'busted': set()})[0] == 'object'   # every other check still stands


def test_a_soft_objection_must_be_backed_by_its_own_record():
    why = {'lean': 3, 'drivers': []}
    row = {'safe': True, 'tv': {'call': ['x', 'WATCH'], 'rug': 5}, 'mint': 'M', 'mind': {'bots': (60, ['only 0% of the volume is organic', 'wash-traded volume']), 'crowd': {'swarm': True, 'swarmShare': 0.8}}}
    n = {'c1': 5, 'age': 3}
    one = {**row, 'mind': {'bots': row['mind']['bots']}}
    w = []
    assert ag.devil_args('enter', n, why, one, {'busted': set()}, warns=w) == [] and {x[0] for x in w} == {'botted'}   # one bot signal, no record yet: a WARNING, never a veto
    assert ag.devil('enter', n, why, one, {'busted': set()})[0] == 'agree'
    assert ag.devil('enter', n, why, row, {'busted': set()})[0] == 'object'                                               # a swarm AND a botted launch together: material
    flat = {'busted': set(), 'drivers': {'botted': {'n': 300, 'med': 0.0}, 'swarm': {'n': 40, 'med': 0.4}}}
    assert ag.devil('enter', n, why, row, flat) == ('agree', 'no evidence against it')                                    # 300 judged calls say it is no worse than any coin → waved through
    bad = {'busted': set(), 'drivers': {'botted': {'n': 300, 'med': -4.0}, 'swarm': {'n': 40, 'med': 0.4}}}
    v, arg = ag.devil('enter', n, why, row, bad)
    assert v == 'object' and arg.startswith('botted launch')                                                              # a record that really loses keeps the objection
    assert ag.devil('enter', n, why, {**row, 'tv': {'call': ['x', 'WATCH'], 'rug': 70}}, flat)[0] == 'object'             # hard checks never soften


def test_a_rug_sign_must_beat_the_base_rate_and_old_rugs_are_never_counted_twice():
    call = lambda i, drv, p5: {'mint': f'M{i}', 'at': i, 'kind': 'enter', 'drivers': drv, 'p5': p5, 'sym': f'S{i}'}
    js = [call(i, ['buyers', 'src:open'], -80 if i % 10 == 0 else 2) for i in range(100)] + [call(100 + i, ['buyers', 'drain'], -90) for i in range(5)] + [call(200 + i, ['buyers', 'drain'], 3) for i in range(3)]
    sg = ag.rug_lift(js)
    assert sg == {'drain': 5}                                  # on 5 of its 8 coins' rugs (62%) vs a 14% base → a sign; "buyers" is on every rug only because it is on every coin
    assert ag.rug_lift([]) == {} and ag.rug_lift(js[:2]) == {}
    st = {'done': js}
    a1 = ag.autopsy(st, 1000); a2 = ag.autopsy(a1, 2000); a3 = ag.autopsy(a2, 3000)
    assert a1['rugSigns'] == a2['rugSigns'] == a3['rugSigns'] == {'drain': 5}       # the same record → the same counts, pass after pass
    assert len(a3['autopsies']) == 15 and len({x['id'] for x in a3['autopsies']}) == 15
    many = {'done': [call(i, ['x'], -80) for i in range(90)]}
    b1 = ag.autopsy(many, 1); b2 = ag.autopsy(b1, 2)
    assert [x['id'] for x in b1['autopsies']] == [x['id'] for x in b2['autopsies']] and len(b2['autopsies']) == 60     # the kept 60 do not churn
    assert ag.learn(st)['rugSigns'] == {'drain': 5}


def test_a_duty_case_is_judged_on_the_coin_not_on_triggers_losing_streak():
    why = {'lean': 3, 'drivers': []}; row = {'safe': True, 'tv': {'call': ['x', 'WATCH'], 'rug': 5}, 'mint': 'M'}; n = {'c1': 5, 'age': 3}
    losing = {'busted': set(), 'cards': {'trigger': {'n': 40, 'med': -4.0}}}
    assert ag.devil('enter', n, why, row, losing)[0] == 'object'                       # Trigger's own entry: a STRONG losing record still stops it
    w = []
    assert ag.devil_args('enter', n, why, row, {'busted': set(), 'cards': {'trigger': {'n': 40, 'med': -2.0}}}, warns=w) == [] and w[0][0] == 'trigger_losing'   # a mild one warns
    assert ag.devil('enter', n, why, row, losing, duty=True)[0] == 'agree'             # a duty case: the coin itself is clean
    assert ag.devil('enter', n, why, {**row, 'tv': {'call': ['x', 'WATCH'], 'rug': 80}}, losing, duty=True)[0] == 'object'   # … and a dirty coin never is


def test_the_degen_ideas_are_paper_first_strategies_with_no_starting_belief():
    import meme_terms as mt
    base = {'li': {'phase': 'PRE-FOMO'}, 'mind': {}}
    assert 'base_crowd' in ag.strats(base, {'d5': 1.0, 'buy': 61, 'holdD': 4})
    assert 'base_crowd' not in ag.strats(base, {'d5': 9.0, 'buy': 61, 'holdD': 4})             # already moving = not the base
    assert 'base_crowd' not in ag.strats(base, {'d5': 1.0, 'buy': 61})                          # holders not read = not claimed
    assert 'pro_first_call' in ag.strats({'pros': 1, 'mind': {'crowd': {'callers': 1}}}, {})
    assert 'pro_first_call' not in ag.strats({'pros': 1, 'mind': {'crowd': {'callers': 6}}}, {})  # six callers in = not the first call
    assert ag.strats({'waveRole': 'copy', 'mind': {}}, {}) == ['wave_copycat'] and ag.strats({'waveRole': 'lead', 'mind': {}}, {}) == ['wave_original']
    for k in ('base_crowd', 'pro_first_call', 'wave_original', 'wave_copycat'):
        assert ag.PRIOR.get(f'strat:{k}') is None and ag.word(f'strat:{k}').startswith('🎯')    # record only, never a belief
    trend = [{'kind': 'wave', 'term': 'pepe', 'today': 12, 'coins': []}, {'kind': 'wave', 'term': 'tiny', 'today': 3, 'coins': []}]
    rows = [{'mint': 'A', 'symbol': 'PEPE', 'mcap': 90000, 'ageH': 5}, {'mint': 'B', 'symbol': 'PEPE2', 'name': 'baby pepe', 'mcap': 20000, 'ageH': 1},
            {'mint': 'C', 'symbol': 'DOG', 'mcap': 5000}, {'mint': 'D', 'symbol': 'TINY', 'mcap': 1}, {'mint': 'E', 'symbol': 'TINY', 'mcap': 2}]
    assert mt.wave_roles(trend, rows) == {'A': 'lead', 'B': 'copy'}                               # a 3-coin "wave" is not a wave
