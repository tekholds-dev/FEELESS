"""🎩 All 4 seats for Sicario's PoWs, Auto-collect until full, and desk buys off still stops everything else. No network, no card."""
import ai_seat as seat


def legs(*ai, placeholder=0):
    return [{'mint': f'm{i}', 'aiSeat': a} for i, a in enumerate(ai)] + [{'mint': f'p{i}', 'placeholder': True} for i in range(placeholder)]


def test_a_placeholder_sits_in_no_seat():
    assert seat.card_seats(legs(True, False, placeholder=1), 4) == {'seats': 4, 'held': 2, 'ai': 1, 'free': 2}


def test_three_held_still_lets_the_fourth_in_and_four_refuses():
    assert seat.sicario_refusal(None, legs(True, True, True), 4, 'new', 100) is None
    assert 'full' in seat.sicario_refusal(None, legs(True, True, True, True), 4, 'new', 100)


def test_it_never_doubles_a_coin_or_overwrites_a_pending_order():
    assert 'already' in seat.sicario_refusal(None, legs(True), 4, 'm0', 100)
    assert 'deciding' in seat.sicario_refusal({'action': 'SELL', 'at': 95, 'mint': 'm0'}, legs(True), 4, 'new', 100)


def test_desk_buys_off_only_passes_the_coin_sicario_asked_for():
    plan = [{'mint': 'a', 'g4': True}, {'mint': 'b'}]
    assert seat.desk_off_plan(plan, True) == [{'mint': 'a', 'g4': True}]
    assert seat.desk_off_plan(plan, False) == []
    assert seat.desk_off_plan(None, True) == []


def test_every_model_seat_gets_its_review_in_turn():
    l_ = legs(True, False, True)
    assert {seat.review_leg(l_, m * 60)['mint'] for m in range(4)} == {'m0', 'm2'}
    assert seat.review_leg(legs(False), 0) is None


def test_auto_collect_files_pows_only_while_seats_are_free():
    import feecat_service as fs
    fs._POW_WANT.clear()
    c = {'id': 's', 'handle': 'sicarios', 'hive': {'on': True}, 'brainsCfg': {'mindNames': ['OSSY', 'G4']}}
    fs._sicario_loop({'cats': {'s': c}}, 1000.0, 0)
    assert 's' not in fs._POW_WANT and not c['brainsCfg'].get('cardSeat')
    fs._sicario_loop({'cats': {'s': c}}, 1000.0, None)
    assert 's' not in fs._POW_WANT
    fs._sicario_loop({'cats': {'s': c}}, 1000.0, 2)
    assert fs._POW_WANT.pop('s')['do'] == 'start' and c['brainsCfg']['cardSeat'] is True
    fs._sicario_loop({'cats': {'s': c}}, 1000.0 + fs.SICARIO_FILL_GAP_S - 1, 2)
    assert 's' not in fs._POW_WANT   # rested between PoWs
    c['hive']['on'] = False
    fs._sicario_loop({'cats': {'s': c}}, 9000.0, 2)
    assert 's' not in fs._POW_WANT   # off means off


def test_a_rested_run_from_the_last_proof_does_not_block_the_next():
    import feecat_service as fs
    fs._POW_WANT.clear()
    c = {'id': 's', 'handle': 'sicarios', 'hive': {'on': True}, 'powRun': {'n': 2, 'rested': 1.0}, 'brainsCfg': {'mindNames': ['OSSY', 'G4']}}
    fs._sicario_loop({'cats': {'s': c}}, 1000.0, 1)
    assert fs._POW_WANT.pop('s')['do'] == 'start'
    c['powRun']['folder'] = {'id': 'f'}; c['brainsCfg']['loopAt'] = 0
    fs._sicario_loop({'cats': {'s': c}}, 2000.0, 1)
    assert 's' not in fs._POW_WANT
