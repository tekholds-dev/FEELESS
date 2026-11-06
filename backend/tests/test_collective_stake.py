"""The stake deal: the owner's own example, the cap, nobody's cut shrinks, and a send never pays a reward."""
import collective_pool as cp
import collective_stake as sk
import pytest

NOW = 1_000_000.0


def state(**cfg):
    st = cp.new_state(); st['cfg'] = cp.clean_cfg({'walletCapPct': 50, **cfg}); return st


def send(st, key, cat, usd, grade, owner=None, held=False):
    return cp.send(st, key, cat, owner or f'o-{cat}', 'USDC', int(usd * 1e6), usd, NOW, 0.0, {'grade': grade, 'held': held})


def test_the_owners_example_10_dollars_grade_87():
    st = state(); send(st, 'k', 'a', 10.0, 87); s = sk.of(st['agents']['a'])
    assert (s['x'], s['capUsd'], s['pointsLeft']) == (1.87, 18.7, 18.7)
    assert sk.view(st, 'a', NOW)['cutPct'] == pytest.approx(1.87)


def test_a_send_is_a_stake_and_pays_nobody():
    st = state(); send(st, 'k', 'a', 10.0, 87); b = st['books']['USDC']
    assert b['stake'] == 10_000_000 and b['keep'] == 0 and b['pot'] == 0 and st['agents']['a']['earned']['USDC'] == 0
    send(st, 'k2', 'b', 1000.0, 100)
    assert st['agents']['a']['earned']['USDC'] == 0


def test_fees_are_the_collectives_from_the_jump():
    st = state(); cp.income(st, 'f', 'USDC', 5_000_000, 'txn'); cp.income(st, 't', 'USDC', 2_000_000, 'topup'); b = st['books']['USDC']
    assert b['keep'] == 7_000_000 and b['pot'] == 0


def test_profit_splits_three_ways_and_every_unit_lands():
    st = state(collectivePoolPct=20); send(st, 'k', 'a', 10.0, 87)
    r = sk.pay_profit(st, 'p', 'USDC', 100_000_000, 1e-6, NOW)
    assert r == {'paidUnits': 1_870_000, 'collectiveUnits': 20_000_000, 'compoundUnits': 78_130_000, 'agents': 1}
    assert sk.drip_left(st['agents']['a'], 'USDC') == 1_870_000 and st['agents']['a']['owed']['USDC'] == 0
    assert st['books']['USDC']['keep'] == 20_000_000 and st['books']['USDC']['compound'] == 78_130_000
    assert sk.pay_profit(st, 'p', 'USDC', 100_000_000, 1e-6, NOW) is None   # one transaction, once


def test_points_cap_what_it_can_ever_earn_and_show_what_was_paid():
    st = state(); send(st, 'k', 'a', 10.0, 87)
    for i in range(40):
        sk.pay_profit(st, f'p{i}', 'USDC', 1_000_000_000, 1e-6, NOW)
    s = sk.of(st['agents']['a'])
    assert s['paidUsd'] == pytest.approx(18.7, abs=1e-5) and s['pointsLeft'] == pytest.approx(0, abs=1e-5)
    before = st['books']['USDC']['compound']; sk.pay_profit(st, 'after', 'USDC', 1_000_000_000, 1e-6, NOW)
    sk.release(st, NOW + 8 * 86400); assert st['agents']['a']['earned']['USDC'] == 18_700_000 and st['books']['USDC']['compound'] > before


def test_a_held_proof_earns_nothing_until_cleared():
    st = state(); r = send(st, 'k', 'a', 10.0, 87, held=True)
    assert sk.of(st['agents']['a'])['pointsLeft'] == 0 and sk.cuts(st, NOW) == {}
    assert cp.clear_review(st, 'a', r['id']) and sk.of(st['agents']['a'])['pointsLeft'] == 18.7


def test_fast_reaches_the_top_cut_and_no_other_cut_shrinks():
    st = state(); send(st, 'k', 'a', 10.0, 20); send(st, 'k2', 'b', 10.0, 90)
    before = sk.cuts(st, NOW)
    r = sk.buy_fast(st, 'a', 1, NOW); assert r['burned'] == 5.0 and sk.of(st['agents']['a'])['burned'] == 5.0
    after = sk.cuts(st, NOW)
    assert after['b']['total'] == before['b']['total'] and after['a']['total'] == pytest.approx(0.019)
    assert sk.cuts(st, NOW + 3 * 86400)['a']['total'] == before['a']['total']   # the time runs out


def test_fast_only_spends_free_room():
    st = state(collectivePoolPct=80, cutPerX=10); [send(st, f'k{i}', f'a{i}', 10.0, 0 if i == 0 else 100) for i in range(4)]
    plain = sk.cuts(st, NOW); assert sum(v['total'] for v in plain.values()) == pytest.approx(0.2)   # already full, scaled to what the Collective leaves
    sk.buy_fast(st, 'a0', 1, NOW); after = sk.cuts(st, NOW)
    assert after == plain   # no room, so fast adds nothing, and nobody loses


def test_fast_needs_points_and_stops_at_the_limit():
    st = state(fastMaxDays=10); send(st, 'k', 'a', 10.0, 87)
    with pytest.raises(ValueError):
        sk.buy_fast(st, 'nobody', 1, NOW)
    st2 = state(fastMaxDays=90); send(st2, 'k', 'a', 10.0, 87)
    with pytest.raises(ValueError):
        sk.buy_fast(st2, 'a', 60, NOW)   # 300 points it does not have
    r = sk.buy_fast(st, 'a', 3, NOW); assert r['days'] == 3
    sk.buy_fast(st, 'a', 0.1, NOW)
    assert sk.of(st['agents']['a'])['burned'] == pytest.approx(15.5)


def test_many_agents_on_one_wallet_gain_nothing_past_its_limit():
    st = cp.new_state(); st['cfg'] = cp.clean_cfg({'walletCapPct': 3}); [send(st, f'k{i}', f'a{i}', 5.0, 100, owner='same') for i in range(50)]
    assert sum(v['total'] for v in sk.cuts(st, NOW).values()) == pytest.approx(0.03)


def test_a_loss_comes_off_compound_then_stake_and_never_off_points():
    st = state(); send(st, 'k', 'a', 100.0, 87); sk.pay_profit(st, 'p', 'USDC', 10_000_000, 1e-6, NOW); b = st['books']['USDC']; c = b['compound']
    pts = sk.of(st['agents']['a'])['pointsLeft']
    assert sk.pool_loss(st, 'l', 'USDC', c + 5_000_000) and b['compound'] == 0 and b['stake'] == 95_000_000
    assert sk.of(st['agents']['a'])['pointsLeft'] == pts and not sk.pool_loss(st, 'l', 'USDC', 1)


def test_grade_comes_from_the_record():
    seats = [{'ok': True}] * 5
    assert sk.grade_of({'seats': seats}, 100) == 100 and sk.grade_of({'seats': seats}, 67.5) == 87
    assert sk.grade_of({'seats': [{'ok': False}] * 5}, 0) == 0 and sk.x_of(None) == 1


def test_pools_are_labels_that_move_nothing():
    st = state(); r = sk.add_pool(st, 'meteora', 'SOL-USDC', 'Addr111', 'note', NOW); assert r['on'] and 'note' not in sk.public_pools(st)[0]
    with pytest.raises(ValueError):
        sk.add_pool(st, 'meteora', 'SOL-USDC', 'Addr111', '', NOW)
    with pytest.raises(ValueError):
        sk.add_pool(st, 'hack', 'X', '', '', NOW)
    assert not sk.set_pool(st, r['id'], {'on': False})['on']
    sk.pay_profit(st, 'p', 'USDC', 1_000_000, 1e-6, NOW, r['id']); assert st['pools'][0]['profitUsd'] == 1.0


def test_stored_bank_ledger_moves_to_the_stake_deal(tmp_path):
    p = tmp_path / 'l.json'; import json; p.write_text(json.dumps({'v': 3, 'cfg': {'deal': 'bank'}}))
    assert cp.load(p)['cfg']['deal'] == 'stake'


def test_paying_early_comes_from_profit_or_earnings_and_never_a_stake():
    st = state(); send(st, 'k', 'a', 100.0, 100); stake = st['books']['USDC']['stake']
    with pytest.raises(ValueError):
        sk.pay_early(st, 'e', 'stake', 'USDC', 1_000_000, 1e-6, NOW)
    with pytest.raises(ValueError):
        sk.pay_early(st, 'e', 'compound', 'USDC', 1_000_000, 1e-6, NOW)   # nothing compounded yet
    sk.pay_profit(st, 'p', 'USDC', 100_000_000, 1e-6, NOW); before = sk.of(st['agents']['a'])['paidUsd']; comp = st['books']['USDC']['compound']
    r = sk.pay_early(st, 'e', 'compound', 'USDC', 10_000_000, 1e-6, NOW)
    assert r['paidUnits'] == 10_000_000 and st['books']['USDC']['compound'] == comp - 10_000_000 and st['books']['USDC']['stake'] == stake
    assert sk.of(st['agents']['a'])['paidUsd'] == pytest.approx(before + 10)
    assert sk.pay_early(st, 'e', 'compound', 'USDC', 1_000_000, 1e-6, NOW) is None   # once


def test_paying_early_still_stops_at_points():
    st = state(); send(st, 'k', 'a', 2.0, 0); cp.income(st, 'f', 'USDC', 50_000_000, 'txn')
    assert sk.pay_early(st, 'e', 'keep', 'USDC', 50_000_000, 1e-6, NOW)['paidUnits'] == 2_000_000
    assert st['books']['USDC']['keep'] == 48_000_000 and sk.of(st['agents']['a'])['pointsLeft'] == 0


def test_a_bonus_is_only_what_the_collective_earned_and_takes_no_points():
    st = state(); send(st, 'k', 'a', 10.0, 87)
    with pytest.raises(ValueError):
        sk.bonus(st, 'b', 'a', 'USDC', 1_000_000, 1e-6, 'x', NOW)   # the stake is not the Collective's to give
    cp.income(st, 'f', 'USDC', 5_000_000, 'txn')
    assert sk.bonus(st, 'b', 'a', 'USDC', 2_000_000, 1e-6, 'great proof', NOW)['paidUnits'] == 2_000_000
    assert st['agents']['a']['owed']['USDC'] == 2_000_000 and sk.of(st['agents']['a'])['pointsLeft'] == 18.7 and st['books']['USDC']['keep'] == 3_000_000
    assert st['payLog'][-1]['why'] == 'great proof'


def test_the_stop_keeps_profit_compounding_and_pays_nobody():
    st = state(); send(st, 'k', 'a', 100.0, 87); st['payPaused'] = True
    r = sk.pay_profit(st, 'p', 'USDC', 100_000_000, 1e-6, NOW)
    assert r['paidUnits'] == 0 and r['collectiveUnits'] == 20_000_000 and st['books']['USDC']['compound'] == 80_000_000


def test_targets_stay_inside_the_limits_and_a_stop_warns():
    st = state(spotMaxPct=40, reservePct=30); a = sk.add_pool(st, 'orca', 'A', '1', '', NOW); b = sk.add_pool(st, 'orca', 'B', '2', '', NOW)
    sk.set_pool(st, a['id'], {'targetPct': 40})
    with pytest.raises(ValueError):
        sk.set_pool(st, b['id'], {'targetPct': 41})
    with pytest.raises(ValueError):
        sk.set_pool(st, b['id'], {'targetPct': 31})   # eats the reserve
    sk.set_pool(st, b['id'], {'targetPct': 30, 'inUsd': 100, 'stopPct': 15, 'lossUsd': 14}); assert sk.stop_hits(st) == []
    sk.set_pool(st, b['id'], {'lossUsd': 15}); assert sk.stop_hits(st) == [b['id']]


def test_a_dust_send_earns_no_points_and_changing_the_dial_later_shrinks_nothing():
    st = state(minStakeUsd=5); send(st, 'k', 'a', 1.0, 100); send(st, 'k2', 'a', 10.0, 100)
    assert sk.of(st['agents']['a'])['capUsd'] == 20.0
    st['cfg']['minStakeUsd'] = 50.0; assert sk.of(st['agents']['a'])['capUsd'] == 20.0


def test_the_owner_endpoint_runs_the_whole_deal(monkeypatch, tmp_path):
    """Through the real route: a pool is listed, a stake and fees land, and early pay and a bonus work. Refused without the owner. No network, no money."""
    import asyncio
    import pathlib
    import reputation_service as rs
    from fastapi.testclient import TestClient
    path = pathlib.Path(tmp_path) / 'pool.json'; monkeypatch.setattr(rs, 'POOL_PATH', path)
    async def px():
        return 100.0
    monkeypatch.setattr(rs, '_sol_usd', px)
    client = TestClient(rs.app)
    assert client.post('/api/reputation/admin/collective', json={'poolAdd': {'platform': 'orca', 'pair': 'X-Y'}}).status_code in (401, 403)
    monkeypatch.setattr(rs, '_require_owner', lambda request: 'owner')
    post = lambda body: client.post('/api/reputation/admin/collective', json=body)
    r = post({'poolAdd': {'platform': 'orca', 'pair': 'SOL-USDC', 'address': 'Addr1'}}); assert r.status_code == 200 and r.json()['pools'][0]['pair'] == 'SOL-USDC'
    pid = r.json()['pools'][0]['id']
    assert post({'poolSet': {'id': pid, 'targetPct': 40}}).json()['pools'][0]['targetPct'] == 40
    assert post({'poolSet': {'id': pid, 'targetPct': 90}}).status_code == 400
    def seed(st):
        send(st, 'k', 'a', 100.0, 87); cp.income(st, 'f', 'USDC', 50_000_000, 'txn')
    cp.update(path, seed)
    v = post({'bonus': {'cat': 'a', 'usd': 5, 'token': 'USDC', 'nonce': 'n1', 'why': 'top'}}).json()
    assert v['stake']['keepUsd'] == 45 and v['stake']['stakedUsd'] == 100 and v['payLog'][0]['why'] == 'top'
    assert post({'bonus': {'cat': 'a', 'usd': 5, 'token': 'USDC', 'nonce': 'n1'}}).status_code == 409   # the same press twice
    assert post({'bonus': {'cat': 'a', 'usd': 5000, 'token': 'USDC', 'nonce': 'n2'}}).status_code == 400
    assert post({'payEarly': {'source': 'stake', 'usd': 5, 'token': 'USDC', 'nonce': 'n3'}}).status_code == 400   # never a stake
    v = post({'payEarly': {'source': 'keep', 'usd': 10, 'token': 'USDC', 'nonce': 'n4'}}).json()
    assert v['stake']['keepUsd'] == 35 and v['stake']['paidUsd'] == 10 and v['stakeAgents'][0]['pointsLeft'] == pytest.approx(177)
    assert post({'payPaused': True}).json()['payPaused'] is True
    assert post({'profitSig': 'nope'}).status_code == 400
    asyncio.run(asyncio.sleep(0))


def test_dollars_lift_the_cut_and_slow_after_1k():
    cfg = cp.clean_cfg({})
    assert [sk.size_of(cfg, u) for u in (10, 100, 1000, 10000, 100000)] == [1, 2, 3, 3.5, 4]
    assert sk.size_of(cfg, 1) == 0.25 and sk.size_of(cfg, 0) == 0
    st = state(); send(st, 'k', 'small', 10.0, 87); send(st, 'k2', 'big', 1000.0, 87); send(st, 'k3', 'whale', 100000.0, 87); c = sk.cuts(st, NOW)
    assert c['small']['total'] == pytest.approx(0.0187) and c['big']['total'] == pytest.approx(0.0561) and c['whale']['total'] == pytest.approx(0.0748)
    assert c['whale']['total'] < c['big']['total'] * 1.34   # 100x the money, not even 1.34x the cut


def test_boost_cash_counts_real_profit_second_by_second():
    st = state(dripDays=10); send(st, 'k', 'a', 100.0, 100); a = st['agents']['a']
    sk.pay_profit(st, 'p', 'USDC', 1_000_000_000, 1e-6, NOW); paid = sk.drip_left(a, 'USDC')
    assert paid == 40_000_000 and sk.of(a)['paidUsd'] == 40.0   # its points are taken now
    assert sk.drip_rate(st, a, 'USDC') == pytest.approx(paid / (10 * 86400))
    view = cp.view(st, 'a', NOW, 100.0); assert view['ratePerSecUsd'] > 0
    sk.release(st, NOW + 86400); assert a['owed']['USDC'] == pytest.approx(4_000_000, abs=2)
    assert cp.backed(st, 'USDC') == 40_000_000   # the wallet must hold what has not released yet
    sk.release(st, NOW + 11 * 86400); assert a['owed']['USDC'] == 40_000_000 and sk.drip_left(a, 'USDC') == 0


def test_the_stop_freezes_boost_cash():
    st = state(); send(st, 'k', 'a', 100.0, 100); sk.pay_profit(st, 'p', 'USDC', 100_000_000, 1e-6, NOW); a = st['agents']['a']; st['payPaused'] = True
    sk.release(st, NOW + 86400); assert a['owed']['USDC'] == 0 and sk.drip_rate(st, a, 'USDC') == 0
    st['payPaused'] = False; sk.release(st, NOW + 86400); assert a['owed']['USDC'] == 0   # stopped time does not pay later
