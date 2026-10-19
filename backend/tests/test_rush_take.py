import office as of


def _leg(**k):
    return {'pairAddress': 'P', 'mint': 'M', 'symbol': 'X', 'entry': 1.0, 'units': 10, 'real': True, 'aiSeat': True, 'aiBy': 'G4', 'aiTp': 30, **k}


def test_model_take_is_sold_at_the_line_on_a_quiet_tape():
    pulls, raises = of.rush_take([_leg()], {'M': 1.31}, {}, 1000)
    assert pulls and 'R6m' in pulls[0][1] and not raises


def test_model_take_under_the_line_does_nothing():
    assert of.rush_take([_leg()], {'M': 1.2}, {}, 1000) == ([], [])


def test_volume_rush_at_the_take_raises_it_with_a_trail_then_honours_after_three():
    hot = {'P': {'state': 'BUYERS', 'hot': True}}
    pulls, raises = of.rush_take([_leg()], {'M': 1.32}, hot, 1000)
    assert not pulls and raises[0][1]['aiTp'] >= 39 and raises[0][1]['aiTrail'] == of.RUSH_TRAIL
    assert of.rush_take([_leg(rushN=3)], {'M': 1.32}, hot, 1000)[0]


def test_your_pick_is_never_touched():
    assert of.rush_take([_leg(aiSeat=False, picked=True, tags=None)], {'M': 2.0}, {}, 1000) == ([], [])
