from launchpad_board import launchpad_board_snapshot, save_board_snapshot


def test_board_snapshot_round_trip_keeps_other_kinds_and_expires(tmp_path):
    p = tmp_path / 'board_snapshot.json'
    assert launchpad_board_snapshot(p, 'trending', 1000) is None                       # nothing saved yet
    save_board_snapshot(p, 'trending', [{'pairAddress': 'A'}], {'provider': 'x'}, 1000)
    save_board_snapshot(p, 'new', [{'pairAddress': 'B'}], {}, 1010)
    age, ranked, meta = launchpad_board_snapshot(p, 'trending', 1300)
    assert age == 300 and ranked == [{'pairAddress': 'A'}] and meta == {'provider': 'x'}
    assert launchpad_board_snapshot(p, 'new', 1100)[1] == [{'pairAddress': 'B'}]       # the other kind survives
    assert launchpad_board_snapshot(p, 'trending', 1000 + 901) is None                 # older than 15 min: not served
    save_board_snapshot(p, 'trending', [], {}, 2000)
    assert launchpad_board_snapshot(p, 'trending', 2001) is None                       # an empty board is never served
    p.write_text('{broken')
    assert launchpad_board_snapshot(p, 'trending', 2001) is None                       # unreadable file = cold build as before
