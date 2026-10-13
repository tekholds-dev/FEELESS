"""😴 The regret ledger: coins the checks blocked are graded beside the coins taken; a costly check on AGENTS moves one notch, and back."""
import regret as R


def _book(blocked_why, b_end, t_end, n=14, dump_b=0):
    b = {}
    for i in range(n):
        b = R.note(b, f'B{i}', blocked_why, 1.0, 100.0 + i)
        b = R.note(b, f'T{i}', 'taken', 1.0, 100.0 + i)
    px = {**{f'B{i}': 1 + (b_end if i >= dump_b else -40.0) / 100 for i in range(n)}, **{f'T{i}': 1 + t_end / 100 for i in range(n)}}
    return R.watch(b, px, 100.0 + n + R.JUDGE_SEC)


def test_a_refusal_reads_as_its_check_and_every_note_is_graded_beside_the_taken_coins():
    assert R.why_class('buy price 3.1% above market (> 2.5%)') == 'gate:gap'
    assert R.why_class('live pool too thin: $2,533 liquidity < $8,000') == 'gate:pool'
    assert R.why_class('sells back for 5.0% less (> 3.5%)') == 'gate:back' and R.why_class('something else') is None
    b = _book('gate:gap', 12.0, -6.0)
    rec = R.record(b, 100.0 + R.JUDGE_SEC + 20)
    assert rec['gate:gap']['n'] == 14 and rec['gate:gap']['med'] == 12.0 and rec['taken']['med'] == -6.0
    assert R.note(b, 'B0', 'gate:gap', 1.0, 160.0)['open'] == b['open']   # once per coin + check per 30 min
    g = R.watch(R.note({}, 'X', 'gate:pool', 1.0, 0.0), {}, R.GONE_SEC + 1)
    assert g['done'][0]['end'] == -100.0 and g['done'][0]['gone']                       # no price for 2h = gone


def test_a_costly_gate_steps_one_notch_looser_only_where_the_owner_left_agents_and_rolls_back():
    b = _book('gate:gap', 12.0, -6.0)
    now = 100.0 + R.JUDGE_SEC + 20
    b2, ch = R.tune(b, {}, now)
    assert b2['tune']['agentGapPct']['value'] == 4 and ch and 'blocked coins did +12.0%' in ch[0]['why']
    assert R.effective({}, b2)['agentGapPct'] == 4 and R.effective({'agentGapPct': 6}, b2)['agentGapPct'] == 6   # the owner's value wins
    b3, ch3 = R.tune(b, {'agentGapPct': 6}, now)
    assert 'agentGapPct' not in b3['tune'] and not ch3                                      # never touched while the owner set it
    b4, _ = R.tune(b2, {}, now + 60)
    assert b4['tune']['agentGapPct']['value'] == 4                                          # one notch per STEP_SEC
    # the coins taken after the tweak did much worse → rolled back
    t0 = now + 100
    for i in range(14):
        b4 = R.note(b4, f'N{i}', 'taken', 1.0, t0 + i)
    b4 = R.watch(b4, {f'N{i}': 0.7 for i in range(14)}, t0 + 14 + R.JUDGE_SEC)
    b5, ch5 = R.tune(b4, {}, t0 + 20 + R.JUDGE_SEC)
    assert 'agentGapPct' not in b5['tune'] and any('rolled back' in c['why'] for c in ch5)
    b6, _ = R.tune(b5, {}, t0 + 60 + R.JUDGE_SEC)
    assert 'agentGapPct' not in b6['tune']                                                  # it rests before the record may move it again


def test_a_check_that_kept_us_out_of_dumps_is_never_loosened_and_a_costly_tape_wait_switches_off():
    b = _book('gate:pool', 12.0, -6.0, dump_b=8)   # 8 of 14 blocked coins dumped −40%: the pool check was RIGHT about those
    b2, ch = R.tune(b, {}, 100.0 + R.JUDGE_SEC + 20)
    assert 'agentPoolMin' not in b2['tune'] and not ch
    w = _book('flow:PEAK', 15.0, -5.0)
    w2, ch = R.tune(w, {}, 100.0 + R.JUDGE_SEC + 20)
    assert w2['tune']['peakWait']['value'] is False and R.effective({}, w2)['peakWait'] is False
    assert R.effective({'peakWait': False}, {})['peakWait'] is False and R.effective({}, {})['sellersWait'] is True
    v = R.view(w2, 100.0 + R.JUDGE_SEC + 20)
    assert v['record']['flow:PEAK']['n'] == 14 and v['tune']['peakWait']['value'] is False
