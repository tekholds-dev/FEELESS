"""🧭 Every proof walks a new path: the angles turn each proof, the two minds never share one, used sites go last, and each kind has its own fallback."""
import proof_footprint as fp


def test_angles_turn_every_proof_and_the_minds_never_share():
    for kind in fp.ANGLES:
        seen = []
        for n in range(3):
            folders = [{'id': str(i)} for i in range(n)]
            a, b = fp.angle_for(kind, folders, 0), fp.angle_for(kind, folders, 1)
            assert a != b
            seen += [a, b]
        assert len(set(seen)) == 6   # three proofs in a row use all six angles, none twice


def test_sites_the_last_proofs_used_go_last():
    folders = [{'id': '1', 'sites': ['https://espn.com/x']}, {'id': '2', 'sites': ['https://espn.com/y', 'https://rotowire.com']}]
    order = fp.order_sites('pob', ['https://espn.com', 'https://rotowire.com', 'https://covers.com', 'https://teamrankings.com'], folders)
    assert set(order) == {'https://espn.com', 'https://rotowire.com', 'https://covers.com', 'https://teamrankings.com'}
    assert order.index('https://espn.com') > order.index('https://covers.com') and order.index('https://espn.com') == 3


def test_every_kind_says_what_to_do_when_a_step_fails():
    for kind in ('pob', 'pop', 'poc', 'pow', 'pos'):
        assert 'IF A STEP FAILS' in fp.note(kind, [{'id': '1', 'topic': 'knicks'}], 0)
        assert 'IF A STEP FAILS' in fp.note(kind, [], 1) and 'YOUR ANGLE' in fp.note(kind, [], 1)
    assert 'never invent' in fp.FALLBACKS['pob']
