import pump_calls as pc

M1 = '5eWFHPqUtDo8o7ZnSLHZK7DEF7VPU8pUQLj1RQ4Vpump'
M2 = '8NCievmJCg2d9Vc2TWgz2HkE6ANeSX7kwvdq5AL7pump'
NOW = 1791502200000.0


def _coin(mint, user, cid, views=100, at='2026-10-08T23:28:37.485Z', mc=6736, mult=1.9, verified=False, thesis='ca is posted', **kw):
    return {'coinMint': mint, 'coinName': 'Pump Lineage', 'symbol': 'Lineage', 'coinImage': 'https://ipfs.io/ipfs/x', 'marketCap': 12000, 'chain': 'solana',
            'position': {'userName': user, 'isVerified': verified, 'xUsername': user, 'totalCallouts': 8, 'valueUsd': 394.7, 'pnlPercentage': 141.5,
                         'callout': {'calloutId': cid, 'assetClass': 'ASSET_CLASS_TOKEN', 'calledOutAtMcap': mc, 'multiple': mult, 'maxMultiplier': 2.0, 'thesis': thesis,
                                     'calloutTimestamp': at, 'likes': 2, 'viewCount': views, 'replyCount': 1, 'commentCount': 0, 'repostCount': 0}}, **kw}


def test_board_groups_calls_by_coin_and_ranks_the_loudest_first():
    home = {'coins': [_coin(M1, 'a', 'c1', views=700), _coin(M1, 'b', 'c2', views=50, mc=9000, verified=True), _coin(M2, 'z', 'c3', views=10, at='2026-10-08T12:00:00Z')]}
    new = {'coins': [_coin(M1, 'a', 'c1', views=700), _coin(M1, 'c', 'c4', views=5)]}   # c1 again: one callout is one callout
    b = pc.board(home, new, None, NOW)
    assert b['n'] == 4 and [c['mint'] for c in b['coins']] == [M1, M2]
    c = b['coins'][0]
    assert (c['calls'], c['callers'], c['verified'], c['views'], c['firstMc']) == (3, 3, 1, 755, 6736)
    assert c['lead']['user'] == 'a' and c['lead']['mult'] == 1.9 and c['heat'] > b['coins'][1]['heat']
    assert b['latest'][0]['at'] >= b['latest'][-1]['at']
    assert pc.label(c) == '📣 3 callers · called at $6.7K → 1.9×'
    assert pc.summary(c)['lead']['thesis'] == 'ca is posted' and pc.summary({}) is None


def test_bad_rows_never_get_through_and_thesis_is_cleaned():
    long = 'x' * 400 + '\n\x00<script>'
    home = {'coins': ['n', _coin('not a mint', 'a', 'c1'), {'coinMint': M1, 'position': {'callout': None}}, _coin(M2, 'q', 'c9', thesis=long),
                      {**_coin(M1, 'e', 'c8'), 'chain': 'base'}, _coin(M1, 'p', 'c7', coinImage='javascript:alert(1)')]}
    b = pc.board(home, 'nonsense', {'entries': 'no'}, NOW)
    assert [c['mint'] for c in b['coins']] == [M1, M2] or [c['mint'] for c in b['coins']] == [M2, M1]
    by = {c['mint']: c for c in b['coins']}
    assert len(by[M2]['lead']['thesis']) <= pc.THESIS_MAX and '\n' not in by[M2]['lead']['thesis'] and '\x00' not in by[M2]['lead']['thesis']
    assert by[M1]['calls'] == 1 and by[M1]['logo'] is None   # the other-chain call is dropped; a non-https image is dropped
    assert pc.board(None, None, None, NOW) == {'coins': [], 'top': [], 'latest': [], 'n': 0, 'calls': []}


def test_top_callouts_come_from_the_leaderboard_with_the_callers_profit():
    top = {'entries': [{'rank': 1, 'coinMint': M2, 'username': 'OneEyeddd', 'isVerified': False, 'pnlUsd': 63182.1, 'pnlPercentage': 239.2, 'valueUsd': 11228.5, 'isExited': False,
                        'callout': {'calloutId': 't1', 'assetClass': 'ASSET_CLASS_TOKEN', 'calledOutAtMcap': 1061646, 'multiple': 0.895, 'thesis': 'gem', 'calloutTimestamp': '2026-10-08T01:15:41.913Z', 'viewCount': 6809}},
                       {'rank': 2, 'coinMint': M1, 'callout': {'calloutId': 't2', 'assetClass': 'ASSET_CLASS_PERP'}}]}
    b = pc.board({'coins': [_coin(M2, 'z', 'c3')]}, None, top, NOW)
    assert len(b['top']) == 1   # a perp callout is not a coin callout
    t = b['top'][0]
    assert (t['rank'], t['user'], t['pnlUsd'], t['pnlPct'], t['atMc'], t['mult'], t['symbol']) == (1, 'OneEyeddd', 63182.1, 239.2, 1061646, 0.9, 'Lineage')


def test_heat_is_bounded_and_a_called_coin_becomes_a_feed_candidate():
    assert pc.heat(0, 0, 0, 1e9) == 3 and pc.heat(50, 1e9, 9, 0) == 100
    assert pc.heat(3, 2000, 1, 5) > pc.heat(3, 2000, 1, 300)   # a fresh call is louder than an old one
    c = pc.candidate({'mint': M1, 'symbol': 'L', 'callers': 3, 'mcap': 12000})
    assert c['launchpad'] == 'pump' and c['pumpCalls'] == 3 and c['mover'] is True and c['url'].endswith(M1)
    assert pc.candidate({'mint': 'bad mint'}) is None


def _call(user, cid, mins_ago, mult, mint=M1, mcap=20000, at_mc=10000):
    return {'id': cid, 'user': user, 'mint': mint, 'symbol': 'L', 'at': NOW - mins_ago * 60000, 'mult': mult, 'atMc': at_mc, 'mcap': mcap}


def test_a_caller_is_proven_only_on_calls_judged_an_hour_later():
    st = pc.caller_track({}, [_call('ace', f'a{i}', 90, m) for i, m in enumerate((2.0, 1.5, 0.8))] + [_call('ace', 'a9', 5, 9.0), _call('rug', 'r1', 90, 0.2), _call('rug', 'r2', 70, 0.4), _call('rug', 'r3', 61, 3.0)], NOW)
    b = pc.caller_board(st)
    assert b['ace'] == {'n': 3, 'medMult': 1.5, 'wonPct': 67, 'best': 2.0, 'proven': True}   # the 5-minute-old 9× call is not judged yet
    assert b['rug']['proven'] is False and b['rug']['medMult'] == 0.4
    st2 = pc.caller_track(st, [_call('ace', 'a0', 200, 0.1)], NOW + 60000)   # a judged call keeps its result, whatever the coin does later
    assert pc.caller_board(st2)['ace']['medMult'] == 1.5
    st3 = pc.caller_track({'new': {'seen': NOW, 'calls': {'n1': {'mint': M1, 'at': NOW - 30 * 60000, 'mult': 1.7}}}}, [], NOW + 40 * 60000)
    assert st3['new']['calls']['n1']['res'] == 1.7   # left the feed before the hour: its last reading stands
    assert pc.caller_track({'old': {'seen': NOW - 8 * 86400000, 'calls': {'x': {'at': 1, 'res': 2}}}}, [], NOW) == {}
    board = pc.mark_pros({'coins': [{'mint': M1, 'users': ['ace', 'rug', 'zed']}, {'mint': M2, 'users': ['rug']}]}, b)
    assert (board['coins'][0]['pro'], board['coins'][0]['pros'], board['coins'][1]['pro']) == (1, ['ace'], 0)
    assert [r['user'] for r in pc.leaders(b)] == ['ace', 'rug'] and pc.summary({'mint': M1, 'pro': 1, 'pros': ['ace']})['pro'] == 1


def test_a_call_rush_needs_three_different_callers_in_ten_minutes_under_the_owners_cap():
    calls = [_call('a', '1', 2, 1.1), _call('b', '2', 4, 1.0), _call('c', '3', 9, 1.2), _call('a', '4', 1, 1.0), _call('d', '5', 30, 1.0),
             _call('x', '6', 1, 1, mint=M2), _call('y', '7', 2, 1, mint=M2)]
    assert pc.rush(calls, NOW, 50000) == [{'mint': M1, 'symbol': 'L', 'callers': 3, 'mcap': 20000, 'firstMc': 10000}]
    assert pc.rush(calls, NOW, 15000) == [] and pc.rush(calls, NOW, 0) == []   # over the cap · alert off
    assert pc.RUSH_CAPS_K[0] == 0
