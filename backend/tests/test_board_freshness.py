"""📡 The launch board fetches only the coins that are DUE: the hottest every 45s, the tail every 4 min (it re-fetched ~all 660 every 20s)."""
import launchpad_board as lb


def test_only_due_coins_are_fetched_hot_first_and_the_rest_reuse_their_last_snapshot():
    mints = [f'M{i}' for i in range(300)]
    mem = {m: (1000.0, {'p': m}) for m in mints}
    assert lb.due_mints(mints, mem, 1000.0 + 30) == []                                   # everything fresh: nothing fetched
    due = lb.due_mints(mints, mem, 1000.0 + 60)
    assert due == mints[:lb.HOT_N]                                                       # 60s later only the hot coins are due
    assert len(lb.due_mints(mints, mem, 1000.0 + lb.TAIL_SEC + 1)) == 300                # the tail after 4 min
    assert lb.due_mints(['NEW'] + mints, mem, 1000.0 + 30) == ['NEW']                    # a new coin is always fetched
    assert lb.due_mints(mints, {}, 0.0, skip={'M0'})[:1] == ['M1']                      # seeded coins are never re-fetched
    assert lb.fresh_from(mints, {**mem, 'X': (1000.0, None)}, 1000.0 + 60) == {m: {'p': m} for m in mints[lb.HOT_N:]}
    assert lb.fresh_from(['X'], {'X': (1000.0, None)}, 1010.0) == {'X': None}            # "the source had nothing" is remembered too
