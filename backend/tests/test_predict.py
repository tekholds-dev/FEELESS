import predict as pr

LISTS = {'ptrend': [{'mint': 'A'}, {'mint': 'B'}], 'volume': [{'mint': 'A'}, {'mint': 'C'}], 'movers': [{'mint': 'X'}, {'mint': 'D'}], 'pump': [{'mint': 'E'}]}
PX = {'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0}


def test_ballot_takes_one_priced_coin_per_door_without_repeats():
    c = pr.candidates(LISTS, PX, {'A': 'AAA'})
    assert [(x['mint'], x['door']) for x in c] == [('A', 'ptrend'), ('C', 'volume'), ('D', 'movers'), ('E', 'pump')]     # X has no price → the next coin of its door
    assert c[0]['symbol'] == 'AAA' and c[1]['symbol'] == 'C'                               # a known ticker is used, else the mint's first letters
    assert len(pr.candidates(LISTS, PX, n=2)) == 2


def test_picks_close_two_minutes_before_the_bell_and_only_ballot_coins():
    rnd = pr.new_round(7200 + 10, pr.candidates(LISTS, PX))
    assert rnd['id'] == 7200 and rnd['closesAt'] == 10800
    assert pr.can_pick(rnd, 'A', 7300) == (True, '')
    assert pr.can_pick(rnd, 'A', 10800 - 60)[0] is False and pr.can_pick(rnd, 'ZZZ', 7300)[0] is False and pr.can_pick(None, 'A', 0)[0] is False


def test_the_biggest_move_wins_and_streaks_build_points_capped():
    rnd = pr.new_round(0, pr.candidates(LISTS, PX)); rnd['picks'] = {'w1': 'D', 'w2': 'A'}
    res = pr.settle(rnd, {'A': 1.1, 'C': 3.0, 'D': 5.0, 'E': 5.0})          # D +25% leads
    assert res['winner'] == 'D' and res['moves']['D'] == 25.0
    players = {'w1': {'picks': 0, 'wins': 0, 'streak': 3, 'best': 3, 'pickAt': [], 'winAt': []}}
    paid = dict(pr.award(players, rnd, 'D', 5000))
    assert paid == {'w1': 25} and players['w1']['streak'] == 4 and players['w2']['streak'] == 0           # 10 + 5 × 3 (the 4th win in a row); the loser's streak resets
    assert dict(pr.award({'w': {'picks': 0, 'wins': 0, 'streak': 20, 'best': 20, 'pickAt': [], 'winAt': []}}, {'picks': {'w': 'D'}}, 'D', 1)) == {'w': 30}   # the streak bonus is capped (+20)
    assert pr.settle(rnd, {'A': 1.0})['winner'] is None                    # fewer than two priced coins → no result, nobody loses a streak


def test_board_counts_the_week_only():
    day = 86400
    pl = {'a': {'picks': 5, 'wins': 2, 'streak': 1, 'pickAt': [1, 20 * day], 'winAt': [20 * day]}, 'b': {'picks': 1, 'wins': 0, 'streak': 0, 'pickAt': [1], 'winAt': []}}
    b = pr.board(pl, 21 * day)
    assert b == [{'address': 'a', 'wins': 1, 'picks': 1, 'streak': 1}]
