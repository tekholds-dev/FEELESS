import pytest
import family_room as fr

NOW = 1_800_000_000.0
A, B, C = 'A' * 40, 'B' * 40, 'C' * 40


def crew():
    return {'owner': A, 'members': [A, B, C], 'created': NOW - 10 * 86400}


def pc(at, usd, ret, sym='X'):
    return {'at': at, 'usd': usd, 'costUsd': 10, 'ret': ret, 'symbol': sym}


def test_only_the_don_sets_roles_and_one_underboss_at_a_time():
    c = crew()
    with pytest.raises(ValueError):
        fr.set_role(c, B, C, role='scout')
    fr.set_role(c, A, B, role='hitter', rank='underboss')
    fr.set_role(c, A, C, rank='underboss')
    assert c['roles'][C]['rank'] == 'underboss' and 'rank' not in c['roles'][B] and c['roles'][B]['role'] == 'hitter'
    with pytest.raises(ValueError):
        fr.set_role(c, A, A, rank='capo')
    with pytest.raises(ValueError):
        fr.set_role(c, A, B, role='boss')
    fr.set_role(c, A, B, role='')
    assert B not in c['roles']


def test_promotions_sit_on_top_of_the_auto_ladder():
    c = crew(); fr.set_role(c, A, C, rank='consigliere')
    out = fr.ranks(c, {A: ('don', 'Don'), B: ('underboss', 'U'), C: ('associate', 'As')})
    assert out[C][0] == 'consigliere' and out[A][0] == 'don' and out[B][0] == 'underboss'


def test_member_activity_and_family_vitals():
    c = crew()
    hot = [pc(NOW - 3600 * i, 2, 0.2, f'S{i}') for i in range(6)]
    quiet = [pc(NOW - 5 * 86400, -1, -0.1)]
    m = {A: fr.member(c, A, hot, NOW), B: fr.member(c, B, quiet, NOW), C: fr.member(c, C, [], NOW)}
    assert m[A]['status'] == 'fire' and m[A]['streak'] == 6 and m[A]['last']['sym'] == 'S0' and m[A]['best']['pct'] == 20.0
    assert m[B]['status'] == 'quiet' and m[B]['heat'] < 25 and m[C]['trades'] == 0
    v = fr.vitals(c, m, NOW, {'wins': 2, 'losses': 0})
    assert v['trades'] == 7 and v['active'] == 1 and v['hot']['w'] == A and v['streak']['n'] == 6 and 0 <= v['respect'] <= 100
    w = fr.wire({A: hot, B: quiet}, {A: ('don', '🎩 Don')}, lambda x: x[:2])
    assert w[0]['sym'] == 'S0' and w[0]['rank'] == '🎩 Don' and len(w) == 7
