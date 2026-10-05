import arena_league as lg


def card(k, n=4):
    return {'key': k, 'name': k.upper(), 'legs': [{'pairAddress': f'{k}{i}'} for i in range(n)]}


def test_field_is_capped_like_the_playground_and_everyone_starts_at_20():
    s = lg.new_season([card(f'c{i}') for i in range(12)] + [card('c1')], 1, 0)
    assert len(s['field']) == lg.FIELD_MAX == 8 and s['rounds'] == 7
    assert all(r['hist'] == [20.0] for r in s['field'])


def test_points_table_and_no_rematch():
    s = lg.new_season([card(k) for k in 'abcd'], 1, 0)
    p1 = lg.pair_round(s)
    assert len(p1) == 2
    res = [{'aKey': a, 'bKey': b, 'winnerKey': a, 'draw': False} for a, b in p1]
    s = lg.settle(s, res, {r['key']: 21.0 for r in s['field']})
    assert s['round'] == 1 and sorted(r['pts'] for r in s['field']) == [0, 0, 3, 3]
    p2 = {frozenset(p) for p in lg.pair_round(s)}
    assert not p2 & {frozenset(p) for p in p1}            # nobody meets the same card twice while another pairing exists


def test_cards_at_one_dollar_or_down_75_in_3_rounds_are_cycled_for_playground_cards():
    s = lg.new_season([card(k) for k in 'abcd'], 1, 0)
    for r in s['field']:
        r['hist'] = {'a': [20, 19, 18, 21], 'b': [20, 3, 0.9], 'c': [20, 20, 8, 4.5], 'd': [20, 30, 25, 22]}[r['key']]
    s, moves = lg.cycle(s, [card('a'), card('pg1'), card('pg2')], 10)
    keys = [r['key'] for r in s['field']]
    assert sorted(m['outKey'] for m in moves) == ['b', 'c'] and 'pg1' in keys and 'pg2' in keys and 'a' in keys
    assert next(r for r in s['field'] if r['key'] == 'pg1')['hist'] == [20.0]
    assert 'lost 78%' in next(m['why'] for m in moves if m['outKey'] == 'c')


def test_season_ends_after_its_rounds_and_crowns_points_then_money():
    s = lg.new_season([card(k) for k in 'ab'], 3, 0)
    for _ in range(lg.ROUNDS):
        s = lg.settle(s, [{'aKey': 'a', 'bKey': 'b', 'draw': True}], {'a': 25.0, 'b': 22.0})
    assert lg.done(s) and lg.champion(s)['key'] == 'a'          # equal points → bigger book wins


def test_paper_tier_cards_start_over_on_20_once_and_real_cards_are_untouched():
    import asyncio, pytest
    rs = pytest.importorskip('reputation_service')
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {'sizeUsd': 100}, 'cards': {'degen': {'label': 'Blaze', 'real': True, 'startUsd': 10},
                                                                                'gold': {'label': 'Gold', 'startUsd': 100, 'putInUsd': 100}}}})
    assert asyncio.run(rs._prime_reset_paper(1.0)) == 1
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert set(pr['cards']) == {'degen'} and pr['cfg']['sizeUsd'] == 20.0 and pr['archive'][-1]['cards']['gold']['startUsd'] == 100
    assert asyncio.run(rs._prime_reset_paper(2.0)) == 0          # once only
