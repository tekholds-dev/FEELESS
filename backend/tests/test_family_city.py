import random
import pytest
import family_city as fc

A, B, C = 'A' * 40, 'B' * 40, 'C' * 40
NOW = 1_800_000_000.0


def crew(cid='c1', owner=A, members=None, tag='SIC'):
    return {'id': cid, 'tag': tag, 'name': tag, 'owner': owner, 'members': members or [owner]}


def test_build_produce_collect_upgrade():
    c = crew()
    fc.build(c, A, 0, 'pizza', NOW)
    assert c['city']['bank'] == fc.START_MP - 100
    with pytest.raises(ValueError):
        fc.build(c, A, 0, 'gas', NOW)                                     # lot taken
    v = fc.view(c, NOW + 3600)
    assert v['stash'] == 12 and v['rate'] == 12 and v['lots'][0]['name'] == 'Pump Pizzeria'
    assert fc.collect(c, A, NOW + 3600) == 12 and c['city']['bank'] == fc.START_MP - 100 + 12
    c['city']['bank'] = 10_000
    fc.upgrade(c, A, 0, NOW + 3601)
    assert c['city']['lots']['0']['lvl'] == 2 and fc.rate(c['city']) == 24
    fc.view(c, NOW + 3601 + 3600 * 100)
    assert c['city']['stash'] <= fc.rate(c['city']) * fc.STASH_HOURS + 0.01        # the stash caps


def test_locks_roles_and_the_creator_gets_everything():
    c = crew(members=[A, B])
    with pytest.raises(ValueError):
        fc.build(c, B, 1, 'pizza', NOW)                                   # a member is not the Don
    fc.build(c, B, 1, 'pizza', NOW, rank_of={B: 'underboss'})
    with pytest.raises(ValueError):
        fc.build(c, A, 2, 'tower', NOW)                                   # locked
    fc.build(c, A, 2, 'tower', NOW, staff=True)
    assert c['city']['lots']['2']['b'] == 'tower'
    cat = fc.view(c, NOW, staff=True, mine=True)['catalog']
    assert all(x['ok'] and x['cost'] == 0 for x in cat)
    assert next(x for x in fc.view(c, NOW, mine=True)['catalog'] if x['key'] == 'tower')['need'].startswith('25,000 MP made')


def test_goons_boost_cap_and_robbery():
    a, d = crew('a', A, tag='AAA'), crew('d', C, tag='DDD')
    a['city'] = fc.blank(NOW); d['city'] = fc.blank(NOW)
    a['city']['bank'] = 5000; d['city']['bank'] = 5000
    fc.build(d, C, 0, 'gas', NOW)
    fc.hire(d, C, 'earner', NOW)
    assert fc.rate(d['city']) == pytest.approx(15 * (1 + fc.EARNER_BOOST))
    with pytest.raises(ValueError):
        fc.rob(a, d, A, NOW)                                              # no hitter
    fc.hire(a, A, 'hitter', NOW)
    d['city']['stash'] = 400
    r = fc.rob(a, d, A, NOW, rng=random.Random(1))
    assert 0.1 <= r['odds'] <= 0.85
    if r['win']:
        assert r['take'] == 100 and d['city']['stash'] == 300
    else:
        assert a['city']['goons']['hitter'] == 0
    with pytest.raises(ValueError):
        fc.rob(a, d, A, NOW + 60)                                         # cooldown
    a['city']['goons']['hitter'] = 3; d['city']['goons']['guard'] = 2
    assert fc.rob_odds(a['city'], d['city']) == pytest.approx(0.5)
    for _ in range(fc.goon_cap(a['city'])):
        a['city']['bank'] = 99999
        try:
            fc.hire(a, A, 'guard', NOW)
        except ValueError:
            break
    assert sum(a['city']['goons'].values()) <= fc.goon_cap(a['city'])


def test_trading_boost_and_power():
    c = crew(); fc.build(c, A, 0, 'pizza', NOW)
    assert fc.rate(c['city'], boost=2) == 24 and fc.rate(c['city'], boost=9) == 24     # boost capped ×2
    assert fc.power(c['city']) == 10 + 0 + int(c['city']['bank'] / 100)
