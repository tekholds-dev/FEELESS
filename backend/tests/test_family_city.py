import random
import pytest
import family_city as fc

A, B = 'A' * 40, 'B' * 40
NOW = 1_800_000_000.0


def crew(cid='c1', owner=A, members=None, tag='SIC'):
    return {'id': cid, 'tag': tag, 'name': tag, 'owner': owner, 'members': members or [owner]}


def test_build_produce_collect_upgrade_with_house_tax():
    c = crew()
    fc.build(c, A, 0, 'pizza', NOW)
    assert c['city']['bank'] == fc.START_MP - 150
    with pytest.raises(ValueError):
        fc.build(c, A, 0, 'gas', NOW)
    v = fc.view(c, NOW + 3600)
    assert v['rate'] == 60 and v['stash'] == 60 and v['lots'][0]['func'].startswith('trains')
    got, house = fc.collect(c, A, NOW + 3600)
    assert (got, house) == (57, 3) and v['crew'] == []
    c['city']['bank'] = 100_000
    fc.upgrade(c, A, 0, NOW + 3601)
    assert c['city']['lots']['0']['lvl'] == 2 and fc.rate(c['city']) == pytest.approx(120 * 1.05)   # + the 1-day collect streak
    fc.view(c, NOW + 3601 + 3600 * 100)
    assert c['city']['stash'] <= fc.rate(c['city']) * fc.STASH_HOURS + 0.01


def test_every_store_does_its_job():
    c = crew(members=[A, B, 'C' * 40, 'D' * 40, 'E' * 40])
    city = fc.city_of(c, NOW)
    city['bank'] = 1_000_000
    fc.build(c, A, 0, 'pizza', NOW)
    fc.build(c, A, 1, 'laundry', NOW)
    fc.build(c, A, 2, 'bank', NOW)
    fc.build(c, A, 3, 'gas', NOW)
    assert fc.rate(city) == pytest.approx((60 + 90 + 700 + 75) * 1.05)        # gas: +5 % per level
    bank0 = city['bank']
    fc.accrue(city, NOW + 3600)
    assert city['bank'] > bank0                                             # laundry: some MP skipped the stash
    assert fc.stash_cap(city, 100) == 100 * (fc.STASH_HOURS + 2)            # bank: +2 h per level
    fc.build(c, A, 4, 'mart', NOW + 3600, staff=True)
    assert fc.build_cost('tower', city) == int(6000 * 0.97)                 # mart: −3 %


def test_recruits_level_up_by_training_and_the_creator_builds_anything():
    c = crew()
    city = fc.city_of(c, NOW)
    city['bank'] = 10_000
    fc.build(c, A, 0, 'pizza', NOW)
    fc.hire(c, A, 'guard', NOW)
    with pytest.raises(ValueError):
        fc.hire(c, A, 'spy', NOW)                                           # needs the lab
    fc.accrue(city, NOW + 3600 * 40)                                        # 3 XP an hour × 40 h = 120 XP
    assert city['crew'][0]['lvl'] == 2
    fc.build(c, A, 5, 'tower', NOW, staff=True)
    assert all(x['ok'] and x['cost'] == 0 for x in fc.view(c, NOW, staff=True, mine=True)['catalog'])


def test_old_goon_counts_become_recruits_and_robbery_hurts_on_a_miss():
    a, d = crew('a', A), crew('d', B, tag='RIV')
    a['city'] = {**fc.blank(NOW), 'goons': {'hitter': 2}}
    del a['city']['crew']
    assert len(fc.city_of(a, NOW)['crew']) == 2
    fc.city_of(d, NOW)['stash'] = 1000.0
    rng = random.Random(1)
    res = fc.rob(a, d, A, NOW, rng=rng)
    assert res['win'] in (True, False)
    if not res['win']:
        assert any(r['hurt'] > NOW for r in a['city']['crew'])
    with pytest.raises(ValueError):
        fc.rob(a, d, A, NOW + 60)                                           # cooldown


def test_streak_grows_day_by_day_and_resets():
    c = crew()
    city = fc.city_of(c, NOW)
    for i, d in enumerate((0, 1, 2)):
        city['stash'] = 50.0
        fc.collect(c, A, NOW + d * fc.DAY)
    assert city['streak']['days'] == 3 and fc.streak_bonus(city) == pytest.approx(0.15)
    city['stash'] = 50.0
    fc.collect(c, A, NOW + 9 * fc.DAY)
    assert city['streak']['days'] == 1


def test_casino_is_points_only_and_capped():
    c = crew()
    city = fc.city_of(c, NOW)
    city['bank'] = 100_000
    with pytest.raises(ValueError):
        fc.casino(c, A, 100, NOW)
    fc.build(c, A, 0, 'casino', NOW, staff=True)
    with pytest.raises(ValueError):
        fc.casino(c, A, 10_000, NOW)                                        # over 5 % of the bank
    r = fc.casino(c, A, 1000, NOW, rng=random.Random(3))
    assert r['stake'] == 1000
    with pytest.raises(ValueError):
        fc.casino(c, A, 1000, NOW + 60)                                     # once an hour
