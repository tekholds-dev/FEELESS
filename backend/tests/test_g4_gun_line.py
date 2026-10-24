import reputation_service as rs


def test_models_never_offered_a_coin_at_its_gun_line():
    assert rs._g4_bad_entry({'chart': {'distHigh': 1.6}, 'nums': {'d5': -2.4}})        # $1: 1.6% under the gun line
    assert rs._g4_bad_entry({'chart': {'distHigh': 20}, 'nums': {'d5': 1}, 'chartCall': 'SKIP'})
    assert rs._g4_bad_entry({'chart': {'distHigh': 20, 'germDist': 4}, 'nums': {'d5': 1}, 'chartCall': 'ENTER NOW'}) is None


def test_models_never_chase_a_parabolic_or_a_spike_far_over_its_germ():
    # 2026-10-23 audit (179 closed model trades): PARABOLIC / E2 entries 10 trades, 1 won · a spike 5–10% over its germ −10.7% avg.
    # $mil: +23.9% in 5 min, 12% over its germ — the 15% germ line exempted it from spike_chase, OSSY bought it, −17.7%.
    mil = {'mint': 'MIL', 'chart': {'distHigh': 60, 'germDist': 12.1, 'state': 'CHOP'}, 'nums': {'d5': 23.9}, 'chartCall': 'WAIT'}
    assert 'germ floor' in rs._g4_bad_entry(mil)
    assert rs._g4_bad_entry({**mil, 'chart': {**mil['chart'], 'germDist': 3}}) is None                         # a spike back ON its germ is the entry
    assert 'PARABOLIC' in rs._g4_bad_entry({'mint': 'P', 'chart': {'distHigh': 30, 'germDist': 2, 'state': 'PARABOLIC'}, 'nums': {'d5': 2}})
    assert 'PARABOLIC' in rs._g4_bad_entry({'mint': 'E', 'chart': {'distHigh': 30, 'germDist': 2, 'state': 'RANGE',
                                                                  'entry': ['WAIT FOR PULLBACK', 'E2 no chasing', '+30% in 5 min']}, 'nums': {'d5': 2}})
    assert rs._g4_bad_entry({'mint': 'OK', 'chart': {'distHigh': 30, 'germDist': 2, 'state': 'PULLBACK IN UPTREND',
                                                     'entry': ['WAIT FOR CONFIRMATION', 'E9 pullback not turned']}, 'nums': {'d5': 3}}) is None   # the one entry that paid
