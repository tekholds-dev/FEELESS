"""👨‍⚖️ Loss accountability, not a fear engine: a cause becomes a (bounded, ranking-only) rule only by repetition; valid setups that lost
are said to be valid; wins are studied too."""
import judge_review as jr
import opportunity as op


def pos(m, pct, **k):
    return {'mint': m, 'sym': m, 'since': 1000.0, 'closedAt': 1600.0, 'realPct': pct, 'confirmed': True, 'path': [0.5, 1.0, pct], 'peak': max(pct, 1.0),
            'low': min(pct, 0), 'rule': 'R5 stop', 'tag': '🤖 agents · B-tier', 'thesis': {'structure': 'UPTREND', 'call': 'ENTER NOW'}, **k}


def test_a_valid_setup_that_lost_is_variance_not_a_rule():
    r = jr.review(pos('A', -6))
    assert r['kind'] == 'loss' and r['cause'] == 'variance' and r['desk'] is None and r['decision'] == 'valid decision that lost'


def test_root_causes_name_the_right_desk():
    assert jr.review(pos('R', -40, rule='R1 pool drained'))['desk'] == 'devil'
    assert jr.review(pos('G', -2, peak=14))['cause'] == 'gave_back' and jr.review(pos('G', -2, peak=14))['desk'] == 'reaper'
    assert jr.review(pos('K', -18, path=[-7, -12, -18], thesis={'structure': 'RANGE', 'call': 'WAIT FOR BREAKOUT'}))['desk'] == 'trigger'
    assert jr.review(pos('T', -14, liq=12_000, thesis={'structure': 'RANGE', 'call': 'ENTER NOW'}))['cause'] == 'thin_pool'
    r = jr.review(pos('W', 22, peak=30))
    assert r['kind'] == 'win' and 'entered on UPTREND' in r['why'] and 'B' in r['why']


def test_one_loss_records_two_shadow_three_promote_bounded_and_expiring():
    st = {}
    for i in range(1):
        st = jr.note(st, {**pos(f'a{i}', -14, liq=12_000, thesis={'structure': 'RANGE', 'call': 'ENTER NOW'}), 'closedAt': 1000 + i}, 2000)
    c = jr.court(st, 2000); assert not c['shadow'] and not c['promoted']
    st = jr.note(st, {**pos('a1', -15, liq=11_000, thesis={'structure': 'RANGE', 'call': 'ENTER NOW'}), 'closedAt': 1001}, 2000)
    c = jr.court(st, 2000); assert c['shadow'][0]['cause'] == 'thin_pool' and not c['promoted']
    st = jr.note(st, {**pos('a2', -16, liq=10_500, thesis={'structure': 'RANGE', 'call': 'ENTER NOW'}), 'closedAt': 1002}, 2000)
    c = jr.court(st, 2000); assert c['promoted'][0]['penalty'] == 'thin pool' and c['promoted'][0]['points'] == -jr.PROMOTE_PTS
    assert jr.court(st, 1002 + jr.PROMOTE_SEC + 1)['promoted'] == []                     # it expires unless the cause repeats
    assert jr.court(st, 2000)['scores']['warden'] > 0 and jr.court(st, 2000)['scores']['tally'] == 0   # no desk is punished automatically


def test_unrelated_losses_do_not_tighten_anything():
    st = {}
    for i, p in enumerate((pos('x', -40, rule='R1 drain'), pos('y', -2, peak=12), pos('z', -6))):
        st = jr.note(st, {**p, 'closedAt': 1000 + i}, 2000)
    assert jr.court(st, 2000)['promoted'] == []


def test_a_promoted_rule_is_a_ranking_penalty_never_a_veto():
    row = {'mint': 'M', 'px': 1, 'vitals': {'safe': True, 'liq': 15_000, 'mcap': 50_000, 'rug': 5}, 'nums': {'liq': 15_000, 'd5': 1}, 'chart': {'state': 'UPTREND'}, 'why': {'lean': 1}}
    plain = op.score(row)[0]; pen = op.score(row, pens={'thin pool': -8.0})[0]
    assert pen == plain - 8 and op.hard_fail(row) is None


def test_warden_shares_the_blame_for_a_low_confidence_seat_sized_large():
    r = jr.review(pos('O', -18, tag='🤖 agents · C-tier', warden=1.0, thesis={'structure': 'RANGE', 'call': 'ENTER NOW'}))
    assert r['oversized'] and r['resp']['warden'] >= 50
    assert not jr.review(pos('O2', -18, tag='🤖 agents · A-tier', warden=1.0))['oversized']   # a full A seat was the right size
