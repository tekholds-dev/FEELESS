import ai_learn as al


def _book(stance_pcts):
    b = {'open': [], 'done': []}
    for st, pcts in stance_pcts.items():
        b['done'] += [{'mint': f'{st}{i}', 'stance': st, 'px': 1.0, 'at': 0, 'pct': p} for i, p in enumerate(pcts)]
    return b


def test_a_stance_is_noted_once_judged_fifteen_minutes_later_and_a_vanished_coin_is_a_total_loss():
    b = al.note(None, 'devil', 'M', 'wait', 2.0, 1000.0, 'AAA')
    b = al.note(b, 'sherlock', 'M', 'WAIT', 2.2, 1100.0)          # the same stance on the same coin inside 30 min: one call
    b = al.note(b, 'devil', 'M', 'AVOID', 2.0, 1100.0)            # a different stance is its own call
    b = al.note(b, 'devil', 'Z', 'ENTER', 0, 1100.0)              # no live price = nothing to judge against
    assert [(c['mint'], c['stance']) for c in b['open']] == [('M', 'WAIT'), ('M', 'AVOID')]
    assert len(al.settle(b, {'M': 3.0}, 1000.0 + al.JUDGE_SEC - 1)['open']) == 2            # not due yet
    s = al.settle(b, {'M': 3.0}, 1100.0 + al.JUDGE_SEC)
    assert not s['open'] and [c['pct'] for c in s['done']] == [50.0, 50.0]
    w = al.settle(b, {}, 1100.0 + al.JUDGE_SEC)                                             # a pass with no price: it waits …
    assert len(w['open']) == 2 and not w['done']
    g = al.settle(b, {}, 1100.0 + al.GONE_SEC)                                              # … an hour with none: gone = −100%
    assert [c['pct'] for c in g['done']] == [-100.0, -100.0] and all(c['gone'] for c in g['done'])


def test_an_unproven_model_weighs_nothing_and_a_proven_stance_moves_the_rank_by_ten_percent_at_most():
    few = al.record(_book({'AVOID': [-30] * 5, 'ENTER': [20] * 5}))
    assert al.factor(few, 'AVOID') == 1.0 and al.factor(few, 'ENTER') == 1.0               # under MIN_N: shown, not used
    rec = al.record(_book({'AVOID': [-30] * 25, 'ENTER': [12] * 25, 'WATCH': [0.5] * 25}))
    assert al.factor(rec, 'AVOID') == al.DOWN == 0.85 and al.factor(rec, 'enter') == al.UP == 1.0 and al.factor(rec, 'WATCH') == 1.0
    assert al.factor(rec, 'HOLD') == 1.0 and al.factor(rec, None) == 1.0 and al.factor(None, 'AVOID') == 1.0
    bear = al.record(_book({'AVOID': [-20] * 25, 'ENTER': [-20] * 25}))                     # everything fell the same: no stance is a proven warning
    assert al.factor(bear, 'AVOID') == 1.0 and al.factor(bear, 'ENTER') == 1.0
    now = 10_000.0
    notes = {'A': {'devil': {'advice': {'stance': 'AVOID'}, 'at': now - 60}, 'sherlock': {'advice': {'stance': 'ENTER'}, 'at': now - 60}},   # two desks: the cautious one counts
             'B': {'sherlock': {'advice': {'stance': 'ENTER'}, 'at': now - 60}}, 'C': {'sherlock': {'advice': {'stance': 'WATCH'}, 'at': now - 60}},
             'OLD': {'devil': {'advice': {'stance': 'AVOID'}, 'at': now - al.FRESH_SEC - 1}}}
    assert al.weights(notes, rec, now) == {'A': 0.85}
    assert al.weights(notes, few, now) == {}
    v = al.view(_book({'AVOID': [-30] * 25, 'ENTER': [12] * 25}))
    assert v['state'] == 'IN USE' and {r['stance']: r['factor'] for r in v['rows']} == {'AVOID': 0.85, 'ENTER': 1.0}
    assert al.view(_book({'AVOID': [-30] * 3}))['state'] == 'LEARNING' and al.view(None)['state'] == 'LEARNING'


def test_the_kernel_rank_takes_the_models_factor_inside_its_bounds_only():
    import opportunity as opp
    row = {'mint': 'M', 'px': 1.0, 'nums': {'d5': 4, 'v5': 5000, 'pace': 2, 'buy': 60}, 'vitals': {'ageH': 0.2, 'mcap': 40000}}
    plain = opp.open_score(row)[0]
    assert opp.open_score(row, ai_w={'M': 0.85})[0] < plain == opp.open_score(row, ai_w={'M': 1.1})[0]   # veto-only: the model never ranks a coin up
    assert opp.open_score(row, ai_w={'M': 0.1})[0] == opp.open_score(row, ai_w={'M': 0.85})[0]     # clamped: never more than 15% down
    assert opp.open_score(row, ai_w={'OTHER': 0.9})[0] == plain
