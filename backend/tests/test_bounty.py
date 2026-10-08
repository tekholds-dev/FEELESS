import bounty as bo


def _rec(*reports):
    return {'mints': {}, 'reported': True, 'reports': [{'mint': m, 'role': role, 'by': by, 'at': at} for m, role, by, at in reports]}


def test_the_first_reporter_of_a_wallet_is_its_finder():
    bl = {'W1': _rec(('M1', 'bundler', 'alice', 100), ('M1', 'bundler', 'bob', 200)),    # bob only confirmed it
          'W2': _rec(('M1', 'sniper', 'bob', 150)),
          'W3': _rec(('M2', 'sniper', 'anon', 50))}                                       # anonymous reports never rank
    fs = {f['wallet']: f['by'] for f in bo.finds(bl)}
    assert fs == {'W1': 'alice', 'W2': 'bob', 'W3': 'anon'}
    b = bo.board(bl, now=1000)
    assert b['total'] == {'coins': 1, 'wallets': 2}
    assert b['recent'][0]['mint'] == 'M1' and b['recent'][0]['wallets'] == 2 and b['recent'][0]['bundlers'] == 1 and b['recent'][0]['snipers'] == 1


def test_points_follow_the_award_rule_25_each_capped_at_100_a_coin():
    assert bo.points(1) == 25 and bo.points(3) == 75 and bo.points(9) == 100
    bl = {f'W{i}': _rec(('M1', 'bundler', 'alice', 100 + i)) for i in range(6)}
    bl['X'] = _rec(('M2', 'sniper', 'alice', 90))
    top = bo.board(bl, now=1000)['all'][0]
    assert top == {'by': 'alice', 'wallets': 7, 'coins': 2, 'pts': 125}                    # 100 (capped) + 25


def test_the_week_board_only_counts_recent_finds_and_events_feed_the_quest():
    day = 86400
    bl = {'OLD': _rec(('M1', 'bundler', 'alice', 10)), 'NEW': _rec(('M2', 'bundler', 'alice', 20 * day))}
    b = bo.board(bl, now=21 * day)
    assert [r['wallets'] for r in b['week']] == [1] and [r['wallets'] for r in b['all']] == [2]
    assert bo.find_events(bl, {'alice', 'alice2'}) == [10, 20 * day] and bo.find_events(bl, {'bob'}) == []
