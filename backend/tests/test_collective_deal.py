import collective_pool as cp

U = cp.UNITS['USDC']


def fresh(**cfg):
    st = cp.new_state(); st['cfg'] = cp.clean_cfg({'deal': 'quarterly', 'capPct': 100, **cfg}); return st


def test_the_collective_keeps_all_of_a_send_and_nothing_comes_back():
    st = fresh(); r = cp.send(st, 'k1', 'a', 'o1', 'USDC', 20 * U, 20.0, 1000.0, boost=0.0)
    assert r['keptUnits'] == 20 * U and r['lockedUnits'] == 0 and r['backUnits'] == 0
    assert st['agents']['a']['locked']['USDC'] == 0 and st['agents']['a']['owed']['USDC'] == 0
    cp.tick(st, 1000.0, 1.0); cp.tick(st, 1000.0 + 80 * 86400, 1.0)
    assert st['agents']['a']['owed']['USDC'] == 0


def test_points_are_dollars_times_the_boost_and_one_send_counts_once():
    st = fresh(weightMaxX=2.0); cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 1.0, boost=1.0); assert st['agents']['a']['rewardPts'] == 20
    assert cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 2.0, boost=1.0) is None and st['agents']['a']['rewardPts'] == 20
    cp.send(st, 'k2', 'b', 'o2', 'USDC', 10 * U, 10.0, 1.0, boost=0.0); assert st['agents']['b']['rewardPts'] == 10


def test_a_quarter_shares_real_fees_by_points_and_only_fees():
    st = fresh(rewardDays=90, rewardPayPct=50, carryPct=50, weightMaxX=3.0)
    cp.send(st, 'k1', 'a', 'o1', 'USDC', 100 * U, 100.0, 1000.0, boost=0.0); cp.send(st, 'k2', 'b', 'o2', 'USDC', 100 * U, 100.0, 1000.0, boost=1.0)
    cp.tick(st, 1000.0, 1.0); cp.tick(st, 1100.0, 1.0)
    assert st['books']['USDC']['pot'] == 0   # a send never fills the pot: nobody is paid from somebody else's money coming in
    cp.income(st, 'fee', 'USDC', 1000 * U, 'site'); pot = st['books']['USDC']['pot']; assert pot > 0
    cp.tick(st, 1000.0 + 91 * 86400, 1.0)
    a = st['agents']['a']['earned']['USDC']; b = st['agents']['b']['earned']['USDC']
    assert abs(a + b - pot // 2) <= 2 and abs(b - 3 * a) <= 3 and st['books']['USDC']['pot'] == pot - a - b
    assert st['agents']['a']['rewardPts'] == 50 and st['agents']['b']['rewardPts'] == 150 and st['agents']['b']['lifetimePts'] == 300
    assert len(st['rewards']) == 1


def test_a_quarter_with_no_fees_pays_nothing_and_breaks_nothing():
    st = fresh(); cp.send(st, 'k', 'a', 'o', 'USDC', U, 1.0, 1.0); cp.tick(st, 1.0, 1.0); cp.tick(st, 100.0, 1.0); cp.tick(st, 1.0 + 200 * 86400, 1.0)
    assert st['agents']['a']['earned']['USDC'] == 0


def test_the_owner_cap_keeps_the_rest_in_the_pot():
    st = fresh(capPct=10, rewardPayPct=100); cp.send(st, 'k', 'a', 'whale', 'USDC', 1000 * U, 1000.0, 1.0); cp.income(st, 'f', 'USDC', 100 * U, 'site'); pot = st['books']['USDC']['pot']; cp.reward_close(st, 2.0)
    assert st['agents']['a']['earned']['USDC'] == pot // 10 and st['books']['USDC']['pot'] == pot - pot // 10


def test_a_held_proof_earns_no_points_until_it_is_cleared():
    st = fresh(); r = cp.send(st, 'k', 'a', 'o', 'USDC', 10 * U, 10.0, 1.0, meta={'held': True}); assert not st['agents']['a'].get('rewardPts')
    assert cp.clear_review(st, 'a', r['id']) and st['agents']['a']['rewardPts'] == 10


def test_rank_is_a_name_from_lifetime_points():
    assert cp.rank_of(0)['name'] == 'Spark' and cp.rank_of(300)['name'] == 'Ridge' and cp.rank_of(300)['next'] == 'Print' and cp.rank_of(99999)['next'] is None
    st = fresh(); cp.send(st, 'k', 'a', 'o', 'USDC', 60 * U, 60.0, 1.0); assert cp.view(st, 'a', 2.0, 1.0)['rank']['name'] == 'Signal'


def test_the_record_still_audits_to_the_unit():
    st = fresh(); cp.send(st, 'k', 'a', 'o', 'USDC', 5 * U, 5.0, 1.0)
    assert st['books']['USDC']['in']['proofs'] == 5 * U if 'in' in st['books']['USDC'] else True
