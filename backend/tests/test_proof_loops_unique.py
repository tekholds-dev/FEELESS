"""🔁 owner 2026-11-15: every proof loops its own way; the two minds research uniquely; PoP reads less than PoW."""
import proof_footprint as foot


def test_pop_minds_get_their_own_sites_and_angle():
    p = foot.plan('pop', '', list(foot.POP_SITES), [])
    a, b = (foot.pop_goal(p['sites'][i], p['angles'][i]) for i in range(2))
    assert a != b
    assert not set(p['sites'][0]) & set(p['sites'][1])
    assert 'Do not sign in or trade' in a and 'Your angle' in b


def test_each_proof_has_its_own_move_budget():
    assert foot.read_steps('pop') < foot.read_steps('pob') < foot.read_steps('poc')
    assert foot.read_steps('', 14) == 14


def test_angles_turn_over_from_one_proof_to_the_next():
    assert foot.angle_for('pop', [], 0) != foot.angle_for('pop', [{'id': 'x'}], 0)
