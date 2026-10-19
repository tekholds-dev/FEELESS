import pytest
import crews as cr

W = 'Own1111111111111111111111111111111111111111'
M = 'Mem1111111111111111111111111111111111111111'


def _st():
    st = {}
    cr.create(st, W, 'Sicario', 'SIC', 0)
    return st


def test_generated_passcode_is_stored_hashed_and_joins():
    st = _st()
    c, plain = cr.set_code(st, W)
    assert len(plain) == 16 and 'code' not in c and plain not in str(c)
    assert cr.join(st, M, plain)['id'] == c['id']
    with pytest.raises(ValueError):
        cr.join(st, 'X' * 44, 'wrong-code')


def test_own_code_and_only_the_owner_sets_it():
    st = _st(); cr.join(st, M, st['crews'][next(iter(st['crews']))]['code'])
    with pytest.raises(ValueError):
        cr.set_code(st, M, 'mycode123')
    c, plain = cr.set_code(st, W, 'trench-gang')
    assert plain == 'trench-gang' and cr.code_ok(c, 'trench-gang')


def test_bounty_board_and_launch_are_points_and_words_only():
    st = _st(); cid = next(iter(st['crews'])); cr.join(st, M, st['crews'][cid]['code'])
    b = cr.bounty_add(st, W, 'find a germ entry', 50, 1)
    with pytest.raises(ValueError):
        cr.bounty_add(st, M, 'nope', 5, 1)
    cr.bounty_claim(st, M, b['id'], 'tx 5abc', 2)
    cr.bounty_settle(st, W, b['id'], True, 3)
    assert st['crews'][cid]['points'][M] == 50
    p = cr.post(st, M, '  gm   crew ', 4); cr.post(st, W, 'gm', 5, parent=p['id'])
    assert st['crews'][cid]['posts'][0]['text'] == 'gm crew'
    assert cr.launch(st, W, 'So11111111111111111111111111111111111111112', 'SOL', 'ours', 6)['symbol'] == 'SOL'
    with pytest.raises(ValueError):
        cr.launch(st, W, 'not a mint', '', '', 7)
