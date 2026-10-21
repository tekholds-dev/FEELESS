import pytest
import family_world as fw

NOW = 1_800_000_000.0


def test_home_turf_bridges_and_reach():
    w = fw.blank()
    h = fw.ensure_home(w, 'c1')
    assert fw.ensure_home(w, 'c1') == h and w['own'][h] == 'c1'
    assert fw.hops('harbor', 'harbor') == 0 and fw.hops('harbor', 'heights') == 1 and fw.hops('harbor', 'docks') == 3
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
    assert len(v['blocks']) == 96 and len(v['bridges']) == len(fw.BRIDGES)
    assert sum(1 for b in v['blocks'] if b.get('mine')) == 1
    assert sum(1 for b in v['blocks'] if b.get('kind') == 'cpu') == 8
    assert any(b.get('kind') == 'cartel' for b in v['blocks']) and v['boom']['borough'] != 'docks'
