"""🤝 Alliances: at most 10, one per wallet, a Union only after the owner's days."""
import pytest

import alliances as al


def test_ten_members_at_most_and_one_alliance_per_wallet():
    rows = []
    a = al.create(rows, 'w0', 'The Crew', 100, 'msg1')
    assert a['from'] == 'msg1'
    for i in range(1, 10):
        al.join(rows, f'w{i}', a['id'])
    with pytest.raises(ValueError, match='full'):
        al.join(rows, 'w10', a['id'])
    with pytest.raises(ValueError, match='already'):
        al.create(rows, 'w1', 'Another', 100)
    with pytest.raises(ValueError, match='taken'):
        al.create(rows, 'x', 'the crew', 100)
    with pytest.raises(ValueError, match='3 characters'):
        al.create(rows, 'x', 'a', 100)


def test_a_union_waits_for_the_owners_days_and_only_the_founder_can_found_it():
    rows = []
    a = al.create(rows, 'f', 'The Crew', 0)
    al.join(rows, 'm', a['id'])
    with pytest.raises(ValueError, match='after 30 days'):
        al.found_union(rows, 'f', 'Big Union', 30, 86400)
    with pytest.raises(ValueError, match='founder'):
        al.found_union(rows, 'm', 'Big Union', 30, 31 * 86400)
    assert al.found_union(rows, 'f', 'Big Union', 30, 31 * 86400)['union']['name'] == 'Big Union'
    with pytest.raises(ValueError, match='already'):
        al.found_union(rows, 'f', 'Again', 30, 32 * 86400)


def test_leaving_passes_it_on_and_the_last_one_out_closes_it():
    rows = []
    a = al.create(rows, 'f', 'The Crew', 0)
    al.join(rows, 'm', a['id'])
    al.leave(rows, 'f')
    assert a['founder'] == 'm' and rows
    al.leave(rows, 'm')
    assert rows == []
    with pytest.raises(ValueError, match='not in'):
        al.leave(rows, 'm')


def test_the_public_view_never_shows_a_whole_wallet():
    rows = []
    a = al.create(rows, 'ABCDEFGHIJKLMNOP', 'The Crew', 0)
    v = al.public(a, 30, 10, 'ABCDEFGHIJKLMNOP')
    assert v['members'] == ['ABCD…MNOP'] and v['mine'] and v['founder'] and not v['ready']
