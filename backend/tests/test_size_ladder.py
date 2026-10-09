import arena_prime as ap


def test_ladder_stages_climb_with_the_card_and_hold_on_small_dips():
    assert ap.ladder_stage(2) == 'trench' and ap.ladder_stage(12) == 'runner' and ap.ladder_stage(150) == 'sniper'
    assert ap.ladder_stage(2500) == 'bluechip' and ap.ladder_stage(100000) == 'majors'
    assert ap.ladder_stage(9, 'runner') == 'runner'      # 90% of the $10 floor keeps the stage
    assert ap.ladder_stage(7.9, 'runner') == 'trench'    # under 80% steps down
    assert ap.ladder_stage(50, 'trench') == 'runner'     # up at once


def test_every_ladder_value_is_a_real_editor_option():
    for key, _f, _n, _w, patch in ap.LADDER:
        out = ap.clean_cfg(ap.ladder_patch({'ladder': True}, key))
        for k, v in patch.items():
            if k == 'cycles':
                assert all(out['cycles'][t] == c for t, c in v.items()), key
            else:
                assert out[k] == v or float(out[k]) == float(v), (key, k, out[k], v)
        assert out['ladder'] is True


def test_ladder_view_names_the_next_stage():
    v = ap.ladder_view('trench')
    assert v['next']['at'] == 10 and len(v['stages']) == 5 and ap.ladder_view('majors')['next'] is None


def test_a_setting_the_owner_taps_beats_the_ladder():
    out = ap.clean_cfg(ap.ladder_patch({'ladder': True, 'coins': 4, 'sl': 20.0}, 'trench', keep=['coins']))
    assert out['coins'] == 4 and out['sl'] == 15.0   # coins kept (tapped), stop still the stage's
    assert 'coins' in ap.ladder_keys('trench') and 'cycles' in ap.ladder_keys('majors')
