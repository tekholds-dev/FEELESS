from intel_desk import build_actors, threat, rings, next_moves, snapshot, check

NOW = 1_000_000_000
H = 3600


def world():
    block = {'S1': {'mints': {'m1': 'sniper', 'm2': 'sniper'}, 'firstSeen': NOW - 10 * H, 'lastSeen': NOW - H},
             'B1': {'mints': {'m1': 'bundler'}, 'firstSeen': NOW - 20 * H, 'lastSeen': NOW - 20 * H},
             'SAFE': {'mints': {'m1': 'sniper'}}}
    funders = {'funders': {'F': {'mints': {'m1': True, 'm2': True}, 'funded': ['S1', 'B1'], 'firstSeen': NOW - 30 * H, 'lastSeen': NOW - 2 * H}},
               'offenderFunder': {'S1': 'F', 'B1': 'F'}}
    creators = {'R': {'rugged': 2, 'dumped': 1, 'launches': 5, 'launchTimes': [NOW - 40 * H, NOW - 30 * H, NOW - 20 * H, NOW - 10 * H]}}
    return build_actors(block, funders, creators, protected={'SAFE'})


def test_actors_roles_and_protected():
    a = world()
    assert set(a) == {'S1', 'B1', 'F', 'R'}
    assert a['S1']['roles'] == {'sniper': 2} and a['S1']['fundedBy'] == 'F'
    assert a['F']['roles']['funder'] == 2 and a['F']['funded'] == ['B1', 'S1']
    assert a['R']['roles'] == {'rugger': 2, 'dumper': 1}


def test_threat_is_cited():
    a = world()
    score, ev = threat(a['R'])
    assert score > threat(a['S1'])[0] and all(e['claim'] and e['source'] for e in ev)


def test_rings_group_funder_and_puppets():
    rg = rings(world())
    assert len(rg) == 1 and rg[0]['core'] == 'F' and rg[0]['members'] == ['B1', 'F', 'S1'] and rg[0]['launchesHit'] == 2


def test_next_moves():
    a = world()
    due = next_moves(a['R'], NOW)[0]
    assert due['move'] == 'Next launch due' and due['eta'] == NOW
    assert any(m['move'].startswith('Loading fresh wallets') for m in next_moves(a['F'], NOW))
    assert any(m['move'] == 'Active right now' for m in next_moves(a['S1'], NOW))


def test_snapshot_and_check():
    a = world()
    s = snapshot(a, NOW)
    assert s['totals']['actors'] == 4 and s['totals']['rings'] == 1 and s['wanted'][0]['threat'] >= s['wanted'][-1]['threat']
    c = check(s['index'], rings(a), ['S1', 'nobody'])
    assert list(c['known']) == ['S1'] and c['rings'][0]['core'] == 'F'
