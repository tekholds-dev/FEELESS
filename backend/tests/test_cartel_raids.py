import family_world as fw


def test_cartels_are_raidable_from_any_city_families_still_need_reach():
    w = fw.blank()
    w['own']['harbor-2'] = 'fam-a'; w['home']['fam-a'] = 'harbor-2'           # Pump Harbor → Cartel Docks is 2+ bridges
    assert fw.hops('harbor', 'docks') >= 2
    assert not fw.reach(w, 'fam-a', 'docks')                                     # a family / CPU town over there: out of reach
    assert not fw.can_raid(w, 'fam-a', 'docks', 'family')
    assert fw.can_raid(w, 'fam-a', 'docks', 'cartel')                            # ⚖ the rep's bad guys: from anywhere
    assert fw.can_raid(w, 'fam-a', 'harbor', 'family')                           # your own borough still works


def test_every_cartel_has_a_raidable_town_even_without_a_building():
    wallets = {f'W{i}': {'mints': {f'M{i % 4}{j}': 'sniper' for j in range(4)}, 'strikes': 10 + i, 'lastSeen': 0} for i in range(30)}
    cs = fw.cartels(wallets, now=1e9)
    assert cs and all(c['kind'] == 'cartel' and c['borough'] == 'docks' for c in cs)
    for c in cs:                                                                 # a board to raid exists for each one (lots + guards)
        t = fw.cartel_town(c)
        assert t['lots'] and t['guards']
