import arena as ar


def test_the_level_curve_and_what_each_level_unlocks():
    assert ar.level_of(0) == {'level': 1, 'into': 0, 'need': 600, 'total': 0}
    assert ar.level_of(600)['level'] == 2 and ar.level_of(600 + 850)['level'] == 3 and ar.level_of(10 ** 9)['level'] == ar.MAX_LEVEL
    u1, u10 = ar.unlocked(1), ar.unlocked(10)
    assert u1['guns'] == ['rifle'] and u1['parts']['optic'] == ['iron'] and 'sniper' in u10['guns'] and 'scope' in u10['parts']['optic']


def test_a_loadout_only_wears_what_the_level_owns_and_the_stats_follow_the_parts():
    assert ar.clean_loadout({'gun': 'sniper', 'optic': 'scope', 'skin': 'gold'}, 1) == ar.DEFAULT        # locked → default
    lo = ar.clean_loadout({'gun': 'smg', 'barrel': 'long', 'mag': 'ext', 'optic': 'dot', 'skin': 'pink'}, 6)
    assert lo == {'gun': 'smg', 'barrel': 'long', 'optic': 'dot', 'mag': 'ext', 'stock': 'std', 'skin': 'pink'}
    s = ar.stats(lo); base = ar.GUNS['smg']
    assert s['mag'] == 48 and s['range'] > base['range'] and s['spread'] < base['spread'] and s['zoom'] == 1.45
    assert ar.stats({'gun': 'nope'})['name'] == 'FX-7 RIFLE'


def test_match_results_are_checked_and_pay_xp():
    assert ar.check(10, 3, 4, 180) is None
    assert 'short' in ar.check(1, 0, 0, 5) and 'headshots' in ar.check(2, 0, 3, 120) and 'clock' in ar.check(200, 0, 0, 60) and ar.check(1, 0, 0, 60, 'x') == 'Unknown mode.'
    assert ar.match_xp(10, 4, True) == 50 + 1000 + 200 + 400
    players = {'W1': {'name': 'Sal', 'tag': 'FRT', 'xp': 5000, 'day': {'date': 'D', 'xp': 900, 'kills': 7}}, 'tg:2': {'name': 'Vito', 'xp': 100, 'day': {'date': 'old', 'xp': 9999}}}
    b = ar.board(players, 'D')
    assert [r['name'] for r in b] == ['Sal'] and b[0]['level'] == ar.level_of(5000)['level']
    assert 'LEVEL 10' in ar.level_post('Sal', 'FRT', 10, 'sniper') and 'WHALE HUNTER' in ar.level_post('Sal', 'FRT', 10, 'sniper')
