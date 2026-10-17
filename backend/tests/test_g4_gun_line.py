import reputation_service as rs


def test_models_never_offered_a_coin_at_its_gun_line():
    assert rs._g4_bad_entry({'chart': {'distHigh': 1.6}, 'nums': {'d5': -2.4}})        # $1: 1.6% under the gun line
    assert rs._g4_bad_entry({'chart': {'distHigh': 20}, 'nums': {'d5': 1}, 'chartCall': 'SKIP'})
    assert rs._g4_bad_entry({'chart': {'distHigh': 20, 'germDist': 4}, 'nums': {'d5': 1}, 'chartCall': 'ENTER NOW'}) is None
