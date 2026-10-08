import pytest
import crews as cr


def test_create_join_leave_with_one_crew_each_and_a_member_cap():
    st = {}
    c = cr.create(st, 'A', 'Degen Dogs', 'dd', 1)
    assert c['tag'] == 'DD' and c['members'] == ['A'] and st['by']['A'] == c['id'] and len(c['code']) >= 6
    with pytest.raises(ValueError): cr.create(st, 'A', 'Another', 'AN', 2)            # one crew each
    with pytest.raises(ValueError): cr.create(st, 'B', 'degen dogs', 'XX', 2)          # names are unique, any case
    with pytest.raises(ValueError): cr.create(st, 'B', 'Other', 'dd', 2)               # tags are unique
    cr.join(st, 'B', c['code'])
    assert c['members'] == ['A', 'B']
    with pytest.raises(ValueError): cr.join(st, 'B', c['code'])                        # already in
    with pytest.raises(ValueError): cr.join(st, 'Z', 'nope')                           # unknown code
    for w in 'CDE': cr.join(st, w, c['code'])
    assert len(c['members']) == 5 and c['seats'] == 5                                    # $25 buys 5 seats including the owner
    with pytest.raises(ValueError): cr.join(st, 'F', c['code'])                        # full
    cr.leave(st, 'A')                                                                   # the owner leaves → the longest-standing member leads
    assert c['owner'] == 'B' and 'A' not in st['by']
    with pytest.raises(ValueError): cr.leave(st, 'A')


def test_the_last_member_leaving_disbands_the_crew_and_bad_names_are_refused():
    st = {}; c = cr.create(st, 'A', 'Solo', 'SO', 1)
    assert cr.leave(st, 'A') == {} and st['crews'] == {} and st['by'] == {}
    for bad in ('ab', 'x' * 21, '<script>'):
        with pytest.raises(ValueError): cr.clean_name(bad)
    for bad in ('A', 'ABCDE', 'a!'):
        with pytest.raises(ValueError): cr.clean_tag(bad)


def _p(usd, cost, at):
    return {'usd': usd, 'costUsd': cost, 'at': at}


def test_the_board_ranks_on_verified_weekly_results_and_leaves_thin_crews_unranked():
    st = {}
    a = cr.create(st, 'A1', 'Alpha', 'AL', 1); cr.join(st, 'A2', a['code'])
    b = cr.create(st, 'B1', 'Bravo', 'BR', 1); cr.join(st, 'B2', b['code'])
    c = cr.create(st, 'C1', 'Solo', 'SO', 1)                                              # one member: never ranked
    now = 10 * 86400
    pcs = {'A1': [_p(1, 10, now - 100)] * 3, 'A2': [_p(-0.5, 10, now - 200)] * 3,          # alpha: 6 trades, +3 − 1.5 on $60 = +2.5%
           'B1': [_p(2, 10, now - 300)] * 3, 'B2': [_p(1, 10, now - 400)] * 3,             # bravo: +9 on $60 = +15%
           'C1': [_p(50, 10, now - 50)] * 9,
           'A9': [_p(999, 1, 1)]}                                                         # old (outside the week) and not a member
    rows = cr.board(st, pcs, now)
    assert [r['name'] for r in rows] == ['Bravo', 'Alpha', 'Solo']
    assert rows[0]['pct'] == 15.0 and rows[0]['ranked'] and rows[1]['pct'] == 2.5 and rows[2]['ranked'] is False
    assert rows[0]['active'] == 2 and rows[0]['wonPct'] == 100


def test_a_crew_costs_25_with_5_seats_and_each_5_more_seats_cost_5_never_reusing_a_payment():
    assert cr.price('create') == 25.0 and cr.price('seats') == 5.0 and cr.price('create', {'createUsd': 30}) == 30.0
    st = {}
    c = cr.create(st, 'A', 'Paid Crew', 'PC', 1, paid={'sig': 'S1', 'usd': 25.0, 'at': 1, 'kind': 'create'})
    assert c['seats'] == 5 and c['paid'][0]['usd'] == 25.0 and cr.sig_used(st, 'S1') and not cr.sig_used(st, 'S2')
    for w in 'BCDE': cr.join(st, w, c['code'])
    with pytest.raises(ValueError) as e: cr.join(st, 'F', c['code'])
    assert '$5' in str(e.value)                                                         # the refusal says what adding seats costs
    with pytest.raises(ValueError): cr.add_seats(st, 'B', {'sig': 'X', 'usd': 5, 'at': 2})   # only the owner buys seats
    cr.add_seats(st, 'A', {'sig': 'S2', 'usd': 5.0, 'at': 2, 'kind': 'seats'})
    assert c['seats'] == 10 and cr.sig_used(st, 'S2') and len(c['paid']) == 2
    cr.join(st, 'F', c['code'])                                                         # the 6th member fits now
    assert [r['seats'] for r in cr.board(st, {}, 10)] == [10]


def test_check_new_refuses_before_anyone_pays():
    st = {}
    cr.create(st, 'A', 'Taken', 'TK', 1)
    for owner, name, tag in (('A', 'Other', 'OT'), ('B', 'taken', 'XX'), ('B', 'Fresh', 'tk'), ('B', 'x', 'ZZ')):
        with pytest.raises(ValueError): cr.check_new(st, owner, name, tag)
    assert cr.check_new(st, 'B', ' Fresh  Crew ', 'fc') == ('Fresh Crew', 'FC')
