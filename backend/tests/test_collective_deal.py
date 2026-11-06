import collective_pool as cp
import agent_features as feat

U = cp.UNITS['USDC']; DAY = 86400


def fresh(**cfg):
    st = cp.new_state(); st['cfg'] = cp.clean_cfg({'capPct': 100, 'floorPct': 0, **cfg}); return st


def test_the_collective_banks_all_of_a_send_and_it_never_reaches_a_reward():
    st = fresh(); r = cp.send(st, 'k1', 'a', 'o1', 'USDC', 20 * U, 20.0, 1000.0)
    assert r['keptUnits'] == 20 * U and r['lockedUnits'] == 0 and r['backUnits'] == 0
    assert st['books']['USDC']['pot'] == 0 and st['books']['USDC']['keep'] == 20 * U
    for d in range(1, 200, 5):
        cp.tick(st, 1000.0 + d * DAY, 1.0)
    assert st['agents']['a']['earned']['USDC'] == 0 and st['books']['USDC']['keep'] == 20 * U


def test_points_are_dollars_times_the_boost_and_one_send_counts_once():
    st = fresh(weightMaxX=2.0); cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 1.0, boost=1.0); assert st['agents']['a']['rewardPts'] == 20
    assert cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 2.0, boost=1.0) is None and st['agents']['a']['rewardPts'] == 20


def test_rank_and_boost_shorten_the_wait_never_below_the_floor():
    c = cp.clean_cfg({})
    assert cp.cycle_days(c, 0, 0) == 30 and cp.cycle_days(c, 5, 0) == 15 and cp.cycle_days(c, 5, 1) == 10.5 and cp.cycle_days(c, 0, 1) == 21
    assert cp.cycle_days(cp.clean_cfg({'rankSpeedPct': 80, 'boostSpeedPct': 80}), 5, 1) == 7


def test_a_fast_agent_gets_paid_sooner_not_more_in_a_month():
    st = fresh(rewardPayPct=50, carryPct=100)
    cp.send(st, 'a', 'slow', 'o1', 'USDC', 100 * U, 100.0, 1000.0, boost=0.0); cp.send(st, 'b', 'fast', 'o2', 'USDC', 100 * U, 100.0, 1000.0, boost=0.0); st['agents']['fast']['lifetimePts'] = 30000; st['agents']['slow']['lifetimePts'] = 0
    cp.income(st, 'f', 'USDC', 1000 * U, 'site'); t = 1000.0; cp.tick(st, t, 1.0); cp.tick(st, t + DAY, 1.0); st['monthEnd'] = t + 999 * DAY
    for d in range(2, 18):
        cp.tick(st, t + d * DAY, 1.0)
    assert st['agents']['fast']['earned']['USDC'] > 0 and st['agents']['slow']['earned']['USDC'] == 0
    for d in range(18, 33):
        cp.tick(st, t + d * DAY, 1.0)
    fast = st['agents']['fast']['earned']['USDC']; slow = st['agents']['slow']['earned']['USDC']
    assert slow > 0 and abs(fast - slow) <= 2   # the same part of the same month


def test_every_owner_eats_from_the_floor_and_points_decide_the_rest():
    st = fresh(floorPct=20); cp.send(st, 'a', 'small', 'o1', 'USDC', 1 * U, 1.0, 1.0); cp.send(st, 'b', 'big', 'o2', 'USDC', 999 * U, 999.0, 1.0)
    p = cp.reward_shares(st); assert p['small'] > 0.1 and p['big'] > p['small'] and abs(sum(p.values()) - 1) < 1e-9


def test_payouts_never_pass_half_of_all_fee_money_even_over_years():
    st = fresh(rewardPayPct=100, payoutCapPct=100); st['cfg']['payoutCapPct'] = cp.clean_cfg({'payoutCapPct': 100})['payoutCapPct']; assert st['cfg']['payoutCapPct'] == 50
    cp.send(st, 'a', 'a', 'o', 'USDC', 10 * U, 10.0, 1.0); cp.income(st, 'f', 'USDC', 1000 * U, 'site'); fee = 1000 * U
    for d in range(1, 800, 3):
        cp.tick(st, 1.0 + d * DAY, 1.0)
    b = st['books']['USDC']; assert b['rewardPaid'] <= fee // 2 and st['agents']['a']['earned']['USDC'] == b['rewardPaid'] and b['pot'] + b['rewardPaid'] == fee


def test_no_fees_pays_nothing_and_breaks_nothing():
    st = fresh(); cp.send(st, 'k', 'a', 'o', 'USDC', U, 1.0, 1.0)
    for d in range(1, 100, 7):
        cp.tick(st, 1.0 + d * DAY, 1.0)
    assert st['agents']['a']['earned']['USDC'] == 0


def test_the_owner_cap_keeps_the_rest_in_the_pot():
    st = fresh(capPct=10, rewardPayPct=100); cp.send(st, 'k', 'a', 'whale', 'USDC', 1000 * U, 1000.0, 1.0); cp.income(st, 'f', 'USDC', 100 * U, 'site'); cp.tick(st, 1.0, 1.0); cp.tick(st, 100.0, 1.0); cp.tick(st, 1.0 + 31 * DAY, 1.0)
    assert st['agents']['a']['earned']['USDC'] <= 10 * U and st['books']['USDC']['pot'] >= 90 * U


def test_a_held_proof_earns_no_points_until_it_is_cleared():
    st = fresh(); r = cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 1.0, meta={'held': True}); assert not st['agents']['a'].get('rewardPts')
    assert cp.clear_review(st, 'a', r['id']) and st['agents']['a']['rewardPts'] == 10


def test_rank_is_a_name_from_lifetime_points():
    assert cp.rank_of(0)['name'] == 'Spark' and cp.rank_of(300)['next'] == 'Print' and cp.rank_of(99999)['next'] is None
    st = fresh(); cp.send(st, 'k', 'a', 'o', 'USDC', 60 * U, 60.0, 1.0); v = cp.view(st, 'a', 2.0, 1.0); assert v['rank']['name'] == 'Signal' and v['cycleDays'] == 27


def test_a_models_notes_after_the_document_never_reach_the_page():
    page = '<html><body><p>Hi</p></body></html>\n\n### Live Desk\nHow it works'
    assert '###' not in feat.preview(page) and 'Hi' in feat.preview(page) and feat.strip_notes('<div>x</div>') == '<div>x</div>'


def _run_months(st, months, start=1_000_000.0):
    t = start
    for _ in range(months * 2):
        t += 15 * 86400; cp.tick(st, t, 100.0)
    return t


def test_rewards_stop_at_the_ceiling_however_much_profit_comes_in():
    st = cp.new_state(); cp.send(st, 'k1', 'a', 'o', 'USDC', 37_000_000, 37.0, 1_000_000.0)
    cp.book_result(st, 'p1', 'USDC', 100_000_000_000)
    st['cfg']['capPct'] = 100.0
    _run_months(st, 60)
    assert st['agents']['a']['earned']['USDC'] == int(37_000_000 * 1.08)
    assert cp.back_room(st, 'a', 'USDC') == 0


def test_the_owner_raising_the_ceiling_opens_more_room():
    st = cp.new_state(); cp.send(st, 'k1', 'a', 'o', 'USDC', 10_000_000, 10.0, 1_000_000.0)
    assert cp.back_room(st, 'a', 'USDC') == 10_800_000
    st['cfg'] = cp.clean_cfg({**st['cfg'], 'maxBackX': 1.5})
    assert cp.back_room(st, 'a', 'USDC') == 15_000_000
    assert cp.clean_cfg({'maxBackX': 99})['maxBackX'] == 5


def test_sends_alone_never_pay_the_first_user_anything():
    st = cp.new_state(); cp.send(st, 'k1', 'a', 'o', 'USDC', 37_000_000, 37.0, 1_000_000.0)
    _run_months(st, 24)
    assert st['agents']['a']['earned']['USDC'] == 0 and st['books']['USDC']['keep'] == 37_000_000


def test_paid_out_never_passes_half_of_the_profit_and_the_books_only_grow():
    st = cp.new_state(); cp.send(st, 'k1', 'a', 'o', 'USDC', 1_000_000_000, 1000.0, 1_000_000.0); st['cfg']['capPct'] = 100.0
    cp.book_result(st, 'p1', 'USDC', 10_000_000)
    _run_months(st, 36); b = st['books']['USDC']
    assert b['rewardPaid'] <= 5_000_000 and b['keep'] == 1_000_000_000 and b['pot'] + b['rewardPaid'] == 10_000_000


def test_a_pool_loss_hits_the_pot_then_the_bank_and_counts_once():
    st = cp.new_state(); cp.send(st, 'k1', 'a', 'o', 'USDC', 100_000_000, 100.0, 1_000_000.0); cp.book_result(st, 'p1', 'USDC', 5_000_000)
    assert cp.book_result(st, 'l1', 'USDC', -8_000_000) and not cp.book_result(st, 'l1', 'USDC', -8_000_000)
    b = st['books']['USDC']; assert b['pot'] == 0 and b['keep'] == 97_000_000
    assert cp._budget_left({**st, 'budget': {'USDC': 10 ** 9}}, 'USDC') == 0
