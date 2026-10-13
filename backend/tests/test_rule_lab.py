"""🧪 The rule lab: the model proposes in our own words, the real record decides; live rules become the desks' lessons."""
import rule_lab as L
from trench_kernel import brain


def _trade(i, pct, struct='UPTREND', flow=None, dist=None, age=2.0):
    th = {'structure': struct, 'triggerRule': 'E9 pullback recovered'}
    if flow:
        th['flow'] = {'state': flow}
    if dist is not None:
        th['distHigh'] = dist
    return {'confirmed': True, 'realPct': pct, 'closedAt': 1000 + i, 'thesis': th, 'launch': {'ageH': age}, 'li': {}, 'tag': '🤖 agents · ⚡ READY (kernel)'}


def _record():
    """40 trades: every coin bought into SELLERS lost ~12%, the rest made ~+2% — in both halves of time."""
    return [_trade(i, -12.0 if i % 3 == 0 else 2.0, flow='SELLERS' if i % 3 == 0 else 'BUYERS') for i in range(40)]


def test_a_proposal_may_only_use_words_from_our_own_record():
    v = L.vocab(_record())
    assert 'flow:SELLERS' in v and v['flow:SELLERS']['med'] == -12.0
    ok = L.clean([{'act': 'avoid', 'when': ['flow:SELLERS'], 'name': 'buying into sellers'},
                  {'act': 'avoid', 'when': ['moon:soon'], 'name': 'made up'},                 # a word we never recorded → dropped
                  {'act': 'yolo', 'when': ['flow:SELLERS']},                                  # not an act → dropped
                  {'act': 'avoid', 'when': ['flow:SELLERS', 'struct:UPTREND', 'age:<6h']}], v)   # 3 words → dropped
    assert [r['id'] for r in ok] == ['avoid:flow:SELLERS'] and ok[0]['desk'] == 'trigger'


def test_walk_forward_takes_a_rule_live_and_its_lesson_reaches_trigger_and_the_rank():
    t = _record()
    st, went = L.step({}, L.clean([{'act': 'avoid', 'when': ['flow:SELLERS'], 'name': 'into sellers'}], L.vocab(t)), t, 5000)
    r = st['rules'][0]
    assert r['status'] == 'live' and r['door'] == 'walk-forward' and went and r['replay']['test']['avg'] < r['replay']['test']['rest']
    assert L.weight(st, ['flow:SELLERS', 'struct:UPTREND']) == L.AVOID_F and L.weight(st, ['flow:BUYERS']) == 1.0
    lessons = L.trigger_lessons(st)
    assert lessons and lessons[0]['when'] == ['flow:SELLERS'] and L.lessons(st)['trigger']
    # the brain: a coin Trigger would ENTER on, whose live tape is SELLERS, is armed by the lesson (the flow rule arms it already — use a high-band rule)
    st2, _ = L.step({}, [{'id': 'avoid:high:top', 'act': 'avoid', 'when': ['high:top'], 'name': 'top tick', 'desk': 'trigger', 'why': ''}],
                    [_trade(i, -10.0 if i % 2 else 3.0, dist=1.0 if i % 2 else 12.0) for i in range(40)], 5000)
    assert st2['rules'][0]['status'] == 'live'
    row = {'mint': 'M', 'chart': {'state': 'UPTREND', 'f': {'distHigh': 0.8}}, 'vitals': {'ageH': 1.0}, 'nums': {}}
    ms = {'row': row, 'market': {'move5m': 2.0}, 'identity': {'mint': 'M'}}
    orig = brain._opp.narrative
    brain._opp.narrative = lambda r: ('BREAKOUT', 'breaking out')
    try:
        assert brain.trigger(ms)['state'] == 'ENTER'
        tr = brain.trigger(ms, None, L.trigger_lessons(st2))
        assert tr['state'] == 'ARM' and 'lesson' in tr['why']
    finally:
        brain._opp.narrative = orig


def test_a_rule_the_record_contradicts_fails_and_a_repeat_real_loss_is_a_new_cause():
    t = _record()
    st, _ = L.step({}, [{'id': 'avoid:flow:BUYERS', 'act': 'avoid', 'when': ['flow:BUYERS'], 'name': 'x', 'desk': 'trigger', 'why': ''}], t, 5000)
    assert st['rules'][0]['status'] == 'failed'   # the coins it would avoid did BETTER on unseen trades
    # too few trades to replay, but the last real losses keep showing the same thing → a new cause
    few = [_trade(i, -15.0, struct='PARABOLIC', age=0.3) for i in range(4)] + [_trade(10 + i, 4.0) for i in range(4)]
    st2, went = L.step({}, [{'id': 'avoid:struct:PARABOLIC', 'act': 'avoid', 'when': ['struct:PARABOLIC'], 'name': 'parabolic chase', 'desk': 'trigger', 'why': ''}], few, 5000)
    assert st2['rules'][0]['status'] == 'live' and st2['rules'][0]['door'] == 'new cause' and st2['rules'][0]['lossHits'] == 4 and went


def test_an_unproven_proposal_retires_after_a_day_and_the_case_is_our_own_table():
    t = [_trade(i, 1.0) for i in range(30)]
    st, _ = L.step({}, [{'id': 'favor:struct:UPTREND', 'act': 'favor', 'when': ['struct:UPTREND'], 'name': 'trend', 'desk': 'trigger', 'why': ''}], t, 5000)
    assert st['rules'][0]['status'] == 'proposed'
    st, _ = L.step(st, [], t, 5000 + L.RETIRE_SEC + 1)
    assert st['rules'][0]['status'] == 'failed'
    c = L.case(t, st, [{'sym': 'A', 'pct': -9, 'cause': 'rugged'}])
    assert c['trades'] == 30 and any('struct:UPTREND' in x for x in c['vocabTable']) and c['losses'] == ['A: -9% · rugged']
