import pytest
import family_world as fw

NOW = 1_800_000_000.0


def test_home_turf_bridges_and_reach():
    w = fw.blank()
    h = fw.ensure_home(w, 'c1')
    assert fw.ensure_home(w, 'c1') == h and w['own'][h] == 'c1'
    assert fw.hops('harbor', 'harbor') == 0 and fw.hops('harbor', 'heights') == 1 and fw.hops('harbor', 'docks') == 2   # Fee City is the hub: harbor → fee → docks
    free = next(b for b in fw.block_ids('market') if b not in fw.taken(w))
    with pytest.raises(ValueError):
        fw.buy_block(w, 'c1', 10, free)
    cost = fw.buy_block(w, 'c1', 1_000_000, free)
    assert cost > 0 and free in fw.turf_of(w, 'c1')
    with pytest.raises(ValueError):
        fw.buy_block(w, 'c2', 1_000_000, free)                               # held
    assert fw.reach(w, 'c1', 'market')
    assert fw.sell_block(w, 'c1', free) > 0 and free not in w['own']
    with pytest.raises(ValueError):
        fw.sell_block(w, 'c1', h)                                            # never the home block


def test_cpu_towns_are_hard_and_refill():
    t = fw.cpu_town('cpu-7', NOW)
    assert min(t['guards']) >= 5 and len(t['guards']) >= 10
    w = fw.blank()
    s = fw.cpu_stash(w, 'cpu-7', NOW)
    s['stash'] = 0
    assert fw.cpu_stash(w, 'cpu-7', NOW + 3600)['stash'] == pytest.approx(t['rate'])


def test_cartels_cluster_by_shared_coins():
    wl = {f'w{i}': {'mints': {f'm{j}': 'bundler' for j in range(i % 3, i % 3 + 4)}, 'lastSeen': NOW} for i in range(9)}
    wl['s1'] = {'mints': {'x1': 'sniper', 'x2': 'sniper', 'x3': 'sniper'}, 'lastSeen': 0}
    wl['tiny'] = {'mints': {'z': 'funder'}}
    cs = fw.cartels(wl, NOW)
    roles = {c['role'] for c in cs}
    assert roles == {'bundler', 'sniper'}
    b = next(c for c in cs if c['role'] == 'bundler')
    assert b['members'] == 9 and b['active7d'] == 9 and b['kind'] == 'cartel'
    assert fw.cartel_town(b)['guards']


def test_raid_is_a_chess_game_and_the_house_defends():
    w = fw.blank()
    tgt = {'id': 'd', 'tag': 'D', 'name': 'D', 'lots': [{'lot': 0, 'b': 'pizza', 'lvl': 3}, {'lot': 4, 'b': 'bank', 'lvl': 6}], 'guards': [5]}
    r = fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt, 'me', 'don', [6, 5], 10_000, NOW)
    assert r['power'] == 3 and r['board'][1]['def'] == 5                     # the guard sits on the rich lot
    view = fw.raid_view(r, 'a')
    assert all(x['def'] is None for x in view['board'])                      # hidden until scouted
    fw.attack(r, 'scout', 4, NOW)
    assert fw.raid_view(r, 'a')['board'][1]['def'] == 5
    with pytest.raises(ValueError):
        fw.attack(r, 'hit', 0, NOW)                                          # defender's turn
    fw.tick(r, NOW + fw.RESPOND_SEC)                                         # no answer → the house plays
    assert r['moves'][-1]['side'] == 'b' and 'house' in r['moves'][-1]['word']
    fw.attack(r, 'hit', 0, NOW + 300)
    fw.defend(r, 'guard', 4, NOW + 310)
    assert r['status'] == 'done' and r['loot'] <= int(10_000 * fw.LOOT_MAX)
    with pytest.raises(ValueError):
        fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt, 'me', 'don', [6], 10_000, NOW + 400)   # pair cooldown


def test_cartel_raid_pays_justice_and_replays():
    w1, w2 = fw.blank(), fw.blank()
    tgt = {'id': 'cartel-sniper-1', 'tag': 'SN1', 'name': 'x', 'lots': [{'lot': 2, 'b': 'casino', 'lvl': 2}], 'guards': [1]}
    outs = []
    for w in (w1, w2):
        r = fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt, 'me', 'don', [10, 10, 10], 5000, NOW, kind='cartel')
        fw.attack(r, 'hit', 2, NOW)
        fw.defend(r, 'guard', 2, NOW)
        fw.attack(r, 'retreat', 2, NOW)
        outs.append((r['loot'], r['paid']))
    assert outs[0] == outs[1] and outs[0][1] == int(outs[0][0] * fw.JUSTICE)


def test_challenges_errands_rewards_and_feecat_redeem():
    rows = fw.challenge_rows({'errands': 5}, [])
    assert next(r for r in rows if r['key'] == 'first-run')['ready']
    assert fw.claim_challenge('first-run', {'errands': 5}, [])['recruit'] == {'k': 'earner', 'lvl': 3}
    with pytest.raises(ValueError):
        fw.claim_challenge('first-run', {'errands': 5}, ['first-run'])
    cd = {}
    mp, pts, _ = fw.errand({'pharma': 2}, cd, 'pharma', NOW, 400)
    assert mp == 80 + 200 and pts == 14
    with pytest.raises(ValueError):
        fw.errand({'pharma': 2}, cd, 'pharma', NOW + 60, 400)
    with pytest.raises(ValueError):
        fw.errand({}, {}, 'pizza', NOW, 400)
    assert fw.reward('rush', 5000) == 4000
    assert fw.redeem_feecat(2_500_000) == (2_000_000, 20_000)
    with pytest.raises(ValueError):
        fw.redeem_feecat(999_999)


def test_map_view_has_every_block_and_marks_mine():
    w = fw.blank()
    fw.ensure_home(w, 'c1')
    cs = fw.cartels({f'w{i}': {'mints': {'a': 'sniper', 'b': 'sniper', 'c': 'sniper'}} for i in range(3)}, NOW)
    v = fw.map_view(w, [{'id': 'c1', 'tag': 'SIC', 'name': 'S'}], [fw.cpu_town(c[0], NOW) for c in fw.CPU], cs, me='c1', boom_=fw.boom('ai'), now=NOW)
    assert len(v['blocks']) == 96 + fw.PLOTS['fee'] and len(v['bridges']) == len(fw.BRIDGES)
    assert sum(1 for b in v['blocks'] if b.get('mine')) == 1
    assert sum(1 for b in v['blocks'] if b.get('kind') == 'cpu') == 8
    assert any(b.get('kind') == 'cartel' for b in v['blocks']) and v['boom']['borough'] != 'docks'


def test_fee_city_is_the_hub_with_premium_plots_and_never_a_free_home():
    assert len(fw.block_ids('fee')) == 24 and all(fw.hops('fee', c) == 1 for c in ('harbor', 'heights', 'bay', 'docks'))
    assert sorted(b for c in fw.CITIES for b in c[2]) == sorted(fw.BKEYS)            # every borough sits in exactly one city
    w = fw.blank()
    homes = [fw.ensure_home(w, f'c{i}') for i in range(40)]
    assert not any(h.startswith('fee-') for h in homes)
    assert fw.block_price(w, 'c0', 'fee-3') > fw.block_price(w, 'c0', 'harbor-3') * 2


def test_owner_rules_are_clamped_and_live_ones_change_the_engine():
    r = fw.clean_rules({'blockMp': 5, 'feeTier': 99, 'turfMax': '7', 'createUsd': 10, 'createFeeUsd': 50, 'junk': 1})
    assert r['blockMp'] == 100 and r['feeTier'] == 20 and r['turfMax'] == 7 and r['createFeeUsd'] == 10 and 'junk' not in r
    try:
        fw.set_rules(dict(r, blockMp=1000, feeTier=3.0))
        assert fw.BLOCK_MP == 1000 and fw.tier('fee') == 3.0 and fw.TURF_MAX == 7
    finally:
        fw.set_rules(fw.RULES)
    assert fw.BLOCK_MP == 2400 and fw.tier('fee') == 2.5


def test_family_fuse_cards_must_match_and_mp_battles_need_2k():
    assert fw.family_fuse_ok(3, 3)[0] and fw.family_fuse_ok(3, 4)[0] and fw.family_fuse_ok(4, 3)[0]
    assert not fw.family_fuse_ok(4, 6)[0] and not fw.family_fuse_ok(0, 1)[0]
    assert not fw.family_fuse_ok(3, 3, bank_mp=1999, stake='mp')[0] and fw.family_fuse_ok(3, 3, bank_mp=2000, stake='mp')[0]


def test_ranks_climb_in_divisions_and_the_top_25_are_dons():
    assert fw.rank_of(0)['name'] == 'Street Rat' and fw.rank_of(0)['div'] == 'III'
    assert fw.rank_of(600)['name'] == 'Capo' and fw.rank_of(1199)['div'] == 'I'
    assert fw.rank_of(9000, place=3)['name'] == fw.TOP_TITLE and fw.rank_of(9000, place=26)['name'] == 'Kingpin'
    assert fw.rank_of(100, place=1)['name'] == 'Runner'                                # #1 alone is not enough: Dons need Kingpin power


def test_paid_hit_payout_follows_the_owners_anchors():
    assert fw.paid_hit_payout(5, 100, 1000) < 0.0005                                   # $5 on a 10x bigger family ~ $0.0001
    assert 0.05 <= fw.paid_hit_payout(4000, 4000, 4000) <= 0.10                        # equal $4K families, whole wallet: <= the cap
    assert fw.paid_hit_payout(5, 1000, 100) < fw.paid_hit_payout(5, 100, 1000)         # bullying a smaller family pays less
    assert fw.paid_hit_payout(1e9, 1, 1e9, cap_usd=0.1) == 0.1 and fw.paid_hit_payout(10, 10, 0) == 0


def test_a_held_building_can_be_set_to_a_real_pool_and_cleared_never_someone_elses():
    w = fw.blank()
    h = fw.ensure_home(w, 'c1')
    row = {'pool': 'jito', 'sym': 'JITOSOL', 'kind': 'stake', 'proto': 'Jito', 'tvl': 1}
    assert fw.link_block(w, 'c1', h, row) == {'pool': 'jito', 'sym': 'JITOSOL', 'kind': 'stake', 'proto': 'Jito'}   # only the display fields are kept
    assert w['links'][h]['pool'] == 'jito'
    other = fw.ensure_home(w, 'c2')
    with pytest.raises(ValueError):
        fw.link_block(w, 'c1', other, row)                                    # not your block
    assert fw.link_block(w, 'c1', h, None) is None and h not in w['links']


def test_turf_blocks_run_on_a_fund_shut_when_dry_and_any_member_can_refill():
    import family_world as fw
    w = fw.blank(); now = 1_800_000_000.0
    home = fw.ensure_home(w, 'fa'); turf = next(b for b in fw.block_ids('heights') if b not in fw.taken(w)); w['own'][turf] = 'fa'
    assert fw.block_state(w, 'fa', home, now) == ('active', None)            # home never shuts
    assert fw.block_state(w, 'fa', turf, now) == ('active', 24.0)            # first sight → a grace day
    assert fw.block_state(w, 'fa', turf, now + 25 * 3600)[0] == 'shut'      # the fund ran dry
    take, hrs = fw.fund_block(w, 'fa', turf, 240, now + 25 * 3600)
    assert (take, hrs) == (240, 24.0) and fw.block_state(w, 'fa', turf, now + 26 * 3600)[0] == 'active'
    import pytest
    with pytest.raises(ValueError, match='never shuts'):
        fw.fund_block(w, 'fa', home, 100, now)
    with pytest.raises(ValueError, match='Hold that block'):
        fw.fund_block(w, 'fb', turf, 100, now)
    with pytest.raises(ValueError, match='at least'):
        fw.fund_block(w, 'fa', turf, 5, now)
    take, hrs = fw.fund_block(w, 'fa', turf, 10_000_000, now + 26 * 3600)   # capped at two weeks
    assert hrs <= fw.FUND_MAX_H and take == int(round(hrs * fw.UPKEEP_MP))


def test_the_docks_show_six_cartels_and_a_familys_launch_stands_on_its_home():
    import family_world as fw
    w = fw.blank(); now = 1_800_000_000.0; home = fw.ensure_home(w, 'fa')
    carts = [{'id': f'cartel-x-{i}', 'tag': f'X{i}', 'name': f'C{i}', 'power': i, 'role': 'sniper', 'icon': '🎯'} for i in range(18)]
    v = fw.map_view(w, [{'id': 'fa', 'tag': 'AAA', 'name': 'A', 'launch': {'mint': 'M1', 'symbol': 'FEE'}}], [], carts, me='fa', now=now)
    shown = [b for b in v['blocks'] if b.get('kind') == 'cartel']
    assert len(shown) == fw.CARTEL_BLOCKS and {b['tag'] for b in shown} == {f'X{i}' for i in range(12, 18)}   # the strongest six
    h = next(b for b in v['blocks'] if b['id'] == home)
    assert h['launch'] == {'mint': 'M1', 'symbol': 'FEE'} and h['state'] == 'active'


def test_raids_are_capped_three_per_family_per_12h_both_ways():
    w = fw.blank(); tgt = lambda i: {'id': i, 'tag': i.upper(), 'name': i, 'lots': [{'lot': 0, 'b': 'pizza', 'lvl': 1}], 'guards': []}
    for k, t in enumerate(('x', 'y', 'z')):   # a family runs 3 raids …
        w['raids'][fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt(t), 'me', 'don', [3], 1000, NOW + k)['id']]['status'] = 'done'
    with pytest.raises(ValueError, match='3 raids in 12 hours'):
        fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt('q'), 'me', 'don', [3], 1000, NOW + 10)
    for k, att in enumerate(('b', 'c')):   # … and a target takes at most 3 in 12 h ('z' already took one)
        w['raids'][fw.start(w, {'id': att, 'tag': att, 'name': att}, tgt('z'), 'me', 'don', [3], 1000, NOW + 20 + k)['id']]['status'] = 'done'
    with pytest.raises(ValueError, match='raided 3'):
        fw.start(w, {'id': 'e', 'tag': 'E', 'name': 'E'}, tgt('z'), 'me', 'don', [3], 1000, NOW + 30)
    assert fw.start(w, {'id': 'a', 'tag': 'A', 'name': 'A'}, tgt('q'), 'me', 'don', [3], 1000, NOW + fw.RAID_CAP_SEC + 5)   # the window ages out
