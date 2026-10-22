"""⚔ Family Fuse: challenge → accept → six duels → pot + crowd paid (owner, 2026-10-21). Points only, prices faked."""
import pytest
import family_fuse as ff

NOW = 1_800_000_000.0
A, B = {'id': 'fa', 'tag': 'AAA', 'name': 'A'}, {'id': 'fb', 'tag': 'BBB', 'name': 'B'}
card = lambda n, k='c': ff.card_of(k, 'Card', [{'pairAddress': f'P{k}{i}', 'symbol': f'S{i}', 'usd': 10} for i in range(n)])


def test_challenge_rules_and_the_coin_count_match():
    st = {}
    with pytest.raises(ValueError, match='itself'):
        ff.challenge(st, 'f0', A, A, card(3), 'paper', 0, 15, NOW, 0, 2000)
    with pytest.raises(ValueError, match='2,000 MP'):
        ff.challenge(st, 'f0', A, B, card(3), 'mp', 500, 15, NOW, 1999, 2000)
    f, hold = ff.challenge(st, 'f1', A, B, card(4), 'mp', 500, 15, NOW, 5000, 2000)
    assert hold == 500 and f['status'] == 'open'
    with pytest.raises(ValueError, match='already'):
        ff.challenge(st, 'f2', B, A, card(4), 'paper', 0, 15, NOW, 0, 2000)
    with pytest.raises(ValueError, match='one apart'):
        ff.accept(f, card(6, 'd'), NOW + 5, 5000, 2000)                       # never 4 vs 6
    with pytest.raises(ValueError, match='needs'):
        ff.accept(f, card(5, 'd'), NOW + 5, 1000, 2000)
    assert ff.accept(f, card(5, 'd'), NOW + 5, 5000, 2000) == 500 and f['status'] == 'live' and f['ends'] == NOW + 5 + 900


def test_crowd_bids_close_at_a_third_and_pay_pro_rata():
    st = {}
    f, _ = ff.challenge(st, 'f1', A, B, card(3), 'mp', 1000, 30, NOW, 5000, 2000)
    ff.accept(f, card(3, 'd'), NOW, 5000, 2000)
    assert ff.bid(f, 'w1', 'a', 100, 500, NOW + 60) == 100
    ff.bid(f, 'w2', 'a', 300, 500, NOW + 60); ff.bid(f, 'w3', 'b', 400, 500, NOW + 60)
    with pytest.raises(ValueError, match='One bid'):
        ff.bid(f, 'w1', 'b', 50, 500, NOW + 60)
    with pytest.raises(ValueError, match='own family'):
        ff.bid(f, 'w4', 'b', 50, 500, NOW + 60, family_of='fa')
    with pytest.raises(ValueError, match='closed'):
        ff.bid(f, 'w5', 'a', 50, 500, NOW + 601)                              # a third of 30 min
    assert ff.odds(f)['pays']['a'] == round(800 * 0.95 / 400, 2)
    paid = ff.settle(f, 'a', NOW + 1800)
    assert paid['fam'] == {'fa': 1900} and paid['bids'] == {'w1': 190, 'w2': 570}
    assert paid['house'] == 100 + 40 and f['status'] == 'done'


def test_draw_and_no_winning_bidders_refund():
    st = {}
    f, _ = ff.challenge(st, 'f1', A, B, card(2), 'mp', 200, 15, NOW, 5000, 2000); ff.accept(f, card(2, 'd'), NOW, 5000, 2000)
    ff.bid(f, 'w1', 'b', 50, 99, NOW)
    assert ff.settle(f, 'draw', NOW + 900) == {'fam': {'fa': 200, 'fb': 200}, 'bids': {'w1': 50}, 'house': 0}
    g, _ = ff.challenge({}, 'f2', A, B, card(2), 'paper', 0, 15, NOW, 0, 2000); ff.accept(g, card(3, 'd'), NOW, 0, 2000)
    ff.bid(g, 'w1', 'b', 50, 99, NOW)
    assert ff.settle(g, 'a', NOW + 900)['bids'] == {'w1': 50}                 # nobody backed the winner → refunds
    h, _ = ff.challenge({}, 'f3', A, B, card(2), 'paper', 0, 15, NOW, 0, 2000)
    assert not ff.expire(h, NOW + 10) and ff.expire(h, NOW + ff.OPEN_SEC + 1) and h['status'] == 'expired'


def test_service_runs_a_whole_family_fuse(monkeypatch):
    import asyncio
    import reputation_service as rs
    from fastapi.testclient import TestClient
    st = {'crews': {'fa': {'id': 'fa', 'name': 'Alpha', 'tag': 'AAA', 'owner': 'WA', 'members': ['WA', 'WS'], 'seats': 5},
                    'fb': {'id': 'fb', 'name': 'Bravo', 'tag': 'BBB', 'owner': 'WB', 'members': ['WB'], 'seats': 5}},
          'by': {'WA': 'fa', 'WS': 'fa', 'WB': 'fb'}, 'house': 0}
    rs._json_save(rs.CREWS_PATH, st)
    rs._json_save(rs.FUSES_PATH, {'fuses': {'d1': {'name': 'A card', 'creator': 'WA', 'legs': [{'pairAddress': 'PA1', 'symbol': 'X'}, {'pairAddress': 'PA2', 'symbol': 'Y'}, {'pairAddress': 'PA3', 'symbol': 'Z'}]},
                                            'd2': {'name': 'B card', 'creator': 'WB', 'legs': [{'pairAddress': 'PB1', 'symbol': 'Q'}, {'pairAddress': 'PB2', 'symbol': 'R'}]}}})
    px = {'PA1': 1.0, 'PA2': 1.0, 'PA3': 1.0, 'PB1': 1.0, 'PB2': 1.0}

    async def pairs(legs):
        return {l['pairAddress']: {'priceUsd': px[l['pairAddress']], 'liquidity': {'usd': 5e6}} for l in legs}
    monkeypatch.setattr(rs, '_fuse_pairs', pairs)
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: a)
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: None)
    monkeypatch.setattr(rs, '_is_staff', lambda a: False)
    clock = [rs.time.time()]
    monkeypatch.setattr(rs.time, 'time', lambda: clock[0])
    s = rs._json_load(rs.CREWS_PATH, {})
    for cid in ('fa', 'fb'):
        rs._fcity.city_of(s['crews'][cid], clock[0])['bank'] = 6000
    s['crews']['fa'].setdefault('world', {})['pts'] = {'WS': 300}
    rs._json_save(rs.CREWS_PATH, s)
    c = TestClient(rs.app)
    post = lambda **b: c.post('/api/reputation/familia-fuse/act', json={'session': 's', **b})
    r = post(address='WA', act='challenge', vs='fb', card='design:d1', stake='mp', mp=1000, mins=15)
    assert r.status_code == 200, r.text
    fid = r.json()['result']['id']
    assert post(address='WS', act='challenge', vs='fb', card='design:d1').status_code == 400        # a soldier cannot call a fight
    assert post(address='WB', act='accept', fight=fid, card='design:d2').status_code == 200
    assert post(address='WS', act='bid', fight=fid, side='a', amount=200).status_code == 200
    s = rs._json_load(rs.CREWS_PATH, {})
    assert rs._fcity.city_of(s['crews']['fa'], clock[0])['bank'] == 5000 and s['crews']['fa']['world']['pts']['WS'] == 100
    px.update(PA1=1.3, PA2=1.2, PA3=1.1)                                       # Alpha's coins run
    clock[0] += 16 * 60
    asyncio.run(rs._ffuse_tick(clock[0], force=True))
    s = rs._json_load(rs.CREWS_PATH, {}); f = s['world']['ffuse'][fid]
    assert f['status'] == 'done' and f['winner'] == 'a' and f['score']['a'] >= 2
    assert rs._fcity.city_of(s['crews']['fa'], clock[0])['bank'] == 5000 + 1900 and s['crews']['fa']['world']['pts']['WS'] == 100 + 190
    assert s['house'] == 100 + 10
    v = c.get('/api/reputation/familia-world').json()['ffuse']
    assert v['fights'][0]['winner'] == 'a' and v['fights'][0]['a']['tag'] == 'AAA'


def test_brackets_ranked_fights_and_ratings_move_zero_sum():
    assert ff.bracket(None)[:2] == ('street', 'Street') and ff.bracket(1100)[1] == 'Made' and ff.bracket(1399)[1] == 'Capo' and ff.bracket(1700)[1] == 'Don'
    assert ff.ranked(1000, 1150) and ff.ranked(1250, 1450) and not ff.ranked(1000, 1260)   # one bracket apart is ranked; two is an exhibition
    a, b = ff.elo(1000, 1000, 1)
    assert (a, b) == (1016, 984)
    a, b = ff.elo(1400, 1000, 1)   # the favourite wins → barely moves
    assert a - 1400 < 4 and a + b == 2400
    assert ff.elo(1000, 1000, 0.5) == (1000, 1000)


def test_any_member_runs_a_paper_fight_the_bank_stays_the_dons():
    ff.may_run('paper', boss=False)
    ff.may_run('mp', boss=True)
    with pytest.raises(ValueError, match='Don or the Underboss'):
        ff.may_run('mp', boss=False)


def test_the_view_carries_ranked_the_caller_and_both_ratings():
    st = {}
    f, _ = ff.challenge(st, 'f1', {**A, 'rating': 1180, 'bracket': 'Made'}, {**B, 'rating': 1010, 'bracket': 'Street'}, card(3), 'paper', 0, 15, NOW, 0, 2000)
    f.update(ranked=ff.ranked(1180, 1010), byName='Vito')
    v = ff.view(f, NOW)
    assert v['ranked'] and v['by'] == 'Vito' and (v['a']['rating'], v['a']['bracket'], v['b']['bracket']) == (1180, 'Made', 'Street')


def test_a_settled_ranked_fight_moves_both_ratings_once_through_the_payout():
    import reputation_service as rs
    st = {'crews': {'fa': {'id': 'fa', 'tag': 'AAA', 'members': []}, 'fb': {'id': 'fb', 'tag': 'BBB', 'members': []}}}
    f, _ = ff.challenge({}, 'f1', A, B, card(3), 'paper', 0, 15, NOW, 0, 2000)
    f['ranked'] = True
    ff.accept(f, card(3, 'd'), NOW, 0, 2000)
    ff.settle(f, 'a', NOW + 900)
    rs._ffuse_pay(st, f, NOW + 900)
    assert st['crews']['fa']['world']['fuseElo'] == 1016 and st['crews']['fb']['world']['fuseElo'] == 984 and f['elo'] == {'a': [1000, 1016], 'b': [1000, 984]}
    rs._ffuse_pay(st, f, NOW + 901)   # paid twice by mistake → ratings don't move again
    assert st['crews']['fa']['world']['fuseElo'] == 1016
