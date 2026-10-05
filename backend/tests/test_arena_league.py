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


def test_real_money_cards_always_get_a_seat_on_top_of_the_8_and_join_mid_season():
    import arena_league as lg
    cards = [{'key': f'user:{i}', 'name': f'C{i}', 'legs': [{'pairAddress': 'P'}]} for i in range(10)] + [{'key': 'prime:degen', 'name': 'Blaze', 'legs': [{'pairAddress': 'Q'}]}]
    s = lg.new_season(cards, 1, 0.0, must=['prime:degen'])
    keys = [r['key'] for r in s['field']]
    assert 'prime:degen' in keys and len(keys) == lg.FIELD_MAX + 1                     # the real card never takes one of the 8 seats
    s2 = lg.new_season(cards[:10], 2, 0.0)
    s2, joined = lg.ensure(s2, cards, ['prime:degen'], 50.0)
    assert joined == ['prime:degen'] and s2['field'][-1]['hist'] == [lg.START_USD]     # funded mid-season → in at once on $20
    assert lg.ensure(s2, cards, ['prime:degen'], 60.0)[1] == []                         # only once


def test_a_game_is_six_duels_most_sparks_wins_and_the_card_move_breaks_a_tie():
    import pg_battle as pgb
    def book(moves, usd=None):
        legs = [{'pairAddress': f'P{n}', 'symbol': n, 'usd': (usd or {}).get(n, 10 - i), 'entry': 1.0, 'mid': 1.0, 'units': 1} for i, n in enumerate(moves)]
        return {'legs': legs, 'px': {f'P{n}': 1 + m / 100 for n, m in moves.items()}}
    bell = lambda b: {l['pairAddress']: 1.0 for l in b['legs']}
    a = book({'A1': 5, 'A2': -2, 'A3': 1, 'A4': 0, 'A5': 9, 'A6': -1})
    b = book({'B1': 3, 'B2': 4, 'B3': -3, 'B4': 0.02, 'B5': 2, 'B6': -6})
    d = pgb.duels(a, b, bell(a), bell(b))
    assert [x['win'] for x in d['seats']] == ['a', 'b', 'a', None, 'a', 'a'] and (d['a'], d['b']) == (4, 1)        # seat 4 is a tie: no spark
    assert d['liveWire'] == {'symbol': 'A5', 'pct': 9.0, 'side': 'a'} and d['blownFuse']['symbol'] in ('B5', 'A2') and d['overload'] is None
    assert pgb.duel_winner(d, -1.0, 2.0) == 'a'                                                                     # sparks decide, not the card's total
    sweep = pgb.duels(book({'X': 3, 'Y': 2, 'Z': 1}), book({'Q': 0, 'R': 0, 'S': 0}), {'PX': 1, 'PY': 1, 'PZ': 1}, {'PQ': 1, 'PR': 1, 'PS': 1})
    assert sweep['overload'] == 'a' and (sweep['a'], sweep['b']) == (3, 0)
    level = {'a': 2, 'b': 2}
    assert pgb.duel_winner(level, 1.5, 0.4) == 'a' and pgb.duel_winner(level, 0.4, 1.5) == 'b' and pgb.duel_winner(level, 1.0, 1.01) == 'draw'
    assert pgb.duel_winner(None, 2.0, 1.0) == 'a'                                                                   # no duel data → the old rule
    # seats go by size (biggest coin = seat 1); a card with fewer coins fields fewer seats; a coin subbed in mid-game starts at its entry
    small = book({'S1': 1, 'S2': 1}); big = book({'L1': 0, 'L2': 0, 'L3': 50})
    assert len(pgb.duels(small, big, bell(small), bell(big))['seats']) == 2
    subbed = book({'N': 10}); subbed['legs'][0]['mid'] = 1.05
    s = pgb.duels(subbed, book({'O': 0}), {'POLD': 1.0}, {'PO': 1.0})
    assert s['seats'][0]['a']['sub'] and s['seats'][0]['a']['pct'] == round((1.10 / 1.05 - 1) * 100, 2)
    assert pgb.duels({'legs': []}, b, {}, bell(b)) is None
    assert pgb.seat_prices(a, {'PA1': 2.0})['PA1'] == 2.0 and pgb.seat_prices(a)['PA2'] == 0.98


def test_sparks_split_cards_level_on_points_in_the_table():
    import arena_league as lg
    s = {'field': [{'key': k, 'w': 0, 'l': 0, 'd': 0, 'pts': 0, 'hist': [20.0]} for k in ('A', 'B', 'C', 'D')], 'played': [], 'round': 0}
    s = lg.settle(s, [{'aKey': 'A', 'bKey': 'B', 'winnerKey': 'A', 'sparks': [4, 2]}, {'aKey': 'C', 'bKey': 'D', 'winnerKey': 'C', 'sparks': [6, 0]}], {})
    by = {r['key']: r for r in s['field']}
    assert (by['A']['sf'], by['A']['sa'], by['B']['sf'], by['B']['sa']) == (4, 2, 2, 4)
    assert [r['key'] for r in lg.table(s)] == ['C', 'A', 'B', 'D']                       # C and A both on 3 pts: C's +6 beats A's +2
