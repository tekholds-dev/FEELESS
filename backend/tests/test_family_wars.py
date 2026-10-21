import pytest
import family_wars as fw

NOW = 1_800_000_000.0


def store():
    return {'crews': {
        'A': {'id': 'A', 'tag': 'AAA', 'name': 'Alpha', 'owner': 'wa', 'members': ['wa', 'wa2']},
        'B': {'id': 'B', 'tag': 'BBB', 'name': 'Bravo', 'owner': 'wb', 'members': ['wb']},
        'C': {'id': 'C', 'tag': 'CCC', 'name': 'Cosa', 'owner': 'wc', 'members': ['wc']},
    }}


def piece(at, usd, cost=10):
    return {'at': at, 'usd': usd, 'costUsd': cost}


def test_a_war_locks_both_stakes_and_the_better_team_takes_the_whole_pot():
    st = store()
    w = fw.challenge(st, 'wa', 'BBB', 100, NOW + 3600, 4, NOW)
    assert st['crews']['A']['chest'] == fw.CHEST_START - 100 and w['state'] == fw.OPEN
    fw.answer(st, 'wb', w['id'], True, 150, NOW + 60)
    assert fw.pot(w) == 250 and st['crews']['B']['chest'] == fw.CHEST_START - 150
    fw.raise_pot(st, 'wa', w['id'], 50, NOW + 120)
    assert fw.pot(w) == 300
    fw.tick(st, {}, NOW + 3600)
    assert w['state'] == fw.LIVE
    pieces = {'wa2': [piece(NOW + 4000, 5)], 'wb': [piece(NOW + 4000, -2)], 'wa': [piece(NOW - 10, 999)]}   # a trade before the bell never counts
    fw.tick(st, pieces, NOW + 3600 + 4 * 3600)
    assert w['state'] == fw.DONE and w['result']['winner'] == 'a'
    assert st['crews']['A']['chest'] == fw.CHEST_START - 150 + 300 and st['crews']['A']['warWins'] == 1 and st['crews']['B']['warLosses'] == 1


def test_a_declined_or_unanswered_call_out_returns_the_stake():
    st = store()
    w = fw.challenge(st, 'wa', 'BBB', 100, NOW + 3600, 1, NOW)
    fw.answer(st, 'wb', w['id'], False, now=NOW)
    assert w['state'] == fw.DECLINED and st['crews']['A']['chest'] == fw.CHEST_START
    w2 = fw.challenge(st, 'wa', 'CCC', 80, NOW + 3600, 1, NOW)
    fw.tick(st, {}, NOW + 3600)
    assert w2['state'] == fw.VOID and st['crews']['A']['chest'] == fw.CHEST_START


def test_nobody_traded_is_a_draw_and_every_stake_goes_home():
    st = store()
    w = fw.challenge(st, 'wa', 'BBB', 100, NOW + 3600, 1, NOW)
    fw.answer(st, 'wb', w['id'], True, 100, NOW)
    fw.tick(st, {}, NOW + 3600)
    fw.tick(st, {}, NOW + 7200)
    assert w['result']['winner'] is None and st['crews']['A']['chest'] == fw.CHEST_START and st['crews']['B']['chest'] == fw.CHEST_START


def test_an_ally_joins_a_side_and_shares_the_pot_by_its_stake():
    st = store()
    assert fw.ally(st, 'wa', 'CCC', NOW) == 'asked' and fw.ally(st, 'wc', 'AAA', NOW) == 'sealed'
    w = fw.challenge(st, 'wb', 'AAA', 100, NOW + 3600, 1, NOW)
    fw.answer(st, 'wa', w['id'], True, 100, NOW)
    fw.join_side(st, 'wc', w['id'], 100, NOW)
    assert fw.pot(w) == 300 and w['allies']['b'] == ['C']
    fw.tick(st, {}, NOW + 3600)
    fw.tick(st, {'wc': [piece(NOW + 4000, 3)]}, NOW + 7200)
    assert w['result']['winner'] == 'b'
    assert st['crews']['A']['chest'] == fw.CHEST_START - 100 + 150 and st['crews']['C']['chest'] == fw.CHEST_START - 100 + 150


def test_only_the_head_acts_and_the_rules_hold():
    st = store()
    with pytest.raises(ValueError):
        fw.challenge(st, 'wa2', 'BBB', 100, NOW + 3600, 1, NOW)        # not the Don
    with pytest.raises(ValueError):
        fw.challenge(st, 'wa', 'AAA', 100, NOW + 3600, 1, NOW)         # itself
    with pytest.raises(ValueError):
        fw.challenge(st, 'wa', 'BBB', 100, NOW + 60, 1, NOW)           # bell too soon
    with pytest.raises(ValueError):
        fw.challenge(st, 'wa', 'BBB', 9999, NOW + 3600, 1, NOW)        # over the stake cap
    with pytest.raises(ValueError):
        fw.challenge(st, 'wa', 'BBB', 100, NOW + 3600, 3, NOW)         # length not on the list


def test_member_ranks_follow_the_week():
    c = {'owner': 'd', 'members': ['d', 'a', 'b', 'c', 'e', 'f', 'g']}
    st = {'a': {'usd': 9, 'trades': 2}, 'b': {'usd': 5, 'trades': 1}, 'c': {'usd': 1, 'trades': 1}, 'e': {'usd': 0, 'trades': 1}, 'f': {'usd': -3, 'trades': 2}}
    r = fw.ranks(c, st)
    assert r['d'][0] == 'don' and r['a'][0] == 'underboss' and r['b'][0] == 'consigliere' and r['c'][0] == 'capo' and r['e'][0] == 'capo'
    assert r['f'][0] == 'soldier' and r['g'][0] == 'associate'
